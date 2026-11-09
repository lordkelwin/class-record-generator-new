"""
test_tasks_1_to_4_verification.py - End-to-end Verification for Tasks 1 through 4.

Verifies:
1. Assessment definition data propagation to Class Record, CLO Report, and Dashboard without approval lock blocks.
2. Review Committee Members signing -> Committee Chair full read/write access to evaluation checklist and endorsement transition.
3. Student Portal inline performance dashboard architecture and API.
4. Relational database persistence in SQLite (academic_catalog.db) across users, students, courses, categories, items, grades, and signatures.
"""

import os
import sys
import json
import unittest
import sqlite3

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app import app
import auth
import student_store
import courses_store
import syllabus_workflow
import db_persistence


class TestTasks1To4Verification(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def tearDown(self):
        # Clean up any dummy test users / students from SQLite and JSON
        conn = db_persistence.get_db_connection()
        try:
            conn.execute("DELETE FROM app_users WHERE username LIKE '%task%'")
            conn.execute("DELETE FROM app_students WHERE student_id LIKE '%99999%'")
            conn.commit()
        finally:
            conn.close()

    def test_task_1_assessment_data_propagation(self):
        """
        Test Task 1:
        Even when syllabus is draft / unapproved, defined assessments propagate
        to blueprint categories, students can be added and scores saved,
        and CLO mapping resolves properly.
        """
        test_user = "test_fac_task1"
        test_cid = "c_task1_propagate_test"

        courses_store.delete_course(test_cid)

        payload = {
            "course_code": "EE 311",
            "course_title": "Power Systems 1",
            "section": "EE 3A",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "blueprint": {
                "metadata": {
                    "course_code": "EE 311",
                    "course_title": "Power Systems 1",
                    "section": "EE 3A",
                    "semester_ay": "1st Semester, A.Y. 2026-2027",
                    "course_description": "Analysis of electric power generation, transmission, and distribution systems.",
                    "syllabus_assessment_activities": [
                        {
                            "code": "SA1",
                            "activity": "Long Quiz 1",
                            "type": "Summative",
                            "weight_pct": 25.0,
                            "clo_aligned": "CLO 1, CLO 2",
                            "is_major_assessment": False
                        },
                        {
                            "code": "PRJ1",
                            "activity": "Design Capstone",
                            "type": "Summative",
                            "weight_pct": 20.0,
                            "clo_aligned": "CLO 2",
                            "is_major_assessment": True,
                            "major_scope": "independent"
                        }
                    ]
                },
                "course_outcomes": [
                    {"co_id": "CLO1", "description": "Outcome 1"},
                    {"co_id": "CLO2", "description": "Outcome 2"}
                ],
                "categories": [],
                "students": [
                    {
                        "student_id": "2023-00101",
                        "name": "Dela Cruz, Juan",
                        "scores": {"SA1_1": 28, "PRJ1": 48}
                    }
                ]
            }
        }

        saved_doc = courses_store.save_course(test_user, test_cid, payload)
        self.assertIsNotNone(saved_doc)
        bp = saved_doc.get("blueprint", {})

        cats = bp.get("categories") or []
        self.assertGreaterEqual(len(cats), 2, "Expected categories to be synchronized from syllabus activities")

        students = bp.get("students") or []
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]["student_id"], "2023-00101")
        self.assertEqual(students[0]["scores"]["SA1_1"], 28)

        conn = db_persistence.get_db_connection()
        try:
            db_cats = conn.execute("SELECT * FROM assessment_categories WHERE course_id = ?", (test_cid,)).fetchall()
            self.assertGreaterEqual(len(db_cats), 2)
            db_items = conn.execute("SELECT * FROM assessment_items WHERE course_id = ?", (test_cid,)).fetchall()
            self.assertGreaterEqual(len(db_items), 2)
            db_grades = conn.execute("SELECT * FROM student_course_grades WHERE course_id = ?", (test_cid,)).fetchall()
            self.assertEqual(len(db_grades), 1)
            scores_in_db = json.loads(db_grades[0]["scores_json"])
            self.assertEqual(scores_in_db.get("SA1_1"), 28)
        finally:
            conn.close()

        courses_store.delete_course(test_cid)

    def test_task_2_committee_chairperson_workflow_access(self):
        """
        Test Task 2:
        Review committee members sign -> status advances to for_committee_chair.
        Committee Chairperson has full read/write access to evaluation checklist.
        Chairperson endorses with signatures -> transitions to for_program_head.
        """
        owner = "faculty_task2"
        chair_user = "chair_task2"
        member_user1 = "member1_task2"
        member_user2 = "member2_task2"
        course_id = "c_task2_committee_wf_test"

        courses_store.delete_course(course_id)

        all_users = auth._load_users()
        all_users[owner] = {
            "username": owner,
            "full_name": "Instructor Owner",
            "role": "faculty",
            "workflow_roles": ["faculty"],
            "program_codes": ["EE"],
            "signature_data": "data:image/png;base64,owner_sig",
            "has_signature": True
        }
        all_users[chair_user] = {
            "username": chair_user,
            "full_name": "Prof. Chairperson",
            "role": "faculty",
            "workflow_roles": ["review_committee_chair"],
            "program_codes": ["EE"],
            "signature_data": "data:image/png;base64,chair_sig",
            "has_signature": True
        }
        all_users[member_user1] = {
            "username": member_user1,
            "full_name": "Dr. Committee Member 1",
            "role": "faculty",
            "workflow_roles": ["review_committee"],
            "program_codes": ["EE"],
            "signature_data": "data:image/png;base64,member1_sig",
            "has_signature": True
        }
        all_users[member_user2] = {
            "username": member_user2,
            "full_name": "Engr. Committee Member 2",
            "role": "faculty",
            "workflow_roles": ["review_committee"],
            "program_codes": ["EE"],
            "signature_data": "data:image/png;base64,member2_sig",
            "has_signature": True
        }
        auth._save_users(all_users)

        doc = courses_store.save_course(owner, course_id, {
            "course_code": "EE 322",
            "course_title": "Electromagnetics",
            "section": "EE 3B",
            "blueprint": {
                "metadata": {
                    "course_code": "EE 322",
                    "course_title": "Electromagnetics",
                    "section": "EE 3B",
                    "program_code": "EE",
                    "course_description": "Static and dynamic electromagnetic fields, Maxwell equations, and transmission lines.",
                    "syllabus_assessment_activities": [
                        {
                            "code": "SA1",
                            "activity": "Major Examination",
                            "type": "Summative",
                            "weight_pct": 50.0,
                            "clo_aligned": "CLO1"
                        }
                    ]
                },
                "course_outcomes": [{"co_id": "CLO1", "description": "Outcome 1"}],
                "categories": [{"category_id": "CAT1", "term": "Midterm", "name": "Exams", "items": [{"item_id": "EX1", "name": "Exam 1", "max_score": 100}]}]
            }
        })

        committee = [
            {"username": member_user1, "name": "Dr. Committee Member 1", "role": "Review Committee Member"},
            {"username": member_user2, "name": "Engr. Committee Member 2", "role": "Review Committee Member"},
            {"username": chair_user, "name": "Prof. Chairperson", "role": "Review Committee Chair"}
        ]
        syllabus_workflow.submit(doc, all_users[owner], committee_members=committee, submission_notes="For committee check")
        courses_store.save_course_doc(doc)
        self.assertEqual(doc["workflow"]["status"], "for_committee_review")

        # Member 1 signs
        syllabus_workflow.sign(
            doc,
            all_users[member_user1],
            decision="approve",
            remarks="Member 1 reviewed and recommended",
            required_item_ids=[]
        )
        courses_store.save_course_doc(doc)
        self.assertEqual(doc["workflow"]["status"], "for_committee_review")

        # Member 2 signs
        syllabus_workflow.sign(
            doc,
            all_users[member_user2],
            decision="approve",
            remarks="Member 2 reviewed and recommended",
            required_item_ids=[]
        )
        courses_store.save_course_doc(doc)

        # After both members sign, state must transition to for_committee_chair
        self.assertEqual(doc["workflow"]["status"], "for_committee_chair")

        # Committee chair must have user_can_act = True
        can_act = syllabus_workflow.user_can_act(all_users[chair_user], doc)
        self.assertTrue(can_act, "Committee Chairperson must be allowed to act on for_committee_chair")

        # Chairperson updates / saves checklist
        checklist_payload = {
            "responses": {"CS1": "FULLY", "CS2": "FULLY"},
            "comments": {"CS1": "Well structured"},
            "overall_recommendation": "Approved",
            "general_remarks": "Endorsed by Chair without revisions"
        }
        updated_wf = syllabus_workflow.save_checklist(doc, all_users[chair_user], checklist_payload)
        self.assertEqual(updated_wf["checklist"]["overall_recommendation"], "Approved")
        self.assertEqual(updated_wf["checklist"]["updated_by"], chair_user)

        # Chairperson affixes signature and endorses
        syllabus_workflow.sign(
            doc,
            all_users[chair_user],
            decision="approve",
            remarks="Chairperson endorsed",
            required_item_ids=[]
        )
        courses_store.save_course_doc(doc)

        # Workflow successfully advances to for_program_head
        self.assertEqual(doc["workflow"]["status"], "for_program_head")

        # Verify all signatures exist in the workflow
        sigs = doc["workflow"]["signatures"]
        steps = [s["step"] for s in sigs]
        self.assertIn("committee_members", steps)
        self.assertIn("committee_chair", steps)

        courses_store.delete_course(course_id)
        all_users.pop(owner, None)
        all_users.pop(chair_user, None)
        all_users.pop(member_user1, None)
        all_users.pop(member_user2, None)
        auth._save_users(all_users)

    def test_task_3_student_inline_performance_dashboard(self):
        """
        Test Task 3:
        Student portal performance view and data retrieval endpoint.
        """
        test_cid = "c_task3_inline_perf_test"
        courses_store.delete_course(test_cid)

        test_student_id = "2023-99999"
        students_db = student_store._load_students()
        students_db[test_student_id] = {
            "student_id": test_student_id,
            "username": test_student_id,
            "full_name": "Test Student Task3",
            "program_year": "BSEE 3rd Year",
            "enrolled_courses": [test_cid]
        }
        student_store._save_students(students_db)

        doc = courses_store.save_course("default", test_cid, {
            "course_code": "EE 323",
            "course_title": "Feedback Control Systems",
            "section": "EE 3A",
            "blueprint": {
                "metadata": {
                    "course_code": "EE 323",
                    "course_title": "Feedback Control Systems",
                    "section": "EE 3A"
                },
                "course_outcomes": [{"co_id": "CLO1", "description": "Control systems modeling"}],
                "categories": [{
                    "category_id": "MID_SA1",
                    "term": "Midterm",
                    "name": "Quiz 1",
                    "assessment_type": "SA",
                    "weight_pct": 30.0,
                    "items": [{"item_id": "Q1", "name": "Quiz 1", "max_score": 50.0, "co_id": "CLO1", "weight_pct": 30.0}]
                }],
                "students": [
                    {
                        "student_id": test_student_id,
                        "name": "Test Student Task3",
                        "scores": {"Q1": 45}
                    }
                ]
            }
        })

        with self.client.session_transaction() as sess:
            sess["student_id"] = test_student_id
            sess["username"] = test_student_id
            sess["role"] = "student"
            sess["student_name"] = "Test Student Task3"

        res = self.client.get(f"/api/student/courses/{test_cid}/performance")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("course", data)
        self.assertEqual(data["course"]["course_code"], "EE 323")
        self.assertIn("grades", data)
        self.assertIn("clo_attainment", data)

        resp_dash = self.client.get("/student/dashboard")
        self.assertEqual(resp_dash.status_code, 200)
        html = resp_dash.get_data(as_text=True)
        self.assertIn('id="studentPerformanceInlineView"', html)
        self.assertIn('id="btnViewPerformance"', html)
        self.assertNotIn('id="performanceModalBackdrop"', html)

        courses_store.delete_course(test_cid)
        students_db.pop(test_student_id, None)
        student_store._save_students(students_db)

    def test_task_4_relational_database_persistence(self):
        """
        Test Task 4:
        Verify SQLite tables exist, relational foreign keys cascade cleanly,
        and all CRUD operations commit persistently.
        """
        db_persistence.init_db()
        conn = db_persistence.get_db_connection()
        try:
            cur = conn.cursor()
            tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            required_tables = [
                "app_users", "app_students", "course_records",
                "assessment_categories", "assessment_items",
                "student_course_grades", "syllabus_reviews_and_signatures",
                "syllabus_evaluations"
            ]
            for tbl in required_tables:
                self.assertIn(tbl, tables, f"Expected table '{tbl}' in SQLite database")

            dummy_cid = "c_sqlite_cascade_test"
            dummy_doc = {
                "id": dummy_cid,
                "owner": "test_owner",
                "course_code": "EE 400",
                "course_title": "Capstone Design",
                "section": "EE 4A",
                "semester_ay": "2nd Semester, A.Y. 2026-2027",
                "blueprint": {
                    "categories": [
                        {
                            "category_id": "CAT_CAP",
                            "term": "Midterm",
                            "name": "Design Phase 1",
                            "items": [{"item_id": "DP1", "name": "Proposal Defense", "max_score": 100}]
                        }
                    ],
                    "students": [
                        {"student_id": "2022-00001", "name": "Student Alpha", "scores": {"DP1": 95}}
                    ]
                },
                "workflow": {
                    "status": "for_committee_review",
                    "signatures": [
                        {"step": "committee_members", "username": "comm1", "decision": "approved"}
                    ],
                    "checklist": {"overall_recommendation": "Approved"}
                }
            }

            db_persistence.save_course_to_db(dummy_doc)

            self.assertEqual(cur.execute("SELECT COUNT(*) FROM course_records WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 1)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM assessment_categories WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 1)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM assessment_items WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 1)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM student_course_grades WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 1)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM syllabus_reviews_and_signatures WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 1)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM syllabus_evaluations WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 1)

            deleted = db_persistence.delete_course_from_db(dummy_cid)
            self.assertTrue(deleted)

            self.assertEqual(cur.execute("SELECT COUNT(*) FROM course_records WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 0)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM assessment_categories WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 0)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM assessment_items WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 0)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM student_course_grades WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 0)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM syllabus_reviews_and_signatures WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 0)
            self.assertEqual(cur.execute("SELECT COUNT(*) FROM syllabus_evaluations WHERE course_id = ?", (dummy_cid,)).fetchone()[0], 0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
