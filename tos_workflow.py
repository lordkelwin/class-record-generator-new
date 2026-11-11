"""
Table of Specifications (TOS) & TOS Test Review Workflow.

Manages:
  - Dynamic synchronization from Dean-approved Course Syllabus (Midterm & Final terms).
  - Inheritance of Course Details, Topics, CLOs, and Syllabus Review Committee.
  - Multi-stage 5-step approval workflow for both Midterm and Final Term TOS:
      Stage 1: Faculty Drafting & Digital Signature -> Submitted to Committee
      Stage 2: Committee Members Review & FM-USeP-MID-04 Review Form completion
      Stage 3: Committee Head Review & Endorsement
      Stage 4: College QA Head Review & Quality Compliance Sign-off
      Stage 5: College Dean Approval & Signature (Locked & Sealed)
  - Controlled Document state tracking (FM-USeP-MID-03 & FM-USeP-MID-04).
"""
import copy
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

TOS_STAGES = [
    {"stage": 1, "key": "drafting", "label": "Faculty Drafting & Signature", "status": "draft"},
    {"stage": 2, "key": "committee_review", "label": "Committee Members Review (FM-USeP-MID-04)", "status": "committee_review"},
    {"stage": 3, "key": "committee_head_review", "label": "Committee Head Endorsement", "status": "committee_head_review"},
    {"stage": 4, "key": "qa_review", "label": "College QA Head Verification", "status": "qa_review"},
    {"stage": 5, "key": "dean_approval", "label": "College Dean Final Approval", "status": "for_dean_approval"},
]

STAGE_STATUS_LABELS = {
    "draft": "Drafting",
    "submitted": "Submitted for Committee Review",
    "committee_review": "Committee Members Review (FM-USeP-MID-04)",
    "committee_head_review": "For Committee Chair Endorsement",
    "qa_review": "For College QA Head Sign-off",
    "for_dean_approval": "For College Dean Approval",
    "approved": "Approved & Locked (Official Controlled Document)",
    "returned": "Returned for Revision",
}

EDITABLE_STATUSES = {"draft", "returned"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_default_cognitive_weights() -> Dict[str, float]:
    """Default Bloom's cognitive taxonomy distribution targets."""
    return {
        "remembering": 20.0,
        "understanding": 30.0,
        "applying_analyzing": 35.0,
        "evaluating_creating": 15.0,
    }


def compute_tos_totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes row totals, column sums, and percentage distribution across Bloom's levels."""
    rem_sum = 0
    und_sum = 0
    app_sum = 0
    eva_sum = 0
    total_points = 0
    total_hours = 0.0

    updated_rows = []
    item_counter = 1

    for r in rows:
        row = dict(r)
        rem = int(row.get("remembering") or 0)
        und = int(row.get("understanding") or 0)
        app = int(row.get("applying_analyzing") or 0)
        eva = int(row.get("evaluating_creating") or 0)
        row_points = rem + und + app + eva

        hrs = float(row.get("time_allotment_hours") or 0.0)
        total_hours += hrs

        row["remembering"] = rem
        row["understanding"] = und
        row["applying_analyzing"] = app
        row["evaluating_creating"] = eva
        row["total_points"] = row_points

        # Calculate default item placement if empty
        if not row.get("item_placement") and row_points > 0:
            end_item = item_counter + row_points - 1
            row["item_placement"] = f"{item_counter}-{end_item}" if row_points > 1 else str(item_counter)
            item_counter = end_item + 1
        elif row_points > 0:
            # If item placement string is provided, try tracking last item
            m = re.findall(r"\d+", str(row.get("item_placement", "")))
            if m:
                item_counter = max(item_counter, int(m[-1]) + 1)

        rem_sum += rem
        und_sum += und
        app_sum += app
        eva_sum += eva
        total_points += row_points
        updated_rows.append(row)

    grand_total = total_points if total_points > 0 else 1
    pct_rem = round((rem_sum / grand_total) * 100, 1) if total_points > 0 else 0.0
    pct_und = round((und_sum / grand_total) * 100, 1) if total_points > 0 else 0.0
    pct_app = round((app_sum / grand_total) * 100, 1) if total_points > 0 else 0.0
    pct_eva = round((eva_sum / grand_total) * 100, 1) if total_points > 0 else 0.0

    return {
        "rows": updated_rows,
        "totals": {
            "remembering": rem_sum,
            "understanding": und_sum,
            "applying_analyzing": app_sum,
            "evaluating_creating": eva_sum,
            "total_points": total_points,
            "total_hours": round(total_hours, 1),
            "pct_remembering": pct_rem,
            "pct_understanding": pct_und,
            "pct_applying_analyzing": pct_app,
            "pct_evaluating_creating": pct_eva,
        }
    }


def parse_hours_from_time_frame(time_frame: str) -> float:
    """Extracts numeric instructional hours from time frame strings like 'Week 1-2 (6 hours)' or '4.5 hrs'."""
    if not time_frame:
        return 3.0
    s = str(time_frame).lower()
    m_hrs = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours|hour|hrs|hr)", s)
    if m_hrs:
        try:
            return float(m_hrs.group(1))
        except Exception:
            pass
    m_weeks = re.search(r"week[s]?\s*(\d+)(?:\s*-\s*(\d+))?", s)
    if m_weeks:
        w_start = int(m_weeks.group(1))
        w_end = int(m_weeks.group(2)) if m_weeks.group(2) else w_start
        weeks_count = max(1, (w_end - w_start) + 1)
        return float(weeks_count * 3)  # default 3 hours per week
    m_num = re.search(r"(\d+(?:\.\d+)?)", s)
    if m_num:
        try:
            return float(m_num.group(1))
        except Exception:
            pass
    return 3.0


