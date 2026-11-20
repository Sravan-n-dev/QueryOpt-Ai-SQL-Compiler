"""Deterministic seed-data generator for the College Database."""

import random
import sqlite3
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Raw data pools
# ---------------------------------------------------------------------------

DEPARTMENTS: List[Tuple[int, str, str]] = [
    (1, "Computer Science", "Dr. Sharma"),
    (2, "Electronics", "Dr. Verma"),
    (3, "Mechanical", "Dr. Patel"),
    (4, "Civil", "Dr. Reddy"),
    (5, "Mathematics", "Dr. Iyer"),
]

COURSES: List[Tuple[int, str, int, int]] = [
    # Computer Science
    (101, "Data Structures", 1, 4),
    (102, "Algorithms", 1, 4),
    (103, "Operating Systems", 1, 3),
    (104, "Database Systems", 1, 3),
    (105, "Computer Networks", 1, 3),
    # Electronics
    (201, "Circuit Theory", 2, 4),
    (202, "Signal Processing", 2, 3),
    (203, "VLSI Design", 2, 3),
    (204, "Embedded Systems", 2, 4),
    # Mechanical
    (301, "Thermodynamics", 3, 4),
    (302, "Fluid Mechanics", 3, 3),
    (303, "Manufacturing", 3, 3),
    (304, "Machine Design", 3, 4),
    # Civil
    (401, "Structural Analysis", 4, 4),
    (402, "Geotechnical Engineering", 4, 3),
    (403, "Transportation Engineering", 4, 3),
    (404, "Environmental Engineering", 4, 3),
    # Mathematics
    (501, "Linear Algebra", 5, 3),
    (502, "Real Analysis", 5, 3),
    (503, "Probability & Statistics", 5, 4),
    (504, "Discrete Mathematics", 5, 3),
]

FIRST_NAMES: List[str] = [
    "Aarav", "Aditi", "Aditya", "Akash", "Amit", "Ananya", "Anjali", "Arjun",
    "Bhavya", "Chandra", "Deepak", "Diya", "Esha", "Gaurav", "Harsh", "Isha",
    "Jaya", "Karan", "Kavya", "Lakshmi", "Manish", "Meera", "Mohit", "Nandini",
    "Nikhil", "Pallavi", "Pooja", "Priya", "Rahul", "Ravi", "Rohit", "Sakshi",
    "Sandeep", "Shreya", "Sneha", "Suresh", "Tanvi", "Varun", "Vikram", "Yash",
]

LAST_NAMES: List[str] = [
    "Agarwal", "Bansal", "Bhat", "Chauhan", "Das", "Deshmukh", "Ghosh",
    "Gupta", "Jain", "Joshi", "Kapoor", "Kumar", "Mehta", "Mishra", "Nair",
    "Pandey", "Patel", "Rao", "Reddy", "Sharma", "Singh", "Srinivasan",
    "Tiwari", "Verma", "Yadav",
]

BRANCH_FOR_DEPT = {
    1: "Computer Science",
    2: "Electronics",
    3: "Mechanical",
    4: "Civil",
    5: "Mathematics",
}


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def _generate_students(rng: random.Random, count: int = 3000) -> List[Tuple]:
    """Return a list of (student_id, name, age, branch, cgpa, dept_id)."""
    students = []
    for sid in range(1, count + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        name = f"{first} {last}"
        age = rng.randint(18, 28)
        dept_id = rng.randint(1, 5)
        branch = BRANCH_FOR_DEPT[dept_id]
        cgpa = round(rng.uniform(4.0, 10.0), 2)
        students.append((sid, name, age, branch, cgpa, dept_id))
    return students


def _generate_enrollments(
    rng: random.Random,
    students: List[Tuple],
    courses: List[Tuple],
    target: int = 8000,
) -> List[Tuple]:
    """Return a list of (enrollment_id, student_id, course_id, marks).

    Each student is enrolled in 2-4 courses (no duplicates per student).
    Generation continues until at least *target* rows are produced.
    """
    course_ids = [c[0] for c in courses]
    enrollments: List[Tuple] = []
    eid = 1
    seen: set = set()

    for student in students:
        sid = student[0]
        num_courses = rng.randint(2, 4)
        chosen = rng.sample(course_ids, min(num_courses, len(course_ids)))
        for cid in chosen:
            if (sid, cid) in seen:
                continue
            seen.add((sid, cid))
            marks = round(rng.uniform(30.0, 100.0), 1)
            enrollments.append((eid, sid, cid, marks))
            eid += 1

    # If we haven't hit the target, cycle through students again
    student_ids = [s[0] for s in students]
    while len(enrollments) < target:
        sid = rng.choice(student_ids)
        cid = rng.choice(course_ids)
        if (sid, cid) in seen:
            continue
        seen.add((sid, cid))
        marks = round(rng.uniform(30.0, 100.0), 1)
        enrollments.append((eid, sid, cid, marks))
        eid += 1

    return enrollments


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_seeded(conn: sqlite3.Connection) -> bool:
    """Return True if the database already contains seed data."""
    try:
        cur = conn.execute("SELECT COUNT(*) FROM Student")
        count = cur.fetchone()[0]
        return count > 0
    except sqlite3.OperationalError:
        return False


def seed_database(conn: sqlite3.Connection) -> None:
    """Insert deterministic seed data into every table.

    Uses ``random.seed(42)`` so results are perfectly reproducible.
    """
    rng = random.Random(42)

    # Departments
    conn.executemany(
        "INSERT INTO Department (dept_id, dept_name, hod) VALUES (?, ?, ?)",
        DEPARTMENTS,
    )

    # Courses
    conn.executemany(
        "INSERT INTO Course (course_id, course_name, dept_id, credits) VALUES (?, ?, ?, ?)",
        COURSES,
    )

    # Students
    students = _generate_students(rng, count=3000)
    conn.executemany(
        "INSERT INTO Student (student_id, name, age, branch, cgpa, dept_id) VALUES (?, ?, ?, ?, ?, ?)",
        students,
    )

    # Enrollments
    enrollments = _generate_enrollments(rng, students, COURSES, target=8000)
    conn.executemany(
        "INSERT INTO Enrollment (enrollment_id, student_id, course_id, marks) VALUES (?, ?, ?, ?)",
        enrollments,
    )

    conn.commit()
