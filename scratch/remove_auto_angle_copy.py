import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

target = [
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"D125"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
]
replacement = [
    '""\t"10.1 Khong copy target sang goc hien tai"\t""\t""\t""\t""\t""',
    '""\t"D124 giu goc hien tai tra ve app; chi HOME moi reset ve 0"\t""\t""\t""\t""\t""',
]

found = False
for i in range(len(lines) - len(target) + 1):
    if lines[i:i + len(target)] == target:
        lines = lines[:i] + replacement + lines[i + len(target):]
        found = True
        print(f"Removed auto MOV D125 -> D124 at line {i + 1}")
        break

if not found:
    raise SystemExit("Target auto angle copy block not found")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
