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

---

## 9. Plan điều khiển PLC qua Modbus cho PC/HMI

Phần này là kế hoạch thao tác thực tế từ PC/HMI dựa trên vùng thanh ghi `D100..D135`.
Mục tiêu là PC chỉ cần ghi lệnh vào vùng `D100..D112`, PLC tự xử lý chu trình và trả trạng thái về `D120..D135`.

### 9.1. Nguyên tắc handshake lệnh

Các lệnh dạng nút nhấn không nên giữ mức `1` lâu. PC/HMI nên gửi theo dạng pulse:

```text
1. Ghi bit/lệnh = 1
2. Chờ 100..300 ms hoặc chờ PLC phản hồi trạng thái thay đổi
3. Ghi bit/lệnh = 0
```

Áp dụng cho:

| Lệnh | Thanh ghi/bit | Cách dùng |
|---|---|---|
| Start hệ thống | `D100.b0` | Pulse `1 -> 0` để bật `M0` |
| Stop hệ thống | `D100.b1` | Pulse `1 -> 0` để tắt `M0` |
| Start test | `D100.b2` | Pulse `1 -> 0` để set `M1`, `M2` |
| Stop test | `D100.b3` | Pulse `1 -> 0` để dừng đo |
| Toggle xi lanh | `D100.b4` | Mỗi pulse đảo trạng thái kẹp/nhả |
| Abort | `D100.b6` | Pulse hoặc giữ `1` khi cần dừng khẩn |
| Clear done | `D100.b7` | Pulse để xóa `D134/M3` sau khi PC nhận kết quả |
| Reset fault | `D109` | Ghi `1`, sau đó trả `0` |
| Jog plus | `D110` | Có thể giữ `1` khi đang jog |
| Jog minus | `D111` | Có thể giữ `1` khi đang jog |
| Home | `D112` | Pulse `1 -> 0` |

> [!IMPORTANT]
> Nếu PC ghi cả word `D100`, cần tránh ghi đè nhầm các bit khác. Tốt nhất là PC đọc `D100`, set/clear bit cần dùng, rồi ghi lại; hoặc dùng function Modbus ghi single bit nếu driver hỗ trợ mapping bit.

### 9.2. Trình tự bật máy / chuẩn bị chạy

```text
Step 1: PC kết nối Modbus RTU Slave ID = 2
Step 2: PC đọc D120..D135 để kiểm tra trạng thái hiện tại
Step 3: Nếu D120.b7 FAULT = 1 hoặc D129 != 0:
        - Ghi D109 = 1
        - Chờ D129 = 0 và D120.b7 = 0
        - Ghi D109 = 0
Step 4: Ghi D100.b0 = 1 rồi trả 0 để RUN hệ thống
Step 5: Chờ D120.b0 = 1 và D133 = 1
Step 6: Toggle/kẹp xi lanh nếu cần bằng D100.b4
Step 7: Chờ D132 = trạng thái mong muốn
```

Điều kiện cho phép bắt đầu test:

| Điều kiện | Thanh ghi đọc về | Giá trị yêu cầu |
|---|---|---|
| Hệ thống RUN | `D120.b0` | `1` |
| Servo ON | `D120.b1` hoặc `D133` | `1` |
| Không lỗi | `D120.b7`, `D129` | `0`, `0` |
| Xi lanh đã kẹp nếu cần | `D120.b2` hoặc `D132` | `1` |
| Không có test đang chạy | `D120.b3` | `0` |

### 9.3. Plan Manual Mode

Manual dùng để kiểm tra servo, xi lanh, hướng quay, tốc độ và giới hạn góc trước khi chạy đo tự động.

PC/HMI ghi cấu hình:

```text
D101 = 0              ; Manual mode
D104 = SPEED_X100     ; ví dụ 1000 = 10.00 deg/s nếu dùng đơn vị deg/s
```

Các thao tác manual:

