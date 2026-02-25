"""
UI Widgets – Real-Time Plot
============================
SRP: Widget này chỉ vẽ biểu đồ. Logic dữ liệu giữ ở MainWindow.

Tối ưu hiệu năng:
- collections.deque thay list → O(1) trim
- Matplotlib blit → chỉ vẽ lại line, không redraw toàn canvas
- Throttle 30 FPS
"""

import time
from collections import deque
from typing import Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import matplotlib.path as mpath

# Fix RecursionError Matplotlib trên Python 3.12+
try:
    del mpath.Path.__deepcopy__
except AttributeError:
    pass


class RealTimePlot(FigureCanvas):
    """
    Widget Matplotlib vẽ biểu đồ thời gian thực.
    Tối ưu: deque + blit + throttle 30 FPS.
    """

    def __init__(
        self,
        title: str = "Plot",
        xlabel: str = "X",
        ylabel: str = "Y",
        max_window_s: float = 60.0,
        color: str = '#5588cc',
    ):
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.fig.patch.set_facecolor('#181820')
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

        self.max_window_s = max_window_s
        # deque với maxlen tự động trim → O(1) 
        max_points = int(max_window_s * 1000)  # Buffer lớn, sẽ trim theo thời gian
        self._x_data: deque = deque(maxlen=max_points)
        self._y_data: deque = deque(maxlen=max_points)
        self._last_draw = 0.0
        self._y_limit: Optional[float] = None

        # Style mặc định (dark) – sẽ được override bởi _apply_chart_theme
        self.ax.set_facecolor('#1a1a24')
        self.ax.tick_params(colors='#777788')
        self.ax.set_title(title, fontsize=11, fontweight='bold', color='#9999aa')
        self.ax.set_xlabel(xlabel, fontsize=10, color='#777788')
        self.ax.set_ylabel(ylabel, fontsize=10, color='#777788')
        self.ax.grid(True, alpha=0.15, color='#444455')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#2a2a3a')

        self.line, = self.ax.plot([], [], color=color, linewidth=1.5, antialiased=True)
        self.fig.tight_layout(pad=1.5)

        # Blit support
        self._bg = None

    def _save_background(self):
        """Lưu background (axes, grid, labels) để blit."""
        self.draw()
        self._bg = self.copy_from_bbox(self.ax.bbox)

    def set_y_limits(self, limit: Optional[float]) -> None:
        """Thiết lập giới hạn trục Y."""
        self._y_limit = limit
        self._bg = None  # Force full redraw
        self.draw_idle()

    def add_point(self, x: float, y: float) -> None:
        """Thêm điểm mới và cập nhật chart (throttle 30 FPS)."""
        self._x_data.append(x)
        self._y_data.append(y)

        # Trim theo thời gian (deque maxlen là backup)
        if self.max_window_s and self._x_data:
            cutoff = x - self.max_window_s
            while self._x_data and self._x_data[0] < cutoff:
                self._x_data.popleft()
                self._y_data.popleft()

        now = time.monotonic()
        if (now - self._last_draw) < 0.033:  # ~30 FPS throttle
            return

        # Update line data
        self.line.set_data(list(self._x_data), list(self._y_data))

        # X-axis sliding window
        if self._x_data:
            x_min, x_max = self._x_data[0], self._x_data[-1]
            if x_max <= x_min:
                x_max = x_min + 1
            self.ax.set_xlim(x_min, x_max)

        # Y-axis
        if self._y_limit is not None and self._y_data:
            y_min_data = min(self._y_data)
            y_max_data = max(self._y_data)
            y_low = min(-self._y_limit, y_min_data * 1.1)
            y_high = max(self._y_limit, y_max_data * 1.1)
            self.ax.set_ylim(y_low, y_high)
        elif self._y_data:
            self.ax.relim()
            self.ax.autoscale_view(scalex=False, scaley=True)

        # Blit rendering: chỉ vẽ lại line nếu có background cache
        if self._bg is not None:
            try:
                self.restore_region(self._bg)
                self.ax.draw_artist(self.line)
                self.blit(self.ax.bbox)
            except Exception:
                # Fallback nếu blit fail (resize, theme change, ...)
                self._bg = None
                self.draw_idle()
        else:
            # Full draw lần đầu hoặc sau khi invalidate
            self.draw_idle()
            # Schedule background save cho frame tiếp theo
            try:
                self._bg = self.copy_from_bbox(self.ax.bbox)
            except Exception:
                self._bg = None

        self._last_draw = now

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu."""
        self._x_data.clear()
        self._y_data.clear()
        self.line.set_data([], [])
        self._bg = None
        self.draw()
