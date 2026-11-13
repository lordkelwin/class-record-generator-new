"""
Academic Catalog Database (SQLite) Access Layer.
Manages persistent programs, courses, prerequisites, corequisites, and faculty roster
stored in data/academic_catalog.db.
All faculty names are stored without honorific titles.
"""

import json
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional

try:
    import config
    BASE_DIR = config.BASE_DIR
    DATA_DIR = config.DATA_DIR
    DB_PATH = config.DATABASE_PATH
except Exception:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "academic_catalog.db"))


def remove_honorific(name: str) -> str:
    """Removes honorific prefixes (Engr., Dr., Prof., etc.) and suffixes (Ph.D., PECE, etc.)."""
    if not name:
        return ""
    cleaned = name.strip()
    prefixes = [
        r"^Engr\.\s*", r"^Dr\.\s*", r"^Prof\.\s*", r"^Hon\.\s*",
        r"^Mr\.\s*", r"^Ms\.\s*", r"^Mrs\.\s*", r"^Atty\.\s*",
        r"^Architect\s*", r"^Arch\.\s*"
    ]
    for p in prefixes:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)

    suffixes = [
        r",\s*Ph\.?D\.?", r",\s*PECE", r",\s*PEE", r",\s*ECE",
        r",\s*MS[A-Z]*", r",\s*M\.?Sc\.?", r",\s*D\.?Eng\.?",
        r",\s*ASEAN\s*Eng\.?"
    ]
    for s in suffixes:
        cleaned = re.sub(s, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured with sqlite3.Row factory and WAL mode."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_academic_db(force_rebuild: bool = False) -> None:
    """Initializes and seeds data/academic_catalog.db if missing or force_rebuild=True."""
    if os.path.exists(DB_PATH) and not force_rebuild:
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    import catalog_data

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS courses")
    cur.execute("DROP TABLE IF EXISTS faculty")
    cur.execute("DROP TABLE IF EXISTS programs")

    # 1. Programs Table
    cur.execute("""
    CREATE TABLE programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        department_name TEXT NOT NULL,
        college TEXT NOT NULL DEFAULT 'College of Engineering',
        program_head TEXT NOT NULL,
        program_head_username TEXT NOT NULL
    )
    """)

    # 2. Faculty Table
    cur.execute("""
    CREATE TABLE faculty (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        original_name TEXT NOT NULL,
        department TEXT,
        position_title TEXT,
        employment_type TEXT,
        roles TEXT,
        email TEXT,
        created_at TEXT
    )
    """)

    # 3. Courses Table
    cur.execute("""
    CREATE TABLE courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_code TEXT NOT NULL,
        course_code TEXT NOT NULL,
        course_title TEXT NOT NULL,
        year_level TEXT,
        credit_units TEXT,
        lec_lab TEXT,
        contact_hours TEXT,
        prerequisites TEXT,
        corequisites TEXT,
        description TEXT,
        topics TEXT,
        sdgs TEXT,
        pgo_pi TEXT,
        FOREIGN KEY (program_code) REFERENCES programs(code)
    )
    """)

    PROGRAMS_INFO = [
        ("BSEE", "Bachelor of Science in Electrical Engineering", "Bachelor of Science in Electrical Engineering", "Charito O. Claro", "faculty_claro"),
        ("BSCE", "Bachelor of Science in Civil Engineering", "Bachelor of Science in Civil Engineering", "Bonifacio T. Aznar Jr.", "faculty_aznar"),
        ("BSECE", "Bachelor of Science in Electronics Engineering", "Bachelor of Science in Electronics Engineering", "Rosanna C. Ucat", "faculty_ucat"),
        ("BSME", "Bachelor of Science in Mechanical Engineering", "Bachelor of Science in Mechanical Engineering", "Randy B. Tongson", "faculty_tongson"),
        ("BSSE", "Bachelor of Science in Sanitary Engineering", "Bachelor of Science in Sanitary Engineering", "Sheena S. Arcega", "faculty_arcega"),
        ("BSABE", "Bachelor of Science in Agricultural and Biosystems Engineering", "Bachelor of Science in Agricultural and Biosystems Engineering", "Ruel Tuyogon", "faculty_tuyogon"),
        ("BSGeo", "Bachelor of Science in Geology", "Bachelor of Science in Geology", "Dean Lester P. Rejas", "faculty_rejas"),
        ("BSGE", "Bachelor of Science in Geodetic Engineering", "Bachelor of Science in Geodetic Engineering", "Fillmore D. Masancay", "faculty_masancay"),
        ("BSMinE", "Bachelor of Science in Mining Engineering", "Bachelor of Science in Mining Engineering", "Mark John S. Pag-alaman", "faculty_pagalaman"),
    ]

    cur.executemany("""
    INSERT INTO programs (code, name, department_name, program_head, program_head_username)
    VALUES (?, ?, ?, ?, ?)
    """, PROGRAMS_INFO)

    # Faculty (from data/users.json + catalog_data.OFFICIAL_FACULTY_ROSTER)
    users_file = os.path.join(DATA_DIR, "users.json")
    users = {}
    if os.path.exists(users_file):
        try:
            with open(users_file, "r", encoding="utf-8") as f:
                users = json.load(f)
        except Exception:
            users = {}

    faculty_rows = []
    seen_unames = set()
    for uname, udata in users.items():
        orig_name = udata.get("full_name", uname)
        clean_name = remove_honorific(orig_name)
        roles_list = udata.get("workflow_roles") or udata.get("roles") or [udata.get("role", "faculty")]
        roles_json = json.dumps(roles_list)
        faculty_rows.append((
            uname,
            clean_name,
            orig_name,
            udata.get("department") or "",
            udata.get("position_title") or udata.get("role", ""),
            "full_time" if "staff" not in uname else "staff",
            roles_json,
            udata.get("email") or f"{uname}@usep.edu.ph",
            udata.get("created_at") or ""
        ))
        seen_unames.add(uname)

    for dept_code, fgroup in catalog_data.OFFICIAL_FACULTY_ROSTER.items():
        for group_type in ("full_time", "part_time"):
            for f_item in fgroup.get(group_type, []):
                un = f_item.get("username")
                if not un or un in seen_unames:
                    continue
                orig_name = f_item.get("name", un)
                clean_name = remove_honorific(orig_name)
                faculty_rows.append((
                    un,
                    clean_name,
                    orig_name,
                    dept_code,
                    f_item.get("title", "Faculty Member"),
                    group_type,
                    json.dumps(f_item.get("roles", ["faculty"])),
                    f"{un}@usep.edu.ph",
                    ""
                ))
                seen_unames.add(un)

    cur.executemany("""
    INSERT INTO faculty (username, full_name, original_name, department, position_title, employment_type, roles, email, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, faculty_rows)

    # Populate Courses for all 9 programs
    PROGRAM_COURSES = [
        ("BSEE", catalog_data.BSEE_COURSES),
        ("BSCE", catalog_data.BSCE_COURSES),
        ("BSECE", catalog_data.BSECE_COURSES),
        ("BSME", catalog_data.BSME_COURSES),
        ("BSSE", catalog_data.BSSE_COURSES),
        ("BSABE", catalog_data.BSABE_COURSES),
        ("BSGeo", catalog_data.BSGEO_COURSES),
        ("BSGE", catalog_data.BSGE_COURSES),
        ("BSMinE", catalog_data.BSMINE_COURSES),
    ]

    course_rows = []
    for prog_code, clist in PROGRAM_COURSES:
        for c in clist:
            c_code = c.get("code", "").strip()
            if " - " in c_code or " – " in c_code:
                delim = " - " if " - " in c_code else " – "
                c_code = c_code.split(delim, 1)[0].strip()

            c_title = c.get("title", "").strip()
            yr = c.get("year_level", "")
            units = c.get("credit_units", "3.0 Units – Lecture")
            lec_lab = c.get("lec_lab", "Lecture")
            hrs = c.get("hours", "")
            prereqs = c.get("prereqs", "")
            coreqs = c.get("coreqs", "")
            desc = c.get("description", "")
            topics = json.dumps(c.get("topics", []))
            sdgs = c.get("sdgs", "")
            pgo = c.get("pgo_pi", "")

            course_rows.append((
                prog_code,
                c_code,
                c_title,
                yr,
                units,
                lec_lab,
                hrs,
                prereqs,
                coreqs,
                desc,
                topics,
                sdgs,
                pgo
            ))

    cur.executemany("""
    INSERT INTO courses (program_code, course_code, course_title, year_level, credit_units, lec_lab, contact_hours, prerequisites, corequisites, description, topics, sdgs, pgo_pi)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, course_rows)

    conn.commit()
    conn.close()


def get_all_programs() -> List[Dict[str, Any]]:
    """Returns all programs from the database."""
    init_academic_db()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT code, name, department_name, college, program_head, program_head_username FROM programs ORDER BY code")
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_program(code: str) -> Optional[Dict[str, Any]]:
    """Returns program details for the given program code."""
    init_academic_db()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM programs WHERE code = ?", (code,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_program_head(program_code: str) -> str:
    """Returns the program head's name for a given program code."""
    prog = get_program(program_code)
    return prog.get("program_head", "") if prog else ""


def get_dean() -> Dict[str, str]:
    """Returns the Dean's official details without honorific titles."""
    return {
        "name": "Joie D. Cataytay",
        "title": "Dean, College of Engineering",
        "college": "College of Engineering",
        "username": "dean_cataytay"
    }


def get_all_faculty(dept: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all faculty members with names stripped of honorific titles."""
    init_academic_db()
    with get_connection() as conn:
        cur = conn.cursor()
        if dept:
            cur.execute("SELECT username, full_name, department, position_title, employment_type, roles, email FROM faculty WHERE department = ? ORDER BY full_name", (dept,))
        else:
            cur.execute("SELECT username, full_name, department, position_title, employment_type, roles, email FROM faculty ORDER BY full_name")
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["roles"] = json.loads(d["roles"]) if d.get("roles") else []
            except Exception:
                d["roles"] = []
            result.append(d)
        return result


def get_faculty_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Returns faculty info by username."""
    init_academic_db()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM faculty WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["roles"] = json.loads(d["roles"]) if d.get("roles") else []
        except Exception:
            d["roles"] = []
        return d


def get_courses_by_program(program_code: str, year_level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns courses for a program with prerequisites, corequisites, units, etc."""
    init_academic_db()
    with get_connection() as conn:
        cur = conn.cursor()
        if year_level:
            cur.execute("""
            SELECT program_code, course_code, course_title, year_level, credit_units, lec_lab,
                   contact_hours, prerequisites, corequisites, description, topics, sdgs, pgo_pi
            FROM courses
            WHERE program_code = ? AND year_level = ?
            ORDER BY course_code
            """, (program_code, year_level))
        else:
            cur.execute("""
            SELECT program_code, course_code, course_title, year_level, credit_units, lec_lab,
                   contact_hours, prerequisites, corequisites, description, topics, sdgs, pgo_pi
            FROM courses
            WHERE program_code = ?
            ORDER BY course_code
            """, (program_code,))
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["topics"] = json.loads(d["topics"]) if d.get("topics") else []
            except Exception:
                d["topics"] = []
            result.append(d)
        return result


def get_course(course_code: str, program_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Finds a single course by course_code, optionally scoped by program_code."""
    init_academic_db()
    clean_code = course_code.strip()
    if " - " in clean_code or " – " in clean_code:
        delim = " - " if " - " in clean_code else " – "
        clean_code = clean_code.split(delim, 1)[0].strip()

    with get_connection() as conn:
        cur = conn.cursor()
        if program_code:
            cur.execute("SELECT * FROM courses WHERE course_code = ? AND program_code = ? LIMIT 1", (clean_code, program_code))
        else:
            cur.execute("SELECT * FROM courses WHERE course_code = ? LIMIT 1", (clean_code,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["topics"] = json.loads(d["topics"]) if d.get("topics") else []
        except Exception:
            d["topics"] = []
        return d


def search_courses(query: str, program_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Searches courses by course code or title."""
    init_academic_db()
    q = f"%{query.strip()}%"
    with get_connection() as conn:
        cur = conn.cursor()
        if program_code:
            cur.execute("""
            SELECT program_code, course_code, course_title, year_level, credit_units, lec_lab,
                   contact_hours, prerequisites, corequisites, description, topics, sdgs, pgo_pi
            FROM courses
            WHERE program_code = ? AND (course_code LIKE ? OR course_title LIKE ?)
            ORDER BY course_code
            """, (program_code, q, q))
        else:
            cur.execute("""
            SELECT program_code, course_code, course_title, year_level, credit_units, lec_lab,
                   contact_hours, prerequisites, corequisites, description, topics, sdgs, pgo_pi
            FROM courses
            WHERE course_code LIKE ? OR course_title LIKE ?
            ORDER BY course_code
            """, (q, q))
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["topics"] = json.loads(d["topics"]) if d.get("topics") else []
            except Exception:
                d["topics"] = []
            result.append(d)
        return result
