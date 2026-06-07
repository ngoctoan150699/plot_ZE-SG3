import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

def find_segment(segment):
    for i in range(len(lines) - len(segment) + 1):
        if lines[i:i+len(segment)] == segment:
            return i
    return -1

# 1) Start đo: lưu xung bắt đầu và góc bắt đầu để tính góc thực tế khi Auto chạy.
start_target = [
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D123"\t""\t""\t""',
]
start_insert = [
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D123"\t""\t""\t""',
    '""\t"06.1 Luu moc xung/goc auto"\t""\t""\t""\t""\t""',
    '""\t""	"DMOV"\t"D8140"\t""\t""\t""',
    '""\t""\t""\t"D170"\t""\t""\t""',
    '""\t""\t"MOV"\t"D124"\t""\t""\t""',
    '""\t""\t""\t"D172"\t""\t""\t""',
]
idx = find_segment(start_target)
if idx < 0:
    raise SystemExit("Không tìm thấy đoạn start D123")
# tránh chèn lặp nếu đã có
if not any('06.1 Luu moc xung/goc auto' in line for line in lines):
    lines = lines[:idx] + start_insert + lines[idx+len(start_target):]
    print("Inserted auto start pulse/angle snapshot")
else:
    print("Auto snapshot block already exists")

# 2) Thay comment cũ cuối file bằng block tính D124 từ D8140 trong auto.
old_tail = [
    '""\t"10.1 Khong copy target sang goc hien tai"\t""\t""\t""\t""\t""',
    '""\t"D124 giu goc hien tai tra ve app; chi HOME moi reset ve 0"\t""\t""\t""\t""\t""',
]
angle_block = [
    '""\t"10.1 Auto tinh goc D124 tu bo dem xung Y000"\t""\t""\t""\t""\t""',
    '""\t"D8140/D8141 la current pulse count cua Y000"\t""\t""\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"DSUB"\t"D8140"\t""\t""\t""',
    '""\t""\t""\t"D170"\t""\t""\t""',
    '""\t""\t""\t"D174"\t""\t""\t""',
    '""\t""\t"LD<"\t"D174"\t""\t""\t""',
    '""\t""\t""\t"K0"\t""\t""\t""',
    '""\t""\t"DNEG"\t"D174"\t""\t""\t""',
    '""\t""\t""\t"D174"\t""\t""\t""',
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
idx = find_segment(old_tail)
if idx < 0:
    # nếu đã từng chèn block thì không làm gì
    if any('10.1 Auto tinh goc D124' in line for line in lines):
        print("Auto angle block already exists")
    else:
        raise SystemExit("Không tìm thấy tail comment để thay")
else:
    lines = lines[:idx] + angle_block + lines[idx+len(old_tail):]
    print("Inserted auto angle calculation from D8140")

with codecs.open(path, "w", "utf-16") as f:
    f.write("\r\n".join(lines) + "\r\n")
print("MAIN.csv updated")
