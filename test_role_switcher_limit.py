# test_role_switcher_limit.py
import unittest
from werkzeug.security import generate_password_hash
from app import app
import auth

class TestRoleSwitcherLimitation(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        auth.ensure_default_admin()

    def test_01_non_admin_cannot_access_switch_api(self):
        # 1. Unauthenticated request blocked
        res = self.client.post("/api/switch-demo-account", json={"username": "faculty_tano"})
        self.assertIn(res.status_code, [401, 403])

        # 2. Regular faculty login blocked from switching accounts
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["is_admin_session"] = False
        res = self.client.post("/api/switch-demo-account", json={"username": "dean_cataytay"})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Admin access required", res.get_json()["error"])

        # 3. Staff login blocked from switching accounts
        with self.client.session_transaction() as sess:
            sess["username"] = "staff_office"
            sess["is_admin_session"] = False
        res = self.client.post("/api/switch-demo-account", json={"username": "admin"})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Admin access required", res.get_json()["error"])

    def test_02_non_admin_does_not_see_switcher_in_html(self):
        # Regular faculty rendering index
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["is_admin_session"] = False
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertNotIn("roleTestSwitcherBar", html)
        self.assertNotIn("Role Test Switcher", html)

        # Staff rendering index
        with self.client.session_transaction() as sess:
            sess["username"] = "staff_office"
            sess["is_admin_session"] = False
        res_staff = self.client.get("/")
        self.assertEqual(res_staff.status_code, 200)
        html_staff = res_staff.get_data(as_text=True)
        self.assertNotIn("roleTestSwitcherBar", html_staff)
        self.assertNotIn("Role Test Switcher", html_staff)

    def test_03_admin_sees_switcher_and_can_switch(self):
        # Admin rendering index
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin_session"] = True
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("roleTestSwitcherBar", html)
        self.assertIn("Role Test Switcher (Admin Only)", html)

        # Admin calls switch API
        res_switch = self.client.post("/api/switch-demo-account", json={"username": "faculty_tano"})
        self.assertEqual(res_switch.status_code, 200)
        data = res_switch.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["username"], "faculty_tano")

        # In switched session, admin session flag is preserved so switcher is still visible to the testing admin
        res_switched_view = self.client.get("/")
        html_switched = res_switched_view.get_data(as_text=True)
        self.assertIn("roleTestSwitcherBar", html_switched)

        # And admin can switch back to admin
        res_back = self.client.post("/api/switch-demo-account", json={"username": "admin"})
        self.assertEqual(res_back.status_code, 200)
        self.assertEqual(res_back.get_json()["user"]["username"], "admin")

    def test_04_logout_clears_admin_session(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin_session"] = True

        res_logout = self.client.get("/logout")
        self.assertEqual(res_logout.status_code, 302)

        # Session should be empty
        with self.client.session_transaction() as sess:
            self.assertNotIn("username", sess)
            self.assertNotIn("is_admin_session", sess)

if __name__ == "__main__":
    unittest.main()
