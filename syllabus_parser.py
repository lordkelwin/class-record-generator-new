import json
import re
from typing import Dict, List, Tuple, Optional
import pdfplumber
from pypdf import PdfReader
import requests

from models import (
    SyllabusBlueprint,
    CourseMetadata,
    TermConfig,
    CourseOutcome,
    AssessmentCategory,
    AssessmentItem,
    CQIPlan,
    get_default_cqi_indicators,
)
from sample_syllabus import get_default_sample_students
from program_structures import get_program_structure


def extract_pdf_content(pdf_path: str) -> Tuple[str, List[List[List[str]]]]:
    """Extracts full text and all tables from a PDF file using pdfplumber with pypdf fallback."""
    full_text_parts = []
    all_tables = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    full_text_parts.append(f"--- Page {page_idx + 1} ---\n{txt}")
                tables = page.extract_tables() or []
                for tbl in tables:
                    cleaned_tbl = []
                    for row in tbl:
                        if not row:
                            continue
                        cleaned_row = [re.sub(r"\s+", " ", (cell or "")).strip() for cell in row]
                        if any(cleaned_row):
                            cleaned_tbl.append(cleaned_row)
                    if cleaned_tbl:
                        all_tables.append(cleaned_tbl)
    except Exception:
        pass

    if not full_text_parts:
        try:
            reader = PdfReader(pdf_path)
            for page_idx, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    full_text_parts.append(f"--- Page {page_idx + 1} ---\n{txt}")
        except Exception as e:
            full_text_parts.append(f"[Error reading PDF: {e}]")

    return "\n\n".join(full_text_parts), all_tables


def _non_empty_cells(row: List[str]) -> List[str]:
    return [c.strip() for c in row if c and c.strip() and c.strip() != ":"]


