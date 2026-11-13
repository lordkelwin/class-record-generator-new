"""
Student Portal Data Store & Acknowledgment Manager.

Handles:
  - Student authentication by Student ID + Last Name / PIN
  - Automatic student discovery across enrolled class rosters in data/courses/
  - Storing student profiles and electronic signatures in data/students.json
  - Real-time aggregation of enrolled subjects:
      * Pending Acknowledgment (QA approved, awaiting student signature)
      * Acknowledged Syllabi (Signed with digital timestamp and signature)
      * In Review (Syllabus undergoing departmental/QA review)
  - Recording student syllabus acknowledgment submissions with e-signature and timestamp
"""

import json
import os
import re
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

DEFAULT_STUDENT_PASSWORD = "student123"
DEFAULT_PASSWORDS = {"student123", "student", "usep", "1234", "123456", "12345678", "password", "pass"}

try:
    import config
    BASE_DIR = config.BASE_DIR
    DATA_DIR = config.DATA_DIR
    STUDENTS_FILE = config.STUDENTS_JSON_PATH
    COURSES_BASE_DIR = config.COURSES_DIR
except Exception:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    STUDENTS_FILE = os.environ.get("STUDENTS_JSON_PATH", os.path.join(DATA_DIR, "students.json"))
    COURSES_BASE_DIR = os.environ.get("COURSES_DIR", os.path.join(DATA_DIR, "courses"))

_lock = threading.RLock()


def normalize_student_id(raw_id: str) -> str:
    """
    Normalizes student identifiers:
      - Trims whitespace and surrounding quotes
      - Strips institutional email domain (e.g., '2024-00101@usep.edu.ph' -> '2024-00101')
      - Collapses internal spaces around hyphens (e.g., '2024 - 00101' -> '2024-00101')
    """
    if not raw_id:
        return ""
    s = str(raw_id).strip().strip('"\'')
    if "@" in s:
        s = s.split("@")[0].strip()
    s = re.sub(r"\s*-\s*", "-", s)
    return s.strip()


def _get_all_courses() -> List[Dict[str, Any]]:
    """
    Retrieves all course documents across BOTH:
      1. SQLite database (db_persistence.list_all_courses_from_db())
      2. File-based storage (data/courses/ JSON files)
    Deduplicates by course_id / id.
    """
    courses_map: Dict[str, Dict[str, Any]] = {}

    # 1. Load from SQLite database
    try:
        import db_persistence
        db_courses = db_persistence.list_all_courses_from_db()
        for c in db_courses:
            cid = c.get("course_id") or c.get("id")
            if cid:
                courses_map[cid] = c
    except Exception as e:
        logger.debug("Could not read courses from SQLite in student_store: %s", e)

    # 2. Load from disk JSON files
    if os.path.exists(COURSES_BASE_DIR):
        for root, _, files in os.walk(COURSES_BASE_DIR):
            for fn in files:
                if not fn.endswith(".json"):
                    continue
                fp = os.path.join(root, fn)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        doc = json.load(f)
                    cid = doc.get("course_id") or doc.get("id") or fn[:-5]
                    if cid:
                        if cid not in courses_map:
                            courses_map[cid] = doc
                        else:
                            # Prefer document with richer student roster
                            existing_sts = courses_map[cid].get("blueprint", {}).get("students", [])
                            file_sts = doc.get("blueprint", {}).get("students", [])
                            if len(file_sts) > len(existing_sts):
                                courses_map[cid] = doc
                except Exception:
                    continue

    return list(courses_map.values())


