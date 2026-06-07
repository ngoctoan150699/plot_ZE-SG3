import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

def find_segment(segment):
    for i in range(len(lines) - len(segment) + 1):
        if lines[i:i + len(segment)] == segment:
            return i
    return -1

# 1) Operating không được reset D130=1 liên tục mỗi scan.
# D130 sẽ là step trong chu kỳ: 1(+36), 2(0), 3(-36).
continuous_reset = [
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    '""\t"09.2 Operating step target: +36 -> 0 -> -36"\t""\t""\t""\t""\t""',
]
i = find_segment(continuous_reset)
if i >= 0:
    lines = lines[:i] + [continuous_reset[2]] + lines[i + len(continuous_reset):]
    print(f"Removed continuous D130 reset at row {i + 1}")
else:
    print("Continuous D130 reset not found or already removed")

# 2) Khi START_RECORD/START đo, khởi tạo step và cycle count.
start_anchor = [
    '""\t"06.1 Luu moc xung/goc auto"\t""\t""\t""\t""\t""',
    '""\t""\t"DMOV"\t"D8140"\t""\t""\t""',
    '""\t""\t""\t"D170"\t""\t""\t""',
    '""\t""\t"MOV"\t"D124"\t""\t""\t""',
    '""\t""\t""\t"D172"\t""\t""\t""',
]
start_extra = start_anchor + [
    '""\t"06.2 Init operating cycle counter"\t""\t""\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D131"\t""\t""\t""',
]
if not any('06.2 Init operating cycle counter' in l for l in lines):
    i = find_segment(start_anchor)
    if i < 0:
        raise SystemExit("Không tìm thấy block start snapshot")
    lines = lines[:i] + start_extra + lines[i + len(start_anchor):]
    print(f"Inserted cycle init at row {i + 1}")
else:
    print("Cycle init already exists")

# 3) Thay block advance cũ bằng block 3 chu kỳ.
old_advance = [
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
new_advance = old_advance + [
    '""\t"10.3 Lap operating 3 chu ky"\t""\t""\t""\t""\t""',
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
    '""\t""\t"AND<="\t"D131"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"RST"\t"M1"\t""\t""\t""',
    '""\t""\t"RST"\t"M2"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D122"\t""\t""\t""',
]
# after increment D131, set D130 back to 1. Must be after ADD block and before done block.
# Insert this by adding after D131 destination in list.
insert_at = 13
new_advance = new_advance[:insert_at] + [
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
] + new_advance[insert_at:]

# If previous run already added 10.3, remove everything from 10.2 until END first.
start = next((i for i, l in enumerate(lines) if '10.2 Operating advance step' in l), -1)
end = next((i for i, l in enumerate(lines) if '"END"' in l), -1)
if start < 0 or end < 0:
    raise SystemExit("Không tìm thấy block advance hoặc END")
lines = lines[:start] + new_advance + lines[end:]
print(f"Replaced advance block at row {start + 1}")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
