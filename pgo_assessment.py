"""
End-to-End Program Graduate Outcomes (PGO) Assessment Consolidation Engine.

Consolidates student attainment bottom-up across the OBE pipeline:
    Class Record Scores (Step 4)
        -> Per-SA & Final CLO Assessment Grades (Step 7 / MID-10)
        -> Performance Indicators (PI) with I-E-D Progression
        -> Program Graduate Outcomes (PGO)
        -> Segregated & Grouped by Student ID Number (ID #) and Cohort Prefix

Enforces Role-Based Access Control (RBAC):
  - Program Head, College QA Head, Staff, Associate Dean, Dean, Admin:
      Full program-wide PGO Assessment across all courses, sections, cohorts, and PGOs.
  - Faculty:
      Restricted strictly to PGOs, PIs, and courses aligned with their handled/assigned courses.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import accdb_curriculum
import courses_store
from models import SyllabusBlueprint
from excel_generator import _get_item_clo_points, _get_student_clo_score

logger = logging.getLogger(__name__)

IED_LABELS = {
    "I": "Introductory",
    "E": "Enabling",
    "D": "Demonstrative",
}


def normalize_program_code(code: str) -> str:
    """Normalizes program codes like 'BSEE' -> 'EE', 'BSCE' -> 'CE'."""
    c = str(code or "").strip().upper()
    if c.startswith("BS") and len(c) > 2:
        return c[2:]
    return c


def normalize_course_code(code: str) -> str:
    """Normalizes course code spacing & case (e.g., 'ee  415' -> 'EE 415')."""
    return re.sub(r"\s+", " ", str(code or "").strip().upper())


def extract_cohort_prefix(student_id: str) -> str:
    """Extracts the year/batch cohort prefix from a Student ID (e.g. '2023-00011' -> '2023')."""
    sid = str(student_id or "").strip()
    m = re.match(r"^(\d{4})[-_/]?", sid)
    if m:
        return m.group(1)
    m_yr = re.match(r"^(\d{2})[-_/]", sid)
    if m_yr:
        return f"20{m_yr.group(1)}"
    return "Other"


def format_student_display_name(st: Dict[str, Any]) -> str:
    """Formats student name cleanly in 'Last, First' or fallback form."""
    ln = str(st.get("last_name") or "").strip()
    fn = str(st.get("first_name") or "").strip()
    if ln or fn:
        return f"{ln}, {fn}".strip(", ")
    return str(st.get("name") or st.get("full_name") or st.get("student_id") or "Student").strip()


def get_user_pgo_scope(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Determines the RBAC scope for the PGO Assessment module based on the current user.
    - Program Head, QA Head, Staff, Associate Dean, Dean, Admin -> Program-wide / College-wide access.
    - Pure Faculty -> Restricted to PGOs/PIs/Courses aligned to their handled/assigned courses.
    """
    if not user:
        return {
            "username": "",
            "full_name": "Guest",
            "role": "guest",
            "workflow_roles": [],
            "is_program_wide": False,
            "is_college_wide": False,
            "allowed_programs": [],
            "scope_label": "Restricted",
        }

    username = str(user.get("username") or "").strip()
    full_name = str(user.get("full_name") or username).strip()
    role = str(user.get("role") or "faculty").strip().lower()
    wf_roles = [str(r).strip().lower() for r in (user.get("workflow_roles") or []) if str(r).strip()]
    wf_set = set(wf_roles)
    user_progs = [normalize_program_code(p) if p != "*" else "*" for p in (user.get("program_codes") or []) if str(p).strip()]

    is_admin = (role == "admin") or ("admin" in wf_set)
    is_staff = (role == "staff") or ("staff" in wf_set) or bool(user.get("is_staff"))
    is_dean = ("dean" in wf_set) or ("associate_dean" in wf_set)
    is_qa = ("qa_head" in wf_set)
    is_ph = ("program_head" in wf_set)

    is_program_wide = is_admin or is_staff or is_dean or is_qa or is_ph
    is_college_wide = is_admin or is_staff or is_dean or is_qa or ("*" in user_progs)

    if is_college_wide:
        allowed_programs = ["*"]
    elif is_ph:
        allowed_programs = [p for p in user_progs if p != "*"] or ["EE"]
    else:
        allowed_programs = [p for p in user_progs if p != "*"] or ["EE"]

    if is_admin:
        scope_label = "Institutional / Admin Full Scope (All Programs & PGOs)"
    elif is_dean:
        scope_label = "College-Wide Dean Oversight (All Programs & PGOs)"
    elif is_qa:
        scope_label = "College QA Oversight (All Programs & PGOs)"
    elif is_staff:
        scope_label = "Academic Staff Oversight (All Programs & PGOs)"
    elif is_ph:
        prog_str = ", ".join(allowed_programs)
        scope_label = f"Program-Wide Scope ({prog_str} Program Head — All PGOs)"
    else:
        scope_label = f"Faculty Scope ({full_name} — Handled Courses & Aligned PGOs Only)"

    return {
        "username": username,
        "full_name": full_name,
        "role": role,
        "workflow_roles": wf_roles,
        "is_program_wide": is_program_wide,
        "is_college_wide": is_college_wide,
        "allowed_programs": allowed_programs,
        "scope_label": scope_label,
    }


def _build_accdb_course_lookup() -> Dict[str, Dict[str, Any]]:
    """Builds a normalized lookup map from course code -> ACCDB course metadata & PGO-PI mappings."""
    lookup: Dict[str, Dict[str, Any]] = {}
    try:
        for item in accdb_curriculum.query_accdb_bsee_courses():
            code = normalize_course_code(item.get("code") or "")
            if code and code not in lookup:
                lookup[code] = item
    except Exception as e:
        logger.debug("ACCDB course lookup fallback: %s", e)
    return lookup


def _infer_ied_from_course_code(course_code: str) -> str:
    """Infers default I-E-D level from course numbering when explicit ACCDB tag is unavailable."""
    m = re.search(r"(\d{3})", str(course_code or ""))
    if m:
        num = int(m.group(1))
        if num >= 400:
            return "D"
        if num >= 300:
            return "E"
    return "I"


