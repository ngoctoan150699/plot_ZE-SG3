# Yêu Cầu Phát Triển Phần Mềm - Tài Liệu R1 (Software Development - R1)

Tài liệu này tổng hợp các yêu cầu cải tiến và bổ sung chức năng cho phần mềm đo mô-men xoắn (torque) của thiết bị servo và xuất báo cáo.

---

## TRANG 1: CHƯƠNG TRÌNH ĐO & THIẾT LẬP SERVO

### 1. Bổ Sung Chương Trình Đo
*   **Part Name Selection**: Thêm các hộp xổ xuống (Combobox) cho phép chọn loại sản phẩm cần đo:
    *   `ITR`
    *   `B/Joint`
    *   `OTR`
    *   `S/Link`
*   **Cấu hình Servo (Setup Button)**: Tạo nút **Setup** để người dùng có thể cấu hình các thông số sau cho từng loại sản phẩm và ứng với 2 chế độ đo mô-men:
    *   Góc độ âm (Negative angle)
    *   Góc độ dương (Positive angle)
    *   Tốc độ servo (Servo speed)
*   **Điều khiển Servo & Ghi dữ liệu**:
    *   **Bắt đầu ghi (Start Record)**: Đồng nghĩa với việc khởi chạy servo để bắt đầu chu trình đo.
    *   **Kết thúc**: Khi chương trình chạy xong chu trình, phần mềm tự động dừng ghi.
    *   **Dừng ghi thủ công**: Nếu bấm dừng ghi, chương trình servo sẽ dừng lập tức. Đổi tên nút này thành **Stop**.

### 2. Các Chế Độ Đo (Test Item)
Thiết kế hộp lựa chọn (Combobox) cho 2 chế độ đo:
1.  **Breakaway Torque (B)**: Mô-men phá vỡ.
2.  **Operating Torque (O)**: Mô-men hoạt động.

#### Quy trình hoạt động của Servo cho từng chế độ đo:

*   **Chương trình đo Mô-men Hoạt Động (Operating Torque - O):**
    *   Dựa trên các giá trị góc âm, góc dương và tốc độ servo đã thiết lập.
    *   Khi nhấn **Bắt đầu ghi**, servo thực hiện chu trình (`1 cycle`): Chạy từ vị trí ban đầu `0°` $\rightarrow$ đi qua **góc dương** $\rightarrow$ đi ngược lại **góc âm** $\rightarrow$ quay về `0°`.
    *   Hệ thống thực hiện lặp lại **3 cycle** thì tự động kết thúc.

*   **Chương trình đo Mô-men Phá Vỡ (Breakaway Torque - B):**
    *   Khi nhấn **Bắt đầu ghi**, servo chạy từ vị trí ban đầu `0°` $\rightarrow$ đi qua **góc dương** $\rightarrow$ quay ngược lại `0°`.
    *   **Lưu ý:** Chỉ lấy dữ liệu đo được trong khoảng từ `0°` đến góc dương (không lấy dữ liệu ở chiều quay ngược lại).

### 3. Vấn Đề Cần Cải Thiện Trong Phần Mềm (Mục 1 - 3)
1.  **Ngôn ngữ**: Chuyển giao diện sang dạng **Song ngữ (Tiếng Anh / Tiếng Việt)**.
2.  **Thêm phần chương trình đo** (như mô tả ở trên).
3.  **Bổ sung biểu đồ Torque-Angle**:
    *   Chia đôi khu vực hiển thị biểu đồ: Một bên hiển thị biểu đồ **Torque – Time**, một bên hiển thị biểu đồ **Torque – Angle**.
    *   **Mô phỏng chu trình (1 Cycle)**: 
        $$\text{Torque } 0^\circ \rightarrow +36^\circ \text{ (Thay đổi tùy theo thiết lập)} \rightarrow -36^\circ \rightarrow 0^\circ$$

---

## TRANG 2: XUẤT NHẬP DỮ LIỆU & BÁO CÁO (PLOT VIEWER)

### 4. Xuất Dữ Liệu
*   Không cần thiết lập chức năng này nữa.

### 5. Import Dữ Liệu Sang Công Cụ Khác
*   Chỉ giữ lại nút **Import to plot viewer**.
*   **Xóa bỏ** nút và tab **Import to converter**.
*   Khi nhấn **Import to plot viewer**, biểu đồ *Torque-Angle* sẽ tự động được chuyển sang tab *Plot Viewer*, đồng thời màn hình tự động chuyển sang tab này (nếu khả thi).

### 6. Cải Tiến Tại Tab Plot Viewer
Tích hợp và tự động hóa quy trình để tối ưu thao tác so với phiên bản trước (vốn yêu cầu chạy PLC $\rightarrow$ Lưu CSV $\rightarrow$ Nhập thủ công $\rightarrow$ Xuất báo cáo).

#### Các nút đường dẫn thư mục:
*   Nút **"CSV File path"**: Chọn thư mục để tự động lưu các file CSV khi chạy xong.
*   Nút **"Report File path"**: Chọn thư mục để tự động lưu báo cáo.

