"""
主题系统 — 定义全局颜色、字体、样式表
"""
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QColor 
from PyQt5.QtCore import Qt


# ─── 颜色系统 ───────────────────────────────────────────
class Color:
    """设计系统调色板"""
    # 主色
    PRIMARY = "#6366f1"          # 靛蓝
    PRIMARY_HOVER = "#818cf8"
    PRIMARY_DARK = "#4f46e5"
    PRIMARY_LIGHT = "#a5b4fc"
    PRIMARY_GLOW = "rgba(99,102,241,0.3)"

    # 辅色
    SECONDARY = "#8b5cf6"        # 紫色
    SECONDARY_HOVER = "#a78bfa"
    ACCENT = "#06b6d4"           # 青色
    ACCENT_HOVER = "#22d3ee"

    # 背景
    BG_DARK = "#0a0a16"          # 最底层背景
    BG_SURFACE = "#111125"       # 表面背景
    BG_CARD = "#1a1a35"          # 卡片背景
    BG_CARD_HOVER = "#222248"    # 卡片悬停
    BG_ELEVATED = "#252550"      # 提升层

    # 文本
    TEXT_PRIMARY = "#f1f5f9"
    TEXT_SECONDARY = "#94a3b8"
    TEXT_MUTED = "#475569"
    TEXT_WHITE = "#ffffff"

    # 语义色
    SUCCESS = "#10b981"
    SUCCESS_BG = "rgba(16,185,129,0.15)"
    WARNING = "#f59e0b"
    WARNING_BG = "rgba(245,158,11,0.15)"
    ERROR = "#ef4444"
    ERROR_BG = "rgba(239,68,68,0.15)"
    INFO = "#3b82f6"
    INFO_BG = "rgba(59,130,246,0.15)"

    # 边框
    BORDER = "#2a2a50"
    BORDER_LIGHT = "#3a3a60"

    # 渐变
    GRADIENT_PRIMARY = ("qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                        "stop:0 #6366f1, stop:1 #8b5cf6)")
    GRADIENT_ACCENT = ("qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                       "stop:0 #06b6d4, stop:1 #3b82f6)")
    GRADIENT_SUCCESS = ("qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                        "stop:0 #10b981, stop:1 #059669)")
    GRADIENT_WARNING = ("qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                        "stop:0 #f59e0b, stop:1 #d97706)")

    # 阴影色
    SHADOW = QColor(0, 0, 0, 80)
    SHADOW_LARGE = QColor(0, 0, 0, 120)

    # 垃圾类别映射颜色
    CLASS_COLORS = {
        "battery": "#ef4444",
        "biological": "#10b981",
        "brown-glass": "#d97706",
        "cardboard": "#f59e0b",
        "clothes": "#8b5cf6",
        "green-glass": "#059669",
        "metal": "#64748b",
        "paper": "#3b82f6",
        "plastic": "#f97316",
        "shoes": "#a855f7",
        "trash": "#78716c",
        "white-glass": "#e2e8f0",
    }

    # 垃圾中文名映射
    CLASS_NAMES_CN = {
        "battery": "电池",
        "biological": "生物垃圾",
        "brown-glass": "棕色玻璃",
        "cardboard": "纸板",
        "clothes": "衣物",
        "green-glass": "绿色玻璃",
        "metal": "金属",
        "paper": "纸张",
        "plastic": "塑料",
        "shoes": "鞋子",
        "trash": "其他垃圾",
        "white-glass": "白色玻璃",
    }

    # 垃圾类别图标
    CLASS_ICONS = {
        "battery": "🔋",
        "biological": "🍂",
        "brown-glass": "🫙",
        "cardboard": "📦",
        "clothes": "👕",
        "green-glass": "🫙",
        "metal": "🔩",
        "paper": "📄",
        "plastic": "🧴",
        "shoes": "👟",
        "trash": "🗑️",
        "white-glass": "🥛",
    }


# ─── 字体系统 ───────────────────────────────────────────
class FontFamily:
    DEFAULT = "Microsoft YaHei UI, Microsoft YaHei, PingFang SC, sans-serif"
    MONO = "Consolas, Courier New, monospace"


def setup_fonts():
    """初始化字体设置"""
    font = QFont(FontFamily.DEFAULT)
    font.setPointSize(10)
    return font


# ─── 圆角尺寸 ──────────────────────────────────────────
class Radius:
    SM = 6
    MD = 10
    LG = 16
    XL = 20
    FULL = 999


# ─── 间距 ──────────────────────────────────────────────
class Spacing:
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32


# ─── 全局样式表 ─────────────────────────────────────────
GLOBAL_STYLESHEET = f"""
/* ── 全局 ── */
* {{
    font-family: {FontFamily.DEFAULT};
}}
QMainWindow {{
    background: transparent;
}}
QWidget {{
    background: transparent;
    color: {Color.TEXT_PRIMARY};
}}

/* ── 滚动条 ── */
QScrollBar:vertical {{
    background: {Color.BG_SURFACE};
    width: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {Color.BORDER_LIGHT};
    min-height: 30px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {Color.PRIMARY};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ── 通用按钮 ── */
QPushButton {{
    background: {Color.BG_CARD};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.MD}px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton:hover {{
    background: {Color.BG_CARD_HOVER};
    border-color: {Color.PRIMARY};
}}
QPushButton:pressed {{
    background: {Color.PRIMARY_DARK};
}}
QPushButton:disabled {{
    background: {Color.BG_CARD};
    color: {Color.TEXT_MUTED};
    border-color: {Color.BORDER};
}}

/* ── 下拉框 ── */
QComboBox {{
    background: {Color.BG_CARD};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.MD}px;
    padding: 8px 16px;
    font-size: 13px;
    min-width: 120px;
}}
QComboBox:hover {{
    border-color: {Color.PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 30px;
}}
QComboBox::down-arrow {{
    image: none;
    border: none;
}}
QComboBox QAbstractItemView {{
    background: {Color.BG_CARD};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.SM}px;
    selection-background-color: {Color.PRIMARY};
    selection-color: {Color.TEXT_WHITE};
    padding: 4px;
    outline: none;
}}

/* ── 进度条 ── */
QProgressBar {{
    background: {Color.BG_CARD};
    border: none;
    border-radius: {Radius.SM}px;
    height: 6px;
    text-align: center;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background: {Color.GRADIENT_PRIMARY};
    border-radius: {Radius.SM}px;
}}

/* ── 滑块 ── */
QSlider::groove:horizontal {{
    background: {Color.BG_CARD};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {Color.PRIMARY};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {Color.PRIMARY_HOVER};
}}

/* ── 文本编辑 ── */
QTextEdit, QPlainTextEdit {{
    background: {Color.BG_CARD};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.MD}px;
    padding: 12px;
    font-size: 13px;
    selection-background-color: {Color.PRIMARY};
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {Color.PRIMARY};
}}

/* ── 复选框 ── */
QCheckBox {{
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {Color.BORDER};
    background: transparent;
}}
QCheckBox::indicator:checked {{
    background: {Color.PRIMARY};
    border-color: {Color.PRIMARY};
}}

/* ── 输入框 ── */
QLineEdit {{
    background: {Color.BG_CARD};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.MD}px;
    padding: 8px 14px;
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {Color.PRIMARY};
}}

/* ── 提示框 Tooltip ── */
QToolTip {{
    background: {Color.BG_ELEVATED};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.SM}px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── 消息弹窗 ── */
QMessageBox {{
    background: {Color.BG_SURFACE};
}}
QMessageBox QLabel {{
    color: {Color.TEXT_PRIMARY};
    font-size: 13px;
}}
"""
