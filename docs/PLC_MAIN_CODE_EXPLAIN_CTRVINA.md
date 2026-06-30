# GIẢI THÍCH CODE PLC MAIN.csv THEO TỪNG CỤM / TỪNG DÒNG

Khách hàng: CÔNG TY CTR VINA

Phiên bản tài liệu: 1.0

Ngày biên soạn: 30/06/2026

Tài liệu này đọc lại từ file MAIN.csv mới nhất. Format giữ theo dạng giải thích cụm: sơ đồ ladder/text, ý nghĩa thanh ghi và tác dụng cụm.

## BẢNG COMMENT THIẾT BỊ / THANH GHI

| Device | Ý nghĩa |
| --- | --- |
| D100 | Word lệnh PC |
| D101 | Chế độ đo |
| D102 | Góc dương x100 |
| D103 | Góc âm x100 |
| D104 | Tốc độ x100 |
| D105 | Số chu kỳ |
| D106 | Vùng lấy mẫu |
| D107 | Chọn loại SP |
| D108 | Loại đo momen |
| D109 | Reset lỗi PC |
| D110 | Jog chiều dương |
| D111 | Jog chiều âm |
| D112 | Lệnh về gốc |
| D120 | TT PC |
| D121 | Mode HT |
| D122 | Bước chạy |
| D123 | Chu kỳ HT |
| D124 | Góc hiện tại |
| D125 | Góc đích |
| D126 | Tốc độ HT |
| D127 | VT servo L |
| D128 | VT servo H |
| D129 | Mã lỗi PLC |
| D130 | Mẫu hợp lệ |
| D131 | Cho ghi mẫu |
| D132 | TT xi lanh |
| D133 | TT Servo |
| D134 | TT Done |
| D135 | Số mẫu |
| D150 | Xung + L |
| D151 | Xung + H |
| D152 | Xung - L |
| D153 | Xung - H |
| D154 | Tốc xung L |
| D155 | Tốc xung H |
| D156 | Góc min OK |
| D157 | Góc max OK |
| D158 | TG bước |
| D160 | Sai goc |
| D161 | ABS goc |
| D162 | Xung tinh L |
| D163 | Xung tinh H |
| D164 | So xung L |
| D165 | So xung H |
| D170 | Xung phát L |
| D172 | Góc xuất phát |
| D174 | Xung phát H |
| D176 | Delta xung L |
| D180 | Lưu tạm xung |
| D182 | Góc dịch chuyển |
| D8140 | Thanh ghi xung hiện tại PLC/servo |
| D8400 | 115200 8N1 |
| D8401 | Modbus Slave RTU |
| D8411 | Delay 5 ms |
| D8414 | Slave ID bằng 2 |
| D8415 | Lưu D |
| D8416 | Từ D200 |
| M0 | TT chạy dừng |
| M1 | Đang đo |
| M2 | Cho ghi data |
| M3 | Hoàn tất |
| M4 | Báo lỗi |
| M10 | Nhớ TT XL |
| M11 | Hai nút OK |
| M12 | Xung 2 nút |
| M13 | PC kẹp nhả |
| M20 | Bắt ghi |
| M21 | Dừng ghi |
| M30 | SV đang chạy |
| M31 | SV chạy xong |
| M32 | SV chiều + |
| M33 | SV chiều - |
| M100 | PC START D100.0 |
| M101 | PC STOP D100.1 |
| M102 | PC bắt đo |
| M103 | PC dừng đo |
| M104 | PC kẹp nhả |
| M105 | PC bật servo |
| M106 | Dừng khẩn |
| M107 | PC xóa DONE |
| M110 | Jog chiều dương từ PC (D110=1) |
| M111 | Jog chiều âm từ PC (D111=1) |
| M112 | Lệnh Home/về gốc từ PC (D112=1) |
| M8000 | PLC RUN |
| M8411 | init modbus |
| X000 | Nút START |
| X001 | Nút STOP |
| X002 | Nút 1 an toàn |
| X003 | Nút 2 an toàn |
| X004 | Nút dừng khẩn |
| Y000 | Xung servo |
| Y002 | Phanh servo |
| Y004 | Chiều servo |
| Y005 | Bật Servo ON |
| Y006 | Xi lanh kẹp nhả |
| Y007 | Xi lanh kẹp nhả 2 |
| Y010 | Đèn báo STOP/không RUN |
| Y011 | Đèn báo lỗi |

## PHẦN 1: 01 Khoi tao truyen thong Modbus RTU slave

```text
Dòng/Step 0 - 27: Khởi tạo truyền thông Modbus RTU Slave cho FX3U/FX3UC: cấu hình tốc độ, protocol, delay, Slave ID và vùng thanh ghi D cho PC truy cập.
```

### Sơ đồ Ladder:
```text
    0 ---| |--- LD M8411            init modbus
    2 [MOV H10D1 -> D8400]
    7 [MOV H11 -> D8401]
   12 [MOV K5 -> D8411]
   17 [MOV K2 -> D8414]
   22 [MOV H11 -> D8415]
   27 [MOV K200 -> D8416]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M8411 | init modbus |
| D8400 | 115200 8N1 |
| D8401 | Modbus Slave RTU |
| D8411 | Delay 5 ms |
| D8414 | Slave ID bằng 2 |
| D8415 | Lưu D |
| D8416 | Từ D200 |

### Giải thích:
- LD M8411: dùng init modbus làm điều kiện logic.
- MOV H10D1 D8400: ghi/copy giá trị H10D1 vào D8400 (115200 8N1).
- MOV H11 D8401: ghi/copy giá trị H11 vào D8401 (Modbus Slave RTU).
- MOV K5 D8411: ghi/copy giá trị K5 vào D8411 (Delay 5 ms).
- MOV K2 D8414: ghi/copy giá trị K2 vào D8414 (Slave ID bằng 2).
- MOV H11 D8415: ghi/copy giá trị H11 vào D8415 (Lưu D).
- MOV K200 D8416: ghi/copy giá trị K200 vào D8416 (Từ D200).

---

## PHẦN 2: 02 Tach va doc lenh PC qua M8000

```text
Dòng/Step 32 - 103: Đọc word/lệnh PC và tách thành các M trung gian để PLC xử lý START/STOP/ghi đo/jog/home.
```

### Sơ đồ Ladder:
```text
   32 ---| |--- LD M8000            PLC RUN
   33 [MPS ]
   34 ---| |--- AND D100.0            Word lệnh PC
   37 -----------------------------(OUT M100)  PC START D100.0
   38 [MRD ]
   39 ---| |--- AND D100.1            Word lệnh PC
   42 -----------------------------(OUT M101)  PC STOP D100.1
   43 [MRD ]
   44 ---| |--- AND D100.2            Word lệnh PC
   47 -----------------------------(OUT M102)  PC bắt đo
   48 [MRD ]
   49 ---| |--- AND D100.3            Word lệnh PC
   52 -----------------------------(OUT M103)  PC dừng đo
   53 [MRD ]
   54 ---| |--- AND D100.4            Word lệnh PC
   57 -----------------------------(OUT M104)  PC kẹp nhả
   58 [MRD ]
   59 ---| |--- AND D100.5            Word lệnh PC
   62 -----------------------------(OUT M105)  PC bật servo
   63 [MRD ]
   64 ---| |--- AND D100.6            Word lệnh PC
   67 -----------------------------(OUT M106)  Dừng khẩn
   68 [MRD ]
   69 ---| |--- AND D100.7            Word lệnh PC
   72 -----------------------------(OUT M107)  PC xóa DONE
   73 [MRD ]
   74 ---[ LD= D110 K1 ]---  Jog chiều dương
   79 [ANB ]
   80 -----------------------------(OUT M110)  Jog chiều dương từ PC (D110=1)
   81 [MRD ]
   82 ---[ LD= D111 K1 ]---  Jog chiều âm
   87 [ANB ]
   88 -----------------------------(OUT M111)  Jog chiều âm từ PC (D111=1)
   89 [MPP ]
   90 ---[ LD= D112 K1 ]---  Lệnh về gốc
   95 [ANB ]
   96 -----------------------------(OUT M112)  Lệnh Home/về gốc từ PC (D112=1)
   97 ---| |--- LD M8000            PLC RUN
   98 ---[ AND<= D105 K0 ]---  Số chu kỳ
  103 [MOV K3 -> D105]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M8000 | PLC RUN |
