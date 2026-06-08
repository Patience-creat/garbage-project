"""
智分宝 · 智能垃圾分类检测系统
基于 YOLOv8 + PyQt5 的专业桌面级 GUI
适用于 AI 视觉应用大赛等场景

Usage:
    python main.py                  # 正常启动
    python main.py --camera 1       # 指定摄像头 ID
    python main.py --conf 0.25      # 指定置信度阈值
"""
import sys
import os
import traceback
import ctypes
import argparse

# ── Windows 高 DPI 支持 ──
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def _setup_exception_hook():
    """设置全局异常钩子，未捕获异常弹窗提示而非静默崩溃"""
    import logging

    def excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.critical(
            "未捕获的异常: %s\n%s",
            exc_value,
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        # PyQt 异常钩子
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            QMessageBox.critical(
                None, "程序异常",
                f"发生未预期的错误，程序将退出：\n\n{exc_value}\n\n"
                f"详情请查看 logs/app.log"
            )
        except Exception:
            pass

    sys.excepthook = excepthook


def _parse_args():
    """命令行参数解析"""
    parser = argparse.ArgumentParser(
        description="智分宝 · 智能垃圾分类检测系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--camera", type=int, default=None,
        help="摄像头 ID（默认 0）",
    )
    parser.add_argument(
        "--conf", type=float, default=None,
        help="检测置信度阈值（默认 0.30）",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="模型权重路径（覆盖默认）",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="开启 DEBUG 级别日志",
    )
    return parser.parse_args()


def main():
    """应用入口 — 带详细错误捕获"""
    args = _parse_args()

    # ── 日志系统（必须在其他导入之前） ──
    from garbage_gui.logger import setup_logger
    logger = setup_logger()
    if args.debug:
        for h in logger.handlers:
            h.setLevel(logging.DEBUG)
        logger.debug("🐛 DEBUG 模式已开启")

    # 设置全局异常钩子
    _setup_exception_hook()

    # ── 配置覆盖（命令行参数优先） ──
    from garbage_gui.config import CONFIG
    if args.camera is not None:
        CONFIG.CAMERA_ID = args.camera
        logger.info(f"摄像头 ID 覆盖为 {args.camera}")
    if args.conf is not None:
        CONFIG.CONF_THRESHOLD = args.conf
        logger.info(f"置信度阈值覆盖为 {args.conf}")
    if args.model is not None:
        CONFIG.MODEL_PATH = args.model
        logger.info(f"模型路径覆盖为 {args.model}")

    # ── 导入阶段 ──
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        from garbage_gui.theme import setup_fonts
        from garbage_gui.app_window import AppWindow
        logger.info("✅ 所有模块导入成功")
    except ImportError as e:
        logger.critical(f"导入失败: {e}")
        print("=" * 60)
        print("❌ 导入失败！请检查依赖是否安装完整。")
        print(f"错误: {e}")
        print()
        print("请运行以下命令安装依赖：")
        print("  pip install -r requirements.txt")
        print("=" * 60)
        input("按回车键退出...")
        return
    except Exception as e:
        logger.critical(f"初始化异常: {e}", exc_info=True)
        traceback.print_exc()
        input("按回车键退出...")
        return

    # ── 应用初始化 ──
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

        app = QApplication(sys.argv)
        app.setFont(setup_fonts())
        app.setApplicationName(CONFIG.WINDOW_TITLE)
        app.setApplicationVersion(CONFIG.APP_VERSION)
        app.setStyle("Fusion")
        logger.info("✅ QApp 创建完成")

        logger.info("🔍 正在创建主窗口...")
        try:
            window = AppWindow()
            logger.info("✅ 窗口创建成功")
            window.show()
        except Exception as win_err:
            logger.critical("AppWindow 构造函数报错", exc_info=True)
            print("=" * 50)
            traceback.print_exc()
            print("=" * 50)
            input("回车退出")
            return

        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"运行时错误: {e}", exc_info=True)
        traceback.print_exc()
        input("按回车键退出...")
        return


if __name__ == "__main__":
    main()
