from pathlib import Path

base = Path(r"D:/gxword2/duan_ctrvina")
project = "Project name:plc_torque2"
watch_sets = {
    "watch_pc.csv": ["M100", "M101", "M102", "M103", "M104", "M106", "D101", "D102", "D100.0"],
    "watch_run.csv": ["X000", "X001", "X002", "X003", "M0", "M1", "M2", "M3", "M4", "M10", "Y004", "Y005", "Y006"],
    "watch_process.csv": ["D121", "D122", "D123", "D124", "D125", "D129", "D130"],
    "watch_math.csv": ["D160", "D161", "D164"],
}

for name, devices in watch_sets.items():
    text = project + "\n" + "Device/Label\r\n" + "".join(f'"{device}"\r\n' for device in devices)
    data = b"\xff\xfe" + text.encode("utf-16le")
    (base / name).write_bytes(data)

print("rewritten", ", ".join(watch_sets))