| Thao tác | Lệnh PC | PLC nên thực hiện | Trạng thái trả về |
|---|---|---|---|
| Bật RUN | Pulse `D100.b0` | Set `M0` | `D120.b0=1` |
| Kẹp/nhả | Pulse `D100.b4` | Toggle `M10`, `Y006` | `D132=0/1` |
| Jog + | Giữ `D110=1` | Quay chiều dương, `Y004=1`, phát xung | `D122=110` |
| Jog - | Giữ `D111=1` | Quay chiều âm, `Y004=0`, phát xung | `D122=120` |
| Home/Zero | Pulse `D112` | Reset góc/xung hiện tại | `D124=0`, `D127/D128=0` |
| Stop | Pulse `D100.b1` | Tắt RUN/test | `D120.b0=0` |

Đề xuất phase manual:

| Phase `D122` | Ý nghĩa |
|---:|---|
| `0` | Idle |
| `100` | Manual ready |
| `110` | Jog plus |
| `120` | Jog minus |
| `130` | Homing/zeroing |

### 9.4. Plan Breakaway Torque

Breakaway là chu trình quay từ vị trí hiện tại đến góc dương `D102` để PC lấy giá trị momen phá vỡ ban đầu.

PC/HMI ghi cấu hình trước khi start:

```text
D101 = 1              ; Breakaway mode
D102 = POS_ANGLE_X100 ; ví dụ +3600 = +36.00°
D103 = NEG_ANGLE_X100 ; có thể không dùng trong Breakaway, vẫn ghi -3600 để đồng bộ
D104 = SPEED_X100     ; tốc độ mong muốn
D107 = PART_SELECT
D108 = 1              ; Breakaway Torque
```

Trình tự điều khiển:

```text
1. PC kiểm tra điều kiện ready ở mục 9.2
2. PC ghi cấu hình D101..D108
3. PC pulse D100.b2 START_RECORD
4. PLC set:
   - M1 = 1
   - M2 = 1
   - D121 = 1
   - D122 = 10/20
   - D123 = 1
   - D125 = D102
   - D130 = 1 trong vùng lấy dữ liệu
5. PC đọc liên tục:
   - D124 current angle
   - D125 target angle
   - D130 data valid
   - D131 record enable
   - D134 test done
   - D129 error code
6. Khi D131=1 và D130=1, PC lưu mẫu torque/góc/thời gian
7. Khi PLC đạt target:
   - M1 = 0
   - M2 = 0
   - M3 = 1
   - D134 = 1
   - D122 = 900
8. PC nhận done, dừng ghi dữ liệu, pulse D100.b7 CLEAR_DONE
```

Đề xuất phase Breakaway:

| Phase `D122` | Ý nghĩa | `D130 DATA_VALID` | `D131 RECORD_ENABLE` |
|---:|---|---:|---:|
| `10` | Prepare | `0` | `0` |
| `20` | Moving to positive angle | `1` | `1` |
| `30` | Hold/settle ngắn nếu cần | `0/1` | `1` |
| `900` | Done | `0` | `0` |
| `999` | Fault/Abort | `0` | `0` |

### 9.5. Plan Operating Torque

Operating là chu trình quay qua lại giữa góc dương `D102` và góc âm `D103` trong `D105` cycle. PC lấy dữ liệu trong vùng phần trăm `D106` để bỏ qua đoạn đầu/cuối nếu cần.

PC/HMI ghi cấu hình:

```text
D101 = 2              ; Operating mode
D102 = POS_ANGLE_X100 ; ví dụ +3600
D103 = NEG_ANGLE_X100 ; ví dụ -3600
D104 = SPEED_X100
D105 = CYCLE_SET      ; ví dụ 3
D106 = WINDOW_PERCENT ; ví dụ 80
D107 = PART_SELECT
D108 = 2              ; Operating Torque
```

Trình tự điều khiển:

