from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QDate, QPoint, QRect, QSize, Qt, QTime
from PySide6.QtGui import (
    QAction,
    QColor,
    QColorConstants,
    QFont,
    QIcon,
    QPainter,
    QPalette,
    QPixmap,
    QBrush,
    QTextCharFormat,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStatusBar,
    QTextBrowser,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .data_access import DataAccess
from .html_utils import html_contains_image, html_to_plain_text, prepare_html_for_display, scale_html_font_sizes
from .models import AppConfig, Memo
from .settings import AppSettings


FONT_SIZE_POINTS = {
    "小": 10,
    "中": 11,
    "大": 13,
    "特大": 15,
}


def get_scaled_point_size(font_size_mode: str, body_text_scale: float) -> float:
    return FONT_SIZE_POINTS.get(font_size_mode, 11) * body_text_scale


def set_translucent_scroll_surface(widget, alpha: int = 100) -> None:
    color = QColor(255, 255, 255, alpha)
    widget.setAutoFillBackground(False)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Base, color)
    palette.setColor(QPalette.ColorRole.Window, color)
    palette.setColor(QPalette.ColorRole.Text, QColor("#31405d"))
    widget.setPalette(palette)

    viewport = widget.viewport()
    viewport.setAutoFillBackground(True)
    viewport_palette = viewport.palette()
    viewport_palette.setColor(QPalette.ColorRole.Base, color)
    viewport_palette.setColor(QPalette.ColorRole.Window, color)
    viewport_palette.setColor(QPalette.ColorRole.Text, QColor("#31405d"))
    viewport.setPalette(viewport_palette)


def style_combo_popup(combo: QComboBox) -> None:
    combo.setStyleSheet(
        "QComboBox {"
        "color: #31405d;"
        "background: rgba(255, 255, 255, 188);"
        "selection-background-color: #eef4ff;"
        "selection-color: #22324f;"
        "}"
    )

    palette = combo.palette()
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#31405d"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#31405d"))
    combo.setPalette(palette)

    popup_view = QListView()
    popup_view.setObjectName("comboPopupView")
    popup_view.setStyleSheet(
        "QListView {"
        "background: #ffffff;"
        "color: #31405d;"
        "selection-background-color: #eef4ff;"
        "selection-color: #22324f;"
        "border: 1px solid #d8dceb;"
        "padding: 2px;"
        "outline: 0;"
        "}"
        "QListView::item {"
        "border: none;"
        "border-radius: 0px;"
        "margin: 0px;"
        "padding: 6px 10px;"
        "min-height: 20px;"
        "background: #ffffff;"
        "}"
        "QListView::item:selected {"
        "background: #eef4ff;"
        "color: #22324f;"
        "}"
    )
    popup_palette = popup_view.palette()
    popup_palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    popup_palette.setColor(QPalette.ColorRole.Text, QColor("#31405d"))
    popup_palette.setColor(QPalette.ColorRole.Highlight, QColor("#eef4ff"))
    popup_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#22324f"))
    popup_view.setPalette(popup_palette)
    popup_view.setUniformItemSizes(True)
    popup_view.setSpacing(0)
    combo.setView(popup_view)


def apply_combo_item_colors(combo: QComboBox) -> None:
    foreground = QColor("#31405d")
    background = QColor("#ffffff")
    for index in range(combo.count()):
        combo.setItemData(index, foreground, Qt.ItemDataRole.ForegroundRole)
        combo.setItemData(index, background, Qt.ItemDataRole.BackgroundRole)


