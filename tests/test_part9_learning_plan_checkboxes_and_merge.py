# tests/test_part9_learning_plan_checkboxes_and_merge.py
import unittest
import json
import io
import pypdf
from app import app
import auth
import models
import sample_syllabus
import syllabus_pdf_generator
import courses_store

class TestPart9LearningPlanCheckboxesAndMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()
        auth.ensure_default_admin()
        users = auth._load_users()
        cls.admin_user = list(users.keys())[0]

    def test_default_learning_plan_merge_flags(self):
        """Verify default learning plan table contains proper merge_assessment_with_prev flags matching EE 211."""
        table = models.get_sample_ee211_learning_plan_table()
        self.assertGreaterEqual(len(table), 10)

        # Orientation: not merged, N/A assessment
        self.assertFalse(table[0].get("merge_assessment_with_prev"))
        self.assertIn("N/A", table[0].get("assessment_activities", ""))

        # Midterm topics 1, 2, 3: topics 2 and 3 are merged with topic 1
        self.assertFalse(table[1].get("merge_assessment_with_prev"))
        self.assertTrue(table[2].get("merge_assessment_with_prev"))
        self.assertTrue(table[3].get("merge_assessment_with_prev"))
        self.assertIn("FA1", table[1].get("assessment_activities", ""))
        self.assertIn("SA1", table[1].get("assessment_activities", ""))

        # Midterm exam: independent
        self.assertFalse(table[4].get("merge_assessment_with_prev"))
        self.assertIn("SA2", table[4].get("assessment_activities", ""))

        # Final term topics 5, 6, 7, 8: topics 6, 7, 8 are merged with topic 5
        self.assertFalse(table[5].get("merge_assessment_with_prev"))
        self.assertTrue(table[6].get("merge_assessment_with_prev"))
        self.assertTrue(table[7].get("merge_assessment_with_prev"))
        self.assertTrue(table[8].get("merge_assessment_with_prev"))

        # Final exam: independent
        self.assertFalse(table[9].get("merge_assessment_with_prev"))
        self.assertIn("SA2", table[9].get("assessment_activities", ""))

    def test_pdf_generation_with_merged_learning_plan(self):
        """Verify PDF generator handles merged learning plan rows using rowspan without errors."""
        bp = sample_syllabus.get_default_blueprint()
        pdf_bytes = syllabus_pdf_generator.generate_usep_syllabus_pdf(bp)
        self.assertIsInstance(pdf_bytes, (bytes, bytearray))
        self.assertGreater(len(pdf_bytes), 10000)

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        full_text = "".join(page.extract_text() for page in reader.pages)
        self.assertIn("PART IX. LEARNING PLAN", full_text)
        self.assertIn("Intended Learning Outcomes", full_text)
        self.assertIn("Course Learning Outcome", full_text)
        self.assertIn("Assessment Activities", full_text)

    def test_pdf_generation_with_unmerged_learning_plan(self):
        """Verify PDF generator works when all topics are unmerged."""
        bp = sample_syllabus.get_default_blueprint()
        for r in bp.metadata.learning_plan_table:
            r["merge_assessment_with_prev"] = False
        pdf_bytes = syllabus_pdf_generator.generate_usep_syllabus_pdf(bp)
        self.assertGreater(len(pdf_bytes), 10000)

    def test_web_ui_part9_elements(self):
        """Verify that index.html contains all required Part IX UI components, CSS, and JS handlers."""
        with self.client.session_transaction() as sess:
            sess["username"] = self.admin_user

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # CSS classes
        self.assertIn(".lp-clo-chip", html)
        self.assertIn(".lp-act-chip", html)

        # JS functions
        self.assertIn("function parseRowClos", html)
        self.assertIn("function toggleLearningPlanRowClo", html)
        self.assertIn("function parseRowActivities", html)
        self.assertIn("function toggleLearningPlanRowActivity", html)
        self.assertIn("function mergeLearningPlanAssessmentWithPrev", html)
        self.assertIn("function unmergeLearningPlanAssessment", html)
        self.assertIn("function syncMergedAssessmentsFromLead", html)

        # Table headers
        self.assertIn("Course Learning Outcome (CLO)", html)
        self.assertIn("Assessment Activities", html)
        self.assertIn("Actions", html)

    def test_course_persistence_preserves_merged_learning_plan(self):
        """Verify that saving and loading course blueprint preserves merge_assessment_with_prev flags."""
        c_info = courses_store.create_course(self.admin_user, course_code="TEST 901", course_title="Test Course")
        course_id = c_info["id"]

        bp = sample_syllabus.get_default_blueprint()
        bp.metadata.course_code = "TEST 901"
        bp.metadata.learning_plan_table = [
            {"topics": "Orientation", "clo": "", "time_frame": "1 hour", "tla": "Lecture", "required_reading": "", "assessment_activities": "• N/A", "merge_assessment_with_prev": False},
            {"topics": "Module 1", "clo": "CLO1", "time_frame": "4 hours", "tla": "Lecture", "required_reading": "", "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz", "merge_assessment_with_prev": False},
            {"topics": "Module 2", "clo": "CLO1", "time_frame": "4 hours", "tla": "Lecture", "required_reading": "", "assessment_activities": "• FA1 – Group Activity\n• SA1 – Quiz", "merge_assessment_with_prev": True},
        ]
        try:
            courses_store.save_course(self.admin_user, course_id, {"blueprint": bp.to_dict()})
            saved_doc = courses_store.get_course(self.admin_user, course_id)
            saved_bp = saved_doc["blueprint"]
            lp = saved_bp["metadata"]["learning_plan_table"]
            self.assertEqual(len(lp), 3)
            self.assertFalse(lp[0].get("merge_assessment_with_prev"))
            self.assertFalse(lp[1].get("merge_assessment_with_prev"))
            self.assertTrue(lp[2].get("merge_assessment_with_prev"))
            self.assertEqual(lp[2].get("assessment_activities"), lp[1].get("assessment_activities"))
        finally:
            courses_store.delete_course(self.admin_user, course_id)

if __name__ == "__main__":
    unittest.main()