```text
1. PC kiểm tra ready
2. PC ghi cấu hình D101..D108
3. PC pulse D100.b2 START_RECORD
4. PLC set cycle hiện tại D123 = 1
5. Với mỗi cycle:
   a. Đi đến D102, phase 210
   b. Đi đến D103, phase 220
   c. Tăng D123 sau khi hoàn tất một vòng + -> -
6. PLC bật D130=1 chỉ trong vùng lấy mẫu hợp lệ theo D106
7. PC chỉ lưu mẫu khi D131=1 và D130=1
8. Khi D123 > D105:
   - PLC set done D134=1
   - Reset M1/M2
   - D122=900
9. PC pulse D100.b7 để clear done
```

Đề xuất phase Operating:

| Phase `D122` | Ý nghĩa | Target `D125` | Ghi dữ liệu |
|---:|---|---|---|
| `200` | Operating prepare | Không đổi | Không |
| `210` | Move to positive angle | `D102` | Có, nếu trong window |
| `220` | Move to negative angle | `D103` | Có, nếu trong window |
| `230` | Cycle complete / tăng `D123` | Không đổi | Không |
| `900` | Done | Không đổi | Không |
| `999` | Fault/Abort | Không đổi | Không |

Cách tính vùng lấy mẫu theo `D106`:

```text
Stroke = ABS(D102 - D103)
WindowPercent = D106
ValidRange = Stroke * WindowPercent / 100
Margin = (Stroke - ValidRange) / 2

DATA_VALID = 1 khi góc hiện tại nằm trong:
NEG_ANGLE + Margin <= CURRENT_ANGLE <= POS_ANGLE - Margin
```

Ví dụ:

```text
D102 = +3600
D103 = -3600
Stroke = 7200
D106 = 80
ValidRange = 5760
Margin = 720
Vùng lấy mẫu = -2880 .. +2880 tương đương -28.80° .. +28.80°
```

### 9.6. Plan đóng gói `D120 STATUS_WORD`

Đề xuất PLC build `D120` mỗi scan từ các bit trạng thái, để PC chỉ cần đọc một word là biết tổng quan.

| Bit | Điều kiện PLC | Ý nghĩa PC |
|---:|---|---|
| `b0` | `M0` | System running |
| `b1` | `Y005` | Servo ON |
| `b2` | `M10` | Cylinder clamped |
| `b3` | `M1` | Test running |
| `b4` | `M2` | Recording enabled |
| `b5` | `D130 = 1` | Data valid |
| `b6` | `M3` hoặc `D134=1` | Done |
| `b7` | `M4` hoặc `D129 != 0` | Fault |

Logic đề xuất:

```text
D120 = 0
IF M0          THEN SET D120.b0
IF Y005        THEN SET D120.b1
IF M10         THEN SET D120.b2
IF M1          THEN SET D120.b3
IF M2          THEN SET D120.b4
IF D130 = 1    THEN SET D120.b5
IF M3          THEN SET D120.b6
IF M4/D129 !=0 THEN SET D120.b7
```

### 9.7. Plan mã lỗi `D129 ERROR_CODE`

Đề xuất chuẩn hóa mã lỗi để PC hiển thị rõ nguyên nhân:

| `D129` | Lỗi | Điều kiện gợi ý |
|---:|---|---|
| `0` | Không lỗi | Bình thường |
| `1` | Servo chưa ON | Start test khi `Y005=0` |
| `2` | Chưa RUN hệ thống | Start test khi `M0=0` |
| `3` | Mode không hợp lệ | `D101` không thuộc `0..2` |
| `4` | Tốc độ không hợp lệ | `D104 <= 0` |
| `5` | Góc dương không hợp lệ | `D102` vượt giới hạn |
| `6` | Góc âm không hợp lệ | `D103` vượt giới hạn |
| `7` | Cycle không hợp lệ | Operating mà `D105 <= 0` |
| `8` | Xi lanh chưa kẹp | Test yêu cầu kẹp nhưng `M10=0` |
| `9` | Abort từ PC | `D100.b6=1` |
| `10` | Stop vật lý | `X001=1` trong khi đang test |

Khi lỗi:

```text
SET M4
MOV error_code D129
RST M1
RST M2
MOV K999 D122
MOV K0 D130
```