def apply_font_to_widget_tree(root: QWidget, font: QFont) -> None:
    root.setFont(font)
    for widget in root.findChildren(QWidget):
        widget.setFont(font)


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 6):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self._items.append(item)

    def addWidget(self, widget: QWidget) -> None:
        super().addWidget(widget)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        max_width = rect.right()

        for item in self._items:
            next_x = x + item.sizeHint().width() + self.spacing()
            if next_x - self.spacing() > max_width and line_height > 0:
                x = rect.x()
                y = y + line_height + self.spacing()
                next_x = x + item.sizeHint().width() + self.spacing()
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class BackgroundSurface(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.background_label = QLabel(self)
        self.background_label.setScaledContents(True)
        self.background_label.lower()
        self.opacity_effect = QGraphicsOpacityEffect(self.background_label)
        self.background_label.setGraphicsEffect(self.opacity_effect)
        self.background_label.hide()

        self.foreground = QWidget(self)
        self.foreground.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self.foreground)

    def resizeEvent(self, event) -> None:
        self.background_label.setGeometry(self.rect())
        super().resizeEvent(event)

    def set_background(self, image_path: str, opacity_percent: int) -> None:
        if not image_path:
            self.background_label.hide()
            return

        candidate = Path(image_path)
        if not candidate.exists():
            self.background_label.hide()
            return

        pixmap = QPixmap(str(candidate))
        if pixmap.isNull():
            self.background_label.hide()
            return

        self.background_label.setPixmap(pixmap)
        self.opacity_effect.setOpacity(max(0.0, min(1.0, opacity_percent / 100.0)))
        self.background_label.show()


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None, db: DataAccess, config: AppConfig):
        super().__init__(parent)
        self.db = db
        self._config = AppConfig(**config.__dict__)
        self.setWindowTitle("設定")
        self.setWindowIcon(self._load_icon("techou.png"))
        self.resize(860, 560)
        self._build_ui()
        self._apply_config()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("文字の大きさ :"))
        self.font_size_combo = QComboBox()
        style_combo_popup(self.font_size_combo)
        self.font_size_combo.addItems(["小", "中", "大", "特大"])
        apply_combo_item_colors(self.font_size_combo)
        top_row.addWidget(self.font_size_combo)
        top_row.addSpacing(20)
        top_row.addWidget(QLabel("日記のタイトル"))
        self.title_edit = QLineEdit()
        top_row.addWidget(self.title_edit, 1)

        ok_button = QPushButton()
        ok_button.setIcon(self._load_icon("fruit_slice10_orange.png"))
        ok_button.setIconSize(QSize(44, 44))
        ok_button.setFixedSize(58, 58)
        ok_button.setToolTip("保存")
        ok_button.clicked.connect(self.accept)
        top_row.addWidget(ok_button)

        cancel_button = QPushButton()
        cancel_button.setIcon(self._load_icon("mark_ng.png"))
        cancel_button.setIconSize(QSize(44, 44))
        cancel_button.setFixedSize(58, 58)
        cancel_button.setToolTip("キャンセル")
        cancel_button.clicked.connect(self.reject)
        top_row.addWidget(cancel_button)

        root.addLayout(top_row)

        body_scale_row = QHBoxLayout()
        body_scale_row.addWidget(QLabel("本文表示倍率 :"))
        self.body_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.body_scale_slider.setRange(90, 300)
        self.body_scale_slider.setSingleStep(5)
        self.body_scale_slider.setPageStep(10)
        self.body_scale_slider.setTickInterval(10)
        self.body_scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.body_scale_value_label = QLabel("1.00")
        self.body_scale_slider.valueChanged.connect(self._on_body_scale_changed)
        body_scale_row.addWidget(self.body_scale_slider, 1)
        body_scale_row.addWidget(self.body_scale_value_label)
        root.addLayout(body_scale_row)

        previews_row = QHBoxLayout()
        previews_row.setSpacing(18)
        previews_row.addWidget(self._create_preview_frame("ホーム画面プレビュー", "home"), 1)
        previews_row.addWidget(self._create_preview_frame("編集画面プレビュー", "editor"), 1)
        root.addLayout(previews_row, 1)

        sliders_row = QHBoxLayout()
        sliders_row.setSpacing(30)
        sliders_row.addLayout(self._create_background_group("ホーム画面背景", "home"))
        sliders_row.addLayout(self._create_background_group("編集画面背景", "editor"))
        root.addLayout(sliders_row)

        bottom_row = QHBoxLayout()
        settings_file_path = ""
        parent_settings = getattr(self.parent(), "settings", None)
        if parent_settings is not None:
            settings_file_path = str(parent_settings.settings_file_path)

        path_labels = QVBoxLayout()
        path_labels.setContentsMargins(0, 0, 0, 0)
        path_labels.setSpacing(4)

        self.db_label = QLabel(f"データファイル :   {self.db.db_path}")
        self.settings_path_label = QLabel(f"設定ファイル :   {settings_file_path}")
        self.settings_path_label.setWordWrap(True)

        path_labels.addWidget(self.db_label)
        path_labels.addWidget(self.settings_path_label)
        bottom_row.addLayout(path_labels, 1)
        root.addLayout(bottom_row)

    def _create_preview_frame(self, title: str, prefix: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("settingsPreviewCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("settingsPreviewTitle")
        layout.addWidget(title_label)

        surface = BackgroundSurface(frame)
        surface.setMinimumHeight(230)
        layout.addWidget(surface, 1)

        overlay = QVBoxLayout(surface.foreground)
        overlay.setContentsMargins(14, 14, 14, 14)
        overlay.setSpacing(10)

        sample_card = QFrame()
        sample_card.setObjectName("previewGlassCard")
        sample_layout = QVBoxLayout(sample_card)
        sample_layout.setContentsMargins(12, 12, 12, 12)
        sample_layout.setSpacing(6)
        sample_title = QLabel("タイトル: 天気 晴れ")
        sample_title.setObjectName("previewSampleTitle")
        sample_layout.addWidget(sample_title)
        sample_layout.addWidget(QLabel("日付: 2026年5月4日(Mon)"))
        sample_layout.addWidget(QLabel("本文プレビューがここに入ります。"))
        overlay.addWidget(sample_card)
        overlay.addStretch(1)

        setattr(self, f"{prefix}_preview", surface)
        return frame

    def _create_background_group(self, title: str, prefix: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.addWidget(QLabel(title))

        path_label = QLabel("")
        path_label.setWordWrap(True)
        path_label.setMinimumHeight(44)
        setattr(self, f"{prefix}_path_label", path_label)
        layout.addWidget(path_label)

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("背景濃度"))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setTickInterval(10)
        slider.setSingleStep(5)
        value_label = QLabel("0")
        slider.valueChanged.connect(lambda value, label=value_label: label.setText(str(value)))
        slider.valueChanged.connect(lambda _value, p=prefix: self._refresh_preview(p))
        setattr(self, f"{prefix}_opacity_slider", slider)
        slider_row.addWidget(slider, 1)
        slider_row.addWidget(value_label)
        layout.addLayout(slider_row)

        buttons_row = QHBoxLayout()
        select_button = QPushButton()
        select_button.setIcon(self._load_icon("Camera.png"))
        select_button.setIconSize(QSize(32, 32))
        select_button.setFixedSize(52, 42)
        select_button.setToolTip("画像を選択")
        select_button.clicked.connect(lambda _=False, p=prefix: self._select_image(p))

        clear_button = QPushButton("クリア")
        clear_button.clicked.connect(lambda _=False, p=prefix: self._clear_image(p))
        buttons_row.addWidget(select_button)
        buttons_row.addWidget(clear_button)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)
        return layout

    def _apply_config(self) -> None:
        self.font_size_combo.setCurrentText(self._config.font_size_mode)
        self.title_edit.setText(self._config.app_title)
        self.body_scale_slider.setValue(int(round(self._config.body_text_scale * 100)))
        self.home_path_label.setText(self._config.home_background_path or "未設定")
        self.editor_path_label.setText(self._config.editor_background_path or "未設定")
        self.home_opacity_slider.setValue(self._config.home_background_opacity)
        self.editor_opacity_slider.setValue(self._config.editor_background_opacity)
        self._refresh_preview("home")
        self._refresh_preview("editor")

    def _on_body_scale_changed(self, value: int) -> None:
        scale = value / 100.0
        self._config.body_text_scale = scale
        self.body_scale_value_label.setText(f"{scale:.2f}")

    def _select_image(self, prefix: str) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "画像を選択",
            str(self.db.writable_root),
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not file_path:
            return
        setattr(self._config, f"{prefix}_background_path", file_path)
        getattr(self, f"{prefix}_path_label").setText(file_path)
        self._refresh_preview(prefix)

    def _clear_image(self, prefix: str) -> None:
        setattr(self._config, f"{prefix}_background_path", "")
        getattr(self, f"{prefix}_path_label").setText("未設定")
        self._refresh_preview(prefix)

    def _refresh_preview(self, prefix: str) -> None:
        image_path = getattr(self._config, f"{prefix}_background_path")
        opacity = getattr(self, f"{prefix}_opacity_slider").value()
        preview_surface = getattr(self, f"{prefix}_preview")
        preview_surface.set_background(image_path, opacity)

    def get_config(self) -> AppConfig:
        self._config.app_title = self.title_edit.text().strip() or "My Diary"
        self._config.font_size_mode = self.font_size_combo.currentText()
        self._config.body_text_scale = self.body_scale_slider.value() / 100.0
        self._config.home_background_opacity = self.home_opacity_slider.value()
        self._config.editor_background_opacity = self.editor_opacity_slider.value()
        return self._config

    def _load_icon(self, file_name: str) -> QIcon:
        path = self.db.resource_root / "Sozai" / file_name
        return QIcon(str(path)) if path.exists() else QIcon()


class MemoEditorDialog(QDialog):
    def __init__(self, parent: QWidget | None, db: DataAccess, config: AppConfig, memo: Memo | None = None):
        super().__init__(parent)
        self.db = db
        self.config = config
        self.memo = memo
        self._memo_id = 0 if memo is None else memo.id
        self._selected_color = QColor(QColorConstants.Black)
        self._selected_marker_color = QColor("#fff59d")
        self._selected_tags: list[str] = []

        self.setWindowTitle("Diary(RICH)")
        self.setWindowIcon(self._load_icon("techou.png"))
        self.resize(940, 760)
        self.surface = BackgroundSurface(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.surface)
        self._build_ui()
        self._load_tag_suggestions()
        self._apply_memo(memo)
        self._apply_font_size()
        self.surface.set_background(config.editor_background_path, config.editor_background_opacity)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self.surface.foreground)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        frame = QFrame()
        frame.setObjectName("editorCard")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(14, 14, 14, 14)
        frame_layout.setSpacing(12)

        header_grid = QGridLayout()
        header_grid.setHorizontalSpacing(8)
        header_grid.setVerticalSpacing(8)
        header_grid.setColumnStretch(0, 0)
        header_grid.setColumnStretch(1, 0)
        header_grid.setColumnStretch(2, 1)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("日記のタイトル")
        self.title_edit.setMinimumWidth(520)

        header_grid.addWidget(QLabel("日付 :"), 0, 0)
        self.date_edit.setFixedWidth(160)
        header_grid.addWidget(self.date_edit, 0, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        header_grid.addWidget(QLabel("タイトル :"), 1, 0)
        header_grid.addWidget(self.title_edit, 1, 1, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)

        action_buttons = QHBoxLayout()
        action_buttons.addStretch(1)

        save_button = QPushButton()
        save_button.setIcon(self._load_icon("yumekawa_bird3_green.png"))
        save_button.setIconSize(QSize(34, 34))
        save_button.setFixedSize(50, 50)
        save_button.setToolTip("保存")
        save_button.clicked.connect(self.accept)
        action_buttons.addWidget(save_button)

        cancel_button = QPushButton()
        cancel_button.setIcon(self._load_icon("mark_ng.png"))
        cancel_button.setIconSize(QSize(34, 34))
        cancel_button.setFixedSize(50, 50)
        cancel_button.setToolTip("キャンセル")
        cancel_button.clicked.connect(self.reject)
        action_buttons.addWidget(cancel_button)
        header_grid.addLayout(action_buttons, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)

        frame_layout.addLayout(header_grid)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(QLabel("文字サイズ:"))

        self.font_size_combo = QComboBox()
        style_combo_popup(self.font_size_combo)
        self.font_size_combo.addItems(["10", "12", "14", "16", "18", "20", "24", "28", "32"])
        apply_combo_item_colors(self.font_size_combo)
        self.font_size_combo.setCurrentText("12")
        toolbar_layout.addWidget(self.font_size_combo)

        toolbar_layout.addWidget(QLabel("文字色:"))
        self.color_combo = QComboBox()
        style_combo_popup(self.color_combo)
        self._populate_color_combo()
        apply_combo_item_colors(self.color_combo)
        toolbar_layout.addWidget(self.color_combo)

        bold_button = QPushButton()
        bold_button.setIcon(self._load_icon("bunbougu_magic4.png"))
        bold_button.setIconSize(QSize(24, 24))
        bold_button.setFixedSize(44, 40)
        bold_button.setToolTip("太字")
        bold_button.clicked.connect(self._toggle_bold)
        toolbar_layout.addWidget(bold_button)

        underline_button = QPushButton()
        underline_button.setIcon(self._load_icon("bunbougu_magic3.png"))
        underline_button.setIconSize(QSize(24, 24))
        underline_button.setFixedSize(44, 40)
        underline_button.setToolTip("下線")
        underline_button.clicked.connect(self._toggle_underline)
        toolbar_layout.addWidget(underline_button)

        toolbar_layout.addWidget(QLabel("マーカー:"))
        self.marker_color_combo = QComboBox()
        style_combo_popup(self.marker_color_combo)
        self._populate_marker_color_combo()
        apply_combo_item_colors(self.marker_color_combo)
        toolbar_layout.addWidget(self.marker_color_combo)

        marker_button = QPushButton()
        marker_button.setIcon(self._load_icon("fruit_slice_grapefruit_pink.png"))
        marker_button.setIconSize(QSize(24, 24))
        marker_button.setFixedSize(44, 40)
        marker_button.setToolTip("ラインマーカーを適用")
        marker_button.clicked.connect(self._apply_marker)
        toolbar_layout.addWidget(marker_button)

        image_button = QPushButton()
        image_button.setIcon(self._load_icon("Camera.png"))
        image_button.setIconSize(QSize(28, 28))
        image_button.setFixedSize(48, 40)
        image_button.setToolTip("画像を挿入")
        image_button.clicked.connect(self._insert_image)
        toolbar_layout.addWidget(image_button)

        style_button = QPushButton()
        style_button.setIcon(self._load_icon("yumekawa_bird3_green.png"))
        style_button.setIconSize(QSize(24, 24))
        style_button.setFixedSize(44, 40)
        style_button.setToolTip("装飾を適用")
        style_button.clicked.connect(self._apply_style)
        toolbar_layout.addWidget(style_button)
        toolbar_layout.addStretch(1)
        frame_layout.addLayout(toolbar_layout)

        self.editor = QTextEdit()
        self.editor.setObjectName("memoEditor")
        self.editor.setAcceptRichText(True)
        self.editor.setMinimumHeight(360)
        self.editor.setPlaceholderText("本文を入力してください")
        set_translucent_scroll_surface(self.editor, 100)
        frame_layout.addWidget(self.editor, 1)

        tag_grid = QGridLayout()
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("#天気 #通勤 または 天気; 通勤")

        self.add_manual_tag_button = QPushButton()
        self.add_manual_tag_button.setIcon(self._load_icon("fruit_slice10_orange.png"))
        self.add_manual_tag_button.setIconSize(QSize(22, 22))
        self.add_manual_tag_button.setFixedSize(42, 38)
        self.add_manual_tag_button.setToolTip("入力したタグを追加")
        self.add_manual_tag_button.clicked.connect(self._add_manual_tags)

        self.tag_suggestion_combo = QComboBox()
        style_combo_popup(self.tag_suggestion_combo)
        self.tag_suggestion_combo.addItem("<選択>")
        apply_combo_item_colors(self.tag_suggestion_combo)

        self.add_tag_button = QPushButton()
        self.add_tag_button.setIcon(self._load_icon("yumekawa_bird3_green.png"))
        self.add_tag_button.setIconSize(QSize(22, 22))
        self.add_tag_button.setFixedSize(42, 38)
        self.add_tag_button.setToolTip("候補からタグを追加")
        self.add_tag_button.clicked.connect(self._append_selected_tag)

        self.tag_chip_area = QScrollArea()
        self.tag_chip_area.setWidgetResizable(True)
        self.tag_chip_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tag_chip_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tag_chip_area.setMinimumHeight(90)
        self.tag_chip_area.setMaximumHeight(120)
        self.tag_chip_area.setFrameShape(QFrame.Shape.NoFrame)
        self.tag_chip_container = QWidget()
        self.tag_chip_layout = FlowLayout(self.tag_chip_container, spacing=8)
        self.tag_chip_area.setWidget(self.tag_chip_container)

        tag_grid.addWidget(QLabel("カテゴリ :"), 0, 0)
        tag_grid.addWidget(self.tags_edit, 0, 1)
        tag_grid.addWidget(self.add_manual_tag_button, 0, 2)
        tag_grid.addWidget(self.tag_suggestion_combo, 0, 3)
        tag_grid.addWidget(self.add_tag_button, 0, 4)
        tag_grid.addWidget(QLabel("選択中のタグ"), 1, 0, Qt.AlignmentFlag.AlignTop)
        tag_grid.addWidget(self.tag_chip_area, 1, 1, 1, 4)
        tag_grid.addWidget(QLabel("カテゴリの区切りはセミコロン (;) またはスペースです"), 2, 1, 1, 4)
        frame_layout.addLayout(tag_grid)

        root.addWidget(frame, 1)

    def _apply_font_size(self) -> None:
        point_size = get_scaled_point_size(self.config.font_size_mode, self.config.body_text_scale)
        font = self.font()
        font.setPointSizeF(point_size)
        self.setFont(font)
        self._apply_body_text_scale()

    def _apply_body_text_scale(self) -> None:
        font = self.editor.font()
        font.setPointSizeF(get_scaled_point_size(self.config.font_size_mode, self.config.body_text_scale))
        self.editor.setFont(font)

    def _load_tag_suggestions(self) -> None:
        for name in self.db.get_category_names():
            self.tag_suggestion_combo.addItem(name)
        apply_combo_item_colors(self.tag_suggestion_combo)

    def _populate_color_combo(self) -> None:
        color_names = ["Black", "DarkBlue", "DarkGreen", "Crimson", "Goldenrod", "Tomato", "AliceBlue"]
        for color_name in color_names:
            self.color_combo.addItem(self._create_color_icon(QColor(color_name)), color_name)
        self.color_combo.addItem(self._create_color_icon(QColor("#888888")), "Custom...")

    def _populate_marker_color_combo(self) -> None:
        marker_colors = [
            ("Yellow", "#fff59d"),
            ("Pink", "#ffd6e7"),
            ("Mint", "#c8f7dc"),
            ("Blue", "#cfe8ff"),
            ("Lavender", "#e5d8ff"),
            ("Orange", "#ffd7a8"),
        ]
        for label, color_code in marker_colors:
            self.marker_color_combo.addItem(self._create_color_icon(QColor(color_code)), label)
            self.marker_color_combo.setItemData(
                self.marker_color_combo.count() - 1,
                color_code,
                Qt.ItemDataRole.UserRole,
            )
        self.marker_color_combo.addItem(self._create_color_icon(QColor("#888888")), "Custom...")

    def _create_color_icon(self, color: QColor) -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QColor("#666666"))
        painter.setBrush(color)
        painter.drawEllipse(2, 2, 14, 14)
        painter.end()
        return QIcon(pixmap)

    def _apply_memo(self, memo: Memo | None) -> None:
        if memo is None:
            self._refresh_tag_chips()
            return
        self.date_edit.setDate(QDate.fromString(memo.date, "yyyy-MM-dd"))
        self.title_edit.setText(memo.title)
        self._selected_tags = DataAccess.parse_tags(memo.category)
        self._refresh_tag_chips()
        self.editor.setHtml(prepare_html_for_display(memo.content, self.db.db_path.parent, self.config.body_text_scale))
        self._apply_body_text_scale()

    def _append_selected_tag(self) -> None:
        if self.tag_suggestion_combo.currentIndex() <= 0:
            return
        tag = self.tag_suggestion_combo.currentText().strip()
        self._add_tags([tag])
        self.tag_suggestion_combo.setCurrentIndex(0)

    def _add_manual_tags(self) -> None:
        self._collect_pending_tags()

    def _collect_pending_tags(self) -> None:
        pending = self.tags_edit.text().strip()
        if not pending:
            return
        self._add_tags(DataAccess.parse_tags(pending))
        self.tags_edit.clear()

    def _add_tags(self, tags: list[str]) -> None:
        changed = False
        for tag in tags:
            normalized = tag.strip().lstrip("#").strip()
            if normalized and normalized not in self._selected_tags:
                self._selected_tags.append(normalized)
                changed = True
        if changed:
            self._selected_tags = sorted(self._selected_tags, key=str.casefold)
            self._refresh_tag_chips()

    def _refresh_tag_chips(self) -> None:
        while self.tag_chip_layout.count():
            item = self.tag_chip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self._selected_tags:
            empty = QLabel("タグはまだありません")
            empty.setStyleSheet("color: #667085; padding: 4px;")
            self.tag_chip_layout.addWidget(empty)
            return

        for tag in self._selected_tags:
            chip = QPushButton(f"#{tag}  ×")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            chip.setStyleSheet(
                "QPushButton {"
                "background: #e8f0ff;"
                "border: 1px solid #b9caef;"
                "border-radius: 14px;"
                "padding: 5px 10px;"
                "color: #204a87;"
                "font-weight: 600;"
                "}"
                "QPushButton:hover { background: #dbe8ff; }"
            )
            chip.clicked.connect(lambda _=False, tag_name=tag: self._remove_tag(tag_name))
            self.tag_chip_layout.addWidget(chip)

    def _remove_tag(self, tag_name: str) -> None:
        self._selected_tags = [tag for tag in self._selected_tags if tag != tag_name]
        self._refresh_tag_chips()

    def _selected_font_size(self) -> float:
        try:
            return float(self.font_size_combo.currentText())
        except ValueError:
            return 12.0

    def _resolve_color(self) -> QColor:
        name = self.color_combo.currentText()
        if name == "Custom...":
            color = QColorDialog.getColor(self._selected_color, self, "文字色")
            if color.isValid():
                self._selected_color = color
            return self._selected_color
        color = QColor(name)
        if color.isValid():
            self._selected_color = color
        return self._selected_color

    def _resolve_marker_color(self) -> QColor:
        color_code = self.marker_color_combo.currentData(Qt.ItemDataRole.UserRole)
        if isinstance(color_code, str) and color_code:
            color = QColor(color_code)
            if color.isValid():
                self._selected_marker_color = color
            return self._selected_marker_color

        color = QColorDialog.getColor(self._selected_marker_color, self, "マーカー色")
        if color.isValid():
            self._selected_marker_color = color
        return self._selected_marker_color

    def _apply_style(self) -> None:
        color = self._resolve_color()
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        fmt.setFontPointSize(self._selected_font_size())
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            self.editor.setCurrentCharFormat(fmt)
            return
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _toggle_bold(self) -> None:
        cursor = self.editor.textCursor()
        fmt = QTextCharFormat()
        current_weight = self.editor.fontWeight()
        fmt.setFontWeight(QFont.Normal if current_weight >= QFont.Bold else QFont.Bold)
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _toggle_underline(self) -> None:
        cursor = self.editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.currentCharFormat().fontUnderline())
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _apply_marker(self) -> None:
        color = self._resolve_marker_color()
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(color))
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            self.editor.setCurrentCharFormat(fmt)
            return
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _insert_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "画像を選択",
            str(self.db.writable_root),
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not file_path:
            return

        source = Path(file_path)
        extension = source.suffix.lower() if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"} else ".jpg"
        target_name = f"{QDate.currentDate().toString('yyyyMMdd')}_{uuid4().hex}{extension}"
        target = self.db.images_dir / target_name
        shutil.copy2(source, target)

        alt_text = source.stem
        self.editor.textCursor().insertHtml(f'<p><img src="{target.resolve().as_uri()}" alt="{alt_text}" /></p>')

    def get_memo(self) -> Memo:
        title = self.title_edit.text().strip() or "無題"
        self._collect_pending_tags()
        categories = DataAccess.normalize_tags("; ".join(self._selected_tags))
        raw_html = self.editor.toHtml()
        if self.config.body_text_scale not in (0, 1.0):
            raw_html = scale_html_font_sizes(raw_html, 1.0 / self.config.body_text_scale)
        storage_html = self._convert_display_html_to_storage(raw_html)
        return Memo(
            id=self._memo_id,
            date=self.date_edit.date().toString("yyyy-MM-dd"),
            category=categories,
            title=title,
            content=storage_html,
        )

    def _convert_display_html_to_storage(self, html: str) -> str:
        result = html
        for image_path in sorted(self.db.images_dir.glob("*")):
            storage_path = Path("img") / image_path.name
            result = result.replace(image_path.resolve().as_uri(), storage_path.as_posix())
        return result

    def _load_icon(self, file_name: str) -> QIcon:
        path = self.db.resource_root / "Sozai" / file_name
        return QIcon(str(path)) if path.exists() else QIcon()


