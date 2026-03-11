import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("🚀 Starting Database Setup...")

# 1. Add 'status' column if it doesn't exist
try:
    cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'approved'")
    print("- Added 'status' column successfully.")
except sqlite3.OperationalError:
    print("- 'status' column already exists.")

# 2. Create the Admin user if they don't exist
# This ensures you have a way to log in immediately
admin_user = 'admin'
admin_pass = generate_password_hash('admin123')

# Check if admin already exists
cursor.execute("SELECT * FROM users WHERE username = ?", (admin_user,))
if cursor.fetchone() is None:
    cursor.execute("INSERT INTO users (username, password, role, status) VALUES (?, ?, 'admin', 'approved')",
                   (admin_user, admin_pass))
    print(f"- Created NEW admin user: {admin_user}")
else:
    # If user exists, ensure they have admin rights and are approved
    cursor.execute("UPDATE users SET role = 'admin', status = 'approved' WHERE username = ?", (admin_user,))
    print(f"- Updated EXISTING user '{admin_user}' to Admin role.")

# 3. Set all existing teachers to 'pending'
# Students remain 'approved' by default
cursor.execute("UPDATE users SET status = 'pending' WHERE role = 'teacher'")
print("- All teacher accounts set to 'pending' (Awaiting Admin Approval).")

# Save and Close
conn.commit()
conn.close()

print("\n✅ Setup Complete!")
print(f"User: {admin_user}")
print("Pass: admin123")