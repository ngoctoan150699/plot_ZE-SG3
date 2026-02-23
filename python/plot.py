#!/usr/bin/env python3
"""
PLC Modbus RTU Master - SCADA System
======================================
✅ GUI PyQt5: 3 cột (Control / Digital Displays / Plots) + Activity Log
✅ Modbus RTU master dùng pymodbus ModbusSerialClient
✅ Hỗ trợ FC3 read_holding_registers và FC6/FC16 write_register/write_registers
✅ Fallback tham số `unit` vs `slave` (tương thích nhiều phiên bản pymodbus)
✅ Default serial UI: 115200, Parity None, bytesize=8, stopbits=1, timeout ~0.2–0.5s
✅ Auto-detect Unit ID + addr base offset (0/1)
✅ Polling thread không block GUI, đọc 3 regs (addr 1..3)
✅ CSV export + cycle counting theo Mission Done bit

Mapping (base-1) theo spec (đã dịch +1 so với bản base-0):
READ:
    addr 1 (optional): Actual Angle (deg*100) // tương ứng thanh ghi PLC D0 (40001)
    addr 2: Analog raw // tương ứng thanh ghi PLC D1 (40002)
    addr 3: Status bits (bit0 Home, bit1 Servo Run, bit2 Mission Done) // tương ứng thanh ghi PLC D2 (40003)
WRITE:
    addr 4: Control (1 START, 2 STOP, 3 ESTOP, 4 HOME, 0 CLEAR) // tương ứng thanh ghi PLC D3 (40004)
    addr 5: Speed for DPLSY (pulses/s, u16) // tương ứng thanh ghi PLC D4 (40005)
    addr 6..8: Target Mean/Amp/Phase (deg*100) // tương ứng thanh ghi PLC D5..D7 (40006..40008)

Extra (SCADA/test):
    addr 9: Target cycles (u16)
    addr 10: Test done flag (u16)

Fast cmd-angle path:
    addr 11: Cmd angle (deg*100, int16 stored in u16)
    addr 12: Cmd seq (u16, increment each write)
    
"""

import sys
import logging
import threading
from collections import deque
from datetime import datetime
import time
import csv
import json
from pathlib import Path
import math
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QComboBox, QPushButton,
    QTextEdit, QDoubleSpinBox, QSpinBox, QSplitter, QCheckBox, QAction, QFileDialog
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont

# Matplotlib for real-time plotting
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Modbus client - compatible with multiple pymodbus versions
try:
    from pymodbus.client.sync import ModbusSerialClient
except ImportError:
    try:
        from pymodbus.client import ModbusSerialClient
    except ImportError:
        ModbusSerialClient = None

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
try:
    logging.getLogger('pymodbus').setLevel(logging.WARNING)
except Exception:
    pass


# ================== MODBUS HOLDING REGISTER MAP (BASE-1) ==================
# NOTE: Các địa chỉ dưới đây là logical address (base-1). Khi thực thi I/O,
# code vẫn cộng thêm self.addr_offset để tương thích thiết bị base-0/base-1.
# Angle uses 2 registers (32-bit) for 6-decimal precision: deg * 1000000
HR_ACTUAL_ANGLE_HI = 1       # deg*1000000 HIGH word (bits 31-16)
HR_ACTUAL_ANGLE_LO = 2       # deg*1000000 LOW word (bits 15-0)
HR_ANALOG_RAW = 3            # u16
HR_STATUS_BITS = 4           # bit0 Home, bit1 Servo Run, bit2 Mission Done

HR_CONTROL = 5               # 1 START, 2 STOP, 3 ESTOP, 4 HOME, 0 CLEAR
HR_SPEED_PPS = 6             # DPLSY pulses/s (u16)
HR_TARGET_MEAN = 7           # deg*100
HR_TARGET_AMP = 8            # deg*100
HR_TARGET_PHASE = 9          # deg*100

HR_TARGET_CYCLES = 10        # u16
HR_TEST_DONE = 11            # u16

# Fast cmd-angle path (written every poll when test is running)
HR_CMD_ANGLE = 12            # deg*100 (int16 stored in u16)
HR_CMD_SEQ = 13              # u16

HR_READ_START = HR_ACTUAL_ANGLE_HI
HR_READ_COUNT = 4            # Read 4 regs: angle_hi, angle_lo, analog, status

# Control command values written to HR_CONTROL
CTRL_CLEAR = 0
CTRL_START = 1
CTRL_STOP = 2
CTRL_ESTOP = 3
CTRL_HOME = 4


# ================== DEFAULT UI SETTINGS ==================
# NOTE: Các giá trị mặc định cho UI nên tập trung tại đây để dễ bảo trì.
# HIGH-SPEED SAMPLING: Multi-threaded architecture for 2ms precision.
# - Reader thread: reads Modbus as fast as possible into ring buffer
# - Sampler thread: extracts samples at precise 2ms intervals
# - GUI thread: updates display at lower rate (~20Hz)
DEFAULT_POLL_INTERVAL_MS = 10      # Minimum poll interval (reader runs flat-out)
DEFAULT_WRITE_DELAY_MS = 50       # Throttle writes to avoid bus congestion
DEFAULT_SAMPLE_INTERVAL_MS = 10    # 10ms = 100Hz sampling (like Insize equipment)
DEFAULT_PLOT_EVERY_N_POLLS = 25   # Update plot every 25 polls (~20Hz at 100Hz sample)
DEFAULT_WRITE_PARAMS_ON_CONNECT = True
DEFAULT_RING_BUFFER_SIZE = 1000   # Ring buffer size for high-speed reads

# UI Visibility flags - set False to hide blocks for performance/cleaner UI
SHOW_SERVO_SETTINGS = True        # Servo Settings in Config tab
SHOW_ANALOG_SETTINGS = True       # Analog Settings in Config tab  
SHOW_POLL_SETTINGS = True         # Poll/Throttle Settings in Config tab
SHOW_ACTIVITY_LOG = False          # Activity Log panel at bottom
SHOW_SAFETY_LIMITS = True        # Safety Limits block
SHOW_ZERO_HOME_RESET = True       # Zero/Home/Reset block

# Stop behavior:
# - Preferred: stop on Mission Done bit from PLC/simulator.
# - Optional fallback: time-based stop when Mission Done pulse is missed.
DEFAULT_ENABLE_TIME_BASED_STOP = False

# Smoothing for received values (EMA filter for smoother plots)
# tau_ms = time constant in milliseconds. Smaller = faster response, larger = smoother.
# Set to 0 to disable smoothing.
DEFAULT_PLOT_SMOOTH_TAU_MS = 10  # ~10ms smoothing for plot data
DEFAULT_ENABLE_PLOT_SMOOTHING = True

# Plot angle source:
# - True: Use Command angle (calculated/sent angle) for X-axis in Torque-Angle plot
# - False: Use Actual angle (read from simulator via Modbus)
DEFAULT_USE_CMD_ANGLE_FOR_PLOT = False


def _u16_to_i16(v: int) -> int:
    v = int(v) & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _i16_to_u16(v: int) -> int:
    return int(v) & 0xFFFF

# Servo conversion settings (DPLSY pulses/s <-> deg/s)
DEFAULT_PULSES_PER_REV = 8000
DEFAULT_GEAR_RATIO = 10.0

# Parameters defaults
DEFAULT_SPEED_PPS = 0.0
DEFAULT_SPEED_DEG_S = 30.0
DEFAULT_TARGET_MEAN_DEG = 0.0
DEFAULT_TARGET_AMP_DEG = 35.0
DEFAULT_TARGET_PHASE_DEG = 0.0
DEFAULT_CONTROL_MODE = 'Angle'         # 'Angle'
DEFAULT_FUNCTION_MODE = 'Triangular'   # 'Triangular'
DEFAULT_TARGET_CYCLES = 1
MIN_TARGET_AMP_DEG = 0.01

# Safety limits defaults
DEFAULT_LIMIT_ANGLE_LOW_DEG = -360.0
DEFAULT_LIMIT_ANGLE_HIGH_DEG = 360.0
DEFAULT_LIMIT_TORQUE_LOW_NM = 0.0
DEFAULT_LIMIT_TORQUE_HIGH_NM = 210.0
DEFAULT_LIMIT_ACTION = 'Motor Off'
DEFAULT_LIMITS_ENABLED = False

# Analog signal mode:
# - NonBipolar: 800-4000 = 0 to max_mv_v (unipolar, e.g., 0-1.6 mV/V)
# - Bipolar: 2400 = 0, 800-2400 = -max to 0, 2400-4000 = 0 to +max
DEFAULT_ANALOG_BIPOLAR = True
DEFAULT_ANALOG_MAX_MV_V = 1.6
DEFAULT_BIPOLAR_ZERO_POINT = 2400  # Analog raw at 0 torque for Bipolar mode
DEFAULT_ANALOG_MAX_TORQUE_NM = 3.0


class RealTimePlot(FigureCanvas):
    """Real-time plotting widget - optimized for smooth curves"""
    def __init__(self, title="Plot", xlabel="X", ylabel="Y", max_points=None, max_time_window_s=None):
        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.max_points = max_points
        self.max_time_window_s = max_time_window_s  # Rolling time window in seconds

        # If max_points is None (default), keep all points from START to STOP.
        # If max_points is an int, behave like a sliding window.
        if max_points is None:
            self.x_data = []
            self.y_data = []
        else:
            self.x_data = deque(maxlen=int(max_points))
            self.y_data = deque(maxlen=int(max_points))
        
        # Thinner line for smoother appearance with many points
        self.line, = self.ax.plot([], [], 'b-', linewidth=0.8, antialiased=True)
        self.ax.set_title(title, fontsize=10, fontweight='bold')
        self.ax.set_xlabel(xlabel, fontsize=9)
        self.ax.set_ylabel(ylabel, fontsize=9)
        self.ax.grid(True, alpha=0.3)
        self.fig.tight_layout()

        self._update_count = 0
        self._last_draw_time = 0.0
        self._min_draw_interval = 0.033  # ~30 FPS for smooth rendering
    
    def update_plot(self, x, y):
        """Add new data point and refresh plot - optimized for smooth curves"""
        try:
            self.x_data.append(x)
            self.y_data.append(y)
        except Exception:
            return
        
        # If max_time_window_s is set, trim old data outside the time window
        if self.max_time_window_s is not None and len(self.x_data) > 0:
            xs = list(self.x_data) if not isinstance(self.x_data, list) else self.x_data
            cutoff = x - self.max_time_window_s
            while xs and xs[0] < cutoff:
                try:
                    if isinstance(self.x_data, list):
                        self.x_data.pop(0)
                        self.y_data.pop(0)
                    else:
                        self.x_data.popleft()
                        self.y_data.popleft()
                    xs = list(self.x_data) if not isinstance(self.x_data, list) else self.x_data
                except Exception:
                    break
        
        if len(self.x_data) > 0:
            # Throttle draw_idle() to avoid excessive redraws
            now = time.time()
            if (now - self._last_draw_time) >= self._min_draw_interval:
                xs = list(self.x_data) if not isinstance(self.x_data, list) else self.x_data
                ys = list(self.y_data) if not isinstance(self.y_data, list) else self.y_data
                self.line.set_data(xs, ys)
                
                # Autoscale less frequently for performance
                self._update_count += 1
                if self._update_count % 20 == 0:
                    self.ax.relim()
                    self.ax.autoscale_view()
                self.draw_idle()
                self._last_draw_time = now
    
    def clear_plot(self):
        """Clear all data"""
        try:
            self.x_data.clear()
            self.y_data.clear()
        except Exception:
            self.x_data = []
            self.y_data = []
        self.line.set_data([], [])
        self.draw()


def torque_from_analog_raw(analog_raw: int, bipolar: bool = True, max_torque_nm: float = DEFAULT_ANALOG_MAX_TORQUE_NM):
    """Convert analog raw -> (current_mA, torque_Nm).

    NonBipolar (unipolar): 800-4000 = 4-20mA = 0 to max_torque
    Bipolar: 2400 = 0 torque, 800-2400 = -max to 0, 2400-4000 = 0 to +max

    Returns:
        (current_mA, torque_Nm)
    """
    try:
        analog = float(analog_raw)
    except Exception:
        analog = 800.0

    if bipolar:
        # Bipolar mode: 2400 is zero point
        # 800..2400 -> -max..0, 2400..4000 -> 0..+max
        # Scale: (analog - 2400) / 1600 * max_torque
        zero_point = 2400.0
        half_range = 1600.0  # 2400-800 or 4000-2400
        torque = (analog - zero_point) / half_range * float(max_torque_nm)
        # Current mA: 800-4000 -> 4-20 mA (standard 4-20mA loop)
        current_ma = 4.0 + (analog - 800.0) / 3200.0 * 16.0
    else:
        # NonBipolar (unipolar): 800-4000 = 4-20mA = 0 to max_torque
        current_ma = 4.0 + (analog - 800.0) / 3200.0 * 16.0
        torque = (current_ma - 4.0) / 16.0 * float(max_torque_nm)

    return current_ma, torque


