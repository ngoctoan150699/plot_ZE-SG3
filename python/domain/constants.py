"""
Domain Layer – Constants
========================
Tất cả hằng số thanh ghi Modbus, lệnh điều khiển và đơn vị
cho thiết bị Seneca Z-SG3 / ZE-SG3.

Tài liệu tham khảo: MI00617-4-EN (Seneca ZE-SG3 Installation Manual)
Địa chỉ thanh ghi: base-0 cho pymodbus (tài liệu dùng 40001 = offset 0)
"""

# === HOLDING REGISTERS (Offset base-0) ===
REG_MACHINE_ID        = 0    # 40001: Mã định danh thiết bị (RO)
REG_FIRMWARE_REV      = 1    # 40002: Phiên bản firmware (RO)
REG_MEASURE_UNIT      = 2    # 40003: Đơn vị đo (RW)
REG_MEASURE_TYPE      = 3    # 40004: 0=Bipolar, 1=Unipolar (RW)
REG_ANALOG_OUT_TYPE   = 4    # 40005: Loại đầu ra Analog (RW)
REG_DIO_TYPE          = 5    # 40006: Digital I/O type/mode (RW)
REG_CALIB_MODE        = 6    # 40007: 0=Factory, 1=Standard Weight (RW)
REG_ADDRESS           = 8    # 40009: Station Address (1..247) (RW)
REG_BAUD              = 9    # 40010: Baud Rate Index (0..7) (RW)
REG_PARITY            = 10   # 40011: Parity (0:None, 1:Even, 2:Odd) (RW)

REG_CELL_SENS_HI      = 13   # 40014: Cell Sensitivity MSW (Float32, mV/V)
REG_CELL_SENS_LO      = 14   # 40015: Cell Sensitivity LSW
REG_CELL_FS_HI        = 15   # 40016: Cell Full Scale MSW (Float32)
REG_CELL_FS_LO        = 16   # 40017: Cell Full Scale LSW
REG_STD_WEIGHT_HI     = 17   # 40018: Standard Weight MSW (Float32)
REG_STD_WEIGHT_LO     = 18   # 40019: Standard Weight LSW

REG_DELTA_WEIGHT_HI   = 29   # 40030: Delta Weight MSW (Float32) – ngưỡng ổn định
REG_DELTA_WEIGHT_LO   = 30   # 40031: Delta Weight LSW
REG_DELTA_TIME        = 31   # 40032: Thời gian giữ ổn định (×100ms)

REG_FILTER_LEVEL      = 42   # 40043: Mức lọc 0-6 (2ms-850ms), 7=Advanced (RW)
REG_RESOLUTION_MODE   = 43   # 40044: 0=Auto, 1=Manual, 2=Max (RW)

REG_ADC_SPS           = 34   # 40035: ADC Sampling Rate Index (0..6) (RW)
                             # 0=960Hz, 1=300Hz, 2=150Hz, 3=100Hz, 4=60Hz, 5=12Hz, 6=4.7Hz

REG_ADC_16BIT_FILT    = 62   # 40063: ADC 16-bit đã lọc (RO)
REG_NET_WEIGHT_HI     = 63   # 40064: Net Weight MSW (Float32, RO)
REG_NET_WEIGHT_LO     = 64   # 40065: Net Weight LSW
REG_GROSS_WEIGHT_HI   = 65   # 40066: Gross Weight MSW (Float32, RO)
REG_GROSS_WEIGHT_LO   = 66   # 40067: Gross Weight LSW
REG_TARE_WEIGHT_HI    = 67   # 40068: Tare Weight MSW (Float32, RO)
REG_TARE_WEIGHT_LO    = 68   # 40069: Tare Weight LSW

REG_INT_NET_HI        = 69   # 40070: Integer Net Weight MSW (Signed32, RO)
REG_INT_NET_LO        = 70   # 40071: Integer Net Weight LSW
REG_INT_GROSS_HI      = 71   # 40072: Integer Gross Weight MSW (Signed32, RO)
REG_INT_GROSS_LO      = 72   # 40073: Integer Gross Weight LSW
REG_INT_TARE_HI       = 73   # 40074: Integer Tare Weight MSW (Signed32, RO)
REG_INT_TARE_LO       = 74   # 40075: Integer Tare Weight LSW

REG_FACTORY_TARE_HI   = 75   # 40076: Factory Manual Tare MSW (Float32, RW)
REG_FACTORY_TARE_LO   = 76   # 40077: Factory Manual Tare LSW

REG_STATUS            = 77   # 40078: Status Register (RW)
                             # Bit 4 (0x10): Stable Weight
                             # Bit 3 (0x08): Full Scale cell

REG_COMMAND           = 79   # 40080: Command Register (RW)