def _parse_metadata_from_text_and_tables(text: str, tables: List[List[List[str]]], notes: List[str]) -> CourseMetadata:
    meta = CourseMetadata()

    if "University of Southeastern Philippines" in text:
        meta.university = "University of Southeastern Philippines"
        meta.college = "COLLEGE OF ENGINEERING"
        meta.address = "Iñigo St., Bo. Obrero, Davao City 8000"

    sem_val = ""
    ay_val = ""

    # Inspect tables for key-value pairs (handling ':' or empty spacer columns)
    for tbl in tables:
        for row in tbl:
            cells = _non_empty_cells(row)
            if len(cells) < 2:
                continue
            key = cells[0].lower().rstrip(":").strip()
            val = cells[1].strip()
            if not val:
                continue

            if key in ("course code", "subject code") and len(val) < 25:
                meta.course_code = val
            elif key in ("course title", "course name", "subject title"):
                meta.course_title = val
            elif key in ("college", "college / school"):
                meta.college = val
            elif key in ("department", "department / program"):
                meta.department = val
            elif key in ("course description", "description"):
                meta.course_description = val
            elif key in ("pre-requisite", "prerequisite", "prerequisites", "pre-requisites"):
                meta.prerequisites = val
            elif key in ("co-requisite", "corequisite", "corequisites", "co-requisites"):
                meta.corequisites = val
            elif key in ("no. of hours", "contact hours", "number of hours"):
                meta.contact_hours = val
            elif key in ("consultation hours", "consultation schedule"):
                meta.consultation_hours = val
            elif key in ("email address", "email", "e-mail"):
                meta.faculty_email = val
            elif key in ("contact number", "contact no.", "telephone"):
                meta.faculty_contact = val
            elif key in ("class schedule", "schedule"):
                meta.schedule = val
            elif key in ("credit", "credit units", "units"):
                meta.credit_units = val
                if "lab" in val.lower() and "lec" not in val.lower():
                    meta.lec_lab = "Laboratory"
                elif "lec" in val.lower() and "lab" in val.lower():
                    meta.lec_lab = "Lecture/Laboratory"
                else:
                    meta.lec_lab = "Lecture"
            elif key == "semester":
                sem_val = val
            elif key in ("academic year", "a.y.", "sy"):
                ay_val = val
            elif "semester" in key and ("a.y" in key or "year" in key):
                meta.semester_ay = val
            elif key == "section":
                meta.section = val
            elif key in ("faculty name", "instructor", "professor", "faculty"):
                if "reviewed" not in val.lower() and "approved" not in val.lower():
                    meta.faculty_name = val
            elif key == "program name":
                meta.program_name = val
                if "electrical" in val.lower():
                    meta.program_code = "EE"
                    meta.department = "Department of Electrical Engineering"
                    meta.section = "EE 2A"
                elif "civil" in val.lower():
                    meta.program_code = "CE"
                    meta.department = "Department of Civil Engineering"
                elif "electronics" in val.lower():
                    meta.program_code = "ECE"
                    meta.department = "Department of Electronics Engineering"
                elif "mechanical" in val.lower():
                    meta.program_code = "ME"
                    meta.department = "Department of Mechanical Engineering"
                elif "sanitary" in val.lower():
                    meta.program_code = "SE"
                    meta.department = "Department of Sanitary Engineering"
                elif "agricultural" in val.lower() or "biosystems" in val.lower():
                    meta.program_code = "ABE"
                    meta.department = "Department of Agricultural and Biosystems Engineering"
                elif "geodetic" in val.lower():
                    meta.program_code = "GE"
                    meta.department = "Department of Geodetic Engineering"
                elif "mining" in val.lower():
                    meta.program_code = "MinE"
                    meta.department = "Department of Mining Engineering"
                elif "geology" in val.lower():
                    meta.program_code = "BSGeo"
                    meta.department = "Department of Geology"
            elif key == "transmutation":
                if "50" in val:
                    meta.transmutation_base = 50
            elif key == "passing cutoff":
                m_pct = re.search(r"(\d{2}(?:\.\d+)?)\s*%", val)
                if m_pct:
                    meta.passing_percentage = float(m_pct.group(1))

    if sem_val and ay_val:
        meta.semester_ay = f"{sem_val}, A.Y. {ay_val}"
    elif sem_val:
        meta.semester_ay = sem_val

    # Parse Pre-requisite / Co-requisite strings into structured prereq_coreq_table rows
    parsed_reqs = []
    for req_label, raw_str in [("Pre-requisite", meta.prerequisites), ("Co-requisite", meta.corequisites)]:
        if raw_str and raw_str.strip().lower() not in ("none", "n/a", ""):
            for part in re.split(r"[;\n]+", raw_str):
                part = part.strip()
                if not part or part.lower() == "none":
                    continue
                if "–" in part or "-" in part:
                    sep = "–" if "–" in part else "-"
                    c_code, c_title = part.split(sep, 1)
                    parsed_reqs.append({
                        "req_type": req_label,
                        "course_code": c_code.strip(),
                        "course_title": c_title.strip(),
                    })
                else:
                    parsed_reqs.append({
                        "req_type": req_label,
                        "course_code": part,
                        "course_title": "",
                    })
    if parsed_reqs:
        meta.prereq_coreq_table = parsed_reqs

    # Extract SDG Alignment Table rows, References Table rows, and Assessment Activity rows from PDF tables
    sdg_rows = []
    ref_rows = []
    act_rows = []
    for tbl in tables:
        for row in tbl:
            cells = _non_empty_cells(row)
            if len(cells) >= 2:
                c0 = cells[0].strip()
                c1 = cells[1].strip()
                # Check SDG row e.g. "7: Affordable and Clean Energy" or "SDG 7: ..."
                if re.match(r"^(?:SDG\s*)?\d{1,2}\s*:\s+[A-Za-z]", c0, re.I) and len(c1) > 25:
                    sdg_rows.append({"sdg": c0, "description": c1})
                # Check Reference row e.g. "Ref01"
                elif re.match(r"^Ref\s*\d+$", c0, re.I) and len(c1) > 10:
                    ref_rows.append({"code": c0, "reference": c1})
                # Check Assessment Activity row e.g. "FA1" / "SA1" / "SA2" (exclude Part VIII weight rows like "40%")
                elif re.match(r"^(FA|SA)\d+$", c0, re.I) and len(cells) >= 4 and "%" not in c1:
                    a_type = "Formative" if c0.upper().startswith("FA") else "Summative"
                    act_rows.append({
                        "type": a_type,
                        "code": c0.upper(),
                        "activity": c1,
                        "description": cells[2].strip(),
                        "clo_aligned": cells[3].strip().replace("\n", ", "),
                    })

    if sdg_rows:
        meta.sdg_table = sdg_rows
    if ref_rows:
        meta.references_table = ref_rows
    if act_rows:
        meta.syllabus_assessment_activities = act_rows

    # Check Grade Equivalence Table for "< 75 = 5.00" or Base-50
    if re.search(r"<\s*75\s*=\s*5\.00", text) or re.search(r"Base[-\s]?50", text, re.I):
        meta.transmutation_base = 50
        meta.passing_percentage = 75.0

    # Signatories at the end of USeP Syllabus ("Prepared by: Reviewed by: Approved:\nELWIN JAY J. TANO CHARITO O. CLARO JOIE D. CATAYTAY")
    sig_match = re.search(
        r"Prepared\s+by:\s+Reviewed\s+by:\s+Approved:\s*\n\s*([^\n]+)",
        text,
        re.I,
    )
    if sig_match:
        sig_line = sig_match.group(1).strip()
        # Extract uppercase names if separated
        if meta.faculty_name and sig_line.upper().startswith(meta.faculty_name.upper()):
            rem = sig_line[len(meta.faculty_name):].strip()
            parts = re.split(r"\s{2,}", rem)
            if len(parts) >= 2:
                meta.program_head = parts[0].strip()
                meta.dean_name = parts[1].strip()
            else:
                # Split by middle initial pattern (e.g. "CHARITO O. CLARO JOIE D. CATAYTAY")
                m_two = re.match(r"^([A-Z\s]+\s[A-Z]\.\s+[A-Z]+)\s+([A-Z\s]+\s[A-Z]\.\s+[A-Z]+)$", rem)
                if m_two:
                    meta.program_head = m_two.group(1).strip()
                    meta.dean_name = m_two.group(2).strip()

    notes.append(
        f"Detected Course: {meta.course_code} – {meta.course_title} | Faculty: {meta.faculty_name} | "
        f"Transmutation: Base-{meta.transmutation_base} (Passing = {meta.passing_percentage:.0f} -> 3.00)."
    )
    return meta


