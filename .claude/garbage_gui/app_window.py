"""
主窗口 — 无边框现代窗口，整合侧边栏、页面、标题栏
"""
import cv2
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QFrame, QGraphicsDropShadowEffect, QLabel,
    QDesktopWidget, QMessageBox, QStatusBar,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QKeySequence, QFont

from .theme import Color, Radius, GLOBAL_STYLESHEET, setup_fonts
from .widgets import TitleBar, Sidebar, AboutDialog
from .pages import DashboardPage, DetectionPage, HistoryPage
from .config import CONFIG
from .logger import logger

# 模型加载
from ultralytics import YOLO

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
        self.setWindowTitle(CONFIG.WINDOW_TITLE)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # 窗口状态
        self._model = None
        self._page_loaded = False
        self._normal_rect = None
        self._cum_total = 0

        # 设置窗口大小
        self.resize(CONFIG.WINDOW_WIDTH, CONFIG.WINDOW_HEIGHT)
        self._center_on_screen()

        # 键盘快捷键
        self._setup_shortcuts()

        # 显示闪屏后延迟初始化
        self._show_splash()
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

    def _setup_shortcuts(self):
        """注册键盘快捷键"""
        from PyQt5.QtWidgets import QShortcut

        # Ctrl+Q 退出
        sc_quit = QShortcut(QKeySequence("Ctrl+Q"), self)
        sc_quit.activated.connect(self._confirm_close)

        # Ctrl+O 打开图片
        sc_open = QShortcut(QKeySequence("Ctrl+O"), self)
        sc_open.activated.connect(self._shortcut_open_image)

        # Ctrl+C 开启摄像头
        sc_cam = QShortcut(QKeySequence("Ctrl+C"), self)
        sc_cam.activated.connect(self._shortcut_start_camera)

        # Ctrl+S 保存结果
        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.activated.connect(self._shortcut_save)

        # F5 开始/停止
        sc_toggle = QShortcut(QKeySequence("F5"), self)
        sc_toggle.activated.connect(self._shortcut_toggle_detection)

        # F1 关于
        sc_about = QShortcut(QKeySequence("F1"), self)
        sc_about.activated.connect(self._show_about)

    def _shortcut_open_image(self):
        """快捷键打开图片"""
        if self._page_loaded:
            self._on_nav_change(1)
            self.page_detection._on_image()

    def _shortcut_start_camera(self):
        """快捷键开启摄像头"""
        if self._page_loaded:
            self._on_nav_change(1)
            self.page_detection._on_camera()

    def _shortcut_save(self):
        """快捷键保存结果"""
        if self._page_loaded:
            self.page_detection._on_save()

    def _shortcut_toggle_detection(self):
        """快捷键切换检测状态"""
        if not self._page_loaded:
            return
        self._on_nav_change(1)
        if self.page_detection._is_detecting:
            self.page_detection._on_stop()
        else:
            self.page_detection._on_camera()

    def _confirm_close(self):
        """关闭前确认"""
        reply = QMessageBox.question(
            self, "确认退出",
            "确定要退出智分宝吗？\n当前检测将会停止。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.close()

    def _show_about(self):
        """显示关于对话框"""
        dlg = AboutDialog(self)
        dlg.exec_()

    # ── 初始化 ──

    def _init_app(self):
        """初始化应用组件"""
        self._load_model()
        self._build_ui()
        self._apply_global_style()
        self._splash.hide()
        self._splash.deleteLater()
        self._splash = None
        self._page_loaded = True
        logger.info("🎯 智分宝启动完成")

    def _load_model(self):
        """加载YOLO模型（CPU模式）"""
        if not os.path.exists(CONFIG.MODEL_PATH):
            logger.warning(f"模型文件未找到: {CONFIG.MODEL_PATH}")
            self._model = None
            return
        try:
            self._model = YOLO(CONFIG.MODEL_PATH)
            logger.info("✅ 自定义垃圾模型加载成功（CPU模式）")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self._model = None

    def _build_ui(self):
        """构建完整 UI"""
        container = QWidget(self)
        container.setObjectName("appContainer")
        container.setStyleSheet(f"""
            #appContainer {{
                background: {Color.BG_DARK};
                border-radius: {Radius.XL}px;
            }}
        """)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 标题栏 ──
        self.title_bar = TitleBar(container, CONFIG.WINDOW_TITLE)
        self.title_bar.window_minimized.connect(self.showMinimized)
        self.title_bar.window_maximized.connect(self._on_maximize)
        self.title_bar.window_restored.connect(self._on_restore)
        self.title_bar.window_closed.connect(self._confirm_close)
        self.title_bar.about_requested.connect(self._show_about)
        main_layout.addWidget(self.title_bar)

        # ── 主体 ──
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar()
        self.sidebar.navigation_changed.connect(self._on_nav_change)
        self.sidebar.exit_requested.connect(self._confirm_close)
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

        self.pages.addWidget(self.page_dashboard)
        self.pages.addWidget(self.page_detection)
        self.pages.addWidget(self.page_history)

        self.page_dashboard.navigate_requested.connect(self._on_dashboard_nav)
        self.page_detection.detection_made.connect(self._on_detection_made)
        self.page_detection.results_ready.connect(self.add_detection_record)
        self.page_detection.detection_started.connect(self.reset_stats)

        body_layout.addWidget(self.pages, 1)
        main_layout.addWidget(body, 1)

        # ── 状态栏 ──
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {Color.BG_SURFACE};
                color: {Color.TEXT_MUTED};
                border-top: 1px solid {Color.BORDER};
                font-size: 11px;
                padding: 2px 12px;
                border-bottom-left-radius: {Radius.XL}px;
                border-bottom-right-radius: {Radius.XL}px;
            }}
        """)
        self.status_bar.showMessage("就绪 | Ctrl+O 打开图片  F5 开始检测  F1 关于")
        main_layout.addWidget(self.status_bar)

        self.setCentralWidget(container)
        self._apply_shadow()

    def _apply_shadow(self):
        """窗口阴影"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.centralWidget().setGraphicsEffect(shadow)

    def _apply_global_style(self):
        self.setStyleSheet(GLOBAL_STYLESHEET)

    # ── 导航 ──

    def _on_nav_change(self, index):
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)

    def _on_dashboard_nav(self, page_index):
        self.sidebar.set_active(page_index)
        self.pages.setCurrentIndex(page_index)

    def _on_detection_made(self, total, categories, avg_conf, fps):
        self._cum_total += total
        self.page_dashboard.update_stats(self._cum_total, categories, avg_conf, fps)

    def add_detection_record(self, detections):
        self.page_history.add_record(detections)

    def reset_stats(self):
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
        logger.info("正在关闭程序...")
        if hasattr(self, 'page_detection'):
            self.page_detection._stop_detection()
        if hasattr(self, 'page_history'):
            self.page_history.save_records()
        logger.info("程序已退出")
        event.accept()

    def paintEvent(self, event):
        """填充窗口背景，防止拖拽时出现黑色残留"""
        from PyQt5.QtGui import QPainter
        painter = QPainter(self)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(Color.BG_DARK))
        painter.drawRect(self.rect())
        painter.end()
        super().paintEvent(event)
