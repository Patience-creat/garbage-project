"""
合并训练脚本 — 融合多个数据集 → 12类多目标检测模型

台式机执行：
  1. 确保三个数据源已准备好
  2. python merge_train.py
  3. 把桌面 best_merged.pt 拷回笔记本
"""
import os, sys, glob, shutil, random, cv2, numpy as np, zipfile, urllib.request
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# ═══════════════════════════════════════
# 配置 — 按实际情况修改路径
# ═══════════════════════════════════════
KAGGLE_DIR = r"D:/Garbage Classification"     # Kaggle (6类, 1万张)
DLLG_DIR = r"D:/DLLG_datasets/DLLG_YOLO"            # 博主B站视频同款 (3类路垃圾)
RAW_ZIP = r"D:/garbage_dataset.zip"           # 原始12类数据包
OUT_DIR = r"D:/garbage_merged"           # 输出目录

# 目标 12 类
CLASSES = ['battery','biological','brown-glass','cardboard','clothes',
           'green-glass','metal','paper','plastic','shoes','trash','white-glass']
CID = {n:i for i,n in enumerate(CLASSES)}

# Kaggle 6类 → 目标12类映射
KAGGLE_MAP = {
    'Cardboard': 'cardboard',
    'Glass': 'brown-glass',     # 统一归到玻璃
    'Metal': 'metal',
    'Paper': 'paper',
    'Plastic': 'plastic',
    'Trash': 'trash',
}

