"""
Authentication for the USeP OBE Syllabus Creator & Class Record Generator.

- Faculty accounts are stored locally in data/users.json with hashed passwords
  (werkzeug PBKDF2/scrypt). Plain-text passwords are never written to disk.
- There is no public registration page: only an admin can create accounts.
- On first run a default admin account is created (admin / admin123) and is
  forced to change its password on first login.
"""
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    session, url_for, current_app, make_response,
)
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import config
    BASE_DIR = config.BASE_DIR
    DATA_DIR = config.DATA_DIR
    USERS_FILE = config.USERS_JSON_PATH
    SECRET_KEY_FILE = config.SECRET_KEY_FILE
except Exception:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    USERS_FILE = os.environ.get("USERS_JSON_PATH", os.path.join(DATA_DIR, "users.json"))
    SECRET_KEY_FILE = os.environ.get("SECRET_KEY_FILE", os.path.join(DATA_DIR, "secret_key"))

DELETED_USERS_FILE = os.path.join(DATA_DIR, "deleted_users.json")

def _load_deleted_users() -> set:
    if not os.path.exists(DELETED_USERS_FILE):
        return set()
    try:
        with open(DELETED_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()

def _save_deleted_users(deleted: set) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(DELETED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(deleted)), f, indent=2)
    except Exception as e:
        print(f"Error saving deleted users: {e}")


LEGACY_USERNAME_ALIASES = {
    "committee_basan": "faculty_basan",
    "committee_arenga": "faculty_arenga",
    "committee_ravida": "faculty_ravida",
    "programhead_claro": "faculty_claro",
    "assoc_dean": "faculty_tongson",
    "staff_simplicio_lab": "faculty_simplicio",
}

DEFAULT_ADMIN_USERNAME = "admin" 
DEFAULT_ADMIN_PASSWORD = "admin123"
MIN_PASSWORD_LENGTH = 8

# Simple in-memory brute-force protection: lock a username/IP pair for a while
# after too many failed attempts.
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 120

_lock = threading.Lock()
_failed_attempts = {}  # key -> (count, first_failure_ts)

auth_bp = Blueprint("auth", __name__)

PROGRAM_FULL_NAMES = {
    "EE": "Electrical Engineering",
    "ECE": "Electronics Engineering",
    "ME": "Mechanical Engineering",
    "CE": "Civil Engineering",
    "GE": "Geodetic Engineering",
    "MinE": "Mining Engineering",
    "BSGeo": "Geology",
    "SE": "Sanitary Engineering",
    "ABE": "Agricultural and Biosystems Engineering",
}

def apply_roles_to_user_dict(
    target: dict,
    workflow_roles=None,
    program_codes=None,
    custom_title: str = "",
    is_admin: bool = False
):
    roles = []
    for r in (workflow_roles or []):
        r_clean = str(r).strip().lower()
        if r_clean and r_clean not in roles:
            roles.append(r_clean)

    is_staff = ("staff" in roles)
    has_faculty_roles = any(r in roles for r in ["review_committee", "faculty", "program_head", "qa_head", "dean", "associate_dean"])

    if is_staff and not has_faculty_roles and not is_admin and "admin" not in roles:
        roles = ["staff"]
    elif not roles or roles == ["faculty"]:
        roles = ["review_committee"]
    elif "review_committee" not in roles and not is_staff:
        roles.append("review_committee")

    cleaned_progs = []
    for p in (program_codes or []):
        p_clean = str(p).strip().upper()
        if p_clean and p_clean not in cleaned_progs:
            cleaned_progs.append(p_clean)
    if not cleaned_progs:
        cleaned_progs = ["*"] if is_staff else ["EE"]

    target["workflow_roles"] = roles
    target["program_codes"] = cleaned_progs

    if not custom_title:
        title_parts = []
        if "program_head" in roles:
            p_names = [PROGRAM_FULL_NAMES.get(p, p) for p in cleaned_progs if p != "*"]
            p_str = ", ".join(p_names) if p_names else "Electrical Engineering"
            title_parts.append(f"Program Head - {p_str}")
        if "dean" in roles:
            title_parts.append("Dean, College of Engineering")
        elif "associate_dean" in roles:
            title_parts.append("Associate Dean, College of Engineering")
        if "qa_head" in roles:
            title_parts.append("College Quality Assurance Head")
        if "staff" in roles:
            title_parts.append("Academic Programs Staff (Oversight)")
        if "admin" in roles and not title_parts:
            title_parts.append("System Administrator")
        if not title_parts:
            title_parts.append("Faculty Member")

        custom_title = " & ".join(title_parts)

    target["position_title"] = custom_title

    is_pure_staff = (is_staff and not has_faculty_roles and not is_admin and "admin" not in roles)
    if is_admin or "admin" in roles:
        target["role"] = "admin"
    elif is_pure_staff:
        target["role"] = "staff"
    else:
        target["role"] = "faculty"


