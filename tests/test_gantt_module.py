# -*- coding: utf-8 -*-
"""
Integration and Unit Tests for Course Delivery Gantt Chart Module
================================================================
Verifies:
1. Stepper placement, sequential numbering (Step 3: Delivery Timeline), and unbroken 1-8 order.
2. Dean approval prerequisite lock gating on API endpoints and UI lock barriers.
3. Dynamic Lecture/Lab contact hour capacity calculation (1 hr/unit Lec, 3 hrs/unit Lab).
4. Philippine regular, special non-working, and Davao City holidays pre-loading.
5. Non-class dates manager (custom suspensions, faculty leaves) and hour deductions on meeting days.
6. Interactive topic completion tracking and dual-timeline pacing (on_track, ahead, behind, shifted).
"""

import unittest
import json
import re
from app import app
import courses_store
import gantt_workflow


class TestCourseDeliveryGanttModule(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_stepper_tab_placement_and_numbering(self):
        """Verifies Step 3: Delivery Timeline tab in ribbon stepper with sequential 1-8 order."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        m = re.search(r'<div class="ribbon-group-content ribbon-steps">(.*?)</div>\s*</div>', content, re.DOTALL)
        self.assertIsNotNone(m, "ribbon-steps container must exist")
        steps_html = m.group(1)

        # Check button order
        expected_ids = [
            "stepBtnTabSyllabus",
            "stepBtnTabAssessments",
            "stepBtnTabGantt",
            "stepBtnTabGradebook",
            "stepBtnTabReceiptAck",
            "stepBtnTabTos",
            "stepBtnTabCloreport",
            "stepBtnTabCqi"
        ]

        pos = -1
        for btn_id in expected_ids:
            btn_pos = steps_html.find(f'id="{btn_id}"')
            self.assertNotEqual(btn_pos, -1, f"Button {btn_id} not found in ribbon-steps")
            self.assertGreater(btn_pos, pos, f"Button {btn_id} must appear in order")
            pos = btn_pos

        # Check sequential badge numbers 1 to 8
        matches = re.findall(r'<button[^>]+id="([^"]+)"[^>]*>.*?<span class="step-num">([^<]+)</span>', steps_html, re.DOTALL)
        self.assertEqual(len(matches), 8)
        self.assertEqual(matches[2], ("stepBtnTabGantt", "3"))

        # Check click handler
        self.assertIn('onclick="switchSyllabusStep(\'tab-gantt\')"', steps_html)

    def test_gantt_tab_panel_and_lock_barrier_markup(self):
        """Verifies tab-gantt panel, lock barrier banner, content card, and modal."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        # tab-gantt panel
        self.assertIn('id="tab-gantt"', content)
        self.assertIn('id="classRecordLockBannerGantt"', content)
        self.assertIn('id="ganttTabContent"', content)
        self.assertIn('id="ganttMatrixTable"', content)
        self.assertIn('id="nonClassDateModal"', content)

        # Ensure tab-gantt is positioned immediately after tab-assessments
        idx_assess = content.find('id="tab-assessments"')
        idx_gantt = content.find('id="tab-gantt"')
        idx_gradebook = content.find('id="tab-gradebook"')
        self.assertGreater(idx_gantt, idx_assess, "tab-gantt must appear after tab-assessments")
        self.assertGreater(idx_gradebook, idx_gantt, "tab-gradebook must appear after tab-gantt")

    def test_dean_approval_prerequisite_lock_on_api(self):
        """Verifies Gantt API is strictly locked (403) until Course Syllabus receives Dean approval."""
        # Create an unapproved course
        unapproved_doc = {
            "id": "c_test_unapproved_gantt",
            "course_code": "EE 999",
            "section": "EE 4A",
            "workflow": {
                "status": "draft",
                "approved": False,
            },
            "blueprint": {
                "metadata": {
                    "course_code": "EE 999",
                    "course_title": "Test Gating Course",
                    "lecture_units": 3.0,
                    "lab_units": 0.0,
                    "schedule": "MWF 08:00 AM - 09:00 AM",
                    "learning_plan_table": [
                        {"topics": "Topic 1", "time_frame": "3 hours"}
                    ]
                }
            }
        }
        courses_store.save_course_doc(unapproved_doc)

        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        try:
            # 1. GET Gantt on unapproved syllabus -> 403 Forbidden
            res = self.client.get(f"/api/courses/{unapproved_doc['id']}/gantt")
            self.assertEqual(res.status_code, 403)
            data = res.get_json()
            self.assertTrue(data.get("is_locked"))
            self.assertTrue(data.get("requires_dean_approval"))
            self.assertIn("Sequential Gating Locked", data.get("error", ""))

            # 2. PUT Gantt on unapproved syllabus -> 403 Forbidden
            res_put = self.client.put(
                f"/api/courses/{unapproved_doc['id']}/gantt",
                data=json.dumps({"gantt": {}}),
                content_type="application/json"
            )
            self.assertEqual(res_put.status_code, 403)

            # 3. POST Sync Gantt on unapproved syllabus -> 403 Forbidden
            res_sync = self.client.post(f"/api/courses/{unapproved_doc['id']}/gantt/sync")
            self.assertEqual(res_sync.status_code, 403)

            # Now approve the syllabus
            unapproved_doc["workflow"]["status"] = "approved"
            unapproved_doc["workflow"]["approved"] = True
            courses_store.save_course_doc(unapproved_doc)

            # 4. GET Gantt on approved syllabus -> 200 OK
            res_ok = self.client.get(f"/api/courses/{unapproved_doc['id']}/gantt")
            self.assertEqual(res_ok.status_code, 200)
            ok_data = res_ok.get_json()
            self.assertTrue(ok_data.get("success"))
            self.assertIn("gantt", ok_data)
            self.assertEqual(len(ok_data["gantt"]["calendar_weeks"]), 18)

        finally:
            # Clean up test course
            try:
                courses_store.delete_course("faculty_tano", unapproved_doc["id"])
            except Exception:
                pass

    def test_contact_hours_lecture_and_lab_formula(self):
        """Verifies CHED / OBE formula: Lec Units * 1 + Lab Units * 3 = Total Hours/Week."""
        # 3.0 Lec, 0.0 Lab
        calc1 = gantt_workflow.calculate_weekly_contact_hours(3.0, 0.0)
        self.assertEqual(calc1["total_hours_per_week"], 3.0)

        # 0.0 Lec, 1.0 Lab (3 contact hours per lab unit)
        calc2 = gantt_workflow.calculate_weekly_contact_hours(0.0, 1.0)
        self.assertEqual(calc2["total_hours_per_week"], 3.0)

        # 3.0 Lec, 1.0 Lab (3 + 3 = 6 contact hours/week)
        calc3 = gantt_workflow.calculate_weekly_contact_hours(3.0, 1.0)
        self.assertEqual(calc3["total_hours_per_week"], 6.0)

        # 2.0 Lec, 1.0 Lab (2 + 3 = 5 contact hours/week)
        calc4 = gantt_workflow.calculate_weekly_contact_hours(2.0, 1.0)
        self.assertEqual(calc4["total_hours_per_week"], 5.0)

    def test_preloaded_holidays_and_davao_celebrations(self):
        """Verifies pre-population of National Philippine Holidays and Local Davao City celebrations."""
        holidays = gantt_workflow.get_philippine_holidays(2026)
        holiday_names = {h["name"]: h for h in holidays}

        # National Regular
        self.assertIn("New Year's Day", holiday_names)
        self.assertIn("Independence Day", holiday_names)
        self.assertIn("Labor Day", holiday_names)
        self.assertIn("National Heroes Day", holiday_names)
        self.assertIn("Bonifacio Day", holiday_names)
        self.assertIn("Christmas Day", holiday_names)
        self.assertIn("Rizal Day", holiday_names)

        # National Special
        self.assertIn("Ninoy Aquino Day", holiday_names)
        self.assertIn("All Saints' Day", holiday_names)
        self.assertIn("All Souls' Day", holiday_names)
        self.assertIn("Feast of the Immaculate Conception of Mary", holiday_names)
        self.assertIn("EDSA People Power Revolution Anniversary", holiday_names)

        # Davao City Celebrations
        self.assertIn("Araw ng Dabaw (Davao City Charter Day)", holiday_names)
        self.assertEqual(holiday_names["Araw ng Dabaw (Davao City Charter Day)"]["date"], "2026-03-01")
        self.assertEqual(holiday_names["Araw ng Dabaw (Davao City Charter Day)"]["category"], "davao_holiday")

        self.assertIn("Indigenous Peoples Day (Kadayawan Festival)", holiday_names)
        kadayawan = holiday_names["Indigenous Peoples Day (Kadayawan Festival)"]
        self.assertEqual(kadayawan["category"], "davao_holiday")
        self.assertEqual(kadayawan["date"], "2026-08-21")

    def test_non_class_dates_and_topic_variance_shifting(self):
        """Verifies that non-class disruptions deduct hours and topics track on_track/ahead/behind."""
        # Course starting on Monday Aug 17, 2026
        # Aug 21, 2026 (Friday) is Ninoy Aquino / Kadayawan Day
        holidays = gantt_workflow.get_philippine_holidays(2026)
        cal = gantt_workflow.build_18_week_calendar(
            start_date_str="2026-08-17",
            meeting_days=["Mon", "Wed", "Fri"],
            weekly_hours=3.0,
            all_non_class_dates=holidays,
        )

        w1 = cal[0]
        self.assertEqual(w1["week_number"], 1)
        self.assertTrue(w1["is_disrupted"])
        self.assertEqual(w1["hours_lost"], 1.0)
        self.assertEqual(w1["effective_hours"], 2.0)

        # Ideal allocation
        topics = [
            {"topic_id": "top_1", "planned_hours": 3.0},
            {"topic_id": "top_2", "planned_hours": 3.0},
        ]
        sched = gantt_workflow.calculate_ideal_topic_schedule(topics, weekly_capacity=3.0)
        self.assertEqual(sched[0]["ideal_start_week"], 1)
        self.assertEqual(sched[1]["ideal_start_week"], 2)

        # Topic 1 done on week 1 -> on track
        pacing1 = gantt_workflow.compute_topic_pacing_and_variance(
            {"ideal_start_week": 1, "ideal_end_week": 1, "status": "done", "actual_start_week": 1, "actual_end_week": 1},
            cal, {1: 1.0, 2: 1.0}
        )
        self.assertEqual(pacing1["variance_status"], "on_track")

        # Topic 2 delayed to week 3 -> behind
        pacing2 = gantt_workflow.compute_topic_pacing_and_variance(
            {"ideal_start_week": 2, "ideal_end_week": 2, "status": "done", "actual_start_week": 2, "actual_end_week": 3},
            cal, {1: 1.0, 2: 1.0}
        )
        self.assertEqual(pacing2["variance_status"], "behind")

        # Topic 2 completed in week 1 -> ahead
        pacing3 = gantt_workflow.compute_topic_pacing_and_variance(
            {"ideal_start_week": 2, "ideal_end_week": 2, "status": "done", "actual_start_week": 1, "actual_end_week": 1},
            cal, {1: 1.0, 2: 1.0}
        )
        self.assertEqual(pacing3["variance_status"], "ahead")


if __name__ == "__main__":
    unittest.main()
