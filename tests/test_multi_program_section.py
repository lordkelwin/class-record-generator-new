import os
import unittest
import tempfile
import json
from models import CourseMetadata, SyllabusBlueprint
import courses_store
from syllabus_pdf_generator import generate_usep_syllabus_pdf
from clo_report_pdf_generator import generate_clo_report_pdf_bytes
from excel_generator import generate_class_record_workbook
from sample_syllabus import get_default_blueprint, get_blank_blueprint


class TestMultiProgramAndSection(unittest.TestCase):

    def test_metadata_defaults(self):
        m = CourseMetadata()
        self.assertEqual(m.program_code, "EE")
        self.assertEqual(m.programs, ["EE"])
        self.assertEqual(m.section, "EE 2A")
        self.assertEqual(m.sections, ["EE 2A"])
        self.assertEqual(m.program_names, ["Bachelor of Science in Electrical Engineering"])
        self.assertEqual(m.program_name, "Bachelor of Science in Electrical Engineering")

    def test_metadata_multi_programs_and_sections(self):
        m = CourseMetadata(
            programs=["EE", "CE", "ME"],
            sections=["EE 1A", "CE 1A", "ME 1A"]
        )
        self.assertEqual(m.programs, ["EE", "CE", "ME"])
        self.assertEqual(m.program_code, "EE, CE, ME")
        self.assertEqual(m.sections, ["EE 1A", "CE 1A", "ME 1A"])
        self.assertEqual(m.section, "EE 1A, CE 1A, ME 1A")
        self.assertEqual(len(m.program_names), 3)
        self.assertIn("Electrical Engineering", m.program_names[0])
        self.assertIn("Civil Engineering", m.program_names[1])
        self.assertIn("Mechanical Engineering", m.program_names[2])

    def test_metadata_backward_compat_from_comma_strings(self):
        m = CourseMetadata(
            program_code="EE, CE",
            section="EE 2A, CE 2A"
        )
        self.assertEqual(m.programs, ["EE", "CE"])
        self.assertEqual(m.sections, ["EE 2A", "CE 2A"])
        self.assertEqual(len(m.program_names), 2)
        self.assertIn("Electrical Engineering", m.program_names[0])
        self.assertIn("Civil Engineering", m.program_names[1])

    def test_blueprint_serialization(self):
        bp = get_blank_blueprint(
            course_code="MATH 111",
            course_title="Engineering Calculus 1",
            programs=["EE", "CE", "ECE", "ME"],
            sections=["EE 1A", "CE 1A", "ECE 1A", "ME 1A"],
        )
        data = bp.to_dict()
        self.assertEqual(data["metadata"]["programs"], ["EE", "CE", "ECE", "ME"])
        self.assertEqual(data["metadata"]["sections"], ["EE 1A", "CE 1A", "ECE 1A", "ME 1A"])
        self.assertEqual(data["metadata"]["program_code"], "EE, CE, ECE, ME")
        self.assertEqual(data["metadata"]["section"], "EE 1A, CE 1A, ECE 1A, ME 1A")

        rebuilt = SyllabusBlueprint.from_dict(data)
        self.assertEqual(rebuilt.metadata.programs, ["EE", "CE", "ECE", "ME"])
        self.assertEqual(rebuilt.metadata.sections, ["EE 1A", "CE 1A", "ECE 1A", "ME 1A"])
        self.assertEqual(rebuilt.metadata.program_code, "EE, CE, ECE, ME")
        self.assertEqual(rebuilt.metadata.section, "EE 1A, CE 1A, ECE 1A, ME 1A")

    def test_courses_store_multi_program_lifecycle(self):
        username = "test_multi_prog_user"
        doc = courses_store.create_course(
            username=username,
            course_code="PHYS 121",
            course_title="Physics for Engineers",
            section="EE 1A, CE 1A",
            semester_ay="1st Semester, A.Y. 2026-2027",
            programs=["EE", "CE"],
            sections=["EE 1A", "CE 1A"]
        )
        cid = doc["id"]
        try:
            fetched = courses_store.get_course(username, cid)
            self.assertIsNotNone(fetched)
            meta = fetched["blueprint"]["metadata"]
            self.assertEqual(meta["programs"], ["EE", "CE"])
            self.assertEqual(meta["sections"], ["EE 1A", "CE 1A"])
            self.assertEqual(meta["program_code"], "EE, CE")
            self.assertEqual(meta["section"], "EE 1A, CE 1A")

            # Check list_courses summary
            c_list = courses_store.list_courses(username)
            matching = [c for c in c_list["courses"] if c["id"] == cid]
            self.assertEqual(len(matching), 1)
            summary = matching[0]
            self.assertEqual(summary["programs"], ["EE", "CE"])
            self.assertEqual(summary["sections"], ["EE 1A", "CE 1A"])
            self.assertEqual(summary["section"], "EE 1A, CE 1A")
            self.assertEqual(summary["program_code"], "EE, CE")

            # Save / update with a third program and section
            fetched["blueprint"]["metadata"]["programs"] = ["EE", "CE", "ME"]
            fetched["blueprint"]["metadata"]["sections"] = ["EE 1A", "CE 1A", "ME 1A"]
            updated = courses_store.save_course(username, cid, {
                "course_code": "PHYS 121",
                "course_title": "Physics for Engineers",
                "section": "EE 1A, CE 1A, ME 1A",
                "programs": ["EE", "CE", "ME"],
                "sections": ["EE 1A", "CE 1A", "ME 1A"],
                "blueprint": fetched["blueprint"]
            })
            self.assertEqual(updated["blueprint"]["metadata"]["programs"], ["EE", "CE", "ME"])
            self.assertEqual(updated["blueprint"]["metadata"]["sections"], ["EE 1A", "CE 1A", "ME 1A"])
        finally:
            courses_store.delete_course(username, cid)

    def test_pdf_and_excel_exports_with_multi_programs(self):
        bp = get_default_blueprint(include_sample_scores=True)
        bp.metadata.programs = ["EE", "CE", "ME"]
        bp.metadata.sections = ["EE 2A", "CE 2A", "ME 2A"]
        bp.metadata.program_code = "EE, CE, ME"
        bp.metadata.section = "EE 2A, CE 2A, ME 2A"

        # 1. Syllabus PDF bytes
        pdf_bytes = generate_usep_syllabus_pdf(bp)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 5000)

        # 2. CLO Report PDF bytes
        clo_pdf_bytes = generate_clo_report_pdf_bytes(bp)
        self.assertIsInstance(clo_pdf_bytes, bytes)
        self.assertGreater(len(clo_pdf_bytes), 5000)

        # 3. Excel Class Record Workbook bytes
        excel_bytes = generate_class_record_workbook(bp)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 5000)


if __name__ == "__main__":
    unittest.main()