class PLCMasterSCADA(QMainWindow):
    """PLC Modbus RTU Master with SCADA features"""
    
    # Signals for thread-safe GUI updates
    log_signal = pyqtSignal(str)
    poll_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.modbus_client = None
        self.slave_id = 1
        self.connected = False

        # Detected addressing
        self.unit_id = None
        self.addr_offset = 0

        # Threading / synchronization - Multi-threaded high-speed architecture
        self._modbus_lock = threading.Lock()
        self._poll_stop = threading.Event()
        self._poll_pause = threading.Event()
        self._poll_thread = None           # High-speed Modbus reader
        self._sampler_thread = None        # Precise 2ms sampler
        self._poll_interval_ms = int(DEFAULT_POLL_INTERVAL_MS)
        self._sample_interval_ms = int(DEFAULT_SAMPLE_INTERVAL_MS)
        self._plot_every_n_polls = int(DEFAULT_PLOT_EVERY_N_POLLS)
        self._poll_count = 0
        
        # Ring buffer for high-speed data (thread-safe via deque)
        self._ring_buffer = deque(maxlen=DEFAULT_RING_BUFFER_SIZE)
        self._ring_lock = threading.Lock()
        self._latest_regs = None           # Most recent valid reading
        self._latest_regs_time = 0.0       # Timestamp of latest reading
        self._sample_count = 0             # Total samples acquired
        self._sample_stats = {'rate_hz': 0, 'count': 0}

        # Fast cmd-angle write state
        self._cmd_seq = 0
        self._cmd_angle_to_send_i16 = 0

        # Stop behavior
        self.enable_time_based_stop = bool(DEFAULT_ENABLE_TIME_BASED_STOP)

        # Settings dialog (keep persistent to avoid Qt deleting reused widgets)
        self._settings_dlg = None

        # Persisted settings values (for rebuilding widgets if needed)
        self._write_delay_ms = int(DEFAULT_WRITE_DELAY_MS)

        # Diagnostics
        self._consecutive_failures = 0
        self._max_consecutive_failures_log = 5
        self._last_status_bits = None

        # Mission/cycle
        self._cycle_count = 0
        self._last_mission_done = 0
        self._target_cycles = 0
        self._test_running = False
        self._auto_stop_issued = False
        self._samples = []
        self._max_samples = 200000

        # Fixed-step sampling (plot + CSV)
        self._sample_interval_ms = int(DEFAULT_SAMPLE_INTERVAL_MS)
        self._sample_dt_s = self._sample_interval_ms / 1000.0
        self._run_t0_perf = None
        self._sample_index = 0
        self._next_sample_due_s = 0.0
        self._last_sample_time_s = 0.0
        
        # Legacy wall-clock start_time (kept for timestamps)
        self.start_time = datetime.now()
        
        # Current values
        self.current_torque = 0.0
        self.current_torque_raw = 0.0
        self.current_angle = 0.0
        self.current_angle_raw = 0.0
        self.current_analog = 0
        self.current_ma = 0.0
        # Control/function mode (UI state)
        self.control_mode = str(DEFAULT_CONTROL_MODE)
        self.function_mode = str(DEFAULT_FUNCTION_MODE)

        # Zero offsets
        self.angle_zero_offset_deg = 0.0
        self.torque_zero_offset_nm = 0.0

        # Command/feedback stats
        self.command_angle_deg = 0.0
        self._cmd_peak = None
        self._cmd_valley = None
        self._fb_peak = None
        self._fb_valley = None
        self._torque_peak = None
        self._torque_valley = None

        # Limits
        self._limit_tripped = False

        # Speed sync
        self._updating_speed = False

        # Servo conversion settings (DPLSY pulses/s <-> deg/s)
        self.pulses_per_rev = int(DEFAULT_PULSES_PER_REV)
        self.gear_ratio = float(DEFAULT_GEAR_RATIO)

        # Analog signal settings (Bipolar vs NonBipolar)
        self.analog_bipolar = bool(DEFAULT_ANALOG_BIPOLAR)
        self.analog_max_torque_nm = float(DEFAULT_ANALOG_MAX_TORQUE_NM)

        # Plot angle source setting
        self.use_cmd_angle_for_plot = bool(DEFAULT_USE_CMD_ANGLE_FOR_PLOT)

        # Plot smoothing (EMA filter)
        self._plot_smooth_enabled = bool(DEFAULT_ENABLE_PLOT_SMOOTHING)
        self._plot_smooth_tau_ms = float(DEFAULT_PLOT_SMOOTH_TAU_MS)
        self._smooth_angle = 0.0
        self._smooth_torque = 0.0
        self._smooth_initialized = False
        self._last_smooth_time = None

        # Test time UI timer
        self._test_time_timer = QTimer()
        self._test_time_timer.setInterval(200)
        self._test_time_timer.timeout.connect(self._update_test_time_label)

        # last-sent caches for parameters
        self._last_sent_speed_raw = None
        self._last_sent_targets_raw = None  # tuple(mean, amp, phase)
        self._pending_speed_raw = None
        self._pending_targets_raw = None
        self._speed_write_timer = QTimer()
        self._speed_write_timer.setSingleShot(True)
        self._speed_write_timer.timeout.connect(self._do_send_params)
        self._targets_write_timer = QTimer()
        self._targets_write_timer.setSingleShot(True)
        self._targets_write_timer.timeout.connect(self._do_send_params)
        
        self.init_ui()

        # Load saved servo settings (best-effort)
        try:
            self.load_servo_config(self._default_config_path(), quiet=True)
        except Exception:
            pass

        # Ensure pps/deg/s displays are consistent at startup
        try:
            self._update_servo_settings_labels()
            self._update_speed_pps_from_deg_s()
        except Exception:
            pass

        try:
            self._test_time_timer.start()
        except Exception:
            pass
        
        # Connect log signal
        self.log_signal.connect(self.append_log)
        self.poll_signal.connect(self.on_polled_data)
        
        # Initial COM port scan
        self.refresh_com_ports()
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("PLC Modbus RTU Master - SCADA System")
        self.setGeometry(100, 100, 1400, 900)

        # ===== Top menu (Config / Save / Settings) =====
        try:
            menubar = self.menuBar()
            cfg_menu = menubar.addMenu("Config")

            act_load_master = QAction("Load Master Config...", self)
            act_load_master.triggered.connect(self._menu_load_master_config)
            cfg_menu.addAction(act_load_master)

            act_save_master = QAction("Save Master Config...", self)
            act_save_master.triggered.connect(self._menu_save_master_config)
            cfg_menu.addAction(act_save_master)

            try:
                cfg_menu.addSeparator()
            except Exception:
                pass

            act_load = QAction("Load Servo Config...", self)
            act_load.triggered.connect(self._menu_load_servo_config)
            cfg_menu.addAction(act_load)

            act_save = QAction("Save Servo Config...", self)
            act_save.triggered.connect(self._menu_save_servo_config)
            cfg_menu.addAction(act_save)

            # Settings menu for opening settings dialog
            settings_menu = menubar.addMenu("⚙️ Settings")
            act_open_settings = QAction("Open Settings Panel...", self)
            act_open_settings.triggered.connect(self._open_settings_dialog)
            settings_menu.addAction(act_open_settings)
        except Exception:
            pass
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # ===== MAIN CONTENT AREA (3 columns) =====
        splitter = QSplitter(Qt.Horizontal)

        # --- Column 1: Control ---
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)

        conn_group = QGroupBox("🔌 Connection Settings")
        conn_layout = QGridLayout()
        conn_layout.setSpacing(6)

        # Hàng 1: COM Port (nhỏ) + Refresh button bên phải
        conn_layout.addWidget(QLabel("COM Port:"), 0, 0)
        self.com_combo = QComboBox()
        self.com_combo.setMaximumWidth(180)
        conn_layout.addWidget(self.com_combo, 0, 1)
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setMaximumWidth(90)
        btn_refresh.clicked.connect(self.refresh_com_ports)
        conn_layout.addWidget(btn_refresh, 0, 2)

        # Hàng 2: Baudrate, Parity, Slave ID (3 cột)
        conn_layout.addWidget(QLabel("Baudrate:"), 1, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setMaximumWidth(100)
        conn_layout.addWidget(self.baud_combo, 1, 1)

        conn_layout.addWidget(QLabel("Parity:"), 1, 2)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        self.parity_combo.setCurrentText("None")
        self.parity_combo.setMaximumWidth(90)
        conn_layout.addWidget(self.parity_combo, 1, 3, 1, 1)

        # Slave ID trên cùng hàng bên phải
        conn_layout.addWidget(QLabel("Slave ID:"), 1, 4)
        self.slave_spin = QSpinBox()
        self.slave_spin.setRange(0, 247)
        self.slave_spin.setValue(1)
        self.slave_spin.setMaximumWidth(60)
        conn_layout.addWidget(self.slave_spin, 1, 5)

        # Hàng 3: Connect button
        self.connect_btn = QPushButton("🔗 Connect")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn, 2, 0, 1, 6)

        # Status labels (dưới cùng)
        self.status_label = QLabel("⚪ Disconnected")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        conn_layout.addWidget(self.status_label, 3, 0, 1, 3)

        self.detect_label = QLabel("Unit: - | Addr offset: -")
        self.detect_label.setStyleSheet("color: gray; font-size: 9pt;")
        conn_layout.addWidget(self.detect_label, 3, 3, 1, 3)

        conn_group.setLayout(conn_layout)
        control_layout.addWidget(conn_group)

        # Manual Unit/Offset override (hidden, but functionality preserved)
        manual_group = QGroupBox("🔧 Manual Unit/Offset")
        manual_layout = QHBoxLayout()
        self.manual_checkbox = QCheckBox("Enable manual unit/offset (skip probe)")
        manual_layout.addWidget(self.manual_checkbox)
        manual_layout.addWidget(QLabel("Addr offset:"))
        self.addr_offset_spin = QSpinBox()
        self.addr_offset_spin.setRange(0, 1)
        self.addr_offset_spin.setValue(0)
        manual_layout.addWidget(self.addr_offset_spin)
        self.apply_unit_btn = QPushButton("Apply Unit/Offset")
        self.apply_unit_btn.clicked.connect(self.apply_manual_unit_offset)
        manual_layout.addWidget(self.apply_unit_btn)
        manual_group.setLayout(manual_layout)
        manual_group.setVisible(False)
        control_layout.addWidget(manual_group)

        # ===== Digital Displays (moved here - below Connection, above Control) =====
        disp_group = QGroupBox("📟 Digital Displays")
        disp_layout = QGridLayout()
        disp_layout.setSpacing(4)

        font_value = QFont()
        font_value.setPointSize(11)
        font_value.setBold(True)

        disp_layout.addWidget(QLabel("Angle:"), 0, 0)
        self.angle_label = QLabel("-")
        self.angle_label.setFont(font_value)
        self.angle_label.setStyleSheet("color: #FF9800;")
        disp_layout.addWidget(self.angle_label, 0, 1)

        disp_layout.addWidget(QLabel("Torque:"), 0, 2)
        self.torque_label = QLabel("-")
        self.torque_label.setFont(font_value)
        self.torque_label.setStyleSheet("color: #F44336;")
        disp_layout.addWidget(self.torque_label, 0, 3)

        disp_layout.addWidget(QLabel("Analog:"), 1, 0)
        self.analog_label = QLabel("-")
        self.analog_label.setFont(font_value)
        self.analog_label.setStyleSheet("color: #9C27B0;")
        disp_layout.addWidget(self.analog_label, 1, 1)

        disp_layout.addWidget(QLabel("Current:"), 1, 2)
        self.current_label = QLabel("-")
        self.current_label.setFont(font_value)
        self.current_label.setStyleSheet("color: #2196F3;")
        disp_layout.addWidget(self.current_label, 1, 3)

        disp_layout.addWidget(QLabel("Home:"), 2, 0)
        self.home_label = QLabel("-")
        disp_layout.addWidget(self.home_label, 2, 1)

        disp_layout.addWidget(QLabel("Servo:"), 2, 2)
        self.servo_run_label = QLabel("-")
        disp_layout.addWidget(self.servo_run_label, 2, 3)

        disp_layout.addWidget(QLabel("Done:"), 3, 0)
        self.mission_done_label = QLabel("-")
        disp_layout.addWidget(self.mission_done_label, 3, 1)

        disp_layout.addWidget(QLabel("Fails:"), 3, 2)
        self.fail_label = QLabel("0")
        disp_layout.addWidget(self.fail_label, 3, 3)

        disp_layout.addWidget(QLabel("Cmd:"), 4, 0)
        self.cmd_angle_label = QLabel("-")
        self.cmd_angle_label.setFont(font_value)
        disp_layout.addWidget(self.cmd_angle_label, 4, 1)

        disp_layout.addWidget(QLabel("Cmd P/V:"), 4, 2)
        self.cmd_pv_label = QLabel("-")
        disp_layout.addWidget(self.cmd_pv_label, 4, 3)

        disp_layout.addWidget(QLabel("FB P/V:"), 5, 0)
        self.fb_pv_label = QLabel("-")
        disp_layout.addWidget(self.fb_pv_label, 5, 1)

        disp_layout.addWidget(QLabel("Trq P/V:"), 5, 2)
        self.torque_pv_label = QLabel("-")
        disp_layout.addWidget(self.torque_pv_label, 5, 3)

        # Poll rate display (Modbus read rate)
        disp_layout.addWidget(QLabel("Read Hz:"), 6, 0)
        self.poll_rate_label = QLabel("-")
        self.poll_rate_label.setToolTip("Modbus read rate (Hz) and avg/max read time (ms)")
        disp_layout.addWidget(self.poll_rate_label, 6, 1)
        
        # Sample rate display (actual data sampling rate)
        disp_layout.addWidget(QLabel("Sample Hz:"), 6, 2)
        self.sample_rate_label = QLabel("-")
        self.sample_rate_label.setToolTip("Data sampling rate (target: 500Hz = 2ms interval)")
        disp_layout.addWidget(self.sample_rate_label, 6, 3)
        
        disp_layout.addWidget(QLabel("Samples:"), 7, 0)
        self.sample_count_label = QLabel("0")
        disp_layout.addWidget(self.sample_count_label, 7, 1)

        disp_group.setLayout(disp_layout)
        control_layout.addWidget(disp_group)

        # ===== Settings widgets (created but stored for Settings dialog) =====
        self._create_settings_widgets()

        ctrl_group = QGroupBox("🎮 Control")
        ctrl_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶️ START")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_start.clicked.connect(self.start_servo)
        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 10px;")
        self.btn_stop.clicked.connect(self.stop_servo)
        self.btn_estop = QPushButton("🛑 ESTOP")
        self.btn_estop.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 10px;")
        self.btn_estop.clicked.connect(self.emergency_stop)
        self.btn_clear_ctrl = QPushButton("♻️ CLEAR")
        self.btn_clear_ctrl.setStyleSheet("padding: 10px;")
        self.btn_clear_ctrl.clicked.connect(self.reset_commands)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_estop)
        btn_layout.addWidget(self.btn_clear_ctrl)
        ctrl_layout.addLayout(btn_layout)
        ctrl_group.setLayout(ctrl_layout)
        control_layout.addWidget(ctrl_group)

        params_group = QGroupBox("🧰 Parameters")
        params_layout = QGridLayout()
        params_layout.setSpacing(6)

        # Hàng 1: Speed (DPLSY pulses/s) + Speed (deg/s)
        params_layout.addWidget(QLabel("Speed (DPLSY) (pps):"), 0, 0)
        self.speed_hz_spin = QDoubleSpinBox()
        self.speed_hz_spin.setRange(0.0, 1_000_000.0)
        self.speed_hz_spin.setDecimals(1)
        self.speed_hz_spin.setValue(float(DEFAULT_SPEED_PPS))
        self.speed_hz_spin.setSingleStep(10.0)
        self.speed_hz_spin.setMaximumWidth(90)
        params_layout.addWidget(self.speed_hz_spin, 0, 1)
        self.speed_hz_spin.valueChanged.connect(self.on_speed_changed)

        params_layout.addWidget(QLabel("Speed (deg/s):"), 0, 2)
        self.speed_deg_s_spin = QDoubleSpinBox()
        self.speed_deg_s_spin.setRange(0.0, 100000.0)
        self.speed_deg_s_spin.setDecimals(3)
        self.speed_deg_s_spin.setValue(float(DEFAULT_SPEED_DEG_S))
        self.speed_deg_s_spin.setSingleStep(1.0)
        self.speed_deg_s_spin.setMaximumWidth(90)
        params_layout.addWidget(self.speed_deg_s_spin, 0, 3)
        self.speed_deg_s_spin.valueChanged.connect(self.on_speed_deg_s_changed)

        # Hàng 2: Target Mean, Amp, Phase (3 cột)
        params_layout.addWidget(QLabel("Mean (°):"), 1, 0)
        self.target_mean_spin = QDoubleSpinBox()
        self.target_mean_spin.setRange(-360.0, 360.0)
        self.target_mean_spin.setDecimals(2)
        self.target_mean_spin.setValue(float(DEFAULT_TARGET_MEAN_DEG))
        self.target_mean_spin.setMaximumWidth(80)
        params_layout.addWidget(self.target_mean_spin, 1, 1)
        self.target_mean_spin.valueChanged.connect(self.on_targets_changed)

        params_layout.addWidget(QLabel("Amp (°):"), 1, 2)
        self.target_amp_spin = QDoubleSpinBox()
        self.target_amp_spin.setRange(MIN_TARGET_AMP_DEG, 360.0)
        self.target_amp_spin.setDecimals(2)
        self.target_amp_spin.setValue(float(DEFAULT_TARGET_AMP_DEG))
        self.target_amp_spin.setMaximumWidth(80)
        params_layout.addWidget(self.target_amp_spin, 1, 3)
        self.target_amp_spin.valueChanged.connect(self.on_targets_changed)

        params_layout.addWidget(QLabel("Phase (°):"), 1, 4)
        self.target_phase_spin = QDoubleSpinBox()
        self.target_phase_spin.setRange(-360.0, 360.0)
        self.target_phase_spin.setDecimals(2)
        self.target_phase_spin.setValue(float(DEFAULT_TARGET_PHASE_DEG))
        self.target_phase_spin.setMaximumWidth(80)
        params_layout.addWidget(self.target_phase_spin, 1, 5)
        self.target_phase_spin.valueChanged.connect(self.on_targets_changed)

        # Hàng 3: Control Mode, Function, Cycles
        params_layout.addWidget(QLabel("Mode:"), 2, 0)
        self.control_mode_combo = QComboBox()
        self.control_mode_combo.addItems(["Angle"])
        self.control_mode_combo.setCurrentText(str(DEFAULT_CONTROL_MODE))
        self.control_mode_combo.setMaximumWidth(90)
        self.control_mode_combo.currentTextChanged.connect(self.on_control_mode_changed)
        params_layout.addWidget(self.control_mode_combo, 2, 1)

        params_layout.addWidget(QLabel("Function:"), 2, 2)
        self.function_combo = QComboBox()
        self.function_combo.addItems(["Triangular"])
        self.function_combo.setCurrentText(str(DEFAULT_FUNCTION_MODE))
        self.function_combo.setMaximumWidth(100)
        self.function_combo.currentTextChanged.connect(self.on_function_changed)
        params_layout.addWidget(self.function_combo, 2, 3)

        params_layout.addWidget(QLabel("Cycles:"), 2, 4)
        self.target_cycles_spin = QSpinBox()
        self.target_cycles_spin.setRange(0, 1000000)
        self.target_cycles_spin.setValue(int(DEFAULT_TARGET_CYCLES))
        self.target_cycles_spin.setMaximumWidth(80)
        params_layout.addWidget(self.target_cycles_spin, 2, 5)

        # Hàng 4: Buttons + Labels (gọn)
        self.btn_set_params = QPushButton("✅ Write")
        self.btn_set_params.setStyleSheet("background-color: #009688; color: white; font-weight: bold; padding: 4px;")
        self.btn_set_params.setMaximumWidth(90)
        self.btn_set_params.clicked.connect(self.set_parameters)
        params_layout.addWidget(self.btn_set_params, 3, 0, 1, 1)

        self.btn_export_csv = QPushButton("💾 Export")
        self.btn_export_csv.setMaximumWidth(90)
        self.btn_export_csv.clicked.connect(self.export_csv)
        params_layout.addWidget(self.btn_export_csv, 3, 1, 1, 1)

        self.cycle_label = QLabel("Cycle: 0")
        self.cycle_label.setStyleSheet("font-size: 9pt;")
        params_layout.addWidget(self.cycle_label, 3, 2, 1, 2)

        self.test_time_label = QLabel("Time: 0.0s")
        self.test_time_label.setStyleSheet("font-size: 9pt;")
        params_layout.addWidget(self.test_time_label, 3, 4, 1, 2)

        params_group.setLayout(params_layout)
        control_layout.addWidget(params_group)

        # Zero / Home / Reset (optional)
        zero_group = QGroupBox("🧭 Zero / Home / Reset")
        zero_layout = QHBoxLayout()
        self.btn_zero_angle = QPushButton("Zero Angle")
        self.btn_zero_angle.clicked.connect(self.zero_set_angle)
        zero_layout.addWidget(self.btn_zero_angle)
        self.btn_zero_torque = QPushButton("Zero Torque")
        self.btn_zero_torque.clicked.connect(self.zero_set_torque)
        zero_layout.addWidget(self.btn_zero_torque)
        self.btn_home = QPushButton("🏠 Home")
        self.btn_home.clicked.connect(self.to_home_position)
        zero_layout.addWidget(self.btn_home)
        self.btn_servo_reset = QPushButton("🔄 Reset")
        self.btn_servo_reset.clicked.connect(self.servo_reset)
        zero_layout.addWidget(self.btn_servo_reset)
        zero_group.setLayout(zero_layout)
        if SHOW_ZERO_HOME_RESET:
            control_layout.addWidget(zero_group)

        # Safety limits chỉ còn cấu hình trong Settings dialog, không chiếm chỗ ở main control
        control_layout.addStretch(1)

        # --- Column 2: Plots (moved here, Digital Display is now in Column 1) ---
        plots_widget = QWidget()
        plots_layout = QVBoxLayout(plots_widget)
        plot1_group = QGroupBox("📈 Torque - Time (Rolling 60s)")
        plot1_layout = QVBoxLayout()
        # Rolling 60s window, always updates regardless of test state
        self.plot_torque_time = RealTimePlot("Torque vs Time", "Time (s)", "Torque (N·m)", max_time_window_s=60.0)
        plot1_layout.addWidget(self.plot_torque_time)
        plot1_group.setLayout(plot1_layout)
        plots_layout.addWidget(plot1_group)

        plot2_group = QGroupBox("📉 Torque - Angle")
        plot2_layout = QVBoxLayout()
        self.plot_torque_angle = RealTimePlot("Torque vs Angle", "Angle (°)", "Torque (N·m)")
        plot2_layout.addWidget(self.plot_torque_angle)
        plot2_group.setLayout(plot2_layout)
        plots_layout.addWidget(plot2_group)

        btn_clear_plot = QPushButton("🗑️ Clear Plots")
        btn_clear_plot.clicked.connect(self.clear_plots)
        plots_layout.addWidget(btn_clear_plot)
        plots_layout.addStretch(1)

        # Add columns to splitter (2 columns now: Control+Display | Plots)
        splitter.addWidget(control_widget)
        splitter.addWidget(plots_widget)
        splitter.setSizes([450, 900])

        main_layout.addWidget(splitter, 1)
        
        # ===== LOG PANEL (optional) =====
        self.log_group = QGroupBox("📝 Activity Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet("font-family: 'Courier New'; font-size: 9pt;")
        log_layout.addWidget(self.log_text)
        self.log_group.setLayout(log_layout)
        if SHOW_ACTIVITY_LOG:
            main_layout.addWidget(self.log_group)
        
        # Footer
        footer = QLabel("PLC Modbus RTU Master SCADA")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: gray; font-size: 9pt;")
        main_layout.addWidget(footer)

    def _create_settings_widgets(self):
        """Create settings widgets (Servo, Analog, Poll, Safety) - stored for Settings dialog."""
        # Servo settings
        self.pulses_per_rev_spin = QSpinBox()
        self.pulses_per_rev_spin.setRange(1, 10_000_000)
        self.pulses_per_rev_spin.setValue(int(getattr(self, 'pulses_per_rev', DEFAULT_PULSES_PER_REV)))
        self.pulses_per_rev_spin.valueChanged.connect(self.on_servo_settings_changed)

        self.gear_ratio_spin = QDoubleSpinBox()
        self.gear_ratio_spin.setRange(0.0001, 1000.0)
        self.gear_ratio_spin.setDecimals(4)
        self.gear_ratio_spin.setValue(float(getattr(self, 'gear_ratio', DEFAULT_GEAR_RATIO)))
        self.gear_ratio_spin.setSingleStep(0.1)
        self.gear_ratio_spin.valueChanged.connect(self.on_servo_settings_changed)

        self.pulses_per_deg_label = QLabel("-")

        # Analog settings
        self.bipolar_checkbox = QCheckBox("Bipolar Mode (torque có giá trị âm)")
        self.bipolar_checkbox.setChecked(bool(getattr(self, 'analog_bipolar', DEFAULT_ANALOG_BIPOLAR)))
        self.bipolar_checkbox.stateChanged.connect(self.on_analog_mode_changed)

        self.max_torque_spin = QDoubleSpinBox()
        self.max_torque_spin.setRange(1.0, 10000.0)
        self.max_torque_spin.setDecimals(1)
        self.max_torque_spin.setValue(float(getattr(self, 'analog_max_torque_nm', DEFAULT_ANALOG_MAX_TORQUE_NM)))
        self.max_torque_spin.setSingleStep(10.0)
        self.max_torque_spin.valueChanged.connect(self.on_analog_mode_changed)

        self.bipolar_info_label = QLabel("Bipolar: 2400=0, 800=-max, 4000=+max")

        # Poll/Throttle settings
        self.poll_interval_spin = QSpinBox()
        self.poll_interval_spin.setRange(1, 2000)
        self.poll_interval_spin.setValue(int(getattr(self, '_poll_interval_ms', DEFAULT_POLL_INTERVAL_MS)))
        self.poll_interval_spin.valueChanged.connect(self.on_poll_interval_changed)

        self.write_delay_spin = QSpinBox()
        self.write_delay_spin.setRange(0, 5000)
        self.write_delay_spin.setValue(int(getattr(self, '_write_delay_ms', DEFAULT_WRITE_DELAY_MS)))
        self.write_delay_spin.valueChanged.connect(self.on_write_delay_changed)

        self.sample_interval_spin = QSpinBox()
        self.sample_interval_spin.setRange(1, 2000)
        self.sample_interval_spin.setValue(int(getattr(self, '_sample_interval_ms', DEFAULT_SAMPLE_INTERVAL_MS)))
        self.sample_interval_spin.valueChanged.connect(self.on_sample_interval_changed)

        self.time_stop_cb = QCheckBox("Time-based auto-stop (fallback)")
        self.time_stop_cb.setChecked(bool(DEFAULT_ENABLE_TIME_BASED_STOP))
        self.time_stop_cb.stateChanged.connect(self.on_time_stop_changed)

        # Safety limits widgets
        self.angle_low_spin = QDoubleSpinBox()
        self.angle_low_spin.setRange(-999999.0, 999999.0)
        self.angle_low_spin.setDecimals(2)
        self.angle_low_spin.setValue(float(DEFAULT_LIMIT_ANGLE_LOW_DEG))

        self.angle_high_spin = QDoubleSpinBox()
        self.angle_high_spin.setRange(-999999.0, 999999.0)
        self.angle_high_spin.setDecimals(2)
        self.angle_high_spin.setValue(float(DEFAULT_LIMIT_ANGLE_HIGH_DEG))

        self.torque_low_spin = QDoubleSpinBox()
        self.torque_low_spin.setRange(-999999.0, 999999.0)
        self.torque_low_spin.setDecimals(2)
        self.torque_low_spin.setValue(float(DEFAULT_LIMIT_TORQUE_LOW_NM))

        self.torque_high_spin = QDoubleSpinBox()
        self.torque_high_spin.setRange(-999999.0, 999999.0)
        self.torque_high_spin.setDecimals(2)
        self.torque_high_spin.setValue(float(DEFAULT_LIMIT_TORQUE_HIGH_NM))

        self.limit_action_combo = QComboBox()
        self.limit_action_combo.addItems(["Motor Off", "Command Stop"])
        try:
            self.limit_action_combo.setCurrentText(str(DEFAULT_LIMIT_ACTION))
        except Exception:
            pass

        self.limits_enable_checkbox = QCheckBox("Enable limits")
        self.limits_enable_checkbox.setChecked(bool(DEFAULT_LIMITS_ENABLED))

        # Plot settings
        self.use_cmd_angle_checkbox = QCheckBox("Use Command Angle for Plot (thay vì Actual Angle)")
        self.use_cmd_angle_checkbox.setChecked(bool(getattr(self, 'use_cmd_angle_for_plot', DEFAULT_USE_CMD_ANGLE_FOR_PLOT)))
        self.use_cmd_angle_checkbox.stateChanged.connect(self.on_plot_angle_source_changed)

        self.plot_smooth_checkbox = QCheckBox("Enable Plot Smoothing (EMA filter)")
        self.plot_smooth_checkbox.setChecked(bool(getattr(self, '_plot_smooth_enabled', DEFAULT_ENABLE_PLOT_SMOOTHING)))
        self.plot_smooth_checkbox.stateChanged.connect(self.on_plot_smooth_changed)

        self.plot_smooth_tau_spin = QSpinBox()
        self.plot_smooth_tau_spin.setRange(0, 500)
        self.plot_smooth_tau_spin.setValue(int(getattr(self, '_plot_smooth_tau_ms', DEFAULT_PLOT_SMOOTH_TAU_MS)))
        self.plot_smooth_tau_spin.setSuffix(" ms")
        self.plot_smooth_tau_spin.valueChanged.connect(self.on_plot_smooth_tau_changed)

    def on_plot_angle_source_changed(self, state):
        """Handle plot angle source checkbox change."""
        self.use_cmd_angle_for_plot = (state == Qt.Checked)
        source = "Command Angle" if self.use_cmd_angle_for_plot else "Actual Angle"
        self.log(f"📊 Plot angle source changed to: {source}")

    def on_plot_smooth_changed(self, state):
        """Handle plot smoothing checkbox change."""
        self._plot_smooth_enabled = (state == Qt.Checked)
        status = "enabled" if self._plot_smooth_enabled else "disabled"
        self.log(f"📊 Plot smoothing {status}")

    def on_plot_smooth_tau_changed(self, value):
        """Handle plot smoothing tau change."""
        self._plot_smooth_tau_ms = float(value)
        self.log(f"📊 Plot smoothing tau: {value} ms")

    def _open_settings_dialog(self):
        """Open Settings dialog with Servo, Analog, Poll, Safety limits settings."""
        from PyQt5.QtWidgets import QDialog, QTabWidget

        def _qt_is_deleted(obj) -> bool:
            if obj is None:
                return True
            try:
                import sip  # type: ignore
                return bool(sip.isdeleted(obj))
            except Exception:
                try:
                    from PyQt5 import sip as pyqt_sip  # type: ignore
                    return bool(pyqt_sip.isdeleted(obj))
                except Exception:
                    try:
                        obj.parent()
                        return False
                    except RuntimeError:
                        return True

        # If a previous (non-persistent) dialog re-parented these widgets, they may have been deleted.
        # Recreate them as needed.
        try:
            if _qt_is_deleted(getattr(self, 'pulses_per_rev_spin', None)) or _qt_is_deleted(getattr(self, 'gear_ratio_spin', None)):
                self._create_settings_widgets()
        except Exception:
            try:
                self._create_settings_widgets()
            except Exception:
                pass

        # Reuse a persistent dialog so Qt doesn't delete the widgets on close.
        try:
            if getattr(self, '_settings_dlg', None) is not None and not _qt_is_deleted(self._settings_dlg):
                try:
                    if self._settings_dlg.isVisible():
                        self._settings_dlg.raise_()
                        self._settings_dlg.activateWindow()
                        return
                except Exception:
                    pass
                self._settings_dlg.show()
                try:
                    self._settings_dlg.raise_()
                    self._settings_dlg.activateWindow()
                except Exception:
                    pass
                return
        except Exception:
            self._settings_dlg = None

        dlg = QDialog(self)
        dlg.setWindowTitle("⚙️ Settings")
        dlg.setMinimumWidth(450)
        dlg_layout = QVBoxLayout(dlg)

        tabs = QTabWidget()

        # === Servo Settings Tab ===
        if SHOW_SERVO_SETTINGS:
            servo_tab = QWidget()
            servo_layout = QGridLayout(servo_tab)
            servo_layout.addWidget(QLabel("Pulses / Rev:"), 0, 0)
            servo_layout.addWidget(self.pulses_per_rev_spin, 0, 1)
            servo_layout.addWidget(QLabel("Gear Ratio:"), 1, 0)
            servo_layout.addWidget(self.gear_ratio_spin, 1, 1)
            servo_layout.addWidget(QLabel("Pulses / Deg:"), 2, 0)
            servo_layout.addWidget(self.pulses_per_deg_label, 2, 1)
            servo_layout.setRowStretch(3, 1)
            tabs.addTab(servo_tab, "⚙️ Servo")

        # === Analog Settings Tab ===
        if SHOW_ANALOG_SETTINGS:
            analog_tab = QWidget()
            analog_layout = QGridLayout(analog_tab)
            analog_layout.addWidget(self.bipolar_checkbox, 0, 0, 1, 2)
            analog_layout.addWidget(QLabel("Max Torque (N·m):"), 1, 0)
            analog_layout.addWidget(self.max_torque_spin, 1, 1)
            analog_layout.addWidget(self.bipolar_info_label, 2, 0, 1, 2)
            analog_layout.setRowStretch(3, 1)
            tabs.addTab(analog_tab, "📊 Analog")

        # === Poll/Throttle Settings Tab ===
        if SHOW_POLL_SETTINGS:
            poll_tab = QWidget()
            poll_layout = QGridLayout(poll_tab)
            poll_layout.addWidget(QLabel("Poll interval (ms):"), 0, 0)
            poll_layout.addWidget(self.poll_interval_spin, 0, 1)
            poll_layout.addWidget(QLabel("Write delay (ms):"), 1, 0)
            poll_layout.addWidget(self.write_delay_spin, 1, 1)
            poll_layout.addWidget(QLabel("Sample interval (ms):"), 2, 0)
            poll_layout.addWidget(self.sample_interval_spin, 2, 1)
            poll_layout.addWidget(self.time_stop_cb, 3, 0, 1, 2)
            poll_layout.setRowStretch(4, 1)
            tabs.addTab(poll_tab, "⚡ Poll")

        # === Safety Limits Tab ===
        if SHOW_SAFETY_LIMITS:
            safety_tab = QWidget()
            safety_layout = QGridLayout(safety_tab)

            safety_layout.addWidget(QLabel("Angle Low (°):"), 0, 0)
            safety_layout.addWidget(self.angle_low_spin, 0, 1)
            safety_layout.addWidget(QLabel("Angle High (°):"), 0, 2)
            safety_layout.addWidget(self.angle_high_spin, 0, 3)

            safety_layout.addWidget(QLabel("Torque Low (N·m):"), 1, 0)
            safety_layout.addWidget(self.torque_low_spin, 1, 1)
            safety_layout.addWidget(QLabel("Torque High (N·m):"), 1, 2)
            safety_layout.addWidget(self.torque_high_spin, 1, 3)

            safety_layout.addWidget(QLabel("Limit Action:"), 2, 0)
            safety_layout.addWidget(self.limit_action_combo, 2, 1)
            safety_layout.addWidget(self.limits_enable_checkbox, 2, 2, 1, 2)

            safety_layout.setRowStretch(3, 1)
            tabs.addTab(safety_tab, "🛡️ Safety")

        # === Plot Settings Tab ===
        plot_tab = QWidget()
        plot_layout = QGridLayout(plot_tab)
        plot_layout.addWidget(self.use_cmd_angle_checkbox, 0, 0, 1, 2)
        plot_layout.addWidget(QLabel("• Command Angle: góc tính toán/gửi đi"), 1, 0, 1, 2)
        plot_layout.addWidget(QLabel("• Actual Angle: góc thực tế đọc từ Modbus"), 2, 0, 1, 2)
        plot_layout.addWidget(self.plot_smooth_checkbox, 3, 0, 1, 2)
        plot_layout.addWidget(QLabel("Smoothing tau:"), 4, 0)
        plot_layout.addWidget(self.plot_smooth_tau_spin, 4, 1)
        plot_layout.addWidget(QLabel("(Tau nhỏ=nhanh, lớn=mượt hơn)"), 5, 0, 1, 2)
        plot_layout.setRowStretch(6, 1)
        tabs.addTab(plot_tab, "📈 Plot")

        dlg_layout.addWidget(tabs)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        dlg_layout.addWidget(btn_close)

        self._settings_dlg = dlg
        dlg.exec_()

    def on_write_delay_changed(self, value):
        try:
            self._write_delay_ms = int(value)
        except Exception:
            self._write_delay_ms = int(DEFAULT_WRITE_DELAY_MS)
    
    # ========== COM PORT MANAGEMENT ==========
    
    def refresh_com_ports(self):
        """Scan and list available COM ports"""
        self.com_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            self.com_combo.addItem("No COM ports found")
            self.log("⚠️ No COM ports detected on system")
            return
        
        for port in ports:
            desc = port.description or port.hwid or ""
            display = f"{port.device} - {desc}"
            self.com_combo.addItem(display, port.device)
        
        self.log(f"✅ Found {len(ports)} COM port(s)")
    
    # ========== CONNECTION ==========
    
    def toggle_connection(self):
        """Connect/Disconnect to Modbus slave"""
        if self.connect_btn.text() == "🔗 Connect":
            self.connect_modbus()
        else:
            self.disconnect_modbus()
    
    def connect_modbus(self):
        """Establish Modbus connection"""
        port = self.com_combo.currentData()
        if not port:
            port_text = self.com_combo.currentText()
            if "No COM" in port_text or not port_text:
                self.log("❌ No COM port selected")
                return
            port = port_text.split(" - ")[0].strip()
        
        baud = int(self.baud_combo.currentText())
        parity_map = {"None": "N", "Even": "E", "Odd": "O"}
        parity = parity_map[self.parity_combo.currentText()]
        self.slave_id = self.slave_spin.value()
        
        try:
            self.modbus_client = ModbusSerialClient(
                port=port,
                method='rtu',
                baudrate=baud,
                bytesize=8,
                parity=parity,
                stopbits=1,
                # Ultra-fast timeout for maximum polling speed
                # Modbus RTU at 115200: ~3-5ms typical, 20ms worst case
                timeout=0.02,
                # Reduce inter-character timeout for faster framing
                strict=False,
            )
            # enable low-level frame debug when available
            try:
                self.modbus_client.debug_enabled = True
            except Exception:
                pass

            self.connected = bool(self.modbus_client.connect())
            if self.connected:
                self.connect_btn.setText("🔌 Disconnect")
                self.connect_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 5px;")
                self.status_label.setText("🟢 Connected")
                self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 11pt;")
                
                # Initialize rolling plot timeline
                self._plot_t0_monotonic = time.monotonic()
                
                self.log(f"✅ Connected: {port} @ {baud} baud, Parity={parity}, Slave={self.slave_id}")

                self.unit_id = None
                self.addr_offset = 0
                self.detect_label.setText("Unit: - | Addr offset: -")
                self._consecutive_failures = 0
                self.fail_label.setText("0")

                # Automatically apply Unit ID and Addr Offset from the UI immediately
                # (behaves like pressing 'Apply Unit/Offset' right after connect)
                try:
                    # Use UI values as authoritative defaults
                    self.unit_id = int(self.slave_spin.value())
                    self.addr_offset = int(self.addr_offset_spin.value())
                    self.detect_label.setText(f"Unit: {self.unit_id} | Addr offset: {self.addr_offset}")
                    self.log(f"✅ Applied Unit/Offset from UI: Unit={self.unit_id}, addr_offset={self.addr_offset}")
                    # start polling immediately
                    QTimer.singleShot(0, self._start_polling_thread)

                    # Auto-write initial parameters on connect (speed + mean/amp/phase)
                    if bool(DEFAULT_WRITE_PARAMS_ON_CONNECT):
                        QTimer.singleShot(0, self._write_params_on_connect)
                except Exception as e:
                    self.log(f"⚠️ Failed to apply Unit/Offset after connect: {e}")
                    # fallback to probe if manual values cannot be applied
                    QTimer.singleShot(0, self._probe_unit_and_offset_async)
            else:
                self.log("❌ Failed to open COM port")
                self.modbus_client = None
                self.connected = False
                
        except Exception as e:
            self.log(f"❌ Connection error: {e}")
            self.modbus_client = None
            self.connected = False
    
    def disconnect_modbus(self):
        """Close Modbus connection"""
        self._stop_polling_thread()
        
        if self.modbus_client:
            try:
                self.modbus_client.close()
            except Exception:
                pass
            self.modbus_client = None
        self.connected = False
        
        self.connect_btn.setText("🔗 Connect")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        self.status_label.setText("⚪ Disconnected")
        self.status_label.setStyleSheet("color: gray; font-weight: bold; font-size: 11pt;")
        
        self.log("🔌 Disconnected")
    
    def _probe_unit_and_offset_async(self):
        """Detect unit id and address base offset (0/1) without blocking GUI."""
        def worker():
            try:
                unit_candidates = []
                # prefer user-selected, then 1, then 0 (common for single servers)
                for u in [self.slave_id, 1, 0, 2, 3]:
                    if u not in unit_candidates and 0 <= int(u) <= 247:
                        unit_candidates.append(int(u))

                best = None
                best_score = -1
                for unit in unit_candidates:
                    for offset in (0, 1):
                        regs = self._read_regs_raw(HR_READ_START + offset, HR_READ_COUNT, unit)
                        if not regs or len(regs) < 4:
                            continue
                        angle_hi, angle_lo, analog_raw, status_bits = regs[0], regs[1], regs[2], regs[3]

                        score = 0
                        # status bits should be small
                        if 0 <= status_bits <= 0xFF:
                            score += 2
                        # angle_hi should be reasonable (within ±360° = ±360000000)
                        if angle_hi <= 0xFFFF:
                            score += 1
                        # analog raw any u16 ok
                        if 0 <= analog_raw <= 65535:
                            score += 1

                        if score > best_score:
                            best_score = score
                            best = (unit, offset)

                if best is None:
                    self.log_signal.emit("⚠️ Probe failed: cannot read addr 1..3 with unit/offset candidates")
                    # fallback to user-selected
                    unit = int(self.slave_id)
                    offset = 0
                else:
                    unit, offset = best

                def apply():
                    self.unit_id = int(unit)
                    self.addr_offset = int(offset)
                    self.detect_label.setText(f"Unit: {self.unit_id} | Addr offset: {self.addr_offset}")
                    self.log(f"✅ Using Unit={self.unit_id}, addr_offset={self.addr_offset}")
                    self._start_polling_thread()

                    # Auto-write initial parameters on connect (speed + mean/amp/phase)
                    if bool(DEFAULT_WRITE_PARAMS_ON_CONNECT):
                        QTimer.singleShot(0, self._write_params_on_connect)

                QTimer.singleShot(0, apply)
            except Exception as e:
                self.log_signal.emit(f"⚠️ Probe exception: {e}")
                QTimer.singleShot(0, self._start_polling_thread)

        threading.Thread(target=worker, daemon=True).start()

    def _write_params_on_connect(self):
        """Send current UI parameters to slave once right after connect."""
        try:
            if not self.connected:
                return
            self._pending_speed_raw = int(round(float(self.speed_hz_spin.value())))
            self._pending_targets_raw = (
                int(round(float(self.target_mean_spin.value()) * 100.0)),
                int(round(max(MIN_TARGET_AMP_DEG, float(self.target_amp_spin.value())) * 100.0)),
                int(round(float(self.target_phase_spin.value()) * 100.0)),
            )
            self._do_send_params()
        except Exception as e:
            try:
                self.log(f"⚠️ Auto-write params on connect failed: {e}")
            except Exception:
                pass
    
    def apply_manual_unit_offset(self):
        """Apply manual unit/addr_offset settings and start polling (if connected)."""
        try:
            if not self.connected:
                self.log("⚠️ Not connected. Connect first before applying manual unit/offset")
                return

            unit = int(self.slave_spin.value())
            offset = int(self.addr_offset_spin.value())
            self.unit_id = unit
            self.addr_offset = offset
            self.detect_label.setText(f"Unit: {self.unit_id} | Addr offset: {self.addr_offset}")
            self.log(f"✅ Manual Unit/Offset applied: Unit={self.unit_id}, addr_offset={self.addr_offset}")
            # restart polling with forced values
            self._start_polling_thread()
        except Exception as e:
            self.log(f"❌ Apply manual Unit/Offset failed: {e}")
    
    # ========== MODBUS I/O ==========
    
    # ========== MODBUS I/O (FC3/FC6/FC16) + FALLBACK unit/slave ==========

    def _call_with_unit_fallback(self, func, *args, unit=None):
        """Call pymodbus client method with kw fallback: unit -> slave."""
        if unit is None:
            unit = self.slave_id
        try:
            return func(*args, unit=unit)
        except TypeError:
            return func(*args, slave=unit)

    def _read_regs_raw(self, addr, count, unit):
        """Ultra-fast register read with minimal overhead."""
        if not self.modbus_client or not self.connected:
            return None
        try:
            # Direct call without extra lock (pymodbus is thread-safe for single client)
            try:
                result = self.modbus_client.read_holding_registers(addr, count, unit=unit)
            except TypeError:
                result = self.modbus_client.read_holding_registers(addr, count, slave=unit)
            
            # Fast path: check registers attribute directly
            if result and hasattr(result, 'registers'):
                return result.registers  # Return directly, no list() copy needed
            return None
        except Exception:
            return None

    def read_registers(self, addr, count):
        """Read holding registers using detected unit+offset."""
        unit = self.unit_id if self.unit_id is not None else self.slave_id
        addr2 = int(addr) + int(self.addr_offset)
        return self._read_regs_raw(addr2, count, unit)

    def _write_regs(self, addr, values):
        """Write holding registers. Prefer FC16 then fallback to FC6 (single)."""
        if not self.modbus_client or not self.connected:
            self.log("⚠️ Not connected")
            return False

        unit = self.unit_id if self.unit_id is not None else self.slave_id
        addr2 = int(addr) + int(self.addr_offset)

        vals = list(values)
        for v in vals:
            if v < 0 or v > 65535:
                self.log(f"⚠️ Value {v} out of range (0-65535)")
                return False

        # Pause polling to reduce contention
        self._poll_pause.set()
        try:
            # Try FC16 first
            try:
                with self._modbus_lock:
                    result = self._call_with_unit_fallback(
                        self.modbus_client.write_registers, addr2, vals, unit=unit
                    )
                if result is not None:
                    try:
                        if not result.isError():
                                # successful write; attempt read-back verification
                                try:
                                    # read back the first register we wrote
                                    try:
                                        rb = self._call_with_unit_fallback(
                                            self.modbus_client.read_holding_registers, addr2, 1, unit=unit
                                        )
                                    except TypeError:
                                        rb = self._call_with_unit_fallback(
                                            self.modbus_client.read_holding_registers, addr2, 1, slave=unit
                                        )

                                    if rb is not None and (not getattr(rb, 'isError', lambda: False)()) and hasattr(rb, 'registers'):
                                        self.log(f"✅ Write verified: HR@{addr2} = {rb.registers[0]}")
                                    else:
                                        self.log(f"⚠️ Write may not have applied (read-back failed) at HR@{addr2}")
                                except Exception:
                                    pass
                                return True
                    except Exception:
                        pass
            except Exception:
                pass

            # Fallback FC6 for single value
            if len(vals) == 1:
                try:
                    with self._modbus_lock:
                        result = self._call_with_unit_fallback(
                            self.modbus_client.write_register, addr2, vals[0], unit=unit
                        )
                    if result is None:
                        return False
                    try:
                        return not result.isError()
                    except Exception:
                        return True
                except Exception:
                    return False

            return False
        finally:
            self._poll_pause.clear()

    def _write_regs_fast(self, addr, values):
        """Fast write without pausing polling or read-back verification (for high-rate cmd writes)."""
        if not self.modbus_client or not self.connected:
            return False

        unit = self.unit_id if self.unit_id is not None else self.slave_id
        addr2 = int(addr) + int(self.addr_offset)
        vals = [int(v) & 0xFFFF for v in list(values)]

        try:
            with self._modbus_lock:
                result = self._call_with_unit_fallback(
                    self.modbus_client.write_registers, addr2, vals, unit=unit
                )
            if result is None:
                return False
            try:
                return not result.isError()
            except Exception:
                return True
        except Exception:
            return False

    # ========== HIGH-SPEED MULTI-THREADED POLLING ==========
    # Architecture:
    # 1. Reader thread: reads Modbus as fast as possible, stores in ring buffer
    # 2. Sampler thread: extracts samples at precise intervals (default 2ms)
    # 3. GUI updates via signal at lower rate
    
    def on_poll_interval_changed(self, value):
        try:
            self._poll_interval_ms = int(value)
        except Exception:
            self._poll_interval_ms = 1

    def on_sample_interval_changed(self, value):
        try:
            self._sample_interval_ms = int(value)
        except Exception:
            self._sample_interval_ms = 2
        self._sample_interval_ms = max(1, int(self._sample_interval_ms))
        self._sample_dt_s = float(self._sample_interval_ms) / 1000.0

    def _start_polling_thread(self):
        """Start high-speed multi-threaded data acquisition."""
        self._stop_polling_thread()
        self._poll_stop.clear()
        self._poll_pause.clear()
        self._poll_count = 0
        self._sample_count = 0
        
        # Clear ring buffer
        with self._ring_lock:
            self._ring_buffer.clear()
        self._latest_regs = None
        self._latest_regs_time = 0.0
        
        # Performance tracking
        self._poll_stats = {'avg_ms': 0, 'min_ms': 0, 'max_ms': 0, 'rate_hz': 0, 'count': 0}
        self._sample_stats = {'rate_hz': 0, 'count': 0}

        # ===== THREAD 1: High-speed Modbus Reader =====
        def reader_worker():
            """Read Modbus registers as fast as possible into ring buffer."""
            poll_stop = self._poll_stop
            poll_pause = self._poll_pause
            read_regs = self.read_registers
            perf_counter = time.perf_counter
            
            poll_times = []
            track_start = perf_counter()
            poll_count = 0
            
            while not poll_stop.is_set():
                t0 = perf_counter()

                if poll_pause.is_set():
                    time.sleep(0.001)
                    continue

                if not self.connected:
                    time.sleep(0.01)
                    continue

                # Ultra-fast read - no lock needed for single client
                try:
                    regs = read_regs(HR_READ_START, HR_READ_COUNT)
                except Exception:
                    regs = None

                if regs and len(regs) >= 4:
                    t_read = perf_counter()
                    # Store in ring buffer (thread-safe deque append)
                    self._ring_buffer.append({
                        't': t_read,
                        'regs': regs,
                    })
                    # Also keep latest for immediate GUI access
                    self._latest_regs = regs
                    self._latest_regs_time = t_read

                poll_count += 1
                self._poll_count = poll_count
                
                # Minimal time tracking
                elapsed_ms = (perf_counter() - t0) * 1000.0
                poll_times.append(elapsed_ms)
                
                # Stats every 100 reads
                if len(poll_times) >= 100:
                    n = len(poll_times)
                    total_s = perf_counter() - track_start
                    self._poll_stats = {
                        'avg_ms': sum(poll_times) / n,
                        'min_ms': min(poll_times),
                        'max_ms': max(poll_times),
                        'rate_hz': n / total_s if total_s > 0 else 0,
                        'count': poll_count
                    }
                    poll_times.clear()
                    track_start = perf_counter()

                # Minimal sleep to prevent CPU saturation but maximize throughput
                # At 115200 baud, one read takes ~3-5ms minimum
                # No sleep = back-to-back reads as fast as serial allows

        # ===== THREAD 2: Precise Interval Sampler =====
        def sampler_worker():
            """Sample from ring buffer at precise intervals (default 2ms)."""
            poll_stop = self._poll_stop
            emit_signal = self.poll_signal.emit
            perf_counter = time.perf_counter
            
            sample_count = 0
            last_sample_time = perf_counter()
            track_start = perf_counter()
            plot_every = self._plot_every_n_polls
            
            while not poll_stop.is_set():
                interval_s = self._sample_interval_ms / 1000.0
                now = perf_counter()
                
                # Wait until next sample time
                elapsed = now - last_sample_time
                if elapsed < interval_s:
                    sleep_time = interval_s - elapsed
                    if sleep_time > 0.0001:
                        time.sleep(sleep_time)
                    continue
                
                last_sample_time = now
                
                if not self.connected:
                    continue
                
                # Get latest data from buffer
                regs = self._latest_regs
                if regs is None:
                    continue
                
                sample_count += 1
                self._sample_count = sample_count
                
                # Update sample stats every 250 samples
                if sample_count % 250 == 0:
                    total_s = perf_counter() - track_start
                    self._sample_stats = {
                        'rate_hz': 250 / total_s if total_s > 0 else 0,
                        'count': sample_count
                    }
                    track_start = perf_counter()
                
                # Emit to GUI (throttled by plot_every)
                try:
                    emit_signal({
                        "ts": datetime.now(),
                        "regs": regs,
                        "plot": (sample_count % plot_every == 0),
                        "sample_count": sample_count,
                    })
                except Exception:
                    pass

        # Start both threads
        self._poll_thread = threading.Thread(target=reader_worker, daemon=True, name="ModbusReader")
        self._sampler_thread = threading.Thread(target=sampler_worker, daemon=True, name="Sampler")
        
        self._poll_thread.start()
        self._sampler_thread.start()

    def _stop_polling_thread(self):
        """Stop all data acquisition threads."""
        try:
            self._poll_stop.set()
        except Exception:
            pass
        
        # Wait for threads to finish
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=0.5)
        if self._sampler_thread and self._sampler_thread.is_alive():
            self._sampler_thread.join(timeout=0.5)
            
        self._poll_thread = None
        self._sampler_thread = None

    def _reset_plot_session_state(self, reason: str = None):
        """Reset plots/sampling timeline so incoming data can be graphed."""
        self._test_running = True
        self._limit_tripped = False
        self._auto_stop_issued = False
        self._cycle_count = 0
        self._last_mission_done = 0
        self._cmd_peak = None
        self._cmd_valley = None
        self._fb_peak = None
        self._fb_valley = None
        self._torque_peak = None
        self._torque_valley = None
        self.cycle_label.setText("Cycles: 0")
        self._samples = []
        self._run_t0_perf = time.perf_counter()
        self._sample_index = 0
        self._next_sample_due_s = 0.0
        self._last_sample_time_s = 0.0
        # Reset smoothing filter state
        self._smooth_angle = 0.0
        self._smooth_torque = 0.0
        self._smooth_initialized = False
        self._last_smooth_time = None
        try:
            self.plot_torque_time.clear_plot()
            self.plot_torque_angle.clear_plot()
        except Exception:
            pass
        self.start_time = datetime.now()
        if reason:
            self.log(f"▶️ Plot session started ({reason})")

    def on_polled_data(self, payload: dict):
        """Handle polled data on GUI thread."""
        # Update poll stats display (Modbus read rate)
        try:
            if hasattr(self, '_poll_stats'):
                stats = self._poll_stats
                self.poll_rate_label.setText(f"{stats['rate_hz']:.0f} ({stats['avg_ms']:.1f}/{stats['max_ms']:.1f}ms)")
        except Exception:
            pass
        
        # Update sample stats display (data sampling rate)
        try:
            if hasattr(self, '_sample_stats'):
                s_stats = self._sample_stats
                self.sample_rate_label.setText(f"{s_stats['rate_hz']:.0f}")
        except Exception:
            pass
        
        regs = payload.get("regs")
        if not regs or len(regs) < 4:
            self._consecutive_failures += 1
            self.fail_label.setText(str(self._consecutive_failures))
            if self._consecutive_failures == self._max_consecutive_failures_log:
                self.log("⚠️ Polling: consecutive read failures")
            return

        self._consecutive_failures = 0
        self.fail_label.setText("0")

        # 32-bit angle from 2 registers (deg * 1000000 for 6 decimal precision)
        angle_hi, angle_lo, analog_raw, status_bits = int(regs[0]), int(regs[1]), int(regs[2]), int(regs[3])
        angle_i32 = (angle_hi << 16) | angle_lo
        # Convert from unsigned 32-bit to signed 32-bit
        if angle_i32 & 0x80000000:
            angle_i32 = angle_i32 - 0x100000000

        # Convert to degrees (6 decimal precision: deg * 1000000)
        self.current_angle_raw = float(angle_i32) / 1000000.0
        self.current_angle = self.current_angle_raw - float(getattr(self, 'angle_zero_offset_deg', 0.0))
        self.angle_label.setText(f"{self.current_angle:.6f} °")

        self.current_analog = analog_raw
        self.analog_label.setText(str(self.current_analog))
        # Use bipolar mode setting for torque conversion
        bipolar = bool(getattr(self, 'analog_bipolar', DEFAULT_ANALOG_BIPOLAR))
        max_torque = float(getattr(self, 'analog_max_torque_nm', DEFAULT_ANALOG_MAX_TORQUE_NM))
        self.current_ma, self.current_torque_raw = torque_from_analog_raw(self.current_analog, bipolar=bipolar, max_torque_nm=max_torque)
        self.current_torque = float(self.current_torque_raw) - float(getattr(self, 'torque_zero_offset_nm', 0.0))
        self.current_label.setText(f"{self.current_ma:.3f} mA")
        self.torque_label.setText(f"{self.current_torque:.6f} N·m")

        home = 1 if (status_bits & 0x01) else 0
        servo_run = 1 if (status_bits & 0x02) else 0
        mission_done = 1 if (status_bits & 0x04) else 0

        self.home_label.setText("🟢 ON" if home else "⚪ OFF")
        self.servo_run_label.setText("🟢 ON" if servo_run else "⚪ OFF")
        self.mission_done_label.setText("✅ DONE" if mission_done else "⏳ RUNNING")

        # === ALWAYS update Torque vs Time plot (rolling 60s window) ===
        # This runs continuously regardless of test state
        try:
            # Use monotonic time for rolling window (relative to connection start)
            if not hasattr(self, '_plot_t0_monotonic') or self._plot_t0_monotonic is None:
                self._plot_t0_monotonic = time.monotonic()
            plot_time = time.monotonic() - self._plot_t0_monotonic
            self.plot_torque_time.update_plot(plot_time, self.current_torque)
        except Exception:
            pass

        # Log state changes
        if self._last_status_bits is None:
            self._last_status_bits = status_bits
        elif status_bits != self._last_status_bits:
            self.log(f"🔁 Status change: 0x{self._last_status_bits:04X} → 0x{status_bits:04X}")
            self._last_status_bits = status_bits

        # If the simulator auto-runs (servo_run=ON) but START was not clicked,
        # auto-start plotting so analog feedback is graphed.
        if servo_run and not self._test_running:
            self._reset_plot_session_state(reason="auto: Servo Run=ON")

        # Only start timeline/plots/sampling AFTER user presses START
        if not self._test_running:
            return

        ts = payload.get("ts") or datetime.now()
        if self._run_t0_perf is None:
            self._run_t0_perf = time.perf_counter()
        elapsed_real = max(0.0, time.perf_counter() - float(self._run_t0_perf))

        # Update cmd-angle for fast write path (real-time, not fixed-step sample time)
        try:
            cmd_rt = float(self._compute_command_angle(float(elapsed_real)))
            self._cmd_angle_to_send_i16 = int(round(cmd_rt * 100.0))
        except Exception:
            self._cmd_angle_to_send_i16 = 0
        try:
            mean_deg = float(self.target_mean_spin.value())
            amp_deg = float(self.target_amp_spin.value())
            phase_deg = float(self.target_phase_spin.value())
            _pps = float(self.speed_hz_spin.value())
        except Exception:
            mean_deg, amp_deg, phase_deg, _pps = 0.0, 0.0, 0.0, 0.0

        # Append uniform samples up to elapsed_real (time axis: 0, dt, 2dt, ...)
        self._append_uniform_samples(elapsed_real, ts)

        # Optional fallback auto-stop based on elapsed time (ONLY if enabled).
        # Default behavior: stop on Mission Done from PLC/simulator.
        if bool(getattr(self, 'enable_time_based_stop', False)):
            try:
                if not self._auto_stop_issued:
                    target_cycles_cfg = int(self.target_cycles_spin.value())
                else:
                    target_cycles_cfg = 0
            except Exception:
                target_cycles_cfg = 0

            if target_cycles_cfg > 0 and not self._auto_stop_issued:
                try:
                    freq_hz = float(self._equivalent_freq_hz())
                except Exception:
                    freq_hz = 0.0
                try:
                    dt_s = float(getattr(self, '_sample_dt_s', 0.004))
                except Exception:
                    dt_s = 0.004

                if freq_hz > 0.0:
                    expected_end_s = float(target_cycles_cfg) / float(freq_hz)
                    if float(elapsed_real) + (0.5 * max(1e-6, dt_s)) >= expected_end_s:
                        self._auto_stop_issued = True
                        try:
                            self._cycle_count = int(target_cycles_cfg)
                            self.cycle_label.setText(f"Cycles: {self._cycle_count}")
                        except Exception:
                            pass
                        self.log(f"✅ Time-based stop (fallback): reached {target_cycles_cfg} cycle(s) (t≈{elapsed_real:.3f}s, f={freq_hz:.6f}Hz)")
                        try:
                            self._write_regs_fast(HR_TEST_DONE, [1])
                        except Exception:
                            pass
                        try:
                            self.stop_servo()
                        except Exception:
                            pass

        # Update command/feedback/torque peak/valley using latest (held) values
        def _pv_update(val, cur_peak, cur_valley):
            if cur_peak is None or val > cur_peak:
                cur_peak = val
            if cur_valley is None or val < cur_valley:
                cur_valley = val
            return cur_peak, cur_valley

        self._cmd_peak, self._cmd_valley = _pv_update(self.command_angle_deg, self._cmd_peak, self._cmd_valley)
        self._fb_peak, self._fb_valley = _pv_update(self.current_angle, self._fb_peak, self._fb_valley)
        self._torque_peak, self._torque_valley = _pv_update(self.current_torque, self._torque_peak, self._torque_valley)

        try:
            if self._cmd_peak is not None and self._cmd_valley is not None:
                self.cmd_pv_label.setText(f"{self._cmd_peak:.6f} / {self._cmd_valley:.6f}")
            if self._fb_peak is not None and self._fb_valley is not None:
                self.fb_pv_label.setText(f"{self._fb_peak:.6f} / {self._fb_valley:.6f}")
            if self._torque_peak is not None and self._torque_valley is not None:
                self.torque_pv_label.setText(f"{self._torque_peak:.6f} / {self._torque_valley:.6f}")
        except Exception:
            pass

        # Safety limits (optional)
        try:
            if (getattr(self, 'limits_enable_checkbox', None) and self.limits_enable_checkbox.isChecked()) and (not self._limit_tripped):
                a_lo = float(self.angle_low_spin.value())
                a_hi = float(self.angle_high_spin.value())
                t_lo = float(self.torque_low_spin.value())
                t_hi = float(self.torque_high_spin.value())

                angle_bad = (self.current_angle < a_lo) or (self.current_angle > a_hi)
                torque_bad = (self.current_torque < t_lo) or (self.current_torque > t_hi)

                if angle_bad or torque_bad:
                    self._limit_tripped = True
                    self.log(f"🛡️ LIMIT TRIP: angle={self.current_angle:.6f} ([{a_lo:.6f},{a_hi:.6f}]) torque={self.current_torque:.6f} ([{t_lo:.6f},{t_hi:.6f}])")
                    act = str(self.limit_action_combo.currentText())
                    if act == 'Motor Off':
                        try:
                            self.emergency_stop()
                        except Exception:
                            pass
                    else:
                        try:
                            self.stop_servo()
                        except Exception:
                            pass
        except Exception:
            pass

        # Cycle counting on rising edge of mission_done
        if mission_done and not self._last_mission_done:
            self._cycle_count += 1
            self.cycle_label.setText(f"Cycles: {self._cycle_count}")
            self.log(f"🏁 Mission Done rising edge → cycle={self._cycle_count}")

            # auto-stop on reaching target cycles
            try:
                self._target_cycles = int(self.target_cycles_spin.value())
            except Exception:
                self._target_cycles = 0
            if self._target_cycles > 0 and self._cycle_count >= self._target_cycles and not self._auto_stop_issued:
                self._auto_stop_issued = True
                self.log(f"✅ Target cycles reached ({self._cycle_count}/{self._target_cycles}) → stopping")
                try:
                    self._write_regs_fast(HR_TEST_DONE, [1])
                except Exception:
                    pass
                try:
                    self.stop_servo()
                except Exception:
                    pass

        self._last_mission_done = mission_done

        # Samples/plots are handled by _append_uniform_samples()

    def on_time_stop_changed(self, _value=None):
        try:
            self.enable_time_based_stop = bool(self.time_stop_cb.isChecked())
        except Exception:
            self.enable_time_based_stop = False

    def _compute_command_angle(self, t_s: float) -> float:
        try:
            mean_deg = float(self.target_mean_spin.value())
            amp_deg = max(MIN_TARGET_AMP_DEG, float(self.target_amp_spin.value()))
            phase_deg = float(self.target_phase_spin.value())
            freq_hz = float(self._equivalent_freq_hz())
        except Exception:
            mean_deg, amp_deg, phase_deg, freq_hz = 0.0, MIN_TARGET_AMP_DEG, 0.0, 0.0

        cm = str(getattr(self, 'control_mode', 'Angle'))
        fm = str(getattr(self, 'function_mode', 'Sine'))

        if cm != 'Angle':
            return 0.0

        w = 2.0 * math.pi * max(0.0, freq_hz)
        phi = (w * float(t_s)) + math.radians(float(phase_deg))
        if fm.lower().startswith('tri'):
            # Triangle wave [-1, +1] with period 2π, starting at 0 when phi=0.
            # Shape over one cycle: 0 → +1 → 0 → -1 → 0
            u = (phi / (2.0 * math.pi)) % 1.0
            if u < 0.25:
                tri = 4.0 * u
            elif u < 0.75:
                tri = 2.0 - 4.0 * u
            else:
                tri = -4.0 + 4.0 * u
            return float(mean_deg + amp_deg * tri)
        return float(mean_deg + amp_deg * math.sin(phi))

    def _equivalent_freq_hz(self) -> float:
        """Derive a waveform frequency from the operator's deg/s value.

        - Triangular: deg/s ~= 4*amp*freq
        - Sine: peak deg/s ~= amp*2π*freq
        """
        try:
            deg_s = float(self.speed_deg_s_spin.value())
        except Exception:
            deg_s = 0.0
        try:
            amp = max(MIN_TARGET_AMP_DEG, float(self.target_amp_spin.value()))
        except Exception:
            amp = MIN_TARGET_AMP_DEG

        deg_s = max(0.0, float(deg_s))
        amp = max(MIN_TARGET_AMP_DEG, float(amp))
        if deg_s <= 0.0:
            return 0.0

        fm = str(getattr(self, 'function_mode', 'Sine'))
        if fm.lower().startswith('tri'):
            return deg_s / (4.0 * amp)
        return deg_s / (2.0 * math.pi * amp)

    def _smooth_value(self, raw_val: float, prev_smooth: float, dt_s: float) -> float:
        """Apply exponential moving average (EMA) smoothing.
        
        alpha = 1 - exp(-dt / tau)
        smoothed = alpha * raw + (1 - alpha) * prev_smooth
        """
        tau_ms = float(getattr(self, '_plot_smooth_tau_ms', DEFAULT_PLOT_SMOOTH_TAU_MS))
        if tau_ms <= 0.0 or dt_s <= 0.0:
            return raw_val
        tau_s = tau_ms / 1000.0
        try:
            alpha = 1.0 - math.exp(-dt_s / tau_s)
        except Exception:
            alpha = 1.0
        return alpha * raw_val + (1.0 - alpha) * prev_smooth

    def _append_uniform_samples(self, elapsed_real_s: float, ts: datetime):
        """Append sample for each successful poll (real-time sampling).
        
        Changed from fixed-time-step to poll-based sampling for better data capture.
        Each successful Modbus read creates one sample with actual timestamp.
        """
        if len(self._samples) >= self._max_samples:
            return

        t_sample = elapsed_real_s
        cmd_angle = self._compute_command_angle(t_sample)
        self.command_angle_deg = float(cmd_angle)

        # Apply smoothing to angle and torque for plots
        enable_smooth = bool(getattr(self, '_plot_smooth_enabled', DEFAULT_ENABLE_PLOT_SMOOTHING))
        if enable_smooth:
            if not self._smooth_initialized:
                # Initialize filter state with first values
                self._smooth_angle = float(self.current_angle)
                self._smooth_torque = float(self.current_torque)
                self._smooth_initialized = True
                self._last_smooth_time = t_sample
            else:
                # Calculate dt since last smoothing update
                smooth_dt = t_sample - (self._last_smooth_time or 0.0)
                smooth_dt = max(0.0001, smooth_dt)  # Minimum 0.1ms
                self._smooth_angle = self._smooth_value(float(self.current_angle), self._smooth_angle, smooth_dt)
                self._smooth_torque = self._smooth_value(float(self.current_torque), self._smooth_torque, smooth_dt)
                self._last_smooth_time = t_sample
            plot_torque = self._smooth_torque
            plot_actual_angle = self._smooth_angle
        else:
            plot_torque = self.current_torque
            plot_actual_angle = self.current_angle

        row = {
            "timestamp": ts.isoformat(timespec='milliseconds'),
            "time_s": f"{t_sample:.6f}",
            "elapsed_s": f"{t_sample:.6f}",
            "cycle": self._cycle_count,
            "angle_deg": f"{self.current_angle:.6f}",
            "cmd_angle_deg": f"{self.command_angle_deg:.6f}",
            "analog_raw": self.current_analog,
            "current_mA": f"{self.current_ma:.3f}",
            "torque_Nm": f"{self.current_torque:.6f}",
            "status_bits": getattr(self, '_last_status_bits', 0) or 0,
            "home": 1 if (getattr(self, 'home_label', None) and 'ON' in self.home_label.text()) else 0,
            "servo_run": 1 if (getattr(self, 'servo_run_label', None) and 'ON' in self.servo_run_label.text()) else 0,
            "mission_done": 1 if (getattr(self, 'mission_done_label', None) and 'DONE' in self.mission_done_label.text()) else 0,
            "unit": self.unit_id if self.unit_id is not None else self.slave_id,
            "addr_offset": self.addr_offset,
        }
        self._samples.append(row)
        
        # Update sample count display
        try:
            self.sample_count_label.setText(str(len(self._samples)))
        except Exception:
            pass

        # Update Torque vs Angle plot (Torque vs Time is updated always in on_polled_data)
        try:
            # Use Command Angle or (smoothed) Actual Angle based on setting
            plot_angle = self.command_angle_deg if getattr(self, 'use_cmd_angle_for_plot', False) else plot_actual_angle
            self.plot_torque_angle.update_plot(plot_angle, plot_torque)
        except Exception:
            pass

        self._sample_index += 1
        self._last_sample_time_s = t_sample

        try:
            self.cmd_angle_label.setText(f"{self.command_angle_deg:.6f} °")
        except Exception:
            pass

    def on_speed_changed(self, value):
        try:
            raw = int(round(float(value)))
        except Exception:
            return
        # keep derived deg/s in sync
        try:
            self._update_speed_deg_s_from_pps()
        except Exception:
            pass
        if self._last_sent_speed_raw == raw:
            return
        self._pending_speed_raw = raw
        delay = int(self.write_delay_spin.value())
        try:
            self._speed_write_timer.stop()
            self._speed_write_timer.start(delay)
        except Exception:
            self._do_send_params()

    def on_targets_changed(self, _value):
        try:
            amp_val = float(self.target_amp_spin.value())
            if amp_val < MIN_TARGET_AMP_DEG:
                self.target_amp_spin.blockSignals(True)
                self.target_amp_spin.setValue(MIN_TARGET_AMP_DEG)
                self.target_amp_spin.blockSignals(False)
                amp_val = MIN_TARGET_AMP_DEG

            mean_raw = int(round(float(self.target_mean_spin.value()) * 100.0))
            amp_raw = int(round(float(amp_val) * 100.0))
            phase_raw = int(round(float(self.target_phase_spin.value()) * 100.0))
        except Exception:
            return
        # keep derived deg/s in sync
        try:
            self._update_speed_deg_s_from_pps()
        except Exception:
            pass
        pending = (mean_raw, amp_raw, phase_raw)
        if self._last_sent_targets_raw == pending:
            return
        self._pending_targets_raw = pending
        delay = int(self.write_delay_spin.value())
        try:
            self._targets_write_timer.stop()
            self._targets_write_timer.start(delay)
        except Exception:
            self._do_send_params()

    def _do_send_params(self):
        """Write speed + targets (addr5..8) with FC16 preferred."""
        if not self.connected:
            return

        try:
            speed_raw = self._pending_speed_raw
            if speed_raw is None:
                speed_raw = int(round(float(self.speed_hz_spin.value())))
        except Exception:
            speed_raw = None

        targets = self._pending_targets_raw
        if targets is None:
            try:
                targets = (
                    int(round(float(self.target_mean_spin.value()) * 100.0)),
                    int(round(max(MIN_TARGET_AMP_DEG, float(self.target_amp_spin.value())) * 100.0)),
                    int(round(float(self.target_phase_spin.value()) * 100.0)),
                )
            except Exception:
                targets = None

        if speed_raw is None or targets is None:
            return

        if self._last_sent_speed_raw == speed_raw and self._last_sent_targets_raw == targets:
            self._pending_speed_raw = None
            self._pending_targets_raw = None
            return

        # Log selected control/function mode to help operator/debugging
        try:
            cm = str(getattr(self, 'control_mode', 'Angle'))
            fm = str(getattr(self, 'function_mode', 'Sine'))
        except Exception:
            cm = 'Angle'
            fm = 'Sine'

        ok = self._write_regs(HR_SPEED_PPS, [speed_raw, targets[0], targets[1], targets[2]])
        if ok:
            self._last_sent_speed_raw = speed_raw
            self._last_sent_targets_raw = targets
            self.log(f"🔧 Wrote params: speed_raw={speed_raw} (DPLSY pps), mean/amp/phase={targets} | ControlMode={cm} Function={fm}")
        else:
            self.log("⚠️ Write params failed")

        self._pending_speed_raw = None
        self._pending_targets_raw = None

        # keep deg/s display in sync after any write
        try:
            self._update_speed_deg_s_from_pps()
        except Exception:
            pass
    
    # ========== SERVO CONTROL ==========
    
    def start_servo(self):
        """Write all parameters FIRST, then send START command.
        
        This ensures simulator/PLC has correct amp/mean/phase before motion begins.
        """
        if not self.connected:
            self.log("⚠️ Not connected - cannot start")
            return

        # 1) Write speed + mean/amp/phase parameters FIRST
        try:
            speed_raw = int(round(float(self.speed_hz_spin.value())))
            mean_raw = int(round(float(self.target_mean_spin.value()) * 100.0))
            amp_raw = int(round(max(MIN_TARGET_AMP_DEG, float(self.target_amp_spin.value())) * 100.0))
            phase_raw = int(round(float(self.target_phase_spin.value()) * 100.0))
            
            ok_params = self._write_regs_fast(HR_SPEED_PPS, [speed_raw, mean_raw, amp_raw, phase_raw])
            if ok_params:
                self.log(f"📝 Params written: speed={speed_raw}, mean={mean_raw}, amp={amp_raw}, phase={phase_raw}")
            else:
                self.log("⚠️ Failed to write parameters before START")
        except Exception as e:
            self.log(f"⚠️ Error writing params: {e}")

        # 2) Write target cycles and clear done flag
        try:
            self._target_cycles = int(self.target_cycles_spin.value())
        except Exception:
            self._target_cycles = 0
        try:
            self._write_regs_fast(HR_TARGET_CYCLES, [max(0, self._target_cycles)])
            self._write_regs_fast(HR_TEST_DONE, [0])
        except Exception:
            pass

        # 3) NOW send START command
        if self._write_regs_fast(HR_CONTROL, [CTRL_START]):
            self._reset_plot_session_state(reason=None)
            self.log(f"▶️ START sent (ctrl={CTRL_START})")
        else:
            self.log("⚠️ Failed to send START command")

    def _update_test_time_label(self):
        try:
            if not getattr(self, 'test_time_label', None):
                return
            if not self._test_running:
                self.test_time_label.setText("Test Time: 0.000 s")
                return
            # show normalized (fixed-step) time
            self.test_time_label.setText(f"Test Time: {float(getattr(self, '_last_sample_time_s', 0.0)):.3f} s")
        except Exception:
            pass

    def _update_speed_deg_s_from_pps(self):
        """Convert DPLSY pulses/s -> deg/s using pulses/rev and gear ratio."""
        if self._updating_speed:
            return
        try:
            pps = float(self.speed_hz_spin.value())
            ppd = float(self._pulses_per_degree())
            deg_s = (max(0.0, pps) / ppd) if ppd > 0 else 0.0
            self._updating_speed = True
            self.speed_deg_s_spin.setValue(float(deg_s))
        finally:
            self._updating_speed = False

    def _update_speed_pps_from_deg_s(self):
        if self._updating_speed:
            return
        try:
            deg_s = float(self.speed_deg_s_spin.value())
            ppd = float(self._pulses_per_degree())
            pps = max(0.0, deg_s) * ppd if ppd > 0 else 0.0
            self._updating_speed = True
            self.speed_hz_spin.setValue(float(pps))
        finally:
            self._updating_speed = False

    def on_speed_deg_s_changed(self, _value):
        """When operator edits deg/s, convert to DPLSY pulses/s and reuse existing write pipeline."""
        try:
            self._update_speed_pps_from_deg_s()
        except Exception:
            return

    def _pulses_per_degree(self) -> float:
        try:
            ppr = int(getattr(self, 'pulses_per_rev_spin', None).value()) if getattr(self, 'pulses_per_rev_spin', None) else int(getattr(self, 'pulses_per_rev', 0))
        except Exception:
            ppr = int(getattr(self, 'pulses_per_rev', 0))
        try:
            gr = float(getattr(self, 'gear_ratio_spin', None).value()) if getattr(self, 'gear_ratio_spin', None) else float(getattr(self, 'gear_ratio', 1.0))
        except Exception:
            gr = float(getattr(self, 'gear_ratio', 1.0))
        ppr = max(0, int(ppr))
        gr = max(0.0, float(gr))
        if ppr <= 0 or gr <= 0.0:
            return 0.0
        return (float(ppr) * float(gr)) / 360.0

    def _update_servo_settings_labels(self):
        try:
            ppd = float(self._pulses_per_degree())
            if getattr(self, 'pulses_per_deg_label', None):
                self.pulses_per_deg_label.setText(f"{ppd:.6f} pulses/deg")
        except Exception:
            try:
                self.pulses_per_deg_label.setText("-")
            except Exception:
                pass

    def on_servo_settings_changed(self, _value):
        # Cache values
        try:
            self.pulses_per_rev = int(self.pulses_per_rev_spin.value())
        except Exception:
            pass
        try:
            self.gear_ratio = float(self.gear_ratio_spin.value())
        except Exception:
            pass

        self._update_servo_settings_labels()
        # Recompute speed conversion without changing the commanded pps
        try:
            self._update_speed_deg_s_from_pps()
        except Exception:
            pass

    def on_analog_mode_changed(self, _value=None):
        """Update analog bipolar/max torque settings from UI."""
        try:
            self.analog_bipolar = bool(self.bipolar_checkbox.isChecked())
        except Exception:
            pass
        try:
            self.analog_max_torque_nm = float(self.max_torque_spin.value())
        except Exception:
            pass
        # Update info label
        try:
            if self.analog_bipolar:
                self.bipolar_info_label.setText("Bipolar: 2400=0, 800=-max, 4000=+max")
            else:
                self.bipolar_info_label.setText("NonBipolar: 800=0, 4000=+max (unipolar)")
        except Exception:
            pass

    def _default_config_path(self) -> str:
        try:
            return str((Path(__file__).resolve().parent / 'plc_master_config.json'))
        except Exception:
            return 'plc_master_config.json'

    def _default_master_config_path(self) -> str:
        try:
            return str((Path(__file__).resolve().parent / 'plc_master_full_config.json'))
        except Exception:
            return 'plc_master_full_config.json'

    def save_master_config(self, path: str, quiet: bool = False) -> bool:
        """Save full master UI/runtime config to JSON."""
        try:
            conn = {
                'port': (self.com_combo.currentData() or '').strip() if getattr(self, 'com_combo', None) else '',
                'baudrate': int(self.baud_combo.currentText()) if getattr(self, 'baud_combo', None) else int(getattr(self, 'baudrate', 115200)),
                'parity_ui': str(self.parity_combo.currentText()) if getattr(self, 'parity_combo', None) else 'None',
                'slave_id': int(self.slave_spin.value()) if getattr(self, 'slave_spin', None) else int(getattr(self, 'slave_id', 1)),
                'addr_offset': int(self.addr_offset_spin.value()) if getattr(self, 'addr_offset_spin', None) else int(getattr(self, 'addr_offset', 0)),
            }
        except Exception:
            conn = {}

        try:
            poll = {
                'poll_interval_ms': int(getattr(self, '_poll_interval_ms', DEFAULT_POLL_INTERVAL_MS)),
                'sample_interval_ms': int(getattr(self, '_sample_interval_ms', DEFAULT_SAMPLE_INTERVAL_MS)),
                'write_delay_ms': int(getattr(self, '_write_delay_ms', DEFAULT_WRITE_DELAY_MS)),
                'plot_every_n_polls': int(getattr(self, '_plot_every_n_polls', DEFAULT_PLOT_EVERY_N_POLLS)),
            }
        except Exception:
            poll = {}

        try:
            params = {
                'speed_pps': float(self.speed_hz_spin.value()) if getattr(self, 'speed_hz_spin', None) else float(getattr(self, 'speed_pps', 0.0)),
                'speed_deg_s': float(self.speed_deg_s_spin.value()) if getattr(self, 'speed_deg_s_spin', None) else float(getattr(self, 'speed_deg_s', 0.0)),
                'target_mean_deg': float(self.target_mean_spin.value()) if getattr(self, 'target_mean_spin', None) else 0.0,
                'target_amp_deg': float(self.target_amp_spin.value()) if getattr(self, 'target_amp_spin', None) else float(DEFAULT_TARGET_AMP_DEG),
                'target_phase_deg': float(self.target_phase_spin.value()) if getattr(self, 'target_phase_spin', None) else 0.0,
                'target_cycles': int(self.target_cycles_spin.value()) if getattr(self, 'target_cycles_spin', None) else int(getattr(self, '_target_cycles', 0)),
            }
        except Exception:
            params = {}

        try:
            servo = {
                'pulses_per_rev': int(getattr(self, 'pulses_per_rev', DEFAULT_PULSES_PER_REV)),
                'gear_ratio': float(getattr(self, 'gear_ratio', DEFAULT_GEAR_RATIO)),
            }
        except Exception:
            servo = {}

        try:
            analog = {
                'bipolar': bool(getattr(self, 'analog_bipolar', DEFAULT_ANALOG_BIPOLAR)),
                'max_torque_nm': float(getattr(self, 'analog_max_torque_nm', DEFAULT_ANALOG_MAX_TORQUE_NM)),
            }
        except Exception:
            analog = {}

        try:
            plot = {
                'use_cmd_angle_for_plot': bool(getattr(self, 'use_cmd_angle_for_plot', DEFAULT_USE_CMD_ANGLE_FOR_PLOT)),
                'smooth_enabled': bool(getattr(self, '_plot_smooth_enabled', DEFAULT_ENABLE_PLOT_SMOOTHING)),
                'smooth_tau_ms': float(getattr(self, '_plot_smooth_tau_ms', DEFAULT_PLOT_SMOOTH_TAU_MS)),
            }
        except Exception:
            plot = {}

        try:
            offsets = {
                'angle_zero_offset_deg': float(getattr(self, 'angle_zero_offset_deg', 0.0)),
                'torque_zero_offset_nm': float(getattr(self, 'torque_zero_offset_nm', 0.0)),
            }
        except Exception:
            offsets = {}

        try:
            stop_cfg = {
                'enable_time_based_stop': bool(getattr(self, 'enable_time_based_stop', DEFAULT_ENABLE_TIME_BASED_STOP)),
            }
        except Exception:
            stop_cfg = {}

        try:
            geo = None
            try:
                g = self.geometry()
                geo = [int(g.x()), int(g.y()), int(g.width()), int(g.height())]
            except Exception:
                geo = None
        except Exception:
            geo = None

        data = {
            'version': 1,
            'saved_at': datetime.now().isoformat(timespec='seconds'),
            'connection': conn,
            'poll': poll,
            'params': params,
            'servo': servo,
            'analog': analog,
            'plot': plot,
            'offsets': offsets,
            'stop': stop_cfg,
            'window_geometry': geo,
        }

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if not quiet:
                self.log(f"💾 Saved master config: {path}")
            return True
        except Exception as e:
            if not quiet:
                self.log(f"❌ Save master config failed: {e}")
            return False

    def load_master_config(self, path: str, quiet: bool = False) -> bool:
        """Load full master UI/runtime config from JSON."""
        try:
            if not Path(path).exists():
                return False
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            if not quiet:
                self.log(f"❌ Load master config failed: {e}")
            return False

        # Apply values (best-effort; do not assume widgets always exist)
        try:
            conn = dict(data.get('connection') or {})
            poll = dict(data.get('poll') or {})
            params = dict(data.get('params') or {})
            servo = dict(data.get('servo') or {})
            analog = dict(data.get('analog') or {})
            plot = dict(data.get('plot') or {})
            offsets = dict(data.get('offsets') or {})
            stop_cfg = dict(data.get('stop') or {})
        except Exception:
            conn = poll = params = servo = analog = plot = offsets = stop_cfg = {}

        # Connection widgets
        try:
            if getattr(self, 'baud_combo', None):
                # Always set if present; default to 115200
                self.baud_combo.setCurrentText(str(int(conn.get('baudrate', 115200))))
        except Exception:
            pass
        try:
            if getattr(self, 'parity_combo', None) and 'parity_ui' in conn:
                self.parity_combo.setCurrentText(str(conn.get('parity_ui', 'None')))
        except Exception:
            pass
        try:
            if getattr(self, 'slave_spin', None) and 'slave_id' in conn:
                self.slave_spin.setValue(int(conn.get('slave_id', 1)))
        except Exception:
            pass
        try:
            if getattr(self, 'addr_offset_spin', None) and 'addr_offset' in conn:
                self.addr_offset_spin.setValue(int(conn.get('addr_offset', 0)))
        except Exception:
            pass
        try:
            # Try to select COM port if it exists in list
            port_val = str(conn.get('port') or '').strip()
            if port_val and getattr(self, 'com_combo', None):
                for i in range(self.com_combo.count()):
                    if str(self.com_combo.itemData(i) or '').strip() == port_val:
                        self.com_combo.setCurrentIndex(i)
                        break
        except Exception:
            pass

        # Poll/throttle
        try:
            if 'poll_interval_ms' in poll:
                self._poll_interval_ms = int(poll.get('poll_interval_ms', DEFAULT_POLL_INTERVAL_MS))
                if getattr(self, 'poll_interval_spin', None):
                    self.poll_interval_spin.setValue(int(self._poll_interval_ms))
        except Exception:
            pass
        try:
            if 'sample_interval_ms' in poll:
                self._sample_interval_ms = int(poll.get('sample_interval_ms', DEFAULT_SAMPLE_INTERVAL_MS))
                if getattr(self, 'sample_interval_spin', None):
                    self.sample_interval_spin.setValue(int(self._sample_interval_ms))
                self._sample_dt_s = float(max(1, int(self._sample_interval_ms))) / 1000.0
        except Exception:
            pass
        try:
            if 'write_delay_ms' in poll:
                self._write_delay_ms = int(poll.get('write_delay_ms', DEFAULT_WRITE_DELAY_MS))
                if getattr(self, 'write_delay_spin', None):
                    self.write_delay_spin.setValue(int(self._write_delay_ms))
        except Exception:
            pass
        try:
            if 'plot_every_n_polls' in poll:
                self._plot_every_n_polls = int(poll.get('plot_every_n_polls', DEFAULT_PLOT_EVERY_N_POLLS))
        except Exception:
            pass

        # Servo settings
        try:
            if 'pulses_per_rev' in servo:
                self.pulses_per_rev = int(servo.get('pulses_per_rev', DEFAULT_PULSES_PER_REV))
                if getattr(self, 'pulses_per_rev_spin', None):
                    try:
                        self.pulses_per_rev_spin.blockSignals(True)
                        self.pulses_per_rev_spin.setValue(int(self.pulses_per_rev))
                    finally:
                        self.pulses_per_rev_spin.blockSignals(False)
        except Exception:
            pass
        try:
            if 'gear_ratio' in servo:
                self.gear_ratio = float(servo.get('gear_ratio', DEFAULT_GEAR_RATIO))
                if getattr(self, 'gear_ratio_spin', None):
                    try:
                        self.gear_ratio_spin.blockSignals(True)
                        self.gear_ratio_spin.setValue(float(self.gear_ratio))
                    finally:
                        self.gear_ratio_spin.blockSignals(False)
        except Exception:
            pass

        # Analog settings
        try:
            if 'bipolar' in analog:
                self.analog_bipolar = bool(analog.get('bipolar', DEFAULT_ANALOG_BIPOLAR))
                if getattr(self, 'bipolar_checkbox', None):
                    try:
                        self.bipolar_checkbox.blockSignals(True)
                        self.bipolar_checkbox.setChecked(bool(self.analog_bipolar))
                    finally:
                        self.bipolar_checkbox.blockSignals(False)
        except Exception:
            pass
        try:
            if 'max_torque_nm' in analog:
                self.analog_max_torque_nm = float(analog.get('max_torque_nm', DEFAULT_ANALOG_MAX_TORQUE_NM))
                if getattr(self, 'max_torque_spin', None):
                    try:
                        self.max_torque_spin.blockSignals(True)
                        self.max_torque_spin.setValue(float(self.analog_max_torque_nm))
                    finally:
                        self.max_torque_spin.blockSignals(False)
        except Exception:
            pass

        # Plot settings
        try:
            if 'use_cmd_angle_for_plot' in plot:
                self.use_cmd_angle_for_plot = bool(plot.get('use_cmd_angle_for_plot', DEFAULT_USE_CMD_ANGLE_FOR_PLOT))
                if getattr(self, 'use_cmd_angle_checkbox', None):
                    try:
                        self.use_cmd_angle_checkbox.blockSignals(True)
                        self.use_cmd_angle_checkbox.setChecked(bool(self.use_cmd_angle_for_plot))
                    finally:
                        self.use_cmd_angle_checkbox.blockSignals(False)
        except Exception:
            pass
        try:
            if 'smooth_enabled' in plot:
                self._plot_smooth_enabled = bool(plot.get('smooth_enabled', DEFAULT_ENABLE_PLOT_SMOOTHING))
                if getattr(self, 'plot_smooth_checkbox', None):
                    try:
                        self.plot_smooth_checkbox.blockSignals(True)
                        self.plot_smooth_checkbox.setChecked(bool(self._plot_smooth_enabled))
                    finally:
                        self.plot_smooth_checkbox.blockSignals(False)
        except Exception:
            pass
        try:
            if 'smooth_tau_ms' in plot:
                self._plot_smooth_tau_ms = float(plot.get('smooth_tau_ms', DEFAULT_PLOT_SMOOTH_TAU_MS))
                if getattr(self, 'plot_smooth_tau_spin', None):
                    try:
                        self.plot_smooth_tau_spin.blockSignals(True)
                        self.plot_smooth_tau_spin.setValue(int(round(self._plot_smooth_tau_ms)))
                    finally:
                        self.plot_smooth_tau_spin.blockSignals(False)
        except Exception:
            pass

        # Params
        try:
            if getattr(self, 'speed_hz_spin', None) and 'speed_pps' in params:
                try:
                    self.speed_hz_spin.blockSignals(True)
                    self.speed_hz_spin.setValue(float(params.get('speed_pps', 0.0)))
                finally:
                    self.speed_hz_spin.blockSignals(False)
        except Exception:
            pass
        try:
            if getattr(self, 'speed_deg_s_spin', None) and 'speed_deg_s' in params:
                try:
                    self.speed_deg_s_spin.blockSignals(True)
                    self.speed_deg_s_spin.setValue(float(params.get('speed_deg_s', 0.0)))
                finally:
                    self.speed_deg_s_spin.blockSignals(False)
        except Exception:
            pass
        try:
            if getattr(self, 'target_mean_spin', None) and 'target_mean_deg' in params:
                try:
                    self.target_mean_spin.blockSignals(True)
                    self.target_mean_spin.setValue(float(params.get('target_mean_deg', 0.0)))
                finally:
                    self.target_mean_spin.blockSignals(False)
        except Exception:
            pass
        try:
            if getattr(self, 'target_amp_spin', None) and 'target_amp_deg' in params:
                try:
                    self.target_amp_spin.blockSignals(True)
                    self.target_amp_spin.setValue(float(params.get('target_amp_deg', DEFAULT_TARGET_AMP_DEG)))
                finally:
                    self.target_amp_spin.blockSignals(False)
        except Exception:
            pass
        try:
            if getattr(self, 'target_phase_spin', None) and 'target_phase_deg' in params:
                try:
                    self.target_phase_spin.blockSignals(True)
                    self.target_phase_spin.setValue(float(params.get('target_phase_deg', 0.0)))
                finally:
                    self.target_phase_spin.blockSignals(False)
        except Exception:
            pass
        try:
            if getattr(self, 'target_cycles_spin', None) and 'target_cycles' in params:
                try:
                    self.target_cycles_spin.blockSignals(True)
                    self.target_cycles_spin.setValue(int(params.get('target_cycles', 0)))
                finally:
                    self.target_cycles_spin.blockSignals(False)
        except Exception:
            pass

        # Offsets
        try:
            if 'angle_zero_offset_deg' in offsets:
                self.angle_zero_offset_deg = float(offsets.get('angle_zero_offset_deg', 0.0))
        except Exception:
            pass
        try:
            if 'torque_zero_offset_nm' in offsets:
                self.torque_zero_offset_nm = float(offsets.get('torque_zero_offset_nm', 0.0))
        except Exception:
            pass

        # Stop behavior
        try:
            if 'enable_time_based_stop' in stop_cfg:
                self.enable_time_based_stop = bool(stop_cfg.get('enable_time_based_stop', DEFAULT_ENABLE_TIME_BASED_STOP))
                if getattr(self, 'time_stop_cb', None):
                    try:
                        self.time_stop_cb.blockSignals(True)
                        self.time_stop_cb.setChecked(bool(self.enable_time_based_stop))
                    finally:
                        self.time_stop_cb.blockSignals(False)
        except Exception:
            pass

        # Update dependent displays
        try:
            self._update_servo_settings_labels()
        except Exception:
            pass
        try:
            self._update_speed_deg_s_from_pps()
        except Exception:
            pass
        try:
            self.on_analog_mode_changed()
        except Exception:
            pass

        # Window geometry
        try:
            geo = data.get('window_geometry')
            if isinstance(geo, list) and len(geo) == 4:
                self.setGeometry(int(geo[0]), int(geo[1]), int(geo[2]), int(geo[3]))
        except Exception:
            pass

        # If connected, restart acquisition so new intervals take effect
        try:
            if bool(getattr(self, 'connected', False)):
                self._start_polling_thread()
        except Exception:
            pass

        if not quiet:
            self.log(f"📂 Loaded master config: {path}")
        return True

    def _menu_load_master_config(self):
        try:
            base_dir = str(Path(self._default_master_config_path()).parent)
            path, _ = QFileDialog.getOpenFileName(self, 'Load Master Config', base_dir, 'JSON (*.json);;All Files (*)')
        except Exception:
            path = ''
        if not path:
            return
        self.load_master_config(path, quiet=False)

    def _menu_save_master_config(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, 'Save Master Config', self._default_master_config_path(), 'JSON (*.json);;All Files (*)')
        except Exception:
            path = ''
        if not path:
            return
        if not str(path).lower().endswith('.json'):
            path = str(path) + '.json'
        self.save_master_config(path, quiet=False)

    def save_servo_config(self, path: str, quiet: bool = False) -> bool:
        data = {
            'pulses_per_rev': int(getattr(self, 'pulses_per_rev', 10000)),
            'gear_ratio': float(getattr(self, 'gear_ratio', 1.0)),
            'analog_bipolar': bool(getattr(self, 'analog_bipolar', DEFAULT_ANALOG_BIPOLAR)),
            'analog_max_torque_nm': float(getattr(self, 'analog_max_torque_nm', DEFAULT_ANALOG_MAX_TORQUE_NM)),
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if not quiet:
                self.log(f"💾 Saved servo config: {path}")
            return True
        except Exception as e:
            if not quiet:
                self.log(f"❌ Save servo config failed: {e}")
            return False

    def load_servo_config(self, path: str, quiet: bool = False) -> bool:
        try:
            if not Path(path).exists():
                return False
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            if not quiet:
                self.log(f"❌ Load servo config failed: {e}")
            return False

        try:
            if 'pulses_per_rev' in data:
                self.pulses_per_rev = int(data['pulses_per_rev'])
                if getattr(self, 'pulses_per_rev_spin', None):
                    try:
                        self.pulses_per_rev_spin.blockSignals(True)
                        self.pulses_per_rev_spin.setValue(int(self.pulses_per_rev))
                    finally:
                        self.pulses_per_rev_spin.blockSignals(False)
            if 'gear_ratio' in data:
                self.gear_ratio = float(data['gear_ratio'])
                if getattr(self, 'gear_ratio_spin', None):
                    try:
                        self.gear_ratio_spin.blockSignals(True)
                        self.gear_ratio_spin.setValue(float(self.gear_ratio))
                    finally:
                        self.gear_ratio_spin.blockSignals(False)
            if 'analog_bipolar' in data:
                self.analog_bipolar = bool(data['analog_bipolar'])
                if getattr(self, 'bipolar_checkbox', None):
                    try:
                        self.bipolar_checkbox.blockSignals(True)
                        self.bipolar_checkbox.setChecked(bool(self.analog_bipolar))
                    finally:
                        self.bipolar_checkbox.blockSignals(False)
            if 'analog_max_torque_nm' in data:
                self.analog_max_torque_nm = float(data['analog_max_torque_nm'])
                if getattr(self, 'max_torque_spin', None):
                    try:
                        self.max_torque_spin.blockSignals(True)
                        self.max_torque_spin.setValue(float(self.analog_max_torque_nm))
                    finally:
                        self.max_torque_spin.blockSignals(False)
        except Exception:
            pass

        self._update_servo_settings_labels()
        try:
            self._update_speed_deg_s_from_pps()
        except Exception:
            pass
        try:
            self.on_analog_mode_changed()
        except Exception:
            pass

        if not quiet:
            self.log(f"📂 Loaded servo config: {path}")
        return True

    def _menu_load_servo_config(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, 'Load Servo Config', str(Path(self._default_config_path()).parent), 'JSON (*.json);;All Files (*)')
        except Exception:
            path = ''
        if not path:
            return
        self.load_servo_config(path, quiet=False)

    def _menu_save_servo_config(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, 'Save Servo Config', self._default_config_path(), 'JSON (*.json);;All Files (*)')
        except Exception:
            path = ''
        if not path:
            return
        if not str(path).lower().endswith('.json'):
            path = str(path) + '.json'
        self.save_servo_config(path, quiet=False)

    def on_control_mode_changed(self, value):
        try:
            self.control_mode = str(value)
        except Exception:
            self.control_mode = 'Angle'

        # No longer need to force since only Angle is available

    def on_function_changed(self, value):
        try:
            self.function_mode = str(value)
        except Exception:
            self.function_mode = 'Triangular'

        # No longer need to force since only Triangular is available

    def zero_set_angle(self):
        """Set current feedback angle as 0°."""
        try:
            self.angle_zero_offset_deg = float(self.current_angle_raw)
            self.log(f"🧭 Zero Set Angle: offset={self.angle_zero_offset_deg:.6f}°")
        except Exception as e:
            self.log(f"⚠️ Zero Set Angle failed: {e}")

    def zero_set_torque(self):
        """Set current torque as 0 N·m (offset subtract)."""
        try:
            self.torque_zero_offset_nm = float(self.current_torque_raw)
            self.log(f"🧭 Zero Set Torque: offset={self.torque_zero_offset_nm:.6f} N·m")
        except Exception as e:
            self.log(f"⚠️ Zero Set Torque failed: {e}")

    def to_home_position(self):
        """Send HOME control to PLC/simulator without modifying UI parameters.

        This will instruct the simulator/PLC to force actual angle to 0° while
        preserving the operator-set Mean/Amp/Phase values in the UI.
        """
        try:
            # Only send CTRL_HOME; do not change target_mean/amp/phase in the UI.
            if self._write_regs_fast(HR_CONTROL, [CTRL_HOME]):
                self.log(f"🏠 To Home: HOME sent (ctrl={CTRL_HOME})")
            else:
                self.log("🏠 To Home: HOME ctrl send failed")
        except Exception as e:
            self.log(f"⚠️ To Home failed: {e}")

    def servo_reset(self):
        """Best-effort servo reset: send CLEAR (ctrl=0)."""
        try:
            self.reset_commands()
            self.log("🔄 Servo Reset: CLEAR sent")
        except Exception as e:
            self.log(f"⚠️ Servo Reset failed: {e}")
    
    def stop_servo(self):
        """Control register (addr 4) = 2"""
        if self._write_regs_fast(HR_CONTROL, [CTRL_STOP]):
            self._test_running = False
            self.log(f"⏹ STOP sent (ctrl={CTRL_STOP})")
    
    def emergency_stop(self):
        """Control register (addr 4) = 3"""
        if self._write_regs_fast(HR_CONTROL, [CTRL_ESTOP]):
            self._test_running = False
            self.log(f"🛑 ESTOP sent (ctrl={CTRL_ESTOP})")
    
    def reset_commands(self):
        """Clear control register (addr 4) = 0"""
        if self._write_regs_fast(HR_CONTROL, [CTRL_CLEAR]):
            self._test_running = False
            self.log(f"♻️ Control cleared (ctrl={CTRL_CLEAR})")
    
    def set_parameters(self):
        """Write params immediately (addr5..8)."""
        self._pending_speed_raw = int(round(float(self.speed_hz_spin.value())))
        self._pending_targets_raw = (
            int(round(float(self.target_mean_spin.value()) * 100.0)),
            int(round(max(MIN_TARGET_AMP_DEG, float(self.target_amp_spin.value())) * 100.0)),
            int(round(float(self.target_phase_spin.value()) * 100.0)),
        )
        self._do_send_params()
    
    def clear_plots(self):
        """Clear all plot data"""
        self.plot_torque_time.clear_plot()
        self.plot_torque_angle.clear_plot()
        # Reset rolling plot timeline
        self._plot_t0_monotonic = time.monotonic()
        self.start_time = datetime.now()
        self.log("🗑️ Plots cleared")

    def export_csv(self):
        """Export current samples in CTR DATA FORMAT #1 (Revision 2019.06.27)."""
        if not self._samples:
            self.log("⚠️ No samples to export")
            return

        fname = f"ctr_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        # Let user choose where to save the CSV (default filename suggested)
        try:
            options = QFileDialog.Options()
            try:
                # Prefer showing non-native dialog when available to avoid platform quirks
                options |= QFileDialog.DontUseNativeDialog
            except Exception:
                pass
            suggested = str(Path.home() / fname)
            file_dialog_path, _ = QFileDialog.getSaveFileName(self, "Save CTR CSV", suggested, "CSV Files (*.csv);;All Files (*)", options=options)
            if not file_dialog_path:
                self.log("ℹ️ CSV export cancelled by user")
                return
            out_path = Path(file_dialog_path)
        except Exception:
            out_dir = Path(__file__).resolve().parent
            out_path = out_dir / fname

        dt = float(getattr(self, '_sample_dt_s', 0.002))
        dt = max(1e-6, dt)

        # Build numeric rows: [Save, State, Cycle, Time, Command, Angle, Torque]
        rows = []
        for r in self._samples:
            try:
                t = float(r.get('time_s', 0.0))
            except Exception:
                t = 0.0
            # Sample file starts at dt, not 0
            if t <= 1e-12:
                continue

            try:
                cmd = float(r.get('cmd_angle_deg', 0.0))
            except Exception:
                cmd = 0.0
            try:
                ang = float(r.get('angle_deg', 0.0))
            except Exception:
                ang = 0.0
            try:
                tor = float(r.get('torque_Nm', 0.0))
            except Exception:
                tor = 0.0

            try:
                target_cycles = int(self.target_cycles_spin.value())
            except Exception:
                target_cycles = 0
            if target_cycles > 0:
                cyc = float(min(self._cycle_count + 1, target_cycles))
            else:
                cyc = float(max(1, self._cycle_count + 1))

            # Save=1, State=3 (matches sample)
            rows.append([1.0, 3.0, cyc, float(t), float(cmd), float(ang), float(tor)])

        if not rows:
            self.log("⚠️ No usable samples to export (need at least one sample at t>0)")
            return

        n = len(rows)

        def f6(x: float) -> str:
            try:
                return f"{float(x):.6f}"
            except Exception:
                return "0.000000"

        def _fmt_saved_date(dt_obj: datetime) -> str:
            # Match sample: 12/18/2025 9:22:08 AM (no leading zero on hour)
            try:
                s = dt_obj.strftime('%m/%d/%Y %I:%M:%S %p')
                return s.replace(' 0', ' ')
            except Exception:
                return dt_obj.isoformat(sep=' ', timespec='seconds')

        cols = list(zip(*rows))
        col_max = [max(c) for c in cols]
        col_min = [min(c) for c in cols]
        col_start = [c[0] for c in cols]
        col_stop = [c[-1] for c in cols]

        # Header values
        func = str(getattr(self, 'function_mode', 'Triangular')).upper()
        if func.startswith('TRI'):
            func = 'TRIANGULAR'
        elif func.startswith('SIN'):
            func = 'SINE'

        try:
            freq = float(self._equivalent_freq_hz())
        except Exception:
            freq = 0.0

        try:
            test_cycles = float(int(self.target_cycles_spin.value()))
        except Exception:
            test_cycles = float(max(1, self._cycle_count))
        if test_cycles <= 0:
            test_cycles = float(max(1, self._cycle_count))

        # SAMPLE INFO: keep same style as the example
        sample_info = f"///DEVELOPMENT/{datetime.now().strftime('%Y-%m-%d')}"

        try:
            with out_path.open('w', newline='', encoding='utf-8') as f:
                f.write("%===============================================================\n")
                f.write("%     CTR DATA FORMAT #1 (Revision 2019.06.27)\n")
                f.write("%     TITLE : Ball-Joint Torque Test Data File  \n")
                f.write("%===============================================================\n")
                f.write("BEGIN_OF_HEADER\n")
                f.write(f"SAVED_DATE = {_fmt_saved_date(datetime.now())}\n")
                f.write(f"SAMPLE INFO = {sample_info}\n")
                f.write(f"TEST FUNCTION = {func}\n")
                f.write(f"TEST FREQUENCY ={f6(freq).rstrip('0').rstrip('.') if abs(freq) < 1000 else f6(freq)}\n")
                f.write(f"TEST CYCLE ={f6(test_cycles)}\n")
                f.write("NUMBER_OF_COLUMNS = 7\n")
                f.write("COLUMN_NAME = [Save,State,Cycle,Time,Command,Angle,Torque]\n")
                f.write("COLUMN_UNIT = [NA,NA,Cycle,sec,Dgree,Dgree,N*m]\n")
                f.write(f"COLUMN_LENGTH = [{n},{n},{n},{n},{n},{n},{n}]\n")
                f.write(f"COLUMN_MAXIMUM = [{','.join(str(int(v)) if i < 3 else f6(v) for i, v in enumerate(col_max))}]\n")
                f.write(f"COLUMN_MINIMUM = [{','.join(str(int(v)) if i < 3 else f6(v) for i, v in enumerate(col_min))}]\n")
                f.write(f"COLUMN_START = [{','.join(str(int(v)) if i < 3 else f6(v) for i, v in enumerate(col_start))}]\n")
                f.write(f"COLUMN_STOP = [{','.join(str(int(v)) if i < 3 else f6(v) for i, v in enumerate(col_stop))}]\n")
                f.write(f"COLUMN_DELTA = [{','.join(f6(dt) for _ in range(7))}]\n")
                f.write("COLUMN_DELTA_UNIT = [sec,sec,sec,sec,sec,sec,sec]\n")
                f.write("END_OF_HEADER\n")

                for row in rows:
                    formatted = [
                        str(int(row[0])),  # Save
                        str(int(row[1])),  # State
                        str(int(row[2])),  # Cycle
                        f6(row[3]),  # Time
                        f6(row[4]),  # Command
                        f6(row[5]),  # Angle
                        f6(row[6]),  # Torque
                    ]
                    f.write(",".join(formatted) + "\n")

            self.log(f"💾 CSV exported (CTR FORMAT #1): {out_path}")
        except Exception as e:
            self.log(f"❌ CSV export failed: {e}")
    
    # ========== LOGGING ==========
    
    def log(self, message):
        """Add message to log (thread-safe)"""
        self.log_signal.emit(message)
    
    def append_log(self, message):
        """Append to log text box"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


def main():
    app = QApplication(sys.argv)
    window = PLCMasterSCADA()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()