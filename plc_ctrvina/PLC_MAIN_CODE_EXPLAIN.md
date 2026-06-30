# GIẢI THÍCH CODE PLC MAIN.csv

Tài liệu này được đọc lại theo file `plc_ctrvina/MAIN.csv` mới nhất. Nội dung giải thích theo từng cụm logic chính, kèm ý nghĩa các thanh ghi/bit quan trọng để kỹ thuật dễ kiểm tra và bàn giao.

---

## 1. Thông tin tổng quan chương trình

```text
PLC: FXCPU FX3U/FX3UC
File nguồn: plc_ctrvina/MAIN.csv
Chức năng chính: nhận lệnh từ PC qua Modbus, điều khiển RUN/STOP, servo, xi lanh, chu trình quay góc và trả trạng thái về PC.
```

### Các vùng tín hiệu chính

- **D100**: word lệnh PC ghi xuống PLC. Cuối mỗi scan PLC reset D100 về 0 để tạo lệnh dạng nhấn-nhả.
- **D101**: chế độ chạy. `K0` = Manual, các mode khác dùng cho chu trình đo.
- **D102**: góc thuận/target dương.
- **D103**: góc nghịch/target âm, trong code được đưa qua `NEG` để tạo giá trị âm.
- **D104**: tốc độ phát xung servo.
- **D105**: số chu kỳ cần chạy. Nếu PC gửi `D105 <= 0`, PLC tự gán mặc định `K3`.
- **D120..D134**: vùng PLC trả trạng thái về PC.
- **D130**: step hiện tại của chu trình góc: `1 -> 2 -> 3 -> 4` tương ứng `+góc -> 0 -> -góc -> 0`.
- **D180**: bộ đếm cycle hiện tại.

---

## 2. Khởi tạo truyền thông Modbus RTU Slave

```text
Dòng 0 - 27: cấu hình truyền thông Modbus RTU Slave cho PLC.
```

### Giải thích từng lệnh chính

- **LD M8411**: điều kiện kích hoạt khối cấu hình truyền thông. `M8411` liên quan cờ/kích hoạt truyền thông của FX3U.
- **MOV H10D1 D8400**: cấu hình thông số truyền thông cho cổng PLC, tương ứng baudrate/parity/stop bit theo cấu hình đang dùng.
- **MOV H11 D8401**: chọn chế độ/giao thức truyền thông Modbus RTU Slave.
- **MOV K5 D8411**: đặt thời gian delay phản hồi là 5 ms.
- **MOV K2 D8414**: đặt Slave ID PLC là 2.
- **MOV H11 D8415**: cho phép vùng thiết bị D tham gia giao tiếp Modbus.
- **MOV K200 D8416**: đặt vùng mapping Modbus bắt đầu theo cấu hình hiện tại là K200.

> Lưu ý: file MAIN mới nhất đang dùng `K200` tại `D8416`, khác với bản mô tả cũ từng ghi `K100`.

---

## 3. Tách lệnh PC từ D100 và các thanh ghi Manual

```text
Dòng 32 - 96: đọc D100.0..D100.7 và D110..D112 thành các bit trung gian M100..M112.
```

### D100 command word

- **D100.0 -> M100**: lệnh Start/RUN từ PC.
- **D100.1 -> M101**: lệnh Stop từ PC.
- **D100.2 -> M102**: lệnh bắt đầu đo/Start Record.
- **D100.3 -> M103**: lệnh dừng đo/Stop Record.
- **D100.4 -> M104**: lệnh toggle kẹp/nhả xi lanh.
- **D100.5 -> M105**: lệnh servo ON từ PC, hiện chương trình chủ yếu ON servo theo điều kiện RUN/an toàn.
- **D100.6 -> M106**: lệnh Abort/dừng khẩn chu trình từ PC.
- **D100.7 -> M107**: lệnh Clear Done.

### D110, D111, D112 cho Manual

- **LD= D110 K1 -> M110**: Jog Plus khi PC ghi D110 = 1.
- **LD= D111 K1 -> M111**: Jog Minus khi PC ghi D111 = 1.
- **LD= D112 K1 -> M112**: Home/Zero khi PC ghi D112 = 1.

### Mặc định cycle