def _parse_pgo_lookup(tables: List[List[List[str]]], program_code: str = "EE") -> Dict[str, Dict[str, str]]:
    """
    Extracts Program Graduate Outcomes (PGO) table from USeP syllabus,
    pre-seeded with the official Program Structure catalog for program_code.
    Returns dict mapping e.g. 'PGO a', 'a', 'PGO1', '1' -> {'pgo_code': 'PGO a', 'desc': 'a) Apply...', 'pi': 'a.1. Apply...', 'iga': 'IGA2'}
    """
    pgo_map: Dict[str, Dict[str, str]] = {}
    prog_struct = get_program_structure(program_code)
    for p in prog_struct.get("pgo_pi_catalog", []):
        p_code = p.get("pgo_code", "PGO a")
        p_letter = str(p.get("letter", "a")).lower()
        p_desc = p.get("description", "")
        first_pi = p["pis"][0] if p.get("pis") else {}
        entry = {
            "pgo_code": p_code,
            "desc": p_desc,
            "pi": first_pi.get("full_text", ""),
            "iga": first_pi.get("igas", p.get("igas", "IGA2")),
        }
        pgo_map[p_code.lower()] = entry
        pgo_map[p_letter] = entry

    for tbl in tables:
        for row in tbl:
            cells = _non_empty_cells(row)
            if len(cells) >= 3:
                m_pgo = re.match(r"^(?:PGO|SO|PO|GO)\s*[-:]?\s*([a-m]|\d{1,2})\b", cells[0], re.I)
                if m_pgo:
                    token = m_pgo.group(1).lower()
                    code = f"PGO{token}" if token.isdigit() else f"PGO {token}"
                    desc = cells[1]
                    if not token.isdigit() and not re.match(r"^[a-m]\)", desc.lower()):
                        desc = f"{token}) {desc}"
                    pi = cells[2] if len(cells) >= 3 else ""
                    iga = cells[3] if len(cells) >= 4 else ""
                    entry = {"pgo_code": code, "desc": desc, "pi": pi, "iga": iga}
                    pgo_map[code.lower()] = entry
                    pgo_map[token] = entry
    return pgo_map