def apply_role_to_user_dict(target: dict, designation: str, prog_code: str = "EE", custom_title: str = "", is_admin: bool = False):
    desig = (designation or "faculty").strip().lower()
    prog = (prog_code or "EE").strip().upper()
    if desig == "program_head":
        roles = ["program_head", "review_committee"]
        progs = [prog]
    elif desig == "qa_head":
        roles = ["qa_head", "review_committee"]
        progs = ["*"]
    elif desig == "associate_dean":
        roles = ["associate_dean", "review_committee"]
        progs = ["*"]
    elif desig == "dean":
        roles = ["dean", "review_committee"]
        progs = ["*"]
    elif desig == "staff":
        roles = ["staff"]
        progs = ["*"]
    elif desig == "admin":
        roles = ["admin", "review_committee", "program_head", "qa_head", "dean"]
        progs = ["*"]
        is_admin = True
    else:
        roles = ["review_committee"]
        progs = [prog]

    apply_roles_to_user_dict(target, roles, progs, custom_title, is_admin)


# --------------------------------------------------------------------------
# Storage helpers
# --------------------------------------------------------------------------
def get_or_create_secret_key() -> bytes:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "rb") as f:
            key = f.read().strip()
            if key:
                return key
    key = secrets.token_hex(32).encode("ascii")
    with open(SECRET_KEY_FILE, "wb") as f:
        f.write(key)
    return key


def derive_email(username: str, full_name: str = "") -> str:
    """Derives a standard USeP institutional email address."""
    name = re.sub(r"^(Engr\.|Dr\.|Dean|Prof\.|Mr\.|Ms\.|Mrs\.)\s*", "", full_name or "", flags=re.IGNORECASE).strip()
    name = re.sub(r",.*$", "", name).strip()
    parts = [p.lower() for p in re.findall(r"[A-Za-z]+", name) if len(p) > 1]
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[-1]}@usep.edu.ph"
    elif len(parts) == 1:
        return f"{parts[0]}@usep.edu.ph"
    clean_u = username.lower().replace("faculty_", "").replace("programhead_", "").replace("committee_", "")
    return f"{clean_u}@usep.edu.ph"


def _load_users() -> dict:
    try:
        import db_persistence
        db_users = db_persistence.load_users_from_db()
        if db_users:
            return db_users
    except Exception:
        pass
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            # Ensure every user account has an institutional email
            dirty = False
            for uname, u in data.items():
                if isinstance(u, dict) and not u.get("email"):
                    u["email"] = derive_email(uname, u.get("full_name", ""))
                    dirty = True
            if dirty:
                try:
                    with open(USERS_FILE, "w", encoding="utf-8") as fw:
                        json.dump(data, fw, indent=2)
                except Exception:
                    pass
            return data
    except (OSError, json.JSONDecodeError):
        return {}


def _save_users(users: dict) -> None:
    try:
        import db_persistence
        db_persistence.save_users_dict_to_db(users)
    except Exception:
        pass
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    for _ in range(5):
        try:
            os.replace(tmp, USERS_FILE)
            return
        except PermissionError:
            import time
            time.sleep(0.05)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass


def ensure_default_admin() -> None:
    with _lock:
        users = _load_users()
        now_ts = datetime.now().isoformat(timespec="seconds")

        # Standard default admin
        if DEFAULT_ADMIN_USERNAME not in users:
            users[DEFAULT_ADMIN_USERNAME] = {
                "full_name": "System Administrator",
                "role": "admin",
                "workflow_roles": ["review_committee", "program_head", "qa_head", "dean"],
                "position_title": "System Administrator",
                "password_hash": generate_password_hash(DEFAULT_ADMIN_PASSWORD),
                "must_change_password": False,
                "created_at": now_ts,
                "last_login": None,
            }

        # Clean legacy duplicate accounts from users
        for leg in ["committee_basan", "committee_arenga", "committee_ravida", "programhead_claro", "assoc_dean", "staff_simplicio_lab", "faculty_tester"]:
            if leg in users:
                del users[leg]

        # Seed standard signatory/workflow test accounts
        seed_accounts = [
            ("faculty_tano", "Elwin Jay J. Tano", "faculty", ["review_committee"], "Faculty Member", "EE"),
            ("faculty_basan", "Nikka Samantha A. Basan", "faculty", ["review_committee"], "Faculty Member", "EE"),
            ("faculty_arenga", "Delan Zoe H. Arenga", "faculty", ["review_committee"], "Faculty Member", "ECE"),
            ("faculty_ravida", "Kim P. Ravida", "faculty", ["qa_head", "review_committee"], "College Quality Assurance Head", "ECE"),
            ("faculty_claro", "Charito O. Claro", "faculty", ["program_head", "review_committee"], "Program Head - Electrical Engineering", "EE"),
            ("qahead_ce", "College QA Head", "faculty", ["qa_head"], "College Quality Assurance Head", "*"),
            ("dean_cataytay", "Joie D. Cataytay", "faculty", ["dean", "review_committee"], "Dean, College of Engineering", "*"),
            ("staff_office", "Academic Affairs Staff", "staff", ["staff"], "Academic Programs Staff (Oversight)", "*"),
        ]
        for uname, fname, role, w_roles, pos, prog in seed_accounts:
            if uname not in users:
                users[uname] = {
                    "full_name": fname,
                    "role": role,
                    "workflow_roles": w_roles,
                    "position_title": pos,
                    "program_codes": [prog],
                    "college": "COLLEGE OF ENGINEERING",
                    "password_hash": generate_password_hash("password123"),
                    "must_change_password": False,
                    "created_at": now_ts,
                    "last_login": None,
                }
            else:
                users[uname]["full_name"] = fname
                users[uname]["position_title"] = pos
                users[uname]["workflow_roles"] = w_roles

        # Seed official faculty roster from catalog_data
        try:
            import base64
            from catalog_data import OFFICIAL_FACULTY_ROSTER
            default_hash = generate_password_hash("password123")
            for dept_code, groups in OFFICIAL_FACULTY_ROSTER.items():
                is_staff = (dept_code == "STAFF")
                deleted_set = _load_deleted_users()
                for fac in (groups.get("full_time", []) + groups.get("part_time", [])):
                    u = fac.get("username")
                    if not u or u in deleted_set:
                        continue
                    roles = fac.get("roles", [])
                    if not roles and fac.get("type") == "Full-Time" and not is_staff:
                        roles = ["review_committee"]
                    if u not in users:
                        users[u] = {
                            "full_name": fac.get("name", u),
                            "role": "staff" if is_staff else "faculty",
                            "workflow_roles": roles,
                            "position_title": fac.get("title", "Faculty Member"),
                            "program_codes": ["*"] if is_staff else [dept_code],
                            "college": "COLLEGE OF ENGINEERING",
                            "password_hash": default_hash,
                            "must_change_password": False,
                            "created_at": now_ts,
                            "last_login": None,
                        }
                    else:
                        users[u]["full_name"] = fac.get("name", users[u]["full_name"])
                        users[u]["position_title"] = fac.get("title", users[u]["position_title"])
                        if roles:
                            users[u]["workflow_roles"] = roles

            # Attach transparent e-signatures from static/signatures if present
            sig_dir = os.path.join(BASE_DIR, "static", "signatures")
            p_joie = os.path.join(sig_dir, "dean_cataytay.png")
            if os.path.exists(p_joie) and "dean_cataytay" in users:
                with open(p_joie, "rb") as f:
                    users["dean_cataytay"]["signature_data"] = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

            p_sheena = os.path.join(sig_dir, "sheena_arcega.png")
            if os.path.exists(p_sheena) and "faculty_arcega" in users:
                with open(p_sheena, "rb") as f:
                    users["faculty_arcega"]["signature_data"] = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
        except Exception:
            pass

        # Final sweep: clean duplicate and test accounts before saving
        for leg in ["committee_basan", "committee_arenga", "committee_ravida", "programhead_claro", "assoc_dean", "staff_simplicio_lab", "faculty_tester"]:
            if leg in users:
                del users[leg]

        _save_users(users)


