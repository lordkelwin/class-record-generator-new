import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import app
import courses_store
import db_persistence


def _faculty_ee() -> dict:
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


def _program_head_ee() -> dict:
    return {
        "username": "ph_ee_test",
        "full_name": "Program Head EE",
        "role": "program_head",
        "workflow_roles": ["program_head"],
        "program_codes": ["EE"],
        "is_staff": False,
        "must_change_password": False,
        "can_access_faculty_tools": True,
    }


def _program_head_ce() -> dict:
    return {
        "username": "ph_ce_test",
        "full_name": "Program Head CE",
        "role": "program_head",
        "workflow_roles": ["program_head"],
        "program_codes": ["CE"],
        "is_staff": False,
        "must_change_password": False,
        "can_access_faculty_tools": True,
    }


def _student_user(sid: str = "2099-66601") -> dict:
    return {
        "username": sid,
        "student_id": sid,
        "full_name": "Dela Cruz, CqiTest",
        "role": "student",
        "workflow_roles": ["student"],
        "must_change_password": False,
    }


class TestFlowchartScrollAndCqiWorkflow(unittest.TestCase):
    def setUp(self):
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()
        self.temp_cid = "test_tmp_cqi_workflow_course"
        self.temp_sid_1 = "2099-66601"
        self.temp_sid_2 = "2099-66602"

        # Construct a realistic course where CO1 passes and CO2 fails MID-10 cohort target
        doc = {
            "id": self.temp_cid,
            "owner": "faculty_tano",
            "program_code": "EE",
            "course_code": "EE 499",
            "course_title": "CQI Synthesis & Flowchart Verification",
            "section": "BSEE 4B",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "workflow": {"status": "approved", "signatures": [], "history": []},
            "class_record_workflow": {"status": "approved"},
            "blueprint": {
                "metadata": {
                    "program_code": "EE",
                    "course_code": "EE 499",
                    "course_title": "CQI Synthesis & Flowchart Verification",
                    "section": "BSEE 4B",
                    "semester_ay": "1st Semester, A.Y. 2026-2027",
                    "passing_percentage": 75.0,
                },
                "course_outcomes": [
                    {
                        "co_id": "CO1",
                        "description": "Compute symmetrical and unsymmetrical fault currents.",
                        "program_outcomes": "PGO a",
                        "performance_indicator": "PI a.1",
                        "degree_target": 75.0,
                        "target_pct": 50.0,
                    },
                    {
                        "co_id": "CO2",
                        "description": "Design inverse-time overcurrent relay coordination.",
                        "program_outcomes": "PGO c",
                        "performance_indicator": "PI c.2",
                        "degree_target": 75.0,
                        "target_pct": 50.0,
                    },
                ],
                "categories": [
                    {
                        "category_id": "SA1",
                        "term": "Midterm",
                        "name": "Quizzes & Midterm",
                        "assessment_code": "SA1",
                        "assessment_type": "SA",
                        "weight_pct": 50.0,
                        "items": [
                            {"item_id": "Q1", "name": "Fault Quiz 1", "max_score": 50, "co_id": "CO1"},
                        ],
                    },
                    {
                        "category_id": "SA2",
                        "term": "Finals",
                        "name": "Final Relay Exam",
                        "assessment_code": "SA2",
                        "assessment_type": "SA",
                        "weight_pct": 50.0,
                        "items": [
                            {"item_id": "FE1", "name": "Relay Coordination Exam", "max_score": 100, "co_id": "CO2"},
                        ],
                    },
                ],
                "students": [
                    {
                        "student_id": self.temp_sid_1,
                        "last_name": "Dela Cruz",
                        "first_name": "CqiTest",
                        "name": "Dela Cruz, CqiTest",
                        "program_year": "BSEE 4B",
                        "scores": {"Q1": 45, "FE1": 20},  # CO1=95%, CO2=60% (below 75%)
                        "clo_scores": {},
                    },
                    {
                        "student_id": self.temp_sid_2,
                        "last_name": "Santos",
                        "first_name": "CqiTwo",
                        "name": "Santos, CqiTwo",
                        "program_year": "BSEE 4B",
                        "scores": {"Q1": 42, "FE1": 30},  # CO1=92%, CO2=65% (below 75%)
                        "clo_scores": {},
                    },
                ],
            },
        }
        courses_store.save_course_doc(doc)

    def tearDown(self):
        try:
            conn = db_persistence.get_db_connection()
            conn.execute("DELETE FROM cqi_plans WHERE course_id = ?", (self.temp_cid,))
            conn.execute(
                "DELETE FROM survey_responses WHERE subject_id = ? OR student_id IN (?, ?)",
                (self.temp_cid, self.temp_sid_1, self.temp_sid_2),
            )
            conn.execute(
                "DELETE FROM app_students WHERE student_id IN (?, ?)",
                (self.temp_sid_1, self.temp_sid_2),
            )
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

            sts = student_store._load_students()
            sts.pop(self.temp_sid_1, None)
            sts.pop(self.temp_sid_2, None)
            student_store._save_students(sts)
        except Exception:
            pass

    def test_01_flowchart_scroll_preservation_and_ui_markers(self):
        """Verify flowchart scroll preserves selected prerequisite connectors and CQI/Portal UI markers exist."""
        fac = _faculty_ee()
        with patch("app.current_user", return_value=fac), patch("auth.current_user", return_value=fac):
            f_html = self.client.get("/").get_data(as_text=True)

        for marker in [
            "preserveFlowchartSelectionHighlight",
            "observeFlowchartLayout",
            'id="ribbonBtnPortalCqiPlans"',
            'id="portalViewCqiPlans"',
            'id="cqiThreeSourceBody"',
            'id="btnSynthesizeCqiRule"',
            'id="btnSynthesizeCqiAi"',
            'id="btnSubmitCqiPlan"',
            'id="cqi_gap_analysis"',
            'id="cqi_root_causes"',
            'id="cqi_target_kpis"',
        ]:
            self.assertIn(marker, f_html)

        # Ensure scroll handler calls preserveFlowchartSelectionHighlight without clearing SVG edges
        scroll_idx = f_html.find("function observeFlowchartLayout")
        self.assertGreater(scroll_idx, 0)
        scroll_block = f_html[scroll_idx : scroll_idx + 1800]
        self.assertIn("preserveFlowchartSelectionHighlight", scroll_block)
        self.assertIn("flowchartSvgEdgesGroup", scroll_block)

        st = _student_user(self.temp_sid_1)
        with patch("app.current_user", return_value=st), \
             patch("auth.current_user", return_value=st), \
             patch("student_store.get_student_profile", return_value=st):
            s_html = self.client.get("/student/dashboard").get_data(as_text=True)
        self.assertIn('id="exitSurveyChallengingTopics"', s_html)
        self.assertIn("cqi_category", s_html)

    def test_02_expanded_exit_survey_three_source_synthesis_submit_and_program_head_review(self):
        """End-to-end: Exit Survey CQI anchors -> 3-Source Synthesis (Rule & AI) -> Submit (+1yr Revisit) -> PH Review & RBAC."""
        st = _student_user(self.temp_sid_1)
        fac = _faculty_ee()
        ph_ee = _program_head_ee()
        ph_ce = _program_head_ce()

        # 1. Student fetches expanded Exit Survey schema & submits CQI-anchored ratings + challenging topics
        with patch("app.current_user", return_value=st), \
             patch("auth.current_user", return_value=st), \
             patch("student_store.get_student_profile", return_value=st):
            get_srv = self.client.get(f"/api/student/courses/{self.temp_cid}/exit-survey")
            self.assertEqual(get_srv.status_code, 200)
            srv_schema = get_srv.get_json()
            gen_qs = srv_schema["general_questions"]
            self.assertGreaterEqual(len(gen_qs), 5)
            anchor_keys = [q.get("cqi_anchor_key") for q in gen_qs]
            self.assertIn("instructional_delivery_pacing", anchor_keys)
            self.assertIn("assessment_tos_rubrics", anchor_keys)
            self.assertIn("learning_resources_labs", anchor_keys)
            self.assertIn("student_support_consultation", anchor_keys)

            post_srv = self.client.post(
                f"/api/student/courses/{self.temp_cid}/exit-survey",
                json={
                    "clo_ratings": {"CO1": 5, "CO2": 2},
                    "general_ratings": {
                        "syllabus_clarity": 4,
                        "teaching_delivery": 4,
                        "assessment_fairness": 3,
                        "resources_facilities": 2,
                        "feedback_consultation": 4,
                    },
                    "challenging_topics": "Inverse-time relay pickup current calculations in Lab 3 (CO2) lacked worked examples.",
                    "comments": "Need guided relay coordination lab simulations.",
                },
            )
            self.assertEqual(post_srv.status_code, 200)
            self.assertTrue(post_srv.get_json()["is_completed"])

        # 2. Verify exit survey aggregate includes cqi_anchors_summary and challenging_topics
        with patch("app.current_user", return_value=fac), patch("auth.current_user", return_value=fac):
            sum_res = self.client.get(f"/api/courses/{self.temp_cid}/exit-survey-summary")
            self.assertEqual(sum_res.status_code, 200)
            sum_data = sum_res.get_json()
            self.assertEqual(sum_data["total_responses"], 1)
            self.assertIn("learning_resources_labs", sum_data["cqi_anchors_summary"])
            self.assertEqual(sum_data["cqi_anchors_summary"]["learning_resources_labs"]["avg_rating"], 2.0)
            self.assertEqual(len(sum_data["challenging_topics"]), 1)

            # 3. Rule-based 3-Source CQI Synthesis
            syn_rule = self.client.post(
                f"/api/courses/{self.temp_cid}/cqi/synthesize",
                json={"use_ai": False},
            )
            self.assertEqual(syn_rule.status_code, 200)
            sr = syn_rule.get_json()
            self.assertTrue(sr["success"])
            self.assertEqual(sr["engine"], "rule_based_three_source_correlation")
            plan = sr["cqi_plan"]
            self.assertIn("CO2", plan["targeted_clos"])
            self.assertNotIn("CO1", plan["targeted_clos"])
            self.assertIn("CO2", plan["gap_analysis"])
            self.assertIn("Relay Coordination Exam", plan["areas_for_improvement"])
            self.assertIn("Inverse-time relay pickup current calculations", plan["root_causes"])
            self.assertTrue(bool(plan["action_plan"]))
            self.assertTrue(bool(plan["target_kpis"]))

            # 4. Mocked Gemini 2.5 Flash AI-Assisted Synthesis
            fake_ai_json = json.dumps({
                "key_strengths": "CO1 symmetrical fault analysis achieved 100% attainment.",
                "areas_for_improvement": "CO2 overcurrent relay coordination fell below 50% cohort target.",
                "gap_analysis": "Direct MID-10 CO2 (0.0%) aligns with low CO2 survey confidence (2.0/5).",
                "root_causes": "Insufficient worked examples and lab time for inverse-time relay curves.",
                "action_plan": "Add structured lab worksheet and pre-lab numerical walkthrough on relay curves.",
                "target_kpis": "Raise CO2 attainment >= 75% in 1st Semester, A.Y. 2027-2028.",
            })
            fake_http_resp = MagicMock()
            fake_http_resp.ok = True
            fake_http_resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": fake_ai_json}]}}]
            }

            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-test-key"}, clear=False), \
                 patch("requests.post", return_value=fake_http_resp):
                syn_ai = self.client.post(
                    f"/api/courses/{self.temp_cid}/cqi/synthesize",
                    json={"use_ai": True},
                )
            self.assertEqual(syn_ai.status_code, 200)
            sa = syn_ai.get_json()
            self.assertEqual(sa["engine"], "gemini_ai_assisted")
            self.assertIn("relay curves", sa["cqi_plan"]["root_causes"])

            # 5. Faculty submits CQI Plan -> Mandatory Revisit Date (+1 yr) & Next AY Same Semester
            sub_res = self.client.post(
                f"/api/courses/{self.temp_cid}/cqi/submit",
                json=sa["cqi_plan"],
            )
            self.assertEqual(sub_res.status_code, 200)
            sd = sub_res.get_json()
            self.assertTrue(sd["success"])
            rec = sd["cqi_plan_record"]
            self.assertEqual(rec["status"], "submitted")
            self.assertEqual(rec["revisit_term"], "1st Semester, A.Y. 2027-2028")
            expected_revisit_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
            self.assertEqual(rec["revisit_date"], expected_revisit_date)

            # Faculty attempting Program Head review gets 403
            fac_rev = self.client.post(
                f"/api/workflow/cqi-plans/{self.temp_cid}/review",
                json={"action": "approve"},
            )
            self.assertEqual(fac_rev.status_code, 403)

        # 6. Program Head RBAC: CE Program Head cannot see EE CQI Plan
        with patch("app.current_user", return_value=ph_ce), patch("auth.current_user", return_value=ph_ce):
            ce_list = self.client.get("/api/workflow/cqi-plans").get_json()
            ce_ids = [p["course_id"] for p in ce_list["plans"]]
            self.assertNotIn(self.temp_cid, ce_ids)

        # 7. EE Program Head sees EE CQI Plan segregated by Semester/AY & can approve, fine-tune date, and close
        with patch("app.current_user", return_value=ph_ee), patch("auth.current_user", return_value=ph_ee):
            ee_list_res = self.client.get("/api/workflow/cqi-plans")
            self.assertEqual(ee_list_res.status_code, 200)
            ee_list = ee_list_res.get_json()
            self.assertTrue(ee_list["can_review"])
            matched = [p for p in ee_list["plans"] if p["course_id"] == self.temp_cid]
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0]["semester_ay"], "1st Semester, A.Y. 2026-2027")
            self.assertEqual(matched[0]["revisit_term"], "1st Semester, A.Y. 2027-2028")

            # Approve & Schedule Revisit with fine-tuned revisit date
            app_res = self.client.post(
                f"/api/workflow/cqi-plans/{self.temp_cid}/review",
                json={"action": "approve", "remarks": "Approved for next A.Y. revisit.", "revisit_date": "2028-09-15"},
            )
            self.assertEqual(app_res.status_code, 200)
            app_rec = app_res.get_json()["cqi_plan_record"]
            self.assertEqual(app_rec["status"], "approved_scheduled")
            self.assertEqual(app_rec["revisit_date"], "2028-09-15")
            self.assertEqual(app_rec["revisit_status"], "Upcoming")

            # Close / Verify Revisit
            cls_res = self.client.post(
                f"/api/workflow/cqi-plans/{self.temp_cid}/review",
                json={"action": "close", "remarks": "Revisit completed; CO2 reached 82%."},
            )
            self.assertEqual(cls_res.status_code, 200)
            cls_rec = cls_res.get_json()["cqi_plan_record"]
            self.assertEqual(cls_rec["status"], "verified")
            self.assertEqual(cls_rec["revisit_status"], "Closed/Verified")


if __name__ == "__main__":
    unittest.main()
