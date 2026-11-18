import io
import json
import unittest
from unittest.mock import patch, MagicMock

import app
import auth
import courses_store


def _faculty_user() -> dict:
    users = auth._load_users()
    u = users["faculty_tano"]
    return {
        "username": "faculty_tano",
        "full_name": u.get("full_name") or "Elwin Jay Tano",
        "role": u.get("role") or "faculty",
        "workflow_roles": u.get("workflow_roles") or ["faculty"],
        "program_codes": u.get("program_codes") or ["EE"],
        "is_staff": False,
        "must_change_password": False,
        "can_access_faculty_tools": True,
    }


class TestMid07ImportAndStep1Ocr(unittest.TestCase):
    def setUp(self):
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()
        self.mock_user = _faculty_user()
        self.temp_cid = "test_tmp_mid07_import_course"
        self.doc = {
            "id": self.temp_cid,
            "owner": "faculty_tano",
            "course_code": "EE 499",
            "course_title": "Temporary Verification Course",
            "section": "BSEE 4A",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "workflow": {"status": "for_student_acknowledgment", "signatures": [], "history": []},
            "student_acknowledgments": [],
            "blueprint": {
                "metadata": {"course_code": "EE 499", "section": "BSEE 4A"},
                "students": [
                    {"student_id": "2099-00001", "last_name": "Alpha", "first_name": "Ana", "name": "Alpha, Ana", "scores": {}},
                    {"student_id": "2099-00002", "last_name": "Beta", "first_name": "Ben", "name": "Beta, Ben", "scores": {}},
                ],
            },
        }
        courses_store.save_course_doc(self.doc)

    def tearDown(self):
        try:
            courses_store.delete_course(self.temp_cid)
        except Exception:
            pass
        try:
            import db_persistence, student_store
            conn = db_persistence.get_db_connection()
            conn.execute("DELETE FROM app_students WHERE student_id IN ('2099-00001', '2099-00002')")
            conn.commit()
            conn.close()
            sts = student_store._load_students()
            for k in ("2099-00001", "2099-00002"):
                sts.pop(k, None)
            student_store._save_students(sts)
        except Exception:
            pass

    def test_01_import_signed_mid07_csv_updates_acks_and_threshold(self):
        """Importing a signed CSV matches roster students and updates FM-USeP-MID-07 & workflow."""
        csv_content = (
            "student_id,student_name,status,acknowledged_at,comment\n"
            "2099-00001,\"Alpha, Ana\",Signed,2026-08-20,Reviewed and accepted\n"
            "2099-00002,\"Beta, Ben\",Signed,2026-08-21,Acknowledged\n"
        ).encode("utf-8")

        with patch("app.current_user", return_value=self.mock_user), \
             patch("auth.current_user", return_value=self.mock_user):
            res = self.client.post(
                f"/api/courses/{self.temp_cid}/student-acknowledgment/import",
                data={"file": (io.BytesIO(csv_content), "signed_mid07.csv"), "enroll_unlisted": "0"},
                content_type="multipart/form-data",
            )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["imported_count"], 2)
        self.assertEqual(data["total_acknowledged"], 2)
        self.assertEqual(data["workflow"]["status"], "for_dean_approval")

    def test_02_step1_ocr_extract_raw_text_and_mocked_gemini_vision(self):
        """Step 1 OCR endpoint extracts structured CLO/Learning Plan fields via parser and mocked Gemini Vision."""
        with patch("app.current_user", return_value=self.mock_user), \
             patch("auth.current_user", return_value=self.mock_user):
            # A. Structured raw text fallback for CLOs
            res_txt = self.client.post(
                "/api/syllabus/ocr-extract",
                json={
                    "section_key": "course_outcomes",
                    "raw_text": "CO1: Analyze power distribution circuits.\nCO2: Design protection coordination schemes.",
                },
            )
            self.assertEqual(res_txt.status_code, 200)
            d_txt = res_txt.get_json()
            self.assertTrue(d_txt["success"])
            self.assertEqual(len(d_txt["data"]["course_outcomes"]), 2)
            self.assertEqual(d_txt["data"]["course_outcomes"][0]["co_id"], "CO1")

            # B. Mocked Gemini Vision multimodal extraction from base64 PNG
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": json.dumps({
                                "learning_plan_table": [
                                    {"ilo": "Explain transmission parameters", "clo": "CO1", "time_frame": "Week 3 (3 hrs)", "topics": "ABCD Parameters", "tla": "Lecture", "required_reading": "Ref01", "assessment_activities": "Quiz 1"}
                                ]
                            })
                        }]
                    }
                }]
            }
            with patch("requests.post", return_value=mock_resp):
                res_vis = self.client.post(
                    "/api/syllabus/ocr-extract",
                    json={
                        "section_key": "learning_plan",
                        "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
                        "gemini_api_key": "dummy-test-key",
                    },
                )
            self.assertEqual(res_vis.status_code, 200)
            d_vis = res_vis.get_json()
            self.assertTrue(d_vis["success"])
            self.assertEqual(d_vis["engine"], "gemini_vision")
            self.assertEqual(d_vis["data"]["learning_plan_table"][0]["topics"], "ABCD Parameters")

    def test_03_frontend_ui_features_present(self):
        """Verify FAB toggle, flowchart layout observers, AI hover lock, MID-07 import UI, OCR buttons, and PGO directory render cleanly."""
        with patch("app.current_user", return_value=self.mock_user), \
             patch("auth.current_user", return_value=self.mock_user):
            resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        for marker in [
            'id="floatingSidebarToggleBtn"',
            "observeFlowchartLayout(",
            "ResizeObserver",
            "MutationObserver",
            "advisorActiveHighlights",
            'id="pgoDirectoryCard"',
            "openImportSignedAckModal()",
            'id="importSignedAckModal"',
            "openSyllabusOcrModal(",
            'id="syllabusSectionOcrModal"',
            'document.addEventListener("paste"',
        ]:
            self.assertIn(marker, html, f"Missing expected frontend feature marker: {marker}")


if __name__ == "__main__":
    unittest.main()