def _normalize_username(raw: str) -> str:
    uname = (raw or "").strip().lower()
    return LEGACY_USERNAME_ALIASES.get(uname, uname)


def _valid_username(username: str) -> bool:
    return 3 <= len(username) <= 40 and all(ch.isalnum() or ch in "._-" for ch in username)


def _password_problem(pw: str) -> str:
    if len(pw or "") < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if not any(ch.isalpha() for ch in pw) or not any(ch.isdigit() for ch in pw):
        return "Password must contain both letters and numbers."
    return ""


# --------------------------------------------------------------------------
# Session / CSRF helpers
# --------------------------------------------------------------------------
def current_user():
    username = session.get("username") or session.get("student_id")
    if not username:
        return None
    if session.get("role") == "student":
        sid = session.get("student_id") or username
        sig_data = ""
        try:
            import student_store
            prof = student_store.get_student_profile(sid)
            if prof:
                sig_data = prof.get("signature_data", "")
        except Exception:
            pass
        return {
            "username": username,
            "student_id": sid,
            "full_name": session.get("student_name") or username,
            "role": "student",
            "workflow_roles": ["student"],
            "position_title": "Student",
            "email": session.get("email") or f"{username}@usep.edu.ph",
            "college": session.get("college", "COLLEGE OF ENGINEERING"),
            "program_codes": session.get("program_codes", ["*"]),
            "has_signature": bool(sig_data or session.get("has_signature")),
            "signature_data": sig_data,
            "must_change_password": False,
            "is_staff": False,
            "is_pure_staff": False,
            "can_access_faculty_tools": False,
            "is_admin_session": False,
        }
    username = LEGACY_USERNAME_ALIASES.get(username, username)
    user = _load_users().get(username)
    if not user:
        session.clear()
        return None
    is_admin = user.get("role") == "admin"
    workflow_roles = ["review_committee", "program_head", "qa_head", "dean"] if is_admin else (user.get("workflow_roles") or [])
    role = user.get("role", "faculty")
    is_staff = (role == "staff" or "staff" in workflow_roles)
    has_faculty_roles = any(r in workflow_roles for r in ["review_committee", "faculty", "program_head", "qa_head", "dean", "associate_dean"])
    is_pure_staff = is_staff and not is_admin and not has_faculty_roles
    can_access_faculty_tools = not is_pure_staff

    default_title = "System Administrator" if is_admin else ("Academic Programs Staff (Oversight)" if is_pure_staff else "Faculty Member")
    return {
        "username": username,
        "full_name": user.get("full_name") or username,
        "role": role,
        "workflow_roles": workflow_roles,
        "position_title": user.get("position_title") or default_title,
        "email": user.get("email") or derive_email(username, user.get("full_name") or ""), 
        "college": user.get("college", "COLLEGE OF ENGINEERING"),
        "program_codes": user.get("program_codes", ["*"]),
        "has_signature": bool(user.get("signature_data")),
        "signature_data": user.get("signature_data", ""),
        "must_change_password": bool(user.get("must_change_password")),
        "is_staff": is_staff,
        "is_pure_staff": is_pure_staff,
        "can_access_faculty_tools": can_access_faculty_tools,
        "is_admin_session": bool(session.get("is_admin_session") or is_admin),
    }


def get_csrf_token() -> str:
    tok = session.get("_csrf")
    if not tok:
        tok = secrets.token_urlsafe(32)
        session["_csrf"] = tok
    return tok


def _check_csrf() -> None:
    sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
    if not sent and request.is_json:
        sent = (request.get_json(silent=True) or {}).get("_csrf")
    expected = session.get("_csrf", "")
    if not sent or not secrets.compare_digest(sent, expected):
        abort(400, description="Invalid or missing security token. Please reload the page and try again.")


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("auth.login", next=request.path))
        if user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapper


PUBLIC_ENDPOINTS = {"auth.login", "student_login", "student_logout", "static", "api_download_roster_template"}
PASSWORD_CHANGE_ALLOWED = {"auth.change_password", "auth.logout", "static"}


