"""
Unit and integration tests for the Student Portal and Course Syllabus Acknowledgment workflow:
  - Student authentication (Student ID + Last Name / PIN)
  - Automatic reflection of enrolled courses from class record rosters
  - Student dashboard and course categorization (Pending vs Acknowledged vs In Review)
  - Interactive Electronic Syllabus Acknowledgment submission
  - Generation of FM-USeP-MID-07 Course Syllabus Acknowledgement Form PDF with student signature & timestamp
"""

import io
import json
import os
import unittest

from app import app
import courses_store
import student_store


class TestStudentPortal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a test course with 2 enrolled students and QA approved workflow
        cls.course_id = "test_course_student_portal"
        cls.course_doc = {
            "course_id": cls.course_id,
            "course_code": "EE 312",
            "course_title": "Control Systems Analysis",
            "section": "3A",
            "semester_ay": "1st Semester, AY 2025-2026",
            "credit_units": "3.0 Units - Lecture",
            "faculty_name": "Engr. Elwin Jay Tano",
            "class_schedule": "MWF 09:00 AM - 10:00 AM",
            "workflow": {
                "step": 5,
                "status": "approved",
                "qa_approved_at": "2026-10-29T10:00:00",
                "qa_counter_signed": True,
            },
            "blueprint": {
                "metadata": {
                    "course_code": "EE 312",
                    "course_title": "Control Systems Analysis",
                    "section": "3A",
                    "semester_ay": "1st Semester, AY 2025-2026",
                    "faculty_name": "Engr. Elwin Jay Tano",
                    "credit_units": "3.0 Units - Lecture",
                },
                "course_outcomes": [
                    {"co_id": "CLO1", "description": "Formulate mathematical models of physical control systems."}
                ],
                "categories": [],
                "students": [
                    {
                        "student_id": "2024-99001",
                        "last_name": "Bautista",
                        "first_name": "Carlos",
                        "program_year": "BSEE 3A",
                        "scores": {}
                    },
                    {
                        "student_id": "2024-99002",
                        "last_name": "Mercado",
                        "first_name": "Andrea",
                        "program_year": "BSEE 3A",
                        "scores": {}
                    }
                ]
            },
            "student_acknowledgments": []
        }
        courses_store.save_course("admin", cls.course_id, cls.course_doc)

    @classmethod
    def tearDownClass(cls):
        try:
            courses_store.delete_course(cls.course_id)
        except Exception:
            pass

    def setUp(self):
        self.client = app.test_client()
        doc = courses_store.find_course(self.course_id)
        if doc:
            doc["student_acknowledgments"] = []
            if "workflow" in doc and isinstance(doc["workflow"], dict):
                doc["workflow"]["student_acknowledgments"] = []
            courses_store.save_course_doc(doc)

    def test_student_discovery_from_roster(self):
        """Item: Enrolled students are automatically discoverable by Student ID across course rosters."""
        st = student_store.find_student_in_course_rosters("2024-99001")
        self.assertIsNotNone(st, "Enrolled student 2024-99001 should be found across course rosters")
        self.assertEqual(st["last_name"], "Bautista")
        self.assertIn("Carlos", st["full_name"])

    def test_student_login_success(self):
        """Item: Student can log in using Student ID and registered Last Name."""
        # 1. Login with valid Student ID and Last Name
        res = self.client.post("/student/login", data={
            "student_id": "2024-99001",
            "secret": "Bautista"
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertIn("/student/dashboard", res.headers.get("Location", ""))

    def test_student_login_invalid(self):
        """Item: Non-enrolled student or incorrect verification is rejected."""
        res = self.client.post("/student/login", data={
            "student_id": "9999-99999",
            "secret": "Nonexistent"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn("not found in any active course roster", res.text)

    def test_student_dashboard_and_auto_reflected_courses(self):
        """Item: Enrolled subjects auto-reflect on the student dashboard."""
        with self.client.session_transaction() as sess:
            sess["username"] = "2024-99001"
            sess["student_id"] = "2024-99001"
            sess["student_name"] = "Carlos Bautista"
            sess["role"] = "student"

        # 1. GET dashboard page
        res = self.client.get("/student/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn("EE 312", res.text)
        self.assertIn("Control Systems Analysis", res.text)
        self.assertIn("Carlos Bautista", res.text)

        # 2. GET /api/student/courses
        res_api = self.client.get("/api/student/courses")
        self.assertEqual(res_api.status_code, 200)
        data = res_api.get_json()
        pending_codes = [c["course_code"] for c in data["pending"]]
        self.assertIn("EE 312", pending_codes, "EE 312 should auto-reflect in Pending Acknowledgment")

    def test_student_acknowledgment_submission_and_pdf(self):
        """Item: Student submits e-signature, records timestamp, and can download signed FM-USeP-MID-07 PDF."""
        with self.client.session_transaction() as sess:
            sess["username"] = "2024-99001"
            sess["student_id"] = "2024-99001"
            sess["student_name"] = "Carlos Bautista"
            sess["role"] = "student"

        dummy_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        # 1. Sign Acknowledgment via POST /api/student/sign-acknowledgment
        res_sign = self.client.post("/api/student/sign-acknowledgment", json={
            "course_id": self.course_id,
            "signature_data": dummy_sig
        })
        self.assertEqual(res_sign.status_code, 200)
        resp_data = res_sign.get_json()
        self.assertTrue(resp_data.get("success"))

        # 2. Verify course now reflects in acknowledged list
        res_courses = self.client.get("/api/student/courses")
        cdata = res_courses.get_json()
        ack_codes = [c["course_code"] for c in cdata["acknowledged"]]
        self.assertIn("EE 312", ack_codes, "EE 312 should now appear under Acknowledged Syllabi")

        # 3. Download official FM-USeP-MID-07 Syllabus Acknowledgment Form PDF
        res_pdf = self.client.get(f"/api/courses/{self.course_id}/export-acknowledgment-pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, "application/pdf")
        self.assertGreater(len(res_pdf.data), 5000, "PDF should contain official layout with signatures")


if __name__ == "__main__":
    unittest.main()
