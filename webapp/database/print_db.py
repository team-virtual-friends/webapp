import sqlite3

# Connect to the database
conn = sqlite3.connect('waitlist.db')
c = conn.cursor()

# Fetch all rows from waitlist table
rows = c.execute("SELECT * FROM waitlist").fetchall()

for row in rows:
    print(row)

conn.close()