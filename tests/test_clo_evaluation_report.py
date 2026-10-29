"""
Unit and integration tests for official FM-USeP-MID-10 Course Learning Outcome Evaluation Result report generation:
  - clo_evaluation_excel_generator.py (Excel workbook strictly matching FM-USeP-MID-10 sample)
  - clo_report_pdf_generator.py (PDF document strictly matching FM-USeP-MID-10 controlled form)
  - app.py endpoints (POST /api/export-clo-report-excel, POST /api/export-clo-report-pdf, GET /api/courses/<id>/export-clo-report-excel, GET /api/courses/<id>/export-clo-report-pdf)
"""

import io
import os
import unittest
import openpyxl

from app import app
import auth
import courses_store
from models import SyllabusBlueprint, AssessmentCategory, AssessmentItem, CourseOutcome
from clo_evaluation_excel_generator import generate_clo_evaluation_excel_bytes
from clo_report_pdf_generator import generate_clo_report_pdf_bytes


class TestCloEvaluationReport(unittest.TestCase):
    def setUp(self):
        self.bp = SyllabusBlueprint()
        self.bp.metadata.faculty_name = "ENGR. JUAN DELA CRUZ, PECE"
        self.bp.metadata.course_code = "EE 211"
        self.bp.metadata.course_title = "Electrical Circuits 1"
        self.bp.metadata.course_description = "Fundamental principles of electric circuits, DC analysis, Kirchhoff's laws, nodal and mesh analysis."
        self.bp.metadata.credit_units = "3.0 Units - Lecture"
        self.bp.metadata.semester_ay = "1st Semester, AY 2025-2026"
        self.bp.metadata.program_name = "Bachelor of Science in Electrical Engineering"
        self.bp.metadata.academic_unit = "College of Engineering"
        self.bp.metadata.program_head = "ENGR. MARIA SANTOS, MSEE"

        self.bp.course_outcomes = [
            CourseOutcome(co_id="CLO1", description="Analyze DC resistive circuits using basic laws."),
            CourseOutcome(co_id="CLO2", description="Apply network theorems to linear electrical networks."),
            CourseOutcome(co_id="CLO3", description="Evaluate transient response of RL and RC circuits."),
            CourseOutcome(co_id="CLO4", description="Conduct laboratory experiments and simulations."),
            CourseOutcome(co_id="CLO5", description="Demonstrate professional engineering ethics and communication."),
        ]

        self.bp.metadata.course_assessment_plan = [
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

        self.bp.categories = [
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

        self.bp.students = [
            {"student_id": "2023-00001", "name": "Cruz, Juan", "scores": {"CP1": 90, "Q1": 45, "Q2": 40, "Q3": 42, "GP1": 85, "GP2": 88, "FE1": 42, "FE2": 45, "FE3": 40, "FE4": 44}},
            {"student_id": "2023-00002", "name": "Santos, Maria", "scores": {"CP1": 85, "Q1": 40, "Q2": 38, "Q3": 40, "GP1": 80, "GP2": 82, "FE1": 40, "FE2": 42, "FE3": 38, "FE4": 40}}
        ]

        self.app = app
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"

    def test_clo_excel_generator_structure_and_formulas(self):
        """Validates that the generated Excel strictly matches FM-USeP-MID-10."""
        excel_bytes = generate_clo_evaluation_excel_bytes(self.bp)
        self.assertGreater(len(excel_bytes), 5000, "Workbook bytes should be non-trivial")

        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=False)
        ws = wb.active
        self.assertEqual(ws.title, "Sheet1")

        # 1. Document Control Box (F2:G6)
        self.assertEqual(ws["F2"].value, "Form No.")
        self.assertEqual(ws["G2"].value, "FM-USeP-MID-10")
        self.assertEqual(ws["F3"].value, "Issue Status")
        self.assertEqual(ws["G3"].value, "01")
        self.assertEqual(ws["F4"].value, "Revision No.")
        self.assertEqual(ws["G4"].value, "00")
        self.assertEqual(ws["F5"].value, "Date Effective")
        self.assertEqual(ws["G5"].value, "18 August 2026")
        self.assertEqual(ws["F6"].value, "Approved by")
        self.assertEqual(ws["G6"].value, "President")

        # 2. Document Title
        self.assertEqual(ws["A7"].value, "COURSE LEARNING OUTCOME EVALUATION RESULT")

        # 3. 5 Basic Details retrieved from syllabus creation
        self.assertEqual(ws["A9"].value, "Name of Faculty:")
        self.assertIn("Dela Cruz", str(ws["C9"].value))

        self.assertEqual(ws["A10"].value, "Course Title, Description and Units:")
        c10_val = str(ws["C10"].value)
        self.assertIn("EE 211", c10_val)
        self.assertIn("Electrical Circuits 1", c10_val)
        self.assertIn("3 Units", c10_val)
        self.assertIn("Fundamental principles of electric circuits", c10_val)

        self.assertEqual(ws["A11"].value, "Semester and Academic Year:")
        self.assertEqual(ws["C11"].value, "1st Semester, AY 2025-2026")

        self.assertEqual(ws["A12"].value, "Program:")
        self.assertEqual(ws["C12"].value, "Bachelor of Science in Electrical Engineering")

        self.assertEqual(ws["A13"].value, "Academic Unit:")
        self.assertEqual(ws["C13"].value, "College of Engineering")

        # 4. Table 1: Course Assessment Plan
        self.assertEqual(ws["A15"].value, "COURSE ASSESSMENT PLAN (As declared in the Syllabus)")
        self.assertEqual(ws["A16"].value, "Assessment Component")
        self.assertEqual(ws["C16"].value, "Course Assessment Plan")
        self.assertEqual(ws["C17"].value, "CLO1")
        self.assertEqual(ws["G17"].value, "CLO5")

        # Dynamic height check
        self.assertGreaterEqual(ws.row_dimensions[18].height, 20.0)

        # 5. Table 2: Course Learning Outcome Evaluation Result
        self.assertEqual(ws["A23"].value, "COURSE LEARNING OUTCOME EVALUATION RESULT (Based on Class Record)")
        self.assertEqual(ws["A24"].value, "Assessment Component")
        self.assertEqual(ws["C24"].value, "Course Assessment Plan")
        self.assertEqual(ws["C25"].value, "CLO1")

        # Check attainment formatted as percentage
        self.assertEqual(ws["C27"].number_format, "0%")

        # Check Row 30 weighted average formula
        self.assertEqual(ws["A30"].value, "Overall (Weighted Average %)")
        formula_c30 = str(ws["C30"].value)
        self.assertTrue(formula_c30.startswith("="), f"Formula expected, got {formula_c30}")
        self.assertIn("C27*(20/70)", formula_c30)
        self.assertIn("C29*(50/70)", formula_c30)

        # Check Note
        self.assertIn("Note: Weighted Average is computed as", str(ws["A31"].value))

        # Check Signatories
        self.assertEqual(ws["A33"].value, "Prepared by:")
        self.assertEqual(ws["D33"].value, "Reviewed and Noted by:")
        self.assertIn("DELA CRUZ", str(ws["A35"].value))
        self.assertIn("MARIA SANTOS", str(ws["D35"].value))

        # Check Actions Needed
        self.assertEqual(ws["A39"].value, "Actions Needed:")
        self.assertEqual(ws["D39"].value, "Actions Needed:")

        # Check Page Setup: Fit to 1 page wide, portrait, A4
        self.assertTrue(ws.sheet_properties.pageSetUpPr.fitToPage)
        self.assertEqual(ws.page_setup.orientation, ws.ORIENTATION_PORTRAIT)
        self.assertEqual(str(ws.page_setup.paperSize), "9")

    def test_clo_pdf_generator_conformance(self):
        """Validates that the generated PDF conforms to FM-USeP-MID-10 layout and details."""
        pdf_bytes = generate_clo_report_pdf_bytes(self.bp)
        self.assertGreater(len(pdf_bytes), 5000, "PDF bytes should be non-empty and valid")
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Should have valid PDF header")

    def test_api_export_clo_report_excel_and_pdf(self):
        """Validates API endpoints for exporting CLO reports."""
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"

        # 1. POST /api/export-clo-report-excel
        res_excel = self.client.post(
            "/api/export-clo-report-excel",
            json={"blueprint": self.bp.to_dict()}
        )
        self.assertEqual(res_excel.status_code, 200)
        self.assertEqual(res_excel.mimetype, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertIn("FM-USeP-MID-10.xlsx", res_excel.headers.get("Content-Disposition", ""))

        # 2. POST /api/export-clo-report-pdf
        res_pdf = self.client.post(
            "/api/export-clo-report-pdf",
            json={"blueprint": self.bp.to_dict()}
        )
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, "application/pdf")
        self.assertIn("FM-USeP-MID-10.pdf", res_pdf.headers.get("Content-Disposition", ""))

    def test_course_get_clo_report_endpoints(self):
        """Validates GET /api/courses/<id>/export-clo-report-excel and /api/courses/<id>/export-clo-report-pdf."""
        course_id = "test_course_mid10"
        courses_store.save_course("admin", course_id, {
            "course_id": course_id,
            "course_code": "EE 211",
            "course_title": "Electrical Circuits 1",
            "course_description": "Fundamental principles of electric circuits, DC analysis, Kirchhoff's laws.",
            "credit_units": "3.0 Units - Lecture",
            "semester_ay": "1st Semester, AY 2025-2026",
            "program_name": "Bachelor of Science in Electrical Engineering",
            "academic_unit": "College of Engineering",
            "faculty_name": "Engr. Juan Dela Cruz, PECE",
            "program_head": "Engr. Maria Santos, MSEE",
            "blueprint": self.bp.to_dict()
        })

        # Test GET Excel
        res_excel = self.client.get(f"/api/courses/{course_id}/export-clo-report-excel")
        self.assertEqual(res_excel.status_code, 200)
        self.assertEqual(res_excel.mimetype, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Test GET PDF
        res_pdf = self.client.get(f"/api/courses/{course_id}/export-clo-report-pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, "application/pdf")

        # Cleanup
        try:
            courses_store.delete_course(course_id)
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
