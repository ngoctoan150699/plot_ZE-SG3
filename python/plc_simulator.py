#!/usr/bin/env python3
"""
PLC Modbus Simulator – ZE-SG3 Servo Flow
=======================================
Mô phỏng PLC điều khiển servo/state machine theo register plan D100..D135.

Khuyến nghị mới:
  - Nếu cần mô phỏng cả torque + PLC trên cùng COM, hãy chạy
    python python/torque_simulator.py
  - File đó tạo 2 slave: torque ID=1 và PLC ID=2.

Cách dùng file PLC đơn lẻ này:
  1. Tạo cặp COM ảo bằng com0com/VSPD, ví dụ COM12 <-> COM13.
  2. Chạy: python python/plc_simulator.py
  3. Chọn COM simulator, ví dụ COM12, slave ID mặc định 2.
  4. Trong app chính, kết nối PLC tới COM còn lại, ví dụ COM13.

Lưu ý:
  - PLC simulator này chỉ mô phỏng D100..D135 cho servo, gate record, angle, cycle.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
from dataclasses import dataclass

import serial.tools.list_ports
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock
from pymodbus.server.sync import ModbusSerialServer
from pymodbus.transaction import ModbusRtuFramer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PlcSimulator")


# PLC register map D100..D135 (base-0 Modbus holding register offsets).
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

PLC_CMD_START_RUN = 1 << 0
PLC_CMD_STOP_RUN = 1 << 1
PLC_CMD_START_RECORD = 1 << 2
PLC_CMD_STOP_RECORD = 1 << 3
PLC_CMD_CYLINDER_TOGGLE = 1 << 4
PLC_CMD_SERVO_ON = 1 << 5
PLC_CMD_ABORT = 1 << 6
PLC_CMD_CLEAR_DONE = 1 << 7

PLC_STATUS_RUN = 1 << 0
PLC_STATUS_SERVO_ON = 1 << 1
PLC_STATUS_CYLINDER_CLAMPED = 1 << 2
PLC_STATUS_TEST_RUNNING = 1 << 3
PLC_STATUS_RECORDING = 1 << 4
PLC_STATUS_DATA_VALID = 1 << 5
PLC_STATUS_DONE = 1 << 6
PLC_STATUS_FAULT = 1 << 7

PLC_MODE_MANUAL = 0
PLC_MODE_BREAKAWAY = 1
PLC_MODE_OPERATING = 2

UINT16_MASK = 0xFFFF


def encode_i16(value: int) -> int:
    return int(value) & UINT16_MASK


def decode_i16(value: int) -> int:
    value = int(value) & UINT16_MASK
    return value - 0x10000 if value & 0x8000 else value


@dataclass
class PlcRuntimeState:
    run: bool = False
    recording: bool = False
    clamped: bool = False
    servo_on: bool = True
    done: bool = False
    fault_code: int = 0
    angle_deg: float = 0.0
    target_deg: float = 0.0
    cycle: int = 0
    sample_index: int = 0
    phase: int = 0
    last_update: float = time.monotonic()


class PlcSimulatorWindow(QMainWindow):
    """Standalone GUI mô phỏng PLC D100..D135."""

    sig_log = pyqtSignal(str)

    STYLESHEET = """
    QMainWindow { background: #f5f7fb; }
    QGroupBox {
        background: #ffffff;
        border: 1px solid #dbe3ef;
        border-radius: 8px;
        margin-top: 14px;
        padding: 12px;
        font-weight: bold;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
    QLabel { color: #263238; }
    QPushButton {
        background: #e3f2fd;
        border: 1px solid #90caf9;
        border-radius: 5px;
        padding: 7px 12px;
        color: #0d47a1;
        font-weight: 600;
    }
    QPushButton:hover { background: #bbdefb; }
    QPushButton#start { background: #2e7d32; color: white; }
    QPushButton#stop { background: #c62828; color: white; }
    QTextEdit { background: #fafafa; border: 1px solid #dbe3ef; font-family: Consolas; font-size: 9pt; }
    QSpinBox, QDoubleSpinBox, QComboBox { background: white; border: 1px solid #b0bec5; border-radius: 4px; padding: 4px; }
    """

    def __init__(self):
        super().__init__()
        self._context = None
        self._server = None
        self._server_thread = None
        self._loop = None
        self._slave_id = 2
        self._state = PlcRuntimeState()

        self._build_ui()
        self.setStyleSheet(self.STYLESHEET)

        self._scan_ports()

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(50)
        self._update_timer.timeout.connect(self._tick)

        self._command_timer = QTimer(self)
        self._command_timer.setInterval(50)
        self._command_timer.timeout.connect(self._check_commands)

        self.sig_log.connect(self._log)

    def _build_ui(self):
        self.setWindowTitle("🤖 PLC Modbus Simulator D100..D135")
        self.setGeometry(140, 100, 640, 760)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        conn_grp = QGroupBox("🔌 Kết nối Modbus RTU")
        cg = QGridLayout()
        cg.addWidget(QLabel("COM Port simulator:"), 0, 0)
        self.combo_port = QComboBox()
        cg.addWidget(self.combo_port, 0, 1)
        btn_scan = QPushButton("🔄 Quét")
        btn_scan.clicked.connect(self._scan_ports)
        cg.addWidget(btn_scan, 0, 2)

        cg.addWidget(QLabel("Baudrate:"), 1, 0)
        self.combo_baud = QComboBox()
        for baud in [9600, 19200, 38400, 57600, 115200]:
            self.combo_baud.addItem(str(baud), baud)
        self.combo_baud.setCurrentText("115200")
        cg.addWidget(self.combo_baud, 1, 1)

        cg.addWidget(QLabel("Slave ID:"), 2, 0)
        self.spin_slave = QSpinBox()
        self.spin_slave.setRange(1, 247)
        self.spin_slave.setValue(2)
        cg.addWidget(self.spin_slave, 2, 1)
        conn_grp.setLayout(cg)
        layout.addWidget(conn_grp)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶️ Start PLC Simulator")
        self.btn_start.setObjectName("start")
        self.btn_start.clicked.connect(self._start_server)
        btn_row.addWidget(self.btn_start)
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setObjectName("stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_server)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        sim_grp = QGroupBox("⚙️ Trạng thái mô phỏng")
        sg = QGridLayout()
        self.chk_auto_done = QCheckBox("Tự Done khi đủ cycle")
        self.chk_auto_done.setChecked(True)
        sg.addWidget(self.chk_auto_done, 0, 0, 1, 2)

        sg.addWidget(QLabel("Angle hiện tại (deg):"), 1, 0)
        self.spin_angle = QDoubleSpinBox()
        self.spin_angle.setRange(-3600.0, 3600.0)
        self.spin_angle.setDecimals(2)
        self.spin_angle.valueChanged.connect(self._manual_angle_changed)
        sg.addWidget(self.spin_angle, 1, 1)

        sg.addWidget(QLabel("Fault code D129:"), 2, 0)
        self.spin_fault = QSpinBox()
        self.spin_fault.setRange(0, 9999)
        self.spin_fault.valueChanged.connect(self._manual_fault_changed)
        sg.addWidget(self.spin_fault, 2, 1)

        self.btn_run = QPushButton("RUN")
        self.btn_run.clicked.connect(self._manual_run)
        sg.addWidget(self.btn_run, 3, 0)
        self.btn_stop_run = QPushButton("STOP")
        self.btn_stop_run.clicked.connect(self._manual_stop)
        sg.addWidget(self.btn_stop_run, 3, 1)

        self.btn_record = QPushButton("START RECORD")
        self.btn_record.clicked.connect(self._manual_start_record)
        sg.addWidget(self.btn_record, 4, 0)
        self.btn_stop_record = QPushButton("STOP RECORD")
        self.btn_stop_record.clicked.connect(self._manual_stop_record)
        sg.addWidget(self.btn_stop_record, 4, 1)

        self.btn_clamp = QPushButton("Clamp toggle")
        self.btn_clamp.clicked.connect(self._toggle_clamp)
        sg.addWidget(self.btn_clamp, 5, 0)
        self.btn_done = QPushButton("Set/Clear Done")
        self.btn_done.clicked.connect(self._toggle_done)
        sg.addWidget(self.btn_done, 5, 1)

        self.btn_home = QPushButton("Home angle=0")
        self.btn_home.clicked.connect(self._home)
        sg.addWidget(self.btn_home, 6, 0)
        self.btn_reset = QPushButton("Reset Fault/Done")
        self.btn_reset.clicked.connect(self._reset_fault_done)
        sg.addWidget(self.btn_reset, 6, 1)

        sim_grp.setLayout(sg)
        layout.addWidget(sim_grp)

        status_grp = QGroupBox("📊 Register status")
        st = QVBoxLayout()
        self.lbl_status = QLabel("PLC: stopped")
        self.lbl_status.setStyleSheet("font-weight: 700; color: #1565c0;")
        st.addWidget(self.lbl_status)
        self.lbl_registers = QLabel("D120..D135: -")
        self.lbl_registers.setWordWrap(True)
        st.addWidget(self.lbl_registers)
        status_grp.setLayout(st)
        layout.addWidget(status_grp)

        log_grp = QGroupBox("📋 Log")
        lg = QVBoxLayout()
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(150)
        lg.addWidget(self.log_box)
        log_grp.setLayout(lg)
        layout.addWidget(log_grp)

    def _scan_ports(self):
        self.combo_port.clear()
        ports = serial.tools.list_ports.comports()
        for port in sorted(ports, key=lambda item: item.device):
            self.combo_port.addItem(f"{port.device} – {port.description}", port.device)
        if self.combo_port.count() == 0:
            self.combo_port.addItem("Không tìm thấy COM port", "")

    def _create_datastore(self):
        simulator = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0] * 256),
            co=ModbusSequentialDataBlock(0, [0] * 256),
            hr=ModbusSequentialDataBlock(0, [0] * 256),
            ir=ModbusSequentialDataBlock(0, [0] * 256),
            zero_mode=True
        )
        context = ModbusServerContext(slaves={self._slave_id: simulator}, single=False)

        def set_init(address: int, values: list[int]):
            context[self._slave_id].setValues(3, address, values)

        set_init(PLC_D101_MODE, [PLC_MODE_BREAKAWAY])
        set_init(PLC_D102_POS_ANGLE_X100, [3600])
        set_init(PLC_D103_NEG_ANGLE_X100, [encode_i16(-3600)])
        set_init(PLC_D104_SPEED_X100, [1000])
        set_init(PLC_D105_CYCLE_SET, [3])
        set_init(PLC_D106_WINDOW_PERCENT, [80])
        set_init(PLC_D107_PART_SELECT, [1])
        set_init(PLC_D108_TORQUE_TYPE, [1])
        return context

    def _context_set_values(self, address: int, values: list[int]):
        if self._context:
            self._context[self._slave_id].setValues(3, address, values)

    def _context_get_values(self, address: int, count: int = 1):
        if not self._context:
            return [0] * count
        return self._context[self._slave_id].getValues(3, address, count)

    def _start_server(self):
        port = self.combo_port.currentData()
        if not port:
            self._log("❌ Chưa chọn COM port")
            return
        self._slave_id = self.spin_slave.value()
        baudrate = self.combo_baud.currentData()
        self._state = PlcRuntimeState()
        self._context = self._create_datastore()

        self._server_thread = threading.Thread(
            target=self._run_server,
            args=(port, baudrate),
            daemon=True,
            name="PlcModbusServer",
        )
        self._server_thread.start()
        self._update_timer.start()
        self._command_timer.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.combo_port.setEnabled(False)
        self.combo_baud.setEnabled(False)
        self.spin_slave.setEnabled(False)
        self._log(f"✅ PLC simulator chạy trên {port} @ {baudrate}, slave={self._slave_id}")

    def _run_server(self, port: str, baudrate: int):
        try:
            self._server = ModbusSerialServer(
                context=self._context,
                framer=ModbusRtuFramer,
                port=port,
                baudrate=baudrate,
                parity="N",
                stopbits=1,
                bytesize=8,
                timeout=1,
            )
            self.sig_log.emit(f"🔗 Đang lắng nghe PLC Modbus RTU trên {port}")
            self._server.serve_forever()
        except Exception as exc:
            self.sig_log.emit(f"❌ Lỗi server: {exc}")
            import traceback
            self.sig_log.emit(traceback.format_exc())
        finally:
            self._server = None

    def _stop_server(self):
        self._update_timer.stop()
        self._command_timer.stop()
        if self._server:
            try:
                self._server.is_running = False
                if getattr(self._server, "handler", None) is not None:
                    self._server.server_close()
                else:
                    if hasattr(self._server, "socket") and self._server.socket:
                        self._server.socket.close()
            except Exception as exc:
                logger.warning("Stop server error: %s", exc)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.combo_port.setEnabled(True)
        self.combo_baud.setEnabled(True)
        self.spin_slave.setEnabled(True)
        self.lbl_status.setText("PLC: stopped")
        self._log("⏹ PLC simulator đã dừng")

    def _read_config(self):
        values = self._context_get_values(PLC_D101_MODE, 8)
        mode = values[0]
        pos_deg = decode_i16(values[1]) / 100.0
        neg_deg = decode_i16(values[2]) / 100.0
        speed_deg_s = max(1.0, values[3] / 100.0)
        cycle_set = max(1, values[4])
        return mode, pos_deg, neg_deg, speed_deg_s, cycle_set

    def _tick(self):
        if not self._context:
            return
        state = self._state
        now = time.monotonic()
        dt = max(0.001, now - state.last_update)
        state.last_update = now

        mode, pos_deg, neg_deg, speed_deg_s, cycle_set = self._read_config()
        state.target_deg = neg_deg if mode == PLC_MODE_OPERATING else pos_deg

        jog_plus, jog_minus = self._context_get_values(PLC_D110_JOG_PLUS, 2)
        if jog_plus:
            state.angle_deg += speed_deg_s * dt
            state.phase = 2
        elif jog_minus:
            state.angle_deg -= speed_deg_s * dt
            state.phase = 2
        elif state.run and not state.done and not state.fault_code:
            state.phase = 1
            delta = state.target_deg - state.angle_deg
            step = speed_deg_s * dt
            if abs(delta) <= step:
                state.angle_deg = state.target_deg
                state.cycle += 1
                if self.chk_auto_done.isChecked() and state.cycle >= cycle_set:
                    state.done = True
                    state.run = False
                    state.recording = False
                    state.phase = 0
                    self._log("✅ Auto Done: đủ cycle")
            else:
                state.angle_deg += step if delta > 0 else -step
        else:
            state.phase = 0

        if state.recording and state.run and not state.done and not state.fault_code:
            state.sample_index = (state.sample_index + 1) & UINT16_MASK

        self.spin_angle.blockSignals(True)
        self.spin_angle.setValue(state.angle_deg)
        self.spin_angle.blockSignals(False)
        self.spin_fault.blockSignals(True)
        self.spin_fault.setValue(state.fault_code)
        self.spin_fault.blockSignals(False)

        self._write_status(mode, speed_deg_s)

    def _write_status(self, mode: int, speed_deg_s: float):
        state = self._state
        status = 0
        if state.run:
            status |= PLC_STATUS_RUN | PLC_STATUS_TEST_RUNNING
        if state.servo_on:
            status |= PLC_STATUS_SERVO_ON
        if state.clamped:
            status |= PLC_STATUS_CYLINDER_CLAMPED
        if state.recording:
            status |= PLC_STATUS_RECORDING | PLC_STATUS_DATA_VALID
        if state.done:
            status |= PLC_STATUS_DONE
        if state.fault_code:
            status |= PLC_STATUS_FAULT

        angle_x100 = encode_i16(round(state.angle_deg * 100))
        target_x100 = encode_i16(round(state.target_deg * 100))
        speed_x100 = int(round(speed_deg_s * 100)) & UINT16_MASK
        pulse = int(round(state.angle_deg * 1000)) & 0xFFFFFFFF
        regs = [
            status,
            mode & UINT16_MASK,
            state.phase & UINT16_MASK,
            state.cycle & UINT16_MASK,
            angle_x100,
            target_x100,
            speed_x100,
            pulse & UINT16_MASK,
            (pulse >> 16) & UINT16_MASK,
            state.fault_code & UINT16_MASK,
            1 if state.recording else 0,
            1 if state.recording else 0,
            1 if state.clamped else 0,
            1 if state.servo_on else 0,
            1 if state.done else 0,
            state.sample_index & UINT16_MASK,
        ]
        self._context_set_values(PLC_D120_STATUS_WORD, regs)
        self.lbl_status.setText(
            f"PLC: run={int(state.run)} rec={int(state.recording)} clamp={int(state.clamped)} "
            f"angle={state.angle_deg:.2f}° target={state.target_deg:.2f}° "
            f"cycle={state.cycle} sample={state.sample_index} done={int(state.done)} fault={state.fault_code}"
        )
        self.lbl_registers.setText("D120..D135 = " + ", ".join(str(v) for v in regs))

    def _check_commands(self):
        if not self._context:
            return
        cmd_values = self._context_get_values(PLC_D100_CMD_WORD, 1)
        if cmd_values and cmd_values[0]:
            self._handle_command(cmd_values[0])
            self._context_set_values(PLC_D100_CMD_WORD, [0])

        aux_values = self._context_get_values(PLC_D109_RESET_FAULT, 4)
        if aux_values:
            if aux_values[0]:
                self._reset_fault_done()
                self._context_set_values(PLC_D109_RESET_FAULT, [0])
            if aux_values[3]:
                self._home()
                self._context_set_values(PLC_D112_HOME_CMD, [0])

    def _handle_command(self, cmd_word: int):
        if cmd_word & PLC_CMD_START_RUN:
            self._manual_run()
            self._log("📩 D100 START_RUN")
        if cmd_word & PLC_CMD_STOP_RUN:
            self._manual_stop()
            self._log("📩 D100 STOP_RUN")
        if cmd_word & PLC_CMD_START_RECORD:
            self._manual_start_record()
            self._log("📩 D100 START_RECORD")
        if cmd_word & PLC_CMD_STOP_RECORD:
            self._manual_stop_record()
            self._log("📩 D100 STOP_RECORD")
        if cmd_word & PLC_CMD_CYLINDER_TOGGLE:
            self._toggle_clamp()
            self._log("📩 D100 CLAMP_TOGGLE")
        if cmd_word & PLC_CMD_SERVO_ON:
            self._state.servo_on = True
            self._log("📩 D100 SERVO_ON")
        if cmd_word & PLC_CMD_ABORT:
            self._state.run = False
            self._state.recording = False
            self._state.fault_code = 1
            self._log("📩 D100 ABORT")
        if cmd_word & PLC_CMD_CLEAR_DONE:
            self._state.done = False
            self._state.sample_index = 0
            self._log("📩 D100 CLEAR_DONE")

    def _manual_angle_changed(self, value: float):
        self._state.angle_deg = value

    def _manual_fault_changed(self, value: int):
        self._state.fault_code = value

    def _manual_run(self):
        self._state.run = True
        self._state.done = False
        self._state.fault_code = 0

    def _manual_stop(self):
        self._state.run = False
        self._state.recording = False

    def _manual_start_record(self):
        self._state.run = True
        self._state.recording = True
        self._state.done = False
        self._state.fault_code = 0
        self._state.sample_index = 0

    def _manual_stop_record(self):
        self._state.recording = False

    def _toggle_clamp(self):
        self._state.clamped = not self._state.clamped

    def _toggle_done(self):
        self._state.done = not self._state.done
        if self._state.done:
            self._state.run = False
            self._state.recording = False

    def _home(self):
        self._state.angle_deg = 0.0
        self._state.cycle = 0
        self._state.sample_index = 0

    def _reset_fault_done(self):
        self._state.fault_code = 0
        self._state.done = False
        self._state.sample_index = 0

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")

    def closeEvent(self, event):
        self._stop_server()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PLC Modbus Simulator")
    window = PlcSimulatorWindow()
    window.show()
    logger.info("PLC Simulator đã khởi động")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
