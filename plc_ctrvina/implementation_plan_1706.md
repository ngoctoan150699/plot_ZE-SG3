# Checklist cải tiến phần mềm 06/17

Nguồn yêu cầu: phản hồi ngày 17/06 và file tham khảo
[Worksheet in Software%20development%20-%20R2.xlsx](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/docs/Worksheet%20in%20Software%2520development%2520-%2520R2.xlsx).

File Excel tham khảo có sheet `Sheet1`, header gồm:

| Cột | Tên cột |
|---:|---|
| 1 | Date |
| 2 | Line No |
| 3 | Part Name |
| 4 | Part No |
| 5 | Test Item |
| 6 | Test Purpose |
| 7 | Testing Team |
| 8 | Specification Min (Nm) |
| 9 | Specification Max (Nm) |
| 10 | Actual value (Nm) |
| 11 | Judgment |
| 12 | Remark |

## 1. PLC / chương trình đo

- [ ] Kiểm tra trực tiếp tại máy phần **Breakaway Torque**.
  - [ ] Xác nhận hướng quay thực tế đúng với logic PLC.
  - [ ] Xác nhận chu trình Breakaway mong muốn: `0 -> + -> 0`.
  - [ ] Xác nhận Breakaway có lặp theo cycle cài đặt.
  - [ ] Ghi lại video hoặc log test nếu còn sai.

- [ ] Sửa hướng chạy đầu tiên của **Operating/Oscillating Torque**.
  - [ ] Hiện tại khi bắt đầu ghi, máy chạy qua trái trước.
  - [ ] Kết quả vòng đầu ra giá trị âm trước.
  - [ ] Yêu cầu: đổi để máy chạy qua phải trước.
  - [ ] Vòng đầu tiên phải cho giá trị dương trước.
  - [ ] Kiểm tra lại chiều `Y004` và quy ước dấu góc/momen.

## 2. Tab phân tích dữ liệu

### 2.1. Đồng bộ giao diện

- [ ] Thêm đổi ngôn ngữ Việt/Anh trong tab phân tích dữ liệu.
  - [ ] Dùng chung hệ thống i18n hiện có trong [i18n.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/i18n.py).
  - [ ] Không hardcode text mới nếu tránh được.

- [ ] Thêm đổi giao diện sáng/tối cho tab phân tích dữ liệu.
  - [ ] Đồng bộ style với tab thu thập dữ liệu.
  - [ ] Kiểm tra tất cả label, button, table, chart sau khi đổi theme.

### 2.2. Import CSV

- [ ] Sửa lỗi không import được CSV trong tab phân tích dữ liệu.
  - [ ] Hiện có 2 nút import CSV nhưng cả 2 không hoạt động.
  - [ ] Giữ lại 1 nút import CSV duy nhất.
  - [ ] Xóa hoặc ẩn nút import dư.
  - [ ] Sửa luồng chọn file CSV.
  - [ ] Parse được file CSV export từ phần mềm.
  - [ ] Hiển thị dữ liệu lên chart/table phân tích.
  - [ ] Báo lỗi rõ nếu CSV sai format.

### 2.3. Lưu spec

- [ ] Sửa lỗi ô nhập cài spec không lưu được.
  - [ ] Xác định field spec min/max đang lưu ở đâu.
  - [ ] Lưu spec vào settings hoặc cấu hình phù hợp.
  - [ ] Load lại spec khi mở phần mềm.
  - [ ] Không mất spec sau khi đổi tab hoặc đóng/mở app.

## 3. Report xuất tự động

- [ ] Kiểm tra report hiện tại đang tạo ra dữ liệu thô.
  - [ ] Mở file report hiện tại để xác nhận format sai.
  - [ ] Xác định service/module tạo report.
  - [ ] Sửa để report theo đúng form người dùng gửi.

- [ ] Tạo report theo form Excel tham khảo.
  - [ ] Header đúng thứ tự:
    - `Date`
    - `Line No`
    - `Part Name`
    - `Part No`
    - `Test Item`
    - `Test Purpose`
    - `Testing Team`
    - `Specification Min (Nm)`
    - `Specification Max (Nm)`
    - `Actual value (Nm)`
    - `Judgment`
    - `Remark`
  - [ ] Dữ liệu không còn là raw data nếu người dùng bấm lưu report.
  - [ ] File Excel có định dạng table.
  - [ ] Format cột ngày, số, text rõ ràng.

