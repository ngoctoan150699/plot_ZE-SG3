# Tài liệu Giải thích Logic PLC & Bản đồ Thanh ghi Modbus (FX3U)

Tài liệu này mô tả chi tiết sơ đồ thanh ghi Modbus, cách phân chia nhiệm vụ và logic điều khiển trong file chương trình PLC `MAIN.csv`.

---

## 1. Bản đồ Thanh ghi Modbus (D100 - D135)

PLC FX3U hoạt động như một Modbus RTU Slave (ID = 2, Baudrate = 115200, 8-N-1). Dữ liệu trao đổi giữa máy tính (PC) và PLC được ánh xạ qua các thanh ghi từ `D100` trở đi.

### 1.1. Thanh ghi PC ghi xuống PLC (Lệnh & Cấu hình)

| Thanh ghi | Tên (Ký hiệu) | Kiểu | Mô tả |
| :--- | :--- | :---: | :--- |
| **D100** | `CMD_WORD` | Word | **Word điều khiển chính** (Tách ra thành các bit `M100` đến `M107` trong PLC). Chi tiết xem mục 1.3. |
| **D101** | `MODE` | INT | **Chế độ đo:** `0` = Manual (Chạy tay), `1` = Breakaway (Đo phá vỡ), `2` = Operating (Đo dao động). |
| **D102** | `POS_ANGLE_X100` | INT | **Góc đích dương** (Góc phải) nhân 100. VD: `3600` = +36.00°. |
| **D103** | `NEG_ANGLE_X100` | INT | **Góc đích âm** (Góc trái) nhân 100. VD: `-3600` = -36.00°. |
| **D104** | `SPEED_X100` | INT | **Tốc độ phát xung** của Servo (tỉ lệ thuận với tốc độ quay deg/s). |
| **D105** | `CYCLE_SET` | INT | **Số chu kỳ đo thiết lập** trong chế độ Operating (mặc định là 3 chu kỳ). |
| **D110** | `JOG_PLUS` | INT | Nút nhấn Jog thuận chiều (Manual Jog+). `1` = Chạy, `0` = Dừng. |
| **D111** | `JOG_MINUS` | INT | Nút nhấn Jog ngược chiều (Manual Jog-). `1` = Chạy, `0` = Dừng. |
| **D112** | `HOME_CMD` | INT | Lệnh yêu cầu máy quay về vị trí Home (vị trí gốc 0). |

### 1.2. Thanh ghi PLC gửi lên PC (Trạng thái & Dữ liệu đo)

| Thanh ghi | Tên (Ký hiệu) | Kiểu | Mô tả |
| :--- | :--- | :---: | :--- |
| **D120** | `STATUS_WORD` | Word | **Word trạng thái hệ thống** (Gộp từ các bit trạng thái `M0` đến `M4`). Chi tiết xem mục 1.4. |
| **D121** | `CURRENT_MODE` | INT | Chế độ hoạt động hiện tại PLC đang chạy. |
| **D122** | `CURRENT_PHASE` | INT | Phase (bước) hiện hành trong chu trình tự động (VD: 10, 20, 210, 220...). |
| **D123** | `CURRENT_CYCLE` | INT | Chu kỳ đo hiện tại đang thực hiện. |
| **D124** | `CURRENT_ANGLE_X100`| INT | **Góc quay hiện tại** nhân 100 (gửi lên phần mềm để vẽ đồ thị). |
| **D125** | `TARGET_ANGLE_X100` | INT | Góc đích hiện tại mà PLC đang di chuyển tới. |
| **D130** | `DATA_VALID` | INT | Cờ báo dữ liệu đo hợp lệ (`1` = Hợp lệ để phần mềm lấy mẫu). |
| **D131** | `RECORD_ENABLE` | INT | Cờ cho phép phần mềm bắt đầu ghi log dữ liệu. |
| **D132** | `CYLINDER_STATUS` | INT | Trạng thái xi lanh kẹp (`1` = Đang kẹp, `0` = Đang nhả). |
| **D133** | `SERVO_ON_STATUS` | INT | Trạng thái Servo (`1` = Servo ON, `0` = Servo OFF). |
| **D134** | `TEST_DONE` | INT | Cờ báo chu trình đo đã hoàn tất thành công (`1` = Xong). |

### 1.3. Các bit lệnh trong `D100 CMD_WORD`

| Bit | Ký hiệu trong PLC | Mô tả chức năng |
| :---: | :--- | :--- |
| **b0** | `M100` | Lệnh bật hệ thống RUN (tương đương nút START vật lý). |
| **b1** | `M101` | Lệnh dừng hệ thống STOP (tương đương nút STOP vật lý). |
| **b2** | `M102` | Khởi động chu trình đo (`START_RECORD`). |
| **b3** | `M103` | Dừng chu trình đo (`STOP_RECORD`). |
| **b4** | `M104` | Lệnh kẹp/nhả xi lanh (Toggle latch). |
| **b5** | `M105` | Lệnh kích hoạt Servo ON. |
| **b6** | `M106` | Dừng khẩn cấp chu trình đo (`ABORT`). |
| **b7** | `M107` | Xóa cờ hoàn tất (`CLEAR_DONE`). |

### 1.4. Các bit trạng thái trong `D120 STATUS_WORD`

