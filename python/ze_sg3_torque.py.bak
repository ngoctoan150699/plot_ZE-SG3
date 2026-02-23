#!/usr/bin/env python3
"""
Seneca ZE-SG3 Torque Data Acquisition System
=============================================
✅ Giao tiếp Modbus RTU/TCP với bộ khuếch đại Seneca ZE-SG3
✅ Thu thập dữ liệu Torque từ cảm biến DYJN-101 50Nm
✅ Biểu đồ Torque theo thời gian thời gian thực
✅ Xuất CSV với 2 định dạng: Đơn giản và CTR DATA FORMAT #1
✅ Cấu hình thanh ghi theo tài liệu MI00617-4-EN

Bản đồ thanh ghi ZE-SG3 (Holding Registers 4x):
- 40003: Đơn vị đo (5=N cho N.m)
- 40004: Chế độ đo (0=Bipolar lưỡng cực)
- 40007: Chế độ hiệu chuẩn (0=Factory)
- 40014-40015: Độ nhạy cảm biến (Float32 mV/V)
- 40016-40017: Tầm đo tối đa (Float32)
- 40043: Mức lọc nhiễu (0-6; 7=Advanced)
- 40064-40065: Giá trị lực thực tế Net Weight (Float32)
- 40078: Thanh ghi trạng thái (Bit 4 = Stable Weight)
- 40080: Thanh ghi lệnh (49914=Tare, 43948=Restart)
- 40094-40095: ADC RAW (Unsigned 32)
"""

import sys
import struct
import threading
import time
import csv
import json
from collections import deque
from datetime import datetime
from pathlib import Path

import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QComboBox, QPushButton,
    QTextEdit, QDoubleSpinBox, QSpinBox, QTabWidget, QCheckBox,
    QFileDialog, QMessageBox, QSplitter, QFrame
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.path

# === FIX RecursionError Matplotlib on Python 3.14 ===
# Lỗi này xảy ra do deepcopy chạy vô hạn trong matplotlib.path.Path
# Ta xóa hàm __deepcopy__ bị lỗi để Python dùng cơ chế mặc định
try:
    del matplotlib.path.Path.__deepcopy__
except AttributeError:
    pass
# ====================================================

# Modbus client
try:
    from pymodbus.client.sync import ModbusSerialClient
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client import ModbusSerialClient, ModbusTcpClient
    except ImportError:
        ModbusSerialClient = None
        ModbusTcpClient = None

# ================== ZE-SG3 REGISTER MAP ==================
# Địa chỉ thanh ghi (base-0 cho pymodbus, tài liệu dùng 40001 = addr 0)
REG_MEASURE_UNIT = 2          # 40003: Đơn vị đo
REG_MEASURE_TYPE = 3          # 40004: Chế độ đo (0=Bipolar)
REG_CALIB_MODE = 6            # 40007: Chế độ hiệu chuẩn
REG_CELL_SENS_HI = 13         # 40014: Cell Sensitivity (Float32 MSW)
REG_CELL_SENS_LO = 14         # 40015: Cell Sensitivity (Float32 LSW)
REG_CELL_FS_HI = 15           # 40016: Cell Full Scale (Float32 MSW)
REG_CELL_FS_LO = 16           # 40017: Cell Full Scale (Float32 LSW)
REG_FILTER_LEVEL = 42         # 40043: Mức lọc nhiễu
REG_NET_WEIGHT_HI = 63        # 40064: Net Weight (Float32 MSW)
REG_NET_WEIGHT_LO = 64        # 40065: Net Weight (Float32 LSW)
REG_STATUS = 77               # 40078: Thanh ghi trạng thái
REG_COMMAND = 79              # 40080: Thanh ghi lệnh
REG_ADC_RAW_HI = 93           # 40094: ADC RAW (Unsigned32 MSW)
REG_ADC_RAW_LO = 94           # 40095: ADC RAW (Unsigned32 LSW)

# Lệnh điều khiển
CMD_TARE = 49914              # Lấy Tare (điểm không)
CMD_RESTART = 43948           # Khởi động lại thiết bị
CMD_SAMPLE_CALIB = 50700      # Hiệu chuẩn bằng trọng lượng mẫu

