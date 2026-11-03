import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import courses_store
import syllabus_workflow
import syllabus_pdf_generator


class MultiFacultyAuthorshipTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.lead_username = "faculty_tano"
        self.coauthor_username = "faculty_arenga"
        self.created_course_ids = []

    def tearDown(self):
        for cid, owner in self.created_course_ids:
            try:
                courses_store.delete_course(owner, cid)
            except Exception:
                pass

    def test_multi_faculty_authoring_and_submission_flow(self):
        # 1. Lead faculty initializes the syllabus
        with self.client.session_transaction() as sess:
            sess["username"] = self.lead_username

        res = self.client.post("/api/courses", json={
            "course_code": "EE 321",
            "course_title": "Electromagnetic Fields",
            "section": "EE 3A",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "programs": ["EE"],
        })
        self.assertEqual(res.status_code, 201)
        course_data = res.get_json()["course"]
        cid = course_data["id"]
        self.created_course_ids.append((cid, self.lead_username))

        # Check initial author is only the lead author
        doc = courses_store.find_course(cid)
        authors = courses_store.get_doc_authors(doc)
        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0]["username"], self.lead_username)

        # 2. Lead author includes a co-author (faculty_arenga)
        bp = doc["blueprint"]
        bp["metadata"]["course_code"] = "EE 321"
        bp["metadata"]["course_title"] = "Electromagnetic Fields"
        bp["metadata"]["course_description"] = "Study of static and time-varying electromagnetic fields."
        bp["course_outcomes"] = [
            {"id": "CLO1", "statement": "Analyze electrostatic and magnetostatic boundary conditions."}
        ]
        bp["metadata"]["syllabus_assessment_activities"] = [
            {"code": "FA1", "activity": "Seatwork", "weight_pct": 0, "type": "formative"},
            {"code": "SA1", "activity": "Problem Sets", "weight_pct": 50, "type": "summative"},
            {"code": "SA2", "activity": "Major Exam", "weight_pct": 50, "type": "summative"}
        ]
        multi_authors = [
            {"username": self.lead_username, "name": "Engr. Elwin Jay J. Tano", "role": "Lead Author"},
            {"username": self.coauthor_username, "name": "Engr. Delan Zoe H. Arenga", "role": "Co-Author"}
        ]
        bp["metadata"]["authors"] = multi_authors

        save_res = self.client.put(f"/api/courses/{cid}", json={
            "blueprint": bp,
            "authors": multi_authors
        })
        self.assertEqual(save_res.status_code, 200)

        # Verify authors persisted on disk
        doc = courses_store.find_course(cid)
        persisted_authors = courses_store.get_doc_authors(doc)
        self.assertEqual(len(persisted_authors), 2)
        author_unames = [a["username"] for a in persisted_authors]
        self.assertIn(self.lead_username, author_unames)
        self.assertIn(self.coauthor_username, author_unames)

        # 3. Co-author logs in and sees course in their course list
        with self.client.session_transaction() as sess:
            sess["username"] = self.coauthor_username

        list_res = self.client.get("/api/courses")
        self.assertEqual(list_res.status_code, 200)
        coauthor_courses = list_res.get_json()["courses"]
        coauthor_cids = [c["id"] for c in coauthor_courses]
        self.assertIn(cid, coauthor_cids)

        co_item = next(c for c in coauthor_courses if c["id"] == cid)
        self.assertFalse(co_item["is_owner"])
        self.assertTrue(co_item["is_coauthor"])
        self.assertTrue(co_item["is_multi_authored"])

        # 4. Co-author can edit syllabus content
        get_res = self.client.get(f"/api/courses/{cid}")
        self.assertEqual(get_res.status_code, 200)
        co_bp = get_res.get_json()["blueprint"]
        co_bp["metadata"]["workload_description"] = "54 hours of student effort including simulation drills."

        update_res = self.client.put(f"/api/courses/{cid}", json={"blueprint": co_bp})
        self.assertEqual(update_res.status_code, 200)

        # Ensure the file still belongs to lead author and was not duplicated
        reloaded = courses_store.find_course(cid)
        self.assertEqual(reloaded["owner"], self.lead_username)
        self.assertEqual(reloaded["blueprint"]["metadata"]["workload_description"], "54 hours of student effort including simulation drills.")

        # 5. First author submits: Status stays awaiting co-author submission
        with self.client.session_transaction() as sess:
            sess["username"] = self.lead_username

        submit_data = {
            "committee_members": [
                {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Chair"},
                {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Member"},
                {"username": "faculty_claro", "name": "Engr. Charito O. Claro", "role": "Review Committee Member"}
            ],
            "submission_notes": "Ready for multi-faculty team review."
        }
        res_sub1 = self.client.post(f"/api/courses/{cid}/workflow/submit", json=submit_data)
        self.assertEqual(res_sub1.status_code, 200)
        sub1_json = res_sub1.get_json()
        self.assertTrue(sub1_json["awaiting_coauthors"])
        wf1 = sub1_json["workflow"]
        self.assertEqual(wf1["status"], "draft")
        self.assertTrue(wf1["is_awaiting_coauthors"])
        self.assertEqual(len(wf1["submitted_authors"]), 1)
        self.assertEqual(len(wf1["pending_authors"]), 1)
        self.assertEqual(wf1["pending_authors"][0]["username"], self.coauthor_username)

        # Lead author can no longer click submit (already submitted)
        wf_res = self.client.get(f"/api/courses/{cid}/workflow")
        lead_wf = wf_res.get_json()
        self.assertFalse(lead_wf["can_submit"])
        self.assertTrue(lead_wf["user_has_submitted"])

        # 6. Co-author logs in and sees pending submission endorsement
        with self.client.session_transaction() as sess:
            sess["username"] = self.coauthor_username

        wf_res = self.client.get(f"/api/courses/{cid}/workflow")
        co_wf = wf_res.get_json()
        self.assertTrue(co_wf["can_submit"])
        self.assertFalse(co_wf["user_has_submitted"])

        # Co-author clicks submit individually
        res_sub2 = self.client.post(f"/api/courses/{cid}/workflow/submit", json={})
        self.assertEqual(res_sub2.status_code, 200)
        sub2_json = res_sub2.get_json()
        self.assertFalse(sub2_json["awaiting_coauthors"])
        wf2 = sub2_json["workflow"]
        self.assertEqual(wf2["status"], "for_committee_review")
        self.assertFalse(wf2["is_awaiting_coauthors"])
        self.assertEqual(len(wf2["submitted_authors"]), 2)
        self.assertEqual(len(wf2["pending_authors"]), 0)

        # 7. PDF export reflects both faculty authors in Prepared by
        pdf_res = self.client.get(f"/api/courses/{cid}/export-pdf")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertGreater(len(pdf_res.data), 10000)

    def test_multi_faculty_submission_withdrawal_flow(self):
        """If an author submits but withdraws before all submit, submission resets to clean draft."""
        with self.client.session_transaction() as sess:
            sess["username"] = self.lead_username

        res = self.client.post("/api/courses", json={
            "course_code": "EE 322",
            "course_title": "Power Systems",
            "section": "EE 3B",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "programs": ["EE"],
        })
        cid = res.get_json()["course"]["id"]
        self.created_course_ids.append((cid, self.lead_username))

        doc = courses_store.find_course(cid)
        bp = doc["blueprint"]
        bp["metadata"]["course_code"] = "EE 322"
        bp["metadata"]["course_description"] = "Power systems analysis."
        bp["course_outcomes"] = [{"id": "CLO1", "statement": "Analyze symmetrical components."}]
        bp["metadata"]["syllabus_assessment_activities"] = [
            {"code": "FA1", "activity": "Quiz", "weight_pct": 50, "type": "summative"}
        ]
        multi_authors = [
            {"username": self.lead_username, "name": "Engr. Elwin Jay J. Tano", "role": "Lead Author"},
            {"username": self.coauthor_username, "name": "Engr. Delan Zoe H. Arenga", "role": "Co-Author"}
        ]
        bp["metadata"]["authors"] = multi_authors
        self.client.put(f"/api/courses/{cid}", json={"blueprint": bp, "authors": multi_authors})

        # Lead author submits
        submit_data = {
            "committee_members": [
                {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Chair"},
                {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Member"},
                {"username": "faculty_claro", "name": "Engr. Charito O. Claro", "role": "Review Committee Member"}
            ],
            "submission_notes": "Ready for multi-faculty team review."
        }
        sub_res = self.client.post(f"/api/courses/{cid}/workflow/submit", json=submit_data)
        self.assertEqual(sub_res.status_code, 200)
        self.assertTrue(sub_res.get_json()["awaiting_coauthors"])

        # Lead author withdraws submission
        wd_res = self.client.post(f"/api/courses/{cid}/workflow/withdraw")
        self.assertEqual(wd_res.status_code, 200)
        wf_after = wd_res.get_json()["workflow"]
        self.assertEqual(wf_after["status"], "draft")
        self.assertFalse(wf_after.get("is_awaiting_coauthors", False))
        self.assertEqual(len(wf_after.get("author_submissions", {})), 0)


if __name__ == "__main__":
    unittest.main()
