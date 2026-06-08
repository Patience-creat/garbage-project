"""
主窗口 — 无边框现代窗口，整合侧边栏、页面、标题栏
"""
import cv2
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QFrame, QGraphicsDropShadowEffect, QLabel, QDesktopWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from .theme import Color, Radius, GLOBAL_STYLESHEET, setup_fonts
from .widgets import TitleBar, Sidebar
from .pages import DashboardPage, DetectionPage, HistoryPage

# 模型加载
from ultralytics import YOLO

MODEL_PATH = "runs/detect/train-3/weights/best.pt"

# ─── 用于平滑启动的闪屏 ────────────────────────────────
SPLASH_MESSAGE = """<div style='text-align:center;'>
    <div style='font-size:48px; margin-bottom:16px;'>♻️</div>
    <div style='font-size:22px; font-weight:bold; color:#f1f5f9;'>智分宝</div>
    <div style='font-size:13px; color:#94a3b8; margin-top:4px;'>智能垃圾分类检测系统</div>
    <div style='font-size:11px; color:#475569; margin-top:20px;'>正在加载模型，请稍候...</div>
</div>"""


class AppWindow(QMainWindow):
    """主应用窗口 — 无边框 + 圆角 + 阴影"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("智分宝 · 垃圾分类检测系统")
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 不启用 WA_TranslucentBackground，避免 Windows 上 UpdateLayeredWindowIndirect 报错
        # 窗口为深色实心背景，圆角通过容器样式表实现
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        # 窗口状态
        self._model = None
        self._page_loaded = False
        self._normal_rect = None

        # 累计检测数（仪表盘使用）
        self._cum_total = 0

        # 设置窗口大小
        self.resize(1280, 800)
        self._center_on_screen()

        # 显示闪屏（先显示加载界面再初始化）
        self._show_splash()

        # 延迟初始化（让闪屏先显示）
        QTimer.singleShot(50, self._init_app)

    def _center_on_screen(self):
        """居中显示"""
        screen = QDesktopWidget().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def _show_splash(self):
        """显示加载中的闪屏"""
        self._splash = QLabel(self)
        self._splash.setGeometry(0, 0, self.width(), self.height())
        self._splash.setAlignment(Qt.AlignCenter)
        self._splash.setTextFormat(Qt.RichText)
        self._splash.setText(SPLASH_MESSAGE)
        self._splash.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {Color.BG_DARK}, stop:1 {Color.BG_SURFACE});
            border-radius: {Radius.XL}px;
        """)
        self._splash.show()
        self._splash.raise_()

    def _init_app(self):
        """初始化应用组件"""
        # 加载模型
        self._load_model()

        # 构建 UI
        self._build_ui()

        # 应用全局样式
        self._apply_global_style()

        # 隐藏闪屏
        self._splash.hide()
        self._splash.deleteLater()
        self._splash = None
        self._page_loaded = True

    def _load_model(self):
        """加载YOLO模型（强制CPU运行，适配无N卡电脑）"""
        if not os.path.exists(MODEL_PATH):
            print(f"[警告] 模型文件未找到: {MODEL_PATH}")
            self._model = None
            return
        try:
            # 新版 Ultralytics 构造函数无 device 参数，通过 predict 时指定
            self._model = YOLO(MODEL_PATH)
            print("✅ 自定义垃圾模型加载成功（CPU模式）")
        except Exception as e:
            print(f"[错误] 模型加载失败: {e}")
            self._model = None

    def _build_ui(self):
        """构建完整 UI"""
        # 主容器（带圆角和阴影）
        container = QWidget(self)
        container.setObjectName("appContainer")
        container.setStyleSheet(f"""
            #appContainer {{
                background: {Color.BG_DARK};
                border-radius: {Radius.XL}px;
            }}
        """)

        # 主布局
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 标题栏 ──
        self.title_bar = TitleBar(container, "智分宝 · 垃圾分类检测系统")
        self.title_bar.window_minimized.connect(self.showMinimized)
        self.title_bar.window_maximized.connect(self._on_maximize)
        self.title_bar.window_restored.connect(self._on_restore)
        self.title_bar.window_closed.connect(self.close)
        main_layout.addWidget(self.title_bar)

        # ── 主体：侧边栏 + 内容区域 ──
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar()
        self.sidebar.navigation_changed.connect(self._on_nav_change)
        self.sidebar.exit_requested.connect(self.close)
        body_layout.addWidget(self.sidebar)

        # 分隔线
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background: {Color.BORDER};")
        body_layout.addWidget(divider)

        # 页面容器
        self.pages = QStackedWidget()
        self.pages.setStyleSheet(f"background: {Color.BG_SURFACE}; border-radius: 0;")

        self.page_dashboard = DashboardPage()
        self.page_detection = DetectionPage(self._model)
        self.page_history = HistoryPage()

        self.pages.addWidget(self.page_dashboard)    # index 0
        self.pages.addWidget(self.page_detection)     # index 1
        self.pages.addWidget(self.page_history)       # index 2

        # 连接仪表盘快速跳转
        self.page_dashboard.navigate_requested.connect(self._on_dashboard_nav)

        # 连接检测页面信号
        self.page_detection.detection_made.connect(self._on_detection_made)
        self.page_detection.results_ready.connect(self.add_detection_record)
        self.page_detection.detection_started.connect(self.reset_stats)

        body_layout.addWidget(self.pages, 1)
        main_layout.addWidget(body, 1)

        # 设置主容器
        self.setCentralWidget(container)

        # 窗口阴影
        self._apply_shadow()

    def _apply_shadow(self):
        """给窗口添加阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.centralWidget().setGraphicsEffect(shadow)

    def _apply_global_style(self):
        """应用全局样式表"""
        self.setStyleSheet(GLOBAL_STYLESHEET)

    # ── 导航 ──

    def _on_nav_change(self, index):
        """侧边栏导航切换"""
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)

    def _on_dashboard_nav(self, page_index):
        """仪表盘快速操作跳转"""
        self.sidebar.set_active(page_index)
        self.pages.setCurrentIndex(page_index)

    def _on_detection_made(self, total, categories, avg_conf, fps):
        """检测页面更新统计 — 累计后更新仪表盘"""
        self._cum_total += total
        self.page_dashboard.update_stats(
            self._cum_total, categories, avg_conf, fps
        )

    def add_detection_record(self, detections):
        """添加检测记录到历史页面"""
        self.page_history.add_record(detections)

    def reset_stats(self):
        """重置累计统计（新检测开始时）"""
        self._cum_total = 0

    # ── 窗口控制 ──

    def _on_maximize(self):
        self._normal_rect = self.frameGeometry()
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)

    def _on_restore(self):
        if self._normal_rect:
            self.setGeometry(self._normal_rect)
            self._normal_rect = None

    # ── 关闭事件 ──

    def closeEvent(self, event):
        """清理资源后关闭"""
        # 停止检测
        if hasattr(self, 'page_detection'):
            self.page_detection._stop_detection()
        event.accept()

    def paintEvent(self, event):
        """绘制窗口圆角背景（在子控件下方）"""
        if not self._page_loaded:
            # 闪屏已经覆盖了
            super().paintEvent(event)
            return
        # 用 centralWidget 处理圆角
        super().paintEvent(event)
