"""
PLC control service for the D100..D135 Modbus register plan.

This service is intentionally UI-independent. It only depends on IModbusClient
and domain protocol models so it can be tested with a fake Modbus client.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from application.interfaces import IModbusClient
from domain.constants import (
    PLC_CMD_ABORT,
    PLC_CMD_CLEAR_DONE,
    PLC_CMD_CYLINDER_TOGGLE,
    PLC_CMD_START_RECORD,
    PLC_CMD_START_RUN,
    PLC_CMD_STOP_RECORD,
    PLC_CMD_STOP_RUN,
    PLC_CONFIG_START_ADDRESS,
    PLC_D100_CMD_WORD,
    PLC_D101_MODE,
    PLC_D104_SPEED_X100,
    PLC_D109_RESET_FAULT,
    PLC_D110_JOG_PLUS,
    PLC_D111_JOG_MINUS,
    PLC_D112_HOME_CMD,
    PLC_D123_CURRENT_CYCLE,
    PLC_D124_CURRENT_ANGLE_X100,
    PLC_D134_TEST_DONE,
    PLC_DEFAULT_SLAVE_ID,
    PLC_STATUS_REGISTER_COUNT,
    PLC_STATUS_START_ADDRESS,
)
from domain.plc_protocol import (
    PlcRealtimeState,
    PlcStatus,
    PlcTestConfig,
    angle_to_x100,
    clamp_u16,
    decode_signed_16,
    encode_signed_16,
)

logger = logging.getLogger(__name__)


class PlcControlService:
    """Application service for PLC servo/state-machine commands."""

    def __init__(self, client: IModbusClient, slave_id: int = PLC_DEFAULT_SLAVE_ID):
        self._client = client
        self._slave_id = slave_id
        self._scheduler = None
        self._last_written: dict[int, int] = {}

    def set_scheduler(self, scheduler) -> None:
        """Set scheduler to delegate pulse clears instead of spawning threads."""
        self._scheduler = scheduler

    def set_client(self, client: IModbusClient, slave_id: int = PLC_DEFAULT_SLAVE_ID) -> None:
        """Replace Modbus client/slave after the UI connects or reconnects."""
        self._client = client
        self._slave_id = slave_id
        self._last_written.clear()

    @property
    def slave_id(self) -> int:
        return self._slave_id

    def is_connected(self) -> bool:
        """Return True when the underlying client reports an active connection."""
        try:
            return bool(self._client and self._client.is_connected())
        except Exception as exc:
            logger.debug("PLC is_connected failed: %s", exc)
            return False

    def read_cycle_angle_done(self) -> Optional[PlcRealtimeState]:
        """Read minimal realtime PLC data: D123 cycle, D124 angle, D134 done."""
        try:
            regs = self._client.read_registers(
                PLC_STATUS_START_ADDRESS,
                PLC_STATUS_REGISTER_COUNT,
                self._slave_id,
            )
            if regs is None or len(regs) < PLC_STATUS_REGISTER_COUNT:
                return None
            return PlcRealtimeState(
                current_cycle=clamp_u16(regs[3]),
                current_angle_x100=decode_signed_16(regs[4]),
                test_done=clamp_u16(regs[14]),
            )
        except Exception as exc:
            logger.debug("PLC read_cycle_angle_done failed: %s", exc)
            return None

    def read_status(self) -> Optional[PlcStatus]:
        """Read D120..D135 and decode it into PlcStatus."""
        try:
            registers = self._client.read_registers(
                PLC_STATUS_START_ADDRESS,
                PLC_STATUS_REGISTER_COUNT,
                self._slave_id,
            )
            if registers is None:
                return None
            return PlcStatus.from_registers(registers)
        except Exception as exc:
            logger.debug("PLC read_status failed: %s", exc)
            return None

    def write_test_config(self, config: PlcTestConfig) -> bool:
        """Write D101..D108 test configuration as one Modbus block."""
        try:
            return bool(
                self._client.write_registers(
                    PLC_CONFIG_START_ADDRESS,
                    config.to_registers(),
                    self._slave_id,
                )
            )
        except Exception as exc:
            logger.debug("PLC write_test_config failed: %s", exc)
            return False

    def pulse_cmd_bit(self, bit_mask: int, pulse_ms: int = 50) -> bool:
        """Pulse one command bit in D100 with minimum operator latency.

        Return immediately after the SET write succeeds. The CLEAR write runs in
        a short background task so RUN/STOP/Clamp do not wait for a second RTU
        write response before the UI reports success.
        """
        bit_mask = clamp_u16(bit_mask)
        try:
            if self._client.write_register(PLC_D100_CMD_WORD, bit_mask, self._slave_id):
                self._clear_cmd_word_later(pulse_ms)
                return True
        except Exception as exc:
            logger.debug("PLC pulse_cmd_bit(%s) failed: %s", bit_mask, exc)
        return False

    def _clear_cmd_word_later(self, pulse_ms: int) -> None:
        if self._scheduler and hasattr(self._scheduler, 'schedule_clear_register'):
            self._scheduler.schedule_clear_register(PLC_D100_CMD_WORD, 0, self._slave_id, pulse_ms)
            return

        import threading

        def _worker() -> None:
            try:
                time.sleep(max(0, int(pulse_ms)) / 1000.0)
                self._client.write_register(PLC_D100_CMD_WORD, 0, self._slave_id)
            except Exception as exc:
                logger.debug("PLC clear D100 failed: %s", exc)

        threading.Thread(target=_worker, name="PLC-Clear-D100", daemon=True).start()

    def start_run(self) -> bool:
        return self.pulse_cmd_bit(PLC_CMD_START_RUN)

    def stop_run(self) -> bool:
        return self.pulse_cmd_bit(PLC_CMD_STOP_RUN)

    def toggle_cylinder(self) -> bool:
        return self.pulse_cmd_bit(PLC_CMD_CYLINDER_TOGGLE)

    def start_record(self) -> bool:
        return self.pulse_cmd_bit(PLC_CMD_START_RECORD)

    def stop_record(self) -> bool:
        return self.pulse_cmd_bit(PLC_CMD_STOP_RECORD)

    def abort(self) -> bool:
        return self.pulse_cmd_bit(PLC_CMD_ABORT)

    def clear_done(self) -> bool:
        return self.pulse_cmd_bit(PLC_CMD_CLEAR_DONE)

    def reset_fault(self, pulse_ms: int = 150) -> bool:
        """Reset fault with D109 = 1 -> 0."""
        return self._write_pulse_register(PLC_D109_RESET_FAULT, pulse_ms=pulse_ms)

    def jog_plus(self, active: bool) -> bool:
        """Hold/release Jog+ through D110."""
        return self._write_bool_register(PLC_D110_JOG_PLUS, active)

    def jog_minus(self, active: bool) -> bool:
        """Hold/release Jog- through D111."""
        return self._write_bool_register(PLC_D111_JOG_MINUS, active)

    def home(self, pulse_ms: int = 150) -> bool:
        """Pulse Home command through D112 = 1 -> 0."""
        return self._write_pulse_register(PLC_D112_HOME_CMD, pulse_ms=pulse_ms)

    def write_speed(self, speed_rpm: float) -> bool:
        """Write speed (as speed_x100) directly to D104."""
        try:
            val_x100 = int(round(float(speed_rpm) * 100.0))
            return self._write_if_changed(PLC_D104_SPEED_X100, val_x100)
        except Exception as exc:
            logger.debug("PLC write_speed failed: %s", exc)
            return False

    def write_mode(self, mode: int) -> bool:
        """Write PLC mode directly to D101 (0=Manual, 1=Breakaway, 2=Operating)."""
        try:
            return self._write_if_changed(PLC_D101_MODE, clamp_u16(mode))
        except Exception as exc:
            logger.debug("PLC write_mode failed: %s", exc)
            return False

    def write_current_angle(self, angle_deg: float) -> bool:
        """Write current angle to D124 as signed angle x100."""
        try:
            value = encode_signed_16(angle_to_x100(angle_deg))
            return self._write_if_changed(PLC_D124_CURRENT_ANGLE_X100, value)
        except Exception as exc:
            logger.debug("PLC write_current_angle failed: %s", exc)
            return False

    def _write_bool_register(self, address: int, active: bool) -> bool:
        try:
            return self._write_if_changed(address, 1 if active else 0)
        except Exception as exc:
            logger.debug("PLC write bool register %s failed: %s", address, exc)
            return False

    def _write_if_changed(self, address: int, value: int) -> bool:
        value = clamp_u16(value)
        if self._last_written.get(address) == value:
            return True
        ok = bool(self._client.write_register(address, value, self._slave_id))
        if ok:
            self._last_written[address] = value
        return ok

    def _write_pulse_register(self, address: int, pulse_ms: int = 150) -> bool:
        try:
            if not self._client.write_register(address, 1, self._slave_id):
                return False
            
            if self._scheduler and hasattr(self._scheduler, 'schedule_clear_register'):
                self._scheduler.schedule_clear_register(address, 0, self._slave_id, pulse_ms)
                return True
                
            time.sleep(max(0, int(pulse_ms)) / 1000.0)
            return bool(self._client.write_register(address, 0, self._slave_id))
        except Exception as exc:
            logger.debug("PLC pulse register %s failed: %s", address, exc)
            return False
