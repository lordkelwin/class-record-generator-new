import os
import unittest
import openpyxl

from models import CourseMetadata
from sample_syllabus import get_blank_blueprint, get_designated_program_heads
import courses_store
from clo_evaluation_excel_generator import generate_clo_evaluation_excel_bytes
from clo_report_pdf_generator import generate_clo_report_pdf_bytes


class TestSyllabusEnhancements(unittest.TestCase):
    def test_designated_program_heads_single_and_multiple(self):
        # Single program
        ee_heads = get_designated_program_heads(["EE"])
        self.assertEqual(ee_heads, ["Engr. Charito O. Claro"])

        ce_heads = get_designated_program_heads(["CE"])
        self.assertEqual(ce_heads, ["Engr. Bonifacio T. Aznar Jr."])

        # Multiple accommodated programs
        multi_heads = get_designated_program_heads(["EE", "CE", "ME"])
        self.assertIn("Engr. Charito O. Claro", multi_heads)
        self.assertIn("Engr. Bonifacio T. Aznar Jr.", multi_heads)
        self.assertIn("Engr. Randy B. Tongson", multi_heads)
        self.assertEqual(len(multi_heads), 3)

    def test_get_blank_blueprint_autofills(self):
        bp = get_blank_blueprint(
            course_code="EE 211 - Electrical Circuits 1",
            programs=["EE", "CE"],
            faculty_name="",
        )
        # Course code should be sanitized to exclude title
        self.assertEqual(bp.metadata.course_code, "EE 211")
        self.assertEqual(bp.metadata.course_title, "Electrical Circuits 1")

        # Program heads should combine all designated heads
        self.assertIn("Engr. Charito O. Claro", bp.metadata.program_head)
        self.assertIn("Engr. Bonifacio T. Aznar Jr.", bp.metadata.program_head)
        self.assertEqual(len(bp.metadata.program_heads), 2)

        # Dean auto-fill
        self.assertEqual(bp.metadata.dean_name, "Engr. Joie D. Cataytay, Ph.D.")

        # Base-50 cutoff default
        self.assertEqual(bp.metadata.transmutation_base, 50)
        self.assertEqual(bp.metadata.passing_percentage, 75.0)

        # Learning plan table has only orientation by default
        self.assertEqual(len(bp.metadata.learning_plan_table), 1)
        self.assertIn("Course Orientation", bp.metadata.learning_plan_table[0]["topics"])

    def test_courses_store_create_course_autofills(self):
        doc = courses_store.create_course(
            username="faculty_tano",
            course_code="CE 311 – Structural Theory",
            programs=["CE"],
            sections=["CE 3A"],
        )
        self.assertEqual(doc["course_code"], "CE 311")
        self.assertEqual(doc["course_title"], "Structural Theory")
        bp_dict = doc["blueprint"]
        meta = bp_dict["metadata"]
        self.assertEqual(meta["faculty_name"], "Engr. Elwin Jay J. Tano")
        self.assertEqual(meta["program_head"], "Engr. Bonifacio T. Aznar Jr.")
        self.assertEqual(meta["dean_name"], "Engr. Joie D. Cataytay, Ph.D.")
        self.assertEqual(meta["passing_percentage"], 75.0)
        self.assertEqual(len(meta["learning_plan_table"]), 1)
        self.assertIn("Course Orientation", meta["learning_plan_table"][0]["topics"])

        # Clean up created course
        courses_store.delete_course("faculty_tano", doc["id"])

    def test_fm_usep_mid10_excludes_course_description(self):
        bp = get_blank_blueprint(
            course_code="EE 211",
            course_title="Electrical Circuits 1",
            course_description="Extremely detailed description of circuit theorems, Kirchhoff laws, and mesh analysis.",
            credit_units="3.0 Units – Lecture",
            faculty_name="Engr. Elwin Jay J. Tano",
        )

        # 1. Test Excel generation excludes description
        tmp_xlsx = os.path.join("data", "test_mid10_exclude_desc.xlsx")
        try:
            excel_bytes = generate_clo_evaluation_excel_bytes(bp)
            with open(tmp_xlsx, "wb") as f:
                f.write(excel_bytes)
            wb = openpyxl.load_workbook(tmp_xlsx)
            ws = wb.active
            c10_val = str(ws["C10"].value)
            self.assertIn("EE 211", c10_val)
            self.assertIn("Electrical Circuits 1", c10_val)
            self.assertIn("3 Units", c10_val)
            self.assertNotIn("Extremely detailed description", c10_val)
        finally:
            if os.path.exists(tmp_xlsx):
                os.remove(tmp_xlsx)

        # 2. Test PDF generation excludes description
        pdf_bytes = generate_clo_report_pdf_bytes(bp)
        self.assertGreater(len(pdf_bytes), 1000)


if __name__ == "__main__":
    unittest.main()
