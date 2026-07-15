import ctypes
import copy
import json
import logging
import math
import os
import sys
import time
from ctypes import wintypes

sys.dont_write_bytecode = True

_PROCESS_MUTEX_HANDLE = None


def acquire_process_mutex():
    global _PROCESS_MUTEX_HANDLE
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel32.CreateMutexW(None, False, "Global\\SystemMonitorWidgetSingleInstance")
    if not handle:
        return
    if kernel32.GetLastError() == 183:
        sys.exit(0)
    _PROCESS_MUTEX_HANDLE = handle


if __name__ == "__main__":
    acquire_process_mutex()

from PyQt5.QtCore import QPointF, QRectF, QSharedMemory, Qt, QTimer
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from system_monitor import SystemMonitor


APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
LOG_FILE = os.path.join(APP_DIR, "system_monitor.log")
APP_NAME = "系统监控"
GAUGE_WIDTH = 112
GAUGE_HEIGHT = 116
GAUGE_GAP = 8
FONT_FILES = (
    "SF-Pro-Display-Regular.otf",
    "SF-Pro-Display-Bold.otf",
    "SF-Pro-Text-Regular.otf",
    "SF-Pro-Text-Bold.otf",
)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)


def app_path(name):
    resource_path = os.path.join(RESOURCE_DIR, name)
    if os.path.exists(resource_path):
        return resource_path
    return os.path.join(APP_DIR, name)


def startup_command():
    if getattr(sys, "frozen", False):
        return sys.executable
    exe_path = os.path.join(APP_DIR, "dist", "SystemMonitor", "SystemMonitor.exe")
    if os.path.exists(exe_path):
        return exe_path
    return os.path.abspath(__file__)


def load_settings():
    defaults = {
        "refresh_interval": 1,
        "opacity": 96,
        "auto_start": False,
        "theme": "深色",
        "size": "中型",
        "layout": "square",
        "layout_positions": {},
        "selected_disks": [],
        "position": [100, 100],
        "desktop_mode": False,
    }
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            defaults.update(data)
    except Exception:
        logging.exception("failed to load settings")
    return defaults


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def load_local_fonts():
    global FONT_FAMILIES
    font_dir = app_path("fonts")
    if not os.path.isdir(font_dir):
        return "SimHei"

    loaded_families = []
    for filename in FONT_FILES:
        font_path = os.path.join(font_dir, filename)
        if not os.path.exists(font_path):
            continue
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id >= 0:
            loaded_families.extend(QFontDatabase.applicationFontFamilies(font_id))
    FONT_FAMILIES = set(loaded_families)

    for preferred in ("SF Pro Display", "SF Pro Text", "SF Pro", "SF Compact Display", "San Francisco"):
        if preferred in loaded_families:
            return preferred
    return loaded_families[0] if loaded_families else "SimHei"


FONT_FAMILY = "SimHei"
FONT_FAMILIES = set()


def make_font(size, weight=QFont.Normal):
    family = FONT_FAMILY
    if size <= 11 and "SF Pro Text" in FONT_FAMILIES:
        family = "SF Pro Text"
    font = QFont(family, size)
    if weight >= QFont.Bold:
        font.setStyleName("Bold")
        font.setBold(True)
    elif weight >= QFont.DemiBold:
        font.setStyleName("Semibold")
    font.setWeight(weight)
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


def format_bytes_per_second(value):
    value = max(float(value or 0), 0.0)
    units = ["B/s", "K/s", "M/s", "G/s"]
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    if index == 0:
        return f"{int(value)}{units[index]}"
    if value >= 100:
        return f"{value:.0f}{units[index]}"
    if value >= 10:
        return f"{value:.0f}{units[index]}"
    return f"{value:.1f}{units[index]}"


def format_bytes_compact(value):
    value = max(float(value or 0), 0.0)
    units = ["B", "K", "M", "G"]
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    if index == 0:
        return f"{int(value)}{units[index]}"
    if value >= 10:
        return f"{value:.0f}{units[index]}"
    return f"{value:.1f}{units[index]}"


def normalize_disk_mount(mountpoint):
    return str(mountpoint or "").rstrip("\\/").upper()


def disk_matches_selection(mountpoint, selected_disks):
    if not selected_disks:
        return True
    if "__none__" in selected_disks:
        return False
    selected = {normalize_disk_mount(item) for item in selected_disks}
    return normalize_disk_mount(mountpoint) in selected


def is_autostart_enabled():
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        value, _ = winreg.QueryValueEx(key, "SystemMonitor")
        winreg.CloseKey(key)
        return bool(value)
    except Exception:
        return False


def set_autostart(enable):
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        if enable:
            command = startup_command()
            winreg.SetValueEx(key, "SystemMonitor", 0, winreg.REG_SZ, command)
            logging.info("autostart enabled: %s", command)
        else:
            try:
                winreg.DeleteValue(key, "SystemMonitor")
            except FileNotFoundError:
                pass
            logging.info("autostart disabled")
        winreg.CloseKey(key)
        return True
    except Exception:
        logging.exception("failed to update autostart")
        return False