| D100 | Word lệnh PC |
| M100 | PC START D100.0 |
| M101 | PC STOP D100.1 |
| M102 | PC bắt đo |
| M103 | PC dừng đo |
| M104 | PC kẹp nhả |
| M105 | PC bật servo |
| M106 | Dừng khẩn |
| M107 | PC xóa DONE |
| D110 | Jog chiều dương |
| M110 | Jog chiều dương từ PC (D110=1) |
| D111 | Jog chiều âm |
| M111 | Jog chiều âm từ PC (D111=1) |
| D112 | Lệnh về gốc |
| M112 | Lệnh Home/về gốc từ PC (D112=1) |
| D105 | Số chu kỳ |

### Giải thích:
- LD M8000: dùng PLC RUN làm điều kiện logic.
- MPS: lệnh chia/ghép nhánh ladder để dùng chung điều kiện trước đó.
- AND D100.0: dùng Word lệnh PC làm điều kiện logic.
- OUT M100: tác động lên M100 - PC START D100.0.
- MRD: lệnh chia/ghép nhánh ladder để dùng chung điều kiện trước đó.
- AND D100.1: dùng Word lệnh PC làm điều kiện logic.
- OUT M101: tác động lên M101 - PC STOP D100.1.
- AND D100.2: dùng Word lệnh PC làm điều kiện logic.
- OUT M102: tác động lên M102 - PC bắt đo.
- AND D100.3: dùng Word lệnh PC làm điều kiện logic.
- OUT M103: tác động lên M103 - PC dừng đo.
- AND D100.4: dùng Word lệnh PC làm điều kiện logic.
- OUT M104: tác động lên M104 - PC kẹp nhả.
- AND D100.5: dùng Word lệnh PC làm điều kiện logic.
- OUT M105: tác động lên M105 - PC bật servo.
- AND D100.6: dùng Word lệnh PC làm điều kiện logic.
- OUT M106: tác động lên M106 - Dừng khẩn.
- AND D100.7: dùng Word lệnh PC làm điều kiện logic.
- OUT M107: tác động lên M107 - PC xóa DONE.
- LD= D110 K1: kiểm tra D110 (Jog chiều dương) bằng K1; đúng thì cho phép nhánh logic tiếp tục.
- ANB: lệnh chia/ghép nhánh ladder để dùng chung điều kiện trước đó.
- OUT M110: tác động lên M110 - Jog chiều dương từ PC (D110=1).
- LD= D111 K1: kiểm tra D111 (Jog chiều âm) bằng K1; đúng thì cho phép nhánh logic tiếp tục.
- OUT M111: tác động lên M111 - Jog chiều âm từ PC (D111=1).
- MPP: lệnh chia/ghép nhánh ladder để dùng chung điều kiện trước đó.
- LD= D112 K1: kiểm tra D112 (Lệnh về gốc) bằng K1; đúng thì cho phép nhánh logic tiếp tục.
- OUT M112: tác động lên M112 - Lệnh Home/về gốc từ PC (D112=1).
- AND<= D105 K0: kiểm tra D105 (Số chu kỳ) nhỏ hơn hoặc bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- MOV K3 D105: ghi/copy giá trị K3 vào D105 (Số chu kỳ).

---

## PHẦN 3: 11 Tra trang thai ve PC

```text
Dòng/Step 108 - 157: Ghi trạng thái máy về PC qua các thanh ghi D131..D134 để phần mềm biết xi lanh, servo, done và quyền ghi mẫu.
```

### Sơ đồ Ladder:
```text
  108 ---| |--- LD M8000            PLC RUN
  109 [MOV K0 -> D120]
  114 ---| |--- LD M10            Nhớ TT XL
  115 [MOV K1 -> D132]
  120 ---|/|--- LDI M10            Nhớ TT XL
  121 [MOV K0 -> D132]
  126 ---| |--- LD Y005            Bật Servo ON
  127 [MOV K1 -> D133]
  132 ---|/|--- LDI Y005            Bật Servo ON
  133 [MOV K0 -> D133]
  138 ---| |--- LD M3            Hoàn tất
  139 [MOV K1 -> D134]
  144 ---|/|--- LDI M3            Hoàn tất
  145 [MOV K0 -> D134]
  150 ---| |--- LD M2            Cho ghi data
  151 [MOV K1 -> D131]
  156 ---|/|--- LDI M2            Cho ghi data
  157 [MOV K0 -> D131]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M8000 | PLC RUN |
| D120 | TT PC |
| M10 | Nhớ TT XL |
| D132 | TT xi lanh |
| Y005 | Bật Servo ON |
| D133 | TT Servo |
| M3 | Hoàn tất |
| D134 | TT Done |
| M2 | Cho ghi data |
| D131 | Cho ghi mẫu |

### Giải thích:
- LD M8000: dùng PLC RUN làm điều kiện logic.
- MOV K0 D120: ghi/copy giá trị K0 vào D120 (TT PC).
- LD M10: dùng Nhớ TT XL làm điều kiện logic.
- MOV K1 D132: ghi/copy giá trị K1 vào D132 (TT xi lanh).
- LDI M10: dùng Nhớ TT XL làm điều kiện logic.
- MOV K0 D132: ghi/copy giá trị K0 vào D132 (TT xi lanh).
- LD Y005: dùng Bật Servo ON làm điều kiện logic.
- MOV K1 D133: ghi/copy giá trị K1 vào D133 (TT Servo).
- LDI Y005: dùng Bật Servo ON làm điều kiện logic.
- MOV K0 D133: ghi/copy giá trị K0 vào D133 (TT Servo).
- LD M3: dùng Hoàn tất làm điều kiện logic.
- MOV K1 D134: ghi/copy giá trị K1 vào D134 (TT Done).
- LDI M3: dùng Hoàn tất làm điều kiện logic.
- MOV K0 D134: ghi/copy giá trị K0 vào D134 (TT Done).
- LD M2: dùng Cho ghi data làm điều kiện logic.
- MOV K1 D131: ghi/copy giá trị K1 vào D131 (Cho ghi mẫu).
- LDI M2: dùng Cho ghi data làm điều kiện logic.
- MOV K0 D131: ghi/copy giá trị K0 vào D131 (Cho ghi mẫu).

---

## PHẦN 4: 12 Den bao trang thai

```text
Dòng/Step 162 - 169: Điều khiển các đèn/ngõ ra báo trạng thái RUN, STOP hoặc lỗi.
```

### Sơ đồ Ladder:
```text
  162 ---| |--- LD M0            TT chạy dừng
  163 ---|/|--- ANI M4            Báo lỗi
  164 -----------------------------(OUT Y007)  Xi lanh kẹp nhả 2
  165 ---|/|--- LDI M0            TT chạy dừng
  166 ---|/|--- ANI M4            Báo lỗi
  167 -----------------------------(OUT Y010)  Đèn báo STOP/không RUN
  168 ---| |--- LD M4            Báo lỗi
  169 -----------------------------(OUT Y011)  Đèn báo lỗi
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M0 | TT chạy dừng |
| M4 | Báo lỗi |
| Y007 | Xi lanh kẹp nhả 2 |
| Y010 | Đèn báo STOP/không RUN |
| Y011 | Đèn báo lỗi |

