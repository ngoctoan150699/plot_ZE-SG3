"""
Infrastructure Layer – PLC Servo Controller
===========================================
Implementations of IPLCServoController:
1. PLCServoController: Điều khiển thực qua Modbus PLC.
2. DummyPLCServoController: Giả lập chuyển động và trạng thái thanh ghi PLC.
"""

import time
import logging
from typing import Optional

from application.interfaces import IPLCServoController, IModbusClient
from domain.constants import (
    REG_PLC_CONTROL, REG_PLC_STATUS, REG_PLC_TARGET_ANGLE, REG_PLC_SPEED,
    PLC_CMD_START, PLC_CMD_STOP, PLC_CMD_SERVO_ON, PLC_CMD_SERVO_OFF,
    PLC_STATUS_READY, PLC_STATUS_ENABLED, PLC_STATUS_MOVING, PLC_STATUS_IN_POSITION,
    PLC_DEFAULT_SLAVE_ID
)

logger = logging.getLogger(__name__)


class PLCServoController(IPLCServoController):
    """
    Điều khiển Servo thực tế thông qua việc đọc/ghi Modbus PLC.
    """

    def __init__(self, modbus_client: IModbusClient, slave_id: int = PLC_DEFAULT_SLAVE_ID):
        self._client = modbus_client
        self._slave_id = slave_id

    def set_target_angle(self, angle: float) -> bool:
        logger.info(f"PLC: Ghi góc đích {angle}°")
        return self._client.write_float32(REG_PLC_TARGET_ANGLE, angle, self._slave_id)

    def set_speed(self, speed: float) -> bool:
        logger.info(f"PLC: Ghi tốc độ {speed} rpm")
        return self._client.write_float32(REG_PLC_SPEED, speed, self._slave_id)

    def write_command(self, cmd: int) -> bool:
        logger.info(f"PLC: Ghi control word = {cmd}")
        return self._client.write_register(REG_PLC_CONTROL, cmd, self._slave_id)

    def read_status(self) -> Optional[int]:
        return self._client.read_register(REG_PLC_STATUS, self._slave_id)

    def is_moving(self) -> bool:
        status = self.read_status()
        if status is None:
            return False
        return (status & PLC_STATUS_MOVING) != 0

    def is_in_position(self) -> bool:
        status = self.read_status()
        if status is None:
            return False
        return (status & PLC_STATUS_IN_POSITION) != 0


class DummyPLCServoController(IPLCServoController):
    """
    Giả lập điều khiển Servo PLC khi chạy offline không có thiết bị.
    """

    def __init__(self):
        self._target_angle = 0.0
        self._current_angle = 0.0
        self._speed = 10.0
        self._control_word = 0
        self._status_word = PLC_STATUS_READY
        self._last_cmd_time = 0.0
        self._start_angle = 0.0

    def set_target_angle(self, angle: float) -> bool:
        self._target_angle = angle
        return True

    def set_speed(self, speed: float) -> bool:
        self._speed = speed
        return True

    def write_command(self, cmd: int) -> bool:
        self._control_word = cmd
        
        if cmd == PLC_CMD_START:
            # Bật bit MOVING và tắt bit IN_POSITION
            self._status_word = (self._status_word | PLC_STATUS_MOVING) & ~PLC_STATUS_IN_POSITION
            self._last_cmd_time = time.monotonic()
            self._start_angle = self._current_angle
            logger.info(f"Dummy PLC: Servo bắt đầu di chuyển từ {self._current_angle:.1f}° -> {self._target_angle:.1f}° với tốc độ {self._speed:.1f} rpm")
        
        elif cmd == PLC_CMD_STOP:
            # Tắt bit MOVING
            self._status_word &= ~PLC_STATUS_MOVING
            logger.info("Dummy PLC: Dừng servo khẩn cấp")
        
        elif cmd == PLC_CMD_SERVO_ON:
            # Bật bit ENABLED
            self._status_word |= PLC_STATUS_ENABLED
            logger.info("Dummy PLC: Servo ENABLE")
        
        elif cmd == PLC_CMD_SERVO_OFF:
            # Tắt bit ENABLED và MOVING
            self._status_word &= ~(PLC_STATUS_ENABLED | PLC_STATUS_MOVING)
            logger.info("Dummy PLC: Servo DISABLE")
            
        return True

    def read_status(self) -> Optional[int]:
        # Cập nhật trạng thái chuyển động giả lập dựa trên thời gian trôi qua
        if (self._status_word & PLC_STATUS_MOVING) != 0:
            elapsed = time.monotonic() - self._last_cmd_time
            # 1 rpm = 6 độ/giây
            deg_per_sec = self._speed * 6.0
            distance = deg_per_sec * elapsed
            total_needed = abs(self._target_angle - self._start_angle)
            
            if total_needed == 0:
                self._current_angle = self._target_angle
                # Tắt MOVING, bật IN_POSITION
                self._status_word = (self._status_word & ~PLC_STATUS_MOVING) | PLC_STATUS_IN_POSITION
            elif distance >= total_needed:
                self._current_angle = self._target_angle
                # Tắt MOVING, bật IN_POSITION
                self._status_word = (self._status_word & ~PLC_STATUS_MOVING) | PLC_STATUS_IN_POSITION
                logger.info(f"Dummy PLC: Servo đã đến vị trí đích {self._target_angle:.1f}°")
            else:
                direction = 1.0 if self._target_angle > self._start_angle else -1.0
                self._current_angle = self._start_angle + direction * distance
                
        return self._status_word

    def is_moving(self) -> bool:
        status = self.read_status()
        return (status & PLC_STATUS_MOVING) != 0

    def is_in_position(self) -> bool:
        status = self.read_status()
        return (status & PLC_STATUS_IN_POSITION) != 0
