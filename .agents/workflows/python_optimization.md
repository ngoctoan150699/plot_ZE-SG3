---
description: Tối ưu hóa code Python – best practices về performance, threading, typing, và logging
---

# Python Optimization Skill

Áp dụng các best practices sau để code Python chạy nhanh, an toàn và dễ bảo trì.

## 1. Typing – Khai báo kiểu dữ liệu rõ ràng
```python
from typing import Optional, List, Dict, Callable, Tuple
from dataclasses import dataclass

@dataclass
class SampleData:
    time_s: float
    value: float
    stable: bool

def process(samples: List[SampleData]) -> Optional[float]:
    ...
```
- Dùng `dataclasses` thay vì dict khi có cấu trúc cố định.
- Khai báo `Optional[X]` khi giá trị có thể là `None`.
- Dùng `-> None` cho method không trả về.

## 2. Threading – Thread Safety
```python
import threading
import queue

# ✅ ĐÚNG: Dùng Event để stop thread gracefully
stop_event = threading.Event()
data_queue: queue.Queue = queue.Queue(maxsize=1000)

def worker():
    while not stop_event.is_set():
        # ... đọc dữ liệu
        stop_event.wait(timeout=0.1)  # Cho phép stop ngay lập tức

# ❌ TRÁNH: time.sleep() dài trong thread (không thể interrupt nhanh)
# ❌ TRÁNH: bool flag không dùng threading.Event (race condition)
# ❌ TRÁNH: Chia sẻ list/dict giữa threads mà không dùng Lock hay Queue
```

## 3. Logging – Dùng logging module thay vì print()
```python
import logging
logger = logging.getLogger(__name__)

# Setup ở main.py (1 lần duy nhất)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Dùng đúng level:
logger.debug("Chi tiết: giá trị thanh ghi = %d", val)   # Dev only
logger.info("Kết nối thành công COM3")                   # Thông tin
logger.warning("Lỗi đọc Modbus, thử lại")               # Cảnh báo
logger.error("Không thể kết nối: %s", str(e))           # Lỗi
```

## 4. Performance – Tối ưu vòng lặp và cấu trúc dữ liệu
```python
# ✅ Dùng collections.deque thay list khi pop(0) nhiều
from collections import deque
buffer = deque(maxlen=6000)  # Tự động drop phần tử cũ

# ✅ List comprehension nhanh hơn for-loop append
rows = [process(s) for s in samples if s.stable]

# ✅ Join string nhanh hơn +=
parts = [f"{x:.6f}" for x in values]
result = ','.join(parts)

# ✅ time.monotonic() cho đo elapsed time (không bị ảnh hưởng system clock)
start = time.monotonic()
elapsed = time.monotonic() - start

# ❌ TRÁNH: list.pop(0) O(n) – dùng deque.popleft() O(1)
# ❌ TRÁNH: string += trong vòng lặp lớn
```

## 5. Exception Handling – Xử lý lỗi đúng cách
```python
# ✅ ĐÚNG: Catch exception cụ thể, log rõ ràng
try:
    result = client.read_holding_registers(addr, 2)
except ConnectionError as e:
    logger.error("Mất kết nối: %s", e)
    return None
except Exception as e:
    logger.exception("Lỗi không mong đợi")  # In cả traceback
    return None

# ❌ TRÁNH: bare except: (bắt cả SystemExit, KeyboardInterrupt)
# ❌ TRÁNH: except Exception: pass (nuốt lỗi im lặng)
```

## 6. Resource Management – Context Manager
```python
# ✅ Luôn dùng with cho file, connection
with open(path, 'w', encoding='utf-8') as f:
    writer.writerow(...)

# ✅ Implement __enter__/__exit__ cho các resource custom
class ModbusConnection:
    def __enter__(self): self.connect(); return self
    def __exit__(self, *_): self.disconnect()
```

## 7. Anti-patterns cần tránh
| ❌ Anti-pattern | ✅ Thay bằng |
|:---|:---|
| `global state` | Dependency Injection |
| `def func(items=[])` mutable default | `def func(items=None): items = items or []` |
| `import *` | Import cụ thể |
| Magic number `49914` | Constant có tên `CMD_TARE = 49914` |
| `print()` cho debug | `logger.debug()` |
| `time.sleep()` lớn trong thread | `stop_event.wait(timeout=...)` |
| Đọc từng register riêng lẻ | Đọc block liên tiếp (ít Modbus round-trip) |

## 8. Code Structure
- **Newspaper Principle**: Chi tiết quan trọng ở đầu file, implementation thấp ở dưới.
- **Function ≤ 20 dòng**: Nếu dài hơn, extract ra function con.
- **Magic number → Constant**: Mọi số "magic" phải đặt tên.
- **CQS**: Function hoặc là Command (thay đổi state, return None) hoặc Query (trả về data, không side effect).

## 9. Profiling khi cần tối ưu
```python
# Đo thời gian
import cProfile
cProfile.run('my_function()')

# Đo specific block
import timeit
elapsed = timeit.timeit('data_list.pop(0)', number=10000)
```
