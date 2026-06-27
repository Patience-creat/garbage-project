"""
历史回看 & 专家评审模式 — 为睿抗AI视觉大赛设计
"""
import os
import json
import cv2
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QScrollArea, QDialog, QSizePolicy, QProgressBar, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QImage, QPainter, QColor, QPen, QPainterPath

from .theme import Color, Radius
from .config import CONFIG
from .logger import logger


# ═══════════════════════════════════════════════════════
# 1. 历史回看页面
# ═══════════════════════════════════════════════════════
class HistoryReviewPage(QWidget):
    """历史回看 — 缩略图网格展示最近 20 张检测图片"""

    navigate_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyReviewPage")
        self._meta = []          # images_meta.json 内容
        self._thumbnails = []    # 缩略图卡片列表
        # 选择删除模式
        self._selection_mode = False
        self._selected_indices = set()
        self._selection_buttons = []  # 选择模式下覆盖的 checkbox 控件
        self._setup_ui()
        self.refresh()

    def showEvent(self, event):
        """切换到该页面时自动刷新"""
        super().showEvent(event)
        QTimer.singleShot(100, self.refresh)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 顶部工具栏 ──
        toolbar = QWidget()
        toolbar.setObjectName("reviewToolbar")
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(f"""
            #reviewToolbar {{
                background: {Color.BG_SURFACE};
                border-bottom: 1px solid {Color.BORDER};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("📸 历史回看")
        title_font = QFont("Microsoft YaHei UI", 15, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: white; background: transparent;")
        toolbar_layout.addWidget(title)
        toolbar_layout.addStretch()

        # ── 选择删除按钮（切换模式） ──
        self.btn_select = QPushButton("☑️ 选择删除")
        self.btn_select.setToolTip("进入选择模式，勾选需要删除的图片")
        self.btn_select.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #f59e0b;
                border: 1px solid rgba(245,158,11,0.4);
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(245,158,11,0.15);
                border-color: #f59e0b;
            }
        """)
        self.btn_select.clicked.connect(self._toggle_selection_mode)
        toolbar_layout.addWidget(self.btn_select)
        self.btn_select.hide()  # 加载前隐藏

        # ── 删除选中按钮（选择模式下显示） ──
        self.btn_delete_selected = QPushButton("🗑️ 删除选中 (0)")
        self.btn_delete_selected.setToolTip("删除已勾选的图片")
        self.btn_delete_selected.setStyleSheet("""
            QPushButton {
                background: rgba(239,68,68,0.2);
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239,68,68,0.35);
            }
            QPushButton:disabled {
                background: transparent;
                color: #475569;
                border-color: #2a2a50;
            }
        """)
        self.btn_delete_selected.clicked.connect(self._delete_selected)
        toolbar_layout.addWidget(self.btn_delete_selected)
        self.btn_delete_selected.hide()

        # ── 取消选择（选择模式下显示） ──
        self.btn_cancel_select = QPushButton("✕ 取消选择")
        self.btn_cancel_select.setToolTip("退出选择模式")
        self.btn_cancel_select.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: 1px solid #2a2a50;
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(148,163,184,0.15);
                border-color: #94a3b8;
            }
        """)
        self.btn_cancel_select.clicked.connect(self._exit_selection_mode)
        toolbar_layout.addWidget(self.btn_cancel_select)
        self.btn_cancel_select.hide()

        # ── 清空全部 ──
        self.btn_clear_all = QPushButton("🗑️ 清空全部")
        self.btn_clear_all.setToolTip("删除所有存档图片（不可恢复）")
        self.btn_clear_all.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ef4444;
                border: 1px solid rgba(239,68,68,0.3);
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239,68,68,0.15);
                border-color: #ef4444;
            }
        """)
        self.btn_clear_all.clicked.connect(self._clear_all)
        toolbar_layout.addWidget(self.btn_clear_all)

        # ── 刷新 ──
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.setToolTip("重新加载存档图片")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #a5b4fc;
                border: 1px solid #6366f1;
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(99,102,241,0.15);
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh)
        toolbar_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(toolbar)

        # ── 缩略图网格（滚动区域） ──
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
        self._grid_layout = QGridLayout(scroll_content)
        self._grid_layout.setContentsMargins(24, 20, 24, 20)
        self._grid_layout.setSpacing(16)
        self._grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

    def refresh(self):
        """从磁盘重新加载存档元数据并重建缩略图网格"""
        # 退出选择模式（如果有）
        self._exit_selection_mode()

        # 清空现有缩略图
        for card in self._thumbnails:
            self._grid_layout.removeWidget(card)
            card.deleteLater()
        self._thumbnails.clear()

        # 加载元数据
        self._meta = self._load_meta()
        if not self._meta:
            self._show_empty_state()
            self.btn_select.hide()
            return

        # 显示选择删除按钮
        self.btn_select.show()

        # 最多显示 20 张
        entries = self._meta[:20]
        cols = 4
        for idx, entry in enumerate(entries):
            card = self._create_thumbnail_card(entry, idx)
            row = idx // cols
            col = idx % cols
            self._grid_layout.addWidget(card, row, col)
            self._thumbnails.append(card)

    def _load_meta(self):
        """加载 images_meta.json"""
        meta_file = os.path.join(CONFIG.RECORDS_DIR, "images_meta.json")
        if not os.path.exists(meta_file):
            return []
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"加载 images_meta.json 失败: {e}")
            return []

    def _show_empty_state(self):
        empty = QLabel("📭 暂无检测图片存档\n进行检测后，标注图片会自动保存到这里")
        empty_font = QFont("Microsoft YaHei UI", 14)
        empty.setFont(empty_font)
        empty.setAlignment(Qt.AlignCenter)
        empty.setMinimumHeight(300)
        empty.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent;")
        self._grid_layout.addWidget(empty, 0, 0, 1, 4)
        self._thumbnails.append(empty)

    def _create_thumbnail_card(self, entry, index=0):
        """创建单个缩略图卡片（含选择模式支持）"""
        card = QFrame()
        card.setObjectName("thumbCard")
        card.setFixedSize(220, 180)
        card.setCursor(Qt.PointingHandCursor)
        is_selected = index in self._selected_indices
        border_color = Color.PRIMARY if is_selected else Color.BORDER
        card.setStyleSheet(f"""
            #thumbCard {{
                background: {Color.BG_CARD};
                border: 2px solid {border_color};
                border-radius: {Radius.LG}px;
            }}
            #thumbCard:hover {{
                background: {Color.BG_CARD_HOVER};
                border-color: {Color.PRIMARY};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 缩略图
        img_path = os.path.join(CONFIG.IMAGES_ARCHIVE_DIR, entry["filename"])
        pixmap = None
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(220, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setPixmap(scaled)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setMinimumHeight(140)
            img_label.setStyleSheet("background: transparent;")
        else:
            img_label = QLabel("⚠ 图片缺失")
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setFixedHeight(140)
            img_label.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: {Color.BG_DARK};")
        layout.addWidget(img_label, 1)

        # 底部信息条
        info_bar = QWidget()
        info_bar.setFixedHeight(40)
        info_bar.setStyleSheet(f"""
            background: rgba(10,10,22,0.85);
            border-bottom-left-radius: {Radius.LG}px;
            border-bottom-right-radius: {Radius.LG}px;
        """)
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(10, 0, 10, 0)
        info_layout.setSpacing(4)

        count_badge = QLabel(f"  {entry['total']} 项  ")
        count_badge.setStyleSheet(f"""
            background: {Color.PRIMARY};
            color: white;
            border-radius: 8px;
            padding: 1px 6px;
            font-size: 10px;
            font-weight: bold;
        """)

        cats = entry.get("categories", [])
        cats_text = ", ".join(
            Color.CLASS_NAMES_CN.get(c, c) for c in cats[:3]
        )
        if len(cats) > 3:
            cats_text += f" +{len(cats)-3}"
        cat_label = QLabel(cats_text)
        cat_label.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent; font-size: 10px;")

        info_layout.addWidget(count_badge)
        info_layout.addWidget(cat_label, 1)
        layout.addWidget(info_bar)

        # 选择模式下：在信息栏添加选中标记 + 点击切换选择
        if self._selection_mode:
            if is_selected:
                sel_label = QLabel("✅ 已选")
                sel_label.setStyleSheet(f"color: {Color.SUCCESS}; background: transparent; font-size: 10px; font-weight: bold;")
                info_layout.addWidget(sel_label)
            card.mousePressEvent = lambda e, i=index: self._toggle_select(i)
        else:
            entry_data = entry
            card.mousePressEvent = lambda e, d=entry_data: self._show_full_image(d)

        return card

    def _rebuild_grid(self):
        """从当前 self._meta 重建缩略图网格（不重新加载磁盘）"""
        # 清空现有缩略图
        for card in self._thumbnails:
            self._grid_layout.removeWidget(card)
            card.deleteLater()
        self._thumbnails.clear()

        if not self._meta:
            self._show_empty_state()
            self.btn_select.hide()
            return

        entries = self._meta[:20]
        cols = 4
        for idx, entry in enumerate(entries):
            card = self._create_thumbnail_card(entry, idx)
            row = idx // cols
            col = idx % cols
            self._grid_layout.addWidget(card, row, col)
            self._thumbnails.append(card)

    # ── 选择删除模式 ──

    def _toggle_selection_mode(self):
        """切换选择模式"""
        self._selection_mode = not self._selection_mode
        if not self._selection_mode:
            self._selected_indices.clear()
            self.btn_delete_selected.hide()
            self.btn_cancel_select.hide()
        else:
            self.btn_delete_selected.show()
            self.btn_cancel_select.show()
            self._update_delete_btn()
        self.btn_select.setText("☑️ 取消选择" if self._selection_mode else "☑️ 选择删除")
        self._rebuild_grid()

    def _exit_selection_mode(self):
        """退出选择模式"""
        if self._selection_mode:
            self._selection_mode = False
            self._selected_indices.clear()
            self.btn_select.setText("☑️ 选择删除")
            self.btn_delete_selected.hide()
            self.btn_cancel_select.hide()
            self._rebuild_grid()

    def _toggle_select(self, index):
        """切换某个缩略图的选中状态"""
        if index in self._selected_indices:
            self._selected_indices.discard(index)
        else:
            self._selected_indices.add(index)
        self._update_delete_btn()
        self._rebuild_grid()

    def _update_delete_btn(self):
        """更新删除选中按钮的文字和启用状态"""
        count = len(self._selected_indices)
        self.btn_delete_selected.setText(f"🗑️ 删除选中 ({count})")
        self.btn_delete_selected.setEnabled(count > 0)

    def _delete_selected(self):
        """删除选中的图片"""
        if not self._selected_indices:
            return

        count = len(self._selected_indices)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {count} 张图片吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 从后往前删除，避免索引偏移
        archive_dir = CONFIG.IMAGES_ARCHIVE_DIR
        for idx in sorted(self._selected_indices, reverse=True):
            if idx < len(self._meta):
                entry = self._meta.pop(idx)
                img_path = os.path.join(archive_dir, entry["filename"])
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception as e:
                        logger.warning(f"删除图片失败: {img_path} - {e}")

        # 保存更新后的元数据
        self._save_meta_to_disk()
        self._exit_selection_mode()
        logger.info(f"已删除 {count} 张存档图片")

    def _clear_all(self):
        """清空全部存档图片"""
        if not self._meta:
            return
        reply = QMessageBox.question(
            self, "确认清空",
            f"确定要清空全部 {len(self._meta)} 张存档图片吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 删除所有图片文件
        archive_dir = CONFIG.IMAGES_ARCHIVE_DIR
        for entry in self._meta:
            img_path = os.path.join(archive_dir, entry["filename"])
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception as e:
                    logger.warning(f"删除图片失败: {img_path} - {e}")

        self._meta.clear()
        self._save_meta_to_disk()
        self._exit_selection_mode()
        self._rebuild_grid()
        logger.info("已清空全部存档图片")

    def _save_meta_to_disk(self):
        """将当前元数据写入磁盘"""
        meta_file = os.path.join(CONFIG.RECORDS_DIR, "images_meta.json")
        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(self._meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")

    def _show_full_image(self, entry):
        """弹出大图查看对话框"""
        dlg = QDialog(self)
        dlg.setWindowTitle("检测图片详情")
        dlg.setFixedSize(800, 620)
        dlg.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        dlg.setModal(True)
        dlg.setStyleSheet(f"""
            QDialog {{
                background: {Color.BG_SURFACE};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 大图
        img_path = os.path.join(CONFIG.IMAGES_ARCHIVE_DIR, entry["filename"])
        pixmap = QPixmap(img_path) if os.path.exists(img_path) else QPixmap()
        img_label = QLabel()
        if not pixmap.isNull():
            scaled = pixmap.scaled(760, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label.setPixmap(scaled)
        else:
            img_label.setText("⚠ 图片文件缺失")
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setMinimumHeight(400)
        img_label.setStyleSheet(f"""
            background: {Color.BG_DARK};
            border: 1px solid {Color.BORDER};
            border-radius: {Radius.MD}px;
        """)
        layout.addWidget(img_label)

        # 检测详情
        detail = QFrame()
        detail.setStyleSheet(f"""
            background: {Color.BG_CARD};
            border: 1px solid {Color.BORDER};
            border-radius: {Radius.MD}px;
        """)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(16, 12, 16, 12)
        detail_layout.setSpacing(4)

        time_label = QLabel(f"🕐 {entry['timestamp']}")
        time_label.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent; font-size: 12px;")
        detail_layout.addWidget(time_label)

        for cls_name, conf in entry["detections"]:
            cn = Color.CLASS_NAMES_CN.get(cls_name, cls_name)
            icon = Color.CLASS_ICONS.get(cls_name, "📦")
            conf_pct = conf * 100
            conf_color = Color.SUCCESS if conf > 0.7 else Color.WARNING if conf > 0.4 else Color.ERROR
            row = QLabel(f"{icon} {cn} ({cls_name})  —  <b style='color:{conf_color}'>{conf_pct:.1f}%</b>")
            row.setStyleSheet(f"color: {Color.TEXT_PRIMARY}; background: transparent; font-size: 12px;")
            detail_layout.addWidget(row)

        layout.addWidget(detail)

        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {Color.PRIMARY};
                color: white;
                border: none;
                border-radius: {Radius.MD}px;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {Color.PRIMARY_HOVER};
            }}
        """)
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close)

        dlg.exec_()

    def save_meta(self):
        """供关闭时调用，无须额外操作（元数据已有存档）"""
        pass


# ═══════════════════════════════════════════════════════
# 2. 专家评审模式页面
# ═══════════════════════════════════════════════════════
class ExpertReviewPage(QWidget):
    """专家评审模式 — 逐张判定检测结果对/错，自动汇总得分"""

    review_completed = pyqtSignal(int, int)  # (得分, 总分)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("expertReviewPage")

        # 评审状态
        self._images = []         # 待评审图片元数据列表
        self._current_idx = 0     # 当前图片索引
        self._results = []        # 评审结果: [(entry, True/False/None)]
        self._is_completed = False

        self._setup_ui()
        self._show_idle_state()

    def showEvent(self, event):
        """切换到该页面时刷新数据"""
        super().showEvent(event)
        if not self._is_completed and not self._images:
            QTimer.singleShot(100, self._start_review)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 顶部工具栏 ──
        toolbar = QWidget()
        toolbar.setObjectName("expertToolbar")
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(f"""
            #expertToolbar {{
                background: {Color.BG_SURFACE};
                border-bottom: 1px solid {Color.BORDER};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("🏆 专家评审模式")
        title_font = QFont("Microsoft YaHei UI", 15, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: white; background: transparent;")
        toolbar_layout.addWidget(title)
        toolbar_layout.addStretch()

        self.btn_start = QPushButton("▶ 开始评审")
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background: {Color.GRADIENT_PRIMARY};
                color: white;
                border: none;
                border-radius: {Radius.MD}px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {Color.PRIMARY_HOVER};
            }}
        """)
        self.btn_start.clicked.connect(self._start_review)
        toolbar_layout.addWidget(self.btn_start)

        main_layout.addWidget(toolbar)

        # ── 主体 ──
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 16, 24, 24)
        content_layout.setSpacing(16)

        # 进度 & 得分栏
        self._setup_score_bar(content_layout)

        # 图片预览区
        self._setup_preview_area(content_layout)

        # 判定按钮区
        self._setup_action_buttons(content_layout)

        main_layout.addWidget(content, 1)

    def _setup_score_bar(self, parent_layout):
        """顶部进度 + 得分"""
        score_bar = QFrame()
        score_bar.setFixedHeight(56)
        score_bar.setStyleSheet(f"""
            background: {Color.BG_CARD};
            border: 1px solid {Color.BORDER};
            border-radius: {Radius.LG}px;
        """)
        score_layout = QHBoxLayout(score_bar)
        score_layout.setContentsMargins(20, 0, 20, 0)
        score_layout.setSpacing(16)

        # 进度文字（含图片序号）
        self.progress_label = QLabel("进度: 0 / 0")
        self.progress_label.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent; font-size: 13px;")
        score_layout.addWidget(self.progress_label)

        # 图片序号（第 N/20 张）
        self.image_counter = QLabel("")
        self.image_counter.setStyleSheet(f"color: {Color.PRIMARY_LIGHT}; background: transparent; font-size: 13px; font-weight: bold;")
        score_layout.addWidget(self.image_counter)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {Color.BG_SURFACE};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {Color.GRADIENT_PRIMARY};
                border-radius: 4px;
            }}
        """)
        score_layout.addWidget(self.progress_bar)

        # 得分
        self.score_label = QLabel("得分: --")
        score_font = QFont("Microsoft YaHei UI", 14, QFont.Bold)
        self.score_label.setFont(score_font)
        self.score_label.setStyleSheet(f"color: {Color.TEXT_PRIMARY}; background: transparent;")
        score_layout.addWidget(self.score_label)

        score_layout.addStretch()

        # 正确/错误计数
        self.correct_label = QLabel("✅ 正确: 0")
        self.correct_label.setStyleSheet(f"color: {Color.SUCCESS}; background: transparent; font-size: 13px;")
        score_layout.addWidget(self.correct_label)

        self.wrong_label = QLabel("❌ 错误: 0")
        self.wrong_label.setStyleSheet(f"color: {Color.ERROR}; background: transparent; font-size: 13px;")
        score_layout.addWidget(self.wrong_label)

        parent_layout.addWidget(score_bar)

    def _setup_preview_area(self, parent_layout):
        """图片预览区域"""
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            background: {Color.BG_DARK};
            border: 1px solid {Color.BORDER};
            border-radius: {Radius.LG}px;
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 12, 12, 12)

        self.preview_label = QLabel("点击上方「开始评审」加载最近 20 张检测图片")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(600, 400)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent; font-size: 14px;")

        preview_layout.addWidget(self.preview_label, 1)

        # 图片信息栏（叠加在预览区底部）
        self.info_bar = QWidget()
        self.info_bar.setFixedHeight(40)
        self.info_bar.setStyleSheet(f"""
            background: rgba(10,10,22,0.85);
            border-radius: {Radius.MD}px;
        """)
        self.info_bar_layout = QHBoxLayout(self.info_bar)
        self.info_bar_layout.setContentsMargins(14, 0, 14, 0)
        self.info_bar_layout.setSpacing(8)
        self.info_time = QLabel("")
        self.info_time.setStyleSheet(f"color: {Color.TEXT_MUTED}; background: transparent; font-size: 11px;")
        self.info_cats = QLabel("")
        self.info_cats.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; background: transparent; font-size: 11px;")
        self.info_bar_layout.addWidget(self.info_time)
        self.info_bar_layout.addWidget(self.info_cats, 1)
        self.info_bar.hide()

        # 用覆盖层实现：预览区底部叠 info_bar
        preview_layout.addWidget(self.info_bar)

        parent_layout.addWidget(preview_frame, 1)

    def _setup_action_buttons(self, parent_layout):
        """判定操作按钮区"""
        btn_frame = QFrame()
        btn_frame.setFixedHeight(64)
        btn_frame.setStyleSheet(f"""
            background: {Color.BG_CARD};
            border: 1px solid {Color.BORDER};
            border-radius: {Radius.LG}px;
        """)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(24, 0, 24, 0)
        btn_layout.setSpacing(16)

        # ✅ 正确
        self.btn_correct = QPushButton("✅  正确")
        self.btn_correct.setFixedHeight(42)
        self.btn_correct.setStyleSheet(f"""
            QPushButton {{
                background: rgba(16,185,129,0.2);
                color: {Color.SUCCESS};
                border: 1px solid {Color.SUCCESS};
                border-radius: {Radius.MD}px;
                padding: 0 28px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(16,185,129,0.35);
            }}
            QPushButton:pressed {{
                background: rgba(16,185,129,0.5);
            }}
            QPushButton:disabled {{
                background: rgba(16,185,129,0.05);
                color: {Color.TEXT_MUTED};
                border-color: {Color.BORDER};
            }}
        """)
        self.btn_correct.clicked.connect(self._mark_correct)

        # ❌ 错误
        self.btn_wrong = QPushButton("❌  错误")
        self.btn_wrong.setFixedHeight(42)
        self.btn_wrong.setStyleSheet(f"""
            QPushButton {{
                background: rgba(239,68,68,0.2);
                color: {Color.ERROR};
                border: 1px solid {Color.ERROR};
                border-radius: {Radius.MD}px;
                padding: 0 28px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(239,68,68,0.35);
            }}
            QPushButton:pressed {{
                background: rgba(239,68,68,0.5);
            }}
            QPushButton:disabled {{
                background: rgba(239,68,68,0.05);
                color: {Color.TEXT_MUTED};
                border-color: {Color.BORDER};
            }}
        """)
        self.btn_wrong.clicked.connect(self._mark_wrong)

        # ⏭️ 跳过 / 重新评审
        self.btn_skip = QPushButton("⏭️ 跳过")
        self.btn_skip.setFixedHeight(42)
        self.btn_skip.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Color.TEXT_SECONDARY};
                border: 1px solid {Color.BORDER};
                border-radius: {Radius.MD}px;
                padding: 0 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {Color.BG_CARD_HOVER};
                border-color: {Color.TEXT_MUTED};
            }}
            QPushButton:disabled {{
                color: {Color.TEXT_MUTED};
                border-color: {Color.BORDER};
                background: transparent;
            }}
        """)
        self.btn_skip.clicked.connect(self._skip_image)

        # 中间弹簧
        btn_layout.addWidget(self.btn_correct)
        btn_layout.addWidget(self.btn_wrong)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_skip)

        parent_layout.addWidget(btn_frame)

    # ── 状态管理 ──

    def _show_idle_state(self):
        """显示等待开始状态"""
        self.preview_label.setText("点击上方「开始评审」加载最近 20 张检测图片")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.info_bar.hide()
        self.btn_correct.setEnabled(False)
        self.btn_wrong.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.btn_start.setText("▶ 开始评审")
        self.progress_label.setText("进度: 0 / 0")
        self.image_counter.setText("")
        self.score_label.setText("得分: --")
        self.correct_label.setText("✅ 正确: 0")
        self.wrong_label.setText("❌ 错误: 0")
        self.progress_bar.setValue(0)

    def _start_review(self):
        """开始新一轮评审"""
        # 加载最近 20 张图片
        meta_file = os.path.join(CONFIG.RECORDS_DIR, "images_meta.json")
        if not os.path.exists(meta_file):
            QMessageBox.information(self, "提示", "暂无检测图片，请先进行检测")
            return

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                all_meta = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载存档失败: {e}")
            return

        if not all_meta:
            QMessageBox.information(self, "提示", "暂无检测图片可评审")
            return

        self._images = all_meta[:20]
        self._current_idx = 0
        self._results = [(img, None) for img in self._images]  # None = 未判定
        self._is_completed = False

        self.btn_start.setText("🔄 重新评审")
        self.btn_correct.setEnabled(True)
        self.btn_wrong.setEnabled(True)
        self.btn_skip.setEnabled(True)

        self._update_score_display()
        self._show_current_image()

    def _show_current_image(self):
        """显示当前待评审图片"""
        if self._current_idx >= len(self._images):
            self._finish_review()
            return

        entry = self._images[self._current_idx]
        img_path = os.path.join(CONFIG.IMAGES_ARCHIVE_DIR, entry["filename"])

        pixmap = QPixmap(img_path) if os.path.exists(img_path) else QPixmap()
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.preview_label.setPixmap(scaled)
        else:
            self.preview_label.setText(f"⚠ 图片缺失: {entry['filename']}")
            self.preview_label.setAlignment(Qt.AlignCenter)

        # 图片序号
        total = len(self._images)
        self.image_counter.setText(f"第 {self._current_idx + 1}/{total} 张")

        # 更新信息栏：显示所有检测详情
        det_texts = []
        for cls_name, conf in entry["detections"]:
            cn = Color.CLASS_NAMES_CN.get(cls_name, cls_name)
            icon = Color.CLASS_ICONS.get(cls_name, "📦")
            conf_pct = conf * 100 if conf < 1 else conf
            det_texts.append(f"{icon}{cn}({conf_pct:.0f}%)")
        det_str = "  ".join(det_texts)

        self.info_time.setText(f"🕐 {entry['timestamp']}")
        self.info_cats.setText(f"{det_str}")
        self.info_bar.show()

        # 如果这张已经判定过，显示判定结果
        if self._current_idx < len(self._results):
            _, verdict = self._results[self._current_idx]
            if verdict is True:
                self.preview_label.setStyleSheet(f"""
                    background: {Color.BG_DARK};
                    border: 3px solid {Color.SUCCESS};
                    border-radius: {Radius.MD}px;
                    color: {Color.TEXT_MUTED};
                    font-size: 14px;
                """)
            elif verdict is False:
                self.preview_label.setStyleSheet(f"""
                    background: {Color.BG_DARK};
                    border: 3px solid {Color.ERROR};
                    border-radius: {Radius.MD}px;
                    color: {Color.TEXT_MUTED};
                    font-size: 14px;
                """)
            else:
                self.preview_label.setStyleSheet(f"""
                    background: {Color.BG_DARK};
                    border: 1px solid {Color.BORDER};
                    border-radius: {Radius.MD}px;
                    color: {Color.TEXT_MUTED};
                    font-size: 14px;
                """)

        self._update_score_display()

    def _mark_correct(self):
        """标记当前图片为正确"""
        if self._current_idx < len(self._results):
            self._results[self._current_idx] = (self._images[self._current_idx], True)
        self._next_image()

    def _mark_wrong(self):
        """标记当前图片为错误"""
        if self._current_idx < len(self._results):
            self._results[self._current_idx] = (self._images[self._current_idx], False)
        self._next_image()

    def _skip_image(self):
        """跳过当前图片（留空不判定）"""
        self._next_image()

    def _next_image(self):
        """切换到下一张"""
        self._current_idx += 1
        if self._current_idx >= len(self._images):
            self._finish_review()
        else:
            self._show_current_image()

    def _update_score_display(self):
        """更新进度条和得分显示"""
        total = len(self._images)
        judged = sum(1 for _, v in self._results if v is not None)
        correct = sum(1 for _, v in self._results if v is True)
        wrong = sum(1 for _, v in self._results if v is False)

        self.progress_label.setText(f"进度: {judged}/{total}")
        self.correct_label.setText(f"✅ 正确: {correct}")
        self.wrong_label.setText(f"❌ 错误: {wrong}")

        if judged > 0:
            pct = int(judged / total * 100)
            self.progress_bar.setValue(pct)
            self.score_label.setText(f"得分: {correct}/{judged}  ({correct * 100 // max(judged, 1)}%)")
        else:
            self.progress_bar.setValue(0)
            self.score_label.setText("得分: --")

    def _finish_review(self):
        """评审完成，显示结果"""
        self._is_completed = True
        self.btn_correct.setEnabled(False)
        self.btn_wrong.setEnabled(False)
        self.btn_skip.setEnabled(False)

        total = len(self._images)
        correct = sum(1 for _, v in self._results if v is True)
        wrong = sum(1 for _, v in self._results if v is False)
        skipped = sum(1 for _, v in self._results if v is None)
        score = correct
        max_score = total - skipped  # 跳过的不计入总分
        pct = (score / max_score * 100) if max_score > 0 else 0

        self.progress_bar.setValue(100)
        self.score_label.setText(f"最终得分: {score} / {max_score}  ({pct:.0f}%)")

        # 保存结果
        self._save_results()

        # 显示结果对话框
        self._show_result_dialog(score, max_score, correct, wrong, skipped)

    def _show_result_dialog(self, score, max_score, correct, wrong, skipped):
        """显示评审结果弹窗"""
        pct = (score / max_score * 100) if max_score > 0 else 0
        passed = pct >= 60  # 60% 及格线

        msg = QMessageBox(self)
        msg.setWindowTitle("评审完成")
        msg.setStyleSheet(f"""
            QMessageBox {{
                background: {Color.BG_SURFACE};
            }}
            QMessageBox QLabel {{
                color: {Color.TEXT_PRIMARY};
                font-size: 14px;
                padding: 10px;
            }}
        """)

        icon = "🏆" if passed else "📋"
        result_text = (
            f"{icon} 评审完成！\n\n"
            f"📊 总览\n"
            f"  待评审图片: {max_score + skipped} 张\n"
            f"  已评审: {correct + wrong} 张\n"
            f"  跳过: {skipped} 张\n\n"
            f"✅ 正确: {correct}\n"
            f"❌ 错误: {wrong}\n"
            f"🎯 最终得分: {score} / {max_score}  ({pct:.0f}%)\n\n"
            f"{'🎉 恭喜通过评审！' if passed else '💪 还需继续努力！'}"
        )
        msg.setText(result_text)
        msg.setStandardButtons(QMessageBox.Ok)

        # 自定义按钮文字
        ok_btn = msg.button(QMessageBox.Ok)
        ok_btn.setText("知道了")
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Color.PRIMARY};
                color: white;
                border: none;
                border-radius: {Radius.MD}px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {Color.PRIMARY_HOVER};
            }}
        """)

        msg.exec_()

        # 发射信号
        self.review_completed.emit(score, max_score)

    def _save_results(self):
        """保存评审结果到 JSON 文件"""
        try:
            os.makedirs(os.path.dirname(CONFIG.REVIEW_RESULTS_FILE), exist_ok=True)
            records = []
            for entry, verdict in self._results:
                records.append({
                    "filename": entry["filename"],
                    "timestamp": entry["timestamp"],
                    "detections": entry["detections"],
                    "verdict": verdict,  # True=正确, False=错误, null=跳过
                })
            result = {
                "review_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_images": len(self._images),
                "correct": sum(1 for _, v in self._results if v is True),
                "wrong": sum(1 for _, v in self._results if v is False),
                "skipped": sum(1 for _, v in self._results if v is None),
                "records": records,
            }
            with open(CONFIG.REVIEW_RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"评审结果已保存 → {CONFIG.REVIEW_RESULTS_FILE}")
        except Exception as e:
            logger.error(f"保存评审结果失败: {e}")

    def resizeEvent(self, event):
        """窗口大小变化时重新缩放当前图片"""
        super().resizeEvent(event)
        if hasattr(self, '_current_idx') and self._current_idx < len(self._images):
            self._show_current_image()
