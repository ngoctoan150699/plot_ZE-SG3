# ZE-SG3 Torque Acquisition v2.0.13

## Thay đổi chính / Key Updates

1. **Sổ tùy chọn mã hàng (Part No. Dropdown & Auto-complete)**:
   - Tự động nạp danh sách mã hàng từ file tiêu chuẩn (`Upload standard.xlsx` hoặc file người dùng chọn).
   - Cho phép vừa chọn từ dropdown vừa nhập tay tự do (tự động viết hoa, giới hạn 8 ký tự).
   - Tự động tra cứu đồ gá, ren, cảnh báo và giới hạn mô-men khi chọn/nhập mã hàng.
   - Đồng bộ gợi ý mã hàng sang ô *MÃ SẢN PHẨM* trong tab Phân tích dữ liệu (Plot Viewer).

2. **Cập nhật giao diện điều khiển & dữ liệu thời gian thực**:
   - Khung *Thông tin dữ liệu*: Mặc định chỉ hiển thị Mô-men và Trạng thái; các thông số phụ (Samples, Time, Tare, PLC Angle, Max, Min) được thu gọn trong nút bấm Chi tiết/Ẩn bớt đa ngôn ngữ.
   - Bố cục *Điều khiển PLC/Servo*: Đặt 2 nút quay JOG (`◀ Quay -` và `Quay + ▶`) lên trên nút `▶ CHẠY`.

3. **Cải tiến thông tin báo cáo & Xuất Excel (Report & Summary Report)**:
   - Thêm trường **Machine ID** (Mã máy) tại ô L5 (đề mục) và L6 (giá trị) trong file báo cáo Excel.
   - Thêm cột **Internal spec Min** (ô L7 đề mục, L8 giá trị) và **Internal spec Max** (ô M7 đề mục, M8 giá trị).
   - Tách biệt đánh giá bản vẽ và đánh giá nội bộ: `JUDGMENT (Drawing spec)` tại hàng 7 và `JUDGMENT (Internal spec)` tại E8:F8; chuyển `LINE NO` xuống hàng 9.
   - Đầy đủ hỗ trợ đa ngôn ngữ VI/EN cho tất cả các nhãn báo cáo và bảng đồ thị.

Asset đính kèm là bộ cài đặt `mysetupZE-SG3 Torque Acquisition v2.0.13.exe` tạo bằng Inno Setup cho Windows.
