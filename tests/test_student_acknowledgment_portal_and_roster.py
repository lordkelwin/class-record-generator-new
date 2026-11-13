"""
Unit tests for Student Portal Syllabus Acknowledgment, Roster Management, and Comments.
"""

import os
import json
import io
import unittest
from datetime import datetime

import app as flask_app
import student_store
import courses_store


class TestStudentPortalAndRoster(unittest.TestCase):
    def setUp(self):
        self.app = flask_app.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Create a unique test course in QA countersign / student acknowledgment stage
        self.test_course_id = "test_course_ack_portal_unique"
        self.test_username = "admin"
        self.test_student_id = "2026-99001"
        self.test_student_last = "Villanueva"
        self.test_student_first = "Elena"
        self.test_student_full = "Elena Villanueva"

        # Base course doc
        self.course_doc = {
            "id": self.test_course_id,
            "course_id": self.test_course_id,
            "owner": self.test_username,
            "course_code": "EE 312",
            "course_title": "Electromagnetic Fields II",
            "credit_units": "3 Units",
            "section": "BSEE 3A",
            "semester_ay": "First Semester, AY 2026-2027",
            "faculty_name": "Engr. Elwin Tano",
            "program_name": "Bachelor of Science in Electrical Engineering",
            "class_schedule": "MWF 10:00AM - 11:00AM",
            "course_description": "Advanced electrostatic and magnetostatic boundary-value problems and electromagnetic wave propagation.",
            "blueprint": {
                "metadata": {
                    "course_code": "EE 312",
                    "course_title": "Electromagnetic Fields II",
                    "credit_units": "3 Units",
                    "section": "BSEE 3A",
                    "program_name": "Bachelor of Science in Electrical Engineering",
                    "passing_percentage": 75.0,
                },
                "clos": [
                    {"code": "CLO1", "statement": "Apply Maxwell equations to time-harmonic electromagnetic fields."},
                    {"code": "CLO2", "statement": "Analyze uniform plane wave propagation in various media."},
                ],
                "students": [
                    {
                        "student_id": self.test_student_id,
                        "last_name": self.test_student_last,
                        "first_name": self.test_student_first,
                        "name": f"{self.test_student_last}, {self.test_student_first}",
                        "program_year": "BSEE 3A",
                        "email": f"{self.test_student_id}@usep.edu.ph",
                        "scores": {},
                    }
                ],
            },
            "workflow": {
                "status": "for_student_acknowledgment",
                "step": 5,
                "qa_approved_at": datetime.now().isoformat(timespec="seconds"),
                "signatures": [
                    {"step": "faculty", "signer_name": "Engr. Elwin Tano"},
                    {"step": "dept_chair", "signer_name": "Engr. Nikka Basan"},
                    {"step": "prog_head", "signer_name": "Engr. Charito Claro"},
                    {"step": "qa_head", "signer_name": "College QA Head"},
                ],
                "student_acknowledgments": [],
            },
            "student_acknowledgments": [],
        }

        # Save course
        courses_store.save_course_doc(self.course_doc)

        # Register initial student
        student_store.register_or_update_student(
            student_id=self.test_student_id,
            last_name=self.test_student_last,
            first_name=self.test_student_first,
            full_name=self.test_student_full,
            program_year="BSEE 3A",
            email=f"{self.test_student_id}@usep.edu.ph",
        )
        all_sts = student_store._load_students()
        if self.test_student_id in all_sts and "syllabus_acknowledgments" in all_sts[self.test_student_id]:
            all_sts[self.test_student_id]["syllabus_acknowledgments"].pop(self.test_course_id, None)
            student_store._save_students(all_sts)

    def tearDown(self):
        courses_store.delete_course("admin", self.test_course_id)
        courses_store.delete_course(self.test_username, self.test_course_id)
        all_sts = student_store._load_students()
        if self.test_student_id in all_sts:
            del all_sts[self.test_student_id]
            student_store._save_students(all_sts)

    def test_login_navigation_links(self):
        """Test navigation between Faculty Portal and Student Portal."""
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"/student/login", res.data)
        self.assertIn(b"Go to Student Portal", res.data)

        res_stud = self.client.get("/student/login")
        self.assertEqual(res_stud.status_code, 200)
        self.assertIn(b"Back to Faculty Portal", res_stud.data)
        self.assertIn(b"/login", res_stud.data)

    def test_download_roster_template(self):
        """Test downloading CSV roster template."""
        res = self.client.get("/api/roster-template.csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"student_id,last_name,first_name,program_year,email", res.data)
        self.assertIn(b"2024-00101,Dela Cruz,Juan", res.data)

    def test_manual_student_encoding(self):
        """Test faculty manually encoding a student at the acknowledgment stage."""
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["role"] = "admin"

        payload = {
            "student_id": "2026-99002",
            "last_name": "Santos",
            "first_name": "Maria",
            "program_year": "BSEE 3A",
            "email": "2026-99002@usep.edu.ph",
        }
        res = self.client.post(
            f"/api/courses/{self.test_course_id}/roster/add-student",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total_students"), 2)

        # Verify reflected in course document
        doc = courses_store.find_course(self.test_course_id)
        stud_ids = [s["student_id"] for s in doc["blueprint"]["students"]]
        self.assertIn("2026-99002", stud_ids)

        # Verify registered in student_store
        st_profile = student_store.get_student_profile("2026-99002")
        self.assertIsNotNone(st_profile)
        self.assertEqual(st_profile["last_name"], "Santos")

    def test_roster_import_paste_and_csv(self):
        """Test importing students via paste text and CSV."""
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["role"] = "admin"

        # Case 1: Paste text
        paste_text = (
            "2026-99003, Reyes, Pedro, BSEE 3A\n"
            "2026-99004, Garcia, Ana, BSEE 3A\n"
        )
        res = self.client.post(
            f"/api/courses/{self.test_course_id}/roster/import",
            data=json.dumps({"paste_text": paste_text}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("added_count"), 2)

        # Case 2: CSV file upload
        csv_file = io.BytesIO(b"student_id,last_name,first_name,program_year\n2026-99005,Torres,Luis,BSEE 3A\n")
        res_file = self.client.post(
            f"/api/courses/{self.test_course_id}/roster/import",
            data={"file": (csv_file, "roster.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res_file.status_code, 200)
        data_file = res_file.get_json()
        self.assertTrue(data_file.get("success"))

        doc = courses_store.find_course(self.test_course_id)
        stud_ids = [s["student_id"] for s in doc["blueprint"]["students"]]
        self.assertIn("2026-99005", stud_ids)

    def test_student_login_and_enrolled_reflection(self):
        """Test that enrolled student can log in and view their course in Pending Acknowledgment."""
        res_login = self.client.post(
            "/student/login",
            data={"student_id": self.test_student_id, "secret": self.test_student_last},
            follow_redirects=False,
        )
        self.assertEqual(res_login.status_code, 302)
        self.assertIn("/student/dashboard", res_login.headers["Location"])

        # Access dashboard
        res_dash = self.client.get("/student/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"EE 312", res_dash.data)
        self.assertIn(b"Electromagnetic Fields II", res_dash.data)
        self.assertIn(b"Action Required: Pending Syllabus Acknowledgment", res_dash.data)
        self.assertIn(b"Review Syllabus", res_dash.data)

        # Check API
        res_api = self.client.get("/api/student/courses")
        self.assertEqual(res_api.status_code, 200)
        cdata = res_api.get_json()
        pending_ids = [c["course_id"] for c in cdata["pending"]]
        self.assertIn(self.test_course_id, pending_ids)

    def test_student_sign_acknowledgment_with_comment(self):
        """Test student acknowledging syllabus with electronic signature and custom comment."""
        with self.client.session_transaction() as sess:
            sess["username"] = self.test_student_id
            sess["student_id"] = self.test_student_id
            sess["student_name"] = self.test_student_full
            sess["role"] = "student"

        dummy_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        test_comment = "Understood and accepted. All grading percentages and laboratory requirements are clear."

        payload = {
            "course_id": self.test_course_id,
            "signature_data": dummy_sig,
            "comment": test_comment,
        }

        res = self.client.post(
            "/api/student/sign-acknowledgment",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        ack = data.get("acknowledgment") or {}
        self.assertEqual(ack.get("student_id"), self.test_student_id)
        self.assertEqual(ack.get("comment"), test_comment)

        # Course should now be in acknowledged list on student portal
        res_courses = self.client.get("/api/student/courses")
        cdata = res_courses.get_json()
        ack_ids = [c["course_id"] for c in cdata["acknowledged"]]
        self.assertIn(self.test_course_id, ack_ids)
        self.assertNotIn(self.test_course_id, [c["course_id"] for c in cdata["pending"]])
        ack_course = next(c for c in cdata["acknowledged"] if c["course_id"] == self.test_course_id)
        self.assertEqual(ack_course["comment"], test_comment)

        # On faculty side, verify enriched roster reflects acknowledgment and student comment
        res_fac = self.client.get(f"/api/courses/{self.test_course_id}/student-acknowledgment")
        self.assertEqual(res_fac.status_code, 200)
        fac_data = res_fac.get_json()
        roster = fac_data.get("roster") or []
        self.assertEqual(len(roster), 1)
        self.assertTrue(roster[0]["is_acknowledged"])
        self.assertEqual(roster[0]["comment"], test_comment)
        self.assertIsNotNone(roster[0]["acknowledged_at"])

        # Verify PDF export of FM-USeP-MID-07 includes acknowledged student
        res_pdf = self.client.get(f"/api/courses/{self.test_course_id}/export-acknowledgment-pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, "application/pdf")
        self.assertGreater(len(res_pdf.data), 1000)


if __name__ == "__main__":
    unittest.main()
