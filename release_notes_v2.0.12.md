# ZE-SG3 Torque Acquisition v2.0.12

## Cải tiến & Sửa lỗi quan trọng (Tính năng đo góc Angle Program)

- **Đánh giá lực tuyệt đối `abs(torque)` cho Angle Program**:
  - Hỗ trợ dừng chuẩn xác khi đạt ngưỡng giới hạn độ lớn mô-men (chẳng hạn 1.0 Nm) cho dù cảm biến ZE-SG3 đo ra mô-men dấu Dương (+1.0 Nm) hay dấu ÂM (-1.0 Nm).
  - Khắc phục hoàn toàn hiện tượng Servo chạy vượt quá 2 Nm không dừng khi mô-men sinh ra bị mang dấu âm.
- **Tự động Tare cảm biến trước khi đo góc**:
  - Tự động trừ bì (Tare) cảm biến ZE-SG3 về 0.000 Nm ngay khi bắt đầu Angle Program.
- **Tự động điều chỉnh `Safety Torque Limit` cho Angle Mode**:
  - Tự động thiết lập ngưỡng ngắt khẩn cấp an toàn theo tỷ lệ 150% ngưỡng giới hạn Angle (ví dụ 1.5 Nm - 2.0 Nm đối với limit 1.0 Nm), ngăn chặn hoàn toàn việc vọt lực quá cao.
  - Cho phép quan sát và chỉnh ô "Giới hạn lực an toàn" trong dialog cài đặt của chế độ Angle.

Asset đính kèm gồm EXE portable và bộ cài Windows tạo bằng Inno Setup.
