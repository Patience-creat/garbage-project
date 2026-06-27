"""
增强版多目标训练数据生成器
用真实世界背景图 + 从原图提取的垃圾物体 → 合成多目标检测训练数据
"""
import os, cv2, numpy as np, random, glob, urllib.request, shutil

random.seed(42)
np.random.seed(42)

# 配置
RAW_ROOT = r"D:/archive/garbage_classification"
BG_DIR = r"D:/archive/backgrounds"
OUTPUT_ROOT = r"D:/archive/garbage_classification/yolo_dataset_v3"

CLASSES = [
    "battery", "biological", "brown-glass", "cardboard", "clothes",
    "green-glass", "metal", "paper", "plastic", "shoes", "trash", "white-glass",
]
CLASS_ID_MAP = {n: i for i, n in enumerate(CLASSES)}

N_COMPOSITE_TRAIN = 3000   # 生成 3000 张合成训练图
N_COMPOSITE_VAL = 300      # 生成 300 张合成验证图
MAX_OBJ = 6                # 每张最多放 6 个物体
MIN_OBJ = 2                # 最少 2 个
IMG_SIZE = 640

os.makedirs(OUTPUT_ROOT, exist_ok=True)


# ─── 第一步：下载背景图 ───

def download_backgrounds(n=200):
    """从 picsum.photos 下载免费背景图"""
    existing = glob.glob(f"{BG_DIR}/*.jpg")
    if len(existing) >= n:
        print(f"  已有 {len(existing)} 张背景图，跳过下载")
        return existing[:n]

    os.makedirs(BG_DIR, exist_ok=True)
    count = 0
    for i in range(n * 3):  # 多试几次
        if count >= n:
            break
        try:
            url = f"https://picsum.photos/640/480?random={count + 100}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as f:
                path = f"{BG_DIR}/bg_{count:03d}.jpg"
                with open(path, "wb") as out:
                    out.write(f.read())
                count += 1
                if count % 20 == 0:
                    print(f"    下载进度: {count}/{n}")
        except Exception:
            continue
    print(f"  下载完成: {count} 张背景图")
    return glob.glob(f"{BG_DIR}/*.jpg")[:n]


# ─── 第二步：从原图提取物体 ───

def find_tight_bbox(img):
    """找物体紧致边界框"""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        x, y, bw, bh = cv2.boundingRect(max(contours, key=cv2.contourArea))
        ar = (bw * bh) / (w * h)
        if 0.05 <= ar <= 0.95:
            return (max(0, x - 2), max(0, y - 2),
                    min(w, x + bw + 2), min(h, y + bh + 2))
    # 兜底
    mx, my = int(w * 0.1), int(h * 0.1)
    return (mx, my, w - mx, h - my)


