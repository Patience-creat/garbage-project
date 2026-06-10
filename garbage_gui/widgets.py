"""
自定义控件模块 — 标题栏、侧边栏、统计卡片、按钮等
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect, QRectF, QPoint
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QPainterPath, QFont
)

from .theme import Color, Radius, Spacing


# ═══════════════════════════════════════════════════════
# 1. 自定义标题栏
# ═══════════════════════════════════════════════════════
class TitleBar(QWidget):
    """现代风格自定义标题栏 — 支持拖动、双击最大化"""

    window_minimized = pyqtSignal()
    window_maximized = pyqtSignal()
    window_closed = pyqtSignal()
    window_restored = pyqtSignal()
    about_requested = pyqtSignal()

    def __init__(self, parent, title="智分宝"):
        super().__init__(parent)
        self.parent = parent
        self._is_dragging = False
        self._drag_pos = QPoint()
        self._is_maximized = False
        self._title = title
        self.setFixedHeight(48)
        self.setObjectName("titleBar")

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        # App 图标 + 标题
        self.icon_label = QLabel(" ♻️ ")
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setAlignment(Qt.AlignCenter)
        icon_font = QFont("Segoe UI Emoji", 16)
        self.icon_label.setFont(icon_font)

        self.title_label = QLabel(self._title)
        self.title_label.setObjectName("titleLabel")
        title_font = QFont()
        title_font.setFamily("Microsoft YaHei UI")
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.title_label.setFont(title_font)

        # 中间弹簧
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 窗口控制按钮
        self.btn_about = TitleBarButton("ℹ️", self)
        self.btn_about.setToolTip("关于 (F1)")
        self.btn_about.clicked.connect(self._on_about)
        self.btn_minimize = TitleBarButton("─", self)
        self.btn_minimize.clicked.connect(self._on_minimize)
        self.btn_maximize = TitleBarButton("□", self)
        self.btn_maximize.clicked.connect(self._on_maximize)
        self.btn_close = TitleBarButton("✕", self, is_close=True)
        self.btn_close.clicked.connect(self._on_close)

        # layout order
        layout.addWidget(self.icon_label)
        layout.addSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(spacer, 1)
        layout.addWidget(self.btn_about)
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

    def _apply_style(self):
        self.setStyleSheet(f"""
            #titleBar {{
                background: transparent;
                border-top-left-radius: {Radius.XL}px;
                border-top-right-radius: {Radius.XL}px;
            }}
            #titleLabel {{
                color: {Color.TEXT_PRIMARY};
                background: transparent;
                padding: 0;
            }}
        """)

    def _on_minimize(self):
        self.window_minimized.emit()

    def _on_maximize(self):
        if self._is_maximized:
            self.window_restored.emit()
        else:
            self.window_maximized.emit()
        self._is_maximized = not self._is_maximized
        self.btn_maximize.setText("❐" if self._is_maximized else "□")

    def _on_close(self):
        self.window_closed.emit()

    def _on_about(self):
        self.about_requested.emit()

    # ── 窗口拖动 ──
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            win = self.window()
            self._drag_pos = event.globalPos() - win.frameGeometry().topLeft()
            self.grabMouse()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag_pos)
            if self._is_maximized:
                self._is_maximized = False
                self.btn_maximize.setText("□")
                self.window_restored.emit()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        if self.mouseGrabber() is self:
            self.releaseMouse()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self._on_maximize()
        event.accept()

    def set_title(self, text):
        self._title = text
        self.title_label.setText(text)


class TitleBarButton(QPushButton):
    """标题栏控制按钮"""

    def __init__(self, text, parent=None, is_close=False):
        super().__init__(text, parent)
        self._is_close = is_close
        self.setFixedSize(42, 32)
        self.setCursor(Qt.ArrowCursor)
        self.setObjectName("titleBarBtn")
        self.setProperty("isClose", is_close)
        self._setup_style()

    def _setup_style(self):
        close_hover = "#dc2626"
        normal_hover = Color.BG_CARD_HOVER

        self.setStyleSheet(f"""
            #titleBarBtn {{
                background: transparent;
                color: {Color.TEXT_PRIMARY};
                border: none;
                border-radius: {Radius.SM}px;
                font-size: 14px;
                font-weight: 300;
                padding: 0;
            }}
            #titleBarBtn:hover {{
                background: {normal_hover};
            }}
            #titleBarBtn[isClose="true"]:hover {{
                background: {close_hover};
                color: white;
            }}
            #titleBarBtn:pressed {{
                background: rgba(255,255,255,0.1);
            }}
        """)


# ═══════════════════════════════════════════════════════
# 2. 导航侧边栏
# ═══════════════════════════════════════════════════════
class SidebarButton(QPushButton):
    """侧边栏导航按钮"""

    def __init__(self, text, icon_emoji="●", parent=None):
        super().__init__(parent)
        self._icon = icon_emoji
        self._text = text
        self._active = False
        self.setObjectName("sidebarBtn")
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(52)
        self._update_style()

    def set_active(self, active):
        self._active = active
        self.setChecked(active)
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                #sidebarBtn {{
                    background: {Color.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {Radius.MD}px;
                    font-size: 13px;
                    font-weight: bold;
                    text-align: left;
                    padding-left: 16px;
                }}
                #sidebarBtn:hover {{
                    background: {Color.PRIMARY_HOVER};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                #sidebarBtn {{
                    background: transparent;
                    color: {Color.TEXT_SECONDARY};
                    border: none;
                    border-radius: {Radius.MD}px;
                    font-size: 13px;
                    font-weight: normal;
                    text-align: left;
                    padding-left: 16px;
                }}
                #sidebarBtn:hover {{
                    background: {Color.BG_CARD};
                    color: {Color.TEXT_PRIMARY};
                }}
            """)

    def paintEvent(self, event):
        """重绘以支持 emoji+文本 组合"""
        super().paintEvent(event)
        if not self.text():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            # 绘制 emoji 图标
            emoji_font = QFont("Segoe UI Emoji", 16)
            painter.setFont(emoji_font)
            painter.drawText(QRect(16, 0, 32, self.height()), Qt.AlignCenter, self._icon)
            # 绘制文本
            text_font = QFont("Microsoft YaHei UI", 12)
            painter.setFont(text_font)
            if self._active:
                painter.setPen(QColor("#ffffff"))
            else:
                painter.setPen(QColor(Color.TEXT_SECONDARY))
            painter.drawText(QRect(56, 0, self.width() - 60, self.height()), Qt.AlignVCenter, self._text)
            painter.end()


