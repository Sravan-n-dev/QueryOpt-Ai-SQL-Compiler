-- QueryOpt AI — College Database Schema

CREATE TABLE IF NOT EXISTS Department (
    dept_id   INTEGER PRIMARY KEY,
    dept_name TEXT    NOT NULL,
    hod       TEXT
);

CREATE TABLE IF NOT EXISTS Student (
    student_id INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    age        INTEGER,
    branch     TEXT,
    cgpa       REAL,
    dept_id    INTEGER,
    FOREIGN KEY (dept_id) REFERENCES Department (dept_id)
);

CREATE TABLE IF NOT EXISTS Course (
    course_id   INTEGER PRIMARY KEY,
    course_name TEXT    NOT NULL,
    dept_id     INTEGER,
    credits     INTEGER,
    FOREIGN KEY (dept_id) REFERENCES Department (dept_id)
);

CREATE TABLE IF NOT EXISTS Enrollment (
    enrollment_id INTEGER PRIMARY KEY,
    student_id    INTEGER,
    course_id     INTEGER,
    marks         REAL,
    FOREIGN KEY (student_id) REFERENCES Student (student_id),
    FOREIGN KEY (course_id)  REFERENCES Course (course_id)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_student_age           ON Student (age);
CREATE INDEX IF NOT EXISTS idx_student_branch        ON Student (branch);
CREATE INDEX IF NOT EXISTS idx_student_dept_id       ON Student (dept_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_student_id ON Enrollment (student_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_course_id  ON Enrollment (course_id);
CREATE INDEX IF NOT EXISTS idx_course_dept_id        ON Course (dept_id);