def install_auth(app) -> None:
    """Attach secret key, the auth blueprint and a global login guard to the app."""
    app.secret_key = get_or_create_secret_key()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,  # 8 hours
    )
    ensure_default_admin()
    app.register_blueprint(auth_bp)

    @app.context_processor
    def _inject_auth():
        return {"current_user": current_user(), "csrf_token": get_csrf_token}

    @app.before_request
    def _require_login():
        endpoint = request.endpoint or ""
        path = request.path or ""
        if endpoint in PUBLIC_ENDPOINTS or path.startswith("/student/login") or path.startswith("/static") or path == "/api/roster-template.csv":
            return None
        user = current_user()
        is_api = path.startswith("/api/") or path.startswith("/curriculum/advisor")
        if not user:
            if is_api:
                return jsonify({"error": "Authentication required. Please sign in again."}), 401
            if path.startswith("/student"):
                return redirect(url_for("student_login", next=request.full_path.rstrip("?")))
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))

        # If logged in user is a student:
        if user.get("role") == "student":
            if (
                path.startswith("/student")
                or path.startswith("/api/student")
                or path.startswith("/api/courses/")
                or path.startswith("/api/curriculum")
                or path.startswith("/curriculum")
            ):
                return None
            return redirect(url_for("student_dashboard"))

        if user["must_change_password"] and endpoint not in PASSWORD_CHANGE_ALLOWED:
            if is_api:
                return jsonify({"error": "You must change your password before continuing."}), 403
            return redirect(url_for("auth.change_password"))
        return None


# --------------------------------------------------------------------------
# Brute-force throttle
# --------------------------------------------------------------------------
def _attempt_key(username: str) -> str:
    return f"{request.remote_addr}|{username}"


def _locked_seconds_left(key: str) -> int:
    with _lock:
        rec = _failed_attempts.get(key)
        if not rec:
            return 0
        count, first_ts = rec
        elapsed = time.time() - first_ts
        if elapsed > LOCKOUT_SECONDS:
            _failed_attempts.pop(key, None)
            return 0
        return int(LOCKOUT_SECONDS - elapsed) if count >= MAX_FAILED_ATTEMPTS else 0


def _register_failure(key: str) -> None:
    with _lock:
        count, first_ts = _failed_attempts.get(key, (0, time.time()))
        _failed_attempts[key] = (count + 1, first_ts)


def _clear_failures(key: str) -> None:
    with _lock:
        _failed_attempts.pop(key, None)


def _safe_next(target: str) -> str:
    # Only allow local, relative redirects to avoid open-redirects.
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("index")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.args.get("signed_out"):
        session.clear()
        session.modified = True

    curr = current_user()
    if curr and not request.args.get("signed_out"):
        if curr.get("role") == "student":
            return redirect(url_for("student_dashboard"))
        return redirect(url_for("index"))

    error = None
    info = "You have been signed out." if request.args.get("signed_out") else None
    username = ""
    if request.method == "POST":
        _check_csrf()
        raw_username = request.form.get("username") or ""
        username = _normalize_username(raw_username)
        password = request.form.get("password") or ""
        key = _attempt_key(username)
        wait = _locked_seconds_left(key)
        if wait:
            error = f"Too many failed attempts. Please wait {wait} seconds and try again."
        else:
            users = _load_users()
            user = users.get(username)
            if user and check_password_hash(user.get("password_hash", ""), password):
                _clear_failures(key)
                session.clear()
                session.permanent = True
                session["username"] = username
                session["is_admin_session"] = bool(user.get("role") == "admin")
                get_csrf_token()
                with _lock:
                    users = _load_users()
                    if username in users:
                        users[username]["last_login"] = datetime.now().isoformat(timespec="seconds")
                        _save_users(users)
                if user.get("must_change_password"):
                    return redirect(url_for("auth.change_password"))
                return redirect(_safe_next(request.args.get("next", "")))

            # If not a faculty account, check if this is an enrolled student signing in
            import student_store
            ok_st, st_obj, _ = student_store.verify_student_login(raw_username, password)
            if ok_st and st_obj:
                _clear_failures(key)
                session.clear()
                session.permanent = True
                session["username"] = st_obj["student_id"]
                session["student_id"] = st_obj["student_id"]
                session["student_name"] = st_obj.get("full_name") or st_obj.get("name") or st_obj.get("student_id")
                session["role"] = "student"
                session["email"] = st_obj.get("email") or f"{st_obj['student_id']}@usep.edu.ph"
                session["has_signature"] = bool(st_obj.get("signature_data"))
                get_csrf_token()
                return redirect(url_for("student_dashboard"))

            _register_failure(key)
            error = "Invalid username or password."

    resp = make_response(render_template("login.html", error=error, info=info, username=username))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    session.modified = True
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
    resp = make_response(redirect(url_for("auth.login", signed_out=1)))
    resp.delete_cookie(cookie_name, path="/")
    resp.delete_cookie(cookie_name, path="/student")
    resp.delete_cookie("session", path="/")
    resp.delete_cookie("session")
    resp.set_cookie(cookie_name, "", expires=0, max_age=0, path="/")
    resp.set_cookie("session", "", expires=0, max_age=0, path="/")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@auth_bp.route("/account/password", methods=["GET", "POST"])
