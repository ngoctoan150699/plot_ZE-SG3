# ZE-SG3 Torque Acquisition v2.0.14

## Thay đổi chính / Key Updates

1. **Khắc phục lỗi ghi nhớ Cài đặt lấy mẫu (Sampling Settings)**:
   - Khắc phục triệt để lỗi không lưu/không nhớ **Chu kỳ lấy mẫu** (`interval_ms`), **Cửa sổ biểu đồ** (`window_s`), **Giới hạn Y** (`y_max`, `fixed_y`) khi khởi động lại ứng dụng.
   - Khóa lưu UI (`_restoring_ui_state = True`) trong suốt chu trình khởi tạo ban đầu để tránh các tín hiệu giao diện (`currentTextChanged`, `currentIndexChanged`) vô tình ghi đè giá trị mặc định lên `settings.json`.
   - Tự động áp dụng và đồng bộ ngay chu kỳ lấy mẫu đã lưu xuống bộ thu thập dữ liệu (`DataCollectorService` / `ModbusBusScheduler`) và biểu đồ khi vừa mở ứng dụng.
   - Đảm bảo việc bấm `Save` trong hộp thoại Cài đặt lấy mẫu lập tức ghi lưu đồng bộ vào file `settings.json`.

Asset đính kèm là bộ cài đặt `mysetupZE-SG3 Torque Acquisition v2.0.14.exe` tạo bằng Inno Setup cho Windows.
