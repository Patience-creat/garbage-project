"""
数据准备 — 为12类垃圾生成紧致边界框 + 合成多目标训练数据
替代旧版 prepare_data.py（只生成整图框）

流程：
  1. 对每张原图用图像分割自动提取物体 → 生成紧致 YOLO 框
  2. 合成多目标图片（2~4个垃圾随机拼接到一张图上）
  3. 划分 train/val，输出可直接用于 yolo detect train

用法：
  python prepare_detection_data.py
"""
import os
import cv2
import numpy as np
import random
import shutil
from glob import glob
from datetime import datetime

random.seed(42)
np.random.seed(42)

# ─── 配置 ───────────────────────────────────────────────
RAW_ROOT = r"D:/archive/garbage_classification"
OUTPUT_ROOT = r"D:/archive/garbage_classification/yolo_dataset_v2"

CLASSES = [
    "battery", "biological", "brown-glass", "cardboard", "clothes",
    "green-glass", "metal", "paper", "plastic", "shoes", "trash", "white-glass",
]
CLASS_ID_MAP = {name: i for i, name in enumerate(CLASSES)}

TRAIN_RATIO = 0.85
VAL_RATIO = 0.15

# 合成多目标参数
COMPOSITE_PER_CLASS = 40      # 每类合成多少张多目标图
MAX_OBJECTS_PER_IMAGE = 5     # 每张合成图最多放几个物体
MIN_OBJECTS_PER_IMAGE = 2     # 最少放几个
COMPOSITE_SIZE = 640          # 合成图尺寸（YOLO 默认输入尺寸）

