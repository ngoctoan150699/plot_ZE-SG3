from pathlib import Path
root=Path('.')
# bump build script 2.0.15 -> 2.0.16
p=root/'build_exe.bat'
s=p.read_text(encoding='utf-8')
s=s.replace('v2.0.15','v2.0.16').replace('2.0.15.iss','2.0.16.iss')
p.write_text(s,encoding='utf-8')
# create ISS 2.0.16 from 2.0.15
src=root/'iss'/'ZE-SG3 Torque Acquisition2.0.15.iss'
dst=root/'iss'/'ZE-SG3 Torque Acquisition2.0.16.iss'
s=src.read_text(encoding='utf-8')
s=s.replace('2.0.15','2.0.16')
dst.write_text(s,encoding='utf-8')
# release notes
notes=root/'release_notes_v2.0.16.md'
notes.write_text('''# ZE-SG3 Torque Acquisition v2.0.16\n\n## Thay đổi chính\n\n- Fix oscillating torque range display issue.\n- Update standard report with 3 new display columns.\n- Fix k_factor multiplication during save report.\n\nAsset đính kèm là file setup tạo bằng Inno Setup cho Windows.\n''', encoding='utf-8')
# remove scratch patch scripts created during implementation
for f in (root/'scratch').glob('patch_*.py'):
    f.unlink(missing_ok=True)
(root/'scratch'/'fix_plc_two_registers.py').unlink(missing_ok=True)
