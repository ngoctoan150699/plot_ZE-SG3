#!/usr/bin/env python3
"""
Torque Sensor Simulator – ZE-SG3 / DYJN-101 50Nm
==================================================
Mô phỏng cảm biến torque qua Modbus RTU trên cặp COM port ảo.

Yêu cầu:
  pip install pymodbus pyserial pyqt5 com0com (hoặc dùng com0com/VSPD tạo cặp port)

Cách dùng:
  1. Tạo cặp COM port ảo bằng com0com hoặc VSPD (VD: COM10 <-> COM11)
  2. Chạy simulator:  python torque_simulator.py
  3. Chọn COM port simulator (VD: COM10)
  4. Trong phần mềm chính (main.py), kết nối tới COM port còn lại (VD: COM11)
  5. Kéo slider để thay đổi giá trị torque
"""

import struct
import sys
import threading
import time
import logging
import math
import asyncio

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSlider, QSpinBox, QVBoxLayout, QWidget, QCheckBox,
    QGridLayout, QFrame, QTextEdit,
)

import serial.tools.list_ports

# ── Modbus Server ──
from pymodbus.server import ModbusSerialServer, ServerStop
from pymodbus.datastore import (
    ModbusDeviceContext as ModbusSlaveContext,
    ModbusServerContext,
    ModbusSimulatorContext,
)
from pymodbus.framer import FramerType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger("TorqueSimulator")


# =====================================================================
# REGISTER MAP (ZE-SG3 compatible)
# =====================================================================
# Holding Registers base-0 (Modbus 40001 = offset 0)
REG_MACHINE_ID        = 0
REG_FIRMWARE_REV      = 1
REG_MEASURE_UNIT      = 2
REG_MEASURE_TYPE      = 3
REG_ANALOG_OUT_TYPE   = 4
REG_DIO_TYPE          = 5
REG_CALIB_MODE        = 6
REG_ADDRESS           = 8
REG_BAUD              = 9
REG_PARITY            = 10
REG_CELL_SENS_HI      = 13
REG_CELL_SENS_LO      = 14
REG_CELL_FS_HI        = 15
REG_CELL_FS_LO        = 16
REG_STD_WEIGHT_HI     = 17
REG_STD_WEIGHT_LO     = 18
REG_DELTA_WEIGHT_HI   = 29
REG_DELTA_WEIGHT_LO   = 30
REG_DELTA_TIME        = 31
REG_ADC_SPS           = 34
REG_FILTER_LEVEL      = 42
REG_RESOLUTION_MODE   = 43
REG_ADC_16BIT_FILT    = 62
REG_NET_WEIGHT_HI     = 63
REG_NET_WEIGHT_LO     = 64
REG_GROSS_WEIGHT_HI   = 65
REG_GROSS_WEIGHT_LO   = 66
REG_TARE_WEIGHT_HI    = 67
REG_TARE_WEIGHT_LO    = 68
REG_INT_NET_HI        = 69
REG_INT_NET_LO        = 70
REG_INT_GROSS_HI      = 71
REG_INT_GROSS_LO      = 72
REG_INT_TARE_HI       = 73
REG_INT_TARE_LO       = 74
REG_FACTORY_TARE_HI   = 75
REG_FACTORY_TARE_LO   = 76
REG_STATUS            = 77
REG_COMMAND           = 79
REG_PIECES_NR         = 80
REG_MAX_NET_HI        = 81
REG_MAX_NET_LO        = 82
REG_MIN_NET_HI        = 83
REG_MIN_NET_LO        = 84

STATUS_BIT_STABLE     = 0x10
CMD_TARE              = 49914
CMD_TARE_RAM          = 49594
CMD_RESTART           = 43948
CMD_RESET_MAX         = 49151
CMD_RESET_MIN         = 45056


def float_to_regs(value: float):
    """Encode Python float → 2 × uint16 (Big-Endian)."""
    packed = struct.pack('>f', value)
    hi, lo = struct.unpack('>HH', packed)
    return hi, lo


def int32_to_regs(value: int):
    """Encode signed int32 → 2 × uint16 (Big-Endian)."""
    packed = struct.pack('>i', value)
    hi, lo = struct.unpack('>HH', packed)
    return hi, lo


