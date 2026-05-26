# Kế Hoạch Triển Khai Chi Tiết: Software Development R2

Kế hoạch này chia nhỏ toàn bộ quá trình phát triển thành 13 phiên làm việc (Sessions) độc lập, nhỏ gọn và dễ dàng kiểm thử từng bước.

---

## 📋 DANH SÁCH CÁC PHIÊN LÀM VIỆC (SESSIONS)

### Session 1: Khai Báo Các Hằng Số & Danh Mục Mới (Core Constants)
- **Công việc**: Thêm danh sách Part Names, Test Items, Purposes, Teams, Line Nos và địa chỉ thanh ghi PLC vào `python/domain/constants.py`.
- **Tác động**: [constants.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/domain/constants.py)

### Session 2: Tạo Các Thực Thể Dữ Liệu Mới (Domain Entities)
- **Công việc**: Khai báo các dataclass `ServoProfile`, `OperatingTorqueSetup`, `ReportMetadata`, `MeasurementResult` và cập nhật `SampleData` / `RecordingSession` để lưu trữ dữ liệu góc (`angle_deg`).
- **Tác động**: [entities.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/domain/entities.py)

### Session 3: Mở Rộng Hệ Thống Lưu Trữ Cấu Hình (App Settings)
- **Công việc**: Bổ sung các phương thức `load_` và `save_` cho các cài đặt mới (`servo_profiles`, `operating_setups`, `report_paths`) vào file cấu hình JSON.
- **Tác động**: [app_settings.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/infrastructure/app_settings.py)

### Session 4: Viết Bộ Tiện Ích Chuẩn Hóa Chữ Tester (Tester String Helper)
- **Công việc**: Viết hàm `remove_vietnamese_diacritics(text)` để tự động chuyển ký tự tiếng Việt có dấu sang chữ viết hoa không dấu (Ví dụ: "Lê Văn Tám" -> "LE VAN TAM").
- **Tác động**: Tạo file tiện ích mới hoặc tích hợp trong helper module.

### Session 5: Tạo Module Dịch Song Ngữ (Bilingual Dictionary & Service)
- **Công việc**: Xây dựng class `I18n` quản lý từ điển song ngữ Anh-Việt cho toàn bộ nhãn hiển thị trong ứng dụng.
- **Tác động**: Tạo file mới [i18n.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/i18n.py)

### Session 6: Thiết Kế Bộ Điều Khiển PLC Modbus (PLC Driver)
- **Công việc**: Lập trình interface `IPLCServoController` và class `PLCServoController` kết nối với PLC (Slave ID 2) qua Modbus Holding Registers, hỗ trợ chế độ `Dummy` mô phỏng.
- **Tác động**: Tạo file mới `python/infrastructure/plc_servo_controller.py`

### Session 7: Lập Trình Chu Trình Đo Động Cơ (Servo Sequence Service)
- **Công việc**: Xây dựng logic chạy chu trình cho **Breakaway Torque** (chỉ ghi dữ liệu từ 0 -> Positive, quay về không ghi) và **Operating Torque** (lặp lại 3 cycle từ 0 -> Positive -> Negative -> 0), tự động tính toán góc xoay dựa trên tốc độ và thời gian thực.
- **Tác động**: Tạo file mới `python/application/servo_service.py`

### Session 8: Xây Dựng Bộ Tính Toán Kết Quả Đo (Measurement Calculator)
- **Công việc**: Xây dựng logic lọc dữ liệu Operating (cắt bỏ 10% đầu, 10% cuối chu kỳ 3, giữ lại 80% vùng ở giữa để tính Average, Max, Min) và Breakaway (lấy Max), đánh giá OK/NG dựa trên Spec.
- **Tác động**: Tạo file mới `python/application/measurement_service.py`

### Session 9: Viết Dịch Vụ Lưu Trữ Báo Cáo Tự Tăng (Report & File Service)
- **Công việc**: Thực hiện hàm tự động tạo tên tệp không trùng lặp dạng `yymmdd-B/O-PartNo-Purpose-Team-##` (số thứ tự tự tăng từ 01) và lưu đồng thời cả raw CSV và CTR report.
- **Tác động**: Tạo file mới `python/application/report_service.py`

### Session 10: Tạo Đồ Thị Góc Thời Gian Thực (Torque-Angle Live Chart)
- **Công việc**: Lập trình widget `TorqueAnglePlot` vẽ biểu đồ Mô-men xoắn vs Góc xoay thời gian thực bằng Matplotlib Blit.
- **Tác động**: Tạo file mới `python/ui/widgets/torque_angle_plot.py`

### Session 11: Cập Nhật Vùng Đồ Thị & Bố Cục UI Chính (Main UI Splitter & Language)
- **Công việc**: Gỡ bỏ tab Converter và nút "Import to Converter". Sử dụng `QSplitter` chia đôi biểu đồ Time & Angle. Tích hợp nút đổi ngôn ngữ và đổi tên "Factor K" -> "Calibration".
- **Tác động**: [main_window.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/main_window.py)

### Session 12: Thiết Kế Lại Nhóm Thông Tin Tab Plot Viewer (Plot Viewer Layout)
- **Công việc**: Cải tiến nhóm QGroupBox "Report Info" trong `draw_plot.py` (chứa các box Test Item, Part Name read-only, Part No viết hoa, Tester viết hoa không dấu, Team, Line No), thêm các hộp chọn thư mục CSV/Report Path và nút **Save the Report**. Cập nhật sự kiện click nút **Import to Plot Viewer** chuyển tab và đồ thị.
- **Tác động**: [draw_plot.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/draw_plot/draw_plot.py) và [main_window.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/main_window.py)

### Session 13: Tích Hợp Entry Point & Chạy Thử (System Integration)
- **Công việc**: Cập nhật hàm `main()` trong `main.py` để inject các service mới vào MainWindow. Chạy thử toàn bộ ứng dụng và kiểm chứng.
- **Tác động**: [main.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/main.py)
