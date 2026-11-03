"""

Generates an official University of Southeastern Philippines (USeP)

OBE Course Syllabus PDF (FM-USeP-MID-01) in 8.5 x 13 in Landscape format,

matching the exact structure, tables, rubrics, colors, and layout of EE 211.pdf.

"""



import os
import re
import base64
import tempfile
from typing import List, Dict, Any, Optional

from fpdf import FPDF

from fpdf.fonts import FontFace

from models import (

    SyllabusBlueprint,

    get_default_prereq_coreq_table,

    get_default_sdg_table,

    get_default_syllabus_assessment_activities,

    get_default_learning_plan_table,

    get_default_references_table,

    get_default_policies_table,

)






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

def _clean_text(val: str, has_ttf: bool = True) -> str:
    """Sanitizes text for PDF rendering, supporting rich typographic characters."""
    if val is None:
        return ""
    s = str(val)
    replacements = {
        "\u2013": "–" if has_ttf else "-",
        "\u2014": "—" if has_ttf else "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "•" if has_ttf else "*",
        "\u25cf": "•" if has_ttf else "*",
        "\u2713": "[X]",
        "\u2714": "[X]",
        "\u2717": "[x]",
        "\u2718": "[x]",
        "\u2192": "->",
        "\u2265": ">=",
        "\u2264": "<=",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    if not has_ttf:
        return s.encode("latin-1", "replace").decode("latin-1")
    return s


class USePSyllabusPDF(FPDF):
    def __init__(self, course_code: str = "EE 211", course_title: str = "ELECTRICAL CIRCUITS 1", college: str = "COLLEGE OF ENGINEERING"):
        # Official USeP Syllabus Folio format: 8.5 x 13 inches (215.9 mm x 330.2 mm) in Landscape
        super().__init__(orientation="L", unit="mm", format=(215.9, 330.2))
        self.course_code = course_code.strip()
        self.course_title = course_title.strip().upper()
        self.college = college.strip().upper()
        self.set_margins(left=12.5, top=12.5, right=12.5)

        # Detect Windows standard TrueType fonts for exact Arial & Arial Narrow match
        win_fonts = "C:/Windows/Fonts"
        self.has_ttf = False
        if os.path.exists(os.path.join(win_fonts, "arial.ttf")) and os.path.exists(os.path.join(win_fonts, "arialbd.ttf")):
            try:
                self.add_font("Arial", "", os.path.join(win_fonts, "arial.ttf"))
                self.add_font("Arial", "B", os.path.join(win_fonts, "arialbd.ttf"))
                if os.path.exists(os.path.join(win_fonts, "ariali.ttf")):
                    self.add_font("Arial", "I", os.path.join(win_fonts, "ariali.ttf"))
                if os.path.exists(os.path.join(win_fonts, "arialbi.ttf")):
                    self.add_font("Arial", "BI", os.path.join(win_fonts, "arialbi.ttf"))
                self.font_main = "Arial"
                self.has_ttf = True
            except Exception:
                self.font_main = "Helvetica"
        else:
            self.font_main = "Helvetica"

        if os.path.exists(os.path.join(win_fonts, "ARIALN.TTF")) and os.path.exists(os.path.join(win_fonts, "ARIALNB.TTF")):
            try:
                self.add_font("ArialNarrow", "", os.path.join(win_fonts, "ARIALN.TTF"))
                self.add_font("ArialNarrow", "B", os.path.join(win_fonts, "ARIALNB.TTF"))
                if os.path.exists(os.path.join(win_fonts, "ARIALNI.TTF")):
                    self.add_font("ArialNarrow", "I", os.path.join(win_fonts, "ARIALNI.TTF"))
                if os.path.exists(os.path.join(win_fonts, "ARIALNBI.TTF")):
                    self.add_font("ArialNarrow", "BI", os.path.join(win_fonts, "ARIALNBI.TTF"))
                self.font_narrow = "ArialNarrow"
            except Exception:
                self.font_narrow = self.font_main
        else:
            self.font_narrow = self.font_main

        if os.path.exists(os.path.join(win_fonts, "times.ttf")) and os.path.exists(os.path.join(win_fonts, "timesbd.ttf")):
            try:
                self.add_font("TimesNewRoman", "", os.path.join(win_fonts, "times.ttf"))
                self.add_font("TimesNewRoman", "B", os.path.join(win_fonts, "timesbd.ttf"))
                self.font_times = "TimesNewRoman"
            except Exception:
                self.font_times = "Times"
        else:
            self.font_times = "Times"

        # Official Cinzel Bold font for University Header
        if os.path.exists(os.path.join(win_fonts, "Cinzel-Bold.otf")):
            try:
                self.add_font("Cinzel", "B", os.path.join(win_fonts, "Cinzel-Bold.otf"))
                self.font_cinzel = "Cinzel"
            except Exception:
                self.font_cinzel = self.font_main
        else:
            self.font_cinzel = self.font_main

    def footer(self):
        # Match FM-USeP-MID-01 Rev 01 footer box at bottom of every page
        self.set_y(-16.5)
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.3)
        self.set_font(self.font_main, "I", 8)
        self.set_text_color(0, 0, 0)

        # Per guide: if harmonized course (GE, PE, NSTP), omit college name
        is_harmonized = any(self.course_code.upper().startswith(h) for h in ["GE ", "PE ", "NSTP ", "CWTS "])
        if is_harmonized:
            left_text = f"  COURSE SYLLABUS IN {self.course_code} - {self.course_title}"
        else:
            left_text = f"  COURSE SYLLABUS IN {self.course_code} - {self.course_title} | {self.college}"

        self.cell(268.2, 6.8, _clean_text(left_text, self.has_ttf), border=1, align="L")
        self.set_font(self.font_main, "", 8)
        self.cell(37.0, 6.8, f"Page {self.page_no()} of {{nb}}", border=1, align="C")


def _draw_page1_header_block(pdf: USePSyllabusPDF, meta):
    """Draws the FM-USeP-MID-01 Rev 01 Document Control Header & Logo matching the official template."""
    x0 = 12.5
    y0 = 12.5
    left_w = 250.2
    ctrl_label_w = 26.0
    ctrl_val_w = 29.0
    row_h = 6.2
    total_h = row_h * 5  # 31.0 mm

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    # Outer left box for University identity
    pdf.rect(x0, y0, left_w, total_h)

    # Embed USeP logo if available
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "static", "logo_1_Image39.jpg")
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=x0 + 4.0, y=y0 + 1.8, w=27.0, h=27.0)
        except Exception:
            pass

    # University text inside left box
    pdf.set_xy(x0 + 33.0, y0 + 2.0)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.cell(left_w - 35.0, 4.2, "Republic of the Philippines", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x0 + 33.0)
    pdf.set_font(pdf.font_cinzel, "B", 13.5)
    pdf.cell(left_w - 35.0, 5.5, _clean_text(meta.university, pdf.has_ttf), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x0 + 33.0)
    pdf.set_font(pdf.font_main, "", 8)
    pdf.cell(left_w - 35.0, 4.0, _clean_text(meta.address, pdf.has_ttf), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x0 + 33.0)
    pdf.cell(left_w - 35.0, 4.0, "Telephone: (082) 227-8192", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x0 + 33.0)
    pdf.cell(left_w - 35.0, 4.0, "Website: www.usep.edu.ph", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x0 + 33.0)
    pdf.cell(left_w - 35.0, 4.0, "Email: president@usep.edu.ph", align="C", new_x="LMARGIN", new_y="NEXT")

    # Right control table (5 rows) - Conforming strictly to FM-USeP-MID-01 Rev 01
    ctrl_rows = [
        ("Form No.", "FM-USeP-MID-01"),
        ("Issue Status", "02"),
        ("Revision No.", "01"),
        ("Date Effective", "24 September 2026"),
        ("Approved by", "President"),
    ]
    cx = x0 + left_w
    for idx, (k, v) in enumerate(ctrl_rows):
        ry = y0 + idx * row_h
        pdf.set_xy(cx, ry)
        pdf.set_font(pdf.font_narrow, "", 7.5)
        pdf.cell(ctrl_label_w, row_h, k, border=1, align="L")
        pdf.set_font(pdf.font_narrow, "B" if idx == 0 else "", 7.5)
        pdf.cell(ctrl_val_w, row_h, v, border=1, align="L")

    # Title Bar right under control header (ALL CAPS bold, centered per guide)
    pdf.set_xy(x0, y0 + total_h)
    pdf.set_font(pdf.font_narrow, "B", 10.5)
    pdf.cell(
        305.2,
        7.0,
        _clean_text(f"COURSE SYLLABUS IN {meta.course_code} - {meta.course_title.upper()}", pdf.has_ttf),
        border=1,
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )





