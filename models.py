from dataclasses import dataclass, field, asdict
from typing import List, Dict


@dataclass
class CourseOutcome:
    co_id: str  # e.g., "CLO1", "CLO2"
    description: str
    program_outcomes: str = "PGO a"  # Short code e.g. "PGO a"
    graduate_outcome_desc: str = "a) Apply knowledge of mathematics and sciences to solve engineering problems"
    performance_indicator: str = "a.1. Apply concepts in mathematics to solve engineering problems."
    iga_aligned: str = "IGA2"
    target_score_pct: float = 75.0  # Degree (from CO): 75 in Base-50 (equivalent to 50% raw accuracy)
    target_class_pass_pct: float = 50.0  # Target (% of Students achieving CLO): 50%


@dataclass
class AssessmentItem:
    item_id: str  # Label e.g., "A1", "Q1", "Q2", "MTE", "A3", "Q3", "Q4", "FTE"
    name: str  # e.g., "Formative Activity 1", "Quiz 1", "Midterm Exam"
    max_score: float = 30.0
    co_id: str = "CLO1"  # Aligned CLO(s), e.g. "CLO1" or "CLO1, CLO2"
    weight_pct: float = 20.0  # Item weight within the term (0 for FA, >0 for SA)
    clo_points: Dict[str, float] = field(default_factory=dict)  # Per-CLO max points, e.g. {"CLO1": 15.0, "CLO2": 15.0}

    def __post_init__(self):
        import re
        raw_clos = [
            p.split(":")[0].strip().upper()
            for p in re.split(r"[,;/]+", str(self.co_id or "CLO1"))
            if p.strip()
        ]
        clos = []
        for c in raw_clos:
            if c and c not in clos:
                clos.append(c)
        if not clos:
            clos = ["CLO1"]

        # Parse inline "CLO1:15, CLO2:15" if present in co_id
        inline_pts: Dict[str, float] = {}
        for p in re.split(r"[,;/]+", str(self.co_id or "")):
            if ":" in p:
                k, v = p.split(":", 1)
                k_clean = k.strip().upper()
                try:
                    inline_pts[k_clean] = float(v.strip())
                except ValueError:
                    pass

        cleaned_pts: Dict[str, float] = {}
        if isinstance(self.clo_points, dict):
            for k, v in self.clo_points.items():
                try:
                    val = float(v)
                    if val > 0:
                        cleaned_pts[str(k).strip().upper()] = val
                except (ValueError, TypeError):
                    pass

        for k, v in inline_pts.items():
            if k not in cleaned_pts and v > 0:
                cleaned_pts[k] = v

        total = float(self.max_score or 30.0)
        n_clos = max(1, len(clos))
        default_each = round(total / n_clos, 2)

        final_pts: Dict[str, float] = {}
        for c in clos:
            final_pts[c] = cleaned_pts.get(c, default_each)

        self.clo_points = final_pts
        self.co_id = ", ".join(clos)
        pts_sum = round(sum(final_pts.values()), 2)
        if pts_sum > 0:
            self.max_score = pts_sum


@dataclass
class AssessmentCategory:
    category_id: str  # e.g., "MID_FA1", "MID_SA1", "MID_SA2"
    term: str  # "Midterm" or "Finals"
    assessment_type: str = "SA"  # "FA" (Formative) or "SA" (Summative)
    assessment_code: str = "SA1"  # "FA1", "FA2", "SA1", "SA2", "SA3"
    name: str = "Summative Assessment 1 (Quizzes)"
    lec_lab: str = "Lecture"
    weight_pct: float = 40.0  # Weight of this category within the term (0 for FA, e.g. 40% for SA1, 60% for SA2)
    items: List[AssessmentItem] = field(default_factory=list)


@dataclass
class TermConfig:
    term_name: str  # "Midterm", "Finals"
    weight_pct: float = 50.0


@dataclass
class StudentRecord:
    student_id: str
    last_name: str
    first_name: str
    middle_initial: str = ""
    program_year: str = "BSEE 2A"
    scores: Dict[str, float] = field(default_factory=dict)  # item_id -> raw score

    @property
    def full_name(self) -> str:
        if self.first_name:
            mi = f" {self.middle_initial}" if self.middle_initial else ""
            return f"{self.last_name}, {self.first_name}{mi}".strip()
        return self.last_name


@dataclass
class CQIIndicator:
    category: str
    number: int
    title: str
    subtitle: str
    mark: str = "✓"  # "✓" or "✗"
    remarks: str = ""


