import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

bad_block = [
    '""\t""\t"LD<"\t"D174"\t""\t""\t""',
    '""\t""\t""\t"K0"\t""\t""\t""',
    '""\t""\t"DNEG"\t"D174"\t""\t""\t""',
    '""\t""\t""\t"D174"\t""\t""\t""',
]

for i in range(len(lines) - len(bad_block) + 1):
    if lines[i:i + len(bad_block)] == bad_block:
        del lines[i:i + len(bad_block)]
        print(f"Removed invalid DNEG block at row {i + 1}")
        break
else:
    print("DNEG block not found; no CSV change")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
