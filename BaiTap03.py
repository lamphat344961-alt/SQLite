import time
import random
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse


# ================== HÀM DELAY TỰ NHIÊN (CHỐNG BLOCK) ==================
def human_delay(a=1.0, b=3.0):
    """Sleep ngẫu nhiên để tránh bị detect bot"""
    time.sleep(random.uniform(a, b))


# ================== HÀM XỬ LÝ GIÁ ==================
def clean_price(price_str: str) -> int:
    if not price_str:
        return 0
    s = price_str.replace("đ", "").replace("Đ", "")
    s = s.replace(".", "").replace(",", "").strip()
    try:
        return int(s)
    except:
        return 0


# ================== DB ==================
def init_db(db_name="longchau_db.sqlite"):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            product_url   TEXT PRIMARY KEY,
            category_url  TEXT,
            brand         TEXT,
            product_name  TEXT,
            price         INTEGER,
            unit          TEXT,
            strike_price  INTEGER,
            discount_text TEXT,
            origin_country TEXT,
            expiry        TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


# ================== HỖ TRỢ LẤY HÀNG TRONG BẢNG THÔNG TIN ==================
def get_info_row(container, label_text):
    try:
        row = container.find_element(
            By.XPATH,
            ".//table[contains(@class,'content-list')]"
            f"//tr[.//p[contains(normalize-space(), '{label_text}')]]"
        )
        try:
            val_el = row.find_element(
                By.XPATH, ".//td[last()]//div | .//td[last()]//p | .//td[last()]"
            )
        except:
            val_el = row.find_element(By.XPATH, ".//td[last()]")

        return val_el.text.strip()
    except:
        return ""


# ================== CRAWL TRANG CHI TIẾT ==================
def crawl_product_detail(driver, conn, product_url, category_url):
    cur = conn.cursor()

    print(f"  → Đang mở trang sản phẩm: {product_url}")
    driver.get(product_url)
    human_delay(1.5, 3.2)

    # Block thông tin chính
    try:
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-lcpr='prr-id-product-detail-product-information']")
            )
        )
    except:
        print("    ⚠ Không tìm thấy block sản phẩm.")
        return

    # ---- Thương hiệu ----
    try:
        brand_el = container.find_element(
            By.XPATH,
            ".//span[contains(normalize-space(),'Thương hiệu')]/following-sibling::span//a"
        )
        brand = brand_el.text.strip()
    except:
        brand = ""

    # ---- Tên sản phẩm ----
    try:
        name_el = container.find_element(By.XPATH, ".//h1[@data-test='product_name']")
        product_name = name_el.text.strip()
    except:
        product_name = ""

    # ---- Giá & đơn vị ----
    try:
        price_el = container.find_element(By.XPATH, ".//span[@data-test='price']")
        price_text = price_el.text.strip()
        price = clean_price(price_text)
    except:
        price_text = ""
        price = 0

    try:
        unit_el = container.find_element(By.XPATH, ".//span[@data-test='unit']")
        unit = unit_el.text.strip()
    except:
        unit = ""

    # ---- Giá gạch ----
    try:
        strike_el = container.find_element(
            By.XPATH, ".//div[@data-test='strike_price']"
        )
        strike_price_text = strike_el.text.strip()
        strike_price = clean_price(strike_price_text)
    except:
        strike_price_text = ""
        strike_price = 0
    if strike_price == 0:
        strike_price  = price

    # ---- Text giảm giá ----
    discount_text = ""
    try:
        promo_ps = container.find_elements(
            By.XPATH, ".//div[contains(@class,'promotion-list')]//p"
        )
        texts = [p.text.strip() for p in promo_ps if p.text.strip()]
        discount_text = " | ".join(texts)
    except:
        discount_text = ""

    # ---- Nước sản xuất ----
    origin_country = get_info_row(container, "Nước sản xuất")

    # ---- Hạn sử dụng ----
    expiry = get_info_row(container, "Hạn sử dụng")

    # ---- Lưu DB ----
    sql = """
        INSERT OR IGNORE INTO products (
            product_url, category_url, brand, product_name,
            price, unit, strike_price, discount_text,
            origin_country, expiry
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    cur.execute(
        sql,
        (
            product_url,
            category_url,
            brand,
            product_name,
            price,
            unit,
            strike_price,
            discount_text,
            origin_country,
            expiry,
        ),
    )
    conn.commit()

    print(f"    ✅ Lưu: {product_name} | {price_text} | {unit} | {origin_country} | {expiry}")
    human_delay(1.0, 2.5)


# ================== CRAWL LINK SẢN PHẨM TRONG DANH MỤC ==================
def crawl_category_get_links(driver, category_url, max_click_more=2):
    print(f"\n=== Đang mở danh mục: {category_url} ===")
    driver.get(category_url)
    human_delay(2, 4)

    # Load thêm sản phẩm
    for i in range(max_click_more):
        print(f"  → Scroll + click 'Xem thêm' #{i+1}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        human_delay(2, 4)

        buttons = driver.find_elements(
            By.XPATH,
            "//button[contains(., 'Xem thêm') and contains(., 'sản phẩm')]"
        )
        if not buttons:
            print("    Không còn 'Xem thêm'")
            break

        try:
            driver.execute_script("arguments[0].click();", buttons[0])
            human_delay(2, 4)
        except:
            break

    # Lấy link
    product_urls = set()

    # Tìm tất cả <a> dẫn tới .html
    all_links = driver.find_elements(By.XPATH, "//a[contains(@href,'.html')]")

    for a in all_links:
        try:
            href = a.get_attribute("href") or ""
            href = href.split("#")[0].split("?")[0]

            if "nhathuoclongchau.com.vn" in href and href.endswith(".html"):
                product_urls.add(href)
        except:
            continue

    print(f"  → Tổng link lấy được: {len(product_urls)}")
    return list(product_urls)


# ================== MAIN ==================
if __name__ == "__main__":
    conn = init_db()

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)

    category_urls = [
        "https://nhathuoclongchau.com.vn/thuc-pham-chuc-nang",
        "https://nhathuoclongchau.com.vn/duoc-my-pham"
    ]

    all_links = []

    # Pha 1: lấy link
    for cat in category_urls:
        links = crawl_category_get_links(driver, cat, max_click_more=2)
        for link in links:
            all_links.append((link, cat))

    # Loại trùng
    unique_links = {}
    for link, cat in all_links:
        if link not in unique_links:
            unique_links[link] = cat

    print(f"\n=== Tổng số link sản phẩm duy nhất: {len(unique_links)} ===")

    # Pha 2: crawl chi tiết từng sản phẩm
    for i, (product_url, cat_url) in enumerate(unique_links.items(), start=1):
        print(f"\n[{i}/{len(unique_links)}]")
        try:
            crawl_product_detail(driver, conn, product_url, cat_url)
        except Exception as e:
            print(f"⚠ Lỗi sản phẩm {product_url}: {e}")

    driver.quit()
    conn.close()

    print("\n✅ Hoàn thành crawl.")
