DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS exams;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS results;
DROP TABLE IF EXISTS notes; -- Added this so your notes logic doesn't crash
DROP TABLE IF EXISTS vacancies;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL, -- Added missing comma here
    status TEXT NOT NULL 
);

CREATE TABLE exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    created_by INTEGER,
    status TEXT DEFAULT 'active', -- Added this column for your dashboard logic
    FOREIGN KEY (created_by) REFERENCES users (id)
);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER,
    question_text TEXT NOT NULL,
    option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
    correct_option CHAR(1),
    explanation TEXT,
    difficulty TEXT,
    FOREIGN KEY (exam_id) REFERENCES exams (id)
);

CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    exam_id INTEGER,
    score INTEGER,
    total_questions INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users (id),
    FOREIGN KEY (exam_id) REFERENCES exams (id)
);

-- Added Notes table for your upload_note route
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    filename TEXT NOT NULL,
    teacher_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users (id)
);

-- Added Vacancies table
CREATE TABLE vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT,
    min_score INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    student_id INTEGER,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    cgpa REAL,
    resume_filename TEXT,
    status TEXT DEFAULT 'pending',
    applied_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES vacancies (id),
    FOREIGN KEY (student_id) REFERENCES users (id)
);