class SettingsDialog(QMainWindow):
    def __init__(self, parent_window):
        super().__init__(None)
        self.parent_window = parent_window
        self.monitor = parent_window.monitor
        self.settings = dict(parent_window.settings)
        self.setWindowTitle("设置")
        self.disk_preview_timer = QTimer(self)
        self.disk_preview_timer.setSingleShot(True)
        self.disk_preview_timer.timeout.connect(self.preview_disk_selection)
        self.original_parent_settings = copy.deepcopy(parent_window.settings)
        self.original_edit_mode = parent_window.edit_mode
        self.original_desktop_mode = bool(parent_window.settings.get("desktop_mode", False))
        self.preview_edit_started = False
        self.saved = False
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.resize(520, 560)
        self.setMinimumSize(480, 520)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setSpacing(12)

        refresh_group = QGroupBox("刷新")
        refresh_layout = QHBoxLayout(refresh_group)
        refresh_layout.addWidget(QLabel("刷新间隔"))
        self.refresh_spinbox = QSpinBox()
        self.refresh_spinbox.setRange(1, 60)
        self.refresh_spinbox.setSuffix(" 秒")
        self.refresh_spinbox.setValue(self.settings.get("refresh_interval", 1))
        refresh_layout.addWidget(self.refresh_spinbox)
        layout.addWidget(refresh_group)

        appearance_group = QGroupBox("外观")
        appearance_layout = QVBoxLayout(appearance_group)
        opacity_row = QHBoxLayout()
        self.opacity_label = QLabel()
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(35, 100)
        self.opacity_slider.setValue(self.settings.get("opacity", 96))
        self.opacity_slider.valueChanged.connect(
            lambda value: self.opacity_label.setText(f"透明度 {value}%")
        )
        self.opacity_label.setText(f"透明度 {self.opacity_slider.value()}%")
        opacity_row.addWidget(self.opacity_label)
        opacity_row.addWidget(self.opacity_slider)
        appearance_layout.addLayout(opacity_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("尺寸"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(["小型", "中型", "大型"])
        current_size = self.settings.get("size", "中型")
        self.size_combo.setCurrentText(current_size if current_size in ["小型", "中型", "大型"] else "中型")
        size_row.addWidget(self.size_combo)
        appearance_layout.addLayout(size_row)
        layout.addWidget(appearance_group)

        disk_group = QGroupBox("磁盘筛选")
        disk_layout = QVBoxLayout(disk_group)
        selected = self.settings.get("selected_disks", [])
        self.disk_checks = []
        cached_info = getattr(self.parent_window, "latest_info", None) or {}
        partitions = cached_info.get("disk", {}).get("partitions", [])
        if not partitions:
            partitions = self.monitor.get_disk_info().get("partitions", [])
        for partition in partitions:
            mount = partition["mountpoint"]
            used = partition["used"] / (1024 ** 3)
            total = partition["total"] / (1024 ** 3)
            checkbox = QCheckBox(f"{mount}  {used:.0f}/{total:.0f}GB")
            checkbox.setProperty("mountpoint", mount)
            checkbox.setChecked(disk_matches_selection(mount, selected))
            checkbox.stateChanged.connect(self.schedule_disk_preview)
            self.disk_checks.append(checkbox)
            disk_layout.addWidget(checkbox)
        if not partitions:
            disk_layout.addWidget(QLabel("没有读取到可用磁盘"))
        layout.addWidget(disk_group)

        startup_group = QGroupBox("启动")
        startup_layout = QVBoxLayout(startup_group)
        self.startup_checkbox = QCheckBox("开机自启")
        self.startup_checkbox.setChecked(bool(self.settings.get("auto_start", False)) or is_autostart_enabled())
        startup_layout.addWidget(self.startup_checkbox)
        layout.addWidget(startup_group)

        layout.addStretch()
        outer.addWidget(scroll)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.cancel_and_close)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_and_close)
        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)
        outer.addLayout(button_row)

        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f2f3f5; color: #20242a; font-family: "SimHei"; }
            QGroupBox { border: 1px solid #d6d9de; border-radius: 8px; margin-top: 12px; padding: 12px 8px 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPushButton { min-width: 72px; padding: 7px 12px; border-radius: 6px; border: 1px solid #c4c8cf; background: #ffffff; }
            QPushButton:hover { background: #e9edf2; }
            """
        )

    def get_selected_disks(self):
        selected_disks = [
            checkbox.property("mountpoint")
            for checkbox in self.disk_checks
            if checkbox.isChecked()
        ]
        if len(selected_disks) == len(self.disk_checks):
            selected_disks = []
        elif not selected_disks:
            selected_disks = ["__none__"]
        return selected_disks

    def preview_disk_selection(self):
        self.begin_preview_edit_mode()
        self.settings["selected_disks"] = self.get_selected_disks()
        self.parent_window.preview_selected_disks(self.settings["selected_disks"])

    def schedule_disk_preview(self):
        self.disk_preview_timer.start(120)

    def begin_preview_edit_mode(self):
        if self.preview_edit_started or not self.original_desktop_mode:
            return
        self.preview_edit_started = True
        self.parent_window.suspend_persistence = True
        self.parent_window.detach_from_desktop_layer()
        self.parent_window.edit_mode = True
        self.parent_window.settings["desktop_mode"] = False
        self.parent_window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.parent_window.show()
        self.parent_window.force_show()
        self.parent_window.update_tray_labels()
        QApplication.processEvents()

    def restore_or_attach_parent(self, settings):
        self.parent_window.settings = copy.deepcopy(settings)
        self.parent_window.last_visible_disks = None
        self.parent_window.apply_settings(self.parent_window.settings, persist=False)
        if self.original_desktop_mode:
            self.parent_window.edit_mode = False
            self.parent_window.settings["desktop_mode"] = True
            self.parent_window.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
            self.parent_window.show()
            self.parent_window.attach_to_desktop_layer()
            self.parent_window.force_show()
        else:
            self.parent_window.edit_mode = self.original_edit_mode
        self.parent_window.update_tray_labels()

    def cancel_and_close(self):
        if self.disk_preview_timer.isActive():
            self.disk_preview_timer.stop()
        logging.info("settings canceled; restoring previous settings")
        self.parent_window.suspend_persistence = True
        self.restore_or_attach_parent(self.original_parent_settings)
        self.parent_window.suspend_persistence = False
        save_settings(self.original_parent_settings)
        self.saved = True
        self.close()

    def save_and_close(self):
        if self.disk_preview_timer.isActive():
            self.disk_preview_timer.stop()
        selected_disks = self.get_selected_disks()
        logging.info("selected disks saved: %s", selected_disks or "all")
        self.preview_disk_selection()
        self.settings.update(
            {
                "refresh_interval": self.refresh_spinbox.value(),
                "opacity": self.opacity_slider.value(),
                "size": self.size_combo.currentText(),
                "selected_disks": selected_disks,
                "auto_start": self.startup_checkbox.isChecked(),
            }
        )
        set_autostart(self.settings["auto_start"])
        save_settings(self.settings)
        self.parent_window.suspend_persistence = False
        self.parent_window.apply_settings(self.settings)
        if self.original_desktop_mode:
            self.parent_window.attach_to_desktop()
        self.saved = True
        self.close()

    def closeEvent(self, event):
        if not self.saved:
            self.cancel_and_close()
            event.ignore()
            return
        event.accept()


class GaugeWidget(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.metric_key = ""
        self.value = 0
        self.value_text = "0%"
        self.detail_text = ""
        self.accent_override = None
        self.upload_history = []
        self.download_history = []
        self.setFixedSize(GAUGE_WIDTH, GAUGE_HEIGHT)

    def update_data(self, value, detail_text="", value_text=None):
        self.value = max(0, min(float(value or 0), 100))
        self.detail_text = detail_text or ""
        self.value_text = value_text if value_text is not None else f"{int(round(self.value))}%"
        self.update()

    def update_network_data(self, sent, recv):
        sent = max(float(sent or 0), 0.0)
        recv = max(float(recv or 0), 0.0)
        dominant = max(sent, recv)
        self.value = min(dominant / (1024 ** 2) * 100, 100)
        self.value_text = format_bytes_per_second(dominant)
        self.detail_text = f"↑{format_bytes_compact(sent)}  ↓{format_bytes_compact(recv)}"
        self.upload_history = (self.upload_history + [sent])[-24:]
        self.download_history = (self.download_history + [recv])[-24:]
        self.update()

    def get_color(self):
        if self.accent_override:
            return QColor(self.accent_override)
        if self.value < 50:
            return QColor(48, 210, 104)
        if self.value < 80:
            return QColor(255, 156, 18)
        return QColor(244, 82, 82)

    def _arc_path(self, center_x, center_y, radius, start_degrees, sweep_degrees):
        path = QPainterPath()
        steps = max(14, int(abs(sweep_degrees) / 4))
        for step in range(steps + 1):
            degrees = start_degrees + sweep_degrees * step / steps
            radians = math.radians(degrees)
            point = QPointF(
                center_x + math.cos(radians) * radius,
                center_y + math.sin(radians) * radius,
            )
            if step == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        return path

    def _fit_font(self, painter, text, max_width, base_size, min_size, weight=QFont.Normal):
        size = base_size
        while size > min_size:
            font = make_font(size, weight)
            painter.setFont(font)
            if painter.fontMetrics().horizontalAdvance(text) <= max_width:
                return font
            size -= 1
        return make_font(min_size, weight)

    def _draw_fitted_text(self, painter, rect, text, base_size, min_size, color, weight=QFont.Normal):
        painter.setPen(color)
        font = self._fit_font(painter, text, rect.width(), base_size, min_size, weight)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        fitted_text = metrics.elidedText(text, Qt.ElideRight, int(rect.width()))
        painter.drawText(rect, Qt.AlignCenter, fitted_text)

    def _draw_series(self, painter, chart_rect, values, color, max_value):
        if not values:
            return
        if len(values) == 1:
            values = [0, values[0]]
        path = QPainterPath()
        for index, value in enumerate(values):
            x = chart_rect.left() + chart_rect.width() * index / max(1, len(values) - 1)
            ratio = min(max(value / max_value, 0.0), 1.0)
            y = chart_rect.bottom() - chart_rect.height() * ratio
            if index == 0:
                path.moveTo(QPointF(x, y))
            else:
                path.lineTo(QPointF(x, y))
        painter.setPen(QPen(color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

    def _draw_network(self, painter, rect):
        upload_color = QColor(48, 210, 104)
        download_color = QColor(244, 82, 82)
        upload_rect = QRectF(rect.left() + 11, rect.top() + 18, rect.width() - 22, 26)
        download_rect = QRectF(rect.left() + 11, rect.top() + 66, rect.width() - 22, 26)

        for chart_rect in (upload_rect, download_rect):
            painter.setPen(QPen(QColor(78, 86, 104, 130), 1))
            painter.drawLine(
                QPointF(chart_rect.left(), chart_rect.bottom()),
                QPointF(chart_rect.right(), chart_rect.bottom()),
            )

        upload_max = max(self.upload_history + [1024.0])
        download_max = max(self.download_history + [1024.0])
        self._draw_series(painter, upload_rect, self.upload_history, upload_color, upload_max)
        self._draw_series(painter, download_rect, self.download_history, download_color, download_max)

        text_color = QColor(238, 241, 246)
        upload_text_rect = QRectF(rect.left() + 8, rect.top() + 45, rect.width() - 16, 17)
        download_text_rect = QRectF(rect.left() + 8, rect.top() + 93, rect.width() - 16, 17)
        parts = self.detail_text.split("  ", 1)
        upload_text = parts[0] if parts else "↑0B"
        download_text = parts[1] if len(parts) > 1 else "↓0B"
        self._draw_fitted_text(painter, upload_text_rect, upload_text, 11, 9, text_color, QFont.Bold)
        self._draw_fitted_text(painter, download_text_rect, download_text, 11, 9, text_color, QFont.Bold)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        self.draw_card(painter, rect)

    def draw_card(self, painter, rect):
        card_path = QPainterPath()
        card_path.addRoundedRect(rect, 18, 18)
        painter.fillPath(card_path, QColor(34, 38, 48, 236))
        painter.setPen(QPen(QColor(94, 101, 118, 190), 1))
        painter.drawPath(card_path)

        if self.metric_key == "network":
            self._draw_network(painter, rect)
            return

        center_x = rect.center().x()
        radius = min(rect.width() / 2 - 17, 39)
        center_y = rect.top() + radius + 18
        total_degrees = 200
        start_degrees = 170

        base_pen = QPen(QColor(76, 83, 98, 220), 6, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(base_pen)
        painter.drawPath(self._arc_path(center_x, center_y, radius, start_degrees, total_degrees))

        progress_pen = QPen(self.get_color(), 6, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(progress_pen)
        painter.drawPath(
            self._arc_path(center_x, center_y, radius, start_degrees, total_degrees * self.value / 100)
        )

        value_rect = QRectF(rect.left() + 8, rect.top() + 43, rect.width() - 16, 27)
        self._draw_fitted_text(
            painter,
            value_rect,
            self.value_text,
            19 if len(self.value_text) <= 4 else 17,
            13,
            QColor(238, 241, 246),
            QFont.Bold,
        )

        title_rect = QRectF(rect.left() + 8, rect.top() + 73, rect.width() - 16, 15)
        self._draw_fitted_text(painter, title_rect, self.title, 9, 7, QColor(222, 226, 234), QFont.Bold)

        detail_rect = QRectF(rect.left() + 7, rect.top() + 91, rect.width() - 14, 14)
        self._draw_fitted_text(
            painter,
            detail_rect,
            self.detail_text,
            8,
            6,
            QColor(205, 211, 221),
            QFont.Bold,
        )


class MonitorPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_mode = "square"
        self.widgets = []
        self.columns = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

    def set_widgets(self, widgets, layout_mode, columns=None):
        self.widgets = widgets
        self.layout_mode = layout_mode
        self.columns = columns
        self.rebuild()

    def rebuild(self):
        while self.root_layout.count():
            item = self.root_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                layout = item.layout()
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().setParent(None)
                layout.deleteLater()

        columns = self.columns or self.grid_columns(len(self.widgets))
        rows = max(1, math.ceil(len(self.widgets) / columns))

        grid = QGridLayout()
        grid.setSpacing(GAUGE_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        for index, widget in enumerate(self.widgets):
            row = index // columns
            column = index % columns
            grid.addWidget(widget, row, column)
        for column in range(columns):
            grid.setColumnStretch(column, 0)
            grid.setColumnMinimumWidth(column, GAUGE_WIDTH)
        for row in range(rows):
            grid.setRowStretch(row, 0)
            grid.setRowMinimumHeight(row, GAUGE_HEIGHT)
        self.root_layout.addLayout(grid)

    @staticmethod
    def grid_columns(count):
        if count <= 0:
            return 1
        return max(1, math.ceil(math.sqrt(count)))

    def paintEvent(self, event):
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.shared_memory = QSharedMemory("SystemMonitorSingleInstance")
        if not self.shared_memory.create(1):
            logging.info("another instance is running")
            sys.exit(0)

        self.monitor = SystemMonitor()
        self.settings = load_settings()
        self.drag_position = None
        self.edit_mode = not bool(self.settings.get("desktop_mode", False))
        self.tray_icon = None
        self.tray_menu = None
        self.settings_dialog = None
        self.gauges = {}
        self.gauge_keys = []
        self.gauge_layout = None
        self.last_force_show_log = 0
        self.last_update_log = 0
        self.last_update_time = 0
        self.update_log_count = 0
        self.desktop_parent_hwnd = 0
        self.last_visible_disks = None
        self.latest_info = None
        self.suspend_persistence = False

        self.init_ui()
        self.init_tray()
        self.init_timers()
        self.apply_settings(self.settings, persist=False)

    def init_ui(self):
        self.setWindowTitle(APP_NAME)
        if self.settings.get("desktop_mode", False):
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.panel = MonitorPanel(self)
        self.setCentralWidget(self.panel)
        position = self.settings.get("position", [100, 100])
        if isinstance(position, list) and len(position) == 2:
            self.move(position[0], position[1])
        self.setWindowOpacity(self.settings.get("opacity", 96) / 100)

    def init_tray(self):
        menu = QMenu()
        self.tray_menu = menu
        self.edit_action = menu.addAction("进入编辑模式")
        self.edit_action.triggered.connect(self.toggle_edit_mode)
        menu.addSeparator()
        self.layout_action = menu.addAction("切换横向布局")
        self.layout_action.triggered.connect(self.toggle_layout)
        settings_action = menu.addAction("设置")
        settings_action.triggered.connect(self.open_settings)
        self.autostart_action = menu.addAction("开机自启")
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(bool(self.settings.get("auto_start", False)) or is_autostart_enabled())
        self.autostart_action.triggered.connect(self.toggle_autostart)
        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self.quit_application)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            logging.warning("system tray is not available")
            self.update_tray_labels()
            return
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.create_tray_icon_pixmap()))
        self.tray_icon.setToolTip(APP_NAME)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        self.update_tray_labels()

    def init_timers(self):
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(self.settings.get("refresh_interval", 1) * 1000)
        self.desktop_timer = QTimer(self)
        self.desktop_timer.timeout.connect(self.maintain_desktop_behavior)
        self.desktop_timer.start(5000)

    def create_tray_icon_pixmap(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(38, 42, 50))
        painter.drawRoundedRect(3, 3, 26, 26, 7, 7)
        painter.setPen(QPen(QColor(48, 210, 104), 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(8, 8, 16, 16, 150 * 16, 210 * 16)
        painter.end()
        return pixmap

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.enter_edit_mode()

    def contextMenuEvent(self, event):
        if self.tray_menu:
            self.tray_menu.exec_(event.globalPos())
            event.accept()

    def update_tray_labels(self):
        if hasattr(self, "edit_action"):
            self.edit_action.setText("退出编辑模式" if self.edit_mode else "进入编辑模式")
        if hasattr(self, "layout_action"):
            self.layout_action.setText(
                "切换方形布局" if self.settings.get("layout", "square") == "horizontal" else "切换横向布局"
            )

    def build_gauges(self, info):
        entries = [("cpu", "CPU"), ("memory", "MEM"), ("gpu", "GPU")]

        selected = self.settings.get("selected_disks", [])
        partitions = info.get("disk", {}).get("partitions", [])
        if selected:
            partitions = [p for p in partitions if disk_matches_selection(p.get("mountpoint"), selected)]
        visible_disks = [p.get("mountpoint") for p in partitions]
        if visible_disks != self.last_visible_disks:
            self.last_visible_disks = list(visible_disks)
            logging.info("visible disks: %s", visible_disks or "none")
        for partition in partitions:
            disk_name = partition.get("mountpoint", "").rstrip("\\/")
            label = f"Disk {disk_name}"
            entries.append((f"disk:{partition.get('mountpoint')}", label))

        entries.append(("network", "NET"))
        next_keys = [key for key, _ in entries]
        next_layout = self.settings.get("layout", "square")
        if next_keys != self.gauge_keys or next_layout != self.gauge_layout:
            old = self.gauges
            old_panel = self.panel
            self.gauges = {}
            widgets = []
            for key, title in entries:
                widget = GaugeWidget(title)
                widget.metric_key = key
                if key == "network" and key in old:
                    widget.upload_history = list(old[key].upload_history)
                    widget.download_history = list(old[key].download_history)
                    widget.detail_text = old[key].detail_text
                    widget.value_text = old[key].value_text
                    widget.value = old[key].value
                self.gauges[key] = widget
                widgets.append(widget)

            for widget in old.values():
                widget.hide()
                widget.deleteLater()

            self.gauge_keys = next_keys
            self.gauge_layout = next_layout
            logging.info("gauge layout rebuilt: %s", next_keys)
            self.panel = MonitorPanel(self)
            self.setCentralWidget(self.panel)
            old_panel.hide()
            old_panel.deleteLater()
            columns, _, _, _ = self.layout_metrics(len(widgets), next_layout)
            self.panel.set_widgets(widgets, next_layout, columns)
            self.resize_for_widget_count(len(widgets))
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.panel.updateGeometry()
            self.panel.update()
            self.panel.repaint()
            self.updateGeometry()
            self.update()
            self.repaint()
        else:
            for key, title in entries:
                self.gauges[key].title = title

    def resize_for_widget_count(self, count):
        _, _, width, height = self.layout_metrics(count, self.settings.get("layout", "square"))
        self.setFixedSize(width, height)
        self.ensure_on_screen()
        self.sync_native_window_rect()

    def layout_metrics(self, count, layout_mode):
        columns = self.layout_columns(count, layout_mode)
        rows = max(1, math.ceil(count / columns))
        width = columns * GAUGE_WIDTH + max(0, columns - 1) * GAUGE_GAP
        height = rows * GAUGE_HEIGHT + max(0, rows - 1) * GAUGE_GAP
        return columns, rows, width, height

    def layout_columns(self, count, layout_mode):
        return self.calculate_layout_columns(count, layout_mode, self.horizontal_available_width())

    @staticmethod
    def calculate_layout_columns(count, layout_mode, available_width):
        if count <= 0:
            return 1
        if layout_mode != "horizontal":
            return MonitorPanel.grid_columns(count)
        columns = max(1, int((available_width + GAUGE_GAP) // (GAUGE_WIDTH + GAUGE_GAP)))
        return min(count, columns)

    def horizontal_available_width(self):
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return GAUGE_WIDTH
        available = screen.availableGeometry()
        margin = 8
        return max(GAUGE_WIDTH, available.width() - margin * 2)

    def ensure_on_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        margin = 8
        x = min(max(self.x(), available.left() + margin), available.right() - self.width() - margin)
        y = min(max(self.y(), available.top() + margin), available.bottom() - self.height() - margin)
        if x != self.x() or y != self.y():
            self.move(x, y)
            self.settings["position"] = [x, y]
            self.save_layout_position()
            if not self.suspend_persistence:
                save_settings(self.settings)

    def current_layout_key(self):
        return self.settings.get("layout", "square")

    def save_layout_position(self):
        positions = self.settings.setdefault("layout_positions", {})
        positions[self.current_layout_key()] = [self.x(), self.y()]
        self.settings["position"] = [self.x(), self.y()]

    def restore_layout_position(self, layout_key):
        positions = self.settings.get("layout_positions", {})
        position = positions.get(layout_key)
        if isinstance(position, list) and len(position) == 2:
            self.move(position[0], position[1])

    def update_data(self):
        started = time.time()
        info = self.monitor.get_all_info()
        self.latest_info = info
        interval = 0 if not self.last_update_time else started - self.last_update_time
        self.last_update_time = started
        self.update_log_count += 1
        if self.update_log_count <= 30 or started - self.last_update_log > 10:
            self.last_update_log = started
            logging.info(
                "data refreshed #%s interval=%.2fs cpu=%.0f net_up=%s net_down=%s",
                self.update_log_count,
                interval,
                info.get("cpu", {}).get("usage", 0),
                int(info.get("network", {}).get("sent_speed", 0)),
                int(info.get("network", {}).get("recv_speed", 0)),
            )
        self.render_info(info)

    def preview_selected_disks(self, selected_disks):
        self.settings["selected_disks"] = list(selected_disks)
        self.last_visible_disks = None
        if self.latest_info:
            self.render_info(self.latest_info)
        else:
            self.update_data()

    def render_info(self, info):
        self.build_gauges(info)

        cpu = info["cpu"]
        self.gauges["cpu"].update_data(cpu["usage"], f"{cpu['cores']}C / {cpu['threads']}T")

        memory = info["memory"]
        used_gb = memory["used"] / (1024 ** 3)
        total_gb = memory["total"] / (1024 ** 3)
        self.gauges["memory"].update_data(memory["percent"], f"{used_gb:.1f}/{total_gb:.1f}GB")

        gpu = info.get("gpu")
        if gpu:
            memory_total = gpu.get("memory_total") or 0
            detail = gpu.get("name") or gpu.get("source") or "GPU"
            if memory_total:
                detail = f"{gpu.get('memory_used', 0):.0f}/{memory_total:.0f}MB"
            self.gauges["gpu"].update_data(gpu.get("load", 0), detail)
        else:
            self.gauges["gpu"].update_data(0, "N/A")

        partitions = info.get("disk", {}).get("partitions", [])
        selected = self.settings.get("selected_disks", [])
        if selected:
            partitions = [p for p in partitions if disk_matches_selection(p.get("mountpoint"), selected)]
        for partition in partitions:
            key = f"disk:{partition.get('mountpoint')}"
            widget = self.gauges.get(key)
            if widget:
                used = partition["used"] / (1024 ** 3)
                total = partition["total"] / (1024 ** 3)
                widget.update_data(partition["percent"], f"{used:.0f}/{total:.0f}GB")

        network = info.get("network", {})
        recv = network.get("recv_speed", 0)
        sent = network.get("sent_speed", 0)
        self.gauges["network"].update_network_data(sent, recv)
        for widget in self.gauges.values():
            widget.repaint()
        self.panel.update()
        self.panel.repaint()
        self.update()
        self.repaint()
        self.sync_panel_visibility()
        self.redraw_desktop_window()

    def apply_settings(self, settings, persist=True):
        self.settings = dict(settings)
        self.setWindowOpacity(self.settings.get("opacity", 96) / 100)
        interval = max(1, int(self.settings.get("refresh_interval", 1)))
        if hasattr(self, "update_timer"):
            self.update_timer.start(interval * 1000)
        if persist and not self.suspend_persistence:
            self.save_layout_position()
            save_settings(self.settings)
        self.update_tray_labels()
        self.update_data()

    def open_settings(self):
        if self.settings_dialog is not None:
            self.settings_dialog.close()
        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def toggle_layout(self):
        old_layout = self.current_layout_key()
        self.save_layout_position()
        new_layout = "square" if old_layout == "horizontal" else "horizontal"
        if not self.edit_mode:
            self.toggle_layout_from_desktop(new_layout)
            return
        self.settings["layout"] = new_layout
        self.restore_layout_position(new_layout)
        self.apply_settings(self.settings)

    def toggle_layout_from_desktop(self, new_layout):
        logging.info("desktop layout switch begin: %s -> %s", self.current_layout_key(), new_layout)
        self.detach_from_desktop_layer()
        self.edit_mode = True
        self.settings["desktop_mode"] = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.show()
        self.force_show()
        self.sync_panel_visibility()
        QApplication.processEvents()

        self.settings["layout"] = new_layout
        self.restore_layout_position(new_layout)
        self.apply_settings(self.settings, persist=False)
        QApplication.processEvents()

        self.edit_mode = False
        self.settings["desktop_mode"] = True
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.show()
        self.attach_to_desktop_layer()
        self.force_show()
        self.sync_panel_visibility()
        self.update_tray_labels()
        self.save_layout_position()
        save_settings(self.settings)
        logging.info("desktop layout switch end: %s", self.current_layout_key())

    def toggle_autostart(self, checked):
        self.settings["auto_start"] = bool(checked)
        set_autostart(bool(checked))
        save_settings(self.settings)

    def enter_edit_mode(self):
        self.edit_mode = True
        self.settings["desktop_mode"] = False
        self.detach_from_desktop_layer()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.show()
        self.force_show()
        self.sync_panel_visibility()
        self.update_tray_labels()
        save_settings(self.settings)

    def attach_to_desktop(self):
        self.edit_mode = False
        self.settings["desktop_mode"] = True
        self.save_layout_position()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.show()
        self.attach_to_desktop_layer()
        self.force_show()
        self.sync_panel_visibility()
        self.update_tray_labels()
        save_settings(self.settings)

    def toggle_edit_mode(self):
        if self.edit_mode:
            self.attach_to_desktop()
        else:
            self.enter_edit_mode()

    def maintain_desktop_behavior(self):
        if self.edit_mode:
            return
        self.attach_to_desktop_layer()
        self.force_show()

    def get_desktop_parent_hwnd(self):
        user32 = ctypes.windll.user32
        progman = user32.FindWindowW("Progman", None)
        if progman:
            result = ctypes.c_ulong()
            user32.SendMessageTimeoutW(
                progman,
                0x052C,
                0,
                0,
                0x0002,
                1000,
                ctypes.byref(result),
            )

        worker_after_icons = ctypes.c_void_p(0)
        enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_windows(hwnd, lparam):
            shell_view = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
            if shell_view:
                worker_after_icons.value = user32.FindWindowExW(0, hwnd, "WorkerW", None)
                return False
            return True

        user32.EnumWindows(enum_proc_type(enum_windows), 0)
        return worker_after_icons.value or progman or 0

    def attach_to_desktop_layer(self):
        hwnd = int(self.winId())
        if not hwnd:
            return
        try:
            user32 = ctypes.windll.user32
            parent_hwnd = self.get_desktop_parent_hwnd()
            if not parent_hwnd:
                return
            actual_parent = self.get_window_parent(hwnd)
            if self.desktop_parent_hwnd == parent_hwnd and actual_parent == parent_hwnd:
                self.sync_native_window_rect()
                return
            self.apply_desktop_child_style(hwnd)
            user32.SetParent(wintypes.HWND(hwnd), wintypes.HWND(parent_hwnd))
            actual_parent = self.get_window_parent(hwnd)
            if actual_parent != parent_hwnd:
                error = ctypes.get_last_error()
                self.desktop_parent_hwnd = 0
                logging.warning(
                    "attach_to_desktop_layer verification failed hwnd=%s parent=%s actual=%s error=%s",
                    hwnd,
                    parent_hwnd,
                    actual_parent,
                    error,
                )
                return
            self.desktop_parent_hwnd = parent_hwnd
            self.sync_native_window_rect()
            self.sync_panel_visibility()
            logging.info("attached to desktop layer hwnd=%s parent=%s", hwnd, parent_hwnd)
        except Exception:
            logging.exception("attach_to_desktop_layer failed")

    def get_window_parent(self, hwnd):
        ctypes.windll.user32.GetParent.restype = wintypes.HWND
        return int(ctypes.windll.user32.GetParent(wintypes.HWND(hwnd)) or 0)

    def get_window_style(self, hwnd):
        user32 = ctypes.windll.user32
        try:
            user32.GetWindowLongPtrW.restype = ctypes.c_longlong
            return int(user32.GetWindowLongPtrW(wintypes.HWND(hwnd), -16))
        except AttributeError:
            return int(user32.GetWindowLongW(wintypes.HWND(hwnd), -16))

    def set_window_style(self, hwnd, style):
        user32 = ctypes.windll.user32
        try:
            user32.SetWindowLongPtrW(wintypes.HWND(hwnd), -16, ctypes.c_longlong(style))
        except AttributeError:
            user32.SetWindowLongW(wintypes.HWND(hwnd), -16, ctypes.c_long(style))

    def apply_desktop_child_style(self, hwnd):
        style = self.get_window_style(hwnd)
        style = (style | 0x40000000) & ~0x80000000
        self.set_window_style(hwnd, style)

    def apply_top_level_style(self, hwnd):
        style = self.get_window_style(hwnd)
        style = (style | 0x80000000) & ~0x40000000
        self.set_window_style(hwnd, style)

    def sync_native_window_rect(self):
        if not self.desktop_parent_hwnd:
            return
        try:
            flags = 0x0004 | 0x0010 | 0x0040 | 0x0020
            ctypes.windll.user32.SetWindowPos(
                int(self.winId()),
                0,
                int(self.x()),
                int(self.y()),
                int(self.width()),
                int(self.height()),
                flags,
            )
        except Exception:
            logging.exception("sync_native_window_rect failed")

    def redraw_desktop_window(self):
        if not self.desktop_parent_hwnd:
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = wintypes.HWND(int(self.winId()))
            parent = wintypes.HWND(int(self.desktop_parent_hwnd))
            redraw_flags = 0x0001 | 0x0100 | 0x0080 | 0x0004
            user32.InvalidateRect(hwnd, None, True)
            user32.RedrawWindow(hwnd, None, None, redraw_flags)
            user32.UpdateWindow(hwnd)
            user32.InvalidateRect(parent, None, False)
            user32.RedrawWindow(parent, None, None, redraw_flags)
        except Exception:
            logging.exception("redraw_desktop_window failed")

    def detach_from_desktop_layer(self):
        if not self.desktop_parent_hwnd:
            return
        hwnd = int(self.winId())
        try:
            ctypes.windll.user32.SetParent(wintypes.HWND(hwnd), wintypes.HWND(0))
            self.apply_top_level_style(hwnd)
            logging.info("detached from desktop layer hwnd=%s", hwnd)
        except Exception:
            logging.exception("detach_from_desktop_layer failed")
        self.desktop_parent_hwnd = 0
        self.sync_panel_visibility()

    def force_show(self):
        self.show()
        hwnd = int(self.winId())
        try:
            user32 = ctypes.windll.user32
            flags = 0x0001 | 0x0002 | 0x0010 | 0x0040
            hwnd_topmost = -1
            hwnd_notopmost = -2
            user32.ShowWindow(hwnd, 5)
            if self.edit_mode:
                user32.SetWindowPos(hwnd, hwnd_topmost, 0, 0, 0, 0, flags)
            elif self.desktop_parent_hwnd:
                self.sync_native_window_rect()
            elif not self.desktop_parent_hwnd:
                user32.SetWindowPos(hwnd, hwnd_notopmost, 0, 0, 0, 0, flags)
            now = time.time()
            if now - self.last_force_show_log > 30:
                self.last_force_show_log = now
                logging.info(
                    "force show hwnd=%s visible=%s rect=(%s,%s,%s,%s)",
                    hwnd,
                    self.isVisible(),
                    self.x(),
                    self.y(),
                    self.width(),
                    self.height(),
                )
        except Exception:
            logging.exception("force_show failed")

    def sync_panel_visibility(self):
        if not hasattr(self, "panel"):
            return
        use_desktop_paint = bool(self.desktop_parent_hwnd and not self.edit_mode)
        self.panel.setVisible(not use_desktop_paint)
        self.update()

    def paintEvent(self, event):
        if not (self.desktop_parent_hwnd and not self.edit_mode and self.gauge_keys):
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        columns, _, _, _ = self.layout_metrics(len(self.gauge_keys), self.current_layout_key())
        for index, key in enumerate(self.gauge_keys):
            widget = self.gauges.get(key)
            if not widget:
                continue
            row = index // columns
            column = index % columns
            x = column * (GAUGE_WIDTH + GAUGE_GAP)
            y = row * (GAUGE_HEIGHT + GAUGE_GAP)
            widget.draw_card(painter, QRectF(x + 0.5, y + 0.5, GAUGE_WIDTH - 1, GAUGE_HEIGHT - 1))

    def quit_application(self):
        self.save_layout_position()
        save_settings(self.settings)
        if self.tray_icon:
            self.tray_icon.hide()
        if hasattr(self, "shared_memory"):
            self.shared_memory.detach()
        QApplication.quit()

    def closeEvent(self, event):
        self.quit_application()
        event.accept()

    def mousePressEvent(self, event):
        if self.edit_mode and event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.edit_mode and self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.edit_mode:
            self.save_layout_position()
            save_settings(self.settings)
        self.drag_position = None


def main():
    global FONT_FAMILY
    logging.info("application starting")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    FONT_FAMILY = load_local_fonts()
    logging.info("font family loaded: %s", FONT_FAMILY)
    QApplication.setFont(make_font(9))

    window = MainWindow()
    logging.info("main window created")
    window.show()
    if window.settings.get("desktop_mode", False):
        window.attach_to_desktop_layer()
    window.force_show()
    logging.info(
        "main window shown visible=%s rect=(%s,%s,%s,%s)",
        window.isVisible(),
        window.x(),
        window.y(),
        window.width(),
        window.height(),
    )

    def cleanup():
        if hasattr(window, "shared_memory"):
            window.shared_memory.detach()

    app.aboutToQuit.connect(cleanup)
    result = app.exec_()
    logging.info("application exited: %s", result)
    return result


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        logging.exception("fatal error")
        raise
