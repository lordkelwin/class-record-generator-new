"""
db_persistence.py - Relational SQLite Persistence Layer for Courses, Blueprints,
Assessments, Grades, Users, and Students.

Consolidates persistence into `data/academic_catalog.db`.
Provides relational table schemas, automated migration from JSON files, and atomic CRUD operations.
"""

import os
import re
import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import config
    BASE_DIR = config.BASE_DIR
    DATA_DIR = config.DATA_DIR
    DB_PATH = config.DATABASE_PATH
    USERS_JSON_PATH = config.USERS_JSON_PATH
    STUDENTS_JSON_PATH = config.STUDENTS_JSON_PATH
    COURSES_BASE_DIR = config.COURSES_DIR
except Exception:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "academic_catalog.db"))
    USERS_JSON_PATH = os.environ.get("USERS_JSON_PATH", os.path.join(DATA_DIR, "users.json"))
    STUDENTS_JSON_PATH = os.environ.get("STUDENTS_JSON_PATH", os.path.join(DATA_DIR, "students.json"))
    COURSES_BASE_DIR = os.environ.get("COURSES_DIR", os.path.join(DATA_DIR, "courses"))


def get_db_connection() -> sqlite3.Connection:
    """Returns a connection with WAL mode and foreign keys enabled."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initializes relational tables if they do not exist."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # 1. App Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                full_name TEXT NOT NULL,
                email TEXT,
                role TEXT,
                workflow_roles TEXT,
                program_codes TEXT,
                department TEXT,
                college TEXT,
                position_title TEXT,
                signature_data TEXT,
                can_access_faculty_tools INTEGER DEFAULT 1,
                is_staff INTEGER DEFAULT 0,
                extra_data TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # 2. App Students table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_students (
                student_id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                full_name TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                program_year TEXT,
                signature_data TEXT,
                signature_updated_at TEXT,
                enrolled_courses TEXT,
                assessment_acknowledgments TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # 3. Course Records table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS course_records (
                course_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                course_code TEXT NOT NULL,
                course_title TEXT NOT NULL,
                section TEXT,
                semester_ay TEXT,
                schedule TEXT,
                program_code TEXT,
                year_level TEXT,
                credit_units REAL,
                workflow_status TEXT,
                blueprint_json TEXT NOT NULL,
                workflow_json TEXT,
                class_record_workflow_json TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # 4. Assessment Categories table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS assessment_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                category_id TEXT NOT NULL,
                term TEXT NOT NULL,
                name TEXT NOT NULL,
                assessment_code TEXT,
                assessment_type TEXT,
                weight_pct REAL,
                is_major INTEGER DEFAULT 0,
                lec_lab TEXT DEFAULT 'Lecture',
                FOREIGN KEY (course_id) REFERENCES course_records(course_id) ON DELETE CASCADE
            )
        """)

        # 5. Assessment Items table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS assessment_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                category_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                name TEXT NOT NULL,
                max_score REAL,
                co_id TEXT,
                weight_pct REAL,
                clo_points_json TEXT,
                FOREIGN KEY (course_id) REFERENCES course_records(course_id) ON DELETE CASCADE
            )
        """)

        # 6. Student Course Grades table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_course_grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                student_name TEXT,
                scores_json TEXT,
                midterm_grade REAL,
                finals_grade REAL,
                afg REAL,
                usep_grade TEXT,
                remarks TEXT,
                assessment_acknowledgments_json TEXT,
                updated_at TEXT,
                FOREIGN KEY (course_id) REFERENCES course_records(course_id) ON DELETE CASCADE,
                UNIQUE(course_id, student_id)
            )
        """)

        # 7. Syllabus Reviews and Signatures table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS syllabus_reviews_and_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                step TEXT NOT NULL,
                role TEXT NOT NULL,
                username TEXT NOT NULL,
                full_name TEXT,
                decision TEXT,
                remarks TEXT,
                signature_data TEXT,
                signed_at TEXT,
                content_hash TEXT,
                FOREIGN KEY (course_id) REFERENCES course_records(course_id) ON DELETE CASCADE
            )
        """)

        # 8. Syllabus Evaluation Checklist Responses table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS syllabus_evaluations (
                course_id TEXT PRIMARY KEY,
                responses_json TEXT,
                comments_json TEXT,
                recommendations TEXT,
                general_remarks TEXT,
                faculty_action_taken TEXT,
                overall_recommendation TEXT,
                revision_type TEXT,
                other_comments TEXT,
                updated_by TEXT,
                updated_at TEXT,
                FOREIGN KEY (course_id) REFERENCES course_records(course_id) ON DELETE CASCADE
            )
        """)

        # Create helpful indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cr_owner ON course_records(owner);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cr_code ON course_records(course_code);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ac_cid ON assessment_categories(course_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ai_cid ON assessment_items(course_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_scg_cid ON student_course_grades(course_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_srs_cid ON syllabus_reviews_and_signatures(course_id);")

        # Dynamic schema migrations
        try:
            cur.execute("ALTER TABLE course_records ADD COLUMN student_acknowledgments_json TEXT;")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE app_students ADD COLUMN syllabus_acknowledgments TEXT;")
        except sqlite3.OperationalError:
            pass

        conn.commit()
    finally:
        conn.close()


