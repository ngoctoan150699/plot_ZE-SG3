# HƯỚNG DẪN SỬ DỤNG & BÀN GIAO PHẦN MỀM ZE-SG3 TORQUE ACQUISITION

Khách hàng: CÔNG TY CTR VINA

Ngôn ngữ tài liệu: Tiếng Việt

Phiên bản tài liệu: 1.0

Ngày biên soạn: 29/06/2026

Tài liệu này dùng để hướng dẫn vận hành, bàn giao và bảo trì cơ bản hệ thống đo mô-men ZE-SG3 kết hợp PLC/servo. Tài liệu không bao gồm source code phần mềm.


---

# 1. Mục đích tài liệu

Tài liệu này cung cấp hướng dẫn chi tiết cho người vận hành và bộ phận kỹ thuật của CTR VINA khi sử dụng phần mềm ZE-SG3 Torque Acquisition.

- Hiểu tổng quan hệ thống đo mô-men.
- Biết cách kết nối cảm biến ZE-SG3 và PLC.
- Biết cách cấu hình, đo, ghi dữ liệu và phân tích dữ liệu.
- Biết cách đọc Terminal Log và lưu log khi cần hỗ trợ kỹ thuật.
- Biết ý nghĩa các thanh ghi PLC Modbus dùng trong quá trình giao tiếp.
- Có checklist bàn giao để xác nhận hệ thống hoạt động đúng.

# 2. Tổng quan hệ thống

Phần mềm ZE-SG3 Torque Acquisition là ứng dụng chạy trên máy tính Windows, dùng để thu thập dữ liệu mô-men từ thiết bị ZE-SG3, hiển thị biểu đồ thời gian thực, ghi dữ liệu mẫu, phân tích dữ liệu và phối hợp điều khiển PLC/servo trong quá trình test.

| Thành phần | Vai trò |
| --- | --- |
| Máy tính Windows | Chạy phần mềm, hiển thị dữ liệu, lưu CSV/report, gửi lệnh tới PLC. |
| ZE-SG3 | Thiết bị/cảm biến đo mô-men, cung cấp giá trị torque realtime. |
| PLC | Điều khiển trạng thái máy, servo, xi lanh, chu trình test và trả trạng thái về phần mềm. |
| Servo | Tạo chuyển động quay/góc theo chu trình đo. |
| RS485 Modbus RTU | Đường truyền giữa máy tính và PLC. |
| TCP/IP Modbus | Đường truyền đọc dữ liệu ZE-SG3 theo cấu hình hiện tại. |

# 3. Yêu cầu trước khi vận hành

- Máy tính đã cài phần mềm ZE-SG3 Torque Acquisition.
- Cáp mạng/TCP-IP tới ZE-SG3 đã kết nối đúng.
- Cáp USB-RS485 hoặc cổng COM tới PLC đã kết nối đúng.
- PLC đang bật nguồn, đúng Slave ID, đúng baudrate/parity.
- Servo, cơ cấu kẹp/nhả và vùng làm việc cơ khí ở trạng thái an toàn.
- Người vận hành đã kiểm tra jig/sản phẩm trước khi bấm RUN hoặc START RECORD.

# 4. Khởi động phần mềm

Mở ứng dụng ZE-SG3 Torque Acquisition trên máy tính. Khi khởi động, phần mềm tự mở tại màn hình Thu thập > Kết nối để người vận hành kiểm tra kết nối trước.

- Quan sát góc dưới bên trái: trạng thái Chưa kết nối hoặc Đã kết nối.
- Kiểm tra tab Kết nối gồm TCP/IP, RTU (RS485) và Slave.
- Chỉ bắt đầu đo khi cả cảm biến và PLC đã kết nối thành công.

# 5. Mô tả giao diện chính

Giao diện chính chia thành các khu vực: thông tin realtime bên trái, tab thao tác bên trái, biểu đồ realtime bên phải và Terminal Log phía dưới.

