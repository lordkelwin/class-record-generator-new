import unittest
import json
import uuid
import app as flask_app
import syllabus_workflow
import courses_store
import auth

class SyllabusRevisionWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["SECRET_KEY"] = "testing-secret-key"
        self.app = flask_app.app.test_client()
        self.created_course_ids = []

    def tearDown(self):
        # Clean up any created test courses
        for cid, owner in self.created_course_ids:
            try:
                courses_store.delete_course(owner, cid)
            except Exception:
                pass

    def _create_and_approve_course(self, owner_username="faculty_tano", program="EE"):
        doc = courses_store.create_course(
            username=owner_username,
            course_code=f"{program} 999",
            course_title="OBE Advanced Testing",
            programs=[program]
        )
        cid = doc["id"]
        self.created_course_ids.append((cid, owner_username))

        doc["workflow"]["status"] = "approved"
        doc["workflow"]["cycle"] = 1
        doc["workflow"]["current_step"] = "completed"
        doc["workflow"]["approved_at"] = "2026-10-24T04:00:00"
        doc["workflow"]["signatures"] = [
            {"role": "committee_member", "name": "Reviewer 1", "signed_at": "2026-10-24T00:00:00"},
            {"role": "committee_chair", "name": "Chair Person", "signed_at": "2026-10-24T01:00:00"},
            {"role": "program_head", "name": "Program Head", "signed_at": "2026-10-24T02:00:00"},
            {"role": "qa_head", "name": "QA Head", "signed_at": "2026-10-24T03:00:00"},
            {"role": "dean", "name": "College Dean", "signed_at": "2026-10-24T04:00:00"}
        ]
        doc["workflow"]["history"] = []
        courses_store.save_course_doc(doc)
        return cid

    def test_ordinary_faculty_revision_flow(self):
        """Ordinary faculty course revision routes to Program Head -> Dean -> Draft (Cycle 2)"""
        cid = self._create_and_approve_course("faculty_tano", "EE")

        # 1. Faculty requests revision
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        rev_reason = "Updating textbooks and OBE grading scheme for AY 2026-2027"
        res = self.app.post(f"/api/courses/{cid}/workflow/request-revision", json={"reason": rev_reason})
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "revision_for_program_head")
        self.assertEqual(wf.get("revision_reason"), rev_reason)

        # 2. Check permissions: Faculty owner cannot review their own revision request
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertFalse(res.get_json().get("user_can_act"))
        self.assertFalse(res.get_json().get("can_sign"))

        # Other regular faculty member cannot act
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_ramos"
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertFalse(res.get_json().get("user_can_act"))

        # Program Head of different program (e.g. ME: faculty_tongson) cannot act
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tongson"
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertFalse(res.get_json().get("user_can_act"))

        # Program Head of EE (faculty_claro) CAN act and it appears in requests
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_claro"
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertTrue(res.get_json().get("user_can_act"))

        reqs_res = self.app.get("/api/workflow/requests")
        self.assertEqual(reqs_res.status_code, 200)
        pending_ids = [item["id"] for item in reqs_res.get_json().get("pending_action_for_me", [])]
        self.assertIn(cid, pending_ids)

        # 3. Program Head endorses revision request
        res = self.app.post(f"/api/courses/{cid}/workflow/revision-action", json={
            "action": "endorse",
            "remarks": "Endorsed for college dean review and revision unlock."
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "revision_for_dean")

        # 4. Program head can no longer act
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertFalse(res.get_json().get("user_can_act"))

        # Dean (dean_cataytay) CAN act and it appears in Dean's pending actions
        with self.app.session_transaction() as sess:
            sess["username"] = "dean_cataytay"
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertTrue(res.get_json().get("user_can_act"))

        reqs_res = self.app.get("/api/workflow/requests")
        pending_ids = [item["id"] for item in reqs_res.get_json().get("pending_action_for_me", [])]
        self.assertIn(cid, pending_ids)

        # 5. Dean approves revision request
        res = self.app.post(f"/api/courses/{cid}/workflow/revision-action", json={
            "action": "approve",
            "remarks": "Approved by Dean. Syllabus unlocked for Cycle 2."
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "draft")
        self.assertEqual(wf["cycle"], 2)
        self.assertEqual(len(wf["signatures"]), 0)

        # 6. Faculty owner now sees draft status and can_submit=True
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["cycle"], 2)
        self.assertTrue(data["can_submit"])

    def test_program_head_owner_revision_flow(self):
        """Program Head owner course revision routes to Associate Dean -> Dean -> Draft (Cycle 2)"""
        # Program Head (faculty_claro) owns this course
        cid = self._create_and_approve_course("faculty_claro", "EE")

        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_claro"

        rev_reason = "Curricular alignment per CHED memo"
        res = self.app.post(f"/api/courses/{cid}/workflow/request-revision", json={"reason": rev_reason})
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        # Routed directly to Associate Dean because owner is Program Head
        self.assertEqual(wf["status"], "revision_for_associate_dean")

        # Program Head owner CANNOT review their own revision request
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertFalse(res.get_json().get("user_can_act"))

        # Associate Dean (assoc_dean) CAN act and it appears in Associate Dean's pending actions
        with self.app.session_transaction() as sess:
            sess["username"] = "assoc_dean"
        res = self.app.get(f"/api/courses/{cid}/workflow")
        self.assertTrue(res.get_json().get("user_can_act"))

        reqs_res = self.app.get("/api/workflow/requests")
        pending_ids = [item["id"] for item in reqs_res.get_json().get("pending_action_for_me", [])]
        self.assertIn(cid, pending_ids)

        # Associate Dean endorses
        res = self.app.post(f"/api/courses/{cid}/workflow/revision-action", json={
            "action": "endorse",
            "remarks": "Endorsed by Associate Dean."
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "revision_for_dean")

        # Dean approves
        with self.app.session_transaction() as sess:
            sess["username"] = "dean_cataytay"
        res = self.app.post(f"/api/courses/{cid}/workflow/revision-action", json={
            "action": "approve",
            "remarks": "Approved by Dean."
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "draft")
        self.assertEqual(wf["cycle"], 2)

    def test_rejection_by_program_head_restores_approved(self):
        """Rejecting revision request restores status to 'approved' and syllabus remains locked"""
        cid = self._create_and_approve_course("faculty_tano", "EE")

        # Faculty requests revision
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"
        res = self.app.post(f"/api/courses/{cid}/workflow/request-revision", json={"reason": "Minor rewording"})
        self.assertEqual(res.status_code, 200)

        # Program Head rejects revision request
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_claro"
        res = self.app.post(f"/api/courses/{cid}/workflow/revision-action", json={
            "action": "reject",
            "remarks": "Minor edits do not warrant opening a new syllabus cycle at mid-semester."
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        # Status returns to approved
        self.assertEqual(wf["status"], "approved")

        # Course is locked again
        doc = courses_store.find_course(cid)
        self.assertTrue(syllabus_workflow.is_approved(doc))
        self.assertTrue(syllabus_workflow.is_syllabus_locked(doc))

    def test_rejection_by_dean_restores_approved(self):
        """Rejecting revision request by Dean restores status to 'approved'"""
        cid = self._create_and_approve_course("faculty_tano", "EE")

        # Faculty requests revision
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_tano"
        self.app.post(f"/api/courses/{cid}/workflow/request-revision", json={"reason": "Mid-term revisions"})

        # Program Head endorses
        with self.app.session_transaction() as sess:
            sess["username"] = "faculty_claro"
        self.app.post(f"/api/courses/{cid}/workflow/revision-action", json={"action": "endorse", "remarks": "Endorsed"})

        # Dean rejects
        with self.app.session_transaction() as sess:
            sess["username"] = "dean_cataytay"
        res = self.app.post(f"/api/courses/{cid}/workflow/revision-action", json={
            "action": "reject",
            "remarks": "Denied: AY curriculum revisions closed."
        })
        self.assertEqual(res.status_code, 200)
        wf = res.get_json()["workflow"]
        self.assertEqual(wf["status"], "approved")

        doc = courses_store.find_course(cid)
        self.assertTrue(syllabus_workflow.is_approved(doc))
        self.assertTrue(syllabus_workflow.is_syllabus_locked(doc))

if __name__ == "__main__":
    unittest.main()