#### Các trường thông tin đầu vào (Input Fields):
*   **Test Item**: Tự động liên kết từ chế độ đo vừa chạy: `Breakaway Torque (B)` hoặc `Operating Torque (O)`.
*   **Part Name**: Tự động liên kết từ chương trình vừa chạy: `ITR`, `B/Joint`, `OTR`, `S/Link`.
*   **Part No**: Tự động chuyển đổi thành **VIẾT HOA** khi người dùng nhập vào.
*   **Test Purpose**: Hộp xổ chọn gồm:
    *   `Setting (S)`
    *   `First (F)`
    *   `Middle (M)`
    *   `Final (Z)`
    *   `Development (D)`
    *   `Long-term (L)`
    *   `Other (O)`
*   **Tester**: Tự động chuyển thành **VIẾT HOA KHÔNG DẤU** khi nhập.
*   **Team**: Hộp xổ chọn gồm: `PM`, `QM`, `PT`, `EDTV`.
*   **Line No**: Hộp xổ chọn gồm: `ITR #1`, `ITR #2`, `ITR #3`, `B/Joint #1`, `B/Joint #2`, `B/Joint #3`, `OTR #1`, `OTR #2`, `OTR #3`, `S/Link #1`, `S/Link #2`, `S/Link #3`, `S/Link #4`, `Other`.
*   *Các trường thông tin khác*: Giữ nguyên như cũ.

#### Nút chức năng "Save the report":
Khi nhấn nút này, hệ thống sẽ thực hiện đồng thời các tác vụ sau:

1.  **Lưu file CSV gốc**: Lưu toàn bộ dữ liệu ban đầu (bao gồm tất cả các cycle) vào thư mục CSV đã thiết lập. Quy tắc đặt tên file:
    $$\text{[yymmdd]-[Test item]-[Part No]-[Purpose]-[Team]-[Số thứ tự mẫu]}$$
    *   `yymmdd`: Lấy theo ngày giờ hiện tại của hệ thống máy tính.
    *   `Test item`: Sử dụng ký tự viết tắt `B` (Breakaway) hoặc `O` (Operating).
    *   `Part No`: Lấy 7 ký tự đầu tiên của giá trị Part No nhập vào.
    *   `Purpose`: Lấy ký tự đầu tiên của mục đích kiểm tra (ví dụ: `S` cho Setting).
    *   `Số thứ tự mẫu`: Tự động tăng từ `01`, `02`,... nếu trùng các thông tin phía trước.
    *   *Ví dụ*: `260525-B-CBJ0001-S-QM-01`
2.  **Lưu file Báo Cáo (Report)**: Lấy dữ liệu kết quả sau khi đã điều chỉnh vùng dữ liệu và cycle theo form của CTR, tự động tạo và lưu vào thư mục báo cáo với cùng quy tắc đặt tên như trên. Form báo cáo tương tự như phiên bản trước.

---

## TRANG 3: KẾT QUẢ ĐO & HIỆU CHUẨN

### 7. Kết Quả Đo
Hiển thị kết quả đo cho cả hai loại mô-men sau khi dữ liệu được chuyển từ phần thu thập sang:

*   **Breakaway torque**: Lấy giá trị lớn nhất (**Max**) trong kết quả đo.
*   **Operating torque**: Lấy các giá trị **Average (Trung bình)**, **Max**, **Min**.
    *   Cần thiết lập nút **Setup** để người dùng cấu hình vùng lấy dữ liệu (vòng cycle và tỷ lệ phần trăm vùng trung tâm).

#### Bảng cấu hình vùng lấy dữ liệu Operating Torque (Ví dụ):

| Part Name | Operating torque value setup (%) | Cycle |
| :--- | :---: | :---: |
| **ITR** | 80% | 3 |
| **B/Joint** | 80% | 3 |
| **OTR** | - | - |
| **S/Link** | - | - |

> [!NOTE]
> **Giải thích cách tính**:
> Ví dụ, nếu người dùng cấu hình chọn **80%** và cycle thứ **3**:
> *   Hệ thống chỉ lấy dữ liệu của vòng chạy (cycle) thứ 3.
> *   Loại bỏ 10% ở đầu chu kỳ và 10% ở cuối chu kỳ, chỉ lấy 80% vùng dữ liệu ở giữa để tính toán các thông số Max, Min, Average.
> 
> ```
> Cycle 3: |---[ 10% Bỏ ]---[        80% Lấy Dữ Liệu        ]---[ 10% Bỏ ]---|
> ```

*   **Đánh giá OK/NG**:
    *   Nếu kết quả đo nằm trong Spec (tiêu chuẩn): Hiển thị chữ **OK** màu **Xanh lá**.
    *   Nếu kết quả đo nằm ngoài Spec: Hiển thị chữ **NG** màu **Đỏ**.

### 8. Hiệu chuẩn (Calibration)
*   Tại khu vực cấu hình/hiệu chuẩn: Đổi tên trường **Factor K** thành **Calibration**.