Khi reset lỗi:

```text
Nếu D109 = 1 và điều kiện an toàn OK:
RST M4
MOV K0 D129
MOV K0 D122
MOV K0 D130
```

### 9.8. Bảng thao tác nhanh từ PC

| Mục tiêu | PC ghi | PC chờ đọc |
|---|---|---|
| RUN hệ thống | Pulse `D100.b0` | `D120.b0=1`, `D133=1` |
| STOP hệ thống | Pulse `D100.b1` | `D120.b0=0` |
| Kẹp/nhả | Pulse `D100.b4` | `D132` đổi trạng thái |
| Reset lỗi | Pulse/ghi `D109=1`, rồi `0` | `D129=0`, `D120.b7=0` |
| Start Breakaway | Ghi `D101=1`, `D102`, `D104`, pulse `D100.b2` | `D122=20`, `D131=1` |
| Start Operating | Ghi `D101=2`, `D102`, `D103`, `D104`, `D105`, `D106`, pulse `D100.b2` | `D122=210/220`, `D131=1` |
| Stop test | Pulse `D100.b3` | `D120.b3=0`, `D131=0` |
| Abort test | Pulse/giữ `D100.b6` | `D122=999` hoặc `D120.b3=0` |
| Nhận done | Đọc `D134=1`, sau đó pulse `D100.b7` | `D134=0`, `D120.b6=0` |

### 9.9. Checklist implement tiếp trong PLC

Các việc nên bổ sung vào [MAIN.csv](file:///d:/gxword2/duan_ctrvina/MAIN.csv):

1. Build đầy đủ `D120 STATUS_WORD` từ `M0`, `Y005`, `M10`, `M1`, `M2`, `D130`, `M3`, `M4`.
2. Thêm validate tham số trước khi start test:
   - `D101` mode
   - `D104` speed
   - `D102/D103` angle limit
   - `D105` cycle cho Operating
3. Thêm `D129 ERROR_CODE` và logic reset bằng `D109`.
4. Tách rõ state machine:
   - Manual: `100/110/120/130`
   - Breakaway: `10/20/30/900/999`
   - Operating: `200/210/220/230/900/999`
5. Dùng `D103` cho góc âm trong Operating.
6. Dùng `D105` để đếm số cycle qua `D123`.
7. Dùng `D106` để bật/tắt `D130 DATA_VALID` theo vùng lấy mẫu.
8. Cập nhật `D127/D128` nếu PLC có bộ đếm xung/vị trí thực tế.
9. Đảm bảo `D131 RECORD_ENABLE` chỉ bật khi chu trình đo thật sự đang chạy.
10. Khi done hoặc abort, reset `M1`, `M2`, `D130`, giữ `D134` cho tới khi PC clear.

### 9.10. Checklist test Modbus sau khi implement

| Test | Thao tác | Kết quả đúng |
|---|---|---|
| Kết nối | Đọc `D120..D135` | Có response từ Slave ID 2 |
| RUN | Pulse `D100.b0` | `D120.b0=1`, `Y005=ON` |
| STOP | Pulse `D100.b1` | `D120.b0=0`, `Y005=OFF` |
| Xi lanh | Pulse `D100.b4` 2 lần | `D132` đảo `0 -> 1 -> 0` |
| Breakaway | Set `D101=1`, `D102=3600`, `D104>0`, start | `D122=20`, `D125=3600`, `D134=1` khi xong |
| Operating | Set `D101=2`, `D102=3600`, `D103=-3600`, `D105=3`, start | `D123` đếm tới 3, phase đổi `210/220`, done khi xong |
| Data valid | Operating với `D106=80` | `D130=1` trong vùng giữa hành trình |
| Fault speed | Start với `D104=0` | `D129=4`, `D120.b7=1`, `D122=999` |
| Reset fault | Ghi `D109=1 -> 0` | `D129=0`, `D120.b7=0` |
| Clear done | Sau done pulse `D100.b7` | `D134=0`, `D120.b6=0` |