# Đơn vị đo
UNITS = {0: 'Kg', 1: 'g', 2: 't', 3: 'lb', 4: 'l', 5: 'N', 6: 'bar', 7: 'atm', 8: 'other'}

# Mặc định cho DYJN-101 50Nm
DEFAULT_MEASURE_UNIT = 5      # N (Newton)
DEFAULT_MEASURE_TYPE = 0      # Bipolar
DEFAULT_CELL_FS = 50.0        # 50 Nm
DEFAULT_SAMPLE_INTERVAL_MS = 100


def float32_from_regs(hi: int, lo: int) -> float:
    """Chuyển đổi 2 thanh ghi 16-bit thành Float32 IEEE 754 (MSW first)."""
    try:
        packed = struct.pack('>HH', hi & 0xFFFF, lo & 0xFFFF)
        return struct.unpack('>f', packed)[0]
    except Exception:
        return 0.0


def float32_to_regs(value: float) -> tuple:
    """Chuyển đổi Float32 thành 2 thanh ghi 16-bit (MSW, LSW)."""
    try:
        packed = struct.pack('>f', value)
        hi, lo = struct.unpack('>HH', packed)
        return (hi, lo)
    except Exception:
        return (0, 0)


class RealTimePlot(FigureCanvas):
    """Widget biểu đồ thời gian thực"""
    def __init__(self, title="Plot", xlabel="X", ylabel="Y", max_time_window_s=60.0):
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        self.title = title
        self.max_time_window_s = max_time_window_s
        self.x_data = []
        self.y_data = []
        
        self.line, = self.ax.plot([], [], 'b-', linewidth=1.0, antialiased=True)
        self.ax.set_title(title, fontsize=11, fontweight='bold')
        self.ax.set_xlabel(xlabel, fontsize=10)
        self.ax.set_ylabel(ylabel, fontsize=10)
        self.ax.grid(True, alpha=0.3)
        self.fig.tight_layout()
        
        self._last_draw_time = 0.0
    
    def update_plot(self, x, y):
        """Thêm điểm dữ liệu mới và cập nhật biểu đồ"""
        self.x_data.append(x)
        self.y_data.append(y)
        
        # Giới hạn cửa sổ thời gian
        if self.max_time_window_s and len(self.x_data) > 0:
            cutoff = x - self.max_time_window_s
            while self.x_data and self.x_data[0] < cutoff:
                self.x_data.pop(0)
                self.y_data.pop(0)
        
        # Throttle vẽ lại (~30 FPS)
        now = time.time()
        if (now - self._last_draw_time) >= 0.033:
            self.line.set_data(self.x_data, self.y_data)
            self.ax.relim()
            self.ax.autoscale_view()
            self.draw_idle()
            self._last_draw_time = now
    
    def clear_plot(self):
        """Xóa dữ liệu biểu đồ"""
        self.x_data.clear()
        self.y_data.clear()
        self.line.set_data([], [])
        self.draw()


