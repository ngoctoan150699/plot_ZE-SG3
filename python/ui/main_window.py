"""
UI Layer – Main Window
=======================
SRP: MainWindow chỉ điều phối giao tiếp giữa các panel và services.
DIP: Nhận services qua constructor injection (không tạo ở đây).

Cải thiện UX so với file gốc:
- Dark theme chuyên nghiệp
- LED indicator trạng thái kết nối
- Chart live ngay khi kết nối (không cần nhấn ghi)
- Hiển thị Min/Max giá trị
- Auto-save cấu hình khi đóng app
- Logging chuẩn thay vì print()
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QToolButton,
)

import serial.tools.list_ports

from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from application.config_service import ConfigService
from application.data_collector import DataCollectorService
from application.interfaces import IDataExporter, ISettingsRepository
from domain.constants import (
    CMD_RESTART, CMD_TARE, CMD_TARE_RAM, FILTER_LABELS, UNITS,
    DEFAULT_SAMPLE_INTERVAL_MS, DEFAULT_TIME_WINDOW_S,
    BAUD_LABELS, PARITY_LABELS, SPS_LABELS
)
from domain.entities import (
    ConnectionConfig, DeviceConfig, DeviceStatus,
    RecordingSession, SampleData,
)
from ui.widgets.realtime_plot import RealTimePlot

# Plot Viewer & Converter (tái sử dụng từ draw_plot.py)
import os
import tempfile
try:
    from draw_plot import TorquePlotViewer
    from convert_may_gui import ConvertWidget
    _HAS_PLOT_VIEWER = True
except ImportError:
    _HAS_PLOT_VIEWER = False

logger = logging.getLogger(__name__)

# ===================== THEMES =====================
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 10px;
    padding: 8px;
    color: #89b4fa;
    font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 6px 14px;
    color: #cdd6f4;
}
QPushButton:hover  { background: #45475a; border-color: #89b4fa; }
QPushButton:pressed { background: #585b70; }
QPushButton:disabled { color: #6c7086; background: #181825; }
QComboBox, QSpinBox, QDoubleSpinBox {
    background: #181825;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 6px;
    color: #cdd6f4;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #181825;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QTabWidget::pane { border: 1px solid #45475a; border-radius: 4px; }
QTabBar::tab {
    background: #181825;
    color: #a6adc8;
    padding: 6px 10px;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #313244; color: #89b4fa; font-weight: bold; border-top: 2px solid #89b4fa;}
QTabBar::tab:hover:!selected { background: #313244; }
QTextEdit {
    background: #11111b;
    color: #a6e3a1;
    border: 1px solid #313244;
    font-family: Consolas, monospace;
    font-size: 9pt;
}
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #45475a; background: #181825; }
QCheckBox::indicator:checked { background: #89b4fa; border-color: #89b4fa; }
QSplitter::handle { background: #313244; width: 2px; }
QScrollBar:vertical { background: #181825; width: 10px; border-radius: 5px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #585b70; }
"""

LIGHT_STYLE = """
QMainWindow, QWidget {
    background-color: #f4f6f9;
    color: #212121;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    color: #1976d2;
    font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton {
    background: #e3f2fd;
    border: 1px solid #bbdefb;
    border-radius: 4px;
    padding: 6px 14px;
    color: #1565c0;
    font-weight: medium;
}
QPushButton:hover  { background: #bbdefb; border-color: #1976d2; }
QPushButton:pressed { background: #90caf9; }
QPushButton:disabled { color: #9e9e9e; background: #f5f5f5; border: 1px solid #e0e0e0; }
QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #dcdcdc;
    border-radius: 4px;
    padding: 4px 6px;
    color: #212121;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #212121;
    selection-background-color: #bbdefb;
}
QTabWidget::pane { border: 1px solid #e0e0e0; border-radius: 4px; background: #ffffff; }
QTabBar::tab {
    background: #e0e0e0;
    color: #757575;
    padding: 6px 10px;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected { 
    background: #ffffff; 
    color: #1976d2; 
    font-weight: bold; 
    border-top: 2px solid #1976d2;
}
QTabBar::tab:hover:!selected { background: #eeeeee; }
QTextEdit {
    background: #ffffff;
    color: #1b5e20;
    border: 1px solid #e0e0e0;
    font-family: Consolas, monospace;
    font-size: 9pt;
}
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #bdbdbd; background: white; }
QCheckBox::indicator:checked { background: #1976d2; border-color: #1976d2; }
QSplitter::handle { background: #e0e0e0; width: 2px; }
QScrollArea { background-color: transparent; border: none; }
QScrollBar:vertical { background: #f1f1f1; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #c1c1c1; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #a8a8a8; }
"""


from PyQt5.QtWidgets import QAction, QStyle

class CustomToolbar(NavigationToolbar):
    """Custom Toolbar: Loại bỏ nút Subplot và thêm nút Zoom Out."""
    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)
        
        # 1. Loại bỏ nút 'Configure subplots'
        actions = self.actions()
        # Các từ khóa cần loại bỏ (ví dụ 'Configure subplots', 'Customize', 'Figure options')
        blacklist = ('subplot', 'configure', 'custom', 'figure', 'options', 'edit')
        for action in actions:
            tip = (action.toolTip() or '').lower()
            txt = (action.text() or '').lower()
            if any(k in tip or k in txt for k in blacklist):
                try:
                    self.removeAction(action)
                except Exception:
                    pass
        
        # 2. Thêm nút 'Zoom Out'
        self.zoom_out_act = QAction("Zoom Out", self)
        # Sử dụng icon chuẩn SP_TitleBarMinButton (dấu trừ) làm biểu tượng Zoom Out
        self.zoom_out_act.setIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarMinButton))
        self.zoom_out_act.setToolTip("Zoom Out (1.25x)")
        self.zoom_out_act.triggered.connect(self.zoom_out)
        
        # Chèn Zoom Out sau nút Zoom chuẩn nếu tìm thấy
        zoom_action = None
        actions = self.actions() # Lấy lại danh sách sau khi đã xóa subplot
        for action in actions:
            if 'zoom' in action.toolTip().lower() and 'rect' in action.toolTip().lower():
                zoom_action = action
                break
        
        if zoom_action:
            found = False
            for i, action in enumerate(actions):
                if action == zoom_action:
                    if i + 1 < len(actions):
                        next_action = actions[i+1]
                        self.insertAction(next_action, self.zoom_out_act)
                        found = True
                    break
            if not found:
                self.addAction(self.zoom_out_act)
        else:
            self.addAction(self.zoom_out_act)

    def zoom_out(self):
        """Thu nhỏ biểu đồ bằng cách mở rộng giới hạn các trục."""
        if not self.canvas.figure.axes:
            return
        ax = self.canvas.figure.axes[0]
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        factor = 1.25 # Hệ số phóng đại vùng nhìn (tương đương zoom out)
        x_center = (xlim[0] + xlim[1]) / 2
        y_center = (ylim[0] + ylim[1]) / 2
        
        new_w = (xlim[1] - xlim[0]) * factor
        new_h = (ylim[1] - ylim[0]) * factor
        
        ax.set_xlim([x_center - new_w/2, x_center + new_w/2])
        ax.set_ylim([y_center - new_h/2, y_center + new_h/2])
        
        self.canvas.draw()


