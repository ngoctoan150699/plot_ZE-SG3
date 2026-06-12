# Tài liệu Giải thích Chi tiết Từng Dòng Lệnh trong MAIN.csv

Tài liệu này dịch toàn bộ các dòng lệnh ladder logic từ file `MAIN.csv` sang dạng sơ đồ text trực quan và giải thích chi tiết mục đích, cách hoạt động của từng dòng code.

---

## PHẦN 1: CẤU HÌNH TRUYỀN THÔNG MODBUS RTU SLAVE

```text
Dòng 0 - 35: Cấu hình Modbus RTU cho kênh 1 (CH1) của FX3U khi PLC khởi động lần đầu (M8002)
```

### Chi tiết các lệnh khởi tạo:
*   **`LD M8002`**: Tiếp điểm cạnh lên khi PLC chuyển sang chế độ RUN (chỉ ON trong 1 vòng quét đầu tiên).
*   **`MOV H10D1 D8400`**: Cấu hình cổng truyền thông: 115200 bps, 8 data bits, không parity, 1 stop bit.
*   **`MOV H11 D8401`**: Chọn giao thức Modbus RTU Slave.
*   **`MOV K5 D8411`**: Cấu hình thời gian trễ phản hồi (Response Delay) là 5 ms.
*   **`MOV K2 D8414`**: Đặt địa chỉ Slave ID của PLC là 2.
*   **`MOV H11 D8415`**: Cấu hình cho phép đọc/ghi dữ liệu từ thiết bị (thanh ghi D).
*   **`MOV K100 D8416`**: Đặt vùng địa chỉ thanh ghi Modbus bắt đầu từ thanh ghi **`D100`**.
*   **`SET M8411`**: Kích hoạt cổng truyền thông Modbus RTU hoạt động.

---

## PHẦN 2: BÓC TÁCH WORD LỆNH PC (D100) RA CÁC BIT ĐIỀU KHIỂN

```text
Dòng 36 - 110: Tách các bit từ D100 để gán cho các cuộn coil trung gian M100 - M107
```

### Sơ đồ Ladder:
```text
LD M8000 --------+--- [ LDP D100.0 ] ----------------- ( OUT M100 )  <- Lệnh START
                 +--- [ LDP D100.1 ] ----------------- ( OUT M101 )  <- Lệnh STOP
                 +--- [ LDP D100.2 ] ----------------- ( OUT M102 )  <- Bắt đầu đo
                 +--- [ LDP D100.3 ] ----------------- ( OUT M103 )  <- Dừng đo
                 +--- [ LDP D100.4 ] ----------------- ( OUT M104 )  <- Toggle kẹp nhả
                 +--- [ LDP D100.5 ] ----------------- ( OUT M105 )  <- Bật Servo ON
                 +--- [ LDP D100.6 ] ----------------- ( OUT M106 )  <- Lệnh Abort
                 +--- [ LDP D100.7 ] ----------------- ( OUT M107 )  <- Xóa cờ DONE
```
*   **Giải thích:** Đọc liên tục trạng thái các bit của thanh ghi lệnh `D100` (được ghi từ PC xuống). Khi bit nào chuyển từ `0` lên `1` (cạnh lên), PLC sẽ xuất tín hiệu kích hoạt cuộn coil trung gian tương ứng (`M100` đến `M107`) trong vòng 1 chu kỳ quét để xử lý lệnh dạng pulse nhấn nhả.

---

## PHẦN 3: LOGIC RUN / STOP HỆ THỐNG CHÍNH (M0)

```text
Dòng 111 - 128: Mạch duy trì trạng thái RUN/STOP hệ thống (M0)
```

### Sơ đồ Ladder:
```text
   X000 (Start vật lý)
---| |--------------+---|/|-----------|/|-----------|/|-----------|/|-----------( OUT M0 )
   M100 (Start PC)  |  X001 (Stop VL) M101 (Stop PC) M106 (Abort) X004 (EMG)
---| |--------------+
   M0 (Duy trì)     |
---| |--------------+
```
*   **Giải thích:** 
    *   Hệ thống sẽ được kích hoạt RUN (`M0 = ON`) khi nhấn nút Start vật lý `X000` hoặc kích lệnh Start từ máy tính `M100`.
    *   Hệ thống sẽ bị tắt (`M0 = OFF`) ngay lập tức nếu tác động một trong các nút: Stop vật lý `X001`, lệnh Stop từ PC `M101`, lệnh Abort `M106`, hoặc nhấn nút Dừng khẩn cấp EMG `X004`.

---

## PHẦN 4: LOGIC KÍCH HOẠT SERVO ON (Y005)

```text
Dòng 129 - 137: Điều khiển ngõ ra kích hoạt Servo ON (Y005)
```

