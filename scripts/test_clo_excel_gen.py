import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import openpyxl
from models import SyllabusBlueprint, AssessmentCategory, AssessmentItem, CourseOutcome
from clo_evaluation_excel_generator import generate_clo_evaluation_excel_bytes
from clo_report_pdf_generator import generate_clo_report_pdf_bytes

bp = SyllabusBlueprint()
bp.metadata.faculty_name = "ENGR. JUAN DELA CRUZ, PECE"
bp.metadata.course_code = "EE 211"
bp.metadata.course_title = "Electrical Circuits 1"
bp.metadata.course_description = "Fundamental principles of electric circuits, DC analysis, Kirchhoff's laws, nodal and mesh analysis."
bp.metadata.credit_units = "3.0 Units - Lecture"
bp.metadata.semester_ay = "1st Semester, AY 2025-2026"
bp.metadata.program_name = "Bachelor of Science in Electrical Engineering"
bp.metadata.academic_unit = "College of Engineering"
bp.metadata.program_head = "ENGR. MARIA SANTOS, MSEE"

bp.course_outcomes = [
    CourseOutcome(co_id="CLO1", description="Analyze DC resistive circuits using basic laws."),
    CourseOutcome(co_id="CLO2", description="Apply network theorems to linear electrical networks."),
    CourseOutcome(co_id="CLO3", description="Evaluate transient response of RL and RC circuits."),
    CourseOutcome(co_id="CLO4", description="Conduct laboratory experiments and simulations."),
    CourseOutcome(co_id="CLO5", description="Demonstrate professional engineering ethics and communication."),
]

bp.metadata.course_assessment_plan = [
    {
        "code": "SA1",
        "component_name": "Class Participation (10%)",
        "weight_pct": 10,
        "clo_plans": {"CLO5": "Participation (Rubric)"}
    },
    {
        "code": "SA2",
        "component_name": "Individual Class Test (20%)",
        "weight_pct": 20,
        "clo_plans": {"CLO1": "MCQ (1 - 10)", "CLO2": "Essay (Q1 - Q2)", "CLO3": "Essay (Q3)"}
    },
    {
        "code": "SA3",
        "component_name": "Group Project (20%)",
        "weight_pct": 20,
        "clo_plans": {"CLO4": "Research (Rubric)", "CLO5": "Research (Rubric)"}
    },
    {
        "code": "SA4",
        "component_name": "Final Examination (50%)",
        "weight_pct": 50,
        "clo_plans": {"CLO1": "Written Test (Q1 to Q2)", "CLO2": "Written Test (Q3 to Q5)", "CLO3": "Written Test (Q6 to Q8)", "CLO4": "Written Test (Q9 to Q10)"}
    }
]

bp.categories = [
    AssessmentCategory(category_id="CAT_SA1", name="Class Participation", assessment_code="SA1", assessment_type="SA", weight_pct=10, term="Midterm", items=[
        AssessmentItem(item_id="CP1", name="Oral Participation", co_id="CLO5", max_score=100, weight_pct=10)
    ]),
    AssessmentCategory(category_id="CAT_SA2", name="Individual Class Test", assessment_code="SA2", assessment_type="SA", weight_pct=20, term="Midterm", items=[
        AssessmentItem(item_id="Q1", name="Quiz 1", co_id="CLO1", max_score=50, weight_pct=10),
        AssessmentItem(item_id="Q2", name="Quiz 2", co_id="CLO2", max_score=50, weight_pct=5),
        AssessmentItem(item_id="Q3", name="Quiz 3", co_id="CLO3", max_score=50, weight_pct=5),
    ]),
    AssessmentCategory(category_id="CAT_SA3", name="Group Project", assessment_code="SA3", assessment_type="SA", weight_pct=20, term="Final", items=[
        AssessmentItem(item_id="GP1", name="Design Project", co_id="CLO4", max_score=100, weight_pct=10),
        AssessmentItem(item_id="GP2", name="Project Ethics Presentation", co_id="CLO5", max_score=100, weight_pct=10),
    ]),
    AssessmentCategory(category_id="CAT_SA4", name="Final Examination", assessment_code="SA4", assessment_type="SA", weight_pct=50, term="Final", items=[
        AssessmentItem(item_id="FE1", name="Final Exam Part A", co_id="CLO1", max_score=50, weight_pct=15),
        AssessmentItem(item_id="FE2", name="Final Exam Part B", co_id="CLO2", max_score=50, weight_pct=15),
        AssessmentItem(item_id="FE3", name="Final Exam Part C", co_id="CLO3", max_score=50, weight_pct=10),
        AssessmentItem(item_id="FE4", name="Final Exam Part D", co_id="CLO4", max_score=50, weight_pct=10),
    ])
]

bp.students = [
    {"student_id": "2023-00001", "name": "Cruz, Juan", "scores": {}},
    {"student_id": "2023-00002", "name": "Santos, Maria", "scores": {}}
]

# 1. Test Excel Generation
excel_bytes = generate_clo_evaluation_excel_bytes(bp)
print(f"Generated Excel file size: {len(excel_bytes)} bytes")

# 2. Test PDF Generation
pdf_bytes = generate_clo_report_pdf_bytes(bp)
print(f"Generated PDF file size: {len(pdf_bytes)} bytes")
assert len(pdf_bytes) > 1000, "PDF bytes should be non-empty and valid"

print("\nAll generator tests passed successfully!")