### Giải thích:
- LD M0: dùng TT chạy dừng làm điều kiện logic.
- ANI M4: dùng Báo lỗi làm điều kiện logic.
- OUT Y007: tác động lên Y007 - Xi lanh kẹp nhả 2.
- LDI M0: dùng TT chạy dừng làm điều kiện logic.
- OUT Y010: tác động lên Y010 - Đèn báo STOP/không RUN.
- LD M4: dùng Báo lỗi làm điều kiện logic.
- OUT Y011: tác động lên Y011 - Đèn báo lỗi.

---

## PHẦN 5: 03 Giu RUN STOP bang nut va PC

```text
Dòng/Step 170 - 177: Tạo mạch tự giữ RUN M0; START từ nút vật lý/PC, STOP bởi nút Stop, EMG hoặc Abort.
```

### Sơ đồ Ladder:
```text
  170 ---| |--- LD X000            Nút START
  171 ---| |--- OR M100            PC START D100.0
  172 ---| |--- OR M0            TT chạy dừng
  173 ---|/|--- ANI X001            Nút STOP
  174 ---|/|--- ANI X004            Nút dừng khẩn
  175 ---|/|--- ANI M101            PC STOP D100.1
  176 ---|/|--- ANI M106            Dừng khẩn
  177 -----------------------------(OUT M0)  TT chạy dừng
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| X000 | Nút START |
| M100 | PC START D100.0 |
| M0 | TT chạy dừng |
| X001 | Nút STOP |
| X004 | Nút dừng khẩn |
| M101 | PC STOP D100.1 |
| M106 | Dừng khẩn |

### Giải thích:
- LD X000: dùng Nút START làm điều kiện logic.
- OR M100: dùng PC START D100.0 làm điều kiện logic.
- OR M0: dùng TT chạy dừng làm điều kiện logic.
- ANI X001: dùng Nút STOP làm điều kiện logic.
- ANI X004: dùng Nút dừng khẩn làm điều kiện logic.
- ANI M101: dùng PC STOP D100.1 làm điều kiện logic.
- ANI M106: dùng Dừng khẩn làm điều kiện logic.
- OUT M0: tác động lên M0 - TT chạy dừng.

---

## PHẦN 6: 04 Bat Servo ON khi may dang RUN va khong co loi

```text
Dòng/Step 178 - 182: Bật ngõ ra Servo ON Y005 khi hệ thống RUN và điều kiện an toàn hợp lệ.
```

### Sơ đồ Ladder:
```text
  178 ---| |--- LD M8000            PLC RUN
  179 ---| |--- AND M0            TT chạy dừng
  180 ---|/|--- ANI M4            Báo lỗi
  181 ---|/|--- ANI X004            Nút dừng khẩn
  182 -----------------------------(OUT Y005)  Bật Servo ON
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M8000 | PLC RUN |
| M0 | TT chạy dừng |
| M4 | Báo lỗi |
| X004 | Nút dừng khẩn |
| Y005 | Bật Servo ON |

### Giải thích:
- LD M8000: dùng PLC RUN làm điều kiện logic.
- AND M0: dùng TT chạy dừng làm điều kiện logic.
- ANI M4: dùng Báo lỗi làm điều kiện logic.
- ANI X004: dùng Nút dừng khẩn làm điều kiện logic.
- OUT Y005: tác động lên Y005 - Bật Servo ON.

---

## PHẦN 7: 05 Kep nha xi lanh bang nut va PC

```text
Dòng/Step 183 - 201: Toggle kẹp/nhả xi lanh bằng hai nút an toàn hoặc lệnh PC.
```

### Sơ đồ Ladder:
```text
  183 ---| |--- LD X002            Nút 1 an toàn
  184 ---| |--- AND X003            Nút 2 an toàn
  185 -----------------------------(OUT M11)  Hai nút OK
  186 ---|P|--- LDP M11            Hai nút OK
  188 -----------------------------(ALT M10)  Nhớ TT XL
  191 ---|P|--- LDP M104            PC kẹp nhả
  193 -----------------------------(ALT M10)  Nhớ TT XL
  196 ---| |--- LD M8000            PLC RUN
  197 ---| |--- AND M10            Nhớ TT XL
  198 -----------------------------(OUT Y006)  Xi lanh kẹp nhả
  199 ---| |--- LD M8000            PLC RUN
  200 ---|/|--- ANI M10            Nhớ TT XL
  201 -----------------------------(OUT Y007)  Xi lanh kẹp nhả 2
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| X002 | Nút 1 an toàn |
| X003 | Nút 2 an toàn |
| M11 | Hai nút OK |
| M10 | Nhớ TT XL |
| M104 | PC kẹp nhả |
| M8000 | PLC RUN |
| Y006 | Xi lanh kẹp nhả |
| Y007 | Xi lanh kẹp nhả 2 |

### Giải thích:
- LD X002: dùng Nút 1 an toàn làm điều kiện logic.
- AND X003: dùng Nút 2 an toàn làm điều kiện logic.
- OUT M11: tác động lên M11 - Hai nút OK.
- LDP M11: dùng Hai nút OK làm điều kiện logic.
- ALT M10: tác động lên M10 - Nhớ TT XL.
- LDP M104: dùng PC kẹp nhả làm điều kiện logic.
- LD M8000: dùng PLC RUN làm điều kiện logic.
- AND M10: dùng Nhớ TT XL làm điều kiện logic.
- OUT Y006: tác động lên Y006 - Xi lanh kẹp nhả.
- ANI M10: dùng Nhớ TT XL làm điều kiện logic.
- OUT Y007: tác động lên Y007 - Xi lanh kẹp nhả 2.

---

## PHẦN 8: 06 Lenh bat dau do

```text
Dòng/Step 202 - 252: Khởi tạo chu trình đo: set đang đo, cho ghi dữ liệu, reset Done, nạp mode và reset góc/cycle.
```

### Sơ đồ Ladder:
```text
  202 ---|P|--- LDP M102            PC bắt đo
  204 -----------------------------(SET M1)  Đang đo
  205 -----------------------------(SET M2)  Cho ghi data
  206 -----------------------------(RST M3)  Hoàn tất
  207 -----------------------------(RST M20)  Bắt ghi
  208 [MOV D101 -> D121]
  213 [MOV K10 -> D122]
  218 [MOV K1 -> D123]
  223 [MOV K0 -> D124]
  228 [MOV K0 -> D125]
  233 [DMOV D8140 -> D170]
  242 [MOV D124 -> D172]
  247 [MOV K1 -> D130]
  252 [MOV K1 -> D180]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M102 | PC bắt đo |
