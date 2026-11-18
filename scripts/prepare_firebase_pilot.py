#!/usr/bin/env python3
"""
Non-interactive Firebase Pilot Preparation & Data Sync Utility.

Performs:
  1. Strict stray test-data audit (verifies zero test/dummy records remain).
  2. Exports PGO-PI-IGA.accdb curriculum tables -> data/accdb_curriculum_bundle.json
     so Linux Cloud Run containers never require Microsoft Access ODBC drivers.
  3. Mirrors static/ and fonts/ -> public_hosting/ for Firebase Hosting CDN caching.
  4. Optional `--upload` flag pushes the audited pilot dataset + curriculum master
     into Cloud Firestore (`USE_FIREBASE=true` target project).
"""

import argparse
import json
import os
import shutil
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import accdb_curriculum
import config
import courses_store
import db_persistence
import student_store


def sync_public_hosting() -> int:
    """Prepares public_hosting/ with static assets & fonts (no root index.html so Cloud Run serves SSR)."""
    pub_dir = os.path.join(ROOT_DIR, "public_hosting")
    os.makedirs(pub_dir, exist_ok=True)
    copied = 0
    for sub in ("static", "fonts"):
        src = os.path.join(ROOT_DIR, sub)
        dst = os.path.join(pub_dir, sub)
        if os.path.isdir(src):
            shutil.copytree(
                src,
                dst,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("signatures", "*.tmp"),
            )
            for _, _, files in os.walk(dst):
                copied += len(files)
    # Remove any accidental root index.html that would shadow Flask's '/' rewrite
    accidental_idx = os.path.join(pub_dir, "index.html")
    if os.path.exists(accidental_idx):
        os.remove(accidental_idx)
    return copied


def audit_clean_pilot_state() -> dict:
    """Audits SQLite tables to ensure zero stray test records before pilot export."""
    conn = db_persistence.get_db_connection()
    try:
        stray_users = conn.execute(
            "SELECT username FROM app_users WHERE upper(username) LIKE '%TEST%' OR upper(username) LIKE '%TMP%'"
        ).fetchall()
        stray_students = conn.execute(
            "SELECT student_id FROM app_students WHERE student_id LIKE '2099%' OR upper(student_id) LIKE '%TEST%'"
        ).fetchall()
        stray_courses = conn.execute(
            "SELECT course_id FROM course_records WHERE course_id LIKE 'test_%' OR course_id LIKE 'tmp_%' OR course_id LIKE 'mem_%'"
        ).fetchall()
        counts = {}
        for tbl in ("app_users", "app_students", "course_records", "survey_responses", "cqi_plans"):
            counts[tbl] = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    finally:
        conn.close()

    if stray_users or stray_students or stray_courses:
        raise RuntimeError(
            f"Stray test rows detected before pilot export: users={[r[0] for r in stray_users]}, "
            f"students={[r[0] for r in stray_students]}, courses={[r[0] for r in stray_courses]}"
        )
    return counts


def _to_fs_val(v):
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {str(k): _to_fs_val(val) for k, val in v.items()}}}
    if isinstance(v, (list, tuple)):
        return {"arrayValue": {"values": [_to_fs_val(item) for item in v]}}
    return {"stringValue": str(v)}


def _rest_upsert_doc(project_id: str, database_id: str, token: str, collection: str, doc_id: str, payload: dict) -> None:
    import re
    import requests
    safe_id = re.sub(r"[/\\\s]+", "_", str(doc_id or "").strip()) or "_empty_"
    url = (
        f"https://firestore.googleapis.com/v1/projects/{project_id}"
        f"/databases/{database_id}/documents/{collection}/{safe_id}"
    )
    body = {"fields": {str(k): _to_fs_val(v) for k, v in payload.items()}}
    resp = requests.patch(url, headers={"Authorization": f"Bearer {token}"}, json=body, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"Firestore REST upsert failed for {collection}/{safe_id} ({resp.status_code}): {resp.text[:300]}")


