from pathlib import Path

comments_user = [
    ("X000", "Nút     START"),
    ("X001", "Nút     STOP"),
    ("X002", "Nút 1   an toàn"),
    ("X003", "Nút 2   an toàn"),
    ("X004", "Nút dừng khẩn"),  # Nút khẩn cấp vật lý mới thêm
    ("Y000", "Xung    servo"),
    ("Y004", "Chiều   servo"),
    ("Y005", "Bật     Servo ON"),
    ("Y006", "Xi lanh kẹp nhả"),
    ("Y007", "Đèn xanh"),
    ("Y010", "Đèn vàng"),
    ("Y011", "Đèn đỏ"),
    ("M0", "TT chạy dừng"),
    ("M1", "Đang    đo"),
    ("M2", "Cho ghi data"),
    ("M3", "Hoàn tất"),
    ("M4", "Báo lỗi"),
    ("M10", "Nhớ TT XL"),
    ("M11", "Hai nút OK"),
    ("M12", "Xung 2 nút"),
    ("M13", "PC kẹp nhả"),
    ("M20", "Bắt ghi"),
    ("M21", "Dừng ghi"),
    ("M30", "SV đang chạy"),
    ("M31", "SV chạy xong"),
    ("M32", "SV chiều +"),
    ("M33", "SV chiều -"),
    ("M100", "PC      START D100.0"),
    ("M101", "PC      STOP D100.1"),
    ("M102", "PC bắt đo"),
    ("M103", "PC      dừng đo"),
    ("M104", "PC      kẹp nhả"),
    ("M105", "PC      bật servo"),
    ("M106", "Dừng    khẩn"),
    ("M107", "PC      xóa DONE"),
    ("M8000", "PLC RUN"),
    ("D100", "Word    lệnh PC"),
    ("D101", "Chế độ đo"),
    ("D102", "Góc     dương x100"),
    ("D103", "Góc âm  x100"),
    ("D104", "Tốc độ  x100"),
    ("D105", "Số chu kỳ"),
    ("D106", "Vùng    lấy mẫu"),
    ("D107", "Chọn    loại SP"),
    ("D108", "Loại    đo momen"),
    ("D109", "Reset   lỗi PC"),
    ("D110", "Jog     chiều dương"),
    ("D111", "Jog     chiều âm"),
    ("D112", "Lệnh    về gốc"),
    ("D120", "TT PC"),
    ("D121", "Mode HT"),
    ("D122", "Bước chạy"),
    ("D123", "Chu kỳ HT"),
    ("D124", "Góc     hiện tại"),
    ("D125", "Góc     đích"),
    ("D126", "Tốc độ HT"),
    ("D127", "VT servo L"),
    ("D128", "VT servo H"),
    ("D129", "Mã lỗi  PLC"),
    ("D130", "Mẫu hợp lệ"),
    ("D131", "Cho ghi mẫu"),
    ("D132", "TT xi lanh"),
    ("D133", "TT Servo"),
    ("D134", "TT Done"),
    ("D135", "Số mẫu"),
    ("D150", "Xung + L"),
    ("D151", "Xung + H"),
    ("D152", "Xung - L"),
    ("D153", "Xung - H"),
    ("D154", "Tốc xung L"),
    ("D155", "Tốc xung H"),
    ("D156", "Góc min OK"),
    ("D157", "Góc max OK"),
    ("D158", "TG bước"),
    ("D162", "Xung tinh L"),
    ("D163", "Xung tinh H"),
    ("D160", "Sai goc"),
    ("D164", "So xung L"),
    ("D161", "ABS goc"),
    ("D165", "So xung H"),
    ("D170", "Xung phát L"),
    ("D172", "Góc xuất phát"),
    ("D174", "Xung phát H"),
    ("D176", "Delta xung L"),
    ("D180", "Lưu tạm xung"),
    ("D182", "Góc dịch chuyển"),
    ("D8400", "115200  8N1"),
    ("D8401", "Modbus  Slave   RTU"),
    ("D8411", "Delay   5 ms"),
    ("D8414", "Slave   ID bằng 2"),
    ("D8415", "Lưu D"),
    ("D8416", "Từ D200")
]

# Thêm X004 nếu thiếu trong danh sách user gửi
has_x004 = any(x[0] == "X004" for x in comments_user)
if not has_x004:
    comments_user.append(("X004", "Nút dừng khẩn cấp EMG (Vat ly)"))

def generate_exact_comment_csv():
    output_path = Path(r"d:\DuAn\18.Other\plot_draw\plot_ZE-SG3\plc_ctrvina\COMMENT.csv")
    
    lines = [
        '"test1"',
        '"Device Name"\t"Comment"'
    ]
    
    # Giữ nguyên thứ tự và format
    for device, comment in comments_user:
        lines.append(f'"{device}"\t"{comment}"')
        
    content = "\r\n".join(lines) + "\r\n"
    with output_path.open('w', encoding='utf-16', newline='') as f:
        f.write(content)
    print("Exact COMMENT.csv generated successfully!")

if __name__ == '__main__':
    generate_exact_comment_csv()