# =====================================================================
# SIMULATOR GUI
# =====================================================================
class TorqueSimulatorWindow(QMainWindow):
    """Giao diện mô phỏng cảm biến Torque ZE-SG3."""

    sig_log = pyqtSignal(str)

    # ── Light-theme stylesheet ──
    STYLESHEET = """
    QMainWindow { background: #f5f5f5; }
    QGroupBox {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-top: 14px;
        padding: 12px;
        font-weight: bold;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
    QLabel { color: #333; }
    QPushButton {
        background: #e3f2fd;
        border: 1px solid #bbdefb;
        border-radius: 4px;
        padding: 6px 14px;
        color: #1565c0;
        font-weight: 500;
    }
    QPushButton:hover { background: #bbdefb; border-color: #1976d2; }
    QPushButton:pressed { background: #90caf9; }
    QPushButton#btn_start {
        background: #4CAF50; color: white; font-weight: bold; font-size: 11pt;
    }
    QPushButton#btn_start:hover { background: #388E3C; }
    QPushButton#btn_stop {
        background: #f44336; color: white; font-weight: bold; font-size: 11pt;
    }
    QPushButton#btn_stop:hover { background: #C62828; }
    QSlider::groove:horizontal {
        border: 1px solid #bbb;
        background: #e0e0e0;
        height: 8px;
        border-radius: 4px;
    }
    QSlider::handle:horizontal {
        background: #1976d2;
        border: 1px solid #1565c0;
        width: 20px;
        margin: -6px 0;
        border-radius: 10px;
    }
    QSlider::sub-page:horizontal { background: #64b5f6; border-radius: 4px; }
    QTextEdit { background: #fafafa; border: 1px solid #e0e0e0; font-family: Consolas; font-size: 9pt; }
    QComboBox { background: white; border: 1px solid #ccc; border-radius: 4px; padding: 4px 6px; }
    QSpinBox, QDoubleSpinBox { background: white; border: 1px solid #ccc; border-radius: 4px; padding: 4px; }
    """

    def __init__(self):
        super().__init__()

        # Internal state
        self._server_thread = None
        self._server_running = False
        self._server = None
        self._loop = None
        self._context = None
        self._slave_id = 1
        self._torque_value = 0.0
        self._tare_offset = 0.0
        self._max_net = 0.0
        self._min_net = 0.0
        self._noise_enabled = True
        self._noise_amplitude = 0.02
        self._sine_enabled = False
        self._sine_amplitude = 5.0
        self._sine_freq = 0.5

        self._build_ui()
        self.setStyleSheet(self.STYLESHEET)

        # Timer để cập nhật register liên tục
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_registers)
        self._update_timer.setInterval(50)  # 20 Hz

        # Timer kiểm tra command register
        self._cmd_timer = QTimer()
        self._cmd_timer.timeout.connect(self._check_commands)
        self._cmd_timer.setInterval(100)

        self.sig_log.connect(self._log)

    def _build_ui(self):
        self.setWindowTitle("🔧 ZE-SG3 Torque Sensor Simulator")
        self.setGeometry(100, 100, 600, 700)
        self.setMinimumSize(500, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── COM Port + Slave ID ──
        conn_grp = QGroupBox("🔌 Cấu hình kết nối")
        cg = QGridLayout()
        cg.setSpacing(8)

        cg.addWidget(QLabel("COM Port (Simulator):"), 0, 0)
        self.combo_port = QComboBox()
        self._scan_ports()
        cg.addWidget(self.combo_port, 0, 1)

        btn_scan = QPushButton("🔄 Quét lại")
        btn_scan.clicked.connect(self._scan_ports)
        cg.addWidget(btn_scan, 0, 2)

        cg.addWidget(QLabel("Baudrate:"), 1, 0)
        self.combo_baud = QComboBox()
        for b in [9600, 19200, 38400, 57600, 115200]:
            self.combo_baud.addItem(str(b), b)
        self.combo_baud.setCurrentText("115200")
        cg.addWidget(self.combo_baud, 1, 1)

        cg.addWidget(QLabel("Slave ID:"), 2, 0)
        self.spin_slave = QSpinBox()
        self.spin_slave.setRange(1, 247)
        self.spin_slave.setValue(1)
        cg.addWidget(self.spin_slave, 2, 1)

        conn_grp.setLayout(cg)
        layout.addWidget(conn_grp)

        # ── Start / Stop buttons ──
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶️ Bắt đầu mô phỏng")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.clicked.connect(self._start_server)
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ Dừng mô phỏng")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_server)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        # ── Torque Control ──
        torque_grp = QGroupBox("⚡ Điều khiển Torque (Nm)")
        tg = QVBoxLayout()

        # Slider
        self.slider_torque = QSlider(Qt.Horizontal)
        self.slider_torque.setRange(-5000, 5000)  # -50.00 Nm to 50.00 Nm (x100)
        self.slider_torque.setValue(0)
        self.slider_torque.setTickPosition(QSlider.TicksBelow)
        self.slider_torque.setTickInterval(500)
        self.slider_torque.valueChanged.connect(self._on_slider_changed)
        tg.addWidget(self.slider_torque)

        # Value display + spin
        val_row = QHBoxLayout()
        self.lbl_torque = QLabel("0.00 Nm")
        self.lbl_torque.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.lbl_torque.setAlignment(Qt.AlignCenter)
        self.lbl_torque.setStyleSheet("color: #1976d2;")
        val_row.addWidget(self.lbl_torque, stretch=1)

        spin_col = QVBoxLayout()
        spin_col.addWidget(QLabel("Giá trị chính xác:"))
        self.spin_torque = QDoubleSpinBox()
        self.spin_torque.setRange(-50.0, 50.0)
        self.spin_torque.setDecimals(2)
        self.spin_torque.setSingleStep(0.1)
        self.spin_torque.setSuffix(" Nm")
        self.spin_torque.setValue(0.0)
        self.spin_torque.valueChanged.connect(self._on_spin_changed)
        spin_col.addWidget(self.spin_torque)

        btn_zero = QPushButton("⚖️ Reset về 0")
        btn_zero.clicked.connect(self._reset_torque)
        spin_col.addWidget(btn_zero)
        val_row.addLayout(spin_col)
        tg.addLayout(val_row)

        torque_grp.setLayout(tg)
        layout.addWidget(torque_grp)

        # ── Simulation Effects ──
        effect_grp = QGroupBox("🎛️ Hiệu ứng mô phỏng")
        eg = QGridLayout()
        eg.setSpacing(6)

        self.chk_noise = QCheckBox("Thêm nhiễu ngẫu nhiên")
        self.chk_noise.setChecked(True)
        self.chk_noise.toggled.connect(lambda v: setattr(self, '_noise_enabled', v))
        eg.addWidget(self.chk_noise, 0, 0)

        eg.addWidget(QLabel("Biên độ nhiễu (Nm):"), 0, 1)
        self.spin_noise = QDoubleSpinBox()
        self.spin_noise.setRange(0.001, 1.0)
        self.spin_noise.setDecimals(3)
        self.spin_noise.setValue(0.02)
        self.spin_noise.valueChanged.connect(lambda v: setattr(self, '_noise_amplitude', v))
        eg.addWidget(self.spin_noise, 0, 2)

        self.chk_sine = QCheckBox("Sóng sin tự động")
        self.chk_sine.setChecked(False)
        self.chk_sine.toggled.connect(lambda v: setattr(self, '_sine_enabled', v))
        eg.addWidget(self.chk_sine, 1, 0)

        eg.addWidget(QLabel("Biên độ (Nm):"), 1, 1)
        self.spin_sine_amp = QDoubleSpinBox()
        self.spin_sine_amp.setRange(0.1, 50.0)
        self.spin_sine_amp.setValue(5.0)
        self.spin_sine_amp.valueChanged.connect(lambda v: setattr(self, '_sine_amplitude', v))
        eg.addWidget(self.spin_sine_amp, 1, 2)

        eg.addWidget(QLabel("Tần số (Hz):"), 2, 1)
        self.spin_sine_freq = QDoubleSpinBox()
        self.spin_sine_freq.setRange(0.01, 10.0)
        self.spin_sine_freq.setDecimals(2)
        self.spin_sine_freq.setValue(0.5)
        self.spin_sine_freq.valueChanged.connect(lambda v: setattr(self, '_sine_freq', v))
        eg.addWidget(self.spin_sine_freq, 2, 2)

        effect_grp.setLayout(eg)
        layout.addWidget(effect_grp)

        # ── Status / Log ──
        log_grp = QGroupBox("📋 Log")
        lg = QVBoxLayout()
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(120)
        lg.addWidget(self.log_box)
        log_grp.setLayout(lg)
        layout.addWidget(log_grp)

        # Status bar
        self.lbl_status = QLabel("⚪ Chưa khởi động")
        self.lbl_status.setStyleSheet("color: #757575; font-weight: bold; padding: 4px;")
        layout.addWidget(self.lbl_status)

    # ── Port scanning ──
    def _scan_ports(self):
        self.combo_port.clear()
        ports = serial.tools.list_ports.comports()
        for p in sorted(ports, key=lambda x: x.device):
            self.combo_port.addItem(f"{p.device} – {p.description}", p.device)
        if self.combo_port.count() == 0:
            self.combo_port.addItem("Không tìm thấy COM port", "")

    # ── Slider / Spin sync ──
    def _on_slider_changed(self, val):
        self._torque_value = val / 100.0
        self.spin_torque.blockSignals(True)
        self.spin_torque.setValue(self._torque_value)
        self.spin_torque.blockSignals(False)
        self._update_display()

    def _on_spin_changed(self, val):
        self._torque_value = val
        self.slider_torque.blockSignals(True)
        self.slider_torque.setValue(int(val * 100))
        self.slider_torque.blockSignals(False)
        self._update_display()

    def _reset_torque(self):
        self._torque_value = 0.0
        self.slider_torque.setValue(0)
        self.spin_torque.setValue(0.0)
        self._update_display()

    def _update_display(self):
        v = self._torque_value
        color = "#4CAF50" if abs(v) < 10 else ("#FF9800" if abs(v) < 40 else "#f44336")
        self.lbl_torque.setText(f"{v:.2f} Nm")
        self.lbl_torque.setStyleSheet(f"color: {color};")

    def _context_set_values(self, address: int, values):
        """Write holding registers through the server context across pymodbus versions."""
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._context.async_setValues(self._slave_id, 3, address, values),
                self._loop,
            )
            future.result(timeout=1)
        else:
            asyncio.run(self._context.async_setValues(self._slave_id, 3, address, values))

    def _context_get_values(self, address: int, count: int = 1):
        """Read holding registers through the server context across pymodbus versions."""
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._context.async_getValues(self._slave_id, 3, address, count),
                self._loop,
            )
            return future.result(timeout=1)
        return asyncio.run(self._context.async_getValues(self._slave_id, 3, address, count))

    def _create_datastore(self):
        """Tạo Modbus datastore với register map tương thích ZE-SG3."""
        # pymodbus 3.13 deprecates direct DataBlock read/write methods.
        # Use ModbusSimulatorContext so server requests and GUI updates share
        # the same register array via async_getValues/async_setValues.
        config = {
            "setup": {
                "co size": 0,
                "di size": 0,
                "ir size": 255,
                "hr size": 255,
                "shared blocks": True,
                "type exception": False,
                "defaults": {
                    "value": {
                        "bits": 0,
                        "uint16": 0,
                        "uint32": 0,
                        "float32": 0,
                        "string": "",
                    },
                    "action": {
                        "bits": None,
                        "uint16": None,
                        "uint32": None,
                        "float32": None,
                        "string": None,
                    },
                },
            },
            "invalid": [],
            "write": [[0, 254]],
            "bits": [],
            "uint16": [{"addr": [0, 254], "value": 0}],
            "uint32": [],
            "float32": [],
            "string": [],
            "repeat": [],
        }
        simulator = ModbusSimulatorContext(config, custom_actions=None)
        context = ModbusServerContext(devices={self._slave_id: simulator}, single=False)

        def _set_init(reg, vals):
            asyncio.run(context.async_setValues(self._slave_id, 3, reg + 1, vals))

        _set_init(REG_MACHINE_ID, [0x5A53])
        _set_init(REG_FIRMWARE_REV, [0x0100])
        _set_init(REG_MEASURE_UNIT, [8])
        _set_init(REG_MEASURE_TYPE, [0])
        _set_init(REG_CALIB_MODE, [0])
        _set_init(REG_ADDRESS, [self._slave_id])
        _set_init(REG_BAUD, [7])
        _set_init(REG_PARITY, [0])
        _set_init(REG_FILTER_LEVEL, [3])
        _set_init(REG_RESOLUTION_MODE, [0])
        _set_init(REG_ADC_SPS, [3])
        _set_init(REG_DELTA_TIME, [10])

        # Float32 defaults
        sens_hi, sens_lo = float_to_regs(1.9880)
        _set_init(REG_CELL_SENS_HI, [sens_hi, sens_lo])
        fs_hi, fs_lo = float_to_regs(49.70)
        _set_init(REG_CELL_FS_HI, [fs_hi, fs_lo])

        # Status: stable
        _set_init(REG_STATUS, [STATUS_BIT_STABLE])

        return context

    def _start_server(self):
        port = self.combo_port.currentData()
        if not port:
            self._log("❌ Chưa chọn COM port"); return

        self._slave_id = self.spin_slave.value()
        baudrate = self.combo_baud.currentData()
        self._tare_offset = 0.0
        self._max_net = 0.0
        self._min_net = 0.0

        self._context = self._create_datastore()

        self._server_running = True
        self._server_thread = threading.Thread(
            target=self._run_server,
            args=(port, baudrate),
            daemon=True,
            name="ModbusServer"
        )
        self._server_thread.start()

        self._update_timer.start()
        self._cmd_timer.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.combo_port.setEnabled(False)
        self.combo_baud.setEnabled(False)
        self.spin_slave.setEnabled(False)

        self.lbl_status.setText(f"🟢 Đang mô phỏng trên {port} @ {baudrate} bps (Slave {self._slave_id})")
        self.lbl_status.setStyleSheet("color: #388E3C; font-weight: bold; padding: 4px;")
        self._log(f"✅ Server Modbus RTU đã khởi động trên {port} @ {baudrate} bps, Slave ID = {self._slave_id}")
        self._log(f"💡 Trong phần mềm chính, kết nối tới COM port kia trong cặp ảo")

    def _run_server(self, port, baudrate):
        """Chạy Modbus serial server trong event loop riêng (daemon thread).

        ModbusSerialServer phải được khởi tạo bên trong một coroutine
        vì nó gọi `asyncio.get_running_loop()` trong __init__.
        """
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def _server_coro():
                try:
                    # Tạo server bên trong event loop đang chạy
                    self._server = ModbusSerialServer(
                        self._context,
                        framer=FramerType.RTU,
                        port=port,
                        baudrate=baudrate,
                        parity='N',
                        stopbits=1,
                        bytesize=8,
                        timeout=1,
                    )
                    self.sig_log.emit(f"🔗 Modbus server đã tạo, đang lắng nghe trên {port}...")
                    await self._server.serve_forever()
                except asyncio.CancelledError:
                    # graceful cancellation
                    pass

            self._loop.run_until_complete(_server_coro())
        except Exception as e:
            self.sig_log.emit(f"❌ Lỗi server: {e}")
            import traceback
            self.sig_log.emit(traceback.format_exc())
        finally:
            try:
                if self._loop and not self._loop.is_closed():
                    self._loop.close()
            except Exception:
                pass
            self._loop = None
            self._server = None

    def _stop_server(self):
        self._server_running = False
        self._update_timer.stop()
        self._cmd_timer.stop()

        # Gracefully stop the Modbus server
        if self._loop:
            try:
                # ServerStop is a synchronous helper that schedules async stop
                ServerStop()
            except Exception as e:
                logger.warning(f"Stop server error: {e}")

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.combo_port.setEnabled(True)
        self.combo_baud.setEnabled(True)
        self.spin_slave.setEnabled(True)

        self.lbl_status.setText("⚪ Đã dừng mô phỏng")
        self.lbl_status.setStyleSheet("color: #757575; font-weight: bold; padding: 4px;")
        self._log("⏹ Server đã dừng")

    def _update_registers(self):
        """Cập nhật giá trị torque vào Modbus registers (gọi mỗi 50ms)."""
        if not self._context:
            return

        # Tính giá trị torque hiện tại
        base = self._torque_value

        # Sine wave
        if self._sine_enabled:
            t = time.time()
            base = self._sine_amplitude * math.sin(2 * math.pi * self._sine_freq * t)
            # Cập nhật slider/display
            self.slider_torque.blockSignals(True)
            self.slider_torque.setValue(int(base * 100))
            self.slider_torque.blockSignals(False)
            self.spin_torque.blockSignals(True)
            self.spin_torque.setValue(base)
            self.spin_torque.blockSignals(False)
            self._torque_value = base
            self._update_display()

        # Noise
        noise = 0.0
        if self._noise_enabled:
            import random
            noise = random.gauss(0, self._noise_amplitude)

        gross = base + noise
        net = gross - self._tare_offset

        # Track min/max
        if net > self._max_net:
            self._max_net = net
        if net < self._min_net:
            self._min_net = net

        tare = self._tare_offset

        # Int32 versions (x1000 for milli-Nm precision)
        int_net = int(net * 1000)
        int_gross = int(gross * 1000)
        int_tare = int(tare * 1000)

        # Encode all
        def _set_float(reg, value):
            hi, lo = float_to_regs(value)
            self._context_set_values(reg + 1, [hi, lo])

        def _set_int32(reg, value):
            hi, lo = int32_to_regs(value)
            self._context_set_values(reg + 1, [hi, lo])

        _set_float(REG_NET_WEIGHT_HI, net)
        _set_float(REG_GROSS_WEIGHT_HI, gross)
        _set_float(REG_TARE_WEIGHT_HI, tare)
        _set_int32(REG_INT_NET_HI, int_net)
        _set_int32(REG_INT_GROSS_HI, int_gross)
        _set_int32(REG_INT_TARE_HI, int_tare)
        _set_float(REG_MAX_NET_HI, self._max_net)
        _set_float(REG_MIN_NET_HI, self._min_net)

        self._context_set_values(REG_STATUS + 1, [STATUS_BIT_STABLE])

    def _check_commands(self):
        """Kiểm tra Command Register để phản hồi lệnh từ phần mềm chính."""
        if not self._context:
            return

        cmd_vals = self._context_get_values(REG_COMMAND + 1, count=1)
        if not cmd_vals or cmd_vals[0] == 0:
            return
        
        cmd_val = cmd_vals[0]

        # Xử lý lệnh
        if cmd_val == CMD_TARE or cmd_val == CMD_TARE_RAM:
            self._tare_offset = self._torque_value
            self._log(f"⚖️ Tare thực hiện: offset = {self._tare_offset:.3f} Nm")
        elif cmd_val == CMD_RESTART:
            self._tare_offset = 0.0
            self._max_net = 0.0
            self._min_net = 0.0
            self._log("🔄 Restart: Reset tất cả offset")
        elif cmd_val == CMD_RESET_MAX:
            self._max_net = self._torque_value - self._tare_offset
            self._log("📊 Reset Max Net Weight")
        elif cmd_val == CMD_RESET_MIN:
            self._min_net = self._torque_value - self._tare_offset
            self._log("📊 Reset Min Net Weight")
        else:
            self._log(f"📩 Nhận lệnh: {cmd_val}")

        self._context_set_values(REG_COMMAND + 1, [0])

    def _log(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")

    def closeEvent(self, event):
        self._stop_server()
        super().closeEvent(event)


# =====================================================================
# MAIN
# =====================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ZE-SG3 Torque Simulator")

    window = TorqueSimulatorWindow()
    window.show()

    logger.info("Torque Simulator đã khởi động")
    result = app.exec_()
    sys.exit(result)


if __name__ == "__main__":
    main()
