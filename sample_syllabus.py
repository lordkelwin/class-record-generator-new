import os
import re
from typing import List, Dict, Any, Optional
from fpdf import FPDF
from models import (
    SyllabusBlueprint,
    CourseMetadata,
    TermConfig,
    CourseOutcome,
    AssessmentCategory,
    AssessmentItem,
    StudentRecord,
    CQIPlan,
    get_default_cqi_indicators,
    get_default_policies_table,
    get_default_references_table,
    get_default_syllabus_assessment_activities,
)


def get_default_sample_students() -> List[StudentRecord]:
    """Returns a realistic roster of 15 engineering students with scores for EE 211."""
    roster = [
        ("2025-01881", "Abear", "Phave Bryl Perote", "", "EE 2A", 0.82),
        ("2025-00148", "Acedilla", "Princess Aiky Amoin", "", "EE 2A", 0.76),
        ("2025-00264", "Amomas", "Kristine Joy Failog", "", "EE 2A", 0.88),
        ("2024-01487", "Añasco", "Jan Elie Alcoseba", "", "EE 2A", 0.68),
        ("2025-00261", "Bucod", "Caster Troy Ceredon", "", "EE 2A", 0.74),
        ("2025-00263", "Cabanilla", "Mary Queen Rectazo", "", "EE 2A", 0.91),
        ("2025-01401", "Cartagena", "Jancart Gabito", "", "EE 2A", 0.45),
        ("2025-00247", "Castillones", "Angelika Constantino", "", "EE 2A", 0.85),
        ("2025-00271", "Castrodes", "Timothy John Caiña", "", "EE 2A", 0.79),
        ("2025-00278", "Dinoy", "Rica Attos", "", "EE 2A", 0.56),
        ("2025-00251", "Flores", "Louie Adrian Villarin", "", "EE 2A", 0.42),
        ("2025-00253", "Galon", "Gabriel Jhon Melecio", "", "EE 2A", 0.81),
        ("2025-00245", "Gella", "Clark Vergel Yares", "", "EE 2A", 0.48),
        ("2025-00281", "Gemone", "Angelei Rose Cencia", "", "EE 2A", 0.77),
        ("2025-00268", "Gonzales", "Anjelene Macias", "", "EE 2A", 0.84),
    ]
    # Define per-item and per-CLO max points for sample student score generation
    item_clo_max = {
        "A1": {"CLO1": 50, "CLO2": 50},
        "A2": {"CLO1": 50, "CLO2": 50},
        "Q1": {"CLO1": 15, "CLO2": 15},
        "Q2": {"CLO1": 15, "CLO2": 15},
        "MTE": {"CLO1": 30, "CLO2": 30},
        "MTE_1": {"CLO1": 30},
        "MTE_2": {"CLO2": 30},
        "A3": {"CLO1": 50, "CLO2": 50},
        "A4": {"CLO1": 50, "CLO2": 50},
        "Q3": {"CLO1": 15, "CLO2": 15},
        "Q4": {"CLO1": 15, "CLO2": 15},
        "FTE": {"CLO1": 30, "CLO2": 30},
        "FTE_1": {"CLO1": 30},
        "FTE_2": {"CLO2": 30},
    }
    students = []
    for idx, (sid, last, first, mi, prog, perf) in enumerate(roster):
        scores = {}
        for j, (item_id, clo_map) in enumerate(item_clo_max.items()):
            item_total = 0
            for c_idx, (clo_id, clo_max) in enumerate(clo_map.items()):
                offset = ((idx * 7 + j * 5 + c_idx * 11) % 19 - 9) / 100.0
                ratio = max(0.35, min(0.98, perf + offset))
                sc_val = round(clo_max * ratio)
                scores[f"{item_id}__{clo_id}"] = sc_val
                item_total += sc_val
            scores[item_id] = item_total
        students.append(
            StudentRecord(
                student_id=sid,
                last_name=last,
                first_name=first,
                middle_initial=mi,
                program_year=prog,
                scores=scores,
            )
        )
    return students


def get_default_rubrics() -> List[Dict[str, Any]]:
    """Returns an empty list by default, allowing faculty to define their own custom rubrics."""
    return []


