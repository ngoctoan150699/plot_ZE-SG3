"""
Application Layer – Config Service
====================================
SRP: Chịu trách nhiệm duy nhất = đọc/ghi cấu hình thiết bị ZE-SG3
thông qua IModbusClient. Không biết đến UI, không biết đến pymodbus cụ thể.
"""

import logging
from typing import Optional, Tuple

from domain.constants import (
    REG_MEASURE_UNIT, REG_MEASURE_TYPE, REG_CALIB_MODE,
    REG_CELL_SENS_HI, REG_CELL_FS_HI, REG_STD_WEIGHT_HI,
    REG_FILTER_LEVEL, REG_ANALOG_OUT_TYPE, REG_DIO_TYPE,
    REG_DELTA_WEIGHT_HI, REG_DELTA_TIME, REG_RESOLUTION_MODE,
    REG_FACTORY_TARE_HI, REG_ADDRESS, REG_BAUD, REG_PARITY,
    REG_ADC_SPS
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
        Đọc toàn bộ cấu hình từ thiết bị.
        """
        try:
            # 16-bit registers
            unit = self._client.read_register(REG_MEASURE_UNIT, slave_id)
            mtype = self._client.read_register(REG_MEASURE_TYPE, slave_id)
            ana_out = self._client.read_register(REG_ANALOG_OUT_TYPE, slave_id)
            dio = self._client.read_register(REG_DIO_TYPE, slave_id)
            calib = self._client.read_register(REG_CALIB_MODE, slave_id)
            filt = self._client.read_register(REG_FILTER_LEVEL, slave_id)
            adc_sps = self._client.read_register(REG_ADC_SPS, slave_id)
            res_mode = self._client.read_register(REG_RESOLUTION_MODE, slave_id)
            d_time = self._client.read_register(REG_DELTA_TIME, slave_id)
            
            # Comm settings
            addr = self._client.read_register(REG_ADDRESS, slave_id)
            baud = self._client.read_register(REG_BAUD, slave_id)
            pari = self._client.read_register(REG_PARITY, slave_id)

            # Float32 registers
            cell_sens = self._client.read_float32(REG_CELL_SENS_HI, slave_id)
            cell_fs = self._client.read_float32(REG_CELL_FS_HI, slave_id)
            std_w = self._client.read_float32(REG_STD_WEIGHT_HI, slave_id)
            d_weight = self._client.read_float32(REG_DELTA_WEIGHT_HI, slave_id)
            fac_tare = self._client.read_float32(REG_FACTORY_TARE_HI, slave_id)

            if any(v is None for v in [unit, mtype, filt, calib, cell_fs, cell_sens]):
                logger.warning("ConfigService: Không đọc được một số thanh ghi quan trọng")
                return None

            cfg = DeviceConfig(
                measure_unit=unit,
                measure_type=mtype,
                analog_out_type=ana_out if ana_out is not None else 0,
                dio_type=dio if dio is not None else 0,
                calib_mode=calib,
                target_address=addr if addr is not None else slave_id,
                target_baud=baud if baud is not None else 5,
                target_parity=pari if pari is not None else 0,
                cell_sensitivity=cell_sens,
                cell_full_scale=cell_fs,
                std_weight=std_w if std_w is not None else 0.0,
                delta_weight=d_weight if d_weight is not None else 0.01,
                delta_time=d_time if d_time is not None else 10,
                filter_level=filt,
                adc_sps=adc_sps if adc_sps is not None else 3,
                resolution_mode=res_mode if res_mode is not None else 0,
                factory_tare=fac_tare if fac_tare is not None else 0.0,
                slave_id=slave_id,
            )
            logger.info("ConfigService: Đọc cấu hình hoàn chỉnh thành công")
            return cfg

        except Exception as e:
            logger.error(f"ConfigService: Lỗi đọc cấu hình: {e}")
            return None

    def write_config(self, config: DeviceConfig) -> Tuple[bool, list]:
        """
        Ghi cấu hình hoàn chỉnh lên thiết bị.
        Trả về (success, failed_fields_list).
        """
        if not config.validate():
            logger.error("ConfigService: Cấu hình không hợp lệ, hủy ghi")
            return False, ["Validation Failed"]

        sid = config.slave_id
        failed_fields = []
        
        # Danh sách các write cần thực hiện để dễ debug
        writes = [
            ("Measure Unit", lambda: self._client.write_register(REG_MEASURE_UNIT, config.measure_unit, sid)),
            ("Measure Type", lambda: self._client.write_register(REG_MEASURE_TYPE, config.measure_type, sid)),
            ("Analog Out",  lambda: self._client.write_register(REG_ANALOG_OUT_TYPE, config.analog_out_type, sid)),
            ("DIO Type",     lambda: self._client.write_register(REG_DIO_TYPE, config.dio_type, sid)),
            ("Calib Mode",   lambda: self._client.write_register(REG_CALIB_MODE, config.calib_mode, sid)),
            ("Filter Level", lambda: self._client.write_register(REG_FILTER_LEVEL, config.filter_level, sid)),
            ("ADC SPS",     lambda: self._client.write_register(REG_ADC_SPS, config.adc_sps, sid)),
            ("Resolution",   lambda: self._client.write_register(REG_RESOLUTION_MODE, config.resolution_mode, sid)),
            ("Delta Time",   lambda: self._client.write_register(REG_DELTA_TIME, config.delta_time, sid)),
            ("Address",      lambda: self._client.write_register(REG_ADDRESS, config.target_address, sid)),
            ("Baud Index",   lambda: self._client.write_register(REG_BAUD, config.target_baud, sid)),
            ("Parity",       lambda: self._client.write_register(REG_PARITY, config.target_parity, sid)),
            ("Full Scale",   lambda: self._client.write_float32(REG_CELL_FS_HI, config.cell_full_scale, sid)),
            ("Sensitivity",  lambda: self._client.write_float32(REG_CELL_SENS_HI, config.cell_sensitivity, sid)),
            ("Std Weight",   lambda: self._client.write_float32(REG_STD_WEIGHT_HI, config.std_weight, sid)),
            ("Delta Weight", lambda: self._client.write_float32(REG_DELTA_WEIGHT_HI, config.delta_weight, sid)),
            ("Factory Tare", lambda: self._client.write_float32(REG_FACTORY_TARE_HI, config.factory_tare, sid)),
        ]

        for name, func in writes:
            try:
                if not func():
                    logger.warning(f"ConfigService: Ghi '{name}' thất bại")
                    failed_fields.append(name)
            except Exception as e:
                logger.error(f"ConfigService: Lỗi khi ghi '{name}': {e}")
                failed_fields.append(f"{name} (Error)")

        success = (len(failed_fields) == 0)
        if success:
            logger.info("ConfigService: Ghi cấu hình hoàn chỉnh thành công")
            
        return success, failed_fields

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

    def tare_ram(self, slave_id: int = 1) -> bool:
        """
        Lấy Tare lưu vào RAM (mất khi restart).
        Nhanh hơn Flash Tare, phù hợp cho tare thường xuyên.
        """
        from domain.constants import CMD_TARE_RAM
        return self.send_command(CMD_TARE_RAM, slave_id)

    def tare_flash(self, slave_id: int = 1) -> bool:
        """
        Lấy Tare lưu vào Flash (bền vững, không mất khi restart).
        """
        from domain.constants import CMD_TARE
        return self.send_command(CMD_TARE, slave_id)

    def calibrate_with_sample_weight(
        self, std_weight: float, slave_id: int = 1
    ) -> bool:
        """
        Quy trình hiệu chuẩn bằng vật mẫu (Standard Weight Calibration).
        
        Bước 1 (do user thực hiện trước khi gọi hàm này): Tare khi chưa có tải
        Bước 2: Ghi giá trị vật mẫu vào register 40018-19
        Bước 3: Gửi lệnh hiệu chuẩn mẫu (CMD 50700) → Flash
        
        Trả về True nếu cả 2 bước đều thành công.
        """
        from domain.constants import (
            REG_STD_WEIGHT_HI, REG_CALIB_MODE, CMD_SAMPLE_CALIB
        )
        try:
            # 1. Đặt chế độ hiệu chuẩn sang Standard Weight (1)
            ok_mode = self._client.write_register(REG_CALIB_MODE, 1, slave_id)
            if not ok_mode:
                logger.error("ConfigService: Không thể đặt chế độ hiệu chuẩn Standard Weight")
                return False

            # 2. Ghi giá trị vật mẫu vào register
            ok_weight = self._client.write_float32(REG_STD_WEIGHT_HI, std_weight, slave_id)
            if not ok_weight:
                logger.error("ConfigService: Không thể ghi giá trị vật mẫu")
                return False

            # 3. Gửi lệnh hiệu chuẩn (50700) → lưu Flash
            ok_cmd = self.send_command(CMD_SAMPLE_CALIB, slave_id)
            if not ok_cmd:
                logger.error("ConfigService: Lệnh hiệu chuẩn mẫu thất bại")
                return False

            logger.info(f"ConfigService: Hiệu chuẩn mẫu thành công (std_weight={std_weight})")
            return True

        except Exception as e:
            logger.error(f"ConfigService: Lỗi hiệu chuẩn mẫu: {e}")
            return False

    def reset_max(self, slave_id: int = 1) -> bool:
        """Xóa giá trị Max Net Weight."""
        from domain.constants import CMD_RESET_MAX
        return self.send_command(CMD_RESET_MAX, slave_id)

    def reset_min(self, slave_id: int = 1) -> bool:
        """Xóa giá trị Min Net Weight."""
        from domain.constants import CMD_RESET_MIN
        return self.send_command(CMD_RESET_MIN, slave_id)
