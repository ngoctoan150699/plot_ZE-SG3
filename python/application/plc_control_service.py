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
    PLC_D109_RESET_FAULT,
    PLC_D110_JOG_PLUS,
    PLC_D111_JOG_MINUS,
    PLC_D112_HOME_CMD,
    PLC_DEFAULT_SLAVE_ID,
    PLC_STATUS_REGISTER_COUNT,
    PLC_STATUS_START_ADDRESS,
)
from domain.plc_protocol import PlcStatus, PlcTestConfig, clamp_u16

logger = logging.getLogger(__name__)


class PlcControlService:
    """Application service for PLC servo/state-machine commands."""

    def __init__(self, client: IModbusClient, slave_id: int = PLC_DEFAULT_SLAVE_ID):
        self._client = client
        self._slave_id = slave_id

    def set_client(self, client: IModbusClient, slave_id: int = PLC_DEFAULT_SLAVE_ID) -> None:
        """Replace Modbus client/slave after the UI connects or reconnects."""
        self._client = client
        self._slave_id = slave_id

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

    def pulse_cmd_bit(self, bit_mask: int, pulse_ms: int = 150) -> bool:
        """
        Pulse one bit in D100 using read-modify-write.

        Never write D100 = bit_mask directly because other command bits may be
        held by jog/abort or future commands.
        """
        bit_mask = clamp_u16(bit_mask)
        try:
            current = self._client.read_register(PLC_D100_CMD_WORD, self._slave_id)
            if current is None:
                return False
            current = clamp_u16(current)
            set_value = current | bit_mask
            if not self._client.write_register(PLC_D100_CMD_WORD, set_value, self._slave_id):
                return False
            time.sleep(max(0, int(pulse_ms)) / 1000.0)
            latest = self._client.read_register(PLC_D100_CMD_WORD, self._slave_id)
            if latest is None:
                latest = set_value
            clear_value = clamp_u16(latest) & ~bit_mask
            return bool(self._client.write_register(PLC_D100_CMD_WORD, clear_value, self._slave_id))
        except Exception as exc:
            logger.debug("PLC pulse_cmd_bit(%s) failed: %s", bit_mask, exc)
            return False

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

    def _write_bool_register(self, address: int, active: bool) -> bool:
        try:
            return bool(self._client.write_register(address, 1 if active else 0, self._slave_id))
        except Exception as exc:
            logger.debug("PLC write bool register %s failed: %s", address, exc)
            return False

    def _write_pulse_register(self, address: int, pulse_ms: int = 150) -> bool:
        try:
            if not self._client.write_register(address, 1, self._slave_id):
                return False
            time.sleep(max(0, int(pulse_ms)) / 1000.0)
            return bool(self._client.write_register(address, 0, self._slave_id))
        except Exception as exc:
            logger.debug("PLC pulse register %s failed: %s", address, exc)
            return False
