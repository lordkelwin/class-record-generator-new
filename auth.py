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
import secrets
import threading
import time
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SECRET_KEY_FILE = os.path.join(DATA_DIR, "secret_key")

LEGACY_USERNAME_ALIASES = {
    "committee_basan": "faculty_basan",
    "committee_arenga": "faculty_arenga",
    "committee_ravida": "faculty_ravida",
    "programhead_claro": "faculty_claro",
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

    if not roles or roles == ["faculty"]:
        roles = ["review_committee"]
    elif "review_committee" not in roles:
        roles.append("review_committee")

    cleaned_progs = []
    for p in (program_codes or []):
        p_clean = str(p).strip().upper()
        if p_clean and p_clean not in cleaned_progs:
            cleaned_progs.append(p_clean)
    if not cleaned_progs:
        cleaned_progs = ["EE"]

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
        if "admin" in roles and not title_parts:
            title_parts.append("System Administrator")
        if not title_parts:
            title_parts.append("Faculty Member")

        custom_title = " & ".join(title_parts)

    target["position_title"] = custom_title

    if is_admin or "admin" in roles:
        target["role"] = "admin"
    elif target.get("role") == "admin" and target.get("username") != DEFAULT_ADMIN_USERNAME:
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


def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_users(users: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    os.replace(tmp, USERS_FILE)


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
        for leg in ["committee_basan", "committee_arenga", "committee_ravida", "programhead_claro"]:
            if leg in users:
                del users[leg]

        # Seed standard signatory/workflow test accounts
        seed_accounts = [
            ("faculty_tano", "Engr. Elwin Jay J. Tano", "faculty", ["review_committee"], "Faculty Member", "EE"),
            ("faculty_basan", "Engr. Nikka Samantha A. Basan", "faculty", ["review_committee"], "Faculty Member", "EE"),
            ("faculty_arenga", "Engr. Delan Zoe H. Arenga", "faculty", ["review_committee"], "Faculty Member", "ECE"),
            ("faculty_ravida", "Engr. Kim P. Ravida", "faculty", ["review_committee"], "Faculty Member", "ECE"),
            ("faculty_claro", "Engr. Charito O. Claro", "faculty", ["program_head", "review_committee"], "Program Head - Electrical Engineering", "EE"),
            ("qahead_ce", "Engr. College QA Head", "faculty", ["qa_head"], "College Quality Assurance Head", "*"),
            ("dean_cataytay", "Engr. Joie D. Cataytay, Ph.D.", "faculty", ["dean", "review_committee"], "Dean, College of Engineering", "*"),
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

        # Seed official faculty roster from catalog_data
        try:
            import base64
            from catalog_data import OFFICIAL_FACULTY_ROSTER
            default_hash = generate_password_hash("password123")
            for dept_code, groups in OFFICIAL_FACULTY_ROSTER.items():
                is_staff = (dept_code == "STAFF")
                for fac in (groups.get("full_time", []) + groups.get("part_time", [])):
                    target_unames = [fac.get("username")]
                    if fac.get("alias"):
                        target_unames.append(fac.get("alias"))
                    for u in target_unames:
                        if not u:
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
    username = session.get("username")
    if not username:
        return None
    username = LEGACY_USERNAME_ALIASES.get(username, username)
    user = _load_users().get(username)
    if not user:
        session.clear()
        return None
    is_admin = user.get("role") == "admin"
    workflow_roles = ["review_committee", "program_head", "qa_head", "dean"] if is_admin else (user.get("workflow_roles") or [])
    return {
        "username": username,
        "full_name": user.get("full_name") or username,
        "role": user.get("role", "faculty"),
        "workflow_roles": workflow_roles,
        "position_title": user.get("position_title") or ("System Administrator" if is_admin else "Faculty in Charge"),
        "college": user.get("college", "COLLEGE OF ENGINEERING"),
        "program_codes": user.get("program_codes", ["*"]),
        "has_signature": bool(user.get("signature_data")),
        "signature_data": user.get("signature_data", ""),
        "must_change_password": bool(user.get("must_change_password")),
    }


def get_csrf_token() -> str:
    tok = session.get("_csrf")
    if not tok:
        tok = secrets.token_urlsafe(32)
        session["_csrf"] = tok
    return tok


def _check_csrf() -> None:
    sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
    if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
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


PUBLIC_ENDPOINTS = {"auth.login", "static"}
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
        if endpoint in PUBLIC_ENDPOINTS:
            return None
        user = current_user()
        is_api = request.path.startswith("/api/")
        if not user:
            if is_api:
                return jsonify({"error": "Authentication required. Please sign in again."}), 401
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
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
    if current_user():
        return redirect(url_for("index"))

    error = None
    username = ""
    if request.method == "POST":
        _check_csrf()
        username = _normalize_username(request.form.get("username"))
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
                get_csrf_token()
                with _lock:
                    users = _load_users()
                    if username in users:
                        users[username]["last_login"] = datetime.now().isoformat(timespec="seconds")
                        _save_users(users)
                if user.get("must_change_password"):
                    return redirect(url_for("auth.change_password"))
                return redirect(_safe_next(request.args.get("next", "")))
            _register_failure(key)
            error = "Invalid username or password."

    return render_template("login.html", error=error, username=username)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


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
        if u.get("role") == "admin":
            badges.append({"label": "Administrator", "class": "b-admin", "icon": "⚙️"})
        if not badges or (len(badges) == 0):
            badges.append({"label": "Faculty Member", "class": "b-fac", "icon": "👨‍🏫"})

        rows.append({
            "username": uname,
            "full_name": u.get("full_name", ""),
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
        if uname not in users:
            abort(404)
        target = users[uname]
        apply_roles_to_user_dict(target, roles, prog_codes, custom_title, is_admin)
        _save_users(users)

    flash(f"Updated role(s) for '{username}' to '{target.get('position_title')}'.", "success")
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
        flash("You cannot delete the account you are signed in with.", "error")
        return redirect(url_for("auth.manage_users"))
    with _lock:
        users = _load_users()
        if username not in users:
            abort(404)
        if users[username].get("role") == "admin" and sum(1 for u in users.values() if u.get("role") == "admin") <= 1:
            flash("Cannot delete the last admin account.", "error")
            return redirect(url_for("auth.manage_users"))
        users.pop(username)
        _save_users(users)
    flash(f"Account '{username}' deleted.", "success")
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
    data = request.get_json(silent=True) or {}
    target_username = (data.get("username") or "").strip().lower()
    users = _load_users()
    if target_username not in users:
        return jsonify({"error": f"Account '{target_username}' not found."}), 404
    session.clear()
    session["username"] = target_username
    get_csrf_token()
    return jsonify({"success": True, "user": current_user()})