class MainWindow(QMainWindow):
    """
    MainWindow điều phối toàn bộ ứng dụng.
    Services được inject từ bên ngoài (DIP).
    """
    # Qt signals cho thread-safe UI update
    _sig_status = pyqtSignal(DeviceStatus)
    _sig_error  = pyqtSignal(str)

    def __init__(
        self,
        collector: DataCollectorService,
        config_svc: ConfigService,
        exporters: List[IDataExporter],
        settings_repo: ISettingsRepository,
        conn_config: ConnectionConfig,
        dev_config: DeviceConfig,
    ):
        super().__init__()
        # === Inject dependencies ===
        self._collector   = collector
        self._config_svc  = config_svc
        self._exporters   = exporters
        self._settings    = settings_repo
        self._conn_cfg    = conn_config
        self._dev_cfg     = dev_config

        # === Trạng thái nội bộ ===
        self._connected   = False
        self._recording   = False
        self._session     = RecordingSession()
        self._last_status: Optional[DeviceStatus] = None # Lưu status cuối cùng
        self._start_time  = 0.0
        self._ref_time    = 0.0     # Thời gian gốc cho biểu đồ
        self._only_stable = True
        self._chk_stable_only: Optional[QCheckBox] = None
        self._chart_paused = False  # Trạng thái đóng băng biểu đồ

        # === Qt signals → UI callbacks ===
        self._sig_status.connect(self._on_status_received)
        self._sig_error.connect(self._on_error)

        # === Đăng ký callback cho DataCollector ===
        self._collector.on_data(lambda s: self._sig_status.emit(s))
        self._collector.on_error(lambda e: self._sig_error.emit(e))

        # Theme state (load từ settings)
        ui_cfg = settings_repo.load_ui_settings()
        self._is_dark = ui_cfg.get('dark_theme', False)

        self._build_ui()
        self._load_settings_to_ui()
        self._apply_theme(self._is_dark)

    # ===========================================================
    # BUILD UI
    # ===========================================================

    def _build_ui(self):
        self.setWindowTitle("Seneca ZE-SG3 – Torque Acquisition (DYJN-101 50Nm)")
        self.setGeometry(80, 80, 1280, 820)
        self.setMinimumSize(960, 650)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # === QTabWidget cấp cao nhất ===
        self.main_tabs = QTabWidget()
        self.main_tabs.setTabPosition(QTabWidget.North)
        root_layout.addWidget(self.main_tabs)

        # -----------------------------------------------
        # Tab 0: Thu thập (toàn bộ layout cũ)
        # -----------------------------------------------
        acq_page = QWidget()
        main_layout = QVBoxLayout(acq_page)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(10)
        self.splitter = splitter

        # --- Left Panel ---
        left_panel = QWidget()
        left_panel_lay = QVBoxLayout(left_panel)
        left_panel_lay.setContentsMargins(6, 6, 6, 6)
        left_panel_lay.setSpacing(6)

        # 1. Real-time Data Info (Sticky at top)
        self.display_panel = self._build_display_group()
        left_panel_lay.addWidget(self.display_panel)

        # 2. Tab widget đặt trực tiếp
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_connection_tab(), "🔌 Kết nối")
        self.tabs.addTab(self._build_config_tab(), "⚙️ Cấu hình")
        self.tabs.addTab(self._build_acquisition_tab(), "📈 Thu thập")
        left_panel_lay.addWidget(self.tabs, stretch=1)

        # 3. Connection Status and Button (Sticky at bottom)
        conn_bottom_widget = QWidget()
        conn_bottom_lay = QVBoxLayout(conn_bottom_widget)
        conn_bottom_lay.setContentsMargins(2, 4, 2, 2)
        conn_bottom_lay.setSpacing(4)
        
        btn_row = QHBoxLayout()
        self.led_label = QLabel("●")
        self.led_label.setObjectName("led_off")
        self.led_label.setFont(QFont('Segoe UI', 10))
        btn_row.addWidget(self.led_label)
        
        self.btn_connect = QPushButton("🔗 Kết nối")
        self._update_connect_btn_style()
        self.btn_connect.clicked.connect(self._toggle_connect)
        self.btn_connect.setMinimumHeight(32)
        self.btn_connect.setFont(QFont('Segoe UI', 10, QFont.Bold))
        btn_row.addWidget(self.btn_connect, stretch=1)
        
        conn_bottom_lay.addLayout(btn_row)
        
        self.lbl_conn_status = QLabel("⚪ Chưa kết nối")
        self.lbl_conn_status.setStyleSheet("color: #757575;") 
        conn_bottom_lay.addWidget(self.lbl_conn_status)

        left_panel_lay.addWidget(conn_bottom_widget)

        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(16777215)

        # --- Right Panel ---
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(4, 0, 0, 0)
        right_lay.setSpacing(6)
        
        right_lay.addWidget(self._build_chart_group(), stretch=1)
        right_lay.addWidget(self._build_log_group())
        
        self.btn_toggle_theme = QPushButton()
        self._update_theme_btn_text()
        self.btn_toggle_theme.setFixedHeight(30)
        self.btn_toggle_theme.clicked.connect(self._toggle_theme)
        right_lay.addWidget(self.btn_toggle_theme)

        splitter.addWidget(left_panel)
        splitter.addWidget(right)
        splitter.setSizes([310, 970])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)

        self.main_tabs.addTab(acq_page, "📡 Thu thập")

        # -----------------------------------------------
        # Tab 1 + 2: Plot Viewer + Converter
        # -----------------------------------------------
        if _HAS_PLOT_VIEWER:
            # Plot Viewer: tạo TorquePlotViewer, chỉ lấy plot_tab (loại bỏ tab Converter bên trong)
            self._plot_viewer = TorquePlotViewer()
            plot_viewer_widget = QWidget()
            pv_lay = QVBoxLayout(plot_viewer_widget)
            pv_lay.setContentsMargins(0, 0, 0, 0)
            # Lấy riêng plot_tab (không lấy toàn bộ tabs widget có chứa Converter)
            pv_tab = self._plot_viewer.plot_tab
            pv_tab.setParent(plot_viewer_widget)
            pv_lay.addWidget(pv_tab)
            self.main_tabs.addTab(plot_viewer_widget, "📊 Plot Viewer")

            # Converter: tạo ConvertWidget instance
            self._converter = ConvertWidget()
            self.main_tabs.addTab(self._converter, "🔄 Converter")

            # Kết nối Import Button của Converter rẽ sang Plot Viewer
            self._converter.import_requested.connect(self._on_converter_import_requested)

    def showEvent(self, event):
        """Set initial splitter sizes as a proportion of the window width on first show.

        This ensures the left panel occupies a sensible fraction (e.g. 35%)
        of the window when the app starts, avoiding clipped controls.
        """
        super().showEvent(event)
        try:
            total = max(800, self.width())
            left_w = int(total * 0.35)
            right_w = max(300, total - left_w)
            # Apply sizes to splitter
            if hasattr(self, 'splitter'):
                self.splitter.setSizes([left_w, right_w])
        except Exception:
            pass



    # --- Connection Tab ---
    def _build_connection_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # Protocol selector
        proto_grp = QGroupBox("🔌 Giao thức")
        pg = QGridLayout()
        pg.setContentsMargins(8, 10, 8, 8)
        pg.setSpacing(6)
        pg.addWidget(QLabel("Loại:"), 0, 0)
        self.combo_proto = QComboBox()
        self.combo_proto.setSizeAdjustPolicy(QComboBox.AdjustToContents) # Proto thì tĩnh và ngắn, kệ nó
        self.combo_proto.addItems(["Modbus RTU", "Modbus TCP"])
        self.combo_proto.currentTextChanged.connect(self._on_proto_changed)
        pg.addWidget(self.combo_proto, 0, 1)
        pg.setColumnStretch(1, 1)
        proto_grp.setLayout(pg); lay.addWidget(proto_grp)

        # RTU
        self.grp_rtu = QGroupBox("📡 RTU (RS-485)")
        rg = QGridLayout()
        rg.setContentsMargins(8, 10, 8, 8)
        rg.setSpacing(6)
        rg.addWidget(QLabel("COM Port:"), 0, 0)
        self.combo_com = QComboBox()
        self.combo_com.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_com.setMinimumContentsLength(10)
        rg.addWidget(self.combo_com, 0, 1)
        # Use a QToolButton with system reload icon to avoid emoji clipping
        btn_scan = QToolButton()
        btn_scan.setAutoRaise(True)
        btn_scan.setToolTip("Làm mới COM ports")
        try:
            icon = QApplication.style().standardIcon(QStyle.SP_BrowserReload)
        except Exception:
            icon = QApplication.style().standardIcon(QStyle.SP_DialogResetButton)
        btn_scan.setIcon(icon)
        btn_scan.setFixedSize(30, 28)
        btn_scan.clicked.connect(self._scan_com_ports)
        rg.addWidget(btn_scan, 0, 2)
        rg.addWidget(QLabel("Baudrate:"), 1, 0)
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["9600","19200","38400","57600","115200"])
        rg.addWidget(self.combo_baud, 1, 1, 1, 2)
        rg.addWidget(QLabel("Parity:"), 2, 0)
        self.combo_parity = QComboBox()
        self.combo_parity.addItems(["None (N)","Even (E)","Odd (O)"])
        rg.addWidget(self.combo_parity, 2, 1, 1, 2)
        rg.setColumnStretch(1, 1)
        self.grp_rtu.setLayout(rg); lay.addWidget(self.grp_rtu)

        # TCP
        self.grp_tcp = QGroupBox("🌐 TCP/IP")
        tg = QGridLayout()
        tg.addWidget(QLabel("IP:"), 0, 0)
        self.combo_ip = QComboBox(); self.combo_ip.setEditable(True)
        self.combo_ip.addItem("192.168.1.100")
        tg.addWidget(self.combo_ip, 0, 1)
        tg.addWidget(QLabel("Port:"), 1, 0)
        self.spin_tcp_port = QSpinBox(); self.spin_tcp_port.setRange(1,65535)
        self.spin_tcp_port.setValue(502)
        tg.addWidget(self.spin_tcp_port, 1, 1)
        self.grp_tcp.setLayout(tg)
        self.grp_tcp.setVisible(False)
        lay.addWidget(self.grp_tcp)

        # Slave ID
        slave_grp = QGroupBox("📋 Slave")
        sg = QGridLayout()
        sg.setContentsMargins(8, 10, 8, 8)
        sg.setSpacing(6)
        sg.addWidget(QLabel("Slave ID:"), 0, 0)
        self.spin_slave = QSpinBox(); self.spin_slave.setRange(1,247)
        self.spin_slave.setValue(1)
        sg.addWidget(self.spin_slave, 0, 1)
        sg.setColumnStretch(1, 1)
        slave_grp.setLayout(sg); lay.addWidget(slave_grp)

        lay.addStretch()
        self._scan_com_ports()
        return w

    # --- Config Tab ---
    def _build_config_tab(self) -> QWidget:
        w = QWidget()
        main_lay = QVBoxLayout(w)
        main_lay.setContentsMargins(8, 8, 8, 8)
        main_lay.setSpacing(8)

        # 1. Nhóm Cảm biến & Hiệu chuẩn
        sensor_grp = QGroupBox("📊 Cảm biến & Hiệu chuẩn")
        sg = QGridLayout()
        sg.setContentsMargins(8, 10, 8, 8)
        sg.setSpacing(6)

        sg.addWidget(QLabel("Đơn vị đo:"), 0, 0)
        self.combo_unit = QComboBox()
        self.combo_unit.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_unit.setMinimumContentsLength(5)
        for k, v in UNITS.items(): self.combo_unit.addItem(f"{k}: {v}", k)
        sg.addWidget(self.combo_unit, 0, 1)

        sg.addWidget(QLabel("Chế độ đo:"), 1, 0)
        self.combo_mtype = QComboBox()
        self.combo_mtype.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_mtype.setMinimumContentsLength(10)
        self.combo_mtype.addItems(["0: 2 chiều (+/-)", "1: 1 chiều (+)"])
        sg.addWidget(self.combo_mtype, 1, 1)

        sg.addWidget(QLabel("Full Scale (Nm):"), 2, 0)
        self.spin_fs = QDoubleSpinBox()
        self.spin_fs.setRange(0.1, 1000000); self.spin_fs.setDecimals(2); self.spin_fs.setValue(49.70)
        sg.addWidget(self.spin_fs, 2, 1)

        sg.addWidget(QLabel("Sensitivity (mV/V):"), 3, 0)
        self.spin_sens = QDoubleSpinBox()
        self.spin_sens.setRange(0.001, 100); self.spin_sens.setDecimals(4); self.spin_sens.setValue(1.9880)
        sg.addWidget(self.spin_sens, 3, 1)

        sensor_grp.setLayout(sg); main_lay.addWidget(sensor_grp)

        # 2. Nhóm Ổn định & Lọc
        stable_grp = QGroupBox("🛡️ Ổn định & Lọc")
        stg = QGridLayout()

        stg.addWidget(QLabel("Mức lọc nhiễu:"), 0, 0)
        self.combo_filter = QComboBox()
        self.combo_filter.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_filter.setMinimumContentsLength(10)
        for k, v in FILTER_LABELS.items(): self.combo_filter.addItem(v, k)
        stg.addWidget(self.combo_filter, 0, 1)

        stg.setContentsMargins(8, 12, 8, 8)
        stg.setSpacing(6)
        stable_grp.setLayout(stg)
        main_lay.addWidget(stable_grp)


        # Buttons
        btn_row = QHBoxLayout()
        btn_write = QPushButton("📝 Ghi cấu hình")
        btn_write.clicked.connect(self._write_config)
        btn_read  = QPushButton("📖 Đọc từ thiết bị")
        btn_read.clicked.connect(self._read_config)
        btn_row.addWidget(btn_write); btn_row.addWidget(btn_read)
        main_lay.addLayout(btn_row)

        cmd_grp = QGroupBox("⚡ Lệnh nhanh")
        cg = QHBoxLayout()
        btn_tare = QPushButton("⚖️ Tare (Zero)")
        btn_tare.clicked.connect(self._do_tare)
        btn_rst  = QPushButton("🔄 Restart Device")
        btn_rst.clicked.connect(self._do_restart)
        cg.addWidget(btn_tare); cg.addWidget(btn_rst)
        cmd_grp.setLayout(cg); main_lay.addWidget(cmd_grp)

        main_lay.addStretch()
        return w

    # --- Acquisition Tab ---
    def _build_acquisition_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        sample_grp = QGroupBox("⏱️ Lấy mẫu")
        sg = QGridLayout()
        sg.setContentsMargins(8, 10, 8, 8)
        sg.setSpacing(6)
        sg.addWidget(QLabel("Chu kỳ (ms):"), 0, 0)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 10000)
        self.spin_interval.setValue(DEFAULT_SAMPLE_INTERVAL_MS)
        self.spin_interval.editingFinished.connect(self._on_acquisition_settings_changed)
        sg.addWidget(self.spin_interval, 0, 1)
        sg.addWidget(QLabel("Cửa sổ biểu đồ (s):"), 1, 0)
        self.spin_window = QSpinBox()
        self.spin_window.setRange(10, 600); self.spin_window.setValue(60)
        self.spin_window.editingFinished.connect(self._on_acquisition_settings_changed)
        sg.addWidget(self.spin_window, 1, 1)

        # --- Y Axis Scale ---
        sg.addWidget(QLabel("Giới hạn Y (Nm):"), 2, 0)
        self.spin_ymax = QDoubleSpinBox()
        self.spin_ymax.setRange(0.1, 10000); self.spin_ymax.setDecimals(1)
        self.spin_ymax.setValue(5.0)
        self.spin_ymax.valueChanged.connect(lambda _: self._update_plot_limits())
        sg.addWidget(self.spin_ymax, 2, 1)

        self.chk_fixed_y = QCheckBox("Cố định thang đo Y")
        self.chk_fixed_y.setChecked(True)
        self.chk_fixed_y.toggled.connect(lambda _: self._update_plot_limits())
        sg.addWidget(self.chk_fixed_y, 3, 0, 1, 2)
        sample_grp.setLayout(sg); lay.addWidget(sample_grp)

        rec_grp = QGroupBox("🔴 Ghi dữ liệu")
        rg = QVBoxLayout()
        btns = QHBoxLayout()
        self.btn_rec_start = QPushButton("▶️ Bắt đầu ghi")
        self._update_rec_start_btn_style()
        self.btn_rec_start.clicked.connect(self._start_recording)
        self.btn_rec_stop  = QPushButton("⏹ Dừng ghi")
        self._update_rec_stop_btn_style()
        self.btn_rec_stop.clicked.connect(self._stop_recording)
        self.btn_rec_stop.setEnabled(False)
        # Thêm nút Tare ở tab Thu thập để dễ truy cập
        self.btn_tare_acq = QPushButton("⚖️ Tare")
        # Slightly larger and more prominent
        self.btn_tare_acq.setFixedHeight(36)
        self.btn_tare_acq.setMinimumWidth(100)
        self.btn_tare_acq.setStyleSheet("font-size:11pt; font-weight:600;")
        self.btn_tare_acq.clicked.connect(self._do_tare)
        btns.addWidget(self.btn_tare_acq)
        btns.addWidget(self.btn_rec_start); btns.addWidget(self.btn_rec_stop)
        rg.addLayout(btns)

        self.btn_rec_clear = QPushButton("🗑️ Xóa dữ liệu mẫu")
        self._update_rec_clear_btn_style()
        self.btn_rec_clear.clicked.connect(self._clear_samples)
        self.btn_rec_clear.setEnabled(False)
        rg.addWidget(self.btn_rec_clear)
        rec_grp.setLayout(rg); lay.addWidget(rec_grp)

        export_grp = QGroupBox("💾 Xuất dữ liệu")
        eg = QVBoxLayout()
        eg.setSpacing(6)
        for exp in self._exporters:
            btn = QPushButton(f"📄 {exp.display_name}")
            btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
            btn.clicked.connect(lambda checked, e=exp: self._export(e))
            eg.addWidget(btn)

        export_grp.setLayout(eg); lay.addWidget(export_grp)

        # --- Import to Plot Viewer / Converter ---
        if _HAS_PLOT_VIEWER:
            import_grp = QGroupBox("📥 Import dữ liệu sang công cụ khác")
            ig = QVBoxLayout()
            ig.setSpacing(6)

            btn_to_plot = QPushButton("📊 Import to Plot Viewer")
            btn_to_plot.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            btn_to_plot.clicked.connect(self._import_to_plot_viewer)
            ig.addWidget(btn_to_plot)

            btn_to_conv = QPushButton("🔄 Import to Converter")
            btn_to_conv.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
            btn_to_conv.clicked.connect(self._import_to_converter)
            ig.addWidget(btn_to_conv)

            import_grp.setLayout(ig); lay.addWidget(import_grp)

        lay.addStretch()
        return w

    # --- Display group (Redesigned to be compact like draw_plot.py) ---
    def _build_display_group(self) -> QWidget:
        grp = QGroupBox("📊 Real-time Data Info")
        grp.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        g = QGridLayout()
        g.setContentsMargins(6, 8, 6, 6)
        g.setSpacing(4)

        # Current Torque - Styled prominently but not excessively large
        self.lbl_torque = QLabel("0.000 Nm")
        self.lbl_torque.setFont(QFont('Segoe UI', 14, QFont.Bold))
        self.lbl_torque.setStyleSheet("color: #1976D2;") 
        g.addWidget(QLabel("Torque:"), 0, 0)
        g.addWidget(self.lbl_torque, 0, 1, 1, 3)

        # Row 1: Status & Pts
        g.addWidget(QLabel("Status:"), 1, 0)
        self.lbl_stable = QLabel("---")
        self.lbl_stable.setStyleSheet("font-weight: bold; font-size: 11px;")
        g.addWidget(self.lbl_stable, 1, 1)

        g.addWidget(QLabel("Samples:"), 1, 2)
        self.lbl_count = QLabel("0")
        self.lbl_count.setStyleSheet("font-weight: bold;")
        g.addWidget(self.lbl_count, 1, 3)

        # Row 2: Tare & Time
        g.addWidget(QLabel("Tare:"), 2, 0)
        self.lbl_tare = QLabel("--- Nm")
        g.addWidget(self.lbl_tare, 2, 1)

        g.addWidget(QLabel("Time:"), 2, 2)
        self.lbl_rectime = QLabel("0.0 s")
        g.addWidget(self.lbl_rectime, 2, 3)

        # Row 3: Max
        info_style = "font-weight: bold; font-size: 12px;"
        g.addWidget(QLabel("Maximum:"), 3, 0)
        self.lbl_max = QLabel("---")
        self.lbl_max.setStyleSheet(f"color: #1976D2; {info_style}")
        g.addWidget(self.lbl_max, 3, 1)

        # Row 4: Min
        g.addWidget(QLabel("Minimum:"), 4, 0)
        self.lbl_min = QLabel("---")
        self.lbl_min.setStyleSheet(f"color: #D32F2F; {info_style}")
        g.addWidget(self.lbl_min, 4, 1)

        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)
        grp.setLayout(g)
        return grp



    # --- Chart group ---
    def _build_chart_group(self) -> QWidget:
        grp = QGroupBox("📈 Torque – Time")
        lay = QVBoxLayout()
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(2)

        self.plot = RealTimePlot(
            title="Torque vs Time",
            xlabel="Time (s)", ylabel="Torque (Nm)",
            max_window_s=DEFAULT_TIME_WINDOW_S,
        )
        
        # Thêm CustomToolbar thay vì NavigationToolbar mặc định
        self.toolbar = CustomToolbar(self.plot, self)
        self.toolbar.setMaximumHeight(32)
        lay.addWidget(self.toolbar)
        lay.addWidget(self.plot)

        btn_row = QHBoxLayout()
        self.btn_pause_chart = QPushButton("⏸ Dừng vẽ")
        self.btn_pause_chart.setCheckable(True)
        self.btn_pause_chart.toggled.connect(self._toggle_pause_chart)
        btn_row.addWidget(self.btn_pause_chart)

        btn_clear = QPushButton("🗑️ Xóa biểu đồ")
        btn_clear.clicked.connect(self._clear_chart)
        btn_row.addWidget(btn_clear)
        
        lay.addLayout(btn_row)
        grp.setLayout(lay)
        return grp

    def _toggle_pause_chart(self, checked: bool):
        self._chart_paused = checked
        if checked:
            self.btn_pause_chart.setText("▶️ Tiếp tục vẽ")
            self._log("⏸ Đã tạm dừng cập nhật Torque-Time")
        else:
            self.btn_pause_chart.setText("⏸ Dừng vẽ")
            self._log("▶️ Tiếp tục cập nhật Torque-Time")



    def _update_theme_btn_text(self):
        if self._is_dark:
            self.btn_toggle_theme.setText("☀️  Giao diện Sáng")
            self.btn_toggle_theme.setStyleSheet(
                "background:#313244; color:#cdd6f4; font-size:9pt; border-radius:4px; border:1px solid #45475a;"
            )
        else:
            self.btn_toggle_theme.setText("🌙  Giao diện Tối")
            self.btn_toggle_theme.setStyleSheet(
                "background:#e0e0e0; color:#333; font-size:9pt; border-radius:4px; border:1px solid #ccc;"
            )

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self._apply_theme(self._is_dark)
        self._update_theme_btn_text()
        # Lưu vào settings
        ui = self._settings.load_ui_settings()
        ui['dark_theme'] = self._is_dark
        self._settings.save_ui_settings(ui)

    def _apply_theme(self, dark: bool):
        """Áp dụng Dark hoặc Light theme cho toàn app + cập nhật màu chart."""
        self.setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)
        
        # Cập nhật màu sắc cho các label thông số
        torque_color = "#89b4fa" if dark else "#1976D2"
        max_color    = "#a6e3a1" if dark else "#1976D2"
        min_color    = "#f38ba8" if dark else "#D32F2F"
        
        if hasattr(self, 'lbl_torque'):
            self.lbl_torque.setStyleSheet(f"color: {torque_color};")
            self.lbl_max.setStyleSheet(f"color: {max_color}; font-weight: bold; font-size: 12px;")
            self.lbl_min.setStyleSheet(f"color: {min_color}; font-weight: bold; font-size: 12px;")

        if hasattr(self, 'lbl_conn_status'):
            status_color = "#a6adc8" if dark else "#757575"
            self.lbl_conn_status.setStyleSheet(f"color: {status_color};")

        # Cập nhật style nút ghi (vì có màu riêng)
        if hasattr(self, 'btn_rec_start'):
            self._update_rec_start_btn_style()
            self._update_rec_stop_btn_style()
            self._update_rec_clear_btn_style()

        # Cập nhật màu chart theo theme
        if hasattr(self, 'plot'):
            self._apply_chart_theme(dark)

    def _apply_chart_theme(self, dark: bool):
        ax = self.plot.ax
        fig = self.plot.fig
        if dark:
            fig.patch.set_facecolor('#1e1e2e')
            ax.set_facecolor('#181825')
            ax.tick_params(colors='#bac2de')
            ax.title.set_color('#cdd6f4')
            ax.xaxis.label.set_color('#bac2de')
            ax.yaxis.label.set_color('#bac2de')
            ax.grid(True, alpha=0.15, color='#a6adc8')
            for spine in ax.spines.values():
                spine.set_edgecolor('#45475a')
            self.plot.line.set_color('#89b4fa')
        else:
            fig.patch.set_facecolor('#f5f5f5')
            ax.set_facecolor('#ffffff')
            ax.tick_params(colors='#212121')
            ax.title.set_color('#1565c0')
            ax.xaxis.label.set_color('#424242')
            ax.yaxis.label.set_color('#424242')
            ax.grid(True, alpha=0.4, color='#dddddd')
            for spine in ax.spines.values():
                spine.set_edgecolor('#bdbdbd')
            self.plot.line.set_color('#1976d2')
        self.plot.draw_idle()

    # --- Log group ---
    def _build_log_group(self) -> QWidget:
        grp = QGroupBox("📝 Terminal Log")
        lay = QVBoxLayout()
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(140)
        lay.addWidget(self.log_box)
        grp.setLayout(lay)
        return grp

    # --- Helper to update button styles based on state and theme ---
    def _update_connect_btn_style(self):
        if self._connected:
            color = "#F44336" if not self._is_dark else "#f38ba8" # Red
            text_color = "white" if not self._is_dark else "#1e1e2e"
            self.btn_connect.setText("🔌 Ngắt kết nối")
        else:
            color = "#4CAF50" if not self._is_dark else "#a6e3a1" # Green
            text_color = "white" if not self._is_dark else "#1e1e2e"
            self.btn_connect.setText("🔗 Kết nối")
        self.btn_connect.setStyleSheet(f"background-color: {color}; color: {text_color}; font-weight: bold; padding: 8px;")

    def _update_rec_start_btn_style(self):
        color = "#FF9800" if not self._is_dark else "#fab387" # Orange
        text_color = "white" if not self._is_dark else "#1e1e2e"
        self.btn_rec_start.setStyleSheet(f"background-color: {color}; color: {text_color}; font-weight: bold; height: 28px;")

    def _update_rec_stop_btn_style(self):
        color = "#F44336" if not self._is_dark else "#f38ba8" # Red
        text_color = "white" if not self._is_dark else "#1e1e2e"
        self.btn_rec_stop.setStyleSheet(f"background-color: {color}; color: {text_color}; font-weight: bold; height: 28px;")

    def _update_rec_clear_btn_style(self):
        color = "#757575" if not self._is_dark else "#45475a" # Gray
        text_color = "white" if not self._is_dark else "#cdd6f4"
        self.btn_rec_clear.setStyleSheet(f"background-color: {color}; color: {text_color}; font-weight: bold; height: 28px;")

    # ===========================================================
    # LOAD / SAVE SETTINGS

    # ===========================================================

    def _load_settings_to_ui(self):
        c = self._conn_cfg
        # Protocol
        idx = 0 if c.mode == 'RTU' else 1
        self.combo_proto.setCurrentIndex(idx)
        # RTU
        baud_map = {"9600":0,"19200":1,"38400":2,"57600":3,"115200":4}
        self.combo_baud.setCurrentIndex(baud_map.get(str(c.baudrate), 0))
        parity_map = {"N":0,"E":1,"O":2}
        self.combo_parity.setCurrentIndex(parity_map.get(c.parity, 0))
        self.combo_ip.setCurrentText(c.ip)
        self.spin_tcp_port.setValue(c.tcp_port)
        self.spin_slave.setValue(c.slave_id)

        # Device (Config Tab)
        d = self._dev_cfg
        self.combo_unit.setCurrentIndex(d.measure_unit)
        self.combo_mtype.setCurrentIndex(d.measure_type)
        self.combo_filter.setCurrentIndex(d.filter_level)
        
        self.spin_fs.setValue(d.cell_full_scale)
        self.spin_sens.setValue(d.cell_sensitivity)
        
        # UI settings (Acquisition / Plot)
        ui = self._settings.load_ui_settings()
        if 'interval_ms' in ui:
            self.spin_interval.setValue(int(ui['interval_ms']))
        if 'window_s' in ui:
            self.spin_window.setValue(int(ui['window_s']))
        if 'y_max' in ui:
            self.spin_ymax.setValue(float(ui['y_max']))
        if 'fixed_y' in ui:
            self.chk_fixed_y.setChecked(bool(ui['fixed_y']))
        
        # Apply initial plot limits
        self._update_plot_limits()

    def _save_settings_from_ui(self):
        parity_map = {0:'N', 1:'E', 2:'O'}
        conn = ConnectionConfig(
            mode='RTU' if 'RTU' in self.combo_proto.currentText() else 'TCP',
            port=self.combo_com.currentData() or 'COM1',
            baudrate=int(self.combo_baud.currentText()),
            parity=parity_map[self.combo_parity.currentIndex()],
            ip=self.combo_ip.currentText(),
            tcp_port=self.spin_tcp_port.value(),
            slave_id=self.spin_slave.value(),
        )
        self._settings.save_connection_config(conn)

        dev = DeviceConfig(
            measure_unit=self.combo_unit.currentData() if self.combo_unit.currentData() is not None else 8,
            measure_type=self.combo_mtype.currentIndex(),
            filter_level=self.combo_filter.currentData() if self.combo_filter.currentData() is not None else 3,
            
            cell_full_scale=self.spin_fs.value(),
            cell_sensitivity=self.spin_sens.value(),
            
            # Giữ nguyên cấu hình cũ cho các thông số không còn trên UI
            std_weight=self._dev_cfg.std_weight,
            analog_out_type=self._dev_cfg.analog_out_type,
            dio_type=self._dev_cfg.dio_type,
            calib_mode=self._dev_cfg.calib_mode,
            delta_weight=self._dev_cfg.delta_weight,
            delta_time=self._dev_cfg.delta_time,
            adc_sps=self._dev_cfg.adc_sps,
            resolution_mode=self._dev_cfg.resolution_mode,
            factory_tare=self._dev_cfg.factory_tare,
            
            target_address=self._dev_cfg.target_address,
            target_baud=self._dev_cfg.target_baud,
            target_parity=self._dev_cfg.target_parity,
            
            slave_id=self.spin_slave.value(),
        )
        self._settings.save_device_config(dev)
        self._settings.save_ui_settings({
            'interval_ms': self.spin_interval.value(),
            'window_s':    self.spin_window.value(),
            'y_max':       self.spin_ymax.value(),
            'fixed_y':     self.chk_fixed_y.isChecked(),
        })

    def _update_plot_limits(self):
        """Cập nhật giới hạn trục Y của biểu đồ dựa trên UI."""
        if self.chk_fixed_y.isChecked():
            limit = self.spin_ymax.value()
            # Sử dụng logic mới: giới hạn tối thiểu là [-limit, limit]
            self.plot.set_y_limits(limit)
        else:
            self.plot.set_y_limits(None)

    def _on_acquisition_settings_changed(self):
        """Áp dụng và lưu cài đặt thu thập ngay lập tức khi thay đổi trên UI."""
        interval = self.spin_interval.value()
        window = self.spin_window.value()
        
        # 1. Áp dụng ngay vào logic đang chạy
        self._collector.set_interval(interval)
        self.plot.max_window_s = window
        if self._recording:
            self._session.sample_interval_ms = interval
        
        # 2. Lưu lại vào file settings.json (nếu đã init UI xong)
        if hasattr(self, '_settings'):
             ui = self._settings.load_ui_settings()
             ui['interval_ms'] = interval
             ui['window_s'] = window
             ui['y_max'] = self.spin_ymax.value()
             ui['fixed_y'] = self.chk_fixed_y.isChecked()
             self._settings.save_ui_settings(ui)

    # ===========================================================
    # CONNECTION
    # ===========================================================

    def _on_proto_changed(self, text: str):
        is_rtu = 'RTU' in text
        self.grp_rtu.setVisible(is_rtu)
        self.grp_tcp.setVisible(not is_rtu)

    def _scan_com_ports(self):
        self.combo_com.clear()
        ports = serial.tools.list_ports.comports()
        for p in sorted(ports, key=lambda x: x.device):
            self.combo_com.addItem(f"{p.device} – {p.description}", p.device)
        if not ports:
            self.combo_com.addItem("(Trống)")

    def _toggle_connect(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        # Lấy client từ factory (sẽ được inject vào main.py)
        # Ở đây dùng event để signal thành công/thất bại
        from infrastructure.modbus_rtu_client import ModbusRtuClient
        from infrastructure.modbus_tcp_client import ModbusTcpClient

        parity_map = {0:'N', 1:'E', 2:'O'}
        sid = self.spin_slave.value()

        try:
            if 'RTU' in self.combo_proto.currentText():
                port = self.combo_com.currentData()
                if not port:
                    self._log("❌ Chưa chọn cổng COM"); return
                baud = int(self.combo_baud.currentText())
                par  = parity_map[self.combo_parity.currentIndex()]
                new_client = ModbusRtuClient(port=port, baudrate=baud, parity=par)
            else:
                ip   = self.combo_ip.currentText()
                port = self.spin_tcp_port.value()
                new_client = ModbusTcpClient(host=ip, port=port)

            if new_client.connect():
                # Swap client trong services
                self._collector._client  = new_client
                self._config_svc._client = new_client
                self._collector._slave_id = sid

                self._connected = True
                self._ref_time  = time.monotonic()
                self._update_connect_btn_style()
                self.led_label.setObjectName("led_on")
                self._apply_led_style()
                self.lbl_conn_status.setText("🟢 Đã kết nối")


                self._collector.set_interval(self.spin_interval.value())
                self._collector.start()
                self._save_settings_from_ui()
                self._log(f"✅ Kết nối thành công (Slave {sid})")
            else:
                self._log("❌ Không thể kết nối")
        except Exception as e:
            self._log(f"❌ Lỗi kết nối: {e}")

    def _disconnect(self):
        self._collector.stop()
        if self._collector._client:
            self._collector._client.disconnect()
        self._connected = False
        self._update_connect_btn_style()
        self.led_label.setObjectName("led_off")
        self._apply_led_style()
        self.lbl_conn_status.setText("⚪ Chưa kết nối")
        self._log("🔌 Đã ngắt kết nối")

    def _apply_led_style(self):
        if self.led_label.objectName() == "led_on":
            color = "#4CAF50" if not self._is_dark else "#a6e3a1"
        else:
            color = "#F44336" if not self._is_dark else "#f38ba8"
        self.led_label.setStyleSheet(f"color: {color}; font-size: 20px;")


    # ===========================================================
    # DATA CALLBACKS
    # ===========================================================

    def _on_status_received(self, status: DeviceStatus):
        """Gọi từ main thread (qua Qt signal). Cập nhật UI live."""
        self._last_status = status  # Lưu trạng thái mới nhất
        elapsed = time.monotonic() - self._ref_time

        # Cập nhật giá trị hiện tại
        self.lbl_torque.setText(f"{status.net_weight:.3f} Nm")
        self.lbl_tare.setText(f"{status.tare_weight:.3f} Nm")
        self.lbl_max.setText(f"{status.max_net_weight:.3f}")
        self.lbl_min.setText(f"{status.min_net_weight:.3f}")

        if status.is_stable:
            self.lbl_stable.setText("🟢 Stable")
            color = "#4CAF50" if not self._is_dark else "#a6e3a1"
            self.lbl_stable.setStyleSheet(f"color: {color};")
        elif status.is_fullscale:
            self.lbl_stable.setText("🔴 Full Scale!")
            color = "#F44336" if not self._is_dark else "#f38ba8"
            self.lbl_stable.setStyleSheet(f"color: {color};")
        else:
            self.lbl_stable.setText("🟡 Unstable")
            color = "#FF9800" if not self._is_dark else "#f9e2af"
            self.lbl_stable.setStyleSheet(f"color: {color};")


        # Chart update (nếu không đang PAUSE)
        if not self._chart_paused:
            self.plot.add_point(elapsed, status.net_weight)

        # Ghi session nếu đang recording
        if self._recording:
            interval_s = self._session.sample_interval_ms / 1000.0
            elapsed_time = time.monotonic() - self._start_time
            expected_samples = int(elapsed_time / interval_s)
            
            # Tự động sinh thêm các mẫu bị thiếu để đảm bảo đúng tần số yêu cầu
            # (Ví dụ 2ms -> đúng 500 mẫu/giây) bằng cách dùng giá trị gần nhất
            while self._session.count <= expected_samples:
                rec_time = self._session.count * interval_s
                sample = SampleData(
                    time_s=rec_time,
                    torque_Nm=status.net_weight, # Lặp lại giá trị mới nhất
                    stable=status.is_stable,
                    timestamp=time.time(),
                )
                self._session.samples.append(sample)
                
            self.lbl_count.setText(str(self._session.count))
            self.lbl_rectime.setText(f"{elapsed_time:.3f} s")

    def _on_error(self, msg: str):
        self._log(f"⚠️ {msg}")
        if self._connected:
            self.lbl_conn_status.setText("🟡 Lỗi đọc Modbus")

    # ===========================================================
    # CONFIG
    # ===========================================================

    def _write_config(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
            
        try:
            cfg = DeviceConfig(
                measure_unit=self.combo_unit.currentData() if self.combo_unit.currentData() is not None else 8,
                measure_type=self.combo_mtype.currentIndex(),
                analog_out_type=self._dev_cfg.analog_out_type,
                dio_type=self._dev_cfg.dio_type,
                calib_mode=self.combo_calib.currentIndex() if hasattr(self, 'combo_calib') else self._dev_cfg.calib_mode,
                
                cell_full_scale=self.spin_fs.value(),
                cell_sensitivity=self.spin_sens.value(),
                
                std_weight=self._dev_cfg.std_weight,
                delta_weight=self._dev_cfg.delta_weight,
                delta_time=self._dev_cfg.delta_time,
                
                filter_level=self.combo_filter.currentData() if self.combo_filter.currentData() is not None else 3,
                resolution_mode=self._dev_cfg.resolution_mode,
                factory_tare=self._dev_cfg.factory_tare,
                
                target_address=self._dev_cfg.target_address,
                target_baud=self._dev_cfg.target_baud,
                target_parity=self._dev_cfg.target_parity,
                
                slave_id=self.spin_slave.value(),
            )
            
            self._log("⏳ Đang ghi cấu hình...")
            ok, failed_fields = self._config_svc.write_config(cfg)
            
            if ok:
                self._log("✅ Đã ghi cấu hình thành công")
                self._settings.save_device_config(cfg)
                self._dev_cfg = cfg
            else:
                err_msg = ", ".join(failed_fields)
                self._log(f"❌ Ghi thất bại tại: {err_msg}")
        except Exception as e:
            self._log(f"❌ Lỗi xử lý cấu hình: {e}")

    def _read_config(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        
        cfg = self._config_svc.read_config(self.spin_slave.value())
        if cfg:
            self.combo_unit.setCurrentIndex(cfg.measure_unit)
            self.combo_mtype.setCurrentIndex(cfg.measure_type)
            
            self.spin_fs.setValue(cfg.cell_full_scale)
            self.spin_sens.setValue(cfg.cell_sensitivity)
            
            self.combo_filter.setCurrentIndex(cfg.filter_level)
            
            self._dev_cfg = cfg
            self._log(f"📖 Đọc thành công: Unit={cfg.measure_unit}, FS={cfg.cell_full_scale:.2f}, Sens={cfg.cell_sensitivity:.4f}")
        else:
            self._log("❌ Không đọc được cấu hình từ thiết bị")

    def _do_tare(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        
        # Check ổn định từ manual Seneca ZE-SG3 (nên tare khi stable)
        if self._last_status and not self._last_status.is_stable:
            self._log("⚠️ Cảnh báo: Trọng lượng không ổn định. Lệnh Tare có thể bị thiết bị từ chối.")
        
        # CMD_TARE (49914) ghi vào Flash - bền vững nhưng chậm
        # CMD_TARE_RAM (49594) ghi vào RAM - nhanh hơn, dùng cho tare thường xuyên
        ok = self._config_svc.send_command(CMD_TARE, self.spin_slave.value())
        if ok:
            self._log("⚖️ Đã gửi lệnh Tare (49914 → Flash)")
        else:
            self._log("❌ Lỗi Tare (Kiểm tra ổn định hoặc Timeout)")

    def _do_restart(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        ok = self._config_svc.send_command(CMD_RESTART, self.spin_slave.value())
        self._log("🔄 Đã gửi lệnh Restart (43948)" if ok else "❌ Lỗi Restart")

    def _do_tare_ram(self):
        """Tare lưu RAM – nhanh, mất khi restart."""
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        if self._last_status and not self._last_status.is_stable:
            self._log("⚠️ Cảnh báo: Trọng lượng không ổn định.")
        ok = self._config_svc.tare_ram(self.spin_slave.value())
        if ok:
            self._log("⚖️ Đã gửi lệnh Tare RAM (49594)")
        else:
            self._log("❌ Lỗi Tare RAM")

    def _do_reset_minmax(self):
        """Reset cả Min và Max Net Weight."""
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        sid = self.spin_slave.value()
        ok_max = self._config_svc.reset_max(sid)
        ok_min = self._config_svc.reset_min(sid)
        if ok_max and ok_min:
            self._log("🔁 Đã reset Min/Max thành công")
        else:
            self._log(f"⚠️ Reset Min/Max: Max={'OK' if ok_max else 'FAIL'}, Min={'OK' if ok_min else 'FAIL'}")

    def _calib_step1_tare(self):
        """Bước 1 của Calibration Wizard: Acquire Tare."""
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        if self._last_status and not self._last_status.is_stable:
            self._log("⚠️ Cảm biến chưa ổn định! Chờ 🟢 Stable trước khi Tare.")
            self.lbl_calib_status.setText("🟡 Chờ ổn định...")
            return
        ok = self._config_svc.tare_flash(self.spin_slave.value())
        if ok:
            self.lbl_calib_status.setText("✅ Bước 1 hoàn tất – Đã Tare")
            self._log("🔬 Wizard Bước 1: Tare thành công")
        else:
            self.lbl_calib_status.setText("❌ Tare thất bại")
            self._log("❌ Wizard Bước 1: Tare thất bại")

    def _calib_step3_acquire(self):
        """Bước 3 của Calibration Wizard: Acquire Sample Weight."""
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        if self._last_status and not self._last_status.is_stable:
            self._log("⚠️ Cảm biến chưa ổn định! Chờ 🟢 Stable trước khi hiệu chuẩn.")
            self.lbl_calib_status.setText("🟡 Chờ ổn định...")
            return
        std_weight = self.spin_calib_std.value()
        if std_weight <= 0:
            self._log("❌ Giá trị mẫu phải > 0"); return
        
        self.lbl_calib_status.setText("⏳ Đang hiệu chuẩn...")
        QApplication.processEvents()
        
        ok = self._config_svc.calibrate_with_sample_weight(
            std_weight, self.spin_slave.value()
        )
        if ok:
            self.lbl_calib_status.setText(f"✅ Hiệu chuẩn thành công ({std_weight} Nm)")
            self._log(f"🔬 Wizard Bước 3: Hiệu chuẩn mẫu {std_weight} Nm thành công")
        else:
            self.lbl_calib_status.setText("❌ Hiệu chuẩn thất bại")
            self._log("❌ Wizard Bước 3: Hiệu chuẩn thất bại")

    # ===========================================================
    # RECORDING
    # ===========================================================

    def _start_recording(self):
        self._session = RecordingSession(sample_interval_ms=self.spin_interval.value())
        # Đồng bộ hóa cả hai loại đồng hồ
        now_mono = time.monotonic()
        self._session.start_time = now_mono
        self._start_time = now_mono 
        self._recording = True
        self.btn_rec_start.setEnabled(False)
        self.btn_rec_stop.setEnabled(True)
        self.btn_rec_clear.setEnabled(False)
        self.lbl_count.setText("0")
        self._log("▶️ Bắt đầu ghi dữ liệu")

    def _stop_recording(self):
        self._session.end_time = time.monotonic()
        self._recording = False
        duration = self._session.end_time - self._session.start_time
        self.btn_rec_start.setEnabled(True)
        self.btn_rec_stop.setEnabled(False)
        self.btn_rec_clear.setEnabled(True)
        self._log(f"⏹ Đã dừng ghi – {self._session.count} mẫu, {duration:.1f}s")

    def _clear_samples(self):
        self._session = RecordingSession(sample_interval_ms=self.spin_interval.value())
        self.lbl_count.setText("0")
        self.lbl_rectime.setText("0.0 s")
        self.btn_rec_clear.setEnabled(False)
        self._log("🗑️ Đã xóa dữ liệu mẫu")

    # ===========================================================
    # EXPORT
    # ===========================================================

    def _export(self, exporter: IDataExporter):
        if not self._session.samples:
            self._log("⚠️ Không có dữ liệu"); return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"torque_{ts}{exporter.file_extension}"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Lưu – {exporter.display_name}", default_name,
            f"Files (*{exporter.file_extension})"
        )
        if path:
            ok = exporter.export(self._session, path)
            self._log(f"💾 Xuất {'thành công' if ok else 'thất bại'}: {path}")

    # ===========================================================
    # IMPORT TO PLOT VIEWER / CONVERTER
    # ===========================================================

    def _export_session_to_temp_csv(self) -> str:
        """Export session hiện tại ra file CSV tạm (CTR format) để import vào tool khác."""
        if not self._session.samples:
            return ""
        # Tìm exporter CTR
        ctr_exp = None
        for exp in self._exporters:
            if "CTR" in exp.display_name:
                ctr_exp = exp
                break
        if ctr_exp is None and self._exporters:
            ctr_exp = self._exporters[0]
        if ctr_exp is None:
            return ""
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"ze_sg3_session_{ts}.csv")
        ok = ctr_exp.export(self._session, tmp_path)
        return tmp_path if ok else ""

    def _import_to_plot_viewer(self):
        """Export session CSV → load vào Plot Viewer → nhảy sang tab."""
        if not _HAS_PLOT_VIEWER or not hasattr(self, '_plot_viewer'):
            self._log("⚠️ Plot Viewer chưa sẵn sàng"); return
        if not self._session.samples:
            self._log("⚠️ Không có dữ liệu để import"); return
        tmp = self._export_session_to_temp_csv()
        if not tmp:
            self._log("⚠️ Xuất CSV tạm thất bại"); return
        ok = self._plot_viewer.load_file_from_path(tmp)
        if ok:
            self.main_tabs.setCurrentIndex(1)  # Tab Plot Viewer
            self._log(f"📊 Đã import {self._session.count} mẫu sang Plot Viewer")
        else:
            self._log("⚠️ Import sang Plot Viewer thất bại")

    def _import_to_converter(self):
        """Export session CSV → load vào Converter → nhảy sang tab."""
        if not _HAS_PLOT_VIEWER or not hasattr(self, '_converter'):
            self._log("⚠️ Converter chưa sẵn sàng"); return
        if not self._session.samples:
            self._log("⚠️ Không có dữ liệu để import"); return
        tmp = self._export_session_to_temp_csv()
        if not tmp:
            self._log("⚠️ Xuất CSV tạm thất bại"); return
        try:
            self._converter.input_file = tmp
            self._converter.input_path_label.setText(tmp)
            self._converter.load_input_file(tmp)
            self._converter.btn_convert.setEnabled(True)
            self._converter.output_folder = os.path.dirname(tmp)
            self._converter.output_folder_label.setText(self._converter.output_folder)
            self._converter.update_output_filename()
            self.main_tabs.setCurrentIndex(2)  # Tab Converter
            self._log(f"🔄 Đã import {self._session.count} mẫu sang Converter")
        except Exception as e:
            self._log(f"⚠️ Import sang Converter thất bại: {e}")

    def _on_converter_import_requested(self, path: str):
        """Được gọi khi người dùng bấm Import to Plot Viewer trong tab Converter."""
        if hasattr(self, '_plot_viewer'):
            self._plot_viewer.load_file_from_path_signal(path)
            self.main_tabs.setCurrentIndex(1)  # Tab Plot Viewer
            self._log(f"📊 Đã import Dữ liệu Converter ({os.path.basename(path)}) vào Plot Viewer")

    # ===========================================================
    # UTIL
    # ===========================================================

    def _clear_chart(self):
        self.plot.clear()
        self._ref_time = time.monotonic()
        self._log("🗑️ Đã xóa biểu đồ")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")
        logger.info(msg)

    def closeEvent(self, event):
        """Tự động lưu cài đặt và ngắt kết nối khi đóng app."""
        self._save_settings_from_ui()
        # Lưu theme khi thoát
        ui = self._settings.load_ui_settings()
        ui['dark_theme'] = self._is_dark
        ui['interval_ms'] = self.spin_interval.value()
        ui['window_s'] = self.spin_window.value()
        self._settings.save_ui_settings(ui)
        if self._connected:
            self._disconnect()
        super().closeEvent(event)