def _parse_course_outcomes(
    text: str,
    tables: List[List[List[str]]],
    pgo_map: Dict[str, Dict[str, str]],
    notes: List[str],
) -> List[CourseOutcome]:
    outcomes: List[CourseOutcome] = []
    seen_ids = set()

    # 1. Inspect tables for CLO / CO rows (handling spacer cells)
    for tbl in tables:
        for row in tbl:
            cells = _non_empty_cells(row)
            if len(cells) < 2:
                continue
            first_col = cells[0]
            m_co = re.match(r"^(CLO|CO|CILO|ILO)\s*[-#]?\s*(\d+)$", first_col, re.I)
            if m_co:
                prefix = "CLO" if m_co.group(1).upper() == "CLO" else "CLO"
                co_id = f"{prefix}{m_co.group(2)}"
                desc = cells[1]
                if len(desc) < 12 or co_id in seen_ids:
                    continue

                pgo_code = "PGO a"
                grad_desc = "a) Apply knowledge of mathematics and sciences to solve engineering problems"
                pi_desc = "a.1. Apply concepts in mathematics to solve engineering problems."
                iga_str = "IGA2"
                target_score = 75.0
                target_class = 50.0

                for extra in cells[2:]:
                    m_p = re.search(r"(?:PGO|PO|SO|GO)\s*[-:]?\s*([a-m]|\d{1,2})\b", extra, re.I)
                    if m_p:
                        token = m_p.group(1).lower()
                        pgo_code = f"PGO{token}" if token.isdigit() else f"PGO {token}"
                        if token in pgo_map:
                            pgo_code = pgo_map[token]["pgo_code"]
                            grad_desc = pgo_map[token]["desc"]
                            pi_desc = pgo_map[token]["pi"] or pi_desc
                            iga_str = pgo_map[token]["iga"] or iga_str
                        elif pgo_code.lower() in pgo_map:
                            grad_desc = pgo_map[pgo_code.lower()]["desc"]
                            pi_desc = pgo_map[pgo_code.lower()]["pi"] or pi_desc
                            iga_str = pgo_map[pgo_code.lower()]["iga"] or iga_str
                    if re.match(r"^(?:[a-m]|\d{1,2})\.[1-9]\b", extra.strip(), re.I):
                        pi_desc = extra.strip()
                    if re.search(r"\bIGA\s*\d", extra, re.I) and len(extra.strip()) <= 25:
                        iga_str = extra.strip()
                    pcts = re.findall(r"(\d{2}(?:\.\d+)?)\s*%", extra)
                    if pcts:
                        val = float(pcts[0])
                        if target_score == 75.0:
                            target_score = val
                        else:
                            target_class = val

                outcomes.append(
                    CourseOutcome(
                        co_id=co_id,
                        description=desc,
                        program_outcomes=pgo_code,
                        graduate_outcome_desc=grad_desc,
                        performance_indicator=pi_desc,
                        iga_aligned=iga_str,
                        target_score_pct=target_score,
                        target_class_pass_pct=target_class,
                    )
                )
                seen_ids.add(co_id)

    # 2. Regex fallback on text lines if no table CLOs found
    if not outcomes:
        pattern = re.compile(
            r"(?:^|\n)\s*(CLO|CO|CILO)\s*[-#]?\s*(\d+)\s*[:.\-–]?\s*([^\n]+)",
            re.I,
        )
        for m in pattern.finditer(text):
            co_id = f"CLO{m.group(2)}"
            if co_id in seen_ids:
                continue
            desc = re.sub(r"\s+", " ", m.group(3)).strip()
            if len(desc) >= 20:
                outcomes.append(
                    CourseOutcome(
                        co_id=co_id,
                        description=desc[:300],
                        program_outcomes="PGO a",
                        graduate_outcome_desc="a) Apply knowledge of mathematics and sciences to solve engineering problems",
                        performance_indicator="a.1. Apply concepts in mathematics to solve engineering problems.",
                        iga_aligned="IGA2",
                        target_score_pct=75.0,
                        target_class_pass_pct=50.0,
                    )
                )
                seen_ids.add(co_id)

    if outcomes:
        co_summary = ", ".join([f"{c.co_id} -> {c.program_outcomes} ({c.performance_indicator.split('.')[0]}.{c.performance_indicator.split('.')[1] if '.' in c.performance_indicator else ''})" for c in outcomes])
        notes.append(f"Extracted {len(outcomes)} Course Learning Outcomes linked to PGO & Performance Indicators: {co_summary}.")
    else:
        notes.append("No explicit CLO table found in PDF; populated default USeP CLOs (CLO1 & CLO2).")
        outcomes = [
            CourseOutcome(
                "CLO1",
                "Given DC and AC circuit networks, the student will calculate unknown circuit variables by accurately solving necessary linear and differential equations.",
                "PGO a",
                "a) Apply knowledge of mathematics and sciences to solve engineering problems",
                "a.1. Apply concepts in mathematics to solve engineering problems.",
                "IGA2",
                75.0,
                50.0,
            ),
            CourseOutcome(
                "CLO2",
                "Given multi-source electrical networks and time-varying circuits, the student will determine equivalent circuits and complete electrical responses by correctly applying fundamental network theorems and circuit principles.",
                "PGO e",
                "e) Identify, formulate, and solve engineering problems",
                "e.2. Apply concepts, theories, and principles in solving engineering problem(s)",
                "IGA5",
                75.0,
                50.0,
            ),
        ]

    return outcomes


