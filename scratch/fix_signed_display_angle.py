import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

def find_segment(seg):
    for i in range(len(lines) - len(seg) + 1):
        if lines[i:i+len(seg)] == seg:
            return i
    return -1

# 1) Remove erroneous unconditional D130=1 inserted inside advance block.
bad = [
    '""\t""\t"LD="\t"D101"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"AND"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
]
i = find_segment(bad)
if i >= 0:
    del lines[i:i+len(bad)]
    print(f"Removed bad D130 reset at row {i+1}")
else:
    print("Bad D130 reset not found")

# 2) Replace angle display block: D124 is signed display angle, physical reverse still uses positive motion.
old = [
    '""\t"10.1 Auto tinh goc D124 theo target"\t""\t""\t""\t""\t""',
    '""\t"D103 la do lon duong, D124 hien thi am khi D125 am"\t""\t""\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"AND>="\t"D125"\t""\t""\t""',
    '""\t""\t""\t"K0"\t""\t""\t""',
    '""\t""\t"MOV"\t"D125"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"AND<"\t"D125"\t""\t""\t""',
    '""\t""\t""\t"K0"\t""\t""\t""',
    '""\t""\t"MOV"\t"D125"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
]
new = [
    '""\t"10.1 Auto tinh goc hien thi co dau tu xung"\t""\t""\t""\t""\t""',
    '""\t"D124: 0->+36, +36->0, 0->-36; D103 gui PLC la do lon duong"\t""\t""\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"DSUB"\t"D8140"\t""\t""\t""',
    '""\t""\t""\t"D170"\t""\t""\t""',
    '""\t""\t""\t"D174"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"DMUL"\t"D174"\t""\t""\t""',
    '""\t""\t""\t"K9"\t""\t""\t""',
    '""\t""\t""\t"D176"\t""\t""\t""',
    '""\t""\t"DDIV"\t"D176"\t""\t""\t""',
    '""\t""\t""\t"K50"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"AND>="\t"D125"\t""\t""\t""',
    '""\t""\t""\t"D172"\t""\t""\t""',
    '""\t""\t"ADD"\t"D172"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"AND<"\t"D125"\t""\t""\t""',
    '""\t""\t""\t"D172"\t""\t""\t""',
    '""\t""\t"SUB"\t"D172"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
]
i = find_segment(old)
if i < 0:
    raise SystemExit("Không tìm thấy block 10.1 cũ")
lines = lines[:i] + new + lines[i+len(old):]
print(f"Replaced angle display block at row {i+1}")

# 3) After every D130 step change, snapshot pulse/angle baseline so next segment starts from current signed angle.
# Add only if marker not exists.
if not any('10.25 Luu moc sau khi doi step' in l for l in lines):
    marker = next(i for i,l in enumerate(lines) if '10.3 Lap operating 3 chu ky' in l)
    snap = [
        '""\t"10.25 Luu moc sau khi doi step"\t""\t""\t""\t""\t""',
        '""\t""\t"LD"\t"M1"\t""\t""\t""',
        '""\t""\t"AND<="\t"D161"\t""\t""\t""',
        '""\t""\t""\t"K5"\t""\t""\t""',
        '""\t""\t"DMOV"\t"D8140"\t""\t""\t""',
        '""\t""\t""\t"D170"\t""\t""\t""',
        '""\t""\t"LD"\t"M1"\t""\t""\t""',
        '""\t""\t"AND<="\t"D161"\t""\t""\t""',
        '""\t""\t""\t"K5"\t""\t""\t""',
        '""\t""\t"MOV"\t"D124"\t""\t""\t""',
        '""\t""\t""\t"D172"\t""\t""\t""',
    ]
    lines = lines[:marker] + snap + lines[marker:]
    print(f"Inserted step baseline snapshot at row {marker+1}")
else:
    print("Step baseline snapshot already exists")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