| M1 | Đang đo |
| M2 | Cho ghi data |
| M3 | Hoàn tất |
| M20 | Bắt ghi |
| D101 | Chế độ đo |
| D121 | Mode HT |
| D122 | Bước chạy |
| D123 | Chu kỳ HT |
| D124 | Góc hiện tại |
| D125 | Góc đích |
| D8140 | Thanh ghi xung hiện tại PLC/servo |
| D170 | Xung phát L |
| D172 | Góc xuất phát |
| D130 | Mẫu hợp lệ |
| D180 | Lưu tạm xung |

### Giải thích:
- LDP M102: dùng PC bắt đo làm điều kiện logic.
- SET M1: tác động lên M1 - Đang đo.
- SET M2: tác động lên M2 - Cho ghi data.
- RST M3: tác động lên M3 - Hoàn tất.
- RST M20: tác động lên M20 - Bắt ghi.
- MOV D101 D121: ghi/copy giá trị D101 vào D121 (Mode HT).
- MOV K10 D122: ghi/copy giá trị K10 vào D122 (Bước chạy).
- MOV K1 D123: ghi/copy giá trị K1 vào D123 (Chu kỳ HT).
- MOV K0 D124: ghi/copy giá trị K0 vào D124 (Góc hiện tại).
- MOV K0 D125: ghi/copy giá trị K0 vào D125 (Góc đích).
- DMOV D8140 D170: ghi/copy giá trị D8140 vào D170 (Xung phát L).
- MOV D124 D172: ghi/copy giá trị D124 vào D172 (Góc xuất phát).
- MOV K1 D130: ghi/copy giá trị K1 vào D130 (Mẫu hợp lệ).
- MOV K1 D180: ghi/copy giá trị K1 vào D180 (Lưu tạm xung).

---

## PHẦN 9: 07 Lenh dung do

```text
Dòng/Step 257 - 264: Dừng chu trình đo và đưa hệ thống về trạng thái hoàn tất.
```

### Sơ đồ Ladder:
```text
  257 ---| |--- LD M103            PC dừng đo
  258 ---| |--- OR M106            Dừng khẩn
  259 ---| |--- OR X001            Nút STOP
  260 ---| |--- OR X004            Nút dừng khẩn
  261 -----------------------------(RST M1)  Đang đo
  262 -----------------------------(RST M2)  Cho ghi data
  263 -----------------------------(SET M3)  Hoàn tất
  264 [MOV K0 -> D122]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M103 | PC dừng đo |
| M106 | Dừng khẩn |
| X001 | Nút STOP |
| X004 | Nút dừng khẩn |
| M1 | Đang đo |
| M2 | Cho ghi data |
| M3 | Hoàn tất |
| D122 | Bước chạy |

### Giải thích:
- LD M103: dùng PC dừng đo làm điều kiện logic.
- OR M106: dùng Dừng khẩn làm điều kiện logic.
- OR X001: dùng Nút STOP làm điều kiện logic.
- OR X004: dùng Nút dừng khẩn làm điều kiện logic.
- RST M1: tác động lên M1 - Đang đo.
- RST M2: tác động lên M2 - Cho ghi data.
- SET M3: tác động lên M3 - Hoàn tất.
- MOV K0 D122: ghi/copy giá trị K0 vào D122 (Bước chạy).

---

## PHẦN 10: 07.1 Brake immediate control for measurement

```text
Dòng/Step 269 - 275: Nhả phanh servo ngay khi đo và khóa lại khi không đo.
```

### Sơ đồ Ladder:
```text
  269 ---| |--- LD M1            Đang đo
  270 ---|/|--- ANI M4            Báo lỗi
  271 -----------------------------(SET Y002)  Phanh servo
  272 -----------------------------(SET M20)  Bắt ghi
  273 ---|/|--- LDI M1            Đang đo
  274 -----------------------------(RST Y002)  Phanh servo
  275 -----------------------------(RST M20)  Bắt ghi
```

### Ghi chú trong MAIN.csv:
- Y002 ON = nha phanh; M20 ON = brake ready; khong delay

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| M4 | Báo lỗi |
| Y002 | Phanh servo |
| M20 | Bắt ghi |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- ANI M4: dùng Báo lỗi làm điều kiện logic.
- SET Y002: tác động lên Y002 - Phanh servo.
- SET M20: tác động lên M20 - Bắt ghi.
- LDI M1: dùng Đang đo làm điều kiện logic.
- RST Y002: tác động lên Y002 - Phanh servo.
- RST M20: tác động lên M20 - Bắt ghi.

---

## PHẦN 11: 08 Chu trinh goc chung

```text
Dòng/Step 276 - 277: Thiết lập phase chung cho chu trình điều khiển góc.
```

### Sơ đồ Ladder:
```text
  276 ---| |--- LD M1            Đang đo
  277 [MOV K210 -> D122]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D122 | Bước chạy |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- MOV K210 D122: ghi/copy giá trị K210 vào D122 (Bước chạy).

---

## PHẦN 12: 08.1 Target chung: 0 -> + -> 0 -> - -> 0

```text
Dòng/Step 282 - 324: Sinh góc đích theo chuỗi 0 → góc dương → 0 → góc âm → 0.
```

