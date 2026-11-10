import unittest
from app import app
import auth


class TestActiveSubjectBarVisibility(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_subject_bar_visible_on_syllabus_tab(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/?tab=syllabus")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('id="activeSubjectBar"', html)
        # Should NOT have style="display:none;" when tab=syllabus
        self.assertNotIn('id="activeSubjectBar" style="display:none;"', html)
        self.assertNotIn('active-subject-bar hidden', html)

    def test_subject_bar_hidden_on_approvals_tab(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/?tab=approvals")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('id="activeSubjectBar"', html)
        # MUST have hidden and style="display:none;" when tab=approvals
        self.assertIn('id="activeSubjectBar" style="display:none;"', html)
        self.assertIn("active-subject-bar hidden", html)

    def test_subject_bar_hidden_on_curriculum_tab(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/?tab=curriculum")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('id="activeSubjectBar"', html)
        # MUST have hidden and style="display:none;" when tab=curriculum
        self.assertIn('id="activeSubjectBar" style="display:none;"', html)
        self.assertIn("active-subject-bar hidden", html)

    def test_subject_bar_omitted_for_pure_staff_users(self):
        # A pure staff user who cannot access faculty tools
        with self.client.session_transaction() as sess:
            sess["username"] = "staff_ababon"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Faculty tools are disabled, activeSubjectBar should not even exist in DOM
        self.assertNotIn('id="activeSubjectBar"', html)

    def test_javascript_contains_sync_visibility_logic(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn("syncActiveSubjectBarVisibility", html)
        self.assertIn("ribbon-dashboard", html)
        self.assertIn("ribbon-syllabus", html)
        self.assertIn(".active-subject-bar.hidden", html)


if __name__ == "__main__":
    unittest.main()
