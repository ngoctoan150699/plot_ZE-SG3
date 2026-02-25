"""
Exporters – CSV Đơn Giản
=========================
OCP: Một implementation của IDataExporter.
Thêm định dạng mới = tạo file mới, không sửa file này.
"""

import csv
import logging
from datetime import datetime

from application.interfaces import IDataExporter
from domain.entities import RecordingSession

logger = logging.getLogger(__name__)


class CsvSimpleExporter(IDataExporter):
    """Xuất CSV 2 cột: Time (s) | Torque (Nm)."""

    @property
    def display_name(self) -> str:
        return "CSV Đơn Giản (Time, Torque)"

    @property
    def file_extension(self) -> str:
        return ".csv"

    def export(self, session: RecordingSession, file_path: str) -> bool:
        if not session.samples:
            logger.warning("CsvSimpleExporter: Không có dữ liệu để xuất")
            return False
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Time (s)', 'Torque (Nm)'])
                for s in session.samples:
                    writer.writerow([
                        f"{s.time_s:.6f}",
                        f"{s.torque_Nm:.6f}"
                    ])
            logger.info(f"CsvSimpleExporter: Đã xuất {len(session.samples)} mẫu → {file_path}")
            return True
        except Exception as e:
            logger.error(f"CsvSimpleExporter: Lỗi: {e}")
            return False
