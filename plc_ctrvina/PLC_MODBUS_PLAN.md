# Kế hoạch lập trình PLC đo momen qua RS485 Modbus

Dự án hiện tại có 2 file GX Works2:

- [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv)
- [COMMENT.csv](file:///d:/gxword2/duan_ctrvina/COMMENT.csv)

PLC đang dùng FXCPU FX3U/FX3UC, cấu hình Modbus RTU slave:

- `D8400 = H10D1`: 115200, 8 bit, No parity, 1 stop
- `D8401 = H11`: Modbus Slave RTU
- `D8411 = K5`: delay 5 ms
- `D8414 = K2`: Slave ID = 2
- `D8415 = H11`: cho phép lưu/truy cập device D qua Modbus
- `D8416 = K100`: vùng D bắt đầu từ `D100`

## User Review Required

> [!IMPORTANT]
> [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv) hiện đã có các khối cơ bản chạy được: tách bit lệnh PC từ `D100`, latch RUN/STOP nhận cả nút vật lý và PC, servo ON theo `M0`/`M4`, toggle xi lanh bằng hai nút hoặc PC, start/stop đo cơ bản, tính sai góc và phát xung `PLSY`.

> [!IMPORTANT]
> Logic xi lanh trong [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv) đã được đổi sang **toggle latch** đúng yêu cầu: `X002+X003` cạnh lên hoặc `D100.b4` sẽ `ALT M10`, sau đó `Y006 = M10`.

> [!WARNING]
> Phần Breakaway / Operating trong [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv) mới chỉ là logic nền đơn giản: set phase, set `D130`, copy `D102 -> D125`, tính sai góc và phát xung. Chưa có state machine đầy đủ, chưa dùng `D103`, `D105`, `D106`, chưa build đủ `D120 STATUS_WORD` và chưa có fault handling hoàn chỉnh như kế hoạch ban đầu.

## Open Questions

Các chân I/O chính đã được xác nhận:

| Device | Chức năng |
|---|---|
| `X000` | Start vật lý |
| `X001` | Stop vật lý |
| `X002` | Nút nhấn 1 |
| `X003` | Nút nhấn 2 |
| `Y000` | Chân xuất xung vào driver servo |
| `Y004` | Chân quyết định chiều servo |
| `Y005` | Servo ON |
| `Y006` | Xi lanh |

Còn cần xác nhận nếu có thêm tín hiệu bảo vệ:

1. Servo có tín hiệu báo ready/alarm/home không?
   - Nếu có nên thêm input `X004 Servo Ready`, `X005 Servo Alarm`, `X006 Home Sensor`.
2. Góc dương/âm nhập từ PC có giới hạn cơ khí bao nhiêu độ?
   - Ví dụ ảnh minh họa đang dùng `-36°` đến `+36°`.
3. Tốc độ nhập từ PC muốn dùng đơn vị nào?
   - Đề xuất dùng `deg/s`, PLC tự đổi sang `pulse/s`.
4. Giá trị momen/lực đo đến từ đâu?
   - Nếu PC đọc cảm biến trực tiếp thì PLC chỉ cần xuất trạng thái góc/phase.
   - Nếu PLC đọc analog/loadcell thì cần thêm thanh ghi giá trị lực hiện tại.

## Proposed Changes

### 1. Quy đổi góc servo sang xung

Thông số:

- Servo: `10000 pulse / vòng servo`
- Hộp số: `1/20`
- Nghĩa là trục thực tế quay 1 vòng cần servo quay 20 vòng.

Công thức:

```text
Pulse / vòng thực tế = 10000 * 20 = 200000 pulse
Pulse / độ thực tế = 200000 / 360 = 555.5556 pulse/degree
Số xung yêu cầu = Góc độ * 555.5556
```

Ví dụ:

| Góc thực tế | Số xung tương ứng |
|---:|---:|
| `+36°` | `+20000 pulse` |
| `-36°` | `-20000 pulse` |
| `+90°` | `+50000 pulse` |
| `+180°` | `+100000 pulse` |
| `+360°` | `+200000 pulse` |

Trong PLC nên dùng số nguyên:

```text
Pulse = Angle_x100 * 200000 / 36000
```

Trong đó `Angle_x100` là góc nhân 100. Ví dụ `36.00° = 3600`.

---

### 2. Bảng thanh ghi Modbus đề xuất

Vì chương trình hiện tại đặt vùng Modbus D bắt đầu từ `D100`, PC sẽ ghi/đọc các thanh ghi từ `D100` trở đi.

#### Thanh ghi PC ghi xuống PLC

| Thanh ghi | Tên | Kiểu | Ý nghĩa |
|---|---|---:|---|
| `D100` | `CMD_WORD` | INT | Word lệnh điều khiển chính |
| `D101` | `MODE` | INT | `0 = Manual`, `1 = Breakaway`, `2 = Operating` |
| `D102` | `POS_ANGLE_X100` | INT signed | Góc dương, ví dụ `3600 = +36.00°` |
| `D103` | `NEG_ANGLE_X100` | INT signed | Góc âm, ví dụ `-3600 = -36.00°` |
| `D104` | `SPEED_X100` | INT | Tốc độ, ví dụ `1000 = 10.00 deg/s` |
| `D105` | `CYCLE_SET` | INT | Số cycle operating, mặc định `3` |
| `D106` | `OPERATING_WINDOW_PERCENT` | INT | Vùng lấy dữ liệu operating, ví dụ `80` (%) |
| `D107` | `PART_SELECT` | INT | `1=ITR`, `2=B/Joint`, `3=OTR`, `4=S/Link` |
| `D108` | `TORQUE_TYPE` | INT | `1=Breakaway Torque`, `2=Operating Torque` |
| `D109` | `RESET_FAULT` | INT/bit | PC ghi `1` để reset lỗi |
| `D110` | `JOG_PLUS` | INT/bit | Manual jog chiều dương |
| `D111` | `JOG_MINUS` | INT/bit | Manual jog chiều âm |
| `D112` | `HOME_CMD` | INT/bit | Lệnh về home/zero |

#### Bit trong `D100 CMD_WORD`

| Bit | Tên | Ý nghĩa |
|---:|---|---|
| `b0` | `PC_START_RUN` | PC yêu cầu hệ thống chạy, tương đương Start |
| `b1` | `PC_STOP_RUN` | PC yêu cầu dừng, tương đương Stop |
| `b2` | `START_RECORD` | Bắt đầu ghi dữ liệu và chạy test |
| `b3` | `STOP_RECORD` | Dừng ghi/dừng test |
| `b4` | `CYLINDER_TOGGLE` | PC yêu cầu toggle kẹp/nhả xi lanh |
| `b5` | `SERVO_ON_CMD` | Cho phép bật servo ON |
| `b6` | `ABORT_CMD` | Dừng khẩn chu trình đang chạy |
| `b7` | `CLEAR_DONE` | Xóa cờ done sau khi PC đã nhận |

> [!TIP]
> Các bit dạng nút nhấn nên xử lý theo **cạnh lên** trong PLC. PC chỉ cần ghi `1` trong một chu kỳ truyền rồi trả về `0`, hoặc PLC tự tạo one-shot nội bộ.

#### Thanh ghi PLC trả về PC

| Thanh ghi | Tên | Kiểu | Ý nghĩa |
|---|---|---:|---|
| `D120` | `STATUS_WORD` | INT | Trạng thái tổng |
| `D121` | `CURRENT_MODE` | INT | Mode đang chạy |
| `D122` | `CURRENT_PHASE` | INT | Bước hiện tại của chu trình |
| `D123` | `CURRENT_CYCLE` | INT | Cycle hiện tại |
| `D124` | `CURRENT_ANGLE_X100` | INT signed | Góc hiện tại x100 |
| `D125` | `TARGET_ANGLE_X100` | INT signed | Góc đích hiện tại x100 |
| `D126` | `CURRENT_SPEED_X100` | INT | Tốc độ hiện tại x100 |
| `D127` | `SERVO_PULSE_LOW` | INT | Vị trí/xung hiện tại word thấp |
| `D128` | `SERVO_PULSE_HIGH` | INT | Vị trí/xung hiện tại word cao |
| `D129` | `ERROR_CODE` | INT | Mã lỗi PLC |
| `D130` | `DATA_VALID` | INT | `1 = đang trong vùng cần lấy dữ liệu` |
| `D131` | `RECORD_ENABLE` | INT | `1 = PC được phép ghi mẫu đo` |
| `D132` | `CYLINDER_STATUS` | INT | `0 = nhả`, `1 = kẹp` |
| `D133` | `SERVO_ON_STATUS` | INT | Trạng thái output servo ON |
| `D134` | `TEST_DONE` | INT | `1 = test hoàn tất` |
| `D135` | `SAMPLE_INDEX` | INT | Số mẫu/điểm hiện tại nếu PLC cần đếm |

#### Bit trong `D120 STATUS_WORD`

| Bit | Tên | Ý nghĩa |
|---:|---|---|
| `b0` | `RUN_STATUS` | `M0`, hệ thống đang run |
| `b1` | `SERVO_ON_STATUS` | Servo ON |
| `b2` | `CYLINDER_CLAMPED` | Xi lanh đang kẹp |
| `b3` | `TEST_RUNNING` | Chu trình test đang chạy |
| `b4` | `RECORDING` | Đang cho phép ghi dữ liệu |
| `b5` | `DATA_VALID` | Mẫu hiện tại hợp lệ để PC lấy |
| `b6` | `DONE` | Hoàn tất chu trình |
| `b7` | `FAULT` | Có lỗi |

---

### 3. Logic Start/Stop hệ thống

Hiện [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv) đang có đúng logic sau:

```text
LD X000
OR M100
OR M0
ANI X001
ANI M101
ANI M106
OUT M0
```

Ý nghĩa thực tế:

- `X000` hoặc `D100.b0 -> M100` sẽ cho phép giữ RUN.
- `X001` hoặc `D100.b1 -> M101` hoặc `D100.b6 -> M106` sẽ cắt RUN.
- `M0` hiện là latch run/stop chính của hệ thống.
- `Y005` đang được điều khiển bằng:

```text
LD M8000
AND M0
ANI M4
OUT Y005
```

=> Servo ON khi PLC RUN, hệ thống RUN và không có lỗi `M4`.

---

### 4. Logic kẹp/nhả xi lanh

Phần này trong [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv) đã implement như sau:

```text
LD X002
AND X003
OUT M11
LDP M11
ALT M10
LDP M104
ALT M10
LD M10
OUT Y006
```

Suy ra:

- `M11 = X002 AND X003`
- Cạnh lên `M11` sẽ toggle `M10`
- Cạnh lên `M104` (tách từ `D100.b4`) cũng toggle `M10`
- `Y006 = M10`
- Trạng thái trả về PC: `D132 = 1` khi `M10=1`, ngược lại `D132 = 0`

> [!TIP]
> Đây là phần đã khớp tốt với yêu cầu toggle clamp/unclamp.

---

### 5. Trạng thái phần đo đang có trong MAIN.csv

Hiện phần đo trong [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv) đang hoạt động theo mức cơ bản như sau:

#### Start đo

```text
LDP M102
SET M1
SET M2
RST M3
MOV D101 D121
MOV K10 D122
MOV K1 D123
```

- `M102` là cạnh lệnh `D100.b2 START_RECORD`
- `M1 = test running`
- `M2 = record enable`
- `M3` bị reset khi bắt đầu test
- `D121` nhận mode từ `D101`
- `D122` được set bước chuẩn bị `10`
- `D123` đang khởi tạo `1`

#### Stop đo

```text
LD M103
OR M106
OR X001
RST M1
RST M2
MOV K0 D122
```

- `M103` là `D100.b3 STOP_RECORD`
- `M106` là `D100.b6 ABORT_CMD`
- `X001` là stop vật lý
- Khi stop: reset chạy đo, tắt record, đưa phase về `0`

#### Mode Breakaway hiện có

```text
LD= D101 K1
AND M1
MOV K20 D122
MOV K1 D130
MOV D102 D125
```

- Nếu `D101 = 1` và `M1 = 1` thì phase đặt thành `20`
- `D130 = 1`
- `D125 = D102`

#### Mode Operating hiện có

```text
LD= D101 K2
AND M1
MOV K210 D122
MOV K1 D130
MOV D102 D125
```

- Nếu `D101 = 2` và `M1 = 1` thì phase đặt thành `210`
- `D130 = 1`
- `D125 = D102`

#### Tính góc lệch và phát xung

```text
LD M1
SUB D125 D124 D160
LD> D160 K0
OUT Y004
LD> D160 K0
MOV D160 D161
LD< D160 K0
NEG D160 D161
MUL D161 K200000 D162
DIV D162 K36000 D164
LD M1
AND Y005
PLSY D104 D164 Y000
LD M1
MOV D125 D124
```

Ý nghĩa:

- `D160 = D125 - D124` là sai góc
- `Y004 = 1` khi sai góc dương
- `D161 = ABS(D160)`
- `D164` là số xung cần phát
- `PLSY D104 D164 Y000` đang dùng trực tiếp `D104` làm tốc độ phát xung
- Sau khi phát xung, chương trình đang `MOV D125 -> D124`, tức cập nhật góc hiện tại bằng góc đích theo kiểu giả lập nội bộ

> [!WARNING]
> Chưa có chu trình Breakaway/Operating hoàn chỉnh theo kế hoạch ban đầu; hiện mới là nền điều khiển đơn giản để test giao tiếp, setpoint và phát xung.

---

### 7. Device nội bộ PLC đang dùng / đã thấy trong MAIN.csv

| Device | Ý nghĩa |
|---|---|
| `M0` | Run/Stop status |
| `M1` | Đang đo / test running |
| `M2` | Cho ghi dữ liệu |
| `M3` | Done |
| `M4` | Fault |
| `M10` | Latch xi lanh |
| `M11` | Điều kiện hai nút cùng ON |
| `M100..M107` | Các bit lệnh PC đã tách từ `D100.b0..b7` |

| D | Ý nghĩa |
|---|---|
| `D121` | Mode hiện tại |
| `D122` | Phase hiện tại |
| `D123` | Cycle hiện tại |
| `D124` | Góc hiện tại nội bộ |
| `D125` | Góc đích |
| `D130` | Data valid |
| `D132` | Trạng thái xi lanh |
| `D133` | Trạng thái servo ON |
| `D134` | Done |
| `D160` | Sai góc |
| `D161` | ABS sai góc |
| `D162` | Trung gian nhân xung |
| `D164` | Số xung cần phát |

### 8. File đã được cập nhật thực tế

#### [MODIFY] [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv)

Đã có sẵn trong file hiện tại:

1. Cấu hình Modbus `D8400..D8416`
2. Tách bit lệnh `D100.0..D100.7 -> M100..M107`
3. RUN/STOP nhận cả nút vật lý và PC
4. Servo ON theo `M8000`, `M0`, `!M4`
5. Xi lanh toggle bằng `M10`
6. Start/stop đo cơ bản
7. Chọn mode Breakaway / Operating cơ bản
8. Tính sai góc, tính xung và phát `PLSY`
9. Trả một phần trạng thái về `D132`, `D133`, `D134`, `D131`

#### [MODIFY] [COMMENT.csv](file:///d:/gxword2/duan_ctrvina/COMMENT.csv)

Comment hiện đang có cho phần lớn device chính như `M0..M107`, `D100..D165`, `Y004..Y006`, phù hợp để debug trạng thái hiện tại.

---

## Verification Plan

### Automated / Offline Checks

- Mở lại file CSV bằng GX Works2 để kiểm tra import không lỗi.
- Soát lại [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv) để chắc rằng tài liệu khớp rung hiện tại.
- Kiểm tra watch files import được để debug `M0`, `M1`, `M10`, `M100..M106`, `D121`, `D122`, `D125`, `D130`, `D160`, `D164`.

### PLC / Modbus Checks theo logic hiện tại

1. Ghi `D100.b0 = 1`: kiểm tra `M100 = ON`, `M0 = ON`.
2. Ghi `D100.b1 = 1`: kiểm tra `M101 = ON`, `M0 = OFF`.
3. Ghi `D100.b6 = 1`: kiểm tra `M106 = ON`, `M0 = OFF`.
4. Khi `M0 = ON` và `M4 = OFF`: `Y005 = ON`, `D133 = 1`.
5. Nhấn đồng thời `X002 + X003` hoặc ghi `D100.b4 = 1`: `M10` phải toggle và `D132` đổi `0/1`.
6. Ghi `D100.b2 = 1`: `M102` cạnh lên phải set `M1`, `M2`, reset `M3`, copy `D101 -> D121`, set `D122 = 10`.
7. Ghi `D100.b3 = 1` hoặc `D100.b6 = 1` hoặc nhấn `X001`: phải reset `M1`, `M2` và `D122 = 0`.
8. Khi `D101 = 1` và `M1 = 1`: kiểm tra `D122 = 20`, `D130 = 1`, `D125 = D102`.
9. Khi `D101 = 2` và `M1 = 1`: kiểm tra `D122 = 210`, `D130 = 1`, `D125 = D102`.
10. Kiểm tra tính toán: `D160 = D125 - D124`, `D161 = ABS(D160)`, `D164 = D161 * 200000 / 36000`.
11. Khi `M1 = 1` và `Y005 = 1`: PLC phát `PLSY D104 D164 Y000`.

### Gap cần nhớ

- `D120 STATUS_WORD` chưa được đóng gói bit đầy đủ.
- `D103`, `D105`, `D106`, `D127`, `D128`, `D129`, `D135` chưa được dùng đúng theo kế hoạch ban đầu.
- Chưa có state machine hoàn chỉnh cho Breakaway/Operating và chưa có fault recovery hoàn chỉnh.
