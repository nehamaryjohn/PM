import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
psycopg2_error = None
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception as e:
    psycopg2 = None
    RealDictCursor = None
    psycopg2_error = str(e)
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'skillscore_secret' # Used for session security

# --- CONFIGURATION FOR FILE UPLOADS ---
UPLOAD_FOLDER = 'static/uploads/notes'
RESUME_FOLDER = 'static/uploads/resumes'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'txt', 'png', 'jpg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESUME_FOLDER'] = RESUME_FOLDER

# Ensure the upload directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESUME_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- DATABASE HELPER ---
class DBWrapper:
    def __init__(self, conn, db_type):
        self.conn = conn
        self.db_type = db_type

    def execute(self, query, params=()):
        if self.db_type == 'postgres':
            # Convert SQLite ? placeholders to PostgreSQL %s
            query = query.replace('?', '%s')
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            return cur
        else:
            return self.conn.execute(query, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def fetchone(self, query, params=()):
        cur = self.execute(query, params)
        return cur.fetchone()

    def fetchall(self, query, params=()):
        cur = self.execute(query, params)
        return cur.fetchall()

    def insert_get_id(self, query, params=()):
        if self.db_type == 'postgres':
            query = query.replace('?', '%s')
            if 'RETURNING' not in query.upper():
                query += ' RETURNING id'
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            row = cur.fetchone()
            return row['id']
        else:
            cur = self.conn.execute(query, params)
            return cur.lastrowid

def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if not psycopg2:
            print(f"PostgreSQL support enabled but psycopg2 could not be loaded: {psycopg2_error}")
            raise ImportError(f"psycopg2 is required for PostgreSQL support. Import error: {psycopg2_error}")
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        return DBWrapper(conn, 'postgres')
    else:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return DBWrapper(conn, 'sqlite')

# --- INITIALIZE DATABASE TABLES ---
def init_db():
    db = get_db_connection()
    
    # Users table (Assuming it exists based on your logic)
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        status TEXT DEFAULT 'approved'
    )''')

    # Vacancies table
    db.execute('''CREATE TABLE IF NOT EXISTS vacancies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT NOT NULL,
        description TEXT,
        min_score INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Applications table
    db.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        student_id INTEGER,
        full_name TEXT,
        email TEXT,
        phone TEXT,
        cgpa REAL,
        resume_filename TEXT,
        status TEXT DEFAULT 'Pending Review',
        applied_on DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES vacancies (id),
        FOREIGN KEY (student_id) REFERENCES users (id)
    )''')

    # Exams table
    db.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        created_by INTEGER,
        status TEXT DEFAULT 'active',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Questions table
    db.execute('''CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER,
        question_text TEXT,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_option TEXT,
        explanation TEXT,
        FOREIGN KEY (exam_id) REFERENCES exams (id)
    )''')

    # Results table
    db.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        exam_id INTEGER,
        score INTEGER,
        total_questions INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Notes table
    db.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        filename TEXT,
        teacher_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    db.commit()
    db.close()

init_db()

# --- CORE ROUTES ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role'] 
        status = 'pending' if role == 'teacher' else 'approved'
        
        db = get_db_connection()
        try:
            db.execute('INSERT INTO users (username, password, role, status) VALUES (?, ?, ?, ?)',
                       (username, password, role, status))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists!"
        finally:
            db.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db_connection()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()

        if user and check_password_hash(user['password'], password):
            if user['role'] == 'teacher' and user['status'] == 'pending':
                return "Your account is awaiting admin approval. Please contact the administrator."
            
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        
        return "Invalid Credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ADMIN ROUTES ---

@app.route('/admin/manage')
def admin_manage():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_db_connection()
    teachers = db.execute('SELECT * FROM users WHERE role = "teacher"').fetchall()
    students = db.execute('SELECT * FROM users WHERE role = "student"').fetchall()
    vacancies = db.execute('SELECT * FROM vacancies').fetchall()
    
    applications = db.execute('''
        SELECT a.*, v.title as job_title, v.company 
        FROM applications a 
        JOIN vacancies v ON a.job_id = v.id 
        ORDER BY a.applied_on DESC
    ''').fetchall()
    
    db.close()
    return render_template('admin_manage.html', teachers=teachers, students=students, vacancies=vacancies, applications=applications)

@app.route('/admin/approve/<int:user_id>')
def approve_teacher(user_id):
    if session.get('role') != 'admin': 
        return "Unauthorized"
    db = get_db_connection()
    db.execute('UPDATE users SET status = "approved" WHERE id = ?', (user_id,))
    db.commit()
    db.close()
    return redirect(url_for('admin_manage'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('role') != 'admin': 
        return "Unauthorized"
    db = get_db_connection()
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    db.close()
    return redirect(url_for('admin_manage'))

# --- ADMIN APPLICATION MANAGEMENT ---

@app.route('/admin/update_application/<int:app_id>', methods=['POST'])
def update_application(app_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    new_status = request.form.get('status')
    db = get_db_connection()
    db.execute('UPDATE applications SET status = ? WHERE id = ?', (new_status, app_id))
    db.commit()
    db.close()
    flash("Application status updated!")
    return redirect(url_for('admin_manage'))

@app.route('/admin/delete_application/<int:app_id>', methods=['POST'])
def delete_application(app_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_db_connection()
    db.execute('DELETE FROM applications WHERE id = ?', (app_id,))
    db.commit()
    db.close()
    flash("Application deleted successfully.")
    return redirect(url_for('admin_manage'))

# --- DASHBOARD LOGIC ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    
    if session['role'] == 'admin':
        return redirect(url_for('admin_manage'))

    if session['role'] == 'teacher':
        stats = db.execute('''
            SELECT e.id, e.title, e.category, AVG(r.score) as avg_score, COUNT(r.id) as attempts
            FROM exams e
            LEFT JOIN results r ON e.id = r.exam_id
            WHERE e.created_by = ? AND e.status = 'active'
            GROUP BY e.id
        ''', (session['user_id'],)).fetchall()

        history = db.execute('''
            SELECT e.id, e.title, e.category, AVG(r.score) as avg_score, COUNT(r.id) as attempts
            FROM exams e
            LEFT JOIN results r ON e.id = r.exam_id
            WHERE e.created_by = ? AND e.status = 'deleted'
            GROUP BY e.id
        ''', (session['user_id'],)).fetchall()

        category_stats = db.execute('''
            SELECT e.category, AVG(r.score * 100.0 / r.total_questions) as avg_percent
            FROM exams e
            JOIN results r ON e.id = r.exam_id
            WHERE e.created_by = ?
            GROUP BY e.category
        ''', (session['user_id'],)).fetchall()
        
        db.close()
        return render_template('dashboard.html', stats=stats, history=history, category_stats=category_stats)
    
    else:
        exams = db.execute('SELECT * FROM exams WHERE status = "active"').fetchall()
        attended_raw = db.execute('SELECT exam_id FROM results WHERE student_id = ?', 
                                  (session['user_id'],)).fetchall()
        attended_ids = [row['exam_id'] for row in attended_raw]
        
        user_results = db.execute('''
            SELECT AVG(score * 100.0 / total_questions) as avg_percent 
            FROM results WHERE student_id = ?
        ''', (session['user_id'],)).fetchone()

        readiness_status = "In Progress"
        avg_p = user_results['avg_percent']
        
        if avg_p is not None:
            if avg_p >= 75: readiness_status = "High Readiness (Placement Ready)"
            elif avg_p >= 50: readiness_status = "Moderate Readiness"
            else: readiness_status = "Need Improvement"
        
        db.close()
        return render_template('dashboard.html', exams=exams, attended_ids=attended_ids, 
                               readiness=readiness_status, avg_p=avg_p)

# --- EXAM MANAGEMENT ROUTES ---

@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if session.get('role') != 'teacher':
        return "Access Denied"

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        teacher_id = session['user_id']

        q_texts = request.form.getlist('q_text[]')
        opts_a = request.form.getlist('a[]')
        opts_b = request.form.getlist('b[]')
        opts_c = request.form.getlist('c[]')
        opts_d = request.form.getlist('d[]')
        correct_opts = request.form.getlist('correct[]')
        explanations = request.form.getlist('exp[]')

        db = get_db_connection()
        exam_id = db.insert_get_id('INSERT INTO exams (title, category, created_by, status) VALUES (?, ?, ?, "active")',
                                    (title, category, teacher_id))
        
        for i in range(len(q_texts)):
            db.execute('''INSERT INTO questions 
                          (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (exam_id, q_texts[i], opts_a[i], opts_b[i], opts_c[i], opts_d[i], correct_opts[i], explanations[i]))
        
        db.commit()
        db.close()
        flash(f"Exam '{title}' published with {len(q_texts)} questions!")
        return redirect(url_for('dashboard'))

    return render_template('create_exam.html')

