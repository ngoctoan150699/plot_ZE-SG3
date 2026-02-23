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


def main():
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
        def read_register(self, a, s=1): return None
        def read_registers(self, a, c, s=1): return None
        def write_register(self, a, v, s=1): return False

    null_client = _NullModbusClient()

    # -------------------------------------------------------
    # 3. APPLICATION – Services
    # -------------------------------------------------------
    from application.data_collector import DataCollectorService
    from application.config_service import ConfigService

    collector   = DataCollectorService(null_client, slave_id=conn_cfg.slave_id)
    config_svc  = ConfigService(null_client)

    # -------------------------------------------------------
    # 4. EXPORTERS – OCP: thêm exporter mới ở đây
    # -------------------------------------------------------
    from exporters.csv_simple_exporter import CsvSimpleExporter
    from exporters.csv_ctr_exporter    import CsvCtrExporter

    exporters = [
        CsvSimpleExporter(),
        CsvCtrExporter(),
    ]

    # -------------------------------------------------------
    # 5. UI – Inject tất cả dependencies
    # -------------------------------------------------------
    app = QApplication(sys.argv)
    app.setApplicationName("ZE-SG3 Torque Acquisition")
    app.setOrganizationName("Seneca")

    from ui.main_window import MainWindow
    window = MainWindow(
        collector=collector,
        config_svc=config_svc,
        exporters=exporters,
        settings_repo=settings,
        conn_config=conn_cfg,
        dev_config=dev_cfg,
    )
    window.show()

    logger.info("Ứng dụng ZE-SG3 đã khởi động")
    result = app.exec_()

    # Cleanup khi thoát
    collector.stop()
    logger.info("Ứng dụng đã thoát")
    sys.exit(result)


if __name__ == "__main__":
    main()