def _get_gcloud_access_token() -> str:
    import subprocess
    candidates = ["gcloud", r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"]
    for exe in candidates:
        try:
            res = subprocess.run([exe, "auth", "print-access-token"], capture_output=True, text=True, timeout=15)
            tok = (res.stdout or "").strip()
            if res.returncode == 0 and tok:
                return tok
        except Exception:
            continue
    return ""


def upload_pilot_state_to_firestore(bundle: dict) -> dict:
    """Uploads clean curriculum, users, students, courses, surveys, and CQI plans to Firestore."""
    from datetime import datetime
    import firebase_persistence

    users = db_persistence.load_users_from_db()
    students = db_persistence.load_students_from_db()

    conn = db_persistence.get_db_connection()
    try:
        cids = [r[0] for r in conn.execute("SELECT course_id FROM course_records").fetchall()]
        cqi_cids = [r[0] for r in conn.execute("SELECT course_id FROM cqi_plans").fetchall()]
        srv_rows = [db_persistence._row_to_survey_dict(r) for r in conn.execute("SELECT * FROM survey_responses").fetchall()]
    finally:
        conn.close()

    course_docs = [courses_store.find_course(cid) for cid in cids]
    course_docs = [d for d in course_docs if isinstance(d, dict)]
    cqi_docs = [db_persistence.get_cqi_plan_db(cid) for cid in cqi_cids]
    cqi_docs = [d for d in cqi_docs if isinstance(d, dict)]

    # Try native Admin SDK / google-cloud-firestore first; fallback to gcloud token REST API
    use_rest = False
    try:
        firebase_persistence.save_curriculum_bundle(bundle)
    except Exception:
        use_rest = True

    if not use_rest:
        if users:
            firebase_persistence.save_users_dict_to_db(users, purge_missing=False)
        if students:
            firebase_persistence.save_students_dict_to_db(students, purge_missing=False)
        for doc in course_docs:
            firebase_persistence.save_course_to_db(doc)
        for p in cqi_docs:
            firebase_persistence.save_cqi_plan_db(p)
        for d in srv_rows:
            firebase_persistence.save_survey_response_db(
                student_id=d["student_id"],
                subject_id=d["subject_id"],
                course_code=d["course_code"],
                clo_ratings=d["clo_ratings"],
                general_ratings=d["general_ratings"],
                comments=d["comments"],
                cqi_anchors=d["cqi_anchors"],
                challenging_topics=d["challenging_topics"],
            )
    else:
        token = _get_gcloud_access_token()
        if not token:
            raise RuntimeError("No Firebase Admin ADC or gcloud access token available for Firestore upload.")
        proj = getattr(config, "FIREBASE_PROJECT_ID", "faculty-student-studio-usep")
        db_id = getattr(config, "FIRESTORE_DATABASE_ID", "(default)")
        now_iso = datetime.now().isoformat(timespec="seconds")

        bundle_payload = dict(bundle)
        bundle_payload["updated_at"] = now_iso
        _rest_upsert_doc(proj, db_id, token, "curriculum_master", "bsee", bundle_payload)

        for uname, u in users.items():
            username = str(u.get("username") or uname).strip()
            if username:
                u_pay = dict(u)
                u_pay["username"] = username
                u_pay.setdefault("created_at", now_iso)
                u_pay["updated_at"] = now_iso
                _rest_upsert_doc(proj, db_id, token, "app_users", username.lower(), u_pay)

        for sid, s in students.items():
            student_id = str(s.get("student_id") or sid).strip()
            if student_id:
                s_pay = dict(s)
                s_pay["student_id"] = student_id
                s_pay.setdefault("username", student_id)
                s_pay.setdefault("created_at", now_iso)
                s_pay["updated_at"] = now_iso
                _rest_upsert_doc(proj, db_id, token, "app_students", student_id, s_pay)

        for doc in course_docs:
            cid = str(doc.get("id") or doc.get("course_id") or "").strip()
            if cid:
                bp = doc.get("blueprint") if isinstance(doc.get("blueprint"), dict) else {}
                meta = bp.get("metadata") if isinstance(bp.get("metadata"), dict) else {}
                c_pay = dict(doc)
                c_pay["id"] = cid
                c_pay["course_id"] = cid
                c_pay["owner"] = str(doc.get("owner") or "").strip()
                c_pay["owner_lower"] = c_pay["owner"].lower()
                c_pay["course_code"] = str(meta.get("course_code") or doc.get("course_code") or "").strip()
                c_pay["course_title"] = str(meta.get("course_title") or doc.get("course_title") or "").strip()
                c_pay["section"] = str(meta.get("section") or doc.get("section") or "").strip()
                c_pay["semester_ay"] = str(meta.get("semester_ay") or doc.get("semester_ay") or "").strip()
                c_pay.setdefault("created_at", now_iso)
                c_pay["updated_at"] = str(doc.get("updated_at") or now_iso)
                _rest_upsert_doc(proj, db_id, token, "courses", cid, c_pay)

        for p in cqi_docs:
            cid = str(p.get("course_id") or "").strip()
            if cid:
                _rest_upsert_doc(proj, db_id, token, "cqi_plans", cid, p)

        for d in srv_rows:
            doc_id = f"{d['subject_id']}__{d['student_id']}"
            _rest_upsert_doc(proj, db_id, token, "survey_responses", doc_id, d)

    return {
        "curriculum_courses": bundle.get("courses_count", 0),
        "users": len(users),
        "students": len(students),
        "courses": len(course_docs),
        "cqi_plans": len(cqi_docs),
        "survey_responses": len(srv_rows),
        "upload_mode": "firestore_rest_gcloud" if use_rest else "firebase_admin_sdk",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Firebase + Cloud Run Pilot Bundle")
    parser.add_argument("--upload", action="store_true", help="Upload clean database & curriculum directly to Cloud Firestore")
    args = parser.parse_args()

    print("1. Auditing database for zero stray test data...")
    counts = audit_clean_pilot_state()
    print(f"   Clean audit counts: {counts}")

    print("2. Exporting PGO-PI-IGA.accdb curriculum bundle to portable JSON...")
    bundle = accdb_curriculum.export_accdb_cloud_bundle()
    print(f"   Exported {bundle['courses_count']} courses & {bundle['pgo_count']} PGOs -> {accdb_curriculum.BUNDLE_PATH}")

    print("3. Preparing Firebase Hosting static bundle (public_hosting/)...")
    assets_count = sync_public_hosting()
    print(f"   Copied {assets_count} static & font files into public_hosting/")

    if args.upload:
        print("4. Uploading clean pilot dataset to Cloud Firestore...")
        summary = upload_pilot_state_to_firestore(bundle)
        print(f"   Firestore upload complete: {summary}")
    else:
        print("4. Dry-run local prep complete (pass --upload after GCP/Firebase login to seed Firestore).")


if __name__ == "__main__":
    main()
