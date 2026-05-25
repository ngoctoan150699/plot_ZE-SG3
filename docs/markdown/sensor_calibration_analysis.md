# Phân Tích Quy Đổi mV/V ↔ Nm: Cảm Biến DYJN-101 + Seneca ZE-SG3

## Thông Tin Cảm Biến DYJN-101 (SN: 2601351)

| Thông số | Giá trị |
| :--- | :--- |
| **Model** | DAYSENSOR DYJN-101 |
| **Serial No.** | 2601351 |
| **Rated Output (Độ nhạy)** | ~2.0 mV/V |
| **Rated Capacity (Dải đo tối đa)** | ~50 Nm |
| **Hệ số quy đổi** | **1 mV/V = 25 Nm** |
| **Sai số cho phép (MPE)** | ±1.00% |
| **Trở kháng** | 350±5 Ω |
| **Điện áp hoạt động** | 5 ~ 15 V |
| **An toàn quá tải** | 120% (Extreme: 150%) |

---

## Công Thức Quy Đổi mV/V → Nm

> [!IMPORTANT]
> **Torque (Nm) = Giá trị đo (mV/V) × (Cell Full Scale / Cell Sensitivity)**
>
> Với cảm biến DYJN-101 này: **Torque (Nm) = mV/V × 25**

### Giải thích:
- **Cell Sensitivity**: 1.9880 mV/V (rated output từ chứng chỉ hiệu chuẩn)
- **Cell Full Scale**: 49.70 Nm (rated capacity)
- **Hệ số**: 49.70 / 1.9880 ≈ **25 Nm/mV/V**

---

## Bảng Quy Đổi Chuẩn (Từ Chứng Chỉ Hiệu Chuẩn)

### Chiều thuận (Clockwise - CW)

| mV/V | Nm (Chỉ thị) | Nm (Chuẩn) | Sai lệch (Nm) | Sai số (%) |
| :---: | :---: | :---: | :---: | :---: |
| 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| 0.3974 | 9.94 | 9.94 | -0.01 | -0.05 |
| 0.7945 | 19.86 | 19.88 | -0.02 | -0.08 |
| 1.1924 | 29.81 | 29.82 | -0.01 | -0.03 |
| 1.5885 | 39.71 | 39.76 | -0.05 | -0.12 |
| 1.9861 | 49.65 | 49.70 | -0.05 | -0.09 |

### Chiều ngược (Counterclockwise - CCW)

| mV/V | Nm (Chỉ thị) | Nm (Chuẩn) | Sai lệch (Nm) | Sai số (%) |
| :---: | :---: | :---: | :---: | :---: |
| 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| 0.3978 | 9.95 | 9.94 | 0.01 | 0.05 |
| 0.7962 | 19.91 | 19.88 | 0.02 | 0.13 |
| 1.1942 | 29.86 | 29.82 | 0.04 | 0.12 |
| 1.5925 | 39.81 | 39.76 | 0.05 | 0.13 |
| 1.9919 | 49.80 | 49.70 | 0.10 | 0.20 |

> [!NOTE]
> Tất cả các điểm đo đều **ĐẠT** (nằm trong MPE ±1.00%). Độ không đảm bảo đo được tính với k=2 (độ tin cậy ~95%).

---

## Cấu Hình Trên Seneca ZE-SG3

Để thiết lập ZE-SG3 đọc đúng giá trị Nm từ cảm biến DYJN-101:

| Thanh ghi Modbus | Tham số | Giá trị cần đặt |
| :--- | :--- | :--- |
| 40003 | Measure Unit | 8 (Other - vì Nm không có sẵn) |
| 40004 | Measure Type | 0 (Bipolar - đo cả 2 chiều) |
| 40014-15 | Cell Sensitivity | 1.9880 mV/V (từ chứng chỉ hiệu chuẩn) |
| 40016-17 | Cell Full Scale | 49.70 Nm (từ chứng chỉ hiệu chuẩn) |
| 40044 | Resolution Mode | 1 (Manual) |

### Công thức nội bộ của ZE-SG3:
- **Gross Value (Nm)** = (Measured Signal [mV/V] / Cell Sensitivity [mV/V]) × Cell Full Scale [Nm]
- **Net Value (Nm)** = Gross Value - Tare Value

### Ví dụ tính:
- Tín hiệu đo được: 0.7945 mV/V
- Gross = (0.7945 / 1.9880) × 49.70 = **19.86 Nm** ✓

---

## Bảng Tra Nhanh mV/V → Nm

| mV/V | Nm (≈) | % Full Scale |
| :---: | :---: | :---: |
| 0.1 | 2.5 | 5% |
| 0.2 | 5.0 | 10% |
| 0.4 | 10.0 | 20% |
| 0.6 | 15.0 | 30% |
| 0.8 | 20.0 | 40% |
| 1.0 | 25.0 | 50% |
| 1.2 | 30.0 | 60% |
| 1.4 | 35.0 | 70% |
| 1.6 | 40.0 | 80% |
| 1.8 | 45.0 | 90% |
| 2.0 | 50.0 | 100% |

> [!TIP]
> **Quy tắc nhẩm nhanh**: Nhân giá trị mV/V với **25** để ra Nm. Ví dụ: 1.5 mV/V × 25 = 37.5 Nm.

---

## Nguồn Tham Khảo
- **NotebookLM**: Seneca Z-SG3 and ZE-SG3 Series Installation Manual
- **Tài liệu gốc**: `mi00155-3-en.pdf`, `mi00598-3-en.pdf`, `mi00617-4-en.pdf` (Seneca manuals)
- **Chứng chỉ hiệu chuẩn**: `QM-T-091-12_2601351_DYJN-101_DAYSENSOR_Torque Sensor.pdf`