@dataclass
class CQIPlan:
    date_of_evaluation: str = "October 2026"
    indicators: List[CQIIndicator] = field(default_factory=list)
    key_strengths: str = (
        "Course delivery strictly followed the OBE syllabus learning plan, utilizing problem-based learning, "
        "collaborative group activities (FA1), and structured rubric-based summative assessments (SA1 & SA2)."
    )
    areas_for_improvement: str = (
        "Some students encountered difficulties in setting up multi-loop nodal/mesh differential equations "
        "and time-domain RLC transient analysis under time constraints during major examinations."
    )
    action_plan: str = (
        "1. Increase guided problem-solving drills and simulation verification during formative group activities (FA1).\n"
        "2. Conduct targeted remedial review sessions prior to term examinations focusing on CLOs with <75% average score.\n"
        "3. Provide step-by-step rubric exemplars for multi-source network theorem and transient problems."
    )


def get_default_prereq_coreq_table() -> List[Dict[str, str]]:
    return [
        {"req_type": "Pre-requisite", "course_code": "NAT SCI 2", "course_title": "PHYSICS FOR ENGINEERS"},
        {"req_type": "Pre-requisite", "course_code": "MATH 121", "course_title": "ENGINEERING CALCULUS 2"},
        {"req_type": "Co-requisite", "course_code": "EE 211L", "course_title": "ELECTRICAL CIRCUITS 1 LAB"},
    ]


def get_default_sdg_table() -> List[Dict[str, str]]:
    return [
        {
            "sdg": "7: Affordable and Clean Energy",
            "description": (
                "This course introduces the core concepts of electrical power, energy-storing elements "
                "(capacitors and inductors), and maximum power transfer. A rigorous understanding of "
                "voltage, current, and power calculation is the absolute prerequisite for designing, analyzing, "
                "and optimizing renewable energy systems, smart grids, and energy-efficient electrical "
                "networks in the future."
            ),
        },
        {
            "sdg": "9: Industry, Innovation, and Infrastructure",
            "description": (
                "Circuit analysis is the fundamental language of all electrical infrastructure and technological "
                "innovation. By learning to simplify complex multi-source networks and analyze transient "
                "and steady-state responses, students develop the technical competencies required to "
                "innovate and maintain resilient industrial power systems, electronics, and communication "
                "infrastructures."
            ),
        },
    ]


def get_default_syllabus_assessment_activities() -> List[Dict[str, str]]:
    return [
        {
            "type": "Formative",
            "code": "FA1",
            "activity": "Oral Recitation",
            "description": (
                "Oral recitations require students to explain, articulate, and analyze fundamental engineering concepts, "
                "laws, and operational principles. Emphasis is placed on demonstrating conceptual understanding, applying "
                "principles to practical engineering problems, and communicating technical reasoning clearly and logically."
            ),
            "clo_aligned": "CLO1",
            "rubric_ref": "FA1: Oral Recitation Rubric",
        },
        {
            "type": "Formative",
            "code": "FA2",
            "activity": "Group Activity",
            "description": (
                "Collaborative team-based exercises and simulation activities where students solve, analyze, and troubleshoot "
                "practical engineering systems and networks. Reinforces foundational problem-solving, collaborative teamwork, "
                "and technical documentation."
            ),
            "clo_aligned": "CLO2",
            "rubric_ref": "FA2: Group Activity Rubric",
        },
        {
            "type": "Summative",
            "code": "SA1",
            "activity": "Quizzes",
            "description": (
                "Periodic summative assessments comprising conceptual questions, short essays, and structured mathematical "
                "problem-solving scenarios. Designed to incrementally evaluate the students' analytical grasp of core principles "
                "prior to major examinations."
            ),
            "clo_aligned": "CLO1, CLO2",
            "rubric_ref": "SA1/SA2: Problem Solving Rubric",
        },
        {
            "type": "Summative",
            "code": "SA2",
            "activity": "Term Examination",
            "description": (
                "Comprehensive summative examinations evaluating students' overall mastery of course outcomes through a rigorous "
                "mix of conceptual analysis, multi-step problem solving, and analytical design scenarios."
            ),
            "clo_aligned": "CLO1, CLO2",
            "rubric_ref": "SA1/SA2: Problem Solving Rubric",
        },
    ]


