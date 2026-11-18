import unittest
from unittest.mock import patch
import copy

import app
import auth
import courses_store
import pgo_assessment


def _user_from_store(username: str) -> dict:
    users = auth._load_users()
    u_raw = users[username]
    role = u_raw.get("role", "faculty")
    wf_roles = u_raw.get("workflow_roles") or []
    is_staff = (role == "staff") or ("staff" in wf_roles)
    has_fac = any(r in wf_roles for r in ("review_committee", "faculty", "program_head", "qa_head", "dean", "associate_dean"))
    return {
        "username": username,
        "full_name": u_raw.get("full_name") or username,
        "role": role,
        "workflow_roles": wf_roles,
        "program_codes": u_raw.get("program_codes") or ["EE"],
        "is_staff": is_staff,
        "must_change_password": False,
        "can_access_faculty_tools": not (is_staff and not has_fac and role != "admin"),
    }


MOCK_FACULTY_TANO = _user_from_store("faculty_tano")
MOCK_PROGRAM_HEAD_CLARO = _user_from_store("faculty_claro")
MOCK_QA_HEAD = _user_from_store("qahead_ce")
MOCK_DEAN = _user_from_store("dean_cataytay")
MOCK_STAFF = _user_from_store("staff_office")
MOCK_ADMIN = _user_from_store("admin")
MOCK_STUDENT = {"username": "2023-00011", "student_id": "2023-00011", "role": "student", "workflow_roles": ["student"], "must_change_password": False}


