import os
import shutil
import random

# 数据集根目录（改成你的路径）
root_dir = r"D:\archive\garbage_classification"
output_dir = os.path.join(root_dir, "yolo_dataset")
os.makedirs(output_dir, exist_ok=True)

# 类别列表
classes = ['battery', 'biological', 'brown-glass', 'cardboard', 'clothes',
           'green-glass', 'metal', 'paper', 'plastic', 'shoes', 'trash', 'white-glass']

# 创建训练/验证文件夹
for split in ['train', 'val']:
    os.makedirs(os.path.join(output_dir, split, 'images'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, split, 'labels'), exist_ok=True)

# 按8:2划分训练集和验证集
train_ratio = 0.8

for class_id, class_name in enumerate(classes):
    class_dir = os.path.join(root_dir, class_name)
    if not os.path.isdir(class_dir):
        continue
    
    # 获取该类别的所有图片
    images = [f for f in os.listdir(class_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
    random.shuffle(images)
    split_idx = int(len(images) * train_ratio)
    train_images = images[:split_idx]
    val_images = images[split_idx:]
    
    # 复制图片并生成标注（这里是分类转检测的简化标注，框住整个图片）
    for split, img_list in [('train', train_images), ('val', val_images)]:
        for img_name in img_list:
            # 复制图片
            src_img = os.path.join(class_dir, img_name)
            dst_img = os.path.join(output_dir, split, 'images', img_name)
            shutil.copy(src_img, dst_img)
            
            # 生成标注文件（全图检测框）
            label_name = os.path.splitext(img_name)[0] + '.txt'
            label_path = os.path.join(output_dir, split, 'labels', label_name)
            with open(label_path, 'w') as f:
                # YOLO格式：class_id x_center y_center width height
                f.write(f"{class_id} 0.5 0.5 1.0 1.0\n")

print("数据集准备完成！")