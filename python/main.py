#!/usr/bin/env python3
"""
main.py – Entry Point (Composition Root)
==========================================
Đây là điểm duy nhất trong toàn bộ ứng dụng nơi các dependencies
được khởi tạo và "inject" vào nhau (Dependency Inversion Principle).

Theo Clean Architecture: "Composition Root" – chỉ có 1.
"""

import logging
import sys

from PyQt5.QtWidgets import QApplication

# === Setup logging (thay thế print() toàn bộ) ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def set_windows_timer_resolution(enable: bool):
    import sys
    if sys.platform == 'win32':
        try:
            import ctypes
            winmm = ctypes.windll.winmm
            if enable:
                winmm.timeBeginPeriod(1)
                logger.info("Đã nâng độ phân giải Windows timer lên 1ms")
            else:
                winmm.timeEndPeriod(1)
                logger.info("Đã khôi phục độ phân giải Windows timer")
        except Exception as e:
            logger.debug("Không thể cấu hình Windows timer: %s", e)


def main():
    set_windows_timer_resolution(True)
    # -------------------------------------------------------
    # 1. INFRASTRUCTURE – Load settings
    # -------------------------------------------------------
    from infrastructure.app_settings import AppSettings
    settings = AppSettings()
    conn_cfg = settings.load_connection_config()
    dev_cfg  = settings.load_device_config()

    # -------------------------------------------------------
    # 2. INFRASTRUCTURE – Modbus clients (RTU là default)
    #    Client thực sự được khởi tạo khi user nhấn "Kết nối"
    #    Ở đây tạo DummyClient để inject vào services
    # -------------------------------------------------------
    from application.interfaces import IModbusClient
    from typing import Optional

    class _NullModbusClient(IModbusClient):
        """Placeholder client trước khi kết nối thực."""
        def connect(self) -> bool: return False
        def disconnect(self) -> None: pass
        def is_connected(self) -> bool: return False
        def read_register(self, address: int, slave_id: int = 1): return None
        def read_registers(self, address: int, count: int, slave_id: int = 1): return None
        def write_register(self, address: int, value: int, slave_id: int = 1): return False
        def write_registers(self, address: int, values: list, slave_id: int = 1): return False

    null_client = _NullModbusClient()

    # -------------------------------------------------------
    # 3. APPLICATION – Services
    # -------------------------------------------------------
    from application.data_collector import DataCollectorService
    from application.config_service import ConfigService
    from application.servo_service import ServoService
    from application.measurement_service import MeasurementService
    from application.report_service import ReportService
    from application.plc_control_service import PlcControlService
    from application.modbus_bus_scheduler import ModbusBusScheduler
    from infrastructure.plc_servo_controller import DummyPLCServoController

    collector   = DataCollectorService(null_client, slave_id=conn_cfg.slave_id)
    config_svc  = ConfigService(null_client)
    plc_svc     = PlcControlService(null_client, slave_id=conn_cfg.slave_id)
    bus_scheduler = ModbusBusScheduler(
        null_client,
        sensor_slave_id=conn_cfg.slave_id,
        plc_slave_id=conn_cfg.plc_slave_id,
    )
    
    # R2 Upgrades: Servo, Measurement & Report Services
    dummy_plc   = DummyPLCServoController()
    servo_svc   = ServoService(dummy_plc)
    measurement_svc = MeasurementService()
    report_svc  = ReportService()

    # -------------------------------------------------------
    # 4. EXPORTERS – OCP: thêm exporter mới ở đây
    # -------------------------------------------------------
    from application.interfaces import IDataExporter
    from exporters.csv_simple_exporter import CsvSimpleExporter
    from exporters.csv_ctr_exporter    import CsvCtrExporter

    exporters: list[IDataExporter] = [
        CsvSimpleExporter(),
        CsvCtrExporter(),
    ]

    # -------------------------------------------------------
    # 5. UI – Inject tất cả dependencies
    # -------------------------------------------------------
    import os
    from PyQt5.QtGui import QIcon
    
    app = QApplication(sys.argv)
    app.setApplicationName("ZE-SG3 Torque Acquisition")
    app.setOrganizationName("Seneca")
    
    # Path resolution for PyInstaller
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS')
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_path, 'app_icon.ico')
    app.setWindowIcon(QIcon(icon_path))

    from ui.main_window import MainWindow
    window = MainWindow(
        collector=collector,
        config_svc=config_svc,
        exporters=exporters,
        settings_repo=settings,
        conn_config=conn_cfg,
        dev_config=dev_cfg,
        servo_svc=servo_svc,
        plc_svc=plc_svc,
        measurement_svc=measurement_svc,
        report_svc=report_svc,
        bus_scheduler=bus_scheduler,
    )
    window.set_app_icon(icon_path)

    window.show()

    logger.info("Ứng dụng ZE-SG3 đã khởi động")
    result = app.exec_()

    # Cleanup khi thoát
    bus_scheduler.stop()
    collector.stop()
    set_windows_timer_resolution(False)
    logger.info("Ứng dụng đã thoát")
    sys.exit(result)



if __name__ == "__main__":
    main()
