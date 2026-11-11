import unittest
import json
import io
from app import app
import courses_store
import tos_workflow
import tos_pdf_generator
import syllabus_workflow

class TestTosModule(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.test_course_id = "test_tos_course_999"
        
        # Create a mock test course document
        doc = courses_store.get_default_blueprint(include_sample_scores=False).to_dict()
        doc["metadata"]["course_code"] = "EE 411"
        doc["metadata"]["course_title"] = "Feedback and Control Systems"
        doc["metadata"]["credit_units"] = "3.0 Units"
        doc["metadata"]["semester_ay"] = "1st Semester, A.Y. 2026-2027"
        
        # Course doc structure
        self.course_doc = {
            "id": self.test_course_id,
            "course_code": "EE 411",
            "course_title": "Feedback and Control Systems",
            "section": "EE 4A",
            "owner": "faculty_tano",
            "owner_name": "Elwin Jay J. Tano",
            "blueprint": doc,
            "workflow": {
                "status": "draft",
                "committee_members": [
                    {"name": "Nikka Basan", "username": "faculty_basan", "role": "Review Committee Chair"},
                    {"name": "Delan Arenga", "username": "faculty_arenga", "role": "Review Committee Member"},
                    {"name": "Kim Ravida", "username": "faculty_ravida", "role": "Review Committee Member"},
                ],
                "assigned_committee": "faculty_basan",
                "assigned_committee_name": "Nikka Basan",
                "signatures": [],
            }
        }
        courses_store.save_course_doc(self.course_doc)

    def tearDown(self):
        # Clean up test course
        courses_store.delete_course("faculty_tano", self.test_course_id)
        # Restore data directory state if needed
        import os
        for root, dirs, files in os.walk(courses_store.COURSES_BASE_DIR):
            for f in files:
                if self.test_course_id in f:
                    try:
                        os.remove(os.path.join(root, f))
                    except Exception:
                        pass

    # =========================================================================
    # 1. PREREQUISITE LOCKING TESTS
    # =========================================================================
    def test_tos_gated_when_syllabus_not_approved(self):
        """TOS endpoints must return 403 Forbidden if parent Course Syllabus is not Dean-approved."""
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        # 1. GET TOS
        res = self.client.get(f"/api/courses/{self.test_course_id}/tos?term=midterm")
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertTrue(data.get("is_locked"))
        self.assertIn("Sequential Gating Locked", data.get("error", ""))

        # 2. POST Sync
        res_sync = self.client.post(f"/api/courses/{self.test_course_id}/tos/sync", json={"term": "midterm"})
        self.assertEqual(res_sync.status_code, 403)

        # 3. PUT Draft
        res_put = self.client.put(f"/api/courses/{self.test_course_id}/tos", json={"term": "midterm", "tos": {}})
        self.assertEqual(res_put.status_code, 403)

        # 4. POST Submit
        res_sub = self.client.post(f"/api/courses/{self.test_course_id}/tos/submit", json={"term": "midterm"})
        self.assertEqual(res_sub.status_code, 403)

        # 5. Export PDF
        res_pdf = self.client.get(f"/api/courses/{self.test_course_id}/tos/export-pdf?term=midterm")
        self.assertEqual(res_pdf.status_code, 403)

    def test_tos_admin_bypass_prerequisite(self):
        """Admin can inspect TOS even before syllabus finalization."""
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["role"] = "admin"

        res = self.client.get(f"/api/courses/{self.test_course_id}/tos?term=midterm")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("tos", data)
        self.assertIn("permissions", data)

    # =========================================================================
    # 2. SYLLABUS SYNCHRONIZATION & DATA MODEL TESTS
    # =========================================================================
    def test_tos_sync_and_term_selection(self):
        """TOS pulls syllabus details, topics, CLOs, and committee members for Midterm & Final terms."""
        # Approve the syllabus first
        self.course_doc["workflow"]["status"] = "approved"
        self.course_doc["workflow"]["approved_at"] = "2026-11-10T10:00:00"
        courses_store.save_course_doc(self.course_doc)

        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        # Fetch Midterm TOS
        res_mid = self.client.get(f"/api/courses/{self.test_course_id}/tos?term=midterm")
        self.assertEqual(res_mid.status_code, 200)
        mid_data = res_mid.get_json()["tos"]
        self.assertEqual(mid_data["term"], "midterm")
        self.assertEqual(mid_data["course_code"], "EE 411")
        self.assertIn("Midterm Examination", mid_data["examination_period"])
        self.assertGreater(len(mid_data["rows"]), 0)
        self.assertEqual(mid_data["committee_chair_name"], "Nikka Basan")

        # Fetch Final Term TOS
        res_fin = self.client.get(f"/api/courses/{self.test_course_id}/tos?term=final")
        self.assertEqual(res_fin.status_code, 200)
        fin_data = res_fin.get_json()["tos"]
        self.assertEqual(fin_data["term"], "final")
        self.assertIn("Final Term Examination", fin_data["examination_period"])
        self.assertGreater(len(fin_data["rows"]), 0)

        # Totals computation test
        totals = mid_data["totals"]
        self.assertIn("total_points", totals)
        self.assertIn("pct_remembering", totals)
        self.assertIn("pct_understanding", totals)
        self.assertIn("pct_applying_analyzing", totals)
        self.assertIn("pct_evaluating_creating", totals)

    # =========================================================================
    # 3. 5-STAGE APPROVAL WORKFLOW & EDIT LOCKING TESTS
    # =========================================================================
    def test_5_stage_workflow_lifecycle(self):
        """Tests complete 5-stage sequential lifecycle from drafting to Dean sealing."""
        # Approve the syllabus
        self.course_doc["workflow"]["status"] = "approved"
        self.course_doc["workflow"]["approved_at"] = "2026-11-10T10:00:00"
        courses_store.save_course_doc(self.course_doc)

        # STAGE 1: Faculty Drafting & Submit
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        # Faculty saves draft
        put_res = self.client.put(f"/api/courses/{self.test_course_id}/tos", json={
            "term": "midterm",
            "tos": {
                "revision_type": "revised",
                "rows": [
                    {
                        "topic": "Topic 1: System Transfer Functions",
                        "clo": "CLO1",
                        "remembering": 5,
                        "understanding": 5,
                        "applying_analyzing": 10,
                        "evaluating_creating": 5,
                        "time_allotment_hours": 9.0,
                    }
                ]
            }
        })
        self.assertEqual(put_res.status_code, 200)

        # Faculty submits with signature
        sub_res = self.client.post(f"/api/courses/{self.test_course_id}/tos/submit", json={
            "term": "midterm",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })
        self.assertEqual(sub_res.status_code, 200)
        tos_state = sub_res.get_json()["tos"]
        self.assertEqual(tos_state["status"], "committee_review")
        self.assertEqual(tos_state["stage"], 2)

        # Verify editing is locked for faculty after submission
        put_locked = self.client.put(f"/api/courses/{self.test_course_id}/tos", json={"term": "midterm", "tos": {}})
        self.assertEqual(put_locked.status_code, 403)

        # STAGE 2: Committee Members Review & Form completion
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_arenga"
            sess["role"] = "faculty"
            sess["workflow_roles"] = ["review_committee"]

        rev_res = self.client.post(f"/api/courses/{self.test_course_id}/tos/review", json={
            "term": "midterm",
            "comments": "The topics are well-balanced and strictly match the course learning plan.",
            "recommendation": "approved_without_revision",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "decision": "approved"
        })
        self.assertEqual(rev_res.status_code, 200)
        tos_state = rev_res.get_json()["tos"]
        self.assertEqual(tos_state["status"], "committee_head_review")
        self.assertEqual(tos_state["stage"], 3)
        self.assertEqual(tos_state["review_form"]["recommendation"], "approved_without_revision")

        # STAGE 3: Committee Chair Endorsement
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_basan"
            sess["role"] = "faculty"
            sess["workflow_roles"] = ["review_committee", "review_committee_chair"]

        end_res = self.client.post(f"/api/courses/{self.test_course_id}/tos/endorse", json={
            "term": "midterm",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "decision": "approved",
            "remarks": "Endorsed for QA compliance checking."
        })
        self.assertEqual(end_res.status_code, 200)
        tos_state = end_res.get_json()["tos"]
        self.assertEqual(tos_state["status"], "qa_review")
        self.assertEqual(tos_state["stage"], 4)

        # STAGE 4: QA Head Verification
        with self.client.session_transaction() as sess:
            sess["username"] = "qahead_ce"
            sess["role"] = "faculty"
            sess["workflow_roles"] = ["qa_head"]

        qa_res = self.client.post(f"/api/courses/{self.test_course_id}/tos/qa-review", json={
            "term": "midterm",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "decision": "approved",
            "remarks": "Verified compliant with OBE TOS guidelines."
        })
        self.assertEqual(qa_res.status_code, 200)
        tos_state = qa_res.get_json()["tos"]
        self.assertEqual(tos_state["status"], "for_dean_approval")
        self.assertEqual(tos_state["stage"], 5)

        # STAGE 5: College Dean Approval & Sealing
        with self.client.session_transaction() as sess:
            sess["username"] = "dean_cataytay"
            sess["role"] = "faculty"
            sess["workflow_roles"] = ["dean"]

        dean_res = self.client.post(f"/api/courses/{self.test_course_id}/tos/approve", json={
            "term": "midterm",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "decision": "approved"
        })
        self.assertEqual(dean_res.status_code, 200)
        tos_state = dean_res.get_json()["tos"]
        self.assertEqual(tos_state["status"], "approved")
        self.assertIsNotNone(tos_state["approved_at"])
        self.assertIsNotNone(tos_state["signatures"]["dean"])

    def test_return_for_revision_unlocks_editing(self):
        """Returning a TOS at any stage resets status to 'returned' and unlocks editing for faculty."""
        # Approve syllabus
        self.course_doc["workflow"]["status"] = "approved"
        self.course_doc["workflow"]["approved_at"] = "2026-11-10T10:00:00"
        courses_store.save_course_doc(self.course_doc)

        # Faculty submits
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        self.client.post(f"/api/courses/{self.test_course_id}/tos/submit", json={
            "term": "midterm",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })

        # Committee returns for revision
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_arenga"
            sess["role"] = "faculty"
            sess["workflow_roles"] = ["review_committee"]

        ret_res = self.client.post(f"/api/courses/{self.test_course_id}/tos/review", json={
            "term": "midterm",
            "decision": "returned",
            "remarks": "Please increase items for Application and Analysis."
        })
        self.assertEqual(ret_res.status_code, 200)
        tos_state = ret_res.get_json()["tos"]
        self.assertEqual(tos_state["status"], "returned")
        self.assertEqual(tos_state["stage"], 1)

        # Faculty can edit again
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        edit_res = self.client.put(f"/api/courses/{self.test_course_id}/tos", json={
            "term": "midterm",
            "tos": {
                "rows": [
                    {
                        "topic": "Topic 1: System Transfer Functions (Revised)",
                        "clo": "CLO1",
                        "remembering": 3,
                        "understanding": 3,
                        "applying_analyzing": 15,
                        "evaluating_creating": 4,
                    }
                ]
            }
        })
        self.assertEqual(edit_res.status_code, 200)
        self.assertEqual(edit_res.get_json()["tos"]["rows"][0]["applying_analyzing"], 15)

    # =========================================================================
    # 4. CONTROLLED DOCUMENT PDF EXPORT TESTS
    # =========================================================================
    def test_pdf_exports_fm_usep_mid_03_and_04(self):
        """Export endpoints generate valid FM-USeP-MID-03 and FM-USeP-MID-04 PDFs with official headers."""
        # Approve syllabus
        self.course_doc["workflow"]["status"] = "approved"
        self.course_doc["workflow"]["approved_at"] = "2026-11-10T10:00:00"
        courses_store.save_course_doc(self.course_doc)

        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        # 1. Export FM-USeP-MID-03
        res03 = self.client.get(f"/api/courses/{self.test_course_id}/tos/export-pdf?term=midterm")
        self.assertEqual(res03.status_code, 200)
        self.assertEqual(res03.mimetype, "application/pdf")
        self.assertIn("FM-USeP-MID-03", res03.headers.get("Content-Disposition", ""))
        self.assertTrue(res03.data.startswith(b"%PDF"))

        # 2. Export FM-USeP-MID-04
        res04 = self.client.get(f"/api/courses/{self.test_course_id}/tos/export-review-pdf?term=midterm")
        self.assertEqual(res04.status_code, 200)
        self.assertEqual(res04.mimetype, "application/pdf")
        self.assertIn("FM-USeP-MID-04", res04.headers.get("Content-Disposition", ""))
        self.assertTrue(res04.data.startswith(b"%PDF"))

if __name__ == "__main__":
    unittest.main()