# ==============================================================================
# USER CRUD OPERATIONS
# ==============================================================================

def load_users_from_db() -> Dict[str, Dict[str, Any]]:
    """Loads all users from app_users table."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM app_users").fetchall()
        result = {}
        for r in rows:
            u = {
                "username": r["username"],
                "password_hash": r["password_hash"],
                "full_name": r["full_name"],
                "email": r["email"],
                "role": r["role"],
                "workflow_roles": json.loads(r["workflow_roles"] or "[]"),
                "program_codes": json.loads(r["program_codes"] or "[]"),
                "department": r["department"],
                "college": r["college"],
                "position_title": r["position_title"],
                "signature_data": r["signature_data"],
                "can_access_faculty_tools": bool(r["can_access_faculty_tools"]),
                "is_staff": bool(r["is_staff"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            if r["extra_data"]:
                try:
                    extra = json.loads(r["extra_data"])
                    for k, v in extra.items():
                        if k not in u:
                            u[k] = v
                except Exception:
                    pass
            result[r["username"]] = u
        return result
    finally:
        conn.close()


def save_user_to_db(u: Dict[str, Any]) -> None:
    """Inserts or updates a single user into app_users."""
    init_db()
    conn = get_db_connection()
    try:
        now_iso = datetime.now().isoformat()
        username = u.get("username", "").strip()
        if not username:
            return

        known_keys = {
            "username", "password_hash", "full_name", "email", "role",
            "workflow_roles", "program_codes", "department", "college",
            "position_title", "signature_data", "can_access_faculty_tools",
            "is_staff", "created_at", "updated_at"
        }
        extra = {k: v for k, v in u.items() if k not in known_keys}

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO app_users (
                username, password_hash, full_name, email, role,
                workflow_roles, program_codes, department, college,
                position_title, signature_data, can_access_faculty_tools,
                is_staff, extra_data, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                full_name = excluded.full_name,
                email = excluded.email,
                role = excluded.role,
                workflow_roles = excluded.workflow_roles,
                program_codes = excluded.program_codes,
                department = excluded.department,
                college = excluded.college,
                position_title = excluded.position_title,
                signature_data = excluded.signature_data,
                can_access_faculty_tools = excluded.can_access_faculty_tools,
                is_staff = excluded.is_staff,
                extra_data = excluded.extra_data,
                updated_at = excluded.updated_at
        """, (
            username,
            u.get("password_hash"),
            u.get("full_name") or username,
            u.get("email"),
            u.get("role", "faculty"),
            json.dumps(u.get("workflow_roles") or []),
            json.dumps(u.get("program_codes") or []),
            u.get("department"),
            u.get("college"),
            u.get("position_title"),
            u.get("signature_data"),
            1 if u.get("can_access_faculty_tools", True) else 0,
            1 if u.get("is_staff", False) else 0,
            json.dumps(extra) if extra else None,
            u.get("created_at") or now_iso,
            now_iso
        ))
        conn.commit()
    finally:
        conn.close()


