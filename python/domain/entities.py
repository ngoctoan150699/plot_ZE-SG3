"""
Domain Layer – Entities (Dataclasses)
=======================================
Các đối tượng nghiệp vụ thuần khiết – không phụ thuộc vào bất kỳ
thư viện bên ngoài nào (Zero-dependency domain layer theo DIP).
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class DeviceConfig:
    """
    Cấu hình của cảm biến và bộ khuếch đại ZE-SG3.
    Tương ứng với các thanh ghi: 40003, 40004, 40014-17, 40043.
    """
    measure_unit: int   = 5      # 5 = N (Newton), xem UNITS dict trong constants.py
    measure_type: int   = 0      # 0 = Bipolar, 1 = Unipolar
    cell_full_scale: float = 50.0   # Float32 – tầm đo tối đa (đơn vị theo measure_unit)
    cell_sensitivity: float = 2.0   # Float32 – độ nhạy mV/V
    filter_level: int  = 3      # 0-6: thời gian lọc, 7=Advanced
    calib_mode: int    = 0      # 0=Factory, 1=Standard Weight
    slave_id: int      = 1      # Modbus Slave ID

    def validate(self) -> bool:
        """Kiểm tra tính hợp lệ của cấu hình."""
        if self.measure_unit not in range(9):
            return False
        if self.measure_type not in (0, 1):
            return False
        if self.cell_full_scale <= 0:
            return False
        if self.cell_sensitivity <= 0:
            return False
        if self.filter_level not in range(8):
            return False
        return True


@dataclass
class SampleData:
    """
    Một điểm dữ liệu mẫu thu được từ cảm biến.
    Được tạo ra bởi DataCollectorService trong Application Layer.
    """
    time_s: float       # Thời gian thu mẫu (giây) kể từ lúc bắt đầu ghi
    torque_Nm: float    # Giá trị torque/lực đọc từ Net Weight (N.m hoặc đơn vị tương ứng)
    stable: bool        # True nếu Status Bit 4 = 1 (trọng số ổn định)
    timestamp: float    = 0.0   # Unix timestamp tuyệt đối (time.time())


@dataclass
class DeviceStatus:
    """
    Trạng thái hiện tại của thiết bị, đọc từ thanh ghi 40078 và các register giá trị.
    """
    connected: bool       = False
    is_stable: bool       = False    # Bit 4 của STATUS register
    is_fullscale: bool    = False    # Bit 3 của STATUS register
    net_weight: float     = 0.0     # Giá trị hiện tại (Float32)
    gross_weight: float   = 0.0
    tare_weight: float    = 0.0
    max_net_weight: float = 0.0     # Giá trị lớn nhất từ lúc khởi động
    min_net_weight: float = 0.0     # Giá trị nhỏ nhất từ lúc khởi động
    adc_raw_filtered: int = 0       # Giá trị ADC thô 24-bit đã lọc
    raw_status_reg: int   = 0       # Giá trị thô của thanh ghi STATUS


@dataclass
class ConnectionConfig:
    """
    Cấu hình kết nối Modbus – RTU hoặc TCP.
    Được lưu/load bởi AppSettings trong Infrastructure Layer.
    """
    mode: str          = 'RTU'              # 'RTU' hoặc 'TCP'
    # RTU settings
    port: str          = 'COM1'
    baudrate: int      = 9600
    parity: str        = 'N'               # 'N', 'E', 'O'
    stopbits: int      = 1
    bytesize: int      = 8
    timeout: float     = 0.5
    # TCP settings
    ip: str            = '192.168.1.100'
    tcp_port: int      = 502
    # Common
    slave_id: int      = 1


@dataclass
class RecordingSession:
    """
    Phiên ghi dữ liệu – chứa toàn bộ mẫu thu thập được.
    """
    samples: List[SampleData] = field(default_factory=list)
    start_time: float         = 0.0
    end_time: float           = 0.0
    sample_interval_ms: int   = 100

    @property
    def duration_s(self) -> float:
        """Tổng thời gian ghi (giây)."""
        if self.end_time > 0 and self.start_time > 0:
            return self.end_time - self.start_time
        return 0.0

    @property
    def count(self) -> int:
        return len(self.samples)
