"""
Application Layer – Data Collector Service
===========================================
SRP: Chịu trách nhiệm duy nhất = thu thập dữ liệu từ thiết bị theo chu kỳ.

Dùng queue.Queue để thread-safe signal từ polling thread
đến UI thread (PyQt5 hoặc bất kỳ consumer nào).
"""

import logging
import queue
import threading
import time
from typing import Callable, Optional

from domain.constants import (
    REG_NET_WEIGHT_HI, REG_STATUS, REG_GROSS_WEIGHT_HI,
    REG_TARE_WEIGHT_HI, REG_MAX_NET_HI, REG_MIN_NET_HI,
    REG_ADC_RAW_FILT_HI,
    STATUS_BIT_STABLE, STATUS_BIT_FULLSCALE,
    DEFAULT_SAMPLE_INTERVAL_MS,
)
from domain.entities import DeviceStatus, SampleData
from application.interfaces import IModbusClient

logger = logging.getLogger(__name__)


class DataCollectorService:
    """
    Polling thread thu thập dữ liệu từ ZE-SG3 theo chu kỳ định sẵn.

    Callback-based: consumers đăng ký qua on_data / on_error.
    Thread-safe: dùng threading.Event để stop và queue không locking.
    """

    def __init__(self, client: IModbusClient, slave_id: int = 1):
        self._client = client
        self._slave_id = slave_id
        self._interval_ms: int = DEFAULT_SAMPLE_INTERVAL_MS
        self._running = False
        self._paused = False
        self._wake_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._data_callbacks: list = []
        self._error_callbacks: list = []

    # === Public API ===

    def set_interval(self, ms: int) -> None:
        """Thay đổi chu kỳ lấy mẫu (ms). Áp dụng ngay lập tức."""
        self._interval_ms = max(1, ms)
        self._wake_event.set()  # Đánh thức sleep hiện tại nếu có

    def on_data(self, callback: Callable[[DeviceStatus], None]) -> None:
        """Đăng ký callback nhận DeviceStatus mỗi chu kỳ. Thread-safe."""
        self._data_callbacks.append(callback)

    def on_error(self, callback: Callable[[str], None]) -> None:
        """Đăng ký callback khi có lỗi đọc."""
        self._error_callbacks.append(callback)

    def pause_polling(self) -> None:
        """Tạm dừng đọc sensor để nhường bus cho lệnh PLC ưu tiên."""
        self._paused = True
        self._wake_event.set()

    def resume_polling(self) -> None:
        """Tiếp tục đọc sensor sau lệnh PLC ưu tiên."""
        self._paused = False
        self._wake_event.set()

    def start(self) -> None:
        """Bắt đầu polling thread. Idempotent – gọi nhiều lần không vấn đề."""
        if self._running and self._thread and self._thread.is_alive():
            return
        self._running = True
        self._wake_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="ZE-SG3-Poller",
            daemon=True
        )
        self._thread.start()
        logger.info("DataCollectorService: Đã bắt đầu polling")

    def stop(self) -> None:
        """Dừng polling thread và chờ nó kết thúc."""
        self._running = False
        self._wake_event.set() # Đánh thức để thoát loop
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("DataCollectorService: Đã dừng polling")

    def is_running(self) -> bool:
        return self._running

    # === Internal ===

    def _poll_loop(self) -> None:
        """Vòng lặp polling chính – chạy trong daemon thread."""
        while self._running:
            if self._paused:
                self._wake_event.clear()
                self._wake_event.wait(timeout=0.005)
                continue

            start = time.monotonic()
            try:
                status = self._read_device_status()
                if status is not None:
                    for cb in self._data_callbacks:
                        try:
                            cb(status)
                        except Exception as cb_err:
                            logger.error(f"DataCollector callback error: {cb_err}")
            except Exception as e:
                err_msg = f"Lỗi đọc Modbus: {e}"
                logger.warning(err_msg)
                for cb in self._error_callbacks:
                    try:
                        cb(err_msg)
                    except Exception:
                        pass

            # Ngủ để đạt dúng interval
            elapsed = time.monotonic() - start
            target_s = self._interval_ms / 1000.0
            
            if elapsed < target_s:
                # Trên Windows, wait() có độ phân giải thấp (~15ms)
                # Chúng ta dùng wait để cho phép stop() ngắt ngay lập tức
                sleep_s = target_s - elapsed
                self._wake_event.clear()
                self._wake_event.wait(timeout=sleep_s)
            else:
                # Nếu đã quá muộn (đọc chậm hơn interval), không ngủ nữa
                # Yield để tránh treo CPU hoàn toàn
                time.sleep(0.0001)

    def _read_device_status(self) -> Optional[DeviceStatus]:
        """Đọc lực realtime nhanh nhất: chỉ 2 thanh ghi Net Weight Float32."""
        sid = self._slave_id
        regs = self._client.read_registers(REG_NET_WEIGHT_HI, 2, sid)
        if regs is None or len(regs) < 2:
            return None

        net_val = self._decode_float32(regs[0], regs[1])
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

    def _read_device_status_fallback(self) -> Optional[DeviceStatus]:
        """Cách đọc từng phần (chậm hơn) nếu block read thất bại."""
        sid = self._slave_id
        net = self._client.read_float32(REG_NET_WEIGHT_HI, sid)
        if net is None: return None
        
        status_raw = self._client.read_register(REG_STATUS, sid) or 0
        gross = self._client.read_float32(REG_GROSS_WEIGHT_HI, sid) or 0.0
        tare  = self._client.read_float32(REG_TARE_WEIGHT_HI, sid) or 0.0
        max_n = self._client.read_float32(REG_MAX_NET_HI, sid) or 0.0
        min_n = self._client.read_float32(REG_MIN_NET_HI, sid) or 0.0

        return DeviceStatus(
            connected=True,
            is_stable=(status_raw & STATUS_BIT_STABLE) != 0,
            is_fullscale=(status_raw & STATUS_BIT_FULLSCALE) != 0,
            net_weight=net,
            gross_weight=gross,
            tare_weight=tare,
            max_net_weight=max_n,
            min_net_weight=min_n,
            raw_status_reg=status_raw,
        )

    def _decode_float32(self, hi: int, lo: int) -> float:
        import struct
        try:
            packed = struct.pack('>HH', hi & 0xFFFF, lo & 0xFFFF)
            return struct.unpack('>f', packed)[0]
        except Exception:
            return 0.0