def delete_user_from_db(username: str) -> bool:
    """Deletes a user by username from app_users."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM app_users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def save_users_dict_to_db(users_dict: Dict[str, Dict[str, Any]], purge_missing: bool = True) -> None:
    """Saves multiple users into app_users in a single transaction."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        now_iso = datetime.now().isoformat()
        known_keys = {
            "username", "password_hash", "full_name", "email", "role",
            "workflow_roles", "program_codes", "department", "college",
            "position_title", "signature_data", "can_access_faculty_tools",
            "is_staff", "created_at", "updated_at"
        }
        if purge_missing and users_dict:
            valid_keys = [k.lower().strip() for k in users_dict.keys()]
            placeholders = ",".join("?" for _ in valid_keys)
            cur.execute(f"DELETE FROM app_users WHERE LOWER(username) NOT IN ({placeholders})", valid_keys)

        for uname, u in users_dict.items():
            username = (u.get("username") or uname).strip()
            if not username:
                continue
            extra = {k: v for k, v in u.items() if k not in known_keys}
            cur.execute("""
                INSERT INTO app_users (
                    username, password_hash, full_name, email, role,
                    workflow_roles, program_codes, department, college,
                    position_title, signature_data, can_access_faculty_tools,
                    is_staff, extra_data, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password_hash = excluded.password_hash,
                    full_name = excluded.full_name,
                    email = excluded.email,
                    role = excluded.role,
                    workflow_roles = excluded.workflow_roles,
                    program_codes = excluded.program_codes,
                    department = excluded.department,
                    college = excluded.college,
                    position_title = excluded.position_title,
                    signature_data = excluded.signature_data,
                    can_access_faculty_tools = excluded.can_access_faculty_tools,
                    is_staff = excluded.is_staff,
                    extra_data = excluded.extra_data,
                    updated_at = excluded.updated_at
            """, (
                username,
                u.get("password_hash"),
                u.get("full_name") or username,
                u.get("email"),
                u.get("role", "faculty"),
                json.dumps(u.get("workflow_roles") or []),
                json.dumps(u.get("program_codes") or []),
                u.get("department"),
                u.get("college"),
                u.get("position_title"),
                u.get("signature_data"),
                1 if u.get("can_access_faculty_tools", True) else 0,
                1 if u.get("is_staff", False) else 0,
                json.dumps(extra) if extra else None,
                u.get("created_at") or now_iso,
                now_iso
            ))
        conn.commit()
    finally:
        conn.close()


# ==============================================================================
# STUDENT CRUD OPERATIONS
# ==============================================================================

def load_students_from_db() -> Dict[str, Dict[str, Any]]:
    """Loads all students from app_students table."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM app_students").fetchall()
        result = {}
        for r in rows:
            sid = r["student_id"]
            s = {
                "student_id": sid,
                "username": r["username"] or sid,
                "password_hash": r["password_hash"],
                "full_name": r["full_name"],
                "name": r["full_name"],
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "email": r["email"],
                "program_year": r["program_year"],
                "signature_data": r["signature_data"],
                "signature_updated_at": r["signature_updated_at"],
                "enrolled_courses": json.loads(r["enrolled_courses"] or "[]"),
                "assessment_acknowledgments": json.loads(r["assessment_acknowledgments"] or "{}"),
                "syllabus_acknowledgments": json.loads(r["syllabus_acknowledgments"] or "{}") if ("syllabus_acknowledgments" in r.keys() and r["syllabus_acknowledgments"]) else {},
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            result[sid] = s
        return result
    finally:
        conn.close()


def delete_student_from_db(student_id: str) -> bool:
    """Deletes a student by student_id from app_students."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM app_students WHERE student_id = ?", (str(student_id).strip(),))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def disenroll_student_from_course_db(student_id: str, course_id: str) -> bool:
    """
    Disenrolls a student from a course in SQLite:
    1. Deletes student's row from student_course_grades for this course_id.
    2. Updates app_students to remove course_id from enrolled_courses.
    3. Explicitly commits the SQLite transaction.
    """
    init_db()
    sid = str(student_id or "").strip()
    cid = str(course_id or "").strip()
    if not sid or not cid:
        return False

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # 1. Delete from student_course_grades
        cur.execute("""
            DELETE FROM student_course_grades 
            WHERE course_id = ? AND (student_id = ? OR student_id = ?)
        """, (cid, sid, sid.lower()))

        # 2. Update enrolled_courses in app_students
        cur.execute("SELECT student_id, enrolled_courses FROM app_students WHERE student_id = ? OR student_id = ?", (sid, sid.lower()))
        rows = cur.fetchall()
        for r in rows:
            r_sid = r["student_id"]
            try:
                enrolled = json.loads(r["enrolled_courses"] or "[]")
            except Exception:
                enrolled = []
            new_enrolled = [c for c in enrolled if str(c).strip().lower() != cid.lower()]
            cur.execute("UPDATE app_students SET enrolled_courses = ? WHERE student_id = ?", (json.dumps(new_enrolled), r_sid))

        conn.commit()
        return True
    finally:
        conn.close()


