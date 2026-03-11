import sqlite3
from werkzeug.security import generate_password_hash

connection = sqlite3.connect('database.db')

# 1. Run your existing schema.sql (Users, Exams, etc.)
with open('schema.sql') as f:
    connection.executescript(f.read())

# 2. Ensure Vacancies table exists
connection.execute('''CREATE TABLE IF NOT EXISTS vacancies 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              title TEXT, company TEXT, location TEXT, 
              description TEXT, min_score INTEGER)''')

# 3. Create a Default Admin (So you don't get "Invalid Credentials")
# This ensures you always have a way into the system
admin_pass = generate_password_hash('admin123')
try:
    connection.execute('''INSERT INTO users (username, password, role, status) 
                          VALUES (?, ?, ?, ?)''', 
                       ('admin', admin_pass, 'admin', 'approved'))
except sqlite3.IntegrityError:
    pass # Admin already exists, no need to add again

connection.commit()
connection.close()
print("Database initialized successfully! Log in with admin / admin123")