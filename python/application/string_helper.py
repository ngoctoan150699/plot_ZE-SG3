"""
Application Layer – String Helpers
==================================
Các tiện ích định dạng chuỗi, đặc biệt là loại bỏ dấu tiếng Việt
và chuyển sang chữ viết hoa cho báo cáo.
"""

import unicodedata


def remove_vietnamese_diacritics(text: str) -> str:
    """
    Chuyển đổi chuỗi tiếng Việt có dấu thành chữ in hoa không dấu.
    Ví dụ: 'Nguyễn Văn Hùng' -> 'NGUYEN VAN HUNG'
           'Đỗ Mỹ Linh'      -> 'DO MY LINH'
    """
    if not text:
        return ""

    # Chuẩn hóa Unicode NFD (Normal Form Decomposition)
    # Tách các ký tự có dấu thành ký tự cơ sở + ký tự dấu kết hợp (combining mark)
    nfd_form = unicodedata.normalize('NFD', text)
    
    # Loại bỏ tất cả các ký tự dấu kết hợp (combining marks)
    clean_chars = [c for c in nfd_form if not unicodedata.combining(c)]
    clean_text = "".join(clean_chars)
    
    # Xử lý riêng ký tự chữ 'đ' và 'Đ' vì NFD không tách 'đ' thành 'd' + dấu
    clean_text = clean_text.replace('đ', 'd').replace('Đ', 'D')
    
    # Trả về chuỗi viết hoa và đã cắt bỏ khoảng trắng hai đầu
    return clean_text.upper().strip()
