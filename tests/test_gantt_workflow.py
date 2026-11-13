# -*- coding: utf-8 -*-
import unittest
import datetime
from gantt_workflow import (
    calculate_weekly_contact_hours,
    parse_course_credit_units,
    parse_schedule_meeting_days,
    get_philippine_holidays,
    get_kadayawan_indigenous_peoples_day,
    build_18_week_calendar,
    calculate_ideal_topic_schedule,
    compute_topic_pacing_and_variance,
    initialize_course_gantt,
    save_course_gantt,
    sync_gantt_from_syllabus,
)


class TestGanttWorkflow(unittest.TestCase):
    def test_weekly_contact_hours_calculation(self):
        # 1. 3.0 Lecture units, 0.0 Lab units => 3.0 hrs/week
        res = calculate_weekly_contact_hours(3.0, 0.0)
        self.assertEqual(res["lecture_hours_per_week"], 3.0)
        self.assertEqual(res["lab_hours_per_week"], 0.0)
        self.assertEqual(res["total_hours_per_week"], 3.0)

        # 2. 0.0 Lecture units, 1.0 Lab unit => 3.0 hrs/week
        res = calculate_weekly_contact_hours(0.0, 1.0)
        self.assertEqual(res["lecture_hours_per_week"], 0.0)
        self.assertEqual(res["lab_hours_per_week"], 3.0)
        self.assertEqual(res["total_hours_per_week"], 3.0)

        # 3. 3.0 Lecture units, 1.0 Lab unit => 6.0 hrs/week
        res = calculate_weekly_contact_hours(3.0, 1.0)
        self.assertEqual(res["lecture_hours_per_week"], 3.0)
        self.assertEqual(res["lab_hours_per_week"], 3.0)
        self.assertEqual(res["total_hours_per_week"], 6.0)

        # 4. 2.0 Lecture units, 1.0 Lab unit => 5.0 hrs/week
        res = calculate_weekly_contact_hours(2.0, 1.0)
        self.assertEqual(res["lecture_hours_per_week"], 2.0)
        self.assertEqual(res["lab_hours_per_week"], 3.0)
        self.assertEqual(res["total_hours_per_week"], 5.0)

    def test_parse_course_credit_units(self):
        # Explicit fields
        meta = {"lecture_units": 3.0, "lab_units": 1.0, "credit_units": "4.0 Units"}
        res = parse_course_credit_units(meta)
        self.assertEqual(res["total_hours_per_week"], 6.0)

        # String parsing fallback
        meta_str = {"credit_units": "4.0 Units (3.0 Lec, 1.0 Lab)"}
        res_str = parse_course_credit_units(meta_str)
        self.assertEqual(res_str["lecture_units"], 3.0)
        self.assertEqual(res_str["lab_units"], 1.0)
        self.assertEqual(res_str["total_hours_per_week"], 6.0)

    def test_parse_meeting_days(self):
        self.assertEqual(parse_schedule_meeting_days("MWF 08:00 AM - 09:00 AM"), ["Mon", "Wed", "Fri"])
        self.assertEqual(parse_schedule_meeting_days("TTh 10:30 AM - 12:00 PM"), ["Tue", "Thu"])
        self.assertEqual(parse_schedule_meeting_days("Sat 08:00 AM - 11:00 AM"), ["Sat"])
        self.assertEqual(parse_schedule_meeting_days("TF 01:00 PM - 02:30 PM"), ["Tue", "Fri"])

    def test_philippine_holidays_and_davao_city(self):
        holidays_2026 = get_philippine_holidays(2026)
        names = [h["name"] for h in holidays_2026]

        # Regular national holidays
        self.assertIn("New Year's Day", names)
        self.assertIn("Labor Day", names)
        self.assertIn("Independence Day", names)
        self.assertIn("Bonifacio Day", names)
        self.assertIn("Christmas Day", names)
        self.assertIn("Rizal Day", names)

        # Davao City holidays
        self.assertIn("Araw ng Dabaw (Davao City Charter Day)", names)
        self.assertIn("Indigenous Peoples Day (Kadayawan Festival)", names)

        # Check Kadayawan 3rd Friday of August 2026
        # August 2026: Aug 1 is Saturday. First Friday is Aug 7, 2nd is Aug 14, 3rd is Aug 21.
        kadayawan_2026 = get_kadayawan_indigenous_peoples_day(2026)
        self.assertEqual(kadayawan_2026.strftime("%Y-%m-%d"), "2026-08-21")
        self.assertEqual(kadayawan_2026.weekday(), 4)  # Friday

    def test_18_week_calendar_and_disruption_deduction(self):
        # Semester starting Aug 17, 2026 (Monday)
        # Aug 21, 2026 is Friday (Ninoy Aquino / Kadayawan)
        holidays = get_philippine_holidays(2026)
        calendar = build_18_week_calendar(
            start_date_str="2026-08-17",
            meeting_days=["Mon", "Wed", "Fri"],
            weekly_hours=3.0,
            all_non_class_dates=holidays,
        )

        self.assertEqual(len(calendar), 18)
        self.assertEqual(calendar[0]["week_number"], 1)
        self.assertEqual(calendar[0]["start_date"], "2026-08-17")

        # Week 1 has Friday Aug 21 disrupted
        w1 = calendar[0]
        self.assertTrue(w1["is_disrupted"])
        self.assertGreater(w1["hours_lost"], 0.0)
        # Each meeting is 1 hr in 3 hr/wk MWF
        self.assertEqual(w1["hours_lost"], 1.0)
        self.assertEqual(w1["effective_hours"], 2.0)

    def test_ideal_topic_schedule_allocation(self):
        topics = [
            {"topic_id": "t1", "planned_hours": 3.0},
            {"topic_id": "t2", "planned_hours": 6.0},
            {"topic_id": "t3", "planned_hours": 3.0},
        ]
        # With 3.0 hrs/week:
        # t1: 0..3 hrs -> Week 1
        # t2: 3..9 hrs -> Week 2 - 3
        # t3: 9..12 hrs -> Week 4
        scheduled = calculate_ideal_topic_schedule(topics, weekly_capacity=3.0)
        self.assertEqual(scheduled[0]["ideal_start_week"], 1)
        self.assertEqual(scheduled[0]["ideal_end_week"], 1)
        self.assertEqual(scheduled[1]["ideal_start_week"], 2)
        self.assertEqual(scheduled[1]["ideal_end_week"], 3)
        self.assertEqual(scheduled[2]["ideal_start_week"], 4)
        self.assertEqual(scheduled[2]["ideal_end_week"], 4)

    def test_pacing_and_variance_status(self):
        cal = [{"week_number": i, "hours_lost": 0.0} for i in range(1, 19)]
        cum = {i: 0.0 for i in range(1, 19)}

        # Done on time
        t_ontrack = {
            "ideal_start_week": 2, "ideal_end_week": 3,
            "status": "done", "actual_start_week": 2, "actual_end_week": 3
        }
        res1 = compute_topic_pacing_and_variance(t_ontrack, cal, cum)
        self.assertEqual(res1["variance_status"], "on_track")

        # Done ahead
        t_ahead = {
            "ideal_start_week": 2, "ideal_end_week": 3,
            "status": "done", "actual_start_week": 1, "actual_end_week": 2
        }
        res2 = compute_topic_pacing_and_variance(t_ahead, cal, cum)
        self.assertEqual(res2["variance_status"], "ahead")

        # Done behind
        t_behind = {
            "ideal_start_week": 2, "ideal_end_week": 3,
            "status": "done", "actual_start_week": 2, "actual_end_week": 4
        }
        res3 = compute_topic_pacing_and_variance(t_behind, cal, cum)
        self.assertEqual(res3["variance_status"], "behind")

    def test_full_course_gantt_lifecycle(self):
        doc = {
            "id": "test_course_1",
            "blueprint": {
                "metadata": {
                    "course_code": "EE 211",
                    "course_title": "Electrical Circuits 1",
                    "lecture_units": 3.0,
                    "lab_units": 0.0,
                    "schedule": "MWF 08:00 AM - 09:00 AM",
                    "semester_ay": "1st Semester, A.Y. 2026-2027",
                    "learning_plan_table": [
                        {"topics": "Orientation & Course Overview", "time_frame": "3 hours", "clo": "CLO1"},
                        {"topics": "Basic Circuit Concepts & Ohm's Law", "time_frame": "6 hours", "clo": "CLO1"},
                        {"topics": "Nodal & Mesh Analysis", "time_frame": "6 hours", "clo": "CLO2"},
                    ]
                }
            }
        }

        # Initialize
        state = initialize_course_gantt(doc)
        self.assertEqual(len(state["topics"]), 3)
        self.assertEqual(state["total_hours_per_week"], 3.0)
        self.assertEqual(len(state["calendar_weeks"]), 18)

        # Save updates
        state["topics"][0]["status"] = "done"
        state["topics"][0]["actual_start_week"] = 1
        state["topics"][0]["actual_end_week"] = 1

        # Add custom institutional suspension
        custom_ncd = {
            "id": "ncd_custom_intramurals",
            "date": "2026-09-18",
            "title": "University Intramurals 2026",
            "category": "institutional",
            "hours_affected": 1.0,
            "enabled": True,
        }
        state["non_class_dates"].append(custom_ncd)

        saved = save_course_gantt(doc, state)
        self.assertEqual(saved["topics"][0]["status"], "done")
        self.assertEqual(saved["topics"][0]["variance_status"], "on_track")

        # Sync from syllabus preserves done status
        synced = sync_gantt_from_syllabus(doc)
        self.assertEqual(synced["topics"][0]["status"], "done")
        self.assertEqual(synced["topics"][0]["actual_start_week"], 1)


if __name__ == "__main__":
    unittest.main()
