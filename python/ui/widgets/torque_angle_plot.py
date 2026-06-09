"""
UI Widgets – Real-Time Torque-Angle Plot
=========================================
Widget vẽ biểu đồ Torque vs Angle thời gian thực sử dụng Matplotlib blit.
Không trượt trục X theo thời gian mà giữ nguyên thang đo góc xoay.
"""

import time
from collections import deque
from typing import Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import matplotlib.path as mpath

# Sửa lỗi đệ quy trên Python 3.12+
try:
    del mpath.Path.__deepcopy__
except AttributeError:
    pass


class TorqueAnglePlot(FigureCanvas):
    """
    Widget vẽ biểu đồ Mô-men xoắn (Y) theo Góc xoay (X).
    Tối ưu hóa: blit + throttle vẽ mượt mà.
    """

    def __init__(
        self,
        title: str = "Torque vs Angle",
        xlabel: str = "Angle (deg)",
        ylabel: str = "Torque (Nm)",
        color: str = '#ff9900',  # Màu cam đặc trưng cho góc
    ):
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.fig.patch.set_facecolor('#181820')
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

        self._x_data: list = []
        self._y_data: list = []
        self._last_draw = 0.0
        
        # Giới hạn trục
        self._y_limit: Optional[float] = None
        self._min_angle = -45.0
        self._max_angle = 45.0

        # Style mặc định (dark)
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
        self._last_xlim = None
        self._last_ylim = None

    def _save_background(self):
        """Lưu background (axes, grid, labels) để blit."""
        self.draw()
        self._bg = self.copy_from_bbox(self.ax.bbox)
        self._last_xlim = self.ax.get_xlim()
        self._last_ylim = self.ax.get_ylim()

    def set_y_limits(self, limit: Optional[float]) -> None:
        """Thiết lập giới hạn trục Y."""
        self._y_limit = limit
        self._bg = None  # Force full redraw
        self.draw_idle()

    def set_angle_limits(self, min_angle: float, max_angle: float) -> None:
        """Thiết lập giới hạn trục X (Góc xoay) tương ứng với sản phẩm."""
        # Thêm 10% biên an toàn cho biểu đồ rộng rãi
        margin = max(5.0, abs(max_angle - min_angle) * 0.1)
        self._min_angle = min_angle - margin
        self._max_angle = max_angle + margin
        self.ax.set_xlim(self._min_angle, self._max_angle)
        self._bg = None  # Invalidate background cache
        self.draw_idle()

    def add_point(self, angle: float, torque: float) -> None:
        """Thêm điểm mới (góc, torque) và cập nhật đồ thị (throttle 30 FPS)."""
        self._x_data.append(angle)
        self._y_data.append(torque)

        now = time.monotonic()
        if (now - self._last_draw) < 0.033:  # Giới hạn ~30 FPS
            return

        # Cập nhật dữ liệu cho đường line
        self.line.set_data(self._x_data, self._y_data)

        # Thiết lập trục X theo giới hạn đã định
        self.ax.set_xlim(self._min_angle, self._max_angle)

        # Thiết lập trục Y
        if self._y_limit is not None and self._y_data:
            y_min_data = min(self._y_data)
            y_max_data = max(self._y_data)
            y_low = min(-self._y_limit, y_min_data * 1.1)
            y_high = max(self._y_limit, y_max_data * 1.1)
            self.ax.set_ylim(y_low, y_high)
        elif self._y_data:
            self.ax.relim()
            self.ax.autoscale_view(scalex=False, scaley=True)

        # Kiểm tra xem giới hạn trục thực tế có thay đổi so với cache blit không
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()
        if self._last_xlim != current_xlim or self._last_ylim != current_ylim:
            self._bg = None  # Invalidate background cache
            self._last_xlim = current_xlim
            self._last_ylim = current_ylim

        # Vẽ biểu đồ sử dụng Blitting tăng tốc
        if self._bg is not None:
            try:
                self.restore_region(self._bg)
                self.ax.draw_artist(self.line)
                self.blit(self.ax.bbox)
            except Exception:
                self._bg = None
                self.draw_idle()
        else:
            self.draw_idle()
            try:
                self._bg = self.copy_from_bbox(self.ax.bbox)
            except Exception:
                self._bg = None

        self._last_draw = now

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu đồ thị."""
        self._x_data.clear()
        self._y_data.clear()
        self.line.set_data([], [])
        self._bg = None
        self._last_xlim = None
        self._last_ylim = None
        self.draw()