| Khu vực | Chức năng |
| --- | --- |
| Thông tin dữ liệu thời gian thực | Hiển thị mô-men hiện tại, trạng thái, tare, max/min, số mẫu, thời gian và góc PLC. |
| Tab Kết nối | Cấu hình TCP/IP cảm biến, cổng COM PLC, baudrate, parity, slave ID. |
| Tab Cấu hình | Cấu hình đơn vị đo, chế độ đo, full scale, sensitivity, lọc nhiễu, tare/reset. |
| Tab Thu thập | Chọn sản phẩm/chế độ đo, điều khiển PLC/servo, ghi dữ liệu, import sang phân tích. |
| Biểu đồ | Hiển thị Torque-Time, Torque-Angle hoặc cả hai. |
| Terminal Log | Ghi lại sự kiện vận hành, lỗi kết nối, trạng thái PLC và thao tác quan trọng. |

# 6. Hướng dẫn kết nối

## 6.1 Kết nối ZE-SG3 qua TCP/IP

- Nhập địa chỉ IP của ZE-SG3.
- Nhập port Modbus TCP, mặc định thường dùng 502.
- Kiểm tra Slave cảm biến.
- Bấm Kết nối.
- Nếu thành công, trạng thái chuyển sang Đã kết nối và dữ liệu torque bắt đầu cập nhật.

## 6.2 Kết nối PLC qua RS485 Modbus RTU

- Chọn đúng COM Port của USB-RS485.
- Chọn baudrate 115200 nếu PLC đang cấu hình mặc định.
- Chọn parity None (N) nếu PLC đang cấu hình mặc định.
- Nhập PLC Slave ID, mặc định theo kế hoạch là 2.
- Bấm Kết nối và kiểm tra Terminal Log.

## 6.3 Kiểm tra trạng thái PLC Modbus

Nút Trạng thái Modbus PLC dùng để xem dữ liệu/trạng thái giao tiếp PLC. Khi có lỗi truyền thông, dùng chức năng này kết hợp Terminal Log để xác định nguyên nhân.

# 7. Hướng dẫn cấu hình cảm biến

| Thông số | Ý nghĩa | Lưu ý |
| --- | --- | --- |
| Đơn vị đo | Đơn vị hiển thị mô-men. | Nên giữ thống nhất theo yêu cầu đo/report. |
| Chế độ đo | Chế độ đo 1 chiều hoặc 2 chiều. | Chọn đúng theo fixture và quy trình test. |
| Full Scale | Dải đo toàn thang của cảm biến. | Cài sai có thể làm kết quả sai. |
| Sensitivity | Độ nhạy mV/V của loadcell/cảm biến. | Phải khớp thông số thiết bị. |
| Filter | Mức lọc nhiễu. | Lọc cao làm tín hiệu mượt hơn nhưng phản hồi chậm hơn. |
| Tare | Đặt điểm 0. | Chỉ tare khi cơ cấu không chịu tải và tín hiệu ổn định. |

# 8. Quy trình đo dữ liệu

## 8.1 Chuẩn bị

- Lắp sản phẩm đúng jig.
- Kiểm tra cơ cấu kẹp/nhả ở trạng thái an toàn.
- Kiểm tra vùng quay servo không vướng.
- Tare cảm biến nếu cần.
- Chọn đúng sản phẩm và chế độ đo.

## 8.2 Bắt đầu đo

- Bấm Kết nối nếu chưa kết nối.
- Chọn sản phẩm/chế độ đo trong tab Thu thập.
- Kiểm tra tốc độ/góc/cycle nếu có.
- Bấm RUN hoặc điều khiển PLC/servo theo quy trình.
- Bấm Bắt đầu ghi để ghi mẫu đo.
- Theo dõi biểu đồ và Terminal Log trong suốt quá trình.

## 8.3 Dừng đo

- Bấm Dừng ghi khi kết thúc hoặc khi cần dừng thủ công.
- Nếu có bất thường, dùng lệnh dừng/khẩn cấp theo quy trình an toàn.
- Kiểm tra dữ liệu mẫu đã ghi.
- Import sang Plot Viewer nếu cần phân tích sâu.

# 9. Hiển thị biểu đồ

Phần mềm hỗ trợ 3 chế độ hiển thị biểu đồ trong màn hình Thu thập.