class TestPgoAssessmentModule(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.client.testing = True

    def test_01_ribbon_and_ui_rendered_for_faculty_and_staff(self):
        """Top-level PGO Assessment ribbon, flowchart, matrix, and modal render for both Faculty and Staff."""
        for mock_user in (MOCK_FACULTY_TANO, MOCK_STAFF):
            with patch("app.current_user", return_value=mock_user), \
                 patch("auth.current_user", return_value=mock_user):
                resp = self.client.get("/")
                self.assertEqual(resp.status_code, 200)
                html = resp.get_data(as_text=True)
                self.assertIn('id="ribbonTabPgoAssessment"', html)
                self.assertIn('id="ribbonBandPgoAssessment"', html)
                self.assertIn('id="tab-pgo-assessment"', html)
                self.assertIn('id="pgoFlowchartMap"', html)
                self.assertIn('id="pgoNodeTooltip"', html)
                self.assertIn('id="pgoStudentMatrixTable"', html)
                self.assertIn('id="pgoDrilldownModal"', html)

    def test_02_rbac_program_wide_vs_faculty_scope(self):
        """Program Head, QA Head, Dean, Staff, Admin see all 13 PGOs; Faculty sees only handled courses' PGOs."""
        for wide_user in (MOCK_PROGRAM_HEAD_CLARO, MOCK_QA_HEAD, MOCK_DEAN, MOCK_STAFF, MOCK_ADMIN):
            with patch("app.current_user", return_value=wide_user), \
                 patch("auth.current_user", return_value=wide_user):
                res = self.client.get("/api/pgo-assessment")
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertTrue(data["scope"]["is_program_wide"])
                self.assertEqual(len(data["pgos"]), 13, f"{wide_user['username']} should see all 13 PGOs")

        # Faculty scope: faculty_tano only handles EE 415 (aligned to PGOs c, d, f, g, h)
        with patch("app.current_user", return_value=MOCK_FACULTY_TANO), \
             patch("auth.current_user", return_value=MOCK_FACULTY_TANO):
            res = self.client.get("/api/pgo-assessment")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertFalse(data["scope"]["is_program_wide"])
            visible_pgo_ids = {p["pgo_id"] for p in data["pgos"]}
            self.assertEqual(visible_pgo_ids, {"c", "d", "f", "g", "h"})
            self.assertNotIn("a", visible_pgo_ids)
            self.assertNotIn("m", visible_pgo_ids)

            # Drilldown into unaligned PGO 'a' is denied (404 outside scope)
            dd_blocked = self.client.get("/api/pgo-assessment/node-drilldown?node_type=pgo&node_id=pgo:a")
            self.assertEqual(dd_blocked.status_code, 404)

            # Drilldown into aligned PGO 'c' succeeds and returns Student IDs
            dd_ok = self.client.get("/api/pgo-assessment/node-drilldown?node_type=pgo&node_id=pgo:c")
            self.assertEqual(dd_ok.status_code, 200)
            dd_data = dd_ok.get_json()
            self.assertEqual(dd_data["node"]["pgo_id"], "c")
            sids = {s["student_id"] for s in dd_data["node"]["student_ids"]}
            self.assertIn("2023-00011", sids)
            self.assertIn("2022-00667", sids)

    def test_03_student_portal_blocked(self):
        """Students cannot access the Faculty/Institutional PGO Assessment API."""
        with patch("app.current_user", return_value=MOCK_STUDENT), \
             patch("auth.current_user", return_value=MOCK_STUDENT):
            res = self.client.get("/api/pgo-assessment")
            self.assertIn(res.status_code, (302, 403))

    def test_04_bottom_up_obe_math_and_flowchart_edges_in_memory(self):
        """Verify bottom-up Class Record -> CLO -> PI -> PGO math, I-E-D progression, Cohort grouping, and Flowchart edges."""
        doc = copy.deepcopy(courses_store.find_course("c_144aaf4901"))
        self.assertIsNotNone(doc)

        # Populate full passing scores in memory for 2023-00011 (100% on Q1-Q4, MTE, FTE -> Base-50 = 100.0)
        for st in doc["blueprint"]["students"]:
            if st["student_id"] == "2023-00011":
                st["scores"] = {
                    "Q1__CLO1": 6, "Q1__CLO2": 6, "Q1__CLO3": 6, "Q1__CLO4": 6, "Q1__CLO5": 6,
                    "Q2__CLO1": 6, "Q2__CLO2": 6, "Q2__CLO3": 6, "Q2__CLO4": 6, "Q2__CLO5": 6,
                    "MTE__CLO1": 30, "MTE__CLO2": 30, "MTE__CLO3": 30, "MTE__CLO4": 30, "MTE__CLO5": 30,
                    "Q3__CLO1": 6, "Q3__CLO2": 6, "Q3__CLO3": 6, "Q3__CLO4": 6, "Q3__CLO5": 6,
                    "Q4__CLO1": 6, "Q4__CLO2": 6, "Q4__CLO3": 6, "Q4__CLO4": 6, "Q4__CLO5": 6,
                    "FTE__CLO1": 30, "FTE__CLO2": 30, "FTE__CLO3": 30, "FTE__CLO4": 30, "FTE__CLO5": 30,
                }

        with patch("pgo_assessment._collect_scoped_courses", return_value=[doc]):
            rep = pgo_assessment.build_pgo_assessment_report(MOCK_FACULTY_TANO)

        # Student 2023-00011 should have 100.0 across all 5 PGOs
        st_11 = next(s for s in rep["students_matrix"] if s["student_id"] == "2023-00011")
        self.assertEqual(st_11["cohort"], "2023")
        self.assertEqual(st_11["overall_pgo_grade"], 100.0)
        self.assertEqual(st_11["overall_attainment_pct"], 100.0)
        self.assertEqual(st_11["attained_pgos_count"], 5)

        # Verify I-E-D assignments from ACCDB / EE 415
        pgo_c = next(p for p in rep["pgos"] if p["pgo_id"] == "c")
        self.assertIn("D", pgo_c["ied_levels"])
        pgo_f = next(p for p in rep["pgos"] if p["pgo_id"] == "f")
        self.assertIn("E", pgo_f["ied_levels"])

        # Verify Flowchart Nodes & Edges
        fc = rep["flowchart"]
        self.assertEqual(len(fc["course_clo_nodes"]), 5)
        self.assertEqual(len(fc["pgo_nodes"]), 5)
        clo_pi_edges = [e for e in fc["edges"] if e["type"] == "clo-pi"]
        pi_pgo_edges = [e for e in fc["edges"] if e["type"] == "pi-pgo"]
        self.assertEqual(len(clo_pi_edges), 5)
        self.assertEqual(len(pi_pgo_edges), 5)

    def test_05_ied_and_student_search_filters(self):
        """Verify I-E-D and Student ID # search filters narrow results cleanly."""
        with patch("app.current_user", return_value=MOCK_FACULTY_TANO), \
             patch("auth.current_user", return_value=MOCK_FACULTY_TANO):
            res_d = self.client.get("/api/pgo-assessment?ied=D")
            self.assertEqual(res_d.status_code, 200)
            d_data = res_d.get_json()
            aligned_d_pgos = {p["pgo_id"] for p in d_data["pgos"] if p["is_aligned"]}
            self.assertTrue({"c", "d"}.issubset(aligned_d_pgos))
            self.assertNotIn("f", aligned_d_pgos)

            res_q = self.client.get("/api/pgo-assessment?q=2023-00011")
            self.assertEqual(res_q.status_code, 200)
            q_data = res_q.get_json()
            sids = [s["student_id"] for s in q_data["students_matrix"]]
            self.assertEqual(sids, ["2023-00011"])

    def test_06_program_directory_per_program_and_rbac(self):
        """Program PGO & PI Directory lists program-specific outcomes and respects RBAC scope."""
        # Dean sees all 9 engineering programs and every PGO + child PIs
        with patch("app.current_user", return_value=MOCK_DEAN), \
             patch("auth.current_user", return_value=MOCK_DEAN):
            res_dean = self.client.get("/api/pgo-assessment")
            self.assertEqual(res_dean.status_code, 200)
            dir_dean = res_dean.get_json().get("program_directory", {})
            progs = {p["program_code"]: p for p in dir_dean.get("programs", [])}
            self.assertIn("EE", progs)
            self.assertIn("CE", progs)
            self.assertIn("ECE", progs)
            self.assertEqual(progs["EE"]["pgo_count"], 13)
            self.assertGreaterEqual(progs["EE"]["pi_count"], 30)

        # Faculty only sees PGOs aligned to their courses in directory
        with patch("app.current_user", return_value=MOCK_FACULTY_TANO), \
             patch("auth.current_user", return_value=MOCK_FACULTY_TANO):
            res_fac = self.client.get("/api/pgo-assessment")
            self.assertEqual(res_fac.status_code, 200)
            dir_fac = res_fac.get_json().get("program_directory", {})
            ee_prog = next((p for p in dir_fac.get("programs", []) if p["program_code"] == "EE"), None)
            self.assertIsNotNone(ee_prog)
            fac_keys = {pg["pgo_key"] for pg in ee_prog["pgos"]}
            self.assertEqual(fac_keys, {"c", "d", "f", "g", "h"})
            self.assertTrue(all(len(pg["pis"]) >= 1 for pg in ee_prog["pgos"]))

    def test_07_null_and_malformed_cqi_guards_and_lan_cookie_config(self):
        """Missing CQIIndicator.number, None scores, empty records never 500; LAN cookie settings are valid."""
        import config
        malformed_doc = {
            "id": "mem_tmp_malformed_cqi",
            "owner": "faculty_tano",
            "course_code": "EE 415",
            "course_title": "Faulty Blueprint Guard Test",
            "section": "BSEE 4A",
            "blueprint": {
                "metadata": {"course_code": "EE 415", "programs": []},
                "course_outcomes": [
                    None,
                    {"co_id": "CO1", "description": "Design check", "program_outcomes": None, "performance_indicator": None, "target_score_pct": None},
                ],
                "categories": [
                    {
                        "category_id": "SA1",
                        "term": "Midterm",
                        "assessment_type": "SA",
                        "weight_pct": 0,
                        "items": [{"item_id": "Q1", "name": "Quiz 1", "max_score": 0, "co_id": "CO1"}],
                    }
                ],
                "students": [
                    {"student_id": "2023-99901", "name": "Null, Score", "scores": {"Q1": None}},
                    {"student_id": "2023-99902", "last_name": "Bad", "first_name": None, "scores": None},
                ],
                "cqi_plan": {
                    "indicators": [
                        {"category": "Cat I", "title": "Delivery", "subtitle": "Pacing", "mark": "✓", "remarks": ""}
                    ]
                },
            },
        }
        mock_wf = [{"doc_raw": malformed_doc}]
        with patch("app.current_user", return_value=MOCK_DEAN), \
             patch("auth.current_user", return_value=MOCK_DEAN), \
             patch("courses_store.list_all_workflow_courses", return_value=mock_wf):
            res = self.client.get("/api/pgo-assessment")
            self.assertEqual(res.status_code, 200)
            payload = res.get_json()
            self.assertTrue(payload["success"])
            self.assertEqual(payload["courses"][0]["course_code"], "EE 415")

        # Verify LAN binding & cookie compatibility
        self.assertEqual(app.app.config.get("SESSION_COOKIE_SECURE"), False)
        self.assertEqual(app.app.config.get("SESSION_COOKIE_SAMESITE"), "Lax")
        self.assertIsNone(app.app.config.get("SERVER_NAME"))
        self.assertEqual(config.HOST, "0.0.0.0")
        self.assertTrue(bool(config.get_local_ip()))


if __name__ == "__main__":
    unittest.main()
