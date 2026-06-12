from pathlib import Path
p = Path(r"d:\DuAn\18.Other\plot_draw\plot_ZE-SG3\plc_ctrvina\COMMENT.csv")
data = p.read_bytes()
print("First 40 bytes:", data[:40])