```text
Dòng 97 - 103: nếu D105 <= 0 thì MOV K3 D105.
```

- Nếu PC chưa gửi số cycle hoặc gửi 0/số âm, PLC tự đặt **3 cycle** để tránh chu trình không có số lần chạy.

---

## 4. Trả trạng thái về PC

```text
Dòng 108 - 157: ghi các trạng thái quan trọng vào D120..D134.
```

### Các trạng thái trả về

- **MOV K0 D120**: hiện tại D120 được reset về 0 trong mỗi scan, chưa đóng gói bit status tổng.
- **M10 -> D132**: trạng thái xi lanh. `M10 ON` thì `D132 = 1`, `M10 OFF` thì `D132 = 0`.
- **Y005 -> D133**: trạng thái Servo ON. `Y005 ON` thì `D133 = 1`, ngược lại `0`.
- **M3 -> D134**: trạng thái Done. `M3 ON` thì `D134 = 1`, ngược lại `0`.
- **M2 -> D131**: trạng thái cho phép ghi dữ liệu. `M2 ON` thì `D131 = 1`, ngược lại `0`.

---

## 5. Đèn báo trạng thái

```text
Dòng 162 - 169: xuất đèn báo RUN/STOP/FAULT.
```

- **M0 và không lỗi M4 -> Y007**: báo trạng thái máy đang RUN/OK.
- **Không M0 và không lỗi M4 -> Y010**: báo trạng thái dừng/standby.
- **M4 -> Y011**: báo lỗi.

> Trong file mới, `Y007` vừa dùng làm đèn RUN/OK vừa được dùng ở cụm xi lanh khi `M10 OFF`. Cần kiểm tra wiring thực tế để xác nhận `Y007` là đèn hay ngõ nhả xi lanh.

---

## 6. Logic RUN / STOP hệ thống chính

```text
Dòng 170 - 177: giữ trạng thái RUN tại M0.
```

### Điều kiện bật RUN

- **X000**: nút Start vật lý.
- **M100**: lệnh Start từ PC.
- **M0**: tiếp điểm tự duy trì.

### Điều kiện tắt RUN

- **X001**: nút Stop vật lý.
- **X004**: Emergency/EMG.
- **M101**: lệnh Stop từ PC.
- **M106**: lệnh Abort từ PC.

### Ý nghĩa

`M0` là bit RUN tổng. Khi `M0 = ON`, máy được phép bật servo và xử lý các chế độ. Khi có Stop/Abort/EMG, `M0` tắt ngay.

---

## 7. Bật Servo ON

```text
Dòng 178 - 182: điều khiển Y005 Servo ON.
```

Servo ON khi đồng thời có các điều kiện:

- PLC đang scan (`M8000`).
- Máy đang RUN (`M0 = ON`).
- Không có lỗi (`M4 = OFF`).
- Không bị EMG (`X004 = OFF`).

Khi đủ điều kiện, PLC xuất **Y005** để bật servo.

---

## 8. Kẹp / nhả xi lanh

```text
Dòng 183 - 201: toggle trạng thái xi lanh bằng nút vật lý hoặc lệnh PC.
```

### Điều khiển bằng nút vật lý

- **X002 AND X003 -> M11**: khi hai điều kiện/nút vật lý cùng ON thì tạo tín hiệu M11.
- **LDP M11 -> ALT M10**: cạnh lên của M11 đảo trạng thái M10.

### Điều khiển bằng PC

- **LDP M104 -> ALT M10**: khi PC gửi bit toggle xi lanh, PLC đảo trạng thái M10.

### Xuất ngõ ra

- **M10 ON -> Y006 ON**: xi lanh ở trạng thái kẹp/ON.
- **M10 OFF -> Y007 ON**: xi lanh ở trạng thái nhả/OFF hoặc đèn chỉ thị tương ứng tùy wiring.

---

## 9. Lệnh bắt đầu đo

```text
Dòng 202 - 252: xử lý Start Record / bắt đầu chu trình đo.
```

Khi có cạnh lên **M102**:

- **SET M1**: bật trạng thái đang test/chạy chu trình đo.
- **SET M2**: bật trạng thái cho phép ghi dữ liệu.
- **RST M3**: xóa Done cũ.
- **RST M20**: reset trạng thái brake ready.
- **MOV D101 D121**: trả mode hiện tại về PC.
- **MOV K10 D122**: phase ban đầu = 10.
- **MOV K1 D123**: cycle hiện tại ban đầu = 1.
- **MOV K0 D124**: reset góc hiện tại.
- **MOV K0 D125**: reset target angle.
- **DMOV D8140 D170**: lưu bộ đếm xung servo hiện tại làm mốc.
- **MOV D124 D172**: lưu góc hiện tại làm mốc tính toán.
- **MOV K1 D130**: đặt step đầu tiên là step 1.
- **MOV K1 D180**: đặt cycle đang chạy là 1.

---

## 10. Lệnh dừng đo

```text
Dòng 257 - 264: dừng test khi PC Stop Record, Abort, Stop vật lý hoặc EMG.
```

Điều kiện dừng gồm:

- **M103**: Stop Record từ PC.
- **M106**: Abort từ PC.
- **X001**: Stop vật lý.
- **X004**: EMG.

Khi dừng:

- **RST M1**: tắt trạng thái đang test.
- **RST M2**: tắt cho phép ghi dữ liệu.
- **SET M3**: bật Done để báo kết thúc/dừng.
- **MOV K0 D122**: phase về 0.

---

## 11. Điều khiển phanh tức thời cho đo

```text
Dòng 269 - 289: điều khiển Y002 và M20.
```

- Khi **M1 ON** và **không lỗi M4**, PLC **SET Y002** và **SET M20**.
- Theo comment trong MAIN.csv: `Y002 ON = nhả phanh`, `M20 ON = brake ready`, không dùng delay.
- Khi **M1 OFF**, PLC **RST Y002** và **RST M20**.

Ý nghĩa: khi bắt đầu test, phanh được nhả ngay và `M20` báo servo/chu trình đã sẵn sàng phát xung đo.

---

## 12. Chu trình góc chung

```text
Dòng 372 - 445: đặt phase và target theo step D130.
Chu trình target: 0 -> +góc -> 0 -> -góc -> 0.
```

### Phase khi đang test

- **LD M1 -> MOV K210 D122**: khi đang test, phase trả về PC là 210.

### Target theo step D130

- **D130 = 1 -> MOV D102 D125**: target là góc thuận/dương.
- **D130 = 2 -> MOV K0 D125**: target về 0.
- **D130 = 3 -> MOV D103 D125; NEG D125**: target là góc nghịch/âm.
- **D130 = 4 -> MOV K0 D125**: target về 0.

---

## 13. Bỏ qua target bằng 0

```text
Dòng 448 - 475: tự skip step nếu góc cài đặt bằng 0.
```

- Nếu đang **step 1** mà `D102 = 0`, PLC chuyển thẳng sang **step 3** để bỏ qua đoạn chạy góc dương.
- Nếu đang **step 3** mà `D103 = 0`, PLC chuyển sang **step 4** để bỏ qua đoạn chạy góc âm và về/kết thúc tại 0.

Ý nghĩa: tránh phát xung không cần thiết khi người dùng cấu hình góc thuận hoặc góc nghịch bằng 0.

---

## 14. Chế độ Manual, Jog và Home

```text
Dòng 450 - 520: xử lý mode Manual D101 = 0.
```

### Manual standby

Khi `D101 = 0`, máy RUN, không lỗi, không test và không có Jog/Home:

- **MOV K100 D122**: phase Manual Standby.

### Jog Plus

Khi `D101 = 0`, RUN, không lỗi, không test và `M110 ON`:

- **MOV K110 D122**: phase Jog Plus.
- **MUL D104 K1 D150**: tốc độ jog dương.
- **DPLSV D150 Y000 Y004**: phát xung liên tục cho servo theo chiều dương.

### Jog Minus

Khi `D101 = 0`, RUN, không lỗi, không test và `M111 ON`:

- **MOV K120 D122**: phase Jog Minus.
- **MUL D104 K-1 D150**: tốc độ jog âm.
- **DPLSV D150 Y000 Y004**: phát xung liên tục theo chiều âm.

### Home / Zero

Khi `D101 = 0` và có cạnh lên `M112`:

- **MOV K130 D122**: phase Home.
- **MOV K0 D124**: reset góc hiện tại về 0.
- **MOV K0 D125**: reset target về 0.

---

## 15. Xóa dữ liệu tính toán khi không test

```text
Dòng 525 - 536: khi M1 OFF, reset D160, D161, D164.
```

- **D160**: sai lệch góc target - current.
- **D161**: trị tuyệt đối sai lệch góc.
- **D164**: số xung cần phát cho đoạn di chuyển.

Khi không test, các giá trị này được đưa về 0 để tránh còn dữ liệu cũ.

---

## 16. Tính sai lệch góc và số xung cần phát

```text
Dòng 541 - 593: tính delta angle và quy đổi sang số xung servo.
```

### Công thức trong PLC

- **SUB D125 D124 D160**: `D160 = target angle - current angle`.
- Nếu **D160 > 0**: reset chiều âm `Y004`.
- Nếu **D160 < 0**: set `Y004` để chọn chiều âm.
- **D161 = ABS(D160)**: lấy trị tuyệt đối sai lệch.
- **MUL D161 K50 D162**: nhân sai lệch với 50.
- **DDIV D162 K9 D164**: chia cho 9 để ra số xung cần phát.

Ý nghĩa: PLC dùng sai lệch góc để tính số pulse servo cần chạy. Tỷ lệ hiện tại là:

```text
pulse = abs(target - current) * 50 / 9
```

---

## 17. Phát xung servo trong Manual Jog

```text
Dòng 606 - 668: phát xung DPLSV cho Jog Plus/Jog Minus.
```

- **Jog Plus**: `D150 = D104 * 1`.
- **Jog Minus**: `D150 = D104 * -1`.
- Khi không Jog, `DMOV K0 D150` để tốc độ về 0.
- Khi có M110 hoặc M111, mode Manual, RUN, không test, servo ON và không lỗi: PLC gọi **DPLSV D150 Y000 Y004**.

Ý nghĩa: Jog là phát xung liên tục theo tốc độ `D104`, chiều được quyết định bởi dấu của `D150` và ngõ chiều `Y004`.

---

## 18. Phát xung servo trong chu trình đo

```text
Dòng 681 - 685: khi đang test, brake ready và servo ON thì phát xung PLSY.
```

Điều kiện phát xung đo:

- **M1 ON**: đang test.
- **M20 ON**: brake ready/phanh đã nhả.
- **Y005 ON**: servo ON.
- **M4 OFF**: không lỗi.

Lệnh phát xung:

```text
PLSY D104 D164 Y000
```

- **D104**: tốc độ phát xung.
- **D164**: số xung cần phát đã tính từ sai lệch góc.
- **Y000**: ngõ phát pulse servo.

---

## 19. Cập nhật góc hiện tại theo encoder/pulse

```text
Dòng 692 - 756: cập nhật D124 theo delta pulse D8140.
```

### Các bước tính

- **DSUB D8140 D170 D174**: lấy số xung tăng thêm so với mốc D170.
- **DMUL D174 K9 D176**: nhân delta pulse với 9.
- **DDIV D176 K50 D182**: chia 50 để đổi pulse về góc.
- Nếu **D125 >= D172**: `D124 = D172 + D182`.
- Nếu **D125 < D172**: `D124 = D172 - D182`.

Ý nghĩa: `D124` không nhảy ngay tới target, mà được cập nhật dần theo xung thực tế từ bộ đếm `D8140`. Điều này giúp PC thấy góc realtime gần với chuyển động servo.

---

## 20. Điều kiện chuyển step và kết thúc cycle

```text
Dòng 949 - 1180: chuyển step khi sai lệch còn nhỏ và cập nhật cycle.
Điều kiện đạt target: D161 <= K5.
```

### Step 1: +góc xong -> về 0

```text
Dòng 1135 - 1175
```

Điều kiện:

- Đang test `M1`.
- Sai lệch `D161 <= 5`.
- Target đang dương `D125 > 0`.
- Đang step 1 `D130 = 1`.

Hành động:

- Chốt `D124 = D125`.
- Lưu lại mốc pulse `D170 = D8140`.
- Lưu mốc góc `D172 = D124`.
- Chuyển sang **D130 = 2**.

