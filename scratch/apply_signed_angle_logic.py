import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

def find_segment(seg):
    for i in range(len(lines) - len(seg) + 1):
        if lines[i:i+len(seg)] == seg:
            return i
    return -1

# Replace target assignment block so D125 is the signed command angle:
# step 1: +D102, step 2: 0, step 3: -D103 (D103 itself is positive magnitude from PC).
old_target = [
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
    '""\t""\t"MUL"\t"D103"\t""\t""\t""',
    '""\t""\t""\t"K-1"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
]
new_target = old_target[:]  # already correct, kept as marker for validation
if find_segment(old_target) < 0:
    print("Target block not matched exactly; leaving as-is")
else:
    print("Target block already uses signed D125 (+D102, 0, -D103)")

# Replace the problematic realtime angle block with a deterministic signed-angle block:
# D124 follows signed target D125. This avoids treating servo physical 0..360 as the display angle.
# Direction and pulse count are still computed earlier from signed error D160 = D125 - D124.
start = next((i for i, l in enumerate(lines) if '10.1 Auto tinh goc' in l), -1)
end = next((i for i, l in enumerate(lines) if '10.2 Operating advance step' in l), -1)
if start < 0 or end < 0 or end <= start:
    raise SystemExit("Không tìm thấy block 10.1..10.2 để thay")
new_angle = [
    '""\t"10.1 Cap nhat goc hien thi signed"\t""\t""\t""\t""\t""',
    '""\t"D124 la goc co dau tra app; servo vat ly van 0..360"\t""\t""\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"D125"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
]
lines = lines[:start] + new_angle + lines[end:]
print(f"Replaced angle display block rows {start+1}..{end}")

# Replace the step/cycle block from 10.2 to END with a clean version.
start = next((i for i, l in enumerate(lines) if '10.2 Operating advance step' in l), -1)
end = next((i for i, l in enumerate(lines) if '"END"' in l), -1)
if start < 0 or end < 0 or end <= start:
    raise SystemExit("Không tìm thấy block 10.2..END")
clean_step = [
    '""\t"10.2 Operating advance step khi den gan target"\t""\t""\t""\t""\t""',
    # D130 1 -> 2
    '""\t""\t"LD="\t"D101"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"AND"\t"M1"\t""\t""\t""',
    '""\t""\t"AND<="\t"D161"\t""\t""\t""',
    '""\t""\t""\t"K5"\t""\t""\t""',
    '""\t""\t"AND="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K1"\t""\t""\t""',
    '""\t""\t"MOV"\t"K2"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    # D130 2 -> 3
    '""\t""\t"LD="\t"D101"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"AND"\t"M1"\t""\t""\t""',
    '""\t""\t"AND<="\t"D161"\t""\t""\t""',
    '""\t""\t""\t"K5"\t""\t""\t""',
    '""\t""\t"AND="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"MOV"\t"K3"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    '""\t"10.3 Lap operating 3 chu ky"\t""\t""\t""\t""\t""',
    # D130 3 reached, if cycle < 3: D131++, D130=1
    '""\t""\t"LD="\t"D101"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"AND"\t"M1"\t""\t""\t""',
    '""\t""\t"AND<="\t"D161"\t""\t""\t""',
    '""\t""\t""\t"K5"\t""\t""\t""',
    '""\t""\t"AND="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"AND<"\t"D131"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"ADD"\t"D131"\t""\t""\t""',
    '""\t""\t""\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D131"\t""\t""\t""',
    '""\t""\t"LD="\t"D101"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"AND"\t"M1"\t""\t""\t""',
    '""\t""\t"AND<="\t"D161"\t""\t""\t""',
    '""\t""\t""\t"K5"\t""\t""\t""',
    '""\t""\t"AND="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"AND<"\t"D131"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    # D130 3 reached, if cycle >=3: done
    '""\t""\t"LD="\t"D101"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"AND"\t"M1"\t""\t""\t""',
    '""\t""\t"AND<="\t"D161"\t""\t""\t""',
    '""\t""\t""\t"K5"\t""\t""\t""',
    '""\t""\t"AND="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"AND>="\t"D131"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"RST"\t"M1"\t""\t""\t""',
    '""\t""\t"RST"\t"M2"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D122"\t""\t""\t""',
]
lines = lines[:start] + clean_step + lines[end:]
print(f"Replaced step/cycle block rows {start+1}..{end}")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