def get_default_learning_plan_table() -> List[Dict[str, str]]:
    return [
        {
            "ilo": (
                "• Recognize the university VMGO & Institutional Graduate Attributes.\n"
                "• Appreciates the significance of PEOs and PGOs of the programs.\n"
                "• Recognize the rules and regulations of the course and the grading system."
            ),
            "clo": "",
            "time_frame": "1 hour",
            "topics": (
                "• Course Orientation\n"
                "• VMGO & IGA of the University\n"
                "• PEOs & PGOs of the program.\n"
                "• Rules and regulations of the course & grading system\n"
                "• Presentation of the course outline"
            ),
            "tla": "• On-site or online meeting",
            "required_reading": "• USeP Student Handbook (2016 edition)",
            "assessment_activities": "• N/A",
        },
        {
            "ilo": (
                "• Formulate basic circuit equations using voltage and current laws to solve unknown variables "
                "in fundamental networks. (CDIO Skills: 1.2.1, 2.1.1)"
            ),
            "clo": "CLO1",
            "time_frame": "4 hours",
            "topics": "• DC/AC SOURCES AND ELECTRICAL CIRCUIT COMPONENTS, VOLTAGE AND CURRENT LAWS",
            "tla": (
                "• Student-based Learning\n• Flipped Classroom\n• Collaborative and Team Learning\n"
                "• Active Learning\n• Technology Integration\n• Problem sets\n• Lecture"
            ),
            "required_reading": "• Ref01-08",
            "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz",
        },
        {
            "ilo": (
                "• Set up and solve linear equations using general nodal and mesh analysis methods for complex "
                "circuit networks. (CDIO Skills: 1.2.1, 2.1.2)"
            ),
            "clo": "CLO1",
            "time_frame": "7 hours",
            "topics": "• NODAL AND MESH ANALYSIS\n  o General mesh analysis\n  o General nodal analysis",
            "tla": (
                "• Student-based Learning\n• Flipped Classroom\n• Collaborative and Team Learning\n"
                "• Active Learning\n• Technology Integration\n• Problem sets\n• Lecture"
            ),
            "required_reading": "• Ref01-08",
            "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz",
        },
        {
            "ilo": (
                "• Simplify multi-source electrical networks into equivalent circuits using standard theorems. "
                "(CDIO Skills: 1.2.1, 2.1.3, 2.1.4)"
            ),
            "clo": "CLO2",
            "time_frame": "12 hours",
            "topics": (
                "• CIRCUIT ANALYSIS TECHNIQUES\n"
                "  o Linearity and superposition\n"
                "  o Source transformation\n"
                "  o Thevenin and Norton equivalent circuits\n"
                "  o Maximum power transfer\n"
                "  o Delta-Wye conversion\n"
                "  o Circuits with controlled sources and the ideal op amp"
            ),
            "tla": (
                "• Student-based Learning\n• Flipped Classroom\n• Collaborative and Team Learning\n"
                "• Active Learning\n• Technology Integration\n• Problem sets\n• Lecture"
            ),
            "required_reading": "• Ref01-08",
            "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz",
        },
        {
            "ilo": "• Demonstrate mastery of foundational circuit analysis and network theorems.",
            "clo": "CLO1\nCLO2",
            "time_frame": "3 hours",
            "topics": "MIDTERM EXAMINATION",
            "tla": "• Conduct of Midterm Examination – Independent Assessment",
            "required_reading": "",
            "assessment_activities": "• SA2 – Term Examination",
        },
        {
            "ilo": (
                "• Explain the characteristics of energy-storing elements and calculate their voltage-current "
                "relationship. (CDIO Skills: 1.2.1, 2.1.1)"
            ),
            "clo": "CLO1",
            "time_frame": "4 hours",
            "topics": "• CHARACTERISTICS OF ENERGY-STORING ELEMENTS\n  o Capacitors and capacitance\n  o Inductors and inductance",
            "tla": (
                "• Student-based Learning\n• Flipped Classroom\n• Collaborative and Team Learning\n"
                "• Active Learning\n• Technology Integration\n• Problem Sets\n• Lecture"
            ),
            "required_reading": "• Ref01-08",
            "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz",
        },
        {
            "ilo": (
                "• Determine the transient and steady-state responses of source-free and driven first-order "
                "circuits. (CDIO Skills: 1.2.1, 2.1.2, 2.1.3)"
            ),
            "clo": "CLO1\nCLO2",
            "time_frame": "8 hours",
            "topics": "• ANALYSIS OF RL AND RC CIRCUITS\n  o Source-free RL and RC circuits\n  o Driven RL and RC circuits",
            "tla": (
                "• Student-based Learning\n• Flipped Classroom\n• Collaborative and Team Learning\n"
                "• Active Learning\n• Technology Integration\n• Problem Sets\n• Lecture"
            ),
            "required_reading": "• Ref01-08",
            "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz",
        },
        {
            "ilo": (
                "• Calculate the complete response of series and parallel second-order circuits. "
                "(CDIO Skills: 1.2.1, 2.1.2, 2.1.5)"
            ),
            "clo": "CLO1\nCLO2",
            "time_frame": "6 hours",
            "topics": (
                "• ANALYSIS OF RLC CIRCUITS\n"
                "  o Source-free series and parallel RLC circuits\n"
                "  o Complete response of RLC circuits"
            ),
            "tla": (
                "• Student-based Learning\n• Flipped Classroom\n• Collaborative and Team Learning\n"
                "• Active Learning\n• Technology Integration\n• Learning Journals\n• Lecture"
            ),
            "required_reading": "• Ref01-08",
            "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz",
        },
        {
            "ilo": (
                "• Apply phasor concepts and impedance parameters to perform nodal and mesh analysis in the "
                "frequency domain. (CDIO Skills: 1.2.1, 2.1.2, 2.1.4)"
            ),
            "clo": "CLO1\nCLO2",
            "time_frame": "6 hours",
            "topics": (
                "• SINUSOIDAL STEADY-STATE ANALYSIS IN THE FREQUENCY DOMAIN\n"
                "  o The phasor concept and phasor diagram\n"
                "  o Concept of impedance and admittance\n"
                "  o Nodal and mesh analysis"
            ),
            "tla": (
                "• Collaborative and Team Learning\n• Active Learning\n• Technology Integration\n"
                "• Learning Journals\n• Lecture"
            ),
            "required_reading": "• Ref01-08",
            "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz",
        },
        {
            "ilo": (
                "• Demonstrate mastery of time-varying circuits, transient analysis, and frequency-domain "
                "steady-state analysis."
            ),
            "clo": "CLO1\nCLO2",
            "time_frame": "3 hours",
            "topics": "FINAL EXAMINATION",
            "tla": "• Conduct of Final Examination – Independent Assessment",
            "required_reading": "",
            "assessment_activities": "• SA2 – Term Examination",
        },
    ]


