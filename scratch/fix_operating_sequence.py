import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

def find_segment(segment):
    for i in range(len(lines) - len(segment) + 1):
        if lines[i:i+len(segment)] == segment:
            return i
    return -1

def replace(segment, repl, name):
    global lines
    i = find_segment(segment)
    if i < 0:
        raise SystemExit(f"Không tìm thấy {name}")
    lines = lines[:i] + repl + lines[i+len(segment):]
    print(f"Updated {name} at row {i+1}")

# Operating mode: phase 1 target +36, phase 2 return 0, phase 3 target -36.
operating_old = [
    '""\t""\t"MOV"\t"K210"\t""\t""\t""',
    '""\t""\t""\t"D122"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    '""\t""\t"MOV"\t"D102"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
]
operating_new = [
    '""\t""\t"MOV"\t"K210"\t""\t""\t""',
    '""\t""\t""\t"D122"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    '""\t"09.2 Operating step target: +36 -> 0 -> -36"\t""\t""\t""\t""\t""',
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K1"\t""\t""\t""',
    '""\t""\t"MOV"\t"D102"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"MOV"\t"D103"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
]
if not any('09.2 Operating step target' in l for l in lines):
    replace(operating_old, operating_new, "operating stepped targets")
else:
    print("Operating stepped target block already exists")

# Auto pulse calculation: use signed delta pulse. Remove Y004 sign dependency.
angle_old = [
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"DMUL"\t"D174"\t""\t""\t""',
    '""\t""\t""\t"K9"\t""\t""\t""',
    '""\t""\t""\t"D176"\t""\t""\t""',
    '""\t""\t"DDIV"\t"D176"\t""\t""\t""',
    '""\t""\t""\t"K50"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"AND"\t"Y004"\t""\t""\t""',
    '""\t""\t"ADD"\t"D172"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"ANI"\t"Y004"\t""\t""\t""',
    '""\t""\t"SUB"\t"D172"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
]
angle_new = [
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"DMUL"\t"D174"\t""\t""\t""',
    '""\t""\t""\t"K9"\t""\t""\t""',
    '""\t""\t""\t"D176"\t""\t""\t""',
    '""\t""\t"DDIV"\t"D176"\t""\t""\t""',
    '""\t""\t""\t"K50"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"ADD"\t"D172"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
]
replace(angle_old, angle_new, "signed auto angle calculation")

# Add step advance: when target reached, go from +36 -> 0 -> -36.
end_index = next(i for i, l in enumerate(lines) if '"END"' in l)
if not any('10.2 Operating advance step' in l for l in lines):
    advance = [
        '""\t"10.2 Operating advance step khi den gan target"\t""\t""\t""\t""\t""',
        '""\t""\t"LD="\t"D101"\t""\t""\t""',
        '""\t""\t""\t"K2"\t""\t""\t""',
        '""\t""\t"AND"\t"M1"\t""\t""\t""',
        '""\t""\t"AND<="\t"D161"\t""\t""\t""',
        '""\t""\t""\t"K5"\t""\t""\t""',
        '""\t""\t"AND="\t"D130"\t""\t""\t""',
        '""\t""\t""\t"K1"\t""\t""\t""',
        '""\t""\t"MOV"\t"K2"\t""\t""\t""',
        '""\t""\t""\t"D130"\t""\t""\t""',
        '""\t""\t"LD="\t"D101"\t""\t""\t""',
        '""\t""\t""\t"K2"\t""\t""\t""',
        '""\t""\t"AND"\t"M1"\t""\t""\t""',
        '""\t""\t"AND<="\t"D161"\t""\t""\t""',
        '""\t""\t""\t"K5"\t""\t""\t""',
        '""\t""\t"AND="\t"D130"\t""\t""\t""',
        '""\t""\t""\t"K2"\t""\t""\t""',
        '""\t""\t"MOV"\t"K3"\t""\t""\t""',
        '""\t""\t""\t"D130"\t""\t""\t""',
    ]
    lines = lines[:end_index] + advance + lines[end_index:]
    print("Inserted operating step advance")
else:
    print("Operating step advance already exists")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
