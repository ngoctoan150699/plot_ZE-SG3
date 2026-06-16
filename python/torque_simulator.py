#!/usr/bin/env python3
"""Integrated ZE-SG3 Torque TCP/IP + PLC Modbus RTU simulator.

Hai kênh Modbus mô phỏng cùng lúc:
- TCP/IP: ZE-SG3 / cảm biến lực torque, Slave ID 1.
- RTU/COM: PLC/servo controller D100..D135, Slave ID 2.
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
import struct
import sys
import threading
import time
from dataclasses import dataclass, field

import serial.tools.list_ports
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock
from pymodbus.server.sync import ModbusSerialServer, ModbusTcpServer
from pymodbus.transaction import ModbusRtuFramer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("IntegratedSimulator")

# ZE-SG3 holding register offsets.
REG_MACHINE_ID = 0
REG_FIRMWARE_REV = 1
REG_MEASURE_UNIT = 2
REG_MEASURE_TYPE = 3
REG_CALIB_MODE = 6
REG_ADDRESS = 8
REG_BAUD = 9
REG_PARITY = 10
REG_CELL_SENS_HI = 13
REG_CELL_FS_HI = 15
REG_DELTA_TIME = 31
REG_ADC_SPS = 34
REG_FILTER_LEVEL = 42
REG_RESOLUTION_MODE = 43
REG_NET_WEIGHT_HI = 63
REG_GROSS_WEIGHT_HI = 65
REG_TARE_WEIGHT_HI = 67
REG_INT_NET_HI = 69
REG_INT_GROSS_HI = 71
REG_INT_TARE_HI = 73
REG_STATUS = 77
REG_COMMAND = 79
REG_MAX_NET_HI = 81
REG_MIN_NET_HI = 83
STATUS_BIT_STABLE = 0x10
CMD_TARE = 49914
CMD_TARE_RAM = 49594
CMD_RESTART = 43948
CMD_RESET_MAX = 49151
CMD_RESET_MIN = 45056

# PLC D100..D135 offsets.
PLC_D100_CMD_WORD = 100
PLC_D101_MODE = 101
PLC_D102_POS_ANGLE_X100 = 102
PLC_D103_NEG_ANGLE_X100 = 103
PLC_D104_SPEED_X100 = 104
PLC_D105_CYCLE_SET = 105
PLC_D106_WINDOW_PERCENT = 106
PLC_D107_PART_SELECT = 107
PLC_D108_TORQUE_TYPE = 108
PLC_D109_RESET_FAULT = 109
PLC_D110_JOG_PLUS = 110
PLC_D111_JOG_MINUS = 111
PLC_D112_HOME_CMD = 112
PLC_D120_STATUS_WORD = 120
PLC_D121_CURRENT_MODE = 121
PLC_D122_CURRENT_PHASE = 122
PLC_D123_CURRENT_CYCLE = 123
PLC_D124_CURRENT_ANGLE_X100 = 124
PLC_D125_TARGET_ANGLE_X100 = 125
PLC_D126_CURRENT_SPEED_X100 = 126
PLC_D127_SERVO_PULSE_LOW = 127
PLC_D128_SERVO_PULSE_HIGH = 128
PLC_D129_ERROR_CODE = 129
PLC_D130_DATA_VALID = 130
PLC_D131_RECORD_ENABLE = 131
PLC_D132_CYLINDER_STATUS = 132
PLC_D133_SERVO_ON_STATUS = 133
PLC_D134_TEST_DONE = 134
PLC_D135_SAMPLE_INDEX = 135

CMD_START_RUN = 1 << 0
CMD_STOP_RUN = 1 << 1
CMD_START_RECORD = 1 << 2
CMD_STOP_RECORD = 1 << 3
CMD_CYLINDER_TOGGLE = 1 << 4
CMD_SERVO_ON = 1 << 5
CMD_ABORT = 1 << 6
CMD_CLEAR_DONE = 1 << 7

ST_RUN = 1 << 0
ST_SERVO = 1 << 1
ST_CLAMP = 1 << 2
ST_TEST = 1 << 3
ST_RECORD = 1 << 4
ST_VALID = 1 << 5
ST_DONE = 1 << 6
ST_FAULT = 1 << 7

MODE_MANUAL = 0
MODE_BREAKAWAY = 1
MODE_OPERATING = 2
TORQUE_ID = 1
PLC_ID = 2
UINT16 = 0xFFFF


def u16(value: int) -> int:
    return value & UINT16


def i16(value: int) -> int:
    value = value & UINT16
    return value - 0x10000 if value & 0x8000 else value


def float_regs(value: float) -> list[int]:
    return list(struct.unpack(">HH", struct.pack(">f", value)))


def int32_regs(value: int) -> list[int]:
    return list(struct.unpack(">HH", struct.pack(">i", value)))


def sim_context(hr_size: int = 256) -> ModbusSlaveContext:
    return ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0] * hr_size),
        co=ModbusSequentialDataBlock(0, [0] * hr_size),
        hr=ModbusSequentialDataBlock(0, [0] * hr_size),
        ir=ModbusSequentialDataBlock(0, [0] * hr_size),
        zero_mode=True
    )


@dataclass
class PlantState:
    run: bool = False
    servo_on: bool = False
    clamped: bool = False
    test_running: bool = False
    record_enable: bool = False
    data_valid: bool = False
    done: bool = False
    fault_code: int = 0
    mode: int = MODE_MANUAL
    phase: int = 0
    cycle: int = 0
    sample_index: int = 0
    angle_deg: float = 0.0
    target_deg: float = 0.0
    velocity_deg_s: float = 0.0
    torque_nm: float = 0.0
    tare_offset: float = 0.0
    max_net: float = 0.0
    min_net: float = 0.0
    settle_until: float = 0.0
    op_target_positive: bool = True
    last_cmd_word: int = 0
    last_update: float = field(default_factory=time.monotonic)


class IntegratedSimulatorWindow(QMainWindow):
    sig_log: pyqtSignal = pyqtSignal(str)

    STYLESHEET = """
    QGroupBox { margin-top: 10px; padding: 8px; font-weight: normal; }
    QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px; }
    QPushButton { padding: 5px 10px; }
    QTextEdit { font-family: Consolas; font-size: 9pt; }
    """

    def __init__(self):
        super().__init__()
        self._context: ModbusServerContext | None = None
        self._server = None
        self._plc_server = None
        self._loop = None
        self._thread = None
        self._state = PlantState()
        self._auto_torque = True
        self._manual_torque = 0.0
        self._noise_nm = 0.025
        self._ui_tick_count = 0
        self._build_ui()
        self.setStyleSheet(self.STYLESHEET)
        self._scan_ports()
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._tick)
        self._cmd_timer = QTimer(self)
        self._cmd_timer.setInterval(40)
        self._cmd_timer.timeout.connect(self._scan_commands)
        self.sig_log.connect(self._log)

    def _build_ui(self):
        self.setWindowTitle("Mô phỏng ZE-SG3 TCP/IP + PLC RTU (Torque ID 1, PLC ID 2)")
        self.setGeometry(80, 60, 860, 760)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        conn = QGroupBox("Kết nối mô phỏng")
        grid = QGridLayout(conn)
        grid.addWidget(QLabel("Torque TCP IP lắng nghe:"), 0, 0)
        self.edit_host = QLineEdit("0.0.0.0")
        self.edit_host.setPlaceholderText("0.0.0.0 hoặc 127.0.0.1")
        grid.addWidget(self.edit_host, 0, 1)
        grid.addWidget(QLabel("Torque TCP Port:"), 1, 0)
        self.spin_tcp_port = QSpinBox()
        self.spin_tcp_port.setRange(1, 65535)
        self.spin_tcp_port.setValue(5020)
        grid.addWidget(self.spin_tcp_port, 1, 1)
        grid.addWidget(QLabel("PLC RTU COM:"), 2, 0)
        self.combo_port = QComboBox()
        grid.addWidget(self.combo_port, 2, 1)
        btn_scan = QPushButton("Quét COM")
        btn_scan.clicked.connect(self._scan_ports)
        grid.addWidget(btn_scan, 2, 2)
        grid.addWidget(QLabel("PLC RTU Baudrate:"), 3, 0)
        self.combo_baud = QComboBox()
        for baud in [9600, 19200, 38400, 57600, 115200]:
            self.combo_baud.addItem(str(baud), baud)
        self.combo_baud.setCurrentText("115200")
        grid.addWidget(self.combo_baud, 3, 1)
        self.lbl_ids = QLabel("Torque/cảm biến lực: TCP Slave ID 1 | PLC: RTU Slave ID 2 | 8N1")
        grid.addWidget(self.lbl_ids, 4, 0, 1, 3)
        layout.addWidget(conn)

        row = QHBoxLayout()
        self.btn_start = QPushButton("Bắt đầu mô phỏng")
        self.btn_start.setObjectName("start")
        self.btn_start.clicked.connect(self._start_server)
        row.addWidget(self.btn_start)
        self.btn_stop = QPushButton("Dừng mô phỏng")
        self.btn_stop.setObjectName("stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_server)
        row.addWidget(self.btn_stop)
        layout.addLayout(row)

        machine = QGroupBox("Trạng thái máy")
        mg = QGridLayout(machine)
        self.lamps = {}
        for idx, name in enumerate(["RUN", "SERVO", "CLAMP", "RECORD", "VALID", "DONE", "FAULT"]):
            lbl = QLabel(f"{name}: OFF")
            self.lamps[name] = lbl
            mg.addWidget(lbl, idx // 4, idx % 4)
        self.lbl_motion = QLabel("Servo: DỪNG | Góc 0.00° | Đích 0.00° | Tốc độ 0.00°/s")
        mg.addWidget(self.lbl_motion, 2, 0, 1, 4)
        self.lbl_cylinder = QLabel("Xi lanh: NHẢ | Kẹp phôi: KHÔNG")
        mg.addWidget(self.lbl_cylinder, 3, 0, 1, 2)
        self.lbl_phase = QLabel("PLC: Bước=0, Chế độ=0, Chu kỳ=0, Lỗi D129=0")
        mg.addWidget(self.lbl_phase, 3, 2, 1, 2)
        layout.addWidget(machine)

        torque = QGroupBox("Torque ZE-SG3")
        tg = QGridLayout(torque)
        self.lbl_torque = QLabel("0.000 Nm")
        self.lbl_torque.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_torque.setFont(QFont("Segoe UI", 20, QFont.Bold))
        tg.addWidget(self.lbl_torque, 0, 0, 1, 3)
        self.chk_auto_torque = QCheckBox("Mô-men tự động theo servo/PLC")
        self.chk_auto_torque.setChecked(True)
        self.chk_auto_torque.toggled.connect(lambda v: setattr(self, "_auto_torque", v))
        tg.addWidget(self.chk_auto_torque, 1, 0)
        tg.addWidget(QLabel("Mô-men thủ công:"), 1, 1)
        self.spin_manual_torque = QDoubleSpinBox()
        self.spin_manual_torque.setRange(-50, 50)
        self.spin_manual_torque.setDecimals(3)
        self.spin_manual_torque.setSuffix(" Nm")
        self.spin_manual_torque.valueChanged.connect(lambda v: setattr(self, "_manual_torque", v))
        tg.addWidget(self.spin_manual_torque, 1, 2)
        tg.addWidget(QLabel("Độ nhiễu (Nm):"), 2, 1)
        self.spin_noise = QDoubleSpinBox()
        self.spin_noise.setRange(0, 1)
        self.spin_noise.setDecimals(3)
        self.spin_noise.setValue(self._noise_nm)
        self.spin_noise.valueChanged.connect(lambda v: setattr(self, "_noise_nm", v))
        tg.addWidget(self.spin_noise, 2, 2)
        layout.addWidget(torque)

        manual = QGroupBox("Nút mô phỏng vật lý")
        mr = QHBoxLayout(manual)
        for text, func in [
            ("Chạy (RUN)", self._manual_run),
            ("Dừng (STOP)", self._manual_stop),
            ("Kẹp/Nhả xi lanh", self._toggle_clamp),
            ("Về Home 0°", self._home),
            ("Xóa Lỗi/Hoàn thành", self._reset_fault_done),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            mr.addWidget(btn)
        layout.addWidget(manual)

        regs = QGroupBox("PLC D120..D135")
        rg = QVBoxLayout(regs)
        self.lbl_regs = QLabel("-")
        self.lbl_regs.setWordWrap(True)
        rg.addWidget(self.lbl_regs)
        layout.addWidget(regs)

        log_grp = QGroupBox("Log")
        lg = QVBoxLayout(log_grp)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(160)
        lg.addWidget(self.log_box)
        layout.addWidget(log_grp)

    def _scan_ports(self):
        self.combo_port.clear()
        for port in sorted(serial.tools.list_ports.comports(), key=lambda p: p.device):
            self.combo_port.addItem(f"{port.device} – {port.description}", port.device)
        if self.combo_port.count() == 0:
            self.combo_port.addItem("Không tìm thấy cổng COM", "")

    def _create_context(self) -> ModbusServerContext:
        torque = sim_context(256)
        plc = sim_context(256)
        context = ModbusServerContext(slaves={TORQUE_ID: torque, PLC_ID: plc}, single=False)

        def setv(slave: int, reg: int, vals: list[int]):
            context[slave].setValues(3, reg, vals)

        setv(TORQUE_ID, REG_MACHINE_ID, [0x5A53])
        setv(TORQUE_ID, REG_FIRMWARE_REV, [0x0100])
        setv(TORQUE_ID, REG_MEASURE_UNIT, [8])
        setv(TORQUE_ID, REG_MEASURE_TYPE, [0])
        setv(TORQUE_ID, REG_CALIB_MODE, [0])
        setv(TORQUE_ID, REG_ADDRESS, [TORQUE_ID])
        setv(TORQUE_ID, REG_BAUD, [7])
        setv(TORQUE_ID, REG_PARITY, [0])
        setv(TORQUE_ID, REG_FILTER_LEVEL, [3])
        setv(TORQUE_ID, REG_RESOLUTION_MODE, [0])
        setv(TORQUE_ID, REG_ADC_SPS, [3])
        setv(TORQUE_ID, REG_DELTA_TIME, [10])
        setv(TORQUE_ID, REG_CELL_SENS_HI, float_regs(1.9880))
        setv(TORQUE_ID, REG_CELL_FS_HI, float_regs(49.70))
        setv(TORQUE_ID, REG_STATUS, [STATUS_BIT_STABLE])

        setv(PLC_ID, PLC_D101_MODE, [MODE_BREAKAWAY])
        setv(PLC_ID, PLC_D102_POS_ANGLE_X100, [3600])
        setv(PLC_ID, PLC_D103_NEG_ANGLE_X100, [u16(-3600)])
        setv(PLC_ID, PLC_D104_SPEED_X100, [1000])
        setv(PLC_ID, PLC_D105_CYCLE_SET, [3])
        setv(PLC_ID, PLC_D106_WINDOW_PERCENT, [80])
        setv(PLC_ID, PLC_D107_PART_SELECT, [1])
        setv(PLC_ID, PLC_D108_TORQUE_TYPE, [1])
        return context

    def _ctx_set(self, slave: int, reg: int, vals: list[int]):
        if not self._context:
            return
        self._context[slave].setValues(3, reg, vals)

    def _ctx_get(self, slave: int, reg: int, count: int = 1) -> list[int]:
        if not self._context:
            return [0] * count
        val = self._context[slave].getValues(3, reg, count)
        from pymodbus.pdu import ExceptionResponse
        if isinstance(val, ExceptionResponse) or not isinstance(val, list):
            return [0] * count
        return [int(x) for x in val]

    def _start_server(self):
        host = self.edit_host.text().strip() or "0.0.0.0"
        tcp_port = int(self.spin_tcp_port.value())
        plc_port = self.combo_port.currentData()
        if not plc_port:
            self._log("❌ Chưa chọn cổng COM cho PLC RTU")
            return
        plc_baud = self.combo_baud.currentData()
        self._state = PlantState()
        self._context = self._create_context()
        self._thread = threading.Thread(
            target=self._run_servers,
            args=(host, tcp_port, plc_port, plc_baud),
            daemon=True,
            name="TorqueTcpPlcRtuSimulator",
        )
        self._thread.start()
        self._timer.start()
        self._cmd_timer.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.edit_host.setEnabled(False)
        self.spin_tcp_port.setEnabled(False)
        self.combo_port.setEnabled(False)
        self.combo_baud.setEnabled(False)
        self._log(f"✅ Torque TCP {host}:{tcp_port}; PLC RTU {plc_port} @ {plc_baud}, ID PLC=2")

    def _run_servers(self, host: str, tcp_port: int, plc_port: str, plc_baud: int):
        try:
            self._server = ModbusTcpServer(
                context=self._context,
                address=(host, tcp_port),
                allow_reuse_address=True,
            )
            self._plc_server = ModbusSerialServer(
                context=self._context,
                framer=ModbusRtuFramer,
                port=plc_port,
                baudrate=plc_baud,
                parity="N",
                stopbits=1,
                bytesize=8,
                timeout=0.05,
            )
            self.sig_log.emit(f"🔗 Torque/cảm biến lực TCP: {host}:{tcp_port}, slave 1")
            self.sig_log.emit(f"🔗 PLC Modbus RTU: {plc_port} @ {plc_baud}, slave 2")
            threading.Thread(target=self._plc_server.serve_forever, daemon=True, name="PlcRtuServer").start()
            self._server.serve_forever()
        except Exception as exc:
            self.sig_log.emit(f"❌ Lỗi server: {exc}")
        finally:
            self._server = None

    def _stop_server(self):
        self._timer.stop()
        self._cmd_timer.stop()
        if self._server:
            try:
                self._server.is_running = False
                if getattr(self._server, "handler", None) is not None:
                    self._server.server_close()
                else:
                    if hasattr(self._server, "socket") and self._server.socket:
                        self._server.socket.close()
            except Exception as exc:
                logger.warning("Stop torque TCP server error: %s", exc)
        if self._plc_server:
            try:
                self._plc_server.is_running = False
                if getattr(self._plc_server, "handler", None) is not None:
                    self._plc_server.server_close()
                else:
                    if hasattr(self._plc_server, "socket") and self._plc_server.socket:
                        self._plc_server.socket.close()
            except Exception as exc:
                logger.warning("Stop PLC RTU server error: %s", exc)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.edit_host.setEnabled(True)
        self.spin_tcp_port.setEnabled(True)
        self.combo_port.setEnabled(True)
        self.combo_baud.setEnabled(True)
        self._log("⏹ Bộ mô phỏng đã dừng")

    def _scan_commands(self):
        if not self._context:
            return
        cmd = self._ctx_get(PLC_ID, PLC_D100_CMD_WORD)[0]
        if cmd:
            self._handle_plc_cmd(cmd)
            self._ctx_set(PLC_ID, PLC_D100_CMD_WORD, [0])
        reset, jog_p, jog_m, home = self._ctx_get(PLC_ID, PLC_D109_RESET_FAULT, 4)
        if reset:
            self._reset_fault_done()
            self._ctx_set(PLC_ID, PLC_D109_RESET_FAULT, [0])
        if home:
            self._home()
            self._ctx_set(PLC_ID, PLC_D112_HOME_CMD, [0])
        self._handle_torque_command()

    def _handle_torque_command(self):
        cmd = self._ctx_get(TORQUE_ID, REG_COMMAND)[0]
        if not cmd:
            return
        s = self._state
        if cmd in (CMD_TARE, CMD_TARE_RAM):
            s.tare_offset = s.torque_nm
            self._log(f"⚖️ Torque tare offset={s.tare_offset:.3f} Nm")
        elif cmd == CMD_RESTART:
            s.tare_offset = 0.0
            s.max_net = 0.0
            s.min_net = 0.0
            self._log("🔄 Torque restart/reset")
        elif cmd == CMD_RESET_MAX:
            s.max_net = s.torque_nm - s.tare_offset
        elif cmd == CMD_RESET_MIN:
            s.min_net = s.torque_nm - s.tare_offset
        else:
            self._log(f"📩 Torque command {cmd}")
        self._ctx_set(TORQUE_ID, REG_COMMAND, [0])

    def _handle_plc_cmd(self, cmd: int):
        s = self._state
        if cmd & CMD_START_RUN:
            s.run = True
            s.servo_on = True
            s.done = False
            s.fault_code = 0
            self._log("▶ Lệnh PLC D100.b0 RUN -> Bật đèn RUN và Servo ON")
        if cmd & CMD_STOP_RUN:
            s.run = False
            s.test_running = False
            s.record_enable = False
            s.data_valid = False
            self._log("⏹ Lệnh PLC D100.b1 STOP -> Dừng hệ thống")
        if cmd & CMD_CYLINDER_TOGGLE:
            s.clamped = not s.clamped
            self._log("🔩 Xi lanh KẸP" if s.clamped else "🔓 Xi lanh NHẢ")
        if cmd & CMD_SERVO_ON:
            s.servo_on = True
            self._log("🔌 Servo ON (Sẵn sàng)")
        if cmd & CMD_ABORT:
            s.test_running = False
            s.record_enable = False
            s.data_valid = False
            s.fault_code = 9
            s.phase = 999
            self._log("🛑 Lệnh Abort -> Dừng khẩn cấp, báo lỗi FAULT 9")
        if cmd & CMD_CLEAR_DONE:
            s.done = False
            s.sample_index = 0
            self._log("✅ Xóa trạng thái hoàn thành (Clear done)")
        if cmd & CMD_STOP_RECORD:
            s.test_running = False
            s.record_enable = False
            s.data_valid = False
            s.phase = 0
            self._log("⏺ Dừng ghi/đo (Stop record)")
        if cmd & CMD_START_RECORD:
            self._start_test()

    def _start_test(self):
        s = self._state
        mode, pos, neg, speed, cycles, window = self._read_plc_config()
        s.mode = mode
        if not s.run:
            self._fault(2, "Bắt đầu đo khi PLC chưa ở trạng thái RUN")
            return
        if not s.servo_on:
            self._fault(1, "Bắt đầu đo khi servo chưa bật (Servo ON)")
            return
        if speed <= 0:
            self._fault(4, "Tốc độ đo không hợp lệ (nhỏ hơn hoặc bằng 0)")
            return
        if not s.clamped:
            self._fault(8, "Phôi chưa được kẹp (xi lanh chưa kẹp)")
            return
        s.test_running = True
        s.record_enable = True
        s.data_valid = False
        s.done = False
        s.fault_code = 0
        s.sample_index = 0
        s.cycle = 1
        s.op_target_positive = True
        if mode == MODE_BREAKAWAY:
            s.target_deg = pos
            s.phase = 20
        elif mode == MODE_OPERATING:
            s.target_deg = pos
            s.phase = 210
        elif mode == MODE_MANUAL:
            s.phase = 100
        else:
            self._fault(3, "Chế độ đo không hợp lệ")
            return
        self._log(f"⏺ Bắt đầu đo: chế độ={mode}, đích={s.target_deg:.2f}°, tốc độ={speed:.2f}°/s")

    def _fault(self, code: int, msg: str):
        s = self._state
        s.fault_code = code
        s.test_running = False
        s.record_enable = False
        s.data_valid = False
        s.phase = 999
        self._log(f"❌ BÁO LỖI (FAULT) {code}: {msg}")

    def _read_plc_config(self):
        vals = self._ctx_get(PLC_ID, PLC_D101_MODE, 6)
        mode = vals[0]
        pos = i16(vals[1]) / 100.0
        neg = i16(vals[2]) / 100.0
        speed = vals[3] / 100.0
        cycles = max(1, vals[4])
        window = min(100, max(1, vals[5] or 80))
        return mode, pos, neg, speed, cycles, window

    def _tick(self):
        if not self._context:
            return
        s = self._state
        now = time.monotonic()
        dt = min(0.1, max(0.001, now - s.last_update))
        s.last_update = now
        mode, pos, neg, speed, cycles, window = self._read_plc_config()
        jog_p, jog_m = self._ctx_get(PLC_ID, PLC_D110_JOG_PLUS, 2)

        prev_angle = s.angle_deg
        if s.fault_code:
            s.velocity_deg_s = 0.0
        elif jog_p and s.run and s.servo_on:
            s.phase = 110
            s.target_deg = s.angle_deg
            s.angle_deg += speed * dt
        elif jog_m and s.run and s.servo_on:
            s.phase = 120
            s.target_deg = s.angle_deg
            s.angle_deg -= speed * dt
        elif s.test_running and s.run and s.servo_on:
            self._advance_test(pos, neg, speed, cycles, window, dt)
        else:
            s.velocity_deg_s *= 0.80
            if not s.test_running and s.run and not s.done:
                s.phase = 100 if mode == MODE_MANUAL else 0

        if not (jog_p or jog_m):
            s.velocity_deg_s = (s.angle_deg - prev_angle) / dt
        self._update_torque(dt)
        if s.record_enable and s.test_running:
            s.sample_index = (s.sample_index + 1) & UINT16
        self._write_torque_registers()
        self._write_plc_registers(speed)
        self._update_modbus_status_registers(dt)
        
        self._ui_tick_count = (self._ui_tick_count + 1) % 4
        if self._ui_tick_count == 0:
            self._update_ui()

    def _advance_test(self, pos: float, neg: float, speed: float, cycles: int, window: int, dt: float):
        s = self._state
        delta = s.target_deg - s.angle_deg
        step = max(0.1, speed) * dt
        if abs(delta) <= step:
            s.angle_deg = s.target_deg
            s.velocity_deg_s = 0.0
            if s.mode == MODE_BREAKAWAY:
                s.phase = 900
                s.done = True
                s.test_running = False
                s.record_enable = False
                s.data_valid = False
                self._log("✅ Đo lực Breakaway hoàn thành")
            elif s.mode == MODE_OPERATING:
                if s.op_target_positive:
                    s.op_target_positive = False
                    s.target_deg = neg
                    s.phase = 220
                    self._log(f"↩ Operating: đổi chiều sang đích âm {neg:.2f}°")
                else:
                    if s.cycle >= cycles:
                        s.phase = 900
                        s.done = True
                        s.test_running = False
                        s.record_enable = False
                        s.data_valid = False
                        self._log("✅ Đo Operating hoàn thành đủ chu kỳ")
                    else:
                        s.cycle += 1
                        s.op_target_positive = True
                        s.target_deg = pos
                        s.phase = 210
                        self._log(f"↪ Operating chu kỳ {s.cycle}: đích dương {pos:.2f}°")
        else:
            s.angle_deg += step if delta > 0 else -step
            s.phase = 20 if s.mode == MODE_BREAKAWAY else (210 if s.target_deg >= 0 else 220)
        s.data_valid = self._is_data_valid(pos, neg, window)

    def _is_data_valid(self, pos: float, neg: float, window: int) -> bool:
        s = self._state
        if s.mode == MODE_BREAKAWAY:
            return s.test_running and s.record_enable
        stroke = abs(pos - neg)
        if stroke <= 0:
            return False
        margin = stroke * (100 - window) / 200.0
        lo = min(pos, neg) + margin
        hi = max(pos, neg) - margin
        return s.test_running and s.record_enable and lo <= s.angle_deg <= hi

    def _update_torque(self, dt: float):
        s = self._state
        if not self._auto_torque:
            target = self._manual_torque
        elif not s.clamped or not s.servo_on or abs(s.angle_deg) < 0.03 and abs(s.velocity_deg_s) < 0.05:
            target = 0.0
        else:
            direction = 1.0 if s.velocity_deg_s > 0.05 else (-1.0 if s.velocity_deg_s < -0.05 else (1.0 if s.angle_deg >= 0 else -1.0))
            elastic = 0.18 * s.angle_deg
            friction = 0.55 * direction
            damping = 0.035 * s.velocity_deg_s
            target = elastic + friction + damping
        target = max(-50.0, min(50.0, target))
        alpha = min(1.0, dt / 0.12)
        s.torque_nm += (target - s.torque_nm) * alpha
        s.torque_nm += random.gauss(0, self._noise_nm)
        s.torque_nm = max(-50.0, min(50.0, s.torque_nm))

    def _write_torque_registers(self):
        s = self._state
        gross = s.torque_nm
        net = gross - s.tare_offset
        s.max_net = max(s.max_net, net)
        s.min_net = min(s.min_net, net)
        self._ctx_set(TORQUE_ID, REG_NET_WEIGHT_HI, float_regs(net))
        self._ctx_set(TORQUE_ID, REG_GROSS_WEIGHT_HI, float_regs(gross))
        self._ctx_set(TORQUE_ID, REG_TARE_WEIGHT_HI, float_regs(s.tare_offset))
        self._ctx_set(TORQUE_ID, REG_INT_NET_HI, int32_regs(round(net * 1000)))
        self._ctx_set(TORQUE_ID, REG_INT_GROSS_HI, int32_regs(round(gross * 1000)))
        self._ctx_set(TORQUE_ID, REG_INT_TARE_HI, int32_regs(round(s.tare_offset * 1000)))
        self._ctx_set(TORQUE_ID, REG_MAX_NET_HI, float_regs(s.max_net))
        self._ctx_set(TORQUE_ID, REG_MIN_NET_HI, float_regs(s.min_net))
        self._ctx_set(TORQUE_ID, REG_STATUS, [STATUS_BIT_STABLE])

    def _write_plc_registers(self, speed: float):
        s = self._state
        status = 0
        if s.run:
            status |= ST_RUN
        if s.servo_on:
            status |= ST_SERVO
        if s.clamped:
            status |= ST_CLAMP
        if s.test_running:
            status |= ST_TEST
        if s.record_enable:
            status |= ST_RECORD
        if s.data_valid:
            status |= ST_VALID
        if s.done:
            status |= ST_DONE
        if s.fault_code:
            status |= ST_FAULT
        pulse = int(s.angle_deg * 200000 / 360.0) & 0xFFFFFFFF
        regs = [
            status,
            s.mode & UINT16,
            s.phase & UINT16,
            s.cycle & UINT16,
            u16(round(s.angle_deg * 100)),
            u16(round(s.target_deg * 100)),
            u16(round(abs(speed) * 100)),
            pulse & UINT16,
            (pulse >> 16) & UINT16,
            s.fault_code & UINT16,
            1 if s.data_valid else 0,
            1 if s.record_enable else 0,
            1 if s.clamped else 0,
            1 if s.servo_on else 0,
            1 if s.done else 0,
            s.sample_index & UINT16,
        ]
        self._ctx_set(PLC_ID, PLC_D120_STATUS_WORD, regs)
        if getattr(self, "_ui_tick_count", 0) == 0:
            self.lbl_regs.setText("D120..D135 = " + ", ".join(str(v) for v in regs))

    def _update_ui(self):
        s = self._state
        lamp_state = {
            "RUN": s.run,
            "SERVO": s.servo_on,
            "CLAMP": s.clamped,
            "RECORD": s.record_enable,
            "VALID": s.data_valid,
            "DONE": s.done,
            "FAULT": bool(s.fault_code),
        }
        for name, on in lamp_state.items():
            self.lamps[name].setText(f"{name}: {'ON' if on else 'OFF'}")
            self.lamps[name].setStyleSheet("")
        direction = "DƯƠNG/CW" if s.velocity_deg_s > 0.05 else ("ÂM/CCW" if s.velocity_deg_s < -0.05 else "DỪNG")
        self.lbl_motion.setText(f"Servo: {direction} | Góc {s.angle_deg:.2f}° | Đích {s.target_deg:.2f}° | Tốc độ {s.velocity_deg_s:.2f}°/s")
        self.lbl_cylinder.setText("Xi lanh: KẸP | Kẹp phôi: CÓ" if s.clamped else "Xi lanh: NHẢ | Kẹp phôi: KHÔNG")
        self.lbl_phase.setText(f"PLC: Bước={s.phase}, Chế độ={s.mode}, Chu kỳ={s.cycle}, Lỗi D129={s.fault_code}")
        net = s.torque_nm - s.tare_offset
        self.lbl_torque.setText(f"{net:+.3f} Nm")
        self.lbl_torque.setStyleSheet("")

    def _manual_run(self):
        self._state.run = True
        self._state.servo_on = True
        self._state.done = False
        self._state.fault_code = 0
        self._log("🔘 Nút bấm vật lý: RUN (Chạy)")

    def _manual_stop(self):
        s = self._state
        s.run = False
        s.test_running = False
        s.record_enable = False
        s.data_valid = False
        self._log("🔘 Nút bấm vật lý: STOP (Dừng)")

    def _toggle_clamp(self):
        self._state.clamped = not self._state.clamped
        self._log("🔘 Nút bấm xi lanh: KẸP" if self._state.clamped else "🔘 Nút bấm xi lanh: NHẢ")

    def _home(self):
        s = self._state
        s.angle_deg = 0.0
        s.target_deg = 0.0
        s.velocity_deg_s = 0.0
        s.torque_nm = 0.0
        s.cycle = 0
        s.phase = 130 if s.run else 0
        self._log("🏠 Home: Đã đưa góc quay và mô-men về 0")

    def _reset_fault_done(self):
        s = self._state
        s.fault_code = 0
        s.done = False
        s.sample_index = 0
        if s.phase in (900, 999):
            s.phase = 0
        self._log("🧹 Xóa Lỗi / Trạng thái hoàn thành")

    def _update_modbus_status_registers(self, dt: float):
        if not hasattr(self, '_msg_timer'):
            self._msg_timer = 0.0
            self._msg_count = 120
            self._err_count = 0

        self._msg_timer += dt
        if self._msg_timer >= 1.0:
            self._msg_timer = 0.0
            self._msg_count += random.randint(4, 8)
            if random.random() < 0.02:
                self._err_count += 1

            s_val = [
                self._msg_count & UINT16,          # D200 (Bus Message Counter)
                self._err_count & UINT16,          # D201 (Bus Communication Error Counter)
                0,                                 # D202 (Exception Error Counter)
                0, 0, 0, 0,                        # D203 - D206
                0,                                 # D207 (Character Overrun Counter)
                (self._msg_count - self._err_count) & UINT16, # D208 (Event Counter)
                0,                                 # D209
                8,                                 # D210 (Event Log Length)
                0x0102,                            # D211 (Event Log Data 0-1)
                0x0304,                            # D212 (Event Log Data 2-3)
                0x0506,                            # D213 (Event Log Data 4-5)
                0x0708,                            # D214 (Event Log Data 6-7)
            ]
            self._ctx_set(PLC_ID, 200, s_val)

    def _log(self, msg: str):
        self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def closeEvent(self, a0):
        self._stop_server()
        super().closeEvent(a0)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ZE-SG3 + PLC Integrated Simulator")
    window = IntegratedSimulatorWindow()
    window.show()
    logger.info("Integrated simulator started")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()