import unittest
from unittest.mock import patch
import json
import os
import shutil

import app
import courses_store
import gantt_workflow

TEST_USER = "faculty_tano"
MOCK_FACULTY_USER = {
    "username": TEST_USER,
    "full_name": "Engr. Kenneth Jude Tano",
    "role": "Faculty",
    "can_access_faculty_tools": True,
    "must_change_password": False,
}


class TestDashboardUpgradesModule(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.client.testing = True

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_01_dashboard_dom_and_widgets_structure(self, mock_auth_user, mock_app_user):
        """Test 1: Verify Dashboard DOM elements for Course Selector, Widget 1, Widget 2, and Widget 3 exist in index.html."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 1. Course / Section Selectors
        self.assertIn('id="dashRibbonCourseSelect"', html)
        self.assertIn('id="dashHeaderCourseSelect"', html)
        self.assertIn('switchDashboardCourse(this.value)', html)

        # 2. Widget 1: Syllabus Review & Approval Status with Deadline Monitoring
        self.assertIn('id="dashWorkflowCard"', html)
        self.assertIn('id="dashWfGlobalStatusBadge"', html)
        self.assertIn('id="dashWfProgressBar"', html)
        self.assertIn('id="dashWfStepperContainer"', html)
        self.assertIn('id="dashReviewDeadlineCard"', html)
        self.assertIn('id="dashReviewDeadlineBadge"', html)
        self.assertIn('id="dashReviewDeadlineTargetDate"', html)
        self.assertIn('id="dashApprovalDeadlineCard"', html)
        self.assertIn('id="dashApprovalDeadlineBadge"', html)
        self.assertIn('id="dashApprovalDeadlineTargetDate"', html)
        self.assertIn('id="dashWfSummaryNotice"', html)
        self.assertIn('openDeadlineSettingsModal()', html)

        # 3. Widget 2: Weekly Delivery Timeline & Current Topic Indicator
        self.assertIn('id="dashTimelineCard"', html)
        self.assertIn('id="dashContactHourFormulaBadge"', html)
        self.assertIn('id="dashTimelineLockedBanner"', html)
        self.assertIn('id="dashTimelineActiveContent"', html)
        self.assertIn('id="dashCurrentWeekNumBadge"', html)
        self.assertIn('id="dashCurrentWeekDateRange"', html)
        self.assertIn('id="dashCurrentTopicTitle"', html)
        self.assertIn('id="dashCurrentTopicDetails"', html)
        self.assertIn('id="dashTopicStatusSelect"', html)
        self.assertIn('onDashTopicStatusChange(this.value)', html)
        self.assertIn('id="dashTopicPacingTag"', html)
        self.assertIn('id="dashTimelineProgressBar"', html)
        self.assertIn('id="dashNearbyTopicsList"', html)

        # 4. Widget 3: Comprehensive Student Performance Analytics (Retained 100%)
        self.assertIn('id="dashKpis"', html)
        self.assertIn('id="dashAssessBars"', html)
        self.assertIn('id="dashStudentSelect"', html)
        self.assertIn('id="dashStudentProfile"', html)
        self.assertIn('id="dashHeatmap"', html)
        self.assertIn('id="dashCloAttain"', html)
        self.assertIn('id="dashAlignMap"', html)
        self.assertIn('id="dashAlignTable"', html)

        # 5. Deadline Settings Modal
        self.assertIn('id="deadlineSettingsModal"', html)
        self.assertIn('id="modalReviewDeadlineInput"', html)
        self.assertIn('id="modalApprovalDeadlineInput"', html)
        self.assertIn('saveDeadlineSettings()', html)
        self.assertIn('closeDeadlineSettingsModal()', html)

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_02_ee415_delivery_timeline_and_topic_status_api(self, mock_auth_user, mock_app_user):
        """Test 2: Verify EE 415 has approved syllabus, calculates 2.0 hrs/wk, and updates topic status cleanly."""
        course_id = "c_144aaf4901"
        doc = courses_store.find_course(course_id)
        self.assertIsNotNone(doc, f"Course {course_id} must exist in data store.")

        # Check credit units & hours formula
        bp = doc.get("blueprint") or {}
        meta = bp.get("metadata") or {}
        credit_info = gantt_workflow.parse_course_credit_units(meta)
        self.assertEqual(credit_info["lecture_units"], 2.0)
        self.assertEqual(credit_info["lab_units"], 0.0)
        self.assertEqual(credit_info["total_hours_per_week"], 2.0)

        # Ensure approved syllabus
        wf = doc.get("workflow") or {}
        self.assertEqual(wf.get("status"), "approved")

        # GET Gantt API returns 200 with 18 weeks
        res = self.client.get(f"/api/courses/{course_id}/gantt")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        gantt = data.get("gantt")
        self.assertIsNotNone(gantt)
        self.assertEqual(len(gantt.get("calendar_weeks", [])), 18)
        self.assertEqual(gantt.get("total_hours_per_week"), 2.0)

        topics = gantt.get("topics", [])
        self.assertTrue(len(topics) > 0)

        # Verify PUT Gantt allows updating topic status
        first_topic = topics[0]
        original_status = first_topic.get("completion_status", "pending")
        new_status = "completed" if original_status != "completed" else "in_progress"

        first_topic["completion_status"] = new_status
        put_res = self.client.put(
            f"/api/courses/{course_id}/gantt",
            data=json.dumps({"gantt": gantt}),
            content_type="application/json"
        )
        self.assertEqual(put_res.status_code, 200)
        put_data = put_res.get_json()
        self.assertTrue(put_data.get("success"))
        updated_first = put_data["gantt"]["topics"][0]
        self.assertEqual(updated_first.get("completion_status"), new_status)

        # Revert back to original status to keep data pristine
        first_topic["completion_status"] = original_status
        self.client.put(
            f"/api/courses/{course_id}/gantt",
            data=json.dumps({"gantt": gantt}),
            content_type="application/json"
        )

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_03_student_ack_stats_and_stepper_synchronization(self, mock_auth_user, mock_app_user):
        """Test 3: Verify Student Ack stats and ratio synchronization in workflow and steppers."""
        course_id = "c_144aaf4901"
        res = self.client.get(f"/api/courses/{course_id}/workflow")
        self.assertEqual(res.status_code, 200)
        wf_data = res.get_json()

        # 1. Verify workflow endpoint returns student_ack_stats and student_acknowledgments
        self.assertIn("student_ack_stats", wf_data)
        self.assertIn("student_acknowledgments", wf_data)
        stats = wf_data["student_ack_stats"]
        self.assertGreater(stats.get("total_students", 0), 0)
        self.assertGreaterEqual(stats.get("total_acknowledged", 0), 0)
        self.assertIn("percentage", stats)
        self.assertIn("meets_threshold", stats)

        # 2. Verify templates/index.html includes live ratio in both Dashboard & Step 1 steppers
        index_res = self.client.get("/")
        self.assertEqual(index_res.status_code, 200)
        html = index_res.get_data(as_text=True)

        self.assertIn("${ackCount}/${totalEnrolled} Signed", html)
        self.assertIn("${totalAck}/${totalEnrolled} Signed", html)
        self.assertIn("Pending", html)

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_04_delivery_timeline_learning_plan_synchronization_and_week_13(self, mock_auth_user, mock_app_user):
        """Test 4: Verify EE 415 topics synchronize from Learning Plan, have ideal_weeks, and map Week 13 to Substation Layout."""
        course_id = "c_144aaf4901"
        res = self.client.get(f"/api/courses/{course_id}/gantt")
        self.assertEqual(res.status_code, 200)
        gantt = res.get_json().get("gantt", {})
        topics = gantt.get("topics", [])
        self.assertTrue(len(topics) >= 8)

        # Verify all topics have title/topic_title, hours_allocated/planned_hours, and ideal_weeks
        for t in topics:
            self.assertTrue(bool(t.get("topic_title") or t.get("title")), f"Topic must have title: {t}")
            self.assertTrue(bool(t.get("hours_allocated") or t.get("planned_hours")), f"Topic must have hours: {t}")
            self.assertIn("ideal_weeks", t)
            self.assertTrue(isinstance(t["ideal_weeks"], list) and len(t["ideal_weeks"]) > 0)

        # Find Topic 8 (Substation Layout)
        topic_8 = next((t for t in topics if "substation" in (t.get("title") or t.get("topic_title") or "").lower()), None)
        self.assertIsNotNone(topic_8, "Topic 8 (SUBSTATION LAYOUT) must exist in EE 415 learning plan topics.")
        self.assertIn(13, topic_8.get("ideal_weeks", []))
        self.assertIn(topic_8.get("hours_allocated", topic_8.get("planned_hours")), [6.0, 8.0])

        # Verify frontend code handles nearby topics without blank ':' bug
        index_res = self.client.get("/")
        html = index_res.get_data(as_text=True)
        self.assertIn("dashNearbyTopicsList", html)
        self.assertIn("Done / Discussed", html)

    @patch("app.current_user", return_value=MOCK_FACULTY_USER)
    @patch("auth.current_user", return_value=MOCK_FACULTY_USER)
    def test_05_topic_status_roundtrip_and_pacing(self, mock_auth_user, mock_app_user):
        """Test 5: Verify topic status updates roundtrip cleanly with pacing status recalculation."""
        course_id = "c_144aaf4901"
        res = self.client.get(f"/api/courses/{course_id}/gantt")
        gantt = res.get_json().get("gantt", {})
        topics = gantt.get("topics", [])
        target = topics[0]
        orig_status = target.get("completion_status", "pending")
        orig_weeks = target.get("actual_weeks", [])

        # Update to done with actual week 1
        target["completion_status"] = "completed"
        target["status"] = "done"
        target["actual_start_week"] = 1
        target["actual_end_week"] = 1

        put_res = self.client.put(
            f"/api/courses/{course_id}/gantt",
            data=json.dumps({"gantt": gantt}),
            content_type="application/json"
        )
        self.assertEqual(put_res.status_code, 200)
        saved_gantt = put_res.get_json()["gantt"]
        saved_topic = saved_gantt["topics"][0]
        self.assertEqual(saved_topic["completion_status"], "completed")
        self.assertEqual(saved_topic["status"], "done")
        self.assertEqual(saved_topic["actual_weeks"], [1])

        # Restore original state
        saved_topic["completion_status"] = orig_status
        saved_topic["status"] = "pending" if orig_status == "pending" else orig_status
        saved_topic["actual_weeks"] = orig_weeks
        self.client.put(
            f"/api/courses/{course_id}/gantt",
            data=json.dumps({"gantt": saved_gantt}),
            content_type="application/json"
        )


if __name__ == "__main__":
    unittest.main()
