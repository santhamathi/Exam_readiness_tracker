import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS internal_marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dept TEXT,
    year INTEGER,
    semester INTEGER,
    subject TEXT,
    reg_no TEXT,
    assignment INTEGER,
    mock INTEGER,
    attendance INTEGER,
    unit_percent INTEGER,
    total INTEGER
)
""")

conn.commit()
conn.close()
print(" database & internal_mark table created")