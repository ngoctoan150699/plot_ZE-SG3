import codecs
from pathlib import Path

path = Path(r"d:\du_an_ctrvina\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
lines = codecs.open(path, "r", "utf-16").read().splitlines()

def find_index_contains(text):
    return next((i for i, line in enumerate(lines) if text in line), -1)

# 1) Replace target assignment block: 4 signed steps around home.
start = find_index_contains('09.2 Operating step target')
end = find_index_contains('09.1 Che do Manual')
if start < 0 or end < 0 or end <= start:
    raise SystemExit('Không tìm thấy block 09.2 target')

target_block = [
    '""\t"09.2 Operating signed target: 0 -> + -> 0 -> - -> 0"\t""\t""\t""\t""\t""',
    # step 1: +D102
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K1"\t""\t""\t""',
    '""\t""\t"MOV"\t"D102"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
    # step 2: 0
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K2"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
    # step 3: -D103 (D103 is positive magnitude)
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K3"\t""\t""\t""',
    '""\t""\t"MUL"\t"D103"\t""\t""\t""',
    '""\t""\t""\t"K-1"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
    # step 4: return home 0
    '""\t""\t"LD="\t"D130"\t""\t""\t""',
    '""\t""\t""\t"K4"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D125"\t""\t""\t""',
]
lines = lines[:start] + target_block + lines[end:]
print(f'Replaced target block rows {start+1}..{end}')

# 2) Replace transition/cycle block. Process from high step to low step to avoid same-scan cascading.
start = find_index_contains('10.2 Operating advance step')
end = next((i for i, line in enumerate(lines) if '"END"' in line), -1)
if start < 0 or end < 0 or end <= start:
    raise SystemExit('Không tìm thấy block 10.2..END')

def cond_prefix(step: int, extra_cmp: str | None = None):
    base = [
        '""\t""\t"LD="\t"D101"\t""\t""\t""',
        '""\t""\t""\t"K2"\t""\t""\t""',
        '""\t""\t"AND"\t"M1"\t""\t""\t""',
        '""\t""\t"AND<="\t"D161"\t""\t""\t""',
        '""\t""\t""\t"K5"\t""\t""\t""',
        '""\t""\t"AND="\t"D130"\t""\t""\t""',
        f'""\t""\t""\t"K{step}"\t""\t""\t""',
    ]
    if extra_cmp == 'lt3':
        base += ['""\t""\t"AND<"\t"D180"\t""\t""\t""', '""\t""\t""\t"K3"\t""\t""\t""']
    if extra_cmp == 'ge3':
        base += ['""\t""\t"AND>="\t"D180"\t""\t""\t""', '""\t""\t""\t"K3"\t""\t""\t""']
    return base

def latch_arrival_and_next(next_step: int):
    return [
        # latch actual signed angle exactly at target, then reset pulse/angle baseline for next leg
        '""\t""\t"MOV"\t"D125"\t""\t""\t""',
        '""\t""\t""\t"D124"\t""\t""\t""',
        '""\t""\t"DMOV"\t"D8140"\t""\t""\t""',
        '""\t""\t""\t"D170"\t""\t""\t""',
        '""\t""\t"MOV"\t"D124"\t""\t""\t""',
        '""\t""\t""\t"D172"\t""\t""\t""',
        '""\t""\t"MOV"\t"K%d"\t""\t""\t""' % next_step,
        '""\t""\t""\t"D130"\t""\t""\t""',
    ]

step_block = ['""\t"10.2 Operating advance: +36 -> 0 -> -36 -> 0"\t""\t""\t""\t""\t""']
# step4 reached: either next cycle or done, processed first
step_block += ['""\t"10.3 Neu step4 ve 0 xong va chua du 3 chu ky"\t""\t""\t""\t""\t""']
step_block += cond_prefix(4, 'lt3')
step_block += [
    '""\t""\t"MOV"\t"D125"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
    '""\t""\t"ADD"\t"D180"\t""\t""\t""',
    '""\t""\t""\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D180"\t""\t""\t""',
    '""\t""\t"DMOV"\t"D8140"\t""\t""\t""',
    '""\t""\t""\t"D170"\t""\t""\t""',
    '""\t""\t"MOV"\t"D124"\t""\t""\t""',
    '""\t""\t""\t"D172"\t""\t""\t""',
    '""\t""\t"MOV"\t"K1"\t""\t""\t""',
    '""\t""\t""\t"D130"\t""\t""\t""',
]
step_block += ['""\t"10.4 Neu step4 ve 0 xong va du 3 chu ky thi ket thuc"\t""\t""\t""\t""\t""']
step_block += cond_prefix(4, 'ge3')
step_block += [
    '""\t""\t"MOV"\t"D125"\t""\t""\t""',
    '""\t""\t""\t"D124"\t""\t""\t""',
    '""\t""\t"RST"\t"M1"\t""\t""\t""',
    '""\t""\t"RST"\t"M2"\t""\t""\t""',
    '""\t""\t"MOV"\t"K0"\t""\t""\t""',
    '""\t""\t""\t"D122"\t""\t""\t""',
]
# step3 -> step4, step2 -> step3, step1 -> step2
step_block += ['""\t"10.5 Step3 -36 xong -> ve 0"\t""\t""\t""\t""\t""'] + cond_prefix(3) + latch_arrival_and_next(4)
step_block += ['""\t"10.6 Step2 0 xong -> xuong -36"\t""\t""\t""\t""\t""'] + cond_prefix(2) + latch_arrival_and_next(3)
step_block += ['""\t"10.7 Step1 +36 xong -> ve 0"\t""\t""\t""\t""\t""'] + cond_prefix(1) + latch_arrival_and_next(2)
# status update
step_block += [
    '""\t"10.8 Cap nhat current cycle status"\t""\t""\t""\t""\t""',
    '""\t""\t"LD"\t"M1"\t""\t""\t""',
    '""\t""\t"MOV"\t"D180"\t""\t""\t""',
    '""\t""\t""\t"D123"\t""\t""\t""',
]

lines = lines[:start] + step_block + lines[end:]
print(f'Replaced transition block rows {start+1}..{end}')

with codecs.open(path, 'w', 'utf-16') as f:
    f.write('\r\n'.join(lines) + '\r\n')
print('MAIN.csv updated')
