import unittest
import copy
from sample_syllabus import get_blank_blueprint, DEFAULT_ORIENTATION_ROW, parse_sdg_string_to_table, parse_prereqs_coreqs_to_table
import syllabus_workflow
import courses_store
import student_store


class TestAutoDisplayAndAcknowledgmentWorkflow(unittest.TestCase):
    def test_blank_blueprint_default_content(self):
        bp = get_blank_blueprint(
            course_code="EE 211",
            course_title="Electrical Circuits 1",
            prerequisites="Math 121 - Calculus 2",
            corequisites="EE 211L - Circuits Lab",
            sdg_alignments="7: Affordable and Clean Energy; 9: Industry, Innovation, and Infrastructure"
        )
        # 1. Part IX must ONLY contain the Orientation row by default
        self.assertEqual(len(bp.metadata.learning_plan_table), 1)
        self.assertIn("Course Orientation", bp.metadata.learning_plan_table[0]["topics"])
        self.assertEqual(bp.metadata.learning_plan_table[0]["time_frame"], "1 hour")

        # 2. Part XI policies must be immediately populated
        self.assertGreater(len(bp.metadata.policies_table), 0)
        self.assertTrue(any("Attendance" in p.get("title", "") for p in bp.metadata.policies_table))

        # 3. Prerequisites must be auto-populated
        self.assertEqual(len(bp.metadata.prereq_coreq_table), 2)
        self.assertEqual(bp.metadata.prereq_coreq_table[0]["course_code"], "Math 121")
        self.assertEqual(bp.metadata.prereq_coreq_table[1]["course_code"], "EE 211L")

        # 4. SDGs must be auto-populated
        self.assertGreater(len(bp.metadata.sdg_table), 0)

    def test_create_course_from_catalog(self):
        catalog_sample = {
            "code": "EE 312",
            "title": "Feedback and Control Systems",
            "credit_units": "3.0 Units – Lecture",
            "lec_lab": "Lecture",
            "hours": "3 Hours/Week",
            "year_level": "Third Year",
            "prereqs": "EE 211 - Electrical Circuits 1",
            "coreqs": "None",
            "sdgs": "SDG 9: Industry, Innovation, and Infrastructure",
            "description": "Feedback control principles and root locus analysis."
        }
        res = courses_store.create_course(
            username="faculty_tano",
            course_code="EE 312",
            course_title="Feedback and Control Systems",
            from_catalog=True,
            catalog_course_data=catalog_sample,
            faculty_name="Engr. Elwin Jay J. Tano",
        )
        bp = res["blueprint"]
        meta = bp["metadata"]

        # Year level must be populated from catalog
        self.assertEqual(meta["year_level"], "Third Year")
        # Learning plan table must ONLY have Orientation row
        self.assertEqual(len(meta["learning_plan_table"]), 1)
        self.assertIn("Course Orientation", meta["learning_plan_table"][0]["topics"])
        # Policies table must be immediately present
        self.assertGreater(len(meta["policies_table"]), 0)
        # Prerequisites immediately populated
        self.assertEqual(len(meta["prereq_coreq_table"]), 1)
        self.assertEqual(meta["prereq_coreq_table"][0]["course_code"], "EE 211")
        # Clean up created course
        courses_store.delete_course("faculty_tano", res["id"])

    def test_workflow_steps_include_student_acknowledgment(self):
        step_keys = [s["key"] for s in syllabus_workflow.WORKFLOW_STEPS]
        self.assertIn("student_ack", step_keys)
        # Must be placed between qa_head and dean
        qa_idx = step_keys.index("qa_head")
        ack_idx = step_keys.index("student_ack")
        dean_idx = step_keys.index("dean")
        self.assertEqual(ack_idx, qa_idx + 1)
        self.assertEqual(dean_idx, ack_idx + 1)

    def test_workflow_qa_sign_transitions_to_student_acknowledgment(self):
        # Create a mock doc at QA step
        bp = get_blank_blueprint()
        doc = {
            "id": "test_wf_course",
            "owner": "faculty_tano",
            "blueprint": bp.to_dict(),
            "workflow": {
                "status": "for_qa_countersign",
                "cycle": 1,
                "content_hash": syllabus_workflow.compute_hash(bp.to_dict()),
                "signatures": [
                    {"step": "committee_members", "username": "faculty_mem"},
                    {"step": "committee_chair", "username": "faculty_chair"},
                    {"step": "program_head", "username": "faculty_ph"},
                ],
                "history": [],
            }
        }
        qa_user = {
            "username": "faculty_qa",
            "full_name": "Engr. College QA Head",
            "role": "faculty",
            "workflow_roles": ["qa_head"],
            "has_signature": True,
            "signature_data": "data:image/png;base64,mock",
        }
        wf = syllabus_workflow.sign(doc, qa_user, decision="approve", remarks="QA Checked")
        # After QA countersigns, next step is for_student_acknowledgment
        self.assertEqual(wf["status"], "for_student_acknowledgment")

        # Populate enrolled students and acknowledgments (>=80% threshold required by policy)
        doc["blueprint"]["students"] = [
            {"student_id": "2024-00101", "name": "Student A"},
            {"student_id": "2024-00102", "name": "Student B"},
        ]
        doc["student_acknowledgments"] = [
            {"student_id": "2024-00101", "student_name": "Student A"},
            {"student_id": "2024-00102", "student_name": "Student B"},
        ]

        # Now test forwarding from student_ack to Dean
        owner_user = {
            "username": "faculty_tano",
            "full_name": "Engr. Elwin Jay J. Tano",
            "role": "faculty",
            "has_signature": True,
            "signature_data": "data:image/png;base64,mock",
        }
        self.assertTrue(syllabus_workflow.user_can_act(owner_user, doc))
        wf2 = syllabus_workflow.sign(doc, owner_user, decision="approve", remarks="Students have signed")
        self.assertEqual(wf2["status"], "for_dean_approval")

        # Now Dean approves
        dean_user = {
            "username": "dean_cataytay",
            "full_name": "Dr. Joie D. Cataytay",
            "role": "dean",
            "workflow_roles": ["dean"],
            "has_signature": True,
            "signature_data": "data:image/png;base64,mock",
        }
        wf3 = syllabus_workflow.sign(doc, dean_user, decision="approve", remarks="Final approval")
        self.assertEqual(wf3["status"], "approved")

    def test_student_acknowledgment_button_removed_from_faculty_view(self):
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()
        # "Sign Student Acknowledgment" button should NOT be in the faculty template
        self.assertNotIn("Sign Student Acknowledgment", content)
        # Download button should be present
        self.assertIn("exportAcknowledgmentPdf()", content)
        self.assertIn("Download FM-USeP-MID-07 (.pdf)", content)


if __name__ == "__main__":
    unittest.main()
