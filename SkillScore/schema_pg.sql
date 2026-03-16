-- PostgreSQL Schema for SkillScore

DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS results;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS exams;
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS vacancies;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE exams (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    created_by INTEGER,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (created_by) REFERENCES users (id)
);

CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    exam_id INTEGER,
    question_text TEXT NOT NULL,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_option CHAR(1),
    explanation TEXT,
    difficulty TEXT,
    FOREIGN KEY (exam_id) REFERENCES exams (id)
);

CREATE TABLE results (
    id SERIAL PRIMARY KEY,
    student_id INTEGER,
    exam_id INTEGER,
    score INTEGER,
    total_questions INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users (id),
    FOREIGN KEY (exam_id) REFERENCES exams (id)
);

CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    filename TEXT NOT NULL,
    teacher_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users (id)
);

CREATE TABLE vacancies (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT,
    min_score INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    job_id INTEGER,
    student_id INTEGER,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    cgpa REAL,
    resume_filename TEXT,
    status TEXT DEFAULT 'pending',
    applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES vacancies (id),
    FOREIGN KEY (student_id) REFERENCES users (id)
);