def get_default_references_table() -> List[Dict[str, str]]:
    return [
        {"code": "Ref01", "reference": "Alexander, C.K. & Sadiku, M.N.O. (2020). Fundamentals of Electric Circuits (7th ed.). McGraw Hill"},
        {"code": "Ref02", "reference": "Grob, M. (2021). Grob's Basic Electronics (13th ed.). McGraw Hill"},
        {"code": "Ref03", "reference": "Hayt, W.H., Kemmerly, J.E., & Durbin, S.M. (2019). Engineering Circuit Analysis. Ninth edition. McGraw-Hill Education, New York, NY"},
        {"code": "Ref04", "reference": "Tan, J.C. (2004). Electric Circuit Analysis. National Bookstore"},
        {"code": "Ref05", "reference": "Nahvi, M. & Edminister, J.A. (2003). Schaum's Outline of Theory and Problems of Electric Circuits. Fourth edition. McGraw-Hill"},
        {"code": "Ref06", "reference": "Gussow, M. (2007). Schaum's Outline of Basic Electricity. Second edition. McGraw-Hill"},
        {"code": "Ref07", "reference": "Nahvi, M. & Edminister, J.A. (2018). Schaum's Outline of Theory and Problems of Electric Circuits. Seventh edition. McGraw-Hill"},
        {"code": "Ref08", "reference": "Siskind, C. (1965). Electrical Circuits: Direct and Alternating Current. Second edition. McGraw-Hill"},
    ]


