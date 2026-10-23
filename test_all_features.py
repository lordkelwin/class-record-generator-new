import os
import json
import unittest
from app import app
from auth import _load_users, _save_users, _lock
import syllabus_workflow

class ComprehensiveWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_full_workflow_and_all_requirements(self):
        print("\n=== STEP 1: RESTRICT INSTITUTIONAL REQUESTS FOR REGULAR FACULTY ===")
        # Login as regular faculty (e.g. faculty_tano)
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"
        
        res = self.app.get("/api/workflow/requests")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["can_view_institutional"])
        self.assertEqual(len(data["institutional_requests"]), 0)
        print("PASS: Regular faculty cannot view institutional requests (can_view_institutional=False, list=[]).")

        # Login as admin
        with self.app.session_transaction() as sess:
            sess["username"] = "admin"
        res = self.app.get("/api/workflow/requests")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["can_view_institutional"])
        print("PASS: Admin can view institutional requests (can_view_institutional=True).")

        # Login as dean
        with self.app.session_transaction() as sess:
            sess["username"] = "dean_cataytay"
        res = self.app.get("/api/workflow/requests")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["can_view_institutional"])
        print("PASS: Dean can view institutional requests (can_view_institutional=True).")

        print("\n=== STEP 2: ADMIN FACULTY ROLE ASSIGNMENT (NO SEPARATE ACCOUNTS) ===")
        with self.app.session_transaction() as sess:
            sess["username"] = "admin"

        # 1. Fetch faculty list
        res = self.app.get("/api/admin/faculty-list")
        self.assertEqual(res.status_code, 200)
        fac_list = res.get_json()["faculty"]
        self.assertGreater(len(fac_list), 10)
        print(f"PASS: Admin fetched {len(fac_list)} official faculty members.")

        # 2. Assign faculty_ravida as Program Head - Electronics Engineering (ECE)
        res = self.app.post("/api/admin/users/faculty_ravida/update-role", json={
            "designation": "program_head",
            "program_code": "ECE",
            "position_title": "Program Head - Electronics Engineering",
            "is_admin": False
        })
        self.assertEqual(res.status_code, 200)
        res_data = res.get_json()
        self.assertTrue(res_data["success"])
        self.assertIn("program_head", res_data["user"]["workflow_roles"])
        self.assertEqual(res_data["user"]["position_title"], "Program Head - Electronics Engineering")
        print("PASS: Admin successfully updated faculty_ravida to Program Head - Electronics Engineering.")

        # Verify in signatories list
        res = self.app.get("/api/workflow/signatories")
        self.assertEqual(res.status_code, 200)
        sigs = res.get_json()
        ravida_ph = next((p for p in sigs["program_heads"] if p["username"] == "faculty_ravida"), None)
        self.assertIsNotNone(ravida_ph)
        self.assertEqual(ravida_ph["position_title"], "Program Head - Electronics Engineering")
        print("PASS: Updated Program Head reflected dynamically in signatories roster.")

        # Revert faculty_ravida to regular faculty
        self.app.post("/api/admin/users/faculty_ravida/update-role", json={
            "designation": "faculty",
            "position_title": "Faculty Member",
            "is_admin": False
        })

        print("\n=== STEP 3: SEQUENTIAL REVIEW COMMITTEE APPROVAL ORDER ===")
        # Create a new test course under faculty_tano
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        course_payload = {
            "course_code": "EE 999",
            "course_title": "Sequential Review Committee Test Subject",
            "section": "EE 4X",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "blueprint": {
                "metadata": {
                    "course_code": "EE 999",
                    "course_title": "Sequential Review Committee Test Subject",
                    "course_description": "Comprehensive study of electrical networks, circuits, and advanced engineering principles.",
                    "section": "EE 4X",
                    "program_code": "EE",
                    "semester_ay": "1st Semester, A.Y. 2026-2027",
                    "credit_units": 3,
                    "faculty_name": "Engr. Elwin Jay J. Tano",
                    "syllabus_assessment_activities": [
                        {"name": "Preliminary Examination", "weight": 25}
                    ]
                },
                "course_outcomes": [
                    {"code": "CLO1", "description": "Demonstrate sequential workflow logic and analysis."}
                ],
                "clos": [
                    {"code": "CLO1", "description": "Demonstrate sequential workflow logic and analysis."}
                ],
                "assessment_tasks": [
                    {"name": "Preliminary Examination", "type": "Exam", "weight": 25}
                ],
                "rubrics": []
            }
        }
        res = self.app.post("/api/courses", json=course_payload)
        self.assertEqual(res.status_code, 201)
        course_id = res.get_json()["course"]["id"]
        print(f"Created test course: {course_id}")

        # Submit syllabus with 3 committee members:
        # Chair: faculty_basan
        # Member 1: faculty_arenga
        # Member 2: faculty_ravida
        submit_payload = {
            "committee_members": [
                {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Chair"},
                {"username": "faculty_arenga", "name": "Engr. Delan Zoe H. Arenga", "role": "Review Committee Member"},
                {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Member"}
            ],
            "assigned_committee": "faculty_basan",
            "assigned_committee_name": "Engr. Nikka Samantha A. Basan",
            "submission_notes": "Initial submission testing member approvals prior to chair endorsement."
        }
        res = self.app.post(f"/api/courses/{course_id}/workflow/submit", json=submit_payload)
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "for_committee_review")
        print("PASS: Course submitted. Status is 'for_committee_review'.")

        # Check if Chair (faculty_basan) can sign at this stage:
        # Chair should NOT be able to sign until members have approved
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_basan"
        res = self.app.post(f"/api/courses/{course_id}/workflow/sign", json={
            "decision": "approve",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Only the Review Committee Members", res.get_json()["error"])
        print("PASS: Committee Chair blocked from signing before committee members.")

        # Member 1 saves evaluation checklist with overall recommendation
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_arenga"
        res = self.app.put(f"/api/courses/{course_id}/evaluation-form", json={
            "overall_recommendation": "approved_without_revision",
            "general_remarks": "Syllabus strictly complies with OBE and CMO guidelines.",
            "responses": {}
        })
        self.assertEqual(res.status_code, 200)

        # Member 1 (faculty_arenga) signs:
        res = self.app.post(f"/api/courses/{course_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Member 1 evaluation completed.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "for_committee_review")
        print("PASS: Member 1 signed. 1/2 members signed. Status remains 'for_committee_review'.")

        # Member 2 (faculty_ravida) signs:
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_ravida"
        res = self.app.post(f"/api/courses/{course_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Member 2 evaluation completed.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "for_committee_chair")
        print("PASS: All members have signed! Status automatically advanced to 'for_committee_chair'.")

        # Now Committee Chair (faculty_basan) signs and endorses:
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_basan"
        res = self.app.post(f"/api/courses/{course_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Committee Chair endorsed review to Program Head.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "for_program_head")
        print("PASS: Committee Chair signed. Status advanced to 'for_program_head'.")

        # Program Head (faculty_claro) signs:
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_claro"
        res = self.app.post(f"/api/courses/{course_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Endorsed by Program Head.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "for_qa_countersign")
        print("PASS: Program Head signed. Status advanced to 'for_qa_countersign'.")

        # QA Head (qahead_ce) countersigns:
        with self.app.session_transaction() as sess:
            sess["username"] = "qahead_ce"
        res = self.app.post(f"/api/courses/{course_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Countersigned by College QA Head.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "for_dean_approval")
        print("PASS: QA Head countersigned. Status advanced to 'for_dean_approval'.")

        # Dean (dean_cataytay) gives final approval:
        with self.app.session_transaction() as sess:
            sess["username"] = "dean_cataytay"
        res = self.app.post(f"/api/courses/{course_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Approved and locked by Dean.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "approved")
        self.assertIsNotNone(wf["approved_at"])
        print("PASS: Dean approved! Status is 'approved' and syllabus is officially locked.")

        print("\n=== STEP 4: LOCKED SYLLABUS & REVISION REQUEST ===")
        # Owner checks workflow state
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"
        res = self.app.get(f"/api/courses/{course_id}/workflow")
        self.assertEqual(res.status_code, 200)
        wf_data = res.get_json()
        self.assertEqual(wf_data["status"], "approved")
        self.assertTrue(wf_data.get("can_request_revision"))
        print("PASS: Approved syllabus displays can_request_revision=True to faculty owner.")

        # Submit revision request
        rev_reason = "Updating assessment rubrics and course outcomes for Cycle 2."
        res = self.app.post(f"/api/courses/{course_id}/workflow/request-revision", json={
            "reason": rev_reason
        })
        self.assertEqual(res.status_code, 200)
        rev_data = res.get_json()
        wf_rev = rev_data["workflow"]
        self.assertEqual(wf_rev["status"], "draft")
        self.assertEqual(wf_rev["cycle"], 2)
        self.assertEqual(len(wf_rev["signatures"]), 0)
        self.assertTrue(wf_rev["can_submit"])
        self.assertEqual(wf_rev.get("revision_reason"), rev_reason)
        print("PASS: Revision request approved. Syllabus unlocked for editing, cycle incremented to 2, signatures reset.")

        # Clean up test course
        self.app.delete(f"/api/courses/{course_id}")
        print(f"Cleaned up test course {course_id}.")
        print("\n=== ALL UNIT & INTEGRATION TESTS PASSED PERFECTLY ===")

if __name__ == "__main__":
    unittest.main()