def _parse_terms_and_categories(
    text: str,
    tables: List[List[List[str]]],
    outcomes: List[CourseOutcome],
    notes: List[str],
) -> Tuple[List[TermConfig], List[AssessmentCategory], str]:
    co_ids = [c.co_id for c in outcomes] or ["CLO1", "CLO2"]

    # 1. Extract Assessment Activity definitions (Part VI: FA1, SA1, SA2, etc.)
    activity_defs: Dict[str, Dict[str, str]] = {}
    for tbl in tables:
        for row in tbl:
            cells = _non_empty_cells(row)
            if len(cells) >= 3:
                m_act = re.match(r"^([FS]A\d+)$", cells[0], re.I)
                if m_act and not re.match(r"^\d+(?:\.\d+)?\s*%$", cells[1]):
                    code = m_act.group(1).upper()
                    act_name = cells[1]
                    aligned_str = cells[-1]
                    clos = [f"CLO{n}" for n in re.findall(r"(?:CLO|CO)\s*(\d+)", aligned_str, re.I)]
                    activity_defs[code] = {
                        "name": act_name,
                        "clos": clos or co_ids,
                    }

    # 2. Extract Summative Weights from Part VIII (Grading System and Assessment Plan)
    sa_weights: Dict[str, float] = {}
    for tbl in tables:
        if len(tbl) < 2:
            continue
        hdr_str = " ".join(_non_empty_cells(tbl[0])).lower()
        if "assessment item" in hdr_str or "percentage of final" in hdr_str:
            for row in tbl[1:]:
                cells = _non_empty_cells(row)
                if len(cells) >= 2:
                    m_sa = re.match(r"^([FS]A\d+)$", cells[0], re.I)
                    m_pct = re.search(r"^(\d{1,3}(?:\.\d+)?)\s*%$", cells[1])
                    if m_sa and m_pct:
                        sa_weights[m_sa.group(1).upper()] = float(m_pct.group(1))

    # 3. Check Student Workload for quiz counts (e.g. "Total of 4 quizzes (2 for both Midterm and Final Term)")
    quizzes_per_term = 2
    m_qz = re.search(r"(\d+)\s+for\s+both\s+Midterm\s+and\s+Final", text, re.I)
    if m_qz:
        quizzes_per_term = max(1, int(m_qz.group(1)))

    # If USeP FA/SA structure was detected (like EE 211.pdf), build the exact Midterm + Finals FA & SA structure!
    if sa_weights:
        categories: List[AssessmentCategory] = []
        terms = [
            TermConfig("Midterm", 50.0),
            TermConfig("Finals", 50.0),
        ]

        # Build Formative Assessments (FA1, FA2) per term if FA is in activity_defs
        has_fa = any(k.startswith("FA") for k in activity_defs)
        for t_idx, t_name in enumerate(["Midterm", "Finals"]):
            prefix = "MID" if t_idx == 0 else "FIN"
            if has_fa:
                fa_info = activity_defs.get("FA1", {"name": "Group Activity", "clos": co_ids})
                fa_clos = fa_info.get("clos") or co_ids
                fa_clo_str = ", ".join(fa_clos)
                fa_pts_each = round(100.0 / max(1, len(fa_clos)), 2)
                fa_clo_pts = {c: fa_pts_each for c in fa_clos}
                for fa_i in range(1, len(co_ids) + 1):
                    lbl = f"A{t_idx * len(co_ids) + fa_i}"
                    categories.append(
                        AssessmentCategory(
                            category_id=f"{prefix}_FA{fa_i}",
                            term=t_name,
                            assessment_type="FA",
                            assessment_code=f"FA{fa_i}",
                            name=f"Formative Assessment {fa_i} ({fa_info['name']})",
                            lec_lab="Lecture",
                            weight_pct=0.0,
                            items=[
                                AssessmentItem(
                                    item_id=lbl,
                                    name=f"{fa_info['name']} {t_idx * len(co_ids) + fa_i} ({fa_clo_str})",
                                    max_score=100.0,
                                    co_id=fa_clo_str,
                                    weight_pct=100.0,
                                    clo_points=dict(fa_clo_pts),
                                )
                            ],
                        )
                    )

            # Build Summative Assessments (SA1, SA2, ...) per term
            for sa_code, w_pct in sa_weights.items():
                sa_info = activity_defs.get(sa_code, {"name": sa_code, "clos": co_ids})
                act_label = sa_info["name"]
                sa_clos = sa_info["clos"] or co_ids
                sa_clo_str = ", ".join(sa_clos)
                is_exam = "exam" in act_label.lower() or sa_code == "SA2"
                items_list: List[AssessmentItem] = []

                if is_exam:
                    exam_lbl = "MTE" if t_idx == 0 else "FTE"
                    exam_clo_pts = {c: 30.0 for c in sa_clos}
                    items_list.append(
                        AssessmentItem(
                            item_id=exam_lbl,
                            name=f"{t_name} Examination ({sa_clo_str})",
                            max_score=30.0 * len(sa_clos),
                            co_id=sa_clo_str,
                            weight_pct=w_pct,
                            clo_points=exam_clo_pts,
                        )
                    )
                else:
                    num_q = quizzes_per_term
                    per_q_wt = round(w_pct / num_q, 2)
                    q_pts_each = round(30.0 / max(1, len(sa_clos)), 2)
                    q_clo_pts = {c: q_pts_each for c in sa_clos}
                    for q_i in range(num_q):
                        q_num = t_idx * num_q + q_i + 1
                        items_list.append(
                            AssessmentItem(
                                item_id=f"Q{q_num}",
                                name=f"Quiz {q_num} ({sa_clo_str})",
                                max_score=30.0,
                                co_id=sa_clo_str,
                                weight_pct=per_q_wt,
                                clo_points=dict(q_clo_pts),
                            )
                        )

                categories.append(
                    AssessmentCategory(
                        category_id=f"{prefix}_{sa_code}",
                        term=t_name,
                        assessment_type="SA",
                        assessment_code=sa_code,
                        name=f"Summative Assessment {sa_code[-1]} ({act_label})",
                        lec_lab="Lecture",
                        weight_pct=w_pct,
                        items=items_list,
                    )
                )

        sa_desc = ", ".join([f"{k} ({activity_defs.get(k, {}).get('name', k)}): {v:.0f}%" for k, v in sa_weights.items()])
        notes.append(f"Extracted USeP Assessment Plan: Formative (FA1: 0% weight) + Summative ({sa_desc}) across Midterm & Finals.")
        return terms, categories, "two_term"

    # Fallback: Generic OBE table parser (for other syllabi)
    categories = []
    cat_counter = 1
    for tbl in tables:
        if len(tbl) < 2:
            continue
        header_str = " ".join(_non_empty_cells(tbl[0])).lower()
        if "co code" in header_str or "course outcome" in header_str or "area to assess" in header_str:
            continue
        if not any(k in header_str for k in ("weight", "assessment", "grading", "component")):
            continue

        for row in tbl[1:]:
            cells = _non_empty_cells(row)
            if len(cells) < 2:
                continue
            if re.match(r"^(?:CLO|CO|CILO|ILO|TOTAL|Transmutation|Passing)\b", cells[0], re.I):
                continue
            row_joined = " ".join(cells)
            pct_match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", row_joined)
            if not pct_match:
                continue
            weight_val = float(pct_match.group(1))
            if weight_val <= 0 or weight_val > 100:
                continue

            term_val = "Finals" if "final" in cells[0].lower() else "Midterm"
            cat_name = cells[1] if cells[0].lower() in ("midterm", "finals", "final") and len(cells) >= 3 else cells[0]
            clo_pick = co_ids[(cat_counter - 1) % len(co_ids)]
            categories.append(
                AssessmentCategory(
                    category_id=f"CAT_{cat_counter}",
                    term=term_val,
                    assessment_type="SA",
                    assessment_code=f"SA{cat_counter}",
                    name=cat_name,
                    lec_lab="Lecture",
                    weight_pct=weight_val,
                    items=[
                        AssessmentItem(f"Q{cat_counter}_1", f"{cat_name} 1", 30.0, clo_pick, weight_val / 2),
                        AssessmentItem(f"Q{cat_counter}_2", f"{cat_name} 2", 30.0, co_ids[cat_counter % len(co_ids)], weight_val / 2),
                    ],
                )
            )
            cat_counter += 1

    terms = [TermConfig("Midterm", 50.0), TermConfig("Finals", 50.0)]
    return terms, categories, "two_term"