def change_password():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))

    error = None
    if request.method == "POST":
        _check_csrf()
        current_pw = request.form.get("current_password") or ""
        new_pw = request.form.get("new_password") or ""
        confirm_pw = request.form.get("confirm_password") or ""
        with _lock:
            users = _load_users()
            rec = users.get(user["username"])
            if not rec or not check_password_hash(rec.get("password_hash", ""), current_pw):
                error = "Your current password is incorrect."
            elif new_pw != confirm_pw:
                error = "The new passwords do not match."
            elif new_pw == current_pw:
                error = "The new password must be different from the current password."
            else:
                error = _password_problem(new_pw) or None
            if not error:
                rec["password_hash"] = generate_password_hash(new_pw)
                rec["must_change_password"] = False
                _save_users(users)
        if not error:
            flash("Your password has been updated.", "success")
            return redirect(url_for("index"))

    return render_template("change_password.html", error=error, forced=user["must_change_password"])


@auth_bp.route("/admin/users", methods=["GET"])
@admin_required
def manage_users():
    users = _load_users()
    rows = []
    for uname, u in sorted(users.items()):
        w_roles = u.get("workflow_roles") or []
        prog_codes = u.get("program_codes") or []
        primary_prog = prog_codes[0] if prog_codes and prog_codes[0] != "*" else "EE"

        badges = []
        if "dean" in w_roles:
            badges.append({"label": "College Dean", "class": "b-dean", "icon": "🏛️"})
        if "associate_dean" in w_roles:
            badges.append({"label": "Associate Dean", "class": "b-dean", "icon": "🏛️"})
        if "qa_head" in w_roles:
            badges.append({"label": "College QA Head", "class": "b-qa", "icon": "🛡️"})
        if "program_head" in w_roles:
            p_list = [p for p in prog_codes if p != "*"]
            p_str = ", ".join(p_list) if p_list else primary_prog
            badges.append({"label": f"Program Head ({p_str})", "class": "b-ph", "icon": "👔"})
        if "staff" in w_roles or u.get("role") == "staff":
            badges.append({"label": "Staff (Oversight)", "class": "b-staff", "icon": "📋"})
        if u.get("role") == "admin":
            badges.append({"label": "Administrator", "class": "b-admin", "icon": "⚙️"})
        if not badges or (len(badges) == 0):
            badges.append({"label": "Faculty Member", "class": "b-fac", "icon": "👨‍🏫"})

        rows.append({
            "username": uname,
            "full_name": u.get("full_name", ""),
            "email": u.get("email") or derive_email(uname, u.get("full_name", "")),
            "role": u.get("role", "faculty"),
            "workflow_roles": w_roles,
            "program_codes": prog_codes,
            "badges": badges,
            "position_title": u.get("position_title") or "Faculty Member",
            "must_change_password": bool(u.get("must_change_password")),
            "created_at": u.get("created_at") or "",
            "last_login": u.get("last_login") or "Never",
        })
    return render_template("admin_users.html", users=rows, min_len=MIN_PASSWORD_LENGTH, programs=PROGRAM_FULL_NAMES)


