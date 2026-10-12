import sys
import tempfile
import unittest
from pathlib import Path
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "draw_plot"))

from domain.entities import ConnectionConfig, DeviceConfig, StandardRecord
from draw_plot import TorquePlotViewer
from ui.i18n import I18n

app = QApplication.instance() or QApplication(sys.argv)


class TestPartNoAndInternalSpec(unittest.TestCase):
    def setUp(self):
        self.i18n = I18n("vi")
        self.viewer = TorquePlotViewer(self.i18n)
        self.sample_record = StandardRecord(
            part_no="CBJ0006A",
            breakaway_max=18.0,
            operating_min=1.0,
            operating_max=5.0,
            internal_operating_min=1.5,
            internal_operating_max=4.0,
            part_name="Ball Joint",
        )

    def test_breakaway_disables_and_hides_internal_spec(self):
        """Breakaway Torque không được dùng tiêu chuẩn nội bộ."""
        self.viewer.set_standard_record(self.sample_record, "breakaway")

        # Tiêu chuẩn bản vẽ
        self.assertEqual(self.viewer.spec_min_spin.value(), 0.0)
        self.assertEqual(self.viewer.spec_max_spin.value(), 18.0)
        self.assertTrue(self.viewer._excel_spec_available)

        # Tiêu chuẩn nội bộ phải tắt
        self.assertFalse(self.viewer._has_internal_spec)
        self.assertEqual(self.viewer.internal_spec_min_spin.value(), 0.0)
        self.assertEqual(self.viewer.internal_spec_max_spin.value(), 0.0)

        # Widget nội bộ phải bị ẩn
        self.assertTrue(self.viewer.internal_spec_label.isHidden())
        self.assertTrue(self.viewer.internal_spec_min_spin.isHidden())
        self.assertTrue(self.viewer.internal_spec_max_spin.isHidden())
        self.assertTrue(self.viewer.internal_judgment_title_label.isHidden())
        self.assertTrue(self.viewer.internal_judgment_label.isHidden())

        # Phán định nội bộ không đánh giá
        self.assertEqual(self.viewer.internal_judgment_label.text(), "—")

    def test_operating_enables_and_shows_internal_spec(self):
        """Operating Torque có tiêu chuẩn nội bộ."""
        self.viewer.set_standard_record(self.sample_record, "operating")

        # Tiêu chuẩn bản vẽ
        self.assertEqual(self.viewer.spec_min_spin.value(), 1.0)
        self.assertEqual(self.viewer.spec_max_spin.value(), 5.0)

        # Tiêu chuẩn nội bộ phải bật
        self.assertTrue(self.viewer._has_internal_spec)
        self.assertEqual(self.viewer.internal_spec_min_spin.value(), 1.5)
        self.assertEqual(self.viewer.internal_spec_max_spin.value(), 4.0)

        # Widget nội bộ phải hiển thị (không bị hidden)
        self.assertFalse(self.viewer.internal_spec_label.isHidden())
        self.assertFalse(self.viewer.internal_spec_min_spin.isHidden())
        self.assertFalse(self.viewer.internal_spec_max_spin.isHidden())
        self.assertFalse(self.viewer.internal_judgment_title_label.isHidden())
        self.assertFalse(self.viewer.internal_judgment_label.isHidden())

    def test_oscillating_enables_and_shows_internal_spec(self):
        """Oscillating Torque có tiêu chuẩn nội bộ."""
        self.viewer.set_standard_record(self.sample_record, "oscillating")

        # Tiêu chuẩn bản vẽ
        self.assertEqual(self.viewer.spec_min_spin.value(), 1.0)
        self.assertEqual(self.viewer.spec_max_spin.value(), 5.0)

        # Tiêu chuẩn nội bộ phải bật
        self.assertTrue(self.viewer._has_internal_spec)
        self.assertEqual(self.viewer.internal_spec_min_spin.value(), 1.5)
        self.assertEqual(self.viewer.internal_spec_max_spin.value(), 4.0)

        # Widget nội bộ phải hiển thị (không bị hidden)
        self.assertFalse(self.viewer.internal_spec_label.isHidden())
        self.assertFalse(self.viewer.internal_spec_min_spin.isHidden())
        self.assertFalse(self.viewer.internal_spec_max_spin.isHidden())
        self.assertFalse(self.viewer.internal_judgment_title_label.isHidden())
        self.assertFalse(self.viewer.internal_judgment_label.isHidden())

    def test_switching_modes_updates_internal_spec(self):
        """Chuyển đổi giữa Breakaway và Operating tự động ẩn/hiện tiêu chuẩn nội bộ."""
        # Đầu tiên đặt Operating
        self.viewer.set_standard_record(self.sample_record, "operating")
        self.assertTrue(self.viewer._has_internal_spec)
        self.assertFalse(self.viewer.internal_spec_min_spin.isHidden())

        # Chuyển qua Breakaway
        self.viewer.test_item_combo.setCurrentText("Breakaway Torque")
        self.viewer.on_test_item_changed()
        self.assertFalse(self.viewer._has_internal_spec)
        self.assertTrue(self.viewer.internal_spec_min_spin.isHidden())

        # Chuyển lại qua Operating
        self.viewer.test_item_combo.setCurrentText("Operating Torque")
        self.viewer.on_test_item_changed()
        self.assertTrue(self.viewer._has_internal_spec)
        self.assertFalse(self.viewer.internal_spec_min_spin.isHidden())

    def test_main_window_part_no_sync(self):
        """Mã hàng tự động đồng bộ giữa tab Thu thập và tab Plot Viewer."""
        from infrastructure.app_settings import AppSettings
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "test_settings.json"
            settings = AppSettings(settings_file)
            collector = MagicMock()
            collector._client = MagicMock()
            config_svc = MagicMock()
            conn_cfg = ConnectionConfig()
            dev_cfg = DeviceConfig()
            from ui.main_window import MainWindow

            window = MainWindow(
                collector=collector,
                config_svc=config_svc,
                exporters=[],
                settings_repo=settings,
                conn_config=conn_cfg,
                dev_config=dev_cfg,
            )

            # Lazy load Plot Viewer
            window._on_main_tab_changed(1)
            self.assertTrue(hasattr(window, "_plot_viewer"))

            # 1. Nhập mã hàng bên tab Thu thập -> tự nhảy qua bên Plot Viewer
            window.combo_part_no.setEditText("CBJ0006A")
            self.assertEqual(window._plot_viewer.part_no_edit.text(), "CBJ0006A")

            # 2. Sửa mã hàng bên Plot Viewer -> tự đồng bộ ngược lại bên tab Thu thập
            window._plot_viewer.part_no_edit.setText("ITR0001B")
            self.assertEqual(window.combo_part_no.currentText(), "ITR0001B")


if __name__ == "__main__":
    unittest.main()
