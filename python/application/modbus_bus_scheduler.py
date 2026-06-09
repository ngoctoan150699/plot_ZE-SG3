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
    STATUS_BIT_STABLE,
    STATUS_BIT_FULLSCALE,
)
from domain.entities import DeviceStatus
from domain.plc_protocol import PlcRealtimeState, PlcStatus, decode_signed_16

logger = logging.getLogger(__name__)


import queue
import threading

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
        self._client = client
        self._sensor_slave_id = sensor_slave_id
        self._plc_slave_id = plc_slave_id
        self._sensor_interval_s = max(0.001, sensor_interval_ms / 1000.0)
        self._plc_status_interval_s = max(0.2, plc_interval_ms / 1000.0)
        self._plc_realtime_interval_s = 0.05
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
        
        # Hàng đợi command và danh sách clear register tự động
        self._command_queue: queue.Queue = queue.Queue()
        self._pending_clears: list[dict] = []
        self._last_max_net = 0.0
        self._last_min_net = 0.0

    def set_client(self, client: IModbusClient, sensor_slave_id: int = 1, plc_slave_id: int = 2) -> None:
        self._client = client
        self._sensor_slave_id = sensor_slave_id
        self._plc_slave_id = plc_slave_id
        self._force_timings_ms.clear()
        self._last_max_net = 0.0
        self._last_min_net = 0.0
        
        # Clear hàng đợi khi đổi kết nối
        while not self._command_queue.empty():
            try:
                self._command_queue.get_nowait()
            except Exception:
                pass
        self._pending_clears.clear()

    def set_intervals(self, sensor_ms: int, plc_ms: int = 1000) -> None:
        self._sensor_interval_s = max(0.001, int(sensor_ms) / 1000.0)
        self._plc_status_interval_s = max(0.2, int(plc_ms) / 1000.0)
        self._wake_event.set()

    def set_recording_active(self, active: bool) -> None:
        self._recording_active = bool(active)
        if active:
            # Reset peak khi bắt đầu ghi
            self._last_max_net = -999999.0
            self._last_min_net = 999999.0
        self._wake_event.set()

    def pause_polling(self) -> None:
        """Temporarily stop periodic reads so a PLC configuration can use the bus now."""
        self._polling_paused = True
        self._wake_event.set()

    def resume_polling(self) -> None:
        """Resume periodic reads after configuration finishes."""
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
        """Đưa lệnh điều khiển PLC vào hàng đợi thực thi tuần tự trên thread chính."""
        self._command_queue.put((name, callback))
        self._wake_event.set()
        return True

    def schedule_clear_register(self, address: int, value: int, slave_id: int, delay_ms: int) -> None:
        """Lên lịch clear register (ví dụ xóa bit lệnh D100) trực tiếp trên thread chính."""
        clear_time = time.monotonic() + (max(0, delay_ms) / 1000.0)
        self._pending_clears.append({
            'address': address,
            'value': value,
            'slave_id': slave_id,
            'clear_time': clear_time
        })
        self._wake_event.set()

    def _loop(self) -> None:
        last_sensor = 0.0
        last_plc = 0.0
        bus_gap_s = 0.002
        idle_sleep_s = 0.002

        while self._running:
            now = time.monotonic()
            did_work = False

            # 1. Xử lý các lệnh clear register đã đến hạn
            if self._pending_clears:
                to_run = [item for item in self._pending_clears if now >= item['clear_time']]
                self._pending_clears = [item for item in self._pending_clears if now < item['clear_time']]
                for item in to_run:
                    try:
                        self._client.write_register(item['address'], item['value'], item['slave_id'])
                        logger.debug("Scheduler: cleared address %s to %s", item['address'], item['value'])
                    except Exception as exc:
                        logger.error("Scheduler clear register failed: %s", exc)
                    did_work = True
                    time.sleep(bus_gap_s)

            # 2. Xử lý hàng đợi command ưu tiên (RUN/STOP/CLAMP, v.v.)
            if not self._command_queue.empty():
                try:
                    name, callback = self._command_queue.get_nowait()
                    ok = False
                    try:
                        ok = bool(callback())
                        if ok:
                            # Nghỉ ngắn để simulator/PLC kịp xử lý
                            time.sleep(0.04)
                    except Exception as exc:
                        self._emit_error(f"Lỗi PLC command {name}: {exc}")
                    
                    self._emit_command_result(name, ok)
                    self._command_queue.task_done()
                except queue.Empty:
                    pass
                did_work = True
                time.sleep(bus_gap_s)

            # Nếu đang tạm dừng polling (ví dụ kết nối thiết bị)
            if self._polling_paused:
                self._wake_event.wait(timeout=idle_sleep_s)
                self._wake_event.clear()
                last_sensor = time.monotonic()
                last_plc = last_sensor
                continue

            # 3. Đọc dữ liệu lực của cảm biến định kỳ
            now = time.monotonic()
            if (now - last_sensor) >= self._sensor_interval_s:
                status = self._read_sensor_force()
                if status is not None:
                    self._emit_sensor(status)
                last_sensor = time.monotonic()
                did_work = True
                time.sleep(bus_gap_s)

            # 4. Đọc dữ liệu PLC định kỳ (Góc, chu kỳ, trạng thái)
            now = time.monotonic()
            plc_interval = self._plc_realtime_interval_s if self._recording_active else self._plc_status_interval_s
            if (now - last_plc) >= plc_interval:
                if self._recording_active:
                    plc_status = self._read_plc_realtime()
                else:
                    plc_status = self._read_plc_full_status()
                self._emit_plc(plc_status)
                last_plc = time.monotonic()
                did_work = True
                time.sleep(bus_gap_s)

            # 5. Nghỉ ngắn nếu không làm gì để giảm CPU
            if not did_work:
                self._wake_event.wait(timeout=idle_sleep_s)
                self._wake_event.clear()

    def _read_sensor_force(self) -> Optional[DeviceStatus]:
        start = time.perf_counter()
        try:
            # Khi đang record, chỉ đọc 15 thanh ghi (tới Status ở offset 14) thay vì 22
            count = 15 if self._recording_active else 22
            regs = self._client.read_registers(REG_NET_WEIGHT_HI, count, self._sensor_slave_id)
            if regs is None or len(regs) < count:
                return None
            
            net_val = self._decode_float32(regs[0], regs[1])
            gross_val = self._decode_float32(regs[2], regs[3])
            tare_val = self._decode_float32(regs[4], regs[5])
            raw_status = int(regs[14])
            is_stable = bool(raw_status & STATUS_BIT_STABLE)
            is_fullscale = bool(raw_status & STATUS_BIT_FULLSCALE)
            
            if count == 22:
                max_net_val = self._decode_float32(regs[18], regs[19])
                min_net_val = self._decode_float32(regs[20], regs[21])
                self._last_max_net = max_net_val
                self._last_min_net = min_net_val
            else:
                # Tự tính toán Peak Max/Min trong lúc record để tránh nghẽn bus
                if self._last_max_net == -999999.0 or net_val > self._last_max_net:
                    self._last_max_net = net_val
                if self._last_min_net == 999999.0 or net_val < self._last_min_net:
                    self._last_min_net = net_val
                max_net_val = self._last_max_net
                min_net_val = self._last_min_net
            
            self._record_force_timing((time.perf_counter() - start) * 1000.0)
            return DeviceStatus(
                connected=True,
                is_stable=is_stable,
                is_fullscale=is_fullscale,
                net_weight=net_val,
                gross_weight=gross_val,
                tare_weight=tare_val,
                max_net_weight=max_net_val,
                min_net_weight=min_net_val,
                raw_status_reg=raw_status,
            )
        except Exception as exc:
            self._emit_error(f"Lỗi đọc lực ZE-SG3: {exc}")
            return None

    def _read_plc_realtime(self) -> Optional[PlcRealtimeState]:
        try:
            regs = self._client.read_registers(
                PLC_STATUS_START_ADDRESS,
                PLC_STATUS_REGISTER_COUNT,
                self._plc_slave_id,
            )
            if regs is None or len(regs) < PLC_STATUS_REGISTER_COUNT:
                return None
            return PlcRealtimeState(
                current_cycle=int(regs[3]) & 0xFFFF,
                current_angle_x100=decode_signed_16(regs[4]),
                test_done=int(regs[14]) & 0xFFFF,
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

