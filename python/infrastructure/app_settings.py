"""
Infrastructure Layer – App Settings (JSON Persistence)
========================================================
Repository Pattern: Tách biệt việc lưu/tải cài đặt khỏi logic nghiệp vụ.
Dùng JSON file để lưu cấu hình kết nối và thiết bị giữa các lần chạy.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from application.interfaces import ISettingsRepository
from domain.entities import ConnectionConfig, DeviceConfig
from domain.constants import (
    DEFAULT_SLAVE_ID, DEFAULT_BAUDRATE, DEFAULT_TCP_PORT, DEFAULT_TCP_IP,
    DEFAULT_MEASURE_UNIT, DEFAULT_MEASURE_TYPE, DEFAULT_CELL_FULL_SCALE,
    DEFAULT_CELL_SENSITIVITY, DEFAULT_FILTER_LEVEL,
)

logger = logging.getLogger(__name__)

# File cài đặt lưu cùng thư mục với script chạy
_SETTINGS_FILE = Path(__file__).parent.parent / "settings.json"


class AppSettings(ISettingsRepository):
    """
    Lưu/tải cấu hình ứng dụng dưới dạng JSON.
    Idempotent: file không tồn tại → trả về giá trị mặc định.
    """

    def __init__(self, filepath: Optional[Path] = None):
        self._path = filepath or _SETTINGS_FILE
        self._data: dict = self._load_raw()

    def _load_raw(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"AppSettings: Đã tải settings từ {self._path}")
                    return data
            except Exception as e:
                logger.warning(f"AppSettings: Không đọc được settings.json: {e}")
        return {}

    def _save_raw(self) -> None:
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"AppSettings: Không lưu được settings.json: {e}")

    # === ISettingsRepository Implementation ===

    def load_connection_config(self) -> ConnectionConfig:
        c = self._data.get('connection', {})
        return ConnectionConfig(
            mode=c.get('mode', 'RTU'),
            port=c.get('port', 'COM1'),
            baudrate=int(c.get('baudrate', DEFAULT_BAUDRATE)),
            parity=c.get('parity', 'N'),
            stopbits=int(c.get('stopbits', 1)),
            bytesize=int(c.get('bytesize', 8)),
            timeout=float(c.get('timeout', 0.5)),
            ip=c.get('ip', DEFAULT_TCP_IP),
            tcp_port=int(c.get('tcp_port', DEFAULT_TCP_PORT)),
            slave_id=int(c.get('slave_id', DEFAULT_SLAVE_ID)),
        )

    def save_connection_config(self, config: ConnectionConfig) -> None:
        self._data['connection'] = {
            'mode': config.mode,
            'port': config.port,
            'baudrate': config.baudrate,
            'parity': config.parity,
            'stopbits': config.stopbits,
            'bytesize': config.bytesize,
            'timeout': config.timeout,
            'ip': config.ip,
            'tcp_port': config.tcp_port,
            'slave_id': config.slave_id,
        }
        self._save_raw()

    def load_device_config(self) -> DeviceConfig:
        d = self._data.get('device', {})
        return DeviceConfig(
            measure_unit=int(d.get('measure_unit', DEFAULT_MEASURE_UNIT)),
            measure_type=int(d.get('measure_type', DEFAULT_MEASURE_TYPE)),
            analog_out_type=int(d.get('analog_out_type', 0)),
            dio_type=int(d.get('dio_type', 0)),
            calib_mode=int(d.get('calib_mode', 0)),
            cell_sensitivity=float(d.get('cell_sensitivity', DEFAULT_CELL_SENSITIVITY)),
            cell_full_scale=float(d.get('cell_full_scale', DEFAULT_CELL_FULL_SCALE)),
            std_weight=float(d.get('std_weight', 0.0)),
            delta_weight=float(d.get('delta_weight', 0.01)),
            delta_time=int(d.get('delta_time', 10)),
            filter_level=int(d.get('filter_level', DEFAULT_FILTER_LEVEL)),
            resolution_mode=int(d.get('resolution_mode', 0)),
            factory_tare=float(d.get('factory_tare', 0.0)),
            target_address=int(d.get('target_address', 1)),
            target_baud=int(d.get('target_baud', 5)),
            target_parity=int(d.get('target_parity', 0)),
            slave_id=int(d.get('slave_id', DEFAULT_SLAVE_ID)),
        )

    def save_device_config(self, config: DeviceConfig) -> None:
        self._data['device'] = {
            'measure_unit': config.measure_unit,
            'measure_type': config.measure_type,
            'analog_out_type': config.analog_out_type,
            'dio_type': config.dio_type,
            'calib_mode': config.calib_mode,
            'cell_sensitivity': config.cell_sensitivity,
            'cell_full_scale': config.cell_full_scale,
            'std_weight': config.std_weight,
            'delta_weight': config.delta_weight,
            'delta_time': config.delta_time,
            'filter_level': config.filter_level,
            'resolution_mode': config.resolution_mode,
            'factory_tare': config.factory_tare,
            'target_address': config.target_address,
            'target_baud': config.target_baud,
            'target_parity': config.target_parity,
            'slave_id': config.slave_id,
        }
        self._save_raw()

    def load_ui_settings(self) -> dict:
        """Load cài đặt UI (sample interval, time window, v.v.)"""
        return self._data.get('ui', {})

    def save_ui_settings(self, ui_data: dict) -> None:
        self._data['ui'] = ui_data
        self._save_raw()