def get_default_blueprint(include_sample_scores: bool = True) -> SyllabusBlueprint:
    """Returns the USeP EE 211 (Electrical Circuits 1) syllabus blueprint matching EE 211.pdf & Math 211.xlsm."""
    metadata = CourseMetadata(
        university="University of Southeastern Philippines",
        college="COLLEGE OF ENGINEERING",
        address="Iñigo St., Bo. Obrero, Davao City 8000",
        program_name="Bachelor of Science in Electrical Engineering",
        program_code="EE",
        academic_unit="Engineering",
        course_code="EE 211",
        course_title="Electrical Circuits 1",
        credit_units="3.0 Units – Lecture",
        lec_lab="Lecture",
        schedule="MWF 08:00 AM - 09:00 AM",
        room="304",
        semester_ay="1st Semester, A.Y. 2026-2027",
        section="EE 2A",
        faculty_name="ELWIN JAY J. TANO",
        program_head="CHARITO O. CLARO",
        dean_name="JOIE D. CATAYTAY",
        transmutation_base=50,
        passing_percentage=75.0,
        grading_mode="two_term",
    )

    terms = [
        TermConfig(term_name="Midterm", weight_pct=50.0),
        TermConfig(term_name="Finals", weight_pct=50.0),
    ]

    course_outcomes = [
        CourseOutcome(
            co_id="CLO1",
            description="Given DC and AC circuit networks, the student will calculate unknown circuit variables by accurately solving necessary linear and differential equations.",
            program_outcomes="PGO a",
            graduate_outcome_desc="a) Apply knowledge of mathematics and sciences to solve engineering problems",
            performance_indicator="a.1. Apply concepts in mathematics to solve engineering problems.",
            iga_aligned="IGA2",
            target_score_pct=75.0,
            target_class_pass_pct=50.0,
        ),
        CourseOutcome(
            co_id="CLO2",
            description="Given interconnected electrical elements and energy storage devices, the student will simplify complex circuits into their equivalent models by systematically applying network reduction theorems.",
            program_outcomes="PGO e",
            graduate_outcome_desc="e) Identify, formulate, and solve complex engineering problems",
            performance_indicator="e.2. Formulate and solve complex engineering problems.",
            iga_aligned="IGA5",
            target_score_pct=75.0,
            target_class_pass_pct=50.0,
        ),
    ]

    # Categories strictly matching USeP EE 211 Math 211 grading policy
    categories = [
        # MIDTERM PERIOD
        AssessmentCategory(
            category_id="MID_FA1",
            term="Midterm",
            assessment_type="FA",
            assessment_code="FA1",
            name="Formative Assessment 1 (Group Activity)",
            lec_lab="Lecture",
            weight_pct=0.0,
            items=[
                AssessmentItem(
                    "A1",
                    "FA1 Group Activity 1 (Nodal & Mesh Analysis Exercise)",
                    100.0,
                    "CLO1, CLO2",
                    100.0,
                    {"CLO1": 50.0, "CLO2": 50.0},
                ),
            ],
        ),
        AssessmentCategory(
            category_id="MID_FA2",
            term="Midterm",
            assessment_type="FA",
            assessment_code="FA2",
            name="Formative Assessment 2 (Group Activity)",
            lec_lab="Lecture",
            weight_pct=0.0,
            items=[
                AssessmentItem(
                    "A2",
                    "FA2 Group Activity 2 (Superposition & Thevenin Circuit Simulation)",
                    100.0,
                    "CLO1, CLO2",
                    100.0,
                    {"CLO1": 50.0, "CLO2": 50.0},
                ),
            ],
        ),
        AssessmentCategory(
            category_id="MID_SA1",
            term="Midterm",
            assessment_type="SA",
            assessment_code="SA1",
            name="Summative Assessment 1 (Quizzes)",
            lec_lab="Lecture",
            weight_pct=40.0,
            items=[
                AssessmentItem(
                    "Q1",
                    "Quiz 1 (Nodal, Mesh & Equivalent Circuit Equations)",
                    30.0,
                    "CLO1, CLO2",
                    20.0,
                    {"CLO1": 15.0, "CLO2": 15.0},
                ),
                AssessmentItem(
                    "Q2",
                    "Quiz 2 (Superposition, Thevenin/Norton & Op-Amp Circuits)",
                    30.0,
                    "CLO1, CLO2",
                    20.0,
                    {"CLO1": 15.0, "CLO2": 15.0},
                ),
            ],
        ),
        AssessmentCategory(
            category_id="MID_SA2",
            term="Midterm",
            assessment_type="SA",
            assessment_code="SA2",
            name="Summative Assessment 2 (Term Examination)",
            lec_lab="Lecture",
            weight_pct=60.0,
            items=[
                AssessmentItem(
                    "MTE",
                    "Midterm Examination (CLO1: Circuit Equations | CLO2: Network Theorems)",
                    60.0,
                    "CLO1, CLO2",
                    60.0,
                    {"CLO1": 30.0, "CLO2": 30.0},
                ),
            ],
        ),
        # FINALS PERIOD
        AssessmentCategory(
            category_id="FIN_FA1",
            term="Finals",
            assessment_type="FA",
            assessment_code="FA1",
            name="Formative Assessment 1 (Group Activity)",
            lec_lab="Lecture",
            weight_pct=0.0,
            items=[
                AssessmentItem(
                    "A3",
                    "FA1 Group Activity 3 (RL/RC/RLC Transient Simulation)",
                    100.0,
                    "CLO1, CLO2",
                    100.0,
                    {"CLO1": 50.0, "CLO2": 50.0},
                ),
            ],
        ),
        AssessmentCategory(
            category_id="FIN_FA2",
            term="Finals",
            assessment_type="FA",
            assessment_code="FA2",
            name="Formative Assessment 2 (Group Activity)",
            lec_lab="Lecture",
            weight_pct=0.0,
            items=[
                AssessmentItem(
                    "A4",
                    "FA2 Group Activity 4 (AC Steady-State Analysis & Phasor Exercise)",
                    100.0,
                    "CLO1, CLO2",
                    100.0,
                    {"CLO1": 50.0, "CLO2": 50.0},
                ),
            ],
        ),
        AssessmentCategory(
            category_id="FIN_SA1",
            term="Finals",
            assessment_type="SA",
            assessment_code="SA1",
            name="Summative Assessment 1 (Quizzes)",
            lec_lab="Lecture",
            weight_pct=40.0,
            items=[
                AssessmentItem(
                    "Q3",
                    "Quiz 3 (Energy-Storing Elements & First-Order Transients)",
                    30.0,
                    "CLO1, CLO2",
                    20.0,
                    {"CLO1": 15.0, "CLO2": 15.0},
                ),
                AssessmentItem(
                    "Q4",
                    "Quiz 4 (Second-Order Transients, Sinusoids & Phasor Analysis)",
                    30.0,
                    "CLO1, CLO2",
                    20.0,
                    {"CLO1": 15.0, "CLO2": 15.0},
                ),
            ],
        ),
        AssessmentCategory(
            category_id="FIN_SA2",
            term="Finals",
            assessment_type="SA",
            assessment_code="SA2",
            name="Summative Assessment 2 (Term Examination)",
            lec_lab="Lecture",
            weight_pct=60.0,
            items=[
                AssessmentItem(
                    "FTE",
                    "Final Term Examination (CLO1: Differential/Phasor Equations | CLO2: Complete RLC/AC Responses)",
                    60.0,
                    "CLO1, CLO2",
                    60.0,
                    {"CLO1": 30.0, "CLO2": 30.0},
                ),
            ],
        ),
    ]

    students = get_default_sample_students() if include_sample_scores else []

    return SyllabusBlueprint(
        metadata=metadata,
        terms=terms,
        course_outcomes=course_outcomes,
        categories=categories,
        students=students,
        cqi_plan=CQIPlan(indicators=get_default_cqi_indicators()),
        rubrics=[],
        parser_notes=[
            "Loaded USeP EE 211 (Electrical Circuits 1) OBE Syllabus Blueprint (FM-USeP-MID-01).",
            "Linked CLO1 -> PGO a (PI a.1, IGA2) and CLO2 -> PGO e (PI e.2, IGA5).",
            "Configured Base-50 Grading System (Passing = 75 -> 3.00): FA1 (Formative 0%), SA1 Quizzes (40%), SA2 Term Examination (60%).",
            "Included CLO Grade section, Course Learning Outcome Assessment Report, CO Assessment Tool, and CQI Plan.",
        ],
    )


