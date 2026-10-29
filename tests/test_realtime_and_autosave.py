import unittest
import json
from app import app
import courses_store

class TestRealtimeAndAutoSave(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_post_and_put_course_update(self):
        """Test /api/courses/<course_id> handles PUT and POST (sendBeacon) for real-time saving."""
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        # Create test course
        doc = courses_store.create_course(
            username="faculty_tano",
            course_code="EE 888",
            course_title="Real-Time Testing Systems",
            sections=["EE 4A"]
        )
        c_id = doc["id"]

        try:
            # 1. Test PUT update
            put_payload = {
                "course_code": "EE 888",
                "course_title": "Real-Time Testing Systems (Updated)",
                "section": "EE 4A",
                "sections": ["EE 4A"],
                "blueprint": doc["blueprint"]
            }
            put_payload["blueprint"]["metadata"]["room"] = "Lab 305"

            res_put = self.client.put(f"/api/courses/{c_id}", json=put_payload)
            self.assertEqual(res_put.status_code, 200)
            data_put = res_put.get_json()
            self.assertEqual(data_put["course"]["blueprint"]["metadata"]["room"], "Lab 305")

            # 2. Test POST update (used by navigator.sendBeacon)
            post_payload = dict(put_payload)
            post_payload["blueprint"]["metadata"]["room"] = "Room 401"
            res_post = self.client.post(f"/api/courses/{c_id}", json=post_payload)
            self.assertEqual(res_post.status_code, 200)
            data_post = res_post.get_json()
            self.assertEqual(data_post["course"]["blueprint"]["metadata"]["room"], "Room 401")

        finally:
            courses_store.delete_course("faculty_tano", c_id)

    def test_index_html_realtime_components(self):
        """Verify templates/index.html includes live auto-save and background sync engines."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        # Auto-save engine & status
        self.assertIn("function queueAutoSave", content)
        self.assertIn("computeCourseHash", content)
        self.assertIn("All changes saved", content)
        self.assertIn("asb-pulse", content)

        # Real-time background sync engine
        self.assertIn("function startRealtimeSyncEngine()", content)
        self.assertIn("async function runRealtimeSyncCycle()", content)
        self.assertIn("computeApprovalsSummaryHash", content)
        self.assertIn("badge-pulse", content)

        # Live Toast System
        self.assertIn("function showLiveToast", content)
        self.assertIn('id="liveToastContainer"', content)

        # Live Student Score Calculations
        self.assertIn("function liveCalculateStudentRow", content)
        self.assertIn("liveCalculateStudentRow(", content)

        # Global input auto-save listeners
        self.assertIn('document.addEventListener("input"', content)
        self.assertIn('document.addEventListener("change"', content)
        self.assertIn('window.addEventListener("beforeunload"', content)

    def test_background_polling_does_not_reset_filter(self):
        """Ensure loadApprovalRequests(false, true) does not override user filter."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        # Check that isBackground guard exists around filter setting
        self.assertIn("async function loadApprovalRequests(forceRefresh = false, isBackground = false)", content)
        self.assertIn("if (!isBackground)", content)

if __name__ == "__main__":
    unittest.main()
