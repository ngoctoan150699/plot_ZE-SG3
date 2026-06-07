import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

# Ensure start command resets current/target angle to zero before saving start snapshot.
anchor = '""\t"06.1 Luu moc xung/goc auto"\t""\t""\t""\t""\t""'
if any('06.0 Reset goc khi bat dau do' in l for l in lines):
    print("Start reset angle block already exists")
else:
    idx = next((i for i, l in enumerate(lines) if l == anchor), -1)
    if idx < 0:
        raise SystemExit("Không tìm thấy anchor 06.1")
    block = [
        '""\t"06.0 Reset goc khi bat dau do"\t""\t""\t""\t""\t""',
        '""\t""\t"MOV"\t"K0"\t""\t""\t""',
        '""\t""\t""\t"D124"\t""\t""\t""',
        '""\t""\t"MOV"\t"K0"\t""\t""\t""',
        '""\t""\t""\t"D125"\t""\t""\t""',
    ]
    lines = lines[:idx] + block + lines[idx:]
    print(f"Inserted start angle reset at row {idx + 1}")

# Home already resets D124/D125, keep as-is.
with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
