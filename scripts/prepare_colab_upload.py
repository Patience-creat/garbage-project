"""
打包原始数据 → 上传到 Google Colab 训练用

用法：
  python prepare_colab_upload.py

会生成 garbage_dataset.zip（约 1~2GB），你需要：
  1. 把 zip 上传到 Google 云盘
  2. 打开 train_colab.ipynb 按说明运行
"""
import os, zipfile, shutil

RAW_ROOT = r"D:/archive/garbage_classification"
OUTPUT_ZIP = r"D:/garbage_dataset.zip"

print("正在打包数据集...")
print(f"来源: {RAW_ROOT}")
print(f"输出: {OUTPUT_ZIP}")

with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
    for cls_name in sorted(os.listdir(RAW_ROOT)):
        cls_dir = os.path.join(RAW_ROOT, cls_name)
        if not os.path.isdir(cls_dir):
            continue
        count = 0
        for img_name in os.listdir(cls_dir):
            if img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(cls_dir, img_name)
                arc_path = f"garbage_classification/{cls_name}/{img_name}"
                zf.write(img_path, arc_path)
                count += 1
        print(f"  {cls_name}: {count} 张")

size_mb = os.path.getsize(OUTPUT_ZIP) / 1024 / 1024
print(f"\n打包完成！大小: {size_mb:.0f} MB")
print()
print("下一步:")
print("  1. 把 D:\\garbage_dataset.zip 上传到 Google 云盘")
print(f"  2. 打开 https://colab.research.google.com/")
print("  3. 文件 → 上传笔记本 → 选择 train_colab.ipynb")
print("  4. 运行时 → 更改运行时类型 → T4 GPU")
print("  5. 依次运行所有单元格")
print("  6. 训练完成后从云盘下载 best_multi.pt → models/best.pt")
