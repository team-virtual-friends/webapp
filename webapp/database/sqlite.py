import sqlite3

conn = sqlite3.connect('waitlist.db')
c = conn.cursor()

c.execute('''CREATE TABLE waitlist
             (name TEXT, email TEXT UNIQUE, date_added TEXT)''')
conn.commit()
conn.close()
