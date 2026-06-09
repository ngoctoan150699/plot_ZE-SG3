# Chuyển Modbus sang 1 master/1 worker tuần tự

## Mục tiêu

Triển khai đúng mô hình:

```text
PC Python = Modbus master duy nhất
Slave 1 = Torque AMP ZE-SG3
Slave 2 = PLC/servo
Cùng một bus RS485 A/B
```

Không để nhiều thread cùng gọi Modbus trực tiếp. Mọi đọc/ghi đi qua một
worker duy nhất để tránh nghẽn, timeout chồng chéo, và lỗi điều khiển chậm.

## User Review Required

> [!IMPORTANT]
> Đây là thay đổi kiến trúc Modbus lớn. Sau khi sửa, `MainWindow`,
> `DataCollectorService`, và `PlcControlService` sẽ không còn tự polling
> song song nữa. Một worker mới sẽ điều phối tất cả request trên cùng COM.

## Proposed Changes

### Modbus worker tuần tự

#### [NEW] `modbus_master_worker.py`

Tạo service/worker mới, ví dụ:

[file target](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/application/modbus_master_worker.py)

Nhiệm vụ:

- Giữ một `IModbusClient` duy nhất.
- Giữ một `RLock` duy nhất cho toàn bộ bus.
- Có vòng polling riêng.
- Có cờ `recording`.
- Có request ưu tiên cho nút lệnh.

Luồng khi đang record:

```text
loop:
  read ID1 address 63 count 2       # torque
  delay 5~10ms
  read ID2 address 123 count 2      # cycle + angle
  delay 5~10ms
```

Luồng khi idle:

```text
mỗi 1s:
  read ID2 address 120 count 16     # full PLC status
  read ID1 status/tare/max/min nếu cần
```

Nút ưu tiên:

```text
pause polling
write ID2 D100 = mask
sleep 100ms
write ID2 D100 = 0
resume polling
```

Không đọc/ghi Modbus song song.

---

### Composition root

#### [MODIFY] [main.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/main.py)

- Tạo `ModbusMasterWorker` ở composition root.
- Inject worker vào `MainWindow`.
- Giữ `DataCollectorService`, `PlcControlService` nếu cần cho API cũ,
  nhưng không cho chúng tự tạo polling thread riêng khi dùng worker.

---

### UI orchestration

#### [MODIFY] [main_window.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/ui/main_window.py)

Thay đổi chính:

- Sau connect:
  - set client cho worker
  - start worker
  - không start `_collector.start()`
  - không start `_start_plc_polling()` riêng
- Khi bắt đầu ghi:
  - `worker.set_recording(True)`
  - worker phát signal torque + cycle + angle về UI
- Khi dừng ghi:
  - gửi `STOP_RECORD` ưu tiên nếu cần
  - `worker.set_recording(False)`
- Các nút RUN/STOP/CLAMP/HOME/ABORT:
  - gọi worker command ưu tiên
  - không gọi Modbus trực tiếp từ UI thread/button thread

---

### Data collector

#### [MODIFY] [data_collector.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/application/data_collector.py)

- Giữ logic decode torque/status để tái sử dụng nếu cần.
- Không dùng polling thread riêng trong mode worker.
- Tránh tự đọc Modbus khi worker đang quản lý bus.

---

### PLC service

#### [MODIFY] [plc_control_service.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/application/plc_control_service.py)

- Giữ các hàm build command/config.
- Worker sẽ là nơi gọi thực tế `read_registers/write_register`.
- D100 dùng pulse trực tiếp hoặc read-modify-write tùy mode.

Đề xuất cho mô phỏng/test hiện tại:

```text
D100 = mask
sleep 100ms
D100 = 0
```

---

### Simulator test

#### [MODIFY] [torque_simulator.py](file:///d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/torque_simulator.py)

- Giữ mặc định simulator `COM12`, baud `115200`.
- Main app dùng `COM11`.
- Test `--auto-start`.

## Verification Plan

### Automated Tests

Chạy compile:

```powershell
& G:/python/python.exe -m py_compile `
  python/main.py `
  python/application/modbus_master_worker.py `
  python/application/data_collector.py `
  python/application/plc_control_service.py `
  python/ui/main_window.py `
  python/torque_simulator.py
```

### Manual Verification

Terminal 1:

```powershell
& G:/python/python.exe d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/torque_simulator.py --port COM12 --baud 115200 --auto-start
```

Terminal 2:

```powershell
& G:/python/python.exe d:/DuAn/18.Other/plot_draw/plot_ZE-SG3/python/main.py
```

Kiểm tra:

1. Connect COM11.
2. RUN phản hồi nhanh.
3. CLAMP phản hồi nhanh.
4. Start record đọc đúng:
   - ID1 `63 count 2`
   - ID2 `123 count 2`
5. Khi đang record, không đọc:
   - ID2 `120..135`
   - ID1 phụ/status/config
6. Stop record ưu tiên, không bị chờ polling.

## Open Questions

Không có câu hỏi bắt buộc. Đề xuất triển khai luôn theo đúng phương án anh vừa chốt:

```text
1 worker Modbus duy nhất
record: ID1 63 count2 -> ID2 123 count2
idle: phụ 1s/lần
command: D100 pulse ưu tiên
```
