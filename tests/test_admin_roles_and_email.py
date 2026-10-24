import unittest
import json
import auth
import app

class TestAdminRolesAndEmail(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_admin_users_page_contains_modals_and_email_elements(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin"] = True
            sess["role"] = "admin"

        res = self.client.get("/admin/users")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # 1. Verify modalEmailInput exists in roleModalForm to prevent JS null TypeError
        self.assertIn('id="modalEmailInput"', html, "roleModalForm must include modalEmailInput")
        self.assertIn('name="position_title"', html)

        # 2. Verify dedicated email edit modal exists
        self.assertIn('id="emailModal"', html, "admin_users page must include emailModal")
        self.assertIn('id="quickEmailInput"', html, "emailModal must include quickEmailInput")
        self.assertIn('openEmailModal', html, "admin_users page must declare openEmailModal helper")

        # 3. Verify clean data-* attribute bindings for modal triggers (no inline quote breakage)
        self.assertIn('data-workflow-roles=', html, "Assign roles button must use data-workflow-roles attribute")
        self.assertIn('handleAssignRolesClick(this)', html, "Button must invoke handleAssignRolesClick")
        self.assertIn('handleEditEmailClick(this)', html, "Button must invoke handleEditEmailClick")
        self.assertIn('Edit Email', html, "Existing accounts table must have Edit Email buttons")
        self.assertIn('Assign Roles', html, "Existing accounts table must have Assign Roles buttons")

    def test_update_user_email_endpoint_form_and_json(self):
        csrf_tok = "valid-csrf-token-123"
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin"] = True
            sess["role"] = "admin"
            sess["_csrf"] = csrf_tok

        # Form POST update
        test_email = "nikka.basan.updated@usep.edu.ph"
        res = self.client.post("/admin/users/faculty_basan/email", data={
            "email": test_email,
            "_csrf": csrf_tok
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify email updated in auth users store
        users = auth._load_users()
        self.assertEqual(users["faculty_basan"].get("email"), test_email)

        # JSON POST update
        json_email = "nikka.basan.json@usep.edu.ph"
        res_json = self.client.post("/admin/users/faculty_basan/email", json={
            "email": json_email,
            "_csrf": csrf_tok
        })
        self.assertEqual(res_json.status_code, 200)
        self.assertTrue(res_json.get_json()["success"])

        # Revert back to original clean email
        users = auth._load_users()
        users["faculty_basan"]["email"] = "nikka.basan@usep.edu.ph"
        auth._save_users(users)

    def test_update_user_role_preserves_and_updates_email(self):
        csrf_tok = "valid-csrf-token-123"
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin"] = True
            sess["role"] = "admin"
            sess["_csrf"] = csrf_tok

        new_email = "delan.arenga.official@usep.edu.ph"
        res = self.client.post("/admin/users/faculty_arenga/role", data={
            "roles": ["review_committee", "program_head"],
            "program_codes": ["ECE"],
            "position_title": "Program Head - Electronics Engineering",
            "email": new_email,
            "_csrf": csrf_tok
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        users = auth._load_users()
        self.assertEqual(users["faculty_arenga"].get("email"), new_email)
        self.assertIn("program_head", users["faculty_arenga"].get("workflow_roles", []))
        self.assertEqual(users["faculty_arenga"].get("position_title"), "Program Head - Electronics Engineering")

        # Revert back
        users["faculty_arenga"]["email"] = "delan.arenga@usep.edu.ph"
        users["faculty_arenga"]["workflow_roles"] = ["review_committee"]
        users["faculty_arenga"]["position_title"] = "Faculty Member"
        auth._save_users(users)

    def test_update_nonexistent_user_handles_gracefully(self):
        csrf_tok = "valid-csrf-token-123"
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin"] = True
            sess["role"] = "admin"
            sess["_csrf"] = csrf_tok

        res = self.client.post("/admin/users/nonexistent_person/email", data={
            "email": "ghost@usep.edu.ph",
            "_csrf": csrf_tok
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("not found", res.data.decode("utf-8").lower())

if __name__ == "__main__":
    unittest.main()
