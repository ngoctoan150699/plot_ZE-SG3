# Tổng hợp trạng thái cải tiến phần mềm lần 2

Tài liệu này liệt kê lại toàn bộ yêu cầu cải tiến lần 2 và trạng thái hiện tại:

- `[x]` Đã sửa / đã có thay đổi trong code.
- `[~]` Đã sửa bước đầu nhưng cần test thực tế trên máy hoặc GX Works2.
- `[ ]` Chưa làm.

> Lưu ý: các thay đổi gần đây trên PLC `MAIN.csv` hiện mới sửa trực tiếp file local,
> **chưa commit/push** theo yêu cầu của anh.

---

## 1. Menu Thu Thập - phần mềm Python

| STT | Yêu cầu | Trạng thái | Ghi chú |
|---:|---|:---:|---|
| 1 | Đồng bộ tiếng Việt trong menu Thu Thập | [x] | Đã dịch nhiều label còn lẫn tiếng Anh sang tiếng Việt. |
| 2 | Xóa nút Clamp / biểu tượng Clamp | [x] | Đã bỏ nút Clamp khỏi giao diện chính. |
| 3 | Gộp RUN/STOP thành 1 nút đổi trạng thái | [x] | Chưa chạy: `▶ CHẠY` màu xanh. Đang chạy: `Ⅱ DỪNG` màu đỏ. |
| 4 | Lưu cài đặt chương trình đo | [x] | Đã bổ sung tự lưu một phần cấu hình đo vào settings. Cần test lại toàn bộ field. |
| 5 | Lưu thiết lập servo | [x] | Đã bổ sung lưu trạng thái/cấu hình servo. Cần test đóng/mở app. |
| 6 | Sampling settings vẫn lưu khi không tick cố định thang Y | [x] | Đã sửa lỗi không lưu khi bỏ tick fixed Y. |
| 7 | Thêm giới hạn cảm biến để quá lực thì dừng ngay | [ ] | Chưa làm UI nhập giới hạn Nm và logic monitor torque để STOP/ABORT. |
| 8 | Nút Home về vị trí góc 0 | [ ] | Chưa hoàn thiện phần mềm + PLC. |
| 9 | Thêm nút Set góc 0 | [ ] | Chưa làm. Cần lưu offset/gốc 0 vào settings. |

### File phần mềm đã/sẽ liên quan

- [main_window.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/main_window.py)
- [i18n.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/i18n.py)
- [app_settings.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/infrastructure/app_settings.py)
- [plc_control_service.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/application/plc_control_service.py)

---

## 2. Chương trình đo / PLC `MAIN.csv`

| STT | Yêu cầu | Trạng thái | Ghi chú |
|---:|---|:---:|---|
| 1 | Nút khẩn cấp có tác dụng, nhấn thì máy dừng ngay | [~] | Đã thêm `X004` EMG vào logic cắt RUN, Servo ON và dừng đo. Cần test thực tế trên PLC. |
| 2 | Chương trình đo phá vỡ chạy 1 bên rồi quay về ban đầu | [ ] | Chưa hoàn thiện state machine Breakaway theo đúng yêu cầu. |
| 3 | Chương trình đo quay phải trước để torque ban đầu dương | [~] | Đã đảo logic chân hướng `Y004`: `D160 > 0` thì `RST Y004`, `D160 < 0` thì `SET Y004`. Cần test thực tế chiều servo. |
| 4 | Chu kỳ Operating theo thứ tự `0 → âm → 0 → dương → 0` | [~] | Đã sửa target trong `MAIN.csv`: step 1 chạy âm, step 3 chạy dương. Cần import GX Works2 và test máy. |
| 5 | Home: góc âm quay dương về 0, góc dương quay âm về 0 | [ ] | Chưa hoàn thiện logic Home tự động trong PLC. |
| 6 | Bảo vệ giới hạn góc/hành trình trong PLC | [ ] | Chưa làm. Nên bổ sung để an toàn hơn phần mềm. |

### Các thay đổi PLC local đang có

#### Operating target flow

