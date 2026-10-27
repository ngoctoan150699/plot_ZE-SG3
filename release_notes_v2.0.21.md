# ZE-SG3 Torque Acquisition v2.0.21

## Thay đổi chính / Key Updates

1. **Khắc phục lỗi không JOG được sau khi chạy test**:
   - Khắc phục triệt để lỗi lệch cache `_last_written` trong `PlcControlService`: tự động đồng bộ giá trị các thanh ghi D101..D108 khi ghi cấu hình test (`write_test_config`).
   - Bổ sung cờ `force=True` khi ghi chế độ Manual (`write_mode(0, force=True)`) giúp gửi thẳng lệnh Modbus xuống PLC, không bị bộ nhớ đệm chặn.
   - Lệnh `jog_plus` (D110) và `jog_minus` (D111) ghi trực tiếp 1/0 xuống PLC, đảm bảo độ phản hồi 100% của nút bấm, không bị nuốt lệnh.
   - Tự động dọn dẹp trạng thái PLC khi test kết thúc: gửi `stop_record()`, xóa cờ Done (`clear_done()`), đưa PLC về chế độ Manual (`D101 = 0`) và khôi phục tốc độ JOG `D104`.
   - Tự động kích hoạt RUN (`M0 = 1`) và Servo ON (`Y005 = 1`) trước khi phát xung JOG nếu hệ thống chưa sẵn sàng.
   - Sửa hàm `_selected_plc_mode` hỗ trợ đúng ngôn ngữ tiếng Việt theo mã mode (`breakaway`, `operating`, `oscillating`).

2. **Tự động nhập dữ liệu vào Phân tích (Plot Viewer) sau khi đo xong**:
   - Khi chu trình đo hoàn tất (PLC báo xong hoặc người dùng dừng ghi), hệ thống tự động xuất dữ liệu CTR và nạp trực tiếp vào tab **📊 Plot Viewer (Phân tích dữ liệu)**, tự động chuyển tab để xem biểu đồ và kết quả ngay.
   - Thêm chế độ `silent=True` khi nạp file để không hiện popup hộp thoại làm gián đoạn người vận hành.
   - Bổ sung tùy chọn `[x] ⚡ Tự động phân tích khi đo xong` (`chk_auto_import_plot`) trên giao diện nhóm Nhập dữ liệu, mặc định luôn bật và tự động lưu/khôi phục trong settings.

3. **Cải tiến giao diện ô Checkbox (hiển thị dấu X rõ nét thay vì tô màu kín khối)**:
   - Bổ sung icon vector SVG dấu X sắc nét cho cả giao diện sáng (Light) và giao diện tối (Dark).
   - Khắc phục hiện tượng ô checkbox bị tô kín màu đặc khi được chọn; hiển thị đúng ô vuông nền sáng sạch sẽ với dấu X màu xanh rõ ràng ở giữa.

Asset đính kèm là file cài đặt `mysetupZE-SG3 Torque Acquisition v2.0.21.exe` được tạo bằng Inno Setup.
