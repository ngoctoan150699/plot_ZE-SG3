# ZE-SG3 Torque Acquisition — Agent Context

Use this file as the first, lightweight context before analyzing code. Keep responses in Vietnamese unless the user asks otherwise.

## Project Purpose
Desktop Python/PyQt5 app for Seneca ZE-SG3 torque acquisition:
- Connect ZE-SG3 via Modbus RTU/TCP.
- Read torque realtime.
- Plot Torque-Time and Torque-Angle.
- Record/export CSV/report data.
- Control servo/PLC test flow.
- Support VI/EN UI through `python/ui/i18n.py`.

## Tech Stack
- Python desktop app.
- PyQt5 / PyQtWebEngine for UI.
- matplotlib for realtime charts.
- pymodbus 2.5.3 + pyserial for Modbus.
- pandas/openpyxl/numpy/scipy for data/report processing.

## Entry Point & Run
Main entry: `python/main.py`

Preferred run command on Windows:
```powershell
.\.venv\Scripts\python.exe python\main.py
```

If venv is activated:
```powershell
python python\main.py
```

## Main Folders
- `python/main.py`: composition root, creates services and injects them into UI.
- `python/ui/main_window.py`: main PyQt UI, tabs, chart, recording, servo controls.
- `python/ui/i18n.py`: VI/EN translations. Do not hardcode UI labels if avoidable.
- `python/ui/widgets/`: reusable chart widgets.
- `python/application/`: service layer: data collector, config, servo, measurement, report.
- `python/infrastructure/`: Modbus RTU/TCP clients, settings, PLC/servo controller.
- `python/domain/`: constants and entities.
- `python/exporters/`: CSV exporters.
- `draw_plot/`: external plot viewer/converter imported by UI.
- `plc_ctrvina/PLC_MODBUS_PLAN.md`: PLC Modbus register plan D100..D135.
- `python/settings.json`: persisted connection/device/UI settings.

## Architecture Summary
The app follows a lightweight Clean Architecture style:

```text
main.py
  -> infrastructure: AppSettings, Modbus clients, PLC controller
  -> application: DataCollectorService, ConfigService, ServoService, ReportService
  -> exporters: CSV exporters
  -> ui: MainWindow
```

Core data flow:
```text
MainWindow
  -> DataCollectorService
    -> IModbusClient RTU/TCP
      -> ZE-SG3 registers
    -> DeviceStatus
  -> Qt signals
  -> UI labels/charts/session/export
```

Servo/PLC flow currently:
```text
MainWindow -> ServoService -> PLC/servo controller
```

## Important Rules for Future Edits
1. Read only the relevant files; avoid pasting full large files.
2. `main_window.py` is large: inspect exact methods before editing.
3. Put UI text in `i18n.py`; use `self.i18n.t('key')`.
4. For combo boxes, preserve `userData`; do not depend on display text.
5. Keep `DataCollectorService` reading ZE-SG3 directly unless user requests otherwise.
6. PLC should mainly handle servo/state machine based on `PLC_MODBUS_PLAN.md`.
7. PLC command register `D100` must use read-modify-write to avoid clearing other command bits.
8. PLC compatibility mode is expected because some registers may not be implemented yet.
9. Before major PLC work, read `plc_ctrvina/PLC_MODBUS_PLAN.md` and the current implementation plan artifact if available.
10. Verify with `.\.venv\Scripts\python.exe -m py_compile ...` when possible.

## Current Known Context
- Recent UI i18n fixes touched measure mode, filter options, chart pause/clear, and theme labels.
- `main.py` currently creates `DummyPLCServoController`; real PLC Modbus integration is pending.
- Planned PLC register range is D100..D135.

## Response Style
- Vietnamese.
- Concise but actionable.
- Explain cause briefly, then implement.
- Show only key diff/changed lines when summarizing.
- Ask only when blocked by missing decision or unsafe ambiguity.
