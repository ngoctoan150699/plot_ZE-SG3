"""
Infrastructure Layer – Modbus TCP Client
========================================
Implement IModbusClient cho giao thức Modbus TCP/IP.
LSP: Thay thế hoàn toàn ModbusRtuClient mà không ảnh hưởng Application Layer.
"""

import logging
import threading
import time
from typing import Optional

from application.interfaces import IModbusClient

logger = logging.getLogger(__name__)

# === Hỗ trợ cả pymodbus v2.x và v3.x ===
try:
    from pymodbus.client.sync import ModbusTcpClient as _PyModbusTcp
    _SLAVE_KWARG = 'unit'
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient as _PyModbusTcp
        import inspect as _inspect
        _sig = _inspect.signature(_PyModbusTcp.read_holding_registers)
        _SLAVE_KWARG = 'device_id' if 'device_id' in _sig.parameters else 'slave'
    except ImportError:
        _PyModbusTcp = None
        _SLAVE_KWARG = 'unit'


class ModbusTcpClient(IModbusClient):
    """Kết nối Modbus TCP/IP qua Ethernet, giữ socket lâu dài và tự reconnect."""

    def __init__(self, host: str, port: int = 502, timeout: float = 0.08):
        if _PyModbusTcp is None:
            raise ImportError("pymodbus chưa được cài đặt. Chạy: pip install pymodbus")

        self._host = host
        self._port = port
        self._timeout = timeout
        self._client = _PyModbusTcp(host=host, port=port, timeout=timeout)
        self._connected = False
        self._lock = threading.Lock()
        self._next_reconnect_at = 0.0
        self._reconnect_interval_s = 1.0
        self._warn_ms = 120.0
        logger.info("ModbusTcpClient: Khởi tạo %s:%s", host, port)

    def _recreate_client(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
        self._client = _PyModbusTcp(host=self._host, port=self._port, timeout=self._timeout)

    def _ensure_connected_locked(self) -> bool:
        if self._connected:
            return True
        now = time.monotonic()
        if now < self._next_reconnect_at:
            return False
        self._next_reconnect_at = now + self._reconnect_interval_s
        self._recreate_client()
        try:
            self._connected = bool(self._client.connect())
        except Exception as exc:
            logger.debug("ModbusTcpClient reconnect failed: %s", exc)
            self._connected = False
        if self._connected:
            logger.info("ModbusTcpClient: Reconnect thành công %s:%s", self._host, self._port)
        return self._connected

    def _mark_error_locked(self, action: str, exc: Exception | None = None) -> None:
        if exc:
            logger.debug("ModbusTcpClient %s: %s", action, exc)
        self._connected = False
        self._next_reconnect_at = time.monotonic() + self._reconnect_interval_s

    def connect(self) -> bool:
        with self._lock:
            self._next_reconnect_at = 0.0
            self._connected = False
            ok = self._ensure_connected_locked()
            if ok:
                logger.info("ModbusTcpClient: Kết nối thành công %s:%s", self._host, self._port)
            else:
                logger.warning("ModbusTcpClient: Không thể kết nối %s:%s", self._host, self._port)
            return ok

    def disconnect(self) -> None:
        with self._lock:
            try:
                self._client.close()
            except Exception:
                pass
            self._connected = False
            logger.info("ModbusTcpClient: Đã ngắt kết nối")

    def is_connected(self) -> bool:
        return self._connected

    def read_register(self, address: int, slave_id: int = 1) -> Optional[int]:
        regs = self.read_registers(address, 1, slave_id)
        return regs[0] if regs else None

    def read_registers(self, address: int, count: int, slave_id: int = 1) -> Optional[list]:
        with self._lock:
            if not self._ensure_connected_locked():
                return None
            start = time.perf_counter()
            try:
                result = self._client.read_holding_registers(address, count=count, **{_SLAVE_KWARG: slave_id})
                elapsed = (time.perf_counter() - start) * 1000.0
                if elapsed > self._warn_ms:
                    logger.warning("TCP read slow: addr=%s count=%s slave=%s %.1fms", address, count, slave_id, elapsed)
                if result and hasattr(result, 'registers') and len(result.registers) >= count:
                    return list(result.registers)
                # Không reconnect ngay vì một frame empty/timeout đơn lẻ; giữ TCP socket ổn định.
                return None
            except Exception as e:
                self._mark_error_locked(f"read_registers({address},{count})", e)
                return None

    def write_register(self, address: int, value: int, slave_id: int = 1) -> bool:
        with self._lock:
            if not self._ensure_connected_locked():
                return False
            start = time.perf_counter()
            try:
                result = self._client.write_register(address, int(value), **{_SLAVE_KWARG: slave_id})
                elapsed = (time.perf_counter() - start) * 1000.0
                if elapsed > self._warn_ms:
                    logger.warning("TCP write slow: addr=%s slave=%s %.1fms", address, slave_id, elapsed)
                if result is None:
                    self._mark_error_locked(f"write_register({address}) empty")
                    return False
                return not result.isError() if hasattr(result, 'isError') and callable(result.isError) else True
            except Exception as e:
                self._mark_error_locked(f"write_register({address},{value})", e)
                return False

    def write_registers(self, address: int, values: list, slave_id: int = 1) -> bool:
        with self._lock:
            if not self._ensure_connected_locked():
                return False
            start = time.perf_counter()
            try:
                result = self._client.write_registers(address, values, **{_SLAVE_KWARG: slave_id})
                elapsed = (time.perf_counter() - start) * 1000.0
                if elapsed > self._warn_ms:
                    logger.warning("TCP write_many slow: addr=%s count=%s slave=%s %.1fms", address, len(values), slave_id, elapsed)
                if result is None:
                    self._mark_error_locked(f"write_registers({address}) empty")
                    return False
                return not result.isError() if hasattr(result, 'isError') and callable(result.isError) else True
            except Exception as e:
                self._mark_error_locked(f"write_registers({address},{values})", e)
                return False
