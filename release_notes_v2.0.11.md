# ZE-SG3 Torque Acquisition v2.0.11

## Thay đổi chính

- **Sửa lỗi nghiêm trọng chương trình đo góc (Angle Program):**
  - Safety torque limit giờ hoạt động đúng trong chế độ đo góc (trước đây bị bỏ qua hoàn toàn).
  - Safety abort dừng JOG motor ngay lập tức thay vì chỉ gửi lệnh PLC ABORT.
  - Sửa race condition: servo không còn quay vô hạn sau khi dialog xác nhận bị abort nền.
  - Thêm safety margin 150%: tự động ABORT nếu torque vượt quá 150% giới hạn (phòng polling chậm).
  - Reset đúng flag safety giữa các lần chạy angle program.
  - Gán đúng giới hạn safety từ cấu hình ITR_ANGLE profile.

Asset đính kèm gồm EXE portable và bộ cài Windows tạo bằng Inno Setup.