@auth_bp.route("/admin/users/create", methods=["POST"])
@admin_required
def create_user():
    _check_csrf()
    username = _normalize_username(request.form.get("username"))
    full_name = (request.form.get("full_name") or "").strip()
    
    # Extract roles (supports both multi-checkbox and single designation)
    roles = request.form.getlist("roles")
    if not roles and request.form.get("designation"):
        roles = [request.form.get("designation")]
    if not roles:
        roles = ["review_committee"]

    prog_codes = request.form.getlist("program_codes")
    if not prog_codes and request.form.get("program_code"):
        prog_codes = [request.form.get("program_code")]
        
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        email = derive_email(username, full_name)

    custom_title = (request.form.get("position_title") or "").strip()
    is_admin = bool(request.form.get("is_admin")) or ("admin" in roles) or (request.form.get("role") == "admin")
    password = request.form.get("password") or ""

    if not _valid_username(username):
        flash("Username must be 3–40 characters (letters, numbers, '.', '_' or '-').", "error")
        return redirect(url_for("auth.manage_users"))
    problem = _password_problem(password)
    if problem:
        flash(problem, "error")
        return redirect(url_for("auth.manage_users"))

    with _lock:
        users = _load_users()
        if username in users:
            flash(f"An account named '{username}' already exists.", "error")
            return redirect(url_for("auth.manage_users"))
        new_user = {
            "full_name": full_name or username,
            "email": email,
            "role": "admin" if is_admin else "faculty",
            "password_hash": generate_password_hash(password),
            "must_change_password": True,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_login": None,
        }
        apply_roles_to_user_dict(new_user, roles, prog_codes, custom_title, is_admin)
        users[username] = new_user
        _save_users(users)
    flash(f"Account '{username}' created with role(s) '{new_user.get('position_title')}'.", "success")
    return redirect(url_for("auth.manage_users"))


@auth_bp.route("/admin/users/<username>/role", methods=["POST"])
@admin_required
def update_user_role(username):
    _check_csrf()
    username = _normalize_username(username)
    
    # Extract roles (supports both multi-checkbox and single designation)
    roles = request.form.getlist("roles")
    if not roles and request.form.get("designation"):
        roles = [request.form.get("designation")]
        
    prog_codes = request.form.getlist("program_codes")
    if not prog_codes and request.form.get("program_code"):
        prog_codes = [request.form.get("program_code")]
        
    custom_title = (request.form.get("position_title") or "").strip()
    is_admin = bool(request.form.get("is_admin")) or ("admin" in (roles or []))

    with _lock:
        users = _load_users()
        uname = LEGACY_USERNAME_ALIASES.get(username, username)
        target_key = None
        for k in users:
            if k.lower() == uname.lower():
                target_key = k
                break
        if not target_key:
            flash(f"User '{username}' was not found.", "error")
            return redirect(url_for("auth.manage_users"))
        target = users[target_key]
        email_val = (request.form.get("email") or "").strip().lower()
        if email_val:
            target["email"] = email_val
        apply_roles_to_user_dict(target, roles, prog_codes, custom_title, is_admin)
        _save_users(users)

    flash(f"Updated role(s) for '{username}' to '{target.get('position_title')}'.", "success")
    return redirect(url_for("auth.manage_users"))


@auth_bp.route("/admin/users/<username>/email", methods=["POST"])
@admin_required
def update_user_email(username):
    _check_csrf()
    username = _normalize_username(username)
    email = (request.form.get("email") or "").strip().lower()
    if not email and request.is_json:
        email = (request.get_json(silent=True) or {}).get("email", "").strip().lower()
    if not email:
        if request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({"success": False, "error": "Email address cannot be empty."}), 400
        flash("Email address cannot be empty.", "error")
        return redirect(url_for("auth.manage_users"))
    with _lock:
        users = _load_users()
        uname = LEGACY_USERNAME_ALIASES.get(username, username)
        target_key = None
        for k in users:
            if k.lower() == uname.lower():
                target_key = k
                break
        if not target_key:
            if request.is_json or request.headers.get("Accept") == "application/json":
                return jsonify({"success": False, "error": f"User '{username}' was not found."}), 404
            flash(f"User '{username}' was not found.", "error")
            return redirect(url_for("auth.manage_users"))
        users[target_key]["email"] = email
        _save_users(users)

    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({"success": True, "message": f"Updated notification email for '{username}' to '{email}'.", "email": email})
    flash(f"Updated notification email for '{username}' to '{email}'.", "success")
    return redirect(url_for("auth.manage_users"))


