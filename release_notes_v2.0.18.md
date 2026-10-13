# ZE-SG3 Torque Acquisition v2.0.18

## Thay đổi chính / Key Updates

1. **Bắt buộc nhập mã hàng 8 ký tự trước khi bắt đầu ghi**:
   - Nút "▶️ Bắt đầu ghi" (`btn_rec_start`) chỉ sáng màu cam và được phép thao tác khi ô Mã hàng nhập đủ đúng 8 ký tự.
   - Khi chưa đủ 8 ký tự (hoặc để trống), nút bị vô hiệu hóa (`disabled`) kèm tooltip hướng dẫn *"Chưa nhập đủ 8 ký tự mã hàng"*.
   - Khởi động ứng dụng hoặc sau khi hoàn tất đo sẽ để trống ô mã hàng, không tự ý chọn sẵn mã hàng đầu tiên.

2. **Khóa chỉnh sửa ô nhập liệu trên tab Phân tích (Plot Viewer)**:
   - Khóa ô Mã sản phẩm (`part_no_edit`), Tiêu chuẩn bản vẽ Min/Max (`spec_min_spin`, `spec_max_spin`), và Tiêu chuẩn nội bộ Min/Max (`internal_spec_min_spin`, `internal_spec_max_spin`) ở chế độ chỉ đọc (`read-only`), không nhận focus và không hiển thị completer.
   - Toàn bộ các giá trị này tự động đồng bộ và ăn theo mã hàng được chọn từ tab Thu thập tự động.

3. **Tự động xóa 5 hạng mục bắt buộc + Remark sau khi lưu Mô-men hoạt động**:
   - Sau khi lưu báo cáo thành công ở chế độ **Operating Torque** hoặc **Oscillating Torque**, hệ thống tự động xóa sạch 5 hạng mục bắt buộc (`part_no`, `test_purpose`, `tester`, `team`, `line_no`) và `remark`.
   - Đồng thời tự động xóa mã hàng bên tab Thu thập, reset hiển thị tiêu chuẩn và vô hiệu hóa lại nút "Bắt đầu ghi" để sẵn sàng cho lần đo tiếp theo của người khác.
   - Ở chế độ **Breakaway Torque**, toàn bộ thông tin được bảo lưu nguyên vẹn để tiếp tục chu trình đo Operating Torque.
   - Không xóa sớm Remark khi vừa dừng ghi.

Asset đính kèm là file cài đặt `mysetupZE-SG3 Torque Acquisition v2.0.18.exe` được tạo bằng Inno Setup.
