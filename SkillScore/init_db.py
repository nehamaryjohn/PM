import os
import sqlite3
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash

def get_connection():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if not psycopg2:
            raise ImportError("psycopg2 is required for PostgreSQL support. Install it with 'pip install psycopg2-binary'")
        result = urlparse(database_url)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        return psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        ), 'postgres'
    else:
        return sqlite3.connect('database.db'), 'sqlite'

connection, db_type = get_connection()
cursor = connection.cursor()

# 1. Run the appropriate schema
schema_file = 'schema_pg.sql' if db_type == 'postgres' else 'schema.sql'
with open(schema_file) as f:
    schema_sql = f.read()
    if db_type == 'postgres':
        cursor.execute(schema_sql)
    else:
        cursor.executescript(schema_sql)

# 2. Create a Default Admin (So you don't get "Invalid Credentials")
admin_pass = generate_password_hash('admin123')
try:
    if db_type == 'postgres':
        cursor.execute('''INSERT INTO users (username, password, role, status) 
                          VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO NOTHING''', 
                       ('admin', admin_pass, 'admin', 'approved'))
    else:
        cursor.execute('''INSERT INTO users (username, password, role, status) 
                          VALUES (?, ?, ?, ?)''', 
                       ('admin', admin_pass, 'admin', 'approved'))
except (sqlite3.IntegrityError, psycopg2.IntegrityError):
    pass # Admin already exists, no need to add again

connection.commit()
cursor.close()
connection.close()

print(f"Database ({db_type}) initialized successfully! Log in with admin / admin123")