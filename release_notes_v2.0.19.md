# ZE-SG3 Torque Acquisition v2.0.19

## Thay đổi chính / Key Updates

1. **Xác nhận và tự động xóa biểu đồ khi chuyển từ tab Phân tích sang tab Thu thập**:
   - Khi người dùng đang ở tab **📊 Phân tích (Plot Viewer)** và bấm chuyển sang tab **📡 Thu thập**, nếu đang có dữ liệu biểu đồ/mẫu đo, hệ thống sẽ hiển thị hộp thoại xác nhận:
     > *"Bạn có muốn xóa dữ liệu biểu đồ trước khi chuyển sang tab Thu thập không?"*
   - Nếu chọn **Đồng ý (`OK`)**:
     - Tự động xóa sạch toàn bộ biểu đồ, danh sách tệp mẫu và kết quả phán định trên tab Phân tích.
     - Tự động xóa biểu đồ thời gian thực (`Torque vs Time`), biểu đồ góc (`Torque vs Angle`) và làm mới phiên đo trên tab Thu thập.
     - Áp dụng đồng nhất cho **tất cả các loại mô-men** (*Breakaway Torque, Operating Torque, Oscillating Torque và Đo góc*).
   - Nếu chọn **Hủy (`Cancel`)**: Bảo lưu toàn bộ dữ liệu biểu đồ trên cả 2 tab.
   - Nếu cả 2 tab chưa có dữ liệu biểu đồ: Chuyển tab mượt mà, không hiển thị hộp thoại làm phiền người dùng.

2. **Hỗ trợ đầy đủ song ngữ VI/EN cho hộp thoại và thông báo xóa biểu đồ**:
   - Tích hợp nhãn dịch đa ngôn ngữ cho tiêu đề, nội dung và nút bấm hộp thoại xác nhận.
   - Ghi nhận thông báo trực quan vào khung Terminal Log sau khi xóa biểu đồ thành công.

Asset đính kèm là file cài đặt `mysetupZE-SG3 Torque Acquisition v2.0.19.exe` được tạo bằng Inno Setup.