DEFAULT_ORIENTATION_ROW: Dict[str, str] = {
    "ilo": "• Recognize the university VMGO & Institutional Graduate Attributes.\n• Appreciates the significance of PEOs and PGOs of the program.\n• Recognize the rules and regulations of the course and the grading system.",
    "clo": "",
    "time_frame": "1 hour",
    "topics": "• Course Orientation\n• VMGO & IGA of the University\n• PEOs & PGOs of the program\n• Rules and regulations of the course & grading system\n• Presentation of the course outline",
    "tla": "• On-site or online meeting",
    "required_reading": "• USeP Student Handbook (2016 edition)",
    "assessment_activities": "• N/A",
}


def parse_prereqs_coreqs_to_table(prereqs: str = "", coreqs: str = "") -> List[Dict[str, str]]:
    table: List[Dict[str, str]] = []
    if prereqs and prereqs.strip() and prereqs.strip().lower() != "none":
        for item in prereqs.split(";"):
            item = item.strip()
            if not item:
                continue
            parts = [p.strip() for p in item.split("-", 1)]
            code = parts[0]
            title = parts[1] if len(parts) > 1 else ""
            table.append({"req_type": "Pre-requisite", "course_code": code, "course_title": title})
    if coreqs and coreqs.strip() and coreqs.strip().lower() != "none":
        for item in coreqs.split(";"):
            item = item.strip()
            if not item:
                continue
            parts = [p.strip() for p in item.split("-", 1)]
            code = parts[0]
            title = parts[1] if len(parts) > 1 else ""
            table.append({"req_type": "Co-requisite", "course_code": code, "course_title": title})
    return table


