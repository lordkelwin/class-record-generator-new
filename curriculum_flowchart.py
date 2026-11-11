"""
Curriculum Flowchart and Dependency Graph Service.
Provides authoritative curriculum data, prerequisite/co-requisite dependency edges,
and topological term groupings directly integrated with PGO-PI-IGA.accdb and academic_db.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional

import accdb_curriculum
import academic_db

logger = logging.getLogger(__name__)


def normalize_code(code: str) -> str:
    """Normalize course code for clean comparison (e.g. 'Math  111' -> 'MATH 111')."""
    if not code:
        return ""
    return re.sub(r"\s+", " ", code.strip()).upper()


def get_curriculum_flowchart_data(program_code: str = "BSEE") -> Dict[str, Any]:
    """
    Constructs the nodes-and-edges graph and chronological term columns for the flowchart.
    Pulls directly from PGO-PI-IGA.accdb for BSEE, with fallback/support for other programs via academic_db.
    """
    prog_clean = (program_code or "BSEE").strip().upper()
    is_bsee = prog_clean in ("BSEE", "EE")

    raw_courses: List[Dict[str, Any]] = []
    source_name = "PGO-PI-IGA.accdb" if is_bsee else "academic_catalog.db"
    program_title = "Bachelor of Science in Electrical Engineering"

    if is_bsee:
        raw_courses = accdb_curriculum.query_accdb_bsee_courses(force_refresh=False)
        program_title = "Bachelor of Science in Electrical Engineering (BSEE)"
    else:
        raw_courses = academic_db.get_courses_by_program(prog_clean)
        all_progs = academic_db.get_all_programs()
        for p in all_progs:
            if p.get("code", "").upper() == prog_clean:
                program_title = f"{p.get('name', prog_clean)} ({prog_clean})"
                break

    # Standard Year and Semester ordering
    year_order = ["First Year", "Second Year", "Third Year", "Fourth Year"]
    sem_order = ["1st Semester", "2nd Semester", "Midyear Term"]

    # Term grouping helper
    def map_semester_label(sem_raw: Any) -> str:
        s = str(sem_raw or "").strip().lower()
        if "midyear" in s or "summer" in s or "3" in s:
            return "Midyear Term"
        if "2nd" in s or s == "2" or "second" in s:
            return "2nd Semester"
        return "1st Semester"

    def map_year_label(yr_raw: Any) -> str:
        y = str(yr_raw or "").strip().lower()
        if "4" in y or "fourth" in y:
            return "Fourth Year"
        if "3" in y or "third" in y:
            return "Third Year"
        if "2" in y or "second" in y:
            return "Second Year"
        return "First Year"

    # Pre-process courses
    courses_list: List[Dict[str, Any]] = []
    courses_by_code: Dict[str, Dict[str, Any]] = {}

    for c in raw_courses:
        c_code = c.get("code") or c.get("course_code") or ""
        c_code = c_code.strip()
        if not c_code:
            continue

        c_title = (c.get("title") or c.get("course_title") or "").strip()
        yr_label = map_year_label(c.get("year_level"))
        sem_label = map_semester_label(c.get("semester"))

        # Parse prerequisites
        prereqs_raw = c.get("prereqs") or c.get("prerequisites") or ""
        prereqs_list = []
        if prereqs_raw and prereqs_raw.lower() != "none":
            for p in prereqs_raw.split(","):
                p_clean = p.strip()
                if p_clean and p_clean.lower() != "none" and p_clean not in prereqs_list:
                    prereqs_list.append(p_clean)

        # Parse co-requisites
        coreqs_raw = c.get("coreqs") or c.get("corequisites") or ""
        coreqs_list = []
        if coreqs_raw and coreqs_raw.lower() != "none":
            for co in coreqs_raw.split(","):
                co_clean = co.strip()
                if co_clean and co_clean.lower() != "none" and co_clean not in coreqs_list:
                    coreqs_list.append(co_clean)

        credit_units = c.get("credit_units") or "3.0 Units"
        lec_units = c.get("lecture_units")
        lab_units = c.get("lab_units")
        if lec_units is None or lab_units is None:
            # Try to infer from credit_units string
            m_lec = re.search(r"(\d+)\s*hours?\s*Lecture", str(c.get("hours") or c.get("contact_hours") or ""), re.I)
            m_lab = re.search(r"(\d+)\s*hours?\s*Lab", str(c.get("hours") or c.get("contact_hours") or ""), re.I)
            lec_units = int(m_lec.group(1)) if m_lec else 3
            lab_units = int(int(m_lab.group(1)) / 3) if m_lab else 0

        lec_lab = c.get("lec_lab") or ("Lecture and Laboratory" if (lec_units and lab_units) else ("Laboratory" if lab_units else "Lecture"))
        hours_str = c.get("hours") or c.get("contact_hours") or f"{lec_units + (lab_units * 3)} Hours/Week"

        # Year Level Requirement / Standing based on curriculum data
        yr_req = c.get("year_level_requirement") or c.get("standing_requirement") or c.get("standing")
        if not yr_req:
            pr_lower = (c.get("prereqs") or c.get("prerequisites") or "").lower()
            if "fourth year standing" in pr_lower or "4th year standing" in pr_lower or "graduating" in pr_lower:
                yr_req = "4th Year Standing"
            elif "third year standing" in pr_lower or "3rd year standing" in pr_lower:
                yr_req = "3rd Year Standing"
            elif "second year standing" in pr_lower or "2nd year standing" in pr_lower:
                yr_req = "2nd Year Standing"
            elif yr_label == "Fourth Year":
                yr_req = "4th Year Standing"
            elif yr_label == "Third Year":
                yr_req = "3rd Year Standing"
            elif yr_label == "Second Year":
                yr_req = "2nd Year Standing"
            else:
                yr_req = "1st Year Standing / Regular Standing"

        course_item = {
            "code": c_code,
            "title": c_title,
            "year_level": yr_label,
            "semester": sem_label,
            "year_level_requirement": yr_req,
            "credit_units": credit_units,
            "lecture_units": lec_units,
            "lab_units": lab_units,
            "lec_lab": lec_lab,
            "hours": hours_str,
            "prerequisites": prereqs_list,
            "corequisites": coreqs_list,
            "postrequisites": [],
            "description": (c.get("description") or "").strip(),
            "pgo_pi": c.get("pgo_pi") or "",
            "pgo_pi_mappings": c.get("pgo_pi_mappings") or (accdb_curriculum.parse_pgo_pi_string(c.get("pgo_pi") or "") if c.get("pgo_pi") else []),
            "topics": c.get("topics") or [],
            "sdgs": c.get("sdgs") or "SDG 4: Quality Education",
        }
        courses_list.append(course_item)
        courses_by_code[c_code.upper()] = course_item

    # Build postrequisites map
    for c in courses_list:
        code_upper = c["code"].upper()
        # Check prerequisites
        for p in c["prerequisites"]:
            p_upper = p.upper()
            if p_upper in courses_by_code:
                if c["code"] not in courses_by_code[p_upper]["postrequisites"]:
                    courses_by_code[p_upper]["postrequisites"].append(c["code"])
        # Check corequisites (bidirectional)
        for co in c["corequisites"]:
            co_upper = co.upper()
            if co_upper in courses_by_code:
                if c["code"] not in courses_by_code[co_upper]["corequisites"]:
                    courses_by_code[co_upper]["corequisites"].append(c["code"])

    # Build directed edges
    edges: List[Dict[str, Any]] = []
    seen_prereq_edges = set()
    seen_coreq_edges = set()

    for c in courses_list:
        target_code = c["code"]
        target_upper = target_code.upper()

        # Prerequisite edges (Solid arrow: Source -> Target)
        for p in c["prerequisites"]:
            p_upper = p.upper()
            if p_upper in courses_by_code:
                edge_key = (courses_by_code[p_upper]["code"], target_code)
                if edge_key not in seen_prereq_edges:
                    seen_prereq_edges.add(edge_key)
                    edges.append({
                        "id": f"pre-{edge_key[0]}-{edge_key[1]}",
                        "source": edge_key[0],
                        "target": edge_key[1],
                        "type": "prerequisite"
                    })

        # Co-requisite edges (Dashed line: Source <-> Target)
        for co in c["corequisites"]:
            co_upper = co.upper()
            if co_upper in courses_by_code:
                # Store canonical undirected pair to avoid duplicate drawing
                canonical_pair = tuple(sorted([courses_by_code[co_upper]["code"], target_code]))
                if canonical_pair not in seen_coreq_edges:
                    seen_coreq_edges.add(canonical_pair)
                    edges.append({
                        "id": f"coreq-{canonical_pair[0]}-{canonical_pair[1]}",
                        "source": canonical_pair[0],
                        "target": canonical_pair[1],
                        "type": "corequisite"
                    })

    # Group into chronological Terms
    # 4 Years x (1st Sem, 2nd Sem, Midyear)
    term_definitions = [
        {"year": "First Year", "sem": "1st Semester", "key": "Y1S1", "label": "Year 1 · 1st Semester"},
        {"year": "First Year", "sem": "2nd Semester", "key": "Y1S2", "label": "Year 1 · 2nd Semester"},
        {"year": "First Year", "sem": "Midyear Term", "key": "Y1Mid", "label": "Year 1 · Midyear Term"},
        {"year": "Second Year", "sem": "1st Semester", "key": "Y2S1", "label": "Year 2 · 1st Semester"},
        {"year": "Second Year", "sem": "2nd Semester", "key": "Y2S2", "label": "Year 2 · 2nd Semester"},
        {"year": "Second Year", "sem": "Midyear Term", "key": "Y2Mid", "label": "Year 2 · Midyear Term"},
        {"year": "Third Year", "sem": "1st Semester", "key": "Y3S1", "label": "Year 3 · 1st Semester"},
        {"year": "Third Year", "sem": "2nd Semester", "key": "Y3S2", "label": "Year 3 · 2nd Semester"},
        {"year": "Fourth Year", "sem": "1st Semester", "key": "Y4S1", "label": "Year 4 · 1st Semester"},
        {"year": "Fourth Year", "sem": "2nd Semester", "key": "Y4S2", "label": "Year 4 · 2nd Semester"},
    ]

    terms: List[Dict[str, Any]] = []
    total_credit_units = 0.0

    for t_def in term_definitions:
        matching = [
            c for c in courses_list
            if c["year_level"] == t_def["year"] and c["semester"] == t_def["sem"]
        ]
        # Only include Midyear terms if they contain courses
        if not matching and "Midyear" in t_def["sem"]:
            continue

        term_units = 0.0
        for c in matching:
            # Extract units number
            u_match = re.search(r"(\d+(\.\d+)?)", str(c.get("credit_units", "")))
            if u_match:
                term_units += float(u_match.group(1))

        total_credit_units += term_units

        terms.append({
            "key": t_def["key"],
            "year": t_def["year"],
            "semester": t_def["sem"],
            "label": t_def["label"],
            "course_count": len(matching),
            "total_units": term_units,
            "courses": matching
        })

    pgo_list = accdb_curriculum.get_accdb_pgo_pi_tree()

    return {
        "program_code": prog_clean,
        "program_title": program_title,
        "source": source_name,
        "terms": terms,
        "courses": courses_list,
        "edges": edges,
        "pgo_list": pgo_list,
        "stats": {
            "total_courses": len(courses_list),
            "total_credit_units": round(total_credit_units, 1),
            "prerequisite_links": len(seen_prereq_edges),
            "corequisite_links": len(seen_coreq_edges),
            "pgo_count": len(pgo_list),
        }
    }


def get_course_details(course_code: str, program_code: str = "BSEE") -> Optional[Dict[str, Any]]:
    """
    Fetches comprehensive course metadata including authoritative description,
    prerequisites, co-requisites, downstream post-requisites, and PGO-PI (IED) mappings.
    """
    if not course_code:
        return None

    data = get_curriculum_flowchart_data(program_code)
    target_clean = course_code.strip().upper()

    for c in data.get("courses", []):
        if c.get("code", "").strip().upper() == target_clean:
            return c

    return None