def get_default_policies_table() -> List[Dict[str, str]]:
    return [
        {
            "number": "1",
            "title": "Attendance and Punctuality",
            "description": (
                "Classroom attendance is an integral part of the educational experience; therefore, it is the student's "
                "responsibility to attend class. Attendance will be checked at every meeting. A student who accumulates "
                "exceeding 20% of the prescribed number of class hours will automatically be dropped from the course "
                "(unexcused absences). Arriving 15 minutes after the scheduled start time constitutes a late mark. "
                "Three late marks equate to one unexcused absence."
            ),
        },
        {
            "number": "2",
            "title": "Behavior and Decorum",
            "description": (
                "Respectful, inclusive, and professional behavior is always expected. The use of polite and non-discriminatory "
                "language is strictly observed in line with the University's commitment to a gender-fair and inclusive learning "
                "environment, and adherence to RA 11313, also known as the Safe Spaces Act."
            ),
        },
        {
            "number": "3",
            "title": "Gadget Use",
            "description": (
                "Mobile phones, tablets, and laptops must be stowed away during standard lectures to minimize distractions. "
                "However, laptops are expressively permitted and encouraged during designated practical sessions, such as when "
                "developing scripts for laboratory data automation or running circuit simulations."
            ),
        },
        {
            "number": "4",
            "title": "Dress Code",
            "description": "Wearing the prescribed university uniform is a must in accordance with the Student Handbook.",
        },
        {
            "number": "5",
            "title": "Submission of Coursework",
            "description": (
                "Extensions and late submissions of requirements will only be considered if done in writing to the lecturer "
                "at least two days before the due date. Generally, no extension will be given for the assignments.\n"
                "• Should work be submitted after the due date without written approval for an extension, a penalty of 5% "
                "deduction from the grade will be incurred for every 2 days it is late.\n"
                "• Should the work be assessed as being close to a PASS grade, but the standard has not yet been fully met, "
                "the lecturer may offer the opportunity to resubmit."
            ),
        },
        {
            "number": "6",
            "title": "Use of AI Tools",
            "description": (
                "The responsible use of generative AI tools (e.g., ChatGPT, Grammarly, Quillbot) is permitted only when "
                "explicitly allowed by the instructor for specific tasks. All AI-assisted work must be properly cited or declared."
            ),
        },
        {
            "number": "7",
            "title": "Academic Honesty",
            "description": (
                "All USePians are bound to follow the rules and regulations stipulated in the student handbook of the University "
                "and the College. Academic dishonesty includes cheating in any form, plagiarism, and similar offenses.\n"
                "• Cheating on any assignment or examination incurs a minimum penalty of zero for that work and referral to OSAS.\n"
                "• Submitting AI-generated content as original work without disclosure is considered academic dishonesty (max 15% similarity threshold)."
            ),
        },
        {
            "number": "8",
            "title": "Conduct of Quizzes and Examinations",
            "description": (
                "• Keep calculator jackets, smartphones, and irrelevant items inside bags.\n"
                "• Do not round off intermediate values to avoid accumulated rounding errors; final answers must be in three decimal places.\n"
                "• Write legibly using black or blue ballpoint pen and show all pertinent solutions clearly.\n"
                "• Math plate is used during quizzes and bluebook for term examinations.\n"
                "• No special quizzes or examinations will be given except for valid, documented reasons."
            ),
        },
        {
            "number": "9",
            "title": "Use of Calculators",
            "description": (
                "Allowed calculators must follow the Professional Regulatory Commission (PRC) recommendations "
                "(https://www.prc.gov.ph/node/6984) for non-programmable calculators."
            ),
        },
        {
            "number": "10",
            "title": "Group Work and Independent Effort",
            "description": (
                "Every group must ensure equitable contributions from all members. Directly sharing completed circuits, "
                "code, or written reports across groups is considered plagiarism and will result in a zero (0) for all involved parties."
            ),
        },
        {
            "number": "11",
            "title": "Cleanliness and Energy Conservation",
            "description": (
                "Observe cleanliness before and after class. Ensure all plugged devices and lights are turned off before leaving the classroom."
            ),
        },
        {
            "number": "12",
            "title": "Communication Channels",
            "description": (
                "Official announcements and course updates will be posted via the USeP Virtual Environment (UVE), email, or official class group chat. "
                "Direct communication with the instructor must be conducted strictly during official working days and hours (Monday to Friday, 8:00 AM to 5:00 PM)."
            ),
        },
    ]


@dataclass
class CourseMetadata:
    university: str = "University of Southeastern Philippines"
    college: str = "COLLEGE OF ENGINEERING"
    department: str = "Department of Electrical Engineering"
    address: str = "Iñigo St., Bo. Obrero, Davao City 8000"
    program_name: str = "Bachelor of Science in Electrical Engineering"
    program_code: str = "EE"
    academic_unit: str = "Engineering"
    course_code: str = "EE 211"
    course_title: str = "Electrical Circuits 1"
    credit_units: str = "3.0 Units – Lecture"
    lec_lab: str = "Lecture"
    schedule: str = "MWF 08:00 AM - 09:00 AM"
    room: str = "304"
    semester_ay: str = "1st Semester, A.Y. 2026-2027"
    section: str = "EE 2A"
    faculty_name: str = "ELWIN JAY J. TANO"
    program_head: str = "CHARITO O. CLARO"
    dean_name: str = "JOIE D. CATAYTAY"
    transmutation_base: int = 50  # Base-50 formula: (Score/Items)*50 + 50
    passing_percentage: float = 75.0  # 75 in Base-50 (which equals 50% raw score) = 3.00
    grading_mode: str = "two_term"
    iga_framework: str = "new_5_igas"  # "new_5_igas" (IGA1-IGA5) or "program_structure_6_igas" (IGA1-IGA6)
    # Syllabus Authoring & PDF Export Fields (FM-USeP-MID-01)
    version_number: str = "2026–1.0"
    version_note: str = "New"  # "New", "Minor Revision", "Major Revision", "No Revision"
    describe_revision: str = ""
    year_level: str = "Second Year"
    office: str = "College of Engineering"
    course_description: str = (
        "The course covers nodal and mesh analysis; application of network theorems in circuit analysis; analysis of "
        "circuits with controlled sources and ideal op-amps; fundamentals of capacitors and inductors; analysis of dc-driven "
        "RL, RC, and RLC circuits; sinusoidal steady-state analysis of general RLC circuits."
    )
    workload_description: str = (
        "With 18 weeks at 3 contact hours per week (54 contact hours total) the expected student workload is as follows:\n"
        "• Group Activities for Formative Assessment\n"
        "• Total of 4 quizzes (2 for both Midterm and Final Term)\n"
        "• Midterm and Final Examinations\n"
        "In instances where face-to-face sessions are impractical, online sessions, asynchronous class, or their equivalent will be provided."
    )
    passing_grade_conditions: str = (
        "Students shall take all assessments and examinations and must have an attendance of not less than 80% in the class. "
        "In case of lacking output or examination, a grade of INC (Incomplete) shall be given in accordance with the existing "
        "rules and regulations reflected in the student handbook. In case of incurring absences of more than 20% of the total "
        "expected number of attendances, a grade of UW (Unauthorized Withdrawal) will be reflected in the grade sheet."
    )
    prerequisites: str = "NAT SCI 2 – PHYSICS FOR ENGINEERS; MATH 121 – ENGINEERING CALCULUS 2"
    corequisites: str = "EE 211L – ELECTRICAL CIRCUITS 1 LAB"
    contact_hours: str = "3 Hours/Week (54 Hours/Semester)"
    consultation_hours: str = "Monday-Friday, 8:00 AM – 05:00 PM (excluding lunch break)"
    faculty_email: str = "ejjtano0120241110@usep.edu.ph"
    faculty_contact: str = "09262995868"
    sdg_alignments: str = "7: Affordable and Clean Energy; 9: Industry, Innovation, and Infrastructure"
    prereq_coreq_table: List[Dict[str, str]] = field(default_factory=get_default_prereq_coreq_table)
    sdg_table: List[Dict[str, str]] = field(default_factory=get_default_sdg_table)
    syllabus_assessment_activities: List[Dict[str, str]] = field(default_factory=get_default_syllabus_assessment_activities)
    learning_plan_table: List[Dict[str, str]] = field(default_factory=get_default_learning_plan_table)
    references_table: List[Dict[str, str]] = field(default_factory=get_default_references_table)
    policies_table: List[Dict[str, str]] = field(default_factory=get_default_policies_table)
    learning_plan_topics: List[str] = field(default_factory=list)
    references: str = ""
    classroom_policies: str = ""


