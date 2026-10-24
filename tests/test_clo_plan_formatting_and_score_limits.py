# tests/test_clo_plan_formatting_and_score_limits.py
import unittest
import io
import pypdf
from app import app
import auth
import models
import sample_syllabus
import clo_report_pdf_generator

class TestCloPlanFormattingAndScoreLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()
        auth.ensure_default_admin()
        users = auth._load_users()
        cls.admin_user = list(users.keys())[0]

    def test_course_metadata_plan_persistence(self):
        """Verify CourseMetadata supports course_assessment_plan serialization and deserialization."""
        import dataclasses
        meta = models.CourseMetadata(
            course_assessment_plan=[
                {
                    "code": "SA1",
                    "component_name": "Quizzes (30%)",
                    "weight_pct": 30,
                    "clo_plans": {"CLO1": "Objective quiz", "CLO2": "N/A"}
                },
                {
                    "code": "SA2",
                    "component_name": "Term Examination (50%)",
                    "weight_pct": 50,
                    "clo_plans": {"CLO1": "Problem solving", "CLO2": "Short essay"}
                }
            ]
        )
        d = dataclasses.asdict(meta)
        self.assertIn("course_assessment_plan", d)
        self.assertEqual(len(d["course_assessment_plan"]), 2)
        self.assertEqual(d["course_assessment_plan"][0]["component_name"], "Quizzes (30%)")

        # Test within SyllabusBlueprint to_dict and from_dict
        bp = sample_syllabus.get_default_blueprint()
        bp.metadata.course_assessment_plan = meta.course_assessment_plan
        bp_dict = bp.to_dict()
        self.assertIn("course_assessment_plan", bp_dict["metadata"])

        bp_recreated = models.SyllabusBlueprint.from_dict(bp_dict)
        self.assertEqual(len(bp_recreated.metadata.course_assessment_plan), 2)
        self.assertEqual(bp_recreated.metadata.course_assessment_plan[0]["clo_plans"]["CLO1"], "Objective quiz")
        self.assertEqual(bp_recreated.metadata.course_assessment_plan[0]["clo_plans"]["CLO2"], "N/A")

    def test_clo_report_pdf_generation_with_custom_assessment_plan(self):
        """Verify CLO Report PDF generator incorporates the custom/synced course_assessment_plan."""
        bp = sample_syllabus.get_default_blueprint()
        bp.metadata.course_assessment_plan = [
            {
                "code": "SA1",
                "component_name": "Quizzes Custom (30%)",
                "weight_pct": 30,
                "clo_plans": {
                    "CLO1": "Custom Quiz Rubric Description for CLO1",
                    "CLO2": "N/A",
                    "CLO3": "Custom Quiz Rubric Description for CLO3"
                }
            },
            {
                "code": "SA2",
                "component_name": "Final Exam Custom (50%)",
                "weight_pct": 50,
                "clo_plans": {
                    "CLO1": "Final Exam Problem Solving",
                    "CLO2": "Final Exam Short Essay",
                    "CLO3": "N/A"
                }
            }
        ]

        pdf_bytes = clo_report_pdf_generator.generate_clo_report_pdf_bytes(bp)
        self.assertIsInstance(pdf_bytes, (bytes, bytearray))
        self.assertGreater(len(pdf_bytes), 5000)

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        full_text = "".join(page.extract_text() for page in reader.pages)
        self.assertIn("Quizzes Custom (30%)", full_text)
        self.assertIn("Final Exam Custom (50%)", full_text)
        self.assertIn("Course Assessment Plan", full_text)
        self.assertIn("N/A", full_text)

    def test_clo_report_pdf_generation_fallback(self):
        """Verify CLO Report PDF generator falls back gracefully when course_assessment_plan is empty."""
        bp = sample_syllabus.get_default_blueprint()
        bp.metadata.course_assessment_plan = []
        pdf_bytes = clo_report_pdf_generator.generate_clo_report_pdf_bytes(bp)
        self.assertIsInstance(pdf_bytes, (bytes, bytearray))
        self.assertGreater(len(pdf_bytes), 5000)

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        full_text = "".join(page.extract_text() for page in reader.pages)
        self.assertIn("Course Assessment Plan", full_text)

    def test_web_ui_elements_and_formatting_toolbar(self):
        """Verify templates/index.html includes SyllabusFormatter toolbar, styles, and handlers."""
        with self.client.session_transaction() as sess:
            sess["username"] = self.admin_user

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # Formatting Toolbar UI & CSS
        self.assertIn("#syllabusFormattingToolbar", html)
        self.assertIn("sft-btn", html)
        self.assertIn("syl-format-pill-bar", html)
        self.assertIn("SyllabusFormatter", html)
        self.assertIn("toggleBold", html)
        self.assertIn("toggleItalic", html)
        self.assertIn("insertBullet", html)
        self.assertIn("insertNumberedList", html)
        self.assertIn("insertEnDash", html)
        self.assertIn("insertParagraph", html)
        self.assertIn("clearFormatting", html)
        self.assertIn("handleEnterKey", html)

    def test_web_ui_course_assessment_plan_sync_and_edit(self):
        """Verify templates/index.html includes editable and synchronized Course Assessment Plan functions."""
        with self.client.session_transaction() as sess:
            sess["username"] = self.admin_user

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        self.assertIn("ensureCourseAssessmentPlan", html)
        self.assertIn("updateCapComponentName", html)
        self.assertIn("updateCapCellText", html)
        self.assertIn("toggleCapCellNa", html)
        self.assertIn("addCourseAssessmentPlanRow", html)
        self.assertIn("removeCourseAssessmentPlanRow", html)
        self.assertIn("syncCourseAssessmentPlanFromSyllabus", html)
        self.assertIn("Sync from Syllabus", html)
        self.assertIn("+ Add Component", html)

    def test_web_ui_score_input_limiting(self):
        """Verify templates/index.html includes numerical score limits per CLO and clamping logic."""
        with self.client.session_transaction() as sess:
            sess["username"] = self.admin_user

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        self.assertIn("validateAndLimitScoreInput", html)
        self.assertIn("showScoreLimitToast", html)
        self.assertIn("getItemCloMaxScore", html)
        self.assertIn("Score limited to max score of", html)
        self.assertIn("Math.min(itMax, sumItem)", html)

if __name__ == "__main__":
    unittest.main()
