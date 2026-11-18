"""
Cloud Firestore persistence backend for USeP OBE Pilot Deployment (Cloud Run + Firebase).

Activated transparently when `USE_FIREBASE=true` in environment / config.py.
Maps every operation from db_persistence.py onto Cloud Firestore collections:
  - app_users          (doc ID: lowercase username)
  - app_students       (doc ID: student_id)
  - courses            (doc ID: course_id)
  - survey_responses   (doc ID: {subject_id}__{student_id})
  - cqi_plans          (doc ID: course_id)
  - curriculum_master  (doc ID: bsee)
"""

import copy
import logging
import re
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)

_FS_LOCK = threading.RLock()
_FS_CLIENT = None


def set_firestore_client_for_tests(client: Any) -> None:
    """Allows unit tests to inject an in-memory/mock Firestore client."""
    global _FS_CLIENT
    with _FS_LOCK:
        _FS_CLIENT = client


def _get_db():
    """Returns a thread-safe Cloud Firestore Client singleton (via firebase-admin or google-cloud-firestore)."""
    global _FS_CLIENT
    with _FS_LOCK:
        if _FS_CLIENT is not None:
            return _FS_CLIENT

        proj = getattr(config, "FIREBASE_PROJECT_ID", "") or "faculty-student-studio-usep"
        bucket = getattr(config, "FIREBASE_STORAGE_BUCKET", "") or f"{proj}.firebasestorage.app"
        db_id = getattr(config, "FIRESTORE_DATABASE_ID", "(default)") or "(default)"

        try:
            import firebase_admin
            from firebase_admin import firestore as fb_firestore

            if not firebase_admin._apps:
                firebase_admin.initialize_app(options={
                    "projectId": proj,
                    "storageBucket": bucket,
                })
            try:
                _FS_CLIENT = fb_firestore.client(database_id=db_id)
            except TypeError:
                _FS_CLIENT = fb_firestore.client()
            return _FS_CLIENT
        except ImportError:
            from google.cloud import firestore

            kwargs: Dict[str, Any] = {"project": proj}
            if db_id and db_id != "(default)":
                kwargs["database"] = db_id
            _FS_CLIENT = firestore.Client(**kwargs)
            return _FS_CLIENT


def _safe_doc_id(raw: str) -> str:
    return re.sub(r"[/\\\s]+", "_", str(raw or "").strip()) or "_empty_"


def _norm_survey_sid(student_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(student_id or "")).lower()


def _sid_digits(student_id: str) -> str:
    return re.sub(r"\D", "", str(student_id or ""))


