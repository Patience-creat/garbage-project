"""
主窗口 — 无边框现代窗口，整合侧边栏、页面、标题栏
"""
import cv2
import os

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QFrame, QLabel,
    QDesktopWidget, QMessageBox, QStatusBar,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QKeySequence, QFont, QPainter, QPainterPath, QRegion

from .theme import Color, Radius, GLOBAL_STYLESHEET, setup_fonts
from .widgets import TitleBar, Sidebar, AboutDialog
from .pages import DashboardPage, DetectionPage, HistoryPage
from .review_pages import HistoryReviewPage, ExpertReviewPage
from .config import CONFIG, auto_device, device_display_name
from .logger import logger

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
        # 不启用 WA_TranslucentBackground — 改用 setMask 裁剪窗口形状。
        # 分层窗口（WS_EX_LAYERED）在 Windows 拖拽时来不及合成，会回退黑色背景。
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # 窗口状态
        self._model = None
        self._page_loaded = False
        self._normal_rect = None

        # 累计统计数据（跨多次图片上传累积）
        self._cum_total = 0
        self._cum_categories = set()
        self._cum_confidence_sum = 0.0
        self._cum_confidence_count = 0
        self._cum_fps = 0.0

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
        """初始化应用组件（先构建 UI，再后台加载模型 → 大幅提升启动速度）"""
        # 1. 先构建 UI（很快，毫秒级）
        self._build_ui()
        self._apply_global_style()
        self._page_loaded = True
        self._update_window_mask()

        # 2. 隐藏闪屏，让用户立即看到界面
        self._splash.hide()
        self._splash.deleteLater()
        self._splash = None

        # 3. 延迟加载模型（不阻塞 UI 绘制）
        QTimer.singleShot(0, self._load_model)
        logger.info("🎯 智分宝启动完成（模型后台加载中...）")

    def _load_model(self):
        """加载YOLO模型（延迟导入 + 后台加载，不阻塞UI）"""
        if not os.path.exists(CONFIG.MODEL_PATH):
            logger.warning(f"模型文件未找到: {CONFIG.MODEL_PATH}")
            self._model = None
            self.page_detection.update_model(None)
            self.status_bar.showMessage("⚠ 模型文件未找到")
            return
        try:
            from ultralytics import YOLO  # 延迟导入，加速模块加载
            self.status_bar.showMessage("🔄 正在加载模型...")
            self.status_bar.repaint()
            device = auto_device()
            self._model = YOLO(CONFIG.MODEL_PATH)
            self.page_detection.update_model(self._model)
            self.status_bar.showMessage(f"✓ 模型已加载（{device_display_name(device)}）| 就绪")
            logger.info(f"✅ 自定义垃圾模型加载成功（{device_display_name(device)}）")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self._model = None
            self.page_detection.update_model(None)
            self.status_bar.showMessage("⚠ 模型加载失败")

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
        self.page_history_review = HistoryReviewPage()
        self.page_expert_review = ExpertReviewPage()

        self.pages.addWidget(self.page_dashboard)      # index 0
        self.pages.addWidget(self.page_detection)      # index 1
        self.pages.addWidget(self.page_history)        # index 2
        self.pages.addWidget(self.page_history_review)  # index 3
        self.pages.addWidget(self.page_expert_review)   # index 4

        self.page_dashboard.navigate_requested.connect(self._on_dashboard_nav)
        self.page_detection.detection_made.connect(self._on_detection_made)
        self.page_detection.results_ready.connect(self.add_detection_record)
        self.page_dashboard.refresh_requested.connect(self._update_dashboard)
        self.page_detection.detection_started.connect(self._on_detection_started)
        self.page_history_review.navigate_requested.connect(self._on_dashboard_nav)
        self.page_expert_review.review_completed.connect(self._on_review_completed)

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

        # 容器边框绘制在 paintEvent 中完成
        self.setCentralWidget(container)

    def _apply_global_style(self):
        self.setStyleSheet(GLOBAL_STYLESHEET)

    # ── 导航 ──

    def _on_nav_change(self, index):
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)

    def _on_dashboard_nav(self, page_index):
        self.sidebar.set_active(page_index)
        self.pages.setCurrentIndex(page_index)

    def _on_detection_made(self, detections, fps):
        """收到检测结果 — 累积所有统计并更新仪表盘"""
        # 累积总检测数
        self._cum_total += len(detections)
        # 累积类别和置信度
        for cls_name, conf in detections:
            self._cum_categories.add(cls_name)
            self._cum_confidence_sum += conf
        self._cum_confidence_count += len(detections)
        # 记录处理速度（取最新值）
        self._cum_fps = fps if fps > 0 else self._cum_fps

        self._update_dashboard()

    def _update_dashboard(self):
        """将当前累积统计推送到仪表盘"""
        avg_conf = (self._cum_confidence_sum / max(self._cum_confidence_count, 1)) * 100
        self.page_dashboard.update_stats(
            self._cum_total,
            len(self._cum_categories),
            avg_conf,
            self._cum_fps,
        )

    def _on_detection_started(self, mode):
        """检测会话开始 — 摄像头模式清零累积统计，图片模式继续累积"""
        if mode == "camera":
            self.reset_cumulative_stats()

    def add_detection_record(self, detections):
        self.page_history.add_record(detections)

    def _on_review_completed(self, score, total):
        """专家评审完成后的处理"""
        logger.info(f"🏆 专家评审完成: {score}/{total}")

    def reset_cumulative_stats(self):
        """重置累积统计（用于开始新会话）"""
        self._cum_total = 0
        self._cum_categories.clear()
        self._cum_confidence_sum = 0.0
        self._cum_confidence_count = 0
        self._cum_fps = 0.0
        self._update_dashboard()

    # ── 窗口控制 ──

    def _on_maximize(self):
        self._normal_rect = self.frameGeometry()
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)

    def _on_restore(self):
        if self._normal_rect:
            self.setGeometry(self._normal_rect)
            self._normal_rect = None

    # ── 窗口裁剪 ──

    def _update_window_mask(self):
        """用圆角路径裁剪窗口本身，替代 WA_TranslucentBackground"""
        path = QPainterPath()
        path.addRoundedRect(
            0, 0, self.width(), self.height(),
            Radius.XL, Radius.XL,
        )
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def resizeEvent(self, event):
        """窗口大小变化时重新裁剪窗口形状"""
        super().resizeEvent(event)
        self._update_window_mask()

    # ── 关闭事件 ──

    def closeEvent(self, event):
        logger.info("正在关闭程序...")
        if hasattr(self, 'page_detection'):
            self.page_detection._stop_detection()
        if hasattr(self, 'page_history'):
            self.page_history.save_records()
        if hasattr(self, 'page_history_review'):
            self.page_history_review.save_meta()
        logger.info("程序已退出")
        event.accept()

    def paintEvent(self, event):
        """绘制窗口圆角背景 + 细边框（窗口形状由 setMask 裁剪）"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # 圆角路径（必须与 _update_window_mask 使用的半径完全一致）
        radius = Radius.XL
        path = QPainterPath()
        path.addRoundedRect(0, 0, rect.width(), rect.height(), radius, radius)

        # 填充背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(Color.BG_DARK))
        painter.drawPath(path)

        # 细边框
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QColor(Color.BORDER))
        painter.drawPath(path)

        painter.end()
