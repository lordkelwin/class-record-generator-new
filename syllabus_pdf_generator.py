"""

Generates an official University of Southeastern Philippines (USeP)

OBE Course Syllabus PDF (FM-USeP-MID-01) in 8.5 x 13 in Landscape format,

matching the exact structure, tables, rubrics, colors, and layout of EE 211.pdf.

"""



import os

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





def _clean_text(val: str) -> str:

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

        "\u2265": ">=",

        "\u2264": "<=",

    }

    for k, v in replacements.items():

        s = s.replace(k, v)

    return s.encode("latin-1", "replace").decode("latin-1")





class USePSyllabusPDF(FPDF):

    def __init__(self, course_code: str = "EE 211", course_title: str = "ELECTRICAL CIRCUITS 1", college: str = "COLLEGE OF ENGINEERING"):

        # 8.5 x 13 inches (215.9 mm x 330.2 mm) in Landscape -> width=330.2mm, height=215.9mm

        super().__init__(orientation="L", unit="mm", format=(215.9, 330.2))

        self.course_code = _clean_text(course_code)

        self.course_title = _clean_text(course_title.upper())

        self.college = _clean_text(college.upper())

        self.set_margins(left=12.5, top=12.5, right=12.5)



    def footer(self):

        # Match EE 211.pdf footer box at bottom of every page

        self.set_y(-16.5)

        self.set_draw_color(0, 0, 0)

        self.set_line_width(0.3)

        self.set_font("Helvetica", "I", 8)

        self.set_text_color(0, 0, 0)

        left_text = f"  COURSE SYLLABUS IN {self.course_code} - {self.course_title} | {self.college}"

        self.cell(268.2, 6.8, _clean_text(left_text), border=1, align="L")

        self.set_font("Helvetica", "", 8)

        self.cell(37.0, 6.8, f"Page {self.page_no()} of {{nb}}", border=1, align="C")





def _draw_page1_header_block(pdf: USePSyllabusPDF, meta):

    """Draws the FM-USeP-MID-01 Document Control Header & Logo matching Page 1 of EE 211.pdf."""

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

    pdf.set_font("Helvetica", "", 8.5)

    pdf.cell(left_w - 35.0, 4.2, "Republic of the Philippines", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 33.0)

    pdf.set_font("Times", "B", 13.5)

    pdf.cell(left_w - 35.0, 5.5, _clean_text(meta.university), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 33.0)

    pdf.set_font("Helvetica", "", 8)

    pdf.cell(left_w - 35.0, 4.0, _clean_text(meta.address), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 33.0)

    pdf.cell(left_w - 35.0, 4.0, "Telephone: (082) 227-8192", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 33.0)

    pdf.cell(left_w - 35.0, 4.0, "Website: www.usep.edu.ph", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 33.0)

    pdf.cell(left_w - 35.0, 4.0, "Email: president@usep.edu.ph", align="C", new_x="LMARGIN", new_y="NEXT")



    # Right control table (5 rows)

    ctrl_rows = [

        ("Form No.", "FM-USeP-MID-01"),

        ("Issue Status", "01"),

        ("Revision No.", "00"),

        ("Date Effective", "05 January 2026"),

        ("Approved by", "President"),

    ]

    cx = x0 + left_w

    for idx, (k, v) in enumerate(ctrl_rows):

        ry = y0 + idx * row_h

        pdf.set_xy(cx, ry)

        pdf.set_font("Helvetica", "", 7.5)

        pdf.cell(ctrl_label_w, row_h, k, border=1, align="L")

        pdf.set_font("Helvetica", "B" if idx == 0 else "", 7.5)

        pdf.cell(ctrl_val_w, row_h, v, border=1, align="L")



    # Title Bar right under control header

    pdf.set_xy(x0, y0 + total_h)

    pdf.set_font("Helvetica", "B", 10.5)

    pdf.cell(

        305.2,

        7.0,

        _clean_text(f"COURSE SYLLABUS IN {meta.course_code} - {meta.course_title.upper()}"),

        border=1,

        align="C",

        new_x="LMARGIN",

        new_y="NEXT",

    )





