"""
May Converter GUI - Simplified Version
- Import single file (Time, Torque)
- 4 Part types: Inner Tie Rod, Ball Joint, Outer Tie Rod, Stabilizer Link
- 3 Plots: Input Time-Torque, Output Time-Torque, Output Angle-Torque
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.signal import find_peaks

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QLabel, QPushButton,
                             QFileDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QDoubleSpinBox, QSpinBox, QGroupBox, QSplitter, QMessageBox,
                             QCheckBox, QScrollArea, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# ============================================================
# PART CONFIGURATION
# ============================================================
PART_CONFIG = {
    'Inner Tie Rod': {'max_angle': 22.0, 'code': 'ITR'},
    'Ball Joint': {'max_angle': 36.0, 'code': 'BJ'},
    'Outer Tie Rod': {'max_angle': 36.0, 'code': 'OTR'},
    'Stabilizer Link': {'max_angle': 36.0, 'code': 'SL'},
}


# ============================================================
# CONVERSION FUNCTIONS
# ============================================================
def detect_cycles_continuous(moments, num_cycles, min_distance=500):
    """
    Detect cycles and return continuous segments covering all data.
    Uses peak detection to find cycle length, then divides data evenly.
    Cycles are guaranteed to be adjacent with no gaps.
    """
    peaks, _ = find_peaks(moments, prominence=0.2, distance=min_distance)
    
    total_len = len(moments)
    
    if len(peaks) < 2:
        # Single cycle - divide all data evenly
        cycle_len = total_len // num_cycles
    else:
        # Calculate average cycle length from peaks
        cycle_len = int(np.mean(np.diff(peaks)))
    
    # Find good starting point (skip initial transient if any)
    start_idx = 0
    if len(peaks) > 1 and peaks[0] < cycle_len * 0.3:
        # First peak is too early, likely a startup spike - start from there
        start_idx = peaks[0]
    
    # Calculate how much data we have from start_idx
    available_len = total_len - start_idx
    
    # Adjust cycle_len to fit exactly num_cycles if needed
    if available_len < cycle_len * num_cycles:
        cycle_len = available_len // num_cycles
    
    # Create continuous cycles - each ends exactly where next begins
    cycles = []
    for i in range(num_cycles):
        c_start = start_idx + i * cycle_len
        c_stop = start_idx + (i + 1) * cycle_len
        if c_start >= total_len:
            break
        if c_stop > total_len:
            c_stop = total_len
        cycles.append((c_start, c_stop))
    
    return cycles


# Angular velocity constant: 30 degrees per second
ANGULAR_VELOCITY = 30.0  # degrees/second


def calculate_cycle_time(max_angle):
    """
    Calculate time for one complete cycle based on angular velocity.
    1 cycle = 0 → +max → 0 → -max → 0
    Total angle traveled = 4 * max_angle
    Time = total_angle / angular_velocity
    
    Example for max_angle=36°:
    - 0→+36°: 1.2s (36° at 30°/s)
    - +36°→0: 1.2s
    - 0→-36°: 1.2s
    - -36°→0: 1.2s
    - Total: 4.8s
    """
    total_angle = 4 * max_angle
    cycle_time = total_angle / ANGULAR_VELOCITY
    return cycle_time


def make_command_wave(length, max_angle):
    """
    Create Command waveform: 0 → +max → 0 → -max → 0 (full cycle)
    
    Based on 30°/s angular velocity, each quarter = 1.2s for 36°:
    - Q1 (0→1.2s): 0 → +36°
    - Q2 (1.2→2.4s): +36° → 0
    - Q3 (2.4→3.6s): 0 → -36°
    - Q4 (3.6→4.8s): -36° → 0
    """
    quarter = length // 4
    remaining = length - 4 * quarter
    
    command = np.zeros(length)
    
    # Q1: 0 → +max
    q1_end = quarter
    command[:q1_end] = np.linspace(0, max_angle, quarter, endpoint=False)
    
    # Q2: +max → 0
    q2_end = 2 * quarter
    command[q1_end:q2_end] = np.linspace(max_angle, 0, quarter, endpoint=False)
    
    # Q3: 0 → -max
    q3_end = 3 * quarter
    command[q2_end:q3_end] = np.linspace(0, -max_angle, quarter, endpoint=False)
    
    # Q4: -max → 0 (includes remaining points)
    q4_len = quarter + remaining
    command[q3_end:] = np.linspace(-max_angle, 0, q4_len, endpoint=True)
    
    return command


def make_angle_from_command(command):
    """
    Create Angle that follows Command with dynamics.
    Angle tracks Command with ~98% magnitude.
    """
    alpha = 0.2  # Fast tracking
    angle = np.zeros_like(command)
    angle[0] = command[0] * 0.9  # Start near command start value
    
    for i in range(1, len(command)):
        angle[i] = angle[i-1] + alpha * (command[i] - angle[i-1])
    
    # Scale to match command range (~98%)
    if np.max(np.abs(command)) > 0:
        scale = 0.98 * np.max(np.abs(command)) / max(np.max(np.abs(angle)), 1e-6)
        angle = angle * scale
    
    return angle


def make_angle_continuous(command, start_angle):
    """
    Create Angle that follows Command closely (98% of command).
    For standard conversion, angle should match command almost exactly.
    """
    # Angle follows command at 98% magnitude
    angle = command * 0.98
    return angle


def assign_torque_sign_by_quarter(moments, length):
    """
    Assign sign to torque based on quarter of the cycle.
    Cycle pattern: 0 → +max → 0 → -max → 0
    
    Torque sign pattern per quarter: +, -, -, +
    - Q1 (0→+max): Torque POSITIVE (+)
    - Q2 (+max→0): Torque NEGATIVE (-)
    - Q3 (0→-max): Torque NEGATIVE (-)
    - Q4 (-max→0): Torque POSITIVE (+)
    """
    quarter = length // 4
    
    sign = np.ones(length)
    # Q1: positive
    sign[:quarter] = 1.0
    # Q2: negative
    sign[quarter:2*quarter] = -1.0
    # Q3: negative
    sign[2*quarter:3*quarter] = -1.0
    # Q4: positive
    sign[3*quarter:] = 1.0
    
    # Apply sign to raw moment values
    torque = sign * np.abs(moments)
    return torque


def convert_data(times, moments, max_angle, num_cycles=4):
    """
    Convert raw data to standard format using specific formulas based on Time.
    
    Formulas provided by user (for 36 degree example):
    - 0-1.2s (Q1): Angle = 30*t, Torque = +B2
    - 1.2-2.4s (Q2): Angle = 72 - 30*t, Torque = -B2
    - 2.4-3.6s (Q3): Angle = 72 - 30*t, Torque = -B2
    - 3.6-4.8s (Q4): Angle = -(144 - 30*t), Torque = +B2
    
    Generalized Logic:
    - Angular Velocity = 30 deg/s
    - Quarter Duration = MaxAngle / 30
    """
    if len(times) == 0:
        return pd.DataFrame()
        
    # Ensure time starts at 0 for calculation
    rel_times = times - times[0]
    
    # Constants
    vel = ANGULAR_VELOCITY  # 30.0
    quarter_time = max_angle / vel
    cycle_time = 4 * quarter_time
    
    # --- 1. Calculate Cycle ---
    cycles = np.floor(rel_times / cycle_time).astype(int) + 1
    
    # --- 2. Calculate Angle (Triangular Wave) ---
    # Determine quarter index: 0, 1, 2, 3...
    q_indices = np.floor(rel_times / quarter_time).astype(int)
    
    # Determine Group (2 quarters per group)
    groups = (q_indices + 1) // 2
    
    # Constant for the linear equation: Group * 2 * MaxAngle
    constants = groups * 2 * max_angle
    
    # Even groups (0, 2...): Positive slope (30t - C)
    # Odd groups (1, 3...): Negative slope (C - 30t)
    mask_even = (groups % 2 == 0)
    mask_odd = ~mask_even
    
    angles = np.zeros_like(rel_times)
    term_30t = vel * rel_times
    
    angles[mask_even] = term_30t[mask_even] - constants[mask_even]
    angles[mask_odd] = constants[mask_odd] - term_30t[mask_odd]
    
    # --- 3. Calculate Torque Change (Sign Flip) ---
    # Pattern per quarter cycle: +, -, -, + (0, 1, 2, 3)
    q_mods = q_indices % 4
    mask_pos = (q_mods == 0) | (q_mods == 3)
    mask_neg = ~mask_pos
    
    output_torques = np.zeros_like(moments)
    output_torques[mask_pos] = moments[mask_pos]
    output_torques[mask_neg] = -moments[mask_neg]
    
    # Create DataFrame
    df = pd.DataFrame({
        'Save': 1.0,
        'State': 3.0,
        'Cycle': cycles,
        'Time': rel_times,
        'Command': angles,
        'Angle': angles,
        'Torque': output_torques
    })
    
    # Filter by requested number of cycles if needed
    if num_cycles > 0:
        df = df[df['Cycle'] <= num_cycles]
    
    return df


def save_output(df, out_path, num_cycles):
    """Save DataFrame to CSV with header."""
    nrows = len(df)
    now = datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    header = [
        '%===============================================================',
        '%     CTR DATA FORMAT #1 (Converted)',
        '%     TITLE : Converted Torque Test Data File',
        '%===============================================================',
        'BEGIN_OF_HEADER',
        f'SAVED_DATE = {now}',
        f'SAMPLE INFO = ///DEVELOPMENT/{date_str}',
        'TEST FUNCTION = TRIANGULAR',
        f'TEST CYCLE ={num_cycles:.6f}',
        'NUMBER_OF_COLUMNS = 7',
        'COLUMN_NAME = [Save,State,Cycle,Time,Command,Angle,Torque]',
        'COLUMN_UNIT = [NA,NA,Cycle,sec,Dgree,Dgree,N*m]',
        f'COLUMN_LENGTH = [{nrows},{nrows},{nrows},{nrows},{nrows},{nrows},{nrows}]',
        'END_OF_HEADER'
    ]
    
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    
    with open(out_path, 'w', newline='') as f:
        for line in header:
            f.write(line + '\n')
        for _, row in df.iterrows():
            f.write('%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n' % (
                row['Save'], row['State'], row['Cycle'], row['Time'],
                row['Command'], row['Angle'], row['Torque']))
    
    return out_path


# ============================================================
# MATPLOTLIB CANVAS
# ============================================================
class PlotCanvas(FigureCanvas):
    """Matplotlib canvas for embedding in Qt."""
    def __init__(self, parent=None, width=5, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)


# ============================================================
# MAIN WINDOW
# ============================================================
def get_resource_path(filename):
    """Get path to resource file (works for both dev and PyInstaller)."""
    import sys
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        return os.path.join(sys._MEIPASS, filename)
    else:
        # Running as script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


class ConvertWidget(QWidget):
    import_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Torque Data Conversion Tool')
        self.setMinimumSize(1200, 800)
        
        # Set window icon
        icon_path = get_resource_path('file.png')
        if os.path.exists(icon_path):
            from PyQt5.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        # Data storage
        self.raw_times = None
        self.raw_torques = None
        self.output_df = None
        self.last_saved_path = None
        self.input_file = None
        self.output_folder = None
        
        self.init_ui()
    
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)
        
        # === Input File Section ===
        input_group = QGroupBox("📁 Input File")
        input_layout = QVBoxLayout()
        
        self.input_path_label = QLabel("No file selected")
        self.input_path_label.setWordWrap(True)
        input_layout.addWidget(self.input_path_label)
        
        h_btns = QHBoxLayout()
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_input)
        h_btns.addWidget(btn_browse)
        
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_input)
        h_btns.addWidget(btn_clear)
        input_layout.addLayout(h_btns)
        
        input_group.setLayout(input_layout)
        left_layout.addWidget(input_group)
        
        # === Part Type Section ===
        part_group = QGroupBox("🔧 Part Type")
        part_layout = QVBoxLayout()
        
        self.part_combo = QComboBox()
        self.part_combo.addItems(list(PART_CONFIG.keys()))
        # Set default to 'Ball Joint'
        if 'Ball Joint' in PART_CONFIG:
            self.part_combo.setCurrentText('Ball Joint')
        self.part_combo.currentIndexChanged.connect(self.on_part_changed)
        part_layout.addWidget(self.part_combo)
        
        # Max angle display
        h_angle = QHBoxLayout()
        h_angle.addWidget(QLabel("Max Angle:"))
        self.max_angle_spin = QDoubleSpinBox()
        self.max_angle_spin.setRange(1, 90)
        # Default to selected part's configured max angle
        default_part = self.part_combo.currentText()
        default_angle = PART_CONFIG.get(default_part, {}).get('max_angle', 36.0)
        self.max_angle_spin.setValue(default_angle)
        self.max_angle_spin.setSuffix(" °")
        h_angle.addWidget(self.max_angle_spin)
        part_layout.addLayout(h_angle)
        
        part_group.setLayout(part_layout)
        left_layout.addWidget(part_group)
        
        # === Cycle Settings ===
        cycle_group = QGroupBox("🔄 Cycle Selection")
        cycle_layout = QVBoxLayout()
        
        h_cycles = QHBoxLayout()
        h_cycles.addWidget(QLabel("Total Cycles:"))
        self.num_cycles_spin = QSpinBox()
        self.num_cycles_spin.setRange(1, 50)
        self.num_cycles_spin.setValue(4)
        self.num_cycles_spin.valueChanged.connect(self.on_num_cycles_changed)
        h_cycles.addWidget(self.num_cycles_spin)
        cycle_layout.addLayout(h_cycles)
        
        # Select/Deselect all buttons
        h_select = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(self.select_all_cycles)
        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.clicked.connect(self.deselect_all_cycles)
        h_select.addWidget(btn_select_all)
        h_select.addWidget(btn_deselect_all)
        cycle_layout.addLayout(h_select)
        
        # Cycle checkboxes in scrollable area
        cycle_layout.addWidget(QLabel("Display Cycles:"))
        self.cycle_scroll = QScrollArea()
        self.cycle_scroll.setWidgetResizable(True)
        self.cycle_scroll.setMaximumHeight(120)
        self.cycle_container = QWidget()
        self.cycle_grid = QGridLayout(self.cycle_container)
        self.cycle_grid.setSpacing(2)
        self.cycle_checkboxes = []
        self.cycle_scroll.setWidget(self.cycle_container)
        cycle_layout.addWidget(self.cycle_scroll)
        
        cycle_group.setLayout(cycle_layout)
        left_layout.addWidget(cycle_group)
        
        # === Output Section ===
        output_group = QGroupBox("💾 Output")
        output_layout = QVBoxLayout()
        
        h_folder = QHBoxLayout()
        h_folder.addWidget(QLabel("Folder:"))
        self.output_folder_label = QLabel("(Select folder)")
        self.output_folder_label.setWordWrap(True)
        h_folder.addWidget(self.output_folder_label, stretch=1)
        output_layout.addLayout(h_folder)
        
        btn_folder = QPushButton("Choose Folder...")
        btn_folder.clicked.connect(self.choose_output_folder)
        output_layout.addWidget(btn_folder)
        
        self.output_filename_label = QLabel("Filename: (auto-generated)")
        self.output_filename_label.setWordWrap(True)
        self.output_filename_label.setStyleSheet("color: gray; font-size: 10px;")
        output_layout.addWidget(self.output_filename_label)
        
        output_group.setLayout(output_layout)
        left_layout.addWidget(output_group)
        
        # === Action Buttons ===
        action_group = QGroupBox("⚡ Actions")
        action_layout = QVBoxLayout()
        
        self.btn_convert = QPushButton("🔄 Convert")
        self.btn_convert.setMinimumHeight(40)
        self.btn_convert.clicked.connect(self.do_convert)
        self.btn_convert.setEnabled(False)
        action_layout.addWidget(self.btn_convert)
        
        self.btn_save = QPushButton("💾 Save Output")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.clicked.connect(self.save_output)
        self.btn_save.setEnabled(False)
        action_layout.addWidget(self.btn_save)

        self.btn_import = QPushButton("⬇ Import to Plot")
        self.btn_import.setMinimumHeight(40)
        self.btn_import.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_import.clicked.connect(self.request_import)
        self.btn_import.setEnabled(False)
        action_layout.addWidget(self.btn_import)
        
        action_group.setLayout(action_layout)
        left_layout.addWidget(action_group)
        
        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; padding: 5px;")
        left_layout.addWidget(self.status_label)
        
        left_layout.addStretch()
        main_layout.addWidget(left_panel)
        
        # Right panel - Plots
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Plot 1: Input Time vs Torque
        plot1_group = QGroupBox("📊 Input: Time vs Torque")
        plot1_layout = QVBoxLayout()
        self.canvas_input = PlotCanvas(self, width=8, height=2.5)
        plot1_layout.addWidget(self.canvas_input)
        plot1_group.setLayout(plot1_layout)
        right_layout.addWidget(plot1_group)
        
        # Plot 2: Output Time vs Torque
        plot2_group = QGroupBox("📈 Output: Time vs Torque")
        plot2_layout = QVBoxLayout()
        self.canvas_output_time = PlotCanvas(self, width=8, height=2.5)
        plot2_layout.addWidget(self.canvas_output_time)
        plot2_group.setLayout(plot2_layout)
        right_layout.addWidget(plot2_group)
        
        # Plot 3: Output Angle vs Torque
        plot3_group = QGroupBox("📉 Output: Angle vs Torque")
        plot3_layout = QVBoxLayout()
        self.canvas_output_angle = PlotCanvas(self, width=8, height=2.5)
        plot3_layout.addWidget(self.canvas_output_angle)
        plot3_group.setLayout(plot3_layout)
        right_layout.addWidget(plot3_group)
        
        main_layout.addWidget(right_panel, stretch=1)
        
        # Initialize part settings
        self.on_part_changed()
        self.update_cycle_list()
    
    def on_part_changed(self):
        """Update max angle when part type changes."""
        part = self.part_combo.currentText()
        if part in PART_CONFIG:
            self.max_angle_spin.setValue(PART_CONFIG[part]['max_angle'])
        # Recalculate max cycles based on new max_angle
        if self.raw_times is not None:
            self.update_max_cycles()
            self.do_convert()
    
    def update_max_cycles(self):
        """Recalculate max cycles based on raw data time and current max_angle."""
        if self.raw_times is None:
            return
        # Use max() - min() to handle files with extra rows like "0,0" at the end
        max_time = self.raw_times.max() - self.raw_times.min()
        max_angle = self.max_angle_spin.value()
        cycle_time = 4 * max_angle / ANGULAR_VELOCITY
        max_cycles = max(1, int(max_time / cycle_time))
        self.num_cycles_spin.setMaximum(max(1, max_cycles))
        self.num_cycles_spin.setValue(max_cycles)
        self.update_cycle_list()
    
    def on_num_cycles_changed(self):
        """Update cycle list when number changes."""
        self.update_cycle_list()
        if self.raw_times is not None:
            self.do_convert()
    
    def update_cycle_list(self):
        """Update the cycle checkboxes."""
        # Clear existing checkboxes
        for cb in self.cycle_checkboxes:
            cb.deleteLater()
        self.cycle_checkboxes.clear()
        
        # Create new checkboxes in grid (4 per row)
        num = self.num_cycles_spin.value()
        cols = 4
        for i in range(num):
            cb = QCheckBox(f"{i+1}")
            cb.setChecked(True)  # Select all by default
            cb.stateChanged.connect(self.on_cycle_selection_changed)
            row = i // cols
            col = i % cols
            self.cycle_grid.addWidget(cb, row, col)
            self.cycle_checkboxes.append(cb)
    
    def get_selected_cycles(self):
        """Get list of selected cycle numbers."""
        selected = []
        for i, cb in enumerate(self.cycle_checkboxes):
            if cb.isChecked():
                selected.append(i + 1)
        return selected if selected else list(range(1, self.num_cycles_spin.value() + 1))
    
    def select_all_cycles(self):
        """Select all cycle checkboxes."""
        for cb in self.cycle_checkboxes:
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
        self.on_cycle_selection_changed()
    
    def deselect_all_cycles(self):
        """Deselect all cycle checkboxes."""
        for cb in self.cycle_checkboxes:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self.on_cycle_selection_changed()
    
    def on_cycle_selection_changed(self):
        """Update plots when cycle selection changes."""
        if self.output_df is not None:
            self.update_output_plots()
    
    def browse_input(self):
        """Browse for input file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Input File", "", "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self.input_file = path
            self.input_path_label.setText(path)
            self.load_input_file(path)
            self.btn_convert.setEnabled(True)
            
            # Set output folder to same as input file
            self.output_folder = os.path.dirname(path)
            self.output_folder_label.setText(self.output_folder)
            self.update_output_filename()
    
    def load_input_file(self, path):
        """Load input file, detect cycles, and auto-convert."""
        try:
            df = pd.read_csv(path, header=None, names=['Time', 'Torque'])
            self.raw_times = df['Time'].to_numpy()
            self.raw_torques = df['Torque'].to_numpy()
            # Reset last saved path to ensure new conversion is saved/imported
            self.last_saved_path = None
            # store original start time for absolute time output
            self.start_time = float(df['Time'].iloc[0]) if len(df) > 0 else 0.0

            # auto-detect Inner Tie Rod files by filename and set part/max angle
            base = os.path.basename(path).upper()
            if 'ITR' in base or 'INNER' in base:
                if 'Inner Tie Rod' in PART_CONFIG:
                    self.part_combo.setCurrentText('Inner Tie Rod')
                    self.max_angle_spin.setValue(PART_CONFIG['Inner Tie Rod']['max_angle'])
            
            # Calculate max cycles based on file time duration
            # Use max() - min() to handle files with extra rows like "0,0" at the end
            max_time = self.raw_times.max() - self.raw_times.min()
            
            # Calculate max cycles based on time and angular velocity (30°/s)
            # cycle_time = 4 * max_angle / 30
            # max_cycles = floor(max_time / cycle_time)
            max_angle = self.max_angle_spin.value()
            cycle_time = 4 * max_angle / ANGULAR_VELOCITY
            max_cycles = max(1, int(max_time / cycle_time))
            
            # Update cycle spin box - set to max_cycles by default to show all data
            self.num_cycles_spin.setMaximum(max(1, max_cycles))
            self.num_cycles_spin.setValue(max_cycles)  # Show all cycles by default
            self.update_cycle_list()
            
            # Update input plot
            self.canvas_input.ax.clear()
            self.canvas_input.ax.plot(self.raw_times, self.raw_torques, 'b-', linewidth=0.5)
            self.canvas_input.ax.set_xlabel('Time (s)')
            self.canvas_input.ax.set_ylabel('Torque (N*m)')
            self.canvas_input.ax.set_title('Raw Input Data')
            self.canvas_input.ax.grid(True, alpha=0.3)
            self.canvas_input.draw()
            
            self.status_label.setText(f"Loaded: {len(df)} rows, Max {max_cycles} cycles")
            self.status_label.setStyleSheet("color: green;")
            
            # Auto convert and plot
            self.do_convert()
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}\n{traceback.format_exc()}")
            self.status_label.setText("Load failed")
            self.status_label.setStyleSheet("color: red;")
    
    def clear_input(self):
        """Clear the current input file data and reset plots."""
        self.raw_times = None
        self.raw_torques = None
        self.output_df = None
        self.last_saved_path = None
        self.input_file = None
        
        self.input_path_label.setText("No file selected")
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #666666;")
        
        # Reset cycle list
        for i in reversed(range(self.cycle_grid.count())): 
            self.cycle_grid.itemAt(i).widget().setParent(None)
        self.cycle_checkboxes = []
        
        # Clear plots
        self.canvas_input.ax.clear()
        self.canvas_input.ax.set_title("Input Time vs Torque")
        self.canvas_input.draw()
        
        self.canvas_output_time.ax.clear()
        self.canvas_output_time.ax.set_title("Output: Time vs Torque")
        self.canvas_output_time.draw()
        
        self.canvas_output_angle.ax.clear()
        self.canvas_output_angle.ax.set_title("Output: Angle vs Torque")
        self.canvas_output_angle.draw()
        
        # Disable action buttons
        self.btn_convert.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_import.setEnabled(False)
    
    def choose_output_folder(self):
        """Choose output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_folder_label.setText(folder)
            self.update_output_filename()
    
    def update_output_filename(self):
        """Generate output filename based on current time."""
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        part = self.part_combo.currentText().replace(' ', '_')
        filename = f"converted_{part}_{now}.csv"
        self.output_filename_label.setText(f"Filename: {filename}")
    
    def do_convert(self):
        """Perform conversion."""
        if self.raw_times is None or self.raw_torques is None:
            QMessageBox.warning(self, "Warning", "Please load an input file first.")
            return
        
        try:
            max_angle = self.max_angle_spin.value()
            num_cycles = self.num_cycles_spin.value()
            
            # Convert data
            self.output_df = convert_data(
                self.raw_times, 
                self.raw_torques, 
                max_angle, 
                num_cycles
            )
            
            if len(self.output_df) == 0:
                QMessageBox.warning(self, "Warning", "Conversion produced no data.")
                return
            
            # Update output plots
            self.update_output_plots()
            
            self.btn_save.setEnabled(True)
            self.btn_import.setEnabled(True)
            self.status_label.setText(f"Converted: {len(self.output_df)} rows")
            self.status_label.setStyleSheet("color: green;")
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error", f"Conversion failed:\n{e}\n\n{traceback.format_exc()}")
            self.status_label.setText("Conversion failed")
            self.status_label.setStyleSheet("color: red;")
    
    def update_output_plots(self):
        """Update output plots after conversion."""
        if self.output_df is None:
            return
        
        # Get max_angle and calculate cycle_time based on angular velocity (30°/s)
        max_angle = self.max_angle_spin.value()
        cycle_time = 4 * max_angle / ANGULAR_VELOCITY  # e.g., 4.8s for 36°, 2.93s for 22°
        
        # Get all data
        all_times = self.output_df['Time'].values
        all_torques = self.output_df['Torque'].values
        all_angles = self.output_df['Angle'].values
        
        # Calculate cycle based on TIME (0-cycle_time = cycle 1, cycle_time-2*cycle_time = cycle 2, etc.)
        time_based_cycles = np.floor(all_times / cycle_time).astype(int) + 1
        
        # Get selected cycles
        selected_cycles = self.get_selected_cycles()
        
        # Filter data by selected cycles (based on time)
        mask = np.isin(time_based_cycles, selected_cycles)
        
        if not np.any(mask):
            return
        
        times = all_times[mask]
        torques = all_torques[mask]
        angles = all_angles[mask]
        cycles = time_based_cycles[mask]
        
        # Colors for cycles
        colors = ['C0', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9']
        
        # Plot 2: Output Time vs Torque - draw continuous line then add colored segments
        self.canvas_output_time.ax.clear()
        # First draw all data as one continuous line (gray background)
        self.canvas_output_time.ax.plot(times, torques, '-', color='lightgray', linewidth=1.5, zorder=1)
        # Then overlay colored segments for each cycle with markers for legend
        for c in selected_cycles:
            c_mask = cycles == c
            if np.any(c_mask):
                color = colors[int(c-1) % len(colors)]
                c_times = times[c_mask]
                c_torques = torques[c_mask]
                # Draw colored line segment
                self.canvas_output_time.ax.plot(c_times, c_torques, '-', 
                    color=color, linewidth=0.8, zorder=2)
                # Add single marker for legend
                mid_idx = len(c_times) // 2
                self.canvas_output_time.ax.scatter([c_times[mid_idx]], [c_torques[mid_idx]], 
                    color=color, s=30, zorder=3, label=f'Cycle {int(c)}')
        self.canvas_output_time.ax.set_xlabel('Time (s)')
        self.canvas_output_time.ax.set_ylabel('Torque (N*m)')
        self.canvas_output_time.ax.set_title('Output: Time vs Torque')
        self.canvas_output_time.ax.grid(True, alpha=0.3)
        self.canvas_output_time.ax.legend(loc='upper right', fontsize='small')
        self.canvas_output_time.ax.axhline(0, color='black', linewidth=0.5)
        self.canvas_output_time.draw()
        
        # Plot 3: Output Angle vs Torque - draw continuous line then add colored segments
        self.canvas_output_angle.ax.clear()
        # First draw all data as one continuous line (gray background)
        self.canvas_output_angle.ax.plot(angles, torques, '-', color='lightgray', linewidth=1.5, zorder=1)
        # Then overlay colored segments for each cycle
        for c in selected_cycles:
            c_mask = cycles == c
            if np.any(c_mask):
                color = colors[int(c-1) % len(colors)]
                c_angles = angles[c_mask]
                c_torques = torques[c_mask]
                # Draw colored line segment
                self.canvas_output_angle.ax.plot(c_angles, c_torques, '-', 
                    color=color, linewidth=0.8, zorder=2)
                # Add single marker for legend
                mid_idx = len(c_angles) // 2
                self.canvas_output_angle.ax.scatter([c_angles[mid_idx]], [c_torques[mid_idx]], 
                    color=color, s=30, zorder=3, label=f'Cycle {int(c)}')
        self.canvas_output_angle.ax.set_xlabel('Angle (°)')
        self.canvas_output_angle.ax.set_ylabel('Torque (N*m)')
        self.canvas_output_angle.ax.set_title('Output: Angle vs Torque')
        self.canvas_output_angle.ax.grid(True, alpha=0.3)
        self.canvas_output_angle.ax.legend(loc='upper right', fontsize='small')
        self.canvas_output_angle.ax.axhline(0, color='black', linewidth=0.5)
        self.canvas_output_angle.ax.axvline(0, color='black', linewidth=0.5)
        self.canvas_output_angle.draw()
    
    def save_output(self):
        """Save output to file - only selected cycles. Returns path if successful, None otherwise."""
        if self.output_df is None:
            QMessageBox.warning(self, "Warning", "No data to save. Run conversion first.")
            return None
        
        # Check if output folder is set
        if not self.output_folder:
            QMessageBox.warning(self, "Warning", "Please select an output folder first.")
            self.choose_output_folder()
            if not self.output_folder:
                return None
        
        # Filter by selected cycles
        selected_cycles = self.get_selected_cycles()
        mask = self.output_df['Cycle'].isin(selected_cycles)
        filtered_df = self.output_df[mask].copy()

        if len(filtered_df) == 0:
            QMessageBox.warning(self, "Warning", "No cycles selected.")
            return None

        # Renumber cycles from 1 (keep ordering of selected cycles)
        cycle_map = {old: new for new, old in enumerate(sorted(selected_cycles), 1)}
        filtered_df['Cycle'] = filtered_df['Cycle'].map(cycle_map)

        # Generate filename with timestamp
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        part = self.part_combo.currentText().replace(' ', '_')
        filename = f"converted_{part}_{now}.csv"
        out_path = os.path.join(self.output_folder, filename)

        try:
            # Use the standard save_output() to produce the same header/format as other part types
            num_cycles = len(selected_cycles)
            save_output(filtered_df, out_path, num_cycles)
            QMessageBox.information(self, "Success", f"Saved {num_cycles} cycle(s) to:\n{out_path}")
            self.status_label.setText(f"Saved: {out_path}")
            self.status_label.setStyleSheet("color: green;")
            self.last_saved_path = out_path
            return out_path
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")
            return None

    def request_import(self):
        """Handle request to import to main app."""
        # if not saved or logic changed, save first
        # For simplicity, if we have a last_saved_path that matches current settings? 
        # Easier to just save again or check if self.last_saved_path exists.
        
        # If user hasn't saved yet, save now.
        if not self.last_saved_path or not os.path.exists(self.last_saved_path):
             path = self.save_output()
             if not path:
                 return # Cancelled or failed
        else:
            # Ask if they want to save as new or use existing? 
            # Given the workflow, maybe just 'Import' loads the last saved file.
            pass
            
        if self.last_saved_path and os.path.exists(self.last_saved_path):
            self.import_requested.emit(self.last_saved_path)


# ============================================================
# MAIN
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    # Wrap widget in window for standalone run
    window = QMainWindow()
    widget = ConvertWidget()
    window.setCentralWidget(widget)
    window.setWindowTitle(widget.windowTitle())
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
