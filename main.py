"""
智分宝 · 智能垃圾分类检测系统
基于 YOLOv8 + PyQt5 的专业桌面级GUI
"""
import sys
import traceback
import ctypes

# ── Windows 高 DPI 支持 ──
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def main():
    """应用入口 — 带详细错误捕获"""
    # ── 导入阶段（在此处捕获导入错误） ──
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        from garbage_gui.theme import setup_fonts
        from garbage_gui.app_window import AppWindow
        print("✅ 所有模块导入成功")
    except ImportError as e:
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
        print("=" * 60)
        print(f"❌ 初始化失败: {e}")
        traceback.print_exc()
        print("=" * 60)
        input("按回车键退出...")
        return

    # ── 应用初始化 ──
    try:
        # 启用 High-DPI 支持
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

        app = QApplication(sys.argv)
        app.setFont(setup_fonts())
        app.setApplicationName("智分宝 · 垃圾分类检测系统")
        app.setApplicationVersion("2.0.0")
        app.setStyle("Fusion")
        print("✅ QApp 创建完成")

        # 单独捕获窗口实例化异常【关键改动】
        print("🔍 正在创建主窗口...")
        try:
            window = AppWindow()
            print("✅ 窗口创建成功")
            window.show()
        except Exception as win_err:
            print("="*50)
            print("❌ AppWindow 构造函数报错：")
            traceback.print_exc()
            print("="*50)
            input("回车退出")
            return

        sys.exit(app.exec_())
    except Exception as e:
        print("=" * 60)
        print(f"❌ 运行时错误: {e}")
        traceback.print_exc()
        print("=" * 60)
        input("按回车键退出...")
        return


if __name__ == "__main__":
    main()