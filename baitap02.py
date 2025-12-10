import os
import time
import sqlite3
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By

######################################################
# HÀM TÁCH CHUỖI DÒNG HỌA SĨ
######################################################

def parse_painter_line(line: str):
    """
    Ví dụ:
        'Gwilym Prichard (1931–2015) Welsh painter'
    Trả về:
        name, birth_year, death_year, nationality
    """
    line = line.strip().replace(',', '')
    n = len(line)
    i = 0

    # 1) Tên: chạy tới trước dấu '('
    while i < n and line[i] != '(':
        i += 1
    name = line[:i].strip()

    # Nếu không có '(' thì chỉ trả name, còn lại N/A
    if i == n:
        return name, "N/A", "N/A", "N/A"

    # 2) Năm sinh – mất: từ '(' đến ')'
    i += 1  # bỏ '('
    j = i
    while j < n and line[j] != ')':
        j += 1
    years_part = line[i:j].strip()   # ví dụ: '1931–2015'

    # Chuẩn hoá dấu gạch (có thể là '-' hoặc '–')
    years_norm = years_part.replace('–', '-')
    birth_year = "N/A"
    death_year = "N/A"
    if '-' in years_norm:
        parts = years_norm.split('-', 1)
        if parts[0].strip().isdigit():
            birth_year = parts[0].strip()
        if parts[1].strip().isdigit():
            death_year = parts[1].strip()

    # 3) Quốc tịch: sau dấu ')', bỏ khoảng trắng, đọc đến khoảng trắng đầu tiên
    j += 1  # bỏ ')'

    # bỏ các space sau ')'
    while j < n and line[j] == ' ':
        j += 1

    k = j
    while k < n and line[k] != ' ':
        k += 1

    nationality = line[j:k].strip() if j < n else "N/A"

    return name, birth_year, death_year, nationality

# print(parse_painter_line("Gwilym Prichard (1931–2015) Welsh painter"))

######################################################
# I. CẤU HÌNH SQLITE
######################################################

DB_FILE = "Painters_Data.db"
TABLE_NAME = "painters_info"

# # xóa DB cũ để test
# if os.path.exists(DB_FILE):
#     os.remove(DB_FILE)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# cursor.execute(f"""
# CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
#     name TEXT PRIMARY KEY,
#     birth TEXT,
#     death TEXT,
#     nationality TEXT,
#     link TEXT
# )
# """)
# conn.commit()


# ######################################################
# # II. SELENIUM – LẤY DỮ LIỆU TRONG LI
# ######################################################

# driver = webdriver.Chrome()
# all_data = []

# print("\n--- BẮT ĐẦU QUÉT A–Z ---")

# for i in range(65, 70):  # A–E để test; muốn full dùng range(65, 91)
#     letter = chr(i)
#     url = f'https://en.wikipedia.org/wiki/List_of_painters_by_name_beginning_with_%22{letter}%22'
#     print(f"\nĐang xử lý chữ: {letter}")

#     try:
#         driver.get(url)
#         time.sleep(2)

#         # lấy tất cả li
#         li_list = driver.find_elements(
#             By.XPATH,
#             "//div[@id='mw-content-text']//div[contains(@class,'div-col')]//li"
#         )
#         if len(li_list) == 0:
#             li_list = driver.find_elements(By.XPATH, "//div[@id='mw-content-text']//ul/li")

#         print(f"  -> Tìm thấy {len(li_list)} họa sĩ.")

#         for li in li_list:
#             try:
#                 full_text = li.text.strip()
#                 if not full_text:
#                     continue

#                 # Lấy href từ thẻ <a>
#                 a = li.find_element(By.TAG_NAME, "a")
#                 href = a.get_attribute("href")

#                 # Dùng logic while để tách name, birth, death, nationality
#                 name, birth, death, nationality = parse_painter_line(full_text)

#                 # Lưu vào list
#                 all_data.append({
#                     "Name": name,
#                     "Birth": birth,
#                     "Death": death,
#                     "Nationality": nationality,
#                     "Link": href
#                 })

#                 # Lưu vào DB
#                 cursor.execute(f"""
#                     INSERT OR IGNORE INTO {TABLE_NAME} (name, birth, death, nationality, link)
#                     VALUES (?, ?, ?, ?, ?)
#                 """, (name, birth, death, nationality, href))
#                 conn.commit()

#             except Exception as e:
#                 print("  -> lỗi 1 li:", e)

#     except Exception as e:
#         print("  -> lỗi toàn trang:", e)


# driver.quit()


# ######################################################
# # III. XUẤT EXCEL
# ######################################################

