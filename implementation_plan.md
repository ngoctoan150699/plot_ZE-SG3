# Kế hoạch xử lý các phản hồi người dùng v2.0.15

## 1. Mục tiêu
Giải quyết 4 vấn đề kỹ thuật được người dùng phản ánh:
1. **Khắc phục lỗi biểu đồ bên tab Plot Viewer bị tự xóa** khi chuyển qua tab Thu thập (Acquisition).
2. **Sửa lỗi không đồng bộ Test Item (chế độ đo)** giữa tab Thu thập và tab Plot Viewer (phiên bản mới nhất bị lệch chuỗi i18n Tiếng Việt - Tiếng Anh).
3. **Tự động xóa Remark khi đo xong Oscillating hoặc Operating** (chế độ Breakaway vẫn giữ nguyên Remark).
4. **Bỏ ràng buộc bắt buộc nhập Spec Max/Min của Tiêu chuẩn nội bộ** khi tải lên file Standard Excel (tiêu chuẩn nội bộ chỉ dùng tham khảo, mã hàng có hay không có đều được chấp nhận).

---

## 2. Phân tích nguyên nhân gốc rễ

```mermaid
graph TD
    A["Đổi chế độ đo ở tab Thu thập (Mô-men quay/dao động)"] -->|currentText VI| B["_sync_test_item_to_plot_viewer()"]
    B -->|Text VI không khớp EN| C["set_valid_test_items fallback về items[0] (Breakaway)"]
    C -->|target_mode ép sang Angle| D["Plot Viewer update_plot()"]
    D -->|Mẫu Breakaway không có góc| E["x_data rỗng -> ax.clear() -> Biểu đồ biến mất!"]

    F["Chuyển tab về Thu thập (index = 0)"] --> G["_on_main_tab_changed()"]
    G -->|Tự động gọi sớm| H["clear_remark() & clear_required_report_info()"]
    H --> I["Metadata bị xóa ngay khi vừa chuyển tab"]

    J["Upload Standard Excel"] --> K["StandardService._parse_workbook()"]
    K -->|float(cell) trên ô trống| L["StandardFileError: giá trị phải là số -> Bị chặn"]
    K -->|So sánh 0.0 <= avg <= 0.0| M["Plot Viewer phán định nhầm thành NG"]
```

---

## 3. Các thay đổi chi tiết theo từng bước

### Bước 1: Khắc phục đồng bộ Test Item & Bảo vệ biểu đồ không bị xóa
- **File cần chỉnh sửa:** [`python/ui/main_window.py`](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/main_window.py)
- **Nội dung thực hiện:**
  - Đồng bộ dựa trên **mã chuẩn (test code)** (`breakaway`, `operating`, `oscillating`) thay vì chuỗi hiển thị:
    - Tạo mapping chuẩn 2 chiều:
      - `breakaway` $\leftrightarrow$ `'Breakaway Torque'`
      - `operating` $\leftrightarrow$ `'Operating Torque'`
      - `oscillating` $\leftrightarrow$ `'Oscillating Torque'`
  - Trong `_sync_test_item_to_plot_viewer(self, text: str)`:
    - Lấy code hiện hành từ `self._current_test_item_code()`.
    - Chuyển thành tên tiếng Anh tương ứng của Plot Viewer trước khi gọi `set_valid_test_items` và `test_item_combo.setCurrentText(...)`.
  - Trong `_sync_test_item_to_acquisition(self, text: str)`:
    - Chuyển `text` tiếng Anh của Plot Viewer về `code` chuẩn.
    - Tìm index trong `combo_test_item` qua `findData(code)` và set `setCurrentIndex(idx)`.
  - Trong `_sync_plot_viewer_mode_for_test_item(self, text: str)`:
    - Kiểm tra mode dựa trên `self._current_test_item_code() == 'breakaway'` $\rightarrow$ `time`, ngược lại $\rightarrow$ `angle`. Tránh tình trạng chuỗi tiếng Việt bị gán nhầm sang `angle` làm mất trắng biểu đồ.

---

### Bước 2: Bảo toàn biểu đồ khi chuyển tab & Xóa Remark đúng lúc hoàn thành đo
- **File cần chỉnh sửa:** [`python/ui/main_window.py`](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/main_window.py)
- **Nội dung thực hiện:**
  - Trong `_on_main_tab_changed(self, index: int)`:
    - **Xóa bỏ** đoạn gọi `clear_remark()` và `clear_required_report_info()` khi `index == 0`. Đảm bảo khi người dùng chuyển qua lại giữa các tab, toàn bộ biểu đồ và thông tin trên Plot Viewer được **giữ nguyên 100%**.
    - Khi `index == 1` (Plot Viewer), gọi `self._plot_viewer.canvas.draw_idle()` để đảm bảo canvas Matplotlib luôn repaint hiển thị đầy đủ các đường cong.
  - Trong `_stop_recording(self)` (thời điểm kết thúc chu trình đo thực tế):
    - Kiểm tra `test_code = self._current_test_item_code()`:
      - Nếu `test_code in ('operating', 'oscillating')`: gọi `self._plot_viewer.clear_remark()` (nếu `_plot_viewer` đã khởi tạo).
      - Nếu `test_code == 'breakaway'`: **giữ nguyên Remark**, không xóa.

