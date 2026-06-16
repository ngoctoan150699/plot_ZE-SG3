"""
Domain models and helpers for the PLC Modbus register plan D100..D135.

The PC reads torque directly from ZE-SG3. The PLC is responsible for
servo/cylinder state machine control and reports angle/cycle/status here.
"""
from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    PLC_STATUS_CYLINDER_CLAMPED,
    PLC_STATUS_DATA_VALID,
    PLC_STATUS_DONE,
    PLC_STATUS_FAULT,
    PLC_STATUS_RECORDING,
    PLC_STATUS_RUN,
    PLC_STATUS_SERVO_ON_NEW,
    PLC_STATUS_TEST_RUNNING,
)

UINT16_MASK = 0xFFFF
INT16_SIGN_BIT = 0x8000
INT16_MODULO = 0x10000


def clamp_u16(value: int) -> int:
    """Return *value* as an unsigned 16-bit Modbus register value."""
    return int(value) & UINT16_MASK


def encode_signed_16(value: int) -> int:
    """Encode a signed 16-bit integer for a Modbus holding register."""
    value = int(value)
    if not -32768 <= value <= 32767:
        raise ValueError(f"signed 16-bit value out of range: {value}")
    return value & UINT16_MASK


def decode_signed_16(value: int) -> int:
    """Decode a Modbus holding register as a signed 16-bit integer."""
    value = int(value) & UINT16_MASK
    if value & INT16_SIGN_BIT:
        return value - INT16_MODULO
    return value


def angle_to_x100(angle_deg: float) -> int:
    """Convert degrees to the PLC x100 integer representation."""
    return int(round(float(angle_deg) * 100.0))


def x100_to_angle(value: int) -> float:
    """Convert a signed PLC x100 angle register to degrees."""
    return decode_signed_16(value) / 100.0


SERVO_PULSE_PER_REV = 10000.0
GEAR_RATIO = 20.0
OUTPUT_PULSE_PER_REV = SERVO_PULSE_PER_REV * GEAR_RATIO
PULSE_PER_DEGREE = OUTPUT_PULSE_PER_REV / 360.0


def speed_to_x100(speed_deg_s: float) -> int:
    """Convert output speed in deg/s to PLC PLSY pulse/s.

    MAIN.csv uses D104 directly as the first operand of PLSY, so D104 must be
    pulse/s, not deg/s x100. With 10000 pulse/motor rev and gearbox 1:20:
    1 output rev = 200000 pulse, 1 degree = 200000 / 360 pulse.
    """
    value = int(round(float(speed_deg_s) * PULSE_PER_DEGREE))
    if value < 0:
        raise ValueError(f"speed must be non-negative: {speed_deg_s}")
    if value > UINT16_MASK:
        raise ValueError(f"speed pulse/s out of range: {value}")
    return value


def x100_to_speed(value: int) -> float:
    """Convert PLC D104 pulse/s back to output speed in deg/s."""
    return (int(value) & UINT16_MASK) / PULSE_PER_DEGREE


def combine_u32(low: int, high: int) -> int:
    """Combine low/high 16-bit registers into an unsigned 32-bit value."""
    return (clamp_u16(high) << 16) | clamp_u16(low)


@dataclass(frozen=True)
class PlcTestConfig:
    """Configuration block written to PLC registers D101..D108."""

    mode: int
    pos_angle_x100: int
    neg_angle_x100: int
    speed_x100: int
    cycle_set: int
    window_percent: int
    part_select: int
    torque_type: int

    def to_registers(self) -> list[int]:
        """Return values ready for write_registers(D101, values)."""
        return [
            clamp_u16(self.mode),
            encode_signed_16(self.pos_angle_x100),
            encode_signed_16(self.neg_angle_x100),
            clamp_u16(self.speed_x100),
            clamp_u16(self.cycle_set),
            clamp_u16(self.window_percent),
            clamp_u16(self.part_select),
            clamp_u16(self.torque_type),
        ]


@dataclass(frozen=True)
class PlcRealtimeState:
    """Minimal realtime PLC data read while recording."""

    current_cycle: int
    current_angle_x100: int
    test_done: int = 0

    @property
    def is_done(self) -> bool:
        return bool(self.test_done)

    @property
    def has_fault(self) -> bool:
        return False

    @property
    def should_record_sample(self) -> bool:
        return not self.is_done and not self.has_fault

    @property
    def current_angle_deg(self) -> float:
        angle = self.current_angle_x100 / 100.0
        if angle > 180.0:
            angle -= 360.0
        return angle