def parse_syllabus_with_gemini(
    raw_text: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> Optional[SyllabusBlueprint]:
    """Optional AI parser using Google Gemini REST API to structure syllabus text."""
    if not api_key or not raw_text.strip():
        return None

    prompt = f"""You are an expert Engineering Faculty Assistant for USeP Outcomes-Based Education (OBE).
Analyze the following syllabus text and return ONLY a valid JSON object matching this structure:
{{
  "metadata": {{
    "university": "University of Southeastern Philippines",
    "college": "COLLEGE OF ENGINEERING",
    "course_code": "EE 211",
    "course_title": "Electrical Circuits 1",
    "credit_units": "3.0 Units – Lecture",
    "semester_ay": "1st Semester, A.Y. 2026-2027",
    "section": "EE 2A",
    "faculty_name": "ELWIN JAY J. TANO",
    "program_head": "CHARITO O. CLARO",
    "dean_name": "JOIE D. CATAYTAY",
    "transmutation_base": 50,
    "passing_percentage": 75.0,
    "grading_mode": "two_term"
  }},
  "terms": [
    {{"term_name": "Midterm", "weight_pct": 50.0}},
    {{"term_name": "Finals", "weight_pct": 50.0}}
  ],
  "course_outcomes": [
    {{
      "co_id": "CLO1",
      "description": "string",
      "program_outcomes": "PGO a",
      "graduate_outcome_desc": "a) Apply knowledge of mathematics and sciences to solve engineering problems",
      "performance_indicator": "a.1. Apply concepts in mathematics to solve engineering problems.",
      "iga_aligned": "IGA2",
      "target_score_pct": 75.0,
      "target_class_pass_pct": 50.0
    }}
  ],
  "categories": [
    {{
      "category_id": "MID_SA1",
      "term": "Midterm",
      "assessment_type": "SA",
      "assessment_code": "SA1",
      "name": "Summative Assessment 1 (Quizzes)",
      "lec_lab": "Lecture",
      "weight_pct": 40.0,
      "items": [
        {{"item_id": "Q1", "name": "Quiz 1", "max_score": 30.0, "co_id": "CLO1", "weight_pct": 20.0}}
      ]
    }}
  ]
}}

SYLLABUS TEXT:
{raw_text[:18000]}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    res_json = resp.json()
    text_out = res_json["candidates"][0]["content"]["parts"][0]["text"]
    parsed_dict = json.loads(text_out)
    bp = SyllabusBlueprint.from_dict(parsed_dict)
    bp.raw_text_preview = raw_text[:6000]
    bp.parser_notes = [
        f"Parsed syllabus using Gemini AI ({model_name}).",
        f"Extracted {len(bp.course_outcomes)} CLOs linked to PGOs & Performance Indicators, and {len(bp.categories)} Assessment Categories.",
    ]
    return bp


def analyze_syllabus_pdf(
    pdf_path: str,
    use_ai: bool = False,
    gemini_api_key: str = "",
    include_sample_students: bool = True,
) -> SyllabusBlueprint:
    """
    Hybrid Syllabus Analyzer aligned with USeP FM-USeP-MID-01 & Engineering OBE syllabi.
    """
    raw_text, tables = extract_pdf_content(pdf_path)
    notes: List[str] = []

    if use_ai and gemini_api_key.strip():
        try:
            ai_bp = parse_syllabus_with_gemini(raw_text, gemini_api_key.strip())
            if ai_bp:
                if include_sample_students and not ai_bp.students:
                    ai_bp.students = get_default_sample_students()
                return ai_bp
        except Exception as e:
            notes.append(f"AI extraction fallback triggered ({e}); using rule-based PDF table/text parser.")

    metadata = _parse_metadata_from_text_and_tables(raw_text, tables, notes)
    pgo_map = _parse_pgo_lookup(tables, metadata.program_code or metadata.department)
    outcomes = _parse_course_outcomes(raw_text, tables, pgo_map, notes)
    terms, categories, grading_mode = _parse_terms_and_categories(raw_text, tables, outcomes, notes)
    metadata.grading_mode = grading_mode

    students = []
    if include_sample_students:
        base_students = get_default_sample_students()
        all_items = [it for cat in categories for it in cat.items]
        perf_profiles = [0.82, 0.76, 0.88, 0.68, 0.74, 0.91, 0.44, 0.85, 0.79, 0.56, 0.41, 0.81, 0.47, 0.77, 0.84]
        for idx, st in enumerate(base_students):
            new_scores = dict(st.scores or {})
            base_perf = perf_profiles[idx % len(perf_profiles)]
            for j, it in enumerate(all_items):
                clos_for_it = [c.strip().upper() for c in re.split(r"[,;/]+", str(it.co_id or "CLO1")) if c.strip()] or ["CLO1"]
                pts_map = it.clo_points if isinstance(getattr(it, "clo_points", None), dict) else {}
                def_pts = round(float(it.max_score or 30.0) / max(1, len(clos_for_it)), 2)
                it_total = 0
                for c_idx, clo_id in enumerate(clos_for_it):
                    clo_max = float(pts_map.get(clo_id, def_pts) or def_pts)
                    variation = ((idx * 7 + j * 5 + c_idx * 9) % 17 - 8) / 100.0
                    # Slight differentiation between CLO1 and CLO2 attainment
                    clo_shift = -0.04 if c_idx == 0 and idx in (3, 9) else (0.04 if c_idx > 0 else 0.0)
                    ratio = max(0.32, min(0.98, base_perf + variation + clo_shift))
                    sc_val = round(clo_max * ratio)
                    new_scores[f"{it.item_id}__{clo_id}"] = sc_val
                    it_total += sc_val
                new_scores[it.item_id] = it_total
            st.scores = new_scores
            st.program_year = metadata.section
            students.append(st)

    return SyllabusBlueprint(
        metadata=metadata,
        terms=terms,
        course_outcomes=outcomes,
        categories=categories,
        students=students,
        cqi_plan=CQIPlan(indicators=get_default_cqi_indicators()),
        parser_notes=notes,
        raw_text_preview=raw_text[:8000],
    )