def get_default_cqi_indicators() -> List[CQIIndicator]:
    return [
        CQIIndicator(
            "I. Instructor-Related Factors", 1,
            "1. Subject Matter Expertise and Currency",
            "Depth of knowledge, current trends, curriculum updates.",
            "✓", "Course topics and circuit simulation examples were aligned with current engineering standards."
        ),
        CQIIndicator(
            "I. Instructor-Related Factors", 2,
            "2. Pedagogical Skills and Teaching Methodology",
            "Use of diverse strategies (Problem-based learning, active learning etc.), clarity of objectives, critical thinking stimulation.",
            "✓", "Flipped classroom, collaborative team learning, and structured problem sets were actively utilized."
        ),
        CQIIndicator(
            "I. Instructor-Related Factors", 3,
            "3. Instructional Design and Course Structure",
            "Alignment of objectives, appropriate materials, logical flow, library access.",
            "✓", "Course Learning Outcomes (CLO1 & CLO2) were constructively aligned with FA1, SA1, and SA2."
        ),
        CQIIndicator(
            "I. Instructor-Related Factors", 4,
            "4. Feedback and Assessment Practices",
            "Timely & constructive feedback, variety of assessments, clear rubrics, application opportunities.",
            "✓", "Analytic rubrics (Problem Formulation 40%, Correctness 40%, Clarity 20%) were provided and returned promptly."
        ),
        CQIIndicator(
            "I. Instructor-Related Factors", 5,
            "5. Classroom Management and Environment",
            "Engaging & disciplined environment, positive instructor-student relations, openness, rule enforcement.",
            "✓", "Conducive learning environment maintained in accordance with University policies."
        ),
        CQIIndicator(
            "I. Instructor-Related Factors", 6,
            "6. Adaptability and Responsiveness",
            "Adaptability to learning styles, responsiveness to needs, adjustments based on feedback, tech integration.",
            "✓", "Consultation hours and virtual environment (UVE) resources were made accessible to all learners."
        ),
        CQIIndicator(
            "II. Student-Related Factors", 1,
            "1. Prior Academic Preparation",
            "Performance in prerequisites, aptitude in Math/Science, relevant prior knowledge.",
            "✗", "Several students needed refresher drills on solving systems of linear and differential equations (Math 121)."
        ),
        CQIIndicator(
            "II. Student-Related Factors", 2,
            "2. Motivation and Self-Efficacy",
            "Student interest, effort, belief in success, perceived value, self-regulation.",
            "✓", "Students demonstrated high interest during collaborative circuit analysis and simulation activities."
        ),
        CQIIndicator(
            "II. Student-Related Factors", 3,
            "3. Engagement and Participation",
            "Active participation (discussions, activities), time on coursework, engagement with materials, attendance, online forums.",
            "✓", "High attendance and active participation in formative group activities (FA1)."
        ),
        CQIIndicator(
            "II. Student-Related Factors", 4,
            "4. Study Skills and Habits",
            "Note-taking, test-taking, time management, responsibility (reading, preparation).",
            "✗", "Independent problem-solving practice outside class hours needs reinforcement before summative exams."
        ),
        CQIIndicator(
            "II. Student-Related Factors", 5,
            "5. Learning Styles and Preferences",
            "Preference for visual/auditory/kinesthetic, adaptability to approaches.",
            "✓", "Visual circuit schematics and interactive simulations supported diverse learner preferences."
        ),
        CQIIndicator(
            "III. Course Design and Resources Factors", 1,
            "1. Curriculum Relevance and Alignment",
            "Relevance to industry, alignment with PEOs/SOs, interdisciplinary integration.",
            "✓", "Directly aligned with PGO a (a.1) and PGO e (e.2) as well as SDG 7 and SDG 9."
        ),
        CQIIndicator(
            "III. Course Design and Resources Factors", 2,
            "2. Availability and Quality of Learning Resources",
            "Access to materials (textbooks, online), lab facilities/equipment, software/simulation tools.",
            "✓", "Primary references (Alexander & Sadiku, Hayt) and circuit simulation tools were readily available."
        ),
        CQIIndicator(
            "III. Course Design and Resources Factors", 3,
            "3. Class Size and Structure",
            "Impact of class size on interaction, frequency/duration of lectures/tutorials.",
            "✓", "3 contact hours per week (54 hours total) allowed structured lecture and group problem-solving."
        ),
        CQIIndicator(
            "III. Course Design and Resources Factors", 4,
            "4. Technology Integration",
            "Effective use of EdTech (LMS, simulations, virtual labs), internet reliability, hardware/platform quality.",
            "✓", "Circuit simulation software was integrated into FA1 to verify Thevenin/Norton and RLC responses."
        ),
        CQIIndicator(
            "III. Course Design and Resources Factors", 5,
            "5. Course Load and Difficulty",
            "Appropriateness of workload, perceived difficulty relative to student preparation.",
            "✓", "4 summative quizzes, 2 term exams, and formative group activities provided balanced assessment."
        ),
        CQIIndicator(
            "IV. Institutional and External Factors", 1,
            "1. Institutional Support",
            "Faculty development, tech support, student services, library resources.",
            "✓", "Adequate library and institutional LMS support provided."
        ),
        CQIIndicator(
            "IV. Institutional and External Factors", 2,
            "2. Curriculum Design and Program Quality",
            "Overall curriculum coherence, theory/practice integration, interdisciplinary skills, program responsiveness.",
            "✓", "Curriculum sequence effectively links Calculus/Physics prerequisites to Electrical Circuits 1."
        ),
        CQIIndicator(
            "IV. Institutional and External Factors", 3,
            "3. Socioeconomic Factors",
            "Impact of socioeconomic status on achievement and resource access.",
            "✓", "Open-source / accessible simulation tools and digital handouts ensured equitable access."
        ),
        CQIIndicator(
            "IV. Institutional and External Factors", 4,
            "4. External Context/Unforeseen Circumstances",
            "Impact of global crises, rapid industry changes on curriculum.",
            "✓", "Flexible asynchronous/online contingency provisions were in place per syllabus guidelines."
        ),
    ]


