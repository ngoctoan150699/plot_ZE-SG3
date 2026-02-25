"""
Infrastructure Layer – Modbus TCP Client
=========================================
Implement IModbusClient cho giao thức Modbus TCP/IP.
LSP: Thay thế hoàn toàn ModbusRtuClient mà không ảnh hưởng Application Layer.
"""

import threading
import logging
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
        _SLAVE_KWARG = 'slave'
    except ImportError:
        _PyModbusTcp = None
        _SLAVE_KWARG = 'unit'


class ModbusTcpClient(IModbusClient):
    """
    Kết nối Modbus TCP/IP qua Ethernet.
    Implements IModbusClient – Application Layer dùng interface, không biết TCP hay RTU.
    """

    def __init__(self, host: str, port: int = 502, timeout: float = 1.0):
        if _PyModbusTcp is None:
            raise ImportError("pymodbus chưa được cài đặt. Chạy: pip install pymodbus")

        self._host = host
        self._port = port
        self._client = _PyModbusTcp(host=host, port=port, timeout=timeout)
        self._connected = False
        self._lock = threading.Lock()
        logger.info(f"ModbusTcpClient: Khởi tạo {host}:{port}")

    def connect(self) -> bool:
        with self._lock:
            try:
                self._connected = self._client.connect()
                if self._connected:
                    logger.info(f"ModbusTcpClient: Kết nối thành công {self._host}:{self._port}")
                else:
                    logger.warning(f"ModbusTcpClient: Không thể kết nối {self._host}:{self._port}")
                return self._connected
            except Exception as e:
                logger.error(f"ModbusTcpClient: Lỗi connect: {e}")
                self._connected = False
                return False

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
        with self._lock:
            try:
                result = self._client.read_holding_registers(address, 1, **{_SLAVE_KWARG: slave_id})
                if result and hasattr(result, 'registers'):
                    return result.registers[0]
                return None
            except Exception as e:
                logger.debug(f"ModbusTcpClient read_register({address}): {e}")
                return None

    def read_registers(self, address: int, count: int, slave_id: int = 1) -> Optional[list]:
        with self._lock:
            try:
                result = self._client.read_holding_registers(address, count, **{_SLAVE_KWARG: slave_id})
                if result and hasattr(result, 'registers') and len(result.registers) >= count:
                    return list(result.registers)
                return None
            except Exception as e:
                logger.debug(f"ModbusTcpClient read_registers({address},{count}): {e}")
                return None

    def write_register(self, address: int, value: int, slave_id: int = 1) -> bool:
        with self._lock:
            try:
                result = self._client.write_register(address, int(value), **{_SLAVE_KWARG: slave_id})
                if result is None: return False
                if hasattr(result, 'isError'):
                    return not result.isError() if callable(result.isError) else not result.isError
                return True
            except Exception as e:
                logger.debug(f"ModbusTcpClient write_register({address},{value}): {e}")
                return False

    def write_registers(self, address: int, values: list, slave_id: int = 1) -> bool:
        with self._lock:
            try:
                result = self._client.write_registers(address, values, **{_SLAVE_KWARG: slave_id})
                if result is None: return False
                if hasattr(result, 'isError'):
                    return not result.isError() if callable(result.isError) else not result.isError
                return True
            except Exception as e:
                logger.debug(f"ModbusTcpClient write_registers({address},{values}): {e}")
                return False

