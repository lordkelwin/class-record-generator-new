import syllabus_workflow
import class_record_workflow
"""
Course and Subject Store for USeP OBE Syllabus Creator & Class Record Generator.

Accommodates multiple subjects per faculty, organized hierarchically by
School Year and Semester (e.g. A.Y. 2026-2027 • 1st Semester).

Stores courses as JSON files under data/courses/{username}/{course_id}.json
"""
import copy
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models import CourseMetadata, SyllabusBlueprint
from sample_syllabus import get_default_blueprint, get_blank_blueprint, build_learning_plan_from_topics
from catalog_data import get_full_catalog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COURSES_BASE_DIR = os.path.join(DATA_DIR, "courses")


def _get_user_courses_dir(username: str) -> str:
    safe_user = re.sub(r"[^A-Za-z0-9_.-]+", "_", (username or "default").strip().lower())
    user_dir = os.path.join(COURSES_BASE_DIR, safe_user)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def parse_semester_ay(semester_ay_str: str) -> Tuple[str, str, str]:
    """
    Parses strings like:
      - '1st Semester, A.Y. 2026-2027'
      - '2nd Sem AY 2025-2026'
      - 'Summer, A.Y. 2026-2027'
      - 'A.Y. 2026-2027 1st Semester'
    Returns: (school_year, semester, group_label)
    e.g. ('A.Y. 2026-2027', '1st Semester', 'A.Y. 2026-2027 • 1st Semester')
    """
    text = (semester_ay_str or "").strip()
    if not text:
        return ("A.Y. 2026-2027", "1st Semester", "A.Y. 2026-2027 • 1st Semester")

    # Extract Year: 2026-2027, 2025-2026, 2026/2027, etc.
    m_year = re.search(r"(\d{4}\s*[-–/]\s*\d{4})", text)
    if m_year:
        raw_yr = re.sub(r"\s+", "", m_year.group(1)).replace("–", "-").replace("/", "-")
        school_year = f"A.Y. {raw_yr}"
    else:
        # Single 4-digit year fallback
        m_single = re.search(r"\b(20\d\d)\b", text)
        if m_single:
            yr1 = int(m_single.group(1))
            school_year = f"A.Y. {yr1}-{yr1+1}"
        else:
            school_year = "A.Y. 2026-2027"

    # Extract Semester
    lower = text.lower()
    if "1st" in lower or "first" in lower or "1" in lower and "sem" in lower:
        semester = "1st Semester"
    elif "2nd" in lower or "second" in lower or "2" in lower and "sem" in lower:
        semester = "2nd Semester"
    elif "3rd" in lower or "third" in lower:
        semester = "3rd Trimester"
    elif "summer" in lower or "midyear" in lower or "mid-year" in lower:
        semester = "Summer / Midyear"
    else:
        semester = "1st Semester"

    group_label = f"{school_year} • {semester}"
    return (school_year, semester, group_label)


