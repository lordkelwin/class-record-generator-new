"""
Official USeP Syllabus Evaluation Tool (FM-USeP-MID-02).

Strictly conforms to:
  - Syllabus/Final/Syllabus-Evaluation-Form_AEE 321.pdf (Official 5-Page Folio Format)
  - controlled documents/FM-USeP-MID-02-Syllabus-Evaluation-Form_rev01.docx (Revision 01)
"""
import io
import os
import re
import base64
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from fpdf import FPDF

FORM_INFO = {
    "form_no": "FM-USeP-MID-02",
    "issue_status": "02",
    "revision_no": "01",
    "date_effective": "24 September 2026",
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
    {"id": "core_16", "text": "The TLAs reflect USeP’s educational philosophy:"},
    {"id": "core_17", "text": "- Student engagement is encouraged."},
    {"id": "core_18", "text": "- Learners are given responsibility for their own learning."},
    {"id": "core_19", "text": "- Critical and reflective thinking is promoted."},
    {"id": "core_20", "text": "- Feedback and revision opportunities are provided."},
    {"id": "core_21", "text": "References are updated, relevant, and in APA format."},
    {"id": "core_22", "text": "Classroom policies reflect professionalism, inclusivity, and academic integrity."},
    {"id": "core_23", "text": "Academic honesty and plagiarism policies are clearly stated."},
    {"id": "core_24", "text": "Responsible use of AI tools is clearly addressed."},
    {"id": "core_25", "text": "The syllabus contains the prescribed provision on inclusivity and reasonable accommodation."},
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
_GAD_DOMAINS = [
    {
        "domain": "Domain 1: Intended Learning Outcomes",
        "desc": "The syllabus contains Intended Learning Outcome/s (ILO) that expect students to demonstrate understanding of one or more domains that can be applied within the context of the course.",
        "items": [
            {"id": "gad_1_1", "text": "1.1 Gender Equality: At least one or more ILOs embrace the principle of equal learning opportunities and expectations for all genders, ensuring fairness in student engagement and achievement."},
            {"id": "gad_1_2", "text": "1.2 Gender Equity: At least one or more ILOs aim to empower underrepresented or marginalized genders in the discipline."},
            {"id": "gad_1_3", "text": "1.3 Gender Sensitivity: At least one or more ILOs promote gender fair values and perspectives."},
        ]
    },
    {
        "domain": "Domain 2: Teaching-Learning Activities (TLAs)",
        "desc": "The Teaching-Learning Activities (TLAs) in the syllabus provide equal opportunities for participation among all learners regardless of their gender.",
        "items": [
            {"id": "gad_2_1", "text": "2.1 Gender Equality: At least one or more TLAs employ classroom activities that ensure equal engagement and participation for all learners."},
            {"id": "gad_2_2", "text": "2.2 Gender Equity: At least one or more TLAs employ classroom activities that support a learning environment that promotes respect and value for all genders."},
            {"id": "gad_2_3", "text": "2.3 Gender Sensitivity: At least one or more TLAs employ classroom activities encompassing various perspectives."},
        ]
    },
    {
        "domain": "Domain 3: Learning Contents/Topics",
        "desc": "The course syllabus’ learning contents integrate content knowledge on gender and women studies.",
        "items": [
            {"id": "gad_3_1", "text": "3.1 Gender Equality: At least one or more learning content/s provide a balanced representation of gender in texts, authors, and theories."},
            {"id": "gad_3_2", "text": "3.2 Gender Equity: At least one or more learning content/s includes discussion on gender issues relevant to different social, cultural, or economic groups."},
            {"id": "gad_3_3", "text": "3.3 Gender Sensitivity: At least one or more learning content/s explicitly include topics or discussions related to gender."},
        ]
    },
    {
        "domain": "Domain 4: Assessment Tasks (ATs)",
        "desc": "Assessment tasks (ATs), which include learning evidence/s (LEs) and assessment activities (AAs), are fair and responsive to gender, use inclusive language, unbiased performance criteria, and accessible formats.",
        "items": [
            {"id": "gad_4_1", "text": "4.1 Gender Equality: At least one or more ATs provide equal opportunities for students of all genders to demonstrate learning through varied assessment formats."},
            {"id": "gad_4_2", "text": "4.2 Gender Equity: At least one or more ATs include flexible assessment tasks provisions for students experiencing gender-related challenges or responsibilities."},
            {"id": "gad_4_3", "text": "4.3 Gender Sensitivity: At least one or more ATs and grading methods are free from gender biases or assumptions."},
        ]
    }
]

_GAD_ITEMS_FLAT = [it for d in _GAD_DOMAINS for it in d["items"]]

ANNEX_A_SECTIONS: List[Dict[str, Any]] = [
    {
        "category": "Conceive, Design, Implement, Operate (CDIO) Framework Checklist",
        "items": [
            {"id": "cdio_1", "text": "● The course objectives are clearly defined and encourage innovation and idea generation."},
            {"id": "cdio_2", "text": "● The course provides opportunities for students to engage in iterative design and refinement."},
            {"id": "cdio_3", "text": "● The course includes hands-on activities and practical implementation."},
            {"id": "cdio_4", "text": "● The course includes real-world applications and user feedback."},
        ]
    },
    {
        "category": "Fourth Industrial Revolution (FIRe) Checklist",
        "items": [
            {"id": "fire_1", "text": "● The syllabus promotes critical thinking, creativity, communication, and collaboration through learning activities."},
            {"id": "fire_2", "text": "● The syllabus fosters character qualities such as curiosity, initiative, persistence, adaptability, leadership, and social and cultural awareness."},
            {"id": "fire_3", "text": "● The syllabus includes content on innovation and promotes inclusive practices in technology use and development."},
            {"id": "fire_4", "text": "● The syllabus incorporates discussions on the circular economy, sustainability, and green technologies."},
        ]
    },
    {
        "category": "Cultural Sensitivity and Conflict Sensitivity Checklist",
        "items": [
            {"id": "cult_1", "text": "● The syllabus content includes localized or culturally relevant examples, contexts, or activities."},
            {"id": "cult_2", "text": "● The instructional materials reflected in the syllabus are respectful of local, ethnic, or indigenous knowledge systems."},
            {"id": "cult_3", "text": "● Activities promote multicultural awareness, peace education, or community-based perspectives."},
        ]
    },
    {
        "category": "Sustainable Development Goals Framework Alignment",
        "items": [
            {"id": "sdg_1", "text": "● Course topics explicitly or implicitly support one or more SDGs (e.g., Quality Education, Gender Equality, Climate Action)"},
            {"id": "sdg_2", "text": "● Teaching-learning activities encourage sustainability-oriented thinking and advocacy."},
            {"id": "sdg_3", "text": "● Activities provide opportunities for students to reflect on or act on global/local development issues."},
        ]
    },
    {
        "category": "Gender and Development Framework Checklist",
        "note": "Note: At least one indicator must be marked yes to indicate minimum compliance with each domain.",
        "domains": _GAD_DOMAINS,
        "items": _GAD_ITEMS_FLAT
    },
    {
        "category": "Curriculum Mapping Alignment",
        "items": [
            {"id": "map_1", "text": "● Course Outcomes (COs) are clearly aligned with Program Goals/Objectives (PGOs) and Program Outcomes (PIs)"},
            {"id": "map_2", "text": "● Intended Learning Outcomes (ILOs), Content, TLAs, and Assessment Tasks are consistently aligned and clearly mapped based on the Assessment Plan."},
            {"id": "map_3", "text": "● The Revised Bloom’s Taxonomy is applied across course learning outcomes and assessments, consistent with the appropriate PQF level."},
        ]
    }
]


def get_default_checklist_structure() -> Dict[str, Any]:
    annex_items = []
    for sec in ANNEX_A_SECTIONS:
        for item in sec.get("items", []):
            annex_items.append(item)

    return {
        "revision_type": "New",  # "New" or "Major Revision"
        "core_responses": {item["id"]: "FULLY" for item in CORE_EVALUATION_STATEMENTS},
        "core_gaps": {item["id"]: "" for item in CORE_EVALUATION_STATEMENTS},
        "int_responses": {item["id"]: "FULLY" for item in FRAMEWORK_INTEGRATION_AREAS},
        "int_gaps": {item["id"]: "" for item in FRAMEWORK_INTEGRATION_AREAS},
        "annex_responses": {item["id"]: "YES" for item in annex_items},
        "annex_remarks": {item["id"]: "" for item in annex_items},
        "recommendations": "",
        "faculty_action_taken": "",
        "overall_recommendation": "Approved",  # "Approved", "Approved with Minor Revisions", "Revise and Resubmit"
        "committee_members": [
            {"username": "", "name": "", "role": "Review Committee Chair"},
            {"username": "", "name": "", "role": "Review Committee Member"},
            {"username": "", "name": "", "role": "Review Committee Member"},
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
        "\u2713": "v",
        "\u2714": "v",
        "\u2717": "x",
        "\u2718": "x",
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
        "✓": "v",
        "✔": "v",
        "●": "*",
        "–": "-",
        "—": "--",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
    }
    for orig, rep in replacements.items():
        s = s.replace(orig, rep)
    return s.encode("latin-1", "replace").decode("latin-1")


def _save_data_url_image(data_url: str) -> Optional[str]:
    """Helper to write data URL PNG/JPEG into a temp file for FPDF."""
    if not data_url or not isinstance(data_url, str):
        return None
    if not data_url.startswith("data:image"):
        if os.path.exists(data_url):
            return data_url
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


class OfficialEvalPDF(FPDF):
    """
    Official USeP Folio Legal (8.5 x 13.0 inches = 215.9 x 330.2 mm) Evaluation PDF.
    Strictly follows the 5-page template of FM-USeP-MID-02.
    """
    def __init__(self, course_meta: Dict[str, Any]):
        super().__init__(orientation="P", unit="mm", format=(215.9, 330.2))
        self.set_auto_page_break(auto=False)
        self.set_margins(11.0, 12.0, 11.0)
        self.course_meta = course_meta

    def draw_footer_bar(self, page_num: int):
        self.set_xy(11.0, 310.0)
        self.set_font("Helvetica", "I", 8.5)
        acad_unit = self.course_meta.get("academic_unit") or "College of Engineering"
        self.cell(145.0, 6.0, acad_unit, border=0, align="L")
        self.cell(49.0, 6.0, f"Page {page_num} of 5", border=0, align="R")

    def draw_checkbox(self, x: float, y: float, checked: bool = False, size: float = 3.4):
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.25)
        self.rect(x, y, size, size, style="D")
        if checked:
            self.set_line_width(0.4)
            self.line(x + 0.7, y + 1.8, x + 1.4, y + 2.7)
            self.line(x + 1.4, y + 2.7, x + 2.8, y + 0.8)
            self.set_line_width(0.2)


def generate_syllabus_evaluation_pdf(doc: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Renders official FM-USeP-MID-02 Syllabus Evaluation Form strictly matching
    Syllabus-Evaluation-Form_AEE 321.pdf and FM-USeP-MID-02 Rev 01:
      - 5 Pages Folio Legal (8.5 x 13.0 inches)
      - Institutional Header with USeP logo & document control table
      - Exact 25 Core Statements split across Page 1 (1-19) and Page 2 (20-25)
      - Integration Areas & Recommendations
      - Official Signatories (Review Committee, Faculty Conforme, Program Head, Dean) with e-signatures
      - Annex A Frameworks Checklist (CDIO, FIRe, Cultural Sensitivity, SDGs, GAD 4 Domains, PQF Bloom's)
      - Page 5 Other Comments & Ruled Lines
    """
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    wf = doc.get("workflow") or {}
    cl = wf.get("checklist") or {}

    course_meta = {
        "course_code": _clean_text(meta.get("course_code") or doc.get("course_code") or "EE 211"),
        "course_title": _clean_text(meta.get("course_title") or doc.get("course_title") or ""),
        "faculty_name": _clean_text(meta.get("faculty_name") or "FACULTY"),
        "program": _clean_text(meta.get("program_name") or "ELECTRICAL ENGINEERING"),
        "academic_unit": _clean_text(meta.get("academic_unit") or meta.get("department") or "ENGINEERING"),
        "course_description": _clean_text(bp.get("course_description") or meta.get("course_description") or "The course includes history, principles, theories, and concepts of electric circuits, analysis methods, and applications."),
        "semester": _clean_text(meta.get("semester") or "1ST SEMESTER"),
        "academic_year": _clean_text(meta.get("academic_year") or "2026-2027"),
        "revision_type": cl.get("revision_type") or meta.get("revision_type") or "New",
        "program_head": _clean_text(meta.get("program_head") or "CHARITO O. CLARO"),
        "dean_name": _clean_text(meta.get("dean_name") or "JOIE D. CATAYTAY"),
    }

    resp_map = cl.get("responses") or cl.get("core_responses") or {}
    gaps_map = cl.get("comments") or cl.get("core_gaps") or {}
    annex_resp = cl.get("annex_responses") or {}
    annex_rem = cl.get("annex_remarks") or {}

    # Support legacy response keys for statements
    if "core_16" in resp_map and "core_17" not in resp_map:
        val16 = resp_map.get("core_16")
        resp_map.setdefault("core_17", val16)
        resp_map.setdefault("core_18", val16)
        resp_map.setdefault("core_19", val16)
        resp_map.setdefault("core_20", val16)

    # Collect signatures & temporary files
    sigs_by_role = {}
    sigs_by_user = {}
    sig_temp_files = []
    for s in wf.get("signatures", []):
        r = s.get("role")
        u = s.get("username")
        if r:
            sigs_by_role[r] = s
        if u:
            sigs_by_user[u] = s

    pdf = OfficialEvalPDF(course_meta)
    table_w = 194.0
    x0 = 11.0

    # =========================================================================
    # PAGE 1: Institutional Header, Course Details, Instructions, Statements 1-19
    # =========================================================================
    pdf.add_page()
    pdf.draw_footer_bar(1)

    # 1. Institutional Header Table
    y = 16.0
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.25)
    pdf.rect(x0, y, table_w, 32.5)

    # Logo
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "static", "logo_1_Image39.jpg")
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=x0 + 2.8, y=y + 3.5, w=25.0, h=25.0)
        except Exception:
            pass

    # University text
    pdf.set_xy(x0 + 30.6, y + 2.5)
    pdf.set_font("Helvetica", "", 8.0)
    pdf.cell(99.8, 4.0, "Republic of the Philippines", align="C")
    pdf.set_xy(x0 + 30.6, y + 6.8)
    pdf.set_font("Helvetica", "B", 8.8)
    pdf.cell(99.8, 4.5, "University of Southeastern Philippines", align="C")
    pdf.set_xy(x0 + 30.6, y + 11.5)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(99.8, 3.8, "Iñigo St., Bo. Obrero, Davao City 8000", align="C")
    pdf.set_xy(x0 + 30.6, y + 15.3)
    pdf.cell(99.8, 3.8, "Telephone: (082) 227-8192", align="C")
    pdf.set_xy(x0 + 30.6, y + 19.1)
    pdf.cell(99.8, 3.8, "Website: www.usep.edu.ph", align="C")
    pdf.set_xy(x0 + 30.6, y + 22.9)
    pdf.cell(99.8, 3.8, "Email: president@usep.edu.ph", align="C")

    # Document Control right box (5 rows)
    ctrl_rows = [
        ("Form No.", "FM-USeP-MID-02"),
        ("Issue Status", "02"),
        ("Revision No.", "01"),
        ("Date Effective", "24 September 2026"),
        ("Approved by", "President"),
    ]
    cx = x0 + 30.6 + 99.8
    for r_i, (k, v) in enumerate(ctrl_rows):
        ry = y + r_i * 6.5
        pdf.set_xy(cx, ry)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.cell(26.8, 6.5, k, border=1, align="L")
        pdf.set_font("Helvetica", "B" if r_i == 0 else "", 7.5)
        pdf.cell(36.8, 6.5, v, border=1, align="L")

    # Title Row (Row 5)
    pdf.set_xy(x0, y + 32.5)
    pdf.set_font("Helvetica", "B", 11.0)
    pdf.cell(table_w, 6.8, "SYLLABUS EVALUATION FORM", border=1, align="C")

    # 2. Course Metadata Table
    y_meta = y + 39.3 + 2.0
    pdf.set_xy(x0, y_meta)

    # Row 0: Choose One: [x] New   [ ] Major Revision
    is_new = "NEW" in str(course_meta["revision_type"]).upper()
    pdf.set_font("Helvetica", "", 8.0)
    pdf.rect(x0, y_meta, table_w, 6.5)
    pdf.set_xy(x0 + 4.0, y_meta + 1.2)
    pdf.write(4.2, "Choose One:  ")
    cb_y = y_meta + 1.5
    pdf.draw_checkbox(pdf.get_x(), cb_y, checked=is_new, size=3.4)
    pdf.set_x(pdf.get_x() + 5.0)
    pdf.write(4.2, "New    ")
    pdf.draw_checkbox(pdf.get_x(), cb_y, checked=(not is_new), size=3.4)
    pdf.set_x(pdf.get_x() + 5.0)
    pdf.write(4.2, "Major Revision")

    # Row 1: Faculty Name
    y_meta += 6.5
    pdf.set_xy(x0, y_meta)
    pdf.set_font("Helvetica", "B", 8.0)
    pdf.cell(35.0, 6.2, "Faculty Name", border=1, align="L")
    pdf.set_font("Helvetica", "", 8.0)
    pdf.cell(159.0, 6.2, course_meta["faculty_name"].upper(), border=1, align="L")

    # Row 2: Program | Academic Unit
    y_meta += 6.2
    pdf.set_xy(x0, y_meta)
    pdf.set_font("Helvetica", "B", 8.0)
    pdf.cell(35.0, 6.2, "Program", border=1, align="L")
    pdf.set_font("Helvetica", "", 8.0)
    pdf.cell(82.0, 6.2, course_meta["program"].upper(), border=1, align="L")
    pdf.set_font("Helvetica", "B", 8.0)
    pdf.cell(27.0, 6.2, "Academic Unit", border=1, align="L")
    pdf.set_font("Helvetica", "", 8.0)
    pdf.cell(50.0, 6.2, course_meta["academic_unit"].upper(), border=1, align="L")

    # Row 3: Course Title
    y_meta += 6.2
    pdf.set_xy(x0, y_meta)
    pdf.set_font("Helvetica", "B", 8.0)
    pdf.cell(35.0, 6.2, "Course Title", border=1, align="L")
    pdf.set_font("Helvetica", "", 8.0)
    pdf.cell(159.0, 6.2, f"{course_meta['course_code']} - {course_meta['course_title']}".upper(), border=1, align="L")

    # Row 4: Course Description
    y_meta += 6.2
    desc_text = course_meta["course_description"]
    desc_lines = pdf.multi_cell(157.0, 3.4, desc_text, dry_run=True, output="LINES")
    desc_h = max(16.5, len(desc_lines) * 3.4 + 2.5)
    pdf.set_xy(x0, y_meta)
    pdf.set_font("Helvetica", "B", 8.0)
    pdf.cell(35.0, desc_h, "Course Description", border=1, align="L")
    pdf.rect(x0 + 35.0, y_meta, 159.0, desc_h)
    pdf.set_xy(x0 + 36.0, y_meta + 1.2)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.multi_cell(157.0, 3.4, desc_text, border=0, align="L")

    # Row 5: Semester | Academic Year
    y_meta += desc_h
    pdf.set_xy(x0, y_meta)
    pdf.set_font("Helvetica", "B", 8.0)
    pdf.cell(35.0, 6.2, "Semester", border=1, align="L")
    pdf.set_font("Helvetica", "", 8.0)
    pdf.cell(82.0, 6.2, course_meta["semester"].upper(), border=1, align="L")
    pdf.set_font("Helvetica", "B", 8.0)
    pdf.cell(27.0, 6.2, "Academic Year", border=1, align="L")
    pdf.set_font("Helvetica", "", 8.0)
    pdf.cell(50.0, 6.2, course_meta["academic_year"].upper(), border=1, align="L")

    # 3. Instructions block
    y_inst = y_meta + 6.2 + 2.0
    pdf.set_xy(x0, y_inst)
    pdf.set_font("Helvetica", "", 7.5)
    inst_text = (
        "Instructions: Use this form to evaluate course syllabi. For each statement below, place a check (v) "
        "under the appropriate column if the course FULLY meets the requirement, PARTIALLY complying with, "
        "or NOT FULFILLING the requirements. For indicators that are not fully met, write down the observed gap and recommended action."
    )
    pdf.multi_cell(table_w, 3.5, inst_text, border=0, align="L")
    y_table3 = pdf.get_y() + 2.0

    # 4. Table 3: Core Evaluation Statements 1 to 19
    col_w3 = [78.8, 15.4, 22.8, 22.8, 54.2]
    # Header row
    pdf.set_xy(x0, y_table3)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(col_w3[0], 6.5, "EVALUATION STATEMENT", border=1, align="L")
    pdf.cell(col_w3[1], 6.5, "FULLY", border=1, align="C")
    pdf.cell(col_w3[2], 6.5, "PARTIALLY", border=1, align="C")
    pdf.cell(col_w3[3], 6.5, "NOT FULFILLING", border=1, align="C")
    pdf.cell(col_w3[4], 6.5, "OBSERVED GAP", border=1, align="L")
    y_table3 += 6.5

    for item in CORE_EVALUATION_STATEMENTS[:19]:
        stmt = _clean_text(item["text"])
        pdf.set_font("Helvetica", "", 7.0)
        lines = pdf.multi_cell(col_w3[0] - 2.5, 3.2, stmt, dry_run=True, output="LINES")
        row_h = max(7.2, len(lines) * 3.2 + 1.8)

        cx = x0
        for w in col_w3:
            pdf.rect(cx, y_table3, w, row_h)
            cx += w

        pdf.set_xy(x0 + 1.2, y_table3 + 1.0)
        pdf.multi_cell(col_w3[0] - 2.5, 3.2, stmt, border=0, align="L")

        ans = str(resp_map.get(item["id"]) or "FULLY").upper()
        pdf.draw_checkbox(x0 + col_w3[0] + (col_w3[1] - 3.4) / 2, y_table3 + (row_h - 3.4) / 2, checked="FULL" in ans, size=3.4)
        pdf.draw_checkbox(x0 + col_w3[0] + col_w3[1] + (col_w3[2] - 3.4) / 2, y_table3 + (row_h - 3.4) / 2, checked="PART" in ans, size=3.4)
        pdf.draw_checkbox(x0 + col_w3[0] + col_w3[1] + col_w3[2] + (col_w3[3] - 3.4) / 2, y_table3 + (row_h - 3.4) / 2, checked="NOT" in ans, size=3.4)

        gap = _clean_text(gaps_map.get(item["id"]) or "")
        if gap:
            pdf.set_xy(x0 + col_w3[0] + col_w3[1] + col_w3[2] + col_w3[3] + 1.2, y_table3 + 1.0)
            pdf.multi_cell(col_w3[4] - 2.5, 3.2, gap, border=0, align="L")

        y_table3 += row_h

    # =========================================================================
    # PAGE 2: Statements 20-25, Framework Integration, Recommendations, Signatories
    # =========================================================================
    pdf.add_page()
    pdf.draw_footer_bar(2)

    y_p2 = 14.0
    # 1. Remaining Core Statements (items 20-25)
    for item in CORE_EVALUATION_STATEMENTS[19:]:
        stmt = _clean_text(item["text"])
        pdf.set_font("Helvetica", "", 7.0)
        lines = pdf.multi_cell(col_w3[0] - 2.5, 3.2, stmt, dry_run=True, output="LINES")
        row_h = max(7.2, len(lines) * 3.2 + 1.8)

        cx = x0
        for w in col_w3:
            pdf.rect(cx, y_p2, w, row_h)
            cx += w

        pdf.set_xy(x0 + 1.2, y_p2 + 1.0)
        pdf.multi_cell(col_w3[0] - 2.5, 3.2, stmt, border=0, align="L")

        ans = str(resp_map.get(item["id"]) or "FULLY").upper()
        pdf.draw_checkbox(x0 + col_w3[0] + (col_w3[1] - 3.4) / 2, y_p2 + (row_h - 3.4) / 2, checked="FULL" in ans, size=3.4)
        pdf.draw_checkbox(x0 + col_w3[0] + col_w3[1] + (col_w3[2] - 3.4) / 2, y_p2 + (row_h - 3.4) / 2, checked="PART" in ans, size=3.4)
        pdf.draw_checkbox(x0 + col_w3[0] + col_w3[1] + col_w3[2] + (col_w3[3] - 3.4) / 2, y_p2 + (row_h - 3.4) / 2, checked="NOT" in ans, size=3.4)

        gap = _clean_text(gaps_map.get(item["id"]) or "")
        if gap:
            pdf.set_xy(x0 + col_w3[0] + col_w3[1] + col_w3[2] + col_w3[3] + 1.2, y_p2 + 1.0)
            pdf.multi_cell(col_w3[4] - 2.5, 3.2, gap, border=0, align="L")

        y_p2 += row_h

    # 2. Section Header: Attached Checklist of Frameworks Integrated into Course Syllabus
    y_p2 += 3.0
    pdf.set_xy(x0, y_p2)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(table_w, 5.0, "Attached Checklist of Frameworks Integrated into Course Syllabus", border=0, align="L")
    y_p2 += 6.0

    # 3. Table 2: Framework Integration Areas
    pdf.set_xy(x0, y_p2)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(col_w3[0], 6.2, "INTEGRATION AREA", border=1, align="L")
    pdf.cell(col_w3[1], 6.2, "FULLY", border=1, align="C")
    pdf.cell(col_w3[2], 6.2, "PARTIALLY", border=1, align="C")
    pdf.cell(col_w3[3], 6.2, "NOT FULFILLING", border=1, align="C")
    pdf.cell(col_w3[4], 6.2, "OBSERVED GAP", border=1, align="L")
    y_p2 += 6.2

    for item in FRAMEWORK_INTEGRATION_AREAS:
        stmt = _clean_text(item["text"])
        pdf.set_font("Helvetica", "", 7.0)
        lines = pdf.multi_cell(col_w3[0] - 2.5, 3.2, stmt, dry_run=True, output="LINES")
        row_h = max(7.2, len(lines) * 3.2 + 1.8)

        cx = x0
        for w in col_w3:
            pdf.rect(cx, y_p2, w, row_h)
            cx += w

        pdf.set_xy(x0 + 1.2, y_p2 + 1.0)
        pdf.multi_cell(col_w3[0] - 2.5, 3.2, stmt, border=0, align="L")

        ans = str(resp_map.get(item["id"]) or "FULLY").upper()
        pdf.draw_checkbox(x0 + col_w3[0] + (col_w3[1] - 3.4) / 2, y_p2 + (row_h - 3.4) / 2, checked="FULL" in ans, size=3.4)
        pdf.draw_checkbox(x0 + col_w3[0] + col_w3[1] + (col_w3[2] - 3.4) / 2, y_p2 + (row_h - 3.4) / 2, checked="PART" in ans, size=3.4)
        pdf.draw_checkbox(x0 + col_w3[0] + col_w3[1] + col_w3[2] + (col_w3[3] - 3.4) / 2, y_p2 + (row_h - 3.4) / 2, checked="NOT" in ans, size=3.4)

        gap = _clean_text(gaps_map.get(item["id"]) or "")
        if gap:
            pdf.set_xy(x0 + col_w3[0] + col_w3[1] + col_w3[2] + col_w3[3] + 1.2, y_p2 + 1.0)
            pdf.multi_cell(col_w3[4] - 2.5, 3.2, gap, border=0, align="L")

        y_p2 += row_h

    # 4. Recommendations for Course Syllabus Improvement
    y_p2 += 3.0
    pdf.set_xy(x0, y_p2)
    pdf.set_font("Helvetica", "B", 8.0)
    pdf.cell(table_w, 4.5, "Recommendations for Course Syllabus Improvement", border=0, align="L")
    y_p2 += 5.2

    rec_text = _clean_text(cl.get("recommendations") or cl.get("general_remarks") or "")
    rec_lines = pdf.multi_cell(table_w - 3.0, 3.2, rec_text, dry_run=True, output="LINES")
    rec_h = max(16.0, len(rec_lines) * 3.2 + 2.0)
    pdf.rect(x0, y_p2, table_w, rec_h)
    if rec_text:
        pdf.set_xy(x0 + 1.5, y_p2 + 1.2)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.multi_cell(table_w - 3.0, 3.2, rec_text, border=0, align="L")
    y_p2 += rec_h + 3.0

    # 5. Signatory Block 1: REVIEWED BY (Course Committee) and CONFORME (Faculty)
    half_w = table_w / 2.0
    pdf.set_xy(x0, y_p2)
    pdf.set_font("Helvetica", "B", 7.8)
    pdf.cell(half_w, 4.0, "REVIEWED BY:", border=0, align="L")
    pdf.set_xy(x0 + half_w, y_p2)
    pdf.cell(half_w, 4.0, "CONFORME:", border=0, align="L")
    y_p2 += 4.5

    comm_members = cl.get("committee_members") or wf.get("committee_members") or []
    mem_y = y_p2
    for m_idx in range(3):
        m = comm_members[m_idx] if m_idx < len(comm_members) else {}
        m_uname = m.get("username")
        m_name = (m.get("name") or "").upper()
        m_sig = sigs_by_user.get(m_uname) if m_uname else None
        if not m_sig and m_name:
            for s in wf.get("signatures", []):
                if s.get("full_name") and m_name in s["full_name"].upper():
                    m_sig = s
                    break
        if m_sig and m_sig.get("signature_data"):
            tmp_img = _save_data_url_image(m_sig["signature_data"])
            if tmp_img:
                sig_temp_files.append(tmp_img)
                try:
                    pdf.image(tmp_img, x=x0 + 12.0, y=mem_y - 1.0, w=28.0, h=7.5)
                except Exception:
                    pass

        pdf.set_xy(x0, mem_y + 4.5)
        pdf.set_font("Helvetica", "B" if m_name else "", 7.5)
        pdf.cell(half_w - 10.0, 3.8, m_name if m_name else "___________________________", border=0, align="L")
        mem_y += 7.5

    pdf.set_xy(x0, mem_y)
    pdf.set_font("Helvetica", "", 7.2)
    pdf.cell(half_w, 3.8, "(Course Committee)", border=0, align="L")
    mem_y += 4.2
    chair_sig = sigs_by_role.get("review_committee_chair") or sigs_by_role.get("review_committee")
    c_date = chair_sig.get("date_signed") if chair_sig else "_____________"
    pdf.set_xy(x0, mem_y)
    pdf.cell(half_w, 3.8, f"Date: {c_date}", border=0, align="L")

    # Right column: Faculty Conforme
    fac_sig = sigs_by_role.get("faculty")
    if not fac_sig:
        for s in wf.get("signatures", []):
            if s.get("step") == "submission":
                fac_sig = s
                break
    fac_y = y_p2
    if fac_sig and fac_sig.get("signature_data"):
        tmp_img = _save_data_url_image(fac_sig["signature_data"])
        if tmp_img:
            sig_temp_files.append(tmp_img)
            try:
                pdf.image(tmp_img, x=x0 + half_w + 12.0, y=fac_y + 4.0, w=28.0, h=7.5)
            except Exception:
                pass
    pdf.set_xy(x0 + half_w, fac_y + 11.5)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(half_w - 10.0, 3.8, course_meta["faculty_name"].upper(), border=0, align="L")
    pdf.set_xy(x0 + half_w, fac_y + 15.5)
    pdf.set_font("Helvetica", "", 7.2)
    pdf.cell(half_w, 3.8, "Faculty", border=0, align="L")
    f_date = fac_sig.get("date_signed") if fac_sig else "_____________"
    pdf.set_xy(x0 + half_w, fac_y + 19.5)
    pdf.cell(half_w, 3.8, f"Date: {f_date}", border=0, align="L")

    y_p2 = max(mem_y + 6.0, fac_y + 25.0)

    # 6. Table: - TO BE FILLED UP BY THE FACULTY SYLLABUS WRITER -
    pdf.set_xy(x0, y_p2)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(table_w, 5.0, "- TO BE FILLED UP BY THE FACULTY SYLLABUS WRITER -", border=1, align="C")
    y_p2 += 5.0
    gap_col_w = 72.0
    act_col_w = table_w - gap_col_w
    pdf.set_xy(x0, y_p2)
    pdf.cell(gap_col_w, 5.0, "OBSERVED GAP", border=1, align="L")
    pdf.cell(act_col_w, 5.0, "ACTION TAKEN", border=1, align="L")
    y_p2 += 5.0

    action_taken = _clean_text(cl.get("faculty_action_taken") or "")
    if action_taken:
        lines = pdf.multi_cell(act_col_w - 2.5, 3.2, action_taken, dry_run=True, output="LINES")
        act_h = max(12.0, len(lines) * 3.2 + 2.0)
        pdf.rect(x0, y_p2, gap_col_w, act_h)
        pdf.rect(x0 + gap_col_w, y_p2, act_col_w, act_h)
        pdf.set_xy(x0 + gap_col_w + 1.2, y_p2 + 1.0)
        pdf.set_font("Helvetica", "", 7.2)
        pdf.multi_cell(act_col_w - 2.5, 3.2, action_taken, border=0, align="L")
        y_p2 += act_h + 3.0
    else:
        for _ in range(2):
            pdf.rect(x0, y_p2, gap_col_w, 6.0)
            pdf.rect(x0 + gap_col_w, y_p2, act_col_w, 6.0)
            y_p2 += 6.0
        y_p2 += 3.0

    # 7. Signatory Block 2: ENDORSED BY (Program Head) and APPROVED BY (Dean)
    pdf.set_xy(x0, y_p2)
    pdf.set_font("Helvetica", "B", 7.8)
    pdf.cell(half_w, 4.0, "ENDORSED BY:", border=0, align="L")
    pdf.set_xy(x0 + half_w, y_p2)
    pdf.cell(half_w, 4.0, "APPROVED BY:", border=0, align="L")
    y_p2 += 4.5

    # Program Head
    ph_sig = sigs_by_role.get("program_head")
    ph_y = y_p2
    if ph_sig and ph_sig.get("signature_data"):
        tmp_img = _save_data_url_image(ph_sig["signature_data"])
        if tmp_img:
            sig_temp_files.append(tmp_img)
            try:
                pdf.image(tmp_img, x=x0 + 12.0, y=ph_y + 2.0, w=28.0, h=7.5)
            except Exception:
                pass
    pdf.set_xy(x0, ph_y + 10.0)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(half_w - 10.0, 3.8, course_meta["program_head"].upper(), border=0, align="L")
    pdf.set_xy(x0, ph_y + 14.0)
    pdf.set_font("Helvetica", "", 7.2)
    pdf.cell(half_w, 3.8, f"Program Head - {course_meta['program'].title()}", border=0, align="L")
    ph_date = ph_sig.get("date_signed") if ph_sig else "_____________"
    pdf.set_xy(x0, ph_y + 18.0)
    pdf.cell(half_w, 3.8, f"Date: {ph_date}", border=0, align="L")

    # Dean
    dean_sig = sigs_by_role.get("dean")
    dean_y = y_p2
    if dean_sig and dean_sig.get("signature_data"):
        tmp_img = _save_data_url_image(dean_sig["signature_data"])
        if tmp_img:
            sig_temp_files.append(tmp_img)
            try:
                pdf.image(tmp_img, x=x0 + half_w + 12.0, y=dean_y + 2.0, w=28.0, h=7.5)
            except Exception:
                pass
    pdf.set_xy(x0 + half_w, dean_y + 10.0)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(half_w - 10.0, 3.8, course_meta["dean_name"].upper(), border=0, align="L")
    pdf.set_xy(x0 + half_w, dean_y + 14.0)
    pdf.set_font("Helvetica", "", 7.2)
    pdf.cell(half_w, 3.8, "Dean", border=0, align="L")
    dean_date = dean_sig.get("date_signed") if dean_sig else "_____________"
    pdf.set_xy(x0 + half_w, dean_y + 18.0)
    pdf.cell(half_w, 3.8, f"Date: {dean_date}", border=0, align="L")

    # =========================================================================
    # PAGE 3: Annex A Header, Direction, Table Part 1 (CDIO, FIRe, Cultural, SDGs, GAD 1.1)
    # =========================================================================
    pdf.add_page()
    pdf.draw_footer_bar(3)

    y_p3 = 14.0
    pdf.set_xy(x0, y_p3)
    pdf.set_font("Helvetica", "B", 11.0)
    pdf.cell(table_w, 5.0, "Annex A", border=0, align="L")
    y_p3 += 6.5

    pdf.set_xy(x0, y_p3)
    pdf.set_font("Helvetica", "B", 8.8)
    title_annex = (
        "Checklist on Conceive, Design, Implement, Operate (Cdio) Framework, Fourth Industrial Revolution (Fire) "
        "Framework, Cultural And Conflict Sensitivity, Sustainable Development Goals (SDG) \n"
        "and Gender and Development (GAD) Framework"
    )
    pdf.multi_cell(table_w, 4.0, title_annex, border=0, align="C")
    y_p3 = pdf.get_y() + 2.0

    pdf.set_xy(x0, y_p3)
    pdf.set_font("Helvetica", "", 7.5)
    dir_text = "Direction: Tick the appropriate box to indicate the presence or absence of the following indicators in the course syllabus reviewed."
    pdf.cell(table_w, 4.0, dir_text, border=0, align="L")
    y_p3 += 5.5

    # Table Annex A (Part 1 on Page 3)
    col_annex = [84.0, 15.0, 15.0, 80.0]
    pdf.set_xy(x0, y_p3)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(col_annex[0], 6.0, "COMPONENTS", border=1, align="L")
    pdf.cell(col_annex[1], 6.0, "YES", border=1, align="C")
    pdf.cell(col_annex[2], 6.0, "NO", border=1, align="C")
    pdf.cell(col_annex[3], 6.0, "REMARKS", border=1, align="L")
    y_p3 += 6.0

    def render_annex_item(y_cur: float, item_id: str, text: str) -> float:
        pdf.set_font("Helvetica", "", 7.0)
        lines = pdf.multi_cell(col_annex[0] - 2.5, 3.2, text, dry_run=True, output="LINES")
        h = max(6.8, len(lines) * 3.2 + 1.8)
        cx = x0
        for w in col_annex:
            pdf.rect(cx, y_cur, w, h)
            cx += w
        pdf.set_xy(x0 + 1.2, y_cur + 1.0)
        pdf.multi_cell(col_annex[0] - 2.5, 3.2, text, border=0, align="L")

        ans = str(annex_resp.get(item_id) or "YES").upper()
        pdf.draw_checkbox(x0 + col_annex[0] + (col_annex[1] - 3.4) / 2, y_cur + (h - 3.4) / 2, checked=ans in ("YES", "Y", "TRUE", "FULLY"), size=3.4)
        pdf.draw_checkbox(x0 + col_annex[0] + col_annex[1] + (col_annex[2] - 3.4) / 2, y_cur + (h - 3.4) / 2, checked=ans in ("NO", "N", "FALSE", "NOT"), size=3.4)

        rem = _clean_text(annex_rem.get(item_id) or "")
        if rem:
            pdf.set_xy(x0 + col_annex[0] + col_annex[1] + col_annex[2] + 1.2, y_cur + 1.0)
            pdf.multi_cell(col_annex[3] - 2.5, 3.2, rem, border=0, align="L")
        return y_cur + h

    def render_category_row(y_cur: float, title: str) -> float:
        pdf.set_xy(x0, y_cur)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.cell(table_w, 5.0, title, border=1, align="L")
        return y_cur + 5.0

    # CDIO
    y_p3 = render_category_row(y_p3, "Conceive, Design, Implement, Operate (CDIO) Framework Checklist")
    for it in ANNEX_A_SECTIONS[0]["items"]:
        y_p3 = render_annex_item(y_p3, it["id"], _clean_text(it["text"]))

    # FIRe
    y_p3 = render_category_row(y_p3, "Fourth Industrial Revolution (FIRe) Checklist")
    for it in ANNEX_A_SECTIONS[1]["items"]:
        y_p3 = render_annex_item(y_p3, it["id"], _clean_text(it["text"]))

    # Cultural Sensitivity
    y_p3 = render_category_row(y_p3, "Cultural Sensitivity and Conflict Sensitivity Checklist")
    for it in ANNEX_A_SECTIONS[2]["items"]:
        y_p3 = render_annex_item(y_p3, it["id"], _clean_text(it["text"]))

    # SDGs
    y_p3 = render_category_row(y_p3, "Sustainable Development Goals Framework Alignment")
    for it in ANNEX_A_SECTIONS[3]["items"]:
        y_p3 = render_annex_item(y_p3, it["id"], _clean_text(it["text"]))

    # GAD Intro & Domain 1 (1.1) on Page 3
    y_p3 = render_category_row(y_p3, "Gender and Development Framework Checklist")
    pdf.set_xy(x0, y_p3)
    pdf.set_font("Helvetica", "I", 7.0)
    pdf.cell(table_w, 4.2, "Note: At least one indicator must be marked yes to indicate minimum compliance with each domain.", border=1, align="L")
    y_p3 += 4.2

    pdf.set_xy(x0, y_p3)
    pdf.set_font("Helvetica", "B", 7.2)
    pdf.cell(table_w, 4.2, "Domain 1: Intended Learning Outcomes", border=1, align="L")
    y_p3 += 4.2
    d1_intro = _clean_text("The syllabus contains Intended Learning Outcome/s (ILO) that expect students to demonstrate understanding of one or more domains that can be applied within the context of the course.")
    d1_lines = pdf.multi_cell(table_w - 2.5, 3.2, d1_intro, dry_run=True, output="LINES")
    d1_h = max(5.5, len(d1_lines) * 3.2 + 1.5)
    pdf.rect(x0, y_p3, table_w, d1_h)
    pdf.set_xy(x0 + 1.2, y_p3 + 0.8)
    pdf.set_font("Helvetica", "", 7.0)
    pdf.multi_cell(table_w - 2.5, 3.2, d1_intro, border=0, align="L")
    y_p3 += d1_h

    it_1_1 = ANNEX_A_SECTIONS[4]["domains"][0]["items"][0]
    y_p3 = render_annex_item(y_p3, it_1_1["id"], _clean_text(it_1_1["text"]))

    # =========================================================================
    # PAGE 4: Table Part 2 (GAD 1.2 to 4.3, Curriculum Mapping Alignment)
    # =========================================================================
    pdf.add_page()
    pdf.draw_footer_bar(4)

    y_p4 = 14.0

    d1_items = ANNEX_A_SECTIONS[4]["domains"][0]["items"]
    for it in d1_items[1:]:
        y_p4 = render_annex_item(y_p4, it["id"], _clean_text(it["text"]))

    for d in ANNEX_A_SECTIONS[4]["domains"][1:]:
        pdf.set_xy(x0, y_p4)
        pdf.set_font("Helvetica", "B", 7.2)
        pdf.cell(table_w, 4.2, _clean_text(d["domain"]), border=1, align="L")
        y_p4 += 4.2
        desc = _clean_text(d["desc"])
        d_lines = pdf.multi_cell(table_w - 2.5, 3.2, desc, dry_run=True, output="LINES")
        dh = max(5.2, len(d_lines) * 3.2 + 1.5)
        pdf.rect(x0, y_p4, table_w, dh)
        pdf.set_xy(x0 + 1.2, y_p4 + 0.8)
        pdf.set_font("Helvetica", "", 7.0)
        pdf.multi_cell(table_w - 2.5, 3.2, desc, border=0, align="L")
        y_p4 += dh

        for it in d["items"]:
            y_p4 = render_annex_item(y_p4, it["id"], _clean_text(it["text"]))

    y_p4 = render_category_row(y_p4, "Curriculum Mapping Alignment")
    for it in ANNEX_A_SECTIONS[5]["items"]:
        y_p4 = render_annex_item(y_p4, it["id"], _clean_text(it["text"]))

    # =========================================================================
    # PAGE 5: Other Comments & Ruled Lines
    # =========================================================================
    pdf.add_page()
    pdf.draw_footer_bar(5)

    y_p5 = 14.0
    pdf.set_xy(x0, y_p5)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(table_w, 6.0, "Other Comments:", border=0, align="L")
    y_p5 += 8.0

    other_comm = _clean_text(cl.get("other_comments") or "")
    if other_comm:
        pdf.set_xy(x0, y_p5)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.multi_cell(table_w, 4.5, other_comm, border=0, align="L")
        y_p5 = pdf.get_y() + 6.0

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.2)
    for _ in range(5):
        pdf.line(x0, y_p5, x0 + table_w, y_p5)
        y_p5 += 7.5

    # Clean up temp sig files
    for f in sig_temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    return bytes(pdf.output())
