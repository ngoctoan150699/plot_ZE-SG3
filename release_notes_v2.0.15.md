# ZE-SG3 Torque Acquisition v2.0.15

## Thay đổi chính / Key Updates

1. **Khắc phục lỗi biểu đồ bên Plot Viewer tự xóa khi chuyển tab**:
   - Giữ nguyên toàn bộ đồ thị, danh sách mẫu và thông tin phân tích khi người dùng chuyển qua lại giữa tab Thu thập (Acquisition) và tab Xem biểu đồ (Plot Viewer).
   - Ngăn ngừa tình trạng tự động dọn dẹp dữ liệu hoặc lệch chế độ hiển thị trục khi chuyển tab.

2. **Đồng bộ chuẩn xác Test Item hai chiều giữa hai tab**:
   - Khắc phục lỗi combobox Test Item bên Plot Viewer không cập nhật theo khi thay đổi chế độ đo ở tab Thu thập.
   - Chuẩn hóa mã hóa chế độ đo (`Breakaway`, `Operating`, `Oscillating`) hỗ trợ đầy đủ và mượt mà trên cả giao diện Tiếng Việt lẫn Tiếng Anh.

3. **Tự động xóa Remark đúng chu trình đo**:
   - Tự động xóa nội dung ô Remark sau khi kết thúc chu trình đo **Operating Torque** hoặc **Oscillating Torque**.
   - Giữ nguyên Remark khi đo **Breakaway Torque** theo quy trình thao tác thực tế của người vận hành.

4. **Cho phép upload tiêu chuẩn (Standard) không bắt buộc Spec nội bộ**:
   - Tiêu chuẩn nội bộ (`Internal spec Min/Max`) được chuyển thành tùy chọn (tham khảo). Cho phép ô này để trống trong file Excel tải lên mà không bị báo lỗi.
   - Khi không có tiêu chuẩn nội bộ, hệ thống hiển thị phán định `—` thay vì tự động so sánh với 0.0 gây báo `NG` sai.
   - Báo cáo chi tiết và Summary Report hiển thị dấu `—` hoặc để trống chuẩn xác.

Asset đính kèm là bộ cài đặt `mysetupZE-SG3 Torque Acquisition v2.0.15.exe` tạo bằng Inno Setup cho Windows.