## 4. Bổ sung field nhập liệu

### 4.1. Sample No

- [ ] Thêm ô `Sample No` cạnh ô `Part No`.
  - [ ] Chỉ cho nhập số nguyên.
  - [ ] Giá trị hợp lệ: `1..99`.
  - [ ] Khi lưu/đặt tên file, format thành 2 chữ số:
    - `1 -> 01`
    - `9 -> 09`
    - `10 -> 10`
    - `99 -> 99`
  - [ ] Báo lỗi nếu để trống hoặc ngoài range.

### 4.2. Remark

- [ ] Thêm ô `Remark`.
  - [ ] Cho nhập text.
  - [ ] Tự động chuyển IN HOA.
  - [ ] Giới hạn 100 ký tự.
  - [ ] Không lưu lại cho lần sau.
  - [ ] Tự động xóa khi chuyển qua tab thu thập dữ liệu.
  - [ ] Đưa giá trị Remark vào summary report Excel.

## 5. Đổi quy tắc đặt tên file lưu tự động

### 5.1. Quy tắc hiện tại

```text
yymmdd-Test item-Part No-Purpose-Team-số thứ tự
```

### 5.2. Quy tắc mới

```text
yymmdd-Test item-Part No-Purpose-Team-Sample No-số thứ tự
```

Ví dụ:

```text
260525-B-CBJ0001-S-QM-01-01
```

### 5.3. Mapping dữ liệu

- [ ] `yymmdd`
  - [ ] Lấy theo ngày giờ trên máy tính.
  - [ ] Format `yyMMdd`.

- [ ] `Test item`
  - [ ] Chỉ dùng ký hiệu `B` hoặc `O`.
  - [ ] Lấy từ chương trình đo đang chọn.
  - [ ] `Breakaway Torque -> B`.
  - [ ] `Operating/Oscillating Torque -> O`.

- [ ] `Part No`
  - [ ] Lấy từ ô Part No trong phần xuất dữ liệu.
  - [ ] Chỉ lấy 7 ký tự đầu.
  - [ ] Nên chuyển in hoa và bỏ khoảng trắng đầu/cuối.

- [ ] `Purpose`
  - [ ] Lấy chữ cái đầu tiên của giá trị được chọn ở ô Purpose.
  - [ ] Nên chuyển in hoa.
  - [ ] Ví dụ `Setting -> S`.

- [ ] `Team`
  - [ ] Lấy từ ô Team hiện có.
  - [ ] Ví dụ `QM`.

- [ ] `Sample No`
  - [ ] Lấy từ ô `Sample No` mới.
  - [ ] Format `01..99`.

- [ ] `số thứ tự`
  - [ ] Tự động tạo từ `01` trở đi.
  - [ ] Chỉ tăng nếu trùng toàn bộ thông tin phía trước.
  - [ ] Ví dụ nếu đã có `260525-B-CBJ0001-S-QM-01-01` thì file kế tiếp là `260525-B-CBJ0001-S-QM-01-02`.

## 6. Cách tính kết quả cuối cùng

### 6.1. Operating / Oscillating Torque

- [ ] Không tính trung bình riêng vòng đo thứ 3 như hiện tại.
- [ ] Thêm/cập nhật phần cài đặt `range` theo góc độ.
  - [ ] Người dùng nhập góc bắt đầu.
  - [ ] Người dùng nhập góc kết thúc.
  - [ ] Ví dụ: `-28°` tới `+28°`.
- [ ] Kết quả cuối chỉ lấy dữ liệu nằm trong range góc đã cài.
- [ ] Tính `AVG` torque trong range.
- [ ] Không tính dữ liệu ngoài range.
- [ ] Phần hiển thị:
  - [ ] Chỉ hiển thị `AVG`.
  - [ ] `Min` để trống.
  - [ ] `Max` để trống.

