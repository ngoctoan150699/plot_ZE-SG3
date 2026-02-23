"""
Infrastructure Layer – Modbus RTU Client
=========================================
Implement IModbusClient cho giao thức Modbus RTU (RS-232/RS-485).
Tất cả phụ thuộc pymodbus được gói gọn tại đây – Application Layer không biết.
"""

import logging
from typing import Optional

from application.interfaces import IModbusClient
from domain.constants import MODBUS_TIMEOUT_S

logger = logging.getLogger(__name__)

# === Hỗ trợ cả pymodbus v2.x và v3.x ===
try:
    from pymodbus.client.sync import ModbusSerialClient as _PyModbusRtu
    _RTU_KWARGS = lambda port, baud, par, stop, bs, to: dict(
        port=port, method='rtu', baudrate=baud,
        parity=par, stopbits=stop, bytesize=bs, timeout=to
    )
    _SLAVE_KWARG = 'unit'
except ImportError:
    try:
        from pymodbus.client import ModbusSerialClient as _PyModbusRtu
        _RTU_KWARGS = lambda port, baud, par, stop, bs, to: dict(
            port=port, baudrate=baud, parity=par,
            stopbits=stop, bytesize=bs, timeout=to
        )
        _SLAVE_KWARG = 'slave'
    except ImportError:
        _PyModbusRtu = None
        _RTU_KWARGS = None
        _SLAVE_KWARG = 'unit'


class ModbusRtuClient(IModbusClient):
    """
    Kết nối Modbus RTU qua cổng COM / RS-485 USB Adapter.
    Implements IModbusClient (LSP: thay thế hoàn toàn cho TCP client).
    """

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
        self._client = _PyModbusRtu(
            **_RTU_KWARGS(port, baudrate, parity, stopbits, bytesize, timeout)
        )
        self._connected = False
        logger.info(f"ModbusRtuClient: Khởi tạo cổng {port} @ {baudrate} baud")

    def connect(self) -> bool:
        try:
            self._connected = self._client.connect()
            if self._connected:
                logger.info(f"ModbusRtuClient: Kết nối thành công {self._port}")
            else:
                logger.warning(f"ModbusRtuClient: Không thể kết nối {self._port}")
            return self._connected
        except Exception as e:
            logger.error(f"ModbusRtuClient: Lỗi connect: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
        self._connected = False
        logger.info("ModbusRtuClient: Đã ngắt kết nối")

    def is_connected(self) -> bool:
        return self._connected

    def read_register(self, address: int, slave_id: int = 1) -> Optional[int]:
        try:
            result = self._client.read_holding_registers(address, 1, **{_SLAVE_KWARG: slave_id})
            if result and hasattr(result, 'registers'):
                return result.registers[0]
            return None
        except Exception as e:
            logger.debug(f"ModbusRtuClient read_register({address}): {e}")
            return None

    def read_registers(self, address: int, count: int, slave_id: int = 1) -> Optional[list]:
        try:
            result = self._client.read_holding_registers(address, count, **{_SLAVE_KWARG: slave_id})
            if result and hasattr(result, 'registers') and len(result.registers) >= count:
                return list(result.registers)
            return None
        except Exception as e:
            logger.debug(f"ModbusRtuClient read_registers({address},{count}): {e}")
            return None

    def write_register(self, address: int, value: int, slave_id: int = 1) -> bool:
        try:
            result = self._client.write_register(address, int(value), **{_SLAVE_KWARG: slave_id})
            return result is not None and not hasattr(result, 'isError')
        except Exception as e:
            logger.debug(f"ModbusRtuClient write_register({address},{value}): {e}")
            return False
