"""
UI Widgets – Real-Time Plot
============================
SRP: Widget này chỉ vẽ biểu đồ. Logic dữ liệu giữ ở MainWindow.
"""

import time
import matplotlib.path
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Fix RecursionError Matplotlib trên Python 3.12+
try:
    del matplotlib.path.Path.__deepcopy__
except AttributeError:
    pass


class RealTimePlot(FigureCanvas):
    """
    Widget Matplotlib vẽ biểu đồ thời gian thực.
    Throttle 30 FPS để tránh quá tải CPU.
    """

    def __init__(
        self,
        title: str = "Plot",
        xlabel: str = "X",
        ylabel: str = "Y",
        max_window_s: float = 60.0,
        color: str = '#89dceb',    # Default: cyan (dark theme), sẽ được ghi đè qua _apply_chart_theme
    ):
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.fig.patch.set_facecolor('#1e1e2e')
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

        self.max_window_s = max_window_s
        self._x_data: list = []
        self._y_data: list = []
        self._last_draw = 0.0

        # Style mặc định (dark) – sẽ được override bởi _apply_chart_theme sau khi build_ui
        self.ax.set_facecolor('#252535')
        self.ax.tick_params(colors='#cccccc')
        self.ax.set_title(title, fontsize=11, fontweight='bold', color='#ffffff')
        self.ax.set_xlabel(xlabel, fontsize=10, color='#cccccc')
        self.ax.set_ylabel(ylabel, fontsize=10, color='#cccccc')
        self.ax.grid(True, alpha=0.25, color='#555577')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#444466')

        self.line, = self.ax.plot([], [], color=color, linewidth=1.8, antialiased=True)
        self.fig.tight_layout(pad=1.5)

    def add_point(self, x: float, y: float) -> None:
        """Thêm điểm mới và cập nhật chart (throttle 30 FPS)."""
        self._x_data.append(x)
        self._y_data.append(y)

        # Cắt cửa sổ thời gian
        if self.max_window_s and self._x_data:
            cutoff = x - self.max_window_s
            while self._x_data and self._x_data[0] < cutoff:
                self._x_data.pop(0)
                self._y_data.pop(0)

        now = time.monotonic()
        if (now - self._last_draw) >= 0.033:  # ~30 FPS
            self.line.set_data(self._x_data, self._y_data)
            self.ax.relim()
            self.ax.autoscale_view()
            self.draw_idle()
            self._last_draw = now

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu."""
        self._x_data.clear()
        self._y_data.clear()
        self.line.set_data([], [])
        self.draw()