File: [MAIN.csv](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/plc_ctrvina/MAIN.csv#L175-L192)

Đã đổi comment và target flow:

```text
Trước: 0 -> + -> 0 -> - -> 0
Sau:   0 -> - -> 0 -> + -> 0
```

Logic hiện tại:

```text
D130 = K1  ->  D125 = -D103  ->  0 -> góc âm
D130 = K2  ->  D125 = 0      ->  góc âm -> 0
D130 = K3  ->  D125 = D102   ->  0 -> góc dương
D130 = K4  ->  D125 = 0      ->  góc dương -> 0
```

#### Đảo chiều chân hướng servo `Y004`

File: [MAIN.csv](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/plc_ctrvina/MAIN.csv)

Đã đổi:

```text
D160 > 0: SET Y004 -> RST Y004
D160 < 0: RST Y004 -> SET Y004
```

Ý nghĩa:

```text
Số xung D164 vẫn luôn dương.
Chiều quay do Y004 quyết định.
```

> Cần lưu ý: `DPLSV` dùng cho Jog manual vẫn tự điều khiển `Y004` theo dấu `D150`.
> Nếu Jog+ / Jog- bị ngược sau khi test thì cần đảo dấu `D150` cho phần Jog.

### File PLC liên quan

- [MAIN.csv](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/plc_ctrvina/MAIN.csv)
- [COMMENT.csv](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/plc_ctrvina/COMMENT.csv)
- [PLC_LOGIC_DOCUMENT.md](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/plc_ctrvina/PLC_LOGIC_DOCUMENT.md)
- [PLC_MAIN_CODE_EXPLAIN.md](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/plc_ctrvina/PLC_MAIN_CODE_EXPLAIN.md)

---

## 3. Phân Tích dữ liệu

| STT | Yêu cầu | Trạng thái | Ghi chú |
|---:|---|:---:|---|
| 1 | Cài đặt Specs lưu được | [ ] | Chưa sửa triệt để. Cần kiểm tra trong Plot Viewer. |
| 2 | Import CSV có sẵn lên được | [x] | Anh đã xác nhận import CSV hiện OK. |
| 3 | File trong Report không được giống raw CSV | [~] | Đã đổi tên report dạng `*_report.csv`; cần kiểm tra lại nội dung có đúng là report xử lý chưa. |
| 4 | Khi lưu báo cáo, cập nhật data vào file chung | [ ] | Chưa làm. Đề xuất trước mắt append vào `master_results.csv`. |
| 5 | Nghiên cứu SharePoint List Microsoft | [ ] | Chưa code. Cần thông tin site/list/auth của Microsoft 365. |

### File liên quan

- [draw_plot.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/draw_plot/draw_plot.py)
- [report_service.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/application/report_service.py)

---

## 4. Tài liệu và comment PLC

| STT | Yêu cầu | Trạng thái | Ghi chú |
|---:|---|:---:|---|
| 1 | Viết `COMMENT.csv` mô tả thanh ghi PLC | [~] | Đã cập nhật format và bổ sung các thanh ghi như `D170`, `D180`; cần import lại GX Works2 để xác nhận. |
| 2 | Viết docs mô tả logic PLC tổng quan | [x] | Đã tạo `PLC_LOGIC_DOCUMENT.md`. |
| 3 | Viết docs giải thích code `MAIN.csv` theo block/dòng ladder | [x] | Đã tạo `PLC_MAIN_CODE_EXPLAIN.md`, đã sửa lại số dòng Manual/Jog theo GX Works2. |

---

## 5. Việc cần làm tiếp theo theo thứ tự ưu tiên

### Ưu tiên 1 - Test PLC/GX Works2

- [ ] Import lại [MAIN.csv](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/plc_ctrvina/MAIN.csv) vào GX Works2.
- [ ] Import lại [COMMENT.csv](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/plc_ctrvina/COMMENT.csv).
- [ ] Test `X004` EMG dừng máy.
- [ ] Test Operating flow mới: `0 → âm → 0 → dương → 0`.
- [ ] Test chiều `Y004` sau khi đảo.
- [ ] Test Jog+ / Jog- vì `DPLSV` có thể cần đảo dấu `D150`.

### Ưu tiên 2 - Hoàn thiện PLC motion

- [ ] Sửa Breakaway: chạy 1 bên rồi về 0.
- [ ] Hoàn thiện Home tự động theo góc hiện tại.
- [ ] Chuẩn hóa status/error nếu cần: `D120`, `D129`.

### Ưu tiên 3 - Hoàn thiện phần mềm

- [ ] Thêm giới hạn cảm biến Nm.
- [ ] Thêm Set góc 0.
- [ ] Rà soát toàn bộ tự lưu cài đặt.
- [ ] Sửa Specs không lưu.

### Ưu tiên 4 - Report/SharePoint

- [ ] Kiểm tra nội dung report có khác raw CSV chưa.
- [ ] Tạo file chung `master_results.csv` hoặc `master_results.xlsx`.
- [ ] Thiết kế SharePoint List và cách đăng nhập Microsoft Graph.
