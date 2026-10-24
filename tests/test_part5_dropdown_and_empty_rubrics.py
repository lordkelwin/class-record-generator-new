import os
import unittest
import tempfile
import json
from models import CourseMetadata, SyllabusBlueprint
import courses_store
from syllabus_pdf_generator import generate_usep_syllabus_pdf
from sample_syllabus import get_default_blueprint, get_blank_blueprint, get_default_rubrics


class TestPart5DropdownAndEmptyRubrics(unittest.TestCase):

    def test_rubrics_empty_by_default(self):
        # 1. get_default_rubrics returns empty list
        self.assertEqual(get_default_rubrics(), [])

        # 2. get_default_blueprint has empty rubrics
        bp_default = get_default_blueprint(include_sample_scores=False)
        self.assertEqual(bp_default.rubrics, [])

        # 3. get_blank_blueprint has empty rubrics
        bp_blank = get_blank_blueprint()
        self.assertEqual(bp_blank.rubrics, [])

        # 4. Deserialization from dict with no rubrics preserves empty list
        data = bp_default.to_dict()
        self.assertEqual(data.get("rubrics"), [])
        rebuilt = SyllabusBlueprint.from_dict(data)
        self.assertEqual(rebuilt.rubrics, [])

    def test_pdf_export_without_rubrics(self):
        bp = get_default_blueprint(include_sample_scores=False)
        self.assertEqual(bp.rubrics, [])
        pdf_bytes = generate_usep_syllabus_pdf(bp)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 5000)

    def test_part5_prereq_coreq_structure(self):
        bp = get_blank_blueprint(
            course_code="EE 211",
            course_title="Electrical Circuits 1",
            program_code="EE",
            prerequisites="MATH 121 - ENGINEERING CALCULUS 2",
            corequisites="EE 211L - ELECTRICAL CIRCUITS 1 LAB"
        )
        # Verify prereq_coreq_table is structured with course_code and course_title
        table = bp.metadata.prereq_coreq_table
        self.assertGreaterEqual(len(table), 2)
        prereq = next(r for r in table if "pre" in r["req_type"].lower())
        self.assertEqual(prereq["course_code"], "MATH 121")
        self.assertEqual(prereq["course_title"], "ENGINEERING CALCULUS 2")

        coreq = next(r for r in table if "co" in r["req_type"].lower())
        self.assertEqual(coreq["course_code"], "EE 211L")
        self.assertEqual(coreq["course_title"], "ELECTRICAL CIRCUITS 1 LAB")


if __name__ == "__main__":
    unittest.main()
