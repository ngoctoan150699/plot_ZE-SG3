# Bản Đồ Thanh Ghi Modbus Cho Seneca Z-SG3 và ZE-SG3 Series

Tài liệu này tổng hợp các thanh ghi Modbus quan trọng của thiết bị Seneca Z-SG3 và ZE-SG3, được trích xuất từ tài liệu "Seneca Z-SG3 and ZE-SG3 Series Installation Manual". Việc cung cấp tệp này giúp bạn dễ dàng tra cứu và hiểu cách hoạt động của ứng dụng điều khiển ZE-SG3 mà không cần phải truy cập lại vào NotebookLM.

## Bảng Thanh Ghi Modbus (Holding Registers - Function Code 3)

| Địa chỉ (4x) | Offset | Tên thanh ghi | Quyền | Định dạng | Mô tả / Ví dụ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **40001** | 0 | MACHINE-ID | RO | UNSIGNED 16 | Mã định danh thiết bị. |
| **40002** | 1 | FIRMWARE REVISION | RO | UNSIGNED 16 | Phiên bản firmware hiện tại. |
| **40003** | 2 | MEASURE UNIT | RW | UNSIGNED 16 | Chọn đơn vị: 0=Kg, 1=g, 2=t, 3=lb, 4=l, 5=N, 6=bar, 7=atm, 8=other. |
| **40004** | 3 | UNIPOLAR | RW | UNSIGNED 16 | 0 = Căng/Nén (Bipolar); 1 = Cân/Chỉ nén (Unipolar). |
| **40005** | 4 | ANALOG OUTPUT TYPE | RW | UNSIGNED 16 | Cấu hình đầu ra Analog (Áp hay Dòng). |
| **40007** | 6 | CALIBRATION MODE | RW | UNSIGNED 16 | 0 = Theo Factory; 1 = Theo quả chuẩn Calibration. |
| **40014-15**| 13 | CELL SENSE RATIO | RW | FLOAT 32 | Độ nhạy của Load cell, tính bằng **mV/V** (Ví dụ: 2.0 mV/V). |
| **40016-17**| 15 | CELL FULL SCALE | RW | FLOAT 32 | Giá trị toàn thang (Full Scale) tính theo đơn vị đã chọn (VD: 50.0). |
| **40018-19**| 17 | STANDARD WEIGHT | RW | FLOAT 32 | Giá trị trọng lượng mẫu dùng cho việc Calibration. |
| **40043** | 42 | DENOISE FILTER VAL | RW | UNSIGNED 16 | Mức lọc nhiễu 0 (2ms) đến 6 (850ms). 7 = Chế độ lọc nâng cao. |
| **40064-65**| 63 | **NET WEIGHT VALUE** | RO | FLOAT 32 | **Trọng lượng Tịnh (Net Weight)** tính bằng đơn vị thiết lập. |
| **40066-67**| 65 | **GROSS WEIGHT VALUE**| RO | FLOAT 32 | **Trọng lượng Tổng (Gross Weight)**. |
| **40068-69**| 67 | **TARE WEIGHT VALUE** | RO | FLOAT 32 | **Trọng lượng Trừ Bì (Tare Weight)**. |
| **40076-77**| 75 | FACTORY MANUAL TARE | RW | FLOAT 32 | Giá trị Tare thiết lập thủ công. |
| **40078** | 77 | STATUS | RW | UNSIGNED 16 | Trạng thái thiết bị. Bit 4 (0x10) là báo trạng thái khối lượng đã ổn định. |
| **40080** | 79 | **COMMAND REGISTER** | RW | UNSIGNED 16 | Thanh ghi thực thi lệnh điều khiển. (Chi tiết bên dưới). |
| **40092-93**| 91 | ADC RAW 24 BIT | RO | UNSIGNED 32 | Giá trị ADC thô chưa lọc 24-bit. |
| **40094-95**| 93 | ADC RAW 24 BIT FILT | RO | UNSIGNED 32 | Giá trị ADC 24-bit sau khi đã qua bộ lọc (Filtered). |

---

## Chi tiết Thanh Ghi Lệnh (Command Register - 40080)

Việc ghi các giá trị thập phân (decimal) sau vào thanh ghi `40080` (Offset 79) sẽ thực thi các tác vụ tương ứng:

*   **43948 (`CMD_RESTART`)**: Khởi động lại thiết bị (Reboot).
*   **49594**: Lấy giá trị Tare lưu trong RAM (sẽ mất đi khi khởi động lại).
*   **49914 (`CMD_TARE`)**: Lấy giá trị Tare lưu vào Flash (không bị mất khi khởi động lại).
*   **50700 (`CMD_SAMPLE_CALIB`)**: Lấy trọng lượng mẫu lưu vào Flash (cho việc hiệu chuẩn bằng vật mẫu).
*   **50773**: Áp dụng Tare từ thanh ghi "Factory Manual Tare".
*   **49151 / 45056**: Xóa các thanh ghi lưu/giữ giá trị trọng lượng tịnh lớn nhất, nhỏ nhất (Max / Min net weight).

---

## Đối chiếu mức độ tuân thủ của code `python/ze_sg3_torque.py`

Code thu thập dữ liệu bằng Python hiện tại (`python/ze_sg3_torque.py`) **HOÀN TOÀN TUÂN THỦ** đúng với tài liệu từ NotebookLM.

*   Các địa chỉ Offset: `REG_MEASURE_UNIT = 2`, `REG_MEASURE_TYPE = 3`, `REG_CELL_SENS_HI/LO = 13/14` (kiểu Float32 dùng 2 thanh ghi liên tiếp), `REG_NET_WEIGHT_HI/LO = 63/64`, đều khớp với bảng map bên trên.
*   Cấu hình mặc định cho phép đọc dữ liệu `Float32` thông qua ghép 2 thanh ghi MSW (Most Significant Word) và LSW (Least Significant Word).
*   Việc reset Tare gọi lệnh `49914` lên thanh ghi `79` sẽ ghi vào bộ nhớ Flash để duy trì. Lệnh Reboot gọi `43948` cũng hoàn toàn chuẩn xác.

**Ghi chú:** Đây là nguồn tra cứu dữ liệu gốc chính thức của hãng, được thiết kế cho việc lập trình Modbus RTU / TCP. Trong tương lai, chỉ cần đọc file này là đã nắm được mọi thao tác giao tiếp và điều khiển thiết bị ZE-SG3 / Z-SG3.