def extract_syllabus_term_topics(doc: Dict[str, Any], term: str = "midterm") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts relevant topic rows and CLOs from the approved course syllabus.
    Returns: (term_topics, all_clos)
    """
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    lp = meta.get("learning_plan_table") or bp.get("learning_plan") or []

    clos = []
    for co in bp.get("course_outcomes") or []:
        co_id = co.get("co_id") or co.get("id") or "CLO"
        co_desc = co.get("description") or ""
        clos.append({"id": co_id, "label": f"{co_id}: {co_desc[:80]}..." if len(co_desc) > 80 else f"{co_id}: {co_desc}"})

    if not lp:
        # Fallback to default topics if learning plan is empty
        fallback_topics = [
            {"topic": "Fundamental Principles and Theoretical Framework", "clo": "CLO1", "hours": 9.0},
            {"topic": "Network Laws, Analysis Methods, and Circuit Equations", "clo": "CLO1", "hours": 12.0},
            {"topic": "Applied Problem Solving and Empirical Verification", "clo": "CLO2", "hours": 9.0},
        ] if term == "midterm" else [
            {"topic": "Advanced Systematic Modeling and Dynamic Responses", "clo": "CLO2", "hours": 12.0},
            {"topic": "Complex System Optimization and Frequency Analysis", "clo": "CLO2", "hours": 9.0},
            {"topic": "Integrated Synthesis, Comprehensive Evaluation, and Design", "clo": "CLO2", "hours": 9.0},
        ]
        res = []
        for i, ft in enumerate(fallback_topics, 1):
            res.append({
                "id": f"row_{i}",
                "topic": ft["topic"],
                "clo": ft["clo"],
                "time_allotment_hours": ft["hours"],
                "remembering": 3,
                "understanding": 4,
                "applying_analyzing": 5,
                "evaluating_creating": 3,
                "total_points": 15,
                "item_placement": f"{(i-1)*15 + 1}-{i*15}",
            })
        return res, clos

    # Locate Midterm exam row delimiter
    mid_idx = -1
    for i, row in enumerate(lp):
        topic_txt = (row.get("topics") or "").upper()
        if "MIDTERM" in topic_txt and "EXAM" in topic_txt:
            mid_idx = i
            break
        elif "MIDTERM" in topic_txt:
            mid_idx = i

    if mid_idx == -1:
        # Divide by week numbers or split roughly in half
        mid_idx = max(1, len(lp) // 2)

    if term.lower() == "midterm":
        raw_rows = lp[:mid_idx]
    else:
        raw_rows = lp[mid_idx + 1:] if mid_idx < len(lp) else lp[mid_idx:]

    term_rows = []
    item_counter = 1
    row_num = 1

    for row in raw_rows:
        topic_txt = (row.get("topics") or "").strip()
        # Clean topic: remove bullets, exam markers, or orientation
        clean_top = re.sub(r"^[\s•\-*]+", "", topic_txt).strip()
        if not clean_top or "ORIENTATION" in clean_top.upper() or "VISION" in clean_top.upper():
            continue
        if "FINAL EXAMINATION" in clean_top.upper() or "MIDTERM EXAMINATION" in clean_top.upper():
            continue

        ilo_txt = (row.get("ilo") or "").strip()
        clean_ilo = re.sub(r"^[\s•\-*]+", "", ilo_txt).strip()
        display_topic = clean_top
        if clean_ilo and len(clean_ilo) > 10:
            display_topic = f"{clean_top}\n({clean_ilo[:90]}...)" if len(clean_ilo) > 90 else f"{clean_top}\n({clean_ilo})"

        row_clo = (row.get("clo") or "CLO1").strip().replace("\n", ", ")
        hrs = parse_hours_from_time_frame(row.get("time_frame") or "")

        # Default distributed points (e.g. 10 pts per 3 hrs topic)
        base_pts = max(5, int(hrs * 2))
        rem = max(1, int(base_pts * 0.20))
        und = max(1, int(base_pts * 0.30))
        app = max(1, int(base_pts * 0.35))
        eva = max(1, base_pts - (rem + und + app))
        pts = rem + und + app + eva

        end_item = item_counter + pts - 1
        placement = f"{item_counter}-{end_item}" if pts > 1 else str(item_counter)
        item_counter = end_item + 1

        term_rows.append({
            "id": f"row_{row_num}",
            "topic": display_topic,
            "clo": row_clo,
            "time_allotment_hours": hrs,
            "remembering": rem,
            "understanding": und,
            "applying_analyzing": app,
            "evaluating_creating": eva,
            "total_points": pts,
            "item_placement": placement,
        })
        row_num += 1

    if not term_rows:
        # If filtered rows was empty, add a default topic
        term_rows.append({
            "id": "row_1",
            "topic": f"Core Competencies and Applied Principles ({term.title()})",
            "clo": "CLO1",
            "time_allotment_hours": 9.0,
            "remembering": 5,
            "understanding": 10,
            "applying_analyzing": 15,
            "evaluating_creating": 5,
            "total_points": 35,
            "item_placement": "1-35",
        })

    return term_rows, clos


def build_default_tos(doc: Dict[str, Any], term: str = "midterm") -> Dict[str, Any]:
    """Constructs a fresh TOS record for the specified term synced from the course syllabus."""
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    wf = doc.get("workflow") or {}

    course_code = meta.get("course_code") or doc.get("course_code") or "EE 211"
    course_title = meta.get("course_title") or doc.get("course_title") or "Course Title"
    semester_ay = meta.get("semester_ay") or doc.get("semester_ay") or "1st Semester, A.Y. 2026-2027"

    # Parse semester and academic year
    sem = meta.get("semester")
    ay = meta.get("academic_year")
    if not sem or not ay:
        m_sem = re.search(r"(1st|2nd|Summer)\s*Semester", semester_ay, re.I)
        m_ay = re.search(r"(\d{4}\s*-\s*\d{4})", semester_ay)
        sem = m_sem.group(0) if m_sem else "1st Semester"
        ay = m_ay.group(1) if m_ay else "2026-2027"

    term_label = "Midterm" if term.lower() == "midterm" else "Final Term"
    exam_period = f"{term_label} Examination, {sem}, A.Y. {ay}"

    # Review committee members inheritance
    comm_members = copy.deepcopy(wf.get("committee_members") or [])
    chair = next((m for m in comm_members if m.get("role") == "Review Committee Chair"), None)
    chair_name = chair.get("name") if chair else wf.get("assigned_committee_name") or "Committee Chair"
    chair_uname = chair.get("username") if chair else wf.get("assigned_committee")

    rows, clos = extract_syllabus_term_topics(doc, term)
    totals_res = compute_tos_totals(rows)

    return {
        "term": term.lower(),
        "status": "draft",
        "stage": 1,
        "revision_type": "new",  # "new" | "revised" | "no_change"
        "no_change_sem_ay": "",
        "course_code": course_code,
        "course_title": course_title,
        "credit_units": meta.get("credit_units") or "3.0 Units",
        "academic_unit": meta.get("academic_unit") or meta.get("department") or "Engineering",
        "college": meta.get("college") or "COLLEGE OF ENGINEERING",
        "program_name": meta.get("program_name") or "Bachelor of Science in Electrical Engineering",
        "faculty_name": meta.get("faculty_name") or doc.get("owner_name") or "Faculty",
        "faculty_username": doc.get("owner") or "faculty",
        "program_head": meta.get("program_head") or "Charito O. Claro",
        "dean_name": meta.get("dean_name") or "Joie D. Cataytay",
        "semester": sem,
        "academic_year": ay,
        "examination_period": exam_period,
        "course_description": bp.get("course_description") or meta.get("course_description") or "Course description and fundamental competencies.",
        "rows": totals_res["rows"],
        "totals": totals_res["totals"],
        "available_clos": clos,
        "committee_members": comm_members,
        "committee_chair_name": chair_name,
        "committee_chair_username": chair_uname,
        "review_form": {
            "comments_suggestions": "The Table of Specifications strictly aligns with the approved course syllabus topics, hours allotment, and cognitive domain balance.",
            "recommendation": "approved_without_revision",
            "reviewed_at": None,
            "reviewer_name": None,
            "reviewer_username": None,
        },
        "signatures": {
            "faculty": None,
            "committee_members": [],
            "committee_chair": None,
            "qa_head": None,
            "dean": None,
        },
        "history": [
            {
                "action": "initialized",
                "actor": doc.get("owner") or "system",
                "actor_name": meta.get("faculty_name") or "System",
                "timestamp": _now(),
                "remarks": f"TOS initialized and synchronized from approved syllabus for {term_label}."
            }
        ],
        "created_at": _now(),
        "updated_at": _now(),
        "approved_at": None,
    }


def get_course_tos(doc: Dict[str, Any], term: str = "midterm") -> Dict[str, Any]:
    """Retrieves or initializes the TOS document for the requested term."""
    tos_store = doc.setdefault("tos", {})
    term_key = term.lower()
    if term_key not in tos_store or not isinstance(tos_store[term_key], dict):
        tos_store[term_key] = build_default_tos(doc, term_key)
    return tos_store[term_key]


def sync_tos_from_syllabus(doc: Dict[str, Any], term: str = "midterm", user_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Forces dynamic re-synchronization of course details, committee members, and topics from syllabus."""
    tos_store = doc.setdefault("tos", {})
    term_key = term.lower()
    existing = tos_store.get(term_key)

    new_tos = build_default_tos(doc, term_key)

    if existing and existing.get("status") not in EDITABLE_STATUSES and existing.get("status") != "draft":
        raise ValueError(f"Cannot re-sync TOS while in '{existing.get('status')}' state. Re-synchronization is only permitted during Drafting or Revision.")

    # Preserve any customized row points if topics match
    if existing and existing.get("rows"):
        old_map = {r.get("topic", "").strip(): r for r in existing["rows"]}
        merged_rows = []
        for r in new_tos["rows"]:
            top = r.get("topic", "").strip()
            if top in old_map:
                old = old_map[top]
                r["remembering"] = old.get("remembering", r["remembering"])
                r["understanding"] = old.get("understanding", r["understanding"])
                r["applying_analyzing"] = old.get("applying_analyzing", r["applying_analyzing"])
                r["evaluating_creating"] = old.get("evaluating_creating", r["evaluating_creating"])
                r["item_placement"] = old.get("item_placement", r["item_placement"])
            merged_rows.append(r)
        new_tos["rows"] = merged_rows
        new_tos["totals"] = compute_tos_totals(merged_rows)["totals"]

    # Preserve history
    if existing and existing.get("history"):
        new_tos["history"] = existing["history"]

    actor_name = user_info.get("name") if user_info else "Faculty"
    actor_uname = user_info.get("username") if user_info else doc.get("owner", "faculty")
    new_tos["history"].append({
        "action": "re_synced",
        "actor": actor_uname,
        "actor_name": actor_name,
        "timestamp": _now(),
        "remarks": f"Re-synchronized course details and learning plan topics from Dean-approved syllabus."
    })

    tos_store[term_key] = new_tos
    return new_tos


