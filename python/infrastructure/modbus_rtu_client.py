"""
Infrastructure Layer – Modbus RTU Client
=========================================
Implement IModbusClient cho giao thức Modbus RTU (RS-232/RS-485).
Tất cả phụ thuộc pymodbus được gói gọn tại đây – Application Layer không biết.
"""

import logging
import threading
import time
from typing import Optional

from application.interfaces import IModbusClient
from domain.constants import MODBUS_TIMEOUT_S

logger = logging.getLogger(__name__)

# === Hỗ trợ cả pymodbus v2.x và v3.x ===
try:
    from pymodbus.client.sync import ModbusSerialClient as _PyModbusRtu
    _RTU_KWARGS = lambda port, baud, par, stop, bs, to: dict(
        port=port, method='rtu', baudrate=baud,
        parity=par, stopbits=stop, bytesize=bs, timeout=to,
        retries=0, retry_on_empty=False, inter_byte_timeout=0.01
    )
    _SLAVE_KWARG = 'unit'
except ImportError:
    try:
        from pymodbus.client import ModbusSerialClient as _PyModbusRtu
        _RTU_KWARGS = lambda port, baud, par, stop, bs, to: dict(
            port=port, baudrate=baud, parity=par,
            stopbits=stop, bytesize=bs, timeout=to,
            retries=0, retry_on_empty=False, inter_byte_timeout=0.01
        )
        import inspect as _inspect
        _sig = _inspect.signature(_PyModbusRtu.read_holding_registers)
        _SLAVE_KWARG = 'device_id' if 'device_id' in _sig.parameters else 'slave'
    except ImportError:
        _PyModbusRtu = None
        _RTU_KWARGS = None
        _SLAVE_KWARG = 'unit'


class ModbusRtuClient(IModbusClient):
    """Kết nối Modbus RTU qua COM/RS485 với timeout ngắn, tự reconnect và đo latency."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        parity: str = 'N',
        stopbits: int = 1,
        bytesize: int = 8,
        timeout: float = MODBUS_TIMEOUT_S,
    ):
        if _PyModbusRtu is None:
            raise ImportError("pymodbus chưa được cài đặt. Chạy: pip install pymodbus")

        self._port = port
        self._baudrate = baudrate
        self._parity = parity
        self._stopbits = stopbits
        self._bytesize = bytesize
        self._timeout = timeout
        self._client = self._create_client()
        self._connected = False
        self._lock = threading.Lock()
        self._next_reconnect_at = 0.0
        self._reconnect_interval_s = 1.0
        self._warn_ms = 200.0
        logger.info("ModbusRtuClient: Khởi tạo cổng %s @ %s baud", port, baudrate)

    def _create_client(self):
        return _PyModbusRtu(**_RTU_KWARGS(
            self._port,
            self._baudrate,
            self._parity,
            self._stopbits,
            self._bytesize,
            self._timeout,
        ))

    def _recreate_client(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
        self._client = self._create_client()

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
            logger.debug("ModbusRtuClient reconnect failed: %s", exc)
            self._connected = False
        if self._connected:
            logger.info("ModbusRtuClient: Reconnect thành công %s", self._port)
        return self._connected

    def _mark_error_locked(self, action: str, exc: Optional[Exception] = None) -> None:
        if exc:
            logger.debug("ModbusRtuClient %s: %s", action, exc)
        self._connected = False
        self._next_reconnect_at = time.monotonic() + self._reconnect_interval_s

    def connect(self) -> bool:
        with self._lock:
            self._next_reconnect_at = 0.0
            self._connected = False
            ok = self._ensure_connected_locked()
            if ok:
                logger.info("ModbusRtuClient: Kết nối thành công %s", self._port)
            else:
                logger.warning("ModbusRtuClient: Không thể kết nối %s", self._port)
            return ok

    def disconnect(self) -> None:
        with self._lock:
            try:
                self._client.close()
            except Exception:
                pass
            self._connected = False
            logger.info("ModbusRtuClient: Đã ngắt kết nối")

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
                    logger.warning("RTU read slow: port=%s addr=%s count=%s slave=%s %.1fms", self._port, address, count, slave_id, elapsed)
                if result and hasattr(result, 'registers') and len(result.registers) >= count:
                    return list(result.registers)
                self._mark_error_locked(f"read_registers({address},{count}) empty")
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
                    logger.warning("RTU write slow: port=%s addr=%s slave=%s %.1fms", self._port, address, slave_id, elapsed)
                if result is None:
                    self._mark_error_locked(f"write_register({address}) empty")
                    return False
                if hasattr(result, 'isError'):
                    return not result.isError() if callable(result.isError) else not result.isError
                return True
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
                    logger.warning("RTU write_many slow: port=%s addr=%s count=%s slave=%s %.1fms", self._port, address, len(values), slave_id, elapsed)
                if result is None:
                    self._mark_error_locked(f"write_registers({address}) empty")
                    return False
                if hasattr(result, 'isError'):
                    return not result.isError() if callable(result.isError) else not result.isError
                return True
            except Exception as e:
                self._mark_error_locked(f"write_registers({address},{values})", e)
                return False
