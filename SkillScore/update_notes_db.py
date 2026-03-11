import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()
# Create notes table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        filename TEXT NOT NULL,
        teacher_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES users (id)
    )
''')
conn.commit()
conn.close()
print("Notes table created successfully!")