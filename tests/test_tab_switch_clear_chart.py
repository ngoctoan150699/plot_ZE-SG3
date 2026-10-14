import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "draw_plot"))

from domain.entities import ConnectionConfig, DeviceConfig, SampleData
from ui.main_window import MainWindow
from infrastructure.app_settings import AppSettings

app = QApplication.instance() or QApplication(sys.argv)


class TestTabSwitchClearChart(unittest.TestCase):
    def setUp(self):
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
        # Load Plot Viewer (tab 1)
        self.window._on_main_tab_changed(1)
        self.assertTrue(self.window._plot_viewer_loaded)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_switch_from_plot_viewer_with_samples_confirmed_clears_charts(self):
        """Khi có mẫu trên Plot Viewer, chuyển về Thu thập và nhấn OK sẽ xóa biểu đồ cả 2 bên."""
        pv = self.window._plot_viewer
        pv.samples = [{
            'path': 'dummy.csv',
            'name': 'dummy.csv',
            'time': [0.1, 0.2],
            'torque': [1.5, 2.0],
            'angle': [10.0, 20.0],
            'cycle': [1, 1],
            'selected_cycles': [1],
            'part_no': 'TEST0001',
        }]
        # Giả lập mẫu trên tab Thu thập
        self.window._session.samples = [SampleData(time_s=0.1, torque_Nm=1.5, stable=True)]
        self.window.plot.add_point(0.1, 1.5)

        # Mock người dùng nhấn OK (Đồng ý)
        self.window._confirm_clear_charts_dialog = MagicMock(return_value=True)

        # Chuyển tab về Thu thập (index 0)
        self.window._on_main_tab_changed(0)

        # Xác nhận hộp thoại đã được gọi
        self.window._confirm_clear_charts_dialog.assert_called_once()

        # Xác nhận biểu đồ và dữ liệu mẫu đã bị xóa sạch
        self.assertEqual(len(pv.samples), 0)
        self.assertEqual(len(self.window._session.samples), 0)
        self.assertEqual(len(self.window.plot._x_data), 0)

    def test_switch_from_plot_viewer_cancel_preserves_charts(self):
        """Khi người dùng nhấn Hủy/Không, biểu đồ và dữ liệu mẫu được bảo lưu."""
        pv = self.window._plot_viewer
        sample = {
            'path': 'dummy.csv',
            'name': 'dummy.csv',
            'time': [0.1, 0.2],
            'torque': [1.5, 2.0],
            'angle': [10.0, 20.0],
            'cycle': [1, 1],
            'selected_cycles': [1],
            'part_no': 'TEST0001',
        }
        pv.samples = [sample]
        self.window._session.samples = [SampleData(time_s=0.1, torque_Nm=1.5, stable=True)]
        self.window.plot.add_point(0.1, 1.5)

        # Mock người dùng nhấn Hủy (Không xóa)
        self.window._confirm_clear_charts_dialog = MagicMock(return_value=False)

        # Chuyển tab về Thu thập (index 0)
        self.window._on_main_tab_changed(0)

        # Xác nhận hộp thoại đã được gọi
        self.window._confirm_clear_charts_dialog.assert_called_once()

        # Dữ liệu vẫn được giữ nguyên
        self.assertEqual(len(pv.samples), 1)
        self.assertEqual(len(self.window._session.samples), 1)
        self.assertGreater(len(self.window.plot._x_data), 0)

    def test_switch_applies_to_all_torque_types(self):
        """Áp dụng xóa biểu đồ khi chuyển tab cho tất cả các loại mô-men (Breakaway, Operating, Oscillating)."""
        pv = self.window._plot_viewer

        for test_mode in ('Breakaway Torque', 'Operating Torque', 'Oscillating Torque'):
            self.window.combo_test_item.setCurrentText(test_mode)
            self.window._current_main_tab_index = 1
            pv.samples = [{
                'path': f'{test_mode}.csv',
                'name': f'{test_mode}.csv',
                'time': [0.1],
                'torque': [2.0],
                'angle': [5.0],
                'cycle': [1],
                'selected_cycles': [1],
                'part_no': 'TEST0001',
            }]

            self.window._confirm_clear_charts_dialog = MagicMock(return_value=True)
            self.window._on_main_tab_changed(0)

            self.window._confirm_clear_charts_dialog.assert_called_once()
            self.assertEqual(len(pv.samples), 0, f"Failed to clear for mode: {test_mode}")

    def test_switch_without_any_data_skips_dialog(self):
        """Khi cả 2 tab đều không có dữ liệu mẫu/biểu đồ, không làm phiền người dùng bằng hộp thoại."""
        pv = self.window._plot_viewer
        pv.samples = []
        self.window._session.samples = []
        self.window.plot.clear()

        self.window._confirm_clear_charts_dialog = MagicMock(return_value=True)

        # Chuyển tab về Thu thập
        self.window._on_main_tab_changed(0)

        # Không được gọi hộp thoại hỏi
        self.window._confirm_clear_charts_dialog.assert_not_called()


if __name__ == "__main__":
    unittest.main()
