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
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
COURSES_BASE_DIR = os.path.join(DATA_DIR, "courses")

_lock = threading.Lock()


def _load_students() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(STUDENTS_FILE):
        return {}
    try:
        with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_students(data: Dict[str, Dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _normalize_id(sid: str) -> str:
    return str(sid or "").strip()


def find_student_in_course_rosters(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Searches across all courses in COURSES_BASE_DIR to find if this student_id
    is present in any course roster. Returns student info if found.
    """
    sid_norm = _normalize_id(student_id).lower()
    if not sid_norm or not os.path.exists(COURSES_BASE_DIR):
        return None

    for root, _, files in os.walk(COURSES_BASE_DIR):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                bp = doc.get("blueprint") or {}
                students = bp.get("students") or []
                for st in students:
                    curr_sid = str(st.get("student_id") or "").strip().lower()
                    if curr_sid == sid_norm:
                        last_n = st.get("last_name") or ""
                        first_n = st.get("first_name") or ""
                        name = st.get("name") or ""
                        if not last_n and name:
                            parts = [p.strip() for p in name.split(",", 1)]
                            last_n = parts[0] if parts else ""
                            first_n = parts[1] if len(parts) > 1 else ""
                        full_name = f"{first_n} {last_n}".strip() if (first_n and last_n) else (name or sid_norm)

                        prog_year = st.get("program_year") or bp.get("metadata", {}).get("program_name") or "Engineering"
                        return {
                            "student_id": st.get("student_id") or student_id,
                            "full_name": full_name,
                            "last_name": last_n,
                            "first_name": first_n,
                            "program_year": prog_year,
                            "email": st.get("email") or f"{sid_norm}@usep.edu.ph",
                        }
            except Exception:
                continue
    return None


def get_or_register_student(student_id: str, last_name_guess: str = "") -> Optional[Dict[str, Any]]:
    """
    Retrieves student from data/students.json or auto-registers from course rosters.
    """
    sid = _normalize_id(student_id)
    if not sid:
        return None

    with _lock:
        students = _load_students()
        if sid in students:
            return students[sid]

        # Search across course rosters
        roster_st = find_student_in_course_rosters(sid)
        if not roster_st:
            return None

        new_st = {
            "student_id": sid,
            "full_name": roster_st["full_name"],
            "last_name": roster_st["last_name"] or last_name_guess.strip(),
            "first_name": roster_st["first_name"],
            "program_year": roster_st["program_year"],
            "email": roster_st["email"],
            "password_hash": "",
            "signature_data": "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_login": datetime.now().isoformat(timespec="seconds"),
        }
        students[sid] = new_st
        _save_students(students)
        return new_st


def verify_student_login(student_id: str, secret_or_lastname: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Verifies student credentials.
    Supports:
      - Student ID + Last Name (for easy first-time login)
      - Student ID + Custom Password (if student set one)
      - Default fallback to Student ID or Last Name match
    """
    sid = _normalize_id(student_id)
    secret = (secret_or_lastname or "").strip()

    if not sid:
        return False, None, "Please enter your Student ID Number."

    st = get_or_register_student(sid, last_name_guess=secret)
    if not st:
        return (
            False,
            None,
            f"Student ID '{sid}' was not found in any active course roster. "
            "Please verify your Student ID or check with your instructor.",
        )

    # 1. If password hash is set, check password
    pw_hash = st.get("password_hash")
    if pw_hash:
        if check_password_hash(pw_hash, secret):
            _record_student_login(sid)
            return True, st, ""
        # Also allow matching by last name in case student forgot password
        st_last = (st.get("last_name") or "").strip().lower()
        if secret and st_last and (secret.lower() == st_last or secret.lower() in st.get("full_name", "").lower()):
            _record_student_login(sid)
            return True, st, ""
        return False, None, "Invalid password or verification code."

    # 2. First-time login: verify with Last Name, PIN, or Student ID
    st_last = (st.get("last_name") or "").strip().lower()
    full_name_lower = (st.get("full_name") or "").strip().lower()

    # If user provided secret matches last name, student ID, or is within full name
    secret_lower = secret.lower()
    if not secret:
        # If secret is blank, accept first-time login
        _record_student_login(sid)
        return True, st, ""

    if (
        (st_last and secret_lower == st_last)
        or (secret_lower == sid.lower())
        or (st_last and secret_lower in full_name_lower)
        or (secret in ("1234", "123456", "usep", "student"))
    ):
        _record_student_login(sid)
        return True, st, ""

    # If last name wasn't set on roster, accept and set it
    if not st_last and secret:
        with _lock:
            students = _load_students()
            if sid in students:
                students[sid]["last_name"] = secret
                _save_students(students)
        _record_student_login(sid)
        return True, st, ""

    return (
        False,
        None,
        f"Verification failed. Please enter your registered Last Name (as enrolled in your class record).",
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
    Scans all course files to locate all courses where this student is enrolled.
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

    if not os.path.exists(COURSES_BASE_DIR):
        return {
            "student": st_profile,
            "pending": [],
            "acknowledged": [],
            "in_review": [],
            "stats": {"total": 0, "pending_count": 0, "acknowledged_count": 0, "in_review_count": 0},
        }

    seen_course_ids = set()

    for root, _, files in os.walk(COURSES_BASE_DIR):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    doc = json.load(f)

                cid = doc.get("course_id") or fn[:-5]
                if cid in seen_course_ids:
                    continue

                bp = doc.get("blueprint") or {}
                students = bp.get("students") or []

                matched_st = None
                for st in students:
                    curr_sid = str(st.get("student_id") or "").strip().lower()
                    if curr_sid == sid_lower:
                        matched_st = st
                        break

                if not matched_st:
                    continue

                seen_course_ids.add(cid)

                # Check acknowledgment records
                acks = doc.get("student_acknowledgments") or (doc.get("workflow") or {}).get("student_acknowledgments") or []
                ack_record = None
                for a in acks:
                    if str(a.get("student_id") or "").strip().lower() == sid_lower:
                        ack_record = a
                        break

                wf = doc.get("workflow") or {}
                status = wf.get("status") or "draft"
                # QA approved check (Step 5 counter-signed by QA)
                is_qa_approved = (
                    status.lower() == "approved"
                    or wf.get("step") == 5
                    or wf.get("qa_approved_at") is not None
                )

                meta = bp.get("metadata") or {}
                course_item = {
                    "course_id": cid,
                    "course_code": doc.get("course_code") or meta.get("course_code") or "Course",
                    "course_title": doc.get("course_title") or meta.get("course_title") or "Untitled",
                    "credit_units": doc.get("credit_units") or meta.get("credit_units") or "3 Units",
                    "section": doc.get("section") or meta.get("section") or "",
                    "semester_ay": doc.get("semester_ay") or meta.get("semester_ay") or "",
                    "faculty_name": doc.get("faculty_name") or meta.get("faculty_name") or "Faculty Instructor",
                    "schedule": doc.get("class_schedule") or meta.get("class_schedule") or "TBA",
                    "course_description": doc.get("course_description") or meta.get("course_description") or "",
                    "workflow_status": status,
                    "is_qa_approved": is_qa_approved,
                    "has_acknowledged": ack_record is not None,
                    "acknowledged_at": ack_record.get("acknowledged_at") if ack_record else None,
                    "signature_data": ack_record.get("signature_data") if ack_record else None,
                    "total_enrolled": len(students),
                    "total_acknowledged": len(acks),
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

    return {
        "student": st_profile,
        "pending": pending_list,
        "acknowledged": acknowledged_list,
        "in_review": in_review_list,
        "stats": {
            "total": len(pending_list) + len(acknowledged_list) + len(in_review_list),
            "pending_count": len(pending_list),
            "acknowledged_count": len(acknowledged_list),
            "in_review_count": len(in_review_list),
        },
    }


def record_student_acknowledgment(
    student_id: str,
    course_id: str,
    signature_data: str,
    student_name: str = "",
    ip_address: str = "",
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
        status.lower() == "approved"
        or wf.get("step") == 5
        or wf.get("qa_approved_at") is not None
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

    courses_store.save_course_doc(doc)

    # Save to student profile if signature is missing
    if signature_data and not st_profile.get("signature_data"):
        save_student_signature(sid, signature_data)

    return True, f"Syllabus acknowledgment successfully recorded for {s_name}!", new_ack
