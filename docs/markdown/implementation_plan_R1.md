# 📋 Implementation Plan: Software Development R1
# Kế Hoạch Triển Khai Phần Mềm ZE-SG3 Torque Acquisition – Phiên Bản R1

> **Tài liệu tham chiếu**: `docs/pdf/Software development - R1.pdf`
> **Ngày tạo**: 2026-05-25
> **Trạng thái**: ⏳ Chờ Review & Phê duyệt

---

## 📖 Mục Lục

1. [Tổng Quan Kiến Trúc Hiện Tại](#1-tổng-quan-kiến-trúc-hiện-tại)
2. [Phân Tích Chi Tiết Từng Yêu Cầu](#2-phân-tích-chi-tiết-từng-yêu-cầu)
3. [Kế Hoạch Thay Đổi Theo Từng Layer](#3-kế-hoạch-thay-đổi-theo-từng-layer)
4. [Câu Hỏi Mở Cần Làm Rõ](#4-câu-hỏi-mở-cần-làm-rõ)
5. [Thứ Tự Triển Khai](#5-thứ-tự-triển-khai)
6. [Kế Hoạch Kiểm Thử](#6-kế-hoạch-kiểm-thử)

---

## 1. Tổng Quan Kiến Trúc Hiện Tại

### 1.1. Cấu trúc thư mục

```
python/
├── main.py                          # Entry point (Composition Root – DI)
├── domain/                          # Domain Layer (thuần nghiệp vụ)
│   ├── constants.py                 # Hằng số Modbus, lệnh, đơn vị
│   └── entities.py                  # Dataclasses: DeviceConfig, SampleData, RecordingSession...
├── application/                     # Application Layer (use cases)
│   ├── interfaces.py                # ABC: IModbusClient, IDataExporter, ISettingsRepository
│   ├── data_collector.py            # Polling thread thu thập dữ liệu từ ZE-SG3
│   └── config_service.py            # Đọc/ghi cấu hình thiết bị qua Modbus
├── infrastructure/                  # Infrastructure Layer (implementations)
│   ├── app_settings.py              # JSON persistence cho settings
│   ├── modbus_rtu_client.py         # IModbusClient → Modbus RTU
│   └── modbus_tcp_client.py         # IModbusClient → Modbus TCP
├── exporters/                       # Open/Closed – thêm exporter mới = tạo file mới
│   ├── csv_simple_exporter.py       # CSV 2 cột: Time, Torque
│   └── csv_ctr_exporter.py          # CTR DATA FORMAT #1
├── ui/                              # UI Layer (PyQt5)
│   ├── main_window.py               # 1505 dòng – MainWindow điều phối toàn bộ
│   └── widgets/
│       └── realtime_plot.py          # Biểu đồ Torque-Time thời gian thực (Matplotlib blit)
├── draw_plot.py                     # 202KB – TorquePlotViewer (dùng cho tab Plot Viewer)
├── convert_may_gui.py               # 37KB – ConvertWidget (dùng cho tab Converter)
└── torque_simulator.py              # 24KB – Mô phỏng torque
```

### 1.2. Luồng dữ liệu hiện tại

```
ZE-SG3 (Cảm biến) ──Modbus──► DataCollectorService (Thread)
                                       │
                                       ▼ Qt Signal (thread-safe)
                                  MainWindow
                                  ├── Real-time display (Torque, Status, Max/Min)
                                  ├── Torque-Time chart (RealTimePlot)
                                  ├── Recording Session (List[SampleData])
                                  │       │
                                  │       ▼
                                  ├── Export CSV (CsvSimple / CsvCtr)
                                  ├── Import to Plot Viewer (draw_plot.py)
                                  └── Import to Converter (convert_may_gui.py)
```

### 1.3. Giao diện hiện tại gồm 3 tab chính:
- **📡 Thu thập**: Kết nối Modbus + Cấu hình + Biểu đồ Torque-Time + Ghi dữ liệu + Xuất CSV
- **📊 Plot Viewer**: Xem và phân tích biểu đồ từ file CSV (dùng `draw_plot.py`)
- **🔄 Converter**: Chuyển đổi định dạng file (dùng `convert_may_gui.py`)

---

## 2. Phân Tích Chi Tiết Từng Yêu Cầu

### 📌 Yêu Cầu #1: Part Name Selection (Trang 1 – Mục 1)

**Mô tả**: Thêm combobox cho phép chọn loại sản phẩm cần đo.

**Giá trị combobox**:
| Giá trị | Ý nghĩa |
|---------|---------|
| `ITR` | Inner Tie Rod (thanh nối trong) |
| `B/Joint` | Ball Joint (khớp cầu) |
| `OTR` | Outer Tie Rod (thanh nối ngoài) |
| `S/Link` | Stabilizer Link (thanh ổn định) |

**Vị trí trên UI**: Đặt trong tab "Thu thập", phía trên phần điều khiển ghi dữ liệu.

**Tác động đến code**:
- `domain/constants.py`: Thêm `PART_NAMES` list
- `ui/main_window.py` hoặc widget mới: Thêm QComboBox
- Giá trị được chọn sẽ tự động link sang Plot Viewer (Yêu cầu #6)

**Triển khai cụ thể**:
```python
# domain/constants.py
PART_NAMES = ['ITR', 'B/Joint', 'OTR', 'S/Link']
```

---

### 📌 Yêu Cầu #2: Servo Setup (Trang 1 – Mục 1)

**Mô tả**: Tạo nút **Setup** để cấu hình thông số servo cho từng loại sản phẩm và từng chế độ đo.

**Thông số cần cấu hình** (cho mỗi tổ hợp Part × TestItem):

| Thông số | Ý nghĩa | Ví dụ |
|----------|---------|-------|
| Negative Angle (°) | Góc quay ngược chiều kim đồng hồ | -36° |
| Positive Angle (°) | Góc quay thuận chiều kim đồng hồ | +36° |
| Servo Speed | Tốc độ quay | 10 rpm |

**Ví dụ ma trận cấu hình**:
```
┌─────────────────────────────────────────────────────────────┐
│             Breakaway Torque (B)    Operating Torque (O)    │
│ ITR         +30° / 5rpm             ±36° / 10rpm           │
│ B/Joint     +45° / 8rpm             ±40° / 12rpm           │
│ OTR         +30° / 5rpm             ±36° / 10rpm           │
│ S/Link      +25° / 5rpm             ±30° / 10rpm           │
└─────────────────────────────────────────────────────────────┘
```

**Triển khai**: Tạo QDialog (Setup Dialog) mở ra khi nhấn nút Setup:

```python
# domain/entities.py
@dataclass
class ServoProfile:
    """Cấu hình servo cho 1 tổ hợp Part + TestItem."""
    negative_angle: float = -36.0    # Góc âm (chỉ dùng cho Operating)
    positive_angle: float = 36.0     # Góc dương
    speed: float = 10.0              # Tốc độ servo (rpm hoặc đơn vị tùy chỉnh)
```

**Lưu trữ**: JSON trong `settings.json` dưới key `servo_profiles`:
```json
{
  "servo_profiles": {
    "ITR_B": {"negative_angle": 0, "positive_angle": 30, "speed": 5},
    "ITR_O": {"negative_angle": -36, "positive_angle": 36, "speed": 10},
    "B/Joint_B": {"negative_angle": 0, "positive_angle": 45, "speed": 8}
  }
}
```

---

### 📌 Yêu Cầu #3: Điều Khiển Servo & Ghi Dữ Liệu (Trang 1 – Mục 1)

**Mô tả**: Kết hợp điều khiển servo và ghi dữ liệu thành 1 hành động thống nhất.

**Luồng mới**:
```
Nhấn "Start Record"
    │
    ▼
Khởi chạy Servo theo profile đã Setup
    │
    ├── Đồng thời: Bắt đầu ghi dữ liệu Torque từ ZE-SG3
    │
    ▼
Servo chạy xong chu trình
    │
    ▼
Tự động dừng ghi
```

**So sánh trước/sau**:

| Trước (hiện tại) | Sau (R1) |
|-------------------|----------|
| "Bắt đầu ghi" = chỉ ghi dữ liệu | "Start Record" = khởi chạy servo + ghi dữ liệu |
| "Dừng ghi" = dừng ghi thủ công | Servo xong → tự động dừng |
| Không có nút Stop servo | Nút **Stop** = dừng servo + dừng ghi ngay lập tức |

**⚠️ CẦN LÀM RÕ**: Servo motor được điều khiển qua giao thức nào? (Xem mục Câu hỏi mở)

**Triển khai tạm**: Tạo `IServoController` interface và `DummyServoController` cho testing:

```python
# application/interfaces.py
class IServoController(ABC):
    @abstractmethod
    def move_to_angle(self, angle: float, speed: float) -> bool:
        """Di chuyển servo đến góc chỉ định với tốc độ cho trước."""

    @abstractmethod
    def get_current_angle(self) -> float:
        """Đọc góc hiện tại của servo."""

    @abstractmethod
    def stop(self) -> None:
        """Dừng servo ngay lập tức."""

    @abstractmethod
    def is_moving(self) -> bool:
        """Kiểm tra servo có đang quay không."""
```

---

### 📌 Yêu Cầu #4: Test Item – Chế Độ Đo (Trang 1 – Mục 2)

**Mô tả**: 2 chế độ đo với chu trình servo khác nhau.

#### Chế độ 1: Operating Torque (O)

```
Chu trình 1 cycle:
    0° ──────► +36° ──────► -36° ──────► 0°
    (bắt đầu)  (góc dương)  (góc âm)   (kết thúc)

Lặp lại 3 cycles rồi tự động dừng:
    Cycle 1: 0° → +36° → -36° → 0°
    Cycle 2: 0° → +36° → -36° → 0°
    Cycle 3: 0° → +36° → -36° → 0°  ← Tự động dừng
```

**Dữ liệu thu được**: Torque + Angle cho toàn bộ 3 cycles.

#### Chế độ 2: Breakaway Torque (B)

```
Chu trình:
    0° ──────► +36° ──────► 0°
    (bắt đầu)  (góc dương)  (quay về)

CHÚ Ý: Chỉ lấy dữ liệu từ 0° → +36° (chiều đi)
        KHÔNG lấy dữ liệu chiều quay ngược +36° → 0°
```

**Dữ liệu thu được**: Chỉ Torque + Angle trong khoảng 0° → +angle.

**Triển khai**:

```python
# application/servo_service.py
class ServoService:
    def __init__(self, controller: IServoController, collector: DataCollectorService):
        self._ctrl = controller
        self._collector = collector

    async def run_operating_cycle(self, profile: ServoProfile, num_cycles: int = 3):
        """
        Operating Torque: 0° → +angle → -angle → 0° × N cycles
        """
        for cycle in range(num_cycles):
            self._current_cycle = cycle + 1
            await self._ctrl.move_to_angle(profile.positive_angle, profile.speed)
            await self._ctrl.move_to_angle(profile.negative_angle, profile.speed)
            await self._ctrl.move_to_angle(0, profile.speed)
        # Tự động dừng ghi
        self._collector.stop_recording()

    async def run_breakaway_cycle(self, profile: ServoProfile):
        """
        Breakaway Torque: 0° → +angle → 0°
        Chỉ ghi data chiều đi (0° → +angle)
        """
        self._recording_direction = 'forward'  # Flag: chỉ ghi chiều đi
        await self._ctrl.move_to_angle(profile.positive_angle, profile.speed)
        self._recording_direction = 'return'   # Ngừng ghi
        await self._ctrl.move_to_angle(0, profile.speed)
        self._collector.stop_recording()
```

---

### 📌 Yêu Cầu #5: Cải Thiện Phần Mềm – 3 điểm (Trang 1 – Mục 3)

#### 5a. Song Ngữ (EN/VN)

**Triển khai**: Module `i18n.py` với dict-based translation.

```python
# ui/i18n.py
TRANSLATIONS = {
    'vi': {
        'btn_connect': '🔗 Kết nối',
        'btn_disconnect': '🔌 Ngắt kết nối',
        'btn_start_record': '▶️ Bắt đầu ghi',
        'btn_stop': '⏹ Dừng',
        'tab_acquisition': '📡 Thu thập',
        'tab_plot_viewer': '📊 Plot Viewer',
        'lbl_torque': 'Torque:',
        'lbl_status': 'Trạng thái:',
        'lbl_part_name': 'Loại sản phẩm:',
        'lbl_test_item': 'Chế độ đo:',
        # ... ~100 labels
    },
    'en': {
        'btn_connect': '🔗 Connect',
        'btn_disconnect': '🔌 Disconnect',
        'btn_start_record': '▶️ Start Record',
        'btn_stop': '⏹ Stop',
        'tab_acquisition': '📡 Acquisition',
        'tab_plot_viewer': '📊 Plot Viewer',
        'lbl_torque': 'Torque:',
        'lbl_status': 'Status:',
        'lbl_part_name': 'Part Name:',
        'lbl_test_item': 'Test Item:',
        # ...
    },
}

class I18n:
    def __init__(self, lang='vi'):
        self._lang = lang

    def t(self, key: str) -> str:
        """Dịch key sang ngôn ngữ hiện tại."""
        return TRANSLATIONS.get(self._lang, {}).get(key, key)

    def toggle(self):
        """Chuyển đổi VN ↔ EN."""
        self._lang = 'en' if self._lang == 'vi' else 'vi'
```

**Tác động**: Tất cả QLabel, QPushButton text sẽ dùng `self._i18n.t('key')` thay vì hardcode string.

#### 5b. Thêm chương trình đo
→ Đã covered ở Yêu Cầu #1-#4.

#### 5c. Biểu đồ Torque-Angle

**Hiện tại**: Chỉ có 1 biểu đồ Torque-Time.
**Sau R1**: Chia đôi khu vực hiển thị:

```
┌──────────────────────────────────────────────────────┐
│                   Chart Area (QSplitter)              │
│  ┌─────────────────────┐  ┌────────────────────────┐ │
│  │  📈 Torque – Time   │  │  📐 Torque – Angle     │ │
│  │                     │  │                        │ │
│  │  Y: Torque (Nm)     │  │  Y: Torque (Nm)        │ │
│  │  X: Time (s)        │  │  X: Angle (°)          │ │
│  │                     │  │                        │ │
│  │  ~~~~~~~~~~~~~~~    │  │      /\                 │ │
│  │                     │  │     /  \                │ │
│  │                     │  │    /    \               │ │
│  │                     │  │   /      \              │ │
│  │                     │  │  /        \             │ │
│  └─────────────────────┘  └────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

**Triển khai**: Tạo widget mới `TorqueAnglePlot` tương tự `RealTimePlot`:

```python
# ui/widgets/torque_angle_plot.py
class TorqueAnglePlot(FigureCanvas):
    """Biểu đồ Torque vs Angle – cập nhật khi có dữ liệu angle."""

    def add_point(self, angle: float, torque: float) -> None:
        """Thêm điểm (angle, torque) vào biểu đồ."""
        # Tương tự RealTimePlot nhưng trục X là Angle thay vì Time
```

**⚠️ CẦN LÀM RÕ**: Dữ liệu Angle lấy từ đâu? (Xem mục Câu hỏi mở)

---

### 📌 Yêu Cầu #6: Cải Tiến Plot Viewer (Trang 2 – Mục 5, 6)

#### 6a. Xóa "Import to Converter"

**Hành động**: 
- Xóa nút `btn_to_conv` ("Import to Converter") trong tab Thu thập
- Xóa tab Converter từ `main_tabs`
- Xóa method `_import_to_converter()` trong `main_window.py`
- **KHÔNG xóa** file `convert_may_gui.py` (giữ lại để tham khảo)

#### 6b. Import to Plot Viewer tự động

**Luồng mới**: Khi nhấn "Import to Plot Viewer":
1. Tự động chuyển biểu đồ Torque-Angle sang tab Plot Viewer
2. Tự động switch sang tab Plot Viewer

#### 6c. Các trường thông tin đầu vào trong Plot Viewer

Đây là phần cải tiến lớn nhất của tab Plot Viewer. Các trường input được chia thành 2 loại:

**Trường TỰ ĐỘNG (linked từ tab Thu thập)**:

| Trường | Giá trị | Nguồn |
|--------|---------|-------|
| Test Item | `Breakaway Torque (B)` hoặc `Operating Torque (O)` | Combobox Test Item ở tab Thu thập |
| Part Name | `ITR`, `B/Joint`, `OTR`, `S/Link` | Combobox Part Name ở tab Thu thập |

**Trường NHẬP TAY (với xử lý tự động)**:

| Trường | Loại | Xử lý đặc biệt |
|--------|------|-----------------|
| Part No | QLineEdit | Auto UPPERCASE khi nhập |
| Test Purpose | QComboBox | `Setting (S)`, `First (F)`, `Middle (M)`, `Final (Z)`, `Development (D)`, `Long-term (L)`, `Other (O)` |
| Tester | QLineEdit | Auto UPPERCASE + xóa dấu tiếng Việt |
| Team | QComboBox | `PM`, `QM`, `PT`, `EDTV` |
| Line No | QComboBox | `ITR #1`, `ITR #2`, `ITR #3`, `B/Joint #1`...`S/Link #4`, `Other` |

**Xử lý xóa dấu tiếng Việt cho trường Tester**:
```python
import unicodedata

def remove_vietnamese_diacritics(text: str) -> str:
    """Chuyển 'Nguyễn Văn A' → 'NGUYEN VAN A'"""
    # Chuẩn hóa Unicode NFD → tách ký tự gốc và dấu
    nfkd = unicodedata.normalize('NFKD', text)
    # Lọc bỏ các combining marks (dấu)
    ascii_text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Xử lý đặc biệt: đ → d, Đ → D
    ascii_text = ascii_text.replace('đ', 'd').replace('Đ', 'D')
    return ascii_text.upper()
```

#### 6d. Nút chọn thư mục

```
┌────────────────────────────────┐
│  📁 CSV File path:            │
│  [D:\Data\CSV\________] [📂]  │
│                                │
│  📁 Report File path:         │
│  [D:\Data\Report\_____] [📂]  │
└────────────────────────────────┘
```

#### 6e. Nút "Save the Report"

Khi nhấn, thực hiện **đồng thời**:

**1. Lưu file CSV gốc** (toàn bộ dữ liệu raw):
```
Tên file: [yymmdd]-[Test item]-[Part No 7 ký tự]-[Purpose]-[Team]-[##]
Ví dụ:    260525-B-CBJ0001-S-QM-01.csv
```

**2. Lưu file Report** (dữ liệu đã xử lý theo CTR form):
```
Tên file: 260525-B-CBJ0001-S-QM-01_report.csv (hoặc .xlsx)
```

**Quy tắc đặt tên chi tiết**:

| Thành phần | Nguồn | Ví dụ |
|------------|-------|-------|
| `yymmdd` | System date | `260525` |
| `Test item` | `B` (Breakaway) hoặc `O` (Operating) | `B` |
| `Part No` | 7 ký tự đầu tiên | `CBJ0001` |
| `Purpose` | Ký tự đầu tiên | `S` (Setting) |
| `Team` | Giá trị combobox | `QM` |
| `##` | Auto-increment nếu trùng | `01`, `02`... |

**Logic auto-increment**:
```python
def generate_filename(self, metadata: ReportMetadata, output_dir: str) -> str:
    date_str = datetime.now().strftime('%y%m%d')
    part_no_short = metadata.part_no[:7].upper()
    purpose_char = metadata.test_purpose[0].upper()  # 'S', 'F', 'M'...
    test_char = 'B' if 'Breakaway' in metadata.test_item else 'O'

    base = f"{date_str}-{test_char}-{part_no_short}-{purpose_char}-{metadata.team}"

    # Auto-increment
    seq = 1
    while True:
        filename = f"{base}-{seq:02d}.csv"
        full_path = os.path.join(output_dir, filename)
        if not os.path.exists(full_path):
            return filename
        seq += 1
```

---

### 📌 Yêu Cầu #7: Kết Quả Đo (Trang 3 – Mục 7)

**Mô tả**: Hiển thị kết quả đo sau khi dữ liệu được thu thập.

#### Breakaway Torque
```
┌─────────────────────────────────────┐
│  Breakaway Torque Result            │
│  ┌─────────────────────────────┐    │
│  │  Max: 12.345 Nm     ✅ OK  │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```
→ Chỉ lấy giá trị **Max** từ dữ liệu đo.

#### Operating Torque
```
┌─────────────────────────────────────┐
│  Operating Torque Results           │
│  ┌─────────────────────────────┐    │
│  │  Average: 8.234 Nm  ✅ OK  │    │
│  │  Max:     9.876 Nm  ✅ OK  │    │
│  │  Min:     6.543 Nm  ❌ NG  │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```
→ Lấy **Average**, **Max**, **Min** với xử lý vùng dữ liệu.

#### Cấu hình vùng lấy dữ liệu Operating Torque

Nút **Setup** mở dialog cấu hình:

| Part Name | Operating torque value setup (%) | Cycle |
|-----------|:-------------------------------:|:-----:|
| ITR       | 80%                             | 3     |
| B/Joint   | 80%                             | 3     |
| OTR       | -                               | -     |
| S/Link    | -                               | -     |

**Giải thích logic 80% center**:
```
Dữ liệu Cycle 3 (ví dụ 1000 data points):

|←─ 10% bỏ ─→|←───── 80% LẤY DỮ LIỆU ─────→|←─ 10% bỏ ─→|
|   100 pts   |          800 pts              |   100 pts   |
 ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓

▓ = Bỏ qua (đầu và cuối chu kỳ – dữ liệu không ổn định)
░ = Lấy để tính Average, Max, Min
```

**Triển khai**:
```python
# application/measurement_service.py
class MeasurementService:

    def calculate_operating_result(
        self,
        all_samples: List[SampleData],
        setup: OperatingTorqueSetup,
    ) -> MeasurementResult:
        """
        1. Tách dữ liệu theo cycle
        2. Lấy cycle được cấu hình (ví dụ cycle 3)
        3. Trim đầu/cuối theo % (ví dụ bỏ 10% đầu + 10% cuối)
        4. Tính Average, Max, Min trên vùng còn lại
        """
        # Tách cycle
        cycle_data = self._split_by_cycle(all_samples)

        # Lấy cycle cần (1-indexed)
        target = cycle_data[setup.cycle - 1]

        # Trim
        n = len(target)
        trim_percent = (100 - setup.center_percent) / 2 / 100  # 10%
        start_idx = int(n * trim_percent)
        end_idx = int(n * (1 - trim_percent))
        trimmed = target[start_idx:end_idx]

        # Tính kết quả
        values = [s.torque_Nm for s in trimmed]
        return MeasurementResult(
            operating_avg=sum(values) / len(values),
            operating_max=max(values),
            operating_min=min(values),
        )
```

#### Đánh giá OK/NG

```python
def evaluate_ok_ng(self, value: float, spec_upper: float, spec_lower: float) -> bool:
    """
    True = OK (trong spec), False = NG (ngoài spec).
    """
    return spec_lower <= value <= spec_upper
```

**Hiển thị trên UI**:
- OK → Chữ **OK** màu **xanh lá** (#4CAF50)
- NG → Chữ **NG** màu **đỏ** (#F44336)

---

### 📌 Yêu Cầu #8: Hiệu Chuẩn (Trang 3 – Mục 8)

**Hành động**: Đổi tên label "Factor K" → "Calibration" trong UI.

**Tác động**: Chỉ thay đổi text hiển thị, không thay đổi logic.

> **Lưu ý**: Kiểm tra trong code hiện tại có label "Factor K" ở đâu. Nếu không có (do đã refactor), chỉ cần đảm bảo phần cấu hình hiệu chuẩn dùng đúng tên "Calibration".

---

## 3. Kế Hoạch Thay Đổi Theo Từng Layer

### 3.1. Domain Layer

#### [MODIFY] `python/domain/constants.py`

Thêm ~50 dòng:

```python
# === YÊU CẦU R1: PART NAMES ===
PART_NAMES = ['ITR', 'B/Joint', 'OTR', 'S/Link']

# === YÊU CẦU R1: TEST ITEMS ===
TEST_ITEMS = {
    'B': 'Breakaway Torque',
    'O': 'Operating Torque',
}

# === YÊU CẦU R1: TEST PURPOSES ===
TEST_PURPOSES = {
    'S': 'Setting',
    'F': 'First',
    'M': 'Middle',
    'Z': 'Final',
    'D': 'Development',
    'L': 'Long-term',
    'O': 'Other',
}

# === YÊU CẦU R1: TEAMS ===
TEAMS = ['PM', 'QM', 'PT', 'EDTV']

# === YÊU CẦU R1: LINE NUMBERS ===
LINE_NOS = [
    'ITR #1', 'ITR #2', 'ITR #3',
    'B/Joint #1', 'B/Joint #2', 'B/Joint #3',
    'OTR #1', 'OTR #2', 'OTR #3',
    'S/Link #1', 'S/Link #2', 'S/Link #3', 'S/Link #4',
    'Other',
]

# === YÊU CẦU R1: DEFAULT SERVO ===
DEFAULT_POSITIVE_ANGLE = 36.0   # Góc dương mặc định
DEFAULT_NEGATIVE_ANGLE = -36.0  # Góc âm mặc định
DEFAULT_SERVO_SPEED = 10.0      # Tốc độ servo mặc định
DEFAULT_OPERATING_CYCLES = 3    # Số cycle Operating Torque
DEFAULT_CENTER_PERCENT = 80.0   # Phần trăm vùng trung tâm
```

#### [MODIFY] `python/domain/entities.py`

Thêm ~80 dòng dataclass mới:

```python
@dataclass
class ServoProfile:
    """Cấu hình servo cho 1 tổ hợp Part Name + Test Item."""
    negative_angle: float = -36.0
    positive_angle: float = 36.0
    speed: float = 10.0

@dataclass
class OperatingTorqueSetup:
    """Cấu hình vùng lấy dữ liệu cho Operating Torque."""
    center_percent: float = 80.0  # % vùng trung tâm (bỏ đều 2 đầu)
    cycle: int = 3                # Cycle nào để lấy dữ liệu

@dataclass
class MeasurementResult:
    """Kết quả đo torque."""
    breakaway_max: Optional[float] = None
    operating_avg: Optional[float] = None
    operating_max: Optional[float] = None
    operating_min: Optional[float] = None
    ok_ng_status: Dict[str, bool] = field(default_factory=dict)
    # ok_ng_status = {'breakaway_max': True, 'operating_avg': True, ...}

@dataclass
class ReportMetadata:
    """Thông tin metadata cho báo cáo."""
    test_item: str = ''        # 'Breakaway Torque (B)' hoặc 'Operating Torque (O)'
    part_name: str = ''        # 'ITR', 'B/Joint', ...
    part_no: str = ''          # Mã sản phẩm (auto uppercase)
    test_purpose: str = ''     # 'Setting (S)', 'First (F)', ...
    tester: str = ''           # Tên người đo (auto uppercase no diacritics)
    team: str = ''             # 'PM', 'QM', ...
    line_no: str = ''          # 'ITR #1', ...
    date: str = ''             # Auto: yymmdd

@dataclass
class SpecLimits:
    """Giới hạn Spec cho đánh giá OK/NG."""
    upper: float = 999.0
    lower: float = 0.0
```

Mở rộng `RecordingSession`:
```python
@dataclass
class RecordingSession:
    samples: List[SampleData] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    sample_interval_ms: int = 100
    # === R1: Thêm dữ liệu angle ===
    angle_data: List[float] = field(default_factory=list)
    current_cycle: int = 0
    test_item: str = ''     # 'B' hoặc 'O'
    part_name: str = ''     # 'ITR', 'B/Joint', ...
```

---

### 3.2. Application Layer

#### [NEW] `python/application/servo_service.py` (~150 dòng)

```python
class ServoService:
    """Điều khiển chu trình đo torque qua servo motor."""

    def __init__(self, controller: IServoController, collector: DataCollectorService):
        ...

    def run_operating_cycle(self, profile: ServoProfile, cycles: int = 3) -> None:
        """Chạy Operating Torque: 0→+→-→0 × N cycles."""

    def run_breakaway_cycle(self, profile: ServoProfile) -> None:
        """Chạy Breakaway Torque: 0→+ →0 (chỉ ghi chiều đi)."""

    def stop(self) -> None:
        """Dừng servo + dừng ghi ngay lập tức."""
```

#### [NEW] `python/application/measurement_service.py` (~120 dòng)

```python
class MeasurementService:
    """Tính toán kết quả đo và đánh giá OK/NG."""

    def calculate_breakaway_result(self, samples: List[SampleData]) -> float:
        """Trả về giá trị Max."""

    def calculate_operating_result(self, samples, setup: OperatingTorqueSetup) -> MeasurementResult:
        """Trả về Avg/Max/Min sau khi trim theo cấu hình."""

    def evaluate(self, value: float, spec: SpecLimits) -> bool:
        """OK nếu lower <= value <= upper."""
```

#### [NEW] `python/application/report_service.py` (~200 dòng)

```python
class ReportService:
    """Tạo tên file và lưu báo cáo."""

    def generate_filename(self, metadata: ReportMetadata, output_dir: str) -> str:
        """Tạo tên file: yymmdd-B-CBJ0001-S-QM-01"""

    def save_raw_csv(self, session: RecordingSession, csv_dir: str, metadata: ReportMetadata) -> str:
        """Lưu CSV gốc (toàn bộ cycles)."""

    def save_report(self, session: RecordingSession, report_dir: str,
                    metadata: ReportMetadata, result: MeasurementResult) -> str:
        """Lưu report theo CTR format."""
```

#### [MODIFY] `python/application/interfaces.py`

Thêm ~20 dòng:
```python
class IServoController(ABC):
    @abstractmethod
    def move_to_angle(self, angle: float, speed: float) -> bool: ...

    @abstractmethod
    def get_current_angle(self) -> float: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def is_moving(self) -> bool: ...
```

---

### 3.3. Infrastructure Layer

#### [NEW] `python/infrastructure/servo_controller.py` (~100 dòng)

```python
class DummyServoController(IServoController):
    """Mô phỏng servo controller cho testing.
    Sẽ được thay thế bằng implementation thật khi có spec hardware."""

    def move_to_angle(self, angle, speed):
        time.sleep(abs(angle) / speed)  # Mô phỏng thời gian di chuyển
        self._current_angle = angle
        return True

    def get_current_angle(self):
        return self._current_angle

    def stop(self):
        pass

    def is_moving(self):
        return False
```

#### [MODIFY] `python/infrastructure/app_settings.py`

Thêm ~60 dòng cho các settings mới:

```python
def load_servo_profiles(self) -> Dict[str, ServoProfile]:
    """Load cấu hình servo cho mỗi Part × TestItem."""

def save_servo_profiles(self, profiles: Dict[str, ServoProfile]) -> None:
    """Lưu cấu hình servo."""

def load_report_paths(self) -> dict:
    """Load đường dẫn CSV/Report đã chọn."""

def save_report_paths(self, paths: dict) -> None:
    """Lưu đường dẫn."""

def load_operating_setups(self) -> Dict[str, OperatingTorqueSetup]:
    """Load cấu hình vùng dữ liệu cho Operating Torque."""

def save_operating_setups(self, setups: Dict[str, OperatingTorqueSetup]) -> None:
    """Lưu cấu hình."""
```

---

### 3.4. UI Layer

#### [NEW] `python/ui/i18n.py` (~200 dòng)
- Module song ngữ với dict translations
- Class `I18n` với `t(key)` method

#### [NEW] `python/ui/widgets/measurement_panel.py` (~250 dòng)
- QGroupBox chứa:
  - Part Name combobox
  - Test Item combobox
  - Setup button → mở QDialog cấu hình servo
  - Start Record / Stop buttons

#### [NEW] `python/ui/widgets/torque_angle_plot.py` (~150 dòng)
- Widget Torque vs Angle (tương tự `RealTimePlot`)
- X axis = Angle (°), Y axis = Torque (Nm)

#### [NEW] `python/ui/widgets/results_panel.py` (~200 dòng)
- QGroupBox hiển thị kết quả đo
- Labels cho Max / Avg / Min
- OK/NG indicators (QLabel với màu xanh/đỏ)
- Setup button cho cấu hình vùng dữ liệu

#### [NEW] `python/ui/widgets/report_panel.py` (~300 dòng)
- QGroupBox thay thế phần Export + Import cũ
- Các trường input: Part No, Test Purpose, Tester, Team, Line No
- Thư mục CSV / Report
- Nút Save the Report

#### [MODIFY] `python/ui/main_window.py`
Chi tiết thay đổi:

1. **Import và tích hợp widgets mới** (~20 dòng)
2. **Thêm MeasurementPanel vào tab Thu thập** (~10 dòng)
3. **Chia đôi chart area** với QSplitter horizontal → Torque-Time + Torque-Angle (~30 dòng)
4. **Thay thế phần Export/Import bằng ReportPanel** (~15 dòng)
5. **Xóa tab Converter** (~10 dòng xóa)
6. **Xóa nút Import to Converter** (~15 dòng xóa)
7. **Thêm ResultsPanel** (~10 dòng)
8. **Tích hợp I18n** (~refactor labels)
9. **Đổi "Factor K" → "Calibration"** (1-2 dòng)

---

### 3.5. Entry Point

#### [MODIFY] `python/main.py`
```python
# Thêm inject cho services mới
from application.servo_service import ServoService
from application.measurement_service import MeasurementService
from application.report_service import ReportService
from infrastructure.servo_controller import DummyServoController

servo_ctrl = DummyServoController()
servo_svc = ServoService(servo_ctrl, collector)
measurement_svc = MeasurementService()
report_svc = ReportService()

window = MainWindow(
    collector=collector,
    config_svc=config_svc,
    servo_svc=servo_svc,              # NEW
    measurement_svc=measurement_svc,  # NEW
    report_svc=report_svc,            # NEW
    exporters=exporters,
    settings_repo=settings,
    conn_config=conn_cfg,
    dev_config=dev_cfg,
)
```

---

## 4. Câu Hỏi Mở Cần Làm Rõ

### ❓ Q1: Servo Motor Controller

> **Servo motor được điều khiển qua giao thức nào?**

Hiện tại ZE-SG3 là bộ khuếch đại loadcell, chỉ đọc được torque. Cần biết:
- Servo controller là thiết bị gì? (Brand/Model)
- Giao tiếp qua: Modbus? Serial? PLC? Ethernet/IP?
- Cần biết protocol/thanh ghi để implement `IServoController` thật

**Giải pháp tạm**: Dùng `DummyServoController` để phát triển UI và logic trước, swap implementation khi có spec.

### ❓ Q2: Dữ Liệu Angle

> **Dữ liệu góc (Angle) cho biểu đồ Torque-Angle lấy từ đâu?**

Các phương án:
- **A**: Đọc từ servo encoder qua Modbus/Serial
- **B**: Tính toán: `angle = speed × elapsed_time` (mô phỏng)
- **C**: Từ PLC hoặc encoder riêng

### ❓ Q3: Spec cho OK/NG

> **Giới hạn Spec (Upper/Lower limit) được nhập từ đâu?**

- Nhập trực tiếp trên UI (SpinBox)?
- Đọc từ file cấu hình?
- Khác nhau theo Part Name?

### ❓ Q4: Report Format

> **"Form báo cáo tương tự như phiên bản trước" – cụ thể là gì?**

- File CSV với header đặc biệt (giống CTR format hiện tại)?
- File Excel (.xlsx)?
- File PDF?

### ❓ Q5: Tab Converter

> **Xác nhận xóa hoàn toàn tab Converter?**

- Xóa hoàn toàn khỏi giao diện?
- Hay chỉ ẩn (giữ code, không hiển thị)?

---

## 5. Thứ Tự Triển Khai

### Milestone 1: Domain + Application Logic (Không ảnh hưởng UI)
```
Ước tính: ~2-3 giờ
```

1. ✅ `domain/constants.py` – Thêm constants mới
2. ✅ `domain/entities.py` – Thêm dataclasses
3. ✅ `application/interfaces.py` – Thêm IServoController
4. ✅ `application/measurement_service.py` – Logic tính toán kết quả
5. ✅ `application/report_service.py` – Logic tạo tên file + lưu báo cáo
6. ✅ `application/servo_service.py` – Logic chu trình servo

### Milestone 2: Infrastructure (Persistence)
```
Ước tính: ~1 giờ
```

7. ✅ `infrastructure/servo_controller.py` – DummyServoController
8. ✅ `infrastructure/app_settings.py` – Thêm load/save methods mới

### Milestone 3: UI Layer (Visual Changes)
```
Ước tính: ~4-5 giờ (phần lớn nhất)
```

9. ✅ `ui/i18n.py` – Module song ngữ
10. ✅ `ui/widgets/measurement_panel.py` – Panel chọn Part + Test Item
11. ✅ `ui/widgets/torque_angle_plot.py` – Biểu đồ Torque-Angle
12. ✅ `ui/widgets/results_panel.py` – Panel kết quả đo
13. ✅ `ui/widgets/report_panel.py` – Panel báo cáo
14. ✅ `ui/main_window.py` – Tích hợp tất cả

### Milestone 4: Integration & Cleanup
```
Ước tính: ~1-2 giờ
```

15. ✅ `main.py` – Inject services mới
16. ✅ Xóa code Converter
17. ✅ Testing & bug fixing

**Tổng ước tính**: ~8-11 giờ

---

## 6. Kế Hoạch Kiểm Thử

### 6.1. Unit Tests (tự động)
- `MeasurementService.calculate_operating_result()` với dữ liệu mock
- `MeasurementService.evaluate()` với các edge cases
- `ReportService.generate_filename()` với nhiều tổ hợp
- `remove_vietnamese_diacritics()` với các ký tự đặc biệt

### 6.2. Integration Tests
- Chạy `python main.py` → app khởi động không lỗi
- Kiểm tra tất cả combobox có đúng giá trị
- Kiểm tra Part No auto-uppercase
- Kiểm tra Tester auto-uppercase no diacritics
- Kiểm tra file naming convention

### 6.3. Manual UI Tests
- [ ] Part Name combobox hiển thị 4 giá trị
- [ ] Test Item combobox hiển thị 2 giá trị
- [ ] Setup dialog mở và lưu được
- [ ] Torque-Time và Torque-Angle charts hiển thị song song
- [ ] Import to Plot Viewer hoạt động
- [ ] Tab Converter đã bị xóa
- [ ] Nút Import to Converter đã bị xóa
- [ ] Save Report tạo file với đúng naming convention
- [ ] Kết quả đo hiển thị OK (xanh) / NG (đỏ)
- [ ] Toggle VN ↔ EN hoạt động
- [ ] "Factor K" đã đổi thành "Calibration"