def _summary_from_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    bp_dict = doc.get("blueprint", {})
    meta = bp_dict.get("metadata", {})
    sem_ay = meta.get("semester_ay") or doc.get("semester_ay") or "1st Semester, A.Y. 2026-2027"
    sy, sem, grp = parse_semester_ay(sem_ay)

    students = bp_dict.get("students", [])
    categories = bp_dict.get("categories", [])
    clos = bp_dict.get("course_outcomes", [])

    programs = meta.get("programs") or ([p.strip() for p in (meta.get("program_code") or "EE").split(",") if p.strip()] or ["EE"])
    sections = meta.get("sections") or ([s.strip() for s in (meta.get("section") or doc.get("section") or "1A").split(",") if s.strip()] or ["1A"])
    program_names = meta.get("program_names") or ([meta.get("program_name")] if meta.get("program_name") else ["Bachelor of Science in Electrical Engineering"])

    return {
        "id": doc.get("id"),
        "owner": doc.get("owner"),
        "course_code": (meta.get("course_code") or doc.get("course_code") or "New Course").strip(),
        "course_title": (meta.get("course_title") or doc.get("course_title") or "Untitled Subject").strip(),
        "section": (meta.get("section") or doc.get("section") or "1A").strip(),
        "sections": sections,
        "program_code": (meta.get("program_code") or doc.get("program_code") or "EE").strip(),
        "programs": programs,
        "program_name": meta.get("program_name") or "",
        "program_names": program_names,
        "semester_ay": sem_ay,
        "school_year": sy,
        "semester": sem,
        "group_label": grp,
        "credit_units": meta.get("credit_units") or "3.0 Units",
        "lec_lab": meta.get("lec_lab") or "Lecture",
        "schedule": meta.get("schedule") or "",
        "room": meta.get("room") or "",
        "student_count": len(students),
        "assessment_count": sum(len(c.get("items", [])) for c in categories),
        "clo_count": len(clos),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "workflow_status": (doc.get("workflow") or {}).get("status", "draft"),
        "is_approved": (doc.get("workflow") or {}).get("status") == "approved",
        "is_locked": (doc.get("workflow") or {}).get("status") not in {"draft", "returned"},
        "signatures_count": len((doc.get("workflow") or {}).get("signatures", [])),
    }