@app.route('/take_exam/<int:exam_id>')
def take_exam(exam_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    exam = db.execute('SELECT * FROM exams WHERE id = ? AND status = "active"', (exam_id,)).fetchone()
    if not exam:
        return "Exam no longer available"
    questions = db.execute('SELECT * FROM questions WHERE exam_id = ?', (exam_id,)).fetchall()
    db.close()
    
    return render_template('exam.html', exam=exam, questions=questions)

@app.route('/submit_exam/<int:exam_id>', methods=['POST'])
def submit_exam(exam_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db_connection()
    questions = db.execute('SELECT * FROM questions WHERE exam_id = ?', (exam_id,)).fetchall()
    
    score = 0
    total = len(questions)
    review_data = []

    for q in questions:
        user_answer = request.form.get(f"question_{q['id']}")
        is_correct = (user_answer == q['correct_option'])
        if is_correct: score += 1

        review_data.append({
            'question_text': q['question_text'],
            'user_ans': user_answer if user_answer else "Not Answered",
            'correct_ans': q['correct_option'],
            'is_correct': is_correct,
            'explanation': q['explanation']
        })

    db.execute('INSERT INTO results (student_id, exam_id, score, total_questions) VALUES (?, ?, ?, ?)',
               (session['user_id'], exam_id, score, total))
    db.commit()
    db.close()

    return render_template('result_summary.html', score=score, total=total, review_data=review_data)

@app.route('/exam_report/<int:exam_id>')
def exam_report(exam_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    db = get_db_connection()
    exam = db.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    reports = db.execute('''
        SELECT u.username, r.score, r.total_questions, r.timestamp 
        FROM results r 
        JOIN users u ON r.student_id = u.id 
        WHERE r.exam_id = ?
        ORDER BY r.timestamp DESC
    ''', (exam_id,)).fetchall()
    db.close()
    
    return render_template('exam_report.html', reports=reports, exam=exam)

@app.route('/delete_exam/<int:exam_id>', methods=['POST'])
def delete_exam(exam_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    db = get_db_connection()
    db.execute('UPDATE exams SET status = "deleted" WHERE id = ? AND created_by = ?', 
                (exam_id, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('dashboard'))

# --- NOTES & STUDY MATERIAL ROUTES (UPDATED) ---

@app.route('/upload_note', methods=['GET', 'POST'])
def upload_note():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    db = get_db_connection()

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        file = request.files['file']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp or user_id to filename to prevent overwriting
            unique_filename = f"teacher_{session['user_id']}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            
            db.execute('INSERT INTO notes (title, category, filename, teacher_id) VALUES (?, ?, ?, ?)',
                       (title, category, unique_filename, session['user_id']))
            db.commit()
            flash("Note uploaded successfully!", "success")
            return redirect(url_for('upload_note'))
            
    # Fetch existing notes for this specific teacher to display on page
    notes = db.execute('SELECT * FROM notes WHERE teacher_id = ? ORDER BY timestamp DESC', 
                       (session['user_id'],)).fetchall()
    db.close()
    return render_template('upload_note.html', notes=notes)

@app.route('/delete_note/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    db = get_db_connection()
    note = db.execute('SELECT * FROM notes WHERE id = ? AND teacher_id = ?', 
                      (note_id, session['user_id'])).fetchone()
    
    if note:
        # Delete the actual file from storage
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], note['filename']))
        except OSError:
            pass # File might already be missing
            
        db.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        db.commit()
        flash("Note deleted successfully.", "info")
    
    db.close()
    return redirect(url_for('upload_note'))

@app.route('/my_studies')
def my_studies():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    notes = db.execute('''
        SELECT n.*, u.username as teacher_name 
        FROM notes n 
        JOIN users u ON n.teacher_id = u.id 
        ORDER BY n.timestamp DESC
    ''').fetchall()
    db.close()
    return render_template('my_studies.html', notes=notes)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- JOB VACANCY ROUTES (ADMIN) ---

@app.route('/admin/add_vacancy', methods=['GET', 'POST'])
def add_vacancy():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        description = request.form['description']
        min_score = request.form['min_score']

        db = get_db_connection()
        db.execute('''INSERT INTO vacancies (title, company, location, description, min_score) 
                      VALUES (?, ?, ?, ?, ?)''', (title, company, location, description, min_score))
        db.commit()
        db.close()
        return redirect(url_for('admin_manage'))
        
    return render_template('add_vacancy.html')

# --- JOB BOARD ROUTES (STUDENTS) ---

@app.route('/student/jobs')
def student_jobs():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    
    user_results = db.execute('''
        SELECT AVG(score * 100.0 / total_questions) as avg_percent 
        FROM results WHERE student_id = ?
    ''', (session['user_id'],)).fetchone()
    student_score = user_results['avg_percent'] if user_results['avg_percent'] is not None else 0
    
    vacancies = db.execute('SELECT * FROM vacancies ORDER BY timestamp DESC').fetchall()

    my_apps = db.execute('''
        SELECT a.*, v.title as job_title, v.company 
        FROM applications a 
        JOIN vacancies v ON a.job_id = v.id 
        WHERE a.student_id = ?
    ''', (session['user_id'],)).fetchall()

    db.close()
    return render_template('jobs.html', student_score=student_score, vacancies=vacancies, my_applications=my_apps)

# --- APPLY JOB ROUTE ---

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply_job(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    job = db.execute('SELECT * FROM vacancies WHERE id = ?', (job_id,)).fetchone()
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        cgpa = request.form['cgpa']
        file = request.files['resume']
        
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config['RESUME_FOLDER'], filename))
        
        db.execute('''INSERT INTO applications (job_id, student_id, full_name, email, phone, cgpa, resume_filename)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                   (job_id, session['user_id'], full_name, email, phone, cgpa, filename))
        db.commit()
        db.close()
        return redirect(url_for('student_jobs'))
        
    db.close()
    return render_template('apply_form.html', job=job)

@app.route('/admin/applications')
def view_applications():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    apps = db.execute('''
        SELECT a.*, v.title as job_title, v.company 
        FROM applications a 
        JOIN vacancies v ON a.job_id = v.id 
        ORDER BY a.applied_on DESC
    ''').fetchall()
    db.close()
    return render_template('admin_applications.html', applications=apps)

if __name__ == '__main__':
    app.run(debug=True)