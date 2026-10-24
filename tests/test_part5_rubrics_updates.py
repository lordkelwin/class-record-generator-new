# tests/test_part5_rubrics_updates.py
import unittest
from models import SyllabusBlueprint
from sample_syllabus import get_blank_blueprint
from syllabus_pdf_generator import generate_usep_syllabus_pdf

class TestPart5RubricsUpdates(unittest.TestCase):

    def test_passing_grade_conditions_removed_from_part5(self):
        with open("templates/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        # Should NOT be in the Part V Course Description / Workload grid
        part5_marker = 'Course Description (Part V)'
        part5_idx = html.find(part5_marker)
        self.assertNotEqual(part5_idx, -1)
        part5_sub = html[part5_idx:part5_idx + 800]
        self.assertNotIn('Passing Grade Conditions', part5_sub)

        # Should be in Part VIII (Grading Plan)
        part8_marker = 'Transmutation &amp; Passing Conditions'
        part8_idx = html.find(part8_marker)
        self.assertNotEqual(part8_idx, -1)
        part8_sub = html[part8_idx:part8_idx + 800]
        self.assertIn('Passing Grade Conditions:', part8_sub)
        self.assertIn('id="meta_passing_grade_conditions"', part8_sub)

    def test_rubric_multi_assessment_pdf_generation(self):
        bp = get_blank_blueprint(course_code="EE 312", course_title="Power Systems Analysis", program_code="EE")
        # Add a single rubric that accommodates multiple assessments: SA1, SA2, and Term Exam
        bp.rubrics = [
            {
                "rubric_id": "rub_multi_1",
                "title": "Problem Solving & Calculation Rubric",
                "assessment_codes": ["SA1", "SA2", "FTE"],
                "target_part": "Problem Solving Items",
                "used_for": "Summative Problem Solving Portion",
                "clo_ids": ["CLO1", "CLO2"],
                "enable_criteria_clos": False,  # disabled by default
                "levels": [
                    {"level": 5, "label": "Excellent (5)"},
                    {"level": 3, "label": "Satisfactory (3)"},
                    {"level": 1, "label": "Unsatisfactory (1)"},
                ],
                "criteria": [
                    {
                        "name": "Mathematical Formulation",
                        "weight_pct": 50.0,
                        "clo_id": "CLO1",  # present in dict, but should be ignored in PDF because enable_criteria_clos=False
                        "descriptors": ["Exemplary formulation", "Adequate formulation", "Poor formulation"]
                    },
                    {
                        "name": "Calculations & Accuracy",
                        "weight_pct": 50.0,
                        "clo_id": "CLO2",
                        "descriptors": ["Zero error", "Minor errors", "Major errors"]
                    }
                ]
            }
        ]

        pdf_bytes = generate_usep_syllabus_pdf(bp)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 5000)

        # Now test with enable_criteria_clos=True
        bp.rubrics[0]["enable_criteria_clos"] = True
        pdf_bytes_with_clos = generate_usep_syllabus_pdf(bp)
        self.assertIsInstance(pdf_bytes_with_clos, bytes)
        self.assertGreater(len(pdf_bytes_with_clos), 5000)

    def test_html_contains_multi_assessment_and_criteria_clo_elements(self):
        with open("templates/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        # Accommodates group and functions
        self.assertIn('function rubricAccommodatesAssessment(rub, actCode)', html)
        self.assertIn('function toggleRubricAssessmentCode(rIdx, actCode)', html)
        self.assertIn('function updateRubricAssessmentCodes(rIdx, val)', html)
        self.assertIn('Accommodates:', html)

        # Criteria CLO toggle (disabled by default)
        self.assertIn('function toggleRubricCriteriaClos(rIdx)', html)
        self.assertIn('Aligned CLO per Criteria:', html)
        self.assertIn('Disabled (Default)', html)
        self.assertIn('enable_criteria_clos: false', html)

if __name__ == "__main__":
    unittest.main()
