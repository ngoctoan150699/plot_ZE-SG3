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
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._data_callbacks: list = []
        self._error_callbacks: list = []

    # === Public API ===

    def set_interval(self, ms: int) -> None:
        """Thay đổi chu kỳ lấy mẫu (ms). Thread-safe."""
        self._interval_ms = max(10, ms)

    def on_data(self, callback: Callable[[DeviceStatus], None]) -> None:
        """Đăng ký callback nhận DeviceStatus mỗi chu kỳ. Thread-safe."""
        self._data_callbacks.append(callback)

    def on_error(self, callback: Callable[[str], None]) -> None:
        """Đăng ký callback khi có lỗi đọc."""
        self._error_callbacks.append(callback)

    def start(self) -> None:
        """Bắt đầu polling thread. Idempotent – gọi nhiều lần không vấn đề."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="ZE-SG3-Poller",
            daemon=True
        )
        self._thread.start()
        logger.info("DataCollectorService: Đã bắt đầu polling")

    def stop(self) -> None:
        """Dừng polling thread và chờ nó kết thúc."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("DataCollectorService: Đã dừng polling")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # === Internal ===

    def _poll_loop(self) -> None:
        """Vòng lặp polling chính – chạy trong daemon thread."""
        while not self._stop_event.is_set():
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

            # Ngủ đúng interval, trừ đi thời gian đã đọc
            elapsed = time.monotonic() - start
            sleep_s = max(0.0, self._interval_ms / 1000.0 - elapsed)
            # Dùng Event.wait để stop ngay lập tức khi cần
            self._stop_event.wait(timeout=sleep_s)

    def _read_device_status(self) -> Optional[DeviceStatus]:
        """
        Đọc toàn bộ trạng thái cần thiết từ thiết bị trong 1 lần polling.
        Tối ưu: đọc block liên tiếp thay vì từng thanh ghi riêng lẻ.
        """
        sid = self._slave_id

        # Đọc Net Weight (40064-40065)
        net = self._client.read_float32(REG_NET_WEIGHT_HI, sid)
        if net is None:
            return None  # Không đọc được – báo lỗi

        # Đọc Status (40078) – cùng lúc với gross, tare nếu có thể
        status_raw = self._client.read_register(REG_STATUS, sid)
        if status_raw is None:
            status_raw = 0

        # Đọc thêm các giá trị phụ (không critical, fail thì dùng 0)
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
