import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

# Trong block 6.0..6.2, không dùng LD M1 vì M1 ON suốt khi đang đo.
# Nếu dùng LD M1, D170/D172 bị cập nhật liên tục mỗi scan nên delta pulse luôn gần 0,
# làm D124 không thay đổi. Dùng LDP M102 để chỉ init đúng 1 scan lúc bắt đầu đo.
inside = False
changed = 0
for i, line in enumerate(lines):
    if '06.0 Reset goc khi bat dau do' in line:
        inside = True
        continue
    if inside and '07 Lenh dung do' in line:
        inside = False
        continue
    if inside and line == '""\t""\t"LD"\t"M1"\t""\t""\t""':
        lines[i] = '""\t""\t"LDP"\t"M102"\t""\t""\t""'
        changed += 1

if changed == 0:
    raise SystemExit("Không tìm thấy LD M1 trong block 6.0..6.2")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print(f"Replaced {changed} LD M1 entries with LDP M102 in 6.0..6.2")
print("MAIN.csv updated")