| Chế độ | Ý nghĩa |
| --- | --- |
| Cả 2 biểu đồ | Hiển thị đồng thời Torque-Time và Torque-Angle như mặc định. |
| Chỉ Torque-Time | Ẩn Torque-Angle, biểu đồ Torque-Time chiếm toàn bộ vùng hiển thị. |
| Chỉ Torque-Angle | Ẩn Torque-Time, biểu đồ Torque-Angle chiếm toàn bộ vùng hiển thị. |

Sau khi chọn chế độ hiển thị, bấm Lưu hiển thị để áp dụng và lưu lại cho lần mở phần mềm tiếp theo.

# 10. Terminal Log

Terminal Log ghi lại các sự kiện quan trọng như kết nối, lỗi truyền thông, thao tác PLC, ghi dữ liệu và trạng thái hệ thống.

- Chuột phải trong ô Terminal Log để mở menu thao tác.
- Chọn Copy all để copy toàn bộ log vào clipboard.
- Chọn Save log để lưu log ra file .txt.
- Chọn Clear để xóa log đang hiển thị.

Khi cần hỗ trợ kỹ thuật, nên lưu Terminal Log ngay sau khi lỗi xảy ra để phục vụ kiểm tra nguyên nhân.

# 11. Phân tích dữ liệu bằng Plot Viewer

Plot Viewer dùng để xem lại dữ liệu đã ghi, chọn cycle, chọn vùng phân tích theo time/angle và tính toán các giá trị thống kê.

- Import dữ liệu từ màn hình Thu thập hoặc mở file CSV đã lưu.
- Chọn file/sample cần phân tích.
- Chọn cycle cần xem, ví dụ cycle 3.
- Chọn chế độ phân tích theo Time hoặc Angle.
- Cài start/end range đúng theo tiêu chuẩn test.
- Kiểm tra kết quả trung bình, min, max và xuất báo cáo nếu cần.

Lưu ý: khi phân tích theo Angle, kết quả trung bình chỉ đúng khi chọn đúng cycle và đúng khoảng angle. Nếu chọn sai cycle/range, kết quả có thể khác Excel hoặc tiêu chuẩn nội bộ.

# 12. Xuất dữ liệu và lưu trữ

- Dữ liệu có thể xuất ra CSV để lưu hồ sơ test.
- File CSV nên lưu theo mã sản phẩm, ngày đo, số lot hoặc số thứ tự mẫu.
- Khi bàn giao dữ liệu cho QA/kỹ thuật, cần kèm thông tin sản phẩm, chế độ đo, cycle và người đo nếu có.
- Không chỉnh sửa trực tiếp file CSV gốc nếu cần truy vết dữ liệu.

# 13. Giao tiếp PLC Modbus

PLC nhận lệnh từ máy tính thông qua các thanh ghi Modbus và trả trạng thái về máy tính. Máy tính chủ yếu đọc mô-men trực tiếp từ ZE-SG3, còn PLC phụ trách điều khiển trạng thái máy, servo, xi lanh và chu trình test.

## 13.1 Thông số PLC tham khảo

| Thông số | Giá trị |
| --- | --- |
| Loại truyền thông | Modbus RTU Slave |
| Baudrate | 115200 |
| Data bit | 8 bit |
| Parity | None |
| Stop bit | 1 |
| Slave ID PLC | 2 |
| Vùng thanh ghi sử dụng | D100..D135 |

## 13.2 Thanh ghi PC ghi xuống PLC

| Thanh ghi | Tên | Ý nghĩa |
| --- | --- | --- |
| D100 | CMD_WORD | Word lệnh chính từ PC xuống PLC. |
| D101 | MODE | 0=Manual, 1=Breakaway, 2=Operating. |
| D102 | POS_ANGLE_X100 | Góc dương x100, ví dụ 3600 = 36.00°. |
| D103 | NEG_ANGLE_X100 | Góc âm x100, ví dụ -3600 = -36.00°. |
| D104 | SPEED_X100 | Tốc độ x100. |
| D105 | CYCLE_SET | Số cycle operating. |
| D106 | OPERATING_WINDOW_PERCENT | Phần trăm vùng lấy dữ liệu operating. |
| D107 | PART_SELECT | Mã sản phẩm/chương trình. |
| D108 | TORQUE_TYPE | 1=Breakaway, 2=Operating. |
| D109 | RESET_FAULT | Reset lỗi. |
| D110 | JOG_PLUS | Jog chiều dương. |
| D111 | JOG_MINUS | Jog chiều âm. |
| D112 | HOME_CMD | Lệnh home/zero. |

