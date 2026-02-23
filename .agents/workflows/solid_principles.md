---
description: Áp dụng SOLID Principles khi thiết kế và viết code Python (từ SOLID Handbook - NotebookLM)
---

# SOLID Principles Skill

Khi làm việc với bất kỳ project Python nào, tự động áp dụng 5 nguyên lý SOLID sau đây.

## 1. Single Responsibility Principle (SRP)
**Mỗi class/module chỉ có 1 lý do để thay đổi.**

- ❌ TRÁNH: Một class vừa xử lý UI, vừa kết nối DB, vừa gửi email.
- ✅ LÀM: Chia nhỏ thành `UserController` (chỉ handle request), `CreateUserUseCase` (logic), `EmailService` (gửi mail).
- Khi review code, hỏi: "Class này có bao nhiêu lý do để thay đổi?"
- Mỗi file Python nên có **1 class chính** với 1 trách nhiệm rõ ràng.

## 2. Open/Closed Principle (OCP)
**Mở để mở rộng, đóng để sửa đổi.**

- ❌ TRÁNH: Thêm `if/elif` mới khi có loại mới (if type == 'csv': ... elif type == 'json': ...).
- ✅ LÀM: Dùng `ABC` với `@abstractmethod`. Thêm loại mới = tạo class mới implements ABC.
- Pattern: Strategy, Factory, Plugin.
```python
from abc import ABC, abstractmethod
class IExporter(ABC):
    @abstractmethod
    def export(self, data, path: str) -> bool: ...

class CsvExporter(IExporter): ...   # Thêm loại = tạo file mới
class JsonExporter(IExporter): ...  # Không sửa IExporter hay CsvExporter
```

## 3. Liskov Substitution Principle (LSP)
**Subclass phải có thể thay thế base class mà không làm hỏng chương trình.**

- Nếu function nhận `IModbusClient`, bất kỳ implementation nào (RTU, TCP, Mock) phải hoạt động đúng.
- ❌ TRÁNH: Subclass override method để throw `NotImplementedError` hoặc thay đổi hành vi unexpected.
- ✅ LÀM: Đảm bảo precondition không mạnh hơn, postcondition không yếu hơn base.

## 4. Interface Segregation Principle (ISP)
**Client không nên phụ thuộc vào methods nó không dùng.**

- ❌ TRÁNH: Interface khổng lồ với 20 method → class phải implement hết nhưng chỉ dùng 3.
- ✅ LÀM: Nhiều interface nhỏ, chuyên biệt.
```python
class IReadable(ABC):
    @abstractmethod
    def read(self) -> str: ...

class IWritable(ABC):
    @abstractmethod
    def write(self, data: str): ...

# ReadOnly client chỉ implement IReadable
# ReadWrite client implement cả hai
```

## 5. Dependency Inversion Principle (DIP)
**High-level modules phụ thuộc vào abstractions, không phụ thuộc vào concretions.**

- ❌ TRÁNH: `service = ModbusRtuClient(port='COM3')` hard-code bên trong business logic.
- ✅ LÀM: Inject qua constructor.
```python
class DataCollector:
    def __init__(self, client: IModbusClient):  # Nhận abstraction
        self._client = client

# Tạo ở Composition Root (main.py)
collector = DataCollector(client=ModbusRtuClient('COM3'))
```

## Cấu trúc thư mục khuyến nghị (Clean Architecture)
```
project/
├── domain/          # Zero-dependency: entities, value objects, constants
├── application/     # Use cases + interfaces (ABCs)
├── infrastructure/  # DB, API, Modbus clients (implement interfaces)
├── exporters/       # OCP: thêm format = thêm file mới
├── ui/              # Presentation layer (inject services từ ngoài)
└── main.py          # Composition Root – nơi DÚY NHẤT tạo + ghép dependencies
```

## Checklist trước khi commit code

- [ ] Mỗi class có ≤ 1 lý do thay đổi (SRP)?
- [ ] Thêm tính năng mới không sửa code cũ (OCP)?
- [ ] Mọi implementation có thể swap mà không break (LSP)?
- [ ] Interfaces nhỏ, không "bloated" (ISP)?
- [ ] Business logic không import infrastructure trực tiếp (DIP)?
- [ ] `main.py` hoặc Composition Root là nơi DUY NHẤT tạo concrete objects?
- [ ] Dùng `logging` module thay vì `print()`?
- [ ] Class/function có docstring mô tả rõ trách nhiệm?
