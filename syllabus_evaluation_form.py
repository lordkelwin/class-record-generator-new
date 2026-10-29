"""
Official USeP Syllabus Evaluation Tool (FM-USeP-MID-02).

Contains the complete checklist items, statements, frameworks (CDIO, FIRe, GAD, SDG,
Cultural Sensitivity), scoring, validation, and PDF generator matching FM-USeP-MID-02.
"""
import io
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from fpdf import FPDF
from fpdf.fonts import FontFace

FORM_INFO = {
    "form_no": "FM-USeP-MID-02",
    "issue_status": "01",
    "revision_no": "00",
    "date_effective": "05 January 2026",
    "approved_by": "President",
    "title": "SYLLABUS EVALUATION FORM",
}

# --------------------------------------------------------------------------
# 1. CORE EVALUATION STATEMENTS (Fully / Partially / Not Fulfilling)
# --------------------------------------------------------------------------
CORE_EVALUATION_STATEMENTS: List[Dict[str, str]] = [
    {"id": "core_1", "text": "The USeP Vision, Mission, and Goals are correctly stated in the syllabus."},
    {"id": "core_2", "text": "The Institutional Graduate Attributes (IGAs) are fully listed and accurate."},
    {"id": "core_3", "text": "The course code, title, units, and prerequisites match the approved curriculum."},
    {"id": "core_4", "text": "The course description reflects the PSG or approved Program Structure."},
    {"id": "core_5", "text": "The IGA-PGO-PI alignment table is present and correctly mapped."},
    {"id": "core_6", "text": "The course outcomes (COs) are well-formulated (verb + content + standard)."},
    {"id": "core_7", "text": "The COs align with the mapped PGOs and PIs."},
    {"id": "core_8", "text": "The SDG alignment section is present and clearly described."},
    {"id": "core_9", "text": "The student workload is realistic and well-detailed."},
    {"id": "core_10", "text": "Faculty information is complete with consultation hours."},
    {"id": "core_11", "text": "Formative assessments are appropriate and aligned with COs."},
    {"id": "core_12", "text": "Summative assessments are comprehensive and mapped to COs."},
    {"id": "core_13", "text": "The measurement system (rubrics, assessment plan) is clearly stated and appropriate."},
    {"id": "core_14", "text": "The learning plan includes clear ILOs written in the correct format."},
    {"id": "core_15", "text": "The ILOs are aligned with the course outcomes (COs)."},
    {"id": "core_16", "text": "The TLAs reflect USeP’s educational philosophy: Student engagement is encouraged."},
    {"id": "core_17", "text": "The TLAs reflect USeP’s educational philosophy: Learners are given responsibility for their own learning."},
    {"id": "core_18", "text": "The TLAs reflect USeP’s educational philosophy: Critical and reflective thinking is promoted."},
    {"id": "core_19", "text": "The TLAs reflect USeP’s educational philosophy: Feedback and revision opportunities are provided."},
    {"id": "core_20", "text": "References are updated, relevant, and in APA format."},
    {"id": "core_21", "text": "Classroom policies reflect professionalism, inclusivity, and academic integrity."},
    {"id": "core_22", "text": "Academic honesty and plagiarism policies are clearly stated."},
    {"id": "core_23", "text": "Responsible use of AI tools is clearly addressed."},
]

# --------------------------------------------------------------------------
# 2. INTEGRATION AREAS (Fully / Partially / Not Fulfilling)
# --------------------------------------------------------------------------
FRAMEWORK_INTEGRATION_AREAS: List[Dict[str, str]] = [
    {"id": "int_cdio", "text": "The CDIO Framework (Conceive–Design–Implement–Operate) is embedded in COs, TLAs, or projects."},
    {"id": "int_fire", "text": "The Fourth Industrial Revolution (FIRe) skills are explicitly addressed in content or activities."},
    {"id": "int_sdg", "text": "The course integrates relevant Sustainable Development Goals (SDGs) meaningfully."},
    {"id": "int_gad", "text": "The course applies Gender and Development (GAD) principles in language, examples, and policy."},
    {"id": "int_cult", "text": "Cultural sensitivity and conflict sensitivity are considered in content and classroom policies."},
]

