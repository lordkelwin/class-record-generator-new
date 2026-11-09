import unittest
from unittest.mock import patch
import json
import os
import shutil

import app
import courses_store

TEST_USER = "test_nav_faculty_user"
MOCK_FACULTY_USER = {
    "username": TEST_USER,
    "full_name": "Test Nav Faculty",
    "role": "Faculty",
    "can_access_faculty_tools": True,
    "must_change_password": False,
}


class TestDashboardNavigationAndRedirect(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.client.testing = True
        courses_dir = courses_store._get_user_courses_dir(TEST_USER)
        if os.path.exists(courses_dir):
            for fn in os.listdir(courses_dir):
                try:
                    os.remove(os.path.join(courses_dir, fn))
                except Exception:
                    pass

    def tearDown(self):
        courses_dir = courses_store._get_user_courses_dir(TEST_USER)
        if os.path.exists(courses_dir):
            for fn in os.listdir(courses_dir):
                try:
                    os.remove(os.path.join(courses_dir, fn))
                except Exception:
                    pass

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_01_unapproved_course_defaults_to_syllabus_creator(self, mock_auth_user, mock_app_user):
        """Test 1: Unapproved course causes root route to default to Syllabus Creator, not locked Dashboard."""
        cid = "c_unapproved_test_1"
        courses_store.save_course(
            username=TEST_USER,
            course_id=cid,
            payload={
                "course_code": "EE 101",
                "course_title": "Basic Electrical Engineering",
                "section": "EE 1A",
                "semester_ay": "1st Semester, A.Y. 2026-2027",
            },
        )

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Verify active states in HTML
        self.assertIn('id="ribbonTabSyllabus"', html)
        self.assertIn('class="ribbon-tab active" id="ribbonTabSyllabus"', html)
        self.assertIn('class="ribbon-band active" id="ribbonBandSyllabus"', html)
        self.assertIn('id="tab-syllabus" class="tab-panel active"', html)

        # Ribbon tab dashboard should NOT be active
        self.assertNotIn('class="ribbon-tab active" id="ribbonTabDashboard"', html)
        self.assertNotIn('class="ribbon-band active" id="ribbonBandDashboard"', html)
        self.assertNotIn('id="tab-dashboard" class="tab-panel active"', html)

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_02_dashboard_route_redirects_when_locked(self, mock_auth_user, mock_app_user):
        """Test 2: Accessing /dashboard when prerequisites are unmet redirects to /?tab=syllabus."""
        cid = "c_unapproved_test_2"
        courses_store.save_course(
            username=TEST_USER,
            course_id=cid,
            payload={
                "course_code": "EE 102",
                "course_title": "Basic Electrical Engineering II",
                "section": "EE 1B",
            },
        )

        resp = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.endswith("/?tab=syllabus") or resp.location.endswith("?tab=syllabus"))

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_03_approved_course_with_scores_unlocks_dashboard(self, mock_auth_user, mock_app_user):
        """Test 3: Finalized (approved) course with recorded scores allows Dashboard access."""
        cid = "c_approved_test_3"
        doc = courses_store.save_course(
            username=TEST_USER,
            course_id=cid,
            payload={
                "course_code": "EE 201",
                "course_title": "Circuits I",
                "section": "EE 2A",
            },
        )
        doc["workflow"] = {
            "status": "approved",
            "approved": True,
            "locked": True,
        }
        courses_store.auto_generate_class_record(doc)
        doc["blueprint"]["students"] = [
            {
                "student_id": "2026-NAV01",
                "name": "Dela Cruz, Juan",
                "scores": {"SA1_1__CLO1": 92.5},
            }
        ]
        courses_store.save_course_doc(doc)

        # Test status API
        resp = self.client.get("/api/dashboard/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["is_dashboard_unlocked"])
        self.assertTrue(data["has_recorded_scores"])
        self.assertTrue(data["has_approved_syllabus"])

        # Test root route defaults to dashboard
        root_resp = self.client.get("/")
        self.assertEqual(root_resp.status_code, 200)
        root_html = root_resp.get_data(as_text=True)
        self.assertIn('class="ribbon-tab active" id="ribbonTabDashboard"', root_html)
        self.assertIn('class="ribbon-band active" id="ribbonBandDashboard"', root_html)
        self.assertIn('id="tab-dashboard" class="tab-panel active"', root_html)

        # Test /dashboard route redirects to /?tab=dashboard
        dash_resp = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(dash_resp.status_code, 302)
        self.assertTrue(dash_resp.location.endswith("/?tab=dashboard") or dash_resp.location.endswith("?tab=dashboard"))


if __name__ == "__main__":
    unittest.main()
