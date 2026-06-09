"""
UI Layer – Main Window
=======================
SRP: MainWindow chỉ điều phối giao tiếp giữa các panel và services.
DIP: Nhận services qua constructor injection (không tạo ở đây).

Cải thiện UX so với file gốc:
- Dark theme chuyên nghiệp
- LED indicator trạng thái kết nối
- Chart live ngay khi kết nối (không cần nhấn ghi)
- Hiển thị Min/Max giá trị
- Auto-save cấu hình khi đóng app
- Logging chuẩn thay vì print()
"""

import logging
import threading
import time
from datetime import datetime
from typing import List, Optional, Any, cast

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QSplitter, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget, QToolButton,
)

import serial.tools.list_ports

from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from application.config_service import ConfigService
from application.data_collector import DataCollectorService
from application.interfaces import IDataExporter, ISettingsRepository
from domain.constants import (
    CMD_RESTART, CMD_TARE, CMD_TARE_RAM, FILTER_LABELS, UNITS,
    DEFAULT_SAMPLE_INTERVAL_MS, DEFAULT_TIME_WINDOW_S,
    BAUD_LABELS, PARITY_LABELS, SPS_LABELS
)
from domain.entities import (
    ConnectionConfig, DeviceConfig, DeviceStatus,
    RecordingSession, SampleData,
)
from domain.plc_protocol import PlcTestConfig, angle_to_x100, speed_to_x100
from ui.widgets.realtime_plot import RealTimePlot
from ui.widgets.torque_angle_plot import TorqueAnglePlot

# Plot Viewer & Converter (tái sử dụng từ draw_plot.py)
import os
import sys
import tempfile

# Thêm thư mục draw_plot vào sys.path để lazy import Plot Viewer khi cần.
_cur_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_dir = os.path.dirname(os.path.dirname(_cur_dir))
_draw_plot_path = os.path.join(_workspace_dir, "draw_plot")
if _draw_plot_path not in sys.path:
    sys.path.insert(0, _draw_plot_path)
_HAS_PLOT_VIEWER = True

logger = logging.getLogger(__name__)

# ===================== THEMES =====================
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 14px;
    padding: 14px 8px 8px 8px;
    color: #89b4fa;
    font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
