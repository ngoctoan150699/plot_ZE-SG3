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
    QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
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
    CMD_RESTART, CMD_TARE, FILTER_LABELS, UNITS,
    DEFAULT_SAMPLE_INTERVAL_MS, DEFAULT_TIME_WINDOW_S,
)
from domain.entities import (
    ConnectionConfig, DeviceConfig, DeviceStatus,
    RecordingSession, SampleData,
)
from ui.widgets.realtime_plot import RealTimePlot

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
    color: #cba6f7;
    font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton {
    background: #313244;
    border: 1px solid #585b70;
    border-radius: 5px;
    padding: 6px 14px;
    color: #cdd6f4;
}
QPushButton:hover  { background: #45475a; border-color: #89b4fa; }
QPushButton:pressed { background: #181825; }
QPushButton:disabled { color: #585b70; background: #24273a; }
QComboBox, QSpinBox, QDoubleSpinBox {
    background: #313244;
    border: 1px solid #585b70;
    border-radius: 4px;
    padding: 4px 6px;
    color: #cdd6f4;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QTabWidget::pane { border: 1px solid #45475a; border-radius: 4px; }
QTabBar::tab {
    background: #313244;
    color: #a6adc8;
    padding: 7px 16px;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #45475a; color: #cba6f7; font-weight: bold; }
QTabBar::tab:hover:!selected { background: #3d3f56; }
QTextEdit {
    background: #11111b;
    color: #a6e3a1;
    border: 1px solid #313244;
    font-family: Consolas, monospace;
    font-size: 9pt;
}
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #585b70; background: #313244; }
QCheckBox::indicator:checked { background: #89b4fa; border-color: #89b4fa; }
QSplitter::handle { background: #45475a; width: 2px; }
QScrollBar:vertical { background: #1e1e2e; width: 10px; border-radius: 5px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 5px; min-height: 20px; }
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
    padding: 8px 20px;
    border-radius: 6px 6px 0 0;
    margin-right: 4px;
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
        for action in actions:
            if 'subplot' in action.toolTip().lower() or action.text() == 'Subplots':
                self.removeAction(action)
        
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
        self._start_time  = 0.0
        self._ref_time    = 0.0     # Thời gian gốc cho biểu đồ
        self._only_stable = True
        self._chk_stable_only: Optional[QCheckBox] = None

        # === Qt signals → UI callbacks ===
        self._sig_status.connect(self._on_status_received)
        self._sig_error.connect(self._on_error)

        # === Đăng ký callback cho DataCollector ===
        self._collector.on_data(lambda s: self._sig_status.emit(s))
        self._collector.on_error(lambda e: self._sig_error.emit(e))

        # Theme state (load từ settings)
        ui_cfg = settings_repo.load_ui_settings()
        self._is_dark = ui_cfg.get('dark_theme', True)

        self._build_ui()
        self._load_settings_to_ui()
        self._apply_theme(self._is_dark)

    # ===========================================================
    # BUILD UI
    # ===========================================================

    def _build_ui(self):
        self.setWindowTitle("Seneca ZE-SG3 – Torque Acquisition (DYJN-101 50Nm)")
        self.setGeometry(80, 80, 1320, 860)
        self.setMinimumSize(1000, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        splitter = QSplitter(Qt.Horizontal)

        # --- Left Panel (Scrollable) ---
        left_container = QWidget()
        left_lay = QVBoxLayout(left_container)
        left_lay.setContentsMargins(0, 0, 4, 0)
        left_lay.setSpacing(10)

        # 1. Tabs control
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_connection_tab(), "🔌 Kết nối")
        self.tabs.addTab(self._build_config_tab(), "⚙️ Cấu hình")
        self.tabs.addTab(self._build_acquisition_tab(), "📈 Thu thập")
        self.tabs.addTab(self._build_settings_tab(), "🎨 Giao diện")
        left_lay.addWidget(self.tabs)
        
        # 2. Data Info (Moved from right to left to match draw_plot.py)
        self.display_panel = self._build_display_group()
        left_lay.addWidget(self.display_panel)
        
        left_lay.addStretch() # Đẩy mọi thứ lên trên

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_container)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setMinimumWidth(380)
        left_scroll.setMaximumWidth(600)

        # --- Right Panel ---
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(6, 0, 0, 0)
        right_lay.setSpacing(10)
        
        # Right side now only has Chart and Log
        right_lay.addWidget(self._build_chart_group(), stretch=1)
        right_lay.addWidget(self._build_log_group())

        splitter.addWidget(left_scroll)
        splitter.addWidget(right)
        splitter.setSizes([420, 900])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        main_layout.addWidget(splitter)



    # --- Connection Tab ---
    def _build_connection_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)

        # Protocol selector
        proto_grp = QGroupBox("🔌 Giao thức")
        pg = QGridLayout()
        pg.addWidget(QLabel("Loại:"), 0, 0)
        self.combo_proto = QComboBox()
        self.combo_proto.addItems(["Modbus RTU", "Modbus TCP"])
        self.combo_proto.currentTextChanged.connect(self._on_proto_changed)
        pg.addWidget(self.combo_proto, 0, 1)
        pg.setColumnStretch(1, 1)
        proto_grp.setLayout(pg); lay.addWidget(proto_grp)

        # RTU
        self.grp_rtu = QGroupBox("📡 RTU (RS-485)")
        rg = QGridLayout()
        rg.addWidget(QLabel("COM Port:"), 0, 0)
        self.combo_com = QComboBox(); self.combo_com.setMinimumWidth(140)
        rg.addWidget(self.combo_com, 0, 1)
        btn_scan = QPushButton("🔄"); btn_scan.setMaximumWidth(36)
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
        sg.addWidget(QLabel("Slave ID:"), 0, 0)
        self.spin_slave = QSpinBox(); self.spin_slave.setRange(1,247)
        self.spin_slave.setValue(1)
        sg.addWidget(self.spin_slave, 0, 1)
        sg.setColumnStretch(1, 1)
        slave_grp.setLayout(sg); lay.addWidget(slave_grp)

        # Connect button + LED
        btn_row = QHBoxLayout()
        self.led_label = QLabel("●"); self.led_label.setObjectName("led_off")
        btn_row.addWidget(self.led_label)
        self.btn_connect = QPushButton("🔗 Kết nối")
        self._update_connect_btn_style()
        self.btn_connect.clicked.connect(self._toggle_connect)
        btn_row.addWidget(self.btn_connect, stretch=1)

        lay.addLayout(btn_row)
        self.lbl_conn_status = QLabel("⚪ Chưa kết nối")
        lay.addWidget(self.lbl_conn_status)

        lay.addStretch()
        self._scan_com_ports()
        return w

    # --- Config Tab ---
    def _build_config_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        grp = QGroupBox("📊 Cảm biến")
        g = QGridLayout()

        g.addWidget(QLabel("Đơn vị đo:"), 0, 0)
        self.combo_unit = QComboBox()
        for k, v in UNITS.items():
            self.combo_unit.addItem(f"{k}: {v}", k)
        g.addWidget(self.combo_unit, 0, 1)

        g.addWidget(QLabel("Chế độ đo:"), 1, 0)
        self.combo_mtype = QComboBox()
        self.combo_mtype.addItems(["0: Bipolar (2 chiều ↕)", "1: Unipolar (1 chiều ↑)"])
        g.addWidget(self.combo_mtype, 1, 1)

        g.addWidget(QLabel("Full Scale:"), 2, 0)
        self.spin_fs = QDoubleSpinBox()
        self.spin_fs.setRange(0.1, 10000); self.spin_fs.setDecimals(1)
        g.addWidget(self.spin_fs, 2, 1)

        g.addWidget(QLabel("Sensitivity (mV/V):"), 3, 0)
        self.spin_sens = QDoubleSpinBox()
        self.spin_sens.setRange(0.001, 10); self.spin_sens.setDecimals(4)
        g.addWidget(self.spin_sens, 3, 1)

        g.addWidget(QLabel("Lọc nhiễu:"), 4, 0)
        self.combo_filter = QComboBox()
        for k, v in FILTER_LABELS.items():
            self.combo_filter.addItem(v, k)
        g.addWidget(self.combo_filter, 4, 1)

        grp.setLayout(g); lay.addWidget(grp)

        btn_row = QHBoxLayout()
        btn_write = QPushButton("📝 Ghi cấu hình")
        btn_write.clicked.connect(self._write_config)
        btn_read  = QPushButton("📖 Đọc từ thiết bị")
        btn_read.clicked.connect(self._read_config)
        btn_row.addWidget(btn_write); btn_row.addWidget(btn_read)
        lay.addLayout(btn_row)

        cmd_grp = QGroupBox("⚡ Lệnh")
        cg = QHBoxLayout()
        btn_tare = QPushButton("⚖️ Tare (Zero)")
        btn_tare.clicked.connect(self._do_tare)
        btn_rst  = QPushButton("🔄 Restart")
        btn_rst.clicked.connect(self._do_restart)
        cg.addWidget(btn_tare); cg.addWidget(btn_rst)
        cmd_grp.setLayout(cg); lay.addWidget(cmd_grp)

        lay.addStretch()
        return w

    # --- Acquisition Tab ---
    def _build_acquisition_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)

        sample_grp = QGroupBox("⏱️ Lấy mẫu")
        sg = QGridLayout()
        sg.addWidget(QLabel("Chu kỳ (ms):"), 0, 0)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 5000)
        self.spin_interval.setValue(DEFAULT_SAMPLE_INTERVAL_MS)
        self.spin_interval.valueChanged.connect(
            lambda v: self._collector.set_interval(v)
        )
        sg.addWidget(self.spin_interval, 0, 1)
        sg.addWidget(QLabel("Cửa sổ biểu đồ (s):"), 1, 0)
        self.spin_window = QSpinBox()
        self.spin_window.setRange(10, 600); self.spin_window.setValue(60)
        self.spin_window.valueChanged.connect(
            lambda v: setattr(self.plot, 'max_window_s', v)
        )
        sg.addWidget(self.spin_window, 1, 1)
        self._chk_stable_only = QCheckBox("Chỉ ghi mẫu khi ổn định")
        self._chk_stable_only.setChecked(True)
        sg.addWidget(self._chk_stable_only, 2, 0, 1, 2)
        sample_grp.setLayout(sg); lay.addWidget(sample_grp)

        rec_grp = QGroupBox("🔴 Ghi dữ liệu")
        rg = QHBoxLayout()
        self.btn_rec_start = QPushButton("▶️ Bắt đầu ghi")
        self._update_rec_start_btn_style()
        self.btn_rec_start.clicked.connect(self._start_recording)
        self.btn_rec_stop  = QPushButton("⏹ Dừng ghi")
        self._update_rec_stop_btn_style()
        self.btn_rec_stop.clicked.connect(self._stop_recording)
        self.btn_rec_stop.setEnabled(False)
        rg.addWidget(self.btn_rec_start); rg.addWidget(self.btn_rec_stop)
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

        lay.addStretch()
        return w

    # --- Display group (Redesigned to be compact like draw_plot.py) ---
    def _build_display_group(self) -> QWidget:
        grp = QGroupBox("📊 Real-time Data Info")
        grp.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        g = QGridLayout()
        g.setContentsMargins(10, 12, 10, 10)
        g.setSpacing(8)

        # Current Torque - Styled prominently but not excessively large
        self.lbl_torque = QLabel("0.000 Nm")
        self.lbl_torque.setFont(QFont('Segoe UI', 18, QFont.Bold))
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
        info_style = "font-weight: bold; font-size: 14px;"
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

        btn_clear = QPushButton("🗑️ Xóa biểu đồ")
        btn_clear.clicked.connect(self._clear_chart)
        lay.addWidget(btn_clear)
        grp.setLayout(lay)
        return grp


    # --- Settings Tab (Giao diện / Theme) ---
    def _build_settings_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)

        theme_grp = QGroupBox("🎨 Giao diện")
        tg = QVBoxLayout()

        self.btn_toggle_theme = QPushButton()
        self._update_theme_btn_text()
        self.btn_toggle_theme.setMinimumHeight(44)
        self.btn_toggle_theme.clicked.connect(self._toggle_theme)
        tg.addWidget(self.btn_toggle_theme)

        info = QLabel(
            "Chế độ Sáng tương tự giao diện ứng dụng draw_plot.py\n"
            "Chế độ Tối phù hợp môi trường ánh sáng yếu"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-size: 9pt;")
        tg.addWidget(info)

        theme_grp.setLayout(tg)
        lay.addWidget(theme_grp)
        lay.addStretch()
        return w

    def _update_theme_btn_text(self):
        if self._is_dark:
            self.btn_toggle_theme.setText("☀️  Chuyển sang Giao diện Sáng")
            self.btn_toggle_theme.setStyleSheet(
                "background:#fab387; color:#1e1031; font-weight:bold; border-radius:6px;"
            )
        else:
            self.btn_toggle_theme.setText("🌙  Chuyển sang Giao diện Tối")
            self.btn_toggle_theme.setStyleSheet(
                "background:#1e1e2e; color:#cdd6f4; font-weight:bold; border-radius:6px;"
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
        
        # Cập nhật màu sắc cho các label thông số (đồng nhất với draw_plot.py ở mode sáng)
        torque_color = "#89dceb" if dark else "#1976D2"
        max_color    = "#a6e3a1" if dark else "#1976D2"
        min_color    = "#f38ba8" if dark else "#D32F2F"
        
        if hasattr(self, 'lbl_torque'):
            self.lbl_torque.setStyleSheet(f"color: {torque_color};")
            self.lbl_max.setStyleSheet(f"color: {max_color}; font-weight: bold; font-size: 14px;")
            self.lbl_min.setStyleSheet(f"color: {min_color}; font-weight: bold; font-size: 14px;")

        # Cập nhật màu chart theo theme
        if hasattr(self, 'plot'):
            self._apply_chart_theme(dark)

    def _apply_chart_theme(self, dark: bool):
        ax = self.plot.ax
        fig = self.plot.fig
        if dark:
            fig.patch.set_facecolor('#1e1e2e')
            ax.set_facecolor('#252535')
            ax.tick_params(colors='#cccccc')
            ax.title.set_color('#ffffff')
            ax.xaxis.label.set_color('#cccccc')
            ax.yaxis.label.set_color('#cccccc')
            ax.grid(True, alpha=0.25, color='#555577')
            for spine in ax.spines.values():
                spine.set_edgecolor('#444466')
            self.plot.line.set_color('#89dceb')
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

        # Device
        d = self._dev_cfg
        self.combo_unit.setCurrentIndex(d.measure_unit)
        self.combo_mtype.setCurrentIndex(d.measure_type)
        self.spin_fs.setValue(d.cell_full_scale)
        self.spin_sens.setValue(d.cell_sensitivity)
        self.combo_filter.setCurrentIndex(d.filter_level)

        # UI settings
        ui = self._settings.load_ui_settings()
        if 'interval_ms' in ui:
            self.spin_interval.setValue(int(ui['interval_ms']))
        if 'window_s' in ui:
            self.spin_window.setValue(int(ui['window_s']))

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
            measure_unit=self.combo_unit.currentData(),
            measure_type=self.combo_mtype.currentIndex(),
            cell_full_scale=self.spin_fs.value(),
            cell_sensitivity=self.spin_sens.value(),
            filter_level=self.combo_filter.currentData(),
            slave_id=self.spin_slave.value(),
        )
        self._settings.save_device_config(dev)
        self._settings.save_ui_settings({
            'interval_ms': self.spin_interval.value(),
            'window_s':    self.spin_window.value(),
        })

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
            self.combo_com.addItem("(Không tìm thấy cổng COM)")

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


        # Chart luôn update (không cần đang ghi)
        self.plot.add_point(elapsed, status.net_weight)

        # Ghi session nếu đang recording
        if self._recording:
            rec_time = time.monotonic() - self._start_time
            record_ok = (
                not self._chk_stable_only.isChecked()
                or status.is_stable
            )
            if record_ok:
                sample = SampleData(
                    time_s=rec_time,
                    torque_Nm=status.net_weight,
                    stable=status.is_stable,
                    timestamp=time.time(),
                )
                self._session.samples.append(sample)
                self.lbl_count.setText(str(self._session.count))
            self.lbl_rectime.setText(f"{rec_time:.1f} s")

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
        cfg = DeviceConfig(
            measure_unit=self.combo_unit.currentData(),
            measure_type=self.combo_mtype.currentIndex(),
            cell_full_scale=self.spin_fs.value(),
            cell_sensitivity=self.spin_sens.value(),
            filter_level=self.combo_filter.currentData(),
            slave_id=self.spin_slave.value(),
        )
        ok = self._config_svc.write_config(cfg)
        self._log("✅ Đã ghi cấu hình" if ok else "❌ Ghi cấu hình thất bại")
        if ok:
            self._settings.save_device_config(cfg)

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
            self._log(f"📖 Đọc OK: Unit={cfg.measure_unit}, FS={cfg.cell_full_scale:.1f}, Sens={cfg.cell_sensitivity:.4f}, Filter={cfg.filter_level}")
        else:
            self._log("❌ Không đọc được cấu hình")

    def _do_tare(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        ok = self._config_svc.send_command(CMD_TARE, self.spin_slave.value())
        self._log("⚖️ Đã gửi lệnh Tare (49914 → Flash)" if ok else "❌ Lỗi Tare")

    def _do_restart(self):
        if not self._connected:
            self._log("⚠️ Chưa kết nối"); return
        ok = self._config_svc.send_command(CMD_RESTART, self.spin_slave.value())
        self._log("🔄 Đã gửi lệnh Restart (43948)" if ok else "❌ Lỗi Restart")

    # ===========================================================
    # RECORDING
    # ===========================================================

    def _start_recording(self):
        self._session = RecordingSession(sample_interval_ms=self.spin_interval.value())
        self._start_time = time.monotonic()
        self._recording = True
        self.btn_rec_start.setEnabled(False)
        self.btn_rec_stop.setEnabled(True)
        self.lbl_count.setText("0")
        self._log("▶️ Bắt đầu ghi dữ liệu")

    def _stop_recording(self):
        self._session.end_time = time.time()
        self._recording = False
        self.btn_rec_start.setEnabled(True)
        self.btn_rec_stop.setEnabled(False)
        self._log(f"⏹ Đã dừng ghi – {self._session.count} mẫu, {self._session.duration_s:.1f}s")

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