### Sơ đồ Ladder:
```text
  282 ---| |--- LD M1            Đang đo
  283 ---[ AND= D130 K1 ]---  Mẫu hợp lệ
  288 [MOV D102 -> D125]
  293 ---| |--- LD M1            Đang đo
  294 ---[ AND= D130 K2 ]---  Mẫu hợp lệ
  299 [MOV K0 -> D125]
  304 ---| |--- LD M1            Đang đo
  305 ---[ AND= D130 K3 ]---  Mẫu hợp lệ
  310 [MOV D103 -> D125]
  315 [NEG D125]
  318 ---| |--- LD M1            Đang đo
  319 ---[ AND= D130 K4 ]---  Mẫu hợp lệ
  324 [MOV K0 -> D125]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D130 | Mẫu hợp lệ |
| D102 | Góc dương x100 |
| D125 | Góc đích |
| D103 | Góc âm x100 |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- AND= D130 K1: kiểm tra D130 (Mẫu hợp lệ) bằng K1; đúng thì cho phép nhánh logic tiếp tục.
- MOV D102 D125: ghi/copy giá trị D102 vào D125 (Góc đích).
- AND= D130 K2: kiểm tra D130 (Mẫu hợp lệ) bằng K2; đúng thì cho phép nhánh logic tiếp tục.
- MOV K0 D125: ghi/copy giá trị K0 vào D125 (Góc đích).
- AND= D130 K3: kiểm tra D130 (Mẫu hợp lệ) bằng K3; đúng thì cho phép nhánh logic tiếp tục.
- MOV D103 D125: ghi/copy giá trị D103 vào D125 (Góc đích).
- NEG D125: đổi dấu giá trị trong D125 (Góc đích).
- AND= D130 K4: kiểm tra D130 (Mẫu hợp lệ) bằng K4; đúng thì cho phép nhánh logic tiếp tục.

---

## PHẦN 13: 08.2 Skip zero angle target

```text
Dòng/Step 329 - 356: Sinh góc đích theo chuỗi 0 → góc dương → 0 → góc âm → 0.
```

### Sơ đồ Ladder:
```text
  329 ---| |--- LD M1            Đang đo
  330 ---[ AND= D130 K1 ]---  Mẫu hợp lệ
  335 ---[ AND= D102 K0 ]---  Góc dương x100
  340 [MOV K3 -> D130]
  345 ---| |--- LD M1            Đang đo
  346 ---[ AND= D130 K3 ]---  Mẫu hợp lệ
  351 ---[ AND= D103 K0 ]---  Góc âm x100
  356 [MOV K4 -> D130]
```

### Ghi chú trong MAIN.csv:
- Neu goc thuan = 0 thi bo qua step +, chay thang step -
- Neu goc nghich = 0 thi bo qua step -, ve/ket thuc tai 0

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D130 | Mẫu hợp lệ |
| D102 | Góc dương x100 |
| D103 | Góc âm x100 |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- AND= D130 K1: kiểm tra D130 (Mẫu hợp lệ) bằng K1; đúng thì cho phép nhánh logic tiếp tục.
- AND= D102 K0: kiểm tra D102 (Góc dương x100) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- MOV K3 D130: ghi/copy giá trị K3 vào D130 (Mẫu hợp lệ).
- AND= D130 K3: kiểm tra D130 (Mẫu hợp lệ) bằng K3; đúng thì cho phép nhánh logic tiếp tục.
- AND= D103 K0: kiểm tra D103 (Góc âm x100) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- MOV K4 D130: ghi/copy giá trị K4 vào D130 (Mẫu hợp lệ).

---

## PHẦN 14: 09.1 Che do Manual va JOG HOME

```text
Dòng/Step 361 - 431: Chế độ Manual/Jog/Home khi không chạy test.
```

### Sơ đồ Ladder:
```text
  361 ---[ LD= D101 K0 ]---  Chế độ đo
  366 ---| |--- AND M0            TT chạy dừng
  367 ---|/|--- ANI M4            Báo lỗi
  368 ---|/|--- ANI M1            Đang đo
  369 ---|/|--- ANI M110            Jog chiều dương từ PC (D110=1)
  370 ---|/|--- ANI M111            Jog chiều âm từ PC (D111=1)
  371 ---|/|--- ANI M112            Lệnh Home/về gốc từ PC (D112=1)
  372 [MOV K100 -> D122]
  377 ---[ LD= D101 K0 ]---  Chế độ đo
  382 ---| |--- AND M0            TT chạy dừng
  383 ---|/|--- ANI M4            Báo lỗi
  384 ---|/|--- ANI M1            Đang đo
  385 ---| |--- AND M110            Jog chiều dương từ PC (D110=1)
  386 [MOV K110 -> D122]
  391 ---[ LD= D101 K0 ]---  Chế độ đo
  396 ---| |--- AND M0            TT chạy dừng
  397 ---|/|--- ANI M4            Báo lỗi
  398 ---|/|--- ANI M1            Đang đo
  399 ---| |--- AND M111            Jog chiều âm từ PC (D111=1)
  400 [MOV K120 -> D122]
  405 ---[ LD= D101 K0 ]---  Chế độ đo
  410 ---| |--- AND M0            TT chạy dừng
  411 ---|/|--- ANI M4            Báo lỗi
  412 ---|/|--- ANI M1            Đang đo
  413 ---| |--- AND M112            Lệnh Home/về gốc từ PC (D112=1)
  414 [MOV K130 -> D122]
  419 ---|P|--- LDP M112            Lệnh Home/về gốc từ PC (D112=1)
  421 ---[ AND= D101 K0 ]---  Chế độ đo
  426 [MOV K0 -> D124]
  431 [MOV K0 -> D125]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| D101 | Chế độ đo |
| M0 | TT chạy dừng |
| M4 | Báo lỗi |
| M1 | Đang đo |
| M110 | Jog chiều dương từ PC (D110=1) |
| M111 | Jog chiều âm từ PC (D111=1) |
| M112 | Lệnh Home/về gốc từ PC (D112=1) |
| D122 | Bước chạy |
| D124 | Góc hiện tại |
| D125 | Góc đích |

### Giải thích:
- LD= D101 K0: kiểm tra D101 (Chế độ đo) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- AND M0: dùng TT chạy dừng làm điều kiện logic.
- ANI M4: dùng Báo lỗi làm điều kiện logic.
- ANI M1: dùng Đang đo làm điều kiện logic.
- ANI M110: dùng Jog chiều dương từ PC (D110=1) làm điều kiện logic.
- ANI M111: dùng Jog chiều âm từ PC (D111=1) làm điều kiện logic.
- ANI M112: dùng Lệnh Home/về gốc từ PC (D112=1) làm điều kiện logic.
- MOV K100 D122: ghi/copy giá trị K100 vào D122 (Bước chạy).
- AND M110: dùng Jog chiều dương từ PC (D110=1) làm điều kiện logic.
- MOV K110 D122: ghi/copy giá trị K110 vào D122 (Bước chạy).
- AND M111: dùng Jog chiều âm từ PC (D111=1) làm điều kiện logic.
- MOV K120 D122: ghi/copy giá trị K120 vào D122 (Bước chạy).
- AND M112: dùng Lệnh Home/về gốc từ PC (D112=1) làm điều kiện logic.
- MOV K130 D122: ghi/copy giá trị K130 vào D122 (Bước chạy).
- LDP M112: dùng Lệnh Home/về gốc từ PC (D112=1) làm điều kiện logic.
- AND= D101 K0: kiểm tra D101 (Chế độ đo) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- MOV K0 D124: ghi/copy giá trị K0 vào D124 (Góc hiện tại).
- MOV K0 D125: ghi/copy giá trị K0 vào D125 (Góc đích).

---