os.makedirs(OUTPUT_ROOT, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 第一步：为每张原图生成紧致边界框
# ═══════════════════════════════════════════════════════════

def find_tight_bbox(image):
    """用自适应方法找到物体的紧致边界框

    Returns:
        (x1, y1, x2, y2) 像素坐标，或 None 如果图像为空
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 方法1：高斯模糊 + Otsu 二值化
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 形态学闭运算填充孔洞
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

    # 找轮廓
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # 取面积最大的轮廓
        largest = max(contours, key=cv2.contourArea)
        x, y, bw, bh = cv2.boundingRect(largest)
        area_ratio = (bw * bh) / (w * h)

        # 如果框太小（<5%）或太大（>95%），用边缘检测法试试
        if area_ratio < 0.05 or area_ratio > 0.95:
            return _find_bbox_by_edges(gray, w, h)

        # 稍微向内收缩一点去掉背景边缘
        shrink = 2
        return (x + shrink, y + shrink, x + bw - shrink, y + bh - shrink)

    return _find_bbox_by_edges(gray, w, h)


def _find_bbox_by_edges(gray, w, h):
    """边缘检测法找物体边界（Otsu 失效时的备用方案）"""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        x, y, bw, bh = cv2.boundingRect(largest)
        area_ratio = (bw * bh) / (w * h)

        # 如果框还太大，用中心缩进法
        if area_ratio > 0.90:
            margin_x = int(w * 0.12)
            margin_y = int(h * 0.12)
            return (margin_x, margin_y, w - margin_x, h - margin_y)

        return (x, y, x + bw, y + bh)

    # 实在找不到轮廓：保守地取中心 70% 区域
    margin_x = int(w * 0.15)
    margin_y = int(h * 0.15)
    return (margin_x, margin_y, w - margin_x, h - margin_y)


def bbox_to_yolo(x1, y1, x2, y2, img_w, img_h):
    """像素坐标 → YOLO 格式 (x_center, y_center, width, height) 归一化"""
    x_c = ((x1 + x2) / 2) / img_w
    y_c = ((y1 + y2) / 2) / img_h
    bw = (x2 - x1) / img_w
    bh = (y2 - y1) / img_h
    # 防止超出边界
    bw = max(0.01, min(bw, 0.99))
    bh = max(0.01, min(bh, 0.99))
    x_c = max(bw / 2, min(x_c, 1 - bw / 2))
    y_c = max(bh / 2, min(y_c, 1 - bh / 2))
    return x_c, y_c, bw, bh


def process_raw_images():
    """为所有原始图片生成紧致边界框标注"""
    print("=" * 60)
    print("第一步：为原图生成紧致边界框")
    print("=" * 60)

    for split in ['train', 'val']:
        img_dir = os.path.join(OUTPUT_ROOT, split, 'images')
        label_dir = os.path.join(OUTPUT_ROOT, split, 'labels')
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(label_dir, exist_ok=True)

    all_images = []
    for cls_name in CLASSES:
        cls_dir = os.path.join(RAW_ROOT, cls_name)
        if not os.path.isdir(cls_dir):
            continue
        imgs = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        for img_name in imgs:
            all_images.append((cls_name, os.path.join(cls_dir, img_name), img_name))

    random.shuffle(all_images)
    split_idx = int(len(all_images) * TRAIN_RATIO)
    train_set = all_images[:split_idx]
    val_set = all_images[split_idx:]

    stats = {"total": len(all_images), "train": len(train_set), "val": len(val_set)}
    bbox_fail = 0

    for split_name, dataset in [("train", train_set), ("val", val_set)]:
        img_dir = os.path.join(OUTPUT_ROOT, split_name, 'images')
        label_dir = os.path.join(OUTPUT_ROOT, split_name, 'labels')

        for cls_name, src_path, img_name in dataset:
            img = cv2.imread(src_path)
            if img is None:
                continue

            h, w = img.shape[:2]
            bbox = find_tight_bbox(img)

            if bbox is None:
                bbox_fail += 1
                # 兜底：90% 中心区域
                margin_x = int(w * 0.05)
                margin_y = int(h * 0.05)
                bbox = (margin_x, margin_y, w - margin_x, h - margin_y)

            x1, y1, x2, y2 = bbox
            x_c, y_c, bw, bh = bbox_to_yolo(x1, y1, x2, y2, w, h)
            cls_id = CLASS_ID_MAP[cls_name]

            # 复制图片
            dst_img = os.path.join(img_dir, img_name)
            cv2.imwrite(dst_img, img)

            # 写标注
            label_name = os.path.splitext(img_name)[0] + '.txt'
            label_path = os.path.join(label_dir, label_name)
            with open(label_path, 'w') as f:
                f.write(f"{cls_id} {x_c:.6f} {y_c:.6f} {bw:.6f} {bh:.6f}\n")

    print(f"  总图片: {stats['total']}")
    print(f"  训练集: {stats['train']}  |  验证集: {stats['val']}")
    print(f"  兜底回退: {bbox_fail} 张")
    return stats, train_set, val_set


# ═══════════════════════════════════════════════════════════
# 第二步：合成多目标训练图片
# ═══════════════════════════════════════════════════════════

def extract_object(img, bbox, target_size=200):
    """根据边界框提取物体，缩放到统一大小（带透明背景）"""
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
    obj = img[y1:y2, x1:x2]
    if obj.size == 0:
        return None
    # 缩放保持宽高比
    h, w = obj.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    obj = cv2.resize(obj, (new_w, new_h))
    return obj


def paste_object(canvas, obj, x, y):
    """将物体粘贴到画布上（带羽化边缘）"""
    oh, ow = obj.shape[:2]
    ch, cw = canvas.shape[:2]
    # 边界检查
    if x + ow > cw: ow = cw - x
    if y + oh > ch: oh = ch - y
    if ow <= 0 or oh <= 0:
        return
    canvas[y:y+oh, x:x+ow] = obj[:oh, :ow]


def generate_composite_images(train_set, val_set):
    """生成合成多目标图片 — 多个垃圾物体随机拼接到一张图上"""
    print("\n" + "=" * 60)
    print("第二步：合成多目标训练图片")
    print("=" * 60)

    # 预计算所有物体的紧致框和裁剪图
    objects_pool = []  # [(cls_id, cropped_img), ...]
    for cls_name, src_path, img_name in train_set + val_set:
        img = cv2.imread(src_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        bbox = find_tight_bbox(img)
        if bbox is None:
            continue
        obj = extract_object(img, bbox)
        if obj is None:
            continue
        cls_id = CLASS_ID_MAP[cls_name]
        objects_pool.append((cls_id, obj))

    print(f"  可用物体数: {len(objects_pool)}")

    random.shuffle(objects_pool)
    total_composite = 0

    for split_name, n_composite in [("train", int(COMPOSITE_PER_CLASS * len(CLASSES) * 0.85)),
                                      ("val", int(COMPOSITE_PER_CLASS * len(CLASSES) * 0.15))]:
        if n_composite == 0:
            continue

        img_dir = os.path.join(OUTPUT_ROOT, split_name, 'images')
        label_dir = os.path.join(OUTPUT_ROOT, split_name, 'labels')

        for i in range(n_composite):
            canvas = np.full((COMPOSITE_SIZE, COMPOSITE_SIZE, 3), 45, dtype=np.uint8)
            n_objects = random.randint(MIN_OBJECTS_PER_IMAGE,
                                       min(MAX_OBJECTS_PER_IMAGE, len(objects_pool)))
            selected = random.sample(objects_pool, n_objects)

            annotations = []
            placed = []
            attempts = 0

            for cls_id, obj_img in selected:
                if obj_img is None:
                    continue
                oh, ow = obj_img.shape[:2]

                # 随机缩放 0.6~1.0
                scale = random.uniform(0.6, 1.0)
                new_w, new_h = int(ow * scale), int(oh * scale)
                obj_scaled = cv2.resize(obj_img, (new_w, new_h))

                # 找不重叠的位置（最多尝试 20 次）
                placed_success = False
                for _ in range(20):
                    x = random.randint(0, COMPOSITE_SIZE - new_w)
                    y = random.randint(0, COMPOSITE_SIZE - new_h)

                    # 检查是否与已放置的物体重叠
                    overlap = False
                    for (px, py, pw, ph) in placed:
                        if (x < px + pw and x + new_w > px and
                                y < py + ph and y + new_h > py):
                            overlap = True
                            break
                    if not overlap:
                        placed_success = True
                        break

                if placed_success:
                    paste_object(canvas, obj_scaled, x, y)
                    placed.append((x, y, new_w, new_h))

                    # YOLO 坐标
                    x_c = (x + new_w / 2) / COMPOSITE_SIZE
                    y_c = (y + new_h / 2) / COMPOSITE_SIZE
                    bw_n = new_w / COMPOSITE_SIZE
                    bh_n = new_h / COMPOSITE_SIZE
                    annotations.append(f"{cls_id} {x_c:.6f} {y_c:.6f} {bw_n:.6f} {bh_n:.6f}")

                attempts += 1
                if attempts > 20:
                    break

            # 只在有 >=2 个物体时保存
            if len(annotations) >= 2:
                img_name = f"composite_{split_name}_{i:04d}.jpg"
                label_name = f"composite_{split_name}_{i:04d}.txt"

                cv2.imwrite(os.path.join(img_dir, img_name), canvas)
                with open(os.path.join(label_dir, label_name), 'w') as f:
                    f.write("\n".join(annotations))
                total_composite += 1

    print(f"  合成多目标图片数: {total_composite}")
    return total_composite


# ═══════════════════════════════════════════════════════════
# 第三步：生成 YAML 配置
# ═══════════════════════════════════════════════════════════

def write_yaml():
    """写入训练用的 YAML 配置文件"""
    yaml_path = os.path.join(OUTPUT_ROOT, "dataset.yaml")
    content = f"""# 自动生成: 紧致边界框 + 合成多目标数据
train: {OUTPUT_ROOT}/train/images
val: {OUTPUT_ROOT}/val/images

nc: {len(CLASSES)}
names:
"""
    for i, name in enumerate(CLASSES):
        content += f"  {i}: {name}\n"
    with open(yaml_path, 'w') as f:
        f.write(content)
    print(f"\n  YAML 配置: {yaml_path}")
    return yaml_path


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    start = datetime.now()
    print(f"开始时间: {start}")

    # 清空输出目录（保留原始数据不动）
    if os.path.exists(OUTPUT_ROOT):
        shutil.rmtree(OUTPUT_ROOT)

    # 第一步：紧致边界框
    stats, train_set, val_set = process_raw_images()

    # 第二步：合成多目标
    n_composite = generate_composite_images(train_set, val_set)

    # 写 YAML
    yaml_path = write_yaml()

    # 统计
    train_imgs = len(glob(os.path.join(OUTPUT_ROOT, "train/images", "*")))
    val_imgs = len(glob(os.path.join(OUTPUT_ROOT, "val/images", "*")))
    train_labels = len(glob(os.path.join(OUTPUT_ROOT, "train/labels", "*")))
    val_labels = len(glob(os.path.join(OUTPUT_ROOT, "val/labels", "*")))

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'='*60}")
    print(f"✅ 数据准备完成! 耗时: {elapsed:.0f} 秒")
    print(f"{'='*60}")
    print(f"  训练图片: {train_imgs} 张 (含 {n_composite} 张合成多目标)")
    print(f"  验证图片: {val_imgs} 张")
    print(f"  训练标注: {train_labels} 个文件")
    print(f"  验证标注: {val_labels} 个文件")
    print(f"  输出目录: {OUTPUT_ROOT}")
    print(f"  YAML路径: {yaml_path}")