def find_bbox(img):
    h,w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, o = cv2.threshold(cv2.GaussianBlur(gray,(5,5),0), 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5))
    o = cv2.morphologyEx(cv2.morphologyEx(o,cv2.MORPH_CLOSE,k),cv2.MORPH_OPEN,k)
    c,_ = cv2.findContours(o, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if c:
        x,y,bw,bh = cv2.boundingRect(max(c,key=cv2.contourArea))
        if 0.05 <= (bw*bh)/(w*h) <= 0.95: return x,y,x+bw,y+bh
    mx,my = int(w*0.1),int(h*0.1); return mx,my,w-mx,h-my

def main():
    if os.path.exists(OUT_DIR): shutil.rmtree(OUT_DIR)
    for d in ['train/images','train/labels','val/images','val/labels']:
        os.makedirs(f'{OUT_DIR}/{d}', exist_ok=True)

    total = 0  # 总图片计数

    # ═══════════════════════════════════════
    # 1. Kaggle 数据集 (6类, 真实多目标, 1万张)
    # ═══════════════════════════════════════
    print("="*60)
    print("1. Kaggle 数据集 (6类真实多目标)")
    print("="*60)

    kaggle_used = 0
    if os.path.exists(KAGGLE_DIR):
        for split_name, target_split in [('train','train'), ('valid','val'), ('test','val')]:
            img_dir = f'{KAGGLE_DIR}/{split_name}/images'
            label_dir = f'{KAGGLE_DIR}/{split_name}/labels'
            if not os.path.isdir(img_dir) or not os.path.isdir(label_dir):
                # 试试其他目录结构
                img_dir = f'{KAGGLE_DIR}/images/{split_name}'
                label_dir = f'{KAGGLE_DIR}/labels/{split_name}'
            if not os.path.isdir(img_dir):
                continue

            for lf in glob.glob(f'{label_dir}/*.txt'):
                base = os.path.basename(lf).replace('.txt','')
                img_paths = [f'{img_dir}/{base}.jpg', f'{img_dir}/{base}.png',
                             f'{img_dir}/{base}.jpeg']
                img_path = next((p for p in img_paths if os.path.exists(p)), None)
                if not img_path: continue

                with open(lf) as f:
                    lines = f.read().strip().split('\n')
                if not lines or lines[0] == '': continue

                target_anns = []
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) != 5: continue
                    cls_id, xc, yc, wn, hn = int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                    # Kaggle 的 classes.txt 或 data.yaml
                    cls_name = KAGGLE_MAP.get(str(cls_id), None) or \
                               KAGGLE_MAP.get({0:'Cardboard',1:'Glass',2:'Metal',3:'Paper',4:'Plastic',5:'Trash'}.get(cls_id), None)
                    if cls_name is None: continue
                    target_anns.append((CID[cls_name], xc, yc, wn, hn))

                if not target_anns: continue

                fn = f'kaggle_{kaggle_used:05d}.jpg'
                shutil.copy2(img_path, f'{OUT_DIR}/{target_split}/images/{fn}')
                with open(f'{OUT_DIR}/{target_split}/labels/{fn.replace(".jpg",".txt")}','w') as f:
                    for ci, xc, yc, wn, hn in target_anns:
                        f.write(f'{ci} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}\n')
                kaggle_used += 1
                total += 1

        print(f"  使用: {kaggle_used} 张")
    else:
        print(f"  ⚠ 未找到: {KAGGLE_DIR}")

    # ═══════════════════════════════════════
    # 1.5 DLLG 数据集 (B站博主同款, 3类道路垃圾)
    # ═══════════════════════════════════════
    print("\n" + "="*60)
    print("1.5 DLLG 数据集 (博主同款: 塑料袋/瓶/罐)")
    print("="*60)

    # DLLG 3类: 0=塑料袋, 1=饮料瓶, 2=易拉罐 → 映射到12类
    DLLG_CLASS_MAP = {
        0: 'plastic',    # 塑料袋 → plastic
        1: 'plastic',    # 饮料瓶 → plastic
        2: 'metal',      # 易拉罐 → metal
    }

    dllg_used = 0
    if os.path.exists(DLLG_DIR):
        for split_name, target_split in [('train','train'), ('val','val')]:
            img_dir = f'{DLLG_DIR}/{split_name}/images'
            label_dir = f'{DLLG_DIR}/{split_name}/labels'
            # 兼容两种目录结构：train/images 和 images/train
            if not os.path.isdir(img_dir):
                alt_img = f'{DLLG_DIR}/images/{split_name}'
                alt_lbl = f'{DLLG_DIR}/labels/{split_name}'
                if os.path.isdir(alt_img) and os.path.isdir(alt_lbl):
                    img_dir = alt_img
                    label_dir = alt_lbl
            if not os.path.isdir(img_dir) or not os.path.isdir(label_dir):
                continue

            for lf in glob.glob(f'{label_dir}/*.txt'):
                base = os.path.basename(lf).replace('.txt','')
                img_paths = [f'{img_dir}/{base}.jpg', f'{img_dir}/{base}.png',
                             f'{img_dir}/{base}.jpeg', f'{img_dir}/{base}']
                img_path = next((p for p in img_paths if os.path.exists(p)), None)
                if not img_path: continue

                with open(lf) as f:
                    lines = f.read().strip().split('\n')
                if not lines or lines[0] == '': continue

                target_anns = []
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) != 5: continue
                    cls_id = int(parts[0])
                    if cls_id not in DLLG_CLASS_MAP: continue
                    target_cls = DLLG_CLASS_MAP[cls_id]
                    xc, yc, wn, hn = map(float, parts[1:])
                    target_anns.append((CID[target_cls], xc, yc, wn, hn))

                if not target_anns: continue

                fn = f'dllg_{dllg_used:05d}.jpg'
                shutil.copy2(img_path, f'{OUT_DIR}/{target_split}/images/{fn}')
                with open(f'{OUT_DIR}/{target_split}/labels/{fn.replace(".jpg",".txt")}','w') as f:
                    for ci, xc, yc, wn, hn in target_anns:
                        f.write(f'{ci} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}\n')
                dllg_used += 1
                total += 1

        print(f"  使用: {dllg_used} 张")
    else:
        print(f"  ⚠ 未找到: {DLLG_DIR}，克隆方法: git clone https://github.com/yujiongzhang/DLLG_datasets.git D:/DLLG_datasets")

    # ═══════════════════════════════════════
    # 2. 原始数据 (12类, 单目标, 紧致框)
    # ═══════════════════════════════════════
    print("\n" + "="*60)
    print("2. 原始12类数据")
    print("="*60)

    if not os.path.exists(RAW_ZIP):
        print(f"  ⚠ 未找到: {RAW_ZIP}")
    else:
        with zipfile.ZipFile(RAW_ZIP, 'r') as zf:
            zf.extractall(OUT_DIR + '/raw')
        RAW = f'{OUT_DIR}/raw/garbage_classification'

        objs = []
        orig_count = 0
        for cn in CLASSES:
            d = os.path.join(RAW, cn)
            if not os.path.isdir(d): continue
            imgs = [f for f in os.listdir(d) if f.lower().endswith(('.jpg','.jpeg','.png'))]
            random.shuffle(imgs)
            for i, fn in enumerate(imgs):
                img = cv2.imread(os.path.join(d, fn))
                if img is None: continue
                h,w = img.shape[:2]
                x1,y1,x2,y2 = find_bbox(img)
                obj = img[y1:y2,x1:x2]
                if obj.size>0 and obj.shape[0]>=10:
                    objs.append((CID[cn], obj))
                split = 'train' if i % 10 > 1 else 'val'
                of = f'orig_{CID[cn]}_{orig_count:05d}'
                cv2.imwrite(f'{OUT_DIR}/{split}/images/{of}.jpg', img)
                xc = ((x1+x2)/2)/w; yc = ((y1+y2)/2)/h
                bw = min((x2-x1)/w, 0.98); bh = min((y2-y1)/h, 0.98)
                with open(f'{OUT_DIR}/{split}/labels/{of}.txt','w') as f:
                    f.write(f'{CID[cn]} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n')
                orig_count += 1
                total += 1

        print(f"  原始图: {orig_count} 张")

        # ═══════════════════════════════════════
        # 3. 合成多目标（补充原始数据缺少的多目标场景）
        # ═══════════════════════════════════════
        print("\n" + "="*60)
        print("3. 合成多目标补充")
        print("="*60)
        BG_DIR = f'{OUT_DIR}/backgrounds'
        os.makedirs(BG_DIR, exist_ok=True)
        bgs = glob.glob(f'{BG_DIR}/*.jpg')
        if len(bgs) < 50:
            print("  下载背景图...")
            for i in range(200):
                try: urllib.request.urlretrieve(f'https://picsum.photos/640/480?random={i}', f'{BG_DIR}/bg_{i:03d}.jpg')
                except: pass
            bgs = glob.glob(f'{BG_DIR}/*.jpg')

        if len(objs) > 100 and len(bgs) > 10:
            for sp, n in [('train', 2000), ('val', 200)]:
                cnt = 0
                for i in range(n):
                    bg = cv2.imread(random.choice(bgs))
                    if bg is None: continue
                    bg = cv2.resize(bg, (640, 640))
                    sel = random.sample(objs, random.randint(2, min(4, len(objs))))
                    anns, placed = [], []
                    for ci, oi in sel:
                        s = random.uniform(0.2, 0.6)
                        nw = max(30, int(oi.shape[1]*s)); nh = max(30, int(oi.shape[0]*s))
                        oi = cv2.resize(oi,(nw,nh))
                        ok = False
                        for _ in range(30):
                            x=random.randint(5,640-nw-5); y=random.randint(5,640-nh-5)
                            if not any(x<px+pw and x+nw>px and y<py+ph and y+nh>py for (px,py,pw,ph) in placed): ok=True; break
                        if not ok: continue
                        bg[y:y+nh,x:x+nw]=oi; placed.append((x,y,nw,nh))
                        anns.append(f"{ci} {(x+nw/2)/640:.6f} {(y+nh/2)/640:.6f} {nw/640:.6f} {nh/640:.6f}")
                    if len(anns)>=2:
                        cv2.imwrite(f'{OUT_DIR}/{sp}/images/syn_{sp}_{i:04d}.jpg', bg)
                        with open(f'{OUT_DIR}/{sp}/labels/syn_{sp}_{i:04d}.txt','w') as f: f.write('\n'.join(anns))
                        cnt += 1
                print(f"  合成 {sp}: {cnt} 张")
                total += cnt

    # ═══════════════════════════════════════
    # 4. YAML
    # ═══════════════════════════════════════
    with open(f'{OUT_DIR}/dataset.yaml','w') as f:
        f.write(f'train: {OUT_DIR}/train/images\nval: {OUT_DIR}/val/images\nnc: 12\nnames:\n')
        for i,n in enumerate(CLASSES): f.write(f'  {i}: {n}\n')

    ti = len(glob.glob(f'{OUT_DIR}/train/images/*'))
    vi = len(glob.glob(f'{OUT_DIR}/val/images/*'))
    print(f"\n✅ 合并数据集: 训练 {ti} 张, 验证 {vi} 张, 总计约 {total} 张")

    # ═══════════════════════════════════════
    # 5. 训练 (3060 Ti)
    # ═══════════════════════════════════════
    print("\n" + "="*60)
    print("4. 训练 (3060 Ti)")
    print("="*60)
    from ultralytics import YOLO
    import torch
    print(f"CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available(): print(f"GPU: {torch.cuda.get_device_name(0)}")

    # 用上次训练的模型做起点（追加 DLLG 数据，只需微调）
    pretrained = os.path.expanduser('~/Desktop/best_merged.pt')
    if not os.path.exists(pretrained):
        pretrained = 'yolov8n.pt'  # 第一次运行则从头训练
    model = YOLO(pretrained)
    results = model.train(
        data=f'{OUT_DIR}/dataset.yaml',
        epochs=15, batch=64, imgsz=320,
        device=0, workers=0, name='garbage-merged',
        patience=5, lr0=0.002, seed=42, half=True,
        augment=False,
    )
    best = os.path.join(results.save_dir, 'weights', 'best.pt')
    dst = os.path.expanduser('~/Desktop/best_merged.pt')
    shutil.copy2(best, dst)
    print(f"\n训练完成! 模型: {dst}")
    print(f"拷到笔记本 models/best.pt 替换即可")

if __name__ == '__main__':
    main()
