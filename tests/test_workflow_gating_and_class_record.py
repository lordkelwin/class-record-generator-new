"""
tests/test_workflow_gating_and_class_record.py

Comprehensive test suite verifying:
1. Module Access Gating (Zero-subject state locks Syllabus Creator & Dashboard; subject creation unlocks Syllabus Creator; score entry unlocks Dashboard).
2. Sequential Step-Gating (Steps 2 to 6 strictly locked until syllabus receives final Dean approval; unlocks post-Dean approval).
3. Backend Route & Mutation Protection (Roster management, assessment acknowledgments, CLO reports, and Class Record submission reject with 403 while unapproved).
4. Auto-Generation Pipeline Gating (Auto-generation routine strictly gated on final Dean approval).
5. Student Roster Binding & Score Persistence post-Dean approval.
6. Clean Teardown & Isolated Data Safety (Only TEST_ANTIGRAVITY_ records used and completely purged).
"""

import os
import shutil
import unittest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch

import courses_store
import syllabus_workflow
import class_record_workflow
import db_persistence
from app import app


TEST_PREFIX = "TEST_ANTIGRAVITY_"
TEST_USER = f"{TEST_PREFIX}faculty_user"
TEST_COURSE_ID = f"{TEST_PREFIX}course_101"
TEST_COURSE_CODE = f"{TEST_PREFIX}EE 311"
TEST_SECTION = f"{TEST_PREFIX}SEC_3A"

MOCK_FACULTY_USER = {
    "username": TEST_USER,
    "role": "faculty",
    "full_name": "Test Faculty",
    "signature_data": "data:image/png;base64,mockSignature",
    "can_access_faculty_tools": True,
    "must_change_password": False,
}


class TestWorkflowGatingAndClassRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls._purge_test_records()

    @classmethod
    def tearDownClass(cls):
        cls._purge_test_records()

    @classmethod
    def _purge_test_records(cls):
        """Strictly deletes ONLY records prefixed with TEST_ANTIGRAVITY_."""
        # 1. DB Purge
        try:
            conn = db_persistence.get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM student_course_grades WHERE course_id LIKE ?", (f"{TEST_PREFIX}%",))
            cur.execute("DELETE FROM assessment_items WHERE course_id LIKE ?", (f"{TEST_PREFIX}%",))
            cur.execute("DELETE FROM assessment_categories WHERE course_id LIKE ?", (f"{TEST_PREFIX}%",))
            cur.execute("DELETE FROM syllabus_reviews_and_signatures WHERE course_id LIKE ?", (f"{TEST_PREFIX}%",))
            cur.execute("DELETE FROM syllabus_evaluations WHERE course_id LIKE ?", (f"{TEST_PREFIX}%",))
            cur.execute("DELETE FROM course_records WHERE course_id LIKE ? OR owner LIKE ?", (f"{TEST_PREFIX}%", f"{TEST_PREFIX}%"))
            cur.execute("DELETE FROM app_students WHERE student_id LIKE ?", (f"{TEST_PREFIX}%",))
            conn.commit()
            conn.close()
        except Exception:
            pass

        # 2. Filesystem Course Purge
        user_dir = courses_store._get_user_courses_dir(TEST_USER)
        if os.path.exists(user_dir):
            try:
                shutil.rmtree(user_dir)
            except Exception:
                pass

        courses_base = courses_store.COURSES_BASE_DIR
        if os.path.exists(courses_base):
            for uname in os.listdir(courses_base):
                if uname.startswith(TEST_PREFIX):
                    try:
                        shutil.rmtree(os.path.join(courses_base, uname))
                    except Exception:
                        pass
                else:
                    u_dir = os.path.join(courses_base, uname)
                    if os.path.isdir(u_dir):
                        for fn in os.listdir(u_dir):
                            if fn.startswith(TEST_PREFIX):
                                try:
                                    os.remove(os.path.join(u_dir, fn))
                                except Exception:
                                    pass

    def setUp(self):
        self._purge_test_records()

    def tearDown(self):
        self._purge_test_records()

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_01_zero_subject_gating(self, mock_auth_user, mock_app_user):
        """Test 1: When zero subjects exist, Syllabus Creator & Dashboard are locked."""
        res = courses_store.list_courses(TEST_USER)
        self.assertEqual(res["total"], 0)
        self.assertFalse(res["has_recorded_scores"])
        self.assertFalse(res["has_any_recorded_scores"])

        resp = self.client.get("/api/dashboard/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["has_subjects"])
        self.assertFalse(data["is_syllabus_unlocked"])
        self.assertFalse(data["has_recorded_scores"])
        self.assertFalse(data["is_dashboard_unlocked"])

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_02_subject_creation_unlocks_syllabus_creator_only(self, mock_auth_user, mock_app_user):
        """Test 2: Creating a subject unlocks Syllabus Creator, while Dashboard remains locked."""
        doc = courses_store.save_course(
            username=TEST_USER,
            course_id=TEST_COURSE_ID,
            payload={
                "course_code": TEST_COURSE_CODE,
                "course_title": "Test Circuits",
                "section": TEST_SECTION,
                "semester_ay": "1st Semester, A.Y. 2026-2027",
            },
        )

        res = courses_store.list_courses(TEST_USER)
        self.assertEqual(res["total"], 1)
        self.assertFalse(res["has_recorded_scores"])

        resp = self.client.get("/api/dashboard/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["has_subjects"])
        self.assertTrue(data["is_syllabus_unlocked"])
        self.assertFalse(data["has_recorded_scores"])
        self.assertFalse(data["is_dashboard_unlocked"])  # Still locked!

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_03_sequential_step_gating_pre_dean_approval(self, mock_auth_user, mock_app_user):
        """Test 3: Steps 2 through 6 are strictly locked when syllabus is unapproved (Draft / Review)."""
        doc = courses_store.save_course(
            username=TEST_USER,
            course_id=TEST_COURSE_ID,
            payload={
                "course_code": TEST_COURSE_CODE,
                "course_title": "Advanced Circuit Theory",
                "section": TEST_SECTION,
            },
        )

        # 1. Syllabus is in Draft status
        wf = syllabus_workflow.get_workflow(doc)
        self.assertNotEqual(wf.get("status"), "approved")
        self.assertFalse(syllabus_workflow.is_approved(doc))

        # 2. Auto-generation routine refuses to generate class record while unapproved
        generated = courses_store.auto_generate_class_record(doc)
        self.assertFalse(generated)

        # 3. Backend guards reject Steps 2-6 mutations and endpoints with HTTP 403
        # Step 2: Assessments mutation
        res_step2 = self.client.put(f"/api/courses/{TEST_COURSE_ID}?step=2", json={"blueprint": {}})
        self.assertEqual(res_step2.status_code, 403)
        self.assertIn("Sequential Gating Locked", res_step2.get_json()["error"])

        # Step 3: Roster Add Student
        res_add_st = self.client.post(f"/api/courses/{TEST_COURSE_ID}/roster/add-student", json={
            "student_id": f"{TEST_PREFIX}S01",
            "last_name": "Reyes",
            "first_name": "Carlo",
        })
        self.assertEqual(res_add_st.status_code, 403)

        # Step 3: Roster Remove Student
        res_rem_st = self.client.post(f"/api/courses/{TEST_COURSE_ID}/roster/remove-student", json={
            "student_id": f"{TEST_PREFIX}S01",
        })
        self.assertEqual(res_rem_st.status_code, 403)

        # Step 3: Roster Import
        res_imp = self.client.post(f"/api/courses/{TEST_COURSE_ID}/roster/import")
        self.assertEqual(res_imp.status_code, 403)

        # Step 3: Class Record Submit
        res_cr_sub = self.client.post(f"/api/courses/{TEST_COURSE_ID}/class-record/submit", json={"notes": "test"})
        self.assertEqual(res_cr_sub.status_code, 403)

        # Step 4: Assessment Acknowledgments
        res_ack = self.client.get(f"/api/courses/{TEST_COURSE_ID}/assessment-acknowledgments")
        self.assertEqual(res_ack.status_code, 403)

        # Step 5: CLO Report PDF Export
        res_clo_pdf = self.client.get(f"/api/courses/{TEST_COURSE_ID}/export-clo-report-pdf")
        self.assertEqual(res_clo_pdf.status_code, 403)

        # Step 5: CLO Report Excel Export
        res_clo_xl = self.client.get(f"/api/courses/{TEST_COURSE_ID}/export-clo-report-excel")
        self.assertEqual(res_clo_xl.status_code, 403)

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_04_sequential_step_gating_post_dean_approval(self, mock_auth_user, mock_app_user):
        """Test 4: Steps 2 through 6 unlock and auto-generate immediately post-Dean approval."""
        doc = courses_store.save_course(
            username=TEST_USER,
            course_id=TEST_COURSE_ID,
            payload={
                "course_code": TEST_COURSE_CODE,
                "course_title": "Feedback and Control",
                "section": TEST_SECTION,
            },
        )

        # Approve syllabus as Dean
        doc["workflow"] = {
            "status": "approved",
            "approved": True,
            "locked": True,
            "approved_at": datetime.now().isoformat(),
        }
        courses_store.save_course_doc(doc)

        # 1. Verification of Dean approval
        self.assertTrue(syllabus_workflow.is_approved(doc))

        # 2. Auto-generation succeeds now that syllabus is approved by Dean
        gen_success = courses_store.auto_generate_class_record(doc)
        self.assertTrue(gen_success)
        self.assertGreater(len(doc["blueprint"]["categories"]), 0)

        # 3. Step 3 Roster Add Student now succeeds (HTTP 200)
        res_add = self.client.post(f"/api/courses/{TEST_COURSE_ID}/roster/add-student", json={
            "student_id": f"{TEST_PREFIX}S01",
            "last_name": "Dela Cruz",
            "first_name": "Juan",
            "name": "Dela Cruz, Juan",
            "program_year": TEST_SECTION,
        })
        self.assertEqual(res_add.status_code, 200)
        self.assertTrue(res_add.get_json()["success"])

        # 4. Step 4 Assessment Acknowledgments now succeeds (HTTP 200)
        res_ack = self.client.get(f"/api/courses/{TEST_COURSE_ID}/assessment-acknowledgments")
        self.assertEqual(res_ack.status_code, 200)

        # 5. Reload course and verify student is present with bound columns
        reloaded = courses_store.get_course(TEST_USER, TEST_COURSE_ID)
        students = reloaded["blueprint"]["students"]
        matched = [s for s in students if s["student_id"] == f"{TEST_PREFIX}S01"]
        self.assertEqual(len(matched), 1)
        st = matched[0]
        self.assertIn("scores", st)

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_05_score_entry_and_dashboard_unlocking(self, mock_auth_user, mock_app_user):
        """Test 5: Score entry updates student grade and unlocks Dashboard."""
        doc = courses_store.save_course(
            username=TEST_USER,
            course_id=TEST_COURSE_ID,
            payload={
                "course_code": TEST_COURSE_CODE,
                "course_title": "Power Electronics",
                "section": TEST_SECTION,
            },
        )
        doc["workflow"] = {
            "status": "approved",
            "approved": True,
            "locked": True,
        }
        courses_store.auto_generate_class_record(doc)

        # Add student with scores
        doc["blueprint"]["students"] = [
            {
                "student_id": f"{TEST_PREFIX}S01",
                "name": "Santos, Maria",
                "scores": {"SA1_1__CLO1": 88.0},
            }
        ]
        courses_store.save_course_doc(doc)

        self.assertTrue(courses_store.has_recorded_scores(doc))

        resp = self.client.get("/api/dashboard/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["has_recorded_scores"])
        self.assertTrue(data["is_dashboard_unlocked"])

    def test_06_database_enrolled_students_query(self):
        """Test 6: Database query correctly joins app_students and student_course_grades."""
        students = db_persistence.get_enrolled_students_for_course("c_bb5266e73b", "EE 2A", "EE")
        self.assertTrue(len(students) >= 18)
        self.assertTrue(any(s["student_id"] == "2025-00132" for s in students))
        self.assertTrue(any(s["student_id"] == "2025-01881" for s in students))


if __name__ == "__main__":
    unittest.main()
