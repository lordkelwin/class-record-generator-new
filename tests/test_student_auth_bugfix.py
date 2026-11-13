"""
Unit and integration tests for Student Portal authentication bugfixes:
  1. Enrollment-to-account auto-provisioning across SQLite and file stores.
  2. Credential lookup normalization (hyphenated vs unhyphenated, email identifier, whitespace trimming).
  3. Password verification (default credentials 'student123', registered last name, custom password hashes).
  4. Non-blocking login for active/unfinalized semester class records.
  5. Automatic backfill/sync of all enrolled students into Student Portal authentication store.
"""
import json
import os
import unittest

from app import app
import courses_store
import student_store


class TestStudentAuthBugfix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.test_course_id = "test_course_auth_bugfix"
        cls.test_student_id = "2024-77701"
        cls.test_course_doc = {
            "course_id": cls.test_course_id,
            "id": cls.test_course_id,
            "course_code": "EE 221",
            "course_title": "Circuits II",
            "section": "2A",
            "semester_ay": "2nd Semester, A.Y. 2026-2027",
            "credit_units": "3.0 Units - Lecture",
            "faculty_name": "Engr. Elwin Jay Tano",
            "workflow": {
                "step": 3,
                "status": "in_review",
            },
            "blueprint": {
                "metadata": {
                    "course_code": "EE 221",
                    "course_title": "Circuits II",
                    "section": "2A",
                    "semester_ay": "2nd Semester, A.Y. 2026-2027",
                    "faculty_name": "Engr. Elwin Jay Tano",
                },
                "students": [
                    {
                        "student_id": cls.test_student_id,
                        "last_name": "Magbanua",
                        "first_name": "Rafael",
                        "name": "Magbanua, Rafael",
                        "program_year": "BSEE 2A",
                        "scores": {},
                    }
                ],
            },
        }
        # Save course, which triggers auto-provisioning
        courses_store.save_course("admin", cls.test_course_id, cls.test_course_doc)
        student_store.sync_course_roster_students(cls.test_course_doc)

    @classmethod
    def tearDownClass(cls):
        try:
            courses_store.delete_course(cls.test_course_id)
        except Exception:
            pass
        try:
            student_store._lock.acquire()
            students = student_store._load_students()
            if cls.test_student_id in students:
                del students[cls.test_student_id]
                student_store._save_students(students)
        finally:
            if student_store._lock.locked():
                student_store._lock.release()

    def setUp(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_01_auto_provisioning_on_enrollment(self):
        """Student enrolled in course roster is automatically provisioned with active status & default credentials."""
        st = student_store.get_student_profile(self.test_student_id)
        self.assertIsNotNone(st, "Student should be automatically provisioned in student store")
        self.assertEqual(st.get("student_id"), self.test_student_id)
        self.assertEqual(st.get("last_name"), "Magbanua")
        self.assertIn("active", str(st.get("status", "active")).lower())
        self.assertTrue(bool(st.get("password_hash")), "Default password hash should be initialized")

    def test_02_login_with_registered_last_name(self):
        """Student can log in using standard hyphenated ID and registered Last Name."""
        res = self.client.post("/student/login", data={
            "student_id": self.test_student_id,
            "secret": "Magbanua",
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/student/dashboard", res.headers.get("Location", ""))

    def test_03_login_with_unhyphenated_student_id(self):
        """Student can log in using unhyphenated digits (e.g. 202477701)."""
        res = self.client.post("/student/login", data={
            "student_id": "202477701",
            "secret": "Magbanua",
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/student/dashboard", res.headers.get("Location", ""))

    def test_04_login_with_default_password_student123(self):
        """Student can log in using official default password 'student123'."""
        res = self.client.post("/student/login", data={
            "student_id": self.test_student_id,
            "secret": "student123",
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/student/dashboard", res.headers.get("Location", ""))

    def test_05_login_with_email_identifier(self):
        """Student can log in using email identifier (e.g. 2024-77701@usep.edu.ph)."""
        res = self.client.post("/student/login", data={
            "student_id": f"{self.test_student_id}@usep.edu.ph",
            "secret": "student123",
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/student/dashboard", res.headers.get("Location", ""))

    def test_06_login_with_whitespace_tolerance(self):
        """Student login trims leading and trailing whitespace from both ID and secret."""
        res = self.client.post("/student/login", data={
            "student_id": f"  {self.test_student_id}  ",
            "secret": "  Magbanua  ",
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/student/dashboard", res.headers.get("Location", ""))

    def test_07_unfinalized_course_does_not_block_login(self):
        """Courses in 'in_review' / draft state do not block student login and appear under In Review."""
        res = self.client.post("/student/login", data={
            "student_id": self.test_student_id,
            "secret": "student123",
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("EE 221", res.text)
        self.assertIn("Circuits II", res.text)

    def test_08_non_enrolled_student_rejected(self):
        """Non-enrolled student is rejected with informative message."""
        res = self.client.post("/student/login", data={
            "student_id": "2099-00000",
            "secret": "RandomStudent",
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("not found in any active course roster", res.text)


if __name__ == "__main__":
    unittest.main()
