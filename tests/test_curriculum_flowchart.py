import unittest
import json
from app import app
import auth


class TestCurriculumFlowchartAndDetails(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_api_curriculum_flowchart_unauthenticated(self):
        res = self.client.get("/api/curriculum/flowchart?program=BSEE")
        self.assertEqual(res.status_code, 401)

    def test_api_curriculum_flowchart_authenticated_bsee(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/api/curriculum/flowchart?program=BSEE")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["program_code"], "BSEE")
        self.assertIn("Electrical Engineering", data["program_title"])
        self.assertEqual(data["source"], "PGO-PI-IGA.accdb")
        self.assertGreaterEqual(data["stats"]["total_courses"], 80)
        self.assertGreater(data["stats"]["prerequisite_links"], 50)
        self.assertGreater(data["stats"]["corequisite_links"], 10)
        self.assertGreater(len(data["terms"]), 5)
        self.assertGreater(len(data["edges"]), 50)

    def test_api_curriculum_flowchart_other_program(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/api/curriculum/flowchart?program=BSCE")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["program_code"], "BSCE")
        self.assertEqual(data["source"], "academic_catalog.db")
        self.assertGreater(data["stats"]["total_courses"], 0)

    def test_api_course_details_bsee_course(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/api/curriculum/course-details?course_code=EE%20211&program=BSEE")
        self.assertEqual(res.status_code, 200)
        details = res.get_json()
        self.assertEqual(details["code"], "EE 211")
        self.assertEqual(details["title"], "Electrical Circuits 1")
        self.assertIn("Nat Sci 2", details["prerequisites"])
        self.assertIn("Math 121", details["prerequisites"])
        self.assertIn("EE 221", details["postrequisites"])
        self.assertTrue(len(details["description"]) > 10)

    def test_api_course_details_not_found(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/api/curriculum/course-details?course_code=NONEXISTENT_999&program=BSEE")
        self.assertEqual(res.status_code, 404)

    def test_index_template_contains_curriculum_elements(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Check Ribbon Tab
        self.assertIn('id="ribbonTabCurriculum"', html)
        self.assertIn("Prerequisite Flowchart &amp; Curriculum Map", html)

        # Check Ribbon Command Band
        self.assertIn('id="ribbonBandCurriculum"', html)
        self.assertIn('id="curriculumProgramSelect"', html)
        self.assertIn('id="curriculumYearFilter"', html)
        self.assertIn('id="curriculumConnectorMode"', html)
        self.assertIn('id="flowchartSearchInput"', html)

        # Check Tab Panel
        self.assertIn('id="tab-curriculum"', html)
        self.assertIn('id="flowchartViewport"', html)
        self.assertIn('id="flowchartCanvas"', html)
        self.assertIn('id="flowchartSvg"', html)
        self.assertIn('id="flowchartColumnsContainer"', html)

        # Check Course Details Modal
        self.assertIn('id="courseDescriptionModal"', html)
        self.assertIn('id="modalCourseCodeBadge"', html)
        self.assertIn('id="modalCourseDescriptionText"', html)
        self.assertIn('id="modalPrereqsChipList"', html)
        self.assertIn('id="modalCoreqsChipList"', html)
        self.assertIn('id="modalPostreqsChipList"', html)
        self.assertIn('id="btnModalLocateFlowchart"', html)

    def test_api_pgo_pi_list_endpoint(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/api/curriculum/pgo-pi-list")
        self.assertEqual(res.status_code, 200)
        pgo_tree = res.get_json()
        self.assertIsInstance(pgo_tree, list)
        self.assertEqual(len(pgo_tree), 13)
        pgo_ids = [p["pgo"].lower() for p in pgo_tree]
        for ch in ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m"]:
            self.assertIn(ch, pgo_ids)
        # Check PIs for PGO a
        pgo_a = next(p for p in pgo_tree if p["pgo"].lower() == "a")
        self.assertGreaterEqual(len(pgo_a["pis"]), 1)
        self.assertIn("a.1", [pi["pi"] for pi in pgo_a["pis"]])

    def test_api_flowchart_includes_pgo_list_and_mappings(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/api/curriculum/flowchart?program=BSEE")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("pgo_list", data)
        self.assertEqual(len(data["pgo_list"]), 13)

        # Check course mappings exist
        mapped_courses = [c for c in data["courses"] if c.get("pgo_pi_mappings")]
        self.assertGreaterEqual(len(mapped_courses), 50)
        sample = mapped_courses[0]
        self.assertIn("pgo_id", sample["pgo_pi_mappings"][0])
        self.assertIn("pi", sample["pgo_pi_mappings"][0])
        self.assertIn("ied", sample["pgo_pi_mappings"][0])

    def test_pgo_pi_finder_and_ied_dom_elements(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Single PGO & PI Finder selectors in ribbon
        self.assertIn('id="curriculumPgoSelect"', html)
        self.assertIn('id="curriculumPiSelect"', html)
        # Redundant duplicate dropdowns removed from secondary toolbar
        self.assertNotIn('id="fcToolbarPgoSelect"', html)
        self.assertNotIn('id="fcToolbarPiSelect"', html)

        # I-E-D Legend & Alignment status chip in secondary area
        self.assertIn('id="fcAlignmentStatusChip"', html)
        self.assertIn('class="fc-legend-chip ied-i"', html)
        self.assertIn('class="fc-legend-chip ied-e"', html)
        self.assertIn('class="fc-legend-chip ied-d"', html)

        # Zoom controls (default 70% zoom and fit-to-screen)
        self.assertIn('autoFitFlowchartToScreen()', html)
        self.assertIn('setFlowchartZoom(0.70)', html)
        self.assertIn('zoomFlowchart(', html)
        self.assertIn('id="fcZoomDisplay"', html)
        self.assertIn('>70%</span>', html)

        # Removed Direct accdb button/badge
        self.assertNotIn('id="curriculumSourceBadge"', html)
        self.assertNotIn('>Direct accdb<', html)

        # Active Flow Arrows & Layering
        self.assertIn('@keyframes flowDash', html)
        self.assertIn('highlighted-pre', html)
        self.assertIn('highlighted-coreq', html)
        self.assertIn('z-index: 35;', html)

        # JavaScript functions
        self.assertIn('function getRecursiveDependencyChain(', html)
        self.assertIn('function applyPgoPiFilter(', html)
        self.assertIn('function clearPgoPiFilter(', html)
        self.assertIn('fc-node-prereq-transitive', html)
        self.assertIn('function onCourseNodeClick(', html)
        self.assertIn('function onCourseNodeHover(', html)
        self.assertIn('function onCourseNodeLeave(', html)

        # 1. Prerequisite trace disabled when PGO/PI is active
        self.assertIn('if (flowchartActivePgo || flowchartActivePi) return;', html)
        self.assertIn('if (flowchartSearchLocked) return;', html)

        # 2. Sleeker, reduced arrowhead marker dimensions
        self.assertIn('markerWidth="5" markerHeight="5"', html)
        self.assertIn('markerWidth="6.5" markerHeight="6.5"', html)
        self.assertIn('refX="7.5" refY="5"', html)

        # 3. Center-left to center-left routing for co-requisites forming bracket arc
        self.assertIn('function getNodeBox(el, canvas, scale)', html)
        self.assertIn('if (!isPrereq) {', html)
        self.assertIn('const srcLeftX = sBox.left;', html)
        self.assertIn('const tgtLeftX = tBox.left;', html)
        self.assertIn('const bracketX = Math.min(srcLeftX, tgtLeftX) - gutterOffset;', html)

        # 4. Auto-Deselect Course & Clear Prerequisite Arrows on PGO/PI Selection
        self.assertIn('function clearCourseSelectionAndPrerequisites()', html)
        self.assertIn("path.classList.remove('dimmed', 'highlighted-pre', 'highlighted-coreq', 'highlighted-post');", html)
        self.assertIn('function onCurriculumPgoSelect(pgoId) {\n  // Step 1: Auto-deselect course and immediately clear any active prerequisite/co-requisite chain and arrows\n  clearCourseSelectionAndPrerequisites();', html)
        self.assertIn('function onCurriculumPiSelect(piId) {\n  // Step 1: Auto-deselect course and immediately clear any active prerequisite/co-requisite chain and arrows\n  clearCourseSelectionAndPrerequisites();', html)

        # 5. Course card click vs Details button separation
        self.assertIn("onclick=\"onCourseNodeClick(event, '${codeAttr}')\"", html)
        self.assertIn("onclick=\"event.stopPropagation(); openCourseDetailsModal('${codeAttr}')\"", html)

        # 6. Search lock state
        self.assertIn('let flowchartSearchLocked = false;', html)
        self.assertIn('function searchFlowchartCourses(', html)
        self.assertIn('function clearFlowchartSearch(', html)

    def test_api_curriculum_advisor_failed_course(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.post(
            "/api/curriculum/advisor",
            json={"query": "What courses can I take next semester if I failed EE 211?", "program": "BSEE"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("intent"), "failed_course_impact")
        failed_codes = [c["code"] if isinstance(c, dict) else c for c in data.get("failed_courses", [])]
        self.assertIn("EE 211", failed_codes)
        target_term = data.get("target_term", {})
        self.assertEqual(target_term.get("key"), "Y2S2")
        self.assertGreater(len(data.get("blocked_courses_target", [])), 0)
        self.assertGreater(len(data.get("eligible_courses_target", [])), 0)
        self.assertIn("highlight_action", data)
        hl = data["highlight_action"]
        self.assertIn("EE 211", hl.get("retake", []))
        self.assertIn("EE 221", hl.get("blocked", []))
        self.assertIn("EE 222", hl.get("eligible", []))

    def test_api_curriculum_advisor_prerequisite_inquiry(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.post(
            "/api/curriculum/advisor",
            json={"query": "What are the prerequisites for EE 415?", "program": "BSEE"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("intent"), "prerequisite_inquiry")
        self.assertEqual(data.get("course", {}).get("code"), "EE 415")
        self.assertIn("advice_markdown", data)
        self.assertIn("EE 415", data["advice_markdown"])

    def test_ied_terminology_introductory_enabling_demonstrative(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Strictly verify Introductory, Enabling, Demonstrative
        self.assertIn("Introductory", html)
        self.assertIn("Enabling", html)
        self.assertIn("Demonstrative", html)

    def test_course_details_modal_year_level_requirement(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('id="modalYearLevelReqSection"', html)
        self.assertIn('id="modalYearLevelReqBadge"', html)
        self.assertIn('Year Level Requirement', html)

        # Verify strict placement: modalYearLevelReqSection appears immediately above Pre-requisites section
        idx_year_req = html.find('id="modalYearLevelReqSection"')
        idx_prereqs = html.find('Pre-requisites', idx_year_req)
        self.assertNotEqual(idx_year_req, -1)
        self.assertNotEqual(idx_prereqs, -1)
        self.assertLess(idx_year_req, idx_prereqs)

    def test_curriculum_guide_ai_drawer_and_floating_trigger(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('id="curriculumAiDrawer"', html)
        self.assertIn('id="fcAiFloatingTrigger"', html)
        self.assertIn('id="btnRibbonToggleAi"', html)
        self.assertIn('id="curriculumAiInput"', html)
        self.assertIn('id="curriculumAiMessages"', html)
        self.assertIn('function toggleCurriculumAiDrawer(', html)
        self.assertIn('function submitCurriculumAiQuery(', html)

    def test_flowchart_course_year_level_requirement_data(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/api/curriculum/flowchart?program=BSEE")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("program_code"), "BSEE")
        courses = data.get("courses", [])
        self.assertGreater(len(courses), 0)

        for course in courses:
            self.assertIn("year_level_requirement", course)
            self.assertTrue(len(course["year_level_requirement"]) > 0)

    def test_flowchart_default_70_percent_zoom_lock(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 70% zoom indicator
        self.assertIn('id="fcZoomDisplay"', html)
        self.assertIn('>70%</span>', html)

        # Zoom initialization and reset strictly lock to 70%
        self.assertIn('setFlowchartZoom(0.70)', html)
        self.assertIn('// Enforce 70% default zoom level on initial and reloaded curriculum view\n    setFlowchartZoom(0.70);', html)
        self.assertIn('// Strictly enforce 70% zoom level on reset view\n  setFlowchartZoom(0.70);', html)

    def test_curriculum_advisor_endpoint_methods_and_aliases(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        # POST /api/curriculum/advisor
        res1 = self.client.post("/api/curriculum/advisor", json={"query": "What are the prerequisites for EE 211?", "program": "BSEE"})
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.get_json().get("success"))

        # GET /api/curriculum/advisor
        res2 = self.client.get("/api/curriculum/advisor?query=What+are+the+prerequisites+for+EE+211%3F&program=BSEE")
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.get_json().get("success"))

        # POST /curriculum/advisor (alias)
        res3 = self.client.post("/curriculum/advisor", json={"query": "What are the prerequisites for EE 211?", "program": "BSEE"})
        self.assertEqual(res3.status_code, 200)
        self.assertTrue(res3.get_json().get("success"))

        # GET /curriculum/advisor (alias)
        res4 = self.client.get("/curriculum/advisor?query=What+are+the+prerequisites+for+EE+211%3F&program=BSEE")
        self.assertEqual(res4.status_code, 200)
        self.assertTrue(res4.get_json().get("success"))

    def test_curriculum_advisor_resilience_multi_queries(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        test_cases = [
            ("What happens if I fail Nat Sci 2?", "failed_course_impact"),
            ("What courses can I take next semester if I failed EE 211?", "failed_course_impact"),
            ("What are the prerequisites for EE 415?", "prerequisite_inquiry"),
            ("What is required for 4th year standing?", "general_curriculum_info"),
            ("hello advice", "general_guidance"),
            ("Which courses are blocked if I fail EE 311?", "failed_course_impact"),
        ]

        for query_text, expected_intent in test_cases:
            res = self.client.post(
                "/api/curriculum/advisor",
                json={"query": query_text, "program": "BSEE", "history": []}
            )
            self.assertEqual(res.status_code, 200, f"Failed on query: {query_text}")
            data = res.get_json()
            self.assertTrue(data.get("success"), f"Expected success:True for {query_text}")
            self.assertEqual(data.get("intent"), expected_intent, f"Wrong intent for {query_text}")
            self.assertTrue(data.get("advice_markdown"), f"Empty advice for {query_text}")
            self.assertIn("highlight_action", data)
            self.assertIn("blocked", data["highlight_action"])
            self.assertIn("eligible", data["highlight_action"])
            self.assertIn("retake", data["highlight_action"])

    def test_curriculum_advisor_null_and_fallback_resilience(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        # Missing or None program should cleanly default to BSEE
        res = self.client.post(
            "/api/curriculum/advisor",
            json={"query": "What if I fail EE 211?", "program": None}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("intent"), "failed_course_impact")

        # Unknown course code returns clean guidance without 500 error
        res2 = self.client.post(
            "/api/curriculum/advisor",
            json={"query": "I failed UNKNOWN 999", "program": "BSEE"}
        )
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2.get("success"))
        self.assertTrue(len(data2.get("advice_markdown", "")) > 0)

    def test_pgo_pi_alignment_filtering_and_ied_classes(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # I-E-D highlight CSS classes
        self.assertIn('.flowchart-node.fc-ied-i', html)
        self.assertIn('.flowchart-node.fc-ied-e', html)
        self.assertIn('.flowchart-node.fc-ied-d', html)
        self.assertIn('.fc-ied-pill.i', html)
        self.assertIn('.fc-ied-pill.e', html)
        self.assertIn('.fc-ied-pill.d', html)
        self.assertIn('<span class="fc-ied-pill"', html)
        self.assertIn('function parseClientPgoPiString(', html)

        # API check
        api_res = self.client.get("/api/curriculum/flowchart?program=BSEE")
        self.assertEqual(api_res.status_code, 200)
        data = api_res.get_json()
        courses = data["courses"]
        self.assertGreaterEqual(len(courses), 80)
        # All courses have pgo_pi_mappings
        mapped = [c for c in courses if c.get("pgo_pi_mappings")]
        self.assertEqual(len(mapped), len(courses))

        # Check PGO 'a' aggregation
        pgo_a_courses = [
            c for c in courses
            if any(m.get("pgo_id") == "a" or (m.get("pgo") or "").lower().endswith(" a") for m in c.get("pgo_pi_mappings", []))
        ]
        self.assertGreaterEqual(len(pgo_a_courses), 20)

        # Check PI specific 'a.1'
        pi_a1_courses = [
            c for c in courses
            if any(m.get("pi") == "a.1" for m in c.get("pgo_pi_mappings", []))
        ]
        self.assertGreaterEqual(len(pi_a1_courses), 10)


if __name__ == "__main__":
    unittest.main()