def _load_students() -> Dict[str, Dict[str, Any]]:
    """Loads all students from both SQLite and JSON, merging them safely."""
    merged: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(STUDENTS_FILE):
        try:
            with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    merged.update(data)
        except Exception:
            pass

    try:
        import db_persistence
        db_students = db_persistence.load_students_from_db()
        if db_students and isinstance(db_students, dict):
            for sid, s in db_students.items():
                if sid not in merged:
                    merged[sid] = s
                else:
                    for k, v in s.items():
                        if v is not None and v != "":
                            merged[sid][k] = v
    except Exception:
        pass

    # Ensure baseline fields exist
    for sid, rec in merged.items():
        rec.setdefault("student_id", sid)
        rec.setdefault("username", sid)
        rec.setdefault("status", "active")
        rec.setdefault("is_active", 1)
        rec.setdefault("email", f"{sid.lower()}@usep.edu.ph")
        if not rec.get("password_hash"):
            rec["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)

    return merged


def _save_students(data: Dict[str, Dict[str, Any]]) -> None:
    try:
        import db_persistence
        db_persistence.save_students_dict_to_db(data)
    except Exception as e:
        logger.debug("Error saving students to db: %s", e)
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        import time
        for attempt in range(5):
            try:
                temp_file = f"{STUDENTS_FILE}.tmp.{os.getpid()}"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(temp_file, STUDENTS_FILE)
                break
            except Exception as ex:
                if attempt == 4:
                    # Last resort fallback: direct write
                    try:
                        with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                    except Exception as fatal_ex:
                        logger.warning("Could not write students file: %s", fatal_ex)
                else:
                    time.sleep(0.05 * (attempt + 1))


import unicodedata

def _clean(s: str) -> str:
    s = (s or "").strip()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower().strip()


def _normalize_id(sid: str) -> str:
    return normalize_student_id(sid)


def sync_course_roster_students(doc: Dict[str, Any]) -> int:
    """
    Synchronizes all students from a specific course document's roster into the student store.
    Guarantees active credentials, student ID/email binding, and enrolled course linkage.
    """
    if not doc or not isinstance(doc, dict):
        return 0
    cid = doc.get("id") or doc.get("course_id") or ""
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    sec = doc.get("section") or meta.get("section") or ""
    prog = meta.get("program_name") or "Engineering"
    roster = bp.get("students") or []
    if not roster:
        return 0

    count = 0
    with _lock:
        students = _load_students()
        for st in roster:
            sid = normalize_student_id(str(st.get("student_id") or ""))
            if not sid:
                continue
            last_n = (st.get("last_name") or "").strip()
            first_n = (st.get("first_name") or "").strip()
            name = (st.get("name") or "").strip()
            if not last_n and name:
                parts = [p.strip() for p in name.split(",", 1)]
                last_n = parts[0] if parts else ""
                first_n = parts[1] if len(parts) > 1 else ""
            full_n = f"{last_n}, {first_n}".strip(", ") if (last_n or first_n) else (name or sid)
            py = st.get("program_year") or sec or prog

            rec = students.get(sid, {})
            rec["student_id"] = sid
            rec["username"] = rec.get("username") or sid
            if full_n and not rec.get("full_name"):
                rec["full_name"] = full_n
            if last_n and not rec.get("last_name"):
                rec["last_name"] = last_n
            if first_n and not rec.get("first_name"):
                rec["first_name"] = first_n
            if py and not rec.get("program_year"):
                rec["program_year"] = py
            if not rec.get("email"):
                rec["email"] = f"{sid.lower()}@usep.edu.ph"
            if not rec.get("password_hash"):
                rec["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
            rec.setdefault("status", "active")
            rec.setdefault("is_active", 1)
            rec.setdefault("signature_data", "")
            rec.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))

            enrolled = rec.get("enrolled_courses") or []
            if cid and cid not in enrolled:
                enrolled.append(cid)
            rec["enrolled_courses"] = enrolled

            students[sid] = rec
            count += 1
        _save_students(students)
    return count


def disenroll_student_from_course(student_id: str, course_id: str) -> bool:
    """
    Disenrolls a student from a specific course:
    - Removes course_id from the student's enrolled_courses list in student_store & SQLite.
    - Removes assessment_acknowledgments for that course.
    - Cascades removal from student_course_grades in SQLite.
    """
    sid = normalize_student_id(str(student_id or "").strip())
    cid = str(course_id or "").strip()
    if not sid or not cid:
        return False

    with _lock:
        students = _load_students()
        target_keys = []
        for k, prof in students.items():
            k_sid = normalize_student_id(str(prof.get("student_id") or k).strip())
            if k_sid == sid or k == sid:
                target_keys.append(k)

        for k in target_keys:
            rec = students[k]
            enrolled = [c for c in (rec.get("enrolled_courses") or []) if str(c).strip().lower() != cid.lower()]
            rec["enrolled_courses"] = enrolled
            if "assessment_acknowledgments" in rec and isinstance(rec["assessment_acknowledgments"], dict):
                rec["assessment_acknowledgments"].pop(cid, None)
            students[k] = rec

        _save_students(students)

    try:
        import db_persistence
        db_persistence.disenroll_student_from_course_db(sid, cid)
    except Exception as _e:
        logger.debug("Error in db_persistence.disenroll_student_from_course_db: %s", _e)

    return True


