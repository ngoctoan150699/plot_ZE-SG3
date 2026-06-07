import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

old = [
    '""\t"06.0 Reset goc khi bat dau do"\t""\t""\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
    '""\t"06.1 Luu moc xung/goc auto"\t""\t""\t""\t""\t""',
    '""\t""\t"DMOV"\t"D8140"\t""\t""\t""',
    '""\t""\t""\t"D170"\t""\t""\t""',
    '""\t""\t"MOV"\t"D124"\t""\t""\t""',
    '""\t""\t""\t"D172"\t""\t""\t""',
    '""\t"06.2 Init operating cycle counter"\t""\t""\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D131"\t""\t""\t""',
]
new = [
    '""\t"06.0 Reset goc khi bat dau do"\t""\t""\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
    '""\t"06.1 Luu moc xung/goc auto"\t""\t""\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"DMOV"\t"D8140"\t""\t""\t""',
    '""\t""\t""\t"D170"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"D124"\t""\t""\t""',
    '""\t""\t""\t"D172"\t""\t""\t""',
    '""\t"06.2 Init operating cycle counter"\t""\t""\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D131"\t""\t""\t""',
]

for i in range(len(lines) - len(old) + 1):
    if lines[i:i + len(old)] == old:
        lines = lines[:i] + new + lines[i + len(old):]
        print(f"Added LD M1 before 6.0..6.2 commands at row {i + 1}")
        break
else:
    raise SystemExit("Không tìm thấy block 6.0..6.2 cần sửa")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
