import unittest
import os
import json
import uuid
from datetime import datetime, timedelta
import app as flask_app
import syllabus_workflow
import courses_store
import notification_service
import auth

class EmailAndBottleneckNotificationsTestCase(unittest.TestCase):
    def setUp(self):
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["SECRET_KEY"] = "testing-secret-key"
        self.app = flask_app.app.test_client()
        self.created_course_ids = []
        self.created_usernames = []

    def tearDown(self):
        for cid, owner in self.created_course_ids:
            try:
                courses_store.delete_course(owner, cid)
            except Exception:
                pass
        for uname in self.created_usernames:
            try:
                with auth._lock:
                    users = auth._load_users()
                    users.pop(uname, None)
                    auth._save_users(users)
            except Exception:
                pass

    def _create_submittable_course(self, owner="faculty_tano", code="EE 888", title="Testing"):
        payload = {
            "course_code": code,
            "course_title": title,
            "program": "EE",
            "programs": ["EE"],
            "section": "EE 4A",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "blueprint": {
                "metadata": {
                    "course_code": code,
                    "course_title": title,
                    "course_description": "Comprehensive study of electrical networks, circuits, and advanced engineering principles.",
                    "section": "EE 4A",
                    "program_code": "EE",
                    "semester_ay": "1st Semester, A.Y. 2026-2027",
                    "credit_units": 3,
                    "faculty_name": "Engr. Elwin Jay J. Tano",
                    "syllabus_assessment_activities": [
                        {"name": "Preliminary Examination", "weight": 25}
                    ]
                },
                "course_outcomes": [
                    {"code": "CLO1", "description": "Demonstrate analysis."}
                ],
                "clos": [
                    {"code": "CLO1", "description": "Demonstrate analysis."}
                ],
                "assessment_tasks": [
                    {"name": "Preliminary Examination", "type": "Exam", "weight": 25}
                ],
                "rubrics": []
            }
        }
        with self.app.session_transaction() as sess:
            sess["username"] = owner
        res = self.app.post("/api/courses", json=payload)
        self.assertEqual(res.status_code, 201)
        cid = res.get_json()["course"]["id"]
        self.created_course_ids.append((cid, owner))
        return cid

    def test_account_creation_with_email(self):
        """Account creation must include email and store it properly in data/users.json."""
        with self.app.session_transaction() as sess:
            sess["username"] = "admin"
            sess["_csrf"] = "test-token"

        test_uname = f"fac_test_{uuid.uuid4().hex[:6]}"
        test_email = f"{test_uname}@usep.edu.ph"
        self.created_usernames.append(test_uname)

        res = self.app.post("/admin/users/create", data={
            "_csrf": "test-token",
            "username": test_uname,
            "full_name": "Engr. Test Email Account",
            "email": test_email,
            "password": "Password123!",
            "roles": ["review_committee"],
            "program_codes": ["EE"],
            "position_title": "Faculty Member"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify email is recorded in users.json
        users = auth._load_users()
        self.assertIn(test_uname, users)
        self.assertEqual(users[test_uname].get("email"), test_email)

        # Verify updating email
        updated_email = f"updated_{test_email}"
        res = self.app.post(f"/admin/users/{test_uname}/role", data={
            "_csrf": "test-token",
            "email": updated_email,
            "roles": ["review_committee", "program_head"],
            "program_codes": ["EE"],
            "position_title": "Program Head - Electrical Engineering"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        users = auth._load_users()
        self.assertEqual(users[test_uname].get("email"), updated_email)

    def test_syllabus_review_request_sends_email_notification(self):
        """Submitting a syllabus for review dispatches email notification to review committee."""
        cid = self._create_submittable_course("faculty_tano", "EE 888", "Notification Testing Subject")

        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        committee = [
            {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Chair"},
            {"username": "faculty_arenga", "name": "Engr. Delan Zoe H. Arenga", "role": "Review Committee Member"},
            {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Member"}
        ]

        res = self.app.post(f"/api/courses/{cid}/workflow/submit", json={
            "assigned_committee": "faculty_basan",
            "assigned_committee_name": "Engr. Nikka Samantha A. Basan",
            "committee_members": committee,
            "submission_notes": "Please evaluate under OBE 2026 guidelines."
        })
        self.assertEqual(res.status_code, 200)

        # Inspect sent notifications
        recent = notification_service.get_recent_notifications(10)
        matching = [n for n in recent if n.get("course_id") == cid and n.get("category") == "review_request"]
        self.assertTrue(len(matching) >= 1)
        notif = matching[0]
        self.assertIn("EE 888", notif["subject"])
        # Check committee emails are among recipients
        users = auth._load_users()
        basan_email = users.get("faculty_basan", {}).get("email")
        self.assertIn(basan_email, notif["recipients"])

    def test_bottleneck_detection_and_re_notification(self):
        """Requests pending > 3 days are flagged as queue bottlenecks and re-notified."""
        cid = self._create_submittable_course("faculty_tano", "EE 777", "Bottleneck Test Course")

        # Submit syllabus
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        committee = [
            {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Chair"},
            {"username": "faculty_arenga", "name": "Engr. Delan Zoe H. Arenga", "role": "Review Committee Member"},
            {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Member"}
        ]
        res = self.app.post(f"/api/courses/{cid}/workflow/submit", json={"committee_members": committee})
        self.assertEqual(res.status_code, 200)

        # Test case A: Pending < 3 days (e.g. 1.0 day ago)
        doc = courses_store.find_course(cid)
        self.assertEqual(doc["workflow"]["status"], "for_committee_review")
        one_day_ago = (datetime.now() - timedelta(days=1.0)).isoformat(timespec="seconds")
        doc["workflow"]["step_entered_at"] = one_day_ago
        courses_store.save_course_doc(doc)

        q_age = syllabus_workflow.get_queue_age(doc)
        self.assertFalse(q_age["is_overdue"])
        self.assertAlmostEqual(q_age["days_in_queue"], 1.0, places=0)

        # Test case B: Pending > 3 days (e.g. 4.5 days ago)
        four_half_days_ago = (datetime.now() - timedelta(days=4.5)).isoformat(timespec="seconds")
        doc["workflow"]["step_entered_at"] = four_half_days_ago
        courses_store.save_course_doc(doc)

        q_age = syllabus_workflow.get_queue_age(doc)
        self.assertTrue(q_age["is_overdue"])
        self.assertGreaterEqual(q_age["days_in_queue"], 4.0)

        # Test case C: Trigger reminder dispatch
        with self.app.session_transaction() as sess:
            sess["username"] = "admin"

        res = self.app.post(f"/api/courses/{cid}/workflow/send-reminder")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

        # Verify bottleneck reminder email was sent
        recent = notification_service.get_recent_notifications(10)
        reminders = [n for n in recent if n.get("course_id") == cid and n.get("category") == "bottleneck_reminder"]
        self.assertTrue(len(reminders) >= 1)
        r_notif = reminders[0]
        self.assertIn("OVERDUE", r_notif["subject"])

        # Test case D: Bulk dispatch endpoint
        res = self.app.post("/api/workflow/dispatch-reminders")
        self.assertEqual(res.status_code, 200)
        bulk_data = res.get_json()
        self.assertTrue(bulk_data.get("success"))

    def test_notifications_log_api(self):
        """API /api/notifications/log returns recent notifications log."""
        with self.app.session_transaction() as sess:
            sess["username"] = "admin"

        res = self.app.get("/api/notifications/log")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("notifications", data)
        self.assertIsInstance(data["notifications"], list)

if __name__ == "__main__":
    unittest.main()