---

### Bước 3: Cho phép để trống Tiêu chuẩn nội bộ trong file Standard Excel
- **Files cần chỉnh sửa:**
  - [`python/domain/entities.py`](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/domain/entities.py)
  - [`python/application/standard_service.py`](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/application/standard_service.py)
  - [`draw_plot/draw_plot.py`](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/draw_plot/draw_plot.py)
- **Nội dung thực hiện:**
  1. Trong `StandardRecord` ([`entities.py`](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/domain/entities.py)):
     - Đổi kiểu `internal_operating_min: Optional[float] = None` và `internal_operating_max: Optional[float] = None`.
  2. Trong `StandardService._parse_workbook()` ([`standard_service.py`](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/application/standard_service.py)):
     - Chỉ bắt buộc có số cho `breakaway_max`, `operating_min`, `operating_max`.
     - Với `internal_operating_min` và `internal_operating_max`:
       - Cho phép giá trị rỗng/trống (`None` hoặc `""`).
       - Nếu ô trống $\rightarrow$ gán `None`.
       - Nếu có nhập số $\rightarrow$ ép kiểu float hữu hạn và kiểm tra `min <= max` (nếu cả 2 đều có giá trị).
  3. Trong `TorquePlotViewer` ([`draw_plot/draw_plot.py`](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/draw_plot/draw_plot.py)):
     - Trong `set_standard_record`:
       - Kiểm tra nếu `record.internal_operating_min is not None and record.internal_operating_max is not None`:
         - Đặt cờ `self._has_internal_spec = True`.
         - Gán giá trị vào `internal_spec_min_spin` và `internal_spec_max_spin`.
       - Nếu không có tiêu chuẩn nội bộ:
         - Đặt cờ `self._has_internal_spec = False`.
         - Gán 0.0 vào các ô spin box.
     - Trong `update_average`:
       - Nếu `_has_internal_spec` là `False`: gán kết quả phán định `self._set_judgment(self.internal_judgment_label, None)` $\rightarrow$ hiển thị gạch ngang `'—'`, **không đánh giá NG**.
       - Nếu `_has_internal_spec` là `True`: so sánh `min <= avg <= max` để ra `OK` / `NG`.
     - Trong các hàm xuất báo cáo Excel (Report XLSX và Summary XLSX):
       - Nếu `_has_internal_spec` là `False`: cột Judgment ghi `'—'`, các ô Min/Max ghi `'—'` hoặc để trống.

---

## 4. Kế hoạch xác minh & kiểm thử (Verification Plan)

### Automated / Script Verification
1. **Kiểm tra cú pháp:**
   ```powershell
   .\.venv\Scripts\python.exe -m py_compile python/ui/main_window.py python/application/standard_service.py python/domain/entities.py draw_plot/draw_plot.py
   ```
2. **Kiểm tra đồng bộ chế độ đo (Unit test script):**
   - Viết script test tự động đổi `combo_test_item` ở tab Thu thập sang `Mô-men quay` và `Mô-men dao động` $\rightarrow$ kiểm tra `_plot_viewer.test_item_combo` nhận đúng `Operating Torque` / `Oscillating Torque`.
   - Đổi `test_item_combo` bên Plot Viewer $\rightarrow$ kiểm tra `combo_test_item` bên Thu thập đổi đúng theo nhãn Tiếng Việt.
3. **Kiểm tra upload file Standard Excel:**
   - Tạo file test Excel với 2 mã hàng: 1 mã có đủ cả 2 tiêu chuẩn, 1 mã để trống hoàn toàn cột Spec nội bộ.
   - Gọi `standard_svc.load()` $\rightarrow$ xác nhận file được chấp nhận, parse thành công.
   - Kiểm tra `set_standard_record()` với mã hàng không có spec nội bộ $\rightarrow$ xác nhận phán định hiển thị `'—'`, không bị NG.

### Manual / Integration Verification
1. Nạp file CSV mẫu vào Plot Viewer $\rightarrow$ click sang tab Thu thập $\rightarrow$ click lại tab Plot Viewer $\rightarrow$ xác nhận biểu đồ vẫn hiển thị đầy đủ.
2. Thực hiện kết thúc đo Breakaway $\rightarrow$ xác nhận Remark được giữ lại.
3. Thực hiện kết thúc đo Operating $\rightarrow$ xác nhận Remark tự động xóa.