# --------------------------------------------------------------------------
# 3. ANNEX A DETAILED CHECKLIST (Yes / No / Remarks)
# --------------------------------------------------------------------------
ANNEX_A_SECTIONS: List[Dict[str, Any]] = [
    {
        "category": "Conceive, Design, Implement, Operate (CDIO) Framework Checklist",
        "items": [
            {"id": "cdio_1", "text": "The course objectives are clearly defined and encourage innovation and idea generation."},
            {"id": "cdio_2", "text": "The course provides opportunities for students to engage in iterative design and refinement."},
            {"id": "cdio_3", "text": "The course includes hands-on activities and practical implementation."},
            {"id": "cdio_4", "text": "The course includes real-world applications and user feedback."},
        ]
    },
    {
        "category": "Fourth Industrial Revolution (FIRe) Checklist",
        "items": [
            {"id": "fire_1", "text": "The syllabus promotes critical thinking, creativity, communication, and collaboration through learning activities."},
            {"id": "fire_2", "text": "The syllabus fosters character qualities such as curiosity, initiative, persistence, adaptability, leadership, and social and cultural awareness."},
            {"id": "fire_3", "text": "The syllabus includes content on innovation and promotes inclusive practices in technology use and development."},
            {"id": "fire_4", "text": "The syllabus incorporates discussions on the circular economy, sustainability, and green technologies."},
        ]
    },
    {
        "category": "Cultural Sensitivity and Conflict Sensitivity Checklist",
        "items": [
            {"id": "cult_1", "text": "The syllabus content includes localized or culturally relevant examples, contexts, or activities."},
            {"id": "cult_2", "text": "The instructional materials reflected in the syllabus are respectful of local, ethnic, or indigenous knowledge systems."},
            {"id": "cult_3", "text": "Activities promote multicultural awareness, peace education, or community-based perspectives."},
        ]
    },
    {
        "category": "Sustainable Development Goals Framework Alignment",
        "items": [
            {"id": "sdg_1", "text": "Course topics explicitly or implicitly support one or more SDGs (e.g., Quality Education, Gender Equality, Climate Action)."},
            {"id": "sdg_2", "text": "Teaching-learning activities encourage sustainability-oriented thinking and advocacy."},
            {"id": "sdg_3", "text": "Activities provide opportunities for students to reflect on or act on global/local development issues."},
        ]
    },
    {
        "category": "Gender and Development (GAD) Framework Checklist",
        "note": "Note: At least one indicator must be marked yes to indicate minimum compliance with each domain.",
        "items": [
            {"id": "gad_1_1", "text": "Domain 1 (ILO) 1.1 Gender Equality: At least one or more ILOs embrace the principle of equal learning opportunities and expectations for all genders, ensuring fairness in student engagement and achievement."},
            {"id": "gad_1_2", "text": "Domain 1 (ILO) 1.2 Gender Equity: At least one or more ILOs aim to empower underrepresented or marginalized genders in the discipline."},
            {"id": "gad_1_3", "text": "Domain 1 (ILO) 1.3 Gender Sensitivity: At least one or more ILOs promote gender fair values and perspectives."},
            {"id": "gad_2_1", "text": "Domain 2 (TLAs) 2.1 Gender Equality: At least one or more TLAs employ classroom activities that ensure equal engagement and participation for all learners."},
            {"id": "gad_2_2", "text": "Domain 2 (TLAs) 2.2 Gender Equity: At least one or more TLAs employ classroom activities that support a learning environment that promotes respect and value for all genders."},
            {"id": "gad_2_3", "text": "Domain 2 (TLAs) 2.3 Gender Sensitivity: At least one or more TLAs employ classroom activities encompassing various perspectives."},
            {"id": "gad_3_1", "text": "Domain 3 (Content) 3.1 Gender Equality: At least one or more learning content/s provide a balanced representation of gender in texts, authors, and theories."},
            {"id": "gad_3_2", "text": "Domain 3 (Content) 3.2 Gender Equity: At least one or more learning content/s includes discussion on gender issues relevant to different social, cultural, or economic groups."},
            {"id": "gad_3_3", "text": "Domain 3 (Content) 3.3 Gender Sensitivity: At least one or more learning content/s explicitly include topics or discussions related to gender."},
            {"id": "gad_4_1", "text": "Domain 4 (Assessment) 4.1 Gender Equality: At least one or more ATs provide equal opportunities for students of all genders to demonstrate learning through varied assessment formats."},
            {"id": "gad_4_2", "text": "Domain 4 (Assessment) 4.2 Gender Equity: At least one or more ATs include flexible assessment tasks provisions for students experiencing gender-related challenges or responsibilities."},
            {"id": "gad_4_3", "text": "Domain 4 (Assessment) 4.3 Gender Sensitivity: At least one or more ATs and grading methods are free from gender biases or assumptions."},
        ]
    },
    {
        "category": "Curriculum Mapping Alignment",
        "items": [
            {"id": "map_1", "text": "Course Outcomes (COs) are clearly aligned with Program Goals/Objectives (PGOs) and Program Outcomes (PIs)."},
            {"id": "map_2", "text": "Intended Learning Outcomes (ILOs), Content, TLAs, and Assessment Tasks are consistently aligned and clearly mapped based on the Assessment Plan."},
            {"id": "map_3", "text": "The Revised Bloom’s Taxonomy is applied across course learning outcomes and assessments, consistent with the appropriate PQF level."},
        ]
    }
]