def save_tos_draft(doc: Dict[str, Any], term: str, tos_data: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Saves faculty modifications to the TOS matrix during Stage 1 drafting."""
    current_tos = get_course_tos(doc, term)
    status = current_tos.get("status", "draft")

    if status not in EDITABLE_STATUSES and user.get("role") != "admin":
        raise PermissionError(f"TOS is currently locked for review in '{STAGE_STATUS_LABELS.get(status, status)}' stage. Editing is disabled.")

    # Update metadata
    if "revision_type" in tos_data:
        current_tos["revision_type"] = tos_data["revision_type"]
    if "no_change_sem_ay" in tos_data:
        current_tos["no_change_sem_ay"] = tos_data["no_change_sem_ay"]
    if "examination_period" in tos_data:
        current_tos["examination_period"] = tos_data["examination_period"]

    # Update rows and recompute totals
    if "rows" in tos_data and isinstance(tos_data["rows"], list):
        res = compute_tos_totals(tos_data["rows"])
        current_tos["rows"] = res["rows"]
        current_tos["totals"] = res["totals"]

    current_tos["updated_at"] = _now()
    return current_tos


def submit_tos_to_committee(doc: Dict[str, Any], term: str, user: Dict[str, Any], signature_data: Optional[str] = None) -> Dict[str, Any]:
    """Stage 1: Faculty applies signature and submits TOS to Review Committee."""
    current_tos = get_course_tos(doc, term)
    status = current_tos.get("status", "draft")

    if status not in EDITABLE_STATUSES and user.get("role") != "admin":
        raise PermissionError("TOS has already been submitted and cannot be re-submitted.")

    # Faculty signature resolution
    sig_data = signature_data or user.get("signature_data")
    if not sig_data and not user.get("has_signature") and user.get("role") != "admin":
        raise ValueError("An e-signature is required before submitting the Table of Specifications.")

    current_tos["signatures"]["faculty"] = {
        "name": user.get("name") or user.get("full_name") or current_tos.get("faculty_name"),
        "username": user.get("username"),
        "signed_at": _now(),
        "signature_data": sig_data,
    }

    current_tos["status"] = "committee_review"
    current_tos["stage"] = 2
    current_tos["updated_at"] = _now()

    current_tos["history"].append({
        "action": "submitted",
        "actor": user.get("username"),
        "actor_name": user.get("name") or user.get("full_name") or "Faculty",
        "timestamp": _now(),
        "remarks": "Submitted TOS to Course Review Committee with faculty signature."
    })

    return current_tos


def review_tos_committee(
    doc: Dict[str, Any],
    term: str,
    user: Dict[str, Any],
    comments: str,
    recommendation: str = "approved_without_revision",
    signature_data: Optional[str] = None,
    decision: str = "approved",
    remarks: str = "",
) -> Dict[str, Any]:
    """Stage 2: Course Review Committee fills out FM-USeP-MID-04 and endorses/returns."""
    current_tos = get_course_tos(doc, term)
    status = current_tos.get("status")

    if status != "committee_review" and user.get("role") != "admin":
        raise PermissionError(f"TOS is not currently in Committee Review (current: {status}).")

    if decision.lower() == "returned":
        current_tos["status"] = "returned"
        current_tos["stage"] = 1
        current_tos["updated_at"] = _now()
        # Reset signatures of the current cycle
        current_tos["signatures"]["committee_members"] = []
        current_tos["signatures"]["committee_chair"] = None
        current_tos["signatures"]["qa_head"] = None
        current_tos["signatures"]["dean"] = None

        current_tos["history"].append({
            "action": "returned_by_committee",
            "actor": user.get("username"),
            "actor_name": user.get("name") or user.get("full_name"),
            "timestamp": _now(),
            "remarks": remarks or comments or "Returned by Committee Member for revisions."
        })
        return current_tos

    # Save review form comments & recommendation
    sig_data = signature_data or user.get("signature_data")
    rf = current_tos.setdefault("review_form", {})
    rf["comments_suggestions"] = comments or rf.get("comments_suggestions") or "Reviewed and verified."
    rf["recommendation"] = recommendation or "approved_without_revision"
    rf["reviewed_at"] = _now()
    rf["reviewer_name"] = user.get("name") or user.get("full_name")
    rf["reviewer_username"] = user.get("username")

    # Append committee signature
    current_tos["signatures"]["committee_members"].append({
        "name": user.get("name") or user.get("full_name"),
        "username": user.get("username"),
        "signed_at": _now(),
        "signature_data": sig_data,
        "recommendation": recommendation,
        "comments": comments,
    })

    # Advance to Stage 3 (Committee Head Endorsement)
    current_tos["status"] = "committee_head_review"
    current_tos["stage"] = 3
    current_tos["updated_at"] = _now()

    current_tos["history"].append({
        "action": "committee_reviewed",
        "actor": user.get("username"),
        "actor_name": user.get("name") or user.get("full_name"),
        "timestamp": _now(),
        "remarks": f"Completed FM-USeP-MID-04 Review Form. Recommendation: {recommendation}."
    })

    return current_tos


def endorse_tos_chair(
    doc: Dict[str, Any],
    term: str,
    user: Dict[str, Any],
    signature_data: Optional[str] = None,
    decision: str = "approved",
    remarks: str = "",
) -> Dict[str, Any]:
    """Stage 3: Review Committee Chair endorses the TOS to QA Head."""
    current_tos = get_course_tos(doc, term)
    status = current_tos.get("status")

    if status != "committee_head_review" and user.get("role") != "admin":
        raise PermissionError(f"TOS is not awaiting Committee Chair endorsement (current: {status}).")

    if decision.lower() == "returned":
        current_tos["status"] = "returned"
        current_tos["stage"] = 1
        current_tos["updated_at"] = _now()
        current_tos["signatures"]["committee_chair"] = None
        current_tos["history"].append({
            "action": "returned_by_chair",
            "actor": user.get("username"),
            "actor_name": user.get("name") or user.get("full_name"),
            "timestamp": _now(),
            "remarks": remarks or "Returned by Committee Chair for revisions."
        })
        return current_tos

    sig_data = signature_data or user.get("signature_data")
    current_tos["signatures"]["committee_chair"] = {
        "name": user.get("name") or user.get("full_name") or current_tos.get("committee_chair_name"),
        "username": user.get("username"),
        "signed_at": _now(),
        "signature_data": sig_data,
        "remarks": remarks,
    }

    current_tos["status"] = "qa_review"
    current_tos["stage"] = 4
    current_tos["updated_at"] = _now()

    current_tos["history"].append({
        "action": "chair_endorsed",
        "actor": user.get("username"),
        "actor_name": user.get("name") or user.get("full_name"),
        "timestamp": _now(),
        "remarks": "Committee Chair endorsed TOS forward to College QA Head."
    })

    return current_tos


def signoff_tos_qa(
    doc: Dict[str, Any],
    term: str,
    user: Dict[str, Any],
    signature_data: Optional[str] = None,
    decision: str = "approved",
    remarks: str = "",
) -> Dict[str, Any]:
    """Stage 4: College QA Head signs off on quality compliance."""
    current_tos = get_course_tos(doc, term)
    status = current_tos.get("status")

    if status != "qa_review" and user.get("role") != "admin":
        raise PermissionError(f"TOS is not awaiting College QA Head verification (current: {status}).")

    if decision.lower() == "returned":
        current_tos["status"] = "returned"
        current_tos["stage"] = 1
        current_tos["updated_at"] = _now()
        current_tos["signatures"]["qa_head"] = None
        current_tos["history"].append({
            "action": "returned_by_qa",
            "actor": user.get("username"),
            "actor_name": user.get("name") or user.get("full_name"),
            "timestamp": _now(),
            "remarks": remarks or "Returned by College QA Head for revisions."
        })
        return current_tos

    sig_data = signature_data or user.get("signature_data")
    current_tos["signatures"]["qa_head"] = {
        "name": user.get("name") or user.get("full_name"),
        "username": user.get("username"),
        "signed_at": _now(),
        "signature_data": sig_data,
        "remarks": remarks,
    }

    current_tos["status"] = "for_dean_approval"
    current_tos["stage"] = 5
    current_tos["updated_at"] = _now()

    current_tos["history"].append({
        "action": "qa_signed_off",
        "actor": user.get("username"),
        "actor_name": user.get("name") or user.get("full_name"),
        "timestamp": _now(),
        "remarks": "College QA Head verified quality compliance and submitted to College Dean."
    })

    return current_tos


def approve_tos_dean(
    doc: Dict[str, Any],
    term: str,
    user: Dict[str, Any],
    signature_data: Optional[str] = None,
    decision: str = "approved",
    remarks: str = "",
) -> Dict[str, Any]:
    """Stage 5: College Dean final approval and sealing."""
    current_tos = get_course_tos(doc, term)
    status = current_tos.get("status")

    if status != "for_dean_approval" and user.get("role") != "admin":
        raise PermissionError(f"TOS is not awaiting College Dean approval (current: {status}).")

    if decision.lower() == "returned":
        current_tos["status"] = "returned"
        current_tos["stage"] = 1
        current_tos["updated_at"] = _now()
        current_tos["signatures"]["dean"] = None
        current_tos["history"].append({
            "action": "returned_by_dean",
            "actor": user.get("username"),
            "actor_name": user.get("name") or user.get("full_name"),
            "timestamp": _now(),
            "remarks": remarks or "Returned by College Dean for revisions."
        })
        return current_tos

    sig_data = signature_data or user.get("signature_data")
    current_tos["signatures"]["dean"] = {
        "name": user.get("name") or user.get("full_name") or current_tos.get("dean_name"),
        "username": user.get("username"),
        "signed_at": _now(),
        "signature_data": sig_data,
    }

    current_tos["status"] = "approved"
    current_tos["stage"] = 5
    current_tos["approved_at"] = _now()
    current_tos["updated_at"] = _now()

    current_tos["history"].append({
        "action": "dean_approved",
        "actor": user.get("username"),
        "actor_name": user.get("name") or user.get("full_name"),
        "timestamp": _now(),
        "remarks": "College Dean officially approved and sealed the Table of Specifications."
    })

    return current_tos


def get_tos_permissions(doc: Dict[str, Any], term: str, user: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates user capabilities for the selected term TOS."""
    if not user:
        return {"can_edit": False, "can_submit": False, "can_review": False, "can_endorse": False, "can_qa_signoff": False, "can_approve": False, "can_return": False}

    current_tos = get_course_tos(doc, term)
    status = current_tos.get("status", "draft")
    is_admin = user.get("role") == "admin"
    wf_roles = set(user.get("workflow_roles") or [])
    uname = user.get("username")

    is_owner = uname == doc.get("owner") or uname == current_tos.get("faculty_username") or is_admin
    is_comm_member = is_admin or "review_committee" in wf_roles or any(m.get("username") == uname for m in current_tos.get("committee_members", []))
    is_chair = is_admin or "review_committee_chair" in wf_roles or current_tos.get("committee_chair_username") == uname
    is_qa = is_admin or "qa_head" in wf_roles or user.get("role") == "qa_head"
    is_dean = is_admin or "dean" in wf_roles or user.get("role") == "dean"

    is_editable = status in EDITABLE_STATUSES

    return {
        "status": status,
        "status_label": STAGE_STATUS_LABELS.get(status, status),
        "stage": current_tos.get("stage", 1),
        "is_approved": status == "approved",
        "is_locked": status not in EDITABLE_STATUSES,
        "can_edit": (is_owner and is_editable) or is_admin,
        "can_submit": (is_owner and is_editable) or is_admin,
        "can_review": (is_comm_member and status == "committee_review") or is_admin,
        "can_endorse": (is_chair and status == "committee_head_review") or is_admin,
        "can_qa_signoff": (is_qa and status == "qa_review") or is_admin,
        "can_approve": (is_dean and status == "for_dean_approval") or is_admin,
        "can_return": is_admin or (status == "committee_review" and is_comm_member) or (status == "committee_head_review" and is_chair) or (status == "qa_review" and is_qa) or (status == "for_dean_approval" and is_dean),
    }
