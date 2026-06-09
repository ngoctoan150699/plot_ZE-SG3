"""Single-threaded Modbus scheduler for ZE-SG3 sensor and PLC.

Only this worker should touch the shared Modbus client during realtime
acquisition. This prevents multiple polling/command threads from competing for
one RTU bus while keeping the Qt UI thread non-blocking.
"""
from __future__ import annotations

import logging
import queue
import struct
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from application.interfaces import IModbusClient
from domain.constants import (
    PLC_STATUS_REGISTER_COUNT,
    PLC_STATUS_START_ADDRESS,
    REG_GROSS_WEIGHT_HI,
    REG_NET_WEIGHT_HI,
    STATUS_BIT_FULLSCALE,
    STATUS_BIT_STABLE,
)
from domain.entities import DeviceStatus
from domain.plc_protocol import PlcStatus

logger = logging.getLogger(__name__)


@dataclass
class _QueuedCommand:
    name: str
    callback: Callable[[], bool]


class ModbusBusScheduler:
    """Coordinate all realtime Modbus reads/writes through one worker thread."""

    def __init__(
        self,
        client: IModbusClient,
        sensor_slave_id: int = 1,
        plc_slave_id: int = 2,
        sensor_interval_ms: int = 20,
        plc_interval_ms: int = 150,
    ):
        self._client = client
        self._sensor_slave_id = sensor_slave_id
        self._plc_slave_id = plc_slave_id
        self._sensor_interval_s = max(0.005, sensor_interval_ms / 1000.0)
        self._plc_interval_s = max(0.05, plc_interval_ms / 1000.0)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._wake_event = threading.Event()
        self._commands: queue.Queue[_QueuedCommand] = queue.Queue(maxsize=20)
        self._sensor_callbacks: list[Callable[[DeviceStatus], None]] = []
        self._plc_callbacks: list[Callable[[Optional[PlcStatus]], None]] = []
        self._command_callbacks: list[Callable[[str, bool], None]] = []
        self._error_callbacks: list[Callable[[str], None]] = []

    def set_client(self, client: IModbusClient, sensor_slave_id: int = 1, plc_slave_id: int = 2) -> None:
        self._client = client
        self._sensor_slave_id = sensor_slave_id
        self._plc_slave_id = plc_slave_id

    def set_intervals(self, sensor_ms: int, plc_ms: int = 150) -> None:
        self._sensor_interval_s = max(0.005, int(sensor_ms) / 1000.0)
        self._plc_interval_s = max(0.05, int(plc_ms) / 1000.0)
        self._wake_event.set()

    def on_sensor_data(self, callback: Callable[[DeviceStatus], None]) -> None:
        self._sensor_callbacks.append(callback)

    def on_plc_status(self, callback: Callable[[Optional[PlcStatus]], None]) -> None:
        self._plc_callbacks.append(callback)

    def on_command_result(self, callback: Callable[[str, bool], None]) -> None:
        self._command_callbacks.append(callback)

    def on_error(self, callback: Callable[[str], None]) -> None:
        self._error_callbacks.append(callback)

    def start(self) -> None:
        if self._running and self._thread and self._thread.is_alive():
            return
        self._running = True
        self._wake_event.clear()
        self._thread = threading.Thread(target=self._loop, name="Modbus-Bus-Scheduler", daemon=True)
        self._thread.start()
        logger.info("ModbusBusScheduler: started")

    def stop(self) -> None:
        self._running = False
        self._wake_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._drain_commands()
        logger.info("ModbusBusScheduler: stopped")

    def is_running(self) -> bool:
        return self._running

    def enqueue_command(self, name: str, callback: Callable[[], bool]) -> bool:
        try:
            self._commands.put_nowait(_QueuedCommand(name=name, callback=callback))
            self._wake_event.set()
            return True
        except queue.Full:
            self._emit_error("Hàng đợi lệnh PLC đang đầy")
            return False

    def _loop(self) -> None:
        next_sensor = 0.0
        next_plc = 0.0
        while self._running:
            now = time.monotonic()
            did_work = False

            cmd = self._pop_command()
            if cmd is not None:
                ok = self._run_command(cmd)
                self._emit_command_result(cmd.name, ok)
                did_work = True

            now = time.monotonic()
            if now >= next_sensor:
                status = self._read_sensor_status()
                if status is not None:
                    self._emit_sensor(status)
                next_sensor = time.monotonic() + self._sensor_interval_s
                did_work = True

            now = time.monotonic()
            if now >= next_plc:
                plc_status = self._read_plc_status()
                self._emit_plc(plc_status)
                next_plc = time.monotonic() + self._plc_interval_s
                did_work = True

            if not did_work:
                sleep_s = min(max(0.001, next_sensor - now), max(0.001, next_plc - now), 0.02)
                self._wake_event.wait(timeout=sleep_s)
                self._wake_event.clear()

    def _read_sensor_status(self) -> Optional[DeviceStatus]:
        try:
            regs = self._client.read_registers(REG_NET_WEIGHT_HI, 15, self._sensor_slave_id)
            if regs is None or len(regs) < 15:
                return None
            net_val = self._decode_float32(regs[0], regs[1])
            gross_val = self._decode_float32(regs[2], regs[3])
            tare_val = self._decode_float32(regs[4], regs[5])
            status_raw = regs[14]
            return DeviceStatus(
                connected=True,
                is_stable=(status_raw & STATUS_BIT_STABLE) != 0,
                is_fullscale=(status_raw & STATUS_BIT_FULLSCALE) != 0,
                net_weight=net_val,
                gross_weight=gross_val,
                tare_weight=tare_val,
                max_net_weight=0.0,
                min_net_weight=0.0,
                raw_status_reg=status_raw,
            )
        except Exception as exc:
            self._emit_error(f"Lỗi đọc sensor Modbus: {exc}")
            return None

    def _read_plc_status(self) -> Optional[PlcStatus]:
        try:
            regs = self._client.read_registers(
                PLC_STATUS_START_ADDRESS,
                PLC_STATUS_REGISTER_COUNT,
                self._plc_slave_id,
            )
            if regs is None:
                return None
            return PlcStatus.from_registers(regs)
        except Exception:
            return None

    def _run_command(self, cmd: _QueuedCommand) -> bool:
        try:
            return bool(cmd.callback())
        except Exception as exc:
            self._emit_error(f"Lỗi PLC command {cmd.name}: {exc}")
            return False

    def _pop_command(self) -> Optional[_QueuedCommand]:
        try:
            return self._commands.get_nowait()
        except queue.Empty:
            return None

    def _drain_commands(self) -> None:
        while True:
            try:
                self._commands.get_nowait()
            except queue.Empty:
                break

    def _decode_float32(self, hi: int, lo: int) -> float:
        try:
            packed = struct.pack('>HH', hi & 0xFFFF, lo & 0xFFFF)
            return struct.unpack('>f', packed)[0]
        except Exception:
            return 0.0

    def _emit_sensor(self, status: DeviceStatus) -> None:
        for cb in list(self._sensor_callbacks):
            try:
                cb(status)
            except Exception as exc:
                logger.debug("sensor callback failed: %s", exc)

    def _emit_plc(self, status: Optional[PlcStatus]) -> None:
        for cb in list(self._plc_callbacks):
            try:
                cb(status)
            except Exception as exc:
                logger.debug("plc callback failed: %s", exc)

    def _emit_command_result(self, name: str, ok: bool) -> None:
        for cb in list(self._command_callbacks):
            try:
                cb(name, ok)
            except Exception as exc:
                logger.debug("command callback failed: %s", exc)

    def _emit_error(self, msg: str) -> None:
        logger.debug(msg)
        for cb in list(self._error_callbacks):
            try:
                cb(msg)
            except Exception:
                pass
