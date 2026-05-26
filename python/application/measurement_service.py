"""
Application Layer – Measurement Service
=======================================
Xử lý tính toán kết quả đo (Max, Min, Average) và đánh giá tiêu chuẩn OK/NG.
"""

import logging
from typing import List, Optional, Tuple, Dict

from domain.entities import SampleData, OperatingTorqueSetup, MeasurementResult

logger = logging.getLogger(__name__)


class MeasurementService:
    """
    Dịch vụ tính toán kết quả đo mô-men xoắn.
    """

    def calculate_breakaway_result(self, samples: List[SampleData]) -> MeasurementResult:
        """
        Tính toán kết quả đo Breakaway Torque (Mô-men phá vỡ):
        - Lấy giá trị mô-men xoắn lớn nhất (Max) trong toàn bộ quá trình ghi.
        """
        if not samples:
            return MeasurementResult(breakaway_max=0.0)

        # Lấy giá trị tuyệt đối lớn nhất hoặc giá trị lớn nhất thông thường?
        # Yêu cầu: "Breakaway torque: lấy giá trị lớn nhất trong kết quả đo."
        # Nên lấy giá trị tuyệt đối lớn nhất để hỗ trợ cả 2 chiều quay (thuận/nghịch).
        max_val = max(abs(s.torque_Nm) for s in samples)
        
        # Tìm dấu gốc của giá trị đó
        real_max = 0.0
        for s in samples:
            if abs(s.torque_Nm) == max_val:
                real_max = s.torque_Nm
                break

        logger.info(f"Measurement: Breakaway Torque Max = {real_max:.4f} Nm")
        return MeasurementResult(breakaway_max=real_max)

    def calculate_operating_result(
        self, 
        samples: List[SampleData], 
        setup: OperatingTorqueSetup
    ) -> MeasurementResult:
        """
        Tính toán kết quả đo Operating Torque (Mô-men hoạt động):
        1. Lọc lấy các điểm dữ liệu thuộc chu kỳ (cycle) quy định trong setup (mặc định cycle 3).
        2. Loại bỏ đều X% dữ liệu ở hai đầu (ví dụ: lấy 80% vùng ở giữa nghĩa là bỏ 10% đầu và 10% cuối).
        3. Tính toán các trị số Trung bình (Average), Max, Min trên vùng dữ liệu còn lại.
        """
        if not samples:
            return MeasurementResult(operating_avg=0.0, operating_max=0.0, operating_min=0.0)

        # 1. Lọc dữ liệu theo cycle chỉ định
        cycle_samples = [s for s in samples if s.cycle == setup.cycle]
        
        # Nếu cycle chỉ định không có dữ liệu, fallback về toàn bộ dữ liệu có cycle > 0
        if not cycle_samples:
            logger.warning(f"Measurement: Không tìm thấy dữ liệu cho Cycle {setup.cycle}. Tự động fallback về toàn bộ dữ liệu.")
            cycle_samples = [s for s in samples if s.cycle > 0]
            
        if not cycle_samples:
            # Nếu vẫn không có dữ liệu phân cycle, dùng toàn bộ mẫu thu thập được
            cycle_samples = samples

        n = len(cycle_samples)
        if n < 3:
            # Không đủ mẫu để cắt lát dữ liệu
            torques = [s.torque_Nm for s in cycle_samples]
            avg_val = sum(torques) / len(torques)
            return MeasurementResult(
                operating_avg=avg_val,
                operating_max=max(torques),
                operating_min=min(torques)
            )

        # 2. Cắt lát dữ liệu lấy vùng trung tâm theo cấu hình phần trăm (%)
        # Ví dụ: center_percent = 80% -> trim_percent = (100 - 80) / 2 / 100 = 10% (0.1)
        trim_percent = (100.0 - setup.center_percent) / 2.0 / 100.0
        trim_count = int(n * trim_percent)
        
        # Đảm bảo vùng cắt lát hợp lệ
        start_idx = max(0, trim_count)
        end_idx = min(n, n - trim_count)
        
        # Đảm bảo còn lại ít nhất 1 điểm dữ liệu
        if start_idx >= end_idx:
            start_idx = 0
            end_idx = n

        trimmed_samples = cycle_samples[start_idx:end_idx]
        trimmed_torques = [s.torque_Nm for s in trimmed_samples]

        avg_val = sum(trimmed_torques) / len(trimmed_torques)
        max_val = max(trimmed_torques)
        min_val = min(trimmed_torques)

        logger.info(
            f"Measurement: Operating Torque tính trên chu kỳ {setup.cycle} (lấy {len(trimmed_samples)}/{n} mẫu): "
            f"Avg = {avg_val:.4f} Nm, Max = {max_val:.4f} Nm, Min = {min_val:.4f} Nm"
        )
        
        return MeasurementResult(
            operating_avg=avg_val,
            operating_max=max_val,
            operating_min=min_val
        )

    def evaluate_judgment(
        self, 
        result: MeasurementResult, 
        spec_min: float, 
        spec_max: float,
        is_breakaway: bool = True
    ) -> Dict[str, bool]:
        """
        Đánh giá đạt/lỗi (OK/NG) dựa trên Spec giới hạn (Spec Limits):
        - True = OK (nằm trong khoảng spec_min <= value <= spec_max)
        - False = NG (nằm ngoài khoảng spec)
        Trình trả về dict trạng thái OK/NG cho từng trường tương ứng.
        """
        status = {}
        
        if is_breakaway:
            val = result.breakaway_max if result.breakaway_max is not None else 0.0
            status['breakaway_max'] = (spec_min <= val <= spec_max)
        else:
            avg_val = result.operating_avg if result.operating_avg is not None else 0.0
            max_val = result.operating_max if result.operating_max is not None else 0.0
            min_val = result.operating_min if result.operating_min is not None else 0.0
            
            # Đối với Operating Torque, cả 3 giá trị đều phải nằm trong Spec để đạt OK
            status['operating_avg'] = (spec_min <= avg_val <= spec_max)
            status['operating_max'] = (spec_min <= max_val <= spec_max)
            status['operating_min'] = (spec_min <= min_val <= spec_max)
            
        return status
