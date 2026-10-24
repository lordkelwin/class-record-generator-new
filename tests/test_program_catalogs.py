# tests/test_program_catalogs.py
"""
Test suite validating the integrity and completeness of the course catalogs across
all 9 undergraduate degree programs in the USeP College of Engineering:
  1. EE: Electrical Engineering (CMO 88 s. 2017)
  2. CE: Civil Engineering - Structural Track (CMO 92 s. 2017)
  3. ECE: Electronics Engineering (CMO 101 s. 2017)
  4. ME: Mechanical Engineering (CMO 97 s. 2017)
  5. SE: Sanitary Engineering (CMO 98 s. 2017)
  6. ABE: Agricultural and Biosystems Engineering (CMO 94 s. 2017)
  7. GE: Geodetic Engineering (CMO 89 s. 2017)
  8. MinE: Mining Engineering (CMO 100 s. 2017)
  9. BSGeo: Geology (CMO 44 s. 2017 / CMO 35 s. 2008)
"""

import unittest
import catalog_data
import program_structures


class TestProgramCatalogs(unittest.TestCase):

    def setUp(self):
        self.catalog = catalog_data.get_full_catalog()
        self.college = self.catalog["colleges"][0]
        self.departments = {d["program_code"]: d for d in self.college["departments"]}

    def test_all_nine_programs_present(self):
        """Assert all 9 engineering and geology programs are present in the catalog."""
        expected_codes = {"EE", "CE", "ECE", "ME", "SE", "ABE", "GE", "MinE", "BSGeo"}
        self.assertEqual(set(self.departments.keys()), expected_codes)

    def test_minimum_course_counts(self):
        """Assert each program has a comprehensive course roster matching its curriculum map."""
        expected_minimums = {
            "EE": 70,     # 85 courses
            "CE": 65,     # 72 courses
            "ECE": 70,    # 79 courses
            "ME": 70,     # 78 courses
            "SE": 60,     # 71 courses
            "ABE": 60,    # 69 courses
            "GE": 60,     # 67 courses
            "MinE": 60,   # 68 courses
            "BSGeo": 55,  # 64 courses
        }
        for code, min_count in expected_minimums.items():
            dept = self.departments[code]
            courses = dept["courses"]
            self.assertGreaterEqual(
                len(courses),
                min_count,
                f"Program {code} should have at least {min_count} courses, found {len(courses)}"
            )

    def test_course_schema_completeness(self):
        """Assert each course in every program satisfies all required metadata fields."""
        required_str_fields = ["code", "title", "credit_units", "lec_lab", "hours", "prereqs", "coreqs", "pgo_pi", "sdgs", "description"]
        
        for code, dept in self.departments.items():
            courses = dept["courses"]
            seen_codes = set()
            for c in courses:
                # Required string fields
                for f in required_str_fields:
                    self.assertIn(f, c, f"Course in {code} missing field '{f}': {c.get('code')}")
                    self.assertIsInstance(c[f], str, f"Field '{f}' must be str in {code}: {c.get('code')}")
                    self.assertTrue(c[f].strip(), f"Field '{f}' cannot be blank in {code}: {c.get('code')}")

                # Topics must be a non-empty list of strings
                self.assertIn("topics", c, f"Course in {code} missing 'topics': {c.get('code')}")
                self.assertIsInstance(c["topics"], list, f"'topics' must be list in {code}: {c.get('code')}")
                self.assertGreaterEqual(len(c["topics"]), 2, f"Course {c.get('code')} in {code} must have at least 2 topics")
                for t in c["topics"]:
                    self.assertIsInstance(t, str)
                    self.assertTrue(t.strip())

                # Check unique code per program
                course_code = c["code"].strip()
                self.assertNotIn(course_code, seen_codes, f"Duplicate course code '{course_code}' in {code}")
                seen_codes.add(course_code)

    def test_department_program_structure_alignment(self):
        """Assert each department metadata aligns with program_structures.py."""
        for code, dept in self.departments.items():
            struct = program_structures.PROGRAM_STRUCTURES_BY_CODE[code]
            self.assertEqual(dept["cmo_reference"], struct["cmo_reference"])
            self.assertEqual(dept["source_file"], struct["source_file"])
            self.assertEqual(len(dept["peos"]), len(struct["peos"]))
            self.assertEqual(len(dept["pgo_pi_catalog"]), len(struct["pgo_pi_catalog"]))


if __name__ == "__main__":
    unittest.main()
