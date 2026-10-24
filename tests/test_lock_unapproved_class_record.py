# tests/test_lock_unapproved_class_record.py
import unittest
import json
import os
from werkzeug.security import generate_password_hash
from app import app
import auth
import courses_store
import syllabus_workflow
import class_record_workflow

class TestLockUnapprovedClassRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()
        auth.ensure_default_admin()

        users = auth._load_users()
        fake_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        if "faculty_tester" not in users:
            users["faculty_tester"] = {
                "full_name": "Engr. Tester Faculty",
                "role": "faculty",
                "workflow_roles": ["review_committee"],
                "position_title": "Faculty Member",
                "program_codes": ["EE"],
                "password_hash": generate_password_hash("password123"),
                "signature_data": fake_sig,
            }
        users["faculty_tester"]["signature_data"] = fake_sig
        auth._save_users(users)

    @classmethod
    def tearDownClass(cls):
        users = auth._load_users()
        if "faculty_tester" in users:
            del users["faculty_tester"]
            auth._save_users(users)
        tester_dir = os.path.join(courses_store.COURSES_BASE_DIR, "faculty_tester")
        if os.path.exists(tester_dir):
            import shutil
            shutil.rmtree(tester_dir, ignore_errors=True)

    def login(self, username="faculty_tester"):
        with self.client.session_transaction() as sess:
            sess["username"] = username

    def test_unapproved_syllabus_locks_class_record_setup_and_grades(self):
        """Verify that when syllabus is unapproved (draft), categories and students cannot be altered."""
        self.login("faculty_tester")

        # 1. Create a course (starts in draft syllabus status)
        course = courses_store.create_course("faculty_tester", course_code="EE 411", course_title="Advanced Power Systems", section="EE 4A")
        cid = course["id"]
        initial_categories = json.loads(json.dumps(course["blueprint"].get("categories", [])))
        initial_students = json.loads(json.dumps(course["blueprint"].get("students", [])))
        self.assertNotEqual((course.get("workflow") or {}).get("status"), "approved")

        # 2. Attempt to tamper/modify categories while syllabus is unapproved
        tampered_categories = [
            {
                "category_id": "TAMPERED_CAT",
                "term": "Midterm",
                "assessment_type": "SA",
                "assessment_code": "SA99",
                "name": "Tampered Assessment",
                "weight_pct": 100.0,
                "items": [{"item_id": "TAMPER1", "name": "Tampered Item", "max_score": 100, "co_id": "CLO1"}]
            }
        ]
        tampered_students = [
            {"student_id": "2026-9999", "first_name": "Hacked", "last_name": "Student", "scores": {"TAMPER1__CLO1": 100}}
        ]

        payload = {
            "course_code": "EE 411",
            "course_title": "Advanced Power Systems (Updated Title Allowed in Draft)",
            "section": "EE 4A",
            "blueprint": {
                **course["blueprint"],
                "metadata": {**course["blueprint"]["metadata"], "course_title": "Advanced Power Systems (Updated Title Allowed in Draft)"},
                "categories": tampered_categories,
                "students": tampered_students,
            }
        }

        saved = courses_store.save_course("faculty_tester", cid, payload)

        # Title change should be saved (syllabus editing allowed before submission)
        self.assertEqual(saved["course_title"], "Advanced Power Systems (Updated Title Allowed in Draft)")
        # BUT categories and students must remain locked to initial state!
        self.assertEqual(saved["blueprint"].get("categories"), initial_categories)
        self.assertEqual(saved["blueprint"].get("students"), initial_students)

        # 3. Attempting to submit class record while syllabus is unapproved must fail
        with self.assertRaises(class_record_workflow.ClassRecordWorkflowError) as cm:
            class_record_workflow.submit_class_record(saved, auth._load_users().get("faculty_tester"), "Submit grades")
        self.assertIn("until the syllabus is approved", str(cm.exception))

        # 4. Now officially approve the syllabus workflow
        saved["workflow"] = {"status": "approved", "is_locked": True}
        courses_store.save_course_doc(saved)

        # 5. Now that syllabus is approved, updating categories and students MUST SUCCEED
        new_valid_categories = [
            {
                "category_id": "MID_SA1",
                "term": "Midterm",
                "assessment_type": "SA",
                "assessment_code": "SA1",
                "name": "Midterm Exam",
                "weight_pct": 50.0,
                "items": [{"item_id": "MTE", "name": "Exam Item", "max_score": 50, "co_id": "CLO1"}]
            }
        ]
        new_valid_students = [
            {"student_id": "2026-1001", "first_name": "Valid", "last_name": "Student", "scores": {"MTE__CLO1": 45}}
        ]

        payload_approved = {
            "blueprint": {
                **saved["blueprint"],
                "categories": new_valid_categories,
                "students": new_valid_students,
            }
        }
        saved_after_approval = courses_store.save_course("faculty_tester", cid, payload_approved)
        self.assertEqual(saved_after_approval["blueprint"]["categories"], new_valid_categories)
        self.assertEqual(saved_after_approval["blueprint"]["students"], new_valid_students)

        # Clean up test course
        courses_store.delete_course("faculty_tester", cid)

    def test_dom_elements_and_javascript_guards_present(self):
        """Verify DOM elements and interactive guards exist in templates/index.html."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        # DOM containers
        self.assertIn('id="setupTabContent"', html)
        self.assertIn('id="gradebookTabContent"', html)

        # checkClassRecordLock implementation
        self.assertIn('const setupContent = document.getElementById("setupTabContent");', html)
        self.assertIn('const gradebookContent = document.getElementById("gradebookTabContent");', html)
        self.assertIn('setupContent.style.opacity = isSyllabusApproved ? "1" : "0.5";', html)
        self.assertIn('setupContent.style.pointerEvents = isSyllabusApproved ? "auto" : "none";', html)
        self.assertIn('gradebookContent.style.opacity = isSyllabusApproved ? "1" : "0.5";', html)
        self.assertIn('gradebookContent.style.pointerEvents = isSyllabusApproved ? "auto" : "none";', html)

        # Tab 2 & Tab 3 interaction function guards
        self.assertIn('if (!currentWorkflow || currentWorkflow.status !== "approved") {', html)
        self.assertIn('Class Record Setup & Grades are locked until the syllabus is approved', html)
        self.assertIn('Class Record is locked until the syllabus is approved', html)

if __name__ == "__main__":
    unittest.main()