class Sidebar(QWidget):
    """导航侧边栏"""

    navigation_changed = pyqtSignal(int)
    exit_requested = pyqtSignal()

    NAV_ITEMS = [
        ("仪表盘", "📊"),
        ("智能检测", "📷"),
        ("检测记录", "📋"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = []
        self._current_index = 0
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 16)
        layout.setSpacing(4)

        # Logo 区域
        logo_container = QWidget()
        logo_container.setFixedHeight(80)
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel("♻️ 智分宝")
        logo_font = QFont("Microsoft YaHei UI", 16, QFont.Bold)
        logo_label.setFont(logo_font)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet(f"color: {Color.TEXT_PRIMARY}; background: transparent;")

        sub_label = QLabel("垃圾分类检测系统")
        sub_font = QFont("Microsoft YaHei UI", 10)
        sub_label.setFont(sub_font)
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent;")

        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(sub_label)
        layout.addWidget(logo_container)

        # 分隔线
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background: {Color.BORDER}; max-height: 1px;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(8)

        # 导航按钮
        for i, (name, icon) in enumerate(self.NAV_ITEMS):
            btn = SidebarButton(name, icon)
            btn.clicked.connect(lambda checked, idx=i: self._on_nav_click(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)

        # 底部弹簧
        layout.addStretch(1)

        # ── 退出按钮 ──
        btn_exit = QPushButton("   退出程序")
        btn_exit.setCursor(Qt.PointingHandCursor)
        btn_exit.setFixedHeight(44)
        btn_exit.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Color.ERROR};
                border: 1px solid rgba(239,68,68,0.2);
                border-radius: {Radius.MD}px;
                font-size: 13px;
                font-weight: normal;
                text-align: left;
                padding-left: 16px;
            }}
            QPushButton:hover {{
                background: rgba(239,68,68,0.1);
                border-color: {Color.ERROR};
            }}
            QPushButton:pressed {{
                background: rgba(239,68,68,0.2);
            }}
        """)
        btn_exit.clicked.connect(self.exit_requested.emit)
        layout.addWidget(btn_exit)
        layout.addSpacing(6)

        # 版本信息
        ver_label = QLabel("v2.0 · YOLOv8")
        ver_font = QFont("Microsoft YaHei UI", 9)
        ver_label.setFont(ver_font)
        ver_label.setAlignment(Qt.AlignCenter)
        ver_label.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent;")
        layout.addWidget(ver_label)

        # 初始激活第一个
        if self._buttons:
            self._buttons[0].set_active(True)

    def _on_nav_click(self, index):
        if index == self._current_index:
            return
        # 更新按钮状态
        for i, btn in enumerate(self._buttons):
            btn.set_active(i == index)
        self._current_index = index
        self.navigation_changed.emit(index)

    def set_active(self, index):
        if 0 <= index < len(self._buttons):
            self._on_nav_click(index)


# ═══════════════════════════════════════════════════════
# 3. 统计卡片
# ═══════════════════════════════════════════════════════
class StatCard(QFrame):
    """仪表盘统计卡片 — 带渐变色条和图标"""

    def __init__(self, title, value="0", icon="📊", gradient=Color.GRADIENT_PRIMARY, parent=None):
        super().__init__(parent)
        self._title = title
        self._value = value
        self._icon = icon
        self._gradient = gradient
        self.setObjectName("statCard")
        self.setFixedHeight(130)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()
        self._apply_style()

        # 数值动画
        self._anim_value = 0
        self._target_value = 0
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._tick_animation)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        # 顶部：图标 + 标题
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        icon_label = QLabel(self._icon)
        icon_font = QFont("Segoe UI Emoji", 20)
        icon_label.setFont(icon_font)
        icon_label.setFixedSize(36, 36)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setObjectName("cardIcon")
        icon_label.setStyleSheet("background: transparent;")

        title_label = QLabel(self._title)
        title_label.setObjectName("cardTitle")
        title_font = QFont("Microsoft YaHei UI", 11)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent;")

        top_layout.addWidget(icon_label)
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 数值
        self.value_label = QLabel(self._value)
        self.value_label.setObjectName("cardValue")
        value_font = QFont("Microsoft YaHei UI", 26, QFont.Bold)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet(f"color: {Color.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(self.value_label)

        # 底部渐变条
        bar = QFrame()
        bar.setFixedHeight(3)
        bar.setObjectName("cardBar")
        bar.setStyleSheet(f"background: {self._gradient}; border-radius: 2px;")
        layout.addWidget(bar)

    def _apply_style(self):
        self.setStyleSheet(f"""
            #statCard {{
                background: {Color.BG_CARD};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
            #statCard:hover {{
                background: {Color.BG_CARD_HOVER};
                border-color: {Color.PRIMARY};
            }}
        """)

    def animate_value(self, target_value, duration=600):
        """数值递增动画"""
        self._target_value = target_value
        self._anim_value = 0
        try:
            self._current_value = int(self._value.replace(",", ""))
        except ValueError:
            self._current_value = 0
        self._anim_step = (target_value - self._current_value) / max(duration / 30, 1)
        self._anim_timer.start(30)

    def _tick_animation(self):
        self._current_value += self._anim_step
        if abs(self._current_value - self._target_value) < 1:
            self._current_value = self._target_value
            self._anim_timer.stop()
        # 格式化显示
        if self._current_value >= 1000000:
            self.value_label.setText(f"{self._current_value/10000:.0f}万")
        else:
            self.value_label.setText(f"{int(self._current_value):,}")

    def set_value(self, value):
        self._value = str(value)
        self.value_label.setText(str(value))


# ═══════════════════════════════════════════════════════
# 4. 玻璃态容器
# ═══════════════════════════════════════════════════════
class GlassCard(QFrame):
    """玻璃拟态卡片 — 半透明毛玻璃效果"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setStyleSheet(f"""
            #glassCard {{
                background: rgba(26, 26, 53, 0.85);
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

    def paintEvent(self, event):
        """绘制背景时带半透明效果"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), Radius.LG, Radius.LG)
        painter.setBrush(QColor(26, 26, 53, 220))
        painter.setPen(QPen(QColor(Color.BORDER), 1))
        painter.drawPath(path)
        painter.end()


# ═══════════════════════════════════════════════════════
# 5. 检测结果卡片
# ═══════════════════════════════════════════════════════
class DetectionResultCard(QFrame):
    """检测结果条目卡片 — 显示类别、置信度、颜色标记"""

    def __init__(self, class_name, confidence, class_color="#6366f1", icon="📦", parent=None):
        super().__init__(parent)
        self.setObjectName("resultCard")
        self.setFixedHeight(52)
        self._class_name = class_name
        self._confidence = confidence
        self._class_color = class_color
        self._icon = icon
        self._cn_name = class_name  # will be overridden

        self.setStyleSheet(f"""
            #resultCard {{
                background: rgba(37,37,80,0.6);
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.MD}px;
            }}
            #resultCard:hover {{
                background: rgba(37,37,80,0.9);
                border-color: {self._class_color};
            }}
        """)

    def paintEvent(self, event):
        """自定义绘制：左侧色条 + 图标 + 名称 + 置信度"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        h = self.height()

        # 左侧色条
        bar_rect = QRect(0, 4, 4, h - 8)
        path = QPainterPath()
        path.addRoundedRect(QRectF(bar_rect), 2, 2)
        painter.setBrush(QColor(self._class_color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        # 图标
        emoji_font = QFont("Segoe UI Emoji", 16)
        painter.setFont(emoji_font)
        painter.drawText(QRect(16, 0, 30, h), Qt.AlignCenter, self._icon)

        # 类别名称（中文）
        name_font = QFont("Microsoft YaHei UI", 12, QFont.Bold)
        painter.setFont(name_font)
        painter.setPen(QColor("#f1f5f9"))
        painter.drawText(QRect(52, 4, 120, h - 4), Qt.AlignVCenter, self._cn_name)

        # 英文名
        eng_font = QFont("Microsoft YaHei UI", 9)
        painter.setFont(eng_font)
        painter.setPen(QColor(Color.TEXT_MUTED))
        painter.drawText(QRect(52, 22, 120, h - 22), Qt.AlignVCenter, self._class_name)

        # 置信度标签
        conf_text = f"{self._confidence * 100:.1f}%"
        conf_color = (
            Color.SUCCESS if self._confidence > 0.7
            else Color.WARNING if self._confidence > 0.4
            else Color.ERROR
        )

        # 置信度背景
        conf_bg = QColor(conf_color)
        conf_bg.setAlpha(25)
        conf_rect = QRect(self.width() - 90, 10, 76, h - 20)
        conf_path = QPainterPath()
        conf_path.addRoundedRect(QRectF(conf_rect), Radius.SM, Radius.SM)
        painter.setBrush(conf_bg)
        painter.setPen(Qt.NoPen)
        painter.drawPath(conf_path)

        # 置信度文字
        conf_font = QFont("Consolas", 11, QFont.Bold)
        painter.setFont(conf_font)
        painter.setPen(QColor(conf_color))
        painter.drawText(conf_rect, Qt.AlignCenter, conf_text)

        painter.end()


class DetectionResultPanel(QWidget):
    """检测结果面板 — 管理多个结果卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resultPanel")
        self._cards = []
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            #resultPanel {{
                background: {Color.BG_SURFACE};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(6)

    def update_results(self, detections):
        """更新检测结果列表

        Args:
            detections: list of (class_name, confidence) tuples
        """
        # 清除旧卡片
        for card in self._cards:
            self._layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # 添加新卡片
        for cls_name, conf in detections:
            color = Color.CLASS_COLORS.get(cls_name, Color.PRIMARY)
            icon = Color.CLASS_ICONS.get(cls_name, "📦")
            cn_name = Color.CLASS_NAMES_CN.get(cls_name, cls_name)

            card = DetectionResultCard(cls_name, conf, color, icon)
            card._cn_name = cn_name
            self._cards.append(card)
            self._layout.addWidget(card)

        # 空状态
        if not detections:
            empty_label = QLabel("   暂无检测结果\n   请选择图片或打开摄像头")
            empty_font = QFont("Microsoft YaHei UI", 12)
            empty_label.setFont(empty_font)
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setFixedHeight(120)
            empty_label.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent;")
            self._cards.append(empty_label)
            self._layout.addWidget(empty_label)

        self._layout.addStretch()


# ═══════════════════════════════════════════════════════
# 6. 发光按钮
# ═══════════════════════════════════════════════════════
class GlowButton(QPushButton):
    """发光按钮 — 带悬停发光效果的主操作按钮"""

    def __init__(self, text, icon="", primary=True, parent=None):
        super().__init__(text, parent)
        self._icon = icon
        self._primary = primary
        self.setObjectName("glowBtn")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)

        p_bg = Color.GRADIENT_PRIMARY
        p_hover = Color.GRADIENT_PRIMARY
        p_pressed = Color.PRIMARY_DARK
        if not primary:
            p_bg = Color.BG_CARD
            p_hover = Color.BG_CARD_HOVER
            p_pressed = Color.BORDER

        self.setStyleSheet(f"""
            #glowBtn {{
                background: {p_bg};
                color: white;
                border: none;
                border-radius: {Radius.MD}px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 24px;
            }}
            #glowBtn:hover {{
                background: {p_hover};
            }}
            #glowBtn:pressed {{
                background: {p_pressed};
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._icon:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            emoji_font = QFont("Segoe UI Emoji", 14)
            painter.setFont(emoji_font)
            painter.drawText(QRect(12, 0, 24, self.height()), Qt.AlignCenter, self._icon)
            painter.end()