### Sơ đồ Ladder:
```text
   M8000      M0 (Hệ thống RUN)    M4 (Lỗi)     X004 (EMG)
---| |--------------| |--------------|/|-----------|/|------------------------( OUT Y005 )
```
*   **Giải thích:**
    *   Servo chỉ được kích hoạt bật lực giữ (`Y005 = ON`) khi hệ thống đang ở trạng thái RUN (`M0 = ON`).
    *   Servo sẽ tự động mất lực (OFF) nếu hệ thống bị lỗi (`M4 = ON`) hoặc khi nhấn nút Dừng khẩn cấp EMG (`X004` bị tác động làm hở mạch).

---

## PHẦN 5: LOGIC TOGGLE KẸP / NHẢ XI LANH (Y006)

```text
Dòng 138 - 180: Logic thay đổi trạng thái kẹp xi lanh Y006
```

### Sơ đồ Ladder:
```text
   X002 (Nút an toàn 1) X003 (Nút an toàn 2)
---| |-----------------------| |----------------------------------------------( OUT M11 )

   M11 (Hai nút nhấn đồng thời)
---|P|------------------------------------------------------------------------[ ALT M10 ]

   M104 (PC nhấn toggle kẹp)
---|P|------------------------------------------------------------------------[ ALT M10 ]

   M10 (Trạng thái trung gian)
---| |------------------------------------------------------------------------( OUT Y006 )
```
*   **Giải thích:**
    *   Khi người vận hành nhấn đồng thời cả 2 nút an toàn vật lý `X002` và `X003` (để tránh kẹp tay), cuộn `M11` ON. Cạnh lên của `M11` sẽ kích hoạt lệnh `ALT M10` để đảo trạng thái kẹp/nhả của xi lanh (`M10`).
    *   Tương tự, khi PC gửi lệnh toggle kẹp `M104`, cạnh lên của nó cũng đảo trạng thái `M10`.
    *   Ngõ ra van điện từ xi lanh `Y006` hoạt động theo trạng thái của `M10`.

---

## PHẦN 6: CHU TRÌNH BẮT ĐẦU VÀ DỪNG ĐO (START/STOP RECORD)

```text
Dòng 181 - 245: Khởi động hoặc hủy bỏ chu trình tự động đo momen
```

### Logic Bắt đầu Đo:
```text
   M102 (Cạnh lên lệnh Start đo từ PC)
---|P|--------------+---------------------------------------------------------[ SET M1 ]   <- Set cờ đang đo
                    +---------------------------------------------------------[ SET M2 ]   <- Set cờ cho ghi data
                    +---------------------------------------------------------[ RST M3 ]   <- Reset cờ hoàn tất
                    +---------------------------------------------------------[ MOV D101 D121 ] <- Ghi chế độ đo hiện tại
                    +---------------------------------------------------------[ MOV K10 D122 ]  <- Đưa Phase chạy về 10
                    +---------------------------------------------------------[ MOV K1 D123 ]   <- Khởi tạo chu kỳ thứ 1
```

### Logic Dừng Đo:
```text
   M103 (PC dừng đo)
---| |--------------+---------------------------------------------------------[ RST M1 ]   <- Reset cờ đang đo
   M106 (PC Abort)  |                                                         [ RST M2 ]   <- Reset cờ cho ghi data
---| |--------------+                                                         [ MOV K0 D122 ] <- Đưa Phase chạy về 0
   X001 (Stop VL)   |
---| |--------------+
   X004 (EMG)       |
---| |--------------+
```

---

## PHẦN 7: LOGIC TÍNH SAI LỆCH GÓC, CHỌN HƯỚNG QUAY VÀ TÍNH XUNG PHÁT

```text
Dòng 246 - 315: Tính toán sai lệch góc, xuất tín hiệu hướng quay Y004 và quy đổi xung
```

### 1. Tính sai lệch góc D160:
```text
   M1 (Đang đo)
---| |------------------------------------------------------------------------[ SUB D125 D124 D160 ]
```
*   `D160 (Sai lệch) = Góc đích (D125) - Góc hiện tại (D124)`.

### 2. Quyết định hướng quay Y004 (Đã đảo ngược để quay phải trước):
```text
   M1 (Đang đo)      D160 > K0 (Sai lệch dương)
---| |-------------------| > |------------------------------------------------[ RST Y004 ] (Quay phải)

   M1 (Đang đo)      D160 < K0 (Sai lệch âm)
---| |-------------------| < |------------------------------------------------[ SET Y004 ] (Quay trái)
```

### 3. Tính trị tuyệt đối góc lệch D161:
*   Nếu `D160 > 0` -> `MOV D160 D161`.
*   Nếu `D160 < 0` -> `NEG D160 D161` (đổi dấu thành số dương).

