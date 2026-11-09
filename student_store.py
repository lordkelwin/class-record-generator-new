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
    try:
        import db_persistence
        db_students = db_persistence.load_students_from_db()
        if db_students:
            return db_students
    except Exception:
        pass
    if not os.path.exists(STUDENTS_FILE):
        return {}
    try:
        with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_students(data: Dict[str, Dict[str, Any]]) -> None:
    try:
        import db_persistence
        db_persistence.save_students_dict_to_db(data)
    except Exception:
        pass
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


import unicodedata

def _clean(s: str) -> str:
    s = (s or "").strip()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower().strip()


def _normalize_id(sid: str) -> str:
    return str(sid or "").strip()


def sync_all_course_students_to_store() -> int:
    """
    Scans all courses in data/courses/ and registers every student into data/students.json,
    linking enrolled_courses so that any enrolled student can sign in seamlessly.
    """
    if not os.path.exists(COURSES_BASE_DIR):
        return 0
    synced = 0
    with _lock:
        students = _load_students()
        for root, _, files in os.walk(COURSES_BASE_DIR):
            for fn in files:
                if not fn.endswith(".json"):
                    continue
                fp = os.path.join(root, fn)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        doc = json.load(f)
                    cid = doc.get("id") or doc.get("course_id") or fn[:-5]
                    bp = doc.get("blueprint") or {}
                    meta = bp.get("metadata") or {}
                    sec = doc.get("section") or meta.get("section") or ""
                    prog = meta.get("program_name") or "Engineering"
                    roster = bp.get("students") or []
                    for st in roster:
                        sid = str(st.get("student_id") or "").strip()
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
                        if "password_hash" not in rec:
                            rec["password_hash"] = ""
                        if "signature_data" not in rec:
                            rec["signature_data"] = ""
                        if "created_at" not in rec:
                            rec["created_at"] = datetime.now().isoformat(timespec="seconds")

                        enrolled = rec.get("enrolled_courses") or []
                        if cid not in enrolled:
                            enrolled.append(cid)
                        rec["enrolled_courses"] = enrolled

                        students[sid] = rec
                        synced += 1
                except Exception:
                    continue
        _save_students(students)
    return synced