# ═══════════════════════════════════════════════════════
# 7. 状态指示器
# ═══════════════════════════════════════════════════════
class StatusIndicator(QWidget):
    """状态指示灯 — 圆点 + 文字"""

    STATES = {
        "idle": (Color.TEXT_MUTED, "等待中"),
        "running": (Color.PRIMARY, "检测中..."),
        "success": (Color.SUCCESS, "检测完成"),
        "error": (Color.ERROR, "检测失败"),
        "camera": (Color.SUCCESS, "摄像头已开启"),
    }

    def __init__(self, state="idle", parent=None):
        super().__init__(parent)
        self._state = state
        self._blink = False
        self.setFixedHeight(28)
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._toggle_blink)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.dot = QLabel("●")
        self.dot.setFixedWidth(16)
        dot_font = QFont("Segoe UI", 14)
        self.dot.setFont(dot_font)
        self.dot.setAlignment(Qt.AlignCenter)

        self.text_label = QLabel(self.STATES.get(state, ("", state))[1])
        text_font = QFont("Microsoft YaHei UI", 11)
        self.text_label.setFont(text_font)

        layout.addWidget(self.dot)
        layout.addWidget(self.text_label)

        self.update_state(state)

    def update_state(self, state):
        self._state = state
        color, text = self.STATES.get(state, (Color.TEXT_MUTED, state))
        self.text_label.setText(text)
        self.text_label.setStyleSheet(f"color: {color}; background: transparent;")

        if state in ("running",):
            self._blink_timer.start(500)
        else:
            self._blink_timer.stop()
            self.dot.setStyleSheet(f"color: {color}; background: transparent;")

    def _toggle_blink(self):
        self._blink = not self._blink
        color = self.STATES.get(self._state, (Color.TEXT_MUTED, ""))[0]
        if self._blink:
            self.dot.setStyleSheet(f"color: transparent; background: transparent;")
        else:
            self.dot.setStyleSheet(f"color: {color}; background: transparent;")


