# ZE-SG3 Torque Acquisition v2.0.8

## Thay đổi chính

- Thêm chương trình Đo góc / Angle dành riêng cho sản phẩm ITR.
- Cấu hình chương trình Angle gồm giới hạn mô-men dương, giới hạn mô-men âm và tốc độ chạy.
- Điều khiển servo theo torque thời gian thực qua hai bước xác nhận VI/EN; không ghi mẫu và không chuyển sang tab Phân tích.
- Cải thiện trở về vị trí ban đầu bằng phản hồi góc D124, phát hiện giao qua mốc và timeout an toàn; sử dụng đúng tốc độ Angle đã cài.
- Chỉ xóa thông tin nhập báo cáo sau Operating/Oscillating; giữ thông tin sau Breakaway.
- Giữ nguyên biểu đồ cũ trong tab Phân tích khi chuyển qua lại giữa các tab.

Asset đính kèm gồm EXE portable và bộ cài Windows tạo bằng Inno Setup.
