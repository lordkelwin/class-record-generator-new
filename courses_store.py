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
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models import CourseOutcome, CourseMetadata, SyllabusBlueprint, get_default_cqi_indicators
from sample_syllabus import get_default_blueprint, get_blank_blueprint, build_learning_plan_from_topics
from catalog_data import get_full_catalog

try:
    import config
    BASE_DIR = config.BASE_DIR
    DATA_DIR = config.DATA_DIR
    COURSES_BASE_DIR = config.COURSES_DIR
except Exception:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    COURSES_BASE_DIR = os.environ.get("COURSES_DIR", os.path.join(DATA_DIR, "courses"))


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


def get_doc_authors(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts the list of authors/faculty writers for this syllabus.
    Guaranteed to return at least the course initializer/owner as Lead Author.
    """
    owner = doc.get("owner", "")
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    raw_authors = doc.get("authors") or meta.get("authors") or []
    cleaned_authors: List[Dict[str, Any]] = []
    seen = set()
    owner_name = meta.get("faculty_name") or owner

    for a in raw_authors:
        if isinstance(a, dict):
            uname = (a.get("username") or "").strip()
            name = (a.get("name") or a.get("full_name") or uname).strip()
            if not uname and owner and name.lower() == owner_name.lower():
                uname = owner
            key_u = uname.lower() if uname else None
            key_n = name.lower() if name else None
            if (key_u and key_u in seen) or (key_n and key_n in seen):
                continue
            if key_u: seen.add(key_u)
            if key_n: seen.add(key_n)
            cleaned_authors.append({
                "username": uname,
                "name": name,
                "email": a.get("email") or "",
                "contact": a.get("contact") or "",
                "consultation_hours": a.get("consultation_hours") or "",
                "role": a.get("role") or ("Lead Author" if (owner and uname.lower() == owner.lower()) or not cleaned_authors else "Co-Author")
            })
        elif isinstance(a, str) and a.strip():
            uname = a.strip()
            name = uname
            if owner and uname.lower() == owner.lower() and owner_name:
                name = owner_name
            key_u = uname.lower()
            key_n = name.lower()
            if key_u in seen or key_n in seen:
                continue
            seen.add(key_u)
            seen.add(key_n)
            cleaned_authors.append({
                "username": uname,
                "name": name,
                "email": "",
                "contact": "",
                "consultation_hours": "",
                "role": "Lead Author" if (owner and uname.lower() == owner.lower()) or not cleaned_authors else "Co-Author"
            })

    # Ensure the initializing owner is always present as Lead Author
    if owner:
        owner_lower = owner.lower()
        has_owner = any((a.get("username") or "").lower() == owner_lower for a in cleaned_authors)
        if not has_owner:
            cleaned_authors.insert(0, {
                "username": owner,
                "name": owner_name,
                "email": meta.get("faculty_email") or "",
                "contact": meta.get("faculty_contact") or "",
                "consultation_hours": meta.get("consultation_hours") or "",
                "role": "Lead Author"
            })
    if not cleaned_authors:
        cleaned_authors = [{
            "username": owner or "faculty",
            "name": owner_name or "Faculty Member",
            "email": meta.get("faculty_email") or "",
            "contact": meta.get("faculty_contact") or "",
            "consultation_hours": meta.get("consultation_hours") or "",
            "role": "Lead Author"
        }]

    return cleaned_authors


def has_recorded_scores(doc: Dict[str, Any]) -> bool:
    """Returns True if the course document contains at least one recorded student assessment score > 0."""
    if not doc or not isinstance(doc, dict):
        return False
    bp = doc.get("blueprint") or {}
    students = bp.get("students") or []
    for st in students:
        if not isinstance(st, dict):
            continue
        scores = st.get("scores") or {}
        if not isinstance(scores, dict):
            continue
        for v in scores.values():
            if v is not None and v != "":
                try:
                    num = float(v)
                    if num > 0:
                        return True
                except (ValueError, TypeError):
                    continue
    return False


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

    authors = get_doc_authors(doc)
    author_names = [a.get("name") for a in authors if a.get("name")]

    return {
        "id": doc.get("id"),
        "owner": doc.get("owner"),
        "authors": authors,
        "author_names": author_names,
        "is_multi_authored": len(authors) > 1,
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
        "has_recorded_scores": has_recorded_scores(doc),
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
    Returns all courses owned by the user, PLUS courses where the user is an author/co-author.
    """
    user_dir = _get_user_courses_dir(username)
    files = [f for f in os.listdir(user_dir) if f.endswith(".json")] if os.path.exists(user_dir) else []

    courses_list: List[Dict[str, Any]] = []
    seen_ids = set()

    for fn in files:
        fp = os.path.join(user_dir, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                doc = json.load(f)
                summ = _summary_from_doc(doc)
                summ["is_owner"] = True
                summ["is_coauthor"] = False
                courses_list.append(summ)
                seen_ids.add(summ["id"])
        except Exception:
            continue

    # Also include courses where this user is listed as a co-author across other faculty workspaces
    u_lower = (username or "").strip().lower()
    if u_lower and os.path.exists(COURSES_BASE_DIR):
        for other_user in os.listdir(COURSES_BASE_DIR):
            if other_user.lower() == u_lower:
                continue
            other_dir = os.path.join(COURSES_BASE_DIR, other_user)
            if not os.path.isdir(other_dir):
                continue
            for fn in os.listdir(other_dir):
                if not fn.endswith(".json"):
                    continue
                cid = fn[:-5]
                if cid in seen_ids:
                    continue
                fp = os.path.join(other_dir, fn)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        doc = json.load(f)
                        authors = get_doc_authors(doc)
                        author_unames = [(a.get("username") or "").strip().lower() for a in authors]
                        if u_lower in author_unames:
                            summ = _summary_from_doc(doc)
                            summ["is_owner"] = False
                            summ["is_coauthor"] = True
                            courses_list.append(summ)
                            seen_ids.add(summ["id"])
                except Exception:
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

    has_any_scores = any(bool(c.get("has_recorded_scores")) for c in courses_list)
    return {
        "courses": courses_list,
        "groups": groups,
        "total": len(courses_list),
        "has_recorded_scores": has_any_scores,
        "has_any_recorded_scores": has_any_scores,
    }


def _sync_student_acknowledgments_from_store(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Ensures student assessment_acknowledgments from data/students.json are merged into doc['blueprint']['students'].
    This protects against data loss and guarantees that student acknowledgments recorded via student portal
    are always reflected in the course blueprint for faculty views, gradebook, and receipt matrix.
    """
    if not doc or not isinstance(doc, dict):
        return doc
    cid = doc.get("id")
    bp = doc.get("blueprint") or {}
    students = bp.get("students") or []
    if not cid or not students:
        return doc

    try:
        from student_store import _load_students, _normalize_id
        all_students = _load_students()
        if not all_students:
            return doc
        for st in students:
            sid = str(st.get("student_id") or "").strip().lower()
            sid_norm = _normalize_id(sid)
            sid_digits = re.sub(r"\D", "", sid)

            matched_profile = all_students.get(sid_norm)
            if not matched_profile:
                for k, prof in all_students.items():
                    k_sid = str(prof.get("student_id") or k).strip().lower()
                    k_digits = re.sub(r"\D", "", k_sid)
                    if (k_sid and k_sid == sid) or (k_digits and sid_digits and len(k_digits) >= 4 and k_digits == sid_digits):
                        matched_profile = prof
                        break

            if matched_profile:
                stored_acks = (matched_profile.get("assessment_acknowledgments") or {}).get(cid) or {}
                if stored_acks:
                    cur_acks = st.setdefault("assessment_acknowledgments", {})
                    for it_id, ack_val in stored_acks.items():
                        if it_id not in cur_acks or (not cur_acks[it_id].get("acknowledged") and ack_val.get("acknowledged")):
                            cur_acks[it_id] = {
                                "acknowledged": True,
                                "acknowledged_at": ack_val.get("acknowledged_at", ""),
                                "acknowledged_iso": ack_val.get("acknowledged_iso", ""),
                                "signature_data": ack_val.get("signature_data") or matched_profile.get("signature_data", ""),
                                "student_id": st.get("student_id"),
                                "student_name": st.get("name") or f"{st.get('last_name', '')}, {st.get('first_name', '')}".strip(", "),
                                "statement": ack_val.get("statement", "Student accepted the score, received test paper, and acknowledged that the score is final and reconsideration will not be entertained.")
                            }
                        elif it_id in cur_acks and not cur_acks[it_id].get("signature_data"):
                            cur_acks[it_id]["signature_data"] = ack_val.get("signature_data") or matched_profile.get("signature_data", "")
    except Exception:
        pass

    return doc


def _sync_cqi_plan(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Ensures blueprint has a populated cqi_plan with all 20 indicators across Categories I–IV."""
    if not doc or not isinstance(doc, dict):
        return doc
    bp = doc.get("blueprint")
    if not isinstance(bp, dict):
        return doc

    default_indicators = [asdict(ind) for ind in get_default_cqi_indicators()]
    cqi = bp.get("cqi_plan")
    if not cqi or not isinstance(cqi, dict):
        bp["cqi_plan"] = {
            "key_strengths": "Course delivery strictly followed the OBE syllabus learning plan, utilizing problem-based learning, collaborative group activities (FA1), and structured rubric-based summative assessments (SA1 & SA2).",
            "areas_for_improvement": "Some students encountered difficulties in setting up multi-loop nodal/mesh differential equations and time-domain RLC transient analysis under time constraints during major examinations.",
            "action_plan": "1. Increase guided problem-solving drills and simulation verification during formative group activities (FA1).\n2. Conduct targeted remedial review sessions prior to term examinations focusing on CLOs with <75% average score.\n3. Provide step-by-step rubric exemplars for multi-source network theorem and transient problems.",
            "date_of_evaluation": datetime.now().strftime("%B %Y"),
            "indicators": default_indicators,
        }
    else:
        indicators = cqi.get("indicators")
        if not indicators or not isinstance(indicators, list) or len(indicators) == 0:
            cqi["indicators"] = default_indicators
        else:
            existing_keys = {(ind.get("category"), ind.get("number")) for ind in indicators if isinstance(ind, dict)}
            for def_ind in default_indicators:
                if (def_ind.get("category"), def_ind.get("number")) not in existing_keys:
                    indicators.append(def_ind)
    return doc


def sync_blueprint_assessments_from_activities(bp_dict: Dict[str, Any]) -> None:
    """
    Ensures blueprint categories and items are synchronized with syllabus_assessment_activities
    if categories is missing or empty.
    """
    if not isinstance(bp_dict, dict):
        return
    categories = bp_dict.get("categories") or []
    has_items = any(bool(c.get("items")) for c in categories if isinstance(c, dict))
    meta = bp_dict.get("metadata") or {}
    activities = meta.get("syllabus_assessment_activities") or []
    valid_activities = [a for a in activities if isinstance(a, dict) and ((a.get("code") or "").strip() or (a.get("activity") or "").strip())]
    if has_items or not valid_activities:
        return

    co_options = [c.get("co_id") for c in (bp_dict.get("course_outcomes") or []) if c.get("co_id")]
    if not co_options:
        co_options = ["CLO1"]

    new_categories = []
    for idx, act in enumerate(valid_activities):
        if not isinstance(act, dict):
            continue
        act_name = act.get("activity") or "Assessment Activity"
        code = (act.get("code") or f"A{idx+1}").upper()
        try:
            wt = float(act.get("weight_pct") or 0.0)
        except (ValueError, TypeError):
            wt = 0.0
        is_maj = bool(act.get("is_major_assessment"))
        scope = str(act.get("major_scope") or "independent").lower()
        aligned_str = str(act.get("clo_aligned") or ", ".join(co_options)).strip()
        aligned_clos = [c.strip().upper() for c in re.split(r"[,;/]+", aligned_str) if c.strip()]
        if not aligned_clos:
            aligned_clos = [co_options[0].upper()]

        def _make_clo_pts(pts):
            each = round(pts / max(1, len(aligned_clos)), 2)
            return {c: each for c in aligned_clos}

        if is_maj:
            if scope == "both_terms":
                for t_name, prefix in [("Midterm", "MID"), ("Finals", "FIN")]:
                    item_id = f"{prefix}_{code}"
                    new_categories.append({
                        "category_id": f"{prefix}_MAJ_{code}",
                        "term": t_name,
                        "is_major_assessment": True,
                        "major_scope": "both_terms",
                        "assessment_type": "SA",
                        "assessment_code": code,
                        "name": f"{act_name} ({t_name})",
                        "lec_lab": act.get("lec_lab") or "Lecture",
                        "weight_pct": wt,
                        "items": [{
                            "item_id": item_id,
                            "name": f"{act_name} ({t_name})",
                            "max_score": 50.0,
                            "co_id": ", ".join(aligned_clos),
                            "weight_pct": wt,
                            "clo_points": _make_clo_pts(50.0)
                        }]
                    })
            else:
                term_name = "Major Assessment" if scope == "independent" else ("Finals" if scope == "finals" else "Midterm")
                new_categories.append({
                    "category_id": f"MAJ_{code}",
                    "term": term_name,
                    "is_major_assessment": True,
                    "major_scope": scope,
                    "assessment_type": "SA",
                    "assessment_code": code,
                    "name": act_name,
                    "lec_lab": act.get("lec_lab") or "Lecture",
                    "weight_pct": wt,
                    "items": [{
                        "item_id": code,
                        "name": act_name,
                        "max_score": 50.0,
                        "co_id": ", ".join(aligned_clos),
                        "weight_pct": wt,
                        "clo_points": _make_clo_pts(50.0)
                    }]
                })
        else:
            a_type = "FA" if str(act.get("type", "")).lower().startswith("form") or code.startswith("FA") else "SA"
            for t_name, prefix in [("Midterm", "MID"), ("Finals", "FIN")]:
                cat_code = f"{prefix}_{code}"
                new_categories.append({
                    "category_id": f"{prefix}_{code}",
                    "term": t_name,
                    "is_major_assessment": False,
                    "assessment_type": a_type,
                    "assessment_code": code,
                    "name": f"{act_name} ({t_name})",
                    "lec_lab": act.get("lec_lab") or "Lecture",
                    "weight_pct": wt,
                    "items": [{
                        "item_id": f"{code}_{1 if t_name == 'Midterm' else 2}",
                        "name": f"{act_name} ({t_name})",
                        "max_score": 30.0,
                        "co_id": ", ".join(aligned_clos),
                        "weight_pct": wt if a_type == "SA" else 100.0,
                        "clo_points": _make_clo_pts(30.0)
                    }]
                })
    bp_dict["categories"] = new_categories


def get_standard_categories_and_items(
    course_code: str = "",
    lec_lab: str = "Lecture",
    credit_units: str = "3.0 Units",
    clos: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Generates standard USeP OBE assessment categories and items aligned with course syllabus/grading system.
    Supports Lecture and Lecture/Laboratory grading modes.
    """
    if not clos:
        clos = ["CLO1", "CLO2"]
    co_str = ", ".join(clos)

    def _clo_pts(pts: float) -> Dict[str, float]:
        each = round(pts / max(1, len(clos)), 2)
        return {c: each for c in clos}

    is_lec_lab = (
        "lab" in str(lec_lab).lower() or
        "integrated" in str(credit_units).lower() or
        "lecture/lab" in str(lec_lab).lower()
    )

    categories: List[Dict[str, Any]] = []

    # MIDTERM PERIOD
    categories.append({
        "category_id": "MID_FA1",
        "term": "Midterm",
        "assessment_type": "FA",
        "assessment_code": "FA1",
        "name": "Formative Assessment 1 (Group Activity)",
        "lec_lab": "Lecture",
        "weight_pct": 0.0,
        "is_major_assessment": False,
        "items": [{
            "item_id": "A1",
            "name": f"FA1 Group Activity 1 ({co_str})",
            "max_score": 100.0,
            "co_id": co_str,
            "weight_pct": 100.0,
            "clo_points": _clo_pts(100.0)
        }]
    })
    categories.append({
        "category_id": "MID_FA2",
        "term": "Midterm",
        "assessment_type": "FA",
        "assessment_code": "FA2",
        "name": "Formative Assessment 2 (Group Activity)",
        "lec_lab": "Lecture",
        "weight_pct": 0.0,
        "is_major_assessment": False,
        "items": [{
            "item_id": "A2",
            "name": f"FA2 Group Activity 2 ({co_str})",
            "max_score": 100.0,
            "co_id": co_str,
            "weight_pct": 100.0,
            "clo_points": _clo_pts(100.0)
        }]
    })
    categories.append({
        "category_id": "MID_SA1",
        "term": "Midterm",
        "assessment_type": "SA",
        "assessment_code": "SA1",
        "name": "Summative Assessment 1 (Quizzes)",
        "lec_lab": "Lecture",
        "weight_pct": 40.0,
        "is_major_assessment": False,
        "items": [
            {
                "item_id": "Q1",
                "name": f"Quiz 1 ({co_str})",
                "max_score": 30.0,
                "co_id": co_str,
                "weight_pct": 20.0,
                "clo_points": _clo_pts(30.0)
            },
            {
                "item_id": "Q2",
                "name": f"Quiz 2 ({co_str})",
                "max_score": 30.0,
                "co_id": co_str,
                "weight_pct": 20.0,
                "clo_points": _clo_pts(30.0)
            }
        ]
    })
    categories.append({
        "category_id": "MID_SA2",
        "term": "Midterm",
        "assessment_type": "SA",
        "assessment_code": "SA2",
        "name": "Summative Assessment 2 (Term Examination)",
        "lec_lab": "Lecture",
        "weight_pct": 60.0,
        "is_major_assessment": False,
        "items": [{
            "item_id": "MTE",
            "name": f"Midterm Examination ({co_str})",
            "max_score": 60.0,
            "co_id": co_str,
            "weight_pct": 60.0,
            "clo_points": _clo_pts(60.0)
        }]
    })

    if is_lec_lab:
        categories.append({
            "category_id": "MID_LAB_FA1",
            "term": "Midterm",
            "assessment_type": "FA",
            "assessment_code": "FA1",
            "name": "Laboratory Activity / Experiment 1",
            "lec_lab": "Laboratory",
            "weight_pct": 0.0,
            "is_major_assessment": False,
            "items": [{
                "item_id": "LA1",
                "name": f"Lab Activity 1 ({co_str})",
                "max_score": 100.0,
                "co_id": co_str,
                "weight_pct": 100.0,
                "clo_points": _clo_pts(100.0)
            }]
        })
        categories.append({
            "category_id": "MID_LAB_SA1",
            "term": "Midterm",
            "assessment_type": "SA",
            "assessment_code": "SA1",
            "name": "Laboratory Performance Tasks",
            "lec_lab": "Laboratory",
            "weight_pct": 50.0,
            "is_major_assessment": False,
            "items": [{
                "item_id": "LPT1",
                "name": f"Midterm Lab Performance Task ({co_str})",
                "max_score": 50.0,
                "co_id": co_str,
                "weight_pct": 50.0,
                "clo_points": _clo_pts(50.0)
            }]
        })
        categories.append({
            "category_id": "MID_LAB_SA2",
            "term": "Midterm",
            "assessment_type": "SA",
            "assessment_code": "SA2",
            "name": "Midterm Practical Examination",
            "lec_lab": "Laboratory",
            "weight_pct": 50.0,
            "is_major_assessment": False,
            "items": [{
                "item_id": "MLE",
                "name": f"Midterm Practical Exam ({co_str})",
                "max_score": 50.0,
                "co_id": co_str,
                "weight_pct": 50.0,
                "clo_points": _clo_pts(50.0)
            }]
        })

    # FINALS PERIOD
    categories.append({
        "category_id": "FIN_FA1",
        "term": "Finals",
        "assessment_type": "FA",
        "assessment_code": "FA1",
        "name": "Formative Assessment 1 (Group Activity)",
        "lec_lab": "Lecture",
        "weight_pct": 0.0,
        "is_major_assessment": False,
        "items": [{
            "item_id": "A3",
            "name": f"FA1 Group Activity 3 ({co_str})",
            "max_score": 100.0,
            "co_id": co_str,
            "weight_pct": 100.0,
            "clo_points": _clo_pts(100.0)
        }]
    })
    categories.append({
        "category_id": "FIN_FA2",
        "term": "Finals",
        "assessment_type": "FA",
        "assessment_code": "FA2",
        "name": "Formative Assessment 2 (Group Activity)",
        "lec_lab": "Lecture",
        "weight_pct": 0.0,
        "is_major_assessment": False,
        "items": [{
            "item_id": "A4",
            "name": f"FA2 Group Activity 4 ({co_str})",
            "max_score": 100.0,
            "co_id": co_str,
            "weight_pct": 100.0,
            "clo_points": _clo_pts(100.0)
        }]
    })
    categories.append({
        "category_id": "FIN_SA1",
        "term": "Finals",
        "assessment_type": "SA",
        "assessment_code": "SA1",
        "name": "Summative Assessment 1 (Quizzes)",
        "lec_lab": "Lecture",
        "weight_pct": 40.0,
        "is_major_assessment": False,
        "items": [
            {
                "item_id": "Q3",
                "name": f"Quiz 3 ({co_str})",
                "max_score": 30.0,
                "co_id": co_str,
                "weight_pct": 20.0,
                "clo_points": _clo_pts(30.0)
            },
            {
                "item_id": "Q4",
                "name": f"Quiz 4 ({co_str})",
                "max_score": 30.0,
                "co_id": co_str,
                "weight_pct": 20.0,
                "clo_points": _clo_pts(30.0)
            }
        ]
    })
    categories.append({
        "category_id": "FIN_SA2",
        "term": "Finals",
        "assessment_type": "SA",
        "assessment_code": "SA2",
        "name": "Summative Assessment 2 (Term Examination)",
        "lec_lab": "Lecture",
        "weight_pct": 60.0,
        "is_major_assessment": False,
        "items": [{
            "item_id": "FTE",
            "name": f"Final Term Examination ({co_str})",
            "max_score": 60.0,
            "co_id": co_str,
            "weight_pct": 60.0,
            "clo_points": _clo_pts(60.0)
        }]
    })

    if is_lec_lab:
        categories.append({
            "category_id": "FIN_LAB_FA1",
            "term": "Finals",
            "assessment_type": "FA",
            "assessment_code": "FA1",
            "name": "Laboratory Activity / Experiment 2",
            "lec_lab": "Laboratory",
            "weight_pct": 0.0,
            "is_major_assessment": False,
            "items": [{
                "item_id": "LA2",
                "name": f"Lab Activity 2 ({co_str})",
                "max_score": 100.0,
                "co_id": co_str,
                "weight_pct": 100.0,
                "clo_points": _clo_pts(100.0)
            }]
        })
        categories.append({
            "category_id": "FIN_LAB_SA1",
            "term": "Finals",
            "assessment_type": "SA",
            "assessment_code": "SA1",
            "name": "Laboratory Performance Tasks",
            "lec_lab": "Laboratory",
            "weight_pct": 50.0,
            "is_major_assessment": False,
            "items": [{
                "item_id": "LPT2",
                "name": f"Final Lab Performance Task ({co_str})",
                "max_score": 50.0,
                "co_id": co_str,
                "weight_pct": 50.0,
                "clo_points": _clo_pts(50.0)
            }]
        })
        categories.append({
            "category_id": "FIN_LAB_SA2",
            "term": "Finals",
            "assessment_type": "SA",
            "assessment_code": "SA2",
            "name": "Final Practical Examination",
            "lec_lab": "Laboratory",
            "weight_pct": 50.0,
            "is_major_assessment": False,
            "items": [{
                "item_id": "FLE",
                "name": f"Final Practical Exam ({co_str})",
                "max_score": 50.0,
                "co_id": co_str,
                "weight_pct": 50.0,
                "clo_points": _clo_pts(50.0)
            }]
        })

    return categories


def auto_generate_class_record(doc: Dict[str, Any], force: bool = False) -> bool:
    """
    Automatically synchronizes and generates the Class Record matrix when:
      (a) Syllabus is approved through official review chain by Dean.
    
    Sequential Step-Gating:
      Steps 2-6 remain strictly locked until syllabus is approved by the Dean.
      Therefore, class record auto-generation is gated on syllabus Dean approval.
    """
    if not doc or not isinstance(doc, dict):
        return False

    import syllabus_workflow
    if not force and not syllabus_workflow.is_approved(doc):
        return False

    bp = doc.get("blueprint")
    if not isinstance(bp, dict):
        return False

    meta = bp.get("metadata") or {}
    course_code = (doc.get("course_code") or meta.get("course_code") or "EE 211").strip()
    sec = (doc.get("section") or meta.get("section") or "1A").strip()
    prog_code = (doc.get("program") or meta.get("program_code") or "EE").strip()
    lec_lab = meta.get("lec_lab") or doc.get("lec_lab") or "Lecture"
    credit_units = meta.get("credit_units") or "3.0 Units"
    cid = doc.get("id") or doc.get("course_id") or ""

    clos = [c.get("co_id") for c in (bp.get("course_outcomes") or []) if isinstance(c, dict) and c.get("co_id")]
    if not clos:
        clos = ["CLO1", "CLO2"]

    # 1. Ensure categories & items exist
    categories = bp.get("categories") or []
    has_items = any(bool(c.get("items")) for c in categories if isinstance(c, dict))
    if not has_items:
        sync_blueprint_assessments_from_activities(bp)
        categories = bp.get("categories") or []
        has_items = any(bool(c.get("items")) for c in categories if isinstance(c, dict))

    if not has_items:
        bp["categories"] = get_standard_categories_and_items(course_code, lec_lab, credit_units, clos)
        categories = bp["categories"]
        # Also populate syllabus_assessment_activities if placeholder
        acts = meta.get("syllabus_assessment_activities") or []
        if not acts or all(not (a.get("code") or a.get("activity")) for a in acts if isinstance(a, dict)):
            meta["syllabus_assessment_activities"] = [
                {"type": "Formative", "code": "FA1", "activity": "Group Activity / Assignment", "description": "Formative exercises and group problem solving", "clo_aligned": ", ".join(clos), "weight_pct": 0, "items_midterm": 1, "items_finals": 1, "items_per_term": 1, "is_major_assessment": False, "major_scope": "independent", "lec_lab": "Lecture", "rubric_ref": ""},
                {"type": "Formative", "code": "FA2", "activity": "Worksheet / Simulation Exercise", "description": "Laboratory / simulation worksheets and exercises", "clo_aligned": ", ".join(clos), "weight_pct": 0, "items_midterm": 1, "items_finals": 1, "items_per_term": 1, "is_major_assessment": False, "major_scope": "independent", "lec_lab": "Lecture", "rubric_ref": ""},
                {"type": "Summative", "code": "SA1", "activity": "Summative Quizzes", "description": "Closed-book quizzes assessing module competencies", "clo_aligned": ", ".join(clos), "weight_pct": 40.0, "items_midterm": 2, "items_finals": 2, "items_per_term": 2, "is_major_assessment": False, "major_scope": "independent", "lec_lab": "Lecture", "rubric_ref": ""},
                {"type": "Summative", "code": "SA2", "activity": "Term Examination", "description": "Midterm and final term examinations", "clo_aligned": ", ".join(clos), "weight_pct": 60.0, "items_midterm": 1, "items_finals": 1, "items_per_term": 1, "is_major_assessment": False, "major_scope": "independent", "lec_lab": "Lecture", "rubric_ref": ""},
            ]

    # Extract all item keys (e.g. Q1__CLO1, MTE__CLO1, etc.)
    all_items: List[Dict[str, Any]] = []
    item_keys: List[str] = []
    for cat in categories:
        if not isinstance(cat, dict):
            continue
        for it in cat.get("items") or []:
            if isinstance(it, dict) and it.get("item_id"):
                all_items.append(it)
                item_id = it.get("item_id")
                co_str = str(it.get("co_id") or "")
                aligned_clos = [c.strip().upper() for c in re.split(r"[,;/]+", co_str) if c.strip()]
                if aligned_clos:
                    for c in aligned_clos:
                        item_keys.append(f"{item_id}__{c}")
                else:
                    item_keys.append(item_id)

    # 2. Populate enrolled students from Database & Syllabus Acknowledgments
    students = bp.setdefault("students", [])

    def _norm(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", str(s or "")).lower()

    existing_by_id = {}
    existing_by_name = {}
    for st in students:
        sid = str(st.get("student_id") or "").strip()
        if sid:
            existing_by_id[_norm(sid)] = st
        sname = str(st.get("name") or f"{st.get('last_name', '')}, {st.get('first_name', '')}".strip(", ")).strip().lower()
        if sname:
            existing_by_name[sname] = st

    # Fetch from SQLite app_students if students list is empty (initial setup)
    if not students:
        try:
            import db_persistence
            enrolled_db_students = db_persistence.get_enrolled_students_for_course(cid, sec, prog_code)
            for en in enrolled_db_students:
                students.append(en)
                sid = str(en.get("student_id") or "").strip()
                if sid:
                    existing_by_id[_norm(sid)] = en
                sname = str(en.get("name") or "").strip().lower()
                if sname:
                    existing_by_name[sname] = en
        except Exception as _e:
            logger.debug("Error querying enrolled students in auto_generate_class_record: %s", _e)

    # Also merge syllabus acknowledgments if any
    wf = doc.get("workflow") or {}
    acks = doc.get("student_acknowledgments") or wf.get("student_acknowledgments") or []
    for ack in acks:
        if not isinstance(ack, dict):
            continue
        ack_sid = str(ack.get("student_id") or "").strip()
        ack_name = str(ack.get("student_name") or ack.get("name") or "").strip()
        if not ack_sid and not ack_name:
            continue

        st_match = None
        if ack_sid and _norm(ack_sid) in existing_by_id:
            st_match = existing_by_id[_norm(ack_sid)]
        elif ack_name and ack_name.lower() in existing_by_name:
            st_match = existing_by_name[ack_name.lower()]

        if not st_match:
            if "," in ack_name:
                parts = [p.strip() for p in ack_name.split(",", 1)]
                last_name = parts[0]
                first_name = parts[1]
                mi = ""
                m_mi = re.search(r"\s+([A-Za-z])\.?$", first_name)
                if m_mi:
                    mi = m_mi.group(1)
                    first_name = first_name[:m_mi.start()].strip()
            else:
                parts = ack_name.rsplit(" ", 1)
                if len(parts) == 2:
                    first_name = parts[0].strip()
                    last_name = parts[1].strip()
                    mi = ""
                else:
                    first_name = ack_name
                    last_name = ""
                    mi = ""

            st_match = {
                "student_id": ack_sid or f"2026-{len(students)+1:04d}",
                "last_name": last_name,
                "first_name": first_name,
                "middle_initial": mi,
                "name": ack_name or f"{last_name}, {first_name}".strip(", "),
                "email": ack.get("email") or "",
                "program_year": sec,
                "scores": {},
                "assessment_acknowledgments": {},
            }
            students.append(st_match)
            if ack_sid:
                existing_by_id[_norm(ack_sid)] = st_match
            if ack_name:
                existing_by_name[ack_name.lower()] = st_match

    # Bind assessment columns for all students
    for st in students:
        sc = st.setdefault("scores", {})
        for k in item_keys:
            if k not in sc:
                sc[k] = None

    return True


def get_course(username: str, course_id: str) -> Optional[Dict[str, Any]]:
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
    try:
        import db_persistence
        db_doc = db_persistence.load_course_from_db(safe_id)
        if db_doc:
            bp = db_doc.get("blueprint")
            if isinstance(bp, dict):
                if "rubrics" not in bp:
                    bp["rubrics"] = []
                sync_blueprint_assessments_from_activities(bp)
            _sync_student_acknowledgments_from_store(db_doc)
            _sync_cqi_plan(db_doc)
            auto_generate_class_record(db_doc)
            if isinstance(bp, dict) and "tos" in bp:
                db_doc["tos"] = bp["tos"]
            return db_doc
    except Exception:
        pass
    user_dir = _get_user_courses_dir(username)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
    fp = os.path.join(user_dir, f"{safe_id}.json")
    if os.path.exists(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                doc = json.load(f)
                bp = doc.get("blueprint")
                if isinstance(bp, dict) and "rubrics" not in bp:
                    bp["rubrics"] = []
                _sync_student_acknowledgments_from_store(doc)
                _sync_cqi_plan(doc)
                auto_generate_class_record(doc)
                return doc
        except Exception:
            pass

    # If not in user's direct folder, search other user folders if user is an author or admin
    doc = find_course(course_id)
    if doc:
        authors = get_doc_authors(doc)
        author_unames = [(a.get("username") or "").strip().lower() for a in authors]
        u_lower = (username or "").strip().lower()
        if u_lower == (doc.get("owner") or "").lower() or u_lower in author_unames or username == "admin":
            _sync_student_acknowledgments_from_store(doc)
            _sync_cqi_plan(doc)
            auto_generate_class_record(doc)
            return doc
    return None


def save_course(username: str, course_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves or updates course blueprint, authors, and summary metadata.
    Preserves original initializer/owner when edited by co-authors.
    """
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
    existing = find_course(safe_id) or {}

    # Target directory and owner: always maintain original owner if course already exists
    if existing:
        orig_owner = existing.get("owner") or username
    else:
        orig_owner = username

    user_dir = _get_user_courses_dir(orig_owner)
    fp = os.path.join(user_dir, f"{safe_id}.json")

    bp_dict = payload.get("blueprint") or payload.get("blueprint_dict") or existing.get("blueprint") or {}
    meta = bp_dict.get("metadata", {})

    now_iso = datetime.now().isoformat(timespec="seconds")
    created_at = existing.get("created_at") or now_iso

    course_code = (payload.get("course_code") or meta.get("course_code") or existing.get("course_code") or "Course").strip()
    course_title = (payload.get("course_title") or meta.get("course_title") or existing.get("course_title") or "").strip()
    section = (payload.get("section") or meta.get("section") or existing.get("section") or "1A").strip()
    semester_ay = (payload.get("semester_ay") or meta.get("semester_ay") or existing.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()
    if payload.get("schedule"):
        meta["schedule"] = str(payload.get("schedule")).strip()

    # Enforce syllabus workflow locks on blueprint (existing workflow cannot be forged)
    wf = existing.get("workflow") or payload.get("workflow") or syllabus_workflow.default_workflow()
    temp_doc = {"blueprint": existing.get("blueprint"), "workflow": wf, "owner": username}
    bp_dict = syllabus_workflow.enforce_locks(temp_doc, bp_dict)
    _sync_cqi_plan({"blueprint": bp_dict})

    # Allow students and score entries to persist freely during course setup & operation
    pass

    # Enforce class record grade locks (freeze student scores when under sign-off or finalized)
    cr_wf = existing.get("class_record_workflow") or payload.get("class_record_workflow") or class_record_workflow.default_class_record_workflow(username)
    if existing and class_record_workflow.is_class_record_locked({"class_record_workflow": cr_wf}):
        old_bp = existing.get("blueprint") or {}
        if "students" in old_bp:
            bp_dict["students"] = old_bp["students"]
        if "categories" in old_bp:
            bp_dict["categories"] = old_bp["categories"]

    # Merge and preserve student assessment score & paper acknowledgments
    # so that faculty saves or auto-saves never wipe out student acknowledgments!
    existing_students = (existing.get("blueprint") or {}).get("students") or []
    existing_ack_map = {}
    for st in existing_students:
        s_id = str(st.get("student_id") or "").strip().lower()
        if s_id and st.get("assessment_acknowledgments"):
            existing_ack_map[s_id] = dict(st.get("assessment_acknowledgments") or {})

    # Also include acknowledgments recorded in data/students.json
    try:
        from student_store import _load_students
        all_students_store = _load_students()
        for s_norm_id, s_prof in all_students_store.items():
            c_acks = (s_prof.get("assessment_acknowledgments") or {}).get(safe_id) or {}
            if c_acks:
                st_id_clean = str(s_prof.get("student_id") or s_norm_id).strip().lower()
                target_acks = existing_ack_map.setdefault(st_id_clean, {})
                for it_id, ack_entry in c_acks.items():
                    if it_id not in target_acks or (not target_acks[it_id].get("acknowledged") and ack_entry.get("acknowledged")):
                        target_acks[it_id] = ack_entry
    except Exception:
        pass

    for st in bp_dict.get("students", []):
        s_id = str(st.get("student_id") or "").strip().lower()
        s_digits = re.sub(r"\D", "", s_id)
        matched_acks = existing_ack_map.get(s_id)
        if not matched_acks and s_digits and len(s_digits) >= 4:
            for k_id, v_acks in existing_ack_map.items():
                k_digits = re.sub(r"\D", "", k_id)
                if k_digits and k_digits == s_digits:
                    matched_acks = v_acks
                    break

        if matched_acks:
            cur_acks = st.setdefault("assessment_acknowledgments", {})
            for it_id, ack_val in matched_acks.items():
                if it_id not in cur_acks or not cur_acks[it_id].get("acknowledged"):
                    cur_acks[it_id] = ack_val
                elif not cur_acks[it_id].get("signature_data") and ack_val.get("signature_data"):
                    cur_acks[it_id]["signature_data"] = ack_val.get("signature_data")

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

    # Sanitize & extract authors
    raw_authors = payload.get("authors") or meta.get("authors") or existing.get("authors") or []
    temp_auth_doc = {"owner": orig_owner, "authors": raw_authors, "blueprint": bp_dict}
    cleaned_authors = get_doc_authors(temp_auth_doc)
    if "metadata" in bp_dict:
        bp_dict["metadata"]["authors"] = cleaned_authors

    acks = payload.get("student_acknowledgments") or existing.get("student_acknowledgments") or (wf.get("student_acknowledgments") if isinstance(wf, dict) else None) or []
    if isinstance(wf, dict) and "student_acknowledgments" not in wf and acks:
        wf["student_acknowledgments"] = acks

    doc = {
        "id": safe_id,
        "owner": orig_owner,
        "authors": cleaned_authors,
        "created_at": created_at,
        "updated_at": now_iso,
        "course_code": course_code,
        "course_title": course_title,
        "section": section,
        "semester_ay": semester_ay,
        "schedule": meta.get("schedule") or "TBA",
        "blueprint": bp_dict,
        "workflow": wf,
        "class_record_workflow": cr_wf,
        "student_acknowledgments": acks,
    }

    # Synchronize activities to categories if categories empty
    sync_blueprint_assessments_from_activities(bp_dict)
    auto_generate_class_record(doc)

    # Save to SQLite
    try:
        import db_persistence
        db_persistence.save_course_to_db(doc)
    except Exception as _e:
        logger.warning("Error saving course to SQLite: %s", _e)

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
    credit_units: Optional[str] = None,
    lec_lab: Optional[str] = None,
    contact_hours: Optional[str] = None,
    lecture_units: Optional[float] = None,
    lab_units: Optional[float] = None,
    schedule: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a new subject entry under the user's account with multi-program & multi-section support.
    """
    # Ensure course_code never includes title
    if course_code and (" - " in course_code or " – " in course_code):
        delim = " - " if " - " in course_code else " – "
        parts = course_code.split(delim, 1)
        course_code = parts[0].strip()
        if not course_title or course_title == "Untitled Subject" or course_title == "Electrical Circuits 1":
            course_title = parts[1].strip()

    course_id = f"c_{uuid.uuid4().hex[:10]}"

    init_sections = sections or ([s.strip() for s in section.split(",") if s.strip()] if section else ["EE 2A"])
    init_section = ", ".join(init_sections)
    init_programs = programs or []

    # Auto-resolve faculty_name to account holder if blank
    if not faculty_name:
        try:
            from auth import _load_users
            u_info = _load_users().get(username, {})
            faculty_name = u_info.get("full_name") or ""
        except Exception:
            pass
    if not faculty_name:
        faculty_name = "Elwin Jay J. Tano"

    from sample_syllabus import get_designated_program_heads, DEFAULT_ORIENTATION_ROW, parse_sdg_string_to_table, parse_prereqs_coreqs_to_table
    from models import get_default_policies_table
    import academic_db

    heads = get_designated_program_heads(init_programs)
    computed_ph = " / ".join(heads)

    clean_course_code = course_code.strip()
    if " - " in clean_course_code or " – " in clean_course_code:
        clean_course_code = clean_course_code.split(" - ")[0].split(" – ")[0].strip()

    primary_prog = init_programs[0] if init_programs else "BSEE"
    db_course = academic_db.get_course(clean_course_code, primary_prog) or academic_db.get_course(clean_course_code)

    if from_catalog and catalog_course_data:
        cat_code = (catalog_course_data.get("code") or clean_course_code).strip()
        if " - " in cat_code or " – " in cat_code:
            cat_code = cat_code.split(" - ")[0].split(" – ")[0].strip()
        cat_title = (catalog_course_data.get("title") or (db_course.get("course_title") if db_course else "") or course_title).strip()
        cat_yr = catalog_course_data.get("year_level") or (db_course.get("year_level") if db_course else "") or "Second Year"
        cat_sdgs = catalog_course_data.get("sdgs") or (db_course.get("sdgs") if db_course else "") or "7: Affordable and Clean Energy; 9: Industry, Innovation, and Infrastructure"
        prereqs = catalog_course_data.get("prereqs") or (db_course.get("prerequisites") if db_course else "") or ""
        coreqs = catalog_course_data.get("coreqs") or (db_course.get("corequisites") if db_course else "") or ""
        units = credit_units or catalog_course_data.get("credit_units") or (db_course.get("credit_units") if db_course else "") or "3.0 Units – Lecture"
        lec_lab_val = lec_lab or catalog_course_data.get("lec_lab") or (db_course.get("lec_lab") if db_course else "") or "Lecture"
        contact_hours_val = contact_hours or catalog_course_data.get("hours") or (db_course.get("contact_hours") if db_course else "") or "3 Hours/Week"
        desc = catalog_course_data.get("description") or (db_course.get("description") if db_course else "") or ""
        cat_pgo_pi = catalog_course_data.get("pgo_pi") or (db_course.get("pgo") if db_course else "") or ""

        bp = get_blank_blueprint(
            course_code=cat_code,
            course_title=cat_title,
            section=init_section,
            semester_ay=semester_ay,
            faculty_name=faculty_name,
            credit_units=units,
            lecture_units=lecture_units,
            lab_units=lab_units,
            lec_lab=lec_lab_val,
            contact_hours=contact_hours_val,
            course_description=desc,
            prerequisites=prereqs,
            corequisites=coreqs,
            programs=init_programs if init_programs else None,
            sections=init_sections,
            program_head=computed_ph,
            dean_name="Joie D. Cataytay",
            year_level=cat_yr,
            sdg_alignments=cat_sdgs,
            pgo_pi_str=cat_pgo_pi,
            schedule=schedule or "TBA",
        )
        bp.metadata.program_heads = heads
        bp.metadata.passing_percentage = 75.0
        bp.metadata.year_level = cat_yr
        bp.metadata.sdg_alignments = cat_sdgs
        bp.metadata.workload_description = ""
        bp.metadata.prereq_coreq_table = []
        bp.metadata.sdg_table = []
        bp.metadata.syllabus_assessment_activities = [{"type": "Summative", "code": "", "activity": "", "description": "", "clo_aligned": "", "weight_pct": 0, "items_midterm": 1, "items_finals": 1, "items_per_term": 1, "is_major_assessment": False, "major_scope": "independent", "lec_lab": "Lecture", "rubric_ref": ""}]
        bp.metadata.learning_plan_table = [dict(DEFAULT_ORIENTATION_ROW)]
        bp.metadata.references_table = [{"code": "[1]", "reference": ""}]
        bp.metadata.policies_table = get_default_policies_table()
        is_lec_lab = (bp.metadata.lab_units > 0 and bp.metadata.lecture_units > 0) or ("integrated" in str(bp.metadata.credit_units).lower() or "lecture/laboratory" in str(bp.metadata.lec_lab).lower())
        if is_lec_lab:
            bp.metadata.grading_system_type = "lecture_lab"
            bp.metadata.lecture_weight = 75.0
            bp.metadata.lab_weight = 25.0
        bp_dict = bp.to_dict()
    else:
        cust_title = course_title
        cust_yr = "Second Year"
        cust_prereqs = ""
        cust_coreqs = ""
        cust_units = "3.0 Units – Lecture"
        cust_lec_lab = "Lecture"
        cust_hours = "3 Hours/Week"
        cust_desc = ""
        cust_sdgs = "7: Affordable and Clean Energy; 9: Industry, Innovation, and Infrastructure"

        if credit_units:
            cust_units = credit_units
        if lec_lab:
            cust_lec_lab = lec_lab
        if contact_hours:
            cust_hours = contact_hours

        if db_course:
            if not cust_title or cust_title in ("Untitled Subject", "New Course"):
                cust_title = db_course.get("course_title") or cust_title
            cust_yr = db_course.get("year_level") or cust_yr
            cust_prereqs = db_course.get("prerequisites") or ""
            cust_coreqs = db_course.get("corequisites") or ""
            if not credit_units:
                cust_units = db_course.get("credit_units") or cust_units
            if not lec_lab:
                cust_lec_lab = db_course.get("lec_lab") or cust_lec_lab
            if not contact_hours:
                cust_hours = db_course.get("contact_hours") or cust_hours
            cust_desc = db_course.get("description") or ""
            cust_sdgs = db_course.get("sdgs") or cust_sdgs

        bp = get_blank_blueprint(
            course_code=clean_course_code,
            course_title=cust_title,
            section=init_section,
            semester_ay=semester_ay,
            faculty_name=faculty_name,
            credit_units=cust_units,
            lecture_units=lecture_units,
            lab_units=lab_units,
            lec_lab=cust_lec_lab,
            contact_hours=cust_hours,
            course_description=cust_desc,
            prerequisites=cust_prereqs,
            corequisites=cust_coreqs,
            programs=init_programs if init_programs else None,
            sections=init_sections,
            program_head=computed_ph,
            dean_name="Joie D. Cataytay",
            year_level=cust_yr,
            sdg_alignments=cust_sdgs,
            pgo_pi_str=(db_course.get("pgo") if db_course else "") or "",
            schedule=schedule or "TBA",
        )
        bp.metadata.program_heads = heads
        bp.metadata.passing_percentage = 75.0
        bp.metadata.year_level = cust_yr
        bp.metadata.sdg_alignments = cust_sdgs
        bp.metadata.workload_description = ""
        bp.metadata.prereq_coreq_table = []
        bp.metadata.sdg_table = []
        bp.metadata.syllabus_assessment_activities = [{"type": "Summative", "code": "", "activity": "", "description": "", "clo_aligned": "", "weight_pct": 0, "items_midterm": 1, "items_finals": 1, "items_per_term": 1, "is_major_assessment": False, "major_scope": "independent", "lec_lab": "Lecture", "rubric_ref": ""}]
        bp.metadata.learning_plan_table = [dict(DEFAULT_ORIENTATION_ROW)]
        bp.metadata.references_table = [{"code": "[1]", "reference": ""}]
        bp.metadata.policies_table = get_default_policies_table()
        is_lec_lab = (bp.metadata.lab_units > 0 and bp.metadata.lecture_units > 0) or ("integrated" in str(bp.metadata.credit_units).lower() or "lecture/laboratory" in str(bp.metadata.lec_lab).lower())
        if is_lec_lab:
            bp.metadata.grading_system_type = "lecture_lab"
            bp.metadata.lecture_weight = 75.0
            bp.metadata.lab_weight = 25.0
        bp_dict = bp.to_dict()

    payload = {
        "course_code": bp.metadata.course_code,
        "course_title": bp.metadata.course_title,
        "section": init_section,
        "sections": init_sections,
        "programs": bp.metadata.programs,
        "semester_ay": semester_ay,
        "schedule": bp.metadata.schedule or schedule or "TBA",
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

    auto_generate_class_record(new_doc)
    try:
        import db_persistence
        db_persistence.save_course_to_db(new_doc)
    except Exception:
        pass

    user_dir = _get_user_courses_dir(username)
    fp = os.path.join(user_dir, f"{new_id}.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(new_doc, f, indent=2)

    return new_doc


def delete_course(username_or_course_id: str, course_id: Optional[str] = None) -> bool:
    target_id_for_db = course_id if course_id is not None else username_or_course_id
    safe_db_id = re.sub(r"[^A-Za-z0-9_-]+", "", target_id_for_db)
    try:
        import db_persistence
        db_persistence.delete_course_from_db(safe_db_id)
    except Exception:
        pass
    if course_id is None:
        target_id = username_or_course_id
        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", target_id)
        if os.path.exists(COURSES_BASE_DIR):
            for uname in os.listdir(COURSES_BASE_DIR):
                user_dir = os.path.join(COURSES_BASE_DIR, uname)
                if os.path.isdir(user_dir):
                    fp = os.path.join(user_dir, f"{safe_id}.json")
                    if os.path.exists(fp):
                        try:
                            os.remove(fp)
                            return True
                        except Exception:
                            return False
        return False
    else:
        username = username_or_course_id
        user_dir = _get_user_courses_dir(username)
        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
        fp = os.path.join(user_dir, f"{safe_id}.json")
        if os.path.exists(fp):
            try:
                os.remove(fp)
                return True
            except Exception:
                return False
        if os.path.exists(COURSES_BASE_DIR):
            for uname in os.listdir(COURSES_BASE_DIR):
                u_dir = os.path.join(COURSES_BASE_DIR, uname)
                if os.path.isdir(u_dir):
                    f_path = os.path.join(u_dir, f"{safe_id}.json")
                    if os.path.exists(f_path):
                        try:
                            os.remove(f_path)
                            return True
                        except Exception:
                            return False
        return False


def find_course(course_id: str) -> Optional[Dict[str, Any]]:
    """Finds a course by course_id across all user workspaces."""
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", course_id)
    try:
        import db_persistence
        db_doc = db_persistence.load_course_from_db(safe_id)
        if db_doc:
            bp = db_doc.get("blueprint")
            if isinstance(bp, dict):
                if "rubrics" not in bp:
                    bp["rubrics"] = []
                sync_blueprint_assessments_from_activities(bp)
            _sync_student_acknowledgments_from_store(db_doc)
            _sync_cqi_plan(db_doc)
            auto_generate_class_record(db_doc)
            return db_doc
    except Exception:
        pass
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
                        _sync_student_acknowledgments_from_store(doc)
                        _sync_cqi_plan(doc)
                        auto_generate_class_record(doc)
                        return doc
                except Exception:
                    continue
    return None


def save_course_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Saves an entire course document back to its owner's storage, syncing authors."""
    _sync_cqi_plan(doc)
    auto_generate_class_record(doc)
    owner = doc.get("owner") or "default"
    user_dir = _get_user_courses_dir(owner)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", doc["id"])
    fp = os.path.join(user_dir, f"{safe_id}.json")
    doc["updated_at"] = datetime.now().isoformat(timespec="seconds")
    authors = get_doc_authors(doc)
    doc["authors"] = authors
    bp = doc.get("blueprint") or {}
    if "tos" in doc and isinstance(bp, dict):
        bp["tos"] = doc["tos"]
    if "metadata" in bp:
        bp["metadata"]["authors"] = authors
    _sync_student_acknowledgments_from_store(doc)
    bp_doc = doc.get("blueprint")
    if isinstance(bp_doc, dict):
        sync_blueprint_assessments_from_activities(bp_doc)
    try:
        import db_persistence
        db_persistence.save_course_to_db(doc)
    except Exception as _e:
        logger.warning("Error saving course doc to SQLite: %s", _e)
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