def aggregate_course_surveys_from_dicts(
    subject_id: str,
    rows: List[Dict[str, Any]],
    clos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Shared pure-Python Course Exit Survey aggregator used by both SQLite & Firestore."""
    sub_clean = str(subject_id or "").strip()
    completed = [r for r in (rows or []) if r.get("is_completed", True)]
    completed.sort(key=lambda r: str(r.get("submitted_at") or ""), reverse=True)

    clo_buckets: Dict[str, List[float]] = {}
    gen_buckets: Dict[str, List[float]] = {}
    anchor_buckets: Dict[str, List[float]] = {}
    challenging_list: List[str] = []
    comments_list: List[Dict[str, str]] = []

    for r in completed:
        for cid, val in (r.get("clo_ratings") or {}).items():
            try:
                clo_buckets.setdefault(str(cid).upper(), []).append(float(val))
            except (TypeError, ValueError):
                pass
        for gk, val in (r.get("general_ratings") or {}).items():
            try:
                gen_buckets.setdefault(str(gk), []).append(float(val))
            except (TypeError, ValueError):
                pass
        for ak, val in (r.get("cqi_anchors") or {}).items():
            try:
                anchor_buckets.setdefault(str(ak), []).append(float(val))
            except (TypeError, ValueError):
                pass

        chal = str(r.get("challenging_topics") or "").strip()
        if chal:
            challenging_list.append(chal)

        cmt = str(r.get("comments") or "").strip()
        if cmt:
            comments_list.append({
                "comment": cmt,
                "challenging_topics": chal,
                "submitted_at": str(r.get("submitted_at") or ""),
            })
        elif chal:
            comments_list.append({
                "comment": f"[Challenging Topics/CLOs] {chal}",
                "challenging_topics": chal,
                "submitted_at": str(r.get("submitted_at") or ""),
            })

    clo_desc_map = {
        str(c.get("co_id") or "").upper(): str(c.get("description") or "")
        for c in (clos or []) if isinstance(c, dict) and c.get("co_id")
    }
    ordered_cids = list(clo_desc_map.keys()) + [
        k for k in sorted(clo_buckets.keys()) if k not in clo_desc_map
    ]

    clo_summary = []
    for cid in ordered_cids:
        vals = clo_buckets.get(cid, [])
        avg_r = round(sum(vals) / len(vals), 2) if vals else None
        clo_summary.append({
            "co_id": cid,
            "description": clo_desc_map.get(cid, ""),
            "responses_count": len(vals),
            "avg_rating": avg_r,
            "pct_equivalent": round((avg_r / 5.0) * 100.0, 1) if avg_r is not None else None,
        })

    general_summary = {
        k: {"responses_count": len(v), "avg_rating": round(sum(v) / len(v), 2) if v else None}
        for k, v in gen_buckets.items()
    }
    cqi_anchors_summary = {
        ak: {"responses_count": len(v), "avg_rating": round(sum(v) / len(v), 2) if v else None}
        for ak, v in anchor_buckets.items()
    }
    all_vals = [x for vals in list(clo_buckets.values()) + list(gen_buckets.values()) for x in vals]
    overall_avg = round(sum(all_vals) / len(all_vals), 2) if all_vals else None

    return {
        "subject_id": sub_clean,
        "total_responses": len(completed),
        "overall_avg_rating": overall_avg,
        "clo_ratings_summary": clo_summary,
        "general_ratings_summary": general_summary,
        "cqi_anchors_summary": cqi_anchors_summary,
        "challenging_topics": challenging_list,
        "comments": comments_list,
    }


# ==============================================================================
# USERS CRUD (Firestore collection: app_users)
# ==============================================================================

def load_users_from_db() -> Dict[str, Dict[str, Any]]:
    db = _get_db()
    out: Dict[str, Dict[str, Any]] = {}
    for snap in db.collection("app_users").stream():
        data = snap.to_dict() or {}
        uname = str(data.get("username") or snap.id).strip()
        if uname:
            out[uname] = data
    return out


def save_user_to_db(u: Dict[str, Any]) -> None:
    username = str(u.get("username") or "").strip()
    if not username:
        return
    db = _get_db()
    now_iso = datetime.now().isoformat()
    payload = copy.deepcopy(u)
    payload.setdefault("created_at", now_iso)
    payload["updated_at"] = now_iso
    payload["username"] = username
    db.collection("app_users").document(_safe_doc_id(username.lower())).set(payload)


def delete_user_from_db(username: str) -> bool:
    uname = str(username or "").strip().lower()
    if not uname:
        return False
    db = _get_db()
    ref = db.collection("app_users").document(_safe_doc_id(uname))
    existed = ref.get().exists
    ref.delete()
    if not existed:
        for snap in db.collection("app_users").stream():
            d = snap.to_dict() or {}
            if str(d.get("username") or "").strip().lower() == uname:
                snap.reference.delete()
                existed = True
    return existed


def save_users_dict_to_db(users_dict: Dict[str, Dict[str, Any]], purge_missing: bool = True) -> None:
    db = _get_db()
    now_iso = datetime.now().isoformat()
    col = db.collection("app_users")
    valid_ids = {_safe_doc_id((u.get("username") or k).strip().lower()) for k, u in (users_dict or {}).items() if (u.get("username") or k).strip()}

    if purge_missing and valid_ids:
        for snap in col.stream():
            if snap.id not in valid_ids:
                snap.reference.delete()

    batch = db.batch()
    ops = 0
    for uname, u in (users_dict or {}).items():
        username = str(u.get("username") or uname).strip()
        if not username:
            continue
        payload = copy.deepcopy(u)
        payload["username"] = username
        payload.setdefault("created_at", now_iso)
        payload["updated_at"] = now_iso
        batch.set(col.document(_safe_doc_id(username.lower())), payload)
        ops += 1
        if ops >= 400:
            batch.commit()
            batch = db.batch()
            ops = 0
    if ops:
        batch.commit()


# ==============================================================================
# STUDENTS CRUD (Firestore collection: app_students)
# ==============================================================================

def load_students_from_db() -> Dict[str, Dict[str, Any]]:
    db = _get_db()
    out: Dict[str, Dict[str, Any]] = {}
    for snap in db.collection("app_students").stream():
        data = snap.to_dict() or {}
        sid = str(data.get("student_id") or snap.id).strip()
        if sid:
            out[sid] = data
    return out


def delete_student_from_db(student_id: str) -> bool:
    sid = str(student_id or "").strip()
    if not sid:
        return False
    db = _get_db()
    ref = db.collection("app_students").document(_safe_doc_id(sid))
    existed = ref.get().exists
    ref.delete()
    return existed


def disenroll_student_from_course_db(student_id: str, course_id: str) -> bool:
    sid = str(student_id or "").strip()
    cid = str(course_id or "").strip()
    if not sid or not cid:
        return False
    db = _get_db()
    ref = db.collection("app_students").document(_safe_doc_id(sid))
    snap = ref.get()
    if snap.exists:
        data = snap.to_dict() or {}
        enrolled = data.get("enrolled_courses") or []
        data["enrolled_courses"] = [c for c in enrolled if str(c).strip().lower() != cid.lower()]
        data["updated_at"] = datetime.now().isoformat()
        ref.set(data)
    return True


def save_students_dict_to_db(students_dict: Dict[str, Dict[str, Any]], purge_missing: bool = True) -> None:
    db = _get_db()
    now_iso = datetime.now().isoformat()
    col = db.collection("app_students")
    valid_ids = {_safe_doc_id(str(s.get("student_id") or k).strip()) for k, s in (students_dict or {}).items() if str(s.get("student_id") or k).strip()}

    if purge_missing and valid_ids:
        for snap in col.stream():
            if snap.id not in valid_ids:
                snap.reference.delete()

    batch = db.batch()
    ops = 0
    for sid, s in (students_dict or {}).items():
        student_id = str(s.get("student_id") or sid).strip()
        if not student_id:
            continue
        payload = copy.deepcopy(s)
        payload["student_id"] = student_id
        payload.setdefault("username", student_id)
        payload.setdefault("created_at", now_iso)
        payload["updated_at"] = now_iso
        batch.set(col.document(_safe_doc_id(student_id)), payload)
        ops += 1
        if ops >= 400:
            batch.commit()
            batch = db.batch()
            ops = 0
    if ops:
        batch.commit()


def get_enrolled_students_for_course(
    course_id: str,
    section: str = "",
    program_code: str = "",
    exclude_student_ids: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    cid = str(course_id or "").strip()
    sec = str(section or "").strip()
    prog = str(program_code or "").strip().upper()
    excluded = {str(x).strip().lower() for x in (exclude_student_ids or []) if str(x).strip()}

    sec_tokens = [s.strip() for s in sec.split(",") if s.strip()]
    sec_variants = set()
    for s in sec_tokens:
        sec_variants.add(s.upper())
        clean = re.sub(r"^(BSEE|BSCE|BSCpE|BSECE|BSME|EE)\s*", "", s, flags=re.I).strip().upper()
        if clean:
            sec_variants.add(clean)
            sec_variants.add(f"EE {clean}")
            sec_variants.add(f"BSEE {clean}")
            if prog:
                sec_variants.add(f"{prog} {clean}")

    course_doc = load_course_from_db(cid) or {}
    bp_students = ((course_doc.get("blueprint") or {}).get("students") or [])
    bp_scores_by_sid = {
        str(st.get("student_id") or "").strip().lower(): (st.get("scores") or {})
        for st in bp_students if isinstance(st, dict) and st.get("student_id")
    }

    all_students = load_students_from_db()
    matched: List[Dict[str, Any]] = []
    for sid, st in all_students.items():
        if sid.lower() in excluded:
            continue
        enrolled = [str(x).strip() for x in (st.get("enrolled_courses") or [])]
        prog_yr = str(st.get("program_year") or "").strip().upper()
        in_enrolled = cid in enrolled
        in_bp = sid.lower() in bp_scores_by_sid
        in_sec = bool(sec_variants and any(v == prog_yr or v in prog_yr for v in sec_variants))
        if not (in_enrolled or in_bp or in_sec):
            continue

        all_acks = st.get("assessment_acknowledgments") or {}
        course_acks = all_acks.get(cid, {}) if isinstance(all_acks, dict) else {}
        matched.append({
            "student_id": sid,
            "username": st.get("username") or sid,
            "full_name": st.get("full_name") or sid,
            "first_name": st.get("first_name") or "",
            "last_name": st.get("last_name") or "",
            "email": st.get("email") or "",
            "program_year": st.get("program_year") or "",
            "scores": bp_scores_by_sid.get(sid.lower(), {}),
            "assessment_acknowledgments": course_acks,
        })

    matched.sort(key=lambda x: (x.get("last_name") or "", x.get("first_name") or "", x.get("student_id") or ""))
    return matched


# ==============================================================================
# COURSES CRUD (Firestore collection: courses)
# ==============================================================================

def save_course_to_db(doc: Dict[str, Any]) -> None:
    cid = str(doc.get("id") or doc.get("course_id") or "").strip()
    if not cid:
        return
    db = _get_db()
    bp = doc.get("blueprint") if isinstance(doc.get("blueprint"), dict) else {}
    meta = bp.get("metadata") if isinstance(bp.get("metadata"), dict) else {}
    now_iso = datetime.now().isoformat()

    payload = copy.deepcopy(doc)
    payload["id"] = cid
    payload["course_id"] = cid
    payload["owner"] = str(doc.get("owner") or "").strip()
    payload["owner_lower"] = payload["owner"].lower()
    payload["course_code"] = str(meta.get("course_code") or doc.get("course_code") or "").strip()
    payload["course_title"] = str(meta.get("course_title") or doc.get("course_title") or "").strip()
    payload["section"] = str(meta.get("section") or doc.get("section") or "").strip()
    payload["semester_ay"] = str(meta.get("semester_ay") or doc.get("semester_ay") or "").strip()
    payload.setdefault("created_at", now_iso)
    payload["updated_at"] = str(doc.get("updated_at") or now_iso)
    db.collection("courses").document(_safe_doc_id(cid)).set(payload)


def load_course_from_db(course_id: str) -> Optional[Dict[str, Any]]:
    cid = str(course_id or "").strip()
    if not cid:
        return None
    db = _get_db()
    snap = db.collection("courses").document(_safe_doc_id(cid)).get()
    if not snap.exists:
        return None
    return snap.to_dict()


def list_courses_from_db_for_user(username: str) -> List[Dict[str, Any]]:
    uname_l = str(username or "").strip().lower()
    out: List[Dict[str, Any]] = []
    for doc in list_all_courses_from_db():
        owner_l = str(doc.get("owner") or "").strip().lower()
        authors = doc.get("authors") or ((doc.get("blueprint") or {}).get("metadata") or {}).get("authors") or []
        author_unames = [str(a.get("username") or "").strip().lower() for a in authors if isinstance(a, dict)]
        if owner_l == uname_l or uname_l in author_unames:
            out.append(doc)
    out.sort(key=lambda d: str(d.get("updated_at") or ""), reverse=True)
    return out


def list_all_courses_from_db() -> List[Dict[str, Any]]:
    db = _get_db()
    docs = [snap.to_dict() for snap in db.collection("courses").stream() if snap.exists]
    docs.sort(key=lambda d: str(d.get("updated_at") or ""), reverse=True)
    return docs


def delete_course_from_db(course_id: str) -> bool:
    cid = str(course_id or "").strip()
    if not cid:
        return False
    db = _get_db()
    ref = db.collection("courses").document(_safe_doc_id(cid))
    existed = ref.get().exists
    ref.delete()
    # Cascade cleanup on cqi_plans & survey_responses for this course
    db.collection("cqi_plans").document(_safe_doc_id(cid)).delete()
    for snap in db.collection("survey_responses").where("subject_id", "==", cid).stream():
        snap.reference.delete()
    return existed


# ==============================================================================
# SURVEY RESPONSES CRUD (Firestore collection: survey_responses)
# ==============================================================================

def save_survey_response_db(
    student_id: str,
    subject_id: str,
    course_code: str,
    clo_ratings: Dict[str, int],
    general_ratings: Dict[str, int],
    comments: str = "",
    cqi_anchors: Optional[Dict[str, int]] = None,
    challenging_topics: str = "",
) -> Dict[str, Any]:
    db = _get_db()
    sid_clean = str(student_id or "").strip()
    sub_clean = str(subject_id or "").strip()
    now_ts = datetime.now().isoformat(timespec="seconds")
    doc_id = _safe_doc_id(f"{sub_clean}__{sid_clean}")
    payload = {
        "student_id": sid_clean,
        "subject_id": sub_clean,
        "course_code": str(course_code or "").strip(),
        "clo_ratings": clo_ratings or {},
        "general_ratings": general_ratings or {},
        "cqi_anchors": cqi_anchors or {},
        "challenging_topics": str(challenging_topics or "").strip(),
        "comments": str(comments or "").strip(),
        "submitted_at": now_ts,
        "is_completed": True,
    }
    db.collection("survey_responses").document(doc_id).set(payload)
    return payload


def get_student_survey_response_db(student_id: str, subject_id: str) -> Optional[Dict[str, Any]]:
    sid_norm = _norm_survey_sid(student_id)
    sid_dig = _sid_digits(student_id)
    sub_clean = str(subject_id or "").strip()
    if not sid_norm or not sub_clean:
        return None
    db = _get_db()
    for snap in db.collection("survey_responses").where("subject_id", "==", sub_clean).stream():
        d = snap.to_dict() or {}
        r_sid = str(d.get("student_id") or "")
        if _norm_survey_sid(r_sid) == sid_norm or (sid_dig and len(sid_dig) >= 4 and _sid_digits(r_sid) == sid_dig):
            return d
    return None


def get_student_completed_surveys_map_db(student_id: str) -> Dict[str, Dict[str, Any]]:
    sid_norm = _norm_survey_sid(student_id)
    sid_dig = _sid_digits(student_id)
    if not sid_norm:
        return {}
    db = _get_db()
    out: Dict[str, Dict[str, Any]] = {}
    for snap in db.collection("survey_responses").where("is_completed", "==", True).stream():
        d = snap.to_dict() or {}
        r_sid = str(d.get("student_id") or "")
        if _norm_survey_sid(r_sid) == sid_norm or (sid_dig and len(sid_dig) >= 4 and _sid_digits(r_sid) == sid_dig):
            sub_id = str(d.get("subject_id") or "").strip()
            if sub_id:
                out[sub_id] = d
    return out


def get_course_survey_aggregates_db(
    subject_id: str,
    clos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    sub_clean = str(subject_id or "").strip()
    db = _get_db()
    rows = [
        snap.to_dict() or {}
        for snap in db.collection("survey_responses").where("subject_id", "==", sub_clean).stream()
    ]
    return aggregate_course_surveys_from_dicts(sub_clean, rows, clos)


# ==============================================================================
# CQI PLANS WORKFLOW CRUD (Firestore collection: cqi_plans)
# ==============================================================================

def save_cqi_plan_db(plan_data: Dict[str, Any]) -> Dict[str, Any]:
    db = _get_db()
    now_ts = datetime.now().isoformat(timespec="seconds")
    cid = str(plan_data.get("course_id") or "").strip()
    ref = db.collection("cqi_plans").document(_safe_doc_id(cid))
    existing = ref.get().to_dict() if ref.get().exists else {}

    merged = dict(existing or {})
    merged.update({
        "course_id": cid,
        "course_code": str(plan_data.get("course_code") or "").strip(),
        "course_title": str(plan_data.get("course_title") or "").strip(),
        "section": str(plan_data.get("section") or "").strip(),
        "program_code": str(plan_data.get("program_code") or "EE").strip(),
        "semester_ay": str(plan_data.get("semester_ay") or "").strip(),
        "faculty_username": str(plan_data.get("faculty_username") or "").strip(),
        "faculty_name": str(plan_data.get("faculty_name") or "").strip(),
        "targeted_clos": plan_data.get("targeted_clos") or [],
        "synthesis": plan_data.get("synthesis") or {},
        "key_strengths": str(plan_data.get("key_strengths") or ""),
        "areas_for_improvement": str(plan_data.get("areas_for_improvement") or ""),
        "gap_analysis": str(plan_data.get("gap_analysis") or ""),
        "root_causes": str(plan_data.get("root_causes") or ""),
        "action_plan": str(plan_data.get("action_plan") or ""),
        "target_kpis": str(plan_data.get("target_kpis") or ""),
        "indicators": plan_data.get("indicators") or [],
        "status": str(plan_data.get("status") or "draft"),
        "revisit_status": str(plan_data.get("revisit_status") or existing.get("revisit_status") or "Upcoming"),
        "updated_at": now_ts,
    })
    for opt_k in ("submitted_at", "reviewed_by", "reviewed_by_name", "reviewed_at", "program_head_remarks", "revisit_date", "revisit_term"):
        if plan_data.get(opt_k) is not None:
            merged[opt_k] = plan_data.get(opt_k)
        else:
            merged.setdefault(opt_k, None)

    ref.set(merged)
    return merged


def get_cqi_plan_db(course_id: str) -> Optional[Dict[str, Any]]:
    cid = str(course_id or "").strip()
    if not cid:
        return None
    db = _get_db()
    snap = db.collection("cqi_plans").document(_safe_doc_id(cid)).get()
    return snap.to_dict() if snap.exists else None


def list_cqi_plans_db(include_drafts: bool = False) -> List[Dict[str, Any]]:
    db = _get_db()
    plans = [snap.to_dict() or {} for snap in db.collection("cqi_plans").stream()]
    if not include_drafts:
        plans = [p for p in plans if str(p.get("status") or "draft") != "draft"]
    plans.sort(key=lambda p: str(p.get("submitted_at") or p.get("updated_at") or ""), reverse=True)
    return plans


def update_cqi_plan_review_db(
    course_id: str,
    status: str,
    reviewed_by: str,
    reviewed_by_name: str,
    remarks: str = "",
    revisit_date: Optional[str] = None,
    revisit_status: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    cid = str(course_id or "").strip()
    db = _get_db()
    ref = db.collection("cqi_plans").document(_safe_doc_id(cid))
    snap = ref.get()
    if not snap.exists:
        return None
    row = snap.to_dict() or {}
    now_ts = datetime.now().isoformat(timespec="seconds")
    row["status"] = status
    row["reviewed_by"] = reviewed_by
    row["reviewed_by_name"] = reviewed_by_name
    row["reviewed_at"] = now_ts
    row["program_head_remarks"] = remarks
    if revisit_date and revisit_date.strip():
        row["revisit_date"] = revisit_date.strip()
    if revisit_status and revisit_status.strip():
        row["revisit_status"] = revisit_status.strip()
    row["updated_at"] = now_ts
    ref.set(row)
    return row


# ==============================================================================
# CURRICULUM MASTER BUNDLE (Firestore collection: curriculum_master)
# ==============================================================================

def save_curriculum_bundle(bundle: Dict[str, Any]) -> None:
    db = _get_db()
    payload = copy.deepcopy(bundle)
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    db.collection("curriculum_master").document("bsee").set(payload)


def load_curriculum_bundle() -> Optional[Dict[str, Any]]:
    db = _get_db()
    snap = db.collection("curriculum_master").document("bsee").get()
    return snap.to_dict() if snap.exists else None