### 4. Tính toán số xung phát ra D164:
```text
   M1 (Đang đo)
---| |--------------+---------------------------------------------------------[ MUL D161 K50 D162 ]
                    +---------------------------------------------------------[ DIV D162 K9 D164 ]
```
*   Công thức: $\text{Số xung (D164)} = \frac{\text{ABS lệch góc (D161)} \times 50}{9}$ (Quy đổi tương đương 200,000 xung / 360 độ).

---

## PHẦN 8: CHẾ ĐỘ MANUAL / JOG / HOME VÀ PHÁT XUNG SERVO

```text
Dòng 339 - 570: Điều khiển Manual, Jog/Home, DPLSV và PLSY cho Servo
```

> Lưu ý: số dòng bên dưới là **số dòng Ladder trong GX Works2/MAIN.csv**,
> không phải số thứ tự dòng của file markdown.

### 1. Chọn phase Manual / Jog / Home
```text
Dòng 339:
D101 = K0, M0 ON, M4 OFF, M1 OFF, M110 OFF, M111 OFF, M112 OFF
→ MOV K100 D122
```
* Khi đang ở **Manual mode** (`D101 = 0`), hệ thống RUN, không lỗi,
  không đang đo và không bấm Jog/Home thì PLC đưa bước chạy về `D122 = 100`.
* `D122 = 100` nghĩa là Manual đang sẵn sàng nhưng chưa chạy chuyển động.

```text
Dòng 355:
D101 = K0, M0 ON, M4 OFF, M1 OFF, M110 ON
→ MOV K110 D122
```
* Khi nhấn **Jog+** (`M110`), PLC chuyển phase sang `D122 = 110`.
* Đây là trạng thái Servo đang chạy Jog chiều dương.

```text
Dòng 369:
D101 = K0, M0 ON, M4 OFF, M1 OFF, M111 ON
→ MOV K120 D122
```
* Khi nhấn **Jog-** (`M111`), PLC chuyển phase sang `D122 = 120`.
* Đây là trạng thái Servo đang chạy Jog chiều âm.

```text
Dòng 383:
D101 = K0, M0 ON, M4 OFF, M1 OFF, M112 ON
→ MOV K130 D122
```
* Khi có lệnh **Home** (`M112`), PLC chuyển phase sang `D122 = 130`.

```text
Dòng 397:
M112 OFF, D101 = K0
→ MOV K0 D124
→ MOV K0 D125
```
* Khi lệnh Home không còn giữ, PLC reset góc hiện tại `D124 = 0`
  và góc đích `D125 = 0` trong Manual mode.

### 2. Logic chạy tay bằng DPLSV
```text
Dòng 543 - 554:
M110 OR M111,
D101 = K0,
M0 ON,
M1 OFF,
Y005 ON,
M4 OFF
→ DPLSV D150 Y000 Y004
```
* Khi ở Manual mode và bấm Jog+ hoặc Jog-, PLC phát xung liên tục bằng
  lệnh `DPLSV`.
* `Y000` là chân phát xung Servo.
* `Y004` là chân chiều Servo.
* `D150` là tốc độ xung Jog, dấu/tốc độ của `D150` quyết định chiều chạy
  khi dùng `DPLSV`.

### 3. Logic chạy tự động bằng PLSY
```text
Dòng 567 - 570:
M1 ON,
Y005 ON,
M4 OFF
→ PLSY D104 D164 Y000
```
* Khi đang chạy chu trình đo tự động (`M1 = ON`), Servo ON và không lỗi,
  PLC phát đúng số xung `D164` ra `Y000` với tốc độ `D104`.
* Hướng quay lúc này không nằm trong lệnh `PLSY`, mà đã được quyết định trước
  bằng chân hướng `Y004` ở phần tính sai lệch góc.

---

## PHẦN 9: LOGIC GIẢ LẬP CẬP NHẬT GÓC HIỂN THỊ D124 THEO XUNG PHÁT

```text
Dòng 577 - 637: Tính toán góc hiện tại D124 từ xung đã phát ra để hiển thị đồ thị
```

1.  PLC đọc bộ đếm xung phát ra của ngõ Y000 thông qua thanh ghi đặc biệt **`D8140`**.
2.  Hiệu số xung phát ra giữa 2 chu kỳ quét được tính toán và quy đổi ngược thành độ lệch góc tương ứng `D182`:
    $$\text{Độ lệch góc (D182)} = \frac{\text{Hiệu xung} \times 9}{50}$$
3.  Cập nhật góc hiển thị `D124`:
    *   Nếu đang chạy tới đích lớn hơn (`D125 >= Góc xuất phát D172`):
        *   `D124 = D172 + D182` (Góc tăng dần).
    *   Nếu đang chạy tới đích nhỏ hơn (`D125 < Góc xuất phát D172`):
        *   `D124 = D172 - D182` (Góc giảm dần).