| Bit | Ký hiệu trong PLC | Mô tả trạng thái |
| :---: | :--- | :--- |
| **b0** | `M0` | Hệ thống đang ở trạng thái RUN. |
| **b1** | `Y005` | Servo đang ở trạng thái ON (sẵn sàng chạy). |
| **b2** | `M10` | Xi lanh đang ở trạng thái Kẹp. |
| **b3** | `M1` | Chu trình đo đang chạy (`Test Running`). |
| **b4** | `M2` | Cho phép phần mềm ghi dữ liệu (`Recording`). |
| **b5** | `D130` | Dữ liệu mô-men/góc hợp lệ (`Data Valid`). |
| **b6** | `M3` / `D134` | Chu trình đo hoàn tất (`Done`). |
| **b7** | `M4` | Hệ thống đang báo lỗi (`Fault`). |

---

## 2. Các Thanh ghi Tính toán Nội bộ trong PLC

| Thanh ghi | Ký hiệu | Mô tả chức năng |
| :--- | :--- | :--- |
| **D150** | `JOG_SPEED` | Tốc độ Jog manual (dùng cho lệnh `DPLSV`). |
| **D160** | `ANGLE_DEV` | Sai lệch góc thực tế giữa góc đích và góc hiện tại (`D125 - D124`). |
| **D161** | `ABS_DEV` | Trị tuyệt đối sai lệch góc (`ABS(D160)`). |
| **D164** | `PULSE_COUNT` | **Số xung cần phát** tương ứng với góc lệch (nạp vào lệnh `PLSY`). |
| **D172** | `START_ANGLE` | Góc xuất phát của phase đo hiện tại. |
| **D182** | `DELTA_ANGLE` | Góc dịch chuyển thực tế tính toán từ lượng xung phát ra. |
| **D8140** | `Y000_PULSE` | Bộ đếm tổng số xung đã phát ra ở ngõ Y000 (Thanh ghi đặc biệt FX3U). |

---

## 3. Logic Hoạt động Cốt lõi của PLC

### 3.1. Quy đổi Góc xoay sang Số lượng xung phát (`PLSY`)
Tỉ số truyền cơ khí giữa Servo và bàn xoay đo mô-men:
*   Độ phân giải Driver Servo: `10,000 xung / vòng`.
*   Tỉ số giảm tốc hộp số: `1/20` (Trục đo quay 1 vòng thì servo quay 20 vòng).
*   Tổng số xung cho 1 vòng trục đo: $10,000 \times 20 = 200,000 \text{ xung}$.
*   Hệ số quy đổi: $\frac{200,000 \text{ xung}}{360^\circ} = 555.5556 \text{ xung/độ}$.

Trong PLC, để tránh số thực, góc được nhân với 100 (`Angle_x100`). Công thức tính số xung phát ra `D164` từ sai lệch góc `D161` là:
$$\text{D164} = \frac{\text{D161} \times 200,000}{36,000} = \frac{\text{D161} \times 50}{9}$$
*(Lệnh trong PLC: `MUL D161 K50 D162` tiếp theo `DIV D162 K9 D164`)*.

### 3.2. Logic điều khiển Hướng quay (DIR - `Y004`)
*   Sai lệch góc `D160 = D125 - D124`.
*   **Chiều quay Dương (Quay phải - Lực dương):** Khi `D160 > 0`, PLC sẽ **`RST Y004`** (OFF).
*   **Chiều quay Âm (Quay trái - Lực âm):** Khi `D160 < 0`, PLC sẽ **`SET Y004`** (ON).
*(Đây là logic đã được đảo ngược để ưu tiên quay phải trước nhằm xuất ra giá trị góc và mô-men dương).*

### 3.3. Logic Giả lập Góc hiện tại `D124` để Vẽ đồ thị
PLC không sử dụng Encoder phản hồi để xác định chiều góc nhằm tránh nhiễu và sai lệch hệ tọa độ. Thay vào đó, góc hiện tại `D124` được tính bằng toán học:
1.  Đọc bộ đếm xung phát ra `D8140`. PLC so sánh lượng xung lệch để tính ra góc dịch chuyển thực tế `D182` theo công thức ngược:
    $$\text{D182} = \frac{\text{Delta Pulse} \times 36,000}{200,000} = \frac{\text{Delta Pulse} \times 9}{50}$$
2.  Cập nhật góc hiển thị:
    *   Nếu đang đi tới góc đích lớn hơn (`D125 >= D172`): `D124 = D172 + D182` (Góc tăng).
    *   Nếu đang đi tới góc đích nhỏ hơn (`D125 < D172`): `D124 = D172 - D182` (Góc giảm).

### 3.4. Logic Dừng khẩn cấp (EMG - Chân `X004`)
Tiếp điểm khẩn cấp `X004` (Nút nhấn EMG vật lý bên ngoài) được tích hợp trực tiếp vào các mạch giữ của PLC:
*   Khi nhấn `X004` (tiếp điểm mở ra/ANI X004):
    1. Ngắt ngay lập tức cuộn giữ `M0` (Hệ thống dừng RUN).
    2. Ngắt ngõ ra Servo ON `Y005` (Servo mất lực giữ, tự do).
    3. Hủy bỏ chu trình đo đang chạy (`RST M1`, `RST M2`), đưa `D122` (Phase) về 0.
