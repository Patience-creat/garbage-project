"""
日志系统 — 替换所有 print()，输出到控制台 + 文件
"""
import os
import logging
from datetime import datetime

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def setup_logger(name: str = "garbage") -> logging.Logger:
    """初始化并返回命名日志器

    输出目标：
      1. 控制台（INFO 级别，彩色-绿色提示）
      2. 文件 logs/app.log（DEBUG 级别，滚动追加）
    """
    logger = logging.getLogger(name)
    if logger.handlers:  # 避免重复初始化
        return logger

    logger.setLevel(logging.DEBUG)

    # ── 格式 ──
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(
        "%(levelname)s | %(message)s"
    )

    # ── 文件处理器 ──
    os.makedirs(_LOG_DIR, exist_ok=True)
    log_path = os.path.join(_LOG_DIR, "app.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8", mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    # ── 控制台处理器 ──
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    logger.info(f"📝 日志系统初始化完成 → {log_path}")
    return logger


# 全局默认日志器
logger = setup_logger()
