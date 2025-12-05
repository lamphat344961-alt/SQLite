import sqlite3
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

# --- PHẦN 1: KHỞI TẠO DATABASE (SQLITE) ---
def init_database():
    conn = sqlite3.connect('longchau_db.sqlite')
    cursor = conn.cursor()
    # Tạo bảng với product_url làm khóa chính để tránh trùng lặp
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_url TEXT PRIMARY KEY,
            product_name TEXT,
            price INTEGER,
            original_price INTEGER,
            unit TEXT,
            image_url TEXT,
            category_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

# --- PHẦN 2: HÀM XỬ LÝ DỮ LIỆU ---
def clean_price(price_text):
    """Chuyển đổi '150.000đ' thành số nguyên 150000"""
    if not price_text:
        return 0
    clean = price_text.replace('.', '').replace('đ', '').replace(' ', '')
    try:
        return int(clean)
    except:
        return 0

# --- PHẦN 3: HÀM CÀO DỮ LIỆU (CORE) ---
def crawl_category(driver, conn, category_url):
    print(f"--- Đang cào trang: {category_url} ---")
    driver.get(category_url)
    time.sleep(2)
    
    body = driver.find_element(By.TAG_NAME, "body")
    
    # --- Xử lý cuộn và click "Xem thêm" (Giữ nguyên logic của bạn nhưng tối ưu hơn) ---
    # Lặp click xem thêm vài lần để lấy đủ 50+ sản phẩm
    for k in range(3): 
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                if "Xem thêm" in button.text and "sản phẩm" in button.text:
                    driver.execute_script("arguments[0].click();", button) # Click bằng JS an toàn hơn
                    print("Đã click Xem thêm...")
                    time.sleep(3)
                    break
        except Exception:
            pass
        
        # Cuộn xuống
        for _ in range(10):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)
            
    time.sleep(2) # Đợi load xong hẳn

    # --- Bắt đầu lấy dữ liệu ---
    # Thay vì tìm nút "Chọn mua", ta tìm thẻ bao quanh sản phẩm (Product Card)
    # Mẹo: Tìm thẻ <a> chứa link sản phẩm, thường có class liên quan đến item
    # Ở Long Châu, thẻ div chứa sản phẩm thường có class phức tạp, nhưng ta có thể tìm tất cả thẻ <a>
    # mà bên trong có thẻ <h3> (tên sản phẩm) và thẻ <span> (giá).
    
    # Lấy danh sách các thẻ bao ngoài sản phẩm (Dựa trên cấu trúc HTML Long Châu)
    # Cách an toàn: Tìm tất cả thẻ <div> có chứa class css của ô sản phẩm\

    # Hoặc dùng logic cũ của bạn: Tìm nút chọn mua rồi tìm cha, nhưng bổ sung lấy link
    
    buy_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Chọn mua')]")
    print(f"Tìm thấy {len(buy_buttons)} sản phẩm khả dụng.")
    
    cursor = conn.cursor()
    count_saved = 0
    
    for bt in buy_buttons:
        try:
            # Tìm thẻ cha (Container)
            product_card = bt
            for _ in range(3):
                product_card = product_card.find_element(By.XPATH, "./..")
            
            # 1. Tên sản phẩm
            try:
                name = product_card.find_element(By.TAG_NAME, 'h3').text
            except:
                continue # Không có tên thì bỏ qua

            # 2. Link sản phẩm (QUAN TRỌNG CHO ĐỀ BÀI)
            try:
                # Tìm thẻ a có href trong product_card
                link_tag = product_card.find_element(By.TAG_NAME, 'a')
                url = link_tag.get_attribute('href')
            except:
                url = f"unknown_{name}_{time.time()}" # Fallback nếu lỗi

            # 3. Giá bán
            try:
                # Tìm thẻ có class chứa giá (bạn đang dùng text-blue-5, ok nhưng cần cẩn thận)
                price_tag = product_card.find_element(By.CLASS_NAME, 'text-blue-5')
                price_raw = price_tag.text
                price = clean_price(price_raw)
            except:
                price = 0
            
            # 4. Giá gốc (Original Price) - Thường là thẻ gạch ngang
            try:
                original_price_tag = product_card.find_element(By.CSS_SELECTOR, "span.line-through")
                original_price = clean_price(original_price_tag.text)
            except:
                original_price = 0 # Không có giảm giá

            # 5. Đơn vị tính (Unit)
            # Long Châu hay để dạng: "15.000đ / Hộp". Cần xử lý chuỗi.
            unit = "Hộp" # Mặc định
            try:
                # Tìm text chứa dấu "/"
                all_spans = product_card.find_elements(By.TAG_NAME, "span")
                for span in all_spans:
                    if "/" in span.text:
                        unit = span.text.split("/")[-1].strip() # Lấy phần sau dấu /
                        break
            except:
                pass

            # 6. Hình ảnh
            try:
                img = product_card.find_element(By.TAG_NAME, 'img').get_attribute('src')
            except:
                img = ""

            # --- LƯU TỨC THỜI (Real-time Storage) ---
            # Dùng INSERT OR IGNORE để nếu chạy lại không bị lỗi trùng URL
            sql = """
            INSERT OR IGNORE INTO products 
            (product_url, product_name, price, original_price, unit, image_url, category_url) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (url, name, price, original_price, unit, img, category_url))
            conn.commit() # Lưu ngay lập tức
            count_saved += 1
            
        except Exception as e:
            print(f"Lỗi item: {e}")
            continue
            
    print(f"-> Đã lưu thành công {count_saved} sản phẩm từ danh mục này.")

# --- PHẦN 4: CHẠY CHƯƠNG TRÌNH ---
# Danh sách URL cần cào
list_urls = [
    'https://nhathuoclongchau.com.vn/duoc-my-pham',
    'https://nhathuoclongchau.com.vn/cham-soc-ca-nhan',
    'https://nhathuoclongchau.com.vn/trang-thiet-bi-y-te'
]

# Setup
driver = webdriver.Firefox() # Hoặc Chrome()
db_conn = init_database()

try:
    # Duyệt qua từng URL trong danh sách
    for url in list_urls:
        crawl_category(driver, db_conn, url)
        time.sleep(3) # Nghỉ giữa các danh mục
finally:
    db_conn.close()
    driver.quit()
    print("Hoàn tất cào dữ liệu!")


"""
Đề Bài Thực Hành: Cào Dữ Liệu Long Châu và Quản Lý SQLite
I. Mục Tiêu
    Thực hiện cào dữ liệu sản phẩm từ trang web chính thức của chuỗi nhà thuốc Long Châu bằng công cụ Selenium, lưu trữ dữ liệu thu thập được một cách tức thời vào cơ sở dữ liệu SQLite, và kiểm tra chất lượng dữ liệu.