def ensure_user_has_default_course(username: str, faculty_name: str = "") -> Dict[str, Any]:
    """Ensures that the user has at least one course (seeds default EE 211 if none)."""
    user_dir = _get_user_courses_dir(username)
    files = [f for f in os.listdir(user_dir) if f.endswith(".json")]
    if files:
        # Load the most recently modified course
        files.sort(key=lambda fn: os.path.getmtime(os.path.join(user_dir, fn)), reverse=True)
        return get_course(username, files[0][:-5])

    # Seed default blueprint
    bp = get_default_blueprint(include_sample_scores=True)
    if faculty_name:
        bp.metadata.faculty_name = faculty_name

    now_iso = datetime.now().isoformat(timespec="seconds")
    course_id = f"c_{uuid.uuid4().hex[:10]}"
    doc = {
        "id": course_id,
        "owner": username,
        "created_at": now_iso,
        "updated_at": now_iso,
        "course_code": bp.metadata.course_code,
        "course_title": bp.metadata.course_title,
        "section": bp.metadata.section,
        "semester_ay": bp.metadata.semester_ay,
        "blueprint": bp.to_dict(),
        "workflow": syllabus_workflow.default_workflow(),
        "class_record_workflow": class_record_workflow.default_class_record_workflow(username),
    }
    filepath = os.path.join(user_dir, f"{course_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)

    return doc


def list_courses(username: str, faculty_name: str = "") -> Dict[str, Any]:
    """
    Returns:
      {
        "courses": [ summary1, summary2, ... ],
        "groups": [
          { "group_label": "...", "school_year": "...", "semester": "...", "courses": [ ... ] }
        ],
        "total": int
      }
    """
    user_dir = _get_user_courses_dir(username)
    files = [f for f in os.listdir(user_dir) if f.endswith(".json")]
    if not files:
        return {"courses": [], "groups": [], "total": 0}


    courses_list: List[Dict[str, Any]] = []
    for fn in files:
        fp = os.path.join(user_dir, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                doc = json.load(f)
                courses_list.append(_summary_from_doc(doc))
        except Exception as e:
            continue

    # Sort courses by updated_at descending
    courses_list.sort(key=lambda c: c.get("updated_at") or "", reverse=True)

    # Group by School Year and Semester
    # Order: School Year descending, then 1st Sem -> 2nd Sem -> Summer
    sem_rank = {"1st Semester": 1, "2nd Semester": 2, "3rd Trimester": 3, "Summer / Midyear": 4}

    def _group_sort_key(g_item: Tuple[str, List[Dict[str, Any]]]):
        grp_label = g_item[0]
        sy, sem, _ = parse_semester_ay(grp_label.replace(" • ", ", "))
        m_yr = re.search(r"(\d{4})", sy)
        yr_val = int(m_yr.group(1)) if m_yr else 2026
        rank = sem_rank.get(sem, 5)
        return (-yr_val, rank)

    grouped_dict: Dict[str, List[Dict[str, Any]]] = {}
    for c in courses_list:
        grp = c["group_label"]
        grouped_dict.setdefault(grp, []).append(c)

    sorted_groups = sorted(grouped_dict.items(), key=_group_sort_key)
    groups = []
    for grp_label, c_list in sorted_groups:
        sy, sem, _ = parse_semester_ay(grp_label.replace(" • ", ", "))
        groups.append({
            "group_label": grp_label,
            "school_year": sy,
            "semester": sem,
            "courses": c_list,
        })

    return {
        "courses": courses_list,
        "groups": groups,
        "total": len(courses_list),
    }


def get_course(username: str, course_id: str) -> Optional[Dict[str, Any]]:
    user_dir = _get_user_courses_dir(username)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
    fp = os.path.join(user_dir, f"{safe_id}.json")
    if not os.path.exists(fp):
        return None
    try:
        with open(fp, "r", encoding="utf-8") as f:
            doc = json.load(f)
            bp = doc.get("blueprint")
            if isinstance(bp, dict) and "rubrics" not in bp:
                bp["rubrics"] = []
            return doc
    except Exception:
        return None


def save_course(username: str, course_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves or updates course blueprint and summary metadata.
    """
    user_dir = _get_user_courses_dir(username)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
    fp = os.path.join(user_dir, f"{safe_id}.json")

    existing = {}
    if os.path.exists(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    bp_dict = payload.get("blueprint") or payload.get("blueprint_dict") or existing.get("blueprint") or {}
    meta = bp_dict.get("metadata", {})

    now_iso = datetime.now().isoformat(timespec="seconds")
    created_at = existing.get("created_at") or now_iso

    course_code = (payload.get("course_code") or meta.get("course_code") or existing.get("course_code") or "Course").strip()
    course_title = (payload.get("course_title") or meta.get("course_title") or existing.get("course_title") or "").strip()
    section = (payload.get("section") or meta.get("section") or existing.get("section") or "1A").strip()
    semester_ay = (payload.get("semester_ay") or meta.get("semester_ay") or existing.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()

    # Enforce syllabus workflow locks on blueprint (existing workflow cannot be forged)
    wf = existing.get("workflow") or payload.get("workflow") or syllabus_workflow.default_workflow()
    temp_doc = {"blueprint": existing.get("blueprint"), "workflow": wf, "owner": username}
    bp_dict = syllabus_workflow.enforce_locks(temp_doc, bp_dict)

    # Enforce syllabus approval barrier for Class Record Setup (categories) and Grades (students)
    is_syllabus_approved = (wf or {}).get("status") == "approved"
    if existing and not is_syllabus_approved:
        old_bp = existing.get("blueprint") or {}
        if "students" in old_bp:
            bp_dict["students"] = old_bp["students"]
        if "categories" in old_bp:
            bp_dict["categories"] = old_bp["categories"]

    # Enforce class record grade locks (freeze student scores when under sign-off or finalized)
    cr_wf = existing.get("class_record_workflow") or payload.get("class_record_workflow") or class_record_workflow.default_class_record_workflow(username)
    if existing and class_record_workflow.is_class_record_locked({"class_record_workflow": cr_wf}):
        old_bp = existing.get("blueprint") or {}
        if "students" in old_bp:
            bp_dict["students"] = old_bp["students"]
        if "categories" in old_bp:
            bp_dict["categories"] = old_bp["categories"]

    programs = payload.get("programs") or meta.get("programs") or []
    sections = payload.get("sections") or meta.get("sections") or []
    if not sections and section:
        sections = [s.strip() for s in section.split(",") if s.strip()]
    elif sections:
        section = ", ".join(sections)

    if not programs and (payload.get("program_code") or meta.get("program_code")):
        programs = [p.strip() for p in (payload.get("program_code") or meta.get("program_code")).split(",") if p.strip()]

    # Synchronize metadata inside blueprint as well
    if "metadata" in bp_dict:
        bp_dict["metadata"]["course_code"] = course_code
        bp_dict["metadata"]["course_title"] = course_title
        bp_dict["metadata"]["section"] = section
        bp_dict["metadata"]["sections"] = sections
        bp_dict["metadata"]["programs"] = programs
        if programs:
            bp_dict["metadata"]["program_code"] = ", ".join(programs)
        bp_dict["metadata"]["semester_ay"] = semester_ay

    doc = {
        "id": safe_id,
        "owner": username,
        "created_at": created_at,
        "updated_at": now_iso,
        "course_code": course_code,
        "course_title": course_title,
        "section": section,
        "semester_ay": semester_ay,
        "blueprint": bp_dict,
        "workflow": wf,
        "class_record_workflow": cr_wf,
    }

    for attempt in range(5):
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2)
            break
        except (PermissionError, OSError):
            import time
            time.sleep(0.05)

    return doc


def create_course(
    username: str,
    course_code: str = "EE 211",
    course_title: str = "Electrical Circuits 1",
    section: str = "EE 2A",
    semester_ay: str = "1st Semester, A.Y. 2026-2027",
    from_catalog: bool = False,
    catalog_course_data: Optional[Dict[str, Any]] = None,
    faculty_name: str = "",
    programs: Optional[List[str]] = None,
    sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Creates a new subject entry under the user's account with multi-program & multi-section support.
    """
    course_id = f"c_{uuid.uuid4().hex[:10]}"

    init_sections = sections or ([s.strip() for s in section.split(",") if s.strip()] if section else ["EE 2A"])
    init_section = ", ".join(init_sections)
    init_programs = programs or []

    if from_catalog and catalog_course_data:
        bp = get_blank_blueprint(
            course_code=catalog_course_data.get("code") or course_code,
            course_title=catalog_course_data.get("title") or course_title,
            section=init_section,
            semester_ay=semester_ay,
            faculty_name=faculty_name,
            credit_units=catalog_course_data.get("credit_units") or "3.0 Units – Lecture",
            lec_lab=catalog_course_data.get("lec_lab") or "Lecture",
            contact_hours=catalog_course_data.get("hours") or "3 Hours/Week",
            course_description=catalog_course_data.get("description") or "",
            prerequisites=catalog_course_data.get("prereqs") or "",
            corequisites=catalog_course_data.get("coreqs") or "",
            programs=init_programs if init_programs else None,
            sections=init_sections,
        )
        topics = catalog_course_data.get("topics") or []
        if topics:
            bp.metadata.learning_plan_table = build_learning_plan_from_topics(topics)
        bp_dict = bp.to_dict()
    else:
        bp = get_blank_blueprint(
            course_code=course_code,
            course_title=course_title,
            section=init_section,
            semester_ay=semester_ay,
            faculty_name=faculty_name,
            programs=init_programs if init_programs else None,
            sections=init_sections,
        )
        bp_dict = bp.to_dict()

    payload = {
        "course_code": course_code,
        "course_title": course_title,
        "section": init_section,
        "sections": init_sections,
        "programs": bp.metadata.programs,
        "semester_ay": semester_ay,
        "blueprint": bp_dict,
    }
    return save_course(username, course_id, payload)


def duplicate_course(username: str, course_id: str, new_section: str = "", clear_scores: bool = False) -> Optional[Dict[str, Any]]:
    """
    Duplicates an existing subject (e.g. for another section).
    Copies syllabus, assessment configuration, CLOs, etc.
    Optionally clears student scores for the new section roster.
    """
    source = get_course(username, course_id)
    if not source:
        return None

    new_id = f"c_{uuid.uuid4().hex[:10]}"
    new_doc = copy.deepcopy(source)
    new_doc["id"] = new_id
    now_iso = datetime.now().isoformat(timespec="seconds")
    new_doc["created_at"] = now_iso
    new_doc["updated_at"] = now_iso

    target_sec = new_section.strip() if new_section else f"{source.get('section', '1A')} (Copy)"
    new_doc["section"] = target_sec

    bp_dict = new_doc.get("blueprint", {})
    if "metadata" in bp_dict:
        bp_dict["metadata"]["section"] = target_sec

    if clear_scores and "students" in bp_dict:
        for st in bp_dict.get("students", []):
            st["scores"] = {}

    user_dir = _get_user_courses_dir(username)
    fp = os.path.join(user_dir, f"{new_id}.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(new_doc, f, indent=2)

    return new_doc


def delete_course(username: str, course_id: str) -> bool:
    user_dir = _get_user_courses_dir(username)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
    fp = os.path.join(user_dir, f"{safe_id}.json")
    if os.path.exists(fp):
        try:
            os.remove(fp)
            return True
        except Exception:
            return False
    return False


def find_course(course_id: str) -> Optional[Dict[str, Any]]:
    """Finds a course by course_id across all user workspaces."""
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
    if not os.path.exists(COURSES_BASE_DIR):
        return None
    for uname in os.listdir(COURSES_BASE_DIR):
        user_dir = os.path.join(COURSES_BASE_DIR, uname)
        if os.path.isdir(user_dir):
            fp = os.path.join(user_dir, f"{safe_id}.json")
            if os.path.exists(fp):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        doc = json.load(f)
                        bp = doc.get("blueprint")
                        if isinstance(bp, dict) and not bp.get("rubrics"):
                            import sample_syllabus
                            bp["rubrics"] = sample_syllabus.get_default_rubrics()
                        return doc
                except Exception:
                    continue
    return None


def save_course_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Saves an entire course document back to its owner's storage."""
    owner = doc.get("owner") or "default"
    user_dir = _get_user_courses_dir(owner)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", doc["id"])
    fp = os.path.join(user_dir, f"{safe_id}.json")
    doc["updated_at"] = datetime.now().isoformat(timespec="seconds")
    for attempt in range(5):
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2)
            break
        except (PermissionError, OSError):
            import time
            time.sleep(0.05)
    return doc


def list_all_workflow_courses() -> List[Dict[str, Any]]:
    """Returns all courses across all user workspaces with their workflow state."""
    results = []
    if not os.path.exists(COURSES_BASE_DIR):
        return results
    for uname in os.listdir(COURSES_BASE_DIR):
        user_dir = os.path.join(COURSES_BASE_DIR, uname)
        if not os.path.isdir(user_dir):
            continue
        for fn in os.listdir(user_dir):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(user_dir, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                    bp = doc.get("blueprint") or {}
                    meta = bp.get("metadata") or {}
                    sem_ay = meta.get("semester_ay") or doc.get("semester_ay") or "1st Semester, A.Y. 2026-2027"
                    sy, sem, grp = parse_semester_ay(sem_ay)
                    results.append({
                        "id": doc.get("id"),
                        "owner": doc.get("owner"),
                        "course_code": (meta.get("course_code") or doc.get("course_code") or "New Course").strip(),
                        "course_title": (meta.get("course_title") or doc.get("course_title") or "Untitled Subject").strip(),
                        "section": (meta.get("section") or doc.get("section") or "1A").strip(),
                        "semester_ay": sem_ay,
                        "school_year": sy,
                        "semester": sem,
                        "group_label": grp,
                        "credit_units": meta.get("credit_units") or "3.0 Units",
                        "faculty_name": meta.get("faculty_name") or doc.get("owner"),
                        "created_at": doc.get("created_at"),
                        "updated_at": doc.get("updated_at"),
                        "workflow": syllabus_workflow.public_view(doc),
                        "class_record_workflow": class_record_workflow.public_cr_view(doc),
                        "doc_raw": doc,
                    })
            except Exception:
                continue
    results.sort(key=lambda x: (x.get("workflow", {}).get("submitted_at") or x.get("updated_at") or ""), reverse=True)
    return results

load_course = get_course