def get_default_checklist_structure() -> Dict[str, Any]:
    return {
        "revision_type": "New",  # "New" or "Major Revision"
        "core_responses": {item["id"]: "FULLY" for item in CORE_EVALUATION_STATEMENTS},
        "core_gaps": {item["id"]: "" for item in CORE_EVALUATION_STATEMENTS},
        "int_responses": {item["id"]: "FULLY" for item in FRAMEWORK_INTEGRATION_AREAS},
        "int_gaps": {item["id"]: "" for item in FRAMEWORK_INTEGRATION_AREAS},
        "annex_responses": {item["id"]: "YES" for sec in ANNEX_A_SECTIONS for item in sec["items"]},
        "annex_remarks": {item["id"]: "" for sec in ANNEX_A_SECTIONS for item in sec["items"]},
        "recommendations": "The syllabus is comprehensive, outcome-based, well-structured, and compliant with USeP OBE and CHED CMO standards.",
        "faculty_action_taken": "",
        "overall_recommendation": "Approved",  # "Approved", "Approved with Minor Revisions", "Revise and Resubmit"
        "committee_members": [
            {"name": "NIKKA SAMANTHA A. BASAN", "role": "Review Committee Member"},
            {"name": "DELAN ZOE H. ARENGA", "role": "Review Committee Member"},
            {"name": "KIM P. RAVIDA", "role": "Review Committee Member"},
        ],
        "eval_date": datetime.now().strftime("%B %d, %Y"),
    }



def _clean_text(val: Any) -> str:
    """Sanitizes text to Latin-1 safe characters for standard PDF core fonts."""
    if val is None:
        return ""
    s = str(val)
    replacements = {
        "\u2013": "-",
        "\u2014": "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u25cf": "*",
        "\u2713": "[/]",
        "\u2714": "[/]",
        "\u2717": "[x]",
        "\u2718": "[x]",
        "\u2192": "->",
        "\u2026": "...",
        "\u00a0": " ",
        "\u200b": "",
        "\u2003": " ",
        "\u2002": " ",
        "\u2009": " ",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00b1": "+/-",
        "\u00b0": " deg",
        "\u2020": "+",
        "\u2021": "++",
        "\u2032": "'",
        "\u2033": '"',
        "\u2122": "(TM)",
        "\u00ae": "(R)",
        "\u00a9": "(C)",
        "\u25a0": "[*]",
        "\u25a1": "[ ]",
        "\u25cb": "( )",
        "\u2713": "[v]",
        "\u2714": "[v]",
        "\u2611": "[x]",
        "\u2610": "[ ]",
    }
    for orig, rep in replacements.items():
        s = s.replace(orig, rep)
    # Filter remaining non-latin1 characters
    return s.encode("latin-1", "replace").decode("latin-1")

