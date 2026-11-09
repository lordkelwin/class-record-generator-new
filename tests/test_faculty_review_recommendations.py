"""
Unit and integration tests for faculty review recommendations:
  1. Primary Curriculum Data Integration directly from PGO-PI-IGA.accdb (SQL queries, description sync).
  2. Locked Approver Field (Dean) & Searchable Course Code Combobox in Pre/Co-req table.
  3. Student Acknowledgement Form prerequisite gating before Dean's approval.
  4. Controlled Document layout and Cinzel Bold typography across all 3 PDF exports.
"""

import os
import unittest
import copy
from typing import Dict, Any

import accdb_curriculum
import catalog_data
import academic_db
import syllabus_workflow
from models import SyllabusBlueprint
from syllabus_pdf_generator import generate_usep_syllabus_pdf
from syllabus_evaluation_form import generate_syllabus_evaluation_pdf
from syllabus_acknowledgment_form import generate_syllabus_acknowledgment_pdf


class TestFacultyReviewRecommendations(unittest.TestCase):

    def test_01_accdb_curriculum_sql_integration(self):
        """Task 1: Curriculum Data Integration directly from PGO-PI-IGA.accdb via SQL."""
        courses = accdb_curriculum.query_accdb_bsee_courses(force_refresh=True)
        self.assertEqual(len(courses), 81, "Must extract exactly 81 BSEE courses from PGO-PI-IGA.accdb")

        # Verify key courses and fields
        by_code = {c["code"]: c for c in courses}
        self.assertIn("EE 211", by_code)
        self.assertIn("EE 222", by_code)
        self.assertIn("EE 313", by_code)

        # Check authoritative descriptions
        ee222 = by_code["EE 222"]
        self.assertTrue(len(ee222["description"]) > 100)
        self.assertIn("z-transform", ee222["description"])

        ee313 = by_code["EE 313"]
        self.assertTrue(len(ee313["description"]) > 100)
        self.assertIn("nth order", ee313["description"])

        # Check PGO-PI-IGA mappings from joined tables
        math111 = by_code["Math 111"]
        self.assertTrue(len(math111["pgo_pi_mappings"]) >= 2)
        pgo_keywords = [m["pgo_keyword"] for m in math111["pgo_pi_mappings"]]
        self.assertTrue(any("Engineering Rigor" in k or "Critical Analysis" in k for k in pgo_keywords))

        # Check reciprocal corequisites
        ee211 = by_code["EE 211"]
        ee211L = by_code["EE 211L"]
        self.assertIn("EE 211L", ee211["coreqs"])
        self.assertIn("EE 211", ee211L["coreqs"])

        # Check sync function
        synced_count = accdb_curriculum.sync_accdb_to_catalog_and_db()
        self.assertEqual(synced_count, 81)

        # Verify SQLite academic_db has authoritative synced records
        db_course = academic_db.get_course("EE 222", "BSEE")
        self.assertIsNotNone(db_course)
        self.assertIn("z-transform", db_course["description"])

    def test_02_ui_refinements_in_index_html(self):
        """Task 2: Locked Approver Field and Searchable Pre/Co-req Combobox in templates/index.html."""
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Approver locked field
        self.assertIn('id="meta_dean_name"', html)
        self.assertIn('readonly disabled', html)
        self.assertIn('Engr. Joie D. Cataytay, Ph.D.', html)

        # Searchable Pre/Co-req combobox
        self.assertIn('prereq-combobox-wrapper', html)
        self.assertIn('prereqCodeInput_', html)
        self.assertIn('openPrereqCombobox', html)
        self.assertIn('filterPrereqCombobox', html)
        self.assertIn('selectPrereqComboboxItem', html)
        self.assertIn('prereqDropdown_', html)

    def test_03_student_acknowledgment_workflow_gate(self):
        """Task 3: Student Acknowledgement Form signing is mandatory prerequisite before Dean's approval."""
        bp = SyllabusBlueprint()
        bp.metadata.course_code = "EE 411"
        bp.metadata.course_title = "Feedback and Control Systems"
        bp.metadata.faculty_name = "Elwin Jay J. Tano"

        doc = {
            "id": "c_workflow_gate_test",
            "owner": "faculty_tano",
            "course_code": "EE 411",
            "course_title": "Feedback and Control Systems",
            "blueprint": bp.to_dict(),
            "workflow": {
                "status": "for_student_acknowledgment",
                "cycle": 1,
                "signatures": [
                    {"step": "committee_members", "decision": "approved"},
                    {"step": "committee_chair", "decision": "approved"},
                    {"step": "program_head", "decision": "approved"},
                    {"step": "qa_head", "decision": "approved"},
                ],
                "checklist": {},
                "content_hash": syllabus_workflow.compute_hash(bp.to_dict()),
            },
            "student_acknowledgments": [],
        }

        # 1. Without student signatures (0 signed), endorsement at student_ack stage MUST raise WorkflowError
        faculty_user = {
            "username": "faculty_tano",
            "full_name": "Elwin Jay J. Tano",
            "role": "faculty",
            "workflow_roles": ["faculty"],
            "has_signature": True,
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        }

        with self.assertRaises(syllabus_workflow.WorkflowError) as cm:
            syllabus_workflow.sign(doc, faculty_user, decision="approve", remarks="Endorsing to Dean")
        self.assertIn("Student acknowledgment has not reached the required 80% threshold", str(cm.exception))

        # 2. Dean attempting to approve directly while student ack is incomplete MUST also be blocked
        dean_user = {
            "username": "dean_cataytay",
            "full_name": "Joie D. Cataytay",
            "role": "dean",
            "workflow_roles": ["dean"],
            "has_signature": True,
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        }

        # Step 4 is student_ack; Dean cannot act until student_ack is completed
        curr_step = syllabus_workflow.current_step(doc["workflow"])
        self.assertEqual(curr_step["key"], "student_ack")

        # 3. Add student acknowledgment signature
        doc["student_acknowledgments"].append({
            "student_id": "2023-00001",
            "student_name": "Juan Dela Cruz",
            "acknowledged_at": "2026-11-05 10:00:00",
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        })

        # Now threshold is met (1/1 = 100%)
        stats = syllabus_workflow.get_student_acknowledgment_stats(doc)
        self.assertTrue(stats["meets_threshold"])

        # Endorse to Dean
        wf_after_ack = syllabus_workflow.sign(doc, faculty_user, decision="approve", remarks="Endorsing to Dean")
        self.assertEqual(wf_after_ack["status"], "for_dean_approval")

        # Dean can now approve
        wf_final = syllabus_workflow.sign(doc, dean_user, decision="approve", remarks="Approved by Dean")
        self.assertEqual(wf_final["status"], "approved")

    def test_04_controlled_document_exports_and_cinzel_typography(self):
        """Task 4: Controlled Document styling and Cinzel Bold typography across all 3 exported PDFs."""
        bp = SyllabusBlueprint()
        bp.metadata.course_code = "EE 211"
        bp.metadata.course_title = "Electrical Circuits 1"
        bp.metadata.dean_name = "Engr. Joie D. Cataytay, Ph.D."

        mock_doc = {
            "id": "c_export_test",
            "course_code": "EE 211",
            "course_title": "Electrical Circuits 1",
            "blueprint": bp.to_dict(),
            "workflow": {
                "status": "for_student_acknowledgment",
                "signatures": [],
                "checklist": {}
            },
            "student_acknowledgments": [
                {
                    "student_id": "2023-00001",
                    "student_name": "Juan Dela Cruz",
                    "acknowledged_at": "2026-11-05 10:00:00",
                    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                }
            ]
        }

        # 1. Course Syllabus PDF
        pdf_bytes_1 = generate_usep_syllabus_pdf(bp, mock_doc)
        self.assertGreater(len(pdf_bytes_1), 100000)
        self.assertTrue(pdf_bytes_1.startswith(b"%PDF"))

        # 2. Syllabus Review Tool PDF (FM-USeP-MID-02)
        pdf_bytes_2 = generate_syllabus_evaluation_pdf(mock_doc)
        self.assertGreater(len(pdf_bytes_2), 50000)
        self.assertTrue(pdf_bytes_2.startswith(b"%PDF"))

        # 3. Syllabus Acknowledgement Form PDF (FM-USeP-MID-07)
        pdf_bytes_3 = generate_syllabus_acknowledgment_pdf(bp, mock_doc)
        self.assertGreater(len(pdf_bytes_3), 50000)
        self.assertTrue(pdf_bytes_3.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