def parse_sdg_string_to_table(sdg_str: str = "") -> List[Dict[str, str]]:
    from catalog_data import UN_SDG_CATALOG
    nums = re.findall(r"\b\d{1,2}\b", sdg_str or "")
    rows = []
    for num_str in nums:
        match_obj = next((s for s in UN_SDG_CATALOG if s["sdg"].startswith(f"{num_str}:")), None)
        if match_obj and not any(r["sdg"] == match_obj["sdg"] for r in rows):
            rows.append({"sdg": match_obj["sdg"], "description": match_obj["description"]})
    if not rows and len(UN_SDG_CATALOG) >= 9:
        rows.append({"sdg": UN_SDG_CATALOG[6]["sdg"], "description": UN_SDG_CATALOG[6]["description"]})
        rows.append({"sdg": UN_SDG_CATALOG[8]["sdg"], "description": UN_SDG_CATALOG[8]["description"]})
    return rows


def build_learning_plan_from_topics(topics: List[str]) -> List[Dict[str, str]]:
    if not topics:
        return [dict(DEFAULT_ORIENTATION_ROW)]
    plan: List[Dict[str, str]] = [dict(DEFAULT_ORIENTATION_ROW)]
    mid = max(1, len(topics) // 2)
    for idx, t in enumerate(topics):
        if idx == mid:
            plan.append({
                "ilo": "• Demonstrate midterm competence on covered course outcomes.",
                "clo": "CLO1",
                "time_frame": "3 hours",
                "topics": "MIDTERM EXAMINATION",
                "tla": "• Conduct of Midterm Examination – Independent Assessment",
                "required_reading": "",
                "assessment_activities": "• SA2 – Term Examination",
            })
        plan.append({
            "ilo": f"• Demonstrate competence in {t.lower()}.",
            "clo": "CLO1" if idx < mid else "CLO2",
            "time_frame": "3-4 hours",
            "topics": f"• {t.upper()}",
            "tla": "• Student-based Learning\n• Problem-solving exercises\n• Collaborative and Team Learning\n• Lecture & Discussion",
            "required_reading": "• Course Handouts & Textbook References",
            "assessment_activities": "• FA1 – Formative Activity\n• SA1 – Summative Quiz",
        })
    plan.append({
        "ilo": "• Demonstrate mastery of course outcomes through comprehensive final assessment.",
        "clo": "CLO1\nCLO2",
        "time_frame": "3 hours",
        "topics": "FINAL EXAMINATION",
        "tla": "• Conduct of Final Examination – Independent Assessment",
        "required_reading": "",
        "assessment_activities": "• SA2 – Term Examination",
    })
    return plan


DESIGNATED_PROGRAM_HEADS: Dict[str, str] = {
    "EE": "Engr. Charito O. Claro",
    "CE": "Engr. Bonifacio T. Aznar Jr.",
    "ECE": "Engr. Rosanna C. Ucat",
    "ME": "Engr. Randy B. Tongson",
    "SE": "Engr. Sheena S. Arcega",
    "ABE": "Engr. Sheila C. Cogay",
    "GE": "Engr. Fillmore D. Masancay",
    "MinE": "Engr. Mark John S. Pag-alaman",
    "BSGeo": "Dean Lester P. Rejas",
}

def get_designated_program_heads(programs: Optional[List[str]] = None, primary_code: str = "EE") -> List[str]:
    progs = programs if (programs and len(programs)) else ([primary_code] if primary_code else ["EE"])
    heads = []
    for p in progs:
        p_clean = p.strip().upper()
        for k, v in DESIGNATED_PROGRAM_HEADS.items():
            if k.upper() == p_clean and v not in heads:
                heads.append(v)
    if not heads:
        heads = ["Engr. Charito O. Claro"]
    return heads

def get_blank_blueprint(
    course_code: str = "",
    course_title: str = "",
    section: str = "",
    semester_ay: str = "",
    faculty_name: str = "",
    credit_units: str = "3.0 Units – Lecture",
    lec_lab: str = "Lecture",
    contact_hours: str = "3 Hours/Week (54 Hours/Semester)",
    course_description: str = "",
    prerequisites: str = "",
    corequisites: str = "",
    program_head: str = "",
    dean_name: str = "Engr. Joie D. Cataytay, Ph.D.",
    programs: Optional[List[str]] = None,
    sections: Optional[List[str]] = None,
    program_code: str = "EE",
    program_name: str = "",
    year_level: str = "Second Year",
    sdg_alignments: str = "7: Affordable and Clean Energy; 9: Industry, Innovation, and Infrastructure",
) -> SyllabusBlueprint:
    """Returns a completely clean starter blueprint for creating a syllabus from scratch."""
    if course_code and (" - " in course_code or " – " in course_code):
        delim = " - " if " - " in course_code else " – "
        parts = course_code.split(delim, 1)
        course_code = parts[0].strip()
        if not course_title or course_title == "Untitled Subject":
            course_title = parts[1].strip()
    init_programs = programs or ([p.strip() for p in program_code.split(",") if p.strip()] if program_code else ["EE"])
    init_sections = sections or ([s.strip() for s in section.split(",") if s.strip()] if section else ["EE 2A"])
    heads = get_designated_program_heads(init_programs, program_code)
    computed_ph = (" / ".join(heads)) if (not program_head or len(heads) > 1) else program_head
    computed_dean = dean_name or "Engr. Joie D. Cataytay, Ph.D."
    dept_name = program_name or "Bachelor of Science in Electrical Engineering"
    if dept_name.startswith("Department of "):
        dept_name = dept_name.replace("Department of ", "Bachelor of Science in ")

    metadata = CourseMetadata(
        university="University of Southeastern Philippines",
        college="COLLEGE OF ENGINEERING",
        department=dept_name,
        address="Iñigo St., Bo. Obrero, Davao City 8000",
        program_name=program_name or "Bachelor of Science in Electrical Engineering",
        program_code=program_code or "EE",
        programs=init_programs,
        sections=init_sections,
        academic_unit="Engineering",
        course_code=course_code or "New Course",
        course_title=course_title or "Untitled Subject",
        credit_units=credit_units,
        lec_lab=lec_lab,
        schedule="TBA",
        room="TBA",
        semester_ay=semester_ay or "1st Semester, A.Y. 2026-2027",
        section=section or "EE 2A",
        faculty_name=faculty_name or "Engr. Elwin Jay J. Tano",
        program_head=computed_ph,
        program_heads=heads,
        dean_name=computed_dean,
        transmutation_base=50,
        passing_percentage=75.0,
        grading_mode="two_term",
        course_description=course_description,
        prerequisites=prerequisites,
        corequisites=corequisites,
        contact_hours=contact_hours,
        year_level=year_level or "Second Year",
        sdg_alignments=sdg_alignments,
        prereq_coreq_table=parse_prereqs_coreqs_to_table(prerequisites, corequisites),
        sdg_table=parse_sdg_string_to_table(sdg_alignments),
        syllabus_assessment_activities=get_default_syllabus_assessment_activities(),
        learning_plan_table=[dict(DEFAULT_ORIENTATION_ROW)],
        references_table=get_default_references_table(),
        policies_table=get_default_policies_table(),
    )

    terms = [
        TermConfig(term_name="Midterm", weight_pct=50.0),
        TermConfig(term_name="Finals", weight_pct=50.0),
    ]

    starter_clo = CourseOutcome(
        co_id="CLO1",
        description="",
        program_outcomes="PGO a",
        graduate_outcome_desc="a) Apply knowledge of mathematics and sciences to solve engineering problems",
        performance_indicator="a.1. Apply concepts in mathematics to solve engineering problems.",
        iga_aligned="IGA2",
        target_score_pct=75.0,
        target_class_pass_pct=50.0,
    )

    return SyllabusBlueprint(
        metadata=metadata,
        terms=terms,
        course_outcomes=[starter_clo],
        categories=[],
        students=[],
        cqi_plan=CQIPlan(indicators=get_default_cqi_indicators()),
        rubrics=[],
        parser_notes=["New course syllabus created from scratch."],
    )


def generate_sample_syllabus_pdf(output_path: str) -> str:
    """If EE 211.pdf exists in workspace, returns it; otherwise generates a sample syllabus PDF."""
    workspace_ee211 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "EE 211.pdf")
    if os.path.exists(workspace_ee211):
        return workspace_ee211

    bp = get_default_blueprint(include_sample_scores=False)
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 7, bp.metadata.university, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, f"COURSE SYLLABUS IN {bp.metadata.course_code} - {bp.metadata.course_title.upper()}", new_x="LMARGIN", new_y="NEXT", align="C")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pdf.output(output_path)
    return output_path