### Step 2: về 0 xong -> xuống -góc

```text
Dòng 1090 - 1130
```

Điều kiện:

- `D161 <= 5`.
- Target `D125 = 0`.
- Đang step 2 `D130 = 2`.

Hành động: chốt góc, cập nhật mốc pulse/góc và chuyển sang **D130 = 3**.

### Step 3: -góc xong -> về 0

```text
Dòng 1045 - 1085
```

Điều kiện:

- `D161 <= 5`.
- Target đang âm `D125 < 0`.
- Đang step 3 `D130 = 3`.

Hành động: chốt góc, cập nhật mốc pulse/góc và chuyển sang **D130 = 4**.

### Step 4: về 0 xong nhưng chưa đủ cycle

```text
Dòng 949 - 1001
```

Điều kiện:

- `D161 <= 5`.
- Target `D125 = 0`.
- Đang step 4 `D130 = 4`.
- Cycle hiện tại `D180 < D105`.

Hành động:

- Chốt `D124 = D125`.
- Tăng `D180 = D180 + 1`.
- Cập nhật mốc pulse/góc.
- Quay lại **D130 = 1** để chạy cycle tiếp theo.

### Step 4: về 0 xong và đủ cycle

```text
Dòng 1006 - 1040
```

Điều kiện:

- `D161 <= 5`.
- Target `D125 = 0`.
- Đang step 4 `D130 = 4`.
- Cycle hiện tại `D180 >= D105`.

Hành động:

- **RST M1**: dừng test.
- **RST M2**: tắt ghi dữ liệu.
- **SET M3**: báo Done.
- **MOV K0 D122**: phase về 0.

### Cập nhật current cycle

```text
Dòng 1180 - 1181: MOV D180 D123.
```

PLC trả cycle hiện tại về PC qua `D123`.

---

## 21. Clear Done và reset command word

```text
Dòng 1186 - 1194: xử lý cuối chương trình.
```

### Clear Done

- **LD M107 -> RST M3**: khi PC gửi bit Clear Done, PLC xóa cờ Done.

### Reset D100

- **LD M8000 -> MOV K0 D100**: cuối mỗi scan, PLC xóa word lệnh D100.

Ý nghĩa: PC chỉ cần ghi lệnh dạng pulse vào `D100`; PLC đọc xong sẽ tự clear để tránh lệnh bị giữ liên tục.

---

## 22. Tóm tắt luồng vận hành

```text
PC ghi thông số D101..D112
        ↓
PC gửi Start RUN qua D100.0 hoặc nhấn X000
        ↓
PLC bật M0, Servo ON Y005 nếu an toàn
        ↓
PC gửi Start Record D100.2
        ↓
PLC SET M1/M2, nhả phanh Y002, đặt D130 = 1
        ↓
Chu trình chạy +góc -> 0 -> -góc -> 0
        ↓
Mỗi lần về 0 đủ một cycle thì D180 tăng 1
        ↓
Khi D180 >= D105, PLC RST M1/M2 và SET M3 Done
        ↓
PC đọc D123/D124/D125/D131/D132/D133/D134 để hiển thị và ghi dữ liệu
```

---

## 23. Các điểm cần lưu ý khi bảo trì

- File MAIN mới đang reset `D100` mỗi scan, vì vậy phần mềm PC nên ghi lệnh dạng pulse/read-modify-write nhanh và không kỳ vọng giữ bit lâu.
- `D120` hiện đang bị ghi `K0` liên tục, chưa đóng gói bit status tổng. PC nên đọc các thanh ghi riêng như `D131`, `D132`, `D133`, `D134`.
- `D8416` trong file mới là `K200`; nếu tài liệu Modbus hoặc PC đang giả định mapping bắt đầu `D100`, cần kiểm tra lại cấu hình thực tế PLC/Modbus.
- `Y007` xuất hiện ở cả cụm đèn trạng thái và cụm xi lanh. Cần đối chiếu sơ đồ điện để tránh hiểu nhầm chức năng ngõ ra.
- Ngưỡng đạt target hiện là `D161 <= 5`. Nếu đơn vị góc là x100 thì ngưỡng này tương ứng 0.05 độ; cần xác nhận với thực tế scale.
