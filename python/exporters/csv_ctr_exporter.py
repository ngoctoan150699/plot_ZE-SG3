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
            rows = [
                [
                    1,
                    3,
                    s.cycle if s.cycle > 0 else 1,
                    s.time_s,
                    0.0,
                    s.angle_deg,
                    s.torque_Nm,
                ]
                for s in session.samples
            ]
            n = len(rows)
            cols = list(zip(*rows))
            col_max = [max(c) for c in cols]
            col_min = [min(c) for c in cols]

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write("%===============================================================\n")
                f.write("%     CTR DATA FORMAT #1 (Revision 2019.06.27)\n")
                f.write("%     ZE-SG3 Torque Data – DYJN-101 50Nm\n")
                f.write("%===============================================================\n")
                f.write("BEGIN_OF_HEADER\n")
                f.write(f"SAVED_DATE = {datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')}\n")
                f.write(f"SAMPLE_INTERVAL_MS = {session.sample_interval_ms}\n")
                f.write("NUMBER_OF_COLUMNS = 7\n")
                f.write("COLUMN_NAME = [Save,State,Cycle,Time,Command,Angle,Torque]\n")
                f.write("COLUMN_UNIT = [NA,NA,Cycle,sec,Dgree,Dgree,N*m]\n")
                f.write(f"COLUMN_LENGTH = [{','.join([str(n)]*7)}]\n")
                f.write(f"COLUMN_MAXIMUM = [{','.join(f'{v:.6f}' for v in col_max)}]\n")
                f.write(f"COLUMN_MINIMUM = [{','.join(f'{v:.6f}' for v in col_min)}]\n")
                f.write("END_OF_HEADER\n")
                for row in rows:
                    f.write(
                        f"{int(row[0])},{int(row[1])},{int(row[2])},"
                        f"{row[3]:.6f},{row[4]:.6f},{row[5]:.6f},{row[6]:.6f}\n"
                    )
            logger.info(f"CsvCtrExporter: Đã xuất {n} mẫu → {file_path}")
            return True
        except Exception as e:
            logger.error(f"CsvCtrExporter: Lỗi: {e}")
            return False