def sync_all_course_students_to_store() -> int:
    """
    Scans all courses across BOTH SQLite database and file-based storage,
    registers every student into data/students.json and SQLite app_students,
    initializes default credentials, active flags, and links enrolled courses.
    """
    all_courses = _get_all_courses()
    synced = 0
    with _lock:
        students = _load_students()
        for doc in all_courses:
            cid = doc.get("id") or doc.get("course_id") or ""
            bp = doc.get("blueprint") or {}
            meta = bp.get("metadata") or {}
            sec = doc.get("section") or meta.get("section") or ""
            prog = meta.get("program_name") or "Engineering"
            roster = bp.get("students") or []
            for st in roster:
                sid = normalize_student_id(str(st.get("student_id") or ""))
                if not sid:
                    continue
                last_n = (st.get("last_name") or "").strip()
                first_n = (st.get("first_name") or "").strip()
                name = (st.get("name") or "").strip()
                if not last_n and name:
                    parts = [p.strip() for p in name.split(",", 1)]
                    last_n = parts[0] if parts else ""
                    first_n = parts[1] if len(parts) > 1 else ""
                full_n = f"{last_n}, {first_n}".strip(", ") if (last_n or first_n) else (name or sid)
                py = st.get("program_year") or sec or prog

                rec = students.get(sid, {})
                rec["student_id"] = sid
                rec["username"] = rec.get("username") or sid
                if full_n and not rec.get("full_name"):
                    rec["full_name"] = full_n
                if last_n and not rec.get("last_name"):
                    rec["last_name"] = last_n
                if first_n and not rec.get("first_name"):
                    rec["first_name"] = first_n
                if py and not rec.get("program_year"):
                    rec["program_year"] = py
                if not rec.get("email"):
                    rec["email"] = f"{sid.lower()}@usep.edu.ph"
                if not rec.get("password_hash"):
                    rec["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
                rec.setdefault("status", "active")
                rec.setdefault("is_active", 1)
                rec.setdefault("signature_data", "")
                rec.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))

                enrolled = rec.get("enrolled_courses") or []
                if cid and cid not in enrolled:
                    enrolled.append(cid)
                rec["enrolled_courses"] = enrolled

                students[sid] = rec
                synced += 1

        # Guarantee active status and default credentials for all students
        for sid, rec in students.items():
            if not rec.get("password_hash"):
                rec["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
            rec.setdefault("status", "active")
            rec.setdefault("is_active", 1)
            rec.setdefault("username", sid)
            rec.setdefault("email", f"{sid.lower()}@usep.edu.ph")

        _save_students(students)
    return synced


def find_student_in_course_rosters(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Searches across ALL courses (SQLite database and data/courses/ files)
    to find if this student_id, email, or name is present in any course roster.
    Returns student info including all enrolled_courses if found.
    """
    raw_input = (student_id or "").strip()
    if not raw_input:
        return None
    norm_input = normalize_student_id(raw_input)
    clean_input = _clean(norm_input)
    digits_input = re.sub(r"\D", "", norm_input)
    input_lower = raw_input.lower()

    all_courses = _get_all_courses()
    matched_student = None
    enrolled_cids = []

    for doc in all_courses:
        cid = doc.get("course_id") or doc.get("id") or ""
        bp = doc.get("blueprint") or {}
        students = bp.get("students") or []
        for st in students:
            curr_sid = normalize_student_id(str(st.get("student_id") or ""))
            curr_clean = _clean(curr_sid)
            curr_digits = re.sub(r"\D", "", curr_sid)
            last_n = (st.get("last_name") or "").strip()
            first_n = (st.get("first_name") or "").strip()
            name = (st.get("name") or "").strip()
            st_email = str(st.get("email") or "").strip().lower()

            if not last_n and name:
                parts = [p.strip() for p in name.split(",", 1)]
                last_n = parts[0] if parts else ""
                first_n = parts[1] if len(parts) > 1 else ""
            full_name = f"{last_n}, {first_n}".strip(", ") if (last_n or first_n) else (name or curr_sid)

            matched = False
            if curr_sid and norm_input and curr_sid.lower() == norm_input.lower():
                matched = True
            elif curr_clean and clean_input and curr_clean == clean_input:
                matched = True
            elif curr_digits and digits_input and len(curr_digits) >= 4 and curr_digits == digits_input:
                matched = True
            elif input_lower and st_email and input_lower == st_email:
                matched = True
            elif last_n and _clean(last_n) == clean_input:
                matched = True
            elif full_name and _clean(full_name) == clean_input:
                matched = True

            if matched:
                if cid and cid not in enrolled_cids:
                    enrolled_cids.append(cid)
                if not matched_student:
                    prog_year = st.get("program_year") or bp.get("metadata", {}).get("section") or doc.get("section") or "Engineering"
                    matched_student = {
                        "student_id": curr_sid or norm_input,
                        "full_name": full_name,
                        "last_name": last_n,
                        "first_name": first_n,
                        "program_year": prog_year,
                        "email": st.get("email") or f"{curr_sid.lower()}@usep.edu.ph",
                        "enrolled_courses": enrolled_cids,
                    }

    if matched_student:
        matched_student["enrolled_courses"] = enrolled_cids
        return matched_student
    return None


def register_or_update_student(
    student_id: str,
    last_name: str = "",
    first_name: str = "",
    full_name: str = "",
    email: str = "",
    program_year: str = "",
    signature_data: str = "",
    middle_name: str = "",
    course_id: str = "",
    password: str = "",
) -> Dict[str, Any]:
    """Registers or updates a student profile in data/students.json and SQLite app_students."""
    sid = normalize_student_id(student_id)
    if not sid:
        return {}

    if not full_name:
        if first_name and last_name:
            full_name = f"{last_name}, {first_name}".strip()
        elif last_name:
            full_name = last_name
        else:
            full_name = sid
    if not last_name and full_name:
        parts = [p.strip() for p in full_name.split(",", 1)]
        last_name = parts[0] if parts else full_name

    with _lock:
        students = _load_students()
        st = students.get(sid, {})
        st.update({
            "student_id": sid,
            "username": st.get("username") or sid,
            "full_name": full_name or st.get("full_name") or sid,
            "last_name": last_name or st.get("last_name") or "",
            "first_name": first_name or st.get("first_name") or "",
            "middle_name": middle_name or st.get("middle_name") or "",
            "program_year": program_year or st.get("program_year") or "",
            "email": email or st.get("email") or f"{sid.lower()}@usep.edu.ph",
            "status": "active",
            "is_active": 1,
        })
        if password:
            st["password_hash"] = generate_password_hash(password)
        elif not st.get("password_hash"):
            st["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)

        if signature_data:
            st["signature_data"] = signature_data
        if "created_at" not in st:
            st["created_at"] = datetime.now().isoformat(timespec="seconds")

        enrolled = st.get("enrolled_courses") or []
        if course_id and course_id not in enrolled:
            enrolled.append(course_id)
        st["enrolled_courses"] = enrolled

        students[sid] = st
        _save_students(students)
        return st


def get_or_register_student(student_id: str, last_name_guess: str = "") -> Optional[Dict[str, Any]]:
    """
    Retrieves student from data/students.json / SQLite or auto-registers from course rosters.
    """
    raw_input = (student_id or "").strip()
    if not raw_input:
        return None
    norm_sid = normalize_student_id(raw_input)
    clean_input = _clean(norm_sid)
    digits_input = re.sub(r"\D", "", norm_sid)
    input_lower = raw_input.lower()

    with _lock:
        students = _load_students()
        # Direct lookup by ID
        if norm_sid in students:
            return students[norm_sid]
        if raw_input in students:
            return students[raw_input]

        # Search by digits, clean, email, username, or name in existing students
        for sid, st in students.items():
            s_norm = normalize_student_id(sid)
            s_clean = _clean(sid)
            s_digits = re.sub(r"\D", "", sid)
            st_email = str(st.get("email") or "").strip().lower()
            st_user = str(st.get("username") or "").strip().lower()

            if s_norm.lower() == norm_sid.lower():
                return st
            if s_digits and digits_input and len(s_digits) >= 4 and s_digits == digits_input:
                return st
            if input_lower and (input_lower == st_email or input_lower == st_user):
                return st
            if (st.get("last_name") and _clean(st["last_name"]) == clean_input) or \
               (st.get("full_name") and _clean(st["full_name"]) == clean_input):
                return st

        # Not yet in store: Search across ALL course rosters (SQLite + JSON)
        roster_st = find_student_in_course_rosters(raw_input)
        if not roster_st:
            return None

        actual_sid = roster_st["student_id"]
        if actual_sid in students:
            return students[actual_sid]

        new_st = {
            "student_id": actual_sid,
            "username": actual_sid,
            "full_name": roster_st["full_name"],
            "last_name": roster_st["last_name"] or last_name_guess.strip(),
            "first_name": roster_st["first_name"],
            "program_year": roster_st["program_year"],
            "email": roster_st["email"],
            "status": "active",
            "is_active": 1,
            "password_hash": generate_password_hash(DEFAULT_STUDENT_PASSWORD),
            "signature_data": "",
            "enrolled_courses": roster_st.get("enrolled_courses") or [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_login": datetime.now().isoformat(timespec="seconds"),
        }
        students[actual_sid] = new_st
        _save_students(students)
        return new_st


def verify_student_login(student_id: str, secret_or_lastname: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Verifies student credentials with comprehensive normalization:
      - Student ID + Last Name (for easy first-time login)
      - Student ID + Default Password ("student123", "student", etc.)
      - Student ID + Custom Password (stored hash or plain text)
      - Flexible identifier matching: YYYY-NNNNN, YYYYNNNNN, email, or username
      - Unicode & accent resilient (e.g. Añana == Anana)
      - Does not falsely block students whose courses are active or unfinalized
    """
    raw_sid = (student_id or "").strip()
    secret = (secret_or_lastname or "").strip()

    if not raw_sid:
        return False, None, "Please enter your Student ID Number."

    st = get_or_register_student(raw_sid, last_name_guess=secret)
    if not st:
        # One more attempt: try searching with unhyphenated digits or email
        digits = re.sub(r"\D", "", raw_sid)
        if digits and len(digits) >= 4:
            st = get_or_register_student(digits, last_name_guess=secret)

    if not st:
        return (
            False,
            None,
            f"Student ID '{student_id}' was not found in any active course roster. "
            "Please verify your Student ID or check with your instructor.",
        )

    # Check account active status (ensure never falsely locked)
    is_active = st.get("is_active", 1)
    status_str = str(st.get("status", "active")).lower()
    if is_active in (0, False, "0", "false") or status_str in ("inactive", "disabled", "suspended"):
        return False, None, "Your student account is currently deactivated. Please contact your department administrator."

    actual_sid = st["student_id"]
    pw_hash = st.get("password_hash") or ""

    # Case 1: Stored password verification (hashed or legacy plain text)
    if pw_hash and secret:
        try:
            if check_password_hash(pw_hash, secret):
                _record_student_login(actual_sid)
                return True, st, ""
        except Exception:
            pass
        if pw_hash == secret:
            st["password_hash"] = generate_password_hash(secret)
            _save_students({actual_sid: st})
            _record_student_login(actual_sid)
            return True, st, ""

    # Case 2: Blank secret (allowed for initial portal entry if last name/password not required)
    if not secret:
        if not pw_hash:
            st["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
            _save_students({actual_sid: st})
        _record_student_login(actual_sid)
        return True, st, ""

    # Case 3: Default universal passwords
    sec_lower = secret.strip().lower()
    sec_clean = _clean(secret)
    if sec_lower in DEFAULT_PASSWORDS or sec_clean in DEFAULT_PASSWORDS:
        if not pw_hash:
            st["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
            _save_students({actual_sid: st})
        _record_student_login(actual_sid)
        return True, st, ""

    # Case 4: Resilient name / ID matching
    st_last = _clean(st.get("last_name"))
    st_first = _clean(st.get("first_name"))
    full_name_clean = _clean(st.get("full_name"))
    sid_clean = _clean(actual_sid)
    sid_digits = re.sub(r"\D", "", actual_sid)
    sec_digits = re.sub(r"\D", "", secret)

    name_tokens = [w for w in full_name_clean.replace(",", " ").split() if len(w) >= 2]
    is_match = (
        (st_last and sec_clean == st_last)
        or (st_first and sec_clean == st_first)
        or (full_name_clean and sec_clean in full_name_clean)
        or (st_last and sec_clean in full_name_clean)
        or (sec_clean in name_tokens)
        or (sid_clean and sec_clean == sid_clean)
        or (sid_digits and len(sid_digits) >= 4 and sec_digits == sid_digits)
    )

    if is_match:
        if not pw_hash:
            st["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
            _save_students({actual_sid: st})
        _record_student_login(actual_sid)
        return True, st, ""

    # If last name wasn't set on roster, accept secret as last name
    if not st_last and secret:
        with _lock:
            students = _load_students()
            if actual_sid in students:
                students[actual_sid]["last_name"] = secret
                if not students[actual_sid].get("password_hash"):
                    students[actual_sid]["password_hash"] = generate_password_hash(DEFAULT_STUDENT_PASSWORD)
                _save_students(students)
        _record_student_login(actual_sid)
        return True, st, ""

    return (
        False,
        None,
        "Verification failed. Please enter your registered Last Name, Student ID, or default password (student123).",
    )


def _record_student_login(sid: str) -> None:
    with _lock:
        students = _load_students()
        if sid in students:
            students[sid]["last_login"] = datetime.now().isoformat(timespec="seconds")
            _save_students(students)


def save_student_signature(student_id: str, signature_data: str) -> bool:
    """Saves the student's default electronic signature for reuse."""
    sid = _normalize_id(student_id)
    if not sid or not signature_data:
        return False
    with _lock:
        students = _load_students()
        if sid in students:
            students[sid]["signature_data"] = signature_data
            _save_students(students)
            return True
    return False


def get_student_profile(student_id: str) -> Optional[Dict[str, Any]]:
    """Returns student profile details."""
    sid = _normalize_id(student_id)
    students = _load_students()
    return students.get(sid) or find_student_in_course_rosters(sid)


def find_courses_for_student(student_id: str) -> Dict[str, Any]:
    """
    Scans ALL courses (SQLite database and data/courses/ files) to locate all courses where this student is enrolled.
    Categorizes them into:
      - pending: QA approved syllabus, awaiting student signature
      - acknowledged: already signed by student
      - in_review: syllabus currently undergoing committee/QA review
    """
    sid = _normalize_id(student_id)
    sid_lower = sid.lower()

    st_profile = get_student_profile(sid) or {}

    pending_list = []
    acknowledged_list = []
    in_review_list = []

    all_courses = _get_all_courses()
    seen_course_ids = set()

    for doc in all_courses:
        try:
            cid = doc.get("course_id") or doc.get("id")
            if not cid or cid in seen_course_ids:
                continue

            bp = doc.get("blueprint") or {}
            students = bp.get("students") or []

            matched_st = None
            sid_digits_in = re.sub(r"\D", "", sid_lower)
            for st in students:
                curr_sid = normalize_student_id(str(st.get("student_id") or "")).lower()
                curr_digits = re.sub(r"\D", "", curr_sid)
                if curr_sid == sid_lower or (curr_digits and sid_digits_in and len(curr_digits) >= 4 and curr_digits == sid_digits_in):
                    matched_st = st
                    break

            if not matched_st:
                continue

            if not st_profile.get("full_name"):
                st_name = matched_st.get("name") or ""
                if not st_name and (matched_st.get("first_name") or matched_st.get("last_name")):
                    fn = (matched_st.get("first_name") or "").strip()
                    ln = (matched_st.get("last_name") or "").strip()
                    st_name = f"{fn} {ln}".strip() if (fn and ln) else (ln or fn)
                st_profile["student_id"] = sid
                st_profile["full_name"] = st_name or sid
                st_profile["first_name"] = matched_st.get("first_name") or ""
                st_profile["last_name"] = matched_st.get("last_name") or ""
                st_profile["program_year"] = matched_st.get("program_year") or ""
                st_profile["email"] = matched_st.get("email") or f"{sid.lower()}@usep.edu.ph"

            seen_course_ids.add(cid)

            # Check acknowledgment records
            acks = doc.get("student_acknowledgments") or (doc.get("workflow") or {}).get("student_acknowledgments") or (bp.get("student_acknowledgments") if isinstance(bp, dict) else None) or []
            ack_record = None
            for a in acks:
                if str(a.get("student_id") or "").strip().lower() == sid_lower:
                    ack_record = a
                    break

            if ack_record is None and st_profile:
                st_syl_acks = st_profile.get("syllabus_acknowledgments") or {}
                if cid in st_syl_acks:
                    ack_record = st_syl_acks[cid]

            wf = doc.get("workflow") or {}
            status = wf.get("status") or "draft"
            # QA approved check (Counter-signed by QA, awaiting student ack or Dean approval)
            is_qa_approved = (
                status.lower() in {"for_student_acknowledgment", "for_dean_approval", "approved"}
                or wf.get("step") == 5
                or wf.get("qa_approved_at") is not None
                or any(s.get("step") == "qa_head" for s in wf.get("signatures", []))
            )

            meta = bp.get("metadata") or {}
            sem_ay_raw = doc.get("semester_ay") or meta.get("semester_ay") or ""
            import courses_store
            school_year, semester, group_label = courses_store.parse_semester_ay(sem_ay_raw)

            status_category = "acknowledged" if ack_record is not None else ("pending" if is_qa_approved else "in_review")

            course_item = {
                "course_id": cid,
                "course_code": doc.get("course_code") or meta.get("course_code") or "Course",
                "course_title": doc.get("course_title") or meta.get("course_title") or "Untitled",
                "credit_units": doc.get("credit_units") or meta.get("credit_units") or "3 Units",
                "section": doc.get("section") or meta.get("section") or "",
                "semester_ay": sem_ay_raw,
                "school_year": school_year,
                "semester": semester,
                "group_label": group_label,
                "faculty_name": doc.get("faculty_name") or meta.get("faculty_name") or "Faculty Instructor",
                "schedule": doc.get("class_schedule") or meta.get("class_schedule") or "TBA",
                "course_description": doc.get("course_description") or meta.get("course_description") or "",
                "workflow_status": status,
                "is_qa_approved": is_qa_approved,
                "has_acknowledged": ack_record is not None,
                "acknowledged_at": ack_record.get("acknowledged_at") if ack_record else None,
                "signature_data": ack_record.get("signature_data") if ack_record else None,
                "comment": ack_record.get("comment", "") if ack_record else "",
                "total_enrolled": len(students),
                "total_acknowledged": len(acks),
                "status_category": status_category,
            }

            if ack_record is not None:
                acknowledged_list.append(course_item)
            elif is_qa_approved:
                pending_list.append(course_item)
            else:
                in_review_list.append(course_item)

        except Exception:
            continue

    # Sort each list alphabetically by course code
    pending_list.sort(key=lambda c: c.get("course_code") or "")
    acknowledged_list.sort(key=lambda c: c.get("course_code") or "")
    in_review_list.sort(key=lambda c: c.get("course_code") or "")

    # Group all enrolled courses by School Year and Semester
    # Order: School Year descending, then 1st Sem -> 2nd Sem -> Summer
    import courses_store
    sem_rank = {"1st Semester": 1, "2nd Semester": 2, "3rd Trimester": 3, "Summer / Midyear": 4}

    def _group_sort_key(g_item):
        grp_label = g_item[0]
        sy, sem, _ = courses_store.parse_semester_ay(grp_label.replace(" • ", ", "))
        m_yr = re.search(r"(\d{4})", sy)
        yr_val = int(m_yr.group(1)) if m_yr else 2026
        rank = sem_rank.get(sem, 5)
        return (-yr_val, rank)

    all_enrolled_courses = pending_list + acknowledged_list + in_review_list
    grouped_dict: Dict[str, List[Dict[str, Any]]] = {}
    for c in all_enrolled_courses:
        grp = c["group_label"]
        grouped_dict.setdefault(grp, []).append(c)

    sorted_groups = sorted(grouped_dict.items(), key=_group_sort_key)
    groups = []
    for grp_label, c_list in sorted_groups:
        sy, sem, _ = courses_store.parse_semester_ay(grp_label.replace(" • ", ", "))
        c_list.sort(key=lambda c: c.get("course_code") or "")
        g_pending = [c for c in c_list if c["status_category"] == "pending"]
        g_ack = [c for c in c_list if c["status_category"] == "acknowledged"]
        g_review = [c for c in c_list if c["status_category"] == "in_review"]

        total_units = 0.0
        for c in c_list:
            u_match = re.search(r"(\d+(\.\d+)?)", str(c.get("credit_units", "")))
            if u_match:
                try:
                    total_units += float(u_match.group(1))
                except Exception:
                    pass

        groups.append({
            "group_label": grp_label,
            "school_year": sy,
            "semester": sem,
            "courses": c_list,
            "pending": g_pending,
            "acknowledged": g_ack,
            "in_review": g_review,
            "total_courses": len(c_list),
            "total_units": int(total_units) if total_units.is_integer() else total_units,
        })

    return {
        "student": st_profile,
        "pending": pending_list,
        "acknowledged": acknowledged_list,
        "in_review": in_review_list,
        "groups": groups,
        "terms": [g["group_label"] for g in groups],
        "stats": {
            "total": len(all_enrolled_courses),
            "pending_count": len(pending_list),
            "acknowledged_count": len(acknowledged_list),
            "in_review_count": len(in_review_list),
            "terms_count": len(groups),
        },
    }


def record_student_acknowledgment(
    student_id: str,
    course_id: str,
    signature_data: str,
    student_name: str = "",
    ip_address: str = "",
    comment: str = "",
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Submits a student's electronic signature and timestamp for a course syllabus acknowledgment.
    """
    import courses_store

    sid = _normalize_id(student_id)
    if not sid:
        return False, "Student ID is required.", {}
    if not signature_data:
        return False, "Electronic signature is required.", {}

    doc = courses_store.find_course(course_id)
    if not doc:
        return False, f"Course '{course_id}' was not found.", {}

    wf = doc.get("workflow") or {}
    status = wf.get("status") or "draft"
    is_qa_approved = (
        status.lower() in {"for_student_acknowledgment", "for_dean_approval", "approved"}
        or wf.get("step") in (5, 6, 7)
        or wf.get("qa_approved_at") is not None
        or any(s.get("step") == "qa_head" for s in wf.get("signatures", []))
    )

    if not is_qa_approved:
        return (
            False,
            "This syllabus is currently undergoing review and has not yet received official QA counter-signature approval. "
            "Acknowledgment will be available as soon as the QA counter-signs.",
            {},
        )

    st_profile = get_student_profile(sid) or {}
    s_name = student_name or st_profile.get("full_name") or sid
    email = st_profile.get("email") or f"{sid}@usep.edu.ph"

    now_ts = datetime.now().isoformat(timespec="seconds")
    now_date = datetime.now().strftime("%B %d, %Y")

    new_ack = {
        "student_id": sid,
        "student_name": s_name,
        "email": email,
        "signature_data": signature_data,
        "acknowledged_at": now_ts,
        "date": now_date,
        "ip_address": ip_address,
        "comment": (comment or "").strip(),
    }

    acks = doc.get("student_acknowledgments") or wf.get("student_acknowledgments") or []
    updated = False
    for idx, a in enumerate(acks):
        if str(a.get("student_id") or "").strip().lower() == sid.lower():
            acks[idx] = new_ack
            updated = True
            break
    if not updated:
        acks.append(new_ack)

    doc["student_acknowledgments"] = acks
    if "workflow" in doc and isinstance(doc["workflow"], dict):
        doc["workflow"]["student_acknowledgments"] = acks
    bp = doc.get("blueprint")
    if isinstance(bp, dict):
        bp["student_acknowledgments"] = acks

    import syllabus_workflow
    stats = syllabus_workflow.get_student_acknowledgment_stats(doc)
    wf_status = (wf.get("status") or "").lower()
    msg_suffix = ""
    if wf_status == "for_student_acknowledgment" and stats.get("meets_threshold"):
        wf["status"] = "for_dean_approval"
        wf["status_label"] = syllabus_workflow.STATUS_LABELS["for_dean_approval"]
        wf["step_entered_at"] = now_ts
        wf["auto_endorsed_to_dean"] = True
        wf.setdefault("history", []).append({
            "action": "student_ack_threshold_met",
            "step": "student_ack",
            "at": now_ts,
            "by": "system",
            "remarks": f"Student acknowledgment threshold reached ({stats['total_acknowledged']}/{stats['total_students']} signed, {stats['percentage']}%). Automatically endorsed to Dean for approval.",
        })
        msg_suffix = " 80% threshold reached: Automatically endorsed to Dean for approval!"

    courses_store.save_course_doc(doc)

    # Persist directly into student's profile and database
    try:
        all_sts = _load_students()
        st_entry = all_sts.get(sid)
        if not st_entry:
            for k, v in all_sts.items():
                if _normalize_id(k) == sid or str(v.get("student_id") or "").lower() == sid.lower():
                    st_entry = v
                    break
        if st_entry:
            syl_acks = st_entry.setdefault("syllabus_acknowledgments", {})
            syl_acks[course_id] = new_ack
            if signature_data:
                st_entry["signature_data"] = signature_data
                st_entry["signature_updated_at"] = now_ts
            _save_students(all_sts)
        elif signature_data and not st_profile.get("signature_data"):
            save_student_signature(sid, signature_data)
    except Exception as _e:
        logger.debug("Error saving acknowledgment to student store: %s", _e)

    return True, f"Syllabus acknowledgment successfully recorded for {s_name}! {msg_suffix}".strip(), new_ack


# Automatically sync students from existing course rosters on import
sync_all_course_students_to_store()