def generate_usep_syllabus_pdf(bp: SyllabusBlueprint, doc: Optional[Dict[str, Any]] = None) -> bytes:

    """Generates the complete 8.5x13 Landscape USeP OBE Course Syllabus PDF matching EE 211.pdf."""

    meta = bp.metadata

    pdf = USePSyllabusPDF(course_code=meta.course_code, course_title=meta.course_title, college=meta.college)

    pdf.alias_nb_pages()

    pdf.set_auto_page_break(auto=True, margin=19.0)



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

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.set_xy(12.5, y_start_p1)

    pdf.cell(195.0, 5.5, "PART I. UNIVERSITY INFORMATION", border=0)

    pdf.set_xy(210.5, y_start_p1)

    pdf.cell(107.2, 5.5, "PART II. PROGRAM INFORMATION", border=0, new_x="LMARGIN", new_y="NEXT")



    y_tables_p1 = y_start_p1 + 6.0



    # Left Table: PART I (VISION, MISSION, GOALS, EDUCATIONAL PHILOSOPHY, IGAs)

    pdf.set_xy(12.5, y_tables_p1)

    pdf.set_font("Helvetica", "", 7.2)

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

            "* Teaching and learning is based on science and evidence stemming from experience and reflections on the teaching practice.\n"

            "* A conducive learning environment is founded on integrity and mutual respect, where learning is a co-construction among scholars.\n"

            "* The learner is an active participant in the learning process to develop oneself and others' potential.\n"

            "* A transformative learning experience is grounded in critical and reflective thinking and provides opportunities for practice, improvement, and action."

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

            "* Internationalized University programs and services.\n"

            "* Innovation and RDE-nurturing environment.\n"

            "* Proactive, globally competitive, and service-oriented graduates.\n"

            "* Transformed vulnerable and disadvantaged groups and communities.\n"

            "* Mobilized and optimized resources for sustainable development."

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

    pdf.set_font("Helvetica", "", 7.5)

    with pdf.table(col_widths=(26.0, 81.2), width=107.2, line_height=4.2, align="R") as tp_head:

        rh = tp_head.row()

        rh.cell("Program Name", style=gray_hdr)

        if hasattr(meta, "program_names") and meta.program_names and len(meta.program_names) > 1:
            prog_display = "\n".join(f"• {p}" for p in meta.program_names)
        elif hasattr(meta, "programs") and meta.programs and len(meta.programs) > 1:
            prog_display = "\n".join(f"• BS in {p}" for p in meta.programs)
        else:
            prog_display = meta.program_name or "Bachelor of Science in Electrical Engineering"
        rh.cell(_clean_text(prog_display))

        rh2 = tp_head.row()

        rh2.cell("College", style=gray_hdr)

        rh2.cell(_clean_text(meta.college))

        rh3 = tp_head.row()

        rh3.cell("Department", style=gray_hdr)

        rh3.cell(_clean_text(meta.department))



    pdf.set_xy(210.5, pdf.get_y() + 1.5)

    pdf.set_font("Helvetica", "B", 8)

    pdf.cell(107.2, 5.0, "PROGRAM GRADUATE OUTCOMES", border=1, align="C", fill=False, new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(210.5, pdf.get_y())

    pdf.set_font("Helvetica", "", 7.3)

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

            r.cell(_clean_text(co.program_outcomes))

            r.cell(_clean_text(co.graduate_outcome_desc))

            r.cell(_clean_text(co.performance_indicator))

            r.cell(_clean_text(co.iga_aligned))



    # ==========================================================================

    # PAGE 2: PART III (DOCUMENT INFO), PART IV (FACULTY INFO), PART V (COURSE INFO + PREREQ/COREQ TABLE)

    #         & SDG ALIGNMENT TABLE, COURSE DESCRIPTION, WORKLOAD OF STUDENTS

    # ==========================================================================

    pdf.add_page()

    y_p2 = 14.0



    # Left Column (Parts III, IV, V)

    pdf.set_xy(12.5, y_p2)

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(138.0, 5.5, "PART III. DOCUMENT INFORMATION", new_x="LMARGIN", new_y="NEXT")



    sem_part = meta.semester_ay.split(",")[0].strip() if "," in meta.semester_ay else meta.semester_ay

    ay_part = meta.semester_ay.split(",")[-1].replace("A.Y.", "").strip() if "," in meta.semester_ay else "2026-2027"

    v_note = (meta.version_note or "New").strip()

    vn_str = (

        f"[{'x' if v_note == 'New' else ' '}] New   "

        f"[{'x' if v_note == 'Minor Revision' else ' '}] Minor Revision   "

        f"[{'x' if v_note == 'Major Revision' else ' '}] Major Revision   "

        f"[{'x' if v_note == 'No Revision' else ' '}] No Revision"

    )



    pdf.set_xy(12.5, pdf.get_y() + 0.5)

    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(36.0, 4.0, 98.0), width=138.0, line_height=4.4, align="L") as t_doc:

        for k, v in [

            ("Version Number", _clean_text(meta.version_number or "2026-1.0")),

            ("Version Note", vn_str),

            ("Describe Revision\n(if applicable)", _clean_text(meta.describe_revision or "")),

            ("Semester", _clean_text(sem_part)),

            ("Academic Year", _clean_text(ay_part)),

        ]:

            r = t_doc.row()

            r.cell(k, style=FontFace(emphasis="BOLD"))

            r.cell(":")

            r.cell(v)



    pdf.set_xy(12.5, pdf.get_y() + 3.0)

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(138.0, 5.5, "PART IV. FACULTY INFORMATION", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(12.5, pdf.get_y() + 0.5)

    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(36.0, 4.0, 98.0), width=138.0, line_height=4.4, align="L") as t_fac:

        for k, v in [

            ("Faculty Name", _clean_text(meta.faculty_name)),

            ("Email Address", _clean_text(meta.faculty_email)),

            ("Contact Number", _clean_text(meta.faculty_contact)),

            ("Office", _clean_text(meta.office or meta.college)),

            ("Consultation Hours", _clean_text(meta.consultation_hours)),

        ]:

            r = t_fac.row()

            r.cell(k, style=FontFace(emphasis="BOLD"))

            r.cell(":")

            r.cell(v)



    pdf.set_xy(12.5, pdf.get_y() + 3.0)

    pdf.set_font("Helvetica", "B", 9.5)

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

    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(36.0, 4.0, 98.0), width=138.0, line_height=4.4, align="L") as t_crs:

        for k, v in [

            ("Course Code", _clean_text(meta.course_code)),

            ("Course Title", _clean_text(meta.course_title)),

            ("Pre-requisite", _clean_text(prereq_str)),

            ("Co-requisite", _clean_text(coreq_str)),

            ("Credit", _clean_text(meta.credit_units)),

            ("Level", _clean_text(meta.year_level or "Second Year")),

            ("Section", _clean_text(", ".join(meta.sections) if getattr(meta, "sections", None) else meta.section)),

            ("Class Schedule", _clean_text(f"{meta.schedule} ({meta.room})")),

        ]:

            r = t_crs.row()

            r.cell(k, style=FontFace(emphasis="BOLD"))

            r.cell(":")

            r.cell(v)



    # Right Column on Page 2: SDG Alignment Table, Course Description, Workload of Students

    pdf.set_xy(156.0, y_p2)

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(161.7, 5.5, "SDG Alignment:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(156.0, y_p2 + 6.0)

    pdf.set_font("Helvetica", "", 7.8)

    sdg_rows = meta.sdg_table or get_default_sdg_table()

    with pdf.table(col_widths=(42.0, 119.7), width=161.7, line_height=4.1, align="R") as t_sdg:

        hdr = t_sdg.row(style=gray_hdr)

        hdr.cell("SDG")

        hdr.cell("Description of Alignment")

        for s in sdg_rows:

            r = t_sdg.row()

            r.cell(_clean_text(s.get("sdg", "")))

            r.cell(_clean_text(s.get("description", "")))



    pdf.set_xy(156.0, pdf.get_y() + 3.0)

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(161.7, 5.5, "Course Description:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(156.0, pdf.get_y() + 0.5)

    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(161.7,), width=161.7, line_height=4.2, align="R") as t_cdesc:

        r = t_cdesc.row()

        r.cell(_clean_text(meta.course_description))



    pdf.set_xy(156.0, pdf.get_y() + 3.0)

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(161.7, 5.5, "Workload of Students:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(156.0, pdf.get_y() + 0.5)

    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(161.7,), width=161.7, line_height=4.2, align="R") as t_wload:

        r = t_wload.row()

        r.cell(_clean_text(meta.workload_description))



    # ==========================================================================

    # PAGE 3: COURSE LEARNING OUTCOMES (CLOs) & PART VI. ASSESSMENT ACTIVITIES

    # ==========================================================================

    pdf.add_page()

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(0, 5.5, "Course Learning Outcomes (CLOs)", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8.5)

    pdf.cell(0, 5.0, "On the completion of the course, the student is expected to be able to do the following:", new_x="LMARGIN", new_y="NEXT")



    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(22.0, 155.2, 30.0, 98.0), width=305.2, line_height=4.5) as t_clo:

        hdr = t_clo.row(style=gray_hdr)

        hdr.cell("Code")

        hdr.cell("Course Learning Outcomes")

        hdr.cell("PGO Aligned to")

        hdr.cell("Performance Indicator (PI)")

        for co in bp.course_outcomes:

            r = t_clo.row()

            r.cell(_clean_text(co.co_id))

            r.cell(_clean_text(co.description))

            r.cell(_clean_text(co.program_outcomes))

            r.cell(_clean_text(co.performance_indicator))



    pdf.ln(3.5)

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(0, 5.5, "PART VI. ASSESSMENT ACTIVITIES", new_x="LMARGIN", new_y="NEXT")



    act_rows = meta.syllabus_assessment_activities or get_default_syllabus_assessment_activities()

    fa_acts = [a for a in act_rows if "form" in a.get("type", "").lower() or a.get("code", "").upper().startswith("FA")]

    sa_acts = [a for a in act_rows if a not in fa_acts]



    pdf.set_font("Helvetica", "B", 8.5)

    pdf.cell(0, 5.0, "Formative Assessments:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(22.0, 48.0, 185.2, 50.0), width=305.2, line_height=4.4) as t_fa:

        hdr = t_fa.row(style=gray_hdr)

        hdr.cell("Code")

        hdr.cell("Assessment Activity")

        hdr.cell("Description and Other Details")

        hdr.cell("CLO Aligned to")

        for a in fa_acts:

            r = t_fa.row()

            r.cell(_clean_text(a.get("code", "FA1")))

            r.cell(_clean_text(a.get("activity", "Group Activity")))

            r.cell(_clean_text(a.get("description", "")))

            r.cell(_clean_text(a.get("clo_aligned", "CLO1, CLO2")))



    pdf.ln(2.5)

    pdf.set_font("Helvetica", "B", 8.5)

    pdf.cell(0, 5.0, "Summative Assessments:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(22.0, 48.0, 185.2, 50.0), width=305.2, line_height=4.4) as t_sa:

        hdr = t_sa.row(style=gray_hdr)

        hdr.cell("Code")

        hdr.cell("Assessment Activity")

        hdr.cell("Description and Other Details")

        hdr.cell("CLO Aligned to")

        for a in sa_acts:

            r = t_sa.row()

            r.cell(_clean_text(a.get("code", "SA1")))

            r.cell(_clean_text(a.get("activity", "Quizzes")))

            r.cell(_clean_text(a.get("description", "")))

            r.cell(_clean_text(a.get("clo_aligned", "CLO1, CLO2")))



    # ==========================================================================

    # PAGE 4 & 5: PART VII. MEASUREMENT SYSTEM (RUBRICS) & PART VIII. GRADING SYSTEM

    # ==========================================================================

    pdf.add_page()

    pdf.set_font("Helvetica", "B", 9.5)

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

            pdf.set_font("Helvetica", "B", 8.5)

            pdf.cell(0, 4.8, _clean_text(f"Assessment Activity: {r_title}{codes_str}{part_str}"), new_x="LMARGIN", new_y="NEXT")



            levels = rub.get("levels") or [

                {"level": 5, "label": "Excellent (5)"},

                {"level": 4, "label": "Very Good (4)"},

                {"level": 3, "label": "Satisfactory (3)"},

                {"level": 2, "label": "Needs Improvement (2)"},

                {"level": 1, "label": "Unsatisfactory (1)"},

                {"level": 0, "label": "Unacceptable (0)"},

            ]

            n_levels = max(1, len(levels))

            hdr_cols = ["Area to Assess"] + [_clean_text(str(lvl.get("label", f"Level {i+1}"))) for i, lvl in enumerate(levels)]



            first_col_w = min(52.0, max(36.0, 305.2 * 0.16))

            rem_w = 305.2 - first_col_w

            col_w = rem_w / n_levels

            dyn_widths = (first_col_w,) + tuple(col_w for _ in range(n_levels))



            pdf.set_font("Helvetica", "", 6.8 if n_levels >= 6 else (7.2 if n_levels == 5 else 7.5))

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

                    r_row.cell(_clean_text(lbl), style=FontFace(emphasis="BOLD"))

                    descs = crit.get("descriptors", [])

                    for c_idx in range(n_levels):

                        d_text = descs[c_idx] if c_idx < len(descs) else ""

                        r_row.cell(_clean_text(str(d_text)))

            if rub.get("notes"):

                pdf.set_font("Helvetica", "I", 7.0)

                pdf.cell(0, 4.0, _clean_text(f"Note: {rub['notes']}"), new_x="LMARGIN", new_y="NEXT")

    else:
        pdf.set_font("Helvetica", "I", 7.8)
        pdf.cell(0, 5.0, "No measurement rubrics configured for this syllabus. (Faculty can define custom rubrics in Part VII)", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3.0)

    pdf.cell(0, 5.5, "PART VIII. GRADING SYSTEM AND ASSESSMENT PLAN:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8.5)

    pdf.cell(0, 5.0, "The final grade in this course will be composed of the following items and their weights in the final grade computation:", new_x="LMARGIN", new_y="NEXT")



    # Build distinct SA codes, weights, and aligned CLOs from bp.categories

    sa_summary: Dict[str, float] = {}

    sa_clos_map: Dict[str, set] = {}

    for cat in bp.categories:

        if (cat.assessment_type or "SA").upper() == "SA":

            code = cat.assessment_code.upper()

            if code not in sa_summary:

                sa_summary[code] = float(cat.weight_pct or 0.0)

            if code not in sa_clos_map:

                sa_clos_map[code] = set()

            for it in cat.items:

                for token in str(it.co_id or "").replace(";", ",").replace("/", ",").split(","):

                    tok = token.split(":")[0].strip().upper()

                    if tok:

                        sa_clos_map[code].add(tok)

    if not sa_summary:

        sa_summary = {"SA1": 40.0, "SA2": 60.0}



    n_clos = max(1, len(bp.course_outcomes))

    clo_col_w = 120.0 / n_clos

    col_widths_g = (45.0, 45.0) + tuple(clo_col_w for _ in range(n_clos))



    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=col_widths_g, width=210.0, line_height=4.8, align="L") as t_grd:

        hdr = t_grd.row(style=gray_hdr)

        hdr.cell("Assessment Item")

        hdr.cell("Percentage of Final Grade")

        for co in bp.course_outcomes:

            hdr.cell(_clean_text(co.co_id))



        tot_w = 0.0

        for code, wt in sa_summary.items():

            tot_w += wt

            r = t_grd.row()

            r.cell(_clean_text(code), style=FontFace(emphasis="BOLD"))

            r.cell(f"{wt:.0f}%")

            aligned_set = sa_clos_map.get(code, set())

            for co in bp.course_outcomes:

                if not aligned_set or co.co_id.strip().upper() in aligned_set:

                    matching_rubs = [
                        r for r in rubrics
                        if code in [str(c).upper().strip() for c in (r.get("assessment_codes") or [])]
                        or code in [c.upper().strip() for c in str(r.get("assessment_code") or "").split(",") if c.strip()]
                        or (r.get("assessment_code") or "").upper().strip() == code
                        or code in (r.get("title") or "").upper()
                    ]
                    if matching_rubs:
                        r.cell(_clean_text(matching_rubs[0].get("title", "Measurement Rubric")))
                    else:
                        r.cell("Scores / Assessment Items")

                else:

                    r.cell("-")



        rtot = t_grd.row(style=FontFace(emphasis="BOLD"))

        rtot.cell("TOTAL")

        rtot.cell(f"{tot_w:.0f}%")

        for _ in bp.course_outcomes:

            rtot.cell("")



    pdf.ln(3.0)

    with pdf.table(col_widths=(48.0, 5.0, 252.2), width=305.2, line_height=4.5, align="L") as t_cond:

        for k, v in [

            ("Transmutation", f"Base-{meta.transmutation_base}"),

            ("Passing Grade", "3.00"),

            ("Passing Grade Conditions", _clean_text(meta.passing_grade_conditions)),

        ]:

            r = t_cond.row()

            r.cell(k, style=FontFace(emphasis="BOLD"))

            r.cell(":")

            r.cell(v)



    pdf.ln(3.0)

    pdf.set_font("Helvetica", "B", 8.5)

    pdf.cell(0, 5.0, "Grade Equivalence Table:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)

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

    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(0, 5.5, "PART IX. LEARNING PLAN", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8.5)

    pdf.cell(0, 5.0, "In order to achieve the outcomes of this course, learners will go through this learning plan:", new_x="LMARGIN", new_y="NEXT")



    lp_rows = meta.learning_plan_table or get_default_learning_plan_table()
    pdf.set_font("Helvetica", "", 7.5)

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
            r.cell(_clean_text(row_data.get("ilo", "")))

            clo_val = row_data.get("clo", "")
            if isinstance(clo_val, list):
                clo_val = chr(10).join(str(c) for c in clo_val)
            r.cell(_clean_text(clo_val))

            r.cell(_clean_text(row_data.get("time_frame", "")))
            r.cell(_clean_text(topic_txt))
            r.cell(_clean_text(row_data.get("tla", "")))
            r.cell(_clean_text(row_data.get("required_reading", "")))

            span = spans[idx]
            if span > 1:
                act_val = row_data.get("assessment_activities", "")
                if isinstance(act_val, list):
                    act_val = chr(10).join(str(a) for a in act_val)
                r.cell(_clean_text(act_val), rowspan=span, v_align="MIDDLE")
            elif span == 1:
                act_val = row_data.get("assessment_activities", "")
                if isinstance(act_val, list):
                    act_val = chr(10).join(str(a) for a in act_val)
                r.cell(_clean_text(act_val))
            # if span == 0, omit cell because it is covered by the lead row's rowspan


    # ==========================================================================

    # PAGE 7 & 8: PART X. REFERENCES/ARTICLES TO READ, PART XI. CLASSROOM POLICIES & SIGNATORIES

    # ==========================================================================

    pdf.ln(4.0)

    if pdf.get_y() > 145.0:

        pdf.add_page()



    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(0, 5.5, "PART X. REFERENCES/ARTICLES TO READ", new_x="LMARGIN", new_y="NEXT")

    ref_rows = meta.references_table or get_default_references_table()

    pdf.set_font("Helvetica", "", 8)

    with pdf.table(col_widths=(32.0, 273.2), width=305.2, line_height=4.4) as t_ref:

        hdr = t_ref.row(style=gray_hdr)

        hdr.cell("Code")

        hdr.cell("Reference/Article")

        for ref in ref_rows:

            r = t_ref.row()

            r.cell(_clean_text(ref.get("code", "")))

            r.cell(_clean_text(ref.get("reference", "")))



    pdf.ln(3.5)

    if pdf.get_y() > 155.0:

        pdf.add_page()



    pdf.set_font("Helvetica", "B", 9.5)

    pdf.cell(0, 5.5, "PART XI. CLASSROOM POLICIES", new_x="LMARGIN", new_y="NEXT")

    pol_rows = meta.policies_table or get_default_policies_table()

    pdf.set_font("Helvetica", "", 7.8)

    for idx, pol in enumerate(pol_rows, start=1):

        num = pol.get("number", str(idx)).strip()

        title = pol.get("title", "").strip()

        desc = pol.get("description", "").strip()

        pdf.set_font("Helvetica", "B", 7.8)

        line_prefix = f"{num}. {title}. " if title else f"{num}. "

        pdf.multi_cell(305.2, 4.0, _clean_text(line_prefix + desc), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(0.8)



    # SIGNATORIES BLOCK AT THE END (Official 4-Step Chain with Review Committee, QA Head & Dean)

    if pdf.get_y() > 140.0:

        pdf.add_page()

    pdf.ln(4.0)



    # Collect workflow signatures if passed in workflow or doc

    wf_sigs = {}

    if doc and isinstance(doc, dict):

        for s in (doc.get("workflow", {}).get("signatures", [])):

            wf_sigs[s.get("role")] = s



    dept_short = meta.department.replace("Department of ", "").strip()



    # Retrieve signatory details & timestamps

    comm_sig = wf_sigs.get("review_committee")

    comm_name = comm_sig.get("full_name") if comm_sig else "SYLLABUS REVIEW COMMITTEE"

    comm_title = comm_sig.get("title") if comm_sig else "Course Evaluation Committee"

    comm_time = f"Signed: {comm_sig.get('signed_at')[:16].replace('T', ' ')}" if comm_sig else ""



    ph_sig = wf_sigs.get("program_head")

    ph_name = ph_sig.get("full_name") if ph_sig else meta.program_head

    ph_title = ph_sig.get("title") if ph_sig else f"Program Head - {dept_short}"

    ph_time = f"Signed: {ph_sig.get('signed_at')[:16].replace('T', ' ')}" if ph_sig else ""



    qa_sig = wf_sigs.get("qa_head")

    qa_name = qa_sig.get("full_name") if qa_sig else "COLLEGE QUALITY ASSURANCE HEAD"

    qa_title = qa_sig.get("title") if qa_sig else "College Quality Assurance Head"

    qa_time = f"Countersigned: {qa_sig.get('signed_at')[:16].replace('T', ' ')}" if qa_sig else ""



    dean_sig = wf_sigs.get("dean")

    dean_name = dean_sig.get("full_name") if dean_sig else meta.dean_name

    dean_title = dean_sig.get("title") if dean_sig else "Dean, College of Engineering"

    dean_time = f"Approved & Locked: {dean_sig.get('signed_at')[:16].replace('T', ' ')}" if dean_sig else ""



    # ROW 1: Prepared by (Faculty) | Reviewed by (Review Committee) | Recommending Approval (Program Head)

    pdf.set_font("Helvetica", "", 8.0)

    pdf.cell(101.7, 4.5, "Prepared by:", border=0)

    pdf.cell(101.7, 4.5, "Reviewed by (Syllabus Review Committee):", border=0)

    pdf.cell(101.8, 4.5, "Recommending Approval:", border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5.0)



    pdf.set_font("Helvetica", "B", 8.8)

    pdf.cell(101.7, 4.2, _clean_text(meta.faculty_name.upper()), border=0)

    pdf.cell(101.7, 4.2, _clean_text(comm_name.upper()), border=0)

    pdf.cell(101.8, 4.2, _clean_text(ph_name.upper()), border=0, new_x="LMARGIN", new_y="NEXT")



    pdf.set_font("Helvetica", "", 7.8)

    pdf.cell(101.7, 3.8, "Faculty in Charge", border=0)

    pdf.cell(101.7, 3.8, _clean_text(comm_title), border=0)

    pdf.cell(101.8, 3.8, _clean_text(ph_title), border=0, new_x="LMARGIN", new_y="NEXT")



    pdf.set_font("Helvetica", "I", 7.0)

    pdf.set_text_color(70, 70, 70)

    pdf.cell(101.7, 3.6, "", border=0)

    pdf.cell(101.7, 3.6, _clean_text(comm_time), border=0)

    pdf.cell(101.8, 3.6, _clean_text(ph_time), border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)



    pdf.ln(5.0)



    # ROW 2: Countersigned by (College QA Head) | Approved by (Dean)

    pdf.set_font("Helvetica", "", 8.0)

    pdf.cell(152.6, 4.5, "Countersigned by (Quality Assurance):", border=0)

    pdf.cell(152.6, 4.5, "Approved by:", border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5.0)



    pdf.set_font("Helvetica", "B", 8.8)

    pdf.cell(152.6, 4.2, _clean_text(qa_name.upper()), border=0)

    pdf.cell(152.6, 4.2, _clean_text(dean_name.upper()), border=0, new_x="LMARGIN", new_y="NEXT")



    pdf.set_font("Helvetica", "", 7.8)

    pdf.cell(152.6, 3.8, _clean_text(qa_title), border=0)

    pdf.cell(152.6, 3.8, _clean_text(dean_title), border=0, new_x="LMARGIN", new_y="NEXT")



    pdf.set_font("Helvetica", "I", 7.0)

    pdf.set_text_color(70, 70, 70)

    pdf.cell(152.6, 3.6, _clean_text(qa_time), border=0)

    pdf.cell(152.6, 3.6, _clean_text(dean_time), border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)



    return bytes(pdf.output())

