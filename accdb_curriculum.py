"""
Direct Curriculum Data Access Layer for PGO-PI-IGA.accdb (Microsoft Access).
Provides authoritative curriculum data for Bachelor of Science in Electrical Engineering (BSEE):
  - Course Codes & Titles
  - Authoritative Course Descriptions
  - Lecture, Lab, and Total Units / Hours
  - Pre-requisites and Co-requisites
  - PGO-PI-IGA (IED) Alignment Mappings

All queries use direct SQL through pyodbc with graceful caching and fallback.
"""

import os
import copy
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCDB_PATH = os.path.join(BASE_DIR, "prospectus", "PGO-PI-IGA.accdb")
CONN_STR = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ACCDB_PATH};"

_CACHED_BSEE_COURSES: Optional[List[Dict[str, Any]]] = None


def query_accdb_bsee_courses(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Direct SQL extraction from PGO-PI-IGA.accdb.
    Fetches Courses_EE, Course_PI, PI, PGO, IED, PGO_PI_IGA, and Prereq_Coreq.
    """
    global _CACHED_BSEE_COURSES
    if _CACHED_BSEE_COURSES is not None and not force_refresh:
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]

    if not os.path.exists(ACCDB_PATH):
        logger.warning(f"Access database not found at {ACCDB_PATH}. Falling back to program_catalogs.")
        from program_catalogs.courses_ee import BSEE_COURSES
        _CACHED_BSEE_COURSES = BSEE_COURSES
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]

    import pyodbc

    try:
        conn = pyodbc.connect(CONN_STR, autocommit=True)
        cur = conn.cursor()

        # 1. PI to IGA Mapping (PGO_PI_IGA)
        cur.execute("SELECT [PI ID], [IGA ID] FROM [PGO_PI_IGA]")
        pi_to_igas: Dict[str, List[str]] = {}
        for pi_id, iga_id in cur.fetchall():
            pi_clean = (pi_id or "").strip().rstrip(".")
            iga_clean = (iga_id or "").strip()
            if pi_clean not in pi_to_igas:
                pi_to_igas[pi_clean] = []
            if iga_clean and iga_clean not in pi_to_igas[pi_clean]:
                pi_to_igas[pi_clean].append(iga_clean)

        # 2. Prerequisites & Co-requisites (Prereq_Coreq)
        cur.execute("SELECT [Course Code], [Prereq Code], [Coreq Code] FROM [Prereq_Coreq]")
        course_prereqs: Dict[str, List[str]] = {}
        course_coreqs: Dict[str, List[str]] = {}
        for code, prereq, coreq in cur.fetchall():
            c_code = (code or "").strip()
            p_code = (prereq or "").strip()
            co_code = (coreq or "").strip()

            if c_code not in course_prereqs:
                course_prereqs[c_code] = []
            if p_code and p_code.lower() != "none" and p_code not in course_prereqs[c_code]:
                course_prereqs[c_code].append(p_code)

            if c_code not in course_coreqs:
                course_coreqs[c_code] = []
            if co_code and co_code.lower() != "none" and co_code not in course_coreqs[c_code]:
                course_coreqs[c_code].append(co_code)
                if co_code not in course_coreqs:
                    course_coreqs[co_code] = []
                if c_code not in course_coreqs[co_code]:
                    course_coreqs[co_code].append(c_code)

        # 3. Course_PI joined with IED, PI, PGO
        cur.execute("""
            SELECT 
                cp.[Course Code],
                cp.[PI ID],
                cp.[IED ID],
                i.[IED Name],
                pi.[PI Description],
                pgo.[PGO ID],
                pgo.[PGO Keyword],
                pgo.[PGO Description]
            FROM ((([Course_PI] cp
            LEFT JOIN [IED] i ON cp.[IED ID] = i.[IED ID])
            LEFT JOIN [PI] pi ON cp.[PI ID] = pi.[PI ID])
            LEFT JOIN [PGO] pgo ON pi.[PGO ID] = pgo.[PGO ID])
            ORDER BY cp.[Course Code], cp.[PI ID]
        """)
        course_pi_map: Dict[str, List[Dict[str, Any]]] = {}
        for code, pi_id, ied_id, ied_name, pi_desc, pgo_id, pgo_kw, pgo_desc in cur.fetchall():
            c_code = (code or "").strip()
            pi_clean = (pi_id or "").strip().rstrip(".")
            pgo_clean = (pgo_id or "").strip().lower()
            ied_label = (ied_name or "").strip()
            ied_code = "I" if ied_label == "Introductory" else ("E" if ied_label == "Enabling" else "D")
            igas_str = ", ".join(pi_to_igas.get(pi_clean, []))

            item = {
                "pgo": f"PGO {pgo_clean}",
                "pgo_keyword": (pgo_kw or "").strip(),
                "pi": pi_clean,
                "pi_description": (pi_desc or "").strip(),
                "ied": ied_code,
                "ied_label": ied_label,
                "igas": igas_str
            }
            if c_code not in course_pi_map:
                course_pi_map[c_code] = []
            course_pi_map[c_code].append(item)

        # 4. Courses_EE Master Table
        cur.execute("""
            SELECT [Course Code], [Course Title], [Course Description], [Lecture Units], [Laboratory Units], [Year Level], [Semester]
            FROM [Courses_EE]
            ORDER BY [Year Level], [Semester], [Course Code]
        """)
        raw_courses = cur.fetchall()
        conn.close()

        # Existing metadata lookup for topics & sdgs retention
        from program_catalogs.courses_ee import BSEE_COURSES as fallback_bsee
        fallback_lookup = {c["code"].split(" - ")[0].strip(): c for c in fallback_bsee}

        year_map = {1: "First Year", 2: "Second Year", 3: "Third Year", 4: "Fourth Year"}
        sem_map = {1: "1st Semester", 2: "2nd Semester"}

        courses: List[Dict[str, Any]] = []
        for code, title, desc, lec, lab, yr, sem in raw_courses:
            c_code = (code or "").strip()
            c_title = (title or "").strip()
            # Authoritative description directly from accdb
            c_desc = (desc or "").strip()

            lec_u = int(lec or 0)
            lab_u = int(lab or 0)
            tot_u = lec_u + lab_u

            lec_lab_type = "Lecture and Laboratory" if (lec_u > 0 and lab_u > 0) else ("Laboratory" if lab_u > 0 else "Lecture")
            credit_units_str = f"{tot_u}.0 Units \u2013 {lec_lab_type}"
            hrs_parts = []
            if lec_u > 0:
                hrs_parts.append(f"{lec_u} hours Lecture")
            if lab_u > 0:
                hrs_parts.append(f"{lab_u * 3} hours Laboratory")
            total_hrs = lec_u + (lab_u * 3)
            hours_str = f"{total_hrs} Hours/Week ({', '.join(hrs_parts)})" if hrs_parts else "3 Hours/Week"

            pr_list = course_prereqs.get(c_code, [])
            prereq_str = ", ".join(pr_list) if pr_list else "None"

            co_list = course_coreqs.get(c_code, [])
            coreq_str = ", ".join(co_list) if co_list else "None"

            pi_mappings = course_pi_map.get(c_code, [])
            pgo_pi_summary = "; ".join([f"{m['pgo']}-{m['pi']} [{m['ied']}]" for m in pi_mappings[:3]]) if pi_mappings else ""

            fb = fallback_lookup.get(c_code, {})
            # If accdb has no PI mapping for this course, fallback to existing mapping
            final_pgo_pi = pgo_pi_summary if pgo_pi_summary else fb.get("pgo_pi", "")
            final_pgo_pi_mappings = pi_mappings if pi_mappings else fb.get("pgo_pi_mappings", [])

            # If accdb description was empty (e.g. PE/NSTP/Elective), allow fallback description if available
            final_desc = c_desc if c_desc else fb.get("description", "")
            topics = fb.get("topics", [])
            sdgs = fb.get("sdgs", "SDG 4: Quality Education")

            courses.append({
                "code": c_code,
                "title": c_title,
                "description": final_desc,
                "lecture_units": lec_u,
                "lab_units": lab_u,
                "credit_units": credit_units_str,
                "lec_lab": lec_lab_type,
                "hours": hours_str,
                "year_level": year_map.get(yr, f"Year {yr}"),
                "semester": sem_map.get(sem, f"Semester {sem}"),
                "prereqs": prereq_str,
                "coreqs": coreq_str,
                "pgo_pi": final_pgo_pi,
                "pgo_pi_mappings": final_pgo_pi_mappings,
                "topics": topics,
                "sdgs": sdgs
            })

        _CACHED_BSEE_COURSES = courses
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]

    except Exception as e:
        logger.error(f"Error querying PGO-PI-IGA.accdb: {e}", exc_info=True)
        from program_catalogs.courses_ee import BSEE_COURSES
        _CACHED_BSEE_COURSES = BSEE_COURSES
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]


def sync_accdb_to_catalog_and_db() -> int:
    """
    Syncs the authoritative BSEE records from PGO-PI-IGA.accdb into:
      1. catalog_data.py runtime caches (COLLEGE_DEPARTMENT_CATALOG & BSEE_COURSES)
      2. data/academic_catalog.db (SQLite database)
    Returns number of BSEE courses synced.
    """
    courses = query_accdb_bsee_courses(force_refresh=True)
    if not courses:
        return 0

    # 1. Update catalog_data
    try:
        import catalog_data
        catalog_data.BSEE_COURSES = courses
        for college in catalog_data.COLLEGE_DEPARTMENT_CATALOG:
            for dept in college.get("departments", []):
                if dept.get("program_code") == "EE":
                    dept["courses"] = courses
    except Exception as e:
        logger.error(f"Failed to update catalog_data: {e}")

    # 2. Update SQLite database data/academic_catalog.db
    try:
        import academic_db
        import json
        with academic_db.get_connection() as conn:
            cur = conn.cursor()
            # Delete existing BSEE records only
            cur.execute("DELETE FROM courses WHERE program_code = 'BSEE'")
            
            rows = []
            for c in courses:
                rows.append((
                    "BSEE",
                    c.get("code", "").strip(),
                    c.get("title", "").strip(),
                    c.get("year_level", ""),
                    c.get("credit_units", ""),
                    c.get("lec_lab", "Lecture"),
                    c.get("hours", ""),
                    c.get("prereqs", "None"),
                    c.get("coreqs", "None"),
                    c.get("description", ""),
                    json.dumps(c.get("topics", [])),
                    c.get("sdgs", ""),
                    c.get("pgo_pi", "")
                ))
            cur.executemany("""
                INSERT INTO courses (program_code, course_code, course_title, year_level, credit_units, lec_lab, contact_hours, prerequisites, corequisites, description, topics, sdgs, pgo_pi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update academic_db: {e}")

    return len(courses)
