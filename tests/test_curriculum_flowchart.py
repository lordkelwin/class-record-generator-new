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


if __name__ == "__main__":
    unittest.main()