QPushButton {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 6px 14px;
    color: #cdd6f4;
}
QPushButton:hover  { background: #45475a; border-color: #89b4fa; }
QPushButton:pressed { background: #585b70; }
QPushButton:disabled { color: #6c7086; background: #181825; }
QComboBox {
    background: #181825;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 6px;
    color: #cdd6f4;
}
QSpinBox, QDoubleSpinBox {
    background: #181825;
    border: 1px solid #45475a;
    padding: 4px;
    color: #cdd6f4;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #181825;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QTabWidget::pane { border: 1px solid #45475a; border-radius: 4px; }
QTabBar::tab {
    background: #181825;
    color: #a6adc8;
    padding: 6px 10px;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #313244; color: #89b4fa; font-weight: bold; border-top: 2px solid #89b4fa;}
QTabBar::tab:hover:!selected { background: #313244; }
QTextEdit {
    background: #11111b;
    color: #a6e3a1;
    border: 1px solid #313244;
    font-family: Consolas, monospace;
    font-size: 9pt;
}
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #45475a; background: #181825; }
QCheckBox::indicator:checked { background: #89b4fa; border-color: #89b4fa; }
QSplitter::handle { background: #313244; width: 2px; }
QScrollBar:vertical { background: #181825; width: 6px; border-radius: 3px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #585b70; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""

LIGHT_STYLE = """
QMainWindow, QWidget {
    background-color: #f4f6f9;
    color: #212121;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px 10px 10px 10px;
    color: #1976d2;
    font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
QPushButton {
    background: #e3f2fd;
    border: 1px solid #bbdefb;
    border-radius: 4px;
    padding: 6px 14px;
    color: #1565c0;
    font-weight: medium;
}
QPushButton:hover  { background: #bbdefb; border-color: #1976d2; }
QPushButton:pressed { background: #90caf9; }
QPushButton:disabled { color: #9e9e9e; background: #f5f5f5; border: 1px solid #e0e0e0; }
QComboBox {
    background: #ffffff;
    border: 1px solid #dcdcdc;
    border-radius: 4px;
    padding: 4px 6px;
    color: #212121;
}
QSpinBox, QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #dcdcdc;
    padding: 4px;
    color: #212121;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #212121;
    selection-background-color: #bbdefb;
}
QTabWidget::pane { border: 1px solid #e0e0e0; border-radius: 4px; background: #ffffff; }
QTabBar::tab {
    background: #e0e0e0;
    color: #757575;
    padding: 6px 10px;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected { 
    background: #ffffff; 
    color: #1976d2; 
    font-weight: bold; 
    border-top: 2px solid #1976d2;
}
QTabBar::tab:hover:!selected { background: #eeeeee; }
QTextEdit {
    background: #ffffff;
    color: #1b5e20;
    border: 1px solid #e0e0e0;
    font-family: Consolas, monospace;
    font-size: 9pt;
}
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #bdbdbd; background: white; }
QCheckBox::indicator:checked { background: #1976d2; border-color: #1976d2; }
QSplitter::handle { background: #e0e0e0; width: 2px; }
QScrollArea { background-color: transparent; border: none; }
QScrollBar:vertical { background: #f1f1f1; width: 6px; margin: 0; border-radius: 3px; }
QScrollBar::handle:vertical { background: #c1c1c1; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #a8a8a8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""


from PyQt5.QtWidgets import QAction, QStyle

class CustomToolbar(NavigationToolbar):
    """Custom Toolbar: Loại bỏ nút Subplot và thêm nút Zoom Out."""
    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)
        
        # 1. Loại bỏ nút 'Configure subplots'
        actions = self.actions()
        # Các từ khóa cần loại bỏ (ví dụ 'Configure subplots', 'Customize', 'Figure options')
        blacklist = ('subplot', 'configure', 'custom', 'figure', 'options', 'edit')
        for action in actions:
            tip = (action.toolTip() or '').lower()
            txt = (action.text() or '').lower()
            if any(k in tip or k in txt for k in blacklist):
                try:
                    self.removeAction(action)
                except Exception:
                    pass
        
        # 2. Thêm nút 'Zoom Out'
        self.zoom_out_act = QAction("Zoom Out", self)
        # Sử dụng icon chuẩn SP_TitleBarMinButton (dấu trừ) làm biểu tượng Zoom Out
        style = QApplication.style()
        if style is not None:
            minus_icon = getattr(QStyle, 'SP_TitleBarMinButton', getattr(QStyle, 'SP_TitleBarShadeButton', 20))
            self.zoom_out_act.setIcon(style.standardIcon(minus_icon))
        self.zoom_out_act.setToolTip("Zoom Out (1.25x)")
        self.zoom_out_act.triggered.connect(self.zoom_out)
        
        # Chèn Zoom Out sau nút Zoom chuẩn nếu tìm thấy
        zoom_action = None
        actions = self.actions() # Lấy lại danh sách sau khi đã xóa subplot
        for action in actions:
            if 'zoom' in action.toolTip().lower() and 'rect' in action.toolTip().lower():
                zoom_action = action
                break
        
        if zoom_action:
            found = False
            for i, action in enumerate(actions):
                if action == zoom_action:
                    if i + 1 < len(actions):
                        next_action = actions[i+1]
                        self.insertAction(next_action, self.zoom_out_act)
                        found = True
                    break
            if not found:
                self.addAction(self.zoom_out_act)
        else:
            self.addAction(self.zoom_out_act)

    def zoom_out(self):
        """Thu nhỏ biểu đồ bằng cách mở rộng giới hạn các trục."""
        if not self.canvas.figure.axes:
            return
        ax = self.canvas.figure.axes[0]
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        factor = 1.25 # Hệ số phóng đại vùng nhìn (tương đương zoom out)
        x_center = (xlim[0] + xlim[1]) / 2
        y_center = (ylim[0] + ylim[1]) / 2
        
        new_w = (xlim[1] - xlim[0]) * factor
        new_h = (ylim[1] - ylim[0]) * factor
        
        ax.set_xlim((x_center - new_w/2, x_center + new_w/2))
        ax.set_ylim((y_center - new_h/2, y_center + new_h/2))
        
        self.canvas.draw()


from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox

class ServoSetupDialog(QDialog):
    def __init__(self, parent, settings_repo, part_name, test_item, i18n):
        super().__init__(parent)
        self._settings = settings_repo
        self._part_name = part_name
        self._test_item = test_item
        self.i18n = i18n
        self._build_ui()
        
    def _build_ui(self):
        self.setWindowTitle(self.i18n.t('btn_servo_setup'))
        self.resize(320, 310)
        
        # Style sheet matching parent theme
        parent = cast(Any, self.parent())
        is_dark = bool(getattr(parent, '_is_dark', False)) if parent else False
        self.setStyleSheet(DARK_STYLE if is_dark else LIGHT_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Header info
        self.lbl_info = QLabel(f"Profile: {self._part_name}\n?? Mode: {self._test_item}")
        self.lbl_info.setStyleSheet("font-weight: bold; color: #89b4fa;" if is_dark else "font-weight: bold; color: #1976d2;")
        layout.addWidget(self.lbl_info)
        
        form = QFormLayout()
        form.setSpacing(8)
        
        # Load profile
        part_map = {
            'Inner Tie Rod': 'ITR', 'Ball Joint': 'B/Joint', 'Outer Tie Rod': 'OTR', 'Stabilizer Link': 'S/Link',
            'ITR': 'ITR', 'B/Joint': 'B/Joint', 'OTR': 'OTR', 'S/Link': 'S/Link'
        }
        part_short = part_map.get(self._part_name, 'ITR')
        is_breakaway = "Breakaway" in self._test_item or "B" == self._test_item
        test_char = 'B' if is_breakaway else 'O'
        self._profile_key = f"{part_short}_{test_char}"
        
        profiles = self._settings.load_servo_profiles()
        profile = profiles.get(self._profile_key)
        if not profile:
            from domain.entities import ServoProfile
            profile = ServoProfile(
                negative_angle=-36.0,
                positive_angle=36.0,
                speed=100.0  # 100 rpm = 30 deg/s
            )
            
        # Speed unit selection
        self.combo_speed_unit = QComboBox()
        deg_symbol = chr(176)
        self.combo_speed_unit.addItems(["rpm", f"{deg_symbol}/s"])
        
        # Speed input
        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setDecimals(1)
        
        # Jog Speed input
        self.spin_jog_speed = QDoubleSpinBox()
        self.spin_jog_speed.setRange(0.1, 200.0)
        self.spin_jog_speed.setDecimals(1)
        self.spin_jog_speed.setValue(getattr(profile, 'jog_speed', 10.0))
        self.spin_jog_speed.setSuffix(" rpm")
        
        # Label for dynamic converted speed value (grayed out)
        self.lbl_converted_speed = QLabel()
        self.lbl_converted_speed.setStyleSheet("color: #7f8c8d; font-style: italic; font-size: 9pt;")
        
        def update_converted_label():
            val = self.spin_speed.value()
            unit_idx = self.combo_speed_unit.currentIndex()
            if unit_idx == 0:  # rpm input
                converted_degs = val * 0.3
                pulses_s = (val / 60.0) * 10000.0
                self.lbl_converted_speed.setText(f"~ {converted_degs:.1f} °/s ({pulses_s:,.0f} pul/s)")
            else:  # deg/s input
                converted_rpm = val / 0.3
                pulses_s = (converted_rpm / 60.0) * 10000.0
                self.lbl_converted_speed.setText(f"~ {converted_rpm:.1f} rpm ({pulses_s:,.0f} pul/s)")

        # Helper conversions (Ratio 1/20 -> output deg/s = motor rpm * 0.3)
        def on_unit_changed(unit_idx):
            current_val = self.spin_speed.value()
            if unit_idx == 0:  # Changed to rpm
                self.spin_speed.setRange(0.1, 200.0)
                self.spin_speed.setSuffix(" rpm")
                self.spin_speed.setValue(current_val / 0.3)
            else:  # Changed to deg/s
                self.spin_speed.setRange(0.1, 60.0)
                self.spin_speed.setSuffix(f" {deg_symbol}/s")
                self.spin_speed.setValue(current_val * 0.3)
            update_converted_label()

        self.combo_speed_unit.currentIndexChanged.connect(on_unit_changed)
        self.spin_speed.valueChanged.connect(lambda _: update_converted_label())
        
        # Set default values: default to deg/s (index 1)
        self.combo_speed_unit.blockSignals(True)
        self.spin_speed.setRange(0.1, 60.0)
        self.spin_speed.setSuffix(f" {deg_symbol}/s")
        self.spin_speed.setValue(profile.speed * 0.3)
        self.combo_speed_unit.setCurrentIndex(1)
        self.combo_speed_unit.blockSignals(False)
        update_converted_label()
        
        # Positive Angle
        self.spin_pos = QDoubleSpinBox()
        self.spin_pos.setRange(0.0, 360.0)
        self.spin_pos.setDecimals(1)
        self.spin_pos.setValue(profile.positive_angle)
        self.spin_pos.setSuffix(f" {deg_symbol}")
        
        # Label hi?n th? s? xung t??ng ?ng g?c d??ng
        self.lbl_pos_pulses = QLabel()
        self.lbl_pos_pulses.setStyleSheet("color: #7f8c8d; font-style: italic; font-size: 9pt;")
        
        # Negative Angle
        self.spin_neg = QDoubleSpinBox()
        self.spin_neg.setRange(-360.0, 0.0)
        self.spin_neg.setDecimals(1)
        self.spin_neg.setValue(profile.negative_angle)
        self.spin_neg.setSuffix(f" {deg_symbol}")
        # Góc nghịch nhập dạng âm; mặc định -36° (hiển thị là 36° nghịch).
        self.spin_neg.setToolTip("Góc nghịch nhập giá trị âm, ví dụ -36°")
            
        # Label hiển thị số xung tương ứng góc âm
        self.lbl_neg_pulses = QLabel()
        self.lbl_neg_pulses.setStyleSheet("color: #7f8c8d; font-style: italic; font-size: 9pt;")
        
        # Cycles (Số chu kỳ)
        self.spin_cycles = QSpinBox()
        self.spin_cycles.setRange(1, 100)
        self.spin_cycles.setValue(getattr(profile, 'cycles', 3))
        self.spin_cycles.setSuffix(" chu kỳ" if self.i18n.current_language == 'vi' else " cycles")
        
        # Hàm cập nhật số xung hiển thị
        # 360 độ ứng với 200000 xung (555.5556 pulse / độ)
        def update_pulses_labels():
            pos_pulses = int(round(self.spin_pos.value() * 200000 / 360.0))
            neg_pulses = int(round(self.spin_neg.value() * 200000 / 360.0))
            self.lbl_pos_pulses.setText(f"~ {pos_pulses} pulses")
            self.lbl_neg_pulses.setText(f"~ {neg_pulses} pulses")
                
        self.spin_pos.valueChanged.connect(lambda _: update_pulses_labels())
        self.spin_neg.valueChanged.connect(lambda _: update_pulses_labels())
        update_pulses_labels()
            
        # Labels
        self.lbl_speed = QLabel("Vận tốc (speed):" if self.i18n.current_language == 'vi' else "Speed:")
        self.lbl_jog_speed = QLabel("Tốc độ JOG:" if self.i18n.current_language == 'vi' else "JOG Speed:")
        self.lbl_pos = QLabel("Gốc thuận (+):" if self.i18n.current_language == 'vi' else "Pos Angle (+):")
        self.lbl_neg = QLabel("Gốc nghịch (-):" if self.i18n.current_language == 'vi' else "Neg Angle (-):")
        self.lbl_cycles = QLabel("Số chu kỳ:" if self.i18n.current_language == 'vi' else "Cycles:")
        
        form.addRow(self.lbl_speed, self.spin_speed)
        form.addRow("", self.lbl_converted_speed)
        form.addRow("Đơn vị tốc độ:" if self.i18n.current_language == "vi" else "Speed Unit:", self.combo_speed_unit)
        form.addRow(self.lbl_jog_speed, self.spin_jog_speed)
        form.addRow(self.lbl_pos, self.spin_pos)
        form.addRow("", self.lbl_pos_pulses)
        form.addRow(self.lbl_neg, self.spin_neg)
        form.addRow("", self.lbl_neg_pulses)
        form.addRow(self.lbl_cycles, self.spin_cycles)
        layout.addLayout(form)
        
        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        
    def get_values(self):
        val = self.spin_speed.value()
        # If input unit is deg/s (index 1), convert to rpm before saving
        rpm_val = val / 0.3 if self.combo_speed_unit.currentIndex() == 1 else val
        return {
            'speed': round(rpm_val, 2),
            'jog_speed': round(self.spin_jog_speed.value(), 2),
            'positive_angle': self.spin_pos.value(),
            'negative_angle': self.spin_neg.value(),
            'cycles': self.spin_cycles.value()
        }


class ModbusStatusDialog(QDialog):
    def __init__(self, parent, client, slave_id, i18n):
        super().__init__(parent)
        self._client = client
        self._slave_id = slave_id
        self.i18n = i18n
        self._build_ui()
        self._refresh_data()

    def _build_ui(self):
        self.setWindowTitle(self.i18n.t('modbus_status_title'))
        self.resize(520, 500)
        
        parent = cast(Any, self.parent())
        is_dark = bool(getattr(parent, '_is_dark', False)) if parent else False
        self.setStyleSheet(parent.styleSheet() if parent else '')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header = QLabel("📊 Modbus RTU Communication Status (D200..D242)")
        header.setStyleSheet("font-weight: bold; font-size: 11pt; color: #1976d2;")
        if is_dark:
            header.setStyleSheet("font-weight: bold; font-size: 11pt; color: #89b4fa;")
        layout.addWidget(header)

        grp_counters = QGroupBox("Bộ đếm lỗi & Sự kiện (D200..D210)")
        form = QFormLayout(grp_counters)
        form.setSpacing(6)

        self.lbl_d200 = QLabel("-")
        self.lbl_d201 = QLabel("-")
        self.lbl_d202 = QLabel("-")
        self.lbl_d207 = QLabel("-")
        self.lbl_d208 = QLabel("-")
        self.lbl_d210 = QLabel("-")

        form.addRow("D200 (Số lượng tin nhắn trên Bus):", self.lbl_d200)
        form.addRow("D201 (Số lượng lỗi truyền thông):", self.lbl_d201)
        form.addRow("D202 (Số lỗi ngoại lệ Exception):", self.lbl_d202)
        form.addRow("D207 (Số lần tràn ký tự Overrun):", self.lbl_d207)
        form.addRow("D208 (Số lần giao tiếp thành công):", self.lbl_d208)
        form.addRow("D210 (Độ dài nhật ký sự kiện):", self.lbl_d210)
        layout.addWidget(grp_counters)

        grp_log = QGroupBox("Nhật ký sự kiện (Event Log D211..D242)")
        log_lay = QVBoxLayout(grp_log)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 9))
        log_lay.addWidget(self.txt_log)
        layout.addWidget(grp_log)

        btn_layout = QHBoxLayout()
        self.chk_auto = QCheckBox("Tự động làm mới (1s)")
        btn_layout.addWidget(self.chk_auto)
        
        btn_layout.addStretch()
        
        self.btn_refresh = QPushButton("Làm mới")
        self.btn_refresh.clicked.connect(self._refresh_data)
        btn_layout.addWidget(self.btn_refresh)
        
        self.btn_close = QPushButton("Đóng")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()

    def _on_timer_tick(self):
        if self.chk_auto.isChecked():
            self._refresh_data()

    def _refresh_data(self):
        if not self._client or not self._client.is_connected():
            self.lbl_d200.setText("Chưa kết nối Modbus")
            self.txt_log.setText("Vui lòng kết nối Modbus trước khi đọc trạng thái.")
            return

        try:
            regs = self._client.read_registers(200, 43, self._slave_id)
            if regs is None or len(regs) < 43:
                self.lbl_d200.setText("Lỗi đọc thanh ghi (No Response)")
                return

            self.lbl_d200.setText(str(regs[0]))  # D200
            self.lbl_d201.setText(str(regs[1]))  # D201
            self.lbl_d202.setText(str(regs[2]))  # D202
            self.lbl_d207.setText(str(regs[7]))  # D207
            self.lbl_d208.setText(str(regs[8]))  # D208
            
            log_len = regs[10] # D210
            self.lbl_d210.setText(f"{log_len} bytes")

            log_lines = []
            event_bytes = []
            for i in range(11, 43):
                val = regs[i]
                high_byte = (val >> 8) & 0xFF
                low_byte = val & 0xFF
                event_bytes.append(high_byte)
                event_bytes.append(low_byte)

            display_count = min(log_len, len(event_bytes))
            for idx in range(display_count):
                b = event_bytes[idx]
                if b == 0:
                    continue
                evt_desc = self._decode_event_byte(b)
                log_lines.append(f"Sự kiện {idx+1:02d}: Code 0x{b:02X} - {evt_desc}")

            if not log_lines:
                self.txt_log.setText("Không có sự kiện nào được ghi nhận.")
            else:
                self.txt_log.setText("\n".join(log_lines))

        except Exception as e:
            self.txt_log.setText(f"Lỗi khi truy vấn dữ liệu: {e}")

    def _decode_event_byte(self, b: int) -> str:
        parts = []
        if b & 0x80:
            parts.append("Nhận (Rx)")
        else:
            parts.append("Gửi (Tx)")
            
        if b & 0x40:
            parts.append("Lỗi ngoại lệ (Exception)")
        if b & 0x20:
            parts.append("Tràn ký tự (Overrun)")
        if b & 0x10:
            parts.append("Lỗi khung truyền (Framing)")
        if b & 0x08:
            parts.append("Lỗi Parity")
        if b & 0x04:
            parts.append("Lỗi CRC")
            
        if not parts or (b & 0x7F) == 0:
            return "Truyền thông bình thường (Normal)"
        return ", ".join(parts)


class SamplingSettingsDialog(QDialog):
    def __init__(self, parent, interval_ms: int, window_s: int, y_max: float, fixed_y: bool, i18n):
        super().__init__(parent)
        self.i18n = i18n
        self._interval_ms = interval_ms
        self._window_s = window_s
        self._y_max = y_max
        self._fixed_y = fixed_y
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("Sampling Setting")
        self.resize(340, 220)
        parent = cast(Any, self.parent())
        is_dark = bool(getattr(parent, '_is_dark', False)) if parent else False
        self.setStyleSheet(DARK_STYLE if is_dark else LIGHT_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        info = QLabel("⏱️ Cài đặt lấy mẫu & biểu đồ")
        info.setStyleSheet("font-weight: bold; color: #89b4fa;" if is_dark else "font-weight: bold; color: #1976d2;")
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(8)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 10000)
        self.spin_interval.setValue(self._interval_ms)
        self.spin_interval.setSuffix(" ms")

        self.spin_window = QSpinBox()
        self.spin_window.setRange(10, 600)
        self.spin_window.setValue(self._window_s)
        self.spin_window.setSuffix(" s")

        self.spin_ymax = QDoubleSpinBox()
        self.spin_ymax.setRange(0.1, 10000)
        self.spin_ymax.setDecimals(1)
        self.spin_ymax.setValue(self._y_max)
        self.spin_ymax.setSuffix(" Nm")

        self.chk_fixed_y = QCheckBox("Cố định thang đo Y")
        self.chk_fixed_y.setChecked(self._fixed_y)

        form.addRow("Chu kỳ lấy mẫu:", self.spin_interval)
        form.addRow("Cửa sổ biểu đồ:", self.spin_window)
        form.addRow("Giới hạn Y:", self.spin_ymax)
        form.addRow("", self.chk_fixed_y)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_values(self):
        return {
            'interval_ms': self.spin_interval.value(),
            'window_s': self.spin_window.value(),
            'y_max': self.spin_ymax.value(),
            'fixed_y': self.chk_fixed_y.isChecked(),
        }


class MainWindow(QMainWindow):
    """
    MainWindow điều phối toàn bộ ứng dụng.
    Services được inject từ bên ngoài (DIP).
    """
    # Qt signals cho thread-safe UI update và servo control
    _sig_status = pyqtSignal(DeviceStatus)
    _sig_error  = pyqtSignal(str)
    _sig_plc_status = pyqtSignal(object)
    _sig_plc_angle = pyqtSignal(float)
    _sig_plc_command_result = pyqtSignal(str, bool)
    _sig_servo_finished = pyqtSignal()
    _sig_servo_error = pyqtSignal(str)

    def __init__(
        self,
        collector: DataCollectorService,
        config_svc: ConfigService,
        exporters: List[IDataExporter],
        settings_repo: ISettingsRepository,
        conn_config: ConnectionConfig,
        dev_config: DeviceConfig,
        servo_svc: Optional[Any] = None,
        plc_svc: Optional[Any] = None,
        measurement_svc: Optional[Any] = None,
        report_svc: Optional[Any] = None,
        bus_scheduler: Optional[Any] = None,
    ):
        super().__init__()
        # === Inject dependencies ===
        self._collector   = collector
        self._config_svc  = config_svc
        self._exporters   = exporters
        self._settings    = settings_repo
        self._conn_cfg    = conn_config
        self._dev_cfg     = dev_config
        self._servo_svc   = servo_svc
        self._plc_svc     = plc_svc
        self._measurement_svc = measurement_svc
        self._report_svc  = report_svc
        self._bus_scheduler = bus_scheduler

        if self._plc_svc and self._bus_scheduler:
            self._plc_svc.set_scheduler(self._bus_scheduler)

        # Lưu lại null clients để swap khi disconnect
        self._null_sensor_client = self._collector._client
        self._null_plc_client = self._plc_svc._client if self._plc_svc else None

        # === Trạng thái nội bộ ===
        self._connected   = False
        self._recording   = False
        self._session     = RecordingSession()
        self._last_status: Optional[DeviceStatus] = None # Lưu status cuối cùng
        self._start_time  = 0.0
        self._ref_time    = 0.0     # Thời gian gốc cho biểu đồ
        self._only_stable = True
        self._chk_stable_only: Optional[QCheckBox] = None
        self._chart_paused = False  # Trạng thái đóng băng biểu đồ
        self._current_angle = 0.0
        self._current_cycle = 0
        self._last_plc_status = None
        self._plc_status_error_logged = False
        self._plc_status_fail_count = 0
        self._jog_active = False
        self._jog_direction = 0
        self._jog_started_at = 0.0
        self._jog_start_angle = 0.0
        self._plc_status_polling = False
        self._plc_angle_polling = False
        self._plc_poll_lock = threading.Lock()
        self._plc_poll_running = False
        self._plc_poll_thread = None
        self._plc_status_interval_s = 0.15
        # Không đọc D124 riêng 50ms nữa vì làm nghẽn Modbus mô phỏng/RTU.
        # Angle sẽ lấy từ block D120..D135 trong cùng vòng đọc status.
        self._plc_angle_interval_s = 0.15
        self._plc_command_running = False

        # === Qt signals → UI callbacks ===
        self._sig_status.connect(self._on_status_received)
        self._sig_error.connect(self._on_error)
        self._sig_plc_status.connect(self._on_plc_status_received)
        self._sig_plc_angle.connect(self._on_plc_angle_received)
        self._sig_plc_command_result.connect(self._on_plc_command_result)
        self._sig_servo_finished.connect(self._handle_servo_finished)
        self._sig_servo_error.connect(self._handle_servo_error)

        # === Đăng ký callback cho data source ===
        if self._bus_scheduler:
            self._bus_scheduler.on_sensor_data(lambda s: self._sig_status.emit(s))
            self._bus_scheduler.on_plc_status(lambda s: self._sig_plc_status.emit(s))
            self._bus_scheduler.on_command_result(lambda name, ok: self._sig_plc_command_result.emit(name, ok))
            self._bus_scheduler.on_error(lambda e: self._sig_error.emit(e))
        else:
            self._collector.on_data(lambda s: self._sig_status.emit(s))
            self._collector.on_error(lambda e: self._sig_error.emit(e))

        # === Đăng ký callback cho ServoService nếu có ===
        if self._servo_svc:
            self._servo_svc.register_callbacks(
                on_angle_updated=self._on_servo_angle_updated,
                on_finished=self._on_servo_finished,
                on_error=self._on_servo_error
            )

        # Theme & Ngôn ngữ state (load từ settings)
        ui_cfg = settings_repo.load_ui_settings()
        self._is_dark = ui_cfg.get('dark_theme', False)

        from ui.i18n import I18n
        lang = ui_cfg.get('language', 'vi')
        self.i18n = I18n(lang)

        self._build_ui()
        self._load_settings_to_ui()
        self._apply_theme(self._is_dark)
        self._retranslate_ui()

        # Real-time bi-directional synchronization between Thu thập tab and Plot Viewer tab
        if hasattr(self, '_plot_viewer') and hasattr(self, 'combo_part_name') and _HAS_PLOT_VIEWER:
            self.combo_part_name.currentTextChanged.connect(self._sync_part_name_to_plot_viewer)
            self._plot_viewer.part_name_combo.currentTextChanged.connect(self._sync_part_name_to_acquisition)
            
        if hasattr(self, '_plot_viewer') and hasattr(self, 'combo_test_item') and _HAS_PLOT_VIEWER:
            self.combo_test_item.currentTextChanged.connect(self._sync_test_item_to_plot_viewer)
            self._plot_viewer.test_item_combo.currentTextChanged.connect(self._sync_test_item_to_acquisition)

        if hasattr(self, 'combo_part_name'):
            self.combo_part_name.currentTextChanged.connect(self._update_jog_speed_from_profile)
        if hasattr(self, 'combo_test_item'):
            self.combo_test_item.currentTextChanged.connect(self._update_jog_speed_from_profile)
        self._update_jog_speed_from_profile()

        # PLC polling chạy bằng background thread giống DataCollectorService.
        # Không dùng QTimer để tránh UI thread bị chặn khi Modbus RTU timeout/bận.

    def set_app_icon(self, icon_path: str):
        """Set app/window icon and show the same icon on the status bar."""
        if not icon_path or not os.path.exists(icon_path):
            return
        icon = QIcon(icon_path)
        if icon.isNull():
            return
        self.setWindowIcon(icon)
        QApplication.setWindowIcon(icon)
        status = self.statusBar()
        status.setSizeGripEnabled(True)
        icon_label = QLabel()
        icon_label.setObjectName("status_app_icon")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon_label.setPixmap(icon.pixmap(QSize(18, 18)))
        icon_label.setToolTip("ZE-SG3 Torque Acquisition")
        status.addPermanentWidget(icon_label)

    # ===========================================================
    # BUILD UI
    # ===========================================================

    def _build_ui(self):
        self.setWindowTitle("Seneca ZE-SG3 – Torque Acquisition (DYJN-101 50Nm)")
        self.setGeometry(80, 80, 1280, 820)
        self.setMinimumSize(960, 650)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # === QTabWidget cấp cao nhất ===
        self.main_tabs = QTabWidget()
        self.main_tabs.setTabPosition(QTabWidget.North)
        root_layout.addWidget(self.main_tabs)

        # -----------------------------------------------
        # Tab 0: Thu thập (toàn bộ layout cũ)
        # -----------------------------------------------
        acq_page = QWidget()
        main_layout = QVBoxLayout(acq_page)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        self.splitter = splitter

        # --- Left Panel ---
        left_panel = QWidget()
        left_panel_lay = QVBoxLayout(left_panel)
        left_panel_lay.setContentsMargins(6, 6, 6, 6)
        left_panel_lay.setSpacing(6)

        # 1. Real-time Data Info (Sticky at top)
        self.display_panel = self._build_display_group()
        left_panel_lay.addWidget(self.display_panel)

        # 2. Tab widget đặt trực tiếp
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_connection_tab(), "🔌 Kết nối")
        self.tabs.addTab(self._build_config_tab(), "⚙️ Cấu hình")
        self.tabs.addTab(self._build_acquisition_tab(), "📈 Thu thập")
        left_panel_lay.addWidget(self.tabs, stretch=1)

        # 3. Connection Status and Button (Sticky at bottom)
        conn_bottom_widget = QWidget()
        conn_bottom_lay = QVBoxLayout(conn_bottom_widget)
        conn_bottom_lay.setContentsMargins(2, 4, 2, 2)
        conn_bottom_lay.setSpacing(4)
        
        btn_row = QHBoxLayout()
        self.led_label = QLabel("●")
        self.led_label.setObjectName("led_off")
        self.led_label.setFont(QFont('Segoe UI', 10))
        btn_row.addWidget(self.led_label)
        
        self.btn_connect = QPushButton("🔗 Kết nối")
        self._update_connect_btn_style()
        self.btn_connect.clicked.connect(self._toggle_connect)
        self.btn_connect.setMinimumHeight(32)
        self.btn_connect.setFont(QFont('Segoe UI', 10, QFont.Bold))
        btn_row.addWidget(self.btn_connect, stretch=1)
        
        conn_bottom_lay.addLayout(btn_row)
        
        self.lbl_conn_status = QLabel("⚪ Chưa kết nối")
        self.lbl_conn_status.setStyleSheet("color: #757575;") 
        conn_bottom_lay.addWidget(self.lbl_conn_status)

        left_panel_lay.addWidget(conn_bottom_widget)

        left_panel.setMinimumWidth(500)
        left_panel.setMaximumWidth(16777215)

        # --- Right Panel ---
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(4, 0, 0, 0)
        right_lay.setSpacing(6)
        
        right_lay.addWidget(self._build_chart_group(), stretch=1)
        right_lay.addWidget(self._build_log_group())
        
        options_lay = QHBoxLayout()

        self.btn_toggle_theme = QPushButton()
        self._update_theme_btn_text()
        self.btn_toggle_theme.setFixedHeight(30)
        self.btn_toggle_theme.clicked.connect(self._toggle_theme)
        options_lay.addWidget(self.btn_toggle_theme)

        self.btn_toggle_lang = QPushButton()
        self._update_language_btn_text()
        self.btn_toggle_lang.setFixedHeight(30)
        self.btn_toggle_lang.clicked.connect(self._toggle_language)
        options_lay.addWidget(self.btn_toggle_lang)

        right_lay.addLayout(options_lay)

        splitter.addWidget(left_panel)
        splitter.addWidget(right)
        splitter.setSizes([420, 860])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)

        self.main_tabs.addTab(acq_page, "📡 Thu thập")

        # -----------------------------------------------
        # Tab 1: Plot Viewer
        # -----------------------------------------------
        if _HAS_PLOT_VIEWER:
            self._plot_viewer_loaded = False
            self._plot_viewer_container = QWidget()
            pv_lay = QVBoxLayout(self._plot_viewer_container)
            pv_lay.setContentsMargins(12, 12, 12, 12)
            pv_lay.addWidget(QLabel("Plot Viewer sẽ được tải khi mở tab này."))
            self.main_tabs.addTab(self._plot_viewer_container, "📊 Plot Viewer")
            self.main_tabs.currentChanged.connect(self._on_main_tab_changed)

    def _on_main_tab_changed(self, index: int):
        """Lazy-load Plot Viewer only when user opens the tab."""
        if index != 1 or getattr(self, '_plot_viewer_loaded', False):
            return
        try:
            from draw_plot import TorquePlotViewer
            self._plot_viewer: Any = TorquePlotViewer()
            layout = self._plot_viewer_container.layout()
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            pv_tab = self._plot_viewer.plot_tab
            pv_tab.setParent(self._plot_viewer_container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(pv_tab)
            if hasattr(self, 'combo_part_name') and hasattr(self._plot_viewer, 'part_name_combo'):
                self.combo_part_name.currentTextChanged.connect(self._sync_part_name_to_plot_viewer)
                self._plot_viewer.part_name_combo.currentTextChanged.connect(self._sync_part_name_to_acquisition)
                self._sync_part_name_to_plot_viewer(self.combo_part_name.currentText())
            if hasattr(self, 'combo_test_item') and hasattr(self._plot_viewer, 'test_item_combo'):
                self.combo_test_item.currentTextChanged.connect(self._sync_test_item_to_plot_viewer)
                self._plot_viewer.test_item_combo.currentTextChanged.connect(self._sync_test_item_to_acquisition)
                self._sync_test_item_to_plot_viewer(self.combo_test_item.currentText())
            self._plot_viewer_loaded = True
        except Exception as exc:
            logger.warning("Không tải được Plot Viewer: %s", exc)

    def showEvent(self, a0):
        """Set initial splitter sizes as a proportion of the window width on first show.

        This ensures the left panel occupies a sensible fraction (e.g. 35%)
        of the window when the app starts, avoiding clipped controls.
        """
        super().showEvent(a0)
        try:
            total = max(800, self.width())
            left_w = max(420, int(total * 0.35))
            right_w = max(300, total - left_w)
            # Apply sizes to splitter
            if hasattr(self, 'splitter'):
                self.splitter.setSizes([left_w, right_w])
        except Exception:
            pass



    # --- Connection Tab ---
    def _build_connection_tab(self) -> QWidget:
        # Create a scroll area wrapper to prevent clipping/squishing
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(getattr(Qt.ScrollBarPolicy, 'ScrollBarAsNeeded', 0))
        scroll.setHorizontalScrollBarPolicy(getattr(Qt.ScrollBarPolicy, 'ScrollBarAlwaysOff', 1))
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(8)

        # Protocol selector (Ẩn đi vì chạy chế độ kép)
        self.grp_proto = QGroupBox("🔌 Giao thức")
        pg = QGridLayout()
        pg.setContentsMargins(6, 8, 6, 6)
        pg.setSpacing(6)
        self.lbl_proto_type = QLabel("Loại:")
        pg.addWidget(self.lbl_proto_type, 0, 0)
        self.combo_proto = QComboBox()
        self.combo_proto.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_proto.setMinimumContentsLength(5)
        self.combo_proto.addItems(["Modbus RTU", "Modbus TCP"])
        self.combo_proto.currentTextChanged.connect(self._on_proto_changed)
        pg.addWidget(self.combo_proto, 0, 1)
        pg.setColumnStretch(1, 1)
        self.grp_proto.setLayout(pg)
        self.grp_proto.setVisible(False) # Ẩn bộ chọn giao thức chung

        # Cấu hình Cảm biến (TCP)
        self.grp_tcp = QGroupBox("🌐 Cấu hình Cảm biến (Modbus TCP)")
        tg = QGridLayout()
        tg.setContentsMargins(6, 8, 6, 6)
        tg.setSpacing(6)
        self.lbl_tcp_ip = QLabel("IP:")
        tg.addWidget(self.lbl_tcp_ip, 0, 0)
        self.combo_ip = QComboBox(); self.combo_ip.setEditable(True)
        self.combo_ip.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_ip.setMinimumContentsLength(5)
        self.combo_ip.addItem("192.168.90.101")  # Cài mặc định theo IP người dùng
        tg.addWidget(self.combo_ip, 0, 1)
        self.lbl_tcp_port = QLabel("Port:")
        tg.addWidget(self.lbl_tcp_port, 1, 0)
        self.spin_tcp_port = QSpinBox(); self.spin_tcp_port.setRange(1,65535)
        self.spin_tcp_port.setValue(502)
        tg.addWidget(self.spin_tcp_port, 1, 1)
        self.grp_tcp.setLayout(tg)
        self.grp_tcp.setVisible(True)  # Luôn hiển thị cấu hình TCP
        lay.addWidget(self.grp_tcp)

        # Cấu hình PLC (RTU)
        self.grp_rtu = QGroupBox("📡 Cấu hình PLC (Modbus RTU)")
        rg = QGridLayout()
        rg.setContentsMargins(6, 8, 6, 6)
        rg.setSpacing(6)
        self.lbl_com_port = QLabel("COM Port:")
        rg.addWidget(self.lbl_com_port, 0, 0)
        self.combo_com = QComboBox()
        self.combo_com.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_com.setMinimumContentsLength(10)
        rg.addWidget(self.combo_com, 0, 1)
        # Use a QToolButton with system reload icon to avoid emoji clipping
        self.btn_scan = QToolButton()
        self.btn_scan.setAutoRaise(True)
        self.btn_scan.setToolTip("Làm mới COM ports")
        icon = QIcon()
        style = QApplication.style()
        if style is not None:
            try:
                icon = style.standardIcon(getattr(QStyle, 'SP_BrowserReload', getattr(QStyle, 'SP_ArrowRight', 54)))
            except Exception:
                icon = style.standardIcon(getattr(QStyle, 'SP_DialogResetButton', getattr(QStyle, 'SP_DialogCancelButton', 17)))
        self.btn_scan.setIcon(icon)
        self.btn_scan.setFixedSize(30, 28)
        self.btn_scan.clicked.connect(self._scan_com_ports)
        rg.addWidget(self.btn_scan, 0, 2)
        self.lbl_baudrate = QLabel("Baudrate:")
        rg.addWidget(self.lbl_baudrate, 1, 0)
        self.combo_baud = QComboBox()
        self.combo_baud.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_baud.setMinimumContentsLength(5)
        self.combo_baud.addItems(["9600","19200","38400","57600","115200"])
        rg.addWidget(self.combo_baud, 1, 1, 1, 2)
        self.lbl_parity = QLabel("Parity:")
        rg.addWidget(self.lbl_parity, 2, 0)
        self.combo_parity = QComboBox()
        self.combo_parity.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_parity.setMinimumContentsLength(5)
        self.combo_parity.addItems(["None (N)","Even (E)","Odd (O)"])
        rg.addWidget(self.combo_parity, 2, 1, 1, 2)
        rg.setColumnStretch(1, 1)
        self.grp_rtu.setLayout(rg)
        self.grp_rtu.setVisible(True)  # Luôn hiển thị cấu hình RTU
        lay.addWidget(self.grp_rtu)

        # Slave ID
        self.grp_slave = QGroupBox("📋 Slave PLC")
        sg = QGridLayout()
        sg.setContentsMargins(6, 8, 6, 6)
        sg.setSpacing(6)
        
        self.lbl_slave_id = QLabel(self.i18n.t('sensor_slave_lbl'))
        self.spin_slave = QSpinBox(); self.spin_slave.setRange(1,247)
        self.spin_slave.setValue(1)
        self.lbl_slave_id.setVisible(False)
        self.spin_slave.setVisible(False)

        self.lbl_plc_slave_id = QLabel(self.i18n.t('plc_slave_lbl'))
        sg.addWidget(self.lbl_plc_slave_id, 0, 0)
        self.spin_plc_slave = QSpinBox(); self.spin_plc_slave.setRange(1,247)
        self.spin_plc_slave.setValue(2)
        sg.addWidget(self.spin_plc_slave, 0, 1)

        sg.setColumnStretch(1, 1)
        self.grp_slave.setLayout(sg); lay.addWidget(self.grp_slave)

        self.btn_modbus_status = QPushButton(self.i18n.t('btn_modbus_status'))
        self.btn_modbus_status.clicked.connect(self._show_modbus_status_dialog)
        self.btn_modbus_status.setStyleSheet("background-color: #313244; color: white; font-weight: bold; padding: 6px;")
        lay.addWidget(self.btn_modbus_status)

        lay.addStretch()
        self._scan_com_ports()
        scroll.setWidget(w)
        return scroll

    # --- Config Tab ---
    def _build_config_tab(self) -> QWidget:
        # Create a scroll area wrapper to prevent clipping/squishing
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(getattr(Qt.ScrollBarPolicy, 'ScrollBarAsNeeded', 0))
        scroll.setHorizontalScrollBarPolicy(getattr(Qt.ScrollBarPolicy, 'ScrollBarAlwaysOff', 1))
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        w = QWidget()
        main_lay = QVBoxLayout(w)
        main_lay.setContentsMargins(4, 4, 4, 4)
        main_lay.setSpacing(8)

        # 1. Nhóm Cảm biến & Hiệu chuẩn
        self.grp_sensor = QGroupBox("📊 Cảm biến & Hiệu chuẩn")
        sg = QGridLayout()
        sg.setContentsMargins(6, 8, 6, 6)
        sg.setSpacing(6)

        self.lbl_measure_unit = QLabel("Đơn vị đo:")
        sg.addWidget(self.lbl_measure_unit, 0, 0)
        self.combo_unit = QComboBox()
        self.combo_unit.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_unit.setMinimumContentsLength(5)
        for k, v in UNITS.items(): self.combo_unit.addItem(f"{k}: {v}", k)
        sg.addWidget(self.combo_unit, 0, 1)

        self.lbl_measure_mode = QLabel("Chế độ đo:")
        sg.addWidget(self.lbl_measure_mode, 1, 0)
        self.combo_mtype = QComboBox()
        self.combo_mtype.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_mtype.setMinimumContentsLength(10)
        self.combo_mtype.addItem(self.i18n.t('measure_mode_0'), 0)
        self.combo_mtype.addItem(self.i18n.t('measure_mode_1'), 1)
        sg.addWidget(self.combo_mtype, 1, 1)

        self.lbl_full_scale = QLabel("Full Scale (Nm):")
        sg.addWidget(self.lbl_full_scale, 2, 0)
        self.spin_fs = QDoubleSpinBox()
        self.spin_fs.setRange(0.1, 1000000); self.spin_fs.setDecimals(2); self.spin_fs.setValue(49.70)
        sg.addWidget(self.spin_fs, 2, 1)

        self.lbl_sensitivity = QLabel("Sensitivity (mV/V):")
        sg.addWidget(self.lbl_sensitivity, 3, 0)
        self.spin_sens = QDoubleSpinBox()
        self.spin_sens.setRange(0.001, 100); self.spin_sens.setDecimals(4); self.spin_sens.setValue(1.9880)
        sg.addWidget(self.spin_sens, 3, 1)

        self.grp_sensor.setLayout(sg); main_lay.addWidget(self.grp_sensor)

        # 2. Nhóm Ổn định & Lọc
        self.grp_stability = QGroupBox("🛡️ Ổn định & Lọc")
        stg = QGridLayout()

        self.lbl_filter_level = QLabel("Mức lọc nhiễu:")
        stg.addWidget(self.lbl_filter_level, 0, 0)
        self.combo_filter = QComboBox()
        self.combo_filter.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_filter.setMinimumContentsLength(10)
        for k in FILTER_LABELS:
            self.combo_filter.addItem(self.i18n.t(f'filter_{k}'), k)
        stg.addWidget(self.combo_filter, 0, 1)

        stg.setContentsMargins(6, 8, 6, 6)
        stg.setSpacing(6)
        self.grp_stability.setLayout(stg)
        main_lay.addWidget(self.grp_stability)


        # Buttons
        btn_row = QHBoxLayout()
        self.btn_write_cfg = QPushButton("📝 Ghi cấu hình")
        self.btn_write_cfg.clicked.connect(self._write_config)
        self.btn_read_cfg  = QPushButton("📖 Đọc từ thiết bị")
        self.btn_read_cfg.clicked.connect(self._read_config)
        btn_row.addWidget(self.btn_write_cfg); btn_row.addWidget(self.btn_read_cfg)
        main_lay.addLayout(btn_row)

        self.grp_quick_cmd = QGroupBox("⚡ Lệnh nhanh")
        cg = QHBoxLayout()
        cg.setContentsMargins(6, 8, 6, 6)
        cg.setSpacing(6)
        self.btn_quick_tare = QPushButton("⚖️ Tare (Zero)")
        self.btn_quick_tare.clicked.connect(self._do_tare)
        self.btn_quick_restart  = QPushButton("🔄 Restart Device")
        self.btn_quick_restart.clicked.connect(self._do_restart)
        cg.addWidget(self.btn_quick_tare); cg.addWidget(self.btn_quick_restart)
        self.grp_quick_cmd.setLayout(cg); main_lay.addWidget(self.grp_quick_cmd)

        main_lay.addStretch()
        scroll.setWidget(w)
        return scroll

    # --- Acquisition Tab ---
    def _build_acquisition_tab(self) -> QWidget:
        # Create a scroll area wrapper to prevent clipping/squishing
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(getattr(Qt.ScrollBarPolicy, 'ScrollBarAsNeeded', 0))
        scroll.setHorizontalScrollBarPolicy(getattr(Qt.ScrollBarPolicy, 'ScrollBarAlwaysOff', 1))
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(8)

        self.grp_sampling = QGroupBox("⏱️ Lấy mẫu")
        sg = QVBoxLayout()
        sg.setContentsMargins(6, 8, 6, 6)
        sg.setSpacing(6)

        self.btn_sampling_settings = QPushButton("⏱️ Sampling Setting")
        self.btn_sampling_settings.setMinimumHeight(34)
        self.btn_sampling_settings.clicked.connect(self._open_sampling_settings)
        sg.addWidget(self.btn_sampling_settings)

        self.lbl_sampling_summary = QLabel()
        self.lbl_sampling_summary.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        sg.addWidget(self.lbl_sampling_summary)

        # Hidden backing widgets keep existing save/load and acquisition logic unchanged.
        self.lbl_sample_interval = QLabel("Chu kỳ (ms):")
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 10000)
        self.spin_interval.setValue(DEFAULT_SAMPLE_INTERVAL_MS)
        self.spin_interval.editingFinished.connect(self._on_acquisition_settings_changed)

        self.lbl_chart_window = QLabel("Cửa sổ biểu đồ (s):")
        self.spin_window = QSpinBox()
        self.spin_window.setRange(10, 600)
        self.spin_window.setValue(60)
        self.spin_window.editingFinished.connect(self._on_acquisition_settings_changed)

        self.lbl_y_limits = QLabel("Giới hạn Y (Nm):")
        self.spin_ymax = QDoubleSpinBox()
        self.spin_ymax.setRange(0.1, 10000)
        self.spin_ymax.setDecimals(1)
        self.spin_ymax.setValue(5.0)
        self.spin_ymax.valueChanged.connect(lambda _: self._update_plot_limits())

        self.chk_fixed_y = QCheckBox("Cố định thang đo Y")
        self.chk_fixed_y.setChecked(True)
        self.chk_fixed_y.toggled.connect(lambda _: self._update_plot_limits())

        for hidden in (
            self.lbl_sample_interval, self.spin_interval,
            self.lbl_chart_window, self.spin_window,
            self.lbl_y_limits, self.spin_ymax, self.chk_fixed_y,
        ):
            hidden.setVisible(False)

        self.grp_sampling.setLayout(sg)
        lay.addWidget(self.grp_sampling)

        # === 1.5. Nhóm Chương trình đo (R2 Upgrades) ===
        self.grp_program = QGroupBox("⚙️ Chương trình đo")
        pg_lay = QGridLayout()
        pg_lay.setContentsMargins(6, 14, 6, 6)
        pg_lay.setSpacing(6)
        
        self.lbl_part_name = QLabel("Sản phẩm:")
        pg_lay.addWidget(self.lbl_part_name, 0, 0)
        self.combo_part_name = QComboBox()
        self.combo_part_name.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_part_name.setMinimumContentsLength(5)
        self.combo_part_name.addItems(["Inner Tie Rod", "Ball Joint", "Outer Tie Rod", "Stabilizer Link"])
        pg_lay.addWidget(self.combo_part_name, 0, 1)
        
        self.lbl_test_item = QLabel("Chế độ đo:")
        pg_lay.addWidget(self.lbl_test_item, 1, 0)
        self.combo_test_item = QComboBox()
        self.combo_test_item.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_test_item.setMinimumContentsLength(5)
        self.combo_test_item.addItems(["Breakaway Torque", "Operating Torque", "Oscillating Torque"])
        pg_lay.addWidget(self.combo_test_item, 1, 1)
        
        self.btn_servo_setup = QPushButton("⚙️ Thiết lập Servo")
        self.btn_servo_setup.clicked.connect(self._on_btn_servo_setup_clicked)
        self.btn_servo_setup.setStyleSheet("background-color: #313244; color: white; font-weight: bold; height: 26px;")
        pg_lay.addWidget(self.btn_servo_setup, 2, 0, 1, 2)
        
        self.grp_program.setLayout(pg_lay)
        lay.addWidget(self.grp_program)

        self.grp_plc_control = QGroupBox("🕹️ PLC / Servo Control")
        pc_lay = QVBoxLayout()
        pc_lay.setContentsMargins(6, 8, 6, 6)
        pc_lay.setSpacing(6)

        row_run = QHBoxLayout()
        row_run.setSpacing(6)
        self.btn_plc_run = QPushButton("▶ RUN")
        self.btn_plc_stop = QPushButton("⏹ STOP")
        self.btn_plc_clamp = QPushButton("🔒 Clamp")
        self.btn_plc_run.clicked.connect(self._plc_start_run)
        self.btn_plc_stop.clicked.connect(self._plc_stop_run)
        self.btn_plc_clamp.clicked.connect(self._plc_toggle_clamp)
        row_run.addWidget(self.btn_plc_run)
        row_run.addWidget(self.btn_plc_stop)
        row_run.addWidget(self.btn_plc_clamp)
        pc_lay.addLayout(row_run)

        row_cmd = QHBoxLayout()
        row_cmd.setSpacing(6)
        self.btn_plc_reset = QPushButton("🔄 Reset")
        self.btn_plc_abort = QPushButton("🛑 Abort")
        self.btn_plc_home = QPushButton("🏠 Home")
        self.btn_plc_reset.clicked.connect(self._plc_reset_fault)
        self.btn_plc_abort.clicked.connect(self._plc_abort)
        self.btn_plc_home.clicked.connect(self._plc_home)
        row_cmd.addWidget(self.btn_plc_reset)
        row_cmd.addWidget(self.btn_plc_abort)
        row_cmd.addWidget(self.btn_plc_home)
        pc_lay.addLayout(row_cmd)

        row_jog_speed = QHBoxLayout()
        row_jog_speed.setSpacing(6)
        self.lbl_plc_jog_speed = QLabel(self.i18n.t('lbl_plc_jog_speed'))
        self.spin_plc_jog_speed = QDoubleSpinBox()
        self.spin_plc_jog_speed.setRange(0.1, 200.0)
        self.spin_plc_jog_speed.setValue(10.0)
        self.spin_plc_jog_speed.setSuffix(" rpm")
        self.spin_plc_jog_speed.valueChanged.connect(self._on_plc_jog_speed_changed)
        row_jog_speed.addWidget(self.lbl_plc_jog_speed)
        row_jog_speed.addWidget(self.spin_plc_jog_speed)
        pc_lay.addLayout(row_jog_speed)

        row_jog = QHBoxLayout()
        row_jog.setSpacing(6)
        self.btn_plc_jog_minus = QPushButton("◀ Jog-")
        self.btn_plc_jog_plus = QPushButton("Jog+ ▶")
        self.btn_plc_jog_minus.pressed.connect(lambda: self._plc_jog_minus(True))
        self.btn_plc_jog_minus.released.connect(lambda: self._plc_jog_minus(False))
        self.btn_plc_jog_plus.pressed.connect(lambda: self._plc_jog_plus(True))
        self.btn_plc_jog_plus.released.connect(lambda: self._plc_jog_plus(False))
        row_jog.addWidget(self.btn_plc_jog_minus)
        row_jog.addWidget(self.btn_plc_jog_plus)
        pc_lay.addLayout(row_jog)

        for btn in (
            self.btn_plc_run, self.btn_plc_stop, self.btn_plc_clamp,
            self.btn_plc_reset, self.btn_plc_abort, self.btn_plc_home,
            self.btn_plc_jog_minus, self.btn_plc_jog_plus,
        ):
            btn.setMinimumHeight(34)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.grp_plc_control.setLayout(pc_lay)
        lay.addWidget(self.grp_plc_control)

        self.grp_recording = QGroupBox("🔴 Ghi dữ liệu")
        rg = QVBoxLayout()
        rg.setContentsMargins(6, 8, 6, 6)
        rg.setSpacing(6)
        
        # Row 1: Start and Stop recording
        btns1 = QHBoxLayout()
        btns1.setSpacing(8)
        self.btn_rec_start = QPushButton("▶️ Bắt đầu ghi")
        self._update_rec_start_btn_style()
        self.btn_rec_start.clicked.connect(self._start_recording)
        
        self.btn_rec_stop  = QPushButton("⏹ Dừng ghi")
        self._update_rec_stop_btn_style()
        self.btn_rec_stop.clicked.connect(self._stop_recording)
        self.btn_rec_stop.setEnabled(False)
        
        # Row 2: Tare and Clear
        btns2 = QHBoxLayout()
        btns2.setSpacing(8)
        self.btn_tare_acq = QPushButton("⚖️ Tare")
        self.btn_tare_acq.setStyleSheet("font-size:10pt; font-weight:600;")
        self.btn_tare_acq.clicked.connect(self._do_tare)
        
        self.btn_rec_clear = QPushButton("🗑️ Xóa dữ liệu mẫu")
        self._update_rec_clear_btn_style()
        self.btn_rec_clear.clicked.connect(self._clear_samples)
        self.btn_rec_clear.setEnabled(False)
        
        recording_buttons = [
            self.btn_rec_start,
            self.btn_rec_stop,
            self.btn_tare_acq,
            self.btn_rec_clear,
        ]
        for btn in recording_buttons:
            btn.setMinimumHeight(40)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btns1.addWidget(self.btn_rec_start, stretch=1)
        btns1.addWidget(self.btn_rec_stop, stretch=1)
        rg.addLayout(btns1)
        
        btns2.addWidget(self.btn_tare_acq, stretch=1)
        btns2.addWidget(self.btn_rec_clear, stretch=1)
        rg.addLayout(btns2)
        
        self.grp_recording.setLayout(rg); lay.addWidget(self.grp_recording)

        self.grp_export = QGroupBox("💾 Xuất dữ liệu")
        eg = QVBoxLayout()
        eg.setContentsMargins(6, 8, 6, 6)
        eg.setSpacing(6)
        self.exporter_buttons = {}
        for exp in self._exporters:
            display_name = exp.display_name
            if exp.__class__.__name__ == 'CsvSimpleExporter':
                display_name = self.i18n.t('csv_simple_display_name')
            btn = QPushButton(f"📄 {display_name}")
            btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
            btn.clicked.connect(lambda checked, e=exp: self._export(e))
            eg.addWidget(btn)
            self.exporter_buttons[exp] = btn

        self.grp_export.setLayout(eg); lay.addWidget(self.grp_export)

        # --- Import to Plot Viewer ---
        if _HAS_PLOT_VIEWER:
            self.grp_import_tools = QGroupBox("📥 Import dữ liệu sang công cụ khác")
            ig = QVBoxLayout()
            ig.setContentsMargins(6, 8, 6, 6)
            ig.setSpacing(6)

            self.btn_import_plot = QPushButton("📊 Import to Plot Viewer")
            self.btn_import_plot.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_import_plot.clicked.connect(self._import_to_plot_viewer)
            ig.addWidget(self.btn_import_plot)

            self.grp_import_tools.setLayout(ig); lay.addWidget(self.grp_import_tools)

        self._apply_acquisition_draw_plot_skin()

        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    def _apply_acquisition_draw_plot_skin(self):
        """Apply draw_plot.py-like visual skin without changing layout or behavior."""
        group_style = "QGroupBox{font-weight:bold;}"
        for group in (
            getattr(self, 'grp_sampling', None),
            getattr(self, 'grp_program', None),
            getattr(self, 'grp_plc_control', None),
            getattr(self, 'grp_recording', None),
            getattr(self, 'grp_export', None),
            getattr(self, 'grp_import_tools', None),
        ):
            if group is not None:
                group.setStyleSheet(group_style)

        button_specs = [
            (getattr(self, 'btn_rec_start', None), '#4CAF50', 'white'),
            (getattr(self, 'btn_rec_stop', None), '#F44336', 'white'),
            (getattr(self, 'btn_tare_acq', None), '#FF9800', 'white'),
            (getattr(self, 'btn_rec_clear', None), '#F44336', 'white'),
            (getattr(self, 'btn_servo_setup', None), '#607D8B', 'white'),
            (getattr(self, 'btn_plc_run', None), '#2E7D32', 'white'),
            (getattr(self, 'btn_plc_stop', None), '#C62828', 'white'),
            (getattr(self, 'btn_plc_clamp', None), '#6A1B9A', 'white'),
            (getattr(self, 'btn_plc_reset', None), '#0277BD', 'white'),
            (getattr(self, 'btn_plc_abort', None), '#B71C1C', 'white'),
            (getattr(self, 'btn_plc_home', None), '#455A64', 'white'),
            (getattr(self, 'btn_plc_jog_minus', None), '#EF6C00', 'white'),
            (getattr(self, 'btn_plc_jog_plus', None), '#EF6C00', 'white'),
            (getattr(self, 'btn_import_plot', None), '#4CAF50', 'white'),
        ]
        for btn, bg, fg in button_specs:
            if btn is not None:
                btn.setStyleSheet(
                    f"background-color: {bg}; color: {fg}; "
                    "font-weight: bold; padding: 4px; border-radius: 3px;"
                )

        # Exporter buttons are created dynamically; style them by scanning export group.
        if hasattr(self, 'grp_export'):
            for btn in self.grp_export.findChildren(QPushButton):
                if btn is not getattr(self, 'btn_import_plot', None):
                    btn.setStyleSheet(
                        "background-color: #2196F3; color: white; "
                        "font-weight: bold; padding: 4px; border-radius: 3px;"
                    )

    # --- Display group (Redesigned to be compact like draw_plot.py) ---
    def _build_display_group(self) -> QWidget:
        self.display_panel_grp = QGroupBox("📊 Real-time Data Info")
        self.display_panel_grp.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        g = QGridLayout()
        g.setContentsMargins(6, 8, 6, 6)
        g.setSpacing(4)

        # Current Torque - Styled prominently but not excessively large
        self.lbl_torque = QLabel("0.000 Nm")
        self.lbl_torque.setFont(QFont('Segoe UI', 14, QFont.Bold))
        self.lbl_torque.setStyleSheet("color: #1976D2;") 
        self.lbl_display_torque_title = QLabel("Torque:")
        g.addWidget(self.lbl_display_torque_title, 0, 0)
        g.addWidget(self.lbl_torque, 0, 1, 1, 3)

        # Row 1: Status & Pts
        self.lbl_display_status_title = QLabel("Status:")
        g.addWidget(self.lbl_display_status_title, 1, 0)
        self.lbl_stable = QLabel("---")
        self.lbl_stable.setStyleSheet("font-weight: bold; font-size: 11px;")
        g.addWidget(self.lbl_stable, 1, 1)

        self.lbl_display_samples_title = QLabel("Samples:")
        g.addWidget(self.lbl_display_samples_title, 1, 2)
        self.lbl_count = QLabel("0")
        self.lbl_count.setStyleSheet("font-weight: bold;")
        g.addWidget(self.lbl_count, 1, 3)

        # Row 2: Tare & Time
        self.lbl_display_tare_title = QLabel("Tare:")
        g.addWidget(self.lbl_display_tare_title, 2, 0)
        self.lbl_tare = QLabel("--- Nm")
        g.addWidget(self.lbl_tare, 2, 1)

        self.lbl_display_time_title = QLabel("Time:")
        g.addWidget(self.lbl_display_time_title, 2, 2)
        self.lbl_rectime = QLabel("0.0 s")
        g.addWidget(self.lbl_rectime, 2, 3)

        # Row 3: Max
        info_style = "font-weight: bold; font-size: 12px;"
        self.lbl_display_max_title = QLabel("Maximum:")
        g.addWidget(self.lbl_display_max_title, 3, 0)
        self.lbl_max = QLabel("---")
        self.lbl_max.setStyleSheet(f"color: #1976D2; {info_style}")
        g.addWidget(self.lbl_max, 3, 1)

        # Row 4: Min
        self.lbl_display_min_title = QLabel("Minimum:")
        g.addWidget(self.lbl_display_min_title, 4, 0)
        self.lbl_min = QLabel("---")
        self.lbl_min.setStyleSheet(f"color: #D32F2F; {info_style}")
        g.addWidget(self.lbl_min, 4, 1)

        # Row 4: PLC angle returned from D124
        self.lbl_display_plc_angle_title = QLabel("Góc PLC:")
        g.addWidget(self.lbl_display_plc_angle_title, 4, 2)
        self.lbl_plc_angle = QLabel("0.00°")
        self.lbl_plc_angle.setStyleSheet(f"color: #6A1B9A; {info_style}")
        g.addWidget(self.lbl_plc_angle, 4, 3)

        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)
        self.display_panel_grp.setLayout(g)
        return self.display_panel_grp



    # --- Chart group ---
    def _build_chart_group(self) -> QWidget:
        self.chart_group = QGroupBox("📈 Torque vs Time & Angle")
        lay = QVBoxLayout()
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        # Splitter to display Time and Angle charts side-by-side
        self.chart_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.chart_splitter.setHandleWidth(8)

        # 1. Torque-Time Chart Container
        time_container = QWidget()
        time_lay = QVBoxLayout(time_container)
        time_lay.setContentsMargins(0, 0, 0, 0)
        time_lay.setSpacing(2)

        self.plot = RealTimePlot(
            title="Torque vs Time",
            xlabel="Time (s)", ylabel="Torque (Nm)",
            max_window_s=DEFAULT_TIME_WINDOW_S,
        )
        self.toolbar = CustomToolbar(self.plot, self)
        self.toolbar.setMaximumHeight(32)
        time_lay.addWidget(self.toolbar)
        time_lay.addWidget(self.plot)
        self.chart_splitter.addWidget(time_container)

        # 2. Torque-Angle Chart Container
        angle_container = QWidget()
        angle_lay = QVBoxLayout(angle_container)
        angle_lay.setContentsMargins(0, 0, 0, 0)
        angle_lay.setSpacing(2)

        self.angle_plot = TorqueAnglePlot(
            title="Torque vs Angle",
            xlabel="Angle (deg)", ylabel="Torque (Nm)",
        )
        self.angle_toolbar = CustomToolbar(self.angle_plot, self)
        self.angle_toolbar.setMaximumHeight(32)
        angle_lay.addWidget(self.angle_toolbar)
        angle_lay.addWidget(self.angle_plot)
        self.chart_splitter.addWidget(angle_container)

        # Set equal initial sizes
        self.chart_splitter.setSizes([500, 500])
        lay.addWidget(self.chart_splitter, stretch=1)

        # Control buttons row (Pause & Clear)
        btn_row = QHBoxLayout()
        self.btn_pause_chart = QPushButton(self.i18n.t('btn_pause_chart'))
        self.btn_pause_chart.setCheckable(True)
        self.btn_pause_chart.toggled.connect(self._toggle_pause_chart)
        btn_row.addWidget(self.btn_pause_chart)

        self.btn_clear_chart = QPushButton(self.i18n.t('btn_clear_chart'))
        self.btn_clear_chart.clicked.connect(self._clear_chart)
        btn_row.addWidget(self.btn_clear_chart)
        
        lay.addLayout(btn_row)
        self.chart_group.setLayout(lay)
        return self.chart_group

    def _toggle_pause_chart(self, checked: bool):
        self._chart_paused = checked
        if checked:
            self.btn_pause_chart.setText(self.i18n.t('btn_resume_chart'))
            self._log("⏸ Đã tạm dừng cập nhật Torque-Time")
        else:
            self.btn_pause_chart.setText(self.i18n.t('btn_pause_chart'))
            self._log("▶️ Tiếp tục cập nhật Torque-Time")



    def _update_theme_btn_text(self):
        if self._is_dark:
            self.btn_toggle_theme.setText(self.i18n.t('btn_theme_light'))
            self.btn_toggle_theme.setStyleSheet(
                "background:#313244; color:#cdd6f4; font-size:9pt; border-radius:4px; border:1px solid #45475a;"
            )
        else:
            self.btn_toggle_theme.setText(self.i18n.t('btn_theme_dark'))
            self.btn_toggle_theme.setStyleSheet(
                "background:#e0e0e0; color:#333; font-size:9pt; border-radius:4px; border:1px solid #ccc;"
            )

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self._apply_theme(self._is_dark)
        self._update_theme_btn_text()
        # Lưu vào settings
        ui = self._settings.load_ui_settings()
        ui['dark_theme'] = self._is_dark
        self._settings.save_ui_settings(ui)

    def _apply_theme(self, dark: bool):
        """Áp dụng Dark hoặc Light theme cho toàn app + cập nhật màu chart."""
        self.setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)
        
        # Cập nhật màu sắc cho các label thông số
        torque_color = "#89b4fa" if dark else "#1976D2"
        max_color    = "#a6e3a1" if dark else "#1976D2"
        min_color    = "#f38ba8" if dark else "#D32F2F"
        
        if hasattr(self, 'lbl_torque'):
            self.lbl_torque.setStyleSheet(f"color: {torque_color};")
            self.lbl_max.setStyleSheet(f"color: {max_color}; font-weight: bold; font-size: 12px;")
            self.lbl_min.setStyleSheet(f"color: {min_color}; font-weight: bold; font-size: 12px;")
            if hasattr(self, 'lbl_plc_angle'):
                plc_angle_color = "#cba6f7" if dark else "#6A1B9A"
                self.lbl_plc_angle.setStyleSheet(f"color: {plc_angle_color}; font-weight: bold; font-size: 12px;")

        if hasattr(self, 'lbl_conn_status'):
            status_color = "#a6adc8" if dark else "#757575"
            self.lbl_conn_status.setStyleSheet(f"color: {status_color};")

        # Cập nhật style nút ghi (vì có màu riêng)
        if hasattr(self, 'btn_rec_start'):
            self._update_rec_start_btn_style()
            self._update_rec_stop_btn_style()
            self._update_rec_clear_btn_style()

        # Cập nhật màu chart theo theme
        if hasattr(self, 'plot'):
            self._apply_chart_theme(dark)

    def _apply_chart_theme(self, dark: bool):
        if hasattr(self, 'plot'):
            ax = self.plot.ax
            fig = self.plot.fig
            if dark:
                fig.patch.set_facecolor('#1e1e2e')
                ax.set_facecolor('#181825')
                ax.tick_params(colors='#bac2de')
                ax.title.set_color('#cdd6f4')
                ax.xaxis.label.set_color('#bac2de')
                ax.yaxis.label.set_color('#bac2de')
                ax.grid(True, alpha=0.15, color='#a6adc8')
                for spine in ax.spines.values():
                    spine.set_edgecolor('#45475a')
                self.plot.line.set_color('#89b4fa')
            else:
                fig.patch.set_facecolor('#f5f5f5')
                ax.set_facecolor('#ffffff')
                ax.tick_params(colors='#212121')
                ax.title.set_color('#1565c0')
                ax.xaxis.label.set_color('#424242')
                ax.yaxis.label.set_color('#424242')
                ax.grid(True, alpha=0.4, color='#dddddd')
                for spine in ax.spines.values():
                    spine.set_edgecolor('#bdbdbd')
                self.plot.line.set_color('#1976d2')
            self.plot.draw_idle()

        if hasattr(self, 'angle_plot'):
            ax = self.angle_plot.ax
            fig = self.angle_plot.fig
            self.angle_plot._bg = None  # Invalidate blit background cache
            if dark:
                fig.patch.set_facecolor('#1e1e2e')
                ax.set_facecolor('#181825')
                ax.tick_params(colors='#bac2de')
                ax.title.set_color('#cdd6f4')
                ax.xaxis.label.set_color('#bac2de')
                ax.yaxis.label.set_color('#bac2de')
                ax.grid(True, alpha=0.15, color='#a6adc8')
                for spine in ax.spines.values():
                    spine.set_edgecolor('#45475a')
                self.angle_plot.line.set_color('#fab387')
            else:
                fig.patch.set_facecolor('#f5f5f5')
                ax.set_facecolor('#ffffff')
                ax.tick_params(colors='#212121')
                ax.title.set_color('#1565c0')
                ax.xaxis.label.set_color('#424242')
                ax.yaxis.label.set_color('#424242')
                ax.grid(True, alpha=0.4, color='#dddddd')
                for spine in ax.spines.values():
                    spine.set_edgecolor('#bdbdbd')
                self.angle_plot.line.set_color('#e65100')
            self.angle_plot.draw_idle()

    # --- Log group ---
    def _build_log_group(self) -> QWidget:
        self.grp_log = QGroupBox("📝 Terminal Log")
        lay = QVBoxLayout()
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(140)
        lay.addWidget(self.log_box)
        self.grp_log.setLayout(lay)
        return self.grp_log

    # --- Helper to update button styles based on state and theme ---
    def _update_connect_btn_style(self):
        if self._connected:
            color = "#F44336" if not self._is_dark else "#f38ba8" # Red
            text_color = "white" if not self._is_dark else "#1e1e2e"
            self.btn_connect.setText(self.i18n.t('btn_disconnect'))
        else:
            color = "#4CAF50" if not self._is_dark else "#a6e3a1" # Green
            text_color = "white" if not self._is_dark else "#1e1e2e"
            self.btn_connect.setText(self.i18n.t('btn_connect'))
        self.btn_connect.setStyleSheet(f"background-color: {color}; color: {text_color}; font-weight: bold; padding: 8px;")

    def _update_rec_start_btn_style(self):
        color = "#FF9800" if not self._is_dark else "#fab387" # Orange
        text_color = "white" if not self._is_dark else "#1e1e2e"
        self.btn_rec_start.setStyleSheet(f"background-color: {color}; color: {text_color}; font-weight: bold; height: 28px;")

    def _update_rec_stop_btn_style(self):
        color = "#F44336" if not self._is_dark else "#f38ba8" # Red
        text_color = "white" if not self._is_dark else "#1e1e2e"
        self.btn_rec_stop.setStyleSheet(f"background-color: {color}; color: {text_color}; font-weight: bold; height: 28px;")

    def _update_rec_clear_btn_style(self):
        color = "#757575" if not self._is_dark else "#45475a" # Gray
        text_color = "white" if not self._is_dark else "#cdd6f4"
        self.btn_rec_clear.setStyleSheet(f"background-color: {color}; color: {text_color}; font-weight: bold; height: 28px;")

    # ===========================================================
    # ===========================================================
    # PLC / SERVO CONTROL PANEL
    # ===========================================================

    def _plc_command(self, action_name: str, callback) -> bool:
        """Run PLC command outside UI thread to avoid Not Responding."""
        if not self._plc_svc or not self._plc_svc.is_connected():
            self._log("⚠️ PLC chưa kết nối")
            return False
        if self._plc_command_running:
            self._log(f"⏳ PLC đang xử lý lệnh trước, bỏ qua: {action_name}")
            return False
        self._plc_command_running = True
        self._log(f"⏳ PLC: {action_name}...")
        if self._bus_scheduler:
            if not self._bus_scheduler.enqueue_command(action_name, callback):
                self._plc_command_running = False
                return False
        else:
            threading.Thread(
                target=self._run_plc_command_worker,
                args=(action_name, callback),
                name=f"PLC-Cmd-{action_name}",
                daemon=True,
            ).start()
        return True

    def _run_plc_command_worker(self, action_name: str, callback):
        ok = False
        try:
            ok = bool(callback())
        except Exception:
            ok = False
        self._sig_plc_command_result.emit(action_name, ok)

    def _on_plc_command_result(self, action_name: str, ok: bool):
        self._plc_command_running = False
        self._log(("✅" if ok else "❌") + f" PLC: {action_name}")
        if ok and action_name == "Home":
            self._current_angle = 0.0
            self._jog_active = False
            self._jog_direction = 0
            if hasattr(self, 'lbl_plc_angle'):
                self.lbl_plc_angle.setText("0.00°")

    def _plc_start_run(self):
        self._plc_command("RUN", lambda: self._plc_svc.start_run() if self._plc_svc else False)

    def _plc_stop_run(self):
        self._plc_command("STOP", lambda: self._plc_svc.stop_run() if self._plc_svc else False)
        if self._bus_scheduler:
            self._bus_scheduler.set_recording_active(False)

    def _plc_toggle_clamp(self):
        self._plc_command("Clamp toggle", lambda: self._plc_svc.toggle_cylinder() if self._plc_svc else False)

    def _plc_reset_fault(self):
        self._plc_command("Reset fault", lambda: self._plc_svc.reset_fault() if self._plc_svc else False)

    def _plc_abort(self):
        self._plc_command("Abort", lambda: self._plc_svc.abort() if self._plc_svc else False)
        if self._bus_scheduler:
            self._bus_scheduler.set_recording_active(False)

    def _plc_home(self):
        def _home_and_reset_angle():
            if not self._plc_svc:
                return False
            ok = self._plc_svc.home()
            if ok:
                self._plc_svc.write_current_angle(0.0)
            return ok
        self._plc_command("Home", _home_and_reset_angle)

    def _update_jog_speed_from_profile(self):
        if not hasattr(self, 'spin_plc_jog_speed'):
            return
        part_name = self.combo_part_name.currentText() if hasattr(self, 'combo_part_name') else 'ITR'
        test_item = self.combo_test_item.currentText() if hasattr(self, 'combo_test_item') else 'Operating'
        part_map = {
            'Inner Tie Rod': 'ITR', 'Ball Joint': 'B/Joint', 'Outer Tie Rod': 'OTR', 'Stabilizer Link': 'S/Link',
            'ITR': 'ITR', 'B/Joint': 'B/Joint', 'OTR': 'OTR', 'S/Link': 'S/Link'
        }
        part_short = part_map.get(part_name, 'ITR')
        is_breakaway = "Breakaway" in test_item
        test_char = 'B' if is_breakaway else 'O'
        profile_key = f"{part_short}_{test_char}"

        profiles = self._settings.load_servo_profiles()
        profile = profiles.get(profile_key)
        if profile:
            self.spin_plc_jog_speed.blockSignals(True)
            self.spin_plc_jog_speed.setValue(getattr(profile, 'jog_speed', 10.0))
            self.spin_plc_jog_speed.blockSignals(False)

    def _on_plc_jog_speed_changed(self, val: float):
        if self._plc_svc and self._plc_svc.is_connected():
            if self._plc_svc.write_speed(val):
                self._log(f"⚡ Đã ghi tốc độ JOG {val * 100:.0f} Hz xuống PLC (D104)")

    def _selected_plc_mode(self) -> int:
        """Return PLC mode matching the selected measurement mode in the app."""
        text = self.combo_test_item.currentText() if hasattr(self, 'combo_test_item') else ''
        if 'Breakaway' in text:
            return 1
        if 'Operating' in text or 'Oscillating' in text:
            return 2
        return 0

    def _begin_plc_jog(self, direction: int) -> None:
        """Temporarily switch PLC to Manual mode so D110/D111 JOG can run."""
        if not self._plc_svc or not self._plc_svc.is_connected():
            return
        self._plc_svc.write_speed(self.spin_plc_jog_speed.value())
        self._jog_active = True
        self._jog_direction = 1 if direction >= 0 else -1
        self._jog_started_at = time.monotonic()
        self._jog_start_angle = self._current_angle
        if not hasattr(self, '_plc_mode_before_jog'):
            self._plc_mode_before_jog = self._selected_plc_mode()
        if self._plc_svc.write_mode(0):
            self._log("⚙️ PLC mode -> Manual (D101=0) để JOG")

    def _end_plc_jog(self) -> None:
        """Restore PLC mode from the app selection after releasing JOG."""
        if not self._plc_svc or not self._plc_svc.is_connected():
            return

        if self._jog_active:
            elapsed_s = max(0.0, time.monotonic() - self._jog_started_at)
            jog_rpm = float(self.spin_plc_jog_speed.value())
            # Servo output angle: motor rpm / gearbox 20 * 360 / 60 = rpm * 0.3 deg/s
            delta_deg = self._jog_direction * jog_rpm * 0.3 * elapsed_s
            self._current_angle = self._jog_start_angle + delta_deg
            if self._plc_svc.write_current_angle(self._current_angle):
                self._log(f"📐 Cập nhật góc PLC D124={self._current_angle:.2f}° sau JOG")
            if hasattr(self, 'lbl_plc_angle'):
                self.lbl_plc_angle.setText(f"{self._current_angle:.2f}°")
            self._jog_active = False
            self._jog_direction = 0

        restore_mode = self._selected_plc_mode()
        if self._plc_svc.write_mode(restore_mode):
            self._log(f"⚙️ PLC mode khôi phục D101={restore_mode}")
        if hasattr(self, '_plc_mode_before_jog'):
            delattr(self, '_plc_mode_before_jog')

    def _plc_jog_plus(self, active: bool):
        if active:
            self._begin_plc_jog(direction=1)
        self._plc_command("Jog+ ON" if active else "Jog+ OFF", lambda: self._plc_svc.jog_plus(active) if self._plc_svc else False)
        if not active:
            self._end_plc_jog()

    def _plc_jog_minus(self, active: bool):
        if active:
            self._begin_plc_jog(direction=-1)
        self._plc_command("Jog- ON" if active else "Jog- OFF", lambda: self._plc_svc.jog_minus(active) if self._plc_svc else False)
        if not active:
            self._end_plc_jog()

    def _start_plc_polling(self):
        """Start one PLC polling thread, similar to DataCollectorService."""
        if not self._plc_svc or not self._plc_svc.is_connected():
            return
        if self._plc_poll_running and self._plc_poll_thread and self._plc_poll_thread.is_alive():
            return
        self._plc_poll_running = True
        self._plc_poll_thread = threading.Thread(
            target=self._plc_poll_loop,
            name="PLC-Poller",
            daemon=True,
        )
        self._plc_poll_thread.start()

    def _stop_plc_polling(self):
        self._plc_poll_running = False
        thread = getattr(self, '_plc_poll_thread', None)
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
        self._plc_poll_thread = None
        self._plc_status_polling = False
        self._plc_angle_polling = False

    def _plc_poll_loop(self):
        """Read PLC angle fast and full status slower in a single worker thread."""
        next_angle = 0.0
        next_status = 0.0
        while self._plc_poll_running:
            now = time.monotonic()
            did_work = False

            if now >= next_status:
                self._read_plc_status_once()
                next_status = time.monotonic() + self._plc_status_interval_s
                did_work = True

            if not did_work:
                time.sleep(0.005)
            else:
                time.sleep(0.001)

    def _read_plc_status_once(self):
        status = None
        try:
            if self._plc_svc and self._plc_svc.is_connected():
                status = self._plc_svc.read_status()
        except Exception:
            status = None
        self._sig_plc_status.emit(status)

    def _read_plc_angle_once(self):
        angle = None
        try:
            if self._plc_svc and self._plc_svc.is_connected():
                reg = self._plc_svc._client.read_register(124, self._plc_svc.slave_id)
                if reg is not None:
                    raw = int(reg) & 0xFFFF
                    if raw >= 0x8000:
                        raw -= 0x10000
                    angle = raw / 100.0
        except Exception:
            angle = None
        self._sig_plc_angle.emit(float('nan') if angle is None else float(angle))

    def _on_plc_angle_received(self, angle: float):
        if angle != angle:  # NaN
            return
        self._current_angle = angle
        if hasattr(self, 'lbl_plc_angle'):
            self.lbl_plc_angle.setText(f"{self._current_angle:.2f}°")

    def _on_plc_status_received(self, status):
        if status is None:
            self._plc_status_fail_count = getattr(self, '_plc_status_fail_count', 0) + 1
            # Bỏ qua vài lần timeout lẻ sau command/record vì RTU/simulator có thể bận tức thời.
            if self._plc_status_fail_count >= 5 and not self._plc_status_error_logged:
                self._log("⚠️ Không đọc được PLC status D120..D135")
                self._plc_status_error_logged = True
            return
        self._last_plc_status = status
        self._plc_status_fail_count = 0
        self._plc_status_error_logged = False
        if hasattr(status, 'current_angle_deg'):
            self._current_angle = status.current_angle_deg
        if hasattr(status, 'current_cycle'):
            self._current_cycle = status.current_cycle
        if hasattr(self, 'lbl_plc_angle'):
            self.lbl_plc_angle.setText(f"{self._current_angle:.2f}°")

        if getattr(status, 'has_fault', False):
            self._log(f"⚠️ PLC fault D129={getattr(status, 'error_code', 0)}")

        elapsed_since_start = time.monotonic() - getattr(self, '_start_time', 0.0)
        if self._recording and status.is_done and elapsed_since_start > 1.5:
            self._log("✅ PLC báo hoàn tất test")
            self._recording = False
            self._stop_recording()

    def _poll_plc_status(self):
        """Backward-compatible alias for manual status refresh."""
        if not self._plc_poll_running:
            threading.Thread(target=self._read_plc_status_once, name="PLC-Status-Once", daemon=True).start()

    def _prepare_plc_recording(self, profile, is_breakaway: bool) -> bool:
        if not self._plc_svc or not self._plc_svc.is_connected():
            return True

        plc_status = self._plc_svc.read_status()
        if plc_status and plc_status.has_fault:
            self._log(f"❌ PLC đang lỗi D129={plc_status.error_code}; hãy Reset trước khi ghi")
            return False

        self._current_angle = 0.0
        self._jog_active = False
        self._jog_direction = 0
        if self._plc_svc.write_current_angle(0.0):
            self._log("📐 Bắt đầu ghi: reset góc PLC D124=0.00°")
        if hasattr(self, 'lbl_plc_angle'):
            self.lbl_plc_angle.setText("0.00°")

        part_select = max(1, self.combo_part_name.currentIndex() + 1) if hasattr(self, 'combo_part_name') else 1
        config = PlcTestConfig(
            mode=1 if is_breakaway else 2,
            pos_angle_x100=angle_to_x100(profile.positive_angle),
            # D103 gửi xuống PLC là độ lớn góc nghịch dương; PLC tự đổi dấu khi chạy chiều nghịch.
            neg_angle_x100=angle_to_x100(abs(profile.negative_angle)),
            speed_x100=speed_to_x100(profile.speed),
            cycle_set=1 if is_breakaway else getattr(profile, 'cycles', 3),
            # Ghi thô lấy toàn bộ hành trình; vùng 80% giữa hành trình để Plot Draw/tính toán xử lý sau.
            window_percent=100,
            part_select=part_select,
            torque_type=1 if is_breakaway else 2,
        )
        if not self._plc_svc.write_test_config(config):
            self._log("❌ Không ghi được PLC config D101..D108")
            return False
        self._plc_svc.clear_done()
        if not self._plc_svc.start_record():
            self._log("❌ Không pulse được START_RECORD D100.b2")
            return False
        self._log("✅ Đã ghi PLC config và gửi START_RECORD")
        return True

    # ===========================================================
    # LOAD / SAVE SETTINGS

    # ===========================================================

    def _load_settings_to_ui(self):
        c = self._conn_cfg
        # Protocol (Ẩn đi vì chạy chế độ kết nối kép)
        # idx = 0 if c.mode == 'RTU' else 1
        # self.combo_proto.setCurrentIndex(idx)
        # RTU
        baud_map = {"9600":0,"19200":1,"38400":2,"57600":3,"115200":4}
        self.combo_baud.setCurrentIndex(baud_map.get(str(c.baudrate), 0))
        parity_map = {"N":0,"E":1,"O":2}
        self.combo_parity.setCurrentIndex(parity_map.get(c.parity, 0))
        self.combo_ip.setCurrentText(c.ip)
        self.spin_tcp_port.setValue(c.tcp_port)
        self.spin_slave.setValue(c.slave_id)
        if hasattr(self, 'spin_plc_slave'):
            self.spin_plc_slave.setValue(c.plc_slave_id)

        # Device (Config Tab)
        d = self._dev_cfg
        self.combo_unit.setCurrentIndex(d.measure_unit)
        self.combo_mtype.setCurrentIndex(d.measure_type)
        self.combo_filter.setCurrentIndex(d.filter_level)
        
        self.spin_fs.setValue(d.cell_full_scale)
        self.spin_sens.setValue(d.cell_sensitivity)
        
        # UI settings (Acquisition / Plot)
        ui = self._settings.load_ui_settings()
        if 'interval_ms' in ui:
            self.spin_interval.setValue(int(ui['interval_ms']))
        if 'window_s' in ui:
            self.spin_window.setValue(int(ui['window_s']))
        if 'y_max' in ui:
            self.spin_ymax.setValue(float(ui['y_max']))
        if 'fixed_y' in ui:
            self.chk_fixed_y.setChecked(bool(ui['fixed_y']))
        if 'part_name' in ui and hasattr(self, 'combo_part_name'):
            self.combo_part_name.setCurrentText(ui['part_name'])
        if 'test_item' in ui and hasattr(self, 'combo_test_item'):
            self.combo_test_item.setCurrentText(ui['test_item'])
        
        # Apply initial plot limits
        self._update_plot_limits()
        self._update_sampling_summary()

    def _update_sampling_summary(self):
        if hasattr(self, 'lbl_sampling_summary'):
            fixed = "Fixed Y" if self.chk_fixed_y.isChecked() else "Auto Y"
            self.lbl_sampling_summary.setText(
                f"{self.spin_interval.value()} ms | {self.spin_window.value()} s | "
                f"±{self.spin_ymax.value():.1f} Nm | {fixed}"
            )

    def _open_sampling_settings(self):
        dialog = SamplingSettingsDialog(
            self,
            interval_ms=self.spin_interval.value(),
            window_s=self.spin_window.value(),
            y_max=self.spin_ymax.value(),
            fixed_y=self.chk_fixed_y.isChecked(),
            i18n=self.i18n,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        values = dialog.get_values()
        self.spin_interval.setValue(values['interval_ms'])
        self.spin_window.setValue(values['window_s'])
        self.spin_ymax.setValue(values['y_max'])
        self.chk_fixed_y.setChecked(values['fixed_y'])
        self._update_plot_limits()
        self._on_acquisition_settings_changed()
        self._update_sampling_summary()

    def _show_modbus_status_dialog(self):
        client = getattr(self._plc_svc, '_client', None) if self._plc_svc else None
        slave_id = self.spin_plc_slave.value() if hasattr(self, 'spin_plc_slave') else 2
        dialog = ModbusStatusDialog(self, client, slave_id, self.i18n)
        dialog.exec_()

    def _save_settings_from_ui(self):
        parity_map = {0:'N', 1:'E', 2:'O'}
        conn = ConnectionConfig(
            mode='TCP',  # Chế độ kết nối kép mặc định
            port=self.combo_com.currentData() or 'COM1',
            baudrate=int(self.combo_baud.currentText()),
            parity=parity_map[self.combo_parity.currentIndex()],
            ip=self.combo_ip.currentText(),
            tcp_port=self.spin_tcp_port.value(),
            slave_id=self.spin_slave.value(),
            plc_slave_id=self.spin_plc_slave.value() if hasattr(self, 'spin_plc_slave') else 2,
        )
        self._settings.save_connection_config(conn)

        dev = DeviceConfig(
            measure_unit=self.combo_unit.currentData() if self.combo_unit.currentData() is not None else 8,
            measure_type=self.combo_mtype.currentIndex(),
            filter_level=self.combo_filter.currentData() if self.combo_filter.currentData() is not None else 3,
            
            cell_full_scale=self.spin_fs.value(),
            cell_sensitivity=self.spin_sens.value(),
            
            # Giữ nguyên cấu hình cũ cho các thông số không còn trên UI
            std_weight=self._dev_cfg.std_weight,
            analog_out_type=self._dev_cfg.analog_out_type,
            dio_type=self._dev_cfg.dio_type,
            calib_mode=self._dev_cfg.calib_mode,
            delta_weight=self._dev_cfg.delta_weight,
            delta_time=self._dev_cfg.delta_time,
            adc_sps=self._dev_cfg.adc_sps,
            resolution_mode=self._dev_cfg.resolution_mode,
            factory_tare=self._dev_cfg.factory_tare,
            
            target_address=self._dev_cfg.target_address,
            target_baud=self._dev_cfg.target_baud,
            target_parity=self._dev_cfg.target_parity,
            
            slave_id=self.spin_slave.value(),
        )
        self._settings.save_device_config(dev)
        ui_dict: dict[str, Any] = {
            'interval_ms': self.spin_interval.value(),
            'window_s':    self.spin_window.value(),
            'y_max':       self.spin_ymax.value(),
            'fixed_y':     self.chk_fixed_y.isChecked(),
        }
        if hasattr(self, 'combo_part_name'):
            ui_dict['part_name'] = self.combo_part_name.currentText()
        if hasattr(self, 'combo_test_item'):
            ui_dict['test_item'] = self.combo_test_item.currentText()
        self._settings.save_ui_settings(ui_dict)

    def _update_plot_limits(self):
        """Cập nhật giới hạn trục Y của cả biểu đồ Torque-Time và Torque-Angle."""
        limit = self.spin_ymax.value() if self.chk_fixed_y.isChecked() else None

        if hasattr(self, 'plot'):
            self.plot.set_y_limits(limit)
        if hasattr(self, 'angle_plot'):
            self.angle_plot.set_y_limits(limit)

    def _on_acquisition_settings_changed(self):
        """Áp dụng và lưu cài đặt thu thập ngay lập tức khi thay đổi trên UI."""
        interval = self.spin_interval.value()
        window = self.spin_window.value()
        
        # 1. Áp dụng ngay vào logic đang chạy
        self._collector.set_interval(interval)
        self.plot.max_window_s = window
        if self._recording:
            self._session.sample_interval_ms = interval
        
        # 2. Lưu lại vào file settings.json (nếu đã init UI xong)
        if hasattr(self, '_settings'):
             ui = self._settings.load_ui_settings()
             ui['interval_ms'] = interval
             ui['window_s'] = window
             ui['y_max'] = self.spin_ymax.value()
             ui['fixed_y'] = self.chk_fixed_y.isChecked()
             self._settings.save_ui_settings(ui)
        self._update_sampling_summary()

    # ===========================================================
    # CONNECTION
    # ===========================================================

    def _on_proto_changed(self, text: str):
        pass

    def _scan_com_ports(self):
        self.combo_com.clear()
        ports = serial.tools.list_ports.comports()
        for p in sorted(ports, key=lambda x: x.device):
            self.combo_com.addItem(f"{p.device} – {p.description}", p.device)
        if not ports:
            self.combo_com.addItem("(Trống)")

    def _toggle_connect(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        from infrastructure.modbus_rtu_client import ModbusRtuClient
        from infrastructure.modbus_tcp_client import ModbusTcpClient

        parity_map = {0:'N', 1:'E', 2:'O'}
        sid = self.spin_slave.value()
        plc_sid = self.spin_plc_slave.value() if hasattr(self, 'spin_plc_slave') else 2

        try:
            # 1. Khởi tạo TCP Client cho Cảm biến
            ip = self.combo_ip.currentText()
            tcp_port = self.spin_tcp_port.value()
            self._log(f"⏳ Đang kết nối Cảm biến: {ip}:{tcp_port}...")
            sensor_client = ModbusTcpClient(host=ip, port=tcp_port)
            
            # 2. Khởi tạo RTU Client cho PLC
            port = self.combo_com.currentData()
            if not port:
                self._log("❌ Chưa chọn cổng COM cho PLC")
                return
            baud = int(self.combo_baud.currentText())
            par  = parity_map[self.combo_parity.currentIndex()]
            self._log(f"⏳ Đang kết nối PLC: {port} @ {baud}...")
            plc_client = ModbusRtuClient(port=port, baudrate=baud, parity=par)

            # 3. Tiến hành kết nối cả hai
            sensor_connected = sensor_client.connect()
            if not sensor_connected:
                self._log("❌ Kết nối Cảm biến (TCP) thất bại!")
                return
                
            plc_connected = plc_client.connect()
            if not plc_connected:
                self._log("❌ Kết nối PLC (RTU) thất bại!")
                sensor_client.disconnect()
                return

            # 4. Lưu và gán client mới vào các service
            self._collector._client = sensor_client
            self._config_svc._client = sensor_client
            self._collector._slave_id = sid

            if self._servo_svc:
                from infrastructure.plc_servo_controller import PLCServoController
                self._servo_svc._plc = PLCServoController(plc_client, slave_id=plc_sid)

            if self._plc_svc:
                self._plc_svc.set_client(plc_client, slave_id=plc_sid)

            self._connected = True
            self._ref_time  = time.monotonic()
            self._update_connect_btn_style()
            self.led_label.setObjectName("led_on")
            self._apply_led_style()
            self.lbl_conn_status.setText("🟢 Đã kết nối")

            self._collector.set_interval(self.spin_interval.value())
            if self._bus_scheduler:
                self._bus_scheduler.set_clients(sensor_client, plc_client, sensor_slave_id=sid, plc_slave_id=plc_sid)
                self._bus_scheduler.set_intervals(self.spin_interval.value(), 150)
                self._bus_scheduler.start()
            else:
                self._collector.start()
                if self._plc_svc:
                    self._start_plc_polling()
                    
            self._save_settings_from_ui()
            self._log(f"✅ Kết nối thành công (Cảm biến TCP/IP, PLC Modbus RTU)")
        except Exception as e:
            self._log(f"❌ Lỗi kết nối: {e}")

    def _disconnect(self):
        if self._bus_scheduler:
            self._bus_scheduler.stop()
        else:
            self._stop_plc_polling()
            self._collector.stop()
            
        # Đóng các client kết nối thực tế
        if self._collector._client:
            try:
                self._collector._client.disconnect()
            except Exception:
                pass
        if self._plc_svc and self._plc_svc._client:
            try:
                self._plc_svc._client.disconnect()
            except Exception:
                pass
        
        # Trả về các null client ban đầu
        self._collector._client = self._null_sensor_client
        self._config_svc._client = self._null_sensor_client
        if self._plc_svc:
            self._plc_svc.set_client(self._null_plc_client, slave_id=self.spin_plc_slave.value() if hasattr(self, 'spin_plc_slave') else 2)
        
        # Swap back to Dummy PLC Servo Controller when disconnected
        if self._servo_svc:
            from infrastructure.plc_servo_controller import DummyPLCServoController
            self._servo_svc._plc = DummyPLCServoController()

        self._connected = False
        self._update_connect_btn_style()
        self.led_label.setObjectName("led_off")
        self._apply_led_style()
        self.lbl_conn_status.setText("⚪ Chưa kết nối")
        self._log("🔌 Đã ngắt kết nối")

    def _apply_led_style(self):
        if self.led_label.objectName() == "led_on":
            color = "#4CAF50" if not self._is_dark else "#a6e3a1"
        else:
            color = "#F44336" if not self._is_dark else "#f38ba8"
        self.led_label.setStyleSheet(f"color: {color}; font-size: 20px;")


    # ===========================================================
    # DATA CALLBACKS
    # ===========================================================

    def _on_status_received(self, status: DeviceStatus):
        """Gọi từ main thread (qua Qt signal). Cập nhật UI live."""
        self._last_status = status  # Lưu trạng thái mới nhất
        elapsed = time.monotonic() - self._ref_time

        # Cập nhật giá trị hiện tại
        self.lbl_torque.setText(f"{status.net_weight:.3f} Nm")
        self.lbl_tare.setText(f"{status.tare_weight:.3f} Nm")
        self.lbl_max.setText(f"{status.max_net_weight:.3f}")
        self.lbl_min.setText(f"{status.min_net_weight:.3f}")

        if status.is_stable:
            self.lbl_stable.setText(self.i18n.t('status_stable') if hasattr(self, 'i18n') else "🟢 Stable")
            color = "#4CAF50" if not self._is_dark else "#a6e3a1"
            self.lbl_stable.setStyleSheet(f"color: {color};")
        elif status.is_fullscale:
            self.lbl_stable.setText(self.i18n.t('status_fullscale') if hasattr(self, 'i18n') else "🔴 Full Scale!")
            color = "#F44336" if not self._is_dark else "#f38ba8"
            self.lbl_stable.setStyleSheet(f"color: {color};")
        else:
            self.lbl_stable.setText(self.i18n.t('status_unstable') if hasattr(self, 'i18n') else "🟡 Unstable")
            color = "#FF9800" if not self._is_dark else "#f9e2af"
            self.lbl_stable.setStyleSheet(f"color: {color};")


        # Chart update (nếu không đang PAUSE)
        if not self._chart_paused:
            self.plot.add_point(elapsed, status.net_weight)
            if hasattr(self, 'angle_plot'):
                self.angle_plot.add_point(self._current_angle, status.net_weight)

        # Ghi session nếu đang recording
        if self._recording:
            elapsed_time = time.monotonic() - self._start_time
            if self._plc_svc and self._plc_svc.is_connected():
                plc_status = self._last_plc_status
                if plc_status is not None and not plc_status.should_record_sample:
                    self.lbl_rectime.setText(f"{elapsed_time:.3f} s")
                    return

            interval_s = self._session.sample_interval_ms / 1000.0
            expected_samples = int(elapsed_time / interval_s)

            # Tự động sinh thêm các mẫu bị thiếu để đảm bảo đúng tần số yêu cầu.
            # Khi polling Modbus chậm hơn sample interval, không được lặp nguyên góc hiện tại
            # cho toàn bộ mẫu bù; nội suy tuyến tính từ mẫu cuối -> trạng thái hiện tại.
            last_sample = self._session.samples[-1] if self._session.samples else None
            prev_time = last_sample.time_s if last_sample else 0.0
            prev_torque = last_sample.torque_Nm if last_sample else status.net_weight
            prev_angle = last_sample.angle_deg if last_sample else self._current_angle
            span = max(interval_s, elapsed_time - prev_time)

            while self._session.count <= expected_samples:
                rec_time = self._session.count * interval_s
                ratio = max(0.0, min(1.0, (rec_time - prev_time) / span))
                sample = SampleData(
                    time_s=rec_time,
                    torque_Nm=prev_torque + (status.net_weight - prev_torque) * ratio,
                    stable=status.is_stable,
                    timestamp=time.time(),
                    angle_deg=prev_angle + (self._current_angle - prev_angle) * ratio,
                    cycle=self._current_cycle,
                )
                self._session.samples.append(sample)
                
            self.lbl_count.setText(str(self._session.count))
            self.lbl_rectime.setText(f"{elapsed_time:.3f} s")

    def _on_error(self, msg: str):
        self._log(f"⚠️ {msg}")
        if self._connected:
            self.lbl_conn_status.setText("🟡 Lỗi đọc Modbus")

    # ===========================================================
    # CONFIG
    # ===========================================================

    def _write_config(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
            
        try:
            cfg = DeviceConfig(
                measure_unit=self.combo_unit.currentData() if self.combo_unit.currentData() is not None else 8,
                measure_type=self.combo_mtype.currentIndex(),
                analog_out_type=self._dev_cfg.analog_out_type,
                dio_type=self._dev_cfg.dio_type,
                calib_mode=self.combo_calib.currentIndex() if hasattr(self, 'combo_calib') else self._dev_cfg.calib_mode,
                
                cell_full_scale=self.spin_fs.value(),
                cell_sensitivity=self.spin_sens.value(),
                
                std_weight=self._dev_cfg.std_weight,
                delta_weight=self._dev_cfg.delta_weight,
                delta_time=self._dev_cfg.delta_time,
                
                filter_level=self.combo_filter.currentData() if self.combo_filter.currentData() is not None else 3,
                resolution_mode=self._dev_cfg.resolution_mode,
                factory_tare=self._dev_cfg.factory_tare,
                
                target_address=self._dev_cfg.target_address,
                target_baud=self._dev_cfg.target_baud,
                target_parity=self._dev_cfg.target_parity,
                
                slave_id=self.spin_slave.value(),
            )
            
            self._log("⏳ Đang ghi cấu hình...")
            ok, failed_fields = self._config_svc.write_config(cfg)
            
            if ok:
                self._log("✅ Đã ghi cấu hình thành công")
                self._settings.save_device_config(cfg)
                self._dev_cfg = cfg
            else:
                err_msg = ", ".join(failed_fields)
                self._log(f"❌ Ghi thất bại tại: {err_msg}")
        except Exception as e:
            self._log(f"❌ Lỗi xử lý cấu hình: {e}")

    def _read_config(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        
        cfg = self._config_svc.read_config(self.spin_slave.value())
        if cfg:
            self.combo_unit.setCurrentIndex(cfg.measure_unit)
            self.combo_mtype.setCurrentIndex(cfg.measure_type)
            
            self.spin_fs.setValue(cfg.cell_full_scale)
            self.spin_sens.setValue(cfg.cell_sensitivity)
            
            self.combo_filter.setCurrentIndex(cfg.filter_level)
            
            self._dev_cfg = cfg
            self._log(f"📖 Đọc thành công: Unit={cfg.measure_unit}, FS={cfg.cell_full_scale:.2f}, Sens={cfg.cell_sensitivity:.4f}")
        else:
            self._log("❌ Không đọc được cấu hình từ thiết bị")

    def _do_tare(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        
        # Check ổn định từ manual Seneca ZE-SG3 (nên tare khi stable)
        if self._last_status and not self._last_status.is_stable:
            self._log("⚠️ Cảnh báo: Trọng lượng không ổn định. Lệnh Tare có thể bị thiết bị từ chối.")
        
        # CMD_TARE (49914) ghi vào Flash - bền vững nhưng chậm
        # CMD_TARE_RAM (49594) ghi vào RAM - nhanh hơn, dùng cho tare thường xuyên
        ok = self._config_svc.send_command(CMD_TARE, self.spin_slave.value())
        if ok:
            self._log("⚖️ Đã gửi lệnh Tare (49914 → Flash)")
        else:
            self._log("❌ Lỗi Tare (Kiểm tra ổn định hoặc Timeout)")

    def _do_restart(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        ok = self._config_svc.send_command(CMD_RESTART, self.spin_slave.value())
        self._log("🔄 Đã gửi lệnh Restart (43948)" if ok else "❌ Lỗi Restart")

    def _do_tare_ram(self):
        """Tare lưu RAM – nhanh, mất khi restart."""
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        if self._last_status and not self._last_status.is_stable:
            self._log("⚠️ Cảnh báo: Trọng lượng không ổn định.")
        ok = self._config_svc.tare_ram(self.spin_slave.value())
        if ok:
            self._log("⚖️ Đã gửi lệnh Tare RAM (49594)")
        else:
            self._log("❌ Lỗi Tare RAM")

    def _do_reset_minmax(self):
        """Reset cả Min và Max Net Weight."""
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        sid = self.spin_slave.value()
        ok_max = self._config_svc.reset_max(sid)
        ok_min = self._config_svc.reset_min(sid)
        if ok_max and ok_min:
            self._log("🔁 Đã reset Min/Max thành công")
        else:
            self._log(f"⚠️ Reset Min/Max: Max={'OK' if ok_max else 'FAIL'}, Min={'OK' if ok_min else 'FAIL'}")

    def _calib_step1_tare(self):
        """Bước 1 của Calibration Wizard: Acquire Tare."""
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        if self._last_status and not self._last_status.is_stable:
            self._log("⚠️ Cảm biến chưa ổn định! Chờ 🟢 Stable trước khi Tare.")
            self.lbl_calib_status.setText("🟡 Chờ ổn định...")
            return
        ok = self._config_svc.tare_flash(self.spin_slave.value())
        if ok:
            self.lbl_calib_status.setText("✅ Bước 1 hoàn tất – Đã Tare")
            self._log("🔬 Wizard Bước 1: Tare thành công")
        else:
            self.lbl_calib_status.setText("❌ Tare thất bại")
            self._log("❌ Wizard Bước 1: Tare thất bại")

    def _calib_step3_acquire(self):
        """Bước 3 của Calibration Wizard: Acquire Sample Weight."""
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        if self._last_status and not self._last_status.is_stable:
            self._log("⚠️ Cảm biến chưa ổn định! Chờ 🟢 Stable trước khi hiệu chuẩn.")
            self.lbl_calib_status.setText("🟡 Chờ ổn định...")
            return
        std_weight = self.spin_calib_std.value()
        if std_weight <= 0:
            self._log("❌ Giá trị mẫu phải > 0"); return
        
        self.lbl_calib_status.setText("⏳ Đang hiệu chuẩn...")
        QApplication.processEvents()
        
        ok = self._config_svc.calibrate_with_sample_weight(
            std_weight, self.spin_slave.value()
        )
        if ok:
            self.lbl_calib_status.setText(f"✅ Hiệu chuẩn thành công ({std_weight} Nm)")
            self._log(f"🔬 Wizard Bước 3: Hiệu chuẩn mẫu {std_weight} Nm thành công")
        else:
            self.lbl_calib_status.setText("❌ Hiệu chuẩn thất bại")
            self._log("❌ Wizard Bước 3: Hiệu chuẩn thất bại")

    # ===========================================================
    # RECORDING
    # ===========================================================

    def _start_recording(self):
        # R2 Upgrade: prepare Servo/PLC profile before enabling local recording.
        part_name = self.combo_part_name.currentText() if hasattr(self, 'combo_part_name') else 'ITR'
        test_item = self.combo_test_item.currentText() if hasattr(self, 'combo_test_item') else 'Operating'
        part_map = {
            'Inner Tie Rod': 'ITR',
            'Ball Joint': 'B/Joint',
            'Outer Tie Rod': 'OTR',
            'Stabilizer Link': 'S/Link',
            'ITR': 'ITR',
            'B/Joint': 'B/Joint',
            'OTR': 'OTR',
            'S/Link': 'S/Link'
        }
        part_short = part_map.get(part_name, 'ITR')
        is_breakaway = "Breakaway" in test_item
        test_char = 'B' if is_breakaway else 'O'
        profile_key = f"{part_short}_{test_char}"

        profiles = self._settings.load_servo_profiles()
        profile = profiles.get(profile_key)
        if not profile:
            from domain.entities import ServoProfile
            profile = ServoProfile(
                negative_angle=-36.0,
                positive_angle=36.0,
                speed=100.0
            )

        if not self._prepare_plc_recording(profile, is_breakaway):
            if self._bus_scheduler:
                self._bus_scheduler.set_recording_active(False)
            return

        self._session = RecordingSession(sample_interval_ms=self.spin_interval.value())
        self._session.test_item = 'B' if is_breakaway else 'O'
        self._session.part_name = part_short
        now_mono = time.monotonic()
        self._session.start_time = now_mono
        self._start_time = now_mono
        self._recording = True
        self.btn_rec_start.setEnabled(False)
        self.btn_rec_stop.setEnabled(True)
        self.btn_rec_clear.setEnabled(False)
        self.lbl_count.setText("0")
        self._current_angle = 0.0
        self._current_cycle = 1
        if hasattr(self, 'angle_plot'):
            self.angle_plot.clear()
        if self._bus_scheduler:
            self._bus_scheduler.set_recording_active(True)
        self._log("▶️ Bắt đầu ghi dữ liệu")

        if self._servo_svc and (not self._plc_svc or not self._plc_svc.is_connected()):
            if is_breakaway:
                ok = self._servo_svc.start_breakaway_test(profile)
            else:
                ok = self._servo_svc.start_operating_test(profile, num_cycles=getattr(profile, 'cycles', 3))
            if ok:
                self._log(f"🚀 Khởi chạy Servo fallback: {profile_key} (tốc độ: {profile.speed} rpm)")
            else:
                self._log("❌ Không thể khởi chạy Servo sequence!")

    def _stop_recording(self):
        was_recording = self._recording
        self._session.end_time = time.monotonic()
        self._recording = False
        if self._bus_scheduler:
            self._bus_scheduler.set_recording_active(False)
        duration = self._session.end_time - self._session.start_time
        self.btn_rec_start.setEnabled(True)
        self.btn_rec_stop.setEnabled(False)
        self.btn_rec_clear.setEnabled(True)
        self._log(f"⏹ Đã dừng ghi – {self._session.count} mẫu, {duration:.1f}s")

        # R2 Upgrade: Stop PLC/Servo sequence if running
        if was_recording and self._plc_svc and self._plc_svc.is_connected():
            self._plc_svc.stop_record()
            self._log("⏹ Đã gửi STOP_RECORD tới PLC")
        if self._servo_svc and self._servo_svc.is_running():
            self._servo_svc.stop()
            self._log("⏹ Đã dừng chu trình Servo")

    def _clear_samples(self):
        self._session = RecordingSession(sample_interval_ms=self.spin_interval.value())
        self.lbl_count.setText("0")
        self.lbl_rectime.setText("0.0 s")
        self.btn_rec_clear.setEnabled(False)
        if self._bus_scheduler:
            self._bus_scheduler.set_recording_active(False)
        self._log("🗑️ Đã xóa dữ liệu mẫu")

    # ===========================================================
    # EXPORT
    # ===========================================================

    def _export(self, exporter: IDataExporter):
        if not self._session.samples:
            self._log("⚠️ Không có dữ liệu"); return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"torque_{ts}{exporter.file_extension}"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Lưu – {exporter.display_name}", default_name,
            f"Files (*{exporter.file_extension})"
        )
        if path:
            ok = exporter.export(self._session, path)
            self._log(f"💾 Xuất {'thành công' if ok else 'thất bại'}: {path}")

    # ===========================================================
    # IMPORT TO PLOT VIEWER / CONVERTER
    # ===========================================================

    def _export_session_to_temp_csv(self) -> str:
        """Export session hiện tại ra file CSV tạm (CTR format) để import vào tool khác."""
        if not self._session.samples:
            return ""
        # Tìm exporter CTR
        ctr_exp = None
        for exp in self._exporters:
            if "CTR" in exp.display_name:
                ctr_exp = exp
                break
        if ctr_exp is None and self._exporters:
            ctr_exp = self._exporters[0]
        if ctr_exp is None:
            return ""
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"ze_sg3_session_{ts}.csv")
        ok = ctr_exp.export(self._session, tmp_path)
        return tmp_path if ok else ""

    def _on_btn_servo_setup_clicked(self):
        from PyQt5.QtWidgets import QDialog
        part = self.combo_part_name.currentText()
        test = self.combo_test_item.currentText()
        dialog = ServoSetupDialog(self, self._settings, part, test, self.i18n)
        if dialog.exec_() == QDialog.Accepted:
            vals = dialog.get_values()
            
            # Map selected part and test type to profile key
            part_map = {
                'Inner Tie Rod': 'ITR', 'Ball Joint': 'B/Joint', 'Outer Tie Rod': 'OTR', 'Stabilizer Link': 'S/Link',
                'ITR': 'ITR', 'B/Joint': 'B/Joint', 'OTR': 'OTR', 'S/Link': 'S/Link'
            }
            part_short = part_map.get(part, 'ITR')
            is_breakaway = "Breakaway" in test or "B" == test
            test_char = 'B' if is_breakaway else 'O'
            profile_key = f"{part_short}_{test_char}"
            
            # Load, modify, and save
            profiles = self._settings.load_servo_profiles()
            from domain.entities import ServoProfile
            profiles[profile_key] = ServoProfile(
                negative_angle=vals['negative_angle'],
                positive_angle=vals['positive_angle'],
                speed=vals['speed'],
                jog_speed=vals['jog_speed']
            )
            self._settings.save_servo_profiles(profiles)
            
            self._log(f"✅ Đã cập nhật cấu hình cho {profile_key}: Speed={vals['speed']} rpm, JOG Speed={vals['jog_speed']} rpm, Pos={vals['positive_angle']}°, Neg={vals['negative_angle']}°")
            
            # Cập nhật ô JOG speed trên UI chính
            if hasattr(self, 'spin_plc_jog_speed'):
                self.spin_plc_jog_speed.blockSignals(True)
                self.spin_plc_jog_speed.setValue(vals['jog_speed'])
                self.spin_plc_jog_speed.blockSignals(False)
            
            # Ghi tốc độ JOG mới xuống PLC qua D104 nếu đang kết nối
            if self._plc_svc and self._plc_svc.is_connected():
                if self._plc_svc.write_speed(vals['jog_speed']):
                    self._log(f"⚡ Đã ghi tốc độ JOG {vals['jog_speed'] * 100:.0f} Hz xuống PLC (D104)")
                else:
                    self._log(f"⚠️ Ghi tốc độ JOG xuống PLC (D104) thất bại")

    def _import_to_plot_viewer(self):
        """Export session CSV -> load vào Plot Viewer -> nhảy sang tab."""
        if not _HAS_PLOT_VIEWER or not hasattr(self, '_plot_viewer'):
            self._log("⚠️ Plot Viewer chưa sẵn sàng"); return
        if not self._session.samples:
            self._log("⚠️ Không có dữ liệu để import"); return
        tmp = self._export_session_to_temp_csv()
        if not tmp:
            self._log("⚠️ Xuất CSV tạm thất bại"); return

        # Đồng bộ hóa Test Item & Part Name trực tiếp từ UI Thu thập sang Plot Viewer
        if hasattr(self, 'combo_test_item'):
            self._plot_viewer.test_item_combo.setCurrentText(self.combo_test_item.currentText())
        
        if hasattr(self, 'combo_part_name'):
            self._plot_viewer.part_name_combo.setCurrentText(self.combo_part_name.currentText())

        ok = self._plot_viewer.load_file_from_path(tmp)
        if ok:
            self.main_tabs.setCurrentIndex(1)  # Tab Plot Viewer
            self._log(f"📊 Đã import {self._session.count} mẫu sang Plot Viewer")
        else:
            self._log("⚠️ Import sang Plot Viewer thất bại")

    def _sync_part_name_to_plot_viewer(self, text: str):
        if not _HAS_PLOT_VIEWER or not hasattr(self, '_plot_viewer'):
            return
        self._plot_viewer.part_name_combo.blockSignals(True)
        self._plot_viewer.part_name_combo.setCurrentText(text)
        self._plot_viewer.part_name_combo.blockSignals(False)

    def _sync_test_item_to_plot_viewer(self, text: str):
        if not _HAS_PLOT_VIEWER or not hasattr(self, '_plot_viewer'):
            return
        self._plot_viewer.test_item_combo.blockSignals(True)
        self._plot_viewer.test_item_combo.setCurrentText(text)
        self._plot_viewer.test_item_combo.blockSignals(False)

    def _sync_part_name_to_acquisition(self, text: str):
        if not hasattr(self, 'combo_part_name'):
            return
        self.combo_part_name.blockSignals(True)
        self.combo_part_name.setCurrentText(text)
        self.combo_part_name.blockSignals(False)

    def _sync_test_item_to_acquisition(self, text: str):
        if not hasattr(self, 'combo_test_item'):
            return
        self.combo_test_item.blockSignals(True)
        self.combo_test_item.setCurrentText(text)
        self.combo_test_item.blockSignals(False)

    # ===========================================================
    # UTIL
    # ===========================================================

    def _clear_chart(self):
        self.plot.clear()
        if hasattr(self, 'angle_plot'):
            self.angle_plot.clear()
        self._ref_time = time.monotonic()
        self._log(self.i18n.t('msg_chart_cleared') if hasattr(self, 'i18n') else "🗑️ Đã xóa biểu đồ")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")
        logger.info(msg)

    def closeEvent(self, a0):
        """Tự động lưu cài đặt và ngắt kết nối khi đóng app."""
        self._save_settings_from_ui()
        # Lưu theme khi thoát
        ui = self._settings.load_ui_settings()
        ui['dark_theme'] = self._is_dark
        ui['interval_ms'] = self.spin_interval.value()
        ui['window_s'] = self.spin_window.value()
        if hasattr(self, 'i18n'):
            ui['language'] = self.i18n.current_language
        self._settings.save_ui_settings(ui)
        if self._connected:
            self._disconnect()
        super().closeEvent(a0)

    # ===========================================================
    # BILINGUAL & SERVO CALLBACKS
    # ===========================================================

    def _update_language_btn_text(self):
        if self.i18n.current_language == 'vi':
            self.btn_toggle_lang.setText("🌐 English (EN)")
        else:
            self.btn_toggle_lang.setText("🌐 Tiếng Việt (VI)")

    def _toggle_language(self):
        new_lang = self.i18n.toggle()
        self._retranslate_ui()
        self._update_language_btn_text()
        
        # Lưu vào settings
        ui = self._settings.load_ui_settings()
        ui['language'] = new_lang
        self._settings.save_ui_settings(ui)
        self._log(f"🌐 Đổi ngôn ngữ thành: {new_lang.upper()}")

    def _retranslate_ui(self):
        # 1. Main tabs & sub tabs
        self.main_tabs.setTabText(0, self.i18n.t('tab_acquisition'))
        self.main_tabs.setTabText(1, self.i18n.t('tab_plot_viewer'))
        
        self.tabs.setTabText(0, self.i18n.t('tab_connection'))
        self.tabs.setTabText(1, self.i18n.t('tab_config'))
        self.tabs.setTabText(2, self.i18n.t('tab_acquisition'))

        # 2. Display Group
        if hasattr(self, 'display_panel_grp'):
            self.display_panel_grp.setTitle(self.i18n.t('display_grp'))
        if hasattr(self, 'lbl_display_torque_title'):
            self.lbl_display_torque_title.setText(self.i18n.t('lbl_torque'))
        if hasattr(self, 'lbl_display_status_title'):
            self.lbl_display_status_title.setText(self.i18n.t('lbl_status'))
        if hasattr(self, 'lbl_display_samples_title'):
            self.lbl_display_samples_title.setText(self.i18n.t('lbl_samples'))
        if hasattr(self, 'lbl_display_tare_title'):
            self.lbl_display_tare_title.setText(self.i18n.t('lbl_tare'))
        if hasattr(self, 'lbl_display_time_title'):
            self.lbl_display_time_title.setText(self.i18n.t('lbl_time'))
        if hasattr(self, 'lbl_display_max_title'):
            self.lbl_display_max_title.setText(self.i18n.t('lbl_max'))
        if hasattr(self, 'lbl_display_min_title'):
            self.lbl_display_min_title.setText(self.i18n.t('lbl_min'))
        if hasattr(self, 'lbl_display_plc_angle_title'):
            self.lbl_display_plc_angle_title.setText(self.i18n.t('lbl_plc_angle'))

        # Retranslate connection status live text
        if not self._connected:
            self.lbl_conn_status.setText(self.i18n.t('status_unconnected'))
        else:
            self.lbl_conn_status.setText(self.i18n.t('status_connected'))

        # 3. Connection Tab
        if hasattr(self, 'grp_proto'):
            self.grp_proto.setTitle(self.i18n.t('proto_grp'))
        if hasattr(self, 'lbl_proto_type'):
            self.lbl_proto_type.setText(self.i18n.t('proto_lbl'))
        if hasattr(self, 'grp_rtu'):
            self.grp_rtu.setTitle(self.i18n.t('rtu_grp'))
        if hasattr(self, 'lbl_com_port'):
            self.lbl_com_port.setText(self.i18n.t('com_lbl'))
        if hasattr(self, 'btn_scan'):
            self.btn_scan.setToolTip(self.i18n.t('btn_scan_tooltip'))
        if hasattr(self, 'lbl_baudrate'):
            self.lbl_baudrate.setText(self.i18n.t('baud_lbl'))
        if hasattr(self, 'lbl_parity'):
            self.lbl_parity.setText(self.i18n.t('parity_lbl'))
        if hasattr(self, 'grp_tcp'):
            self.grp_tcp.setTitle(self.i18n.t('tcp_grp'))
        if hasattr(self, 'lbl_tcp_ip'):
            self.lbl_tcp_ip.setText(self.i18n.t('ip_lbl'))
        if hasattr(self, 'lbl_tcp_port'):
            self.lbl_tcp_port.setText(self.i18n.t('port_lbl'))
        if hasattr(self, 'grp_slave'):
            self.grp_slave.setTitle(self.i18n.t('slave_grp'))
        if hasattr(self, 'lbl_slave_id'):
            self.lbl_slave_id.setText(self.i18n.t('sensor_slave_lbl'))
        if hasattr(self, 'lbl_plc_slave_id'):
            self.lbl_plc_slave_id.setText(self.i18n.t('plc_slave_lbl'))
        if hasattr(self, 'btn_modbus_status'):
            self.btn_modbus_status.setText(self.i18n.t('btn_modbus_status'))
        
        # Connect Button
        self._update_connect_btn_style()

        # 4. Config Tab
        if hasattr(self, 'grp_sensor'):
            self.grp_sensor.setTitle(self.i18n.t('sensor_grp'))
        if hasattr(self, 'lbl_measure_unit'):
            self.lbl_measure_unit.setText(self.i18n.t('unit_lbl'))
        if hasattr(self, 'lbl_measure_mode'):
            self.lbl_measure_mode.setText(self.i18n.t('mode_lbl'))
        if hasattr(self, 'lbl_full_scale'):
            self.lbl_full_scale.setText(self.i18n.t('fs_lbl'))
        if hasattr(self, 'lbl_sensitivity'):
            self.lbl_sensitivity.setText(self.i18n.t('sens_lbl'))
        if hasattr(self, 'grp_stability'):
            self.grp_stability.setTitle(self.i18n.t('stable_grp'))
        if hasattr(self, 'lbl_filter_level'):
            self.lbl_filter_level.setText(self.i18n.t('filter_lbl'))
        if hasattr(self, 'btn_write_cfg'):
            self.btn_write_cfg.setText(self.i18n.t('btn_write_cfg'))
        if hasattr(self, 'btn_read_cfg'):
            self.btn_read_cfg.setText(self.i18n.t('btn_read_cfg'))
        if hasattr(self, 'grp_quick_cmd'):
            self.grp_quick_cmd.setTitle(self.i18n.t('quick_cmd_grp'))
        if hasattr(self, 'btn_quick_tare'):
            self.btn_quick_tare.setText(self.i18n.t('btn_quick_tare'))
        if hasattr(self, 'btn_quick_restart'):
            self.btn_quick_restart.setText(self.i18n.t('btn_quick_restart'))

        # 5. Acquisition Tab
        if hasattr(self, 'grp_sampling'):
            self.grp_sampling.setTitle(self.i18n.t('sampling_grp'))
        if hasattr(self, 'lbl_sample_interval'):
            self.lbl_sample_interval.setText(self.i18n.t('interval_lbl'))
        if hasattr(self, 'lbl_chart_window'):
            self.lbl_chart_window.setText(self.i18n.t('window_lbl'))
        if hasattr(self, 'lbl_y_limits'):
            self.lbl_y_limits.setText(self.i18n.t('ymax_lbl'))
        if hasattr(self, 'chk_fixed_y'):
            self.chk_fixed_y.setText(self.i18n.t('chk_fixed_y'))
        
        if hasattr(self, 'grp_program'):
            self.grp_program.setTitle(self.i18n.t('part_program_grp'))
        if hasattr(self, 'lbl_part_name'):
            self.lbl_part_name.setText(self.i18n.t('part_name_lbl'))
        if hasattr(self, 'lbl_test_item'):
            self.lbl_test_item.setText(self.i18n.t('test_item_lbl'))
        if hasattr(self, 'btn_servo_setup'):
            self.btn_servo_setup.setText(self.i18n.t('btn_servo_setup'))
        if hasattr(self, 'lbl_plc_jog_speed'):
            self.lbl_plc_jog_speed.setText(self.i18n.t('lbl_plc_jog_speed'))

        if hasattr(self, 'grp_recording'):
            self.grp_recording.setTitle(self.i18n.t('recording_grp'))
        if hasattr(self, 'btn_rec_start'):
            self._update_rec_start_btn_style()
            if not self._recording:
                self.btn_rec_start.setText(self.i18n.t('btn_start_record'))
            else:
                self.btn_rec_start.setText(self.i18n.t('btn_stop_record'))
        if hasattr(self, 'btn_rec_stop'):
            self.btn_rec_stop.setText(self.i18n.t('btn_stop_record'))
        if hasattr(self, 'btn_rec_clear'):
            self.btn_rec_clear.setText(self.i18n.t('btn_clear_samples'))
        if hasattr(self, 'btn_tare_acq'):
            self.btn_tare_acq.setText(self.i18n.t('btn_tare_acq'))
        
        if hasattr(self, 'grp_export'):
            self.grp_export.setTitle(self.i18n.t('export_grp'))
        if hasattr(self, 'exporter_buttons'):
            for exp, btn in self.exporter_buttons.items():
                display_name = exp.display_name
                if exp.__class__.__name__ == 'CsvSimpleExporter':
                    display_name = self.i18n.t('csv_simple_display_name')
                btn.setText(f"📄 {display_name}")
        if hasattr(self, 'grp_import_tools'):
            self.grp_import_tools.setTitle(self.i18n.t('import_tools_grp'))
        if hasattr(self, 'btn_import_plot'):
            self.btn_import_plot.setText(self.i18n.t('btn_import_plot'))

        # 6. Chart Group
        if hasattr(self, 'chart_group'):
            self.chart_group.setTitle(self.i18n.t('chart_torque_time') + " & " + self.i18n.t('chart_torque_angle'))
        if hasattr(self, 'btn_pause_chart'):
            self.btn_pause_chart.setText(
                self.i18n.t('btn_resume_chart') if self._chart_paused else self.i18n.t('btn_pause_chart')
            )
        if hasattr(self, 'btn_clear_chart'):
            self.btn_clear_chart.setText(self.i18n.t('btn_clear_chart'))
        if hasattr(self, 'combo_mtype'):
            current_data = self.combo_mtype.currentData()
            self.combo_mtype.blockSignals(True)
            self.combo_mtype.setItemText(0, self.i18n.t('measure_mode_0'))
            self.combo_mtype.setItemText(1, self.i18n.t('measure_mode_1'))
            idx = self.combo_mtype.findData(current_data)
            if idx >= 0:
                self.combo_mtype.setCurrentIndex(idx)
            self.combo_mtype.blockSignals(False)
        if hasattr(self, 'combo_filter'):
            current_data = self.combo_filter.currentData()
            self.combo_filter.blockSignals(True)
            for idx in range(self.combo_filter.count()):
                data = self.combo_filter.itemData(idx)
                self.combo_filter.setItemText(idx, self.i18n.t(f'filter_{data}'))
            idx = self.combo_filter.findData(current_data)
            if idx >= 0:
                self.combo_filter.setCurrentIndex(idx)
            self.combo_filter.blockSignals(False)
        if hasattr(self, 'btn_toggle_theme'):
            self._update_theme_btn_text()
        
        # Redraw charts with translated titles and axes labels
        if hasattr(self, 'plot'):
            self.plot.ax.set_title(self.i18n.t('chart_title_time'), fontsize=11, fontweight='bold')
            self.plot.ax.set_xlabel(self.i18n.t('axis_time'))
            self.plot.ax.set_ylabel(self.i18n.t('axis_torque'))
            self.plot.draw_idle()

        if hasattr(self, 'angle_plot'):
            self.angle_plot.ax.set_title(self.i18n.t('chart_title_angle'), fontsize=11, fontweight='bold')
            self.angle_plot.ax.set_xlabel(self.i18n.t('axis_angle'))
            self.angle_plot.ax.set_ylabel(self.i18n.t('axis_torque'))
            self.angle_plot._bg = None  # Invalidate blit cache
            self.angle_plot.draw_idle()

        # 7. Log Group
        if hasattr(self, 'grp_log'):
            self.grp_log.setTitle(self.i18n.t('display_grp') if self.i18n.current_language == 'en' else "📝 Terminal Log")

    # === Servo callbacks ===

    def _on_servo_angle_updated(self, angle: float, cycle: int, recording_active: bool):
        self._current_angle = angle
        self._current_cycle = cycle
        
        # R2 Upgrade: Automatically stop data collection in Breakaway when outgoing direction is done
        if self._recording and not recording_active:
            self._recording = False
            self.btn_rec_start.setEnabled(True)
            self.btn_rec_stop.setEnabled(False)
            self.btn_rec_clear.setEnabled(True)
            self._log(f"⏹ Đã dừng ghi (Tự động ngắt khi hết chiều đi) – {self._session.count} mẫu")

    def _on_servo_finished(self):
        self._sig_servo_finished.emit()

    def _on_servo_error(self, err_msg: str):
        self._sig_servo_error.emit(err_msg)

    def _handle_servo_finished(self):
        self._log("🏁 Chu trình chạy Servo đã hoàn thành")
        # R2 Upgrade: Auto-stop recording if it is still running
        if self._recording:
            self._stop_recording()

    def _handle_servo_error(self, err_msg: str):
        self._log(f"❌ Lỗi Servo: {err_msg}")
        # R2 Upgrade: Auto-stop recording if it is running
        if self._recording:
            self._stop_recording()
        QMessageBox.warning(self, self.i18n.t('msg_err'), f"Lỗi Servo: {err_msg}")
