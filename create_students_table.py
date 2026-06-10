import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reg_no TEXT UNIQUE,
    name TEXT,
    dept TEXT,
    year INTEGER,
    semester INTEGER,
)
""")

conn.commit()
conn.close()

print("students table created successfully")