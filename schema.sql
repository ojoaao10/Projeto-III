PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
 name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 role TEXT NOT NULL CHECK(role IN ('admin','coordinator','teacher','student')),
 password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
CREATE TABLE IF NOT EXISTS classes (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, level TEXT NOT NULL,
 shift TEXT NOT NULL CHECK(shift IN ('Matutino','Vespertino','Noturno')), active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
CREATE TABLE IF NOT EXISTS students (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
 cpf TEXT NOT NULL UNIQUE, registration TEXT NOT NULL UNIQUE, birth_date TEXT,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
CREATE TABLE IF NOT EXISTS subjects (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, code TEXT NOT NULL UNIQUE,
 hours INTEGER NOT NULL CHECK(hours>0), active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
CREATE TABLE IF NOT EXISTS offerings (
 id INTEGER PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id),
 class_id INTEGER NOT NULL REFERENCES classes(id), teacher_id INTEGER NOT NULL REFERENCES users(id),
 period TEXT NOT NULL, weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
 start_time TEXT NOT NULL, end_time TEXT NOT NULL CHECK(end_time>start_time), room TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)), UNIQUE(subject_id,class_id,period));
CREATE TABLE IF NOT EXISTS enrollments (
 id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id),
 offering_id INTEGER NOT NULL REFERENCES offerings(id), active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 UNIQUE(student_id,offering_id));
CREATE TABLE IF NOT EXISTS assessments (
 id INTEGER PRIMARY KEY, offering_id INTEGER NOT NULL REFERENCES offerings(id), title TEXT NOT NULL,
 type TEXT NOT NULL CHECK(type IN ('Prova Bimestral','Simulado','Trabalho','Atividade Avaliativa')),
 date TEXT NOT NULL, weight REAL NOT NULL CHECK(weight>0 AND weight<=100), UNIQUE(offering_id,title));
CREATE TABLE IF NOT EXISTS grades (
 id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL REFERENCES enrollments(id),
 assessment_id INTEGER NOT NULL REFERENCES assessments(id), value REAL NOT NULL CHECK(value BETWEEN 0 AND 10),
 UNIQUE(enrollment_id,assessment_id));
CREATE TABLE IF NOT EXISTS lessons (
 id INTEGER PRIMARY KEY, offering_id INTEGER NOT NULL REFERENCES offerings(id), date TEXT NOT NULL,
 start_time TEXT NOT NULL, topic TEXT NOT NULL, UNIQUE(offering_id,date,start_time));
CREATE TABLE IF NOT EXISTS attendance (
 id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL REFERENCES enrollments(id),
 lesson_id INTEGER NOT NULL REFERENCES lessons(id), status TEXT NOT NULL CHECK(status IN ('Presente','Ausente')),
 UNIQUE(enrollment_id,lesson_id));
CREATE TABLE IF NOT EXISTS materials (
 id INTEGER PRIMARY KEY, offering_id INTEGER NOT NULL REFERENCES offerings(id), title TEXT NOT NULL,
 url TEXT NOT NULL, description TEXT NOT NULL, trigger TEXT NOT NULL CHECK(trigger IN ('Todos','Nota baixa','Baixa frequência')));
CREATE TABLE IF NOT EXISTS interventions (
 id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL REFERENCES enrollments(id),
 owner_id INTEGER NOT NULL REFERENCES users(id), action TEXT NOT NULL, due_date TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('Aberta','Em andamento','Concluída')), result TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS settings (
 id INTEGER PRIMARY KEY CHECK(id=1), min_grade REAL NOT NULL CHECK(min_grade BETWEEN 0 AND 10),
 min_attendance REAL NOT NULL CHECK(min_attendance BETWEEN 0 AND 100));
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, actor_id INTEGER REFERENCES users(id), created_at TEXT NOT NULL,
 action TEXT NOT NULL, entity TEXT NOT NULL, record_id INTEGER, details TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_enrollments_offering ON enrollments(offering_id);
CREATE INDEX IF NOT EXISTS ix_grades_enrollment ON grades(enrollment_id);
CREATE INDEX IF NOT EXISTS ix_attendance_enrollment ON attendance(enrollment_id);
CREATE INDEX IF NOT EXISTS ix_audit_date ON audit(created_at);
INSERT OR IGNORE INTO settings VALUES(1,6,75);
