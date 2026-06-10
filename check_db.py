import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("SELECT * FROM internal_marks")
rows = cur.fetchall()

print("---- INTERNAL MARKS ----")
for row in rows:
    print(row)

conn.close()