# if all_data:
#     df = pd.DataFrame(all_data)
#     df.to_excel("Painters_Final.xlsx", index=False)
#     print("\nĐã lưu thành công vào Painters_Final.xlsx")
# else:
#     print("Không thu thập được dữ liệu nào.")

# cursor.close()
# conn.close()
# print("Đã đóng SQLite.")



# A. Yêu Cầu Thống Kê và Toàn Cục
# 1. Đếm tổng số họa sĩ đã được lưu trữ trong bảng.

slq_dem_tong_so_hoa_si = """
SELECT COUNT(*) AS Tong_So_Hoa_Si
FROM painters_info;
"""
cursor.execute(slq_dem_tong_so_hoa_si)
tong_so_hoa_si = cursor.fetchone()[0]
print(f"Tổng số họa sĩ trong bảng: {tong_so_hoa_si}")



# 2. Hiển thị 5 dòng dữ liệu đầu tiên để kiểm tra cấu trúc và nội dung bảng.
'''
sql_hien_thi_5_dong_dau_tien = """
SELECT *
FROM painters_info ;
"""
cursor.execute(sql_hien_thi_5_dong_dau_tien)
dong_dau_tien = cursor.fetchmany(5)
for dong in dong_dau_tien:
    print(dong)

'''

# 3. Liệt kê danh sách các quốc tịch duy nhất có trong tập dữ liệu.
'''
sql_quoc_tich_duy_nhat = """
SELECT DISTINCT nationality
fROM painters_info;
"""
cursor.execute(sql_quoc_tich_duy_nhat)
quoc_tich = cursor.fetchall()
for qt in quoc_tich:
    print(qt)
'''


# B. Yêu Cầu Lọc và Tìm Kiếm
# 4. Tìm và hiển thị tên của các họa sĩ có tên bắt đầu bằng ký tự 'F'.
'''
sql_hoa_si_F = """
SELECT *
FROM painters_info
WHERE name LIKE 'F%'
ORDER BY name;
"""
cursor.execute(sql_hoa_si_F)
rows = cursor.fetchall()
for r in rows:
    print(r)
'''

# 5. Tìm và hiển thị tên và quốc tịch của những họa sĩ có quốc tịch chứa từ khóa 'French' (ví dụ: French, French-American).
'''
sql_quoc_tich_French = """
SELECT name, nationality
FROM painters_info
WHERE nationality LIKE '%French%'
ORDER BY name;
"""
cursor.execute(sql_quoc_tich_French)
rows = cursor.fetchall()
for r in rows:
    print(r)
'''

# 6. Hiển thị tên của các họa sĩ không có thông tin quốc tịch (hoặc để trống, hoặc NULL).
'''
sql_quoc_tich_NAN = """
SELECT *
FROM painters_info
WHERE nationality LIKE 'N/A' OR nationality IS NULL
ORDER BY name;
"""
cursor.execute(sql_quoc_tich_NAN)
rows = cursor.fetchall()
for r in rows:
    print(r)
'''

# 7. Tìm và hiển thị tên của những họa sĩ có cả thông tin ngày sinh và ngày mất (không rỗng).
'''
sql_ngay_sinh_mat_not_NAN = """
SELECT *
FROM painters_info
WHERE  birth != 'N/A' AND death != 'N/A'
ORDER BY name;
"""
cursor.execute(sql_ngay_sinh_mat_not_NAN)
rows = cursor.fetchall()
for r in rows:
    print(r)
'''

# 8. Hiển thị tất cả thông tin của họa sĩ có tên chứa từ khóa '%Fales%' (ví dụ: George Fales Baker).
'''
sql_hoa_si_Fales = """
SELECT *
FROM painters_info
WHERE name LIKE '%Fales%'
ORDER BY name;
"""
cursor.execute(sql_hoa_si_Fales)
rows = cursor.fetchall()
for r in rows:
    print(r)
'''
# C. Yêu Cầu Nhóm và Sắp Xếp
# 9. Sắp xếp và hiển thị tên của tất cả họa sĩ theo thứ tự bảng chữ cái (A-Z).
'''
sql_sap_xep_AZ = """
SELECT *
FROM painters_info
ORDER BY name ASC;
"""
cursor.execute(sql_sap_xep_AZ)
rows = cursor.fetchall()
for r in rows:
    print(r)
'''
# 10. Nhóm và đếm số lượng họa sĩ theo từng quốc tịch.
'''
sql_dem_theo_quoc_tich = """
SELECT nationality, COUNT(*) AS So_Luong_Hoa_Si
FROM painters_info
GROUP BY nationality
ORDER BY So_Luong_Hoa_Si DESC;
"""
cursor.execute(sql_dem_theo_quoc_tich)
rows = cursor.fetchall()        
for r in rows:
    print(r)
'''