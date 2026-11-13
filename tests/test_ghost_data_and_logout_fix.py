import unittest
import json
import os
import shutil
import tempfile
from app import app
import courses_store
import student_store
import db_persistence
import auth

class GhostDataAndLogoutFixTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess.clear()

        self.test_cid = "EE_TEST_GHOST_101"
        self.test_student_id = "2026-99991"
        self.test_student_id_2 = "2026-99992"

        # Register test students in student store & db
        student_store.register_or_update_student(
            student_id=self.test_student_id,
            last_name="Reyes",
            first_name="Carla",
            program_year="EE 3A",
            course_id=self.test_cid
        )
        student_store.register_or_update_student(
            student_id=self.test_student_id_2,
            last_name="Santos",
            first_name="Marco",
            program_year="EE 3A",
            course_id=self.test_cid
        )

        # Create approved test course document
        self.course_doc = {
            "id": self.test_cid,
            "owner": "admin",
            "course_code": "EE 991",
            "course_title": "Ghost Test Course",
            "section": "3A",
            "semester_ay": "1st Sem 2026-2027",
            "workflow": {
                "status": "approved",
                "is_approved": True,
                "current_step": 3,
                "student_acknowledgments": [
                    {"student_id": self.test_student_id, "student_name": "Reyes, Carla", "email": "carla@usep.edu.ph", "acknowledged": True},
                    {"student_id": self.test_student_id_2, "student_name": "Santos, Marco", "email": "marco@usep.edu.ph", "acknowledged": True}
                ]
            },
            "student_acknowledgments": [
                {"student_id": self.test_student_id, "student_name": "Reyes, Carla", "email": "carla@usep.edu.ph", "acknowledged": True},
                {"student_id": self.test_student_id_2, "student_name": "Santos, Marco", "email": "marco@usep.edu.ph", "acknowledged": True}
            ],
            "blueprint": {
                "metadata": {
                    "course_code": "EE 991",
                    "course_title": "Ghost Test Course",
                    "section": "3A",
                    "program_code": "EE",
                    "lec_lab": "Lecture",
                    "credit_units": "3.0 Units"
                },
                "class_record_initialized": True,
                "students": [
                    {
                        "student_id": self.test_student_id,
                        "last_name": "Reyes",
                        "first_name": "Carla",
                        "name": "Reyes, Carla",
                        "email": "carla@usep.edu.ph",
                        "program_year": "EE 3A",
                        "scores": {"Q1": 25.0}
                    },
                    {
                        "student_id": self.test_student_id_2,
                        "last_name": "Santos",
                        "first_name": "Marco",
                        "name": "Santos, Marco",
                        "email": "marco@usep.edu.ph",
                        "program_year": "EE 3A",
                        "scores": {"Q1": 28.0}
                    }
                ]
            }
        }
        courses_store.save_course_doc(self.course_doc)

    def tearDown(self):
        # Clean up test course
        try:
            courses_store.delete_course("admin", self.test_cid)
        except Exception:
            pass
        try:
            student_store.delete_student(self.test_student_id)
            student_store.delete_student(self.test_student_id_2)
        except Exception:
            pass
        try:
            db_persistence.disenroll_student_from_course_db(self.test_student_id, self.test_cid)
            db_persistence.disenroll_student_from_course_db(self.test_student_id_2, self.test_cid)
        except Exception:
            pass

    def test_01_single_student_removal_does_not_resurrect(self):
        """Verifies removing a single student permanently unlinks them from roster, acknowledgments, and database."""
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["role"] = "admin"
            sess["_csrf"] = "test-token"

        # Remove student 1
        resp = self.client.post(
            f"/api/courses/{self.test_cid}/roster/remove-student",
            json={"student_id": self.test_student_id, "_csrf": "test-token"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total_students"), 1)

        # Verify student 1 is gone from courses_store find_course
        loaded = courses_store.find_course(self.test_cid)
        students = (loaded.get("blueprint") or {}).get("students") or []
        sids = [s.get("student_id") for s in students]
        self.assertNotIn(self.test_student_id, sids)
        self.assertIn(self.test_student_id_2, sids)

        # Verify student 1 is gone from student_acknowledgments
        acks = loaded.get("student_acknowledgments") or []
        ack_sids = [a.get("student_id") for a in acks]
        self.assertNotIn(self.test_student_id, ack_sids)

        # Verify disenrollment in student_store
        st_prof = student_store.get_student_profile(self.test_student_id)
        if st_prof:
            self.assertNotIn(self.test_cid, st_prof.get("enrolled_courses", []))

        # Re-run auto_generate_class_record and check that student 1 does NOT resurrect!
        courses_store.auto_generate_class_record(loaded, force=True)
        re_loaded_students = (loaded.get("blueprint") or {}).get("students") or []
        re_sids = [s.get("student_id") for s in re_loaded_students]
        self.assertNotIn(self.test_student_id, re_sids)
        self.assertEqual(len(re_loaded_students), 1)

    def test_02_clearing_entire_roster_does_not_resurrect_ghost_data(self):
        """Verifies that when an instructor clears all students (students = []), they do not resurrect on reload or save."""
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["role"] = "admin"
            sess["_csrf"] = "test-token"

        # Save course with empty students list
        payload = {
            "course_code": "EE 991",
            "section": "3A",
            "blueprint": {
                "metadata": {
                    "course_code": "EE 991",
                    "section": "3A",
                    "program_code": "EE"
                },
                "class_record_initialized": True,
                "students": []
            }
        }
        resp = self.client.put(
            f"/api/courses/{self.test_cid}",
            json=payload
        )
        self.assertEqual(resp.status_code, 200)

        # Reload course from store
        loaded = courses_store.find_course(self.test_cid)
        students = (loaded.get("blueprint") or {}).get("students") or []
        self.assertEqual(len(students), 0, "Cleared student list should remain empty, not resurrected!")

        # Also reload directly from SQLite db_persistence
        db_doc = db_persistence.load_course_from_db(self.test_cid)
        if db_doc:
            db_students = (db_doc.get("blueprint") or {}).get("students") or []
            self.assertEqual(len(db_students), 0, "SQLite load should respect class_record_initialized and not re-seed!")

    def test_03_faculty_logout_clears_session_and_prevents_refresh_reauth(self):
        """Verifies that faculty logout clears session, deletes cookie, and prevents auto-reauthentication."""
        # 1. Log in as admin
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["role"] = "admin"
            sess["_csrf"] = "test-token"

        # Verify access to dashboard
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

        # 2. Log out
        logout_resp = self.client.post("/logout")
        self.assertEqual(logout_resp.status_code, 302)
        self.assertIn("/login", logout_resp.location)
        self.assertIn("signed_out=1", logout_resp.location)

        # Check Set-Cookie headers on logout response
        set_cookie = logout_resp.headers.get("Set-Cookie", "")
        self.assertTrue(
            "session=;" in set_cookie or "Expires=" in set_cookie or "Max-Age=0" in set_cookie,
            f"Set-Cookie header should expire or clear the session: {set_cookie}"
        )

        # 3. Simulate browser refresh / navigation to index - must redirect to login!
        index_resp = self.client.get("/")
        self.assertEqual(index_resp.status_code, 302)
        self.assertIn("/login", index_resp.location)

        # 4. Visiting login page with signed_out=1 must render login without auto-redirect
        login_page_resp = self.client.get("/login?signed_out=1")
        self.assertEqual(login_page_resp.status_code, 200)
        self.assertIn("Sign in with your faculty account", login_page_resp.get_data(as_text=True))

    def test_04_student_logout_clears_session_and_prevents_refresh_reauth(self):
        """Verifies that student portal logout clears session, deletes cookie, and prevents auto-reauthentication."""
        # 1. Log in as student
        with self.client.session_transaction() as sess:
            sess["username"] = self.test_student_id
            sess["student_id"] = self.test_student_id
            sess["role"] = "student"
            sess["_csrf"] = "test-token"

        # Verify access to student dashboard
        resp = self.client.get("/student/dashboard")
        self.assertEqual(resp.status_code, 200)

        # 2. Log out
        logout_resp = self.client.post("/student/logout")
        self.assertEqual(logout_resp.status_code, 302)
        self.assertIn("/student/login", logout_resp.location)
        self.assertIn("signed_out=1", logout_resp.location)

        # Check Set-Cookie headers
        set_cookie = logout_resp.headers.get("Set-Cookie", "")
        self.assertTrue(
            "session=;" in set_cookie or "Expires=" in set_cookie or "Max-Age=0" in set_cookie,
            f"Set-Cookie header should expire or clear the session: {set_cookie}"
        )

        # 3. Simulate browser refresh / navigation to student dashboard - must redirect to student login!
        dash_resp = self.client.get("/student/dashboard")
        self.assertEqual(dash_resp.status_code, 302)
        self.assertIn("/student/login", dash_resp.location)

        # 4. Visiting student login page with signed_out=1 must render login without auto-redirect
        login_page_resp = self.client.get("/student/login?signed_out=1")
        self.assertEqual(login_page_resp.status_code, 200)
        self.assertIn("Sign In to Student Portal", login_page_resp.get_data(as_text=True))

if __name__ == "__main__":
    unittest.main()
