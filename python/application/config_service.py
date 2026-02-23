"""
Application Layer – Config Service
====================================
SRP: Chịu trách nhiệm duy nhất = đọc/ghi cấu hình thiết bị ZE-SG3
thông qua IModbusClient. Không biết đến UI, không biết đến pymodbus cụ thể.
"""

import logging
from typing import Optional

from domain.constants import (
    REG_MEASURE_UNIT, REG_MEASURE_TYPE, REG_CALIB_MODE,
    REG_CELL_SENS_HI, REG_CELL_FS_HI,
    REG_FILTER_LEVEL,
)
from domain.entities import DeviceConfig
from application.interfaces import IModbusClient

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Use Case: Đọc và ghi cấu hình vào thiết bị ZE-SG3.

    Phụ thuộc vào IModbusClient (Dependency Injection qua constructor).
    High-level policy không phụ thuộc vào implementation cụ thể.
    """

    def __init__(self, client: IModbusClient):
        self._client = client

    def read_config(self, slave_id: int = 1) -> Optional[DeviceConfig]:
        """
        Đọc cấu hình hiện tại từ thiết bị.
        Trả về DeviceConfig nếu thành công, None nếu lỗi.
        """
        try:
            unit = self._client.read_register(REG_MEASURE_UNIT, slave_id)
            mtype = self._client.read_register(REG_MEASURE_TYPE, slave_id)
            filt = self._client.read_register(REG_FILTER_LEVEL, slave_id)
            calib = self._client.read_register(REG_CALIB_MODE, slave_id)

            cell_fs = self._client.read_float32(REG_CELL_FS_HI, slave_id)
            cell_sens = self._client.read_float32(REG_CELL_SENS_HI, slave_id)

            if any(v is None for v in [unit, mtype, filt, calib, cell_fs, cell_sens]):
                logger.warning("ConfigService: Không đọc được một số thanh ghi")
                return None

            cfg = DeviceConfig(
                measure_unit=unit,
                measure_type=mtype,
                cell_full_scale=cell_fs,
                cell_sensitivity=cell_sens,
                filter_level=filt,
                calib_mode=calib,
                slave_id=slave_id,
            )
            logger.info(f"ConfigService: Đọc cấu hình thành công: {cfg}")
            return cfg

        except Exception as e:
            logger.error(f"ConfigService: Lỗi đọc cấu hình: {e}")
            return None

    def write_config(self, config: DeviceConfig) -> bool:
        """
        Ghi cấu hình lên thiết bị.
        Trả về True nếu tất cả thanh ghi ghi thành công.
        """
        if not config.validate():
            logger.error("ConfigService: Cấu hình không hợp lệ, hủy ghi")
            return False

        sid = config.slave_id
        try:
            results = [
                self._client.write_register(REG_MEASURE_UNIT, config.measure_unit, sid),
                self._client.write_register(REG_MEASURE_TYPE, config.measure_type, sid),
                self._client.write_register(REG_FILTER_LEVEL, config.filter_level, sid),
                self._client.write_register(REG_CALIB_MODE, config.calib_mode, sid),
                self._client.write_float32(REG_CELL_FS_HI, config.cell_full_scale, sid),
                self._client.write_float32(REG_CELL_SENS_HI, config.cell_sensitivity, sid),
            ]
            success = all(results)
            if success:
                logger.info("ConfigService: Ghi cấu hình thành công")
            else:
                logger.warning("ConfigService: Một số thanh ghi ghi thất bại")
            return success

        except Exception as e:
            logger.error(f"ConfigService: Lỗi ghi cấu hình: {e}")
            return False

    def send_command(self, command_value: int, slave_id: int = 1) -> bool:
        """
        Ghi lệnh vào Command Register (40080).
        VD: CMD_TARE=49914, CMD_RESTART=43948
        """
        from domain.constants import REG_COMMAND
        try:
            ok = self._client.write_register(REG_COMMAND, command_value, slave_id)
            logger.info(f"ConfigService: Gửi lệnh {command_value} → {'OK' if ok else 'FAIL'}")
            return ok
        except Exception as e:
            logger.error(f"ConfigService: Lỗi gửi lệnh: {e}")
            return False
