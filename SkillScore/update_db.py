import sqlite3

def update_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # This adds the missing 'status' column to your exams table
        cursor.execute("ALTER TABLE exams ADD COLUMN status TEXT DEFAULT 'active'")
        conn.commit()
        print("Success: 'status' column added to exams table.")
    except sqlite3.OperationalError:
        print("Note: 'status' column already exists.")
    finally:
        conn.close()

if __name__ == "__main__":
    update_database()