@dataclass
class SyllabusBlueprint:
    metadata: CourseMetadata = field(default_factory=CourseMetadata)
    terms: List[TermConfig] = field(default_factory=lambda: [
        TermConfig(term_name="Midterm", weight_pct=50.0),
        TermConfig(term_name="Finals", weight_pct=50.0),
    ])
    course_outcomes: List[CourseOutcome] = field(default_factory=list)
    categories: List[AssessmentCategory] = field(default_factory=list)
    students: List[StudentRecord] = field(default_factory=list)
    cqi_plan: CQIPlan = field(default_factory=lambda: CQIPlan(indicators=get_default_cqi_indicators()))
    parser_notes: List[str] = field(default_factory=list)
    raw_text_preview: str = ""
    # Syllabus rubrics built in the Rubric Builder. Each rubric is a dict:
    # {rubric_id, title, used_for, clo_ids:[...], levels:[{label, points}],
    #  criteria:[{name, weight_pct, descriptors:[text per level]}], notes}
    rubrics: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SyllabusBlueprint":
        meta_data = data.get("metadata", {})
        metadata = CourseMetadata(**{k: v for k, v in meta_data.items() if k in CourseMetadata.__dataclass_fields__})

        terms = [
            TermConfig(**{k: v for k, v in t.items() if k in TermConfig.__dataclass_fields__})
            for t in data.get("terms", [])
        ]
        if not terms:
            terms = [
                TermConfig(term_name="Midterm", weight_pct=50.0),
                TermConfig(term_name="Finals", weight_pct=50.0),
            ]

        course_outcomes = []
        for co in data.get("course_outcomes", []):
            co_dict = dict(co)
            if "co_id" not in co_dict and "code" in co_dict:
                co_dict["co_id"] = co_dict["code"]
            filtered = {k: v for k, v in co_dict.items() if k in CourseOutcome.__dataclass_fields__}
            if "co_id" in filtered:
                course_outcomes.append(CourseOutcome(**filtered))

        categories = []
        for cat in data.get("categories", []):
            items = [
                AssessmentItem(**{k: v for k, v in it.items() if k in AssessmentItem.__dataclass_fields__})
                for it in cat.get("items", [])
            ]
            cat_filtered = {k: v for k, v in cat.items() if k in AssessmentCategory.__dataclass_fields__ and k != "items"}
            categories.append(AssessmentCategory(**cat_filtered, items=items))

        students = [
            StudentRecord(**{k: v for k, v in st.items() if k in StudentRecord.__dataclass_fields__})
            for st in data.get("students", [])
        ]

        cqi_raw = data.get("cqi_plan", {})
        if cqi_raw:
            inds = [
                CQIIndicator(**{k: v for k, v in ind.items() if k in CQIIndicator.__dataclass_fields__})
                for ind in cqi_raw.get("indicators", [])
            ]
            if not inds:
                inds = get_default_cqi_indicators()
            cqi_plan = CQIPlan(
                date_of_evaluation=cqi_raw.get("date_of_evaluation", "October 2026"),
                indicators=inds,
                key_strengths=cqi_raw.get("key_strengths", CQIPlan.key_strengths),
                areas_for_improvement=cqi_raw.get("areas_for_improvement", CQIPlan.areas_for_improvement),
                action_plan=cqi_raw.get("action_plan", CQIPlan.action_plan),
            )
        else:
            cqi_plan = CQIPlan(indicators=get_default_cqi_indicators())

        return cls(
            metadata=metadata,
            terms=terms,
            course_outcomes=course_outcomes,
            categories=categories,
            students=students,
            cqi_plan=cqi_plan,
            parser_notes=data.get("parser_notes", []),
            raw_text_preview=data.get("raw_text_preview", ""),
            rubrics=[r for r in (data.get("rubrics") or []) if isinstance(r, dict)],
        )


