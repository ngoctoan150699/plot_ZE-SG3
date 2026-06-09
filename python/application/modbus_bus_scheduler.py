"""Optimized Modbus scheduler for ZE-SG3 force and PLC realtime state.

Only this worker performs periodic reads on the shared Modbus client. PLC
commands are intentionally not queued here; UI command workers call the client
immediately and the infrastructure client lock serializes each RTU transaction.
"""
from __future__ import annotations

import logging
import struct
import time
from typing import Callable, Optional

from application.interfaces import IModbusClient
from domain.constants import (
    PLC_STATUS_REGISTER_COUNT,
    PLC_STATUS_START_ADDRESS,
    REG_NET_WEIGHT_HI,
)
from domain.entities import DeviceStatus
from domain.plc_protocol import PlcRealtimeState, PlcStatus, decode_signed_16

logger = logging.getLogger(__name__)


class ModbusBusScheduler:
    """Coordinate optimized realtime Modbus reads through one worker thread."""

    def __init__(
        self,
        client: IModbusClient,
        sensor_slave_id: int = 1,
        plc_slave_id: int = 2,
        sensor_interval_ms: int = 20,
        plc_interval_ms: int = 1000,
    ):
        import threading

        self._client = client
        self._sensor_slave_id = sensor_slave_id
        self._plc_slave_id = plc_slave_id
        self._sensor_interval_s = max(0.001, sensor_interval_ms / 1000.0)
        self._plc_status_interval_s = max(0.2, plc_interval_ms / 1000.0)
        self._plc_realtime_interval_s = 0.02
        self._recording_active = False
        self._polling_paused = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._wake_event = threading.Event()
        self._sensor_callbacks: list[Callable[[DeviceStatus], None]] = []
        self._plc_callbacks: list[Callable[[Optional[object]], None]] = []
        self._command_callbacks: list[Callable[[str, bool], None]] = []
        self._error_callbacks: list[Callable[[str], None]] = []
        self._force_timings_ms: list[float] = []

    def set_client(self, client: IModbusClient, sensor_slave_id: int = 1, plc_slave_id: int = 2) -> None:
        self._client = client
        self._sensor_slave_id = sensor_slave_id
        self._plc_slave_id = plc_slave_id
        self._force_timings_ms.clear()

    def set_intervals(self, sensor_ms: int, plc_ms: int = 1000) -> None:
        self._sensor_interval_s = max(0.001, int(sensor_ms) / 1000.0)
        self._plc_status_interval_s = max(0.2, int(plc_ms) / 1000.0)
        self._wake_event.set()

    def set_recording_active(self, active: bool) -> None:
        self._recording_active = bool(active)
        self._wake_event.set()

    def pause_polling(self) -> None:
        """Temporarily stop periodic reads so a PLC command can use the bus now."""
        self._polling_paused = True
        self._wake_event.set()

    def resume_polling(self) -> None:
        """Resume periodic reads after an urgent PLC command finishes."""
        self._polling_paused = False
        self._wake_event.set()

    def on_sensor_data(self, callback: Callable[[DeviceStatus], None]) -> None:
        self._sensor_callbacks.append(callback)

    def on_plc_status(self, callback: Callable[[Optional[object]], None]) -> None:
        self._plc_callbacks.append(callback)

    def on_command_result(self, callback: Callable[[str, bool], None]) -> None:
        self._command_callbacks.append(callback)

    def on_error(self, callback: Callable[[str], None]) -> None:
        self._error_callbacks.append(callback)

    def start(self) -> None:
        if self._running and self._thread and self._thread.is_alive():
            return
        import threading

        self._running = True
        self._wake_event.clear()
        self._thread = threading.Thread(target=self._loop, name="Modbus-Bus-Scheduler", daemon=True)
        self._thread.start()
        logger.info("ModbusBusScheduler: started optimized polling")

    def stop(self) -> None:
        self._running = False
        self._wake_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("ModbusBusScheduler: stopped")

    def is_running(self) -> bool:
        return self._running

    def enqueue_command(self, name: str, callback: Callable[[], bool]) -> bool:
        """Compatibility shim: run command immediately instead of queueing it."""
        import threading

        threading.Thread(
            target=self._run_priority_command,
            args=(name, callback),
            name=f"PLC-Cmd-{name}",
            daemon=True,
        ).start()
        return True

    def _run_priority_command(self, name: str, callback: Callable[[], bool]) -> None:
        ok = False
        try:
            ok = bool(callback())
        except Exception as exc:
            self._emit_error(f"Lỗi PLC command {name}: {exc}")
        self._emit_command_result(name, ok)

    def _loop(self) -> None:
        next_sensor = 0.0
        next_plc = 0.0
        while self._running:
            if self._polling_paused:
                self._wake_event.wait(timeout=0.005)
                self._wake_event.clear()
                continue

            now = time.monotonic()
            did_work = False

            if now >= next_sensor:
                status = self._read_sensor_force()
                if status is not None:
                    self._emit_sensor(status)
                next_sensor = time.monotonic() + self._sensor_interval_s
                did_work = True

            now = time.monotonic()
            if now >= next_plc:
                if self._recording_active:
                    plc_status = self._read_plc_realtime()
                    next_plc = time.monotonic() + self._plc_realtime_interval_s
                else:
                    plc_status = self._read_plc_full_status()
                    next_plc = time.monotonic() + self._plc_status_interval_s
                self._emit_plc(plc_status)
                did_work = True

            if not did_work:
                now = time.monotonic()
                sleep_s = min(max(0.001, next_sensor - now), max(0.001, next_plc - now), 0.02)
                self._wake_event.wait(timeout=sleep_s)
                self._wake_event.clear()

    def _read_sensor_force(self) -> Optional[DeviceStatus]:
        start = time.perf_counter()
        try:
            regs = self._client.read_registers(REG_NET_WEIGHT_HI, 2, self._sensor_slave_id)
            if regs is None or len(regs) < 2:
                return None
            net_val = self._decode_float32(regs[0], regs[1])
            self._record_force_timing((time.perf_counter() - start) * 1000.0)
            return DeviceStatus(
                connected=True,
                is_stable=True,
                is_fullscale=False,
                net_weight=net_val,
                gross_weight=0.0,
                tare_weight=0.0,
                max_net_weight=0.0,
                min_net_weight=0.0,
                raw_status_reg=0,
            )
        except Exception as exc:
            self._emit_error(f"Lỗi đọc lực ZE-SG3: {exc}")
            return None

    def _read_plc_realtime(self) -> Optional[PlcRealtimeState]:
        try:
            cycle_angle = self._client.read_registers(123, 2, self._plc_slave_id)
            if cycle_angle is None or len(cycle_angle) < 2:
                return None
            done = self._client.read_register(134, self._plc_slave_id)
            return PlcRealtimeState(
                current_cycle=int(cycle_angle[0]) & 0xFFFF,
                current_angle_x100=decode_signed_16(cycle_angle[1]),
                test_done=0 if done is None else (int(done) & 0xFFFF),
            )
        except Exception:
            return None

    def _read_plc_full_status(self) -> Optional[PlcStatus]:
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

    def _record_force_timing(self, elapsed_ms: float) -> None:
        self._force_timings_ms.append(elapsed_ms)
        if len(self._force_timings_ms) >= 100:
            values = self._force_timings_ms
            avg = sum(values) / len(values)
            logger.info(
                "ZE-SG3 force read timing: min=%.2fms avg=%.2fms max=%.2fms samples=%d",
                min(values),
                avg,
                max(values),
                len(values),
            )
            values.clear()

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

    def _emit_plc(self, status: Optional[object]) -> None:
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
