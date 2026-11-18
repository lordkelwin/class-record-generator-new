import base64
import io
import json
import unittest
from unittest.mock import patch, MagicMock

from PIL import Image, ImageDraw

import app
import courses_store
import db_persistence


def _faculty_user() -> dict:
    return {
        "username": "faculty_tano",
        "full_name": "Elwin Jay Tano",
        "role": "faculty",
        "workflow_roles": ["faculty"],
        "program_codes": ["EE"],
        "is_staff": False,
        "must_change_password": False,
        "can_access_faculty_tools": True,
    }


def _student_user(sid: str = "2099-55501") -> dict:
    return {
        "username": sid,
        "student_id": sid,
        "full_name": "Survey, Tester",
        "role": "student",
        "workflow_roles": ["student"],
        "must_change_password": False,
    }


class TestDefaultOcrAndExitSurveyGating(unittest.TestCase):
    def setUp(self):
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()
        self.temp_cid = "test_tmp_exit_survey_course"
        self.temp_sid = "2099-55501"

        doc = {
            "id": self.temp_cid,
            "owner": "faculty_tano",
            "course_code": "EE 498",
            "course_title": "Exit Survey Gate Test Course",
            "section": "BSEE 4A",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "workflow": {"status": "approved", "signatures": [], "history": []},
            "class_record_workflow": {"status": "approved"},
            "blueprint": {
                "metadata": {
                    "course_code": "EE 498",
                    "course_title": "Exit Survey Gate Test Course",
                    "section": "BSEE 4A",
                    "passing_percentage": 75.0,
                },
                "course_outcomes": [
                    {"co_id": "CO1", "description": "Analyze symmetrical fault currents in power grids."},
                    {"co_id": "CO2", "description": "Design protective relaying coordination curves."},
                ],
                "categories": [
                    {
                        "category_id": "SA1",
                        "term": "Midterm",
                        "name": "Quizzes",
                        "assessment_code": "SA1",
                        "assessment_type": "SA",
                        "weight_pct": 50.0,
                        "items": [
                            {"item_id": "Q1", "name": "Quiz 1", "max_score": 50, "co_id": "CO1"},
                        ],
                    },
                    {
                        "category_id": "SA2",
                        "term": "Finals",
                        "name": "Final Exam",
                        "assessment_code": "SA2",
                        "assessment_type": "SA",
                        "weight_pct": 50.0,
                        "items": [
                            {"item_id": "FE1", "name": "Final Exam", "max_score": 100, "co_id": "CO2"},
                        ],
                    },
                ],
                "students": [
                    {
                        "student_id": self.temp_sid,
                        "last_name": "Survey",
                        "first_name": "Tester",
                        "name": "Survey, Tester",
                        "program_year": "BSEE 4A",
                        "scores": {"Q1": 45, "FE1": 90},
                        "clo_scores": {},
                    }
                ],
            },
        }
        courses_store.save_course_doc(doc)

    def tearDown(self):
        try:
            conn = db_persistence.get_db_connection()
            conn.execute("DELETE FROM survey_responses WHERE subject_id = ? OR student_id = ?", (self.temp_cid, self.temp_sid))
            conn.commit()
            conn.close()
        except Exception:
            pass
        try:
            courses_store.delete_course(self.temp_cid)
        except Exception:
            pass
        try:
            import student_store
            conn = db_persistence.get_db_connection()
            conn.execute("DELETE FROM app_students WHERE student_id = ?", (self.temp_sid,))
            conn.commit()
            conn.close()
            sts = student_store._load_students()
            sts.pop(self.temp_sid, None)
            student_store._save_students(sts)
        except Exception:
            pass

    def test_01_default_built_in_ocr_works_with_zero_api_key(self):
        """Default OCR runs out-of-the-box on uploaded/pasted image without requiring any model or API key setup."""
        img = Image.new("RGB", (900, 140), "white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "CO1: Analyze symmetrical fault currents in power grids", fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64_data = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

        fac = _faculty_user()
        with patch("app.current_user", return_value=fac), \
             patch("auth.current_user", return_value=fac), \
             patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            res = self.client.post(
                "/api/syllabus/ocr-extract",
                json={"section_key": "course_outcomes", "ocr_mode": "default", "image_base64": b64_data},
            )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn(data["engine"], ("built_in_default_ocr", "tesseract_default_ocr"))
        self.assertNotIn("needs_api_key", data)

        # Also check specialized optional override with mocked Gemini Vision
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": json.dumps({"course_outcomes": [{"co_id": "CO1", "description": "Vision CLO"}]})}]}}]
        }
        with patch("app.current_user", return_value=fac), \
             patch("auth.current_user", return_value=fac), \
             patch("requests.post", return_value=mock_resp):
            res_spec = self.client.post(
                "/api/syllabus/ocr-extract",
                json={
                    "section_key": "course_outcomes",
                    "ocr_mode": "gemini-2.5-pro",
                    "gemini_api_key": "opt-key",
                    "image_base64": b64_data,
                },
            )
        self.assertEqual(res_spec.status_code, 200)
        d_spec = res_spec.get_json()
        self.assertEqual(d_spec["engine"], "gemini_vision")
        self.assertEqual(d_spec["model"], "gemini-2.5-pro")

    def test_02_exit_survey_gates_final_grade_and_unlocks_on_submit(self):
        """Final Grade is server-masked until Course Exit Survey is completed, then unlocked permanently & aggregated for CQI."""
        st_user = _student_user(self.temp_sid)
        fac_user = _faculty_user()

        with patch("app.current_user", return_value=st_user), \
             patch("auth.current_user", return_value=st_user):
            # 1. Dynamic survey schema reflects syllabus CLOs
            srv_get = self.client.get(f"/api/student/courses/{self.temp_cid}/exit-survey")
            self.assertEqual(srv_get.status_code, 200)
            s_data = srv_get.get_json()
            self.assertFalse(s_data["is_completed"])
            self.assertEqual([c["co_id"] for c in s_data["clos"]], ["CO1", "CO2"])

            # 2. Performance endpoint masks Final Grade while survey is incomplete
            perf_locked = self.client.get(f"/api/student/courses/{self.temp_cid}/performance")
            self.assertEqual(perf_locked.status_code, 200)
            pl = perf_locked.get_json()
            self.assertTrue(pl["grade_visibility"]["all_assessments_finalized"])
            self.assertFalse(pl["grade_visibility"]["survey_completed"])
            self.assertFalse(pl["grade_visibility"]["final_grade_unlocked"])
            self.assertEqual(pl["grade_visibility"]["lock_reason"], "survey_required")
            self.assertIsNone(pl["grades"]["average_final_grade"])
            self.assertIsNone(pl["grades"]["transmuted_grade"])
            self.assertIsNone(pl["grades"]["finals_grade"])
            self.assertEqual(pl["grades"]["status_label"], "LOCKED_SURVEY_REQUIRED")

            # 3. Submit per-course Exit Survey
            srv_post = self.client.post(
                f"/api/student/courses/{self.temp_cid}/exit-survey",
                json={
                    "clo_ratings": {"CO1": 5, "CO2": 4},
                    "general_ratings": {
                        "syllabus_clarity": 5,
                        "teaching_delivery": 5,
                        "assessment_fairness": 4,
                        "feedback_consultation": 5,
                    },
                    "comments": "Well-structured electrical engineering laboratory and clear grading.",
                },
            )
            self.assertEqual(srv_post.status_code, 200)
            sp = srv_post.get_json()
            self.assertTrue(sp["success"])
            self.assertTrue(sp["is_completed"])

            # 4. Subsequent performance request immediately unlocks Final Grade & keeps it unlocked
            perf_open = self.client.get(f"/api/student/courses/{self.temp_cid}/performance")
            self.assertEqual(perf_open.status_code, 200)
            po = perf_open.get_json()
            self.assertTrue(po["grade_visibility"]["survey_completed"])
            self.assertTrue(po["grade_visibility"]["final_grade_unlocked"])
            self.assertIsNotNone(po["grades"]["average_final_grade"])
            self.assertIsNotNone(po["grades"]["transmuted_grade"])
            self.assertEqual(po["grades"]["status_label"], "PASSED")

        # 5. Faculty CQI exit survey aggregation reflects the submission
        with patch("app.current_user", return_value=fac_user), \
             patch("auth.current_user", return_value=fac_user):
            cqi_res = self.client.get(f"/api/courses/{self.temp_cid}/exit-survey-summary")
            self.assertEqual(cqi_res.status_code, 200)
            cqi = cqi_res.get_json()
            self.assertEqual(cqi["total_responses"], 1)
            clo_means = {c["co_id"]: c["avg_rating"] for c in cqi["clo_ratings_summary"]}
            self.assertEqual(clo_means["CO1"], 5.0)
            self.assertEqual(clo_means["CO2"], 4.0)
            self.assertEqual(len(cqi["comments"]), 1)

    def test_03_ui_markers_present_in_faculty_and_student_portals(self):
        """Both Faculty Studio OCR UI/CQI card and Student Portal Exit Survey modal/lock markers render cleanly."""
        fac_user = _faculty_user()
        with patch("app.current_user", return_value=fac_user), \
             patch("auth.current_user", return_value=fac_user):
            f_html = self.client.get("/").get_data(as_text=True)
        for marker in ['id="syllabusOcrEngineBadge"', 'id="syllabusOcrAdvancedDetails"', 'id="syllabusOcrModelSelect"', 'id="cqiExitSurveyCard"']:
            self.assertIn(marker, f_html)

        st_user = _student_user(self.temp_sid)
        with patch("app.current_user", return_value=st_user), \
             patch("auth.current_user", return_value=st_user), \
             patch("student_store.get_student_profile", return_value=st_user):
            s_html = self.client.get("/student/dashboard").get_data(as_text=True)
        for marker in ['id="courseExitSurveyBackdrop"', "openCourseExitSurveyModal", "Complete Course Exit Survey to View Final Grade", "Take Course Exit Survey"]:
            self.assertIn(marker, s_html)


if __name__ == "__main__":
    unittest.main()
