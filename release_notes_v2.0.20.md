# ZE-SG3 Torque Acquisition v2.0.20

## Thay đổi chính / Key Updates

1. **Khôi phục và tối ưu hóa chỉnh tốc độ JOG Servo/PLC**:
   - Khôi phục ô nhập tốc độ JOG (`spin_plc_jog_speed`) trực tiếp trên khối điều khiển JOG của tab Thu thập.
   - Bổ sung cấu hình tốc độ JOG vào hộp thoại Cài đặt Servo (`ServoSetupDialog`) đồng bộ cho mọi chế độ đo.
   - Hỗ trợ thao tác xóa/nhập số tự do, tự động chuẩn hóa giá trị khi hoàn tất chỉnh sửa, lưu vào cấu hình servo profile và ghi xuống thanh ghi PLC D104.

2. **Thu gọn cấu hình đường dẫn lưu tệp trên tab Phân tích (Plot Viewer)**:
   - Dấu toàn bộ các trường nhập và nút chọn thư mục lưu (CSV, Báo cáo Excel, Báo cáo Tổng hợp, Profile mẫu) vào hộp thoại chuyên biệt thông qua nút `"📁 Cấu hình đường dẫn lưu..."`.
   - Giảm thiểu chiếm dụng không gian dọc, giúp giao diện hiển thị biểu đồ rộng rãi, trực quan và hạn chế thao tác bấm nhầm của người vận hành.

3. **Tái cấu trúc và chuẩn hóa giao diện thông tin mẫu đo (Plot Metadata Panel)**:
   - Phân tách rõ ràng bố cục thành 2 khu vực:
     - **Thông tin quy cách kiểm tra (Tự động)**: Chế độ đo, Tên/Mã sản phẩm, Ngày đo, Tiêu chuẩn bản vẽ Min/Max, Tiêu chuẩn nội bộ Min/Max, Phán định OK/NG.
     - **Thông tin mẫu đo (Nhập thủ công)**: Số thứ tự mẫu, Mã máy, Số lô, Chuyền, Người đo, Nhóm/Ca, Mục đích đo, Tỉ lệ/Số lượng, Ký duyệt Lập/Kiểm/Duyệt, Ghi chú.
   - Chuẩn hóa viết hoa chữ cái đầu (sentence case) cho toàn bộ tiêu đề nhãn (VI/EN).
   - Đồng bộ kích thước font chữ đồng đều (11px) trên cả giao diện sáng (Light) và tối (Dark).
   - Khắc phục triệt để hiện tượng nhảy lệch hàng / lệch cột của Tiêu chuẩn bản vẽ (Drawing Spec) và Tiêu chuẩn nội bộ (Internal Spec).

Asset đính kèm là file cài đặt `mysetupZE-SG3 Torque Acquisition v2.0.20.exe` được tạo bằng Inno Setup.