def save_students_dict_to_db(students_dict: Dict[str, Dict[str, Any]], purge_missing: bool = True) -> None:
    """Saves multiple students into app_students table."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        now_iso = datetime.now().isoformat()
        if purge_missing and students_dict:
            valid_sids = [str(k).strip() for k in students_dict.keys()]
            placeholders = ",".join("?" for _ in valid_sids)
            cur.execute(f"DELETE FROM app_students WHERE student_id NOT IN ({placeholders})", valid_sids)

        for sid, s in students_dict.items():
            student_id = str(s.get("student_id") or sid).strip()
            if not student_id:
                continue
            cur.execute("""
                INSERT INTO app_students (
                    student_id, username, password_hash, full_name,
                    first_name, last_name, email, program_year,
                    signature_data, signature_updated_at, enrolled_courses,
                    assessment_acknowledgments, syllabus_acknowledgments, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    username = excluded.username,
                    password_hash = excluded.password_hash,
                    full_name = excluded.full_name,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    email = excluded.email,
                    program_year = excluded.program_year,
                    signature_data = excluded.signature_data,
                    signature_updated_at = excluded.signature_updated_at,
                    enrolled_courses = excluded.enrolled_courses,
                    assessment_acknowledgments = excluded.assessment_acknowledgments,
                    syllabus_acknowledgments = excluded.syllabus_acknowledgments,
                    updated_at = excluded.updated_at
            """, (
                student_id,
                s.get("username") or student_id,
                s.get("password_hash"),
                s.get("full_name") or s.get("name") or student_id,
                s.get("first_name"),
                s.get("last_name"),
                s.get("email"),
                s.get("program_year"),
                s.get("signature_data"),
                s.get("signature_updated_at"),
                json.dumps(s.get("enrolled_courses") or []),
                json.dumps(s.get("assessment_acknowledgments") or {}),
                json.dumps(s.get("syllabus_acknowledgments") or {}),
                s.get("created_at") or now_iso,
                now_iso
            ))
        conn.commit()
    finally:
        conn.close()


# ==============================================================================
# COURSE DOCUMENT & RELATIONAL ASSESSMENT CRUD OPERATIONS
# ==============================================================================

def save_course_to_db(doc: Dict[str, Any]) -> None:
    """
    Saves course document and synchronizes child relational tables:
    - course_records
    - assessment_categories
    - assessment_items
    - student_course_grades
    - syllabus_reviews_and_signatures
    - syllabus_evaluations
    """
    init_db()
    cid = doc.get("id") or doc.get("course_id")
    if not cid:
        return

    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    wf = doc.get("workflow") or {}
    cr_wf = doc.get("class_record_workflow") or {}

    owner = doc.get("owner") or "default"
    code = (doc.get("course_code") or meta.get("course_code") or "Course").strip()
    title = (doc.get("course_title") or meta.get("course_title") or "").strip()
    section = (doc.get("section") or meta.get("section") or "1A").strip()
    sem_ay = (doc.get("semester_ay") or meta.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()
    schedule = meta.get("schedule") or doc.get("schedule") or ""
    prog_code = (meta.get("program_code") or doc.get("program") or "EE").strip().upper()
    yr_level = meta.get("year_level") or ""
    try:
        credit_units = float(meta.get("credit_units") or 3.0)
    except (ValueError, TypeError):
        credit_units = 3.0

    wf_status = wf.get("status") or "draft"
    now_iso = datetime.now().isoformat()
    created_at = doc.get("created_at") or now_iso

    # Ensure student_acknowledgments is preserved in workflow, blueprint, and doc
    acks = doc.get("student_acknowledgments") or wf.get("student_acknowledgments") or bp.get("student_acknowledgments") or []
    if acks:
        doc["student_acknowledgments"] = acks
        wf["student_acknowledgments"] = acks
        bp["student_acknowledgments"] = acks

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # 1. Upsert course_records
        cur.execute("""
            INSERT INTO course_records (
                course_id, owner, course_code, course_title, section,
                semester_ay, schedule, program_code, year_level,
                credit_units, workflow_status, blueprint_json,
                workflow_json, class_record_workflow_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(course_id) DO UPDATE SET
                owner = excluded.owner,
                course_code = excluded.course_code,
                course_title = excluded.course_title,
                section = excluded.section,
                semester_ay = excluded.semester_ay,
                schedule = excluded.schedule,
                program_code = excluded.program_code,
                year_level = excluded.year_level,
                credit_units = excluded.credit_units,
                workflow_status = excluded.workflow_status,
                blueprint_json = excluded.blueprint_json,
                workflow_json = excluded.workflow_json,
                class_record_workflow_json = excluded.class_record_workflow_json,
                updated_at = excluded.updated_at
        """, (
            cid, owner, code, title, section, sem_ay, schedule,
            prog_code, yr_level, credit_units, wf_status,
            json.dumps(bp), json.dumps(wf), json.dumps(cr_wf),
            created_at, now_iso
        ))

        try:
            cur.execute("UPDATE course_records SET student_acknowledgments_json = ? WHERE course_id = ?", (json.dumps(acks), cid))
        except Exception:
            pass

        # 2. Sync assessment_categories and assessment_items
        cur.execute("DELETE FROM assessment_items WHERE course_id = ?", (cid,))
        cur.execute("DELETE FROM assessment_categories WHERE course_id = ?", (cid,))

        categories = bp.get("categories") or []
        for cat in categories:
            cat_id = cat.get("category_id") or cat.get("assessment_code") or "CAT"
            term = cat.get("term") or "Midterm"
            name = cat.get("name") or "Category"
            a_code = cat.get("assessment_code") or ""
            a_type = cat.get("assessment_type") or "SA"
            try:
                wt = float(cat.get("weight_pct") or 0.0)
            except (ValueError, TypeError):
                wt = 0.0
            is_maj = 1 if cat.get("is_major_assessment") else 0
            lec_lab = cat.get("lec_lab") or "Lecture"

            cur.execute("""
                INSERT INTO assessment_categories (
                    course_id, category_id, term, name, assessment_code,
                    assessment_type, weight_pct, is_major, lec_lab
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cid, cat_id, term, name, a_code, a_type, wt, is_maj, lec_lab))

            for it in cat.get("items", []):
                item_id = it.get("item_id") or "ITEM"
                it_name = it.get("name") or item_id
                try:
                    max_score = float(it.get("max_score") or 30.0)
                except (ValueError, TypeError):
                    max_score = 30.0
                co_id = it.get("co_id") or "CLO1"
                try:
                    it_wt = float(it.get("weight_pct") or 0.0)
                except (ValueError, TypeError):
                    it_wt = 0.0
                clo_pts_json = json.dumps(it.get("clo_points") or {})

                cur.execute("""
                    INSERT INTO assessment_items (
                        course_id, category_id, item_id, name, max_score,
                        co_id, weight_pct, clo_points_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (cid, cat_id, item_id, it_name, max_score, co_id, it_wt, clo_pts_json))

        # 3. Sync student_course_grades
        cur.execute("DELETE FROM student_course_grades WHERE course_id = ?", (cid,))
        students = bp.get("students") or []
        for st in students:
            st_id = str(st.get("student_id") or "").strip()
            if not st_id:
                continue
            st_name = st.get("name") or f"{st.get('last_name', '')}, {st.get('first_name', '')}".strip(", ")
            scores_json = json.dumps(st.get("scores") or {})
            acks_json = json.dumps(st.get("assessment_acknowledgments") or {})
            cur.execute("""
                INSERT INTO student_course_grades (
                    course_id, student_id, student_name, scores_json,
                    assessment_acknowledgments_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (cid, st_id, st_name, scores_json, acks_json, now_iso))

        # 4. Sync syllabus_reviews_and_signatures
        cur.execute("DELETE FROM syllabus_reviews_and_signatures WHERE course_id = ?", (cid,))
        signatures = wf.get("signatures") or []
        for s in signatures:
            cur.execute("""
                INSERT INTO syllabus_reviews_and_signatures (
                    course_id, step, role, username, full_name,
                    decision, remarks, signature_data, signed_at, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cid,
                s.get("step", ""),
                s.get("role", ""),
                s.get("username", ""),
                s.get("full_name", ""),
                s.get("decision", "approved"),
                s.get("remarks", ""),
                s.get("signature_data", ""),
                s.get("signed_at", now_iso),
                s.get("content_hash", "")
            ))

        # 5. Sync syllabus_evaluations
        cl = wf.get("checklist") or {}
        if cl:
            cur.execute("""
                INSERT INTO syllabus_evaluations (
                    course_id, responses_json, comments_json, recommendations,
                    general_remarks, faculty_action_taken, overall_recommendation,
                    revision_type, other_comments, updated_by, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id) DO UPDATE SET
                    responses_json = excluded.responses_json,
                    comments_json = excluded.comments_json,
                    recommendations = excluded.recommendations,
                    general_remarks = excluded.general_remarks,
                    faculty_action_taken = excluded.faculty_action_taken,
                    overall_recommendation = excluded.overall_recommendation,
                    revision_type = excluded.revision_type,
                    other_comments = excluded.other_comments,
                    updated_by = excluded.updated_by,
                    updated_at = excluded.updated_at
            """, (
                cid,
                json.dumps(cl.get("responses") or {}),
                json.dumps(cl.get("comments") or {}),
                cl.get("recommendations", ""),
                cl.get("general_remarks", ""),
                cl.get("faculty_action_taken", ""),
                cl.get("overall_recommendation", ""),
                cl.get("revision_type", ""),
                cl.get("other_comments", ""),
                cl.get("updated_by", ""),
                cl.get("updated_at", now_iso)
            ))

        conn.commit()
    finally:
        conn.close()


def get_enrolled_students_for_course(course_id: str, section: str = "", program_code: str = "", exclude_student_ids: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Queries SQLite database (app_students joined with student_course_grades)
    to fetch all students enrolled in or associated with this course and section.
    
    Matches by:
      1. Student has a grade entry in student_course_grades for course_id
      2. Student's enrolled_courses list contains course_id
      3. Student's program_year matches the course section or its variants (e.g., 'EE 2A', 'BSEE 2A', '2A')
      4. Fallback to student_store / data/students.json
    
    Returns clean student records with scores and acknowledgments populated.
    """
    init_db()
    cid = (course_id or "").strip()
    sec = (section or "").strip()
    prog = (program_code or "").strip().upper()

    cid_like = f'%"{cid}"%'

    # Extract section tokens e.g. 'EE 2A', '2A', 'BSEE 2A'
    sec_tokens = [s.strip() for s in sec.split(",") if s.strip()]
    sec_variants = set()
    for s in sec_tokens:
        sec_variants.add(s)
        sec_variants.add(s.upper())
        clean = re.sub(r'^(BSEE|BSCE|BSCpE|BSECE|BSME|EE)\s*', '', s, flags=re.I).strip()
        if clean:
            sec_variants.add(clean)
            sec_variants.add(f"EE {clean}")
            sec_variants.add(f"BSEE {clean}")
            if prog:
                sec_variants.add(f"{prog} {clean}")

    def _norm(v: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", str(v or "")).lower()

    enrolled_students: Dict[str, Dict[str, Any]] = {}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # 1. Query app_students joined with student_course_grades
        conditions = ["s.enrolled_courses LIKE ?", "g.course_id = ?"]
        params = [cid_like, cid]

        for v in sec_variants:
            conditions.append("s.program_year = ?")
            params.append(v)
            conditions.append("s.program_year LIKE ?")
            params.append(f"%{v}%")

        where_clause = " OR ".join(conditions)
        query = f"""
            SELECT DISTINCT
                s.student_id,
                s.username,
                s.full_name,
                s.first_name,
                s.last_name,
                s.email,
                s.program_year,
                s.enrolled_courses,
                s.assessment_acknowledgments AS student_acks,
                g.scores_json,
                g.assessment_acknowledgments_json AS grade_acks
            FROM app_students s
            LEFT JOIN student_course_grades g ON (s.student_id = g.student_id AND g.course_id = ?)
            WHERE {where_clause}
            ORDER BY s.last_name, s.first_name, s.student_id
        """
        all_params = [cid] + params
        rows = cur.execute(query, all_params).fetchall()
        for r in rows:
            sid = str(r["student_id"] or "").strip()
            if not sid:
                continue

            if exclude_student_ids and str(sid).strip().lower() in [str(x).strip().lower() for x in exclude_student_ids]:
                continue

            norm_id = _norm(sid)
            scores = {}
            if r["scores_json"]:
                try:
                    scores = json.loads(r["scores_json"])
                except Exception:
                    pass
            acks = {}
            if r["grade_acks"]:
                try:
                    acks = json.loads(r["grade_acks"])
                except Exception:
                    pass
            elif r["student_acks"]:
                try:
                    all_s_acks = json.loads(r["student_acks"])
                    acks = all_s_acks.get(cid, {})
                except Exception:
                    pass

            first = (r["first_name"] or "").strip()
            last = (r["last_name"] or "").strip()
            full = (r["full_name"] or "").strip()
            if not last and full:
                if "," in full:
                    parts = [p.strip() for p in full.split(",", 1)]
                    last = parts[0]
                    first = parts[1]
                else:
                    parts = full.split()
                    last = parts[-1] if parts else ""
                    first = " ".join(parts[:-1]) if len(parts) > 1 else full

            enrolled_students[norm_id] = {
                "student_id": sid,
                "first_name": first,
                "last_name": last,
                "name": full or (f"{last}, {first}".strip(", ") if (last or first) else sid),
                "email": r["email"] or f"{sid.lower()}@usep.edu.ph",
                "program_year": r["program_year"] or sec,
                "scores": scores,
                "assessment_acknowledgments": acks,
            }

        # 2. Merge stored grades for enrolled students
        grade_rows = cur.execute(
            "SELECT student_id, scores_json, assessment_acknowledgments_json FROM student_course_grades WHERE course_id = ?",
            (cid,)
        ).fetchall()
        for gr in grade_rows:
            sid = str(gr["student_id"] or "").strip()
            if not sid:
                continue
            if exclude_student_ids and str(sid).strip().lower() in [str(x).strip().lower() for x in exclude_student_ids]:
                continue
            norm_id = _norm(sid)
            if norm_id in enrolled_students:
                if gr["scores_json"]:
                    try:
                        sc = json.loads(gr["scores_json"])
                        enrolled_students[norm_id]["scores"].update(sc)
                    except Exception:
                        pass
                if gr["assessment_acknowledgments_json"]:
                    try:
                        ga = json.loads(gr["assessment_acknowledgments_json"])
                        enrolled_students[norm_id].setdefault("assessment_acknowledgments", {}).update(ga)
                    except Exception:
                        pass
    finally:
        conn.close()

    # 3. Check JSON student_store fallback
    try:
        from student_store import _load_students
        json_students = _load_students()
        for s_norm, s_prof in json_students.items():
            sid = str(s_prof.get("student_id") or s_norm).strip()
            if not sid:
                continue
            if exclude_student_ids and str(sid).strip().lower() in [str(x).strip().lower() for x in exclude_student_ids]:
                continue
            norm_id = _norm(sid)
            c_enrolled = s_prof.get("enrolled_courses") or []
            py = str(s_prof.get("program_year") or "").strip()
            matches_course = (cid in c_enrolled)
            if not matches_course and sec_variants and (c_enrolled is None or len(c_enrolled) == 0):
                matches_course = any(v.lower() == py.lower() or v.lower() in py.lower() for v in sec_variants)

            if matches_course:
                if norm_id in enrolled_students:
                    c_acks = (s_prof.get("assessment_acknowledgments") or {}).get(cid) or {}
                    if c_acks:
                        enrolled_students[norm_id].setdefault("assessment_acknowledgments", {}).update(c_acks)
                else:
                    first = s_prof.get("first_name") or ""
                    last = s_prof.get("last_name") or ""
                    full = s_prof.get("full_name") or s_prof.get("name") or ""
                    enrolled_students[norm_id] = {
                        "student_id": sid,
                        "first_name": first,
                        "last_name": last,
                        "name": full or (f"{last}, {first}".strip(", ") if (last or first) else sid),
                        "email": s_prof.get("email") or f"{sid.lower()}@usep.edu.ph",
                        "program_year": py or sec,
                        "scores": {},
                        "assessment_acknowledgments": (s_prof.get("assessment_acknowledgments") or {}).get(cid) or {},
                    }
    except Exception as e:
        logger.debug("student_store check error: %s", e)

    return list(enrolled_students.values())


def load_course_from_db(course_id: str) -> Optional[Dict[str, Any]]:
    """Loads a course document by course_id from SQLite, ensuring categories and enrolled students are populated."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT * FROM course_records WHERE course_id = ?", (course_id,)).fetchone()
        if not row:
            return None

        bp = json.loads(row["blueprint_json"] or "{}")
        wf = json.loads(row["workflow_json"] or "{}")
        cr_wf = json.loads(row["class_record_workflow_json"] or "{}")

        # 1. Ensure categories are populated if missing from blueprint_json
        if not bp.get("categories"):
            cat_rows = cur.execute("SELECT * FROM assessment_categories WHERE course_id = ? ORDER BY id", (course_id,)).fetchall()
            if cat_rows:
                cats = []
                for cr in cat_rows:
                    cat_id = cr["category_id"]
                    it_rows = cur.execute("SELECT * FROM assessment_items WHERE course_id = ? AND category_id = ? ORDER BY id", (course_id, cat_id)).fetchall()
                    items = []
                    for ir in it_rows:
                        clo_pts = {}
                        if ir["clo_points_json"]:
                            try:
                                clo_pts = json.loads(ir["clo_points_json"])
                            except Exception:
                                pass
                        items.append({
                            "item_id": ir["item_id"],
                            "name": ir["name"],
                            "max_score": float(ir["max_score"] or 30.0),
                            "co_id": ir["co_id"] or "CLO1",
                            "weight_pct": float(ir["weight_pct"] or 0.0),
                            "clo_points": clo_pts
                        })
                    cats.append({
                        "category_id": cat_id,
                        "term": cr["term"],
                        "name": cr["name"],
                        "assessment_code": cr["assessment_code"],
                        "assessment_type": cr["assessment_type"],
                        "weight_pct": float(cr["weight_pct"] or 0.0),
                        "is_major_assessment": bool(cr["is_major"]),
                        "lec_lab": cr["lec_lab"] or "Lecture",
                        "items": items
                    })
                bp["categories"] = cats

        # 2. Populate enrolled students from database if blueprint has no students yet and not yet initialized
        existing_sts = bp.setdefault("students", [])
        is_initialized = bool(bp.get("class_record_initialized") or bp.get("students_initialized"))
        if not existing_sts and not is_initialized:
            enrolled = get_enrolled_students_for_course(row["course_id"], row["section"], row["program_code"])
            if enrolled:
                bp["students"] = enrolled
                bp["class_record_initialized"] = True

        # 3. Restore student_acknowledgments
        acks = []
        try:
            if "student_acknowledgments_json" in row.keys() and row["student_acknowledgments_json"]:
                acks = json.loads(row["student_acknowledgments_json"])
        except Exception:
            pass
        if not acks:
            acks = wf.get("student_acknowledgments") or bp.get("student_acknowledgments") or []

        doc = {
            "id": row["course_id"],
            "course_id": row["course_id"],
            "owner": row["owner"],
            "course_code": row["course_code"],
            "course_title": row["course_title"],
            "section": row["section"],
            "semester_ay": row["semester_ay"],
            "schedule": row["schedule"],
            "program": row["program_code"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "blueprint": bp,
            "workflow": wf,
            "class_record_workflow": cr_wf,
            "student_acknowledgments": acks
        }
        if isinstance(bp, dict) and "tos" in bp:
            doc["tos"] = bp["tos"]
        return doc
    finally:
        conn.close()


def list_courses_from_db_for_user(username: str) -> List[Dict[str, Any]]:
    """Lists courses owned or authored by username from SQLite."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        u_lower = username.strip().lower()
        rows = cur.execute("SELECT * FROM course_records").fetchall()
        courses = []
        for r in rows:
            owner = (r["owner"] or "").lower()
            bp = json.loads(r["blueprint_json"] or "{}")
            meta = bp.get("metadata") or {}
            authors = meta.get("authors") or []
            author_unames = [(a.get("username") or "").lower() for a in authors if isinstance(a, dict)]
            if u_lower in (owner, "admin") or u_lower in author_unames:
                courses.append({
                    "id": r["course_id"],
                    "course_id": r["course_id"],
                    "owner": r["owner"],
                    "course_code": r["course_code"],
                    "course_title": r["course_title"],
                    "section": r["section"],
                    "semester_ay": r["semester_ay"],
                    "schedule": r["schedule"],
                    "program": r["program_code"],
                    "workflow_status": r["workflow_status"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "blueprint": bp,
                    "workflow": json.loads(r["workflow_json"] or "{}"),
                    "class_record_workflow": json.loads(r["class_record_workflow_json"] or "{}")
                })
        return courses
    finally:
        conn.close()


def list_all_courses_from_db() -> List[Dict[str, Any]]:
    """Lists all courses across all departments and programs."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM course_records ORDER BY course_code, section").fetchall()
        courses = []
        for r in rows:
            courses.append({
                "id": r["course_id"],
                "course_id": r["course_id"],
                "owner": r["owner"],
                "course_code": r["course_code"],
                "course_title": r["course_title"],
                "section": r["section"],
                "semester_ay": r["semester_ay"],
                "schedule": r["schedule"],
                "program": r["program_code"],
                "workflow_status": r["workflow_status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "blueprint": json.loads(r["blueprint_json"] or "{}"),
                "workflow": json.loads(r["workflow_json"] or "{}"),
                "class_record_workflow": json.loads(r["class_record_workflow_json"] or "{}")
            })
        return courses
    finally:
        conn.close()


def delete_course_from_db(course_id: str) -> bool:
    """Deletes a course and all its cascaded relational rows."""
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM course_records WHERE course_id = ?", (course_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


# ==============================================================================
# AUTOMATIC MIGRATION FROM JSON FILES TO SQLITE
# ==============================================================================

def migrate_all_from_json() -> None:
    """Migrates users, students, and courses from JSON into SQLite."""
    init_db()

    # 1. Migrate Users
    if os.path.exists(USERS_JSON_PATH):
        try:
            with open(USERS_JSON_PATH, "r", encoding="utf-8") as f:
                u_data = json.load(f)
                if isinstance(u_data, dict):
                    save_users_dict_to_db(u_data)
        except Exception as e:
            logger.warning("Error migrating users.json to SQLite: %s", e)

    # 2. Migrate Students
    if os.path.exists(STUDENTS_JSON_PATH):
        try:
            with open(STUDENTS_JSON_PATH, "r", encoding="utf-8") as f:
                s_data = json.load(f)
                if isinstance(s_data, dict):
                    save_students_dict_to_db(s_data)
        except Exception as e:
            logger.warning("Error migrating students.json to SQLite: %s", e)

    # 3. Migrate Courses
    if os.path.exists(COURSES_BASE_DIR):
        try:
            for owner in os.listdir(COURSES_BASE_DIR):
                owner_dir = os.path.join(COURSES_BASE_DIR, owner)
                if not os.path.isdir(owner_dir):
                    continue
                for fn in os.listdir(owner_dir):
                    if fn.endswith(".json"):
                        fp = os.path.join(owner_dir, fn)
                        try:
                            with open(fp, "r", encoding="utf-8") as f:
                                doc = json.load(f)
                                if isinstance(doc, dict):
                                    if not doc.get("owner"):
                                        doc["owner"] = owner
                                    save_course_to_db(doc)
                        except Exception as e:
                            logger.warning("Error migrating course file %s: %s", fp, e)
        except Exception as e:
            logger.warning("Error scanning courses directory: %s", e)