class MainWindow(QMainWindow):
    def __init__(self, db_path: str, settings: AppSettings | None = None):
        super().__init__()
        self.db = DataAccess(db_path)
        self.settings = settings or AppSettings()
        self.config = self.db.get_app_config()
        self.current_memo_id: int | None = None

        self.setWindowIcon(self._load_icon("techou.png"))
        self.surface = BackgroundSurface(self)
        self.setCentralWidget(self.surface)
        self._build_ui()
        self._restore_geometry()
        self._apply_app_config()
        self._load_categories()
        self._filter_and_load_memos()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self.surface.foreground)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(toolbar)

        actions = [
            ("fruit_ao_ringo.png", "ホーム", self._go_home),
            ("pen_mannenhitsu.png", "新規作成", self._new_memo),
            ("pen_keseru_ballpen.png", "表示・編集", self._edit_selected_memo),
            ("gomibako_empty.png", "削除", self._delete_selected_memo),
            ("floppy_disk.png", "日記ファイルの保存", self._backup_database),
            ("digital_camera.png", "設定", self._open_settings),
        ]
        for icon_name, label, callback in actions:
            action = QAction(self._load_icon(icon_name), label, self)
            action.setToolTip(label)
            action.setStatusTip(label)
            action.triggered.connect(callback)
            toolbar.addAction(action)

        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self.calendar = QCalendarWidget()
        self.calendar.setMinimumWidth(280)
        self.calendar.setMaximumWidth(320)

        left_card = QFrame()
        left_card.setObjectName("leftCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)
        left_layout.addWidget(self.calendar)

        search_panel = QWidget()
        search_layout = QVBoxLayout(search_panel)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)

        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("日付より :"))
        self.combo_period = QComboBox()
        style_combo_popup(self.combo_period)
        self.combo_period.addItems(["全期間", "1か月前まで", "3か月前まで", "6か月前まで", "1年前まで"])
        apply_combo_item_colors(self.combo_period)
        period_row.addWidget(self.combo_period)
        search_layout.addLayout(period_row)

        category_row = QHBoxLayout()
        category_row.addWidget(QLabel("カテゴリ :"))
        self.combo_category = QComboBox()
        style_combo_popup(self.combo_category)
        category_row.addWidget(self.combo_category)
        search_layout.addLayout(category_row)

        keyword_row = QHBoxLayout()
        keyword_row.addWidget(QLabel("内容検索 :"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("タイトルまたは本文を検索")
        keyword_row.addWidget(self.search_box)
        search_layout.addLayout(keyword_row)

        button_row = QHBoxLayout()
        for icon_name, tooltip, callback in [
            ("fruit_ao_ringo.png", "新しいものを表示", self._go_home),
            ("bunbougu_keshigomu.png", "条件をクリア", self._clear_filters),
            ("search_mushimegane.png", "検索", self._filter_and_load_memos),
        ]:
            button = QPushButton()
            button.setObjectName("sidebarIconButton")
            button.setIcon(self._load_icon(icon_name))
            button.setIconSize(QSize(38, 38))
            button.setToolTip(tooltip)
            button.clicked.connect(callback)
            button_row.addWidget(button)
        button_row.addStretch(1)
        search_layout.addLayout(button_row)
        search_layout.addStretch(1)

        left_layout.addWidget(search_panel)
        left_card.setFixedWidth(320)
        content_layout.addWidget(left_card, 0)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setObjectName("memoPreviewSplitter")
        right_splitter.setChildrenCollapsible(False)
        right_splitter.setHandleWidth(10)

        self.list_view = QListView()
        self.list_view.setObjectName("memoListView")
        self.list_model = QStandardItemModel()
        self.list_view.setModel(self.list_model)
        self.list_view.clicked.connect(self._display_selected_memo)
        self.list_view.doubleClicked.connect(self._edit_selected_memo)
        self.list_view.selectionModel().currentChanged.connect(self._on_memo_current_changed)
        set_translucent_scroll_surface(self.list_view, 100)

        list_card = QFrame()
        list_card.setObjectName("rightCard")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(14, 14, 14, 14)
        list_layout.setSpacing(8)
        list_layout.addWidget(QLabel("日記リスト"))
        list_layout.addWidget(self.list_view, 1)
        right_splitter.addWidget(list_card)

        preview_panel = QFrame()
        preview_panel.setObjectName("rightCard")
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(14, 14, 14, 14)
        preview_layout.setSpacing(6)
        self.preview_title = QLabel("タイトル")
        self.preview_title.setObjectName("previewTitle")
        self.preview_meta = QLabel("日付 / カテゴリ")
        self.preview_browser = QTextBrowser()
        self.preview_browser.setObjectName("memoPreviewBrowser")
        set_translucent_scroll_surface(self.preview_browser, 100)
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_meta)
        preview_layout.addWidget(self.preview_browser, 1)
        right_splitter.addWidget(preview_panel)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 2)
        right_splitter.setSizes([420, 280])

        content_layout.addWidget(right_splitter, 1)
        main_layout.addWidget(content_widget, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel("準備完了")
        status.addWidget(self.status_label)

        self.calendar.selectionChanged.connect(self._filter_and_load_memos)
        self.combo_period.currentIndexChanged.connect(self._filter_and_load_memos)
        self.combo_category.currentIndexChanged.connect(self._filter_and_load_memos)
        self.search_box.textChanged.connect(self._filter_and_load_memos)

    def _apply_app_config(self) -> None:
        self.setWindowTitle(self.config.app_title)
        self._apply_font_size()
        self.surface.set_background(self.config.home_background_path, self.config.home_background_opacity)
        self.status_label.setText(f"データファイル :   {self.db.db_path}")
        current_index = self.list_view.currentIndex()
        if current_index.isValid():
            self._display_selected_memo(current_index)

    def _apply_font_size(self) -> None:
        point_size = get_scaled_point_size(self.config.font_size_mode, self.config.body_text_scale)
        font = QApplication.font()
        font.setPointSizeF(point_size)
        QApplication.setFont(font)
        apply_font_to_widget_tree(self, font)
        self._apply_body_text_scale()

    def _apply_body_text_scale(self) -> None:
        scaled_point_size = get_scaled_point_size(self.config.font_size_mode, self.config.body_text_scale)
        list_font = self.list_view.font()
        list_font.setPointSizeF(scaled_point_size)
        self.list_view.setFont(list_font)

        preview_font = self.preview_browser.font()
        preview_font.setPointSizeF(scaled_point_size)
        self.preview_browser.setFont(preview_font)

    def _load_categories(self) -> None:
        current = self.combo_category.currentData()
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        self.combo_category.addItem("<選択>", "")
        for name in self.db.get_category_names():
            self.combo_category.addItem(name, name)
        apply_combo_item_colors(self.combo_category)
        if current:
            index = self.combo_category.findData(current)
            if index >= 0:
                self.combo_category.setCurrentIndex(index)
        self.combo_category.blockSignals(False)

    def _filter_and_load_memos(self) -> None:
        selected_date = self.calendar.selectedDate()
        end_date = selected_date.toString("yyyy-MM-dd")
        period = self.combo_period.currentText()

        start_date: str | None = None
        if period == "1か月前まで":
            start_date = selected_date.addMonths(-1).toString("yyyy-MM-dd")
        elif period == "3か月前まで":
            start_date = selected_date.addMonths(-3).toString("yyyy-MM-dd")
        elif period == "6か月前まで":
            start_date = selected_date.addMonths(-6).toString("yyyy-MM-dd")
        elif period == "1年前まで":
            start_date = selected_date.addYears(-1).toString("yyyy-MM-dd")
        elif period == "全期間":
            end_date = None

        category = self.combo_category.currentData()
        keyword = self.search_box.text().strip() or None
        memos = self.db.get_memos(start_date=start_date, end_date=end_date, category=category, keyword=keyword)

        self.list_model.clear()
        image_icon = self._load_icon("computer_sdcard.png")
        for memo in memos:
            preview = html_to_plain_text(memo.content).replace("\n", " ").strip()
            if len(preview) > 56:
                preview = preview[:56] + "..."
            item = QStandardItem(f"{memo.date}  {memo.title}\n{preview}")
            if not image_icon.isNull() and html_contains_image(memo.content):
                item.setIcon(image_icon)
            item.setEditable(False)
            item.setData(memo, Qt.ItemDataRole.UserRole)
            self.list_model.appendRow(item)

        if memos:
            index = self.list_model.index(0, 0)
            self.list_view.setCurrentIndex(index)
            self._display_selected_memo(index)
        else:
            self.current_memo_id = None
            self.preview_title.setText("タイトル")
            self.preview_meta.setText("日付 / カテゴリ")
            self.preview_browser.clear()

    def _display_selected_memo(self, index) -> None:
        item = self.list_model.itemFromIndex(index)
        if item is None:
            return
        memo = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(memo, Memo):
            return

        self.current_memo_id = memo.id
        self.preview_title.setText(memo.title)
        self.preview_meta.setText(f"{memo.date} / {memo.category or 'カテゴリ未設定'}")
        self.preview_browser.setHtml(
            prepare_html_for_display(memo.content, self.db.db_path.parent, self.config.body_text_scale)
        )

    def _on_memo_current_changed(self, current, _previous) -> None:
        if not current.isValid():
            return
        self._display_selected_memo(current)

    def _new_memo(self) -> None:
        dialog = MemoEditorDialog(self, self.db, self.config)
        dialog.restoreGeometry(self.settings.load_geometry("editor"))
        if dialog.exec() != QDialog.Accepted:
            self.settings.save_geometry("editor", dialog.saveGeometry())
            return

        memo = dialog.get_memo()
        memo_id = self.db.add_memo(memo)
        self.settings.save_geometry("editor", dialog.saveGeometry())
        self._load_categories()
        self._filter_and_load_memos()
        self.status_label.setText(f"日記を保存しました (ID {memo_id})")

    def _edit_selected_memo(self, index=None) -> None:
        if isinstance(index, bool):
            index = None
        memo = self._get_selected_memo(index)
        if memo is None:
            QMessageBox.information(self, "表示・編集", "対象の日記を選択してください。")
            return

        full_memo = self.db.get_memo_by_id(memo.id) or memo
        dialog = MemoEditorDialog(self, self.db, self.config, full_memo)
        dialog.restoreGeometry(self.settings.load_geometry("editor"))
        if dialog.exec() != QDialog.Accepted:
            self.settings.save_geometry("editor", dialog.saveGeometry())
            return

        updated = dialog.get_memo()
        self.db.update_memo(updated)
        self.settings.save_geometry("editor", dialog.saveGeometry())
        self._load_categories()
        self._filter_and_load_memos()
        self.status_label.setText(f"日記を更新しました (ID {updated.id})")

    def _delete_selected_memo(self) -> None:
        memo = self._get_selected_memo()
        if memo is None:
            QMessageBox.information(self, "削除", "削除する日記を選択してください。")
            return
        answer = QMessageBox.question(
            self,
            "削除確認",
            f"『{memo.title}』を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_memo(memo.id)
        self._filter_and_load_memos()
        self.status_label.setText(f"日記を削除しました (ID {memo.id})")

    def _backup_database(self) -> None:
        source_path = self.db.db_path
        timestamp = QDate.currentDate().toString("yyyyMMdd")
        current_time = QTime.currentTime().toString("HHmmss")
        default_name = f"{source_path.stem}_backup_{timestamp}_{current_time}.zip"
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "日記バックアップの保存",
            str(source_path.with_name(default_name)),
            "ZIP Archive (*.zip);;All Files (*)",
        )
        if not destination:
            return

        destination_path = Path(destination).expanduser().resolve()
        if not destination_path.suffix:
            destination_path = destination_path.with_suffix(".zip")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_path == source_path:
            QMessageBox.information(
                self,
                "日記バックアップの保存",
                "元のデータファイルと同じ場所は保存先にできません。別名で保存してください。",
            )
            return

        try:
            self.db.close()
            with zipfile.ZipFile(destination_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(source_path, arcname=source_path.name)
                if self.db.images_dir.exists():
                    image_files = [path for path in self.db.images_dir.rglob("*") if path.is_file()]
                    if image_files:
                        for image_path in image_files:
                            if image_path.resolve() == destination_path:
                                continue
                            archive.write(image_path, arcname=image_path.relative_to(source_path.parent))
                    else:
                        archive.writestr("img/", "")
            self.db.reopen()
        except Exception as exc:
            try:
                self.db.reopen()
            except Exception as reopen_exc:
                QMessageBox.critical(
                    self,
                    "保存エラー",
                    "バックアップZIPの保存に失敗し、データベースの再接続にも失敗しました。\n"
                    f"保存エラー: {exc}\n再接続エラー: {reopen_exc}",
                )
                self.status_label.setText("日記バックアップの保存に失敗しました")
                return

            QMessageBox.critical(
                self,
                "保存エラー",
                f"日記バックアップの保存に失敗しました。\n{exc}",
            )
            self.status_label.setText("日記バックアップの保存に失敗しました")
            return

        self.status_label.setText(f"日記バックアップを保存しました: {destination_path}")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self, self.db, self.config)
        dialog.restoreGeometry(self.settings.load_geometry("settings"))
        if dialog.exec() != QDialog.Accepted:
            self.settings.save_geometry("settings", dialog.saveGeometry())
            return

        self.config = dialog.get_config()
        self.db.save_app_config(self.config)
        self.settings.save_geometry("settings", dialog.saveGeometry())
        self._apply_app_config()

    def _go_home(self) -> None:
        self.calendar.setSelectedDate(QDate.currentDate())
        self.combo_period.setCurrentText("全期間")
        self.search_box.clear()
        self.combo_category.setCurrentIndex(0)
        self._filter_and_load_memos()

    def _clear_filters(self) -> None:
        self.combo_period.setCurrentText("全期間")
        self.combo_category.setCurrentIndex(0)
        self.search_box.clear()
        self._filter_and_load_memos()

    def _get_selected_memo(self, index=None) -> Memo | None:
        if isinstance(index, bool):
            index = None
        model_index = index if index is not None else self.list_view.currentIndex()
        if not model_index.isValid():
            return None
        item = self.list_model.itemFromIndex(model_index)
        memo = item.data(Qt.ItemDataRole.UserRole)
        return memo if isinstance(memo, Memo) else None

    def _restore_geometry(self) -> None:
        geometry = self.settings.load_geometry("main")
        if hasattr(geometry, "isEmpty") and not geometry.isEmpty():
            self.restoreGeometry(geometry)

    def _load_icon(self, file_name: str) -> QIcon:
        icon_path = self.db.resource_root / "Sozai" / file_name
        return QIcon(str(icon_path)) if icon_path.exists() else QIcon()

    def closeEvent(self, event) -> None:
        self.settings.save_geometry("main", self.saveGeometry())
        self.db.close()
        super().closeEvent(event)