## 13.3 Bit trong D100 CMD_WORD

| Bit | Tên | Ý nghĩa |
| --- | --- | --- |
| b0 | PC_START_RUN | Yêu cầu RUN hệ thống. |
| b1 | PC_STOP_RUN | Yêu cầu STOP hệ thống. |
| b2 | START_RECORD | Bắt đầu ghi/chạy test. |
| b3 | STOP_RECORD | Dừng ghi/dừng test. |
| b4 | CYLINDER_TOGGLE | Toggle kẹp/nhả xi lanh. |
| b5 | SERVO_ON_CMD | Cho phép servo ON. |
| b6 | ABORT_CMD | Dừng khẩn chu trình. |
| b7 | CLEAR_DONE | Xóa cờ done sau khi PC đã nhận. |

## 13.4 Thanh ghi PLC trả về PC

| Thanh ghi | Tên | Ý nghĩa |
| --- | --- | --- |
| D120 | STATUS_WORD | Trạng thái tổng. |
| D121 | CURRENT_MODE | Mode đang chạy. |
| D122 | CURRENT_PHASE | Bước/phase hiện tại. |
| D123 | CURRENT_CYCLE | Cycle hiện tại. |
| D124 | CURRENT_ANGLE_X100 | Góc hiện tại x100. |
| D125 | TARGET_ANGLE_X100 | Góc đích hiện tại x100. |
| D126 | CURRENT_SPEED_X100 | Tốc độ hiện tại x100. |
| D127-D128 | SERVO_PULSE | Vị trí/xung servo. |
| D129 | ERROR_CODE | Mã lỗi PLC. |
| D130 | DATA_VALID | 1 = dữ liệu hiện tại hợp lệ để lấy mẫu. |
| D131 | RECORD_ENABLE | 1 = PC được phép ghi mẫu. |
| D132 | CYLINDER_STATUS | 0 = nhả, 1 = kẹp. |
| D133 | SERVO_ON_STATUS | Trạng thái servo ON. |
| D134 | TEST_DONE | 1 = test hoàn tất. |
| D135 | SAMPLE_INDEX | Chỉ số mẫu nếu PLC sử dụng. |

## 13.5 Bit trong D120 STATUS_WORD

| Bit | Tên | Ý nghĩa |
| --- | --- | --- |
| b0 | RUN_STATUS | Hệ thống đang RUN. |
| b1 | SERVO_ON_STATUS | Servo đang ON. |
| b2 | CYLINDER_CLAMPED | Xi lanh đang kẹp. |
| b3 | TEST_RUNNING | Chu trình test đang chạy. |
| b4 | RECORDING | Đang ghi/cho phép ghi. |
| b5 | DATA_VALID | Dữ liệu hiện tại hợp lệ. |
| b6 | DONE | Hoàn tất chu trình. |
| b7 | FAULT | Có lỗi. |

# 14. Luồng vận hành PLC/Servo

## 14.1 RUN/STOP

PC hoặc nút vật lý có thể yêu cầu RUN/STOP. Khi RUN hợp lệ và không có lỗi, PLC cho phép servo ON và hệ thống sẵn sàng chạy chu trình.

## 14.2 Kẹp/nhả xi lanh

Xi lanh có thể được toggle bằng nút vật lý hoặc lệnh từ PC. Trạng thái xi lanh trả về phần mềm qua D132 và STATUS_WORD.

## 14.3 START_RECORD / STOP_RECORD

START_RECORD báo PLC bắt đầu chu trình đo và cho phép phần mềm ghi dữ liệu. STOP_RECORD dùng để kết thúc hoặc dừng quá trình ghi.

## 14.4 Manual Jog

Jog Plus/Jog Minus dùng để quay servo thủ công phục vụ căn chỉnh. Chỉ jog khi khu vực cơ khí an toàn và người vận hành quan sát trực tiếp.

## 14.5 DONE/FAULT

DONE cho biết test hoàn tất. FAULT cho biết PLC hoặc cơ cấu có lỗi cần xử lý trước khi chạy tiếp. Khi có lỗi, cần lưu Terminal Log và kiểm tra D129 ERROR_CODE.

