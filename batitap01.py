import sqlite3 as db

# 1. Kết nối đến cơ sở dữ liệu SQLite
conn = db.connect(r'C:\Users\Admin\Desktop\TANPHAT\Manguonmotrongkhoahocjdulieu\SQLite\inventory.db')

# Tạo một con trỏ để thực thi các lệnh SQL
cursor = conn.cursor()

# 2. Thao tác với cơ sở dữ liệu

# lệnh SQL để tạo bảng products

sql1 = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL ,
    price NUMERIC NOT NULL ,
    quantity INTERGER NOT NULL
)
"""
products_list = [('Laptop', 1200.50, 10),
                 ('Smartphone', 800.00, 25),
                 ('Tablet', 400.75, 15),
                 ('Headphones', 150.20, 50),
                 ('Smartwatch', 200.00, 30)]
sql2 = """
INSERT INTO products (name,price, quantity) 
VALUES (?,?,?)
"""

# # thực hiện tạo bảng 
# cursor.execute(sql1)
# cursor.executemany(sql2,products_list)

# conn.commit()

# đọc dữ liệu từ bảng products
sql3  = """
SELECT * FROM products
"""
cursor.execute(sql3)

data= cursor.fetchall()

for row in data:
    print(f'ID: {row[0]}, Name: {row[1]}, Price: {row[2]}, Quantity: {row[3]}')


# update dữ liệu trong bảng products
sql4 = """
UPDATE products
SET quantity = quantity + 10
WHERE name = 'Smartphone'
"""


sql5 = """
DELETE FROM products
WHERE price < 200.00
"""

# cursor.execute(sql4)
# cursor.execute(sql5)

conn.commit()

cursor.execute(sql3)

data= cursor.fetchall()

for row in data:
    print(f'ID: {row[0]}, Name: {row[1]}, Price: {row[2]}, Quantity: {row[3]}')