def build_transmutation_table(passing_pct: float = 75.0) -> List[Dict]:
    """
    Returns the official USeP Base-50 Grade Equivalence Table (matching EE 211.pdf & Math 211.xlsm)
    when passing_pct == 75 (or custom cutoffs if adjusted by faculty).
    < 75 = 5.00 | 75-76 = 3.00 | 77-79 = 2.75 | 80-82 = 2.50 | 83-85 = 2.25
    86-88 = 2.00 | 89-91 = 1.75 | 92-94 = 1.50 | 95-97 = 1.25 | 98-100 = 1.00
    """
    passing_pct = float(passing_pct or 75.0)
    if abs(passing_pct - 75.0) < 0.5:
        return [
            {"min_pct": 0.0, "max_pct": 49.99, "grade": "UW", "remarks": "FAILED"},
            {"min_pct": 50.0, "max_pct": 74.99, "grade": 5.00, "remarks": "FAILED"},
            {"min_pct": 75.0, "max_pct": 76.99, "grade": 3.00, "remarks": "PASSED"},
            {"min_pct": 77.0, "max_pct": 79.99, "grade": 2.75, "remarks": "PASSED"},
            {"min_pct": 80.0, "max_pct": 82.99, "grade": 2.50, "remarks": "PASSED"},
            {"min_pct": 83.0, "max_pct": 85.99, "grade": 2.25, "remarks": "PASSED"},
            {"min_pct": 86.0, "max_pct": 88.99, "grade": 2.00, "remarks": "PASSED"},
            {"min_pct": 89.0, "max_pct": 91.99, "grade": 1.75, "remarks": "PASSED"},
            {"min_pct": 92.0, "max_pct": 94.99, "grade": 1.50, "remarks": "PASSED"},
            {"min_pct": 95.0, "max_pct": 97.99, "grade": 1.25, "remarks": "PASSED"},
            {"min_pct": 98.0, "max_pct": 100.00, "grade": 1.00, "remarks": "PASSED"},
        ]

    span = 100.0 - passing_pct
    grades = [3.00, 2.75, 2.50, 2.25, 2.00, 1.75, 1.50, 1.25, 1.00]
    step = span / len(grades)
    table = [
        {"min_pct": 0.0, "max_pct": 49.99, "grade": "UW", "remarks": "FAILED"},
        {"min_pct": 50.0, "max_pct": round(passing_pct - 0.01, 2), "grade": 5.00, "remarks": "FAILED"},
    ]
    for i, g in enumerate(grades):
        low = round(passing_pct + i * step, 2) if i > 0 else round(passing_pct, 2)
        high = round(passing_pct + (i + 1) * step - 0.01, 2) if i < len(grades) - 1 else 100.00
        table.append({"min_pct": low, "max_pct": high, "grade": g, "remarks": "PASSED"})
    return table
