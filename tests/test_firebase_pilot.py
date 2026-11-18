import json
import os
import unittest
from unittest.mock import patch

import accdb_curriculum
import app
import auth
import config
import courses_store
import db_persistence
import firebase_persistence


class _FakeSnap:
    def __init__(self, doc_id, data, ref=None):
        self.id = doc_id
        self._data = data
        self.reference = ref

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return json.loads(json.dumps(self._data)) if self._data is not None else None


class _FakeDocRef:
    def __init__(self, store_dict, doc_id):
        self._store = store_dict
        self.id = doc_id

    def get(self):
        return _FakeSnap(self.id, self._store.get(self.id), ref=self)

    def set(self, data):
        self._store[self.id] = json.loads(json.dumps(data))

    def delete(self):
        self._store.pop(self.id, None)


class _FakeQuery:
    def __init__(self, store_dict, field, op, value):
        self._store = store_dict
        self._field = field
        self._op = op
        self._value = value

    def stream(self):
        out = []
        for did, data in list(self._store.items()):
            if self._op == "==" and data.get(self._field) == self._value:
                out.append(_FakeSnap(did, data, ref=_FakeDocRef(self._store, did)))
        return out


class _FakeCollection:
    def __init__(self, store_dict):
        self._store = store_dict

    def document(self, doc_id):
        return _FakeDocRef(self._store, doc_id)

    def stream(self):
        return [_FakeSnap(k, v, ref=_FakeDocRef(self._store, k)) for k, v in list(self._store.items())]

    def where(self, field, op, value):
        return _FakeQuery(self._store, field, op, value)


class _FakeBatch:
    def __init__(self):
        self._ops = []

    def set(self, doc_ref, data):
        self._ops.append((doc_ref, data))

    def commit(self):
        for ref, data in self._ops:
            ref.set(data)
        self._ops.clear()


class _FakeFirestoreClient:
    def __init__(self):
        self._collections = {}

    def collection(self, name):
        col = self._collections.setdefault(name, {})
        return _FakeCollection(col)

    def batch(self):
        return _FakeBatch()


