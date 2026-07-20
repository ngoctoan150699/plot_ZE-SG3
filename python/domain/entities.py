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
    Tương ứng với các thanh ghi: 40003-40011, 40014-40019, 40030-40032, 40043-40044, 40076-40077.
    """
    measure_unit: int   = 5      # 40003: 5 = N (Newton)
    measure_type: int   = 0      # 40004: 0 = Bipolar, 1 = Unipolar
    analog_out_type: int = 0     # 40005: 0=0..20mA, 1=4..20mA, 2=0..5V, 3=0..10V, v.v.
    dio_type: int       = 0      # 40006: Digital I/O mode
    calib_mode: int     = 0      # 40007: 0=Factory, 1=Standard Weight
    
    # RS485 Comm Settings (Software override)
    target_address: int  = 1      # 40009: Station ID
    target_baud: int     = 5      # 40010: Index (5=38400)
    target_parity: int   = 0      # 40011: 0=None
    
    cell_sensitivity: float = 2.0   # 40014-15: mV/V
    cell_full_scale: float = 50.0   # 40016-17: Giá trị toàn thang
    std_weight: float      = 0.0    # 40018-19: Trọng lượng hiệu chuẩn
    
    delta_weight: float    = 0.01   # 40030-31: Ngưỡng ổn định
    delta_time: int        = 10     # 40032: Thời gian giữ ổn định (x100ms)
    
    filter_level: int      = 3      # 40043: Mức lọc nhiễu 0-7
    resolution_mode: int   = 0      # 40044: Độ phân giải 0=Auto, 1=Manual, 2=Max
    
    factory_tare: float    = 0.0    # 40076-77: Tare gán cứng (manual)
    adc_sps: int           = 3      # 40035: Tần số lấy mẫu (3=100Hz)
    slave_id: int          = 1      # Modbus Slave ID

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
    # === YÊU CẦU R2 ===
    angle_deg: float    = 0.0   # Góc xoay tính toán của Servo (độ)
    cycle: int          = 0     # Số thứ tự chu kỳ (cycle) hiện tại (1, 2, 3...)


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
    plc_slave_id: int  = 2


@dataclass
class ServoProfile:
    """Cấu hình hành trình/tốc độ của Servo cho từng loại sản phẩm."""
    negative_angle: float = -36.0
    positive_angle: float = 36.0
    speed: float          = 10.0  # Tốc độ (rpm)
    jog_speed: float      = 10.0  # Tốc độ JOG (rpm)
    cycles: int           = 3     # Số chu kỳ đo (mặc định 3, có thể thay đổi)
    safety_torque_limit_Nm: float = 30.0  # Ngưỡng dừng khẩn theo torque; 0 = tắt
    positive_torque_limit_Nm: float = 5.0  # ITR Angle: dừng chiều dương
    negative_torque_limit_Nm: float = -5.0  # ITR Angle: dừng chiều âm



@dataclass
class OperatingTorqueSetup:
    """Cấu hình phạm vi tính toán cho phép đo mô-men hoạt động."""
    center_percent: float = 80.0  # Tỷ lệ lấy dữ liệu ở giữa (ví dụ 80% bỏ 10% hai đầu)
    cycle: int            = 3     # Vòng chu kỳ lấy dữ liệu (mặc định cycle 3)


@dataclass
class MeasurementResult:
    """Kết quả tính toán sau khi chạy đo."""
    breakaway_max: float = 0.0
    operating_avg: float = 0.0
    operating_max: float = 0.0
    operating_min: float = 0.0
    ok_ng_status: dict   = field(default_factory=dict) # {'breakaway_max': True, 'operating_avg': False...}


@dataclass
class ReportMetadata:
    """Metadata thông tin sản phẩm và lượt đo để tạo báo cáo."""
    test_item: str    = ""
    part_name: str    = ""
    part_no: str      = ""
    sample_no: int    = 1
    remark: str       = ""
    test_purpose: str = ""
    tester: str       = ""
    team: str         = ""
    line_no: str      = ""
    date: str         = ""
    csv_path: str     = ""
    report_path: str  = ""


@dataclass
class RecordingSession:
    """
    Phiên ghi dữ liệu – chứa toàn bộ mẫu thu thập được.
    """
    samples: List[SampleData] = field(default_factory=list)
    start_time: float         = 0.0
    end_time: float           = 0.0
    sample_interval_ms: int   = 100
    # === YÊU CẦU R2 ===
    current_cycle: int        = 0
    test_item: str            = ""
    part_name: str            = ""

    @property
    def duration_s(self) -> float:
        """Tổng thời gian ghi (giây)."""
        if self.end_time > 0 and self.start_time > 0:
            return self.end_time - self.start_time
        return 0.0

    @property
    def count(self) -> int:
        return len(self.samples)
