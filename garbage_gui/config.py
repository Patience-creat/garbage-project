"""
配置中心 — 集中管理所有可调参数
"""
import os
from dataclasses import dataclass, field
from typing import List


def auto_device() -> str:
    """自动选择最佳可用推理设备：CUDA > MPS > CPU"""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def resolve_model_path() -> str:
    """自动查找可用的模型权重文件

    搜索顺序：
    1. 环境变量 MODEL_PATH 指定的路径
    2. models/best.pt（标准化分发路径）
    3. runs/detect/train-3/weights/best.pt（训练输出路径）
    """
    # 环境变量优先
    env_path = os.getenv("MODEL_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 候选路径
    candidates = [
        "models/best.pt",
        "runs/detect/train-3/weights/best.pt",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    # 兜底返回默认路径（让下游报清晰的错误）
    return "models/best.pt"


def device_display_name(device: str) -> str:
    """返回设备的人类可读名称"""
    mapping = {
        "cpu": "CPU",
        "cuda": "CUDA (GPU)",
        "cuda:0": "CUDA (GPU)",
        "mps": "MPS (Apple Silicon)",
    }
    return mapping.get(device, device.upper())


@dataclass
class AppConfig:
    """应用全局配置

    优先级：硬编码默认值 ← 环境变量覆盖
    """
    # ── 模型 ──
    MODEL_PATH: str = resolve_model_path()
    BASE_MODEL_PATH: str = "yolov8n.pt"

    # ── 检测 ──
    CONF_THRESHOLD: float = float(os.getenv("CONF_THRESHOLD", "0.30"))
    IO_U_THRESHOLD: float = 0.7
    MAX_DETECTIONS: int = 300
    CAMERA_ID: int = int(os.getenv("CAMERA_ID", "0"))
    TARGET_FPS: int = 30
    FRAME_WIDTH: int = 1280
    FRAME_HEIGHT: int = 720

    # ── 窗口 ──
    WINDOW_WIDTH: int = 1280
    WINDOW_HEIGHT: int = 800
    WINDOW_TITLE: str = "智分宝 · 智能垃圾分类检测系统"
    APP_VERSION: str = "2.1.0"

    # ── 路径 ──
    RECORDS_DIR: str = os.getenv("RECORDS_DIR", "records")
    LOG_DIR: str = "logs"
    OUTPUT_DIR: str = "output"

    # ── 垃圾类别（与训练一致） ──
    CLASS_NAMES: List[str] = field(default_factory=lambda: [
        "battery", "biological", "brown-glass", "cardboard", "clothes",
        "green-glass", "metal", "paper", "plastic", "shoes", "trash", "white-glass",
    ])

    # ── 比赛信息 ──
    COMPETITION_NAME: str = "AI 视觉应用大赛"
    AUTHOR: str = "Patience-creat"
    GITHUB_URL: str = "https://github.com/Patience-creat/garbage-project"


# 全局单例
CONFIG = AppConfig()
