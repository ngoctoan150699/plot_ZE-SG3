"""
Exporters – CTR Data Format #1
================================
OCP: Thêm định dạng mới không ảnh hưởng CsvSimpleExporter.
"""

import logging
from datetime import datetime

from application.interfaces import IDataExporter
from domain.entities import RecordingSession

logger = logging.getLogger(__name__)


class CsvCtrExporter(IDataExporter):
    """Xuất theo định dạng CTR DATA FORMAT #1 (Revision 2019.06.27)."""

    @property
    def display_name(self) -> str:
        return "CTR Format #1 (Save/State/Cycle/Time/Cmd/Angle/Torque)"

    @property
    def file_extension(self) -> str:
        return ".csv"

    def export(self, session: RecordingSession, file_path: str) -> bool:
        if not session.samples:
            logger.warning("CsvCtrExporter: Không có dữ liệu để xuất")
            return False
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write("Time (s),Angle (deg),Torque (Nm),Cycle\n")
                for s in session.samples:
                    cycle = s.cycle if s.cycle > 0 else 1
                    f.write(
                        f"{s.time_s:.6f},{s.angle_deg:.6f},{s.torque_Nm:.6f},{int(cycle)}\n"
                    )
            logger.info(f"CsvCtrExporter: Đã xuất {len(session.samples)} mẫu theo CSV mẫu → {file_path}")
            return True
        except Exception as e:
            logger.error(f"CsvCtrExporter: Lỗi: {e}")
            return False
