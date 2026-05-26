"""
Application Layer – Servo Sequence Service
===========================================
Điều phối chu trình chạy của Servo qua PLC và tính toán góc quay thời gian thực.
"""

import time
import threading
import logging
from typing import Callable, Optional

from domain.entities import ServoProfile
from application.interfaces import IPLCServoController
from domain.constants import (
    PLC_CMD_START, PLC_CMD_STOP, PLC_CMD_SERVO_ON, PLC_CMD_SERVO_OFF
)

logger = logging.getLogger(__name__)


class ServoService:
    """
    Quản lý chu trình chạy Servo trong luồng nền (background thread).
    Tính toán góc xoay thời gian thực bằng: angle = speed_rpm * 6.0 * elapsed_time.
    """

    def __init__(self, plc_controller: IPLCServoController):
        self._plc = plc_controller
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Trạng thái hiện tại
        self._current_angle = 0.0
        self._current_cycle = 0
        self._speed_rpm = 10.0
        self._direction = 1.0  # 1.0: quay thuận, -1.0: quay nghịch
        self._recording_active = False  # Cờ cho biết có đang trong pha ghi dữ liệu không
        
        # Sự kiện dừng chuyển động hiện tại
        self._stop_event = threading.Event()
        
        # Callbacks
        self._on_angle_updated: Optional[Callable[[float, int, bool], None]] = None  # angle, cycle, recording_active
        self._on_finished: Optional[Callable[[], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    def register_callbacks(
        self,
        on_angle_updated: Callable[[float, int, bool], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None]
    ) -> None:
        """Đăng ký các callback để cập nhật lên UI."""
        self._on_angle_updated = on_angle_updated
        self._on_finished = on_finished
        self._on_error = on_error

    def start_operating_test(self, profile: ServoProfile, num_cycles: int = 3) -> bool:
        """Bắt đầu chu trình đo Operating Torque (0 -> + -> - -> 0 x N cycles)."""
        if self._running:
            return False
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_operating_loop,
            args=(profile, num_cycles),
            name="Servo-Operating-Worker",
            daemon=True
        )
        self._thread.start()
        return True

    def start_breakaway_test(self, profile: ServoProfile) -> bool:
        """Bắt đầu chu trình đo Breakaway Torque (0 -> + -> 0, chỉ ghi dữ liệu chiều đi)."""
        if self._running:
            return False
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_breakaway_loop,
            args=(profile,),
            name="Servo-Breakaway-Worker",
            daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        """Dừng khẩn cấp chu trình đang chạy."""
        self._running = False
        self._stop_event.set()
        # Gửi lệnh dừng khẩn cấp tới PLC
        try:
            self._plc.write_command(PLC_CMD_STOP)
            self._plc.write_command(PLC_CMD_SERVO_OFF)
        except Exception as e:
            logger.error(f"Lỗi khi gửi lệnh dừng khẩn cấp tới PLC: {e}")

    def is_running(self) -> bool:
        return self._running

    def get_current_angle(self) -> float:
        return self._current_angle

    def get_current_cycle(self) -> int:
        return self._current_cycle

    # === Các vòng lặp chạy nền ===

    def _run_operating_loop(self, profile: ServoProfile, num_cycles: int) -> None:
        """Thực thi chu trình Operating Torque."""
        logger.info("Bắt đầu chu trình Operating Torque")
        self._current_angle = 0.0
        self._speed_rpm = profile.speed
        
        try:
            # 1. Bật Servo (Servo On)
            if not self._plc.write_command(PLC_CMD_SERVO_ON):
                raise RuntimeError("Không thể bật Servo (Servo ON)")
            time.sleep(0.5)  # Chờ Servo sẵn sàng
            
            # Thiết lập tốc độ trên PLC
            self._plc.set_speed(profile.speed)
            
            for cycle in range(1, num_cycles + 1):
                if self._stop_event.is_set() or not self._running:
                    break
                self._current_cycle = cycle
                logger.info(f"Operating: Bắt đầu Cycle {cycle}/{num_cycles}")
                
                # Pha A: 0 -> Positive Angle (Ghi dữ liệu hoạt động)
                self._recording_active = True
                if not self._move_to_angle_and_wait(profile.positive_angle):
                    break
                
                # Pha B: Positive -> Negative Angle (Ghi dữ liệu hoạt động)
                if not self._move_to_angle_and_wait(profile.negative_angle):
                    break
                
                # Pha C: Negative -> 0 (Ghi dữ liệu hoạt động)
                if not self._move_to_angle_and_wait(0.0):
                    break

            # Tắt Servo sau khi chạy xong
            self._plc.write_command(PLC_CMD_SERVO_OFF)
            
        except Exception as e:
            logger.error(f"Lỗi chu trình Operating: {e}")
            if self._on_error:
                self._on_error(str(e))
        finally:
            self._running = False
            self._recording_active = False
            if self._on_finished:
                self._on_finished()

    def _run_breakaway_loop(self, profile: ServoProfile) -> None:
        """Thực thi chu trình Breakaway Torque."""
        logger.info("Bắt đầu chu trình Breakaway Torque")
        self._current_angle = 0.0
        self._current_cycle = 1
        self._speed_rpm = profile.speed
        
        try:
            # 1. Bật Servo (Servo On)
            if not self._plc.write_command(PLC_CMD_SERVO_ON):
                raise RuntimeError("Không thể bật Servo (Servo ON)")
            time.sleep(0.5)
            
            # Thiết lập tốc độ
            self._plc.set_speed(profile.speed)
            
            # Chiều đi: 0 -> Positive Angle (Bắt đầu ghi dữ liệu)
            self._recording_active = True
            if self._move_to_angle_and_wait(profile.positive_angle):
                # Chiều về: Positive -> 0 (Tắt ghi dữ liệu)
                self._recording_active = False
                self._move_to_angle_and_wait(0.0)

            # Tắt Servo
            self._plc.write_command(PLC_CMD_SERVO_OFF)
            
        except Exception as e:
            logger.error(f"Lỗi chu trình Breakaway: {e}")
            if self._on_error:
                self._on_error(str(e))
        finally:
            self._running = False
            self._recording_active = False
            if self._on_finished:
                self._on_finished()

    def _move_to_angle_and_wait(self, target_angle: float) -> bool:
        """Gửi lệnh di chuyển và chờ cho đến khi hoàn tất, đồng thời tính toán góc."""
        # Xác định hướng xoay
        self._direction = 1.0 if target_angle > self._current_angle else -1.0
        
        # Ghi góc đích lên PLC
        if not self._plc.set_target_angle(target_angle):
            raise RuntimeError(f"Không thể ghi góc đích {target_angle}° lên PLC")
            
        # Kích hoạt lệnh di chuyển (START)
        if not self._plc.write_command(PLC_CMD_START):
            raise RuntimeError("Không thể gửi lệnh START di chuyển tới PLC")

        last_time = time.monotonic()
        
        # Vòng lặp chờ phản hồi vị trí thô
        # Polling khoảng 20ms
        while self._running and not self._stop_event.is_set():
            time.sleep(0.02)
            
            # Tính toán góc xoay theo thời gian trôi qua
            now = time.monotonic()
            dt = now - last_time
            last_time = now
            
            # Tốc độ góc (độ/giây) = rpm * 6
            deg_per_sec = self._speed_rpm * 6.0
            delta_angle = self._direction * deg_per_sec * dt
            self._current_angle += delta_angle
            
            # Giới hạn góc tính toán tránh vượt quá đích do độ trễ thời gian
            if self._direction > 0:
                if self._current_angle >= target_angle:
                    self._current_angle = target_angle
            else:
                if self._current_angle <= target_angle:
                    self._current_angle = target_angle
            
            # Gửi callback góc cập nhật lên UI
            if self._on_angle_updated:
                self._on_angle_updated(self._current_angle, self._current_cycle, self._recording_active)
                
            # Đọc trạng thái từ PLC để kiểm tra xem đã đến đích chưa
            if self._plc.is_in_position():
                self._current_angle = target_angle  # Đồng bộ chính xác góc đích
                if self._on_angle_updated:
                    self._on_angle_updated(self._current_angle, self._current_cycle, self._recording_active)
                return True
                
        return False
