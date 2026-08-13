import json
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from application.standard_service import StandardFileError, StandardService, default_standard_path
from infrastructure.app_settings import AppSettings

HEADERS = [
    "Mã hàng",
    "Tiêu chuẩn momen phá vỡ lớn nhất (Nm)",
    "Tiêu chuẩn momen hoạt động nhỏ nhất (Nm)",
    "Tiêu chuẩn momen hoạt động lớn nhất (Nm)",
    "Tiêu chuẩn momen hoạt động nội bộ nhỏ nhất (Nm)",
    "Tiêu chuẩn momen hoạt động nội bộ lớn nhất (Nm)",
    "Tiêu chuẩn đồ gá dưới",
    "Tiêu chuẩn đồ gá trên",
    "Mã ren",
    "Cảnh báo đặc biệt",
]
VALID_ROW = ["CBJ0000A", 12, 1, 5, 3, 3.5, "ϕ30", "ϕ35", "M10x1.25", "Hấp"]


class StandardServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_book(self, name="standard.xlsx", headers=None, rows=None):
        path = self.dir / name
        wb = Workbook()
        ws = wb.active
        ws.append(headers or HEADERS)
        for row in rows if rows is not None else [VALID_ROW]:
            ws.append(row)
        wb.save(path)
        wb.close()
        return path

    def test_real_default_file_mapping_and_case_insensitive_lookup(self):
        path = default_standard_path()
        self.assertEqual(path, ROOT / "file" / "Upload%20standard.xlsx")
        service = StandardService()
        self.assertEqual(service.load(), 1)
        record = service.lookup("cbj0000a")
        self.assertIsNotNone(record)
        self.assertEqual((record.breakaway_max, record.operating_min, record.operating_max), (12, 1, 5))
        self.assertEqual((record.internal_operating_min, record.internal_operating_max), (3, 3.5))
        self.assertEqual((record.lower_fixture, record.upper_fixture, record.thread_code, record.special_warning), ("ϕ30", "ϕ35", "M10x1.25", "Hấp"))
        self.assertEqual(service.part_numbers, ["CBJ0000A"])
        self.assertIsNone(service.lookup("CBJ0000"))

    def test_reordered_and_normalized_headers(self):
        order = list(reversed(range(10)))
        headers = ["  " + HEADERS[i].replace(" ", "  ").upper() + "  " for i in order]
        row = [VALID_ROW[i] for i in order]
        service = StandardService(self.write_book(headers=headers, rows=[row]))
        self.assertEqual(service.load(), 1)
        self.assertEqual(service.lookup("CBJ0000A").operating_max, 5)

    def test_rejects_invalid_schema_and_rows(self):
        cases = [
            (HEADERS[:-1], [VALID_ROW[:-1]]),
            (HEADERS + [HEADERS[0]], [VALID_ROW + ["X"]]),
            (HEADERS, [["SHORT", *VALID_ROW[1:]]]),
            (HEADERS, [VALID_ROW, VALID_ROW]),
            (HEADERS, [[VALID_ROW[0], "bad", *VALID_ROW[2:]]]),
            (HEADERS, [[VALID_ROW[0], float("nan"), *VALID_ROW[2:]]]),
            (HEADERS, [[VALID_ROW[0], 12, 6, 5, 3, 3.5, *VALID_ROW[6:]]]),
        ]
        for index, (headers, rows) in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(StandardFileError):
                    StandardService(self.write_book(f"bad{index}.xlsx", headers, rows)).load()

    def test_failed_load_keeps_previous_cache_and_path(self):
        good = self.write_book("good.xlsx")
        bad = self.write_book("bad.xlsx", rows=[["SHORT", *VALID_ROW[1:]]])
        service = StandardService(good)
        service.load()
        old_path = service.active_path
        with self.assertRaises(StandardFileError):
            service.load(bad)
        self.assertEqual(service.active_path, old_path)
        self.assertEqual(service.lookup("CBJ0000A").breakaway_max, 12)

    def test_settings_path_round_trip_preserves_other_ui_keys(self):
        settings_path = self.dir / "settings.json"
        settings_path.write_text(json.dumps({"ui": {"language": "vi"}}), encoding="utf-8")
        settings = AppSettings(settings_path)
        chosen = str(self.dir / "chosen.xlsx")
        settings.save_standard_file_path(chosen)
        restored = AppSettings(settings_path)
        self.assertEqual(restored.load_standard_file_path(), chosen)
        self.assertEqual(restored.load_ui_settings()["language"], "vi")


if __name__ == "__main__":
    unittest.main()
