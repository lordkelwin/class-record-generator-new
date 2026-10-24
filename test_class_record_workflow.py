# test_class_record_workflow.py
# Comprehensive automated test suite for Class Record Workflow & Staff Oversight Portal

import unittest
import json
import os
from werkzeug.security import generate_password_hash
from app import app
import auth
import courses_store
import class_record_workflow
import oversight_report_generator

class TestClassRecordWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

        # Ensure test accounts exist and have e-signatures
        auth.ensure_default_admin()
        users = auth._load_users()
        fake_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        # 1. Ordinary faculty
        if "faculty_tano" not in users:
            users["faculty_tano"] = {
                "full_name": "Engr. Elwin Jay J. Tano", "role": "faculty", "workflow_roles": ["review_committee"],
                "position_title": "Faculty Member", "program_codes": ["EE"], "password_hash": generate_password_hash("password123")
            }
        users["faculty_tano"]["signature_data"] = fake_sig
        users["faculty_tano"]["password_hash"] = generate_password_hash("password123")

        # 2. Program Head (EE)
        if "faculty_claro" not in users:
            users["faculty_claro"] = {
                "full_name": "Engr. Charito O. Claro", "role": "faculty", "workflow_roles": ["program_head", "review_committee"],
                "position_title": "Program Head - Electrical Engineering", "program_codes": ["EE", "*"], "password_hash": generate_password_hash("password123")
            }
        users["faculty_claro"]["signature_data"] = fake_sig
        users["faculty_claro"]["workflow_roles"] = ["program_head", "review_committee"]
        users["faculty_claro"]["password_hash"] = generate_password_hash("password123")

        # 3. Associate Dean
        if "assoc_dean" not in users:
            users["assoc_dean"] = {
                "full_name": "Engr. Delan Zoe H. Arenga", "role": "faculty", "workflow_roles": ["associate_dean", "review_committee"],
                "position_title": "Associate Dean, College of Engineering", "program_codes": ["*"], "password_hash": generate_password_hash("password123")
            }
        users["assoc_dean"]["signature_data"] = fake_sig
        users["assoc_dean"]["workflow_roles"] = ["associate_dean", "review_committee"]
        users["assoc_dean"]["password_hash"] = generate_password_hash("password123")

        # 4. QA Head
        if "qahead_ce" not in users:
            users["qahead_ce"] = {
                "full_name": "Engr. College QA Head", "role": "faculty", "workflow_roles": ["qa_head"],
                "position_title": "College Quality Assurance Head", "program_codes": ["*"], "password_hash": generate_password_hash("password123")
            }
        users["qahead_ce"]["signature_data"] = fake_sig
        users["qahead_ce"]["workflow_roles"] = ["qa_head"]
        users["qahead_ce"]["password_hash"] = generate_password_hash("password123")

        # 5. Dean
        if "dean_cataytay" not in users:
            users["dean_cataytay"] = {
                "full_name": "Engr. Joie D. Cataytay, Ph.D.", "role": "faculty", "workflow_roles": ["dean", "review_committee"],
                "position_title": "Dean, College of Engineering", "program_codes": ["*"], "password_hash": generate_password_hash("password123")
            }
        users["dean_cataytay"]["signature_data"] = fake_sig
        users["dean_cataytay"]["workflow_roles"] = ["dean", "review_committee"]
        users["dean_cataytay"]["password_hash"] = generate_password_hash("password123")

        # 6. Staff
        if "staff_office" not in users:
            users["staff_office"] = {
                "full_name": "Academic Affairs Staff", "role": "staff", "workflow_roles": ["staff"],
                "position_title": "Academic Programs Staff (Oversight)", "program_codes": ["*"],
                "can_access_faculty_tools": False, "password_hash": generate_password_hash("password123")
            }
        users["staff_office"]["role"] = "staff"
        users["staff_office"]["workflow_roles"] = ["staff"]
        users["staff_office"]["can_access_faculty_tools"] = False
        users["staff_office"]["password_hash"] = generate_password_hash("password123")

        auth._save_users(users)

    def login(self, username):
        with self.client.session_transaction() as sess:
            sess["username"] = username

    def create_test_course(self, owner_username, code="EE 301", title="Signals and Systems", sec="EE 3A"):
        course = courses_store.create_course(owner_username, course_code=code, course_title=title, section=sec)
        bp = course.get("blueprint") or {}
        bp["students"] = [
            {"student_id": "2024-00101", "first_name": "Juan", "last_name": "Dela Cruz", "scores": {"SA1_1__CLO1": 28, "SA1_2__CLO2": 26}},
            {"student_id": "2024-00102", "first_name": "Maria", "last_name": "Santos", "scores": {"SA1_1__CLO1": 30, "SA1_2__CLO2": 29}},
        ]
        course["blueprint"] = bp
        course["workflow"] = {"status": "approved", "is_locked": True}
        return courses_store.save_course_doc(course)

    def test_01_ordinary_faculty_class_record_workflow(self):
        """Test ordinary faculty: Faculty -> Program Head -> QA Head -> Dean Approval & Permanent Lock."""
        doc = self.create_test_course("faculty_tano", code="EE 301", title="Control Theory")
        cid = doc["id"]

        # 1. Faculty Finalizes & Submits Class Record
        self.login("faculty_tano")
        res = self.client.post(f"/api/courses/{cid}/class-record/submit", json={
            "notes": "All final student grades computed and checked.",
            "signature_data": "data:image/png;base64,fakeSig"
        })
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        data = res.get_json()
        self.assertEqual(data["class_record_workflow"]["status"], "for_program_head")
        self.assertTrue(data["class_record_workflow"]["is_locked"])

        # 2. Ordinary Faculty cannot endorse their own step
        res_self = self.client.post(f"/api/courses/{cid}/class-record/sign", json={"decision": "approve"})
        self.assertEqual(res_self.status_code, 400)

        # 3. Program Head Endorsement
        self.login("faculty_claro")
        res_ph = self.client.post(f"/api/courses/{cid}/class-record/sign", json={
            "decision": "approve",
            "remarks": "Endorsed. Grades adhere to BSEE OBE curriculum.",
            "signature_data": "data:image/png;base64,fakePhSig"
        })
        self.assertEqual(res_ph.status_code, 200)
        self.assertEqual(res_ph.get_json()["class_record_workflow"]["status"], "for_qa_countersign")

        # 4. College QA Countersign
        self.login("qahead_ce")
        res_qa = self.client.post(f"/api/courses/{cid}/class-record/sign", json={
            "decision": "approve",
            "remarks": "Verified assessment rubrics and transmuted scores.",
            "signature_data": "data:image/png;base64,fakeQASig"
        })
        self.assertEqual(res_qa.status_code, 200)
        self.assertEqual(res_qa.get_json()["class_record_workflow"]["status"], "for_dean_approval")

        # 5. College Dean Final Approval
        self.login("dean_cataytay")
        res_dean = self.client.post(f"/api/courses/{cid}/class-record/sign", json={
            "decision": "approve",
            "remarks": "Approved and sealed into permanent institutional records.",
            "signature_data": "data:image/png;base64,fakeDeanSig"
        })
        self.assertEqual(res_dean.status_code, 200)
        final_wf = res_dean.get_json()["class_record_workflow"]
        self.assertEqual(final_wf["status"], "finalized")
        self.assertTrue(final_wf["is_finalized"])
        self.assertTrue(final_wf["is_locked"])
        self.assertEqual(len(final_wf["signatures"]), 4) # Faculty + PH + QA + Dean

    def test_02_program_head_owner_routes_to_associate_dean(self):
        """Test Program Head course: Faculty (PH) -> Associate Dean -> QA Head -> Dean."""
        doc = self.create_test_course("faculty_claro", code="EE 411", title="Power Systems")
        cid = doc["id"]

        # 1. Program Head finalizes their own course
        self.login("faculty_claro")
        res = self.client.post(f"/api/courses/{cid}/class-record/submit", json={
            "notes": "Grades finalized by Program Head.",
            "signature_data": "data:image/png;base64,fakeSig"
        })
        self.assertEqual(res.status_code, 200)
        # MUST route to for_associate_dean because owner is Program Head
        self.assertEqual(res.get_json()["class_record_workflow"]["status"], "for_associate_dean")

        # 2. Associate Dean Endorsement
        self.login("assoc_dean")
        res_ad = self.client.post(f"/api/courses/{cid}/class-record/sign", json={
            "decision": "approve",
            "remarks": "Endorsed Program Head course on behalf of Academic Affairs.",
            "signature_data": "data:image/png;base64,fakeAdSig"
        })
        self.assertEqual(res_ad.status_code, 200)
        self.assertEqual(res_ad.get_json()["class_record_workflow"]["status"], "for_qa_countersign")

        # 3. College QA Countersign
        self.login("qahead_ce")
        res_qa = self.client.post(f"/api/courses/{cid}/class-record/sign", json={
            "decision": "approve",
            "remarks": "Countersigned.",
            "signature_data": "data:image/png;base64,fakeQASig"
        })
        self.assertEqual(res_qa.status_code, 200)
        self.assertEqual(res_qa.get_json()["class_record_workflow"]["status"], "for_dean_approval")

        # 4. College Dean Approval
        self.login("dean_cataytay")
        res_dean = self.client.post(f"/api/courses/{cid}/class-record/sign", json={
            "decision": "approve",
            "remarks": "Final Dean Approval granted.",
            "signature_data": "data:image/png;base64,fakeDeanSig"
        })
        self.assertEqual(res_dean.status_code, 200)
        self.assertEqual(res_dean.get_json()["class_record_workflow"]["status"], "finalized")

    def test_03_grade_locking_and_revision_unfreeze(self):
        """Test grade locking enforcement: editing student scores is prevented when locked, and unlocked upon request."""
        doc = self.create_test_course("faculty_tano", code="EE 322", title="Electromagnetics")
        cid = doc["id"]

        # Submit to enter lock state
        self.login("faculty_tano")
        self.client.post(f"/api/courses/{cid}/class-record/submit", json={"signature_data": "data:image/png;base64,fakeSig"})

        # Verify doc is locked
        loaded = courses_store.find_course(cid)
        self.assertTrue(class_record_workflow.is_class_record_locked(loaded))

        # Attempt to modify student scores while locked
        tampered_bp = dict(loaded["blueprint"])
        tampered_bp["students"] = [
            {"student_id": "2024-99999", "first_name": "Tampered", "last_name": "Student", "scores": {"SA1_1__CLO1": 100}}
        ]
        saved = courses_store.save_course("faculty_tano", cid, {"blueprint": tampered_bp})
        self.assertEqual(saved["blueprint"]["students"][0]["student_id"], "2024-00101")
        self.assertNotEqual(saved["blueprint"]["students"][0]["student_id"], "2024-99999")

        # Complete approval to finalize
        self.login("faculty_claro")
        self.client.post(f"/api/courses/{cid}/class-record/sign", json={"decision": "approve", "signature_data": "data:image/png;base64,fakeSig"})
        self.login("qahead_ce")
        self.client.post(f"/api/courses/{cid}/class-record/sign", json={"decision": "approve", "signature_data": "data:image/png;base64,fakeSig"})
        self.login("dean_cataytay")
        self.client.post(f"/api/courses/{cid}/class-record/sign", json={"decision": "approve", "signature_data": "data:image/png;base64,fakeSig"})

        # Request Grade Revision
        self.login("faculty_tano")
        res_rev = self.client.post(f"/api/courses/{cid}/class-record/request-revision", json={
            "reason": "Corrected student encoded midterm exam score from 28 to 30."
        })
        self.assertEqual(res_rev.status_code, 200)
        unlocked_wf = res_rev.get_json()["class_record_workflow"]
        self.assertEqual(unlocked_wf["status"], "draft")
        self.assertFalse(unlocked_wf["is_locked"])
        self.assertEqual(unlocked_wf["cycle"], 2)

    def test_04_staff_oversight_analytics_and_report_generation(self):
        """Test staff oversight dashboard: access, analytics metrics, and PDF generation."""
        # 1. Staff access to workflow requests
        self.login("staff_office")
        res = self.client.get("/api/workflow/requests")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["can_view_institutional"])
        self.assertTrue(data["is_staff"])
        self.assertFalse(data["can_access_faculty_tools"])
        self.assertIn("analytics", data)
        self.assertIn("institutional_class_records", data)

        # 2. Staff cannot sign institutional steps
        courses = data["institutional_class_records"]
        if courses:
            cid = courses[0]["id"]
            res_sign = self.client.post(f"/api/courses/{cid}/class-record/sign", json={"decision": "approve"})
            self.assertEqual(res_sign.status_code, 400) # Staff blocked from signing

        # 3. Analytics API endpoint
        res_an = self.client.get("/api/workflow/analytics")
        self.assertEqual(res_an.status_code, 200)
        an_data = res_an.get_json()
        self.assertIn("total_courses", an_data)
        self.assertIn("syllabus_compliance_pct", an_data)
        self.assertIn("class_record_compliance_pct", an_data)
        self.assertIn("programs", an_data)
        self.assertIn("bottlenecks", an_data)

        # 4. Auto-Generated Institutional Oversight Report PDF
        res_pdf = self.client.get("/api/workflow/oversight-report")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.content_type, "application/pdf")
        pdf_bytes = res_pdf.get_data()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Generated report is not a valid PDF")
        self.assertGreater(len(pdf_bytes), 1000)

if __name__ == "__main__":
    unittest.main()