class ZE_SG3_App(QMainWindow):
    """Ứng dụng thu thập dữ liệu Torque từ Seneca ZE-SG3"""
    
    log_signal = pyqtSignal(str)
    data_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.modbus_client = None
        self.connected = False
        self.slave_id = 1
        self.connection_type = 'RTU'  # RTU hoặc TCP
        
        # Threading
        self._poll_stop = threading.Event()
        self._poll_thread = None
        self._sample_interval_ms = DEFAULT_SAMPLE_INTERVAL_MS
        
        # Dữ liệu
        self._samples = []
        self._start_time = None
        self._current_torque = 0.0
        self._is_stable = False
        self._recording = False
        
        self.init_ui()
        self.log_signal.connect(self.append_log)
        self.data_signal.connect(self.on_data_received)
        self.refresh_com_ports()
    
    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("Seneca ZE-SG3 - Torque Data Acquisition (DYJN-101 50Nm)")
        self.setGeometry(100, 100, 1200, 800)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Splitter chính
        splitter = QSplitter(Qt.Horizontal)
        
        # === Panel trái: Cài đặt ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Tab cài đặt
        tabs = QTabWidget()
        
        # --- Tab Kết nối ---
        conn_tab = QWidget()
        conn_layout = QVBoxLayout(conn_tab)
        
        # Loại kết nối
        type_group = QGroupBox("🔌 Loại kết nối")
        type_layout = QGridLayout()
        type_layout.addWidget(QLabel("Giao thức:"), 0, 0)
        self.conn_type_combo = QComboBox()
        self.conn_type_combo.addItems(["Modbus RTU", "Modbus TCP"])
        self.conn_type_combo.currentTextChanged.connect(self.on_conn_type_changed)
        type_layout.addWidget(self.conn_type_combo, 0, 1)
        type_group.setLayout(type_layout)
        conn_layout.addWidget(type_group)
        
        # RTU Settings
        self.rtu_group = QGroupBox("📡 Modbus RTU")
        rtu_layout = QGridLayout()
        rtu_layout.addWidget(QLabel("COM Port:"), 0, 0)
        self.com_combo = QComboBox()
        rtu_layout.addWidget(self.com_combo, 0, 1)
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setMaximumWidth(40)
        self.btn_refresh.clicked.connect(self.refresh_com_ports)
        rtu_layout.addWidget(self.btn_refresh, 0, 2)
        
        rtu_layout.addWidget(QLabel("Baudrate:"), 1, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
        rtu_layout.addWidget(self.baud_combo, 1, 1, 1, 2)
        
        rtu_layout.addWidget(QLabel("Parity:"), 2, 0)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        rtu_layout.addWidget(self.parity_combo, 2, 1, 1, 2)
        
        self.rtu_group.setLayout(rtu_layout)
        conn_layout.addWidget(self.rtu_group)
        
        # TCP Settings
        self.tcp_group = QGroupBox("🌐 Modbus TCP")
        tcp_layout = QGridLayout()
        tcp_layout.addWidget(QLabel("IP Address:"), 0, 0)
        self.ip_edit = QComboBox()
        self.ip_edit.setEditable(True)
        self.ip_edit.addItem("192.168.1.100")
        tcp_layout.addWidget(self.ip_edit, 0, 1)
        
        tcp_layout.addWidget(QLabel("Port:"), 1, 0)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(502)
        tcp_layout.addWidget(self.port_spin, 1, 1)
        
        self.tcp_group.setLayout(tcp_layout)
        self.tcp_group.setVisible(False)
        conn_layout.addWidget(self.tcp_group)
        
        # Slave ID
        slave_group = QGroupBox("📋 Thiết bị")
        slave_layout = QGridLayout()
        slave_layout.addWidget(QLabel("Slave ID:"), 0, 0)
        self.slave_spin = QSpinBox()
        self.slave_spin.setRange(1, 247)
        self.slave_spin.setValue(1)
        slave_layout.addWidget(self.slave_spin, 0, 1)
        slave_group.setLayout(slave_layout)
        conn_layout.addWidget(slave_group)
        
        # Nút kết nối
        self.btn_connect = QPushButton("🔗 Kết nối")
        self.btn_connect.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_connect.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.btn_connect)
        
        self.status_label = QLabel("⚪ Chưa kết nối")
        self.status_label.setStyleSheet("font-weight: bold;")
        conn_layout.addWidget(self.status_label)
        
        conn_layout.addStretch()
        tabs.addTab(conn_tab, "🔌 Kết nối")
        
        # --- Tab Cấu hình ZE-SG3 ---
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        
        sensor_group = QGroupBox("📊 Cảm biến DYJN-101")
        sensor_layout = QGridLayout()
        
        sensor_layout.addWidget(QLabel("Đơn vị đo:"), 0, 0)
        self.unit_combo = QComboBox()
        for k, v in UNITS.items():
            self.unit_combo.addItem(f"{k}: {v}", k)
        self.unit_combo.setCurrentIndex(5)  # N
        sensor_layout.addWidget(self.unit_combo, 0, 1)
        
        sensor_layout.addWidget(QLabel("Chế độ đo:"), 1, 0)
        self.measure_type_combo = QComboBox()
        self.measure_type_combo.addItems(["0: Bipolar (2 chiều)", "1: Unipolar (1 chiều)"])
        sensor_layout.addWidget(self.measure_type_combo, 1, 1)
        
        sensor_layout.addWidget(QLabel("Tầm đo (Nm):"), 2, 0)
        self.cell_fs_spin = QDoubleSpinBox()
        self.cell_fs_spin.setRange(0.1, 10000.0)
        self.cell_fs_spin.setValue(DEFAULT_CELL_FS)
        self.cell_fs_spin.setDecimals(1)
        sensor_layout.addWidget(self.cell_fs_spin, 2, 1)
        
        sensor_layout.addWidget(QLabel("Độ nhạy (mV/V):"), 3, 0)
        self.sens_spin = QDoubleSpinBox()
        self.sens_spin.setRange(0.001, 10.0)
        self.sens_spin.setValue(2.0)
        self.sens_spin.setDecimals(3)
        sensor_layout.addWidget(self.sens_spin, 3, 1)
        
        sensor_layout.addWidget(QLabel("Mức lọc:"), 4, 0)
        self.filter_spin = QSpinBox()
        self.filter_spin.setRange(0, 7)
        self.filter_spin.setValue(3)
        sensor_layout.addWidget(self.filter_spin, 4, 1)
        
        sensor_group.setLayout(sensor_layout)
        config_layout.addWidget(sensor_group)
        
        # Nút cấu hình
        btn_layout = QHBoxLayout()
        self.btn_write_config = QPushButton("📝 Ghi cấu hình")
        self.btn_write_config.clicked.connect(self.write_config)
        btn_layout.addWidget(self.btn_write_config)
        
        self.btn_read_config = QPushButton("📖 Đọc cấu hình")
        self.btn_read_config.clicked.connect(self.read_config)
        btn_layout.addWidget(self.btn_read_config)
        config_layout.addLayout(btn_layout)
        
        # Lệnh điều khiển
        cmd_group = QGroupBox("⚡ Lệnh điều khiển")
        cmd_layout = QHBoxLayout()
        self.btn_tare = QPushButton("⚖️ Tare (Zero)")
        self.btn_tare.clicked.connect(self.perform_tare)
        cmd_layout.addWidget(self.btn_tare)
        
        self.btn_restart = QPushButton("🔄 Restart")
        self.btn_restart.clicked.connect(self.perform_restart)
        cmd_layout.addWidget(self.btn_restart)
        cmd_group.setLayout(cmd_layout)
        config_layout.addWidget(cmd_group)
        
        config_layout.addStretch()
        tabs.addTab(config_tab, "⚙️ Cấu hình")
        
        # --- Tab Thu thập ---
        acq_tab = QWidget()
        acq_layout = QVBoxLayout(acq_tab)
        
        sample_group = QGroupBox("📈 Cài đặt thu thập")
        sample_layout = QGridLayout()
        sample_layout.addWidget(QLabel("Chu kỳ lấy mẫu (ms):"), 0, 0)
        self.sample_interval_spin = QSpinBox()
        self.sample_interval_spin.setRange(10, 5000)
        self.sample_interval_spin.setValue(DEFAULT_SAMPLE_INTERVAL_MS)
        self.sample_interval_spin.valueChanged.connect(self.on_sample_interval_changed)
        sample_layout.addWidget(self.sample_interval_spin, 0, 1)
        
        self.chk_stable_only = QCheckBox("Chỉ ghi khi ổn định (Bit 4)")
        self.chk_stable_only.setChecked(True)
        sample_layout.addWidget(self.chk_stable_only, 1, 0, 1, 2)
        sample_group.setLayout(sample_layout)
        acq_layout.addWidget(sample_group)
        
        # Điều khiển ghi
        rec_group = QGroupBox("🔴 Ghi dữ liệu")
        rec_layout = QHBoxLayout()
        self.btn_start_rec = QPushButton("▶️ Bắt đầu ghi")
        self.btn_start_rec.setStyleSheet("background-color: #4CAF50; color: white;")
        self.btn_start_rec.clicked.connect(self.start_recording)
        rec_layout.addWidget(self.btn_start_rec)
        
        self.btn_stop_rec = QPushButton("⏹ Dừng ghi")
        self.btn_stop_rec.setStyleSheet("background-color: #F44336; color: white;")
        self.btn_stop_rec.clicked.connect(self.stop_recording)
        self.btn_stop_rec.setEnabled(False)
        rec_layout.addWidget(self.btn_stop_rec)
        rec_group.setLayout(rec_layout)
        acq_layout.addWidget(rec_group)
        
        # Xuất CSV
        export_group = QGroupBox("💾 Xuất CSV")
        export_layout = QVBoxLayout()
        
        self.btn_export_simple = QPushButton("📄 Xuất đơn giản (Time, Torque)")
        self.btn_export_simple.clicked.connect(self.export_csv_simple)
        export_layout.addWidget(self.btn_export_simple)
        
        self.btn_export_full = QPushButton("📋 Xuất đầy đủ (CTR Format)")
        self.btn_export_full.clicked.connect(self.export_csv_full)
        export_layout.addWidget(self.btn_export_full)
        
        export_group.setLayout(export_layout)
        acq_layout.addWidget(export_group)
        
        acq_layout.addStretch()
        tabs.addTab(acq_tab, "📈 Thu thập")
        
        left_layout.addWidget(tabs)
        
        # === Panel phải: Hiển thị ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Hiển thị giá trị
        disp_group = QGroupBox("📟 Giá trị hiện tại")
        disp_layout = QGridLayout()
        
        font_big = QFont()
        font_big.setPointSize(24)
        font_big.setBold(True)
        
        disp_layout.addWidget(QLabel("Torque:"), 0, 0)
        self.torque_label = QLabel("0.000 Nm")
        self.torque_label.setFont(font_big)
        self.torque_label.setStyleSheet("color: #2196F3;")
        disp_layout.addWidget(self.torque_label, 0, 1)
        
        disp_layout.addWidget(QLabel("Trạng thái:"), 1, 0)
        self.stable_label = QLabel("---")
        disp_layout.addWidget(self.stable_label, 1, 1)
        
        disp_layout.addWidget(QLabel("Số mẫu:"), 2, 0)
        self.sample_count_label = QLabel("0")
        disp_layout.addWidget(self.sample_count_label, 2, 1)
        
        disp_layout.addWidget(QLabel("Thời gian ghi:"), 3, 0)
        self.rec_time_label = QLabel("0.0 s")
        disp_layout.addWidget(self.rec_time_label, 3, 1)
        
        disp_group.setLayout(disp_layout)
        right_layout.addWidget(disp_group)
        
        # Biểu đồ
        plot_group = QGroupBox("📈 Torque - Time")
        plot_layout = QVBoxLayout()
        self.torque_plot = RealTimePlot("Torque vs Time", "Time (s)", "Torque (Nm)", max_time_window_s=60.0)
        plot_layout.addWidget(self.torque_plot)
        
        self.btn_clear_plot = QPushButton("🗑️ Xóa biểu đồ")
        self.btn_clear_plot.clicked.connect(self.clear_plot)
        plot_layout.addWidget(self.btn_clear_plot)
        plot_group.setLayout(plot_layout)
        right_layout.addWidget(plot_group)
        
        # Log
        log_group = QGroupBox("📝 Nhật ký")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet("font-family: 'Consolas'; font-size: 9pt;")
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 850])
        
        main_layout.addWidget(splitter)
    
    def on_conn_type_changed(self, text):
        """Thay đổi loại kết nối"""
        is_rtu = "RTU" in text
        self.rtu_group.setVisible(is_rtu)
        self.tcp_group.setVisible(not is_rtu)
        self.connection_type = 'RTU' if is_rtu else 'TCP'
    
    def refresh_com_ports(self):
        """Quét cổng COM"""
        self.com_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.com_combo.addItem(f"{port.device} - {port.description}", port.device)
        if not ports:
            self.com_combo.addItem("Không tìm thấy cổng COM")
    
    def toggle_connection(self):
        """Kết nối/Ngắt kết nối"""
        if self.connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Thiết lập kết nối Modbus"""
        self.slave_id = self.slave_spin.value()
        
        try:
            if self.connection_type == 'RTU':
                port = self.com_combo.currentData()
                if not port:
                    self.log("❌ Chưa chọn cổng COM")
                    return
                baud = int(self.baud_combo.currentText())
                parity = {"None": "N", "Even": "E", "Odd": "O"}[self.parity_combo.currentText()]
                
                self.modbus_client = ModbusSerialClient(
                    port=port, method='rtu', baudrate=baud,
                    bytesize=8, parity=parity, stopbits=1, timeout=0.5
                )
            else:
                ip = self.ip_edit.currentText()
                port = self.port_spin.value()
                self.modbus_client = ModbusTcpClient(host=ip, port=port, timeout=1.0)
            
            if self.modbus_client.connect():
                self.connected = True
                self.btn_connect.setText("🔌 Ngắt kết nối")
                self.btn_connect.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
                self.status_label.setText("🟢 Đã kết nối")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.log(f"✅ Đã kết nối thành công")
                self._start_polling()
            else:
                self.log("❌ Không thể kết nối")
        except Exception as e:
            self.log(f"❌ Lỗi kết nối: {e}")
    
    def disconnect(self):
        """Ngắt kết nối"""
        self._stop_polling()
        if self.modbus_client:
            try:
                self.modbus_client.close()
            except:
                pass
        self.modbus_client = None
        self.connected = False
        self.btn_connect.setText("🔗 Kết nối")
        self.btn_connect.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.status_label.setText("⚪ Chưa kết nối")
        self.status_label.setStyleSheet("color: gray; font-weight: bold;")
        self.log("🔌 Đã ngắt kết nối")
    
    def _start_polling(self):
        """Bắt đầu polling"""
        self._poll_stop.clear()
        self._poll_thread = threading.Thread(target=self._poll_worker, daemon=True)
        self._poll_thread.start()
    
    def _stop_polling(self):
        """Dừng polling"""
        self._poll_stop.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=1.0)
    
    def _poll_worker(self):
        """Worker thread đọc dữ liệu"""
        while not self._poll_stop.is_set():
            if not self.connected or not self.modbus_client:
                time.sleep(0.1)
                continue
            
            try:
                # Đọc Net Weight (40064-40065)
                try:
                    result = self.modbus_client.read_holding_registers(REG_NET_WEIGHT_HI, 2, unit=self.slave_id)
                except TypeError:
                    result = self.modbus_client.read_holding_registers(REG_NET_WEIGHT_HI, 2, slave=self.slave_id)
                
                torque = 0.0
                if result and hasattr(result, 'registers') and len(result.registers) >= 2:
                    torque = float32_from_regs(result.registers[0], result.registers[1])
                
                # Đọc Status (40078)
                try:
                    status_result = self.modbus_client.read_holding_registers(REG_STATUS, 1, unit=self.slave_id)
                except TypeError:
                    status_result = self.modbus_client.read_holding_registers(REG_STATUS, 1, slave=self.slave_id)
                
                is_stable = False
                if status_result and hasattr(status_result, 'registers'):
                    status = status_result.registers[0]
                    is_stable = bool(status & 0x10)  # Bit 4
                
                self.data_signal.emit({'torque': torque, 'stable': is_stable, 'time': time.time()})
                
            except Exception as e:
                self.log_signal.emit(f"⚠️ Lỗi đọc: {e}")
            
            time.sleep(self._sample_interval_ms / 1000.0)
    
    def on_data_received(self, data):
        """Xử lý dữ liệu nhận được"""
        torque = data.get('torque', 0.0)
        is_stable = data.get('stable', False)
        
        self._current_torque = torque
        self._is_stable = is_stable
        
        # Cập nhật hiển thị
        self.torque_label.setText(f"{torque:.3f} Nm")
        self.stable_label.setText("🟢 Ổn định" if is_stable else "🟡 Đang dao động")
        self.stable_label.setStyleSheet("color: green;" if is_stable else "color: orange;")
        
        # Cập nhật biểu đồ
        if self._start_time:
            elapsed = time.time() - self._start_time
            self.torque_plot.update_plot(elapsed, torque)
            
            # Ghi dữ liệu nếu đang recording
            if self._recording:
                if not self.chk_stable_only.isChecked() or is_stable:
                    self._samples.append({'time_s': elapsed, 'torque_Nm': torque, 'stable': is_stable})
                    self.sample_count_label.setText(str(len(self._samples)))
                self.rec_time_label.setText(f"{elapsed:.1f} s")
        else:
            self._start_time = time.time()
    
    def on_sample_interval_changed(self, value):
        self._sample_interval_ms = value
    
    def start_recording(self):
        """Bắt đầu ghi dữ liệu"""
        self._samples.clear()
        self._start_time = time.time()
        self._recording = True
        self.btn_start_rec.setEnabled(False)
        self.btn_stop_rec.setEnabled(True)
        self.sample_count_label.setText("0")
        self.log("▶️ Bắt đầu ghi dữ liệu")
    
    def stop_recording(self):
        """Dừng ghi dữ liệu"""
        self._recording = False
        self.btn_start_rec.setEnabled(True)
        self.btn_stop_rec.setEnabled(False)
        self.log(f"⏹ Dừng ghi. Tổng số mẫu: {len(self._samples)}")
    
    def clear_plot(self):
        """Xóa biểu đồ"""
        self.torque_plot.clear_plot()
        self._start_time = time.time()
        self.log("🗑️ Đã xóa biểu đồ")
    
    def write_config(self):
        """Ghi cấu hình vào ZE-SG3"""
        if not self.connected:
            self.log("⚠️ Chưa kết nối")
            return
        
        try:
            unit_val = self.unit_combo.currentData()
            measure_type = 0 if "Bipolar" in self.measure_type_combo.currentText() else 1
            cell_fs = self.cell_fs_spin.value()
            sens = self.sens_spin.value()
            filter_level = self.filter_spin.value()
            
            # Ghi đơn vị đo
            self._write_register(REG_MEASURE_UNIT, unit_val)
            # Ghi chế độ đo
            self._write_register(REG_MEASURE_TYPE, measure_type)
            # Ghi Cell Full Scale
            hi, lo = float32_to_regs(cell_fs)
            self._write_register(REG_CELL_FS_HI, hi)
            self._write_register(REG_CELL_FS_LO, lo)
            # Ghi Cell Sensitivity
            hi, lo = float32_to_regs(sens)
            self._write_register(REG_CELL_SENS_HI, hi)
            self._write_register(REG_CELL_SENS_LO, lo)
            # Ghi Filter level
            self._write_register(REG_FILTER_LEVEL, filter_level)
            
            self.log(f"✅ Đã ghi cấu hình: Unit={unit_val}, Type={measure_type}, FS={cell_fs}, Sens={sens}, Filter={filter_level}")
        except Exception as e:
            self.log(f"❌ Lỗi ghi cấu hình: {e}")
    
    def read_config(self):
        """Đọc cấu hình từ ZE-SG3"""
        if not self.connected:
            self.log("⚠️ Chưa kết nối")
            return
        
        try:
            # Đọc các thanh ghi cấu hình
            unit = self._read_register(REG_MEASURE_UNIT)
            mtype = self._read_register(REG_MEASURE_TYPE)
            fs_hi = self._read_register(REG_CELL_FS_HI)
            fs_lo = self._read_register(REG_CELL_FS_LO)
            sens_hi = self._read_register(REG_CELL_SENS_HI)
            sens_lo = self._read_register(REG_CELL_SENS_LO)
            filter_lv = self._read_register(REG_FILTER_LEVEL)
            
            cell_fs = float32_from_regs(fs_hi, fs_lo)
            sens = float32_from_regs(sens_hi, sens_lo)
            
            self.log(f"📖 Cấu hình: Unit={unit} ({UNITS.get(unit, '?')}), Type={mtype}, FS={cell_fs:.2f}, Sens={sens:.4f}, Filter={filter_lv}")
            
            # Cập nhật UI
            for i in range(self.unit_combo.count()):
                if self.unit_combo.itemData(i) == unit:
                    self.unit_combo.setCurrentIndex(i)
                    break
            self.measure_type_combo.setCurrentIndex(mtype)
            self.cell_fs_spin.setValue(cell_fs)
            self.sens_spin.setValue(sens)
            self.filter_spin.setValue(filter_lv)
        except Exception as e:
            self.log(f"❌ Lỗi đọc cấu hình: {e}")
    
    def _write_register(self, addr, value):
        """Ghi 1 thanh ghi"""
        try:
            self.modbus_client.write_register(addr, int(value), unit=self.slave_id)
        except TypeError:
            self.modbus_client.write_register(addr, int(value), slave=self.slave_id)
    
    def _read_register(self, addr):
        """Đọc 1 thanh ghi"""
        try:
            result = self.modbus_client.read_holding_registers(addr, 1, unit=self.slave_id)
        except TypeError:
            result = self.modbus_client.read_holding_registers(addr, 1, slave=self.slave_id)
        if result and hasattr(result, 'registers'):
            return result.registers[0]
        return 0
    
    def perform_tare(self):
        """Thực hiện Tare (lấy điểm không)"""
        if not self.connected:
            self.log("⚠️ Chưa kết nối")
            return
        try:
            self._write_register(REG_COMMAND, CMD_TARE)
            self.log("⚖️ Đã gửi lệnh Tare (49914)")
        except Exception as e:
            self.log(f"❌ Lỗi Tare: {e}")
    
    def perform_restart(self):
        """Khởi động lại thiết bị"""
        if not self.connected:
            self.log("⚠️ Chưa kết nối")
            return
        try:
            self._write_register(REG_COMMAND, CMD_RESTART)
            self.log("🔄 Đã gửi lệnh Restart (43948)")
        except Exception as e:
            self.log(f"❌ Lỗi Restart: {e}")
    
    def export_csv_simple(self):
        """Xuất CSV đơn giản (Time, Torque)"""
        if not self._samples:
            self.log("⚠️ Không có dữ liệu để xuất")
            return
        
        fname = f"torque_simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Lưu CSV đơn giản", fname, "CSV Files (*.csv)")
        if not path:
            return
        
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Time (s)', 'Torque (Nm)'])
                for s in self._samples:
                    writer.writerow([f"{s['time_s']:.6f}", f"{s['torque_Nm']:.6f}"])
            self.log(f"💾 Đã xuất CSV đơn giản: {path}")
        except Exception as e:
            self.log(f"❌ Lỗi xuất CSV: {e}")
    
    def export_csv_full(self):
        """Xuất CSV định dạng CTR DATA FORMAT #1"""
        if not self._samples:
            self.log("⚠️ Không có dữ liệu để xuất")
            return
        
        fname = f"torque_ctr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Lưu CSV đầy đủ", fname, "CSV Files (*.csv)")
        if not path:
            return
        
        try:
            rows = []
            for s in self._samples:
                t = s['time_s']
                torque = s['torque_Nm']
                rows.append([1, 3, 1, t, 0.0, 0.0, torque])
            
            n = len(rows)
            cols = list(zip(*rows))
            col_max = [max(c) for c in cols]
            col_min = [min(c) for c in cols]
            
            with open(path, 'w', newline='', encoding='utf-8') as f:
                f.write("%===============================================================\n")
                f.write("%     CTR DATA FORMAT #1 (Revision 2019.06.27)\n")
                f.write("%     ZE-SG3 Torque Data - DYJN-101 50Nm\n")
                f.write("%===============================================================\n")
                f.write("BEGIN_OF_HEADER\n")
                f.write(f"SAVED_DATE = {datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')}\n")
                f.write(f"SAMPLE_INTERVAL_MS = {self._sample_interval_ms}\n")
                f.write("NUMBER_OF_COLUMNS = 7\n")
                f.write("COLUMN_NAME = [Save,State,Cycle,Time,Command,Angle,Torque]\n")
                f.write("COLUMN_UNIT = [NA,NA,Cycle,sec,Dgree,Dgree,N*m]\n")
                f.write(f"COLUMN_LENGTH = [{n},{n},{n},{n},{n},{n},{n}]\n")
                f.write(f"COLUMN_MAXIMUM = [{','.join(f'{v:.6f}' for v in col_max)}]\n")
                f.write(f"COLUMN_MINIMUM = [{','.join(f'{v:.6f}' for v in col_min)}]\n")
                f.write("END_OF_HEADER\n")
                
                for row in rows:
                    f.write(','.join([str(int(row[0])), str(int(row[1])), str(int(row[2])),
                                      f"{row[3]:.6f}", f"{row[4]:.6f}", f"{row[5]:.6f}", f"{row[6]:.6f}"]) + '\n')
            
            self.log(f"💾 Đã xuất CSV CTR Format: {path}")
        except Exception as e:
            self.log(f"❌ Lỗi xuất CSV: {e}")
    
    def log(self, message):
        self.log_signal.emit(message)
    
    def append_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


def main():
    app = QApplication(sys.argv)
    window = ZE_SG3_App()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