II. Yêu Cầu Kỹ Thuật (Scraping & Lưu trữ)
    Công cụ: Sử dụng thư viện Selenium kết hợp với Python và Pandas (cho việc quản lý DataFrame tạm thời và lưu vào DB).

    Phạm vi Cào: Chọn một danh mục sản phẩm cụ thể trên trang Long Châu (ví dụ: "Thực phẩm chức năng", "Chăm sóc da", hoặc "Thuốc") và cào ít nhất 50 sản phẩm (có thể cào nhiều trang/URL khác nhau).

    Dữ liệu cần cào: Đối với mỗi sản phẩm, cần thu thập ít nhất các thông tin sau (table phải có các cột bên dưới):

        Mã sản phẩm (id): cố gắng phân tích và lấy mã sản phẩm gốc từ trang web, nếu không được thì dùng mã tự tăng.

        Tên sản phẩm (product_name)

        Giá bán (price)

        Giá gốc/Giá niêm yết (nếu có, original_price)

        Đơn vị tính (ví dụ: Hộp, Chai, Vỉ, unit)

        Link URL sản phẩm (product_url) (Dùng làm định danh duy nhất)

    Lưu trữ Tức thời:

        Sử dụng thư viện sqlite3 để tạo cơ sở dữ liệu (longchau_db.sqlite).

        Thực hiện lưu trữ dữ liệu ngay lập tức sau khi cào xong thông tin của mỗi sản phẩm (sử dụng conn.cursor().execute() hoặc DataFrame.to_sql(if_exists='append')) thay vì lưu trữ toàn bộ sau khi kết thúc quá trình cào.

        Sử dụng product_url hoặc một trường định danh khác làm PRIMARY KEY (hoặc kết hợp với lệnh INSERT OR IGNORE) để tránh ghi đè nếu chạy lại code.

III. Yêu Cầu Phân Tích Dữ Liệu (Query/Truy Vấn)
    Sau khi dữ liệu được thu thập, tạo và thực thi ít nhất 15 câu lệnh SQL (queries) để khảo sát chất lượng và nội dung dữ liệu.

    Nhóm 1: Kiểm Tra Chất Lượng Dữ Liệu (Bắt buộc)
        Kiểm tra trùng lặp (Duplicate Check): Kiểm tra và hiển thị tất cả các bản ghi có sự trùng lặp dựa trên trường product_url hoặc product_name.

        Kiểm tra dữ liệu thiếu (Missing Data): Đếm số lượng sản phẩm không có thông tin Giá bán (price là NULL hoặc 0).

        Kiểm tra giá: Tìm và hiển thị các sản phẩm có Giá bán lớn hơn Giá gốc/Giá niêm yết (logic bất thường).

        Kiểm tra định dạng: Liệt kê các unit (đơn vị tính) duy nhất để kiểm tra sự nhất quán trong dữ liệu.

        Tổng số lượng bản ghi: Đếm tổng số sản phẩm đã được cào.

    Nhóm 2: Khảo sát và Phân Tích (Bổ sung)
        Sản phẩm có giảm giá: Hiển thị 10 sản phẩm có mức giá giảm (chênh lệch giữa original_price và price) lớn nhất.

        Sản phẩm đắt nhất: Tìm và hiển thị sản phẩm có giá bán cao nhất.

        Thống kê theo đơn vị: Đếm số lượng sản phẩm theo từng Đơn vị tính (unit).

        Sản phẩm cụ thể: Tìm kiếm và hiển thị tất cả thông tin của các sản phẩm có tên chứa từ khóa "Vitamin C".

        Lọc theo giá: Liệt kê các sản phẩm có giá bán nằm trong khoảng từ 100.000 VNĐ đến 200.000 VNĐ.

    Nhóm 3: Các Truy vấn Nâng cao (Tùy chọn)
        Sắp xếp: Sắp xếp tất cả sản phẩm theo Giá bán từ thấp đến cao.

        Phần trăm giảm giá: Tính phần trăm giảm giá cho mỗi sản phẩm và hiển thị 5 sản phẩm có phần trăm giảm giá cao nhất (Yêu cầu tính toán trong query hoặc sau khi lấy data).

        Xóa bản ghi trùng lặp: Viết câu lệnh SQL để xóa các bản ghi bị trùng lặp, chỉ giữ lại một bản ghi (sử dụng Subquery hoặc Common Table Expression - CTE).

        Phân tích nhóm giá: Đếm số lượng sản phẩm trong từng nhóm giá (ví dụ: dưới 50k, 50k-100k, trên 100k).

        URL không hợp lệ: Liệt kê các bản ghi mà trường product_url bị NULL hoặc rỗng.
"""