# 15. Cảnh báo an toàn

- Không đặt tay hoặc vật lạ vào vùng chuyển động servo khi hệ thống RUN.
- Không jog servo nếu jig/sản phẩm chưa cố định.
- Luôn kiểm tra E-Stop/interlock trước khi chạy.
- Khi có tiếng động bất thường hoặc chuyển động sai, dừng hệ thống ngay.
- Không thay đổi thông số góc/tốc độ/cycle nếu chưa được phê duyệt.
- Chỉ người được đào tạo mới được vận hành chế độ PLC/servo.

# 16. Lỗi thường gặp và cách xử lý

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
| --- | --- | --- |
| Không kết nối TCP/IP | Sai IP/port, chưa cắm mạng, ZE-SG3 chưa bật. | Kiểm tra IP, cáp mạng, nguồn ZE-SG3, port 502. |
| Không kết nối PLC | Sai COM, sai baudrate/parity/slave, USB-RS485 lỗi. | Chọn lại COM, kiểm tra 115200/N/Slave 2, kiểm tra dây A/B. |
| Torque không thay đổi | Chưa kết nối sensor, sai cấu hình, cần tare. | Kiểm tra trạng thái sensor, cấu hình full scale/sensitivity, thực hiện tare. |
| Angle không thay đổi | PLC chưa chạy hoặc chưa trả D124. | Kiểm tra PLC RUN, servo, Modbus status. |
| Biểu đồ không chạy | Đang pause drawing hoặc chưa có dữ liệu. | Bấm tiếp tục vẽ, kiểm tra kết nối và dữ liệu realtime. |
| Kết quả trung bình không khớp | Chọn sai cycle hoặc range time/angle. | Kiểm tra đúng cycle, đúng start/end range và chế độ phân tích. |
| PLC báo fault | Lỗi cơ khí/servo/interlock hoặc logic PLC. | Dừng máy, lưu log, kiểm tra D129 và trạng thái an toàn. |

# 17. Bảo trì và sao lưu

- Sao lưu file CSV/report sau mỗi ca hoặc mỗi lot quan trọng.
- Lưu Terminal Log khi xảy ra lỗi.
- Không tự ý sửa file cấu hình nếu không hiểu ý nghĩa thông số.
- Kiểm tra định kỳ cáp RS485, cáp mạng, nguồn ZE-SG3 và PLC.
- Định kỳ kiểm tra calibration/tare theo quy trình chất lượng của nhà máy.

# 18. Checklist bàn giao

| STT | Hạng mục | Kết quả |
| --- | --- | --- |
| 1 | Mở phần mềm thành công | ☐ OK  ☐ NG |
| 2 | Kết nối ZE-SG3 TCP/IP thành công | ☐ OK  ☐ NG |
| 3 | Kết nối PLC Modbus RTU thành công | ☐ OK  ☐ NG |
| 4 | Đọc torque realtime thành công | ☐ OK  ☐ NG |
| 5 | Đọc góc PLC realtime thành công | ☐ OK  ☐ NG |
| 6 | Hiển thị Torque-Time đúng | ☐ OK  ☐ NG |
| 7 | Hiển thị Torque-Angle đúng | ☐ OK  ☐ NG |
| 8 | Bắt đầu/dừng ghi dữ liệu thành công | ☐ OK  ☐ NG |
| 9 | Import sang Plot Viewer thành công | ☐ OK  ☐ NG |
| 10 | Xuất CSV/report thành công | ☐ OK  ☐ NG |
| 11 | Copy/Save/Clear Terminal Log bằng chuột phải thành công | ☐ OK  ☐ NG |
| 12 | Người vận hành đã được hướng dẫn quy trình an toàn | ☐ OK  ☐ NG |

# 19. Kết luận

Tài liệu này là tài liệu bàn giao sử dụng và vận hành hệ thống ZE-SG3 Torque Acquisition cho CTR VINA. Trong quá trình sử dụng, nếu phát sinh lỗi hoặc kết quả đo bất thường, người vận hành cần lưu dữ liệu CSV, lưu Terminal Log và ghi nhận điều kiện vận hành để bộ phận kỹ thuật kiểm tra.