def extract_objects():
    """从原图提取所有物体"""
    objects = []
    for cls_name in CLASSES:
        cls_dir = os.path.join(RAW_ROOT, cls_name)
        if not os.path.isdir(cls_dir):
            continue
        imgs = [f for f in os.listdir(cls_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        random.shuffle(imgs)
        for img_name in imgs[:300]:  # 每类最多取 300 张
            path = os.path.join(cls_dir, img_name)
            img = cv2.imread(path)
            if img is None:
                continue
            h, w = img.shape[:2]
            x1, y1, x2, y2 = find_tight_bbox(img)
            obj = img[y1:y2, x1:x2]
            if obj.size == 0 or obj.shape[0] < 10 or obj.shape[1] < 10:
                continue
            objects.append((CLASS_ID_MAP[cls_name], obj))
    print(f"  提取物体: {len(objects)} 个")
    return objects


# ─── 第三步：合成多目标图 ───

def paste_with_shadow(canvas, obj, x, y, w, h):
    """带简单羽化边缘粘贴物体"""
    if y + h > canvas.shape[0] or x + w > canvas.shape[1]:
        return
    obj_resized = cv2.resize(obj, (w, h))
    canvas[y:y+h, x:x+w] = obj_resized


def generate_composites(objects, backgrounds, n_images, split_name):
    """生成多目标合成图"""
    img_dir = os.path.join(OUTPUT_ROOT, split_name, "images")
    label_dir = os.path.join(OUTPUT_ROOT, split_name, "labels")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(label_dir, exist_ok=True)

    generated = 0
    for idx in range(n_images):
        bg = cv2.imread(random.choice(backgrounds))
        if bg is None:
            continue
        bg = cv2.resize(bg, (IMG_SIZE, IMG_SIZE))

        n_obj = random.randint(MIN_OBJ, min(MAX_OBJ, len(objects)))
        selected = random.sample(objects, min(n_obj, len(objects)))

        annotations = []
        placed = []
        for cls_id, obj_img in selected:
            oh, ow = obj_img.shape[:2]
            # 随机缩放 0.25~0.7，让物体在场景中自然
            scale = random.uniform(0.25, 0.7)
            nw, nh = max(30, int(ow * scale)), max(30, int(oh * scale))

            # 随机旋转 -15°~15°
            try:
                M = cv2.getRotationMatrix2D((ow / 2, oh / 2), random.uniform(-15, 15), 1.0)
                obj_img = cv2.warpAffine(obj_img, M, (ow, oh), borderMode=cv2.BORDER_REPLICATE)
            except Exception:
                pass

            obj_resized = cv2.resize(obj_img, (nw, nh))

            # 找不重叠位置
            for _ in range(40):
                x = random.randint(10, IMG_SIZE - nw - 10)
                y = random.randint(10, IMG_SIZE - nh - 10)
                if not any(x < px+pw and x+nw > px and y < py+ph and y+nh > py
                          for (px, py, pw, ph) in placed):
                    break
            else:
                continue  # 找不到位置就跳过这个物体

            paste_with_shadow(bg, obj_resized, x, y, nw, nh)
            placed.append((x, y, nw, nh))

            x_c = (x + nw / 2) / IMG_SIZE
            y_c = (y + nh / 2) / IMG_SIZE
            annotations.append(f"{cls_id} {x_c:.6f} {y_c:.6f} {nw/IMG_SIZE:.6f} {nh/IMG_SIZE:.6f}")

        if len(annotations) >= MIN_OBJ:
            cv2.imwrite(f"{img_dir}/composite_{split_name}_{idx:04d}.jpg", bg)
            with open(f"{label_dir}/composite_{split_name}_{idx:04d}.txt", "w") as f:
                f.write("\n".join(annotations))
            generated += 1

    return generated


# ─── 第四步：也把原始图（单目标）复制进去 ───

def copy_original_images(split_name, class_name, imgs, start_idx):
    """复制原始图（单目标，但用紧致框）到训练集"""
    img_dir = os.path.join(OUTPUT_ROOT, split_name, "images")
    label_dir = os.path.join(OUTPUT_ROOT, split_name, "labels")
    cls_id = CLASS_ID_MAP[class_name]
    count = 0
    for i, img_name in enumerate(imgs):
        src = os.path.join(RAW_ROOT, class_name, img_name)
        img = cv2.imread(src)
        if img is None:
            continue
        h, w = img.shape[:2]
        x1, y1, x2, y2 = find_tight_bbox(img)
        x_c = ((x1 + x2) / 2) / w
        y_c = ((y1 + y2) / 2) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        bw = max(0.02, min(bw, 0.98))
        bh = max(0.02, min(bh, 0.98))

        out_name = f"orig_{start_idx + i:05d}.jpg"
        cv2.imwrite(f"{img_dir}/{out_name}", img)
        with open(f"{label_dir}/{out_name.replace('.jpg', '.txt')}", "w") as f:
            f.write(f"{cls_id} {x_c:.6f} {y_c:.6f} {bw:.6f} {bh:.6f}\n")
        count += 1
    return count


# ═══════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import time
    t0 = time.time()

    # 清理输出
    if os.path.exists(OUTPUT_ROOT):
        shutil.rmtree(OUTPUT_ROOT)

    print("=" * 60)
    print("第一步：下载背景图")
    print("=" * 60)
    bgs = download_backgrounds(200)

    print("\n" + "=" * 60)
    print("第二步：提取物体")
    print("=" * 60)
    objects = extract_objects()

    print("\n" + "=" * 60)
    print("第三步：生成合成多目标训练/验证图")
    print("=" * 60)
    n_train = generate_composites(objects, bgs, N_COMPOSITE_TRAIN, "train")
    n_val = generate_composites(objects, bgs, N_COMPOSITE_VAL, "val")
    print(f"  合成训练图: {n_train}  合成验证图: {n_val}")

    # 也复制一些原始单目标图（用紧致框）
    print("\n" + "=" * 60)
    print("第四步：复制原始单目标图（紧致框）")
    print("=" * 60)
    total_orig_train = 0
    total_orig_val = 0
    for cls_name in CLASSES:
        cls_dir = os.path.join(RAW_ROOT, cls_name)
        if not os.path.isdir(cls_dir):
            continue
        imgs = [f for f in os.listdir(cls_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        random.shuffle(imgs)
        split = int(len(imgs) * 0.85)
        # 训练集
        n = copy_original_images("train", cls_name, imgs[:split], total_orig_train)
        total_orig_train += n
        # 验证集
        n = copy_original_images("val", cls_name, imgs[split:split + 50], total_orig_val)
        total_orig_val += n

    print(f"  原始训练图: {total_orig_train}  原始验证图: {total_orig_val}")

    # 第五步：写 YAML
    yaml_path = os.path.join(OUTPUT_ROOT, "dataset.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"""train: {OUTPUT_ROOT}/train/images
val: {OUTPUT_ROOT}/val/images
nc: {len(CLASSES)}
names:
""")
        for i, name in enumerate(CLASSES):
            f.write(f"  {i}: {name}\n")

    # 统计
    train_imgs = len(glob.glob(f"{OUTPUT_ROOT}/train/images/*"))
    val_imgs = len(glob.glob(f"{OUTPUT_ROOT}/val/images/*"))

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"完成! 耗时: {elapsed:.0f}s")
    print(f"  训练集: {train_imgs} 张")
    print(f"  验证集: {val_imgs} 张")
    print(f"  YAML: {yaml_path}")
    print(f"{'='*60}")
