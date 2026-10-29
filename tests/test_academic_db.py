"""
Unit tests for academic_catalog.db and academic_db.py module.
Verifies that:
1. All 9 programs are properly registered.
2. All faculty have their honorifics removed (e.g. 'Elwin Jay J. Tano', 'Joie D. Cataytay').
3. Courses are correctly queried with prerequisites, corequisites, and year levels.
4. Search queries work properly across courses.
"""

import os
import unittest
import academic_db


class TestAcademicDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        academic_db.init_academic_db()

    def test_programs_count_and_details(self):
        programs = academic_db.get_all_programs()
        self.assertGreaterEqual(len(programs), 9)
        codes = [p["code"] for p in programs]
        for expected in ["BSEE", "BSCE", "BSECE", "BSME", "BSSE", "BSABE", "BSGeo", "BSGE", "BSMinE"]:
            self.assertIn(expected, codes)

        ee_prog = academic_db.get_program("BSEE")
        self.assertIsNotNone(ee_prog)
        self.assertEqual(ee_prog["program_head"], "Charito O. Claro")
        self.assertNotIn("Engr.", ee_prog["program_head"])

    def test_faculty_have_no_honorifics(self):
        faculty = academic_db.get_all_faculty()
        self.assertGreaterEqual(len(faculty), 70)
        for f in faculty:
            full_name = f["full_name"]
            # Verify no honorific prefix or suffix
            for prefix in ["Engr.", "Dr.", "Prof.", "Hon.", "Mr.", "Ms.", "Mrs.", "Atty."]:
                self.assertFalse(full_name.startswith(prefix), f"Faculty {full_name} has prefix {prefix}")
            for suffix in ["Ph.D.", ", Ph.D.", "PECE", "PEE"]:
                self.assertNotIn(suffix, full_name, f"Faculty {full_name} has suffix {suffix}")

    def test_course_lookup_and_prerequisites(self):
        ee_courses = academic_db.get_courses_by_program("BSEE")
        self.assertGreater(len(ee_courses), 50)

        ee211 = academic_db.get_course("EE 211", "BSEE")
        self.assertIsNotNone(ee211)
        self.assertEqual(ee211["course_code"], "EE 211")
        self.assertEqual(ee211["course_title"], "Electrical Circuits 1")
        self.assertEqual(ee211["year_level"], "Second Year")
        self.assertIn("Math 121", ee211["prerequisites"])
        self.assertIn("EE 211L", ee211["corequisites"])

    def test_course_search(self):
        results = academic_db.search_courses("Circuits", "BSEE")
        self.assertGreater(len(results), 0)
        codes = [c["course_code"] for c in results]
        self.assertIn("EE 211", codes)

    def test_dean_details_clean(self):
        dean = academic_db.get_dean()
        self.assertEqual(dean["name"], "Joie D. Cataytay")
        self.assertNotIn("Engr.", dean["name"])
        self.assertNotIn("Ph.D.", dean["name"])


if __name__ == "__main__":
    unittest.main()
