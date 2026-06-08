"""
应用页面 — 仪表盘、智能检测、检测记录
"""
import cv2
from collections import Counter

from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QScrollArea, QFileDialog, QSizePolicy, QSlider
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPixmap, QImage

from .theme import Color, Radius
from .widgets import StatCard, GlowButton, StatusIndicator, DetectionResultPanel
from .worker import DetectionWorker


# ═══════════════════════════════════════════════════════
# 1. 仪表盘页面
# ═══════════════════════════════════════════════════════
class DashboardPage(QWidget):
    """首页仪表盘 — 统计概览 + 快速操作"""

    navigate_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardPage")
        self._setup_ui()

        # 统计数据
        self._stats = {
            "total": 0,
            "classified": 0,
            "categories": 0,
            "accuracy": 0.0,
        }

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        # ── 顶部欢迎横幅 ──
        self._add_welcome_banner(layout)

        # ── 统计卡片 ──
        self._add_stat_cards(layout)

        # ── 快速操作 ──
        self._add_quick_actions(layout)

        # ── 底部空白 ──
        layout.addStretch()

    def _add_welcome_banner(self, parent_layout):
        """渐变欢迎横幅"""
        banner = QFrame()
        banner.setObjectName("welcomeBanner")
        banner.setFixedHeight(160)
        banner.setStyleSheet(f"""
            #welcomeBanner {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e1b4b, stop:0.5 #312e81, stop:1 #1e1b4b);
                border-radius: {Radius.XL}px;
                border: 1px solid rgba(99,102,241,0.3);
            }}
        """)

        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(32, 0, 32, 0)

        # 左侧文字
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setSpacing(8)

        welcome_title = QLabel("♻️ 欢迎使用智分宝")
        title_font = QFont("Microsoft YaHei UI", 22, QFont.Bold)
        welcome_title.setFont(title_font)
        welcome_title.setStyleSheet("color: white; background: transparent;")

        welcome_desc = QLabel(
            "基于 YOLOv8 深度学习引擎·12类垃圾精准识别\n"
            "支持摄像头实时检测、图片上传 · 一键启动，即开即用"
        )
        desc_font = QFont("Microsoft YaHei UI", 12)
        welcome_desc.setFont(desc_font)
        welcome_desc.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent;")

        text_layout.addWidget(welcome_title)
        text_layout.addWidget(welcome_desc)

        # 右侧装饰图标
        icon_label = QLabel("🤖")
        icon_font = QFont("Segoe UI Emoji", 64)
        icon_label.setFont(icon_font)
        icon_label.setStyleSheet("background: transparent;")
        icon_label.setFixedSize(100, 100)
        icon_label.setAlignment(Qt.AlignCenter)

        banner_layout.addWidget(text_container)
        banner_layout.addStretch()
        banner_layout.addWidget(icon_label)

        parent_layout.addWidget(banner)

    def _add_stat_cards(self, parent_layout):
        """统计卡片网格"""
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        self.card_total = StatCard("总检测数", "0", "🗑️", Color.GRADIENT_PRIMARY)
        self.card_categories = StatCard("识别类别", "0", "📦", Color.GRADIENT_ACCENT)
        self.card_accuracy = StatCard("平均置信度", "0%", "🎯", Color.GRADIENT_SUCCESS)
        self.card_fps = StatCard("处理速度", "---", "⚡", Color.GRADIENT_WARNING)

        cards_layout.addWidget(self.card_total, 0, 0)
        cards_layout.addWidget(self.card_categories, 0, 1)
        cards_layout.addWidget(self.card_accuracy, 1, 0)
        cards_layout.addWidget(self.card_fps, 1, 1)

        parent_layout.addLayout(cards_layout)

    def _add_quick_actions(self, parent_layout):
        """快捷操作区"""
        section_label = QLabel("快捷操作")
        section_font = QFont("Microsoft YaHei UI", 15, QFont.Bold)
        section_label.setFont(section_font)
        section_label.setStyleSheet(f"color: {Color.TEXT_PRIMARY}; background: transparent;")
        parent_layout.addWidget(section_label)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)

        actions = [
            ("📷 摄像头检测", "打开摄像头进行实时垃圾识别", 1),
            ("🖼️ 图片检测", "上传图片进行垃圾识别", 1),
            ("📊 查看记录", "浏览历史检测记录", 2),
        ]

        for title, desc, page_idx in actions:
            card = self._create_action_card(title, desc, page_idx)
            actions_layout.addWidget(card)

        parent_layout.addLayout(actions_layout)

    def _create_action_card(self, title, desc, page_idx):
        card = QFrame()
        card.setObjectName("actionCard")
        card.setFixedHeight(120)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            #actionCard {{
                background: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
            #actionCard:hover {{
                background: {Color.BG_CARD_HOVER};
                border-color: {Color.PRIMARY};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_font = QFont("Microsoft YaHei UI", 14, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; background: transparent;")

        desc_label = QLabel(desc)
        desc_font = QFont("Microsoft YaHei UI", 10)
        desc_label.setFont(desc_font)
        desc_label.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent;")
        desc_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        # 点击跳转
        def on_click(event):
            self.navigate_requested.emit(page_idx)
        card.mousePressEvent = on_click

        return card

    def update_stats(self, total, categories, accuracy, fps):
        """更新统计数值（带动画）"""
        self._stats["total"] = total
        self._stats["categories"] = categories
        self._stats["accuracy"] = accuracy
        self._stats["fps"] = fps

        self.card_total.animate_value(total)
        self.card_categories.animate_value(categories)
        self.card_accuracy.set_value(f"{accuracy:.1f}%")
        self.card_fps.set_value(f"{fps:.1f}" if fps > 0 else "---")


# ═══════════════════════════════════════════════════════
# 2. 检测页面
# ═══════════════════════════════════════════════════════
class DetectionPage(QWidget):
    """智能检测页面 — 摄像头/图片/视频检测"""

    # 信号
    detection_made = pyqtSignal(int, int, float, float)  # total, categories, avg_conf, fps
    results_ready = pyqtSignal(list)  # detections list for history
    detection_started = pyqtSignal()  # new detection session started

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.setObjectName("detectionPage")

        # 检测线程
        self._worker_thread = None
        self._worker = None

        # 状态
        self._is_detecting = False
        self._detection_count = 0
        self._total_fps = 0.0
        self._total_confidence = 0.0
        self._class_counter = Counter()
        self._current_image = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 工具栏 ──
        self._setup_toolbar()

        # ── 主体内容 ──
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(24, 16, 24, 24)
        content_layout.setSpacing(20)

        # 左侧：预览区
        preview_container = QWidget()
        preview_container.setObjectName("previewContainer")
        preview_container.setStyleSheet(f"""
            #previewContainer {{
                background: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(8)

        # 预览标题
        preview_header = QHBoxLayout()
        preview_title = QLabel("📷 检测画面")
        title_font = QFont("Microsoft YaHei UI", 13, QFont.Bold)
        preview_title.setFont(title_font)
        preview_title.setStyleSheet("color: white; background: transparent;")

        self.status_indicator = StatusIndicator("idle")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        preview_header.addWidget(self.status_indicator)
        preview_layout.addLayout(preview_header)

        # 画面预览
        self.preview_label = QLabel("点击上方按钮开始检测")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setStyleSheet(f"""
            background: {Color.BG_DARK};
            border: 1px solid {Color.BORDER};
            border-radius: {Radius.MD}px;
            color: {Color.TEXT_MUTED};
            font-size: 14px;
        """)

        # FPS 悬浮标签（作为 preview_container 的子控件）
        self.fps_label = QLabel(preview_container)
        self.fps_label.setStyleSheet(f"""
            background: rgba(0,0,0,0.7);
            color: {Color.SUCCESS};
            border: 1px solid rgba(16,185,129,0.3);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: bold;
        """)
        self.fps_label.setFixedHeight(28)
        self.fps_label.hide()

        preview_layout.addWidget(self.preview_label, 1)

        # 底部控制条
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        self.btn_camera = GlowButton("  开启摄像头", "📷")
        self.btn_image = GlowButton("  上传图片", "🖼️", primary=False)
        self.btn_stop = GlowButton("  停止检测", "⏹️", primary=False)
        self.btn_save = GlowButton("  保存结果", "💾", primary=False)

        controls_layout.addWidget(self.btn_camera)
        controls_layout.addWidget(self.btn_image)
        controls_layout.addWidget(self.btn_stop)
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_save)

        preview_layout.addLayout(controls_layout)
        content_layout.addWidget(preview_container, 3)

        # 右侧：结果面板
        right_panel = QWidget()
        right_panel.setFixedWidth(340)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 结果标题
        result_header = QLabel("📋 检测结果")
        result_font = QFont("Microsoft YaHei UI", 13, QFont.Bold)
        result_header.setFont(result_font)
        result_header.setStyleSheet(f"color: white; background: transparent;")
        right_layout.addWidget(result_header)

        # 检测结果面板
        self.result_panel = DetectionResultPanel()
        right_layout.addWidget(self.result_panel, 1)

        # 统计摘要
        self._setup_summary(right_layout)

        content_layout.addWidget(right_panel, 2)

        main_layout.addWidget(self._toolbar)
        main_layout.addWidget(content, 1)

    def _setup_toolbar(self):
        self._toolbar = QWidget()
        self._toolbar.setObjectName("detectToolbar")
        self._toolbar.setFixedHeight(56)
        self._toolbar.setStyleSheet(f"""
            #detectToolbar {{
                background: {Color.BG_SURFACE};
                border-bottom: 1px solid {Color.BORDER};
            }}
        """)

        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("🔍 智能检测")
        title_font = QFont("Microsoft YaHei UI", 15, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: white; background: transparent;")

        # 置信度滑块
        conf_label = QLabel("置信度阈值:")
        conf_label.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent;")
        conf_label_font = QFont("Microsoft YaHei UI", 11)
        conf_label.setFont(conf_label_font)

        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(10, 90)
        self.conf_slider.setValue(30)
        self.conf_slider.setFixedWidth(120)
        self.conf_slider.setObjectName("confSlider")

        self.conf_value_label = QLabel("0.30")
        self.conf_value_label.setFixedWidth(40)
        self.conf_value_label.setStyleSheet(f"color: {Color.PRIMARY}; background: transparent; font-weight: bold;")

        self.conf_slider.valueChanged.connect(
            lambda v: self.conf_value_label.setText(f"{v/100:.2f}")
        )

        toolbar_layout.addWidget(title)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(conf_label)
        toolbar_layout.addWidget(self.conf_slider)
        toolbar_layout.addWidget(self.conf_value_label)

    def _setup_summary(self, parent_layout):
        summary_card = QFrame()
        summary_card.setObjectName("summaryCard")
        summary_card.setStyleSheet(f"""
            #summaryCard {{
                background: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(6)

        summary_header = QLabel("📊 检测统计")
        header_font = QFont("Microsoft YaHei UI", 12, QFont.Bold)
        summary_header.setFont(header_font)
        summary_header.setStyleSheet("color: white; background: transparent;")
        summary_layout.addWidget(summary_header)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)
        stats_grid.setVerticalSpacing(4)

        self.stat_labels = {}
        stats_data = [
            (0, "本次检测:", "count_label", "0 个目标"),
            (1, "类别数:", "cat_label", "0 类"),
            (2, "平均置信度:", "conf_label", "0%"),
            (3, "处理速度:", "fps_label", "--"),
        ]

        for row, label_text, key, default_val in stats_data:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent; font-size: 11px;")
            val = QLabel(default_val)
            val.setObjectName(f"stat_{key}")
            val.setStyleSheet(f"color: {Color.TEXT_PRIMARY}; background: transparent; font-size: 12px; font-weight: bold;")
            self.stat_labels[key] = val
            stats_grid.addWidget(lbl, row, 0)
            stats_grid.addWidget(val, row, 1)

        summary_layout.addLayout(stats_grid)
        parent_layout.addWidget(summary_card)

    def _connect_signals(self):
        self.btn_camera.clicked.connect(self._on_camera)
        self.btn_image.clicked.connect(self._on_image)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_save.clicked.connect(self._on_save)

    # ── 按钮事件 ──

    def _on_camera(self):
        self._stop_detection()
        self._start_detection("camera")

    def _on_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择检测图片", "",
            "图片文件 (*.jpg *.png *.jpeg *.bmp);;所有文件 (*)"
        )
        if path:
            self._stop_detection()
            self._start_detection("image", path=path)

    def _on_stop(self):
        self._stop_detection()
        self.status_indicator.update_state("idle")

    def _on_save(self):
        if self._current_image is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存检测结果", "detection_result.jpg",
            "JPEG (*.jpg);;PNG (*.png)"
        )
        if path and self._current_image is not None:
            try:
                # Convert QPixmap to QImage to save
                if isinstance(self._current_image, QPixmap):
                    self._current_image.save(path)
            except Exception as e:
                print(f"保存失败: {e}")

    # ── 线程管理 ──

    def _start_detection(self, mode, path=None):
        if self.model is None:
            self.status_indicator.update_state("error")
            return

        # 创建工作线程
        self._worker_thread = QThread(self)
        self._worker = DetectionWorker(self.model)
        self._worker.moveToThread(self._worker_thread)

        # 连接信号
        self._worker.result_ready.connect(self._on_result)
        self._worker.fps_updated.connect(self._on_fps)
        self._worker.status_message.connect(self._on_status)
        self._worker.camera_error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker_thread.started.connect(self._worker.run)

        # 配置
        conf = self.conf_slider.value() / 100.0
        self._worker.set_conf_threshold(conf)

        # 启动
        self._is_detecting = True
        self._class_counter.clear()
        self._detection_count = 0
        self._total_confidence = 0.0

        if mode == "camera":
            self._worker.start_camera()
        elif mode == "image" and path:
            self._worker.start_image(path)

        self._worker_thread.start()
        self.detection_started.emit()
        self.status_indicator.update_state("running")

    def _stop_detection(self):
        if self._worker:
            self._worker.stop()
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait(1000)
            self._worker = None
            self._worker_thread = None
        self._is_detecting = False

    # ── 工作线程回调 ──

    def _on_result(self, frame, detections):
        """收到推理结果"""
        # 更新画面
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        qimg = QImage(rgb.data, w, h, w * c, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self._current_image = scaled

        # 更新检测结果
        self.result_panel.update_results(detections)

        # 统计
        self._detection_count += len(detections)
        for cls_name, conf in detections:
            self._class_counter[cls_name] += 1
            self._total_confidence += conf

        total = len(detections)
        categories = len(self._class_counter)
        avg_conf = (self._total_confidence / max(self._detection_count, 1)) * 100
        fps = self._total_fps

        # 更新统计标签
        self.stat_labels["count_label"].setText(f"{total} 个目标")
        self.stat_labels["cat_label"].setText(f"{categories} 类")
        self.stat_labels["conf_label"].setText(f"{avg_conf:.1f}%")
        self.stat_labels["fps_label"].setText(f"{fps:.1f}" if fps > 0 else "--")

        # 发射信号通知主窗口更新仪表盘 + 保存历史
        self.detection_made.emit(total, categories, avg_conf, fps)
        if detections:
            self.results_ready.emit(detections)

    def _on_fps(self, fps):
        self._total_fps = fps
        self.fps_label.setText(f"  ⚡ {fps:.1f} FPS  ")
        self.fps_label.show()
        self.fps_label.adjustSize()

    def _on_status(self, msg):
        print(f"[Worker] {msg}")

    def _on_error(self, msg):
        self.status_indicator.update_state("error")
        # 在预览区显示错误
        self.preview_label.setText(f"⚠️ {msg}")
        self.preview_label.setAlignment(Qt.AlignCenter)

    def _on_worker_finished(self):
        self._is_detecting = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # fps_label 是 preview_container 的子控件，用容器坐标
        if self.fps_label.isVisible():
            pw = self.preview_label.width()
            fw = self.fps_label.width()
            self.fps_label.move(pw - fw - 12, 12)

    def update_model(self, model):
        """更新模型引用（用于重新加载）"""
        self.model = model


# ═══════════════════════════════════════════════════════
# 3. 检测记录页面
# ═══════════════════════════════════════════════════════
class HistoryPage(QWidget):
    """检测记录页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyPage")
        self._records = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部工具栏
        toolbar = QWidget()
        toolbar.setObjectName("historyToolbar")
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(f"""
            #historyToolbar {{
                background: {Color.BG_SURFACE};
                border-bottom: 1px solid {Color.BORDER};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("📋 检测记录")
        title_font = QFont("Microsoft YaHei UI", 15, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: white; background: transparent;")

        self.btn_clear = QPushButton("🗑️ 清空记录")
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Color.TEXT_SECONDARY};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.MD}px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {Color.ERROR};
                color: {Color.ERROR};
            }}
        """)
        self.btn_clear.clicked.connect(self._clear_records)

        toolbar_layout.addWidget(title)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.btn_clear)
        main_layout.addWidget(toolbar)

        # 内容区域（滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self._records_layout = QVBoxLayout(scroll_content)
        self._records_layout.setContentsMargins(24, 20, 24, 20)
        self._records_layout.setSpacing(12)
        self._records_layout.setAlignment(Qt.AlignTop)

        # 空状态
        self._empty_state = QLabel("   暂无检测记录\n   进行检测后，结果将显示在这里")
        empty_font = QFont("Microsoft YaHei UI", 13)
        self._empty_state.setFont(empty_font)
        self._empty_state.setAlignment(Qt.AlignCenter)
        self._empty_state.setMinimumHeight(200)
        self._empty_state.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent;")
        self._records_layout.addWidget(self._empty_state)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

    def add_record(self, detections, timestamp=None):
        """添加一条检测记录"""
        from datetime import datetime
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        record = {
            "time": timestamp,
            "detections": detections,
            "count": len(detections),
        }
        self._records.insert(0, record)

        # 隐藏空状态
        try:
            self._empty_state.hide()
        except RuntimeError:
            pass  # 防止 _empty_state 已被意外删除时报错

        # 在顶部插入记录卡片
        card = self._create_record_card(record)
        self._records_layout.insertWidget(0, card)

        # 保持最多50条
        while len(self._records) > 50:
            self._records.pop()
            item = self._records_layout.takeAt(self._records_layout.count() - 1)
            if item and item.widget() and item.widget() is not self._empty_state:
                item.widget().deleteLater()

    def _create_record_card(self, record):
        """创建一条记录卡片"""
        card = QFrame()
        card.setObjectName("recordCard")
        card.setStyleSheet(f"""
            #recordCard {{
                background: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
            #recordCard:hover {{
                background: {Color.BG_CARD_HOVER};
                border-color: {Color.PRIMARY};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # 头部：时间 + 数量
        header = QHBoxLayout()
        time_label = QLabel(f"🕐 {record['time']}")
        time_font = QFont("Microsoft YaHei UI", 11)
        time_label.setFont(time_font)
        time_label.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent;")

        count_badge = QLabel(f"  {record['count']} 个目标  ")
        count_badge.setStyleSheet(f"""
            background: rgba(99,102,241,0.15);
            color: {Color.PRIMARY_LIGHT};
            border: 1px solid rgba(99,102,241,0.3);
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)

        header.addWidget(time_label)
        header.addStretch()
        header.addWidget(count_badge)
        layout.addLayout(header)

        # 检测项预览（最多显示6个）
        dets = record["detections"][:6]
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)

        for cls_name, conf in dets:
            cn = Color.CLASS_NAMES_CN.get(cls_name, cls_name)
            icon = Color.CLASS_ICONS.get(cls_name, "📦")
            chip = QLabel(f"{icon} {cn}")
            chip.setStyleSheet(f"""
                background: {Color.BG_SURFACE};
                color: {Color.TEXT_SECONDARY};
                border: 1px solid {Color.BORDER};
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
            """)
            chips_layout.addWidget(chip)

        if len(record["detections"]) > 6:
            more = QLabel(f"+{len(record['detections']) - 6} 更多...")
            more.setStyleSheet(f"color: {Color.TEXT_MUTED}; font-size: 11px;")
            chips_layout.addWidget(more)

        chips_layout.addStretch()
        layout.addLayout(chips_layout)

        return card

    def _clear_records(self):
        """清空所有记录"""
        self._records.clear()
        # 清除所有卡片（保留 _empty_state）
        while self._records_layout.count():
            item = self._records_layout.takeAt(0)
            w = item.widget() if item else None
            if w and w is not self._empty_state:
                w.deleteLater()
        # 显示空状态
        self._empty_state.show()
