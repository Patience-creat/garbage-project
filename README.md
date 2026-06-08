# garbage-project
YOLOv8 垃圾分类检测
# 基于YOLOv8的智能垃圾分类检测系统
## 项目介绍
本项目依托YOLOv8-n轻量级目标检测模型，使用公开垃圾分类数据集完成30轮全量训练，实现**12类生活垃圾实时目标检测**，搭配PyQt5可视化UI界面，支持本地摄像头在线识别，可用于科创比赛演示、课程设计、嵌入式部署拓展。

## 可识别垃圾类别
1. battery（废旧电池，有害垃圾）
2. biological（厨余果蔬，厨余垃圾）
3. brown-glass（棕色玻璃瓶，可回收物）
4. cardboard（硬纸板纸箱，可回收物）
5. clothes（废旧衣物，可回收物）
6. green-glass（绿色玻璃瓶，可回收物）
7. metal（金属易拉罐/铁器，可回收物）
8. paper（废纸书本，可回收物）
9. plastic（塑料瓶/塑料盒，可回收物）
10. shoes（旧鞋，可回收物）
11. trash（其他废弃物，干垃圾）
12. white-glass（透明白玻璃，可回收物）

## 环境部署
### 1. 安装依赖
```bash
pip install -r requirements.txt
2. 项目运行
UI 可视化界面运行（比赛演示首选）
bash
运行
python main.py
数据集预处理（初次复现训练）
bash
运行
python prepare_data.py
重新训练模型
bash
运行
yolo task=detect mode=train model=yolov8n.pt data=garbage.yaml epochs=30 imgsz=640
训练参数说明
基础模型：YOLOv8-Nano（轻量化，CPU 可运行）
训练轮次：30 Epoch
硬件环境：Intel i5-13420H CPU
模型精度：验证集 mAP@0.5≈86%
最优权重路径：runs/detect/train-2/weights/best.pt
项目目录结构
plaintext
garbage-project/
├── main.py              # PyQt5可视化UI主程序
├── train.py             # 模型训练启动脚本
├── prepare_data.py      # 数据集自动划分+标注生成
├── garbage.yaml         # YOLO数据集配置文件
├── requirements.txt     # 项目依赖清单
├── README.md            # 项目说明文档
└── runs/                # 训练权重、日志、效果图
拓展优化方向
扩充私人标注数据集，提升复杂场景识别精度
模型轻量化导出 ONNX，部署至树莓派 / 安卓设备
完善 UI：新增垃圾分类知识库弹窗、识别计数统计功能
