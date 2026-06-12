from pathlib import Path
p = Path(r"d:\DuAn\18.Other\plot_draw\plot_ZE-SG3\plc_ctrvina\COMMENT.csv")
text = p.read_text(encoding='utf-16')
lines = text.splitlines()
if len(lines) > 1:
    line = lines[1]
    print(repr(line))
    for char in line:
        print(f"Char: {repr(char)}, Code: {ord(char)}")