# ═══════════════════════════════════════════════════════
# 8. 圆形头像/预览
# ═══════════════════════════════════════════════════════
class CirclePreview(QLabel):
    """圆形裁剪预览控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setAlignment(Qt.AlignCenter)
        self._pixmap = None
        self.setObjectName("circlePreview")
        self.setStyleSheet(f"""
            #circlePreview {{
                background: {Color.BG_CARD};
                border: 2px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

    def set_image(self, pixmap):
        self._pixmap = pixmap
        self.setPixmap(pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap:
            self.setPixmap(self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


# ═══════════════════════════════════════════════════════
# 9. 关于对话框
# ═══════════════════════════════════════════════════════
class AboutDialog(QDialog):
    """关于对话框 — 显示项目信息、技术栈、性能指标"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 智分宝")
        self.setFixedSize(460, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background: {Color.BG_SURFACE};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

        self._setup_ui()
        self._center_on_parent(parent)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(6)

        # 标题区
        title = QLabel("♻️ 智分宝")
        title_font = QFont("Microsoft YaHei UI", 20, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("智能垃圾分类检测系统")
        subtitle_font = QFont("Microsoft YaHei UI", 12)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(subtitle)

        # 分隔线
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {Color.BORDER};")
        layout.addWidget(line)
        layout.addSpacing(8)

        # 信息表
        from .config import CONFIG
        info_items = [
            ("版本", CONFIG.APP_VERSION),
            ("技术栈", "YOLOv8 + PyTorch + OpenCV + PyQt5"),
            ("模型", f"YOLOv8-Nano ({os.path.getsize(CONFIG.MODEL_PATH)//1024//1024}MB)" if os.path.exists(CONFIG.MODEL_PATH) else "YOLOv8-Nano"),
            ("检测类别", "12 类生活垃圾"),
            ("运行模式", "CPU / CUDA"),
            ("mAP@50", "95.1%"),
            ("项目地址", "GitHub: Patience-creat/garbage-project"),
        ]

        for label, value in info_items:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)
            row_layout.setSpacing(12)

            lbl = QLabel(label)
            lbl.setFixedWidth(80)
            lbl_font = QFont("Microsoft YaHei UI", 11)
            lbl.setFont(lbl_font)
            lbl.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent;")

            val = QLabel(value)
            val_font = QFont("Microsoft YaHei UI", 11)
            val.setFont(val_font)
            val.setStyleSheet("color: white; background: transparent;")
            val.setWordWrap(True)

            row_layout.addWidget(lbl)
            row_layout.addWidget(val, 1)
            layout.addWidget(row)

        layout.addStretch()

        # 关闭按钮
        btn_close = QPushButton("知道了")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedHeight(38)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {Color.PRIMARY};
                color: white;
                border: none;
                border-radius: {Radius.MD}px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {Color.PRIMARY_HOVER};
            }}
        """)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def _center_on_parent(self, parent):
        if parent:
            center = parent.frameGeometry().center()
            self.move(center.x() - self.width() // 2,
                      center.y() - self.height() // 2)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
