<div align="center">

# ♻️ 智分宝 · 智能垃圾分类检测系统

**基于 YOLOv8 + PyQt5 的桌面级实时垃圾分类检测系统**

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-ee4c2c)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Nano-00ccff)](https://github.com/ultralytics/ultralytics)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Patience-creat/garbage-project?style=social)](https://github.com/Patience-creat/garbage-project)

**AI 视觉应用大赛参赛作品**

</div>

---

## 📋 目录

- [项目概述](#-项目概述)
- [功能特性](#-功能特性)
- [演示效果](#-演示效果)
- [技术架构](#-技术架构)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [模型训练](#-模型训练)
- [模型表现](#-模型表现)
- [项目结构](#-项目结构)
- [技术栈](#-技术栈)
- [比赛说明](#-比赛说明)
- [未来计划](#-未来计划)

---

## 🎯 项目概述

**智分宝**是一款基于 YOLOv8 轻量级目标检测模型的智能垃圾分类桌面应用，能实时识别 **12 类生活垃圾**并给出分类结果。支持 **CPU / GPU 自动切换** — 有 NVIDIA 显卡时自动启用 CUDA 加速，无 GPU 时静默回退 CPU。

**应用场景：**
- 🏠 家庭日常垃圾分类辅助
- 🏫 学校、社区环保教育展示
- 🎪 科技竞赛、课程设计演示
- 🔬 边缘计算设备部署验证

**核心指标：**

| 指标 | CPU | GPU (CUDA) |
|------|-----|-----------|
| 识别类别 | 12 类生活垃圾 | 12 类生活垃圾 |
| 模型大小 | ~6 MB（YOLOv8-Nano） | ~6 MB |
| 推理速度 | ~30 FPS | **~60+ FPS** |
| 检测精度 mAP@50 | **95.1%** | **95.1%** |
| 平均精度 Precision | **85.6%** | **85.6%** |
| 召回率 Recall | **94.6%** | **94.6%** |

---

## ✨ 功能特性

### 🎯 实时检测
- **摄像头实时检测** — 即开即用，实时标注垃圾类别与置信度
- **图片上传检测** — 支持 JPG / PNG / BMP 格式上传识别
- **实时 FPS 显示** — 性能一目了然

### ⚡ 智能设备适配
- **自动检测 GPU** — 优先使用 CUDA 加速，可用即享 2~3 倍性能提升
- **静默回退 CPU** — 无 GPU 环境自动降级，无需任何配置
- **纯 CPU 环境** — YOLOv8-Nano 轻量模型依然流畅运行 ~30 FPS

### 📊 智能统计
- **仪表盘概览** — 总检测数、类别覆盖、平均置信度、处理速度
- **实时识别列表** — 每次检测的详细结果卡片
- **检测统计摘要** — 单次检测的目标数、类别数、平均置信度

### 📁 记录管理
- **检测记录持久化** — 自动保存历史记录，重启不丢失
- **CSV 导出** — 一键导出检测数据用于分析
- **截图保存** — 保存带标注的检测画面

### 🎨 现代界面
- **深色科技风 UI** — 护眼暗色主题，渐变色彩
- **无边框窗口** — 圆角 + 阴影，类 macOS 设计
- **键盘快捷键** — 专业级操作效率
  - `Ctrl+O` 上传图片
  - `Ctrl+C` 开启摄像头
  - `F5` 开始/停止检测
  - `Ctrl+S` 保存结果
  - `Ctrl+Q` 退出
- **置信度滑块** — 可调节检测灵敏度
- **状态指示灯** — 实时显示系统运行状态

---

## 🖥️ 演示效果

> 📸 *应用启动后预览：*

| 仪表盘 | 实时检测 | 检测记录 |
|--------|---------|---------|
| 总检测数 / 类别覆盖 / 平均置信度 / 处理速度一览 | 摄像头/图片实时识别，结果卡片即时展示 | 历史记录自动保存，支持导出 CSV |

> **提示：** 实际运行截图请放入 `docs/screenshots/` 目录，并在下方取消注释。

<!--
![主界面](docs/screenshots/main_window.png)
![检测演示](docs/screenshots/detection_demo.png)
![仪表盘](docs/screenshots/dashboard.png)
-->

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────┐
│              用户界面层 (PyQt5)               │
│  ┌─────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ 仪表盘   │ │ 检测页面  │ │ 检测记录      │ │
│  └─────────┘ └──────────┘ └──────────────┘ │
├─────────────────────────────────────────────┤
│              业务逻辑层                      │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ 模型管理  │ │ 推理引擎  │ │ 记录管理器   │ │
│  └──────────┘ └──────────┘ └─────────────┘ │
├─────────────────────────────────────────────┤
│              推理引擎层                      │
│  ┌──────────────────────────────────────┐   │
│  │  DetectionWorker (QThread 多线程)    │   │
│  │  ┌──────────┐  ┌──────────────────┐ │   │
│  │  │ OpenCV   │  │ YOLOv8 (PyTorch) │ │   │
│  │  │ 摄像头/   │  │ 推理 + 后处理     │ │   │
│  │  │ 图片解码  │  │                  │ │   │
│  │  └──────────┘  └──────────────────┘ │   │
│  └──────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│              设备适配层                      │
│      auto_device(): CUDA → MPS → CPU        │
│      运行时自动检测，无需手动配置              │
└─────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求

- **操作系统**: Windows 10 / 11（推荐），Linux / macOS 亦可
- **Python**: 3.10 ~ 3.13
- **硬件**:
  - CPU 即可运行（推荐 4 核以上，~30 FPS）
  - NVIDIA GPU（支持 CUDA）推理速度 ~60+ FPS（自动启用）

### 1️⃣ 克隆项目

```bash
git clone https://github.com/Patience-creat/garbage-project.git
cd garbage-project
```

### 2️⃣ 获取模型权重

模型文件 `models/best.pt`（~6 MB）是运行检测的必需文件。有两种方式获取：

**方式 A：从 GitHub Releases 下载（推荐）**

```bash
python download_model.py
```

**方式 B：使用仓库中已跟踪的模型（如果已存在）**

模型文件直接放在了 `models/best.pt`，克隆后无需额外下载。

> 💡 程序启动时会依次查找：`models/best.pt` → `runs/detect/train-3/weights/best.pt`，也可用 `--model` 参数指定自定义路径。

### 3️⃣ 安装依赖

**使用 conda（推荐）**

```bash
# 创建专用环境
conda create -n garbage python=3.10
conda activate garbage

# CPU 版本（通用，兼容所有电脑）
pip install -r requirements.txt

# 如需 CUDA 加速（NVIDIA GPU），可替换为 GPU 版 PyTorch：
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# pip install -r requirements.txt
```

**使用 pip（直接安装）**

```bash
pip install -r requirements.txt
```

> 系统会在启动时自动检测是否有可用 GPU，无需任何配置修改。

### 4️⃣ 运行程序

```bash
# 基础启动
python main.py

# 指定摄像头（如果你的摄像头不是默认的 0）
python main.py --camera 1

# 指定置信度阈值
python main.py --conf 0.25

# 指定模型路径
python main.py --model models/best.pt

# 开启调试日志
python main.py --debug
```

---

## 📖 使用指南

### 摄像头检测

1. 点击左侧导航栏 **「智能检测」**
2. 点击 **「📷 开启摄像头」** 按钮
3. 系统自动检测并实时标注垃圾类别
4. 按 **F5** 停止 / 重新开始

### 图片检测

1. 在检测页面点击 **「🖼️ 上传图片」**
2. 选择本地图片文件
3. 系统自动识别并显示结果

### 调整检测灵敏度

- 拖动工具栏的 **置信度阈值滑块**（默认 0.30）
- 调高减少误检，调低增加召回率

### 查看统计

- 导航至 **「仪表盘」** 查看累计检测统计
- 导航至 **「检测记录」** 查看详细历史记录
- 点击 **「📤 导出」** 将记录导出为 CSV

---

## 🤖 模型训练

### 数据集

本项目使用公开垃圾分类数据集，包含 **12 类**生活垃圾：
电池、厨余垃圾、棕色玻璃、纸板、衣物、绿色玻璃、金属、纸张、塑料、鞋子、其他垃圾、白色玻璃。

### 训练命令

```bash
yolo task=detect mode=train model=yolov8n.pt data=garbage.yaml epochs=30 imgsz=640
```

### 训练参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 基础模型 | YOLOv8-Nano | 轻量化，CPU 可运行 |
| 训练轮次 | 30 Epoch | 已收敛充分 |
| 批大小 | 16 | 可根据显存/内存调整 |
| 图片尺寸 | 640×640 | 标准输入 |
| 数据划分 | 8:2 (训练:验证) | |

### 数据预处理

```bash
python prepare_data.py
```

脚本会自动将原始图片按 8:2 划分训练/验证集，并生成 YOLO 格式标注。

---

## 📊 模型表现

### 训练曲线

训练过程记录在 `runs/detect/train-3/results.csv`，关键指标如下：

| 指标 | 最终值 |
|------|-------|
| mAP@0.5 | **95.1%** |
| mAP@0.5:0.95 | **98.3%** |
| Precision (精确率) | **85.6%** |
| Recall (召回率) | **94.6%** |
| 模型大小 | **~6 MB** |

### 类别识别效果

| 类别 | 中文名 | 预期精度 |
|------|--------|---------|
| battery | 电池 | ⭐⭐⭐ |
| biological | 厨余垃圾 | ⭐⭐⭐ |
| brown-glass | 棕色玻璃 | ⭐⭐⭐ |
| cardboard | 纸板 | ⭐⭐⭐⭐ |
| clothes | 衣物 | ⭐⭐⭐ |
| green-glass | 绿色玻璃 | ⭐⭐⭐ |
| metal | 金属 | ⭐⭐⭐⭐ |
| paper | 纸张 | ⭐⭐⭐⭐ |
| plastic | 塑料 | ⭐⭐⭐ |
| shoes | 鞋子 | ⭐⭐⭐ |
| trash | 其他垃圾 | ⭐⭐⭐ |
| white-glass | 白色玻璃 | ⭐⭐⭐ |

---

## 📁 项目结构

```
garbage-project/
├── main.py                    # 应用入口（含 CLI 参数解析）
├── detect.py                  # 独立检测脚本（快速测试用）
├── prepare_data.py            # 数据集预处理 + 标注生成
├── download_model.py          # 模型权重下载脚本
├── garbage.yaml               # YOLO 数据集配置
├── requirements.txt           # 依赖清单
├── README.md                  # 项目文档（就是本文件）
├── .gitignore                 # Git 忽略规则
│
├── models/                    # 可分发模型权重
│   └── best.pt                # 最优模型权重（~6MB，Git 直接跟踪）
│
├── garbage_gui/               # GUI 应用包
│   ├── __init__.py            # 包初始化（版本号）
│   ├── app_window.py          # 主窗口（快捷键、状态栏、导航）
│   ├── pages.py               # 页面（仪表盘、检测、记录）
│   ├── widgets.py             # 自定义控件（标题栏、侧边栏、卡片）
│   ├── worker.py              # 多线程推理引擎
│   ├── theme.py               # 主题系统（颜色、字体、样式）
│   ├── config.py              # 配置中心（含 auto_device 设备检测）
│   └── logger.py              # 日志系统
│
├── runs/detect/train-3/       # 训练输出（不推送 GitHub）
│   └── weights/
│       ├── best.pt            # 同上，训练本地副本
│       └── last.pt            # 最后 epoch 权重
│
├── records/                   # 检测记录（JSON 自动保存）
├── logs/                      # 运行日志
└── output/                    # 导出文件目录
```

---

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| **YOLOv8-Nano** | 目标检测模型（Ultralytics） |
| **PyTorch** | 深度学习框架（自动选择 CPU / CUDA / MPS） |
| **OpenCV** | 图像处理、摄像头读取 |
| **PyQt5** | 桌面 GUI 框架 |
| **NumPy** | 数值计算 |
| **Matplotlib** | 训练曲线可视化 |

---

## 🏆 比赛说明

### 技术特色

1. **轻量化部署** — YOLOv8-Nano 模型仅 ~6MB，CPU 即可流畅运行
2. **GPU 智能适配** — 运行时自动检测最佳设备（CUDA → MPS → CPU），无需手动配置
3. **完整工程化** — 日志系统、配置中心、异常处理、CLI 参数
4. **多线程架构** — 推理与 UI 分离，不阻塞界面操作
5. **数据持久化** — 检测记录自动保存，重启可追溯
6. **人性化交互** — 快捷键、状态指示、实时反馈

### 创新点

- 🔄 **全链路闭环**：从数据预处理 → 模型训练 → 桌面部署的完整 AI 应用流水线
- 🎨 **专业化 UI**：深色科技风 + 圆角无边框窗口设计，符合现代桌面应用审美
- 📊 **可视化分析**：实时仪表盘展示检测统计，一目了然
- 🧩 **可扩展架构**：模块化设计，便于增加新的检测类别或功能

---

## 🔮 未来计划

- [x] GPU / CPU 自动适配，无需手动配置
- [ ] 模型 ONNX 导出，部署至树莓派/边缘设备
- [ ] 增加视频文件检测模式
- [ ] 垃圾分类知识库弹窗
- [ ] 多语言界面支持
- [ ] 自定义训练数据扩展
- [ ] 模型热更新（不重启应用切换模型）

---

## 📄 许可证

本项目基于 **MIT License** 开源。欢迎大家 Fork 和 Star ⭐

---

<div align="center">

**Made with ♻️ by Patience-creat**

*AI 视觉应用大赛参赛作品*

[![GitHub](https://img.shields.io/badge/GitHub-Patience--creat-181717?logo=github)](https://github.com/Patience-creat/garbage-project)

</div>