class USePEvalPDF(FPDF):
    def __init__(self, course_meta: Dict[str, Any]):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self.course_meta = course_meta

    def header(self):
        if self.page_no() == 1:
            # Top institution & document header
            self.set_font("Helvetica", "B", 7.5)
            self.cell(100, 3.5, "Republic of the Philippines", 0, 0, "L")
            self.cell(45, 3.5, "Form No.", 0, 0, "L")
            self.cell(45, 3.5, "FM-USeP-MID-02", 0, 1, "R")

            self.set_font("Helvetica", "B", 8.5)
            self.cell(100, 4.0, "University of Southeastern Philippines", 0, 0, "L")
            self.set_font("Helvetica", "", 7.5)
            self.cell(45, 4.0, "Issue Status", 0, 0, "L")
            self.cell(45, 4.0, "01", 0, 1, "R")

            self.cell(100, 3.5, "Iñigo St., Bo. Obrero, Davao City 8000", 0, 0, "L")
            self.cell(45, 3.5, "Revision No.", 0, 0, "L")
            self.cell(45, 3.5, "00", 0, 1, "R")

            self.cell(100, 3.5, "Telephone: (082) 227-8192 | Email: president@usep.edu.ph", 0, 0, "L")
            self.cell(45, 3.5, "Date Effective", 0, 0, "L")
            self.cell(45, 3.5, "05 January 2026", 0, 1, "R")

            self.cell(100, 3.5, "Website: www.usep.edu.ph", 0, 0, "L")
            self.cell(45, 3.5, "Approved by", 0, 0, "L")
            self.cell(45, 3.5, "President", 0, 1, "R")

            self.ln(2.0)
            self.set_draw_color(180, 20, 20)
            self.set_line_width(0.6)
            self.line(10, self.get_y(), 200, self.get_y())
            self.set_draw_color(0, 0, 0)
            self.set_line_width(0.2)
            self.ln(3.0)

            self.set_font("Helvetica", "B", 11)
            self.cell(0, 5.5, "SYLLABUS EVALUATION FORM", 0, 1, "C")
            self.ln(1.5)
        else:
            self.set_font("Helvetica", "I", 7)
            self.cell(100, 4, "Form No. FM-USeP-MID-02 (Rev. 00)", 0, 0, "L")
            c_code = self.course_meta.get("course_code", "")
            self.cell(90, 4, f"{c_code} Syllabus Evaluation", 0, 1, "R")
            self.set_draw_color(180, 180, 180)
            self.line(10, self.get_y(), 200, self.get_y())
            self.set_draw_color(0, 0, 0)
            self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7.5)
        self.cell(100, 4, "College of Engineering", 0, 0, "L")
        self.cell(90, 4, f"Page {self.page_no()}", 0, 0, "R")


def _save_data_url_image(data_url: str) -> Optional[str]:
    """Helper to write data URL PNG/JPEG into a temp file for FPDF."""
    if not data_url or not isinstance(data_url, str) or not data_url.startswith("data:image"):
        return None
    try:
        header, b64_data = data_url.split(",", 1)
        ext = ".png" if "png" in header else ".jpg"
        raw_bytes = base64.b64decode(b64_data)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(raw_bytes)
        tmp.close()
        return tmp.name
    except Exception:
        return None


