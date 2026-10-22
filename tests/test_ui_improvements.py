import sys
import unittest
from pathlib import Path
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "draw_plot"))

from domain.entities import StandardRecord
from draw_plot import TorquePlotViewer
from ui.i18n import I18n

app = QApplication.instance() or QApplication(sys.argv)


class TestUIImprovements(unittest.TestCase):
    def setUp(self):
        self.i18n = I18n("vi")
        self.viewer = TorquePlotViewer(self.i18n)

    def test_path_settings_dialog_exists(self):
        """File save paths are housed inside path_settings_dialog, triggered by path_settings_btn."""
        self.assertTrue(hasattr(self.viewer, 'path_settings_btn'))
        self.assertTrue(hasattr(self.viewer, 'path_settings_dialog'))
        self.assertTrue(hasattr(self.viewer, 'csv_path_edit'))
        self.assertTrue(hasattr(self.viewer, 'report_path_edit'))
        self.assertTrue(hasattr(self.viewer, 'summary_report_path_edit'))
        self.assertTrue(hasattr(self.viewer, 'save_profile_btn'))
        self.assertTrue(hasattr(self.viewer, 'load_profile_btn'))
        self.assertEqual(self.viewer.path_settings_btn.text(), "📁 Cấu hình đường dẫn lưu...")

    def test_auto_and_manual_sections(self):
        """Auto and manual sections are clearly present with proper labels."""
        self.assertTrue(hasattr(self.viewer, 'lbl_auto_section'))
        self.assertTrue(hasattr(self.viewer, 'lbl_manual_section'))
        self.assertIn("tiêu chuẩn", self.viewer.lbl_auto_section.text().lower())
        self.assertIn("nhập liệu", self.viewer.lbl_manual_section.text().lower())

    def test_sentence_case_capitalization(self):
        """Check that labels use sentence case (first letter capitalized only)."""
        self.assertEqual(self.viewer.part_no_label.text(), "Mã sản phẩm:")
        self.assertEqual(self.viewer.sample_no_label.text(), "Số mẫu:")
        self.assertEqual(self.viewer.date_display_label.text(), "Ngày:")
        self.assertEqual(self.viewer.machine_name_label.text(), "Mã máy:")
        self.assertEqual(self.viewer.tester_label.text(), "Người đo:")
        self.assertEqual(self.viewer.test_purpose_label.text(), "Mục đích:")
        self.assertEqual(self.viewer.team_label.text(), "Nhóm:")
        self.assertEqual(self.viewer.lot_no_label.text(), "Số lot:")
        self.assertEqual(self.viewer.line_no_label.text(), "Số line:")
        self.assertEqual(self.viewer.specification_label.text(), "Tiêu chuẩn bản vẽ:")
        self.assertEqual(self.viewer.internal_spec_label.text(), "Tiêu chuẩn nội bộ:")

    def test_spec_alignment(self):
        """Drawing spec and internal spec spins have identical fixed widths for perfect alignment."""
        self.assertEqual(self.viewer.spec_min_spin.width(), self.viewer.internal_spec_min_spin.width())
        self.assertEqual(self.viewer.spec_max_spin.width(), self.viewer.internal_spec_max_spin.width())
        self.assertEqual(self.viewer.spec_min_label.width(), self.viewer.internal_spec_min_label.width())
        self.assertEqual(self.viewer.spec_max_label.width(), self.viewer.internal_spec_max_label.width())


class TestMainWindowJog(unittest.TestCase):
    def setUp(self):
        import tempfile
        from unittest.mock import MagicMock
        from domain.entities import ConnectionConfig, DeviceConfig
        from ui.main_window import MainWindow
        from infrastructure.app_settings import AppSettings
        self.tmpdir = tempfile.TemporaryDirectory()
        settings_file = Path(self.tmpdir.name) / "test_settings.json"
        self.settings = AppSettings(settings_file)
        self.collector = MagicMock()
        self.collector._client = MagicMock()
        self.config_svc = MagicMock()
        self.window = MainWindow(
            collector=self.collector,
            config_svc=self.config_svc,
            exporters=[],
            settings_repo=self.settings,
            conn_config=ConnectionConfig(),
            dev_config=DeviceConfig(),
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_jog_speed_in_layout(self):
        """spin_plc_jog_speed is added to layout and visible."""
        self.assertTrue(hasattr(self.window, 'spin_plc_jog_speed'))
        self.assertTrue(hasattr(self.window, 'lbl_plc_jog_speed'))
        # Ensure it is a child of grp_plc_control layout
        plc_layout = self.window.grp_plc_control.layout()
        found = False
        for i in range(plc_layout.count()):
            item = plc_layout.itemAt(i)
            if item.layout():
                lay = item.layout()
                for j in range(lay.count()):
                    w = lay.itemAt(j).widget()
                    if w is self.window.spin_plc_jog_speed:
                        found = True
                        break
        self.assertTrue(found, "spin_plc_jog_speed should be in grp_plc_control layout")

    def test_jog_speed_change_persists_to_profile(self):
        """Changing spin_plc_jog_speed updates the servo profile."""
        from ui.main_window import servo_profile_key
        self.window.spin_plc_jog_speed.setValue(25.5)
        profiles = self.settings.load_servo_profiles()
        current_key = servo_profile_key(self.window._current_part_code(), self.window._current_test_item_code())
        self.assertIn(current_key, profiles)
        self.assertEqual(profiles[current_key].jog_speed, 25.5)


if __name__ == "__main__":
    unittest.main()