def generate_usep_syllabus_pdf(bp: SyllabusBlueprint, doc: Optional[Dict[str, Any]] = None) -> bytes:
    """Generates the official 8.5x13 Landscape USeP OBE Course Syllabus PDF (FM-USeP-MID-01 Rev 01)."""
    meta = bp.metadata
    pdf = USePSyllabusPDF(course_code=meta.course_code, course_title=meta.course_title, college=meta.college)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=19.0)

    fn_main = pdf.font_main
    fn_narrow = pdf.font_narrow
    has_ttf = pdf.has_ttf

    gray_hdr = FontFace(emphasis="BOLD", fill_color=(204, 204, 204))
    mint_exam = FontFace(emphasis="BOLD", fill_color=(193, 240, 199))

    # ==========================================================================
    # PAGE 1: DOCUMENT HEADER + PART I (UNIVERSITY INFO) & PART II (PROGRAM INFO)
    # ==========================================================================
    pdf.add_page()
    _draw_page1_header_block(pdf, meta)
    pdf.ln(2.0)

    # Part I & Part II Section Titles
    y_start_p1 = pdf.get_y()
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.set_xy(12.5, y_start_p1)
    pdf.cell(195.0, 5.5, "PART I. UNIVERSITY INFORMATION", border=0)
    pdf.set_xy(210.5, y_start_p1)
    pdf.cell(107.2, 5.5, "PART II. PROGRAM INFORMATION", border=0, new_x="LMARGIN", new_y="NEXT")

    y_tables_p1 = y_start_p1 + 6.0

    # Left Table: PART I (VISION, MISSION, GOALS, EDUCATIONAL PHILOSOPHY, IGAs)
    pdf.set_xy(12.5, y_tables_p1)
    pdf.set_font(fn_main, "", 7.2)
    with pdf.table(
        col_widths=(24.0, 73.0, 28.0, 70.0),
        line_height=3.6,
        width=195.0,
        align="L",
    ) as t1:
        r = t1.row()
        r.cell("VISION", style=gray_hdr)
        r.cell("Premier research university transforming communities in the ASEAN and beyond.")
        r.cell("Principles for Teaching and Learning in the University", style=gray_hdr)
        r.cell(
            "In all our educational endeavors, we strive to be continually guided by the following principles:\n"
            "• Teaching and learning is based on science and evidence stemming from experience and reflections on the teaching practice.\n"
            "• A conducive learning environment is founded on integrity and mutual respect, where learning is a co-construction among scholars.\n"
            "• The learner is an active participant in the learning process to develop oneself and others' potential.\n"
            "• A transformative learning experience is grounded in critical and reflective thinking and provides opportunities for practice, improvement, and action."
        )

        r = t1.row()
        r.cell("MISSION", style=gray_hdr)
        r.cell(
            "USeP shall contribute to inclusive growth and sustainable development through continual innovation "
            "in proactive academic programs, impactful research for utilization, economically empowering community "
            "services, and sustainable resource management."
        )
        r.cell("INSTITUTIONAL GRADUATE ATTRIBUTES", style=gray_hdr)
        use_6_igas = getattr(meta, "iga_framework", "new_5_igas") == "program_structure_6_igas"
        if use_6_igas:
            r.cell(
                "IGA1: CRITICAL ANALYSIS - Applies analytical, critical, and problem-solving skills using scientific and engineering methods.\n"
                "IGA2: LEADERSHIP AND TEAMWORK - Functions effectively as a member and leader in multidisciplinary and multicultural teams.\n"
                "IGA3: SERVICE-ORIENTED - Demonstrates social awareness, civic responsibility, and sustainable engineering solutions."
            )
        else:
            r.cell(
                "IGA1: LEADERSHIP SKILLS - Creates and inspires positive changes in the organization; exercises responsibility with integrity and accountability.\n"
                "IGA2: CRITICAL AND ANALYTICAL THINKING SKILLS - Demonstrates creativity, innovativeness, and intellectual curiosity in optimizing available resources.\n"
                "IGA3: SERVICE ORIENTED - Demonstrates concern for others, practices professional ethics, honesty, and socio-cultural/environmental sustainability."
            )

        r = t1.row()
        r.cell("GOALS", style=gray_hdr)
        r.cell(
            "• Internationalized University programs and services.\n"
            "• Innovation and RDE-nurturing environment.\n"
            "• Proactive, globally competitive, and service-oriented graduates.\n"
            "• Transformed vulnerable and disadvantaged groups and communities.\n"
            "• Mobilized and optimized resources for sustainable development."
        )
        if use_6_igas:
            r.cell("IGA4, IGA5 & IGA6", style=gray_hdr)
            r.cell(
                "IGA4: PROFESSIONAL COMPETENCE - Exhibits mastery of core engineering principles, modern tools, design standards, and ethical practice.\n"
                "IGA5: COMMUNICATION - Articulates complete engineering thought and technical information effectively in oral, written, and graphical forms.\n"
                "IGA6: LIFE-LONG LEARNING - Recognizes the need for, and engages in independent, continuous professional learning and development."
            )
        else:
            r.cell("IGA4 & IGA5", style=gray_hdr)
            r.cell(
                "IGA4: LIFELONG LEARNING - Demonstrates enthusiasm and passion for continuous personal and professional development.\n"
                "IGA5: PROFESSIONAL COMPETENCE - Demonstrates proficiency and flexibility in the area of specialization and in conveying information in accordance with global standards."
            )

        r = t1.row()
        r.cell("Nature of Education in the University", style=gray_hdr)
        r.cell(
            "The University of Southeastern Philippines is a state university that contributes to the development of human capital and to fostering innovations to transform communities in Mindanao, the Filipino nation, and the world.",
            colspan=3,
        )

    # Right Table: PART II (PROGRAM NAME & PROGRAM GRADUATE OUTCOMES)
    pdf.set_xy(210.5, y_tables_p1)
    pdf.set_font(fn_main, "", 7.5)
    with pdf.table(col_widths=(26.0, 81.2), width=107.2, line_height=4.2, align="R") as tp_head:
        rh = tp_head.row()
        rh.cell("Program Name", style=gray_hdr)
        if hasattr(meta, "program_names") and meta.program_names and len(meta.program_names) > 1:
            prog_display = "\n".join(f"• {p}" for p in meta.program_names)
        elif hasattr(meta, "programs") and meta.programs and len(meta.programs) > 1:
            prog_display = "\n".join(f"• BS in {p}" for p in meta.programs)
        else:
            prog_display = meta.program_name or "Bachelor of Science in Electrical Engineering"
        rh.cell(_clean_text(prog_display, has_ttf))

        rh2 = tp_head.row()
        rh2.cell("College", style=gray_hdr)
        rh2.cell(_clean_text(meta.college, has_ttf))

        rh3 = tp_head.row()
        rh3.cell("Program Name", style=gray_hdr)
        prog_display = getattr(meta, "program_name", "") or meta.department.replace("Department of ", "Bachelor of Science in ")
        rh3.cell(_clean_text(prog_display, has_ttf))

    pdf.set_xy(210.5, pdf.get_y() + 1.5)
    pdf.set_font(fn_narrow, "B", 8)
    pdf.cell(107.2, 5.0, "PROGRAM GRADUATE OUTCOMES", border=1, align="C", fill=False, new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(210.5, pdf.get_y())
    pdf.set_font(fn_main, "", 7.3)
    with pdf.table(col_widths=(15.0, 38.0, 39.2, 15.0), width=107.2, line_height=3.8, align="R") as tp_pgo:
        hdr = tp_pgo.row(style=gray_hdr)
        hdr.cell("PGO")
        hdr.cell("Description")
        hdr.cell("Performance Indicator")
        hdr.cell("IGA Aligned to")

        seen_pgo = set()
        for co in bp.course_outcomes:
            key = (co.program_outcomes, co.performance_indicator)
            if key in seen_pgo:
                continue
            seen_pgo.add(key)
            r = tp_pgo.row()
            r.cell(_clean_text(co.program_outcomes, has_ttf))
            r.cell(_clean_text(co.graduate_outcome_desc, has_ttf))
            r.cell(_clean_text(co.performance_indicator, has_ttf))
            r.cell(_clean_text(co.iga_aligned, has_ttf))



    # ==========================================================================
    # PAGE 2: PART III (DOCUMENT INFO), PART IV (FACULTY INFO), PART V (COURSE INFO + PREREQ/COREQ TABLE)
    #         & SDG ALIGNMENT TABLE, COURSE DESCRIPTION, WORKLOAD OF STUDENTS
    # ==========================================================================
    pdf.add_page()
    y_p2 = 14.0

    # Left Column (Parts III, IV, V)
    pdf.set_xy(12.5, y_p2)
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(138.0, 5.5, "PART III. DOCUMENT INFORMATION", new_x="LMARGIN", new_y="NEXT")

    sem_part = meta.semester_ay.split(",")[0].strip() if "," in meta.semester_ay else meta.semester_ay
    ay_part = meta.semester_ay.split(",")[-1].replace("A.Y.", "").strip() if "," in meta.semester_ay else "2026-2027"

    # Guide: Version Number format YYYY-X.X (e.g. 2026-1.0)
    v_num = (meta.version_number or "2026-1.0").strip()
    if "-" not in v_num and "–" not in v_num:
        v_num = f"2026-{v_num}"

    v_note = (meta.version_note or "New").strip()
    cycle = 1
    rev_reason = (meta.describe_revision or "").strip()
    if doc and isinstance(doc, dict):
        cycle = doc.get("workflow", {}).get("cycle", 1)
        if not rev_reason:
            rev_reason = (doc.get("workflow", {}).get("revision_reason", "") or "").strip()
    if cycle > 1 and v_note == "New":
        v_note = "Minor Revision"

    vn_str = (
        f"[{'X' if v_note == 'New' else ' '}] New   "
        f"[{'X' if v_note == 'Minor Revision' else ' '}] Minor Revision   "
        f"[{'X' if v_note == 'Major Revision' else ' '}] Major Revision   "
        f"[{'X' if v_note == 'No Revision' else ' '}] No Revision"
    )

    pdf.set_xy(12.5, pdf.get_y() + 0.5)
    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(36.0, 4.0, 98.0), width=138.0, line_height=4.4, align="L") as t_doc:
        for k, v in [
            ("Version Number", _clean_text(v_num, has_ttf)),
            ("Version Note", vn_str),
            ("Describe Revision\n(if applicable)", _clean_text(rev_reason, has_ttf)),
            ("Semester", _clean_text(sem_part, has_ttf)),
            ("Academic Year", _clean_text(ay_part, has_ttf)),
        ]:
            r = t_doc.row()
            r.cell(k, style=FontFace(emphasis="BOLD"))
            r.cell(":")
            r.cell(v)

    pdf.set_xy(12.5, pdf.get_y() + 3.0)
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(138.0, 5.5, "PART IV. FACULTY INFORMATION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(12.5, pdf.get_y() + 0.5)
    pdf.set_font(fn_main, "", 8)
    import courses_store
    doc_authors = courses_store.get_doc_authors(doc) if doc else (meta.authors if hasattr(meta, "authors") and meta.authors else [])
    if doc_authors and len(doc_authors) > 1:
        fac_name_val = "\n".join(f"• {a.get('name', '')} ({a.get('role', 'Faculty Writer')})" for a in doc_authors)
        fac_email_val = "\n".join(f"• {a.get('email', '')}" for a in doc_authors if a.get('email')) or meta.faculty_email
    else:
        fac_name_val = meta.faculty_name
        fac_email_val = meta.faculty_email

    with pdf.table(col_widths=(36.0, 4.0, 98.0), width=138.0, line_height=4.4, align="L") as t_fac:
        for k, v in [
            ("Faculty Name", _clean_text(fac_name_val, has_ttf)),
            ("Email Address", _clean_text(fac_email_val, has_ttf)),
            ("Contact Number", _clean_text(meta.faculty_contact, has_ttf)),
            ("Office", _clean_text(meta.office or meta.college, has_ttf)),
            ("Consultation Hours", _clean_text(meta.consultation_hours, has_ttf)),
        ]:
            r = t_fac.row()
            r.cell(k, style=FontFace(emphasis="BOLD"))
            r.cell(":")
            r.cell(v)

    pdf.set_xy(12.5, pdf.get_y() + 3.0)
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(138.0, 5.5, "PART V. COURSE INFORMATION", new_x="LMARGIN", new_y="NEXT")

    # Format Pre-requisites and Co-requisites from meta.prereq_coreq_table
    req_rows = meta.prereq_coreq_table or get_default_prereq_coreq_table()
    prereq_lines = [
        f"{r.get('course_code', '').strip()} - {r.get('course_title', '').strip()}".strip(" -")
        for r in req_rows
        if "pre" in r.get("req_type", "").lower() and r.get("course_code", "").strip()
    ]
    coreq_lines = [
        f"{r.get('course_code', '').strip()} - {r.get('course_title', '').strip()}".strip(" -")
        for r in req_rows
        if "co" in r.get("req_type", "").lower() and r.get("course_code", "").strip()
    ]
    prereq_str = "\n".join(prereq_lines) if prereq_lines else (meta.prerequisites or "None")
    coreq_str = "\n".join(coreq_lines) if coreq_lines else (meta.corequisites or "None")

    pdf.set_xy(12.5, pdf.get_y() + 0.5)
    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(36.0, 4.0, 98.0), width=138.0, line_height=4.4, align="L") as t_crs:
        for k, v in [
            ("Course Code", _clean_text(meta.course_code, has_ttf)),
            ("Course Title", _clean_text(meta.course_title, has_ttf)),
            ("Pre-requisite", _clean_text(prereq_str, has_ttf)),
            ("Co-requisite", _clean_text(coreq_str, has_ttf)),
            ("Credit", _clean_text(meta.credit_units, has_ttf)),
            ("Level", _clean_text(meta.year_level or "Second Year", has_ttf)),
            ("Section", _clean_text(", ".join(meta.sections) if getattr(meta, "sections", None) else meta.section, has_ttf)),
            ("Class Schedule", _clean_text(f"{meta.schedule} ({meta.room})" if (meta.room and str(meta.room).strip() and str(meta.room).lower() not in str(meta.schedule or "").lower()) else (meta.schedule or "TBA"), has_ttf)),
        ]:
            r = t_crs.row()
            r.cell(k, style=FontFace(emphasis="BOLD"))
            r.cell(":")
            r.cell(v)

    # Right Column on Page 2: SDG Alignment Table, Course Description, Workload of Students
    pdf.set_xy(156.0, y_p2)
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(161.7, 5.5, "SDG Alignment:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(156.0, y_p2 + 6.0)
    pdf.set_font(fn_main, "", 7.8)
    sdg_rows = meta.sdg_table or get_default_sdg_table()
    with pdf.table(col_widths=(42.0, 119.7), width=161.7, line_height=4.1, align="R") as t_sdg:
        hdr = t_sdg.row(style=gray_hdr)
        hdr.cell("SDG")
        hdr.cell("Description of Alignment")
        for s in sdg_rows:
            r = t_sdg.row()
            r.cell(_clean_text(s.get("sdg", ""), has_ttf))
            r.cell(_clean_text(s.get("description", ""), has_ttf))

    pdf.set_xy(156.0, pdf.get_y() + 3.0)
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(161.7, 5.5, "Course Description:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(156.0, pdf.get_y() + 0.5)
    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(161.7,), width=161.7, line_height=4.2, align="R") as t_cdesc:
        r = t_cdesc.row()
        r.cell(_clean_text(meta.course_description, has_ttf))

    pdf.set_xy(156.0, pdf.get_y() + 3.0)
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(161.7, 5.5, "Workload of Students:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(156.0, pdf.get_y() + 0.5)
    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(161.7,), width=161.7, line_height=4.2, align="R") as t_wload:
        r = t_wload.row()
        r.cell(_clean_text(meta.workload_description, has_ttf))

    # ==========================================================================
    # PAGE 3: COURSE LEARNING OUTCOMES (CLOs) & PART VI. ASSESSMENT ACTIVITIES
    # ==========================================================================
    pdf.add_page()
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(0, 5.5, "Course Learning Outcomes (CLOs)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn_main, "", 8.5)
    pdf.cell(0, 5.0, "On the completion of the course, the student is expected to be able to do the following:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(22.0, 155.2, 30.0, 98.0), width=305.2, line_height=4.5) as t_clo:
        hdr = t_clo.row(style=gray_hdr)
        hdr.cell("Code")
        hdr.cell("Course Learning Outcomes")
        hdr.cell("PGO Aligned to")
        hdr.cell("Performance Indicator (PI)")
        for co in bp.course_outcomes:
            r = t_clo.row()
            r.cell(_clean_text(co.co_id, has_ttf))
            r.cell(_clean_text(co.description, has_ttf))
            r.cell(_clean_text(co.program_outcomes, has_ttf))
            r.cell(_clean_text(co.performance_indicator, has_ttf))

    pdf.ln(3.5)
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(0, 5.5, "PART VI. ASSESSMENT ACTIVITIES", new_x="LMARGIN", new_y="NEXT")

    act_rows = meta.syllabus_assessment_activities or get_default_syllabus_assessment_activities()
    fa_acts = [a for a in act_rows if "form" in a.get("type", "").lower() or a.get("code", "").upper().startswith("FA")]
    sa_acts = [a for a in act_rows if a not in fa_acts]

    pdf.set_font(fn_narrow, "B", 8.5)
    pdf.cell(0, 5.0, "Formative Assessments:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(22.0, 48.0, 185.2, 50.0), width=305.2, line_height=4.4) as t_fa:
        hdr = t_fa.row(style=gray_hdr)
        hdr.cell("Code")
        hdr.cell("Assessment Activity")
        hdr.cell("Description and Other Details")
        hdr.cell("CLO Aligned to")
        for a in fa_acts:
            r = t_fa.row()
            r.cell(_clean_text(a.get("code", "FA1"), has_ttf))
            r.cell(_clean_text(a.get("activity", "Group Activity"), has_ttf))
            r.cell(_clean_text(a.get("description", ""), has_ttf))
            r.cell(_clean_text(a.get("clo_aligned", "CLO1, CLO2"), has_ttf))

    pdf.ln(2.5)
    pdf.set_font(fn_narrow, "B", 8.5)
    pdf.cell(0, 5.0, "Summative Assessments:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(22.0, 48.0, 185.2, 50.0), width=305.2, line_height=4.4) as t_sa:
        hdr = t_sa.row(style=gray_hdr)
        hdr.cell("Code")
        hdr.cell("Assessment Activity")
        hdr.cell("Description and Other Details")
        hdr.cell("CLO Aligned to")
        for a in sa_acts:
            r = t_sa.row()
            r.cell(_clean_text(a.get("code", "SA1"), has_ttf))
            r.cell(_clean_text(a.get("activity", "Quizzes"), has_ttf))
            r.cell(_clean_text(a.get("description", ""), has_ttf))
            r.cell(_clean_text(a.get("clo_aligned", "CLO1, CLO2"), has_ttf))



    # ==========================================================================
    # PAGE 4 & 5: PART VII. MEASUREMENT SYSTEM (RUBRICS) & PART VIII. GRADING SYSTEM
    # ==========================================================================
    pdf.add_page()
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(0, 5.5, "PART VII. MEASUREMENT SYSTEM", new_x="LMARGIN", new_y="NEXT")

    rubrics = getattr(bp, "rubrics", []) or []
    if rubrics:
        for r_idx, rub in enumerate(rubrics):
            if r_idx > 0:
                pdf.ln(2.5)
            r_title = rub.get("title") or f"Rubric {r_idx+1}"
            part_str = f" [Graded Portion: {rub['target_part']}]" if rub.get("target_part") else ""
            codes_list = [str(c).strip() for c in (rub.get("assessment_codes") or []) if str(c).strip()]
            if not codes_list and rub.get("assessment_code"):
                codes_list = [c.strip() for c in str(rub.get("assessment_code")).split(",") if c.strip()]
            codes_str = f" [Accommodated Assessments: {', '.join(codes_list)}]" if len(codes_list) > 1 else ""

            pdf.set_font(fn_narrow, "B", 8.5)
            pdf.cell(0, 4.8, _clean_text(f"Assessment Activity: {r_title}{codes_str}{part_str}", has_ttf), new_x="LMARGIN", new_y="NEXT")

            levels = rub.get("levels") or [
                {"level": 5, "label": "5 – Excellent"},
                {"level": 4, "label": "4 – Very Good"},
                {"level": 3, "label": "3 – Good"},
                {"level": 2, "label": "2 – Needs Improvement"},
                {"level": 1, "label": "1 – Poor"},
            ]
            n_levels = max(1, len(levels))
            hdr_cols = ["Areas to Assess"] + [_clean_text(str(lvl.get("label", f"Level {i+1}")), has_ttf) for i, lvl in enumerate(levels)]

            first_col_w = min(52.0, max(36.0, 305.2 * 0.16))
            rem_w = 305.2 - first_col_w
            col_w = rem_w / n_levels
            dyn_widths = (first_col_w,) + tuple(col_w for _ in range(n_levels))

            pdf.set_font(fn_main, "", 6.8 if n_levels >= 6 else (7.2 if n_levels == 5 else 7.5))
            with pdf.table(col_widths=dyn_widths, width=305.2, line_height=3.6) as t_dyn:
                hdr_row = t_dyn.row(style=gray_hdr)
                for h in hdr_cols:
                    hdr_row.cell(h)
                for crit in rub.get("criteria", []):
                    r_row = t_dyn.row()
                    crit_name = crit.get("name", "Criterion")
                    w_pct = crit.get("weight_pct", 0)
                    clo_tag = f" ({crit.get('clo_id')})" if (rub.get("enable_criteria_clos") and crit.get("clo_id")) else ""
                    lbl = f"{crit_name}{clo_tag}" + (f" ({w_pct:.0f}%)" if w_pct else "")
                    r_row.cell(_clean_text(lbl, has_ttf), style=FontFace(emphasis="BOLD"))
                    descs = crit.get("descriptors", [])
                    for c_idx in range(n_levels):
                        d_text = descs[c_idx] if c_idx < len(descs) else ""
                        r_row.cell(_clean_text(str(d_text), has_ttf))
            if rub.get("notes"):
                pdf.set_font(fn_main, "I", 7.0)
                pdf.cell(0, 4.0, _clean_text(f"Note: {rub['notes']}", has_ttf), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font(fn_main, "I", 7.8)
        pdf.cell(0, 5.0, "No measurement rubrics configured for this syllabus. (Faculty can define custom rubrics in Part VII)", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3.0)
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(0, 5.5, "PART VIII. GRADING SYSTEM AND ASSESSMENT PLAN:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn_main, "", 8.5)
    pdf.cell(0, 5.0, "The final grade in this course will be composed of the following items and their weights in the final grade computation:", new_x="LMARGIN", new_y="NEXT")

    # Build distinct SA items with section separators matching syllabus template image
    raw_activities = meta.syllabus_assessment_activities or []
    sa_items = []
    if raw_activities:
        for act in raw_activities:
            a_type = str(act.get("type") or "").strip().lower()
            a_code = str(act.get("code") or "").strip().upper()
            if not a_type.startswith("form") and not a_code.startswith("FA"):
                sa_items.append({
                    "code": a_code,
                    "activity": str(act.get("activity") or ""),
                    "weight_pct": float(act.get("weight_pct") or 0.0),
                    "clo_aligned": str(act.get("clo_aligned") or ""),
                    "lec_lab": str(act.get("lec_lab") or "Lecture"),
                    "is_major_assessment": bool(act.get("is_major_assessment")),
                    "major_scope": str(act.get("major_scope") or "independent"),
                    "clo_methods": act.get("clo_methods") or {}
                })
    
    if not sa_items:
        # Fallback from bp.categories
        for cat in bp.categories:
            if (cat.assessment_type or "SA").upper() == "SA":
                code = cat.assessment_code.upper()
                c_clos = set()
                for it in cat.items:
                    for token in str(it.co_id or "").replace(";", ",").replace("/", ",").split(","):
                        tok = token.split(":")[0].strip().upper()
                        if tok:
                            c_clos.add(tok)
                sa_items.append({
                    "code": code,
                    "activity": cat.name or code,
                    "weight_pct": float(cat.weight_pct or 0.0),
                    "clo_aligned": ", ".join(sorted(c_clos)),
                    "lec_lab": cat.lec_lab or "Lecture",
                    "is_major_assessment": bool(getattr(cat, "is_major_assessment", False))
                })

    if not sa_items:
        sa_items = [
            {"code": "SA1", "activity": "Quizzes", "weight_pct": 40.0, "clo_aligned": "CLO1, CLO4", "lec_lab": "Lecture", "is_major_assessment": False},
            {"code": "SA2", "activity": "Term Examination", "weight_pct": 60.0, "clo_aligned": "CLO1, CLO4", "lec_lab": "Lecture", "is_major_assessment": False}
        ]

    scheme = str(meta.grading_system_type or "two_term").lower()
    lec_wt = float(meta.lecture_weight if meta.lecture_weight is not None else 75.0)
    lab_wt = float(meta.lab_weight if meta.lab_weight is not None else 25.0)
    maj_wt = float(meta.project_weight if meta.project_weight is not None else 20.0)
    mid_wt = float(meta.midterm_weight if meta.midterm_weight is not None else 40.0)
    fin_wt = float(meta.finals_weight if meta.finals_weight is not None else 40.0)

    # Weighted grading model: item % is relative to its section; section share is % of final grade.
    # ALL major assessments (is_major_assessment=True) are retained under OTHER MAJOR ASSESSMENTS / PROJECTS,
    # regardless of whether their scope is both_terms, independent, midterm, or finals.
    def _is_major(it):
        return bool(it.get("is_major_assessment"))

    def _term_scope(it):
        if not it.get("is_major_assessment"):
            return "both_terms"
        s_ = str(it.get("major_scope") or "independent").lower()
        return s_ if s_ in ("both_terms", "midterm", "finals") else "independent"

    major_items = [it for it in sa_items if _is_major(it)]
    term_items = [it for it in sa_items if not _is_major(it)]
    sum_major_wt = sum(float(it.get("weight_pct") or 0.0) for it in major_items)
    term_pool = max(0.0, 100.0 - sum_major_wt)

    # (title, share, mode, items)
    sections = []
    if scheme == "lecture_lab":
        if sum_major_wt > 0 and (lec_wt + lab_wt) > 0:
            eff_lec = term_pool * (lec_wt / (lec_wt + lab_wt))
            eff_lab = term_pool * (lab_wt / (lec_wt + lab_wt))
        else:
            eff_lec = lec_wt
            eff_lab = lab_wt
        sections.append(("LECTURE", eff_lec, "scaled", [it for it in term_items if (it.get("lec_lab") or "Lecture").lower() != "laboratory"]))
        sections.append(("LABORATORY", eff_lab, "scaled", [it for it in term_items if (it.get("lec_lab") or "").lower() == "laboratory"]))
    elif scheme == "lecture_major":
        lw = float(meta.lecture_weight if meta.lecture_weight is not None else 80.0)
        sections.append(("LECTURE", min(lw, term_pool), "scaled", term_items))
    elif scheme == "term_project":
        sections.append(("TERM ASSESSMENTS", term_pool, "scaled", term_items))
    else:
        sections.append(("TERM ASSESSMENTS" if major_items else "SUMMATIVE ASSESSMENTS", term_pool, "scaled", term_items))

    maj_share = sum_major_wt if major_items else (maj_wt if scheme in ("lecture_major", "term_project") else 0.0)
    if major_items or maj_share > 0:
        sections.append(("OTHER MAJOR ASSESSMENTS / PROJECTS", maj_share, "direct", major_items))

    grade_issues = []
    weighted_total = 0.0
    for sec_title, sec_share, sec_mode, sec_items in sections:
        sec_raw_sum = 0.0
        for it in sec_items:
            w = float(it.get("weight_pct") or 0.0)
            sec_raw_sum += w
            if sec_mode == "direct":
                it["_eff"] = w
            else:
                it["_eff"] = w * sec_share / 100.0
            weighted_total += it["_eff"]
        if not sec_items and sec_share > 0:
            grade_issues.append(f"{sec_title.title()} has a {sec_share:g}% share but no items")
        elif sec_items and sec_mode == "scaled" and abs(sec_raw_sum - 100.0) > 0.5:
            grade_issues.append(f"{sec_title.title()} items total {sec_raw_sum:g}% within section (must be 100%)")
    share_sum = sum(sec[1] for sec in sections)
    if abs(share_sum - 100.0) > 0.5:
        grade_issues.append(f"section shares sum to {share_sum:g}% (must be 100%)")
    is_grade_balanced = not grade_issues and abs(weighted_total - 100.0) < 0.5

    n_clos = max(1, len(bp.course_outcomes))
    clo_col_w = 120.0 / n_clos
    col_widths_g = (45.0, 45.0) + tuple(clo_col_w for _ in range(n_clos))

    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=col_widths_g, width=210.0, line_height=4.8, align="L") as t_grd:
        hdr = t_grd.row(style=gray_hdr)
        hdr.cell("Assessment Item", align="L")
        hdr.cell("Percentage of Final Grade", align="C")
        for co in bp.course_outcomes:
            hdr.cell(_clean_text(co.co_id, has_ttf), align="C")

        for sec_title, sec_share, sec_mode, sec_items in sections:
            if not sec_items and not sec_share > 0:
                continue
            # Separator header row spanning all columns
            r_sep = t_grd.row(style=FontFace(emphasis="BOLD", fill_color=(241, 245, 249)))
            r_sep.cell(_clean_text(f"{sec_title} ({sec_share:g}% OF FINAL GRADE)", has_ttf), colspan=2 + n_clos, align="C")

            for item in sec_items:
                code = item["code"]
                wt = item["weight_pct"]
                eff = item.get("_eff", wt)
                r = t_grd.row()
                act_name = str(item.get("activity") or "").strip()
                label = f"{code} ({act_name})" if act_name and act_name.upper() != code.upper() else code
                if item.get("is_major_assessment"):
                    m_sc = str(item.get("major_scope") or "independent").lower()
                    if m_sc == "both_terms":
                        mid_cnt = item.get("items_midterm") or 1
                        fin_cnt = item.get("items_finals") or 1
                        label += f" [Both Terms: Mid {mid_cnt}, Fin {fin_cnt}]"
                    elif m_sc == "midterm":
                        label += f" [Midterm: {item.get('items_midterm') or 1}]"
                    elif m_sc == "finals":
                        label += f" [Finals: {item.get('items_finals') or 1}]"
                    else:
                        label += f" [Standalone: {item.get('items_count') or 1}]"
                r.cell(_clean_text(label, has_ttf), style=FontFace(emphasis="BOLD"), align="L")
                if sec_mode == "scaled" and abs(eff - wt) > 0.05:
                    r.cell(_clean_text(f"{wt:g}% ({eff:.1f}% of final grade)", has_ttf), align="C")
                else:
                    r.cell(f"{wt:g}%", align="C")

                aligned_raw = item.get("clo_aligned") or ""
                aligned_tokens = [tok.strip().upper() for tok in re.split(r"[,;/]+", aligned_raw) if tok.strip()]

                # Determine rubric title
                matching_rubs = [
                    rub for rub in rubrics
                    if code in [str(c).upper().strip() for c in (rub.get("assessment_codes") or [])]
                    or code in [c.upper().strip() for c in str(rub.get("assessment_code") or "").split(",") if c.strip()]
                    or (rub.get("assessment_code") or "").upper().strip() == code
                    or code in (rub.get("title") or "").upper()
                ]
                if matching_rubs:
                    rub_name = matching_rubs[0].get("title", "Measurement Rubric")
                    # Clean rubric prefix like "SA1: "
                    rub_name = re.sub(r"^SA\d+:\s*", "", rub_name)
                elif "lab" in (item.get("activity") or "").lower() or item.get("lec_lab") == "Laboratory":
                    rub_name = "Laboratory Activity Rubric"
                elif "proj" in (item.get("activity") or "").lower() or item.get("is_major_assessment"):
                    rub_name = "Project Evaluation Rubric"
                elif "recit" in (item.get("activity") or "").lower() or "oral" in (item.get("activity") or "").lower():
                    rub_name = "Oral Recitation Rubric"
                else:
                    rub_name = "Problem Solving Rubric"

                clo_methods = item.get("clo_methods") or {}
                for co in bp.course_outcomes:
                    co_key = co.co_id.strip().upper()
                    # Custom CLO assessment method (supports rubrics and non-rubric assessment tools)
                    custom_method = None
                    if co.co_id in clo_methods:
                        custom_method = clo_methods[co.co_id]
                    elif co_key in clo_methods:
                        custom_method = clo_methods[co_key]
                    
                    if custom_method is not None and str(custom_method).strip():
                        r.cell(_clean_text(str(custom_method).strip(), has_ttf), align="C")
                    elif custom_method is not None and not str(custom_method).strip():
                        r.cell("", align="C")
                    else:
                        is_aligned = any(co_key in t or t in co_key for t in aligned_tokens)
                        if is_aligned:
                            r.cell(_clean_text(rub_name, has_ttf), align="C")
                        else:
                            r.cell("", align="C")

        rtot = t_grd.row(style=FontFace(emphasis="BOLD"))
        rtot.cell("TOTAL", align="L")
        rtot.cell(f"{weighted_total:.0f}%" if abs(weighted_total - round(weighted_total)) < 0.05 else f"{weighted_total:.1f}%", align="C")
        status_msg = ("Verified: weighted total (item % x section share) equals 100% of the final grade"
                      if is_grade_balanced else "Warning: " + "; ".join(grade_issues or [f"weighted total is {weighted_total:.1f}%"]))
        rtot.cell(_clean_text(status_msg, has_ttf), colspan=n_clos, align="L")

    pdf.ln(3.0)
    pdf.set_font(fn_main, "", 8)
    pass_cond = (meta.passing_grade_conditions or "").strip()
    if not pass_cond:
        pass_cond = (
            "Students shall submit all assessments, take all examinations, and must have an attendance of not less than 80% "
            "in the class. In case of lacking output or examination, the grade of INC shall be given in accordance with the "
            "existing rules and regulations reflected in the student handbook. In case of incurring absences of more than 20%, "
            "a grade of UW will be reflected in the grade sheet."
        )

    trans_str = f"Base-{meta.transmutation_base} (Default per PM-USeP-MID, Note 1.3)" if meta.transmutation_base == 50 else f"Base-{meta.transmutation_base} (Regulatory / Engineering Board System per PM-USeP-MID)"
    with pdf.table(col_widths=(48.0, 5.0, 252.2), width=305.2, line_height=4.5, align="L") as t_cond:
        for k, v in [
            ("Transmutation", trans_str),
            ("Passing Grade", "3.00"),
            ("Passing Grade Conditions", _clean_text(pass_cond, has_ttf)),
        ]:
            r = t_cond.row()
            r.cell(k, style=FontFace(emphasis="BOLD"))
            r.cell(":")
            r.cell(v)

    pdf.ln(3.0)
    pdf.set_font(fn_narrow, "B", 8.5)
    pdf.cell(0, 5.0, "Grade Equivalence Table:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(42.0, 42.0, 42.0, 42.0, 42.0), width=210.0, line_height=5.0, align="C") as t_eq:
        r1 = t_eq.row()
        for cell_txt in ("< 75 = 5.00", "75-76 = 3.00", "77-79 = 2.75", "80-82 = 2.50", "83-85 = 2.25"):
            r1.cell(cell_txt)
        r2 = t_eq.row()
        for cell_txt in ("86-88 = 2.00", "89-91 = 1.75", "92-94 = 1.50", "95-97 = 1.25", "98-100 = 1.00"):
            r2.cell(cell_txt)

    # ==========================================================================
    # PAGE 6: PART IX. LEARNING PLAN (7-Column Table matching EE 211.pdf)
    # ==========================================================================
    pdf.add_page()
    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(0, 5.5, "PART IX. LEARNING PLAN", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn_main, "", 8.5)
    pdf.cell(0, 5.0, "In order to achieve the outcomes of this course, learners will go through this learning plan:", new_x="LMARGIN", new_y="NEXT")

    lp_rows = meta.learning_plan_table or get_default_learning_plan_table()
    pdf.set_font(fn_main, "", 7.5)

    # Compute rowspan spans for Assessment Activities column to support merged assessments across topics
    spans = [1] * len(lp_rows)
    i = 0
    while i < len(lp_rows):
        k = 1
        while (i + k) < len(lp_rows) and bool(lp_rows[i + k].get("merge_assessment_with_prev")):
            k += 1
        spans[i] = k
        for j in range(1, k):
            spans[i + j] = 0
        i += k

    with pdf.table(
        col_widths=(62.0, 26.0, 22.0, 76.2, 46.0, 35.0, 38.0),
        width=305.2,
        line_height=4.0,
    ) as t_lp:
        hdr = t_lp.row(style=gray_hdr)
        hdr.cell("Intended Learning Outcomes (ILO)")
        hdr.cell("Course Learning Outcome (CLO)")
        hdr.cell("Time Frame")
        hdr.cell("Topics")
        hdr.cell("Teaching-Learning Activities (TLA)")
        hdr.cell("Required Reading")
        hdr.cell("Assessment Activities")

        for idx, row_data in enumerate(lp_rows):
            topic_txt = row_data.get("topics", "")
            is_exam = "EXAMINATION" in topic_txt.upper()
            r = t_lp.row(style=mint_exam if is_exam else None)
            r.cell(_clean_text(row_data.get("ilo", ""), has_ttf))

            clo_val = row_data.get("clo", "")
            if isinstance(clo_val, list):
                clo_val = chr(10).join(str(c) for c in clo_val)
            r.cell(_clean_text(clo_val, has_ttf))

            r.cell(_clean_text(row_data.get("time_frame", ""), has_ttf))
            r.cell(_clean_text(topic_txt, has_ttf))
            r.cell(_clean_text(row_data.get("tla", ""), has_ttf))
            r.cell(_clean_text(row_data.get("required_reading", ""), has_ttf))

            span = spans[idx]
            if span > 1:
                act_val = row_data.get("assessment_activities", "")
                if isinstance(act_val, list):
                    act_val = chr(10).join(str(a) for a in act_val)
                r.cell(_clean_text(act_val, has_ttf), rowspan=span, v_align="MIDDLE")
            elif span == 1:
                act_val = row_data.get("assessment_activities", "")
                if isinstance(act_val, list):
                    act_val = chr(10).join(str(a) for a in act_val)
                r.cell(_clean_text(act_val, has_ttf))
            # if span == 0, omit cell because it is covered by the lead row's rowspan

    # Part IX Term Assessment Weights Audit note
    pdf.ln(1.5)
    pdf.set_font(fn_main, "I", 7.0)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 3.5, _clean_text("Note: Term assessment tasks are monitored in alignment with the Class Record grading scheme (Midterm: 100%, Final Term: 100%).", has_ttf), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    # ==========================================================================
    # PAGE 7 & 8: PART X. REFERENCES/ARTICLES TO READ, PART XI. CLASSROOM POLICIES & SIGNATORIES
    # ==========================================================================
    pdf.ln(4.0)
    if pdf.get_y() > 145.0:
        pdf.add_page()

    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(0, 5.5, "PART X. REFERENCES/ARTICLES TO READ", new_x="LMARGIN", new_y="NEXT")
    ref_rows = meta.references_table or get_default_references_table()
    pdf.set_font(fn_main, "", 8)
    with pdf.table(col_widths=(32.0, 273.2), width=305.2, line_height=4.4) as t_ref:
        hdr = t_ref.row(style=gray_hdr)
        hdr.cell("Code")
        hdr.cell("Reference/Article")
        for ref in ref_rows:
            r = t_ref.row()
            r.cell(_clean_text(ref.get("code", ""), has_ttf))
            r.cell(_clean_text(ref.get("reference", ""), has_ttf))

    pdf.ln(3.5)
    if pdf.get_y() > 155.0:
        pdf.add_page()

    pdf.set_font(fn_narrow, "B", 9.5)
    pdf.cell(0, 5.5, "PART XI. CLASSROOM POLICIES", new_x="LMARGIN", new_y="NEXT")
    pol_rows = meta.policies_table or get_default_policies_table()
    pdf.set_font(fn_main, "", 7.8)
    for idx, pol in enumerate(pol_rows, start=1):
        num = pol.get("number", str(idx)).strip()
        title = pol.get("title", "").strip()
        desc = pol.get("description", "").strip()
        pdf.set_font(fn_main, "B", 7.8)
        line_prefix = f"{num}. {title}. " if title else f"{num}. "
        pdf.multi_cell(305.2, 4.0, _clean_text(line_prefix + desc, has_ttf), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)

    # SIGNATORIES BLOCK (Conforming to USeP Standards & Item 16 Signatory Layout)
    # Only Faculty, Program Head/Associate Dean, and Dean are in the footer,
    # with College QA signature placed alongside the Dean as a small countersignature at the bottom right.
    if pdf.get_y() > 140.0:
        pdf.add_page()
    pdf.ln(4.0)

    # Collect workflow signatures if passed in workflow or doc
    wf_sigs = {}
    if doc and isinstance(doc, dict):
        for s in (doc.get("workflow", {}).get("signatures", [])):
            wf_sigs[s.get("role")] = s

    import auth
    users = auth._load_users()

    # Determine if course owner is a Program Head -> Recommending Approval goes to Associate Dean
    owner = doc.get("owner") if (doc and isinstance(doc, dict)) else ""
    is_owner_ph = False
    if owner:
        owner_roles = users.get(owner, {}).get("workflow_roles") or []
        is_owner_ph = ("program_head" in owner_roles)
    if doc and isinstance(doc, dict):
        rev_req = doc.get("workflow", {}).get("revision_request") or {}
        if rev_req.get("owner_is_program_head"):
            is_owner_ph = True

    # 1. Faculty Information & E-Signature
    import courses_store
    doc_authors = courses_store.get_doc_authors(doc) if doc else (meta.authors if hasattr(meta, "authors") and meta.authors else [])
    if doc_authors and len(doc_authors) > 1:
        prepared_by_names = ", ".join(a.get("name", "") for a in doc_authors)
        prepared_by_title = "Faculty Writers"
    else:
        prepared_by_names = meta.faculty_name
        prepared_by_title = "Faculty in Charge"

    fac_sig_data = ""
    fac_time = ""
    if owner and owner in users:
        fac_sig_data = users[owner].get("signature_data") or ""
    if not fac_sig_data and doc and isinstance(doc, dict):
        author_subs = doc.get("workflow", {}).get("author_submissions") or {}
        if owner in author_subs:
            fac_time = f"Signed: {author_subs[owner].get('submitted_at', '')[:16].replace('T', ' ')}"
        elif doc.get("workflow", {}).get("submitted_at"):
            fac_time = f"Signed: {doc['workflow']['submitted_at'][:16].replace('T', ' ')}"
    tmp_fac_sig = _save_data_url_image(fac_sig_data) if fac_sig_data else None

    # 2. Recommending Approval (Program Head or Associate Dean)
    if is_owner_ph:
        # Recommending Approval: Associate Dean
        assoc_sig = wf_sigs.get("associate_dean")
        ph_display_name = assoc_sig.get("full_name") if assoc_sig else "Delan Zoe H. Arenga"
        ph_display_title = assoc_sig.get("title") if assoc_sig else "Associate Dean, College of Engineering"
        ph_time = f"Signed: {assoc_sig.get('signed_at')[:16].replace('T', ' ')}" if assoc_sig else ""
        ph_sig_data = assoc_sig.get("signature_data") if assoc_sig else (users.get("faculty_arenga", {}).get("signature_data") or "")
    else:
        # Recommending Approval: Program Head(s)
        prog_clean = (meta.department or "").replace("Department of ", "").replace("Bachelor of Science in ", "").strip()
        ph_sig = wf_sigs.get("program_head")
        ph_display_name = ph_sig.get("full_name") if ph_sig else (meta.program_head or "Charito O. Claro")
        num_heads = len(getattr(meta, "program_heads", [])) if hasattr(meta, "program_heads") and meta.program_heads else (len(ph_display_name.split("/")) if "/" in ph_display_name else 1)
        if num_heads > 1:
            ph_display_title = ph_sig.get("title") if ph_sig else "Program Heads"
        else:
            ph_display_title = ph_sig.get("title") if ph_sig else f"Program Head - {prog_clean}"
        ph_time = f"Signed: {ph_sig.get('signed_at')[:16].replace('T', ' ')}" if ph_sig else ""
        ph_sig_data = ph_sig.get("signature_data") if ph_sig else (users.get("faculty_claro", {}).get("signature_data") or "")
    tmp_ph_sig = _save_data_url_image(ph_sig_data) if ph_sig_data else None

    # 3. Approved by (Dean)
    dean_sig = wf_sigs.get("dean")
    dean_name = dean_sig.get("full_name") if dean_sig else (meta.dean_name or "Joie D. Cataytay")
    dean_title = dean_sig.get("title") if dean_sig else "Dean, College of Engineering"
    dean_time = f"Approved & Locked: {dean_sig.get('signed_at')[:16].replace('T', ' ')}" if dean_sig else ""
    dean_sig_data = dean_sig.get("signature_data") if dean_sig else (users.get("dean_cataytay", {}).get("signature_data") or "")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dean_static_png = os.path.join(base_dir, "static", "signatures", "dean_cataytay.png")
    if not dean_sig_data and os.path.exists(dean_static_png):
        dean_sig_data = dean_static_png
    tmp_dean_sig = _save_data_url_image(dean_sig_data) if dean_sig_data else None

    # 4. Countersigned by (College QA Head) - alongside Dean at bottom right
    qa_sig = wf_sigs.get("qa_head")
    qa_name = qa_sig.get("full_name") if qa_sig else "Sheena S. Arcega"
    qa_title = qa_sig.get("title") if qa_sig else "College Quality Assurance Head"
    qa_time = f"Countersigned: {qa_sig.get('signed_at')[:16].replace('T', ' ')}" if qa_sig else ""
    qa_sig_data = qa_sig.get("signature_data") if qa_sig else (users.get("qa_arcega", {}).get("signature_data") or "")
    qa_static_png = os.path.join(base_dir, "static", "signatures", "sheena_arcega.png")
    if not qa_sig_data and os.path.exists(qa_static_png):
        qa_sig_data = qa_static_png
    tmp_qa_sig = _save_data_url_image(qa_sig_data) if qa_sig_data else None

    # Render ROW 1: Prepared by (Faculty) | Recommending Approval (Program Head / Associate Dean)
    y_row1 = pdf.get_y()
    col1_w = 152.6
    col2_w = 152.6

    pdf.set_font(fn_main, "", 8.0)
    pdf.set_xy(12.5, y_row1)
    pdf.cell(col1_w, 4.5, "Prepared by:", border=0)
    pdf.set_xy(12.5 + col1_w, y_row1)
    pdf.cell(col2_w, 4.5, "Recommending Approval:", border=0)

    # Signature Images in Row 1
    sig_img_h = 11.0
    if tmp_fac_sig:
        try:
            pdf.image(tmp_fac_sig, x=12.5 + 8.0, y=y_row1 + 4.5, w=34.0, h=sig_img_h)
        except Exception:
            pass
    if tmp_ph_sig:
        try:
            pdf.image(tmp_ph_sig, x=12.5 + col1_w + 8.0, y=y_row1 + 4.5, w=34.0, h=sig_img_h)
        except Exception:
            pass

    y_names1 = y_row1 + 16.0
    pdf.set_xy(12.5, y_names1)
    pdf.set_font(fn_narrow, "B", 8.8)
    pdf.cell(col1_w, 4.0, _clean_text(prepared_by_names.upper(), has_ttf), border=0)
    pdf.set_xy(12.5 + col1_w, y_names1)
    if len(ph_display_name) > 32:
        pdf.set_font(fn_narrow, "B", 7.2)
    else:
        pdf.set_font(fn_narrow, "B", 8.8)
    pdf.cell(col2_w, 4.0, _clean_text(ph_display_name.upper(), has_ttf), border=0)

    pdf.set_xy(12.5, y_names1 + 4.0)
    pdf.set_font(fn_main, "", 7.8)
    pdf.cell(col1_w, 3.8, prepared_by_title, border=0)
    pdf.set_xy(12.5 + col1_w, y_names1 + 4.0)
    pdf.cell(col2_w, 3.8, _clean_text(ph_display_title, has_ttf), border=0)

    pdf.set_xy(12.5, y_names1 + 7.8)
    pdf.set_font(fn_main, "I", 7.0)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(col1_w, 3.4, _clean_text(fac_time, has_ttf), border=0)
    pdf.set_xy(12.5 + col1_w, y_names1 + 7.8)
    pdf.cell(col2_w, 3.4, _clean_text(ph_time, has_ttf), border=0)
    pdf.set_text_color(0, 0, 0)

    # Render ROW 2: Approved by (Dean) | alongside Dean, small QA signature on bottom right
    y_row2 = y_names1 + 15.0
    dean_w = 175.0
    qa_w = 130.2

    pdf.set_font(fn_main, "", 8.0)
    pdf.set_xy(12.5, y_row2)
    pdf.cell(dean_w, 4.5, "Approved by:", border=0)

    # Small QA countersignature label alongside Dean
    pdf.set_xy(12.5 + dean_w, y_row2 + 1.0)
    pdf.set_font(fn_main, "I", 7.2)
    pdf.cell(qa_w, 3.8, "Countersigned by (Quality Assurance):", border=0)

    # Signature Images in Row 2
    if tmp_dean_sig:
        try:
            pdf.image(tmp_dean_sig, x=12.5 + 8.0, y=y_row2 + 4.5, w=38.0, h=12.0)
        except Exception:
            pass
    if tmp_qa_sig:
        try:
            pdf.image(tmp_qa_sig, x=12.5 + dean_w + 6.0, y=y_row2 + 4.5, w=24.0, h=8.5)
        except Exception:
            pass

    y_names2 = y_row2 + 16.5
    pdf.set_xy(12.5, y_names2)
    pdf.set_font(fn_narrow, "B", 9.0)
    pdf.cell(dean_w, 4.0, _clean_text(dean_name.upper(), has_ttf), border=0)

    # Small QA name
    pdf.set_xy(12.5 + dean_w, y_names2)
    pdf.set_font(fn_narrow, "B", 7.8)
    pdf.cell(qa_w, 3.6, _clean_text(qa_name.upper(), has_ttf), border=0)

    pdf.set_xy(12.5, y_names2 + 4.0)
    pdf.set_font(fn_main, "", 7.8)
    pdf.cell(dean_w, 3.8, _clean_text(dean_title, has_ttf), border=0)

    pdf.set_xy(12.5 + dean_w, y_names2 + 3.6)
    pdf.set_font(fn_main, "", 7.0)
    pdf.cell(qa_w, 3.4, _clean_text(qa_title, has_ttf), border=0)

    pdf.set_xy(12.5, y_names2 + 7.8)
    pdf.set_font(fn_main, "I", 7.0)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(dean_w, 3.4, _clean_text(dean_time, has_ttf), border=0)

    pdf.set_xy(12.5 + dean_w, y_names2 + 7.0)
    pdf.set_font(fn_main, "I", 6.5)
    pdf.cell(qa_w, 3.0, _clean_text(qa_time, has_ttf), border=0)
    pdf.set_text_color(0, 0, 0)

    return bytes(pdf.output())
