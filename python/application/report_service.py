"""
Application Layer – Report & File Service
=========================================
Quản lý lưu trữ báo cáo, sinh tên tệp tự động tăng và xuất báo cáo định dạng CTR.
"""

import os
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple

from domain.entities import SampleData, RecordingSession, ReportMetadata, MeasurementResult
from domain.constants import TEST_ITEMS

logger = logging.getLogger(__name__)


class ReportService:
    """
    Dịch vụ tạo và lưu báo cáo đo.
    Lưu đồng thời:
    1. Tệp CSV gốc (Raw CSV - toàn bộ các chu kỳ).
    2. Tệp Báo cáo (Report CSV - chu kỳ chỉ định sau khi cắt tỉa).
    """

    def generate_filename(self, metadata: ReportMetadata, output_dir: str) -> str:
        """
        Sinh tên tệp theo quy tắc:
        yymmdd-TestItem-PartNo-Purpose-Team-SampleNo-##

        - TestItem: B (Breakaway) hoặc O (Operating/Oscillating)
        - PartNo: Lấy 7 ký tự đầu tiên
        - Purpose: Lấy ký tự đầu tiên viết hoa
        - Team: Lấy nguyên cụm mã Team
        - SampleNo: 01..99
        - ##: Số thứ tự tự động tăng từ 01 nếu trùng prefix
        """
        # 1. Ngày tháng yymmdd
        date_str = datetime.now().strftime('%y%m%d')

        # 2. Ký hiệu Test Item
        test_char = 'B'
        if metadata.test_item:
            if 'Operating' in metadata.test_item or 'Oscillating' in metadata.test_item or 'O' == metadata.test_item:
                test_char = 'O'
            elif 'Breakaway' in metadata.test_item or 'B' == metadata.test_item:
                test_char = 'B'

        # 3. Part No (không có thì dùng UNKNOWN theo file mẫu)
        part_no_clean = (metadata.part_no or "").strip().upper()
        part_no_short = part_no_clean[:7] if part_no_clean else "UNKNOWN"

        # 4. Purpose (lấy chữ cái đầu tiên)
        purpose_clean = (metadata.test_purpose or "").strip()
        purpose_char = purpose_clean[0].upper() if purpose_clean else "O"

        # 5. Team
        team_str = (metadata.team or "OTHER").strip().upper()

        # 6. Sample No (01..99)
        try:
            sample_no = max(1, min(99, int(getattr(metadata, 'sample_no', 1))))
        except Exception:
            sample_no = 1
        sample_no_str = f"{sample_no:02d}"

        # Tên tệp cơ sở (chưa có số thứ tự và phần mở rộng)
        base_name = f"{date_str}-{test_char}-{part_no_short}-{purpose_char}-{team_str}-{sample_no_str}"

        # 7. Tự động tăng số thứ tự mẫu đo
        seq = 1
        while True:
            filename = f"{base_name}-{seq:02d}.csv"
            full_path = os.path.join(output_dir, filename)
            if not os.path.exists(full_path):
                return filename
            seq += 1

    def save_raw_csv(self, session: RecordingSession, csv_dir: str, filename: str) -> str:
        """
        Lưu file CSV gốc theo CTR DATA FORMAT #1 giống file máy chuẩn.
        Cột dữ liệu: Save, State, Cycle, Time, Command, Angle, Torque.
        """
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir, exist_ok=True)

        full_path = os.path.join(csv_dir, filename)

        try:
            with open(full_path, 'w', newline='', encoding='utf-8') as f:
                f.write("Time (s),Angle (deg),Torque (Nm),Cycle\n")
                for s in session.samples:
                    cycle = s.cycle if s.cycle > 0 else 1
                    f.write(
                        f"{float(s.time_s):.6f},{float(s.angle_deg):.6f},"
                        f"{float(s.torque_Nm):.6f},{int(cycle)}\n"
                    )
            logger.info(f"ReportService: Đã lưu raw CSV theo file mẫu thành công → {full_path}")
            return full_path
        except Exception as e:
            logger.error(f"ReportService: Lỗi lưu raw CSV: {e}")
            raise e

    def save_ctr_report(
        self, 
        trimmed_samples: List[SampleData], 
        report_dir: str, 
        filename: str,
        session_interval_ms: int,
        metadata: ReportMetadata
    ) -> str:
        """
        Lưu file báo cáo CTR dựa trên dữ liệu đã điều chỉnh vùng giá trị và cycle.
        Sử dụng định dạng CTR DATA FORMAT #1 (Revision 2019.06.27).
        """
        if not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)

        root, ext = os.path.splitext(filename)
        report_filename = f"{root}_report{ext or '.csv'}"
        full_path = os.path.join(report_dir, report_filename)

        if not trimmed_samples:
            # Fallback nếu danh sách rỗng
            trimmed_samples = [SampleData(time_s=0.0, torque_Nm=0.0, stable=False, angle_deg=0.0, cycle=0)]

        try:
            # Chuẩn bị dữ liệu hàng
            # Cột: [Save, State, Cycle, Time, Command, Angle, Torque]
            rows = []
            for s in trimmed_samples:
                # Save=1, State=3 (mặc định), Command=0.0
                rows.append([1, 3, s.cycle, s.time_s, 0.0, s.angle_deg, s.torque_Nm])

            n = len(rows)
            cols = list(zip(*rows))
            col_max = [max(c) for c in cols]
            col_min = [min(c) for c in cols]

            with open(full_path, 'w', newline='', encoding='utf-8') as f:
                # Ghi tiêu đề CTR
                f.write("%===============================================================\n")
                f.write("%     CTR DATA FORMAT #1 (Revision 2019.06.27)\n")
                f.write("%     ZE-SG3 Torque Data – DYJN-101 50Nm\n")
                f.write("%===============================================================\n")
                f.write("BEGIN_OF_HEADER\n")
                f.write(f"SAVED_DATE = {datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')}\n")
                f.write(f"SAMPLE_INTERVAL_MS = {session_interval_ms}\n")
                f.write("NUMBER_OF_COLUMNS = 7\n")
                f.write("COLUMN_NAME = [Save,State,Cycle,Time,Command,Angle,Torque]\n")
                f.write("COLUMN_UNIT = [NA,NA,Cycle,sec,Dgree,Dgree,N*m]\n")
                f.write(f"COLUMN_LENGTH = [{','.join([str(n)]*7)}]\n")
                f.write(f"COLUMN_MAXIMUM = [{','.join(f'{v:.6f}' for v in col_max)}]\n")
                f.write(f"COLUMN_MINIMUM = [{','.join(f'{v:.6f}' for v in col_min)}]\n")
                
                # Thêm Metadata phụ đề cho Form CTR để dễ quản lý
                f.write(f"PART_NAME = {metadata.part_name}\n")
                f.write(f"PART_NO = {metadata.part_no}\n")
                f.write(f"TESTER = {metadata.tester}\n")
                f.write(f"TEAM = {metadata.team}\n")
                f.write(f"LINE_NO = {metadata.line_no}\n")
                
                f.write("END_OF_HEADER\n")
                
                # Ghi dữ liệu dòng
                for row in rows:
                    f.write(
                        f"{int(row[0])},{int(row[1])},{int(row[2])},"
                        f"{row[3]:.6f},{row[4]:.6f},{row[5]:.6f},{row[6]:.6f}\n"
                    )
            logger.info(f"ReportService: Đã lưu CTR report thành công → {full_path}")
            return full_path
        except Exception as e:
            logger.error(f"ReportService: Lỗi lưu CTR report: {e}")
            raise e