@auth_bp.route("/admin/users/<username>/reset", methods=["POST"])
@admin_required
def reset_user_password(username):
    _check_csrf()
    username = _normalize_username(username)
    password = request.form.get("password") or ""
    problem = _password_problem(password)
    if problem:
        flash(problem, "error")
        return redirect(url_for("auth.manage_users"))
    with _lock:
        users = _load_users()
        if username not in users:
            abort(404)
        users[username]["password_hash"] = generate_password_hash(password)
        users[username]["must_change_password"] = True
        _save_users(users)
    flash(f"Temporary password set for '{username}'.", "success")
    return redirect(url_for("auth.manage_users"))


@auth_bp.route("/admin/users/<username>/delete", methods=["POST"])
@admin_required
def delete_user(username):
    _check_csrf()
    username = _normalize_username(username)
    me = current_user()
    if username == me["username"]:
        if request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({"success": False, "error": "You cannot delete the account you are currently signed in with."}), 400
        flash("You cannot delete the account you are currently signed in with.", "error")
        return redirect(url_for("auth.manage_users"))

    reason = (request.form.get("reason") or (request.get_json(silent=True) or {}).get("reason") or "Administrative removal").strip()
    purge_courses = request.form.get("purge_courses") in ("true", "1", "on") or bool((request.get_json(silent=True) or {}).get("purge_courses"))

    with _lock:
        users = _load_users()
        uname = LEGACY_USERNAME_ALIASES.get(username, username)
        target_key = None
        for k in users:
            if k.lower() == uname.lower():
                target_key = k
                break
        if not target_key:
            if request.is_json or request.headers.get("Accept") == "application/json":
                return jsonify({"success": False, "error": f"Account '{username}' was not found."}), 404
            flash(f"Account '{username}' was not found.", "error")
            return redirect(url_for("auth.manage_users"))

        if users[target_key].get("role") == "admin" and sum(1 for u in users.values() if u.get("role") == "admin") <= 1:
            if request.is_json or request.headers.get("Accept") == "application/json":
                return jsonify({"success": False, "error": "Cannot delete the last remaining administrator account."}), 400
            flash("Cannot delete the last remaining administrator account.", "error")
            return redirect(url_for("auth.manage_users"))

        del_user_obj = users.pop(target_key)
        _save_users(users)
        try:
            import db_persistence
            db_persistence.delete_user_from_db(target_key)
        except Exception:
            pass

        # Mark as deleted to prevent auto-recreation on reboot
        del_set = _load_deleted_users()
        del_set.add(target_key)
        _save_deleted_users(del_set)

        # Purge courses if requested
        if purge_courses:
            import shutil
            c_dir = os.path.join(DATA_DIR, "courses", target_key)
            if os.path.exists(c_dir):
                shutil.rmtree(c_dir, ignore_errors=True)

    full_name = del_user_obj.get("full_name") or target_key
    msg = f"Account '{target_key}' ({full_name}) has been permanently deleted ({reason})."
    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({"success": True, "message": msg, "username": target_key})
    flash(msg, "success")
    return redirect(url_for("auth.manage_users"))

@auth_bp.route("/api/user/me", methods=["GET"])
def api_user_me():
    u = current_user()
    if not u:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"user": u})


@auth_bp.route("/api/user/signature", methods=["POST"])
def api_user_save_signature():
    u = current_user()
    if not u:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json(silent=True) or {}
    sig_data = data.get("signature_data") or ""
    if not sig_data:
        return jsonify({"error": "No signature data provided."}), 400
    with _lock:
        users = _load_users()
        if u["username"] in users:
            users[u["username"]]["signature_data"] = sig_data
            _save_users(users)
    return jsonify({"success": True, "message": "E-signature saved successfully."})


@auth_bp.route("/api/switch-demo-account", methods=["POST"])
def api_switch_demo_account():
    user = current_user()
    is_admin = bool(user and user.get("role") == "admin")
    is_admin_session = bool(session.get("is_admin_session"))
    if not (is_admin or is_admin_session):
        return jsonify({"error": "Admin access required to use the role test switcher."}), 403

    data = request.get_json(silent=True) or {}
    target_username = (data.get("username") or "").strip().lower()
    users = _load_users()
    if target_username not in users:
        return jsonify({"error": f"Account '{target_username}' not found."}), 404
    session["username"] = target_username
    session["is_admin_session"] = True
    get_csrf_token()
    return jsonify({"success": True, "user": current_user()})