def generate_syllabus_evaluation_pdf(doc: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Renders official FM-USeP-MID-02 Syllabus Evaluation Form PDF with:
      - Form header & metadata
      - Course details table
      - 23 Core Evaluation Statements with checkmarks (Fully / Partially / Not Fulfilling)
      - Framework Integration Areas
      - Annex A Frameworks Checklist (CDIO, FIRe, Cultural, SDGs, GAD Domains 1-4, PQF/Bloom's)
      - Evaluation remarks, recommendations, action taken
      - Signatory blocks with embedded e-signatures
    """
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    wf = doc.get("workflow") or {}
    cl = wf.get("checklist") or {}

    course_meta = {
        "course_code": _clean_text(meta.get("course_code") or doc.get("course_code") or "EE 211"),
        "course_title": _clean_text(meta.get("course_title") or doc.get("course_title") or ""),
        "faculty_name": _clean_text(meta.get("faculty_name") or "Faculty"),
        "program": _clean_text(meta.get("program_name") or "Bachelor of Science in Electrical Engineering"),
        "department": _clean_text(meta.get("department") or "Department of Electrical Engineering"),
        "semester_ay": _clean_text(meta.get("semester_ay") or doc.get("semester_ay") or "1st Semester, A.Y. 2026-2027"),
        "credit_units": _clean_text(meta.get("credit_units") or "3.0 Units"),
        "dean_name": _clean_text(meta.get("dean_name") or "Joie D. Cataytay"),
        "program_head": _clean_text(meta.get("program_head") or "Charito O. Claro"),
    }
    _unused_meta = {
        "course_code": str(meta.get("course_code") or doc.get("course_code") or "EE 211").strip(),
        "course_title": str(meta.get("course_title") or doc.get("course_title") or "").strip(),
        "faculty_name": str(meta.get("faculty_name") or "Faculty").strip(),
        "program": str(meta.get("program_name") or "Bachelor of Science in Electrical Engineering").strip(),
        "department": str(meta.get("department") or "Department of Electrical Engineering").strip(),
        "semester_ay": str(meta.get("semester_ay") or doc.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip(),
        "credit_units": str(meta.get("credit_units") or "3.0 Units").strip(),
        "dean_name": str(meta.get("dean_name") or "Joie D. Cataytay").strip(),
        "program_head": str(meta.get("program_head") or "Charito O. Claro").strip(),
    }

    pdf = USePEvalPDF(course_meta)
    pdf.add_page()

    # Course Information Box
    pdf.set_fill_color(248, 249, 250)
    pdf.set_draw_color(160, 160, 160)
    pdf.set_line_width(0.3)
    pdf.rect(10, pdf.get_y(), 190, 24, style="FD")

    cur_y = pdf.get_y() + 2
    pdf.set_xy(13, cur_y)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(32, 4.5, "Course Code & Title:", 0, 0)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(70, 4.5, f"{course_meta['course_code']} - {course_meta['course_title'][:40]}", 0, 0)

    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(28, 4.5, "Credit Units:", 0, 0)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(50, 4.5, course_meta['credit_units'], 0, 1)

    cur_y += 5.0
    pdf.set_xy(13, cur_y)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(32, 4.5, "Faculty in Charge:", 0, 0)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(70, 4.5, course_meta['faculty_name'], 0, 0)

    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(28, 4.5, "Term / Academic Year:", 0, 0)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(50, 4.5, course_meta['semester_ay'], 0, 1)

    cur_y += 5.0
    pdf.set_xy(13, cur_y)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(32, 4.5, "Degree Program:", 0, 0)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(70, 4.5, course_meta['program'][:42], 0, 0)

    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(28, 4.5, "Date of Evaluation:", 0, 0)
    pdf.set_font("Helvetica", "", 7.5)
    eval_date = cl.get("eval_date") or datetime.now().strftime("%B %d, %Y")
    pdf.cell(50, 4.5, str(eval_date), 0, 1)

    cur_y += 5.0
    pdf.set_xy(13, cur_y)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(32, 4.5, "Review Status:", 0, 0)
    pdf.set_font("Helvetica", "B", 7.5)
    status_text = (wf.get("status") or "draft").replace("_", " ").title()
    pdf.set_text_color(180, 20, 20)
    pdf.cell(70, 4.5, f"CYCLE {wf.get('cycle', 1)} - {status_text}", 0, 0)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(28, 4.5, "Recommendation:", 0, 0)
    pdf.set_font("Helvetica", "B", 7.5)
    rec_val = cl.get("overall_recommendation") or "Pending Review"
    pdf.cell(50, 4.5, str(rec_val), 0, 1)

    pdf.set_y(pdf.get_y() + 6)

    # Table 1: Core Evaluation Statements
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 4.5, "PART I. CORE EVALUATION STATEMENTS", 0, 1, "L")
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 3.5, "Direction: Evaluated against CHED CMO and USeP Outcomes-Based Education (OBE) Standards.", 0, 1, "L")
    pdf.ln(1)

    gray_hdr = FontFace(fill_color=(235, 238, 242), emphasis="BOLD")
    resp_map = cl.get("responses") or cl.get("core_responses") or {}
    gaps_map = cl.get("comments") or cl.get("core_gaps") or {}

    col_widths = (10.0, 95.0, 18.0, 18.0, 18.0, 31.0)
    with pdf.table(col_widths=col_widths, width=190.0, line_height=3.6) as t1:
        hdr = t1.row(style=gray_hdr)
        hdr.cell("#", align="C")
        hdr.cell("Evaluation Statement")
        hdr.cell("Fully", align="C")
        hdr.cell("Partially", align="C")
        hdr.cell("Not", align="C")
        hdr.cell("Observed Gaps / Action")

        for idx, item in enumerate(CORE_EVALUATION_STATEMENTS, 1):
            r = t1.row()
            r.cell(str(idx), align="C")
            r.cell(_clean_text(item["text"]))
            ans = str(resp_map.get(item["id"]) or "").upper()
            r.cell("[ X ]" if "FULL" in ans else "[   ]", align="C")
            r.cell("[ X ]" if "PART" in ans else "[   ]", align="C")
            r.cell("[ X ]" if "NOT" in ans else "[   ]", align="C")
            gap = gaps_map.get(item["id"]) or ""
            r.cell(_clean_text(gap)[:60])

    pdf.ln(3)

    # Table 2: Framework Integration Areas
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 4.5, "PART II. INTEGRATION OF UNIVERSITY & NATIONAL FRAMEWORKS", 0, 1, "L")
    pdf.ln(1)

    with pdf.table(col_widths=col_widths, width=190.0, line_height=3.6) as t2:
        hdr = t2.row(style=gray_hdr)
        hdr.cell("#", align="C")
        hdr.cell("Framework Integration Statement")
        hdr.cell("Fully", align="C")
        hdr.cell("Partially", align="C")
        hdr.cell("Not", align="C")
        hdr.cell("Observed Gaps / Remarks")

        for idx, item in enumerate(FRAMEWORK_INTEGRATION_AREAS, 1):
            r = t2.row()
            r.cell(str(idx), align="C")
            r.cell(_clean_text(item["text"]))
            ans = str(resp_map.get(item["id"]) or "").upper()
            r.cell("[ X ]" if "FULL" in ans else "[   ]", align="C")
            r.cell("[ X ]" if "PART" in ans else "[   ]", align="C")
            r.cell("[ X ]" if "NOT" in ans else "[   ]", align="C")
            gap = gaps_map.get(item["id"]) or ""
            r.cell(_clean_text(gap)[:60])

    pdf.ln(4)

    # Annex A Checklist
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(0, 4.5, "ANNEX A: DETAILED FRAMEWORK CHECKLIST", 0, 1, "L")
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 3.5, "Checklist on CDIO, FIRe, Cultural Sensitivity, SDGs, and GAD Frameworks.", 0, 1, "L")
    pdf.ln(1)

    annex_widths = (10.0, 125.0, 16.0, 16.0, 23.0)
    with pdf.table(col_widths=annex_widths, width=190.0, line_height=3.6) as t_annex:
        hdr = t_annex.row(style=gray_hdr)
        hdr.cell("#", align="C")
        hdr.cell("Framework Indicator")
        hdr.cell("YES", align="C")
        hdr.cell("NO", align="C")
        hdr.cell("Remarks")

        counter = 1
        for sec in ANNEX_A_SECTIONS:
            cat_row = t_annex.row(style=FontFace(fill_color=(245, 245, 248), emphasis="BOLD"))
            cat_row.cell("", align="C")
            cat_row.cell(_clean_text(f">> {sec['category'].upper()}"))
            cat_row.cell("", align="C")
            cat_row.cell("", align="C")
            cat_row.cell("")

            for item in sec["items"]:
                r = t_annex.row()
                r.cell(str(counter), align="C")
                counter += 1
                r.cell(_clean_text(item["text"]))
                ans = str(resp_map.get(item["id"]) or "").upper()
                r.cell("[ X ]" if ans in ("YES", "Y", "TRUE", "FULLY") else "[   ]", align="C")
                r.cell("[ X ]" if ans in ("NO", "N", "FALSE", "NOT") else "[   ]", align="C")
                rem = gaps_map.get(item["id"]) or ""
                r.cell(_clean_text(rem)[:40])

    pdf.ln(4)

    # Summary of Recommendations & Remarks
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(0, 4.5, "EVALUATION COMMITTEE FINDINGS & RECOMMENDATIONS", 0, 1, "L")
    pdf.set_font("Helvetica", "", 7.5)
    gen_rem = cl.get("recommendations") or cl.get("general_remarks") or "The syllabus is comprehensive, outcome-based, well-structured, and compliant with USeP OBE standards."
    pdf.multi_cell(190, 4.0, _clean_text(f"Committee Recommendations:\n{gen_rem}"), border=1)
    pdf.ln(2)

    fac_act = cl.get("faculty_action_taken") or "All observed gaps and recommendations have been noted and integrated into the revised syllabus."
    pdf.multi_cell(190, 4.0, _clean_text(f"Faculty Action Taken (Conforme):\n{fac_act}"), border=1)
    pdf.ln(5)

    # Signatories Block (Official 4-Step Chain with e-signatures)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(0, 4.5, "OFFICIAL REVIEW & APPROVAL SIGNATORIES", 0, 1, "L")
    pdf.ln(2)

    # Collect available e-signature files
    sig_files = []
    signatures_by_role = {}
    for s in wf.get("signatures", []):
        signatures_by_role[s.get("role")] = s

    # 1. Review Committee Members (Row 1)
    comm_members = cl.get("committee_members") or [
        {"name": "NIKKA SAMANTHA A. BASAN", "role": "Review Committee Member"},
        {"name": "DELAN ZOE H. ARENGA", "role": "Review Committee Member"},
        {"name": "KIM P. RAVIDA", "role": "Review Committee Member"},
    ]
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.cell(0, 4.0, "REVIEWED BY (Syllabus Review Committee):", 0, 1, "L")
    pdf.ln(2)

    start_y = pdf.get_y()
    for idx, member in enumerate(comm_members[:3]):
        x_pos = 10 + idx * 64
        # Match specific signature for this committee member
        mem_sig = None
        m_uname = member.get("username")
        m_name = (member.get("name") or "").upper()
        for s in wf.get("signatures", []):
            if m_uname and s.get("username") == m_uname:
                mem_sig = s
                break
            if m_name and s.get("full_name") and (m_name in s["full_name"].upper() or s["full_name"].upper() in m_name):
                mem_sig = s
                break
        if not mem_sig and member.get("role") == "Review Committee Chair":
            mem_sig = signatures_by_role.get("review_committee_chair") or signatures_by_role.get("review_committee")
        if not mem_sig:
            mem_sig = signatures_by_role.get("review_committee")

        # Draw signature image if present
        if mem_sig and mem_sig.get("signature_data"):
            tmp_img = _save_data_url_image(mem_sig["signature_data"])
            if tmp_img:
                sig_files.append(tmp_img)
                try:
                    pdf.image(tmp_img, x=x_pos + 12, y=start_y, w=35, h=10)
                except Exception:
                    pass
        pdf.set_xy(x_pos, start_y + 11)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.cell(62, 4.0, _clean_text(member["name"].upper()), 0, 1, "C")
        pdf.set_xy(x_pos, start_y + 15)
        pdf.set_font("Helvetica", "", 7.0)
        pdf.cell(62, 3.5, member["role"], 0, 1, "C")

    pdf.set_y(start_y + 22)

    # 2. Conforme (Faculty) and Endorsed By (Program Head) (Row 2)
    start_y = pdf.get_y()
    pdf.set_xy(10, start_y)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.cell(95, 4.0, "CONFORME:", 0, 0, "L")
    pdf.cell(95, 4.0, "RECOMMENDING APPROVAL (Endorsed by):", 0, 1, "L")

    # Faculty Name
    pdf.set_xy(10, start_y + 11)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(90, 4.0, _clean_text(course_meta["faculty_name"].upper()), 0, 0, "C")

    # Program Head Name & Signature
    ph_sig = signatures_by_role.get("program_head")
    if ph_sig and ph_sig.get("signature_data"):
        tmp_img = _save_data_url_image(ph_sig["signature_data"])
        if tmp_img:
            sig_files.append(tmp_img)
            try:
                pdf.image(tmp_img, x=135, y=start_y, w=40, h=11)
            except Exception:
                pass
    pdf.set_xy(105, start_y + 11)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(90, 4.0, _clean_text(course_meta["program_head"].upper()), 0, 1, "C")

    pdf.set_xy(10, start_y + 15)
    pdf.set_font("Helvetica", "", 7.0)
    pdf.cell(90, 3.5, "Faculty in Charge", 0, 0, "C")
    pdf.cell(90, 3.5, f"Program Head - {course_meta['department'].replace('Department of ', '')}", 0, 1, "C")

    pdf.set_y(start_y + 22)

    # 3. Countersigned by (QA Head) and Approved by (Dean) (Row 3)
    start_y = pdf.get_y()
    pdf.set_xy(10, start_y)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.cell(95, 4.0, "COUNTERSIGNED BY (Quality Assurance):", 0, 0, "L")
    pdf.cell(95, 4.0, "APPROVED BY (Dean):", 0, 1, "L")

    # QA Head signature
    qa_sig = signatures_by_role.get("qa_head")
    if qa_sig and qa_sig.get("signature_data"):
        tmp_img = _save_data_url_image(qa_sig["signature_data"])
        if tmp_img:
            sig_files.append(tmp_img)
            try:
                pdf.image(tmp_img, x=35, y=start_y, w=40, h=11)
            except Exception:
                pass
    pdf.set_xy(10, start_y + 11)
    pdf.set_font("Helvetica", "B", 8)
    qa_name = (qa_sig.get("full_name") if qa_sig else "COLLEGE QUALITY ASSURANCE HEAD").upper()
    pdf.cell(90, 4.0, _clean_text(qa_name), 0, 0, "C")

    # Dean signature
    dean_sig = signatures_by_role.get("dean")
    if dean_sig and dean_sig.get("signature_data"):
        tmp_img = _save_data_url_image(dean_sig["signature_data"])
        if tmp_img:
            sig_files.append(tmp_img)
            try:
                pdf.image(tmp_img, x=135, y=start_y, w=40, h=11)
            except Exception:
                pass
    pdf.set_xy(105, start_y + 11)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(90, 4.0, _clean_text(course_meta["dean_name"].upper()), 0, 1, "C")

    pdf.set_xy(10, start_y + 15)
    pdf.set_font("Helvetica", "", 7.0)
    pdf.cell(90, 3.5, "College Quality Assurance Head", 0, 0, "C")
    pdf.cell(90, 3.5, "Dean, College of Engineering", 0, 1, "C")

    # Clean up temp images
    for f in sig_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    return bytes(pdf.output())