## PHẦN 15: 10.0 Clear calculations when not testing

```text
Dòng/Step 436 - 447: Xóa các thanh ghi tính toán khi không test.
```

### Sơ đồ Ladder:
```text
  436 ---|/|--- LDI M1            Đang đo
  437 [MOV K0 -> D160]
  442 [MOV K0 -> D161]
  447 [MOV K0 -> D164]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D160 | Sai goc |
| D161 | ABS goc |
| D164 | So xung L |

### Giải thích:
- LDI M1: dùng Đang đo làm điều kiện logic.
- MOV K0 D160: ghi/copy giá trị K0 vào D160 (Sai goc).
- MOV K0 D161: ghi/copy giá trị K0 vào D161 (ABS goc).
- MOV K0 D164: ghi/copy giá trị K0 vào D164 (So xung L).

---

## PHẦN 16: 10 Tinh sai lech goc va so xung can phat

```text
Dòng/Step 452 - 596: Tính sai lệch góc, số xung cần phát và chiều servo.
```

### Sơ đồ Ladder:
```text
  452 ---| |--- LD M1            Đang đo
  453 [SUB D125 -> D124 -> D160]
  460 ---| |--- LD M1            Đang đo
  461 ---[ AND> D160 K0 ]---  Sai goc
  466 -----------------------------(RST Y004)  Chiều servo
  467 ---| |--- LD M1            Đang đo
  468 ---[ AND< D160 K0 ]---  Sai goc
  473 -----------------------------(SET Y004)  Chiều servo
  474 ---[ LD> D160 K0 ]---  Sai goc
  479 [MOV D160 -> D161]
  484 ---[ LD< D160 K0 ]---  Sai goc
  489 [MOV D160 -> D161]
  494 [NEG D161]
  497 [MUL D161 -> K50 -> D162]
  504 [DDIV D162 -> K9 -> D164]
  517 ---| |--- LD M110            Jog chiều dương từ PC (D110=1)
  518 ---[ AND= D101 K0 ]---  Chế độ đo
  523 ---| |--- AND M0            TT chạy dừng
  524 ---|/|--- ANI M1            Đang đo
  525 ---|/|--- ANI M4            Báo lỗi
  526 [MUL D104 -> K1 -> D150]
  533 ---| |--- LD M111            Jog chiều âm từ PC (D111=1)
  534 ---[ AND= D101 K0 ]---  Chế độ đo
  539 ---| |--- AND M0            TT chạy dừng
  540 ---|/|--- ANI M1            Đang đo
  541 ---|/|--- ANI M4            Báo lỗi
  542 [MUL D104 -> K-1 -> D150]
  549 ---[ LD= D101 K0 ]---  Chế độ đo
  554 ---| |--- AND M0            TT chạy dừng
  555 ---|/|--- ANI M1            Đang đo
  556 ---|/|--- ANI M4            Báo lỗi
  557 ---|/|--- ANI M110            Jog chiều dương từ PC (D110=1)
  558 ---|/|--- ANI M111            Jog chiều âm từ PC (D111=1)
  559 [DMOV K0 -> D150]
  568 ---| |--- LD M110            Jog chiều dương từ PC (D110=1)
  569 ---| |--- OR M111            Jog chiều âm từ PC (D111=1)
  570 ---[ AND= D101 K0 ]---  Chế độ đo
  575 ---| |--- AND M0            TT chạy dừng
  576 ---|/|--- ANI M1            Đang đo
  577 ---| |--- AND Y005            Bật Servo ON
  578 ---|/|--- ANI M4            Báo lỗi
  579 [DPLSV D150 -> Y000 -> Y004]
  592 ---| |--- LD M1            Đang đo
  593 ---| |--- AND M20            Bắt ghi
  594 ---| |--- AND Y005            Bật Servo ON
  595 ---|/|--- ANI M4            Báo lỗi
  596 [PLSY D104 -> D164 -> Y000]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D125 | Góc đích |
| D124 | Góc hiện tại |
| D160 | Sai goc |
| Y004 | Chiều servo |
| D161 | ABS goc |
| D162 | Xung tinh L |
| D164 | So xung L |
| M110 | Jog chiều dương từ PC (D110=1) |
| D101 | Chế độ đo |
| M0 | TT chạy dừng |
| M4 | Báo lỗi |
| D104 | Tốc độ x100 |
| D150 | Xung + L |
| M111 | Jog chiều âm từ PC (D111=1) |
| Y005 | Bật Servo ON |
| Y000 | Xung servo |
| M20 | Bắt ghi |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- SUB D125 D124 D160: phép tính phục vụ tính góc/xung/chuyển bước.
- AND> D160 K0: kiểm tra D160 (Sai goc) lớn hơn K0; đúng thì cho phép nhánh logic tiếp tục.
- RST Y004: tác động lên Y004 - Chiều servo.
- AND< D160 K0: kiểm tra D160 (Sai goc) nhỏ hơn K0; đúng thì cho phép nhánh logic tiếp tục.
- SET Y004: tác động lên Y004 - Chiều servo.
- LD> D160 K0: kiểm tra D160 (Sai goc) lớn hơn K0; đúng thì cho phép nhánh logic tiếp tục.
- MOV D160 D161: ghi/copy giá trị D160 vào D161 (ABS goc).
- LD< D160 K0: kiểm tra D160 (Sai goc) nhỏ hơn K0; đúng thì cho phép nhánh logic tiếp tục.
- NEG D161: đổi dấu giá trị trong D161 (ABS goc).
- MUL D161 K50 D162: phép tính phục vụ tính góc/xung/chuyển bước.
- DDIV D162 K9 D164: phép tính phục vụ tính góc/xung/chuyển bước.
- LD M110: dùng Jog chiều dương từ PC (D110=1) làm điều kiện logic.
- AND= D101 K0: kiểm tra D101 (Chế độ đo) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- AND M0: dùng TT chạy dừng làm điều kiện logic.
- ANI M1: dùng Đang đo làm điều kiện logic.
- ANI M4: dùng Báo lỗi làm điều kiện logic.
- MUL D104 K1 D150: phép tính phục vụ tính góc/xung/chuyển bước.
- LD M111: dùng Jog chiều âm từ PC (D111=1) làm điều kiện logic.
- MUL D104 K-1 D150: phép tính phục vụ tính góc/xung/chuyển bước.
- LD= D101 K0: kiểm tra D101 (Chế độ đo) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- ANI M110: dùng Jog chiều dương từ PC (D110=1) làm điều kiện logic.
- ANI M111: dùng Jog chiều âm từ PC (D111=1) làm điều kiện logic.
- DMOV K0 D150: ghi/copy giá trị K0 vào D150 (Xung + L).
- OR M111: dùng Jog chiều âm từ PC (D111=1) làm điều kiện logic.
- AND Y005: dùng Bật Servo ON làm điều kiện logic.
- DPLSV D150 Y000 Y004: phát xung servo theo tốc độ/số xung và ngõ ra chỉ định.
- AND M20: dùng Bắt ghi làm điều kiện logic.
- PLSY D104 D164 Y000: phát xung servo theo tốc độ/số xung và ngõ ra chỉ định.

