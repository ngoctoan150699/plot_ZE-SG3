"""
UI Layer – Bilingual Translation Service (EN/VN)
=================================================
Quản lý ngôn ngữ và từ điển dịch nhãn giao diện cho toàn bộ phần mềm.
"""

TRANSLATIONS = {
    'vi': {
        # Tab Headers
        'tab_acquisition': '📡 Thu thập',
        'tab_config': '⚙️ Cấu hình',
        'tab_connection': '🔌 Kết nối',
        'tab_plot_viewer': '📊 Plot Viewer',
        
        # Connection Tab
        'proto_grp': '🔌 Giao thức',
        'proto_lbl': 'Loại:',
        'rtu_grp': '📡 RTU (RS-485)',
        'com_lbl': 'COM Port:',
        'baud_lbl': 'Baudrate:',
        'parity_lbl': 'Parity:',
        'tcp_grp': '🌐 TCP/IP',
        'ip_lbl': 'IP:',
        'port_lbl': 'Port:',
        'slave_grp': '📋 Slave',
        'slave_lbl': 'Slave ID:',
        'btn_connect': '🔗 Kết nối',
        'btn_disconnect': '🔌 Ngắt kết nối',
        'status_unconnected': '⚪ Chưa kết nối',
        'status_connected': '🟢 Đã kết nối',
        'status_stable': '🟢 Ổn định',
        'status_fullscale': '🔴 Quá tải!',
        'status_unstable': '🟡 Không ổn định',
        'btn_scan_tooltip': 'Làm mới COM ports',
        'msg_chart_cleared': '🗑️ Đã xóa biểu đồ',
        
        # Config Tab
        'sensor_grp': '📊 Cảm biến & Hiệu chuẩn',
        'unit_lbl': 'Đơn vị đo:',
        'mode_lbl': 'Chế độ đo:',
        'fs_lbl': 'Full Scale (Nm):',
        'sens_lbl': 'Sensitivity (mV/V):',
        'stable_grp': '🛡️ Ổn định & Lọc',
        'filter_lbl': 'Mức lọc nhiễu:',
        'btn_write_cfg': '📝 Ghi cấu hình',
        'btn_read_cfg': '📖 Đọc từ thiết bị',
        'quick_cmd_grp': '⚡ Lệnh nhanh',
        'btn_quick_tare': '⚖️ Tare (Zero)',
        'btn_quick_restart': '🔄 Restart Device',
        
        # Acquisition Tab
        'sampling_grp': '⏱️ Lấy mẫu',
        'interval_lbl': 'Chu kỳ (ms):',
        'window_lbl': 'Cửa sổ biểu đồ (s):',
        'ymax_lbl': 'Giới hạn Y (Nm):',
        'chk_fixed_y': 'Cố định thang đo Y',
        
        'part_program_grp': '⚙️ Chương trình đo',
        'part_name_lbl': 'Sản phẩm:',
        'test_item_lbl': 'Chế độ đo:',
        'btn_servo_setup': '⚙️ Thiết lập Servo',
        
        'recording_grp': '🔴 Ghi dữ liệu',
        'btn_start_record': '▶️ Bắt đầu ghi',
        'btn_stop_record': '⏹ Stop',
        'btn_clear_samples': '🗑️ Xóa dữ liệu mẫu',
        'btn_tare_acq': '⚖️ Tare',
        
        'export_grp': '💾 Xuất dữ liệu',
        'import_tools_grp': '📥 Import dữ liệu sang công cụ khác',
        'btn_import_plot': '📊 Import to Plot Viewer',
        
        # Real-time Display Group
        'display_grp': '📊 Real-time Data Info',
        'lbl_torque': 'Torque:',
        'lbl_status': 'Status:',
        'lbl_samples': 'Samples:',
        'lbl_tare': 'Tare:',
        'lbl_time': 'Time:',
        'lbl_max': 'Maximum:',
        'lbl_min': 'Minimum:',
        
        # Charts
        'chart_torque_time': '📈 Torque – Time',
        'chart_torque_angle': '📐 Torque – Angle',
        'chart_title_time': 'Torque vs Time',
        'chart_title_angle': 'Torque vs Angle',
        'axis_time': 'Time (s)',
        'axis_angle': 'Angle (deg)',
        'axis_torque': 'Torque (Nm)',
        
        # Calibration Setup
        'calibration_title': 'Calibration',
        
        # Messages & Dialogs
        'msg_err': 'Lỗi',
        'msg_info': 'Thông tin',
        'msg_success': 'Thành công',
        'msg_connect_failed': 'Không thể kết nối đến thiết bị!',
        'msg_write_success': 'Ghi cấu hình thành công!',
        'msg_write_failed': 'Lỗi ghi cấu hình!',
        'msg_read_success': 'Đọc cấu hình thành công!',
        'msg_read_failed': 'Lỗi đọc cấu hình!',
        'measure_mode_0': '0: 2 chiều (+/-)',
        'measure_mode_1': '1: 1 chiều (+)',
        'filter_0': '0: Tắt lọc',
        'filter_1': '1: Thấp',
        'filter_2': '2: Trung bình',
        'filter_3': '3: Cao',
        'btn_pause_chart': '⏸ Dừng vẽ',
        'btn_resume_chart': '▶️ Tiếp tục vẽ',
        'btn_clear_chart': '🗑️ Xóa biểu đồ',
        'btn_theme_light': '☀️  Giao diện Sáng',
        'btn_theme_dark': '🌙  Giao diện Tối',
    },
    'en': {
        # Tab Headers
        'tab_acquisition': '📡 Acquisition',
        'tab_config': '⚙️ Configuration',
        'tab_connection': '🔌 Connection',
        'tab_plot_viewer': '📊 Plot Viewer',
        
        # Connection Tab
        'proto_grp': '🔌 Protocol',
        'proto_lbl': 'Type:',
        'rtu_grp': '📡 RTU (RS-485)',
        'com_lbl': 'COM Port:',
        'baud_lbl': 'Baudrate:',
        'parity_lbl': 'Parity:',
        'tcp_grp': '🌐 TCP/IP',
        'ip_lbl': 'IP:',
        'port_lbl': 'Port:',
        'slave_grp': '📋 Slave Info',
        'slave_lbl': 'Slave ID:',
        'btn_connect': '🔗 Connect',
        'btn_disconnect': '🔌 Disconnect',
        'status_unconnected': '⚪ Disconnected',
        'status_connected': '🟢 Connected',
        'status_stable': '🟢 Stable',
        'status_fullscale': '🔴 Full Scale!',
        'status_unstable': '🟡 Unstable',
        'btn_scan_tooltip': 'Refresh COM ports',
        'msg_chart_cleared': '🗑️ Chart cleared',
        
        # Config Tab
        'sensor_grp': '📊 Sensor & Calibration',
        'unit_lbl': 'Measure Unit:',
        'mode_lbl': 'Measure Mode:',
        'fs_lbl': 'Full Scale (Nm):',
        'sens_lbl': 'Sensitivity (mV/V):',
        'stable_grp': '🛡️ Stability & Filter',
        'filter_lbl': 'Noise Filter Level:',
        'btn_write_cfg': '📝 Write Config',
        'btn_read_cfg': '📖 Read Device',
        'quick_cmd_grp': '⚡ Quick Commands',
        'btn_quick_tare': '⚖️ Tare (Zero)',
        'btn_quick_restart': '🔄 Restart Device',
        
        # Acquisition Tab
        'sampling_grp': '⏱️ Sampling Settings',
        'interval_lbl': 'Interval (ms):',
        'window_lbl': 'Chart Window (s):',
        'ymax_lbl': 'Y Limits (Nm):',
        'chk_fixed_y': 'Fixed Y Axis Scale',
        
        'part_program_grp': '⚙️ Measurement Program',
        'part_name_lbl': 'Part Name:',
        'test_item_lbl': 'Test Item:',
        'btn_servo_setup': '⚙️ Servo Setup',
        
        'recording_grp': '🔴 Data Recording',
        'btn_start_record': '▶️ Start Record',
        'btn_stop_record': '⏹ Stop',
        'btn_clear_samples': '🗑️ Clear Samples',
        'btn_tare_acq': '⚖️ Tare',
        
        'export_grp': '💾 Export Data',
        'import_tools_grp': '📥 Import Data to Other Tools',
        'btn_import_plot': '📊 Import to Plot Viewer',
        
        # Real-time Display Group
        'display_grp': '📊 Real-time Data Info',
        'lbl_torque': 'Torque:',
        'lbl_status': 'Status:',
        'lbl_samples': 'Samples:',
        'lbl_tare': 'Tare:',
        'lbl_time': 'Time:',
        'lbl_max': 'Maximum:',
        'lbl_min': 'Minimum:',
        
        # Charts
        'chart_torque_time': '📈 Torque – Time',
        'chart_torque_angle': '📐 Torque – Angle',
        'chart_title_time': 'Torque vs Time',
        'chart_title_angle': 'Torque vs Angle',
        'axis_time': 'Time (s)',
        'axis_angle': 'Angle (deg)',
        'axis_torque': 'Torque (Nm)',
        
        # Calibration Setup
        'calibration_title': 'Calibration',
        
        # Messages & Dialogs
        'msg_err': 'Error',
        'msg_info': 'Information',
        'msg_success': 'Success',
        'msg_connect_failed': 'Failed to connect to device!',
        'msg_write_success': 'Configuration written successfully!',
        'msg_write_failed': 'Failed to write configuration!',
        'msg_read_success': 'Configuration loaded successfully!',
        'msg_read_failed': 'Failed to read configuration!',
        'measure_mode_0': '0: Bidirectional (+/-)',
        'measure_mode_1': '1: Unidirectional (+)',
        'filter_0': '0: Filter off',
        'filter_1': '1: Low',
        'filter_2': '2: Medium',
        'filter_3': '3: High',
        'btn_pause_chart': '⏸ Pause drawing',
        'btn_resume_chart': '▶️ Resume drawing',
        'btn_clear_chart': '🗑️ Clear chart',
        'btn_theme_light': '☀️  Light Theme',
        'btn_theme_dark': '🌙  Dark Theme',
    }
}


class I18n:
    """Translation manager for bilingual interface (EN/VN)."""
    
    def __init__(self, lang: str = 'vi'):
        self._lang = lang if lang in ('vi', 'en') else 'vi'

    @property
    def current_language(self) -> str:
        return self._lang

    def set_language(self, lang: str) -> None:
        if lang in ('vi', 'en'):
            self._lang = lang

    def toggle(self) -> str:
        """Switch language (vi -> en or en -> vi) and return new language code."""
        self._lang = 'en' if self._lang == 'vi' else 'vi'
        return self._lang

    def t(self, key: str) -> str:
        """Translate key to current language. Return key if not found."""
        return TRANSLATIONS.get(self._lang, {}).get(key, key)
