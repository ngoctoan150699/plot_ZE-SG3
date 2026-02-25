"""
Application Layer – Interfaces (Abstract Base Classes)
=======================================================
Định nghĩa các hợp đồng (contracts) theo DIP:
- High-level modules phụ thuộc vào abstractions, không phải implementations.
- Giúp swap infrastructure (RTU ↔ TCP ↔ Mock) mà không sửa logic nghiệp vụ.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from domain.entities import DeviceConfig, DeviceStatus, RecordingSession


class IModbusClient(ABC):
    """
    Hợp đồng giao tiếp Modbus – RTU lẫn TCP đều implement interface này.
    Application layer chỉ dùng interface này, không biết đến pymodbus cụ thể.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Thiết lập kết nối. Trả về True nếu thành công."""

    @abstractmethod
    def disconnect(self) -> None:
        """Ngắt kết nối và giải phóng tài nguyên."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Kiểm tra trạng thái kết nối hiện tại."""

    @abstractmethod
    def read_register(self, address: int, slave_id: int = 1) -> Optional[int]:
        """
        Đọc 1 Holding Register (UINT16).
        Trả về None nếu lỗi.
        """

    @abstractmethod
    def read_registers(self, address: int, count: int, slave_id: int = 1) -> Optional[list]:
        """
        Đọc nhiều Holding Registers liên tiếp.
        Trả về list các int, hoặc None nếu lỗi.
        """

    @abstractmethod
    def write_register(self, address: int, value: int, slave_id: int = 1) -> bool:
        """
        Ghi 1 Holding Register (UINT16).
        Trả về True nếu thành công.
        """

    @abstractmethod
    def write_registers(self, address: int, values: list, slave_id: int = 1) -> bool:
        """
        Ghi nhiều Holding Registers liên tiếp (Preset Multiple Registers).
        Trả về True nếu thành công.
        """

    def read_float32(self, address_hi: int, slave_id: int = 1) -> Optional[float]:
        """
        Đọc 2 Holding Registers liên tiếp và giải mã thành Float32 IEEE 754 (MSW first).
        Phương thức tiện ích, không cần override.
        """
        import struct
        regs = self.read_registers(address_hi, 2, slave_id)
        if regs is None or len(regs) < 2:
            return None
        try:
            packed = struct.pack('>HH', regs[0] & 0xFFFF, regs[1] & 0xFFFF)
            return struct.unpack('>f', packed)[0]
        except Exception:
            return None

    def write_float32(self, address_hi: int, value: float, slave_id: int = 1) -> bool:
        """
        Chuyển Float32 thành 2 Holding Registers và ghi lên thiết bị (MSW first).
        Phương thức tiện ích, dùng write_registers để ghi 1 lần tránh race condition.
        """
        import struct
        try:
            packed = struct.pack('>f', value)
            regs = list(struct.unpack('>HH', packed))
            return self.write_registers(address_hi, regs, slave_id)
        except Exception:
            return False



class IDataExporter(ABC):
    """
    Hợp đồng xuất dữ liệu – theo Open/Closed Principle.
    Thêm định dạng mới = tạo class mới implement IDataExporter,
    KHÔNG sửa code cũ.
    """

    @abstractmethod
    def export(self, session: RecordingSession, file_path: str) -> bool:
        """
        Xuất dữ liệu session ra file.
        Trả về True nếu thành công.
        """

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Tên hiển thị trên UI (VD: 'CSV Đơn Giản', 'CTR Format #1')."""

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Extension file (VD: '.csv', '.txt')."""


class ISettingsRepository(ABC):
    """
    Hợp đồng lưu/tải cài đặt ứng dụng – Repository Pattern.
    """

    @abstractmethod
    def load_connection_config(self) -> 'ConnectionConfig':
        """Tải cấu hình kết nối Modbus đã lưu."""

    @abstractmethod
    def save_connection_config(self, config: 'ConnectionConfig') -> None:
        """Lưu cấu hình kết nối Modbus."""

    @abstractmethod
    def load_device_config(self) -> DeviceConfig:
        """Tải cấu hình thiết bị đã lưu."""

    @abstractmethod
    def save_device_config(self, config: DeviceConfig) -> None:
        """Lưu cấu hình thiết bị."""
