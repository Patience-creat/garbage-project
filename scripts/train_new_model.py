"""
训练脚本 — 用紧致边界框 + 多目标合成数据训练 YOLOv8

用法：
  python train_new_model.py              # 正常训练
  python train_new_model.py --device 0    # 用 GPU (CUDA)
  python train_new_model.py --epochs 100  # 更多轮次
"""
import argparse
import sys
from ultralytics import YOLO

# ─── 参数 ───
parser = argparse.ArgumentParser(description="训练多目标垃圾分类模型")
parser.add_argument("--data", default=r"D:/archive/garbage_classification/yolo_dataset_v2/dataset.yaml",
                    help="数据集 YAML 路径")
parser.add_argument("--model", default="yolov8n.pt",
                    help="预训练权重 (yolov8n.pt / yolov8s.pt)")
parser.add_argument("--epochs", type=int, default=50,
                    help="训练轮数")
parser.add_argument("--batch", type=int, default=16,
                    help="批大小")
parser.add_argument("--imgsz", type=int, default=640,
                    help="输入图片尺寸")
parser.add_argument("--device", default="cpu",
                    help="训练设备 (cpu / 0 / 0,1)")
parser.add_argument("--name", default="train-multi",
                    help="实验名称")
args = parser.parse_args()

print("=" * 60)
print("YOLOv8 多目标垃圾检测训练")
print("=" * 60)
print(f"  数据: {args.data}")
print(f"  基础模型: {args.model}")
print(f"  轮数: {args.epochs}")
print(f"  批大小: {args.batch}")
print(f"  图片尺寸: {args.imgsz}")
print(f"  设备: {args.device}")
print(f"  实验名: {args.name}")
print()

# ─── 加载模型 ───
model = YOLO(args.model)
print(f"模型加载完成: {type(model.model).__name__}")

# ─── 训练 ───
results = model.train(
    data=args.data,
    epochs=args.epochs,
    batch=args.batch,
    imgsz=args.imgsz,
    device=args.device,
    name=args.name,
    patience=15,           # 15 轮不提升就早停
    lr0=0.005,             # 初始学习率
    augment=True,
    fraction=1.0,          # 使用全部数据
    verbose=True,
    seed=42,
)

print("\n" + "=" * 60)
print("训练完成!")
print("=" * 60)
print(f"  最佳权重: {results.save_dir}/weights/best.pt")
print(f"  结果目录: {results.save_dir}")
