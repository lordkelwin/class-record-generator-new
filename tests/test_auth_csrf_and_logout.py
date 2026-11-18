import re
import unittest
from unittest.mock import patch

import app
import auth


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
    return m.group(1) if m else ""


class TestAuthCsrfAndLogoutSwitch(unittest.TestCase):
    def setUp(self):
        app.app.config["TESTING"] = True
        app.app.config["WTF_CSRF_ENABLED"] = True
        self.client = app.app.test_client()

    def test_01_faculty_logout_then_login_with_fresh_csrf_and_no_store_headers(self):
        """After /logout -> /login?signed_out=1, form action targets /login and CSRF works cleanly without 400."""
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["_csrf"] = "initial-csrf-tok"

        # 1. Logout resets cookie & redirects to /login?signed_out=1
        out_res = self.client.post("/logout", follow_redirects=False)
        self.assertEqual(out_res.status_code, 302)
        self.assertIn("/login?signed_out=1", out_res.headers.get("Location", ""))
        self.assertIn("no-store", out_res.headers.get("Cache-Control", ""))

        # 2. Render /login?signed_out=1 -> generates fresh CSRF token and sets action="/login"
        get_login = self.client.get("/login?signed_out=1")
        self.assertEqual(get_login.status_code, 200)
        self.assertIn("no-store", get_login.headers.get("Cache-Control", ""))
        html = get_login.get_data(as_text=True)
        self.assertIn('action="/login"', html)
        csrf_tok = _extract_csrf(html)
        self.assertTrue(len(csrf_tok) >= 16)

        # 3. Even if browser somehow posts back to /login?signed_out=1 with that CSRF token, it MUST NOT return 400 Bad Request
        with patch("auth.check_password_hash", return_value=True), \
             patch("auth._save_users"):
            post_signed_out = self.client.post(
                "/login?signed_out=1",
                data={"_csrf": csrf_tok, "username": "faculty_tano", "password": "any"},
                follow_redirects=False,
            )
        self.assertEqual(post_signed_out.status_code, 302)
        self.assertNotIn("Invalid or missing security token", post_signed_out.get_data(as_text=True))

    def test_02_stale_csrf_submission_recovers_gracefully_without_400_crash_page(self):
        """Posting an expired/stale CSRF token on /login re-renders styled login form with fresh CSRF instead of bare 400."""
        self.client.get("/login")
        stale_res = self.client.post(
            "/login",
            data={"_csrf": "stale-expired-token", "username": "faculty_tano", "password": "wrong"},
            follow_redirects=False,
        )
        self.assertEqual(stale_res.status_code, 200)
        body = stale_res.get_data(as_text=True)
        self.assertNotIn("400 Bad Request", body)
        self.assertIn("security token expired", body.lower())
        fresh_tok = _extract_csrf(body)
        self.assertTrue(fresh_tok and fresh_tok != "stale-expired-token")

        # Submitting again with the refreshed token now proceeds cleanly
        with patch("auth.check_password_hash", return_value=True), \
             patch("auth._save_users"):
            ok_res = self.client.post(
                "/login",
                data={"_csrf": fresh_tok, "username": "faculty_tano", "password": "any"},
                follow_redirects=False,
            )
        self.assertEqual(ok_res.status_code, 302)

    def test_03_student_logout_then_login_with_signed_out_param(self):
        """After /student/logout -> /student/login?signed_out=1, fresh CSRF & login succeed without 400."""
        out_res = self.client.post("/student/logout", follow_redirects=False)
        self.assertEqual(out_res.status_code, 302)
        self.assertIn("/student/login?signed_out=1", out_res.headers.get("Location", ""))

        get_st = self.client.get("/student/login?signed_out=1")
        self.assertEqual(get_st.status_code, 200)
        self.assertIn("no-store", get_st.headers.get("Cache-Control", ""))
        csrf_tok = _extract_csrf(get_st.get_data(as_text=True))
        self.assertTrue(len(csrf_tok) >= 16)

        with patch("student_store.verify_student_login", return_value=(True, {"student_id": "2023-00011", "full_name": "Test Student"}, None)):
            post_st = self.client.post(
                "/student/login?signed_out=1",
                data={"_csrf": csrf_tok, "student_id": "2023-00011", "secret": "student123"},
                follow_redirects=False,
            )
        self.assertEqual(post_st.status_code, 302)
        self.assertIn("/student/dashboard", post_st.headers.get("Location", ""))


if __name__ == "__main__":
    unittest.main()