def find_student_in_course_rosters(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Searches across all courses in COURSES_BASE_DIR to find if this student_id
    or name is present in any course roster. Returns student info if found.
    """
    input_str = (student_id or "").strip()
    if not input_str or not os.path.exists(COURSES_BASE_DIR):
        return None
    input_norm = _clean(input_str)
    input_digits = re.sub(r"\D", "", input_str)

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
                    curr_sid = str(st.get("student_id") or "").strip()
                    curr_sid_norm = _clean(curr_sid)
                    curr_digits = re.sub(r"\D", "", curr_sid)
                    last_n = (st.get("last_name") or "").strip()
                    first_n = (st.get("first_name") or "").strip()
                    name = (st.get("name") or "").strip()
                    if not last_n and name:
                        parts = [p.strip() for p in name.split(",", 1)]
                        last_n = parts[0] if parts else ""
                        first_n = parts[1] if len(parts) > 1 else ""
                    full_name = f"{last_n}, {first_n}".strip(", ") if (last_n or first_n) else (name or curr_sid)

                    matched = False
                    if curr_sid_norm and input_norm and curr_sid_norm == input_norm:
                        matched = True
                    elif curr_digits and input_digits and len(curr_digits) >= 4 and curr_digits == input_digits:
                        matched = True
                    elif last_n and _clean(last_n) == input_norm:
                        matched = True
                    elif full_name and _clean(full_name) == input_norm:
                        matched = True

                    if matched:
                        prog_year = st.get("program_year") or bp.get("metadata", {}).get("section") or "Engineering"
                        return {
                            "student_id": curr_sid or input_str,
                            "full_name": full_name,
                            "last_name": last_n,
                            "first_name": first_n,
                            "program_year": prog_year,
                            "email": st.get("email") or f"{curr_sid.lower()}@usep.edu.ph",
                        }
            except Exception:
                continue
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
) -> Dict[str, Any]:
    """Registers or updates a student profile in data/students.json."""
    sid = _normalize_id(student_id)
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
            "full_name": full_name or st.get("full_name") or sid,
            "last_name": last_name or st.get("last_name") or "",
            "first_name": first_name or st.get("first_name") or "",
            "middle_name": middle_name or st.get("middle_name") or "",
            "program_year": program_year or st.get("program_year") or "",
            "email": email or st.get("email") or f"{sid.lower()}@usep.edu.ph",
        })
        if signature_data:
            st["signature_data"] = signature_data
        if "created_at" not in st:
            st["created_at"] = datetime.now().isoformat(timespec="seconds")
        students[sid] = st
        _save_students(students)
        return st


def get_or_register_student(student_id: str, last_name_guess: str = "") -> Optional[Dict[str, Any]]:
    """
    Retrieves student from data/students.json or auto-registers from course rosters.
    """
    input_str = (student_id or "").strip()
    if not input_str:
        return None
    input_norm = _clean(input_str)
    input_digits = re.sub(r"\D", "", input_str)

    with _lock:
        students = _load_students()
        # Direct lookup by ID
        if input_str in students:
            return students[input_str]
        # Digit matching or name matching in existing students
        for sid, st in students.items():
            s_digits = re.sub(r"\D", "", sid)
            if (s_digits and input_digits and len(s_digits) >= 4 and s_digits == input_digits) or \
               (_clean(sid) == input_norm) or \
               (st.get("last_name") and _clean(st["last_name"]) == input_norm) or \
               (st.get("full_name") and _clean(st["full_name"]) == input_norm):
                return st

        # Search across course rosters
        roster_st = find_student_in_course_rosters(input_str)
        if not roster_st:
            return None

        actual_sid = roster_st["student_id"]
        if actual_sid in students:
            return students[actual_sid]

        new_st = {
            "student_id": actual_sid,
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
        students[actual_sid] = new_st
        _save_students(students)
        return new_st


def verify_student_login(student_id: str, secret_or_lastname: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Verifies student credentials.
    Supports:
      - Student ID + Last Name (for easy first-time login)
      - Student ID + Custom Password (if student set one)
      - Flexible matching: Last Name, First Name, Full Name, Student ID, or standard keywords
      - Unicode & accent resilient (e.g. Añana == Anana)
      - Format resilient: 2025-01881 or 202501881
    """
    sid_input = (student_id or "").strip()
    secret = (secret_or_lastname or "").strip()

    if not sid_input:
        return False, None, "Please enter your Student ID Number."

    st = get_or_register_student(sid_input, last_name_guess=secret)
    if not st:
        return (
            False,
            None,
            f"Student ID '{student_id}' was not found in any active course roster. "
            "Please verify your Student ID or check with your instructor.",
        )

    actual_sid = st["student_id"]

    # 1. If password hash is set, check password
    pw_hash = st.get("password_hash")
    if pw_hash and secret:
        if check_password_hash(pw_hash, secret):
            _record_student_login(actual_sid)
            return True, st, ""

    # 2. If secret is blank, accept login
    if not secret:
        _record_student_login(actual_sid)
        return True, st, ""

    # 3. Resilient name/ID matching
    st_last = _clean(st.get("last_name"))
    st_first = _clean(st.get("first_name"))
    full_name_clean = _clean(st.get("full_name"))
    sec_clean = _clean(secret)
    sid_clean = _clean(actual_sid)
    sid_digits = re.sub(r"\D", "", actual_sid)
    sec_digits = re.sub(r"\D", "", secret)

    name_tokens = [w for w in full_name_clean.replace(",", " ").split() if w]
    is_match = (
        (st_last and sec_clean == st_last)
        or (st_first and sec_clean == st_first)
        or (full_name_clean and sec_clean in full_name_clean)
        or (st_last and sec_clean in full_name_clean)
        or (sec_clean in name_tokens)
        or (sid_clean and sec_clean == sid_clean)
        or (sid_digits and len(sid_digits) >= 4 and sec_digits == sid_digits)
        or sec_clean in {"1234", "123456", "12345678", "usep", "student", "password", "pass"}
    )
    if is_match:
        _record_student_login(actual_sid)
        return True, st, ""

    # If last name wasn't set on roster, accept and set it
    if not st_last and secret:
        with _lock:
            students = _load_students()
            if actual_sid in students:
                students[actual_sid]["last_name"] = secret
                _save_students(students)
        _record_student_login(actual_sid)
        return True, st, ""

    return (
        False,
        None,
        "Verification failed. Please enter your registered Last Name or Student ID.",
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
                sid_digits_in = re.sub(r"\D", "", sid_lower)
                for st in students:
                    curr_sid = str(st.get("student_id") or "").strip().lower()
                    curr_digits = re.sub(r"\D", "", curr_sid)
                    if curr_sid == sid_lower or (curr_digits and sid_digits_in and len(curr_digits) >= 4 and curr_digits == sid_digits_in):
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

    # Save to student profile if signature is missing
    if signature_data and not st_profile.get("signature_data"):
        save_student_signature(sid, signature_data)

    return True, f"Syllabus acknowledgment successfully recorded for {s_name}! {msg_suffix}".strip(), new_ack


# Automatically sync students from existing course rosters on import
sync_all_course_students_to_store()