def _resolve_clo_alignments(
    course_code: str,
    co: Dict[str, Any],
    accdb_lookup: Dict[str, Dict[str, Any]],
    pgo_lookup: Dict[str, Dict[str, Any]],
    pi_lookup: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Resolves a single syllabus CLO dictionary to structured (PGO, PI, I-E-D) alignment dicts.
    Combines syllabus metadata (`program_outcomes`, `performance_indicator`) with
    authoritative relational mappings from PGO-PI-IGA.accdb.
    """
    if not isinstance(co, dict):
        return []
    accdb_lookup = accdb_lookup if isinstance(accdb_lookup, dict) else {}
    pgo_lookup = pgo_lookup if isinstance(pgo_lookup, dict) else {}
    pi_lookup = pi_lookup if isinstance(pi_lookup, dict) else {}

    norm_code = normalize_course_code(course_code)
    accdb_course = accdb_lookup.get(norm_code) or accdb_lookup.get(f"{norm_code}L") or {}
    accdb_mappings = accdb_course.get("pgo_pi_mappings") or []

    # Index ACCDB mappings by (pgo_id, pi_id) and by pgo_id
    ied_by_pgo_pi: Dict[Tuple[str, str], str] = {}
    ied_by_pgo: Dict[str, str] = {}
    for m in accdb_mappings:
        pid = str(m.get("pgo_id") or "").strip().lower()
        pi = str(m.get("pi") or "").strip().lower().rstrip(".")
        ied = str(m.get("ied") or "I").strip().upper()
        if "D" in ied:
            ied = "D"
        elif "E" in ied:
            ied = "E"
        else:
            ied = "I"
        if pid and pi:
            ied_by_pgo_pi[(pid, pi)] = ied
        if pid and pid not in ied_by_pgo:
            ied_by_pgo[pid] = ied

    raw_pgo = str(co.get("program_outcomes") or "").strip()
    raw_pi = str(co.get("performance_indicator") or "").strip()

    # Extract explicit PGO letters/IDs from syllabus
    pgo_ids: List[str] = []
    if raw_pgo:
        for tok in re.split(r"[;,/]+", raw_pgo):
            tok_c = tok.strip()
            if not tok_c:
                continue
            m_pgo = re.search(r"(?:PGO\s*[-:]?\s*)?([a-m])\b", tok_c, re.I)
            if m_pgo:
                ltr = m_pgo.group(1).lower()
                if ltr not in pgo_ids:
                    pgo_ids.append(ltr)
            else:
                m_num = re.search(r"(?:PGO\s*[-:]?\s*)?(\d+)\b", tok_c, re.I)
                if m_num:
                    idx = int(m_num.group(1))
                    if 1 <= idx <= 13:
                        ltr = chr(ord("a") + idx - 1)
                        if ltr not in pgo_ids:
                            pgo_ids.append(ltr)

    # Extract explicit PI codes (e.g. 'c.2', 'd.3', 'h.2')
    pi_entries: List[Tuple[str, str]] = []
    if raw_pi:
        for line in re.split(r"[;\n]+", raw_pi):
            line = line.strip()
            if not line:
                continue
            m_pi = re.match(r"^([a-m]\.\d+)\.?\s*(.*)$", line, re.I)
            if m_pi:
                pi_code = m_pi.group(1).lower()
                pi_desc = m_pi.group(2).strip() or (pi_lookup.get(pi_code, {}).get("description", ""))
                pi_entries.append((pi_code, pi_desc))
                ltr = pi_code.split(".")[0]
                if ltr not in pgo_ids:
                    pgo_ids.append(ltr)

    # Check if an I-E-D tag is embedded inside syllabus text e.g. [D] or (E)
    explicit_ied_match = re.search(r"[\[\(]\s*([IED])(?:/[IED])?\s*[\]\)]", f"{raw_pgo} {raw_pi}", re.I)
    explicit_ied = explicit_ied_match.group(1).upper() if explicit_ied_match else None

    alignments: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    # Case 1: Syllabus specifies PIs
    if pi_entries:
        for pi_code, pi_desc in pi_entries:
            pgo_id = pi_code.split(".")[0]
            if (pgo_id, pi_code) in seen_pairs:
                continue
            seen_pairs.add((pgo_id, pi_code))
            ied = (
                explicit_ied
                or ied_by_pgo_pi.get((pgo_id, pi_code))
                or ied_by_pgo.get(pgo_id)
                or _infer_ied_from_course_code(course_code)
            )
            pgo_meta = pgo_lookup.get(pgo_id, {})
            alignments.append({
                "pgo_id": pgo_id,
                "pgo_label": f"PGO {pgo_id}",
                "pgo_keyword": pgo_meta.get("keyword") or f"Outcome {pgo_id.upper()}",
                "pgo_description": pgo_meta.get("description") or co.get("graduate_outcome_desc") or "",
                "pi_id": pi_code,
                "pi_description": pi_desc or pi_lookup.get(pi_code, {}).get("description") or f"Indicator {pi_code}",
                "ied": ied,
                "ied_label": IED_LABELS.get(ied, "Introductory"),
            })

    # Case 2: Syllabus specifies PGOs without structured PI codes
    elif pgo_ids:
        for pgo_id in pgo_ids:
            pgo_meta = pgo_lookup.get(pgo_id, {})
            # Pick first ACCDB PI for this PGO, or first tree PI, or fallback '{pgo_id}.1'
            matched_pi = next(
                (m.get("pi") for m in accdb_mappings if str(m.get("pgo_id") or "").lower() == pgo_id and m.get("pi")),
                None,
            )
            if not matched_pi and pgo_meta.get("pis"):
                matched_pi = pgo_meta["pis"][0]["pi_id"]
            pi_code = (matched_pi or f"{pgo_id}.1").lower().rstrip(".")
            if (pgo_id, pi_code) in seen_pairs:
                continue
            seen_pairs.add((pgo_id, pi_code))
            ied = (
                explicit_ied
                or ied_by_pgo_pi.get((pgo_id, pi_code))
                or ied_by_pgo.get(pgo_id)
                or _infer_ied_from_course_code(course_code)
            )
            alignments.append({
                "pgo_id": pgo_id,
                "pgo_label": f"PGO {pgo_id}",
                "pgo_keyword": pgo_meta.get("keyword") or f"Outcome {pgo_id.upper()}",
                "pgo_description": pgo_meta.get("description") or co.get("graduate_outcome_desc") or "",
                "pi_id": pi_code,
                "pi_description": raw_pi or pi_lookup.get(pi_code, {}).get("description") or f"Indicator {pi_code}",
                "ied": ied,
                "ied_label": IED_LABELS.get(ied, "Introductory"),
            })

    # Case 3: Syllabus CLO has empty PGO/PI strings -> fall back to ACCDB relational definitions for the course
    elif accdb_mappings:
        for m in accdb_mappings:
            pgo_id = str(m.get("pgo_id") or "").strip().lower()
            pi_code = str(m.get("pi") or f"{pgo_id}.1").strip().lower().rstrip(".")
            if not pgo_id or (pgo_id, pi_code) in seen_pairs:
                continue
            seen_pairs.add((pgo_id, pi_code))
            ied = str(m.get("ied") or _infer_ied_from_course_code(course_code)).strip().upper()
            if "D" in ied:
                ied = "D"
            elif "E" in ied:
                ied = "E"
            else:
                ied = "I"
            pgo_meta = pgo_lookup.get(pgo_id, {})
            alignments.append({
                "pgo_id": pgo_id,
                "pgo_label": f"PGO {pgo_id}",
                "pgo_keyword": pgo_meta.get("keyword") or m.get("pgo_keyword") or f"Outcome {pgo_id.upper()}",
                "pgo_description": pgo_meta.get("description") or m.get("pgo_description") or "",
                "pi_id": pi_code,
                "pi_description": m.get("pi_description") or pi_lookup.get(pi_code, {}).get("description") or f"Indicator {pi_code}",
                "ied": ied,
                "ied_label": IED_LABELS.get(ied, "Introductory"),
            })

    return alignments


def compute_course_student_clo_metrics(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes exact bottom-up per-student CLO attainment ratings from Class Record scores
    using the official Base-50 formula matching Step 4 Class Record & Step 7 CLO Report (MID-10).
    """
    if not isinstance(doc, dict):
        doc = {}
    bp_dict = doc.get("blueprint") if isinstance(doc.get("blueprint"), dict) else {}
    meta = bp_dict.get("metadata") if isinstance(bp_dict.get("metadata"), dict) else {}
    raw_progs = meta.get("programs")
    first_prog = (
        raw_progs[0]
        if isinstance(raw_progs, list) and raw_progs
        else (meta.get("program_code") or doc.get("program_code") or "EE")
    )
    outcomes_raw = [
        co for co in (bp_dict.get("course_outcomes") or [])
        if isinstance(co, dict)
    ]
    base_meta = {
        "course_code": str(meta.get("course_code") or doc.get("course_code") or "").strip(),
        "course_title": str(meta.get("course_title") or doc.get("course_title") or "").strip(),
        "section": str(meta.get("section") or doc.get("section") or "").strip(),
        "program_code": normalize_program_code(first_prog or "EE"),
        "semester_ay": str(meta.get("semester_ay") or doc.get("semester_ay") or "").strip(),
    }

    try:
        has_scores = bool(courses_store.has_recorded_scores(doc))
    except Exception:
        has_scores = False

    try:
        bp_obj = SyllabusBlueprint.from_dict(bp_dict)
    except Exception as exc:
        logger.warning("PGO Assessment fallback for course '%s': %s", doc.get("id"), exc)
        return {
            **base_meta,
            "has_scores": False,
            "students": [],
            "outcomes": outcomes_raw,
        }

    # Expand all assessment items into per-CLO columns matching renderLiveGradebookAndReports & MID-10
    all_sa_cols: List[Dict[str, Any]] = []
    all_cols: List[Dict[str, Any]] = []

    for cat in (bp_obj.categories or []):
        a_type = (cat.assessment_type or "SA").upper()
        a_code = (cat.assessment_code or ("FA1" if a_type == "FA" else "SA1")).upper()
        n_items = max(1, len(cat.items or []))
        def_wt = float(cat.weight_pct or 0.0) / n_items
        for it in (cat.items or []):
            it_wt = float(it.weight_pct) if float(it.weight_pct or 0.0) > 0 else def_wt
            if it_wt <= 0:
                it_wt = 1.0
            clo_pairs = _get_item_clo_points(it)
            total_it_pts = sum(pts for _, pts in clo_pairs) or float(it.max_score or 30.0)
            n_clos = max(1, len(clo_pairs))
            for clo_id, clo_pts in clo_pairs:
                col_wt = round(it_wt * (clo_pts / total_it_pts), 4) if total_it_pts > 0 else round(it_wt / n_clos, 4)
                col_info = {
                    "term": cat.term,
                    "assessment_type": a_type,
                    "assessment_code": a_code,
                    "item": it,
                    "clo_id": clo_id.upper(),
                    "clo_pts": float(clo_pts),
                    "total_it_pts": float(total_it_pts),
                    "col_wt": col_wt,
                }
                all_cols.append(col_info)
                if a_type == "SA":
                    all_sa_cols.append(col_info)

    student_metrics: List[Dict[str, Any]] = []

    for st_idx, st_obj in enumerate(bp_obj.students or []):
        raw_st_list = bp_dict.get("students") if isinstance(bp_dict.get("students"), list) else []
        raw_st_dict = raw_st_list[st_idx] if st_idx < len(raw_st_list) and isinstance(raw_st_list[st_idx], dict) else {}
        sid = str(getattr(st_obj, "student_id", "") or raw_st_dict.get("student_id") or "").strip()
        if not sid:
            continue

        clo_results: Dict[str, Dict[str, Any]] = {}
        for co in outcomes_raw:
            co_id = str(co.get("co_id") or "CLO1").strip().upper()
            try:
                deg_cutoff = float(co.get("target_score_pct") or 75.0)
            except (ValueError, TypeError):
                deg_cutoff = 75.0
            if deg_cutoff <= 0:
                deg_cutoff = 75.0
            elif deg_cutoff <= 1.0:
                deg_cutoff *= 100.0

            # Prefer SA columns for CLO evaluation; fall back to all columns if no SA mapped
            matching = [c for c in all_sa_cols if c["clo_id"] == co_id]
            if not matching:
                matching = [c for c in all_cols if c["clo_id"] == co_id]

            # Check if this student has at least one recorded numeric score in matching columns
            sum_wt = sum(c["col_wt"] for c in matching)
            num = 0.0
            scored_wt = 0.0
            scored_cols = 0
            sa_groups: Dict[str, List[Dict[str, Any]]] = {}

            for c in matching:
                raw_sc = _get_student_clo_score(st_obj, c["item"], c["clo_id"], c["clo_pts"], c["total_it_pts"])
                is_col_scored = False
                if raw_sc != "" and raw_sc is not None:
                    try:
                        sc_val = float(raw_sc)
                        scored_cols += 1
                        is_col_scored = True
                    except (ValueError, TypeError):
                        sc_val = 0.0
                else:
                    sc_val = 0.0
                max_p = c["clo_pts"] if c["clo_pts"] > 0 else 1.0
                num += sc_val * c["col_wt"] / max_p
                if is_col_scored:
                    scored_wt += c["col_wt"]
                sa_groups.setdefault(c["assessment_code"], []).append((c, raw_sc))

            student_has_clo_scores = bool(has_scores and scored_cols > 0 and sum_wt > 0)
            if student_has_clo_scores:
                clo_final_grade = round((num / sum_wt) * 50.0 + 50.0, 2)
                current_assessed_grade = round((num / scored_wt) * 50.0 + 50.0, 2) if scored_wt > 0 else clo_final_grade
                attained = clo_final_grade >= deg_cutoff
            else:
                clo_final_grade = None
                current_assessed_grade = None
                attained = None

            # Per-SA breakdown for this student & CLO
            per_sa_clo: Dict[str, Optional[float]] = {}
            for sa_code, grp_entries in sa_groups.items():
                sa_wt = sum(c["col_wt"] for c, _ in grp_entries)
                sa_num = 0.0
                sa_scored = 0
                for c, raw_sc in grp_entries:
                    if raw_sc != "" and raw_sc is not None:
                        try:
                            sc_v = float(raw_sc)
                            sa_scored += 1
                        except (ValueError, TypeError):
                            sc_v = 0.0
                    else:
                        sc_v = 0.0
                    max_p = c["clo_pts"] if c["clo_pts"] > 0 else 1.0
                    sa_num += sc_v * c["col_wt"] / max_p
                if has_scores and sa_scored > 0 and sa_wt > 0:
                    per_sa_clo[sa_code] = round((sa_num / sa_wt) * 50.0 + 50.0, 2)
                else:
                    per_sa_clo[sa_code] = None

            clo_results[co_id] = {
                "co_id": co_id,
                "clo_final_grade": clo_final_grade,
                "current_assessed_grade": current_assessed_grade,
                "scored_items_count": scored_cols,
                "total_items_count": len(matching),
                "per_sa_clo": per_sa_clo,
                "target_score_pct": round(deg_cutoff, 2),
                "attained": attained,
                "has_scores": student_has_clo_scores,
            }

        student_metrics.append({
            "student_id": sid,
            "name": format_student_display_name(raw_st_dict),
            "cohort": extract_cohort_prefix(sid),
            "clo_results": clo_results,
        })

    return {
        **base_meta,
        "has_scores": has_scores,
        "students": student_metrics,
        "outcomes": outcomes_raw,
    }


def _collect_scoped_courses(user: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collects all course documents visible to the logged-in user under RBAC rules.
    """
    if scope["is_program_wide"]:
        all_wf = courses_store.list_all_workflow_courses()
        allowed_progs = set(scope["allowed_programs"])
        scoped_docs: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        for entry in all_wf:
            doc = entry.get("doc_raw")
            if not doc or not isinstance(doc, dict):
                continue
            cid = doc.get("id")
            if not cid or cid in seen_ids:
                continue
            bp = doc.get("blueprint") or {}
            meta = bp.get("metadata") or {}
            progs_raw = meta.get("programs") or [meta.get("program_code") or "EE"]
            course_progs = {normalize_program_code(p) for p in progs_raw if str(p).strip()}
            if not course_progs:
                course_progs = {"EE"}
            if "*" not in allowed_progs and not (course_progs & allowed_progs):
                continue
            seen_ids.add(cid)
            scoped_docs.append(doc)
        return scoped_docs

    # Faculty scope: only courses owned or co-authored by the user (or matching faculty_name)
    username = scope["username"]
    full_name = scope["full_name"]
    user_summary = courses_store.list_courses(username, full_name)
    scoped_docs = []
    seen_ids = set()
    for summ in (user_summary.get("courses") or []):
        cid = summ.get("id")
        if not cid or cid in seen_ids:
            continue
        doc = courses_store.find_course(cid)
        if doc:
            seen_ids.add(cid)
            scoped_docs.append(doc)
    return scoped_docs


def _extract_pgo_key(pgo_item: Dict[str, Any]) -> str:
    """Extracts a normalized PGO key ('a'..'m' or '1'..'22') for directory lookup."""
    letter = str(pgo_item.get("letter") or "").strip().lower()
    if letter:
        return letter
    code = str(pgo_item.get("pgo_code") or pgo_item.get("pgo_id") or "").strip().lower()
    m = re.search(r"([a-m]|\d+)$", code)
    return m.group(1) if m else code


def build_program_pgo_pi_directory(
    scope: Dict[str, Any],
    pgo_tree: List[Dict[str, Any]],
    final_pgos: List[Dict[str, Any]],
    pi_node_lookup: Dict[str, Dict[str, Any]],
    faculty_aligned_pgos: Set[str],
    faculty_aligned_pis: Set[str],
    faculty_program_codes: Set[str],
    program_filter: str = "ALL",
) -> Dict[str, Any]:
    """
    Builds the complete Program Graduate Outcomes (PGO) & Performance Indicators (PI)
    Reference Directory grouped per degree program, respecting RBAC visibility:
      - College-wide roles (Dean, Associate Dean, QA Head, Staff, Admin):
          all CoE degree programs, all PGOs, and all PIs.
      - Program Head:
          all PGOs and PIs for their assigned program(s) (or all if '*').
      - Faculty:
          strictly limited to PGOs and PIs aligned to their handled/assigned courses.
    """
    import catalog_data

    catalog = catalog_data.get_full_catalog() or {}
    prog_structs = catalog.get("program_structures") or {}

    accdb_by_key: Dict[str, Dict[str, Any]] = {
        str(p.get("pgo_id") or p.get("pgo") or "").strip().lower(): p
        for p in (pgo_tree or [])
    }
    live_pgo_by_key: Dict[str, Dict[str, Any]] = {
        str(p.get("pgo_id") or "").strip().lower(): p
        for p in (final_pgos or [])
    }

    allowed_progs = set(scope.get("allowed_programs") or [])
    is_college_wide = bool(scope.get("is_college_wide"))
    is_program_wide = bool(scope.get("is_program_wide"))

    prog_flt_norm = normalize_program_code(program_filter) if program_filter and program_filter.upper() != "ALL" else "ALL"

    programs_out: List[Dict[str, Any]] = []
    total_pgos = 0
    total_pis = 0

    for raw_code, struct in prog_structs.items():
        norm_code = normalize_program_code(raw_code)
        if not is_college_wide:
            if is_program_wide:
                if "*" not in allowed_progs and allowed_progs and norm_code not in allowed_progs:
                    continue
            else:
                # Faculty: limit to programs their assigned courses serve
                if faculty_program_codes and norm_code not in faculty_program_codes and norm_code != "EE":
                    continue

        if prog_flt_norm != "ALL" and norm_code != prog_flt_norm:
            continue

        degree_label = raw_code if str(raw_code).upper().startswith("BS") else f"BS{raw_code}"
        pgo_catalog = struct.get("pgo_pi_catalog") or []

        pgos_out: List[Dict[str, Any]] = []
        prog_pi_count = 0

        for p_item in pgo_catalog:
            pkey = _extract_pgo_key(p_item)
            pgo_code = str(p_item.get("pgo_code") or f"PGO {pkey}").strip()
            acc_pgo = accdb_by_key.get(pkey) if norm_code == "EE" else None
            live_pgo = live_pgo_by_key.get(pkey) if norm_code == "EE" else None

            raw_pis = list(p_item.get("pis") or [])
            if not raw_pis and acc_pgo:
                raw_pis = [
                    {
                        "pi_code": str(pi.get("pi_id") or "").strip(),
                        "description": str(pi.get("description") or "").strip(),
                        "full_text": str(pi.get("label") or pi.get("description") or "").strip(),
                        "igas": "",
                    }
                    for pi in (acc_pgo.get("pis") or [])
                ]

            # Faculty RBAC filter: show only aligned PGOs / PIs
            if not is_program_wide:
                if pkey not in faculty_aligned_pgos and pgo_code.lower() not in faculty_aligned_pgos:
                    continue

            pis_out: List[Dict[str, Any]] = []
            for pi in raw_pis:
                pi_code = str(pi.get("pi_code") or pi.get("pi_id") or "").strip()
                pi_norm = pi_code.lower().lstrip("pi-").strip(".")
                if not is_program_wide and faculty_aligned_pis:
                    if pi_norm not in faculty_aligned_pis and pi_code.lower() not in faculty_aligned_pis:
                        # If faculty has PGO aligned but no granular PI match recorded, still keep if no PI list matched
                        if any(al.startswith(f"{pkey}.") for al in faculty_aligned_pis):
                            continue
                live_pi = pi_node_lookup.get(pi_norm) if norm_code == "EE" else None
                pis_out.append({
                    "pi_code": pi_code,
                    "description": str(pi.get("description") or "").strip(),
                    "full_text": str(pi.get("full_text") or pi.get("description") or "").strip(),
                    "igas": str(pi.get("igas") or "").strip(),
                    "is_aligned": bool(live_pi and live_pi.get("is_aligned")),
                    "avg_grade": live_pi.get("avg_grade") if live_pi else None,
                    "attainment_rate_pct": live_pi.get("attainment_rate_pct") if live_pi else None,
                    "ied_levels": live_pi.get("ied_levels") or [] if live_pi else [],
                })

            prog_pi_count += len(pis_out)
            pgos_out.append({
                "pgo_code": pgo_code,
                "pgo_key": pkey,
                "letter": str(p_item.get("letter") or pkey).strip(),
                "keyword": (acc_pgo.get("keyword") if acc_pgo else "") or str(p_item.get("short_label") or pgo_code).strip(),
                "description": (acc_pgo.get("description") if acc_pgo else "") or str(p_item.get("description") or "").strip(),
                "full_description": str(p_item.get("description") or "").strip(),
                "short_label": str(p_item.get("short_label") or "").strip(),
                "igas": str(p_item.get("igas") or "").strip(),
                "is_aligned": bool(live_pgo and live_pgo.get("is_aligned")),
                "avg_grade": live_pgo.get("avg_grade") if live_pgo else None,
                "attainment_rate_pct": live_pgo.get("attainment_rate_pct") if live_pgo else None,
                "ied_levels": live_pgo.get("ied_levels") or [] if live_pgo else [],
                "pis": pis_out,
            })

        if not pgos_out and not is_program_wide:
            continue

        total_pgos += len(pgos_out)
        total_pis += prog_pi_count
        programs_out.append({
            "program_code": norm_code,
            "raw_code": raw_code,
            "degree_label": degree_label,
            "program_name": str(struct.get("program_name") or degree_label).strip(),
            "department": str(struct.get("department") or "").strip(),
            "cmo_reference": str(struct.get("cmo_reference") or "").strip(),
            "source_file": str(struct.get("source_file") or "").strip(),
            "pgo_count": len(pgos_out),
            "pi_count": prog_pi_count,
            "pgos": pgos_out,
        })

    return {
        "programs": programs_out,
        "total_programs": len(programs_out),
        "total_pgos": total_pgos,
        "total_pis": total_pis,
    }


def build_pgo_assessment_report(
    user: Optional[Dict[str, Any]],
    program_filter: str = "ALL",
    course_filter: str = "ALL",
    ied_filter: str = "ALL",
    cohort_filter: str = "ALL",
    search_query: str = "",
) -> Dict[str, Any]:
    """
    Main consolidation orchestrator for the PGO Assessment Dashboard & Interactive Flowchart.
    Consolidates Class Record -> CLO -> PI -> PGO bottom-up, segregated by Student ID #,
    and filters strictly by the user's RBAC role scope.
    """
    scope = get_user_pgo_scope(user)
    pgo_tree = accdb_curriculum.get_accdb_pgo_pi_tree()
    accdb_lookup = _build_accdb_course_lookup()

    pgo_lookup: Dict[str, Dict[str, Any]] = {}
    pi_lookup: Dict[str, Dict[str, Any]] = {}
    for pgo in pgo_tree:
        pid = str(pgo.get("pgo_id") or pgo.get("pgo") or "").strip().lower()
        pgo_lookup[pid] = pgo
        for pi in (pgo.get("pis") or []):
            pi_id = str(pi.get("pi_id") or pi.get("pi") or "").strip().lower().rstrip(".")
            pi_lookup[pi_id] = pi

    scoped_docs = _collect_scoped_courses(user or {}, scope)

    # Collect available filter options before narrowing by program/course
    available_programs_set: Set[str] = set()
    available_courses_meta: List[Dict[str, Any]] = []
    for doc in scoped_docs:
        bp = doc.get("blueprint") or {}
        meta = bp.get("metadata") or {}
        progs_raw = meta.get("programs") or [meta.get("program_code") or "EE"]
        c_progs = [normalize_program_code(p) for p in progs_raw if str(p).strip()] or ["EE"]
        available_programs_set.update(c_progs)
        available_courses_meta.append({
            "course_id": doc.get("id"),
            "course_code": (meta.get("course_code") or doc.get("course_code") or "").strip(),
            "course_title": (meta.get("course_title") or doc.get("course_title") or "").strip(),
            "section": (meta.get("section") or doc.get("section") or "").strip(),
            "programs": c_progs,
            "has_scores": courses_store.has_recorded_scores(doc),
        })

    # Normalize query filters
    prog_flt = normalize_program_code(program_filter) if program_filter and program_filter.upper() != "ALL" else "ALL"
    course_flt = str(course_filter or "ALL").strip()
    ied_flt = str(ied_filter or "ALL").strip().upper()
    cohort_flt = str(cohort_filter or "ALL").strip()
    q_norm = str(search_query or "").strip().lower()

    # Apply course-level filters (program & course_id)
    filtered_docs: List[Dict[str, Any]] = []
    for doc in scoped_docs:
        bp = doc.get("blueprint") or {}
        meta = bp.get("metadata") or {}
        progs_raw = meta.get("programs") or [meta.get("program_code") or "EE"]
        c_progs = {normalize_program_code(p) for p in progs_raw if str(p).strip()} or {"EE"}
        if prog_flt != "ALL" and prog_flt not in c_progs:
            continue
        if course_flt != "ALL" and doc.get("id") != course_flt:
            continue
        filtered_docs.append(doc)

    # Data accumulators
    # Student master index: student_id -> record
    students_acc: Dict[str, Dict[str, Any]] = {}
    # PGO accumulator: pgo_id -> summary
    pgo_acc: Dict[str, Dict[str, Any]] = {}
    # PI accumulator: pi_id -> summary
    pi_acc: Dict[str, Dict[str, Any]] = {}
    # Course summary accumulator
    courses_summary: List[Dict[str, Any]] = []
    # Flowchart nodes & edges
    course_clo_nodes: Dict[str, Dict[str, Any]] = {}
    flowchart_edges: List[Dict[str, Any]] = []
    edge_dedup: Set[Tuple[str, str]] = set()

    # Track faculty's aligned PGOs across ALL their scoped courses (even before optional filter)
    faculty_aligned_pgos: Set[str] = set()
    faculty_aligned_pis: Set[str] = set()
    if not scope["is_program_wide"]:
        for doc in scoped_docs:
            bp = doc.get("blueprint") or {}
            c_code = (bp.get("metadata") or {}).get("course_code") or doc.get("course_code") or ""
            for co in (bp.get("course_outcomes") or []):
                for al in _resolve_clo_alignments(c_code, co, accdb_lookup, pgo_lookup, pi_lookup):
                    faculty_aligned_pgos.add(al["pgo_id"])
                    faculty_aligned_pis.add(al["pi_id"])

    # Initialize PGO and PI buckets
    for pgo in pgo_tree:
        pid = str(pgo.get("pgo_id") or pgo.get("pgo") or "").strip().lower()
        if not scope["is_program_wide"] and pid not in faculty_aligned_pgos:
            continue
        pgo_acc[pid] = {
            "pgo_id": pid,
            "pgo_label": f"PGO {pid}",
            "keyword": pgo.get("keyword") or f"Outcome {pid.upper()}",
            "description": pgo.get("description") or "",
            "is_aligned": False,
            "is_assessed": False,
            "ied_levels": set(),
            "ied_scores": {"I": [], "E": [], "D": []},
            "aligned_courses": {},  # course_id -> dict
            "aligned_clos": set(),
            "pis": [],
            "student_buckets": {},  # student_id -> {grades: [], targets: [], ieds: set(), clos: []}
        }
        for pi in (pgo.get("pis") or []):
            pi_id = str(pi.get("pi_id") or pi.get("pi") or "").strip().lower().rstrip(".")
            if not scope["is_program_wide"] and pi_id not in faculty_aligned_pis:
                continue
            pi_acc[pi_id] = {
                "pi_id": pi_id,
                "pgo_id": pid,
                "pgo_label": f"PGO {pid}",
                "description": pi.get("description") or "",
                "is_aligned": False,
                "is_assessed": False,
                "ied_levels": set(),
                "aligned_courses": {},
                "aligned_clos": set(),
                "student_buckets": {},
            }

    # Helper to ensure dynamic PGO/PI bucket exists if syllabus references non-tree PI
    def _ensure_pgo_pi_buckets(al: Dict[str, Any]) -> None:
        pid = al["pgo_id"]
        pi_id = al["pi_id"]
        if pid not in pgo_acc:
            pgo_acc[pid] = {
                "pgo_id": pid,
                "pgo_label": f"PGO {pid}",
                "keyword": al["pgo_keyword"],
                "description": al["pgo_description"],
                "is_aligned": False,
                "is_assessed": False,
                "ied_levels": set(),
                "ied_scores": {"I": [], "E": [], "D": []},
                "aligned_courses": {},
                "aligned_clos": set(),
                "pis": [],
                "student_buckets": {},
            }
        if pi_id not in pi_acc:
            pi_acc[pi_id] = {
                "pi_id": pi_id,
                "pgo_id": pid,
                "pgo_label": f"PGO {pid}",
                "description": al["pi_description"],
                "is_aligned": False,
                "is_assessed": False,
                "ied_levels": set(),
                "aligned_courses": {},
                "aligned_clos": set(),
                "student_buckets": {},
            }

    # Process each filtered course bottom-up
    total_aligned_clos = 0
    for doc in filtered_docs:
        cid = doc.get("id")
        if not cid:
            continue
        metrics = compute_course_student_clo_metrics(doc)
        c_code = metrics.get("course_code") or str(doc.get("course_code") or "").strip()
        c_title = metrics.get("course_title") or str(doc.get("course_title") or "").strip()
        c_sec = metrics.get("section") or str(doc.get("section") or "").strip()
        has_scores = bool(metrics.get("has_scores", False))
        outcomes = metrics.get("outcomes") or []
        students_m = metrics.get("students") or []

        # Map each CLO in course -> alignments
        clo_align_map: Dict[str, List[Dict[str, Any]]] = {}
        course_pgo_set: Set[str] = set()
        course_pi_set: Set[str] = set()
        course_ied_set: Set[str] = set()

        for co in outcomes:
            if not isinstance(co, dict):
                continue
            co_id = str(co.get("co_id") or co.get("code") or "CLO1").strip().upper()
            aligns = _resolve_clo_alignments(c_code, co, accdb_lookup, pgo_lookup, pi_lookup)
            # Apply I-E-D filter if requested
            if ied_flt in ("I", "E", "D"):
                aligns = [a for a in aligns if a["ied"] == ied_flt]
            if not aligns:
                continue
            total_aligned_clos += 1
            clo_align_map[co_id] = aligns

            # Collect student attainment for this specific Course + CLO node
            clo_grades_for_node: List[float] = []
            clo_pass_for_node = 0
            clo_assessed_cnt = 0
            clo_student_rows: List[Dict[str, Any]] = []

            for st_m in students_m:
                sid = st_m["student_id"]
                if cohort_flt != "ALL" and st_m["cohort"] != cohort_flt:
                    continue
                if q_norm and (q_norm not in sid.lower() and q_norm not in st_m["name"].lower() and q_norm not in c_code.lower()):
                    # Only filter students if search matches student/course; keep if search matches PGO/PI
                    pgo_pi_match = any(
                        q_norm in a["pgo_label"].lower() or q_norm in a["pi_id"].lower() or q_norm in a["pgo_keyword"].lower()
                        for a in aligns
                    )
                    if not pgo_pi_match:
                        continue

                c_res = st_m["clo_results"].get(co_id, {})
                g_val = c_res.get("clo_final_grade")
                att = c_res.get("attained")
                tgt = c_res.get("target_score_pct", 75.0)
                st_has = bool(c_res.get("has_scores"))
                if st_has and g_val is not None:
                    clo_grades_for_node.append(g_val)
                    clo_assessed_cnt += 1
                    if att:
                        clo_pass_for_node += 1

                clo_student_rows.append({
                    "student_id": sid,
                    "name": st_m["name"],
                    "cohort": st_m["cohort"],
                    "course_id": cid,
                    "course_code": c_code,
                    "section": c_sec,
                    "clo_id": co_id,
                    "per_sa_clo": c_res.get("per_sa_clo") or {},
                    "clo_final_grade": g_val,
                    "current_assessed_grade": c_res.get("current_assessed_grade"),
                    "scored_items_count": c_res.get("scored_items_count", 0),
                    "total_items_count": c_res.get("total_items_count", 0),
                    "target_score_pct": tgt,
                    "attained": att,
                    "has_scores": st_has,
                })

            node_key = f"cclo:{cid}:{co_id}"
            avg_node_grade = round(sum(clo_grades_for_node) / len(clo_grades_for_node), 2) if clo_grades_for_node else None
            att_node_pct = round((clo_pass_for_node / clo_assessed_cnt) * 100.0, 1) if clo_assessed_cnt > 0 else None

            course_clo_nodes[node_key] = {
                "node_key": node_key,
                "node_type": "course_clo",
                "course_id": cid,
                "course_code": c_code,
                "course_title": c_title,
                "section": c_sec,
                "clo_id": co_id,
                "clo_description": str(co.get("description") or ""),
                "ied_levels": sorted({a["ied"] for a in aligns}),
                "aligned_pis": [a["pi_id"] for a in aligns],
                "aligned_pgos": [a["pgo_id"] for a in aligns],
                "has_scores": clo_assessed_cnt > 0,
                "assessed_students_count": clo_assessed_cnt,
                "attained_students_count": clo_pass_for_node,
                "enrolled_students_count": len(clo_student_rows),
                "avg_grade": avg_node_grade,
                "attainment_rate_pct": att_node_pct,
                "student_ids": clo_student_rows,
            }

            # Propagate bottom-up to PI and PGO buckets + Student master matrix
            for al in aligns:
                _ensure_pgo_pi_buckets(al)
                pid = al["pgo_id"]
                pi_id = al["pi_id"]
                ied = al["ied"]
                course_pgo_set.add(pid)
                course_pi_set.add(pi_id)
                course_ied_set.add(ied)

                # Flowchart edges: Course/CLO -> PI and PI -> PGO
                e1 = (node_key, f"pi:{pi_id}")
                if e1 not in edge_dedup:
                    edge_dedup.add(e1)
                    flowchart_edges.append({
                        "from": node_key,
                        "to": f"pi:{pi_id}",
                        "type": "clo-pi",
                        "ied": ied,
                        "ied_label": al["ied_label"],
                    })
                e2 = (f"pi:{pi_id}", f"pgo:{pid}")
                if e2 not in edge_dedup:
                    edge_dedup.add(e2)
                    flowchart_edges.append({
                        "from": f"pi:{pi_id}",
                        "to": f"pgo:{pid}",
                        "type": "pi-pgo",
                        "ied": ied,
                        "ied_label": al["ied_label"],
                    })

                # Update PGO & PI alignment metadata
                pgo_b = pgo_acc[pid]
                pgo_b["is_aligned"] = True
                pgo_b["ied_levels"].add(ied)
                pgo_b["aligned_clos"].add(f"{c_code}:{co_id}")
                c_pgo_entry = pgo_b["aligned_courses"].setdefault(cid, {
                    "course_id": cid,
                    "course_code": c_code,
                    "course_title": c_title,
                    "section": c_sec,
                    "clo_ids": [],
                    "ied_levels": set(),
                    "has_scores": has_scores,
                })
                if co_id not in c_pgo_entry["clo_ids"]:
                    c_pgo_entry["clo_ids"].append(co_id)
                c_pgo_entry["ied_levels"].add(ied)

                pi_b = pi_acc[pi_id]
                pi_b["is_aligned"] = True
                pi_b["ied_levels"].add(ied)
                pi_b["aligned_clos"].add(f"{c_code}:{co_id}")
                c_pi_entry = pi_b["aligned_courses"].setdefault(cid, {
                    "course_id": cid,
                    "course_code": c_code,
                    "section": c_sec,
                    "clo_ids": [],
                    "ied_levels": set(),
                    "has_scores": has_scores,
                })
                if co_id not in c_pi_entry["clo_ids"]:
                    c_pi_entry["clo_ids"].append(co_id)
                c_pi_entry["ied_levels"].add(ied)

                # Update per-student buckets for PI, PGO, and Student Matrix
                for st_row in clo_student_rows:
                    sid = st_row["student_id"]
                    st_master = students_acc.setdefault(sid, {
                        "student_id": sid,
                        "name": st_row["name"],
                        "cohort": st_row["cohort"],
                        "courses_map": {},
                        "pi_map": {},
                        "pgo_map": {},
                        "clo_details": [],
                    })

                    # Course enrollment entry for student
                    sc_entry = st_master["courses_map"].setdefault(cid, {
                        "course_id": cid,
                        "course_code": c_code,
                        "course_title": c_title,
                        "section": c_sec,
                        "has_scores": has_scores,
                        "clo_grades": {},
                    })
                    if st_row["has_scores"] and st_row["clo_final_grade"] is not None:
                        sc_entry["clo_grades"][co_id] = st_row["clo_final_grade"]
                        sc_entry["has_scores"] = True

                    # Detailed CLO mapping record on student
                    detail_rec = {
                        "course_id": cid,
                        "course_code": c_code,
                        "section": c_sec,
                        "clo_id": co_id,
                        "pgo_id": pid,
                        "pgo_label": f"PGO {pid}",
                        "pi_id": pi_id,
                        "ied": ied,
                        "ied_label": al["ied_label"],
                        "per_sa_clo": st_row["per_sa_clo"],
                        "clo_final_grade": st_row["clo_final_grade"],
                        "current_assessed_grade": st_row.get("current_assessed_grade"),
                        "scored_items_count": st_row.get("scored_items_count", 0),
                        "total_items_count": st_row.get("total_items_count", 0),
                        "target_score_pct": st_row["target_score_pct"],
                        "attained": st_row["attained"],
                        "has_scores": st_row["has_scores"],
                    }
                    # Avoid duplicate detail entries if same (cid, co_id, pi_id)
                    if not any(
                        d["course_id"] == cid and d["clo_id"] == co_id and d["pi_id"] == pi_id
                        for d in st_master["clo_details"]
                    ):
                        st_master["clo_details"].append(detail_rec)

                    # PI Student Bucket
                    st_pi = pi_b["student_buckets"].setdefault(sid, {
                        "student_id": sid,
                        "name": st_row["name"],
                        "cohort": st_row["cohort"],
                        "grades": [],
                        "targets": [],
                        "ieds": set(),
                        "details": [],
                    })
                    st_pi["ieds"].add(ied)
                    st_pi["details"].append(detail_rec)
                    if st_row["has_scores"] and st_row["clo_final_grade"] is not None:
                        st_pi["grades"].append(st_row["clo_final_grade"])
                        st_pi["targets"].append(st_row["target_score_pct"])

                    # Student master PI accumulator
                    sm_pi = st_master["pi_map"].setdefault(pi_id, {
                        "pi_id": pi_id,
                        "pgo_id": pid,
                        "grades": [],
                        "targets": [],
                        "ieds": set(),
                        "courses": set(),
                    })
                    sm_pi["ieds"].add(ied)
                    sm_pi["courses"].add(c_code)
                    if st_row["has_scores"] and st_row["clo_final_grade"] is not None:
                        sm_pi["grades"].append(st_row["clo_final_grade"])
                        sm_pi["targets"].append(st_row["target_score_pct"])

                    # PGO Student Bucket
                    st_pgo = pgo_b["student_buckets"].setdefault(sid, {
                        "student_id": sid,
                        "name": st_row["name"],
                        "cohort": st_row["cohort"],
                        "grades": [],
                        "targets": [],
                        "ieds": set(),
                        "details": [],
                    })
                    st_pgo["ieds"].add(ied)
                    st_pgo["details"].append(detail_rec)
                    if st_row["has_scores"] and st_row["clo_final_grade"] is not None:
                        st_pgo["grades"].append(st_row["clo_final_grade"])
                        st_pgo["targets"].append(st_row["target_score_pct"])
                        pgo_b["ied_scores"][ied].append(st_row["clo_final_grade"])

                    # Student master PGO accumulator
                    sm_pgo = st_master["pgo_map"].setdefault(pid, {
                        "pgo_id": pid,
                        "grades": [],
                        "targets": [],
                        "ieds": set(),
                        "clos_count": 0,
                    })
                    sm_pgo["ieds"].add(ied)
                    sm_pgo["clos_count"] += 1
                    if st_row["has_scores"] and st_row["clo_final_grade"] is not None:
                        sm_pgo["grades"].append(st_row["clo_final_grade"])
                        sm_pgo["targets"].append(st_row["target_score_pct"])

        courses_summary.append({
            "course_id": cid,
            "course_code": c_code,
            "course_title": c_title,
            "section": c_sec,
            "program_code": metrics.get("program_code") or normalize_program_code(doc.get("program_code") or "EE"),
            "semester_ay": metrics.get("semester_ay") or str(doc.get("semester_ay") or "").strip(),
            "has_scores": has_scores,
            "students_count": len(students_m),
            "aligned_clos_count": len(clo_align_map),
            "aligned_pgos": sorted(course_pgo_set),
            "aligned_pis": sorted(course_pi_set),
            "ied_levels": sorted(course_ied_set),
        })

    # Finalize PI Metrics
    final_pis: List[Dict[str, Any]] = []
    pi_node_lookup: Dict[str, Dict[str, Any]] = {}
    for pi_id in sorted(pi_acc.keys()):
        b = pi_acc[pi_id]
        st_rows: List[Dict[str, Any]] = []
        assessed_cnt = 0
        attained_cnt = 0
        all_grades: List[float] = []

        for sid in sorted(b["student_buckets"].keys()):
            sb = b["student_buckets"][sid]
            if sb["grades"]:
                avg_g = round(sum(sb["grades"]) / len(sb["grades"]), 2)
                tgt = round(sum(sb["targets"]) / len(sb["targets"]), 2) if sb["targets"] else 75.0
                att = avg_g >= tgt
                assessed_cnt += 1
                if att:
                    attained_cnt += 1
                all_grades.append(avg_g)
            else:
                avg_g = None
                tgt = 75.0
                att = None

            st_rows.append({
                "student_id": sid,
                "name": sb["name"],
                "cohort": sb["cohort"],
                "pi_grade": avg_g,
                "target_score_pct": tgt,
                "attained": att,
                "ied_levels": sorted(sb["ieds"]),
                "details": sb["details"],
            })

        pi_avg = round(sum(all_grades) / len(all_grades), 2) if all_grades else None
        pi_att_pct = round((attained_cnt / assessed_cnt) * 100.0, 1) if assessed_cnt > 0 else None
        b["is_assessed"] = assessed_cnt > 0

        aligned_courses_clean = [
            {**cv, "ied_levels": sorted(cv["ied_levels"])}
            for cv in b["aligned_courses"].values()
        ]
        pi_obj = {
            "node_key": f"pi:{pi_id}",
            "node_type": "pi",
            "pi_id": pi_id,
            "pgo_id": b["pgo_id"],
            "pgo_label": b["pgo_label"],
            "description": b["description"],
            "is_aligned": b["is_aligned"],
            "is_assessed": b["is_assessed"],
            "ied_levels": sorted(b["ied_levels"]),
            "aligned_courses": aligned_courses_clean,
            "aligned_clos": sorted(b["aligned_clos"]),
            "enrolled_students_count": len(st_rows),
            "assessed_students_count": assessed_cnt,
            "attained_students_count": attained_cnt,
            "avg_grade": pi_avg,
            "attainment_rate_pct": pi_att_pct,
            "student_ids": st_rows,
        }
        final_pis.append(pi_obj)
        pi_node_lookup[pi_id] = pi_obj

    # Finalize PGO Metrics
    final_pgos: List[Dict[str, Any]] = []
    assessed_pgos_cnt = 0
    pgos_meeting_target = 0
    pgo_grade_pool: List[float] = []
    pgo_att_pool: List[float] = []

    for pid in sorted(pgo_acc.keys()):
        b = pgo_acc[pid]
        st_rows = []
        assessed_cnt = 0
        attained_cnt = 0
        all_grades = []

        for sid in sorted(b["student_buckets"].keys()):
            sb = b["student_buckets"][sid]
            if sb["grades"]:
                avg_g = round(sum(sb["grades"]) / len(sb["grades"]), 2)
                tgt = round(sum(sb["targets"]) / len(sb["targets"]), 2) if sb["targets"] else 75.0
                att = avg_g >= tgt
                assessed_cnt += 1
                if att:
                    attained_cnt += 1
                all_grades.append(avg_g)
            else:
                avg_g = None
                tgt = 75.0
                att = None

            st_rows.append({
                "student_id": sid,
                "name": sb["name"],
                "cohort": sb["cohort"],
                "pgo_grade": avg_g,
                "target_score_pct": tgt,
                "attained": att,
                "ied_levels": sorted(sb["ieds"]),
                "details": sb["details"],
            })

        pgo_avg = round(sum(all_grades) / len(all_grades), 2) if all_grades else None
        pgo_att_pct = round((attained_cnt / assessed_cnt) * 100.0, 1) if assessed_cnt > 0 else None
        is_assessed = assessed_cnt > 0
        meets_target = (pgo_avg >= 75.0) if (pgo_avg is not None) else None

        if is_assessed:
            assessed_pgos_cnt += 1
            if pgo_avg is not None:
                pgo_grade_pool.append(pgo_avg)
            if pgo_att_pct is not None:
                pgo_att_pool.append(pgo_att_pct)
            if meets_target:
                pgos_meeting_target += 1

        ied_summary = {}
        for lvl in ("I", "E", "D"):
            vals = b["ied_scores"][lvl]
            ied_summary[lvl] = {
                "count": len(vals),
                "avg_grade": round(sum(vals) / len(vals), 2) if vals else None,
            }

        child_pis = [p for p in final_pis if p["pgo_id"] == pid]
        aligned_courses_clean = [
            {**cv, "ied_levels": sorted(cv["ied_levels"])}
            for cv in b["aligned_courses"].values()
        ]

        final_pgos.append({
            "node_key": f"pgo:{pid}",
            "node_type": "pgo",
            "pgo_id": pid,
            "pgo_label": b["pgo_label"],
            "keyword": b["keyword"],
            "description": b["description"],
            "is_aligned": b["is_aligned"],
            "is_assessed": is_assessed,
            "ied_levels": sorted(b["ied_levels"]),
            "ied_summary": ied_summary,
            "aligned_courses": aligned_courses_clean,
            "aligned_clos": sorted(b["aligned_clos"]),
            "pis": child_pis,
            "enrolled_students_count": len(st_rows),
            "assessed_students_count": assessed_cnt,
            "attained_students_count": attained_cnt,
            "avg_grade": pgo_avg,
            "attainment_rate_pct": pgo_att_pct,
            "target_score_pct": 75.0,
            "meets_target": meets_target,
            "student_ids": st_rows,
        })

    # Finalize Student ID Matrix & Cohort Aggregation
    students_matrix: List[Dict[str, Any]] = []
    cohort_buckets: Dict[str, Dict[str, Any]] = {}
    available_cohorts_set: Set[str] = set()
    assessed_students_total = 0

    for sid in sorted(students_acc.keys()):
        sm = students_acc[sid]
        available_cohorts_set.add(sm["cohort"])

        pgo_scores_clean: Dict[str, Dict[str, Any]] = {}
        st_grades: List[float] = []
        st_attained_pgos = 0
        st_assessed_pgos = 0

        for pid, pm in sm["pgo_map"].items():
            if pm["grades"]:
                g_avg = round(sum(pm["grades"]) / len(pm["grades"]), 2)
                tgt = round(sum(pm["targets"]) / len(pm["targets"]), 2) if pm["targets"] else 75.0
                att = g_avg >= tgt
                st_assessed_pgos += 1
                st_grades.append(g_avg)
                if att:
                    st_attained_pgos += 1
            else:
                g_avg = None
                tgt = 75.0
                att = None
            pgo_scores_clean[pid] = {
                "pgo_id": pid,
                "grade": g_avg,
                "target": tgt,
                "attained": att,
                "ied_levels": sorted(pm["ieds"]),
                "clos_count": pm["clos_count"],
            }

        pi_scores_clean: Dict[str, Dict[str, Any]] = {}
        for pi_id, pm in sm["pi_map"].items():
            if pm["grades"]:
                g_avg = round(sum(pm["grades"]) / len(pm["grades"]), 2)
                tgt = round(sum(pm["targets"]) / len(pm["targets"]), 2) if pm["targets"] else 75.0
                att = g_avg >= tgt
            else:
                g_avg = None
                tgt = 75.0
                att = None
            pi_scores_clean[pi_id] = {
                "pi_id": pi_id,
                "pgo_id": pm["pgo_id"],
                "grade": g_avg,
                "target": tgt,
                "attained": att,
                "ied_levels": sorted(pm["ieds"]),
                "courses": sorted(pm["courses"]),
            }

        overall_grade = round(sum(st_grades) / len(st_grades), 2) if st_grades else None
        overall_att_pct = round((st_attained_pgos / st_assessed_pgos) * 100.0, 1) if st_assessed_pgos > 0 else None
        if st_assessed_pgos > 0:
            assessed_students_total += 1

        st_entry = {
            "student_id": sid,
            "name": sm["name"],
            "cohort": sm["cohort"],
            "courses": list(sm["courses_map"].values()),
            "pi_scores": pi_scores_clean,
            "pgo_scores": pgo_scores_clean,
            "assessed_pgos_count": st_assessed_pgos,
            "attained_pgos_count": st_attained_pgos,
            "overall_pgo_grade": overall_grade,
            "overall_attainment_pct": overall_att_pct,
            "clo_details": sm["clo_details"],
        }
        students_matrix.append(st_entry)

        # Cohort Aggregation
        coh = sm["cohort"]
        cb = cohort_buckets.setdefault(coh, {
            "cohort": coh,
            "label": f"Batch {coh} ({coh}-XXXXX)" if coh.isdigit() else f"Cohort: {coh}",
            "student_count": 0,
            "assessed_count": 0,
            "grades": [],
            "att_pcts": [],
            "pgo_grades": {},
        })
        cb["student_count"] += 1
        if overall_grade is not None:
            cb["assessed_count"] += 1
            cb["grades"].append(overall_grade)
        if overall_att_pct is not None:
            cb["att_pcts"].append(overall_att_pct)
        for pid, psc in pgo_scores_clean.items():
            if psc["grade"] is not None:
                cb["pgo_grades"].setdefault(pid, []).append(psc["grade"])

    final_cohorts: List[Dict[str, Any]] = []
    for coh in sorted(cohort_buckets.keys(), reverse=True):
        cb = cohort_buckets[coh]
        pgo_avgs = {
            pid: round(sum(vals) / len(vals), 2)
            for pid, vals in cb["pgo_grades"].items() if vals
        }
        final_cohorts.append({
            "cohort": coh,
            "label": cb["label"],
            "student_count": cb["student_count"],
            "assessed_count": cb["assessed_count"],
            "avg_pgo_grade": round(sum(cb["grades"]) / len(cb["grades"]), 2) if cb["grades"] else None,
            "attainment_rate_pct": round(sum(cb["att_pcts"]) / len(cb["att_pcts"]), 1) if cb["att_pcts"] else None,
            "pgos": pgo_avgs,
        })

    # Filter Flowchart nodes strictly to aligned/active nodes so the graph stays clear & readable
    flow_cclo_nodes = sorted(
        course_clo_nodes.values(),
        key=lambda x: (x["course_code"], x["clo_id"]),
    )
    flow_pi_nodes = [p for p in final_pis if p["is_aligned"]]
    flow_pgo_nodes = [p for p in final_pgos if p["is_aligned"]]

    overall_att_pct = round(sum(pgo_att_pool) / len(pgo_att_pool), 1) if pgo_att_pool else 0.0
    overall_avg_grade = round(sum(pgo_grade_pool) / len(pgo_grade_pool), 2) if pgo_grade_pool else 0.0

    program_directory = build_program_pgo_pi_directory(
        scope=scope,
        pgo_tree=pgo_tree,
        final_pgos=final_pgos,
        pi_node_lookup=pi_node_lookup,
        faculty_aligned_pgos=faculty_aligned_pgos,
        faculty_aligned_pis=faculty_aligned_pis,
        faculty_program_codes=available_programs_set,
        program_filter=program_filter,
    )
    all_dir_progs = build_program_pgo_pi_directory(
        scope=scope,
        pgo_tree=pgo_tree,
        final_pgos=final_pgos,
        pi_node_lookup=pi_node_lookup,
        faculty_aligned_pgos=faculty_aligned_pgos,
        faculty_aligned_pis=faculty_aligned_pis,
        faculty_program_codes=available_programs_set,
        program_filter="ALL",
    )
    dir_program_codes = [p["program_code"] for p in all_dir_progs.get("programs", [])]
    combined_programs = sorted(available_programs_set | set(dir_program_codes))

    return {
        "success": True,
        "scope": {
            **scope,
            "visible_pgo_count": len(final_pgos),
            "total_program_pgos": len(pgo_tree),
        },
        "filters": {
            "program": prog_flt,
            "course_id": course_flt,
            "ied": ied_flt,
            "cohort": cohort_flt,
            "q": q_norm,
            "available_programs": combined_programs,
            "available_directory_programs": [
                {"program_code": p["program_code"], "degree_label": p["degree_label"], "program_name": p["program_name"]}
                for p in all_dir_progs.get("programs", [])
            ],
            "available_courses": available_courses_meta,
            "available_cohorts": sorted(available_cohorts_set, reverse=True),
        },
        "kpis": {
            "visible_pgos": len(final_pgos),
            "aligned_pgos": len(flow_pgo_nodes),
            "assessed_pgos": assessed_pgos_cnt,
            "pgos_meeting_target": pgos_meeting_target,
            "overall_attainment_pct": overall_att_pct,
            "overall_avg_grade": overall_avg_grade,
            "total_students_assessed": assessed_students_total,
            "total_students_enrolled": len(students_matrix),
            "aligned_courses_count": len(courses_summary),
            "assessed_courses_count": sum(1 for c in courses_summary if c["has_scores"]),
            "aligned_clos_count": total_aligned_clos,
            "target_threshold_pct": 75.0,
        },
        "pgos": final_pgos,
        "pis": final_pis,
        "program_directory": program_directory,
        "courses": courses_summary,
        "cohorts": final_cohorts,
        "students_matrix": students_matrix,
        "flowchart": {
            "course_clo_nodes": flow_cclo_nodes,
            "pi_nodes": flow_pi_nodes,
            "pgo_nodes": flow_pgo_nodes,
            "edges": flowchart_edges,
        },
    }
