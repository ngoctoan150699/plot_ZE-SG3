import csv
import re
from pathlib import Path

def parse_main_csv():
    main_path = Path(r"d:\DuAn\18.Other\plot_draw\plot_ZE-SG3\plc_ctrvina\MAIN.csv")
    if not main_path.exists():
        print("MAIN.csv not found")
        return
        
    text = main_path.read_text(encoding='utf-16')
    
    # Regex to match device patterns like X000, Y004, M10, D120, etc.
    device_pattern = re.compile(r'\b([XYMDTCD]|M8\d{3}|D8\d{3})\d+\b')
    
    devices = set()
    for line in text.splitlines():
        # Clean line and split by tabs or commas
        parts = [p.strip().strip('"') for p in line.split('\t')]
        if len(parts) < 4:
            # Try comma split if tab split doesn't give enough parts
            parts = [p.strip().strip('"') for p in line.split(',')]
            
        for part in parts:
            matches = device_pattern.findall(part)
            for m in device_pattern.finditer(part):
                devices.add(m.group(0))
                
    print(f"Found {len(devices)} unique devices:")
    for d in sorted(list(devices), key=lambda x: (x[0], int(re.search(r'\d+', x).group(0)))):
        print(d)

if __name__ == '__main__':
    parse_main_csv()
