import unittest
import os
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

        # Revert back to original accurate values
        users = auth._load_users()
        users["faculty_arenga"]["email"] = "delan.arenga@usep.edu.ph"
        users["faculty_arenga"]["workflow_roles"] = ["associate_dean", "review_committee"]
        users["faculty_arenga"]["position_title"] = "Associate Dean, College of Engineering"
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

    def test_admin_users_page_contains_delete_modal_and_controls(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin"] = True
            sess["role"] = "admin"

        res = self.client.get("/admin/users")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Verify delete modal exists with institutional reason options and course purge checkbox
        self.assertIn('id="deleteUserModal"', html)
        self.assertIn('id="deleteUserModalForm"', html)
        self.assertIn('name="reason"', html)
        self.assertIn('name="purge_courses"', html)
        self.assertIn('handleDeleteUserClick(this)', html)
        self.assertIn('closeDeleteUserModal()', html)
        self.assertIn('Permanently Delete Account', html)

    def test_delete_user_endpoint_removes_user_and_prevents_resurrection(self):
        csrf_tok = "valid-csrf-token-123"
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin"] = True
            sess["role"] = "admin"
            sess["_csrf"] = csrf_tok

        # 1. Create a temporary user
        test_uname = "temp_resigned_faculty"
        users = auth._load_users()
        users[test_uname] = {
            "username": test_uname,
            "full_name": "Test Resigned Faculty Member",
            "password": "hashed_pw",
            "role": "faculty",
            "workflow_roles": ["faculty"],
            "email": "resigned@usep.edu.ph",
            "position_title": "Former Faculty"
        }
        auth._save_users(users)

        # Create dummy course directory for test user
        course_dir = os.path.join(auth.DATA_DIR, "courses", test_uname)
        os.makedirs(course_dir, exist_ok=True)
        with open(os.path.join(course_dir, "test_course.json"), "w") as f:
            f.write("{}")
        self.assertTrue(os.path.exists(course_dir))

        try:
            # 2. Issue JSON DELETE POST with reasons and course purge
            res = self.client.post(f"/admin/users/{test_uname}/delete", json={
                "reason": "Faculty is no longer associated with the university (resigned / retired / transfer)",
                "purge_courses": True,
                "_csrf": csrf_tok
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertIn("permanently deleted", data.get("message", "").lower())

            # 3. Verify user removed from active users
            active_users = auth._load_users()
            self.assertNotIn(test_uname, active_users)

            # 4. Verify user added to deleted_users blacklist
            del_set = auth._load_deleted_users()
            self.assertIn(test_uname, del_set)

            # 5. Verify course folder purged
            self.assertFalse(os.path.exists(course_dir))

            # 6. Verify ensure_default_admin() does NOT resurrect deleted user
            auth.ensure_default_admin()
            active_users_after_seeding = auth._load_users()
            self.assertNotIn(test_uname, active_users_after_seeding)

        finally:
            # Cleanup test artifacts
            del_set = auth._load_deleted_users()
            if test_uname in del_set:
                del_set.remove(test_uname)
                auth._save_deleted_users(del_set)

    def test_delete_user_self_protection_and_last_admin_protection(self):
        csrf_tok = "valid-csrf-token-123"
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["is_admin"] = True
            sess["role"] = "admin"
            sess["_csrf"] = csrf_tok

        # Attempting to delete oneself
        res = self.client.post("/admin/users/admin/delete", json={
            "_csrf": csrf_tok
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])
        self.assertIn("currently signed in", res.get_json()["error"])

        # Attempting to delete a nonexistent account
        res_nonexistent = self.client.post("/admin/users/ghost_user_123/delete", json={
            "_csrf": csrf_tok
        })
        self.assertEqual(res_nonexistent.status_code, 404)
        self.assertFalse(res_nonexistent.get_json()["success"])

if __name__ == "__main__":
    unittest.main()
