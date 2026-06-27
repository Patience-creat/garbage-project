"""
台式机（3060Ti）训练多目标垃圾检测模型
用法: python desktop_train.py
训练完后把 best_multi.pt 拷回笔记本即可
"""
import os, sys, zipfile, glob, shutil, random, cv2, numpy as np, urllib.request
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from ultralytics import YOLO
import torch

CLASSES = ['battery','biological','brown-glass','cardboard','clothes',
           'green-glass','metal','paper','plastic','shoes','trash','white-glass']
CID = {n:i for i,n in enumerate(CLASSES)}

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
    mx,my = int(w*0.1),int(h*0.1)
    return mx,my,w-mx,h-my

def main():
    DATA_ZIP = r"D:/garbage_dataset.zip"
    if not os.path.exists(DATA_ZIP):
        print(f"找不到: {DATA_ZIP}"); return

    EXTRACT = r"D:/garbage_training"
    OUT = os.path.join(EXTRACT, "yolo_v3")

    # 解压
    print("解压数据...")
    with zipfile.ZipFile(DATA_ZIP, 'r') as zf: zf.extractall(EXTRACT)
    RAW = os.path.join(EXTRACT, "garbage_classification")

    # CUDA
    print(f"CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # 背景图
    BG = os.path.join(EXTRACT, "backgrounds")
    os.makedirs(BG, exist_ok=True)
    bgs = glob.glob(f"{BG}/*.jpg")
    if len(bgs) < 50:
        print("下载背景图(300张)...")
        for i in range(300):
            try: urllib.request.urlretrieve(f"https://picsum.photos/640/480?random={i}", f"{BG}/bg_{i:03d}.jpg")
            except: pass
        bgs = glob.glob(f"{BG}/*.jpg")
    print(f"背景图: {len(bgs)} 张")

    # 建立输出目录
    for d in ['train/images','train/labels','val/images','val/labels']:
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    # 提取物体
    print("提取物体...")
    objs = []
    for cn in CLASSES:
        d = os.path.join(RAW, cn)
        if not os.path.isdir(d): continue
        for fn in os.listdir(d)[:300]:
            img = cv2.imread(os.path.join(d,fn))
            if img is None: continue
            x1,y1,x2,y2 = find_bbox(img)
            obj = img[y1:y2,x1:x2]
            if obj.size>0 and obj.shape[0]>=10: objs.append((CID[cn],obj))
    print(f"物体: {len(objs)} 个")

    # 合成多目标图
    print("生成合成多目标图...")
    for sp, n in [('train',5000), ('val',500)]:
        cnt = 0
        for i in range(n):
            bg = cv2.imread(random.choice(bgs)) if bgs else None
            if bg is None: continue
            bg = cv2.resize(bg, (640,640))
            sel = random.sample(objs, random.randint(2,5))
            anns, placed = [], []
            for ci,oi in sel:
                s = random.uniform(0.2,0.6)
                nw,nh = max(30,int(oi.shape[1]*s)),max(30,int(oi.shape[0]*s))
                oi = cv2.resize(oi,(nw,nh))
                ok = False
                for _ in range(30):
                    x=random.randint(5,640-nw-5); y=random.randint(5,640-nh-5)
                    if not any(x<px+pw and x+nw>px and y<py+ph and y+nh>py for (px,py,pw,ph) in placed):
                        ok=True; break
                if not ok: continue
                bg[y:y+nh,x:x+nw]=oi; placed.append((x,y,nw,nh))
                anns.append(f"{ci} {(x+nw/2)/640:.6f} {(y+nh/2)/640:.6f} {nw/640:.6f} {nh/640:.6f}")
            if len(anns)>=2:
                cv2.imwrite(f"{OUT}/{sp}/images/comp_{sp}_{i:04d}.jpg", bg)
                with open(f"{OUT}/{sp}/labels/comp_{sp}_{i:04d}.txt",'w') as f: f.write("\n".join(anns))
                cnt += 1
        print(f"  {sp}: {cnt} 张")

    # 复制原图
    print("复制原图...")
    for sp, ratio in [('train',0.85), ('val',0.15)]:
        for cn in CLASSES:
            d = os.path.join(RAW, cn)
            if not os.path.isdir(d): continue
            imgs = [f for f in os.listdir(d) if f.lower().endswith(('.jpg','.jpeg','.png'))]
            random.shuffle(imgs)
            n = int(len(imgs)*ratio) if sp=='train' else min(int(len(imgs)*0.15),80)
            for i,fn in enumerate(imgs[:n]):
                img = cv2.imread(os.path.join(d,fn))
                if img is None: continue
                h,w = img.shape[:2]; x1,y1,x2,y2 = find_bbox(img)
                of = f"orig_{sp}_{CID[cn]}_{i:04d}"
                cv2.imwrite(f"{OUT}/{sp}/images/{of}.jpg", img)
                with open(f"{OUT}/{sp}/labels/{of}.txt",'w') as f:
                    f.write(f"{CID[cn]} {((x1+x2)/2)/w:.6f} {((y1+y2)/2)/h:.6f} {min((x2-x1)/w,0.98):.6f} {min((y2-y1)/h,0.98):.6f}\n")

    train_imgs = len(glob.glob(f"{OUT}/train/images/*"))
    val_imgs = len(glob.glob(f"{OUT}/val/images/*"))
    print(f"\n数据集: 训练 {train_imgs} 验证 {val_imgs}")

    # YAML
    with open(f"{OUT}/dataset.yaml",'w') as f:
        f.write(f"train: {OUT}/train/images\nval: {OUT}/val/images\nnc: 12\nnames:\n")
        for i,n in enumerate(CLASSES): f.write(f"  {i}: {n}\n")

    # 训练
    print("\n开始训练 (3060Ti)...")
    model = YOLO('yolov8n.pt')
    results = model.train(
        data=f"{OUT}/dataset.yaml",
        epochs=50, batch=32, imgsz=640,
        device=0, workers=0, name='garbage-multi',
        patience=10, lr0=0.005, seed=42,
    )

    best = os.path.join(results.save_dir, "weights", "best.pt")
    dst = os.path.expanduser("~/Desktop/best_multi.pt")
    shutil.copy2(best, dst)
    print(f"\n训练完成! 模型已复制到桌面: {dst}")
    print(f"把它拷到笔记本的 models/best.pt 替换即可")

if __name__ == '__main__':
    main()
