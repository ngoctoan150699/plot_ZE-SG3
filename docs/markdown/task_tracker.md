# Bảng Theo Dõi Tiến Độ: Software Development R2

Checklist này giúp bạn và quản lý kiểm tra tiến độ chi tiết từng phần nhỏ của ứng dụng.

---

## 📋 TIẾN ĐỘ THỰC HIỆN (CHECKLIST)

### [x] Session 1: Khai Báo Các Hằng Số & Danh Mục Mới (Core Constants)
- [x] Thêm các danh mục combobox mới (`PART_NAMES`, `TEST_PURPOSES`, `TEAMS`, `LINE_NOS`) vào `python/domain/constants.py`
- [x] Định nghĩa địa chỉ các thanh ghi PLC Modbus (`REG_PLC_CONTROL`, `REG_PLC_STATUS`...) vào `python/domain/constants.py`
- [x] Đổi tên các hằng số liên quan đến "Factor K" thành "Calibration" (không chứa hằng số thừa)

### [x] Session 2: Tạo Các Thực Thể Dữ Liệu Mới (Domain Entities)
- [x] Định nghĩa các thực thể `ServoProfile`, `OperatingTorqueSetup`, `ReportMetadata` trong `python/domain/entities.py`
- [x] Cập nhật `SampleData` thêm trường `angle_deg` và `cycle`
- [x] Mở rộng `RecordingSession` để lưu vết trạng thái góc xoay và chu kỳ hiện tại

### [x] Session 3: Mở Rộng Hệ Thống Lưu Trữ Cấu Hình (App Settings)
- [x] Thêm logic đọc/ghi cấu hình các profile servo vào `python/infrastructure/app_settings.py`
- [x] Thêm logic đọc/ghi cài đặt vùng dữ liệu Operating (`operating_setups`) vào `python/infrastructure/app_settings.py`
- [x] Thêm logic đọc/ghi đường dẫn thư mục lưu báo cáo (`report_paths`) vào `python/infrastructure/app_settings.py`

### [x] Session 4: Viết Bộ Tiện Ích Chuẩn Hóa Chữ Tester (Tester String Helper)
- [x] Viết hàm loại bỏ dấu tiếng Việt và tự động viết hoa (`remove_vietnamese_diacritics`)
- [x] Tạo unit test chạy độc lập kiểm tra kết quả chuẩn hóa chuỗi Tester

### [x] Session 5: Tạo Module Dịch Song Ngữ (Bilingual Dictionary & Service)
- [x] Tạo tệp `python/ui/i18n.py` chứa từ điển tiếng Anh và tiếng Việt
- [x] Lập trình class `I18n` hỗ trợ phương thức dịch nhanh `t(key)` và đổi ngôn ngữ `toggle()`

### [x] Session 6: Thiết Kế Bộ Điều Khiển PLC Modbus (PLC Driver)
- [x] Khai báo interface `IPLCServoController` trong `python/application/interfaces.py`
- [x] Lập trình driver `PLCServoController` trong `python/infrastructure/plc_servo_controller.py` thực hiện ghi thanh ghi Modbus
- [x] Hỗ trợ chế độ chạy mô phỏng `DummyPLCServoController` khi không kết nối thiết bị thực

### [x] Session 7: Lập Trình Chu Trình Đo Động Cơ (Servo Sequence Service)
- [x] Lập trình chạy chế độ Operating (3 cycle lặp lại 0 -> + -> - -> 0) trong `python/application/servo_service.py`
- [x] Lập trình chạy chế độ Breakaway (0 -> + -> 0, chỉ ghi chiều đi) trong `python/application/servo_service.py`
- [x] Tích hợp tính toán góc liên tục theo công thức: `angle = speed * time * 6.0`

### [x] Session 8: Xây Dựng Bộ Tính Toán Kết Quả Đo (Measurement Calculator)
- [x] Lập trình thuật toán cắt lấy 80% dữ liệu ở giữa của cycle 3 trong `python/application/measurement_service.py`
- [x] Lập trình tính toán Avg, Max, Min cho Operating và lấy Max cho Breakaway
- [x] Lập trình bộ đánh giá OK/NG dựa trên so sánh giới hạn tiêu chuẩn (Spec Limits)

### [ ] Session 9: Viết Dịch Vụ Lưu Trữ Báo Cáo Tự Tăng (Report & File Service)
- [ ] Viết logic sinh tên tệp tự động tăng số thứ tự mẫu `yymmdd-T-PartNo-P-Team-##.csv`
- [ ] Lập trình lưu đồng thời tệp raw CSV và tệp CTR report tương ứng vào đúng thư mục cấu hình

### [ ] Session 10: Tạo Đồ Thị Góc Thời Gian Thực (Torque-Angle Live Chart)
- [ ] Tạo widget `TorqueAnglePlot` thừa kế `FigureCanvas` trong `python/ui/widgets/torque_angle_plot.py`
- [ ] Tối ưu hóa việc vẽ đồ thị góc xoay thời gian thực bằng Matplotlib blit

### [ ] Session 11: Cập Nhật Vùng Đồ Thị & Bố Cục UI Chính (Main UI Splitter & Language)
- [ ] Xóa bỏ tab Converter và nút "Import to Converter" trên MainWindow
- [ ] Chia đôi màn hình đồ thị chính bằng `QSplitter` hiển thị song song Đồ thị Time và Angle
- [ ] Tích hợp nút chọn ngôn ngữ Anh-Việt, dịch động các nhãn và nút bấm giao diện chính
- [ ] Đổi tên nhãn "Factor K" thành "Calibration"

### [ ] Session 12: Thiết Kế Lại Nhóm Thông Tin Tab Plot Viewer (Plot Viewer Layout)
- [ ] Redesign nhóm "Report Info" QGroupBox trong `draw_plot.py` với các input mới (Part No viết hoa, Tester viết hoa không dấu...)
- [ ] Bổ sung các ô chọn thư mục lưu **CSV File path** và **Report File path** kèm nút `[📂]`
- [ ] Tích hợp nút **Save the Report** gọi dịch vụ lưu kép báo cáo
- [ ] Đồng bộ hóa nút **Import to Plot Viewer** chuyển đổi dữ liệu và tự động nhảy tab màn hình

### [ ] Session 13: Tích Hợp Entry Point & Chạy Thử (System Integration)
- [ ] Đăng ký khởi tạo các service mới và inject trong `python/main.py`
- [ ] Chạy thử nghiệm toàn hệ thống bằng Python 3.14 không xảy ra lỗi nạp thư viện