---

## PHẦN 17: 10.1 Cap nhat goc hien thi signed theo xung

```text
Dòng/Step 603 - 667: Cập nhật góc hiện tại từ xung phát/encoder để PC hiển thị.
```

### Sơ đồ Ladder:
```text
  603 ---| |--- LD M1            Đang đo
  604 ---| |--- AND M20            Bắt ghi
  605 [DSUB D8140 -> D170 -> D174]
  618 ---| |--- LD M1            Đang đo
  619 ---| |--- AND M20            Bắt ghi
  620 [DMUL D174 -> K9 -> D176]
  633 [DDIV D176 -> K50 -> D182]
  646 ---| |--- LD M1            Đang đo
  647 ---| |--- AND M20            Bắt ghi
  648 ---[ AND>= D125 D172 ]---  Góc đích
  653 [ADD D172 -> D182 -> D124]
  660 ---| |--- LD M1            Đang đo
  661 ---| |--- AND M20            Bắt ghi
  662 ---[ AND< D125 D172 ]---  Góc đích
  667 [SUB D172 -> D182 -> D124]
```

### Ghi chú trong MAIN.csv:
- D124 khong nhay target; tang/giam theo delta pulse tu D8140

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| M20 | Bắt ghi |
| D8140 | Thanh ghi xung hiện tại PLC/servo |
| D170 | Xung phát L |
| D174 | Xung phát H |
| D176 | Delta xung L |
| D182 | Góc dịch chuyển |
| D125 | Góc đích |
| D172 | Góc xuất phát |
| D124 | Góc hiện tại |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- AND M20: dùng Bắt ghi làm điều kiện logic.
- DSUB D8140 D170 D174: phép tính phục vụ tính góc/xung/chuyển bước.
- DMUL D174 K9 D176: phép tính phục vụ tính góc/xung/chuyển bước.
- DDIV D176 K50 D182: phép tính phục vụ tính góc/xung/chuyển bước.
- AND>= D125 D172: kiểm tra D125 (Góc đích) lớn hơn hoặc bằng D172; đúng thì cho phép nhánh logic tiếp tục.
- ADD D172 D182 D124: phép tính phục vụ tính góc/xung/chuyển bước.
- AND< D125 D172: kiểm tra D125 (Góc đích) nhỏ hơn D172; đúng thì cho phép nhánh logic tiếp tục.
- SUB D172 D182 D124: phép tính phục vụ tính góc/xung/chuyển bước.

---

## PHẦN 18: 10.2 Advance chung: + -> 0 -> - -> 0

```text
Step 674: Chuyển bước khi đã tới target.
```

### Sơ đồ Ladder:
```text

```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |

### Giải thích:

---

## PHẦN 19: 10.3 Neu step4 ve 0 xong va chua du 3 chu ky

```text
Dòng/Step 674 - 721: Tăng cycle và quay lại step 1 khi chưa đủ số chu kỳ.
```

### Sơ đồ Ladder:
```text
  674 ---| |--- LD M1            Đang đo
  675 ---[ AND<= D161 K5 ]---  ABS goc
  680 ---[ AND= D125 K0 ]---  Góc đích
  685 ---[ AND= D130 K4 ]---  Mẫu hợp lệ
  690 ---[ AND< D180 D105 ]---  Lưu tạm xung
  695 [MOV D125 -> D124]
  700 [ADD D180 -> K1 -> D180]
  707 [DMOV D8140 -> D170]
  716 [MOV D124 -> D172]
  721 [MOV K1 -> D130]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D161 | ABS goc |
| D125 | Góc đích |
| D130 | Mẫu hợp lệ |
| D180 | Lưu tạm xung |
| D105 | Số chu kỳ |
| D124 | Góc hiện tại |
| D8140 | Thanh ghi xung hiện tại PLC/servo |
| D170 | Xung phát L |
| D172 | Góc xuất phát |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- AND<= D161 K5: kiểm tra D161 (ABS goc) nhỏ hơn hoặc bằng K5; đúng thì cho phép nhánh logic tiếp tục.
- AND= D125 K0: kiểm tra D125 (Góc đích) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- AND= D130 K4: kiểm tra D130 (Mẫu hợp lệ) bằng K4; đúng thì cho phép nhánh logic tiếp tục.
- AND< D180 D105: kiểm tra D180 (Lưu tạm xung) nhỏ hơn D105; đúng thì cho phép nhánh logic tiếp tục.
- MOV D125 D124: ghi/copy giá trị D125 vào D124 (Góc hiện tại).
- ADD D180 K1 D180: phép tính phục vụ tính góc/xung/chuyển bước.
- DMOV D8140 D170: ghi/copy giá trị D8140 vào D170 (Xung phát L).
- MOV D124 D172: ghi/copy giá trị D124 vào D172 (Góc xuất phát).
- MOV K1 D130: ghi/copy giá trị K1 vào D130 (Mẫu hợp lệ).

---

## PHẦN 20: 10.4 Neu step4 ve 0 xong va du 3 chu ky thi ket thuc

```text
Dòng/Step 726 - 750: Kết thúc test khi đủ số chu kỳ.
```

### Sơ đồ Ladder:
```text
  726 ---| |--- LD M1            Đang đo
  727 ---[ AND<= D161 K5 ]---  ABS goc
  732 ---[ AND= D125 K0 ]---  Góc đích
  737 ---[ AND= D130 K4 ]---  Mẫu hợp lệ
  742 ---[ AND>= D180 D105 ]---  Lưu tạm xung
  747 -----------------------------(RST M1)  Đang đo
  748 -----------------------------(RST M2)  Cho ghi data
  749 -----------------------------(SET M3)  Hoàn tất
  750 [MOV K0 -> D122]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D161 | ABS goc |
| D125 | Góc đích |
| D130 | Mẫu hợp lệ |
| D180 | Lưu tạm xung |
| D105 | Số chu kỳ |
| M2 | Cho ghi data |
| M3 | Hoàn tất |
| D122 | Bước chạy |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- AND<= D161 K5: kiểm tra D161 (ABS goc) nhỏ hơn hoặc bằng K5; đúng thì cho phép nhánh logic tiếp tục.
- AND= D125 K0: kiểm tra D125 (Góc đích) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- AND= D130 K4: kiểm tra D130 (Mẫu hợp lệ) bằng K4; đúng thì cho phép nhánh logic tiếp tục.
- AND>= D180 D105: kiểm tra D180 (Lưu tạm xung) lớn hơn hoặc bằng D105; đúng thì cho phép nhánh logic tiếp tục.
- RST M1: tác động lên M1 - Đang đo.
- RST M2: tác động lên M2 - Cho ghi data.
- SET M3: tác động lên M3 - Hoàn tất.
- MOV K0 D122: ghi/copy giá trị K0 vào D122 (Bước chạy).

---

## PHẦN 21: 10.5 Step3 -36 xong -> ve 0

```text
Dòng/Step 755 - 790: Từ góc âm về 0.
```