REG_PIECES_NR         = 80   # 40081: Piece counter (RO, Unsigned16)
REG_MAX_NET_HI        = 81   # 40082: Max Net Weight MSW (Float32, RO)
REG_MAX_NET_LO        = 82   # 40083: Max Net Weight LSW
REG_MIN_NET_HI        = 83   # 40084: Min Net Weight MSW (Float32, RO)
REG_MIN_NET_LO        = 84   # 40085: Min Net Weight LSW

REG_ADC_RAW_HI        = 91   # 40092: ADC Raw 24-bit Unfiltered MSW (RO)
REG_ADC_RAW_LO        = 92   # 40093: ADC Raw 24-bit Unfiltered LSW
REG_ADC_RAW_FILT_HI   = 93   # 40094: ADC Raw 24-bit Filtered MSW (RO)
REG_ADC_RAW_FILT_LO   = 94   # 40095: ADC Raw 24-bit Filtered LSW

REG_MANUAL_ANALOG_OUT = 95   # 40096: Manual Analog Output (mV or uA) (RW)

# === STATUS REGISTER BIT MASKS (REG_STATUS = 40078) ===
STATUS_BIT_STABLE     = 0x10  # Bit 4: Weight Stable
STATUS_BIT_FULLSCALE  = 0x08  # Bit 3: Full Scale Reached

# === COMMAND VALUES (ghi vào REG_COMMAND = 40080) ===
CMD_RESTART           = 43948  # Khởi động lại thiết bị
CMD_TARE_RAM          = 49594  # Lấy Tare lưu RAM (mất khi restart)
CMD_TARE              = 49914  # Lấy Tare lưu Flash (bền vững)
CMD_SAMPLE_CALIB      = 50700  # Hiệu chuẩn bằng trọng lượng mẫu (Flash)
CMD_TARE_FACTORY      = 50773  # Áp dụng tare từ Factory Manual Tare register
CMD_RESET_MAX         = 49151  # Xóa Max Net Weight
CMD_RESET_MIN         = 45056  # Xóa Min Net Weight

# === ĐƠN VỊ ĐO (REG_MEASURE_UNIT = 40003) ===
UNITS = {
    0: 'Kg',
    1: 'g',
    2: 't',
    3: 'lb',
    4: 'l',
    5: 'N',
    6: 'bar',
    7: 'atm',
    8: 'other'
}

# === MỨC LỌC NHIỄU (REG_FILTER_LEVEL = 40043) ===
FILTER_LABELS = {
    0: '0 – 2 ms (nhanh nhất)',
    1: '1 – 5 ms',
    2: '2 – 20 ms',
    3: '3 – 100 ms (khuyến nghị)',
    4: '4 – 200 ms',
    5: '5 – 500 ms',
    6: '6 – 850 ms (chậm nhất)',
    7: '7 – Advanced (điều chỉnh động)',
}

# === TẦN SỐ LẤY MẪU ADC (REG_ADC_SPS = 40035) ===
SPS_LABELS = {
    0: '960 Hz (Nhanh nhất)',
    1: '300 Hz',
    2: '150 Hz',
    3: '100 Hz',
    4: '60 Hz',
    5: '12 Hz',
    6: '4.7 Hz (Chậm nhất)',
}

# === CẤU HÌNH TRUYỀN THÔNG (REG_BAUD / REG_PARITY) ===
BAUD_LABELS = {
    0: '1200 bps',
    1: '2400 bps',
    2: '4800 bps',
    3: '9600 bps',
    4: '19200 bps',
    5: '38400 bps',
    6: '57600 bps',
    7: '115200 bps',
}

PARITY_LABELS = {
    0: 'None',
    1: 'Even',
    2: 'Odd',
    3: 'None (2 stop bits)'
}

# === MẶC ĐỊNH CHO CẢM BIẾN DYJN-101 50Nm ===
DEFAULT_MEASURE_UNIT        = 8      # other (Nm – không có sẵn trong danh sách)
DEFAULT_MEASURE_TYPE        = 0      # Bipolar (cả nén lẫn căng)
DEFAULT_CELL_FULL_SCALE     = 49.70  # 49.70 Nm (từ chứng chỉ hiệu chuẩn DYJN-101 SN:2601351)
DEFAULT_CELL_SENSITIVITY    = 1.9880 # 1.9880 mV/V (từ chứng chỉ hiệu chuẩn)
DEFAULT_FILTER_LEVEL        = 3      # 100ms (khuyến nghị cho đo tĩnh)
DEFAULT_SAMPLE_INTERVAL_MS  = 100    # 10 Hz
DEFAULT_TIME_WINDOW_S       = 60.0   # Cửa sổ biểu đồ 60 giây

# === MODBUS PROTOCOL ===
DEFAULT_SLAVE_ID            = 1
DEFAULT_BAUDRATE            = 115200
DEFAULT_TCP_PORT            = 502
DEFAULT_TCP_IP              = "192.168.90.101"
MODBUS_TIMEOUT_S            = 1.5
