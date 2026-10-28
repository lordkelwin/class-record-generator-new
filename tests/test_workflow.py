import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import courses_store
import syllabus_workflow


class SyllabusWorkflowSequentialTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.username = "faculty_tano"
        doc = courses_store.create_course(
            username=self.username,
            course_code="EE 411",
            course_title="Feedback and Control Systems",
            programs=["EE"]
        )
        self.course_id = doc["id"]
        doc = courses_store.find_course(self.course_id)
        doc["workflow"] = syllabus_workflow.default_workflow()
        if not doc.get("blueprint"):
            doc["blueprint"] = {}
        if not doc["blueprint"].get("metadata"):
            doc["blueprint"]["metadata"] = {}
        doc["blueprint"]["metadata"]["course_code"] = "EE 411"
        doc["blueprint"]["metadata"]["course_title"] = "Feedback and Control Systems"
        doc["blueprint"]["metadata"]["course_description"] = "Comprehensive study of electrical networks."
        doc["blueprint"]["course_outcomes"] = [
            {"id": "CLO1", "statement": "Analyze feedback control systems."}
        ]
        doc["blueprint"]["metadata"]["syllabus_assessment_activities"] = [
            {"code": "FA1", "activity": "Seatwork", "weight_pct": 0, "type": "formative"},
            {"code": "SA1", "activity": "Quizzes", "weight_pct": 50, "type": "summative"},
            {"code": "SA2", "activity": "Exam", "weight_pct": 50, "type": "summative"}
        ]
        courses_store.save_course_doc(doc)

    def tearDown(self):
        try:
            courses_store.delete_course(self.username, self.course_id)
        except Exception:
            pass

    def test_complete_sequential_approval_workflow(self):
        c_id = self.course_id

        # Faculty submits
        with self.client.session_transaction() as sess:
            sess["username"] = self.username

        res = self.client.get(f"/api/courses/{c_id}/workflow")
        wf = res.get_json()
        self.assertEqual(wf["status"], "draft")
        self.assertTrue(wf["can_submit"])

        res = self.client.post(f"/api/courses/{c_id}/workflow/submit", json={
            "committee_members": [
                {"username": "faculty_arenga", "name": "Engr. Delan Zoe H. Arenga", "role": "Review Committee Member"},
                {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Member"},
                {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Chair"}
            ]
        })
        self.assertEqual(res.status_code, 200)

        res = self.client.get(f"/api/courses/{c_id}/workflow")
        wf = res.get_json()
        self.assertEqual(wf["status"], "for_committee_review")

        # Faculty cannot edit checklist
        res = self.client.put(f"/api/courses/{c_id}/evaluation-form", json={"responses": {}})
        self.assertEqual(res.status_code, 400)

        # Committee Member 1 evaluates and signs
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_arenga"

        res = self.client.put(f"/api/courses/{c_id}/evaluation-form", json={
            "responses": {"core_1": "FULLY", "int_cdio": "FULLY"},
            "comments": {"core_1": "Complete and compliant."},
            "overall_recommendation": "Approved",
            "recommendations": "Syllabus meets all OBE and CMO standards.",
        })
        self.assertEqual(res.status_code, 200)

        res = self.client.post(f"/api/courses/{c_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Reviewed and fully endorsed by Member 1.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        })
        self.assertEqual(res.status_code, 200)

        # Committee Member 2 signs
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_ravida"
        res = self.client.post(f"/api/courses/{c_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Reviewed and fully endorsed by Member 2.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        })
        self.assertEqual(res.status_code, 200)

        # Committee Chair signs
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_basan"
        res = self.client.post(f"/api/courses/{c_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Chair endorsement.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        })
        self.assertEqual(res.status_code, 200)

        res = self.client.get(f"/api/courses/{c_id}/workflow")
        wf = res.get_json()
        self.assertEqual(wf["status"], "for_program_head")

        # Program Head signs
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_claro"
        res = self.client.post(f"/api/courses/{c_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Endorsed for College QA review.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        })
        self.assertEqual(res.status_code, 200)

        res = self.client.get(f"/api/courses/{c_id}/workflow")
        wf = res.get_json()
        self.assertEqual(wf["status"], "for_qa_countersign")

        # QA Head countersigns
        with self.client.session_transaction() as sess:
            sess["username"] = "qahead_ce"
        res = self.client.post(f"/api/courses/{c_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Countersigned: QA audit complete.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        })
        self.assertEqual(res.status_code, 200)

        res = self.client.get(f"/api/courses/{c_id}/workflow")
        wf = res.get_json()
        self.assertEqual(wf["status"], "for_dean_approval")

        # Dean approves
        with self.client.session_transaction() as sess:
            sess["username"] = "dean_cataytay"
        res = self.client.post(f"/api/courses/{c_id}/workflow/sign", json={
            "decision": "approve",
            "remarks": "Final approval granted. Syllabus locked.",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        })
        self.assertEqual(res.status_code, 200)

        res = self.client.get(f"/api/courses/{c_id}/workflow")
        wf = res.get_json()
        self.assertEqual(wf["status"], "approved")
        self.assertTrue(wf["approved"])
        self.assertTrue(wf["locked"])
        self.assertGreaterEqual(len(wf["signatures"]), 4)

        # PDF exports
        res = self.client.get(f"/api/courses/{c_id}/export-evaluation-pdf")
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.data), 5000)

        res = self.client.get(f"/api/courses/{c_id}/export-pdf")
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.data), 5000)


if __name__ == "__main__":
    unittest.main()
