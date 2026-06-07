import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

def find_segment(segment):
    for i in range(len(lines) - len(segment) + 1):
        if lines[i:i+len(segment)] == segment:
            return i
    return -1

old_target_neg = [
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"MOV"\t"D103"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
]
new_target_neg = [
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"MUL"\t"D103"\t""\t""\t""',
    '""\t""\t""\t"K-1"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
]
i = find_segment(old_target_neg)
if i >= 0:
    lines = lines[:i] + new_target_neg + lines[i+len(old_target_neg):]
    print(f"Updated negative target to -D103 at row {i+1}")
else:
    print("Negative target block not found or already updated")

old_angle_calc = [
    '""\t"10.1 Auto tinh goc D124 tu bo dem xung Y000"\t""\t""\t""\t""\t""',
    '""\t"D8140/D8141 la current pulse count cua Y000"\t""\t""\t""\t""\t""',
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
    '""\t""\t"ADD"\t"D172"\t""\t""\t""',
    '""\t""\t""\t"D178"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
]
new_angle_calc = [
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
i = find_segment(old_angle_calc)
if i >= 0:
    lines = lines[:i] + new_angle_calc + lines[i+len(old_angle_calc):]
    print(f"Replaced angle calc block at row {i+1}")
else:
    print("Old angle calc block not found; no replacement")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