### Sơ đồ Ladder:
```text
  755 ---| |--- LD M1            Đang đo
  756 ---[ AND<= D161 K5 ]---  ABS goc
  761 ---[ AND< D125 K0 ]---  Góc đích
  766 ---[ AND= D130 K3 ]---  Mẫu hợp lệ
  771 [MOV D125 -> D124]
  776 [DMOV D8140 -> D170]
  785 [MOV D124 -> D172]
  790 [MOV K4 -> D130]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D161 | ABS goc |
| D125 | Góc đích |
| D130 | Mẫu hợp lệ |
| D124 | Góc hiện tại |
| D8140 | Thanh ghi xung hiện tại PLC/servo |
| D170 | Xung phát L |
| D172 | Góc xuất phát |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- AND<= D161 K5: kiểm tra D161 (ABS goc) nhỏ hơn hoặc bằng K5; đúng thì cho phép nhánh logic tiếp tục.
- AND< D125 K0: kiểm tra D125 (Góc đích) nhỏ hơn K0; đúng thì cho phép nhánh logic tiếp tục.
- AND= D130 K3: kiểm tra D130 (Mẫu hợp lệ) bằng K3; đúng thì cho phép nhánh logic tiếp tục.
- MOV D125 D124: ghi/copy giá trị D125 vào D124 (Góc hiện tại).
- DMOV D8140 D170: ghi/copy giá trị D8140 vào D170 (Xung phát L).
- MOV D124 D172: ghi/copy giá trị D124 vào D172 (Góc xuất phát).
- MOV K4 D130: ghi/copy giá trị K4 vào D130 (Mẫu hợp lệ).

---

## PHẦN 22: 10.6 Step2 0 xong -> xuong -36

```text
Dòng/Step 795 - 830: Từ 0 chuyển sang góc âm.
```

### Sơ đồ Ladder:
```text
  795 ---| |--- LD M1            Đang đo
  796 ---[ AND<= D161 K5 ]---  ABS goc
  801 ---[ AND= D125 K0 ]---  Góc đích
  806 ---[ AND= D130 K2 ]---  Mẫu hợp lệ
  811 [MOV D125 -> D124]
  816 [DMOV D8140 -> D170]
  825 [MOV D124 -> D172]
  830 [MOV K3 -> D130]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D161 | ABS goc |
| D125 | Góc đích |
| D130 | Mẫu hợp lệ |
| D124 | Góc hiện tại |
| D8140 | Thanh ghi xung hiện tại PLC/servo |
| D170 | Xung phát L |
| D172 | Góc xuất phát |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- AND<= D161 K5: kiểm tra D161 (ABS goc) nhỏ hơn hoặc bằng K5; đúng thì cho phép nhánh logic tiếp tục.
- AND= D125 K0: kiểm tra D125 (Góc đích) bằng K0; đúng thì cho phép nhánh logic tiếp tục.
- AND= D130 K2: kiểm tra D130 (Mẫu hợp lệ) bằng K2; đúng thì cho phép nhánh logic tiếp tục.
- MOV D125 D124: ghi/copy giá trị D125 vào D124 (Góc hiện tại).
- DMOV D8140 D170: ghi/copy giá trị D8140 vào D170 (Xung phát L).
- MOV D124 D172: ghi/copy giá trị D124 vào D172 (Góc xuất phát).
- MOV K3 D130: ghi/copy giá trị K3 vào D130 (Mẫu hợp lệ).

---

## PHẦN 23: 10.7 Step1 +36 xong -> ve 0

```text
Dòng/Step 835 - 870: Từ góc dương về 0.
```

### Sơ đồ Ladder:
```text
  835 ---| |--- LD M1            Đang đo
  836 ---[ AND<= D161 K5 ]---  ABS goc
  841 ---[ AND> D125 K0 ]---  Góc đích
  846 ---[ AND= D130 K1 ]---  Mẫu hợp lệ
  851 [MOV D125 -> D124]
  856 [DMOV D8140 -> D170]
  865 [MOV D124 -> D172]
  870 [MOV K2 -> D130]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D161 | ABS goc |
| D125 | Góc đích |
| D130 | Mẫu hợp lệ |
| D124 | Góc hiện tại |
| D8140 | Thanh ghi xung hiện tại PLC/servo |
| D170 | Xung phát L |
| D172 | Góc xuất phát |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- AND<= D161 K5: kiểm tra D161 (ABS goc) nhỏ hơn hoặc bằng K5; đúng thì cho phép nhánh logic tiếp tục.
- AND> D125 K0: kiểm tra D125 (Góc đích) lớn hơn K0; đúng thì cho phép nhánh logic tiếp tục.
- AND= D130 K1: kiểm tra D130 (Mẫu hợp lệ) bằng K1; đúng thì cho phép nhánh logic tiếp tục.
- MOV D125 D124: ghi/copy giá trị D125 vào D124 (Góc hiện tại).
- DMOV D8140 D170: ghi/copy giá trị D8140 vào D170 (Xung phát L).
- MOV D124 D172: ghi/copy giá trị D124 vào D172 (Góc xuất phát).
- MOV K2 D130: ghi/copy giá trị K2 vào D130 (Mẫu hợp lệ).

---

## PHẦN 24: 10.8 Cap nhat current cycle status

```text
Dòng/Step 875 - 876: Cập nhật chu kỳ hiện tại.
```

### Sơ đồ Ladder:
```text
  875 ---| |--- LD M1            Đang đo
  876 [MOV D180 -> D123]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M1 | Đang đo |
| D180 | Lưu tạm xung |
| D123 | Chu kỳ HT |

### Giải thích:
- LD M1: dùng Đang đo làm điều kiện logic.
- MOV D180 D123: ghi/copy giá trị D180 vào D123 (Chu kỳ HT).

---

## PHẦN 25: 11 Clear Done command from PC

```text
Dòng/Step 881 - 882: PC xóa cờ DONE.
```

### Sơ đồ Ladder:
```text
  881 ---| |--- LD M107            PC xóa DONE
  882 -----------------------------(RST M3)  Hoàn tất
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M107 | PC xóa DONE |
| M3 | Hoàn tất |

### Giải thích:
- LD M107: dùng PC xóa DONE làm điều kiện logic.
- RST M3: tác động lên M3 - Hoàn tất.

---

## PHẦN 26: 12 Reset D100 command word at scan end

```text
Dòng/Step 883 - 889: Reset word lệnh PC cuối scan.
```

### Sơ đồ Ladder:
```text
  883 ---| |--- LD M8000            PLC RUN
  884 [MOV K0 -> D100]
  889 [END ]
```

### Thanh ghi / thiết bị liên quan:

| Device | Ý nghĩa trong cụm |
| --- | --- |
| M8000 | PLC RUN |
| D100 | Word lệnh PC |

### Giải thích:
- LD M8000: dùng PLC RUN làm điều kiện logic.
- MOV K0 D100: ghi/copy giá trị K0 vào D100 (Word lệnh PC).
- END: kết thúc chương trình, lặp lại từ đầu.

---
