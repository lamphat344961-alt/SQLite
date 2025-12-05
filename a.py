import sqlite3
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pandas as pd

# --- 1. KHỞI TẠO DATABASE (SQLITE) ---
# Tạo kết nối ngay từ đầu
conn = sqlite3.connect('longchau_db.sqlite')
cursor = conn.cursor()

# Tạo bảng products với đầy đủ cột theo đề bài
# product_url là PRIMARY KEY để chống trùng lặp
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        product_url TEXT PRIMARY KEY,
        product_name TEXT,
        price INTEGER,
        original_price INTEGER,
        unit TEXT,
        image_url TEXT,
        category TEXT,
        crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# --- 2. HÀM LÀM SẠCH GIÁ ---
def clean_price_to_int(price_text):
    if not price_text: return 0
    # Xóa dấu chấm, chữ đ, khoảng trắng
    clean = price_text.replace('.', '').replace('đ', '').replace(' ', '')
    try:
        return int(clean)
    except:
        return 0

# --- 3. CHƯƠNG TRÌNH CHÍNH ---
driver = webdriver.Firefox()

lt = [
    'https://nhathuoclongchau.com.vn/thuc-pham-chuc-nang',
    'https://nhathuoclongchau.com.vn/duoc-my-pham',
    'https://nhathuoclongchau.com.vn/cham-soc-ca-nhan',
    'https://nhathuoclongchau.com.vn/trang-thiet-bi-y-te'
]

try:
    for url in lt:
        print(f"--- Đang cào: {url} ---")
        driver.get(url)
        time.sleep(2)
        
        # --- LOGIC CUỘN TRANG & CLICK XEM THÊM (Của bạn) ---
        body = driver.find_element(By.TAG_NAME, "body") 
        
        # Click xem thêm vài lần
        for k in range(3): # Giảm range xuống 3-5 để test cho nhanh
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    if "Xem thêm" in button.text:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(2)
                        break 
            except Exception:
                pass
            
            # Cuộn trang
            for _ in range(20):
                body.send_keys(Keys.PAGE_DOWN) # Dùng PAGE_DOWN nhanh hơn ARROW_DOWN
                time.sleep(0.1)
        
        time.sleep(2) # Đợi load hết

        # --- LOGIC CÀO DỮ LIỆU ---
        # Tìm nút chọn mua -> Quay ra thẻ cha -> Lấy thông tin
        buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Chọn mua')]")
        print(f"Tìm thấy {len(buttons)} sản phẩm.")

        for bt in buttons:
            try:
                # 1. Tìm thẻ bao quanh (Parent Div)
                parent_div = bt
                for _ in range(3):
                    parent_div = parent_div.find_element(By.XPATH, "./..")
                
                # 2. Lấy Tên SP
                try:
                    tsp = parent_div.find_element(By.TAG_NAME, 'h3').text
                except:
                    tsp = ''
                
                # 3. Lấy Giá Bán (Và chuyển sang số)
                try:
                    gsp_text = parent_div.find_element(By.CLASS_NAME, 'text-blue-5').text
                    price = clean_price_to_int(gsp_text)
                except:
                    price = 0

                # 4. Lấy Giá Gốc (Original Price) - Thường là thẻ bị gạch ngang
                try:
                    goc_text = parent_div.find_element(By.CSS_SELECTOR, '.line-through').text
                    original_price = clean_price_to_int(goc_text)
                except:
                    original_price = 0 # Không có giảm giá
                
                # 5. Lấy Hình ảnh
                try:
                    ha = parent_div.find_element(By.TAG_NAME, 'img').get_attribute('src')
                except:
                    ha = ''

                # 6. Lấy Link sản phẩm (QUAN TRỌNG ĐỂ LÀM KHÓA CHÍNH)
                # Tìm thẻ <a> trong khối parent_div
                try:
                    link_tag = parent_div.find_element(By.TAG_NAME, 'a')
                    product_url = link_tag.get_attribute('href')
                except:
                    product_url = f"unknown_{time.time()}" # Tránh lỗi null

                # 7. LƯU VÀO SQLITE NGAY LẬP TỨC
                if tsp: # Chỉ lưu nếu có tên
                    sql = """
                        INSERT OR IGNORE INTO products 
                        (product_url, product_name, price, original_price, image_url, category)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    cursor.execute(sql, (product_url, tsp, price, original_price, ha, url))
                    conn.commit() # Lưu ngay, không sợ mất điện hay lỗi
                    print(f"-> Đã lưu: {tsp}")

            except Exception as e:
                # print(f"Lỗi item: {e}")
                continue

finally:
    # Đóng kết nối khi hoàn tất
    conn.close()
    driver.quit()
    print("Hoàn tất cào dữ liệu!")

# Kiểm tra kết quả
conn = sqlite3.connect('longchau_db.sqlite')
print("Tổng số dòng đã lưu:", pd.read_sql("SELECT count(*) FROM products", conn))