### 6.2. Breakaway Torque

- [ ] Chỉ lấy giá trị `Maximum` trong khoảng góc cài đặt ở `range`.
- [ ] Không lấy dữ liệu ngoài range.
- [ ] Phần hiển thị:
  - [ ] Chỉ hiển thị `Max`.
  - [ ] `AVG` để trống.
  - [ ] `Min` để trống.

## 7. Summary report cho Power Automate / SharePoint List

- [ ] Tạo ô chọn đường dẫn lưu summary report.
  - [ ] Cho người dùng chọn folder hoặc file Excel summary.
  - [ ] Lưu setting đường dẫn để dùng lại lần sau nếu phù hợp.

- [ ] Khi nhấn lưu báo cáo, tự động tạo/cập nhật 1 file Excel summary.
  - [ ] Dùng form theo file tham khảo.
  - [ ] Có định dạng Excel Table.
  - [ ] Mỗi lần lưu report thêm 1 dòng summary mới.
  - [ ] Power Automate sẽ đọc file Excel này để đưa lên SharePoint List.

- [ ] Mapping cột summary:

| Cột Excel | Nguồn dữ liệu trong phần mềm |
|---|---|
| `Date` | Ngày giờ máy tính khi lưu báo cáo |
| `Line No` | Line hoặc station đang chọn/nhập |
| `Part Name` | Part name đang chọn/nhập |
| `Part No` | Part No đầy đủ hoặc theo yêu cầu report |
| `Test Item` | Breakaway Torque / Operating Torque |
| `Test Purpose` | Purpose đang chọn |
| `Testing Team` | Team đang chọn |
| `Specification Min (Nm)` | Spec min đang cài |
| `Specification Max (Nm)` | Spec max đang cài |
| `Actual value (Nm)` | Kết quả cuối sau khi tính theo rule mới |
| `Judgment` | OK/NG theo spec |
| `Remark` | Remark nhập mới, in hoa |

## 8. Kiểm thử bắt buộc

- [ ] Test import CSV.
  - [ ] Import file CSV cũ.
  - [ ] Import file CSV mới vừa export.
  - [ ] Chart/table hiển thị đúng.

- [ ] Test lưu spec.
  - [ ] Nhập spec.
  - [ ] Đổi tab.
  - [ ] Đóng/mở app.
  - [ ] Spec vẫn còn.

- [ ] Test Sample No.
  - [ ] Nhập `1`, tên file ra `01`.
  - [ ] Nhập `9`, tên file ra `09`.
  - [ ] Nhập `10`, tên file ra `10`.
  - [ ] Nhập `0`, `100`, text: phải báo lỗi.

- [ ] Test Remark.
  - [ ] Nhập chữ thường, tự thành in hoa.
  - [ ] Nhập quá 100 ký tự, bị giới hạn.
  - [ ] Chuyển qua tab thu thập, Remark tự xóa.

- [ ] Test đặt tên file.
  - [ ] Đúng format mới.
  - [ ] Tự tăng số thứ tự khi trùng prefix.

- [ ] Test tính kết quả.
  - [ ] Operating/Oscillating chỉ ra `AVG` trong range.
  - [ ] Breakaway chỉ ra `Max` trong range.
  - [ ] Các ô không dùng phải để trống.

- [ ] Test summary Excel.
  - [ ] File được tạo đúng đường dẫn.
  - [ ] Có table format.
  - [ ] Header đúng như file tham khảo.
  - [ ] Dữ liệu append đúng 1 dòng mỗi lần lưu report.

## 9. Ghi chú triển khai

- [ ] Ưu tiên sửa lỗi import CSV và lưu spec trước vì ảnh hưởng kiểm tra dữ liệu.
- [ ] Các text UI mới cần đưa vào [i18n.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/i18n.py).
- [ ] Không hardcode tiếng Việt/Anh trực tiếp trong UI nếu tránh được.
- [ ] Sau khi sửa Python, chạy kiểm tra biên dịch:

```powershell
.\.venv\Scripts\python.exe -m py_compile python\main.py
```

- [ ] Với module sửa cụ thể, py_compile thêm các file liên quan.