@dataclass(frozen=True)
class PlcStatus:
    """Status block read from PLC registers D120..D135."""

    status_word: int
    current_mode: int
    current_phase: int
    current_cycle: int
    current_angle_x100: int
    target_angle_x100: int
    current_speed_x100: int
    servo_pulse_low: int
    servo_pulse_high: int
    error_code: int
    data_valid: int
    record_enable: int
    cylinder_status: int
    servo_on_status: int
    test_done: int
    sample_index: int

    @classmethod
    def from_registers(cls, registers: list[int] | tuple[int, ...]) -> "PlcStatus":
        """Build status from the 16-register block D120..D135."""
        if len(registers) < 16:
            raise ValueError(f"PLC status requires 16 registers, got {len(registers)}")
        values = [clamp_u16(value) for value in registers[:16]]
        return cls(
            status_word=values[0],
            current_mode=values[1],
            current_phase=values[2],
            current_cycle=values[3],
            current_angle_x100=decode_signed_16(values[4]),
            target_angle_x100=decode_signed_16(values[5]),
            current_speed_x100=values[6],
            servo_pulse_low=values[7],
            servo_pulse_high=values[8],
            error_code=values[9],
            data_valid=values[10],
            record_enable=values[11],
            cylinder_status=values[12],
            servo_on_status=values[13],
            test_done=values[14],
            sample_index=values[15],
        )

    def _status_bit_or_fallback(self, mask: int, fallback_value: int) -> bool:
        return bool(self.status_word & mask) or bool(fallback_value)

    @property
    def is_running(self) -> bool:
        """PLC RUN state, with conservative phase fallback."""
        return bool(self.status_word & PLC_STATUS_RUN) or self.is_test_running

    @property
    def is_servo_on(self) -> bool:
        """Servo ON state: D120.b1, fallback D133."""
        return self._status_bit_or_fallback(PLC_STATUS_SERVO_ON_NEW, self.servo_on_status)

    @property
    def is_clamped(self) -> bool:
        """Cylinder clamp state: D120.b2, fallback D132."""
        return self._status_bit_or_fallback(PLC_STATUS_CYLINDER_CLAMPED, self.cylinder_status)

    @property
    def is_test_running(self) -> bool:
        """Test running state: D120.b3, fallback phase when not done/fault."""
        if self.status_word & PLC_STATUS_TEST_RUNNING:
            return True
        return self.current_phase != 0 and not self.is_done and not self.has_fault

    @property
    def is_recording(self) -> bool:
        """Recording state: D120.b4, fallback D131."""
        return self._status_bit_or_fallback(PLC_STATUS_RECORDING, self.record_enable)

    @property
    def has_valid_data(self) -> bool:
        """Data valid state: D120.b5, fallback D130."""
        return self._status_bit_or_fallback(PLC_STATUS_DATA_VALID, self.data_valid)

    @property
    def is_done(self) -> bool:
        """Done state: D120.b6, fallback D134."""
        return self._status_bit_or_fallback(PLC_STATUS_DONE, self.test_done)

    @property
    def has_fault(self) -> bool:
        """Fault state: D120.b7, fallback D129 != 0."""
        return bool(self.status_word & PLC_STATUS_FAULT) or self.error_code != 0

    @property
    def should_record_sample(self) -> bool:
        """Return True while PLC is recording.

        D130/data_valid is only a suggested analysis window from PLC/simulator.
        Acquisition must keep the full raw trace; Plot Draw applies 80% filtering later.
        """
        return self.is_recording and not self.is_done and not self.has_fault

    @property
    def current_angle_deg(self) -> float:
        """Current PLC-reported angle in signed degrees.

        The servo/PLC may report a physical 0..360° angle. For the app,
        convert it to the signed convention: 324° -> -36°.
        """
        angle = self.current_angle_x100 / 100.0
        if angle > 180.0:
            angle -= 360.0
        return angle

    @property
    def target_angle_deg(self) -> float:
        """Target PLC-reported angle in degrees."""
        return self.target_angle_x100 / 100.0

    @property
    def current_speed_deg_s(self) -> float:
        """Current PLC-reported speed in deg/s."""
        return self.current_speed_x100 / 100.0

    @property
    def servo_pulse_count(self) -> int:
        """Combined 32-bit servo pulse count from D127/D128."""
        return combine_u32(self.servo_pulse_low, self.servo_pulse_high)