class TestFirebasePilotDeployment(unittest.TestCase):
    def setUp(self):
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.orig_use_fb = config.USE_FIREBASE
        self.fake_fs = _FakeFirestoreClient()

    def tearDown(self):
        config.USE_FIREBASE = self.orig_use_fb
        firebase_persistence.set_firestore_client_for_tests(None)

    def test_01_firebase_and_container_configs_present_and_valid(self):
        """Verify firebase.json, .firebaserc, firestore.rules, firestore.indexes.json, Dockerfile, .dockerignore."""
        with open(os.path.join(self.root, "firebase.json"), encoding="utf-8") as f:
            fb = json.load(f)
        self.assertEqual(fb["hosting"]["public"], "public_hosting")
        rewrites = fb["hosting"]["rewrites"]
        self.assertEqual(rewrites[0]["source"], "**")
        self.assertEqual(rewrites[0]["run"]["serviceId"], "usep-obe-studio")
        self.assertEqual(fb["firestore"]["rules"], "firestore.rules")
        self.assertEqual(fb["firestore"]["indexes"], "firestore.indexes.json")

        with open(os.path.join(self.root, ".firebaserc"), encoding="utf-8") as f:
            rc = json.load(f)
        self.assertIn("default", rc["projects"])

        with open(os.path.join(self.root, "firestore.rules"), encoding="utf-8") as f:
            rules = f.read()
        self.assertIn("rules_version = '2';", rules)
        self.assertIn("allow read, write: if false;", rules)
        for col in ("app_users", "app_students", "courses", "survey_responses", "cqi_plans", "curriculum_master"):
            self.assertIn(col, rules)

        with open(os.path.join(self.root, "Dockerfile"), encoding="utf-8") as f:
            df = f.read()
        self.assertIn("USE_FIREBASE=true", df)
        self.assertIn("PORT=8080", df)
        self.assertIn("/api/health", df)
        self.assertIn("gunicorn", df)

        with open(os.path.join(self.root, ".dockerignore"), encoding="utf-8") as f:
            di = f.read()
        self.assertIn("data/courses/", di)
        self.assertIn("data/secret_key", di)

    def test_02_cloud_firestore_dual_backend_and_accdb_bundle_no_odbc(self):
        """Verify USE_FIREBASE=true routes Users, Students, Courses, Surveys, CQI Plans, and ACCDB to Firestore without SQLite/ODBC."""
        config.USE_FIREBASE = True
        firebase_persistence.set_firestore_client_for_tests(self.fake_fs)

        # 1. Users in Firestore
        db_persistence.save_user_to_db({
            "username": "pilot_fac1",
            "full_name": "Pilot Faculty One",
            "role": "faculty",
            "workflow_roles": ["faculty"],
            "program_codes": ["EE"],
            "can_access_faculty_tools": True,
        })
        users = db_persistence.load_users_from_db()
        self.assertIn("pilot_fac1", users)

        # 2. Students in Firestore
        db_persistence.save_students_dict_to_db({
            "2099-77701": {
                "student_id": "2099-77701",
                "full_name": "Pilot, Student",
                "first_name": "Student",
                "last_name": "Pilot",
                "program_year": "BSEE 3A",
                "enrolled_courses": ["pilot_tmp_ee311"],
            }
        }, purge_missing=False)
        sts = db_persistence.load_students_from_db()
        self.assertIn("2099-77701", sts)

        # 3. Course persistence & listing via Firestore
        pilot_doc = {
            "id": "pilot_tmp_ee311",
            "owner": "pilot_fac1",
            "course_code": "EE 311",
            "course_title": "Pilot Electrical Circuits",
            "section": "BSEE 3A",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "workflow": {"status": "submitted", "submitted_at": "2026-11-18T12:00:00"},
            "class_record_workflow": {"status": "draft"},
            "blueprint": {
                "metadata": {"course_code": "EE 311", "course_title": "Pilot Electrical Circuits", "section": "BSEE 3A"},
                "course_outcomes": [{"co_id": "CO1", "description": "Solve AC circuits"}],
                "categories": [],
                "students": [],
            },
        }
        db_persistence.save_course_to_db(pilot_doc)
        loaded_c = db_persistence.load_course_from_db("pilot_tmp_ee311")
        self.assertIsNotNone(loaded_c)
        self.assertEqual(loaded_c["course_code"], "EE 311")

        # courses_store workflow listing sees Firestore course cleanly without local disk files
        wf_list = courses_store.list_all_workflow_courses()
        self.assertTrue(any(w["id"] == "pilot_tmp_ee311" for w in wf_list))

        # 4. Exit Survey & CQI Plan in Firestore
        db_persistence.save_survey_response_db(
            student_id="2099-77701",
            subject_id="pilot_tmp_ee311",
            course_code="EE 311",
            clo_ratings={"CO1": 4},
            general_ratings={"syllabus_clarity": 5, "teaching_delivery": 4, "assessment_fairness": 4, "feedback_consultation": 5},
            cqi_anchors={"instructional_delivery_pacing": 4},
            challenging_topics="Phasor diagrams in polyphase circuits",
        )
        agg = db_persistence.get_course_survey_aggregates_db("pilot_tmp_ee311", [{"co_id": "CO1", "description": "Solve AC circuits"}])
        self.assertEqual(agg["total_responses"], 1)
        self.assertEqual(agg["cqi_anchors_summary"]["instructional_delivery_pacing"]["avg_rating"], 4.0)

        db_persistence.save_cqi_plan_db({
            "course_id": "pilot_tmp_ee311",
            "course_code": "EE 311",
            "faculty_username": "pilot_fac1",
            "semester_ay": "1st Semester, A.Y. 2026-2027",
            "status": "submitted",
            "submitted_at": "2026-11-18T12:05:00",
            "revisit_date": "2027-11-18",
            "revisit_term": "1st Semester, A.Y. 2027-2028",
        })
        plans = db_persistence.list_cqi_plans_db(include_drafts=False)
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["course_code"], "EE 311")

        # 5. Portable ACCDB bundle works cleanly in Firestore mode without pyodbc
        bundle_path = os.path.join(self.root, "data", "accdb_curriculum_bundle.json")
        self.assertTrue(os.path.exists(bundle_path))
        accdb_curriculum._CACHED_CLOUD_BUNDLE = None
        accdb_curriculum._CACHED_BSEE_COURSES = None
        accdb_curriculum._CACHED_PGO_PI_TREE = None
        tree = accdb_curriculum.get_accdb_pgo_pi_tree(force_refresh=True)
        courses = accdb_curriculum.query_accdb_bsee_courses(force_refresh=True)
        self.assertGreaterEqual(len(tree), 10)
        self.assertGreaterEqual(len(courses), 50)

        # Clean up test docs from Firestore & verify
        self.assertTrue(db_persistence.delete_course_from_db("pilot_tmp_ee311"))
        self.assertIsNone(db_persistence.load_course_from_db("pilot_tmp_ee311"))
        self.assertTrue(db_persistence.delete_user_from_db("pilot_fac1"))
        self.assertTrue(db_persistence.delete_student_from_db("2099-77701"))

    def test_03_healthz_proxyfix_and_cloud_secret_key(self):
        """Verify /healthz public endpoint, ProxyFix middleware, and env SECRET_KEY precedence."""
        from werkzeug.middleware.proxy_fix import ProxyFix

        self.assertIsInstance(app.app.wsgi_app, ProxyFix)
        c = app.app.test_client()
        res = c.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

        with patch.dict("os.environ", {"SECRET_KEY": "pilot-persistent-cloud-run-secret-key"}, clear=False):
            key = auth.get_or_create_secret_key()
            self.assertEqual(key, b"pilot-persistent-cloud-run-secret-key")

    def test_04_firebase_session_cookie_name_cache_headers_and_csrf_login_flow(self):
        """Verify __session cookie name, Cache-Control: private + Vary: Cookie headers, and first-submit login."""
        import re

        self.assertEqual(app.app.config.get("SESSION_COOKIE_NAME"), "__session")
        self.assertEqual(app.app.config.get("REMEMBER_COOKIE_NAME"), "__session_remember")

        c = app.app.test_client()
        get_login = c.get("/login")
        self.assertEqual(get_login.status_code, 200)
        cc = get_login.headers.get("Cache-Control", "")
        self.assertIn("private", cc)
        self.assertIn("no-store", cc)
        self.assertIn("no-cache", cc)
        self.assertIn("Cookie", get_login.headers.get("Vary", ""))

        # Extract Set-Cookie name and verify it is __session (required by Firebase Hosting CDN)
        set_cookies = get_login.headers.getlist("Set-Cookie")
        self.assertTrue(any(sc.startswith("__session=") for sc in set_cookies), f"Missing __session in {set_cookies}")

        html = get_login.get_data(as_text=True)
        m = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
        self.assertIsNotNone(m)
        csrf_tok = m.group(1)

        # Logout clears both __session and legacy session cookies
        out_res = c.get("/logout", follow_redirects=False)
        self.assertEqual(out_res.status_code, 302)
        out_cookies = "\n".join(out_res.headers.getlist("Set-Cookie"))
        self.assertIn("__session=;", out_cookies)
        self.assertIn("session=;", out_cookies)
        self.assertIn("private", out_res.headers.get("Cache-Control", ""))

        # Two independent clients (simulating Device A & Device B) get isolated __session cookies & CSRF tokens
        c_a = app.app.test_client()
        c_b = app.app.test_client()
        tok_a = re.search(r'name="_csrf"\s+value="([^"]+)"', c_a.get("/student/login").get_data(as_text=True)).group(1)
        tok_b = re.search(r'name="_csrf"\s+value="([^"]+)"', c_b.get("/student/login").get_data(as_text=True)).group(1)
        self.assertNotEqual(tok_a, tok_b)
        self.assertTrue(bool(csrf_tok))


if __name__ == "__main__":
    unittest.main()
