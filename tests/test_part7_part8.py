import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import courses_store


class Part7Part8RubricsTestCase(unittest.TestCase):
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
        if not doc.get("blueprint"):
            doc["blueprint"] = {}
        doc["blueprint"]["rubrics"] = []
        courses_store.save_course_doc(doc)

    def tearDown(self):
        try:
            courses_store.delete_course(self.username, self.course_id)
        except Exception:
            pass

    def test_rubrics_workflow_and_pdf_export(self):
        with self.client.session_transaction() as sess:
            sess["username"] = self.username

        c_id = self.course_id
        res = self.client.get(f"/api/courses/{c_id}")
        self.assertEqual(res.status_code, 200)
        bp = res.get_json()["blueprint"]
        rubrics = bp.get("rubrics", [])
        self.assertEqual(len(rubrics), 0)

        custom_rubric = {
            "rubric_id": "rub_custom_fac_1",
            "title": "Custom Analytic Rubric",
            "assessment_code": "SA1",
            "target_part": "Entire Assessment",
            "used_for": "Faculty Defined Assessment",
            "clo_ids": ["CLO1"],
            "scale_type": "points_5",
            "levels": [
                {"level": 5, "label": "Excellent (5)"},
                {"level": 3, "label": "Satisfactory (3)"},
                {"level": 0, "label": "Unacceptable (0)"}
            ],
            "criteria": [
                {"name": "Accuracy", "weight_pct": 50.0, "descriptors": ["Exact", "Partial", "Wrong"]},
                {"name": "Clarity", "weight_pct": 50.0, "descriptors": ["Clear", "Adequate", "Unclear"]}
            ],
            "notes": "Faculty custom rubric"
        }
        bp["rubrics"] = [custom_rubric]
        save_res = self.client.put(f"/api/courses/{c_id}", json={"blueprint": bp})
        self.assertEqual(save_res.status_code, 200)

        res = self.client.get(f"/api/courses/{c_id}/export-pdf")
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.data), 10000)


if __name__ == "__main__":
    unittest.main()
