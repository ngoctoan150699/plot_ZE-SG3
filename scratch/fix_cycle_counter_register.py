import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

changed = 0
inside_cycle_init = False
inside_cycle_block = False
for i, line in enumerate(lines):
    if '06.2 Init operating cycle counter' in line:
        inside_cycle_init = True
    elif inside_cycle_init and '07 Lenh dung do' in line:
        inside_cycle_init = False

    if '10.3 Lap operating 3 chu ky' in line:
        inside_cycle_block = True
    elif inside_cycle_block and '"END"' in line:
        inside_cycle_block = False

    if (inside_cycle_init or inside_cycle_block) and '"D131"' in line:
        lines[i] = line.replace('"D131"', '"D180"')
        changed += 1

# Keep D123 current-cycle status in sync with D180 while running.
# Insert before END if not already present.
if not any('10.4 Cap nhat current cycle status' in l for l in lines):
    end_idx = next(i for i, l in enumerate(lines) if '"END"' in l)
    block = [
        '""\t"10.4 Cap nhat current cycle status"\t""\t""\t""\t""\t""',
        '""\t""\t"LD"\t"M1"\t""\t""\t""',
        '""\t""\t"MOV"\t"D180"\t""\t""\t""',
        '""\t""\t""\t"D123"\t""\t""\t""',
    ]
    lines = lines[:end_idx] + block + lines[end_idx:]
    print("Inserted D180 -> D123 status update")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print(f"Replaced {changed} cycle-counter references D131 -> D180")
print("MAIN.csv updated")
