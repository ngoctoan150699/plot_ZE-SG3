from pathlib import Path

# Dictionary of device comments (Vietnamese without accents to ensure perfect compatibility in GX Works2)
comments = {
    # Inputs
    "X000": "Nut nhan START (Vat ly)",
    "X001": "Nut nhan STOP (Vat ly)",
    "X002": "Nut nhan an toan 1 (Vat ly)",
    "X003": "Nut nhan an toan 2 (Vat ly)",
    "X004": "Nut dung khan cap EMG (Vat ly)",
    
    # Outputs
    "Y000": "Chan phat xung Servo (PLS)",
    "Y004": "Chan huong quay Servo (DIR)",
    "Y005": "Chan kick hoat Servo ON",
    "Y006": "Van dien tu kep xi lanh",
    "Y007": "Den bao xanh la (System RUN)",
    "Y010": "Den bao vang (Manual JOG)",
    "Y011": "Den bao do (System Fault)",
    
    # Internal Bits (M)
    "M0": "Trang thai RUN/STOP he thong (1=RUN)",
    "M1": "Trang thai chu ky do dang chay (1=Do)",
    "M2": "Cho phep ghi du lieu (1=Record)",
    "M3": "Hoan tat chu ky do (Done)",
    "M4": "Trang thai bao loi he thong (Fault)",
    "M10": "Trang thai xi lanh (1=Kep, 0=Nha)",
    "M11": "Dieu kien ca 2 nut an toan deu ON",
    
    # PC Command Bits (from D100)
    "M100": "Lenh RUN tu PC (D100.b0)",
    "M101": "Lenh STOP tu PC (D100.b1)",
    "M102": "Lenh START RECORD tu PC (D100.b2)",
    "M103": "Lenh STOP RECORD tu PC (D100.b3)",
    "M104": "Lenh TOGGLE CYLINDER tu PC (D100.b4)",
    "M105": "Lenh SERVO ON tu PC (D100.b5)",
    "M106": "Lenh ABORT chu ky tu PC (D100.b6)",
    "M107": "Lenh CLEAR DONE tu PC (D100.b7)",
    
    # Manual Command Bits (from D110-D112)
    "M110": "Lenh JOG PLUS tu PC (D110.b0)",
    "M111": "Lenh JOG MINUS tu PC (D111.b0)",
    "M112": "Lenh HOME tu PC (D112.b0)",
    
    # Special Bits
    "M8000": "Tiep diem luon dong (Always ON)",
    "M8411": "Co truyen thong Modbus Kenh 1",
    
    # Data Registers (D)
    "D100": "Word lenh dieu khien tu PC (CMD_WORD)",
    "D101": "Che do do (0=Manual, 1=Breakaway, 2=Operating)",
    "D102": "Goc dich duong (x100 do, VD: 3600 = 36.00 deg)",
    "D103": "Goc dich am (x100 do, VD: -3600 = -36.00 deg)",
    "D104": "Toc do phat xung (x100 deg/s hoac pulse/s)",
    "D105": "So chu ky do thiet lap (Operating cycles)",
    "D110": "Nhan lenh JOG+ tu PC",
    "D111": "Nhan lenh JOG- tu PC",
    "D112": "Nhan lenh HOME tu PC",
    
    "D120": "Word trang thai he thong gui PC (STATUS_WORD)",
    "D121": "Che do do hien tai (Current Mode)",
    "D122": "Phase hoat dong hien tai (Current Phase)",
    "D123": "Chu ky do hien tai (Current Cycle)",
    "D124": "Goc quay hien tai (x100 do, gui PC)",
    "D125": "Goc dich hien tai cua PLC (x100 do)",
    "D130": "Co du lieu hop le (1=Data Valid)",
    "D131": "Co cho phep PC ghi mau (1=Record Enable)",
    "D132": "Trang thai kep xi lanh gui PC (1=Kep, 0=Nha)",
    "D133": "Trang thai Servo ON gui PC (1=ON, 0=OFF)",
    "D134": "Co hoan tat chu ky do gui PC (1=Done)",
    
    "D150": "Toc do Jog manual (tốc độ xung cua DPLSV)",
    "D160": "Sai lech goc thuc te (D125 - D124)",
    "D161": "Tri tuyet doi sai lech goc (ABS D160)",
    "D162": "So xung trung gian sau nhan he so",
    "D164": "So xung can phat cho servo (PLSY pulse)",
    
    "D170": "So xung phat ra hien tai word thap (D8140)",
    "D172": "Goc xuat phat cua phase hien tai (x100 do)",
    "D174": "Hieu so xung phat ra (Delta pulse)",
    "D176": "So xung trung gian nhan he so goc",
    "D180": "So xung phat ra hien tai luu tam",
    "D182": "Goc dich chuyen thuc te tinh theo xung (x100 do)",
    
    # Special Registers
    "D8140": "Bo dem xung phat ra ngo Y000 (FX3U)",
    "D8400": "Cau hinh dinh dang Modbus RTU",
    "D8401": "Cau hinh Modbus Slave RTU",
    "D8411": "Cau hinh thoi gian tre Modbus (ms)",
    "D8414": "Cau hinh dia chi Slave ID (ID=2)",
    "D8415": "Cho phep truy cap thanh ghi D Modbus",
    "D8416": "Dia chi D bat dau Modbus (D100)"
}

def write_comment_csv():
    output_path = Path(r"d:\DuAn\18.Other\plot_draw\plot_ZE-SG3\plc_ctrvina\COMMENT.csv")
    
    # Headers of GX Works2 Comment CSV
    lines = [
        '"test1"',
        '"Device Name"\t"Comment"'
    ]
    
    for device, comment in sorted(comments.items()):
        lines.append(f'"{device}"\t"{comment}"')
        
    content = "\r\n".join(lines) + "\r\n"
    output_path.write_text(content, encoding='utf-16')
    print("New COMMENT.csv generated successfully!")

if __name__ == '__main__':
    write_comment_csv()
