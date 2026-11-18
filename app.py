import config
import copy
import syllabus_workflow
import class_record_workflow
import oversight_report_generator

from syllabus_evaluation_form import (

    FORM_INFO, CORE_EVALUATION_STATEMENTS, FRAMEWORK_INTEGRATION_AREAS,

    ANNEX_A_SECTIONS, generate_syllabus_evaluation_pdf

)

import io

import os
import secrets

import re

import tempfile

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from flask import Flask, render_template, request, jsonify, send_file, Response, session, redirect, url_for, flash, make_response
from werkzeug.middleware.proxy_fix import ProxyFix







from models import SyllabusBlueprint, StudentRecord, build_transmutation_table

from sample_syllabus import get_default_blueprint, generate_sample_syllabus_pdf

from syllabus_parser import analyze_syllabus_pdf

from excel_generator import generate_class_record_workbook

from catalog_data import get_full_catalog, OFFICIAL_FACULTY_ROSTER

from syllabus_pdf_generator import generate_usep_syllabus_pdf

from clo_report_pdf_generator import generate_clo_report_pdf_bytes
from clo_evaluation_excel_generator import generate_clo_evaluation_excel_bytes

import auth

from auth import install_auth, current_user

import courses_store

# Authoritative BSEE curriculum sync directly from PGO-PI-IGA.accdb via SQL
try:
    import accdb_curriculum
    accdb_curriculum.sync_accdb_to_catalog_and_db()
except Exception as _e:
    logging.getLogger(__name__).warning(f"Could not sync accdb curriculum on startup: {_e}")

# Automatic sync & backfill of all enrolled students into Student Portal authentication store
try:
    import student_store
    student_store.sync_all_course_students_to_store()
except Exception as _e:
    logging.getLogger(__name__).warning(f"Could not sync student store on startup: {_e}")







app = Flask(__name__)
# Trust X-Forwarded-* headers from Firebase Hosting / Cloud Run reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route("/api/health", methods=["GET"])
@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({
        "status": "ok",
        "use_firebase": bool(getattr(config, "USE_FIREBASE", False)),
        "project_id": getattr(config, "FIREBASE_PROJECT_ID", ""),
    }), 200

@app.after_request
def add_cache_control_headers(response):
    if not request.path.startswith(("/static/", "/fonts/")):
        response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        existing_vary = response.headers.get("Vary", "")
        vary_tokens = [v.strip() for v in existing_vary.split(",") if v.strip()]
        if "Cookie" not in vary_tokens:
            vary_tokens.append("Cookie")
            response.headers["Vary"] = ", ".join(vary_tokens)
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, X-CSRF-Token, _csrf"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

from functools import wraps

def faculty_tools_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if u and not u.get("can_access_faculty_tools", True):
            return jsonify({"error": "Staff accounts have oversight access only and cannot create or edit course syllabi."}), 403
        return fn(*args, **kwargs)
    return wrapper


# Login screen, faculty accounts (admin-managed) and a global login guard for every page/API

install_auth(app)

# Environment-aware session cookies: HTTPS secure cookies behind Cloud Run / Firebase Hosting proxy,
# and non-secure HTTP cookies on local development / LAN testing.
_is_https_prod = bool(
    os.environ.get("K_SERVICE")
    or os.environ.get("FORCE_HTTPS_COOKIES", "").lower() in ("1", "true", "yes")
    or os.environ.get("FLASK_ENV") == "production"
)
app.config["SESSION_COOKIE_NAME"] = "__session"
app.config["REMEMBER_COOKIE_NAME"] = "__session_remember"
app.config["SESSION_COOKIE_SECURE"] = _is_https_prod
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SERVER_NAME"] = None







BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EE211_PDF_PATH = os.path.join(BASE_DIR, "EE 211.pdf")

SAMPLE_PDF_PATH = EE211_PDF_PATH if os.path.exists(EE211_PDF_PATH) else os.path.join(BASE_DIR, "samples", "EE211_OBE_Course_Syllabus.pdf")

EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

os.makedirs(os.path.join(BASE_DIR, "samples"), exist_ok=True)

os.makedirs(EXPORTS_DIR, exist_ok=True)
try:
    import db_persistence
    db_persistence.migrate_all_from_json()
except Exception as _e:
    print(f"Database migration notice: {_e}")











@app.context_processor
def inject_current_user():
    return dict(current_user=current_user())

@app.route("/")
def index():
    user = current_user()
    default_tab = "syllabus"
    if user:
        req_tab = request.args.get("tab")
        if req_tab == "pgo-assessment" and user.get("role") != "student":
            default_tab = "pgo-assessment"
        elif not user.get("can_access_faculty_tools", True):
            default_tab = req_tab if req_tab in {"approvals", "curriculum", "pgo-assessment"} else "approvals"
        else:
            username = user.get("username", "")
            courses_data = courses_store.list_courses(username, user.get("full_name") or "")
            courses = courses_data.get("courses", [])
            has_unlocked_dashboard = any(bool(c.get("is_approved") and c.get("has_recorded_scores")) for c in courses)
            if req_tab == "dashboard":
                default_tab = "dashboard" if has_unlocked_dashboard else "syllabus"
            elif req_tab in {"syllabus", "approvals", "curriculum", "pgo-assessment"}:
                default_tab = req_tab
            else:
                default_tab = "dashboard" if has_unlocked_dashboard else "syllabus"
    return render_template("index.html", default_tab=default_tab)


@app.route("/dashboard")
def dashboard_view():
    user = current_user()
    if not user:
        return redirect(url_for("auth_login", next="/dashboard"))
    if not user.get("can_access_faculty_tools", True):
        return redirect(url_for("index", tab="approvals"))
    username = user.get("username", "")
    courses_data = courses_store.list_courses(username, user.get("full_name") or "")
    courses = courses_data.get("courses", [])
    has_unlocked_dashboard = any(bool(c.get("is_approved") and c.get("has_recorded_scores")) for c in courses)
    if not has_unlocked_dashboard:
        return redirect(url_for("index", tab="syllabus"))
    return redirect(url_for("index", tab="dashboard"))











@app.route("/api/catalog", methods=["GET"])

def api_catalog():

    return jsonify(get_full_catalog())


@app.route("/api/faculty-roster", methods=["GET"])
def api_faculty_roster():
    return jsonify(OFFICIAL_FACULTY_ROSTER)


@app.route("/api/db/programs", methods=["GET"])
def api_db_programs():
    import academic_db
    return jsonify(academic_db.get_all_programs())


@app.route("/api/db/courses", methods=["GET"])
def api_db_courses():
    import academic_db
    prog = request.args.get("program", "BSEE")
    yr = request.args.get("year_level")
    return jsonify(academic_db.get_courses_by_program(prog, yr))


@app.route("/api/db/courses/<course_code>", methods=["GET"])
def api_db_course(course_code):
    import academic_db
    prog = request.args.get("program")
    c = academic_db.get_course(course_code, prog)
    if not c:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(c)


@app.route("/api/db/faculty", methods=["GET"])
def api_db_faculty():
    import academic_db
    dept = request.args.get("department") or request.args.get("dept")
    return jsonify(academic_db.get_all_faculty(dept))


@app.route("/api/db/search-courses", methods=["GET"])
def api_db_search_courses():
    import academic_db
    query = request.args.get("q", "").strip()
    prog = request.args.get("program")
    return jsonify(academic_db.search_courses(query, prog))


@app.route("/api/curriculum/flowchart", methods=["GET"])
def api_curriculum_flowchart():
    import curriculum_flowchart
    program = request.args.get("program", "BSEE")
    data = curriculum_flowchart.get_curriculum_flowchart_data(program)
    return jsonify(data)


@app.route("/api/curriculum/course-details", methods=["GET"])
def api_curriculum_course_details():
    import curriculum_flowchart
    code = request.args.get("course_code") or request.args.get("code")
    program = request.args.get("program", "BSEE")
    if not code:
        return jsonify({"error": "course_code is required"}), 400
    details = curriculum_flowchart.get_course_details(code, program)
    if not details:
        return jsonify({"error": f"Course '{code}' not found"}), 404
    return jsonify(details)


@app.route("/api/curriculum/pgo-pi-list", methods=["GET"])
def api_curriculum_pgo_pi_list():
    import accdb_curriculum
    tree = accdb_curriculum.get_accdb_pgo_pi_tree()
    return jsonify(tree)


@app.route("/api/curriculum/advisor", methods=["GET", "POST"], strict_slashes=False)
@app.route("/api/curriculum/advisor/", methods=["GET", "POST"], strict_slashes=False)
@app.route("/curriculum/advisor", methods=["GET", "POST"], strict_slashes=False)
@app.route("/curriculum/advisor/", methods=["GET", "POST"], strict_slashes=False)
def api_curriculum_advisor():
    import curriculum_advisor
    if request.method == "GET":
        query = str(request.args.get("query") or "").strip()
        program = str(request.args.get("program") or "BSEE").strip() or "BSEE"
        history = []
    else:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = request.form.to_dict() if request.form else {}
        query = str(payload.get("query") or request.args.get("query") or "").strip()
        program = str(payload.get("program") or request.args.get("program") or "BSEE").strip() or "BSEE"
        history = payload.get("history")
        if not isinstance(history, list):
            history = []

    if not query:
        return jsonify({
            "success": True,
            "intent": "empty_query",
            "advice_markdown": "Please enter a question about your curriculum, prerequisites, or failed course scenario (e.g., *'What courses can I take next semester if I failed EE 211?'*).",
            "highlight_action": {"blocked": [], "eligible": [], "retake": []}
        }), 200

    try:
        res = curriculum_advisor.query_curriculum_guide_agent(query, program_code=program, history=history)
    except Exception as exc:
        app.logger.exception("Curriculum advisor endpoint failure: %s", exc)
        res = {
            "success": True,
            "intent": "engine_fallback",
            "advice_markdown": "⚠️ I couldn't analyze that question right now. Please mention a specific course code (e.g., *'What happens if I fail EE 211?'*).",
            "highlight_action": {"blocked": [], "eligible": [], "retake": []}
        }
    return jsonify(res)












@app.route("/api/default-blueprint", methods=["GET"])

def api_default_blueprint():

    include_scores = request.args.get("scores", "1") == "1"

    bp = get_default_blueprint(include_sample_scores=include_scores)

    return jsonify({

        "blueprint": bp.to_dict(),

        "transmutation": build_transmutation_table(bp.metadata.passing_percentage),

    })











@app.route("/api/download-sample-pdf", methods=["GET"])

def api_download_sample_pdf():

    target_pdf = EE211_PDF_PATH if os.path.exists(EE211_PDF_PATH) else SAMPLE_PDF_PATH

    if not os.path.exists(target_pdf):

        generate_sample_syllabus_pdf(target_pdf)

    return send_file(

        target_pdf,

        as_attachment=True,

        download_name="EE_211_Course_Syllabus.pdf",

        mimetype="application/pdf",

    )











@app.route("/api/analyze-pdf", methods=["POST"])

@faculty_tools_required
def api_analyze_pdf():

    use_sample = request.form.get("use_sample", "false").lower() == "true"

    use_ai = request.form.get("use_ai", "false").lower() == "true"

    gemini_api_key = request.form.get("gemini_api_key", "").strip()

    include_students = request.form.get("include_students", "true").lower() == "true"







    if use_sample:

        if not os.path.exists(SAMPLE_PDF_PATH):

            generate_sample_syllabus_pdf(SAMPLE_PDF_PATH)

        bp = analyze_syllabus_pdf(

            SAMPLE_PDF_PATH,

            use_ai=use_ai,

            gemini_api_key=gemini_api_key,

            include_sample_students=include_students,

        )

        return jsonify({

            "blueprint": bp.to_dict(),

            "transmutation": build_transmutation_table(bp.metadata.passing_percentage),

        })







    if "file" not in request.files or not request.files["file"].filename:

        return jsonify({"error": "Please select a PDF syllabus file to upload."}), 400







    uploaded = request.files["file"]

    suffix = os.path.splitext(uploaded.filename)[1].lower() or ".pdf"

    if suffix != ".pdf":

        return jsonify({"error": "Only PDF (.pdf) syllabus files are supported."}), 400







    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:

        uploaded.save(tmp.name)

        tmp_path = tmp.name







    try:

        bp = analyze_syllabus_pdf(

            tmp_path,

            use_ai=use_ai,

            gemini_api_key=gemini_api_key,

            include_sample_students=include_students,

        )

        return jsonify({

            "blueprint": bp.to_dict(),

            "transmutation": build_transmutation_table(bp.metadata.passing_percentage),

        })

    finally:

        if os.path.exists(tmp_path):

            try:

                os.remove(tmp_path)

            except OSError:

                pass











@app.route("/api/import-roster", methods=["POST"])

@faculty_tools_required
def api_import_roster():

    if "file" not in request.files or not request.files["file"].filename:

        return jsonify({"error": "No roster file uploaded."}), 400







    f = request.files["file"]

    ext = os.path.splitext(f.filename)[1].lower()

    try:

        if ext == ".csv":

            df = pd.read_csv(f)

        elif ext in (".xlsx", ".xls"):

            df = pd.read_excel(f)

        else:

            return jsonify({"error": "Unsupported file type. Upload a .csv or .xlsx student roster."}), 400







        df.columns = [str(c).strip().lower() for c in df.columns]

        students = []

        for idx, row in df.iterrows():

            sid = str(row.get("student_id", row.get("id", row.get("student no", f"2026-{1001 + idx}")))).strip()

            last = str(row.get("last_name", row.get("lastname", row.get("surname", "")))).strip()

            first = str(row.get("first_name", row.get("firstname", row.get("given name", "")))).strip()

            if not last and "name" in df.columns:

                full = str(row.get("name", "")).strip()

                if "," in full:

                    parts = full.split(",", 1)

                    last, first = parts[0].strip(), parts[1].strip()

                else:

                    parts = full.split()

                    last = parts[-1] if parts else ""

                    first = " ".join(parts[:-1]) if len(parts) > 1 else full

            prog = str(row.get("program_year", row.get("section", row.get("program", "BSEE-3")))).strip()

            if last or first:

                students.append(

                    StudentRecord(

                        student_id=sid,

                        last_name=last,

                        first_name=first,

                        program_year=prog,

                        scores={},

                    ).__dict__

                )

        return jsonify({"students": students, "count": len(students)})

    except Exception as e:

        return jsonify({"error": f"Failed to parse student roster: {e}"}), 400











@app.route("/api/transmutation", methods=["POST"])

def api_transmutation():

    data = request.get_json(silent=True) or {}

    passing_pct = float(data.get("passing_percentage", 75.0))

    return jsonify({"transmutation": build_transmutation_table(passing_pct)})











@app.route("/api/export-syllabus-pdf", methods=["POST"])

@faculty_tools_required
def api_export_syllabus_pdf():

    data = request.get_json(silent=True)

    if not data or "blueprint" not in data:

        return jsonify({"error": "Missing syllabus blueprint data."}), 400







    bp = SyllabusBlueprint.from_dict(data["blueprint"])

    c_id = data.get("course_id")

    doc = courses_store.find_course(c_id) if c_id else None

    pdf_bytes = generate_usep_syllabus_pdf(bp, doc)







    safe_code = re.sub(r"[^A-Za-z0-9_-]+", "_", bp.metadata.course_code.strip()) or "Course"

    filename = f"{safe_code}_OBE_Course_Syllabus.pdf"







    local_out = os.path.join(EXPORTS_DIR, filename)

    with open(local_out, "wb") as f_out:

        f_out.write(pdf_bytes)







    return send_file(

        io.BytesIO(pdf_bytes),

        as_attachment=True,

        download_name=filename,

        mimetype="application/pdf",

    )











def check_syllabus_approved_for_step(doc, step_num=2):
    """
    Validates sequential step-gating: Steps 2 through 8 remain strictly locked
    until the Course Syllabus (Step 1) receives final approval from the Dean.
    Returns (jsonify(...), 403) error response if locked, or None if unlocked/allowed.
    Student roster and enrollment actions are strictly exempt from sequential gating.
    """
    if not doc or not isinstance(doc, dict):
        return None
    # Student roster and enrollment management are 100% exempt from sequential gating at ALL stages
    if str(step_num).lower() in ("roster", "student", "students", "enrollment", "acknowledgment", "acknowledgement"):
        return None
    user = current_user()
    if user and user.get("role") == "admin":
        return None
    wf = doc.get("workflow")
    if not wf:
        return None
    import syllabus_workflow
    if not syllabus_workflow.is_approved(doc):
        step_names = {
            "gantt": "Step 3: Course Delivery Gantt Chart",
            "tos": "Step 6: Table of Specifications (TOS)",
            2: "Step 2: Course Assessments Setup",
            3: "Step 3: Course Delivery Gantt Chart",
            4: "Step 4: Class Record & Gradebook",
            5: "Step 5: Receipt of Scores & Paper",
            6: "Step 6: Table of Specifications (TOS)",
            7: "Step 7: CLO Assessment Report (FM-USeP-MID-10)",
            8: "Step 8: Continuous Quality Improvement (CQI) Plan",
        }
        name = step_names.get(step_num, f"Step {step_num}")
        return jsonify({
            "error": f"Sequential Gating Locked: {name} is locked. The course syllabus (Step 1) must receive final approval from the Dean before accessing or modifying subsequent steps.",
            "is_locked": True,
            "step": step_num,
            "requires_dean_approval": True,
        }), 403
    return None


@app.route("/api/export-clo-report-pdf", methods=["POST"])
@faculty_tools_required
def api_export_clo_report_pdf():
    data = request.get_json(silent=True)
    if not data or "blueprint" not in data:
        return jsonify({"error": "Missing syllabus blueprint data."}), 400

    bp = SyllabusBlueprint.from_dict(data["blueprint"])
    doc = data.get("doc") or {}
    course_id = data.get("course_id")
    if course_id and not doc:
        course_doc = courses_store.find_course(course_id)
        if course_doc:
            doc = course_doc

    if doc:
        err = check_syllabus_approved_for_step(doc, 6)
        if err:
            return err
    pdf_bytes = generate_clo_report_pdf_bytes(bp, doc=doc)

    safe_code = re.sub(r'[\\/*?:"<>|]+', "_", bp.metadata.course_code.strip()) or "Course"
    safe_sec = re.sub(r'[\\/*?:"<>|]+', "_", bp.metadata.section.strip()) or "Section"
    filename = f"{safe_code}_{safe_sec}_CLO_Report_FM-USeP-MID-10.pdf"

    local_out = os.path.join(EXPORTS_DIR, filename)
    with open(local_out, "wb") as f_out:
        f_out.write(pdf_bytes)

    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


@app.route("/api/export-clo-report-excel", methods=["POST"])
@faculty_tools_required
def api_export_clo_report_excel():
    data = request.get_json(silent=True)
    if not data or "blueprint" not in data:
        return jsonify({"error": "Missing syllabus blueprint data."}), 400

    bp = SyllabusBlueprint.from_dict(data["blueprint"])
    doc = data.get("doc") or {}
    course_id = data.get("course_id")
    if course_id and not doc:
        course_doc = courses_store.find_course(course_id)
        if course_doc:
            doc = course_doc

    if doc:
        err = check_syllabus_approved_for_step(doc, 6)
        if err:
            return err
    excel_bytes = generate_clo_evaluation_excel_bytes(bp, doc=doc)

    safe_code = re.sub(r'[\\/*?:"<>|]+', "_", bp.metadata.course_code.strip()) or "Course"
    safe_sec = re.sub(r'[\\/*?:"<>|]+', "_", bp.metadata.section.strip()) or "Section"
    filename = f"{safe_code}_{safe_sec}_CLO_Evaluation_Result_FM-USeP-MID-10.xlsx"

    local_out = os.path.join(EXPORTS_DIR, filename)
    with open(local_out, "wb") as f_out:
        f_out.write(excel_bytes)

    return send_file(
        io.BytesIO(excel_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/export-excel", methods=["POST"])

@faculty_tools_required
def api_export_excel():

    data = request.get_json(silent=True)

    if not data or "blueprint" not in data:

        return jsonify({"error": "Missing syllabus blueprint data."}), 400







    course_id = data.get("course_id")
    doc = data.get("doc") or (courses_store.find_course(course_id) if course_id else None)
    if doc:
        err = check_syllabus_approved_for_step(doc, 3)
        if err:
            return err
    bp = SyllabusBlueprint.from_dict(data["blueprint"])

    xlsx_bytes = generate_class_record_workbook(bp)







    safe_code = re.sub(r"[^A-Za-z0-9_-]+", "_", bp.metadata.course_code.strip()) or "Course"

    safe_sec = re.sub(r"[^A-Za-z0-9_-]+", "_", bp.metadata.section.strip()) or "Section"

    filename = f"{safe_code}_{safe_sec}_OBE_Class_Record.xlsx"







    # Also save a local copy in exports/

    local_out = os.path.join(EXPORTS_DIR, filename)

    with open(local_out, "wb") as f_out:

        f_out.write(xlsx_bytes)







    return send_file(

        io.BytesIO(xlsx_bytes),

        as_attachment=True,

        download_name=filename,

        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

    )











# ======================================================================

# MULTI-SUBJECT MANAGEMENT APIS (Grouped by School Year & Semester)

# ======================================================================


@app.route("/api/dashboard/status", methods=["GET"])
def api_dashboard_status():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    username = user.get("username", "")
    courses_data = courses_store.list_courses(username, user.get("full_name") or "")
    courses = courses_data.get("courses", [])
    has_subjects = len(courses) > 0
    has_scores = bool(courses_data.get("has_recorded_scores") or courses_data.get("has_any_recorded_scores"))
    has_approved = any(bool(c.get("is_approved")) for c in courses)
    is_dashboard_unlocked = any(bool(c.get("is_approved") and c.get("has_recorded_scores")) for c in courses)
    return jsonify({
        "success": True,
        "has_subjects": has_subjects,
        "has_recorded_scores": has_scores,
        "has_approved_syllabus": has_approved,
        "is_syllabus_unlocked": has_subjects,
        "is_dashboard_unlocked": is_dashboard_unlocked,
        "total_subjects": len(courses),
    })

@app.route("/api/courses", methods=["GET"])

def api_list_courses():

    user = current_user()

    username = user["username"] if user else "default"

    faculty_name = user.get("full_name", "") if user else ""

    return jsonify(courses_store.list_courses(username, faculty_name))











@app.route("/api/courses/<course_id>", methods=["GET"])

def api_get_course(course_id):

    user = current_user()

    username = user["username"] if user else "default"

    doc = courses_store.get_course(username, course_id) or courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Subject '{course_id}' not found."}), 404

    bp_dict = doc.get("blueprint", {})

    passing_pct = bp_dict.get("metadata", {}).get("passing_percentage", 75.0)

    wf_view = syllabus_workflow.public_view(doc)

    authors = courses_store.get_doc_authors(doc)
    author_unames = [(a.get("username") or "").lower() for a in authors]
    u_lower = (username or "").lower()
    is_author = (u_lower == (doc.get("owner") or "").lower()) or (u_lower in author_unames) or (user and user.get("role") == "admin")
    user_has_submitted = (wf_view.get("status") != "returned") and (username in (wf_view.get("author_submissions") or {}))

    wf_view["is_author"] = is_author
    wf_view["user_has_submitted"] = user_has_submitted
    wf_view["can_submit"] = is_author and (not user_has_submitted) and (wf_view["status"] in syllabus_workflow.EDITABLE_STATUSES)
    wf_view["can_withdraw"] = is_author and (wf_view.get("is_awaiting_coauthors") or (wf_view["status"] == "for_committee_review" and not wf_view.get("signatures")))
    wf_view["can_sign"] = syllabus_workflow.user_can_act(user, doc)
    wf_view["user_can_act"] = syllabus_workflow.user_can_act(user, doc)
    wf_view["can_request_revision"] = is_author and (wf_view["status"] == "approved")

    cr_view = class_record_workflow.public_cr_view(doc, user)

    return jsonify({
        "course": doc,
        "blueprint": bp_dict,
        "workflow": wf_view,
        "class_record_workflow": cr_view,
        "transmutation": build_transmutation_table(passing_pct),
    })











@app.route("/api/courses", methods=["POST"])

@faculty_tools_required
def api_create_course():

    user = current_user()

    username = user["username"] if user else "default"

    faculty_name = user.get("full_name", "") if user else ""

    data = request.get_json(silent=True) or {}







    # If full blueprint is provided (e.g. from syllabus creator or imported PDF)

    if "blueprint" in data:

        bp_dict = data["blueprint"]

        meta = bp_dict.get("metadata", {})

        c_code = (data.get("course_code") or meta.get("course_code") or "New Course").strip()
        c_title = (data.get("course_title") or meta.get("course_title") or "Untitled Subject").strip()
        if " - " in c_code or " – " in c_code:
            delim = " - " if " - " in c_code else " – "
            parts = c_code.split(delim, 1)
            c_code = parts[0].strip()
            if not c_title or c_title in ("Untitled Subject", "New Subject", "Electrical Circuits 1"):
                c_title = parts[1].strip()
        meta["course_code"] = c_code
        meta["course_title"] = c_title
        if faculty_name and (not meta.get("faculty_name") or meta.get("faculty_name") in ("", "Faculty in Charge", "ELWIN JAY J. TANO")):
            meta["faculty_name"] = faculty_name
        if not meta.get("dean_name"):
            meta["dean_name"] = "Joie D. Cataytay"
        meta["passing_percentage"] = meta.get("passing_percentage") or 75.0

        sec = (data.get("section") or meta.get("section") or "1A").strip()

        sem_ay = (data.get("semester_ay") or meta.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()

        if data.get("credit_units"):
            meta["credit_units"] = data.get("credit_units")
        if data.get("lec_lab"):
            meta["lec_lab"] = data.get("lec_lab")
        if data.get("contact_hours"):
            meta["contact_hours"] = data.get("contact_hours")
        if data.get("lecture_units") is not None:
            meta["lecture_units"] = float(data.get("lecture_units"))
        if data.get("lab_units") is not None:
            meta["lab_units"] = float(data.get("lab_units"))
        if data.get("schedule"):
            meta["schedule"] = str(data.get("schedule")).strip()

        progs = data.get("programs") or meta.get("programs") or []
        secs = data.get("sections") or meta.get("sections") or []
        new_doc = courses_store.save_course(
            username,
            course_id=f"c_{uuid.uuid4().hex[:10]}",
            payload={
                "course_code": c_code,
                "course_title": c_title,
                "section": sec,
                "sections": secs,
                "programs": progs,
                "semester_ay": sem_ay,
                "blueprint": bp_dict,
            }
        )

        return jsonify({

            "course": new_doc,

            "message": f"Subject '{c_code} ({sec})' created under {sem_ay}."

        }), 201







    # Standard creation (catalog or blank)

    from_cat = bool(data.get("from_catalog"))

    cat_course = data.get("catalog_course_data")

    c_code = (data.get("course_code") or (cat_course.get("code") if cat_course else "") or "EE 211").strip()
    c_title = (data.get("course_title") or (cat_course.get("title") if cat_course else "") or "Electrical Circuits 1").strip()
    if " - " in c_code or " – " in c_code:
        delim = " - " if " - " in c_code else " – "
        parts = c_code.split(delim, 1)
        c_code = parts[0].strip()
        if not c_title or c_title in ("Untitled Subject", "New Subject", "Electrical Circuits 1"):
            c_title = parts[1].strip()

    sec = (data.get("section") or "EE 2A").strip()

    sem_ay = (data.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()







    progs = data.get("programs") or []
    secs = data.get("sections") or []
    doc = courses_store.create_course(
        username=username,
        course_code=c_code,
        course_title=c_title,
        section=sec,
        semester_ay=sem_ay,
        from_catalog=from_cat,
        catalog_course_data=cat_course,
        faculty_name=faculty_name,
        programs=progs,
        sections=secs,
        credit_units=data.get("credit_units"),
        lec_lab=data.get("lec_lab"),
        contact_hours=data.get("contact_hours"),
        lecture_units=data.get("lecture_units"),
        lab_units=data.get("lab_units"),
        schedule=data.get("schedule"),
    )

    return jsonify({

        "course": doc,

        "message": f"Subject '{c_code} ({sec})' created under {sem_ay}."

    }), 201











@app.route("/api/courses/<course_id>", methods=["PUT", "POST"])

@faculty_tools_required
def api_update_course(course_id):

    user = current_user()

    username = user["username"] if user else "default"

    data = request.get_json(silent=True) or {}

    existing_doc = courses_store.find_course(course_id)
    if existing_doc:
        step_target = request.args.get("target_step") or request.args.get("step") or data.get("target_step")
        if step_target and str(step_target) in ["2", "3", "4", "5", "6", "7", "8", "gantt", "tos"]:
            is_roster_or_step1 = bool(data.get("is_roster_update") or data.get("is_student_update"))
            if not is_roster_or_step1:
                target_val = int(step_target) if str(step_target).isdigit() else str(step_target)
                err = check_syllabus_approved_for_step(existing_doc, target_val)
                if err:
                    return err

    updated = courses_store.save_course(username, course_id, data)

    return jsonify({

        "course": updated,

        "message": f"Subject '{updated.get('course_code')} ({updated.get('section')})' saved."

    })











@app.route("/api/courses/<course_id>/duplicate", methods=["POST"])

@faculty_tools_required
def api_duplicate_course(course_id):

    user = current_user()

    username = user["username"] if user else "default"

    data = request.get_json(silent=True) or {}

    new_sec = data.get("section", "").strip()

    clear_scores = bool(data.get("clear_scores", True))

    dup = courses_store.duplicate_course(username, course_id, new_section=new_sec, clear_scores=clear_scores)

    if not dup:

        return jsonify({"error": f"Subject '{course_id}' not found."}), 404

    return jsonify({

        "course": dup,

        "message": f"Duplicated subject for Section '{dup.get('section')}'."

    }), 201











@app.route("/api/courses/<course_id>", methods=["DELETE"])

@faculty_tools_required
def api_delete_course(course_id):

    user = current_user()

    username = user["username"] if user else "default"

    ok = courses_store.delete_course(username, course_id)

    if not ok:

        return jsonify({"error": "Failed to delete subject."}), 400

    return jsonify({"success": True, "message": "Subject deleted successfully."})















# ======================================================================

# SYLLABUS WORKFLOW & EVALUATION FORM APIS (Lock-in & Approval Chain)

# ======================================================================

@app.route("/api/courses/<course_id>/workflow", methods=["GET"])

def api_get_course_workflow(course_id):

    user = current_user()

    doc = courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    wf_view = syllabus_workflow.public_view(doc)

    uname = user["username"] if user else ""

    authors = courses_store.get_doc_authors(doc)
    author_unames = [(a.get("username") or "").lower() for a in authors]
    u_lower = (uname or "").lower()
    is_author = (u_lower == (doc.get("owner") or "").lower()) or (u_lower in author_unames) or (user and user.get("role") == "admin")
    user_has_submitted = (wf_view.get("status") != "returned") and (uname in (wf_view.get("author_submissions") or {}))

    wf_view["is_author"] = is_author
    wf_view["user_has_submitted"] = user_has_submitted
    wf_view["can_submit"] = is_author and (not user_has_submitted) and (wf_view["status"] in syllabus_workflow.EDITABLE_STATUSES)
    wf_view["can_withdraw"] = is_author and (wf_view.get("is_awaiting_coauthors") or (wf_view["status"] == "for_committee_review" and not wf_view.get("signatures")))
    wf_view["can_sign"] = syllabus_workflow.user_can_act(user, doc)
    wf_view["user_can_act"] = syllabus_workflow.user_can_act(user, doc)
    wf_view["can_request_revision"] = is_author and (wf_view["status"] == "approved")

    wf_view["can_edit_checklist"] = (

        ("review_committee" in (user.get("workflow_roles") or [])) or (user.get("role") == "admin")

    )

    return jsonify(wf_view)











@app.route("/api/workflow/signatories", methods=["GET"])

def api_get_workflow_signatories():

    user = current_user()

    if not user:

        return jsonify({"error": "Unauthorized"}), 401

    users = auth._load_users()

    committee_members = []

    program_heads = []

    qa_heads = []

    deans = []

    for uname, udata in users.items():

        w_roles = udata.get("workflow_roles") or []

        is_admin = udata.get("role") == "admin"

        item = {

            "username": uname,

            "full_name": udata.get("full_name") or uname,

            "position_title": udata.get("position_title") or ("System Administrator" if is_admin else "Faculty Member"),

            "college": udata.get("college") or "COLLEGE OF ENGINEERING",

            "program_codes": udata.get("program_codes") or ["*"],

            "has_signature": bool(udata.get("signature_data")),

        }

        if "review_committee" in w_roles:
            committee_members.append(item)
        if "program_head" in w_roles or is_admin:
            program_heads.append(item)
        if "qa_head" in w_roles or is_admin:
            qa_heads.append(item)
        if "dean" in w_roles or "associate_dean" in w_roles or is_admin:
            deans.append(item)

    def _dedupe_items(items):
        seen = set()
        res = []
        for it in items:
            fn = (it.get("full_name") or "").strip().lower()
            if fn and fn not in seen:
                seen.add(fn)
                res.append(it)
        res.sort(key=lambda x: x.get("full_name", ""))
        return res

    return jsonify({
        "review_committee": _dedupe_items(committee_members),
        "program_heads": _dedupe_items(program_heads),
        "qa_heads": _dedupe_items(qa_heads),
        "deans": _dedupe_items(deans),
    })











def is_authorized_oversight_user(user):
    """
    Returns True only for Dean, Associate Dean, Program Heads, QA Head, Staffs, and Admin.
    Regular faculty without these designated institutional roles return False.
    """
    if not user:
        return False
    role = (user.get("role") or "").strip().lower()
    if role in ("admin", "staff"):
        return True
    w_roles = set(str(r).strip().lower() for r in (user.get("workflow_roles") or []))
    oversight_roles = {"dean", "associate_dean", "program_head", "qa_head", "staff"}
    return bool(w_roles.intersection(oversight_roles))


@app.route("/api/workflow/requests", methods=["GET"])
def api_get_workflow_requests():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    all_courses = courses_store.list_all_workflow_courses()

    pending_action_for_me = []
    pending_cr_action_for_me = []
    my_submitted_requests = []
    my_submitted_class_records = []
    institutional_requests = []
    institutional_class_records = []

    w_roles = user.get("workflow_roles") or []
    is_admin = (user.get("role") == "admin")
    is_staff = (user.get("role") == "staff" or "staff" in w_roles)
    can_view_institutional = is_authorized_oversight_user(user)

    for c in all_courses:
        doc_raw = c.pop("doc_raw", None)
        wf = c.get("workflow") or {}
        cr_wf = c.get("class_record_workflow") or {}
        is_owner = (c.get("owner") == user["username"])
        authors = c.get("authors") or (courses_store.get_doc_authors(doc_raw) if doc_raw else [])
        author_unames = [(a.get("username") or "").lower() for a in authors]
        is_coauthor = (not is_owner) and (user["username"].lower() in author_unames)
        is_author = is_owner or is_coauthor

        can_act = False
        if doc_raw and (is_admin or not is_owner):
            can_act = syllabus_workflow.user_can_act(user, doc_raw)
        c["user_can_act"] = can_act

        if doc_raw:
            q_age = syllabus_workflow.get_queue_age(doc_raw)
            c["days_in_queue"] = q_age.get("days_in_queue", 0.0)
            c["is_bottleneck"] = q_age.get("is_overdue", False)
            c["step_entered_at"] = q_age.get("step_entered_at")
            c["last_reminder_sent_at"] = q_age.get("last_reminder_sent_at")
            c["student_ack_stats"] = syllabus_workflow.get_student_acknowledgment_stats(doc_raw)

        can_sign_cr = False
        if doc_raw and (is_admin or not is_owner):
            can_sign_cr = class_record_workflow.user_can_sign_class_record(user, doc_raw)
        c["user_can_sign_cr"] = can_sign_cr
        c["is_owner"] = is_owner

        ACTIVE_SYL_REVIEW_STATUSES = {
            "for_committee_review", "for_committee_chair", "for_program_head",
            "for_qa_countersign", "for_student_acknowledgment", "for_dean_approval",
            "revision_for_program_head", "revision_for_associate_dean", "revision_for_dean"
        }
        if can_act and wf.get("status") in ACTIVE_SYL_REVIEW_STATUSES:
            pending_action_for_me.append(c)
        elif doc_raw and wf.get("is_awaiting_coauthors") and is_author:
            user_has_sub = user["username"] in (wf.get("author_submissions") or {})
            if not user_has_sub:
                c_copy = dict(c)
                c_copy["user_can_act"] = True
                c_copy["action_label"] = "Co-Author Submission Confirmation Required"
                pending_action_for_me.append(c_copy)

        if is_author:
            my_submitted_requests.append(c)
            if is_owner:
                my_submitted_class_records.append(c)

        if can_sign_cr and cr_wf.get("status") in {"for_program_head", "for_associate_dean", "for_qa_countersign", "for_dean_approval"}:
            pending_cr_action_for_me.append(c)

        if can_view_institutional:
            # If program head without college-wide rights, only show their program's courses
            if "program_head" in w_roles and not (is_admin or is_staff or "dean" in w_roles or "associate_dean" in w_roles or "qa_head" in w_roles):
                p_codes = user.get("program_codes") or []
                c_prog = (c.get("program_code") or "").upper()
                if not p_codes or "*" in p_codes or c_prog in p_codes:
                    institutional_requests.append(c)
                    institutional_class_records.append(c)
            else:
                institutional_requests.append(c)
                institutional_class_records.append(c)

    analytics = class_record_workflow.compute_institutional_analytics(all_courses) if can_view_institutional else None

    # Check and dispatch automatic 3-day bottleneck reminders
    try:
        import notification_service
        notification_service.check_and_dispatch_bottleneck_reminders()
    except Exception as e:
        pass

    return jsonify({
        "pending_count": len(pending_action_for_me) + len(pending_cr_action_for_me),
        "pending_syl_count": len(pending_action_for_me),
        "pending_cr_count": len(pending_cr_action_for_me),
        "can_view_institutional": can_view_institutional,
        "is_staff": is_staff,
        "can_access_faculty_tools": user.get("can_access_faculty_tools", True),
        "pending_action_for_me": pending_action_for_me,
        "pending_cr_action_for_me": pending_cr_action_for_me,
        "my_submitted_requests": my_submitted_requests,
        "my_submitted_class_records": my_submitted_class_records,
        "institutional_requests": institutional_requests,
        "institutional_class_records": institutional_class_records,
        "analytics": analytics,
        "sla_guidelines": {
            "threshold_days": 3.0,
            "title": "Institutional Syllabus Review & Signature Queue SLA Guidelines",
            "description": "Assigned reviewers (Review Committee, Program Head, QA Head, and Dean) are requested to review and act upon syllabus endorsements within three (3) working days. Requests exceeding 3 days are flagged as queue bottlenecks with automated follow-up reminder notifications."
        },
        "user_info": {
            "username": user["username"],
            "email": user.get("email"),
            "is_staff": is_staff,
            "can_access_faculty_tools": user.get("can_access_faculty_tools", True),
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "workflow_roles": user.get("workflow_roles") or [],
            "position_title": user.get("position_title"),
            "has_signature": user.get("has_signature"),
        }
    })











@app.route("/api/courses/<course_id>/workflow/submit", methods=["POST"])

@faculty_tools_required
def api_submit_syllabus(course_id):

    user = current_user()

    doc = courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    data = request.get_json(silent=True) or {}

    assigned_committee = data.get("assigned_committee")

    assigned_committee_name = data.get("assigned_committee_name")

    committee_members = data.get("committee_members")

    submission_notes = data.get("submission_notes")
    sig_data = (data.get("signature_data") or "").strip()
    if sig_data:
        from auth import _load_users, _save_users, _lock
        with _lock:
            all_users = _load_users()
            if user["username"] in all_users:
                all_users[user["username"]]["signature_data"] = sig_data
                all_users[user["username"]]["has_signature"] = True
                _save_users(all_users)
        user["has_signature"] = True
        user["signature_data"] = sig_data

    if not user.get("has_signature") and not user.get("signature_data"):
        return jsonify({"error": "A valid faculty digital signature is required before submitting the syllabus for committee review."}), 400

    try:

        wf = syllabus_workflow.submit(

            doc, user,

            assigned_committee=assigned_committee,

            assigned_committee_name=assigned_committee_name,

            committee_members=committee_members,

            submission_notes=submission_notes

        )

        courses_store.save_course_doc(doc)

        import notification_service
        pub_wf = syllabus_workflow.public_view(doc)
        if wf.get("is_awaiting_coauthors"):
            pending_authors = pub_wf.get("pending_authors") or []
            notification_service.notify_coauthor_submission_needed(
                doc,
                submitter_user=user,
                pending_authors=pending_authors
            )
            msg = f"Your individual submission has been recorded. Awaiting confirmation from {len(pending_authors)} remaining co-author(s): {', '.join(a['name'] for a in pending_authors)}."
        else:
            notification_service.notify_syllabus_submitted(
                doc,
                submitter_user=user,
                committee_members=wf.get("committee_members") or []
            )
            comm_name = wf.get("assigned_committee_name") or "the Review Committee"
            authors_count = len(pub_wf.get("authors") or [])
            if authors_count > 1:
                msg = f"All {authors_count} faculty authors confirmed submission! Syllabus forwarded to {comm_name}."
            else:
                msg = f"Syllabus submitted and notification sent to {comm_name}."

        return jsonify({
            "success": True,
            "awaiting_coauthors": wf.get("is_awaiting_coauthors", False),
            "message": msg,
            "workflow": pub_wf,
        })

    except syllabus_workflow.WorkflowError as e:

        return jsonify({"error": str(e)}), 400











@app.route("/api/courses/<course_id>/workflow/withdraw", methods=["POST"])

@faculty_tools_required
def api_withdraw_syllabus(course_id):

    user = current_user()

    doc = courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    try:

        wf = syllabus_workflow.withdraw(doc, user)

        courses_store.save_course_doc(doc)

        return jsonify({

            "success": True,

            "message": "Syllabus submission withdrawn. Returned to draft status.",

            "workflow": syllabus_workflow.public_view(doc),

        })

    except syllabus_workflow.WorkflowError as e:

        return jsonify({"error": str(e)}), 400











@app.route("/api/courses/<course_id>/evaluation-form", methods=["GET"])

def api_get_evaluation_form(course_id):

    user = current_user()

    doc = courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    wf = syllabus_workflow.get_workflow(doc)

    can_edit = (syllabus_workflow.user_can_act(user, doc) and wf.get("status") in ("for_committee_review", "for_committee_chair")) or (user.get("role") == "admin")

    return jsonify({

        "form_info": FORM_INFO,

        "core_statements": CORE_EVALUATION_STATEMENTS,

        "framework_integrations": FRAMEWORK_INTEGRATION_AREAS,

        "annex_a_sections": ANNEX_A_SECTIONS,

        "checklist": wf.get("checklist") or {},

        "is_reviewer": can_edit,

        "is_locked_for_user": not can_edit,

        "workflow_status": wf.get("status"),

    })











@app.route("/api/courses/<course_id>/evaluation-form", methods=["PUT"])

def api_save_evaluation_form(course_id):

    user = current_user()

    doc = courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    data = request.get_json(silent=True) or {}

    try:

        wf = syllabus_workflow.save_checklist(doc, user, data)

        courses_store.save_course_doc(doc)

        return jsonify({

            "success": True,

            "message": "Syllabus review checklist saved successfully.",

            "checklist": wf.get("checklist"),

        })

    except syllabus_workflow.WorkflowError as e:

        return jsonify({"error": str(e)}), 400











@app.route("/api/courses/<course_id>/workflow/sign", methods=["POST"])

def api_sign_workflow_step(course_id):

    user = current_user()

    doc = courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    data = request.get_json(silent=True) or {}

    decision = (data.get("decision") or "approve").strip().lower()

    remarks = (data.get("remarks") or "").strip()

    sig_data = data.get("signature_data") or ""







    # If signature image provided in request, save to user profile
    if sig_data:
        from auth import _load_users, _save_users, _lock
        with _lock:
            all_users = _load_users()
            if user["username"] in all_users:
                all_users[user["username"]]["signature_data"] = sig_data
                all_users[user["username"]]["has_signature"] = True
                _save_users(all_users)
        user["has_signature"] = True
        user["signature_data"] = sig_data

    overall_rec = (data.get("overall_recommendation") or "").strip()

    # If syllabus is already at for_dean_approval and faculty author/owner is endorsing
    wf_curr = syllabus_workflow.get_workflow(doc)
    if wf_curr.get("status") == "for_dean_approval" and decision == "approve":
        curr_s = syllabus_workflow.current_step(wf_curr)
        if curr_s and not syllabus_workflow.user_can_act(user, doc, curr_s):
            if user.get("username") == doc.get("owner") or "faculty" in (user.get("workflow_roles") or []):
                return jsonify({
                    "success": True,
                    "message": "Student acknowledgment criteria met. Syllabus has been endorsed to College Dean for approval.",
                    "workflow": syllabus_workflow.public_view(doc),
                })

    try:

        wf = syllabus_workflow.sign(doc, user, decision=decision, remarks=remarks, overall_recommendation=overall_rec)

        courses_store.save_course_doc(doc)

        import notification_service
        status = wf.get("status")
        step_label = (syllabus_workflow.current_step(wf) or {}).get("label") or "Next Step"

        if decision == "return":
            action_msg = "Syllabus returned for revision."
            notification_service.notify_syllabus_decision(doc, "return", user, remarks=remarks)
        elif status == "approved":
            action_msg = "Syllabus approved and locked! Class record is now unlocked."
            notification_service.notify_syllabus_decision(doc, "approve", user, remarks=remarks)
        elif status == "for_committee_chair":
            action_msg = "All committee members approved. Forwarded to Review Committee Chair for final committee endorsement."
            reviewers = syllabus_workflow.get_reviewers_for_step(doc)
            notification_service.notify_syllabus_forwarded(doc, "Review Committee Chair", reviewers, previous_signer=user, remarks=remarks)
        elif status == "for_committee_review":
            action_msg = "Member signature recorded. Waiting for other committee member(s) to sign."
        else:
            action_msg = f"Step signed and forwarded to {step_label}."
            reviewers = syllabus_workflow.get_reviewers_for_step(doc)
            notification_service.notify_syllabus_forwarded(doc, step_label, reviewers, previous_signer=user, remarks=remarks) 

        return jsonify({

            "success": True,

            "message": action_msg,

            "workflow": syllabus_workflow.public_view(doc),

        })

    except syllabus_workflow.WorkflowError as e:

        return jsonify({"error": str(e)}), 400











@app.route("/api/courses/<course_id>/export-evaluation-pdf", methods=["GET"])

def api_export_evaluation_pdf(course_id):

    user = current_user()

    doc = courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    pdf_bytes = generate_syllabus_evaluation_pdf(doc, user)

    c_code = (doc.get("course_code") or "Course").replace(" ", "_")

    filename = f"{c_code}_FM-USeP-MID-02_Evaluation_Form.pdf"

    return send_file(

        io.BytesIO(pdf_bytes),

        as_attachment=True,

        download_name=filename,

        mimetype="application/pdf",

    )













# ======================================================================
# COURSE DELIVERY GANTT CHART (IDEAL VS. ACTUAL TIMELINE) APIS (STEP 3)
# ======================================================================

@app.route("/api/courses/<course_id>/gantt", methods=["GET"])
def api_get_course_gantt(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    # Prerequisite Gating Lock: Syllabus must be approved by Dean in Step 1
    err = check_syllabus_approved_for_step(doc, "gantt")
    if err:
        return err

    import gantt_workflow
    gantt_data = gantt_workflow.get_course_gantt(doc)
    return jsonify({
        "success": True,
        "gantt": gantt_data,
    })


@app.route("/api/courses/<course_id>/gantt", methods=["PUT"])
@faculty_tools_required
def api_save_course_gantt(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "gantt")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    gantt_payload = data.get("gantt") or data

    import gantt_workflow
    updated_gantt = gantt_workflow.save_course_gantt(doc, gantt_payload)
    courses_store.save_course_doc(doc)

    return jsonify({
        "success": True,
        "message": "Course Delivery Gantt Chart updated successfully.",
        "gantt": updated_gantt,
    })


@app.route("/api/courses/<course_id>/gantt/sync", methods=["POST"])
@faculty_tools_required
def api_sync_course_gantt(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "gantt")
    if err:
        return err

    import gantt_workflow
    synced_gantt = gantt_workflow.sync_gantt_from_syllabus(doc)
    courses_store.save_course_doc(doc)

    return jsonify({
        "success": True,
        "message": "Course Delivery Gantt Chart synchronized from syllabus learning plan.",
        "gantt": synced_gantt,
    })


# ======================================================================
# TABLE OF SPECIFICATIONS (TOS) & TOS TEST REVIEW APIS (FM-USeP-MID-03 & FM-USeP-MID-04)
# ======================================================================

@app.route("/api/courses/<course_id>/tos", methods=["GET"])
def api_get_course_tos(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    # Prerequisite Gating Lock: Syllabus must be approved by Dean
    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    term = (request.args.get("term") or "midterm").lower()
    if term not in ["midterm", "final"]:
        term = "midterm"

    import tos_workflow
    tos = tos_workflow.get_course_tos(doc, term)
    perms = tos_workflow.get_tos_permissions(doc, term, user)

    return jsonify({
        "tos": tos,
        "permissions": perms,
        "term": term,
    })


@app.route("/api/courses/<course_id>/tos/sync", methods=["POST"])
@faculty_tools_required
def api_sync_course_tos(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "midterm").lower()
    if term not in ["midterm", "final"]:
        term = "midterm"

    import tos_workflow
    try:
        updated_tos = tos_workflow.sync_tos_from_syllabus(doc, term, user)
        courses_store.save_course_doc(doc)
        perms = tos_workflow.get_tos_permissions(doc, term, user)
        return jsonify({
            "success": True,
            "message": f"Successfully synchronized {term.title()} TOS from approved syllabus.",
            "tos": updated_tos,
            "permissions": perms,
            "term": term,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/tos", methods=["PUT"])
@faculty_tools_required
def api_save_course_tos(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "midterm").lower()
    tos_payload = data.get("tos") or {}

    import tos_workflow
    try:
        updated_tos = tos_workflow.save_tos_draft(doc, term, tos_payload, user)
        courses_store.save_course_doc(doc)
        perms = tos_workflow.get_tos_permissions(doc, term, user)
        return jsonify({
            "success": True,
            "message": f"{term.title()} TOS draft saved successfully.",
            "tos": updated_tos,
            "permissions": perms,
            "term": term,
        })
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/tos/submit", methods=["POST"])
@faculty_tools_required
def api_submit_course_tos(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "midterm").lower()
    signature_data = data.get("signature_data")

    import tos_workflow
    try:
        updated_tos = tos_workflow.submit_tos_to_committee(doc, term, user, signature_data)
        courses_store.save_course_doc(doc)
        perms = tos_workflow.get_tos_permissions(doc, term, user)
        return jsonify({
            "success": True,
            "message": f"{term.title()} TOS submitted to Review Committee with faculty digital signature.",
            "tos": updated_tos,
            "permissions": perms,
            "term": term,
        })
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/tos/review", methods=["POST"])
def api_review_course_tos(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "midterm").lower()
    comments = data.get("comments", "")
    recommendation = data.get("recommendation", "approved_without_revision")
    signature_data = data.get("signature_data")
    decision = data.get("decision", "approved")
    remarks = data.get("remarks", "")

    import tos_workflow
    try:
        updated_tos = tos_workflow.review_tos_committee(
            doc, term, user, comments=comments, recommendation=recommendation,
            signature_data=signature_data, decision=decision, remarks=remarks
        )
        courses_store.save_course_doc(doc)
        perms = tos_workflow.get_tos_permissions(doc, term, user)
        return jsonify({
            "success": True,
            "message": f"TOS Review recorded ({decision}).",
            "tos": updated_tos,
            "permissions": perms,
            "term": term,
        })
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/tos/endorse", methods=["POST"])
def api_endorse_course_tos(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "midterm").lower()
    signature_data = data.get("signature_data")
    decision = data.get("decision", "approved")
    remarks = data.get("remarks", "")

    import tos_workflow
    try:
        updated_tos = tos_workflow.endorse_tos_chair(
            doc, term, user, signature_data=signature_data, decision=decision, remarks=remarks
        )
        courses_store.save_course_doc(doc)
        perms = tos_workflow.get_tos_permissions(doc, term, user)
        return jsonify({
            "success": True,
            "message": f"TOS Endorsement recorded ({decision}).",
            "tos": updated_tos,
            "permissions": perms,
            "term": term,
        })
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/tos/qa-review", methods=["POST"])
def api_qa_review_course_tos(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "midterm").lower()
    signature_data = data.get("signature_data")
    decision = data.get("decision", "approved")
    remarks = data.get("remarks", "")

    import tos_workflow
    try:
        updated_tos = tos_workflow.signoff_tos_qa(
            doc, term, user, signature_data=signature_data, decision=decision, remarks=remarks
        )
        courses_store.save_course_doc(doc)
        perms = tos_workflow.get_tos_permissions(doc, term, user)
        return jsonify({
            "success": True,
            "message": f"TOS QA Verification recorded ({decision}).",
            "tos": updated_tos,
            "permissions": perms,
            "term": term,
        })
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/tos/approve", methods=["POST"])
def api_approve_course_tos(course_id):
    user = current_user()
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "midterm").lower()
    signature_data = data.get("signature_data")
    decision = data.get("decision", "approved")
    remarks = data.get("remarks", "")

    import tos_workflow
    try:
        updated_tos = tos_workflow.approve_tos_dean(
            doc, term, user, signature_data=signature_data, decision=decision, remarks=remarks
        )
        courses_store.save_course_doc(doc)
        perms = tos_workflow.get_tos_permissions(doc, term, user)
        return jsonify({
            "success": True,
            "message": f"TOS officially approved and locked by College Dean.",
            "tos": updated_tos,
            "permissions": perms,
            "term": term,
        })
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/tos/export-pdf", methods=["GET"])
def api_export_tos_pdf(course_id):
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    term = (request.args.get("term") or "midterm").lower()
    import tos_pdf_generator
    try:
        pdf_bytes = tos_pdf_generator.generate_tos_pdf_bytes(doc, term)
        c_code = (doc.get("course_code") or "Course").replace(" ", "_")
        filename = f"{c_code}_{term.title()}_FM-USeP-MID-03_Table_of_Specifications.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate TOS PDF: {str(e)}"}), 500


@app.route("/api/courses/<course_id>/tos/export-review-pdf", methods=["GET"])
def api_export_tos_review_pdf(course_id):
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    err = check_syllabus_approved_for_step(doc, "tos")
    if err:
        return err

    term = (request.args.get("term") or "midterm").lower()
    import tos_pdf_generator
    try:
        pdf_bytes = tos_pdf_generator.generate_tos_review_form_pdf_bytes(doc, term)
        c_code = (doc.get("course_code") or "Course").replace(" ", "_")
        filename = f"{c_code}_{term.title()}_FM-USeP-MID-04_TOS_Test_Review_Form.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate TOS Test Review Form PDF: {str(e)}"}), 500



@app.route("/api/courses/<course_id>/export-clo-report-excel", methods=["GET"])
def api_export_course_clo_report_excel(course_id):
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    err = check_syllabus_approved_for_step(doc, 6)
    if err:
        return err
    bp_dict = doc.get("blueprint") or {}
    bp = SyllabusBlueprint.from_dict(bp_dict)
    excel_bytes = generate_clo_evaluation_excel_bytes(bp, doc=doc)
    c_code = (doc.get("course_code") or "Course").replace(" ", "_")
    filename = f"{c_code}_FM-USeP-MID-10_CLO_Evaluation_Result.xlsx"
    return send_file(
        io.BytesIO(excel_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/courses/<course_id>/export-clo-report-pdf", methods=["GET"])
def api_export_course_clo_report_pdf(course_id):
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    err = check_syllabus_approved_for_step(doc, 6)
    if err:
        return err
    bp_dict = doc.get("blueprint") or {}
    bp = SyllabusBlueprint.from_dict(bp_dict)
    pdf_bytes = generate_clo_report_pdf_bytes(bp, doc=doc)
    c_code = (doc.get("course_code") or "Course").replace(" ", "_")
    filename = f"{c_code}_FM-USeP-MID-10_CLO_Report.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


@app.route("/api/courses/<course_id>/export-pdf", methods=["GET"])

def api_export_course_syllabus_pdf(course_id):

    doc = courses_store.find_course(course_id)

    if not doc:

        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    bp_dict = doc.get("blueprint") or {}

    bp = SyllabusBlueprint.from_dict(bp_dict)

    pdf_bytes = generate_usep_syllabus_pdf(bp, doc)

    c_code = (doc.get("course_code") or "Course").replace(" ", "_")

    sec = (doc.get("section") or "1A").replace(" ", "_")

    filename = f"{c_code}_{sec}_USeP_Course_Syllabus.pdf"

    return send_file(

        io.BytesIO(pdf_bytes),

        as_attachment=True,

        download_name=filename,

        mimetype="application/pdf",

    )


@app.route("/api/courses/<course_id>/student-acknowledgment", methods=["GET", "POST"])
def api_course_student_acknowledgment(course_id):
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    bp_dict = doc.get("blueprint") or {}
    students = bp_dict.get("students") or []
    acks = doc.get("student_acknowledgments") or (doc.get("workflow") or {}).get("student_acknowledgments") or []

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        student_id = (data.get("student_id") or "").strip()
        student_name = (data.get("student_name") or data.get("name") or "").strip()
        sig_data = (data.get("signature_data") or "").strip()
        email = (data.get("email") or "").strip()
        comment = (data.get("comment") or "").strip()
        now_ts = datetime.now().isoformat(timespec="seconds")

        if not student_name:
            return jsonify({"error": "Student name is required."}), 400

        new_ack = {
            "student_id": student_id,
            "student_name": student_name,
            "email": email,
            "signature_data": sig_data,
            "acknowledged_at": now_ts,
            "date": now_ts[:10],
            "ip_address": request.remote_addr or "",
            "comment": comment,
        }

        updated = False
        for idx, a in enumerate(acks):
            if (student_id and a.get("student_id") == student_id) or (student_name.lower() == (a.get("student_name") or "").lower()):
                acks[idx] = new_ack
                updated = True
                break
        if not updated:
            acks.append(new_ack)

        doc["student_acknowledgments"] = acks
        if "workflow" in doc and isinstance(doc["workflow"], dict):
            doc["workflow"]["student_acknowledgments"] = acks
        if "blueprint" in doc and isinstance(doc["blueprint"], dict):
            doc["blueprint"]["student_acknowledgments"] = acks

        if student_id:
            try:
                import student_store
                all_sts = student_store._load_students()
                st_entry = all_sts.get(student_id)
                if not st_entry:
                    for k, v in all_sts.items():
                        if student_store._normalize_id(k) == student_id or str(v.get("student_id") or "").lower() == student_id.lower():
                            st_entry = v
                            break
                if st_entry:
                    syl_acks = st_entry.setdefault("syllabus_acknowledgments", {})
                    syl_acks[course_id] = new_ack
                    if sig_data:
                        st_entry["signature_data"] = sig_data
                        st_entry["signature_updated_at"] = now_ts
                    student_store._save_students(all_sts)
            except Exception as _e:
                logger.debug("Error updating student_store in student-acknowledgment POST: %s", _e)


        import syllabus_workflow
        stats = syllabus_workflow.get_student_acknowledgment_stats(doc)
        wf_obj = doc.get("workflow") or {}
        msg_suffix = ""
        if wf_obj.get("status") == "for_student_acknowledgment" and stats.get("meets_threshold"):
            wf_obj["status"] = "for_dean_approval"
            wf_obj["status_label"] = syllabus_workflow.STATUS_LABELS["for_dean_approval"]
            wf_obj["step_entered_at"] = now_ts
            wf_obj["auto_endorsed_to_dean"] = True
            wf_obj.setdefault("history", []).append({
                "action": "student_ack_threshold_met",
                "step": "student_ack",
                "at": now_ts,
                "by": "system",
                "remarks": f"Student acknowledgment threshold reached ({stats['total_acknowledged']}/{stats['total_students']} signed, {stats['percentage']}%). Automatically endorsed to Dean for approval.",
            })
            doc["workflow"] = wf_obj
            msg_suffix = " 80% threshold reached: Automatically endorsed to Dean for approval!"

        courses_store.save_course_doc(doc)
        resp = jsonify({
            "success": True,
            "message": f"Syllabus acknowledgment recorded for {student_name}! {msg_suffix}".strip(),
            "acknowledgments": acks,
            "total_acknowledged": len(acks),
            "workflow": doc.get("workflow"),
        })
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    # Combined roster view mapping each enrolled student to acknowledgment status, signature, and comments
    ack_by_id = {str(a.get("student_id") or "").strip().lower(): a for a in acks if a.get("student_id")}
    ack_by_name = {str(a.get("student_name") or "").strip().lower(): a for a in acks if a.get("student_name")}

    roster = []
    for s in students:
        sid = str(s.get("student_id") or "").strip()
        sname = str(s.get("name") or "").strip()
        if not sname:
            last = s.get("last_name") or ""
            first = s.get("first_name") or ""
            sname = f"{last}, {first}".strip(", ") if (last or first) else sid

        ack = ack_by_id.get(sid.lower()) or ack_by_name.get(sname.lower())
        roster.append({
            "student_id": sid,
            "name": sname,
            "last_name": s.get("last_name") or "",
            "first_name": s.get("first_name") or "",
            "program_year": s.get("program_year") or s.get("section") or "",
            "email": s.get("email") or "",
            "is_acknowledged": ack is not None,
            "acknowledged_at": ack.get("acknowledged_at") if ack else None,
            "signature_data": ack.get("signature_data") if ack else None,
            "comment": ack.get("comment", "") if ack else "",
        })

    known_sids = {str(r.get("student_id") or "").strip().lower() for r in roster}
    for a in acks:
        asid = str(a.get("student_id") or "").strip().lower()
        if asid and asid not in known_sids:
            roster.append({
                "student_id": a.get("student_id") or "",
                "name": a.get("student_name") or "",
                "last_name": "",
                "first_name": "",
                "program_year": "",
                "email": a.get("email") or "",
                "is_acknowledged": True,
                "acknowledged_at": a.get("acknowledged_at"),
                "signature_data": a.get("signature_data"),
                "comment": a.get("comment", ""),
            })
            known_sids.add(asid)

    total_ack = len([r for r in roster if r.get("is_acknowledged")])

    resp = jsonify({
        "course_id": course_id,
        "course_code": doc.get("course_code"),
        "course_title": doc.get("course_title"),
        "section": doc.get("section"),
        "semester_ay": doc.get("semester_ay"),
        "is_approved": (doc.get("workflow") or {}).get("status") == "approved",
        "students": students,
        "roster": roster,
        "acknowledgments": acks,
        "total_students": len(roster),
        "total_acknowledged": total_ack,
    })
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


def _norm_ack_id(val: str) -> str:
    return re.sub(r"[\s\-_]+", "", str(val or "").strip().lower())


def _norm_ack_name(val: str) -> str:
    s = re.sub(r"[^a-z0-9\s,]", " ", str(val or "").strip().lower())
    return re.sub(r"\s+", " ", s).strip()


def _parse_signed_rows_from_tabular(df) -> list:
    """Extracts acknowledgment rows from a CSV/Excel DataFrame."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    cols = set(df.columns)

    def _pick(row, candidates, default=""):
        for c in candidates:
            if c in cols:
                v = row.get(c)
                if pd.notna(v) and str(v).strip() not in ("", "nan", "None"):
                    return str(v).strip()
        return default

    out = []
    for _, row in df.iterrows():
        sid = _pick(row, ["student_id", "id", "id #", "id_no", "student no", "student number", "id number"])
        last = _pick(row, ["last_name", "lastname", "surname"])
        first = _pick(row, ["first_name", "firstname", "given name"])
        full = _pick(row, ["student_name", "name", "full_name", "student name"])
        if not full and (last or first):
            full = f"{last}, {first}".strip(", ")
        if not sid and not full:
            continue

        status_raw = _pick(row, ["status", "signed", "acknowledged", "acknowledgment", "is_acknowledged", "signature", "e-signature", "e_signature"])
        date_raw = _pick(row, ["acknowledged_at", "date", "date_signed", "signed_at", "timestamp"])
        comment = _pick(row, ["comment", "comments", "feedback", "remarks"])
        sig_data = _pick(row, ["signature_data", "signature_url"])
        email = _pick(row, ["email", "email_address"])

        st_low = status_raw.lower()
        explicitly_unsigned = any(tok in st_low for tok in ("pending", "unsigned", "not signed", "no", "false", "0", "awaiting"))
        if status_raw and explicitly_unsigned:
            continue
        out.append({
            "student_id": sid,
            "student_name": full,
            "last_name": last,
            "first_name": first,
            "acknowledged_at": date_raw,
            "comment": comment,
            "signature_data": sig_data,
            "email": email,
        })
    return out


def _extract_signed_rows_from_pdf(file_bytes: bytes, roster_students: list) -> list:
    """Extracts signed student IDs/names from a signed FM-USeP-MID-07 PDF via pdfplumber."""
    import pdfplumber
    extracted_lines = []
    out = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            extracted_lines.extend([ln.strip() for ln in txt.splitlines() if ln.strip()])
            for tbl in (page.extract_tables() or []):
                for r in tbl:
                    cells = [str(c or "").strip() for c in (r or [])]
                    joined = " | ".join(c for c in cells if c)
                    if joined:
                        extracted_lines.append(joined)

    full_text = "\n".join(extracted_lines)
    text_low = full_text.lower()
    seen_ids = set()

    # 1. Match known enrolled students appearing alongside signed/date markers or inside table rows
    for st in roster_students:
        sid = str(st.get("student_id") or "").strip()
        last = str(st.get("last_name") or "").strip()
        first = str(st.get("first_name") or "").strip()
        sname = str(st.get("name") or f"{last}, {first}".strip(", ")).strip()
        if not sid and not sname:
            continue
        sid_hit = bool(sid and (sid.lower() in text_low or _norm_ack_id(sid) in _norm_ack_id(text_low)))
        name_hit = bool(last and len(last) > 2 and last.lower() in text_low and (not first or first.split()[0].lower() in text_low))
        if sid_hit or name_hit:
            # Skip rows explicitly marked Pending / Awaiting on the line containing this ID/name
            line_match = [ln for ln in extracted_lines if (sid and sid.lower() in ln.lower()) or (last and last.lower() in ln.lower())]
            if line_match and all(any(w in ln.lower() for w in ("pending", "awaiting", "unsigned")) for ln in line_match):
                continue
            key = _norm_ack_id(sid) or _norm_ack_name(sname)
            if key not in seen_ids:
                seen_ids.add(key)
                date_m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", " ".join(line_match))
                out.append({
                    "student_id": sid,
                    "student_name": sname,
                    "acknowledged_at": date_m.group(1) if date_m else "",
                    "comment": "",
                    "signature_data": "",
                })

    # 2. Catch explicit student ID patterns in PDF (e.g. 2023-00011) if roster was partial
    for ln in extracted_lines:
        if any(w in ln.lower() for w in ("pending", "awaiting", "unsigned")):
            continue
        id_m = re.search(r"\b(20\d{2}-\d{4,6})\b", ln)
        if id_m:
            sid = id_m.group(1)
            key = _norm_ack_id(sid)
            if key not in seen_ids:
                seen_ids.add(key)
                date_m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", ln)
                out.append({
                    "student_id": sid,
                    "student_name": sid,
                    "acknowledged_at": date_m.group(1) if date_m else "",
                    "comment": "",
                    "signature_data": "",
                })
    return out


@app.route("/api/courses/<course_id>/student-acknowledgment/import", methods=["POST"])
@faculty_tools_required
def api_import_course_student_acknowledgment(course_id):
    """
    Imports an existing signed Student Acknowledgment file (FM-USeP-MID-07) in .csv, .xlsx,
    .pdf, or scanned image (.png/.jpg/.jpeg/.webp) format, matches enrolled students, and
    records verified acknowledgments & workflow endorsement across stores.
    """
    import base64
    import json as _json

    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    if "file" not in request.files or not request.files["file"].filename:
        return jsonify({"error": "No signed acknowledgment file was uploaded."}), 400

    f = request.files["file"]
    filename = os.path.basename(f.filename)
    ext = os.path.splitext(filename)[1].lower()
    raw_bytes = f.read()
    if not raw_bytes:
        return jsonify({"error": "Uploaded file is empty."}), 400

    bp_dict = doc.setdefault("blueprint", {})
    students = bp_dict.setdefault("students", [])
    acks = list(doc.get("student_acknowledgments") or (doc.get("workflow") or {}).get("student_acknowledgments") or [])

    enroll_unlisted = str(request.form.get("enroll_unlisted") or "").strip().lower() in ("1", "true", "yes")
    mark_all_on_scan = str(request.form.get("mark_all_on_scan") or "").strip().lower() in ("1", "true", "yes")
    selected_ids_raw = (request.form.get("selected_student_ids") or "").strip()
    gemini_key = (request.form.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or "").strip()

    parsed_rows = []
    scan_preview_sig = ""

    try:
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(raw_bytes))
            parsed_rows = _parse_signed_rows_from_tabular(df)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(raw_bytes))
            parsed_rows = _parse_signed_rows_from_tabular(df)
        elif ext == ".pdf":
            parsed_rows = _extract_signed_rows_from_pdf(raw_bytes, students)
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            mime = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")
            if len(raw_bytes) <= 220_000:
                scan_preview_sig = f"data:{mime};base64," + base64.b64encode(raw_bytes).decode("ascii")
            # Try Gemini Vision OCR if key available
            if gemini_key:
                try:
                    import requests as _req
                    b64_img = base64.b64encode(raw_bytes).decode("ascii")
                    prompt = (
                        "Extract all signed students from this scanned USeP FM-USeP-MID-07 Student Acknowledgment sheet. "
                        "Return ONLY valid JSON array of objects with keys: student_id, student_name, acknowledged_at, signed (boolean), comment. "
                        "Include only rows that have a signature or checkmark."
                    )
                    resp_g = _req.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                        json={"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": b64_img}}]}]},
                        timeout=45,
                    )
                    if resp_g.ok:
                        cand_txt = resp_g.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        cand_txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", cand_txt.strip(), flags=re.IGNORECASE)
                        items = _json.loads(cand_txt)
                        if isinstance(items, list):
                            for it in items:
                                if isinstance(it, dict) and it.get("signed", True):
                                    parsed_rows.append({
                                        "student_id": str(it.get("student_id") or "").strip(),
                                        "student_name": str(it.get("student_name") or "").strip(),
                                        "acknowledged_at": str(it.get("acknowledged_at") or "").strip(),
                                        "comment": str(it.get("comment") or "").strip(),
                                        "signature_data": scan_preview_sig,
                                    })
                except Exception as _ocr_err:
                    logger.debug("Gemini scan acknowledgment fallback: %s", _ocr_err)

            if not parsed_rows and selected_ids_raw:
                try:
                    sel_ids = _json.loads(selected_ids_raw)
                except Exception:
                    sel_ids = [s.strip() for s in selected_ids_raw.split(",") if s.strip()]
                sel_norm = {_norm_ack_id(x) for x in sel_ids}
                for st in students:
                    sid = str(st.get("student_id") or "").strip()
                    if _norm_ack_id(sid) in sel_norm:
                        parsed_rows.append({
                            "student_id": sid,
                            "student_name": st.get("name") or f"{st.get('last_name', '')}, {st.get('first_name', '')}".strip(", "),
                            "acknowledged_at": "",
                            "comment": f"Signed file attached: {filename}",
                            "signature_data": scan_preview_sig,
                        })
            elif not parsed_rows and mark_all_on_scan:
                for st in students:
                    sid = str(st.get("student_id") or "").strip()
                    parsed_rows.append({
                        "student_id": sid,
                        "student_name": st.get("name") or f"{st.get('last_name', '')}, {st.get('first_name', '')}".strip(", "),
                        "acknowledged_at": "",
                        "comment": f"Verified signed sheet: {filename}",
                        "signature_data": scan_preview_sig,
                    })
        else:
            return jsonify({"error": f"Unsupported file type '{ext}'. Upload .csv, .xlsx, .pdf, or a scanned image (.png, .jpg, .webp)."}), 400
    except Exception as exc:
        logger.warning("Failed to parse signed acknowledgment file %s: %s", filename, exc)
        return jsonify({"error": f"Could not read signed acknowledgment file: {exc}"}), 400

    # Index existing roster & acknowledgments
    roster_by_id = {_norm_ack_id(s.get("student_id")): s for s in students if s.get("student_id")}
    roster_by_name = {}
    for s in students:
        nm = s.get("name") or f"{s.get('last_name', '')}, {s.get('first_name', '')}".strip(", ")
        if nm:
            roster_by_name[_norm_ack_name(nm)] = s
        first_last = f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
        if first_last:
            roster_by_name[_norm_ack_name(first_last)] = s

    now_ts = datetime.now().isoformat(timespec="seconds")
    imported_count = 0
    matched_existing_count = 0
    added_students_count = 0
    skipped_rows = []

    for row in parsed_rows:
        raw_sid = str(row.get("student_id") or "").strip()
        raw_name = str(row.get("student_name") or "").strip()
        st_obj = roster_by_id.get(_norm_ack_id(raw_sid)) or roster_by_name.get(_norm_ack_name(raw_name))

        if st_obj:
            matched_existing_count += 1
            sid = str(st_obj.get("student_id") or raw_sid).strip()
            sname = str(st_obj.get("name") or f"{st_obj.get('last_name', '')}, {st_obj.get('first_name', '')}".strip(", ") or raw_name or sid).strip()
            email = str(row.get("email") or st_obj.get("email") or "").strip()
        elif enroll_unlisted and raw_sid and raw_name:
            if "," in raw_name:
                last_n, first_n = [p.strip() for p in raw_name.split(",", 1)]
            else:
                parts = raw_name.split()
                last_n = parts[-1] if parts else raw_name
                first_n = " ".join(parts[:-1]) if len(parts) > 1 else ""
            new_st = {
                "student_id": raw_sid,
                "last_name": row.get("last_name") or last_n,
                "first_name": row.get("first_name") or first_n,
                "name": raw_name,
                "program_year": doc.get("section") or "",
                "email": str(row.get("email") or "").strip(),
                "scores": {},
            }
            students.append(new_st)
            roster_by_id[_norm_ack_id(raw_sid)] = new_st
            sid = raw_sid
            sname = raw_name
            email = new_st["email"]
            added_students_count += 1
        else:
            skipped_rows.append(raw_sid or raw_name or "Unknown row")
            continue

        ack_ts = str(row.get("acknowledged_at") or "").strip() or now_ts
        if len(ack_ts) == 10 and ack_ts.count("-") == 2:
            ack_ts = f"{ack_ts}T08:00:00"
        new_ack = {
            "student_id": sid,
            "student_name": sname,
            "email": email,
            "signature_data": row.get("signature_data") or scan_preview_sig or "",
            "acknowledged_at": ack_ts,
            "date": ack_ts[:10],
            "ip_address": request.remote_addr or "",
            "comment": str(row.get("comment") or f"Imported from signed file ({filename})").strip(),
            "source": "imported_file",
            "import_filename": filename,
        }

        replaced = False
        for idx, ex in enumerate(acks):
            if (_norm_ack_id(sid) and _norm_ack_id(ex.get("student_id")) == _norm_ack_id(sid)) or (
                _norm_ack_name(sname) and _norm_ack_name(ex.get("student_name")) == _norm_ack_name(sname)
            ):
                if not new_ack["signature_data"] and ex.get("signature_data"):
                    new_ack["signature_data"] = ex["signature_data"]
                acks[idx] = new_ack
                replaced = True
                break
        if not replaced:
            acks.append(new_ack)
        imported_count += 1

        try:
            all_sts = student_store._load_students()
            st_entry = all_sts.get(sid)
            if not st_entry:
                for k, v in all_sts.items():
                    if _norm_ack_id(k) == _norm_ack_id(sid):
                        st_entry = v
                        break
            if st_entry:
                st_entry.setdefault("syllabus_acknowledgments", {})[course_id] = new_ack
                if new_ack["signature_data"]:
                    st_entry["signature_data"] = new_ack["signature_data"]
                    st_entry["signature_updated_at"] = now_ts
                student_store._save_students(all_sts)
        except Exception as _st_err:
            logger.debug("student_store sync on MID-07 import skipped: %s", _st_err)

    doc["student_acknowledgments"] = acks
    if isinstance(doc.get("workflow"), dict):
        doc["workflow"]["student_acknowledgments"] = acks
    if isinstance(doc.get("blueprint"), dict):
        doc["blueprint"]["student_acknowledgments"] = acks
        doc["blueprint"]["students"] = students

    import syllabus_workflow
    stats = syllabus_workflow.get_student_acknowledgment_stats(doc)
    wf_obj = doc.get("workflow") or {}
    if wf_obj.get("status") == "for_student_acknowledgment" and stats.get("meets_threshold"):
        wf_obj["status"] = "for_dean_approval"
        wf_obj["status_label"] = syllabus_workflow.STATUS_LABELS["for_dean_approval"]
        wf_obj["step_entered_at"] = now_ts
        wf_obj["auto_endorsed_to_dean"] = True
        wf_obj.setdefault("history", []).append({
            "action": "student_ack_threshold_met",
            "step": "student_ack",
            "at": now_ts,
            "by": (current_user() or {}).get("username", "faculty"),
            "remarks": f"Imported signed file '{filename}': {stats['total_acknowledged']}/{stats['total_students']} signed ({stats['percentage']}%). Automatically endorsed to Dean for approval.",
        })
        doc["workflow"] = wf_obj

    courses_store.save_course_doc(doc)

    return jsonify({
        "success": True,
        "filename": filename,
        "imported_count": imported_count,
        "matched_existing_count": matched_existing_count,
        "added_students_count": added_students_count,
        "skipped_count": len(skipped_rows),
        "needs_scan_selection": (ext in (".png", ".jpg", ".jpeg", ".webp") and imported_count == 0 and len(students) > 0),
        "acknowledgments": acks,
        "total_acknowledged": stats.get("total_acknowledged", len(acks)),
        "total_students": stats.get("total_students", len(students)),
        "workflow": doc.get("workflow"),
        "message": (
            f"Imported {imported_count} signed acknowledgment record(s) from {filename}."
            if imported_count > 0
            else f"No matching signed rows auto-detected in {filename}. Use manual selection or upload CSV/XLSX/PDF."
        ),
    })


import student_store


@app.route("/api/roster-template.csv", methods=["GET"])
def api_download_roster_template():
    csv_data = (
        "student_id,last_name,first_name,program_year,email\n"
        "2024-00101,Dela Cruz,Juan,BSEE 3A,2024-00101@usep.edu.ph\n"
        "2024-00102,Santos,Maria,BSEE 3A,2024-00102@usep.edu.ph\n"
        "2024-00103,Reyes,Pedro,BSEE 3A,2024-00103@usep.edu.ph\n"
    )
    return send_file(
        io.BytesIO(csv_data.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="student_roster_template.csv",
    )


@app.route("/api/courses/<course_id>/roster/import", methods=["POST"])
@faculty_tools_required
def api_course_roster_import(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    bp = doc.get("blueprint") or {}
    students = bp.get("students") or []
    existing_by_id = {str(s.get("student_id") or "").strip().lower(): s for s in students if s.get("student_id")}

    imported_list = []

    if "file" in request.files and request.files["file"].filename:
        f = request.files["file"]
        ext = os.path.splitext(f.filename)[1].lower()
        try:
            if ext == ".csv":
                df = pd.read_csv(f)
            elif ext in (".xlsx", ".xls"):
                df = pd.read_excel(f)
            else:
                return jsonify({"error": "Unsupported file format. Please upload a .csv or .xlsx file."}), 400

            df.columns = [str(c).strip().lower() for c in df.columns]

            for idx, row in df.iterrows():
                sid = str(row.get("student_id", row.get("id", row.get("student no", row.get("student_no", f"2026-{1001 + idx}"))))).strip()
                last = str(row.get("last_name", row.get("lastname", row.get("surname", "")))).strip()
                first = str(row.get("first_name", row.get("firstname", row.get("given name", row.get("given_name", ""))))).strip()
                full = str(row.get("name", row.get("student_name", row.get("full_name", "")))).strip()

                if not last and full:
                    if "," in full:
                        parts = full.split(",", 1)
                        last = parts[0].strip()
                        first = parts[1].strip()
                    else:
                        parts = full.split()
                        last = parts[-1] if parts else ""
                        first = " ".join(parts[:-1]) if len(parts) > 1 else full

                prog = str(row.get("program_year", row.get("program", row.get("section", doc.get("section") or "BSEE-3")))).strip()
                email = str(row.get("email", row.get("email_address", f"{sid.lower()}@usep.edu.ph"))).strip()

                if sid or last or first or full:
                    imported_list.append({
                        "student_id": sid,
                        "last_name": last,
                        "first_name": first,
                        "name": f"{last}, {first}".strip(", ") if (last or first) else (full or sid),
                        "program_year": prog,
                        "email": email,
                    })
        except Exception as e:
            return jsonify({"error": f"Failed to parse uploaded roster file: {e}"}), 400
    else:
        data = request.get_json(silent=True) or {}
        raw_students = data.get("students") or []
        paste_text = (data.get("paste_text") or "").strip()

        if paste_text:
            lines = paste_text.splitlines()
            for idx, line in enumerate(lines):
                line = line.strip()
                if not line or line.lower().startswith("student") or line.lower().startswith("id"):
                    continue
                parts = [p.strip() for p in (line.split("\t") if "\t" in line else line.split(","))]
                if len(parts) == 1:
                    sid = parts[0]
                    imported_list.append({"student_id": sid, "name": sid, "last_name": sid, "first_name": ""})
                elif len(parts) >= 2:
                    sid = parts[0]
                    last = parts[1]
                    first = parts[2] if len(parts) > 2 else ""
                    prog = parts[3] if len(parts) > 3 else (doc.get("section") or "Engineering")
                    imported_list.append({
                        "student_id": sid,
                        "last_name": last,
                        "first_name": first,
                        "name": f"{last}, {first}".strip(", "),
                        "program_year": prog,
                        "email": f"{sid.lower()}@usep.edu.ph"
                    })
        elif isinstance(raw_students, list):
            for s in raw_students:
                if isinstance(s, dict):
                    sid = str(s.get("student_id") or "").strip()
                    last = str(s.get("last_name") or "").strip()
                    first = str(s.get("first_name") or "").strip()
                    name = str(s.get("name") or "").strip()
                    prog = str(s.get("program_year") or s.get("section") or doc.get("section") or "").strip()
                    email = str(s.get("email") or f"{sid.lower()}@usep.edu.ph").strip()
                    if sid:
                        imported_list.append({
                            "student_id": sid,
                            "last_name": last,
                            "first_name": first,
                            "name": name or (f"{last}, {first}".strip(", ") if (last or first) else sid),
                            "program_year": prog,
                            "email": email,
                        })

    if not imported_list:
        return jsonify({"error": "No valid student records found to import."}), 400

    added_count = 0
    updated_count = 0

    for item in imported_list:
        sid = item.get("student_id")
        if not sid:
            continue
        sid_norm = sid.strip().lower()

        student_store.register_or_update_student(
            student_id=sid,
            last_name=item.get("last_name") or "",
            first_name=item.get("first_name") or "",
            full_name=item.get("name") or "",
            email=item.get("email") or "",
            program_year=item.get("program_year") or "",
            course_id=course_id,
        )

        if sid_norm in existing_by_id:
            existing = existing_by_id[sid_norm]
            existing.update(item)
            updated_count += 1
        else:
            student_rec = {
                "student_id": sid,
                "last_name": item.get("last_name") or "",
                "first_name": item.get("first_name") or "",
                "name": item.get("name") or sid,
                "program_year": item.get("program_year") or "",
                "email": item.get("email") or "",
                "scores": {},
            }
            students.append(student_rec)
            existing_by_id[sid_norm] = student_rec
            added_count += 1

    bp["students"] = students
    doc["blueprint"] = bp
    courses_store.save_course_doc(doc)

    return jsonify({
        "success": True,
        "message": f"Successfully processed {len(imported_list)} student(s): {added_count} newly enrolled, {updated_count} updated.",
        "total_students": len(students),
        "added_count": added_count,
        "updated_count": updated_count,
    })


@app.route("/api/courses/<course_id>/roster/add-student", methods=["POST"])
@faculty_tools_required
def api_course_roster_add_student(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    data = request.get_json(silent=True) or {}
    sid = str(data.get("student_id") or "").strip()
    last = str(data.get("last_name") or "").strip()
    first = str(data.get("first_name") or "").strip()
    middle = str(data.get("middle_name") or "").strip()
    full = str(data.get("name") or "").strip()
    prog = str(data.get("program_year") or data.get("section") or doc.get("section") or "").strip()
    email = str(data.get("email") or (f"{sid.lower()}@usep.edu.ph" if sid else "")).strip()

    if not sid:
        return jsonify({"error": "Student ID is required (e.g. 2024-00101)."}), 400

    if not last and not full:
        return jsonify({"error": "Student Last Name is required."}), 400

    if not full:
        if middle:
            full = f"{last}, {first} {middle}".strip(", ")
        else:
            full = f"{last}, {first}".strip(", ") if (last or first) else sid
    if not last and full:
        last = full.split(",")[0].strip() if "," in full else full

    bp = doc.get("blueprint") or {}
    students = bp.get("students") or []

    student_store.register_or_update_student(
        student_id=sid,
        last_name=last,
        first_name=first,
        full_name=full,
        email=email,
        program_year=prog,
        middle_name=middle,
        course_id=course_id,
    )

    existing = None
    for s in students:
        if str(s.get("student_id") or "").strip().lower() == sid.lower():
            existing = s
            break

    if existing:
        existing["last_name"] = last
        existing["first_name"] = first
        existing["name"] = full
        existing["program_year"] = prog
        existing["email"] = email
        msg = f"Student '{sid}' roster information updated."
    else:
        new_s = {
            "student_id": sid,
            "last_name": last,
            "first_name": first,
            "middle_name": middle,
            "name": full,
            "program_year": prog,
            "email": email,
            "scores": {},
        }
        students.append(new_s)
        msg = f"Student '{sid}' ({full}) successfully enrolled in this course."

    bp["students"] = students
    removed = bp.get("removed_student_ids") or []
    bp["removed_student_ids"] = [x for x in removed if str(x).strip().lower() != sid.lower()]
    bp["class_record_initialized"] = True
    doc["blueprint"] = bp
    courses_store.save_course_doc(doc)

    resp = jsonify({
        "success": True,
        "message": msg,
        "total_students": len(students),
        "student": {
            "student_id": sid,
            "name": full,
            "last_name": last,
            "first_name": first,
            "middle_name": middle,
            "program_year": prog,
            "email": email,
        }
    })
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/api/courses/<course_id>/roster/remove-student", methods=["POST"])
@faculty_tools_required
def api_course_roster_remove_student(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    data = request.get_json(silent=True) or {}
    sid = str(data.get("student_id") or "").strip()
    if not sid:
        return jsonify({"error": "Student ID is required."}), 400

    bp = doc.get("blueprint") or {}
    students = bp.get("students") or []
    students = [s for s in students if str(s.get("student_id") or "").strip().lower() != sid.lower()]

    bp["students"] = students
    bp["class_record_initialized"] = True
    removed_list = bp.setdefault("removed_student_ids", [])
    if sid.lower() not in [str(x).strip().lower() for x in removed_list]:
        removed_list.append(sid)
    doc["blueprint"] = bp

    # Also clean up student_acknowledgments in doc and workflow
    if "student_acknowledgments" in doc and isinstance(doc["student_acknowledgments"], list):
        doc["student_acknowledgments"] = [a for a in doc["student_acknowledgments"] if str(a.get("student_id") or "").strip().lower() != sid.lower()]
    wf = doc.get("workflow") or {}
    if isinstance(wf, dict) and "student_acknowledgments" in wf and isinstance(wf["student_acknowledgments"], list):
        wf["student_acknowledgments"] = [a for a in wf["student_acknowledgments"] if str(a.get("student_id") or "").strip().lower() != sid.lower()]

    # Disenroll from student_store & SQLite persistence
    try:
        import student_store
        student_store.disenroll_student_from_course(sid, course_id)
    except Exception as _e:
        logger.debug("Error disenrolling student in api_course_roster_remove_student: %s", _e)

    courses_store.save_course_doc(doc)

    resp = jsonify({
        "success": True,
        "message": f"Student '{sid}' removed from course roster.",
        "total_students": len(students),
    })
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/student/login", methods=["GET", "POST"], endpoint="student_login")
def student_login():
    is_signed_out = bool(request.args.get("signed_out"))
    if request.method == "GET" and is_signed_out:
        session.clear()
        auth.get_csrf_token()
        session.modified = True

    user = current_user()
    if user and user.get("role") == "student" and not (request.method == "GET" and is_signed_out):
        return redirect(url_for("student_dashboard"))

    if request.method == "GET":
        auth.get_csrf_token()
        session.modified = True

    error = None
    success = "You have been signed out from the Student Portal." if is_signed_out else None
    student_id = ""
    next_url = request.args.get("next") or ""

    if request.method == "POST":
        student_id = (request.form.get("student_id") or "").strip()
        secret = (request.form.get("secret") or request.form.get("student_secret") or "").strip()
        sent_csrf = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        expected_csrf = session.get("_csrf", "")
        if sent_csrf and expected_csrf and not secrets.compare_digest(sent_csrf, expected_csrf):
            session.clear()
            auth.get_csrf_token()
            session.modified = True
            success = None
            error = "Your Student Portal sign-in token expired. A fresh security token has been issued — please submit again."
        else:
            ok, st, err_msg = student_store.verify_student_login(student_id, secret)
            if ok and st:
                session.clear()
                session.permanent = True
                session["username"] = st["student_id"]
                session["student_id"] = st["student_id"]
                session["student_name"] = st.get("full_name") or st.get("name") or st.get("student_id")
                session["role"] = "student"
                session["email"] = st.get("email") or f"{st['student_id']}@usep.edu.ph"
                session["has_signature"] = bool(st.get("signature_data"))
                auth.get_csrf_token()

                if next_url and next_url.startswith("/student"):
                    return redirect(next_url)
                return redirect(url_for("student_dashboard"))
            else:
                error = err_msg or "Authentication failed. Please verify your Student ID and Last Name."

    resp = make_response(render_template("student_login.html", error=error, success=success, student_id=student_id, next_url=next_url))
    resp.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    resp.headers["Vary"] = "Cookie"
    return resp


@app.route("/student/logout", methods=["GET", "POST"], endpoint="student_logout")
def student_logout():
    session.clear()
    session.modified = True
    cookie_name = app.config.get("SESSION_COOKIE_NAME", "__session")
    remember_name = app.config.get("REMEMBER_COOKIE_NAME", "__session_remember")
    is_secure = bool(app.config.get("SESSION_COOKIE_SECURE", False))
    resp = make_response(redirect(url_for("student_login", signed_out=1)))
    for cname in {cookie_name, "__session", "session", remember_name}:
        resp.delete_cookie(cname, path="/")
        resp.delete_cookie(cname, path="/student")
        resp.delete_cookie(cname)
        resp.set_cookie(cname, "", expires=0, max_age=0, path="/", secure=is_secure, httponly=True, samesite="Lax")
    resp.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    resp.headers["Vary"] = "Cookie"
    return resp


@app.route("/student", methods=["GET"])
@app.route("/student/dashboard", methods=["GET"], endpoint="student_dashboard")
def student_dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("student_login", next=request.path))

    # If faculty or admin logged in, allow them to view student dashboard using demo/first student or their profile
    sid = user.get("student_id") or user.get("username")
    cdata = student_store.find_courses_for_student(sid)

    # If user has no courses under username, but is faculty/admin, check if any student exists to demonstrate
    if cdata["stats"]["total"] == 0 and user.get("role") != "student":
        # Faculty preview mode
        preview_st = {"student_id": "Faculty Preview", "full_name": user.get("full_name"), "program_year": "Faculty Studio Oversight", "signature_data": user.get("signature_data", "")}
        return render_template("student_dashboard.html", student=preview_st, pending=[], acknowledged=[], in_review=[], stats={"total": 0, "pending_count": 0, "acknowledged_count": 0, "in_review_count": 0, "terms_count": 0}, groups=[], terms=[])

    st_obj = dict(cdata.get("student") or {})
    if user.get("full_name") and user.get("full_name") != sid:
        st_obj["full_name"] = user.get("full_name")
    elif not st_obj.get("full_name") or st_obj.get("full_name") == sid:
        st_obj["full_name"] = user.get("student_name") or sid
    st_obj.setdefault("student_id", sid)
    st_obj.setdefault("signature_data", user.get("signature_data", ""))

    return render_template(
        "student_dashboard.html",
        student=st_obj,
        pending=cdata["pending"],
        acknowledged=cdata["acknowledged"],
        in_review=cdata["in_review"],
        stats=cdata["stats"],
        groups=cdata.get("groups", []),
        terms=cdata.get("terms", [])
    )


@app.route("/api/student/courses", methods=["GET"])
def api_student_courses():
    user = current_user()
    if not user or user.get("role") != "student":
        return jsonify({"error": "Student authentication required."}), 401

    sid = user.get("student_id") or user.get("username")
    cdata = student_store.find_courses_for_student(sid)
    return jsonify(cdata)


@app.route("/api/student/sign-acknowledgment", methods=["POST"])
def api_student_sign_acknowledgment():
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required. Please sign in."}), 401

    data = request.get_json(silent=True) or {}
    course_id = (data.get("course_id") or "").strip()
    sig_data = (data.get("signature_data") or "").strip()
    comment = (data.get("comment") or "").strip()

    if not course_id:
        return jsonify({"error": "Course ID is required."}), 400
    if not sig_data:
        return jsonify({"error": "Electronic signature is required."}), 400

    sid = user.get("student_id") or user.get("username")
    s_name = user.get("full_name") or sid

    ok, msg, ack_rec = student_store.record_student_acknowledgment(
        student_id=sid,
        course_id=course_id,
        signature_data=sig_data,
        student_name=s_name,
        ip_address=request.remote_addr or "",
        comment=comment,
    )

    if not ok:
        return jsonify({"error": msg}), 400

    session["has_signature"] = True

    resp = jsonify({
        "success": True,
        "message": msg,
        "acknowledgment": ack_rec
    })
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/api/student/save-signature", methods=["POST"])
def api_student_save_signature():
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json(silent=True) or {}
    sig_data = (data.get("signature_data") or "").strip()
    if not sig_data:
        return jsonify({"error": "Signature data is required."}), 400

    sid = user.get("student_id") or user.get("username")
    saved = student_store.save_student_signature(sid, sig_data)
    if saved:
        session["has_signature"] = True
        return jsonify({"success": True, "message": "Electronic signature saved successfully!"})

    return jsonify({"error": "Failed to save signature."}), 500


@app.route("/api/courses/<course_id>/export-acknowledgment-pdf", methods=["GET"])
def api_export_course_acknowledgment_pdf(course_id):
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    import syllabus_acknowledgment_form
    bp_dict = doc.get("blueprint") or {}
    bp = SyllabusBlueprint.from_dict(bp_dict)
    user = current_user()
    pdf_bytes = syllabus_acknowledgment_form.generate_syllabus_acknowledgment_pdf(bp, doc, user=user)

    c_code = (doc.get("course_code") or "Course").replace(" ", "_")
    sec = (doc.get("section") or "1A").replace(" ", "_")
    filename = f"{c_code}_{sec}_FM-USeP-MID-07_Syllabus_Acknowledgment.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )

















@app.route("/api/courses/<course_id>/workflow/request-revision", methods=["POST"])
@faculty_tools_required
def api_request_syllabus_revision(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or data.get("revision_reason") or "").strip()
    try:
        wf = syllabus_workflow.request_revision(doc, user, reason=reason)
        courses_store.save_course_doc(doc)
        wf_view = syllabus_workflow.public_view(doc)
        wf_view["can_submit"] = False
        target_role = "Associate Dean" if (wf_view.get("revision_request") or {}).get("owner_is_program_head") else "Program Head"

        import notification_service
        reviewers = syllabus_workflow.get_reviewers_for_step(doc)
        notification_service.notify_revision_requested(doc, user, target_role, reviewers, reason)

        return jsonify({
            "success": True,
            "message": f"Syllabus revision request submitted successfully. Forwarded to {target_role} and Dean for approval.",
            "workflow": wf_view,
        })
    except syllabus_workflow.WorkflowError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/workflow/revision-action", methods=["POST"])
@faculty_tools_required
def api_syllabus_revision_action(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    data = request.get_json(silent=True) or {}
    action = data.get("action") or data.get("decision") or ""
    remarks = (data.get("remarks") or "").strip()
    try:
        wf = syllabus_workflow.handle_revision_action(doc, user, action=action, remarks=remarks)
        courses_store.save_course_doc(doc)
        wf_view = syllabus_workflow.public_view(doc)
        status = wf_view.get("status")

        import notification_service
        if status == "draft":
            msg = f"Syllabus revision request approved by Dean! Syllabus is now unlocked for Cycle {wf_view.get('cycle', 2)} updates."
            notification_service.notify_revision_decision(doc, "approved", user, remarks=remarks)
        elif status == "revision_for_dean":
            msg = "Syllabus revision request endorsed and forwarded to the Dean for final approval."
            reviewers = syllabus_workflow.get_reviewers_for_step(doc)
            notification_service.notify_syllabus_forwarded(doc, "College Dean (Revision Approval)", reviewers, previous_signer=user, remarks=remarks)
        elif status == "approved":
            msg = "Syllabus revision request was rejected. The syllabus remains approved and locked."
            notification_service.notify_revision_decision(doc, "rejected", user, remarks=remarks)
        else:
            msg = "Revision request updated."
        return jsonify({
            "success": True,
            "message": msg,
            "workflow": wf_view,
        })
    except syllabus_workflow.WorkflowError as e:
        return jsonify({"error": str(e)}), 400


# =========================================================================
# CLASS RECORD SEQUENTIAL SIGN-OFF & GRADE LOCK-IN APIS
# =========================================================================


@app.route("/api/workflow/dispatch-reminders", methods=["POST"])
def api_dispatch_workflow_reminders():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if not is_authorized_oversight_user(user):
        return jsonify({"error": "Forbidden: Dispatching institutional bottleneck reminders is restricted to Dean, Associate Dean, Program Heads, QA Head, Staff, and Admin."}), 403
    import notification_service
    result = notification_service.check_and_dispatch_bottleneck_reminders(force=True)
    return jsonify({
        "success": True,
        "message": f"Successfully evaluated signature queues. Dispatched {result['reminded_count']} overdue bottleneck reminder notification(s).",
        "reminded_count": result["reminded_count"],
        "reminded_courses": result["reminded_courses"]
    })


@app.route("/api/courses/<course_id>/workflow/send-reminder", methods=["POST"])
def api_send_course_reminder(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    wf = syllabus_workflow.get_workflow(doc)
    if wf.get("status") in syllabus_workflow.EDITABLE_STATUSES or wf.get("status") == "approved":
        return jsonify({"error": "This course is not currently awaiting review sign-off."}), 400
    import notification_service
    reviewers = syllabus_workflow.get_reviewers_for_step(doc)
    if not reviewers:
        return jsonify({"error": "No pending reviewers found for the current step."}), 400
    q_age = syllabus_workflow.get_queue_age(doc)
    days = q_age.get("days_in_queue", 0.0)
    notification_service.notify_bottleneck_reminder(doc, reviewers, days)
    now_iso = datetime.now().isoformat(timespec="seconds")
    wf["last_reminder_sent_at"] = now_iso
    syllabus_workflow._log(
        wf,
        by=user["username"],
        action="reminder_sent",
        remarks=f"Review reminder dispatched by {user.get('full_name') or user['username']} ({days} days in queue)",
        step=wf.get("current_step") or wf.get("status")
    )
    courses_store.save_course_doc(doc)
    return jsonify({
        "success": True,
        "message": f"Follow-up reminder sent to {len(reviewers)} reviewer(s) ({', '.join(r['full_name'] for r in reviewers)}).",
        "reviewers": reviewers,
        "days_in_queue": days
    })


@app.route("/api/notifications/log", methods=["GET"])
def api_get_notifications_log():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    import notification_service
    limit = request.args.get("limit", 50, type=int)
    return jsonify({
        "notifications": notification_service.get_recent_notifications(limit)
    })


@app.route("/api/courses/<course_id>/class-record/workflow", methods=["GET"])
def api_get_class_record_workflow(course_id):
    user = current_user()
    uname = user["username"] if user else "default"
    doc = courses_store.get_course(uname, course_id) or courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Subject '{course_id}' not found."}), 404
    cr_view = class_record_workflow.public_cr_view(doc, user)
    return jsonify({
        "course_id": course_id,
        "class_record_workflow": cr_view,
    })


@app.route("/api/courses/<course_id>/class-record/submit", methods=["POST"])
@faculty_tools_required
def api_submit_class_record(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Subject '{course_id}' not found."}), 404
    err = check_syllabus_approved_for_step(doc, 3)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    notes = (data.get("notes") or data.get("submission_notes") or "").strip()
    sig_data = data.get("signature_data") or user.get("signature_data") or ""
    try:
        cr_wf = class_record_workflow.submit_class_record(doc, user, notes=notes, signature_data=sig_data)
        courses_store.save_course_doc(doc)
        cr_view = class_record_workflow.public_cr_view(doc, user)
        return jsonify({
            "success": True,
            "message": f"Class record finalized and submitted for institutional sign-off. ({cr_view['status_label']})",
            "class_record_workflow": cr_view,
        })
    except class_record_workflow.ClassRecordWorkflowError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/class-record/sign", methods=["POST"])
def api_sign_class_record(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Subject '{course_id}' not found."}), 404
    err = check_syllabus_approved_for_step(doc, 3)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    decision = (data.get("decision") or "approve").strip().lower()
    remarks = (data.get("remarks") or "").strip()
    sig_data = data.get("signature_data") or user.get("signature_data") or ""
    try:
        cr_wf = class_record_workflow.sign_class_record(doc, user, decision=decision, remarks=remarks, signature_data=sig_data)
        courses_store.save_course_doc(doc)
        cr_view = class_record_workflow.public_cr_view(doc, user)
        action_msg = "returned for grade revision" if decision == "return" else "signed and endorsed successfully"
        return jsonify({
            "success": True,
            "message": f"Class record {action_msg}. (Current stage: {cr_view['status_label']})",
            "class_record_workflow": cr_view,
        })
    except class_record_workflow.ClassRecordWorkflowError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<course_id>/class-record/request-revision", methods=["POST"])
@faculty_tools_required
def api_request_class_record_revision(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Subject '{course_id}' not found."}), 404
    err = check_syllabus_approved_for_step(doc, 3)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or data.get("revision_reason") or "").strip()
    try:
        cr_wf = class_record_workflow.request_class_record_revision(doc, user, reason=reason)
        courses_store.save_course_doc(doc)
        cr_view = class_record_workflow.public_cr_view(doc, user)
        return jsonify({
            "success": True,
            "message": "Class record unlocked for grade revision. You can now adjust student scores and re-submit.",
            "class_record_workflow": cr_view,
        })
    except class_record_workflow.ClassRecordWorkflowError as e:
        return jsonify({"error": str(e)}), 400


# =========================================================================
# STAFF OVERSIGHT ANALYTICS & AUTO-GENERATED AUDIT REPORTS
# =========================================================================

@app.route("/api/workflow/analytics", methods=["GET"])
def api_get_workflow_analytics():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if not is_authorized_oversight_user(user):
        return jsonify({"error": "Forbidden: Institutional analytics is restricted to Dean, Associate Dean, Program Heads, QA Head, Staff, and Admin."}), 403
    all_courses = courses_store.list_all_workflow_courses()
    analytics = class_record_workflow.compute_institutional_analytics(all_courses)
    return jsonify(analytics)


@app.route("/api/workflow/oversight-report", methods=["GET"])
def api_download_oversight_report():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if not is_authorized_oversight_user(user):
        return jsonify({"error": "Forbidden: Institutional oversight report is restricted to Dean, Associate Dean, Program Heads, QA Head, Staff, and Admin."}), 403
    all_courses = courses_store.list_all_workflow_courses()
    analytics = class_record_workflow.compute_institutional_analytics(all_courses)
    generated_by = user.get("full_name") or user.get("username") or "Academic Oversight Staff"
    pdf_bytes = oversight_report_generator.generate_oversight_report_pdf(analytics, all_courses, generated_by=generated_by)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=\"USeP_Institutional_Oversight_Report.pdf\"",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )


# =========================================================================
# PROGRAM GRADUATE OUTCOMES (PGO) ASSESSMENT & INTERACTIVE FLOWCHART API
# =========================================================================

@app.route("/api/pgo-assessment", methods=["GET"])
def api_get_pgo_assessment():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.get("role") == "student":
        return jsonify({"error": "Forbidden: PGO Assessment is for Faculty and Academic Leadership."}), 403

    try:
        import pgo_assessment
        program_filter = request.args.get("program", "ALL")
        course_filter = request.args.get("course_id", "ALL")
        ied_filter = request.args.get("ied", "ALL")
        cohort_filter = request.args.get("cohort", "ALL")
        search_query = request.args.get("q", "")

        report = pgo_assessment.build_pgo_assessment_report(
            user=user,
            program_filter=program_filter,
            course_filter=course_filter,
            ied_filter=ied_filter,
            cohort_filter=cohort_filter,
            search_query=search_query,
        )
        return jsonify(report)
    except Exception as exc:
        app.logger.exception("PGO Assessment build failed: %s", exc)
        return jsonify({"error": f"Unable to compute PGO Assessment report: {exc}"}), 500


@app.route("/api/pgo-assessment/node-drilldown", methods=["GET"])
def api_get_pgo_node_drilldown():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.get("role") == "student":
        return jsonify({"error": "Forbidden"}), 403

    try:
        import pgo_assessment
        node_type = (request.args.get("node_type") or "").strip().lower()
        node_id = (request.args.get("node_id") or "").strip()
        report = pgo_assessment.build_pgo_assessment_report(
            user=user,
            program_filter=request.args.get("program", "ALL"),
            course_filter=request.args.get("course_id", "ALL"),
            ied_filter=request.args.get("ied", "ALL"),
            cohort_filter=request.args.get("cohort", "ALL"),
            search_query=request.args.get("q", ""),
        )

        target = None
        if node_type == "pgo":
            pid = node_id.replace("pgo:", "").strip().lower()
            target = next((p for p in (report.get("pgos") or []) if p.get("pgo_id") == pid), None)
        elif node_type == "pi":
            pi_id = node_id.replace("pi:", "").strip().lower()
            target = next((p for p in (report.get("pis") or []) if p.get("pi_id") == pi_id), None)
        elif node_type in ("course_clo", "cclo"):
            cclo_nodes = (report.get("flowchart") or {}).get("course_clo_nodes") or []
            target = next((n for n in cclo_nodes if n.get("node_key") == node_id or f"{n.get('course_id')}:{n.get('clo_id')}" == node_id), None)
        elif node_type == "student":
            target = next((s for s in (report.get("students_matrix") or []) if str(s.get("student_id") or "").lower() == node_id.lower()), None)

        if not target:
            return jsonify({"error": "Requested node or record is not accessible within your role scope."}), 404

        return jsonify({"success": True, "node_type": node_type, "node": target, "scope": report.get("scope")})
    except Exception as exc:
        app.logger.exception("PGO Node Drilldown failed: %s", exc)
        return jsonify({"error": f"Unable to load PGO node details: {exc}"}), 500


# =========================================================================
# COURSE SYLLABUS CREATOR (STEP 1) - PER-SECTION OCR / IMAGE EXTRACTION API
# =========================================================================

_SYLLABUS_OCR_SECTION_PROMPTS = {
    "course_info": (
        "Extract Part I Course & Faculty Metadata as JSON object with optional string keys: "
        "university, schedule, room, semester_ay, faculty_name, program_head, passing_pct."
    ),
    "course_outcomes": (
        "Extract Course Learning Outcomes (CLOs) as JSON object {\"course_outcomes\": [ "
        "{\"co_id\": \"CO1\", \"description\": \"...\", \"program_outcomes\": \"PGO a\", \"performance_indicator\": \"a.1 ...\", \"iga_aligned\": \"IGA1\", \"degree_target\": 75, \"target_pct\": 50} ]}."
    ),
    "course_desc": (
        "Extract Part III-V Course Description, Faculty Email, Consultation Hours, Workload Info as JSON object "
        "with optional keys: version_number, version_note, year_level, faculty_email, consultation_hours, consultation_venue, course_description, workload_description."
    ),
    "prereq_sdg": (
        "Extract Part V Pre-requisites/Co-requisites and SDG Alignments as JSON object: "
        "{\"prereq_coreq_table\": [{\"req_type\": \"Pre-requisite\"|\"Co-requisite\", \"course_code\": \"...\", \"course_title\": \"...\"}], "
        "\"sdg_table\": [{\"sdg\": \"SDG 7: Affordable and Clean Energy\", \"description\": \"...\"}]}."
    ),
    "assessment_activities": (
        "Extract Part VI Assessment Activities as JSON object {\"syllabus_assessment_activities\": [ "
        "{\"type\": \"Formative\"|\"Summative\", \"code\": \"FA1\"|\"SA1\", \"activity\": \"...\", \"description\": \"...\", \"clo_aligned\": \"CO1, CO2\", \"weight_pct\": 0, \"items_per_term\": 2} ]}."
    ),
    "rubrics": (
        "Extract Part VII Measurement System / Rubrics as JSON object {\"rubrics\": [ "
        "{\"title\": \"...\", \"linked_assessment\": \"...\", \"criteria\": [{\"criterion\": \"...\", \"weight\": 25, \"levels\": [\"...\"]}]} ]}."
    ),
    "grading_plan": (
        "Extract Part VIII Grading System & Passing Conditions as JSON object: "
        "{\"grading_system_type\": \"two_term\"|\"term_project\"|\"lecture_lab\", \"passing_grade_conditions\": \"...\"}."
    ),
    "learning_plan": (
        "Extract Part IX Course Learning Plan rows as JSON object {\"learning_plan_table\": [ "
        "{\"ilo\": \"...\", \"clo\": \"CO1\", \"time_frame\": \"Week 2 (3 hrs)\", \"topics\": \"...\", \"tla\": \"...\", \"required_reading\": \"...\", \"assessment_activities\": \"...\"} ]}."
    ),
    "references_policies": (
        "Extract Part X References and Part XI Classroom Policies as JSON object: "
        "{\"references_table\": [{\"code\": \"Ref01\", \"reference\": \"...\"}], "
        "\"policies_table\": [{\"no\": \"1\", \"area\": \"Attendance Policy\", \"details\": \"...\"}]}."
    ),
}


def _parse_ocr_raw_text_fallback(section_key: str, raw_text: str) -> dict:
    """Deterministic text parser when Vision JSON isn't directly structured or raw text is provided."""
    lines = [ln.strip() for ln in str(raw_text or "").splitlines() if ln.strip()]
    if section_key == "course_info":
        out = {}
        joined = "\n".join(lines)
        for key, pat in [
            ("schedule", r"(?:Schedule|Class\s*Schedule)\s*[:\-]\s*(.+)"),
            ("room", r"(?:Room|Venue)\s*[:\-]\s*(.+)"),
            ("semester_ay", r"(?:Semester|A\.?Y\.?|Academic\s*Year)\s*[:\-]\s*(.+)"),
            ("faculty_name", r"(?:Instructor|Faculty|Prepared\s*by)\s*[:\-]\s*(.+)"),
            ("program_head", r"(?:Program\s*Head|Department\s*Chair)\s*[:\-]\s*(.+)"),
        ]:
            m = re.search(pat, joined, flags=re.IGNORECASE)
            if m:
                out[key] = m.group(1).strip()
        return out
    if section_key == "course_outcomes":
        cos = []
        for idx, ln in enumerate(lines, 1):
            m = re.match(r"^(CO\s*\d+|CLO\s*\d+)[\s.:\-]+(.+)$", ln, flags=re.IGNORECASE)
            if m:
                co_code = re.sub(r"\s+", "", m.group(1).upper()).replace("CLO", "CO")
                cos.append({"co_id": co_code, "description": m.group(2).strip()})
            elif len(ln) > 18:
                cos.append({"co_id": f"CO{len(cos) + 1}", "description": ln})
        return {"course_outcomes": cos}
    if section_key == "course_desc":
        return {"course_description": "\n".join(lines)}
    if section_key == "prereq_sdg":
        reqs, sdgs = [], []
        for ln in lines:
            if re.search(r"\bSDG\s*\d+", ln, flags=re.IGNORECASE):
                parts = re.split(r"\s*[\-:|]\s*", ln, maxsplit=1)
                sdgs.append({"sdg": parts[0].strip(), "description": parts[1].strip() if len(parts) > 1 else ln})
            else:
                req_t = "Co-requisite" if "co-req" in ln.lower() or "coreq" in ln.lower() else "Pre-requisite"
                cm = re.search(r"\b([A-Z]{2,6}\s*\d{3}[A-Z]?)\b", ln)
                if cm:
                    code = cm.group(1).strip()
                    title = ln.replace(code, "", 1).strip(" -:|")
                    reqs.append({"req_type": req_t, "course_code": code, "course_title": title})
        return {"prereq_coreq_table": reqs, "sdg_table": sdgs}
    if section_key == "assessment_activities":
        acts = []
        for ln in lines:
            m = re.match(r"^(FA\d+|SA\d+)\b[\s.:\-]+(.+)$", ln, flags=re.IGNORECASE)
            if m:
                code = m.group(1).upper()
                acts.append({
                    "type": "Formative" if code.startswith("FA") else "Summative",
                    "code": code,
                    "activity": m.group(2).strip()[:60],
                    "description": m.group(2).strip(),
                })
        return {"syllabus_assessment_activities": acts}
    if section_key == "grading_plan":
        return {"passing_grade_conditions": "\n".join(lines)}
    if section_key == "learning_plan":
        rows = []
        for idx, ln in enumerate(lines, 1):
            parts = [p.strip() for p in re.split(r"\t+|\s*\|\s*", ln) if p.strip()]
            if len(parts) >= 3:
                rows.append({
                    "ilo": parts[0],
                    "clo": parts[1] if len(parts) > 3 else "",
                    "time_frame": parts[2] if len(parts) > 3 else f"Week {idx}",
                    "topics": parts[3] if len(parts) > 3 else parts[1],
                    "tla": parts[4] if len(parts) > 4 else "Lecture / Discussion",
                    "required_reading": parts[5] if len(parts) > 5 else "",
                    "assessment_activities": parts[6] if len(parts) > 6 else "",
                })
            elif len(ln) > 8:
                wm = re.search(r"(Week\s*\d+(?:\s*[-–]\s*\d+)?)", ln, flags=re.IGNORECASE)
                rows.append({
                    "ilo": f"Understand and apply {ln}",
                    "clo": "",
                    "time_frame": wm.group(1) if wm else f"Week {idx}",
                    "topics": ln,
                    "tla": "Lecture / Guided Discussion",
                    "required_reading": "",
                    "assessment_activities": "",
                })
        return {"learning_plan_table": rows}
    if section_key == "references_policies":
        refs, pols = [], []
        for ln in lines:
            if re.match(r"^(Ref\s*\d+|\[\d+\])", ln, flags=re.IGNORECASE):
                parts = re.split(r"\s+", ln, maxsplit=1)
                refs.append({"code": parts[0], "reference": parts[1] if len(parts) > 1 else ln})
            elif any(w in ln.lower() for w in ("policy", "attendance", "honesty", "late", "grading", "conduct")) or re.match(r"^\d+[\.)]\s+", ln):
                clean = re.sub(r"^\d+[\.)]\s*", "", ln)
                parts = re.split(r"\s*[:\-]\s*", clean, maxsplit=1)
                pols.append({
                    "no": str(len(pols) + 1),
                    "area": parts[0].strip()[:80],
                    "details": parts[1].strip() if len(parts) > 1 else clean,
                })
            else:
                refs.append({"code": f"Ref{len(refs) + 1:02d}", "reference": ln})
        return {"references_table": refs, "policies_table": pols}
    return {"raw_text": "\n".join(lines)}


def _run_built_in_local_ocr(raw_bytes: bytes) -> tuple:
    """
    Runs built-in out-of-the-box local OCR without requiring user API keys or setup:
      1) Local pytesseract if available on host
      2) Native Windows 10/11 WinRT OCR (Windows.Media.Ocr.OcrEngine) via PIL upscaling + PowerShell
    Returns (extracted_text, engine_name).
    """
    from PIL import Image, ImageOps
    import subprocess

    img_obj = Image.open(io.BytesIO(raw_bytes))
    # Upscale smaller captures for much cleaner OCR recognition
    if img_obj.width < 1100:
        scale = 2 if img_obj.width >= 450 else 3
        img_obj = img_obj.resize((img_obj.width * scale, img_obj.height * scale), Image.Resampling.LANCZOS)
    if img_obj.mode not in ("RGB", "L"):
        img_obj = img_obj.convert("RGB")

    # 1. Try pytesseract if installed
    try:
        import pytesseract
        txt = (pytesseract.image_to_string(img_obj) or "").strip()
        if txt:
            return txt, "tesseract_default_ocr"
    except Exception:
        pass

    # 2. Native Windows WinRT OCR fallback (pre-installed on Windows)
    if os.name == "nt":
        prep_buf = io.BytesIO()
        ImageOps.autocontrast(img_obj.convert("L")).save(prep_buf, format="PNG")
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                tf.write(prep_buf.getvalue())
                tmp_path = tf.name
            safe_path = tmp_path.replace("'", "''")
            ps_cmd = (
                "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
                "$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | "
                "Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and "
                "$_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]; "
                "function Await($WinRtTask, $ResultType) { "
                "$asTask = $asTaskGeneric.MakeGenericMethod($ResultType); "
                "$netTask = $asTask.Invoke($null, @($WinRtTask)); "
                "$netTask.Wait(-1) | Out-Null; $netTask.Result }; "
                "$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]; "
                "$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]; "
                "$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]; "
                "$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]; "
                "$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]; "
                "$null = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime]; "
                f"$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync('{safe_path}')) ([Windows.Storage.StorageFile]); "
                "$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream]); "
                "$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder]); "
                "$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap]); "
                "$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages(); "
                "if ($null -ne $engine) { "
                "$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult]); "
                "foreach ($ln in $result.Lines) { Write-Output $ln.Text } }; "
                "$stream.Dispose()"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip(), "built_in_default_ocr"
        except Exception as exc:
            logger.debug("WinRT local OCR error: %s", exc)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    return "", ""


@app.route("/api/syllabus/ocr-extract", methods=["POST"])
@faculty_tools_required
def api_syllabus_section_ocr_extract():
    """
    Performs OCR / Vision extraction for a specific Course Syllabus Creator (Step 1)
    section from an uploaded/clipboard-pasted image or raw text payload.
    Defaults to the built-in out-of-the-box OCR engine (zero config required),
    with optional specialized Gemini Vision model override.
    """
    import base64
    import json as _json
    import requests as _req

    payload = request.get_json(silent=True) if request.is_json else None
    if payload:
        section_key = str(payload.get("section_key") or "learning_plan").strip()
        ocr_mode = str(payload.get("ocr_mode") or "default").strip().lower()
        gemini_key = str(payload.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or "").strip()
        raw_text_in = str(payload.get("raw_text") or "").strip()
        img_b64 = str(payload.get("image_base64") or "").strip()
        mime_type = str(payload.get("mime_type") or "image/png").strip()
        if "," in img_b64 and img_b64.startswith("data:"):
            hdr, img_b64 = img_b64.split(",", 1)
            if ":" in hdr and ";" in hdr:
                mime_type = hdr.split(":", 1)[1].split(";", 1)[0]
    else:
        section_key = str(request.form.get("section_key") or "learning_plan").strip()
        ocr_mode = str(request.form.get("ocr_mode") or "default").strip().lower()
        gemini_key = str(request.form.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or "").strip()
        raw_text_in = str(request.form.get("raw_text") or "").strip()
        img_b64 = ""
        mime_type = "image/png"
        up_file = request.files.get("image") or request.files.get("file")
        if up_file and up_file.filename:
            raw_bytes = up_file.read()
            mime_type = up_file.mimetype or "image/png"
            img_b64 = base64.b64encode(raw_bytes).decode("ascii")

    if section_key not in _SYLLABUS_OCR_SECTION_PROMPTS:
        return jsonify({"error": f"Unknown syllabus section '{section_key}'."}), 400

    # 1. If explicit raw text was sent without an image, parse directly
    if raw_text_in and not img_b64:
        parsed = _parse_ocr_raw_text_fallback(section_key, raw_text_in)
        return jsonify({
            "success": True,
            "engine": "structured_text_parser",
            "section_key": section_key,
            "raw_text": raw_text_in,
            "data": parsed,
        })

    if not img_b64 and not raw_text_in:
        return jsonify({"error": "Please upload an image, paste a screenshot (Ctrl+V), or provide extracted text."}), 400

    # 2. Specialized Vision Model Override (when chosen under Advanced or an explicit API key was supplied)
    explicit_req_key = str((payload or request.form).get("gemini_api_key") or "").strip()
    use_specialized_gemini = bool(
        gemini_key and (ocr_mode.startswith("gemini") or bool(explicit_req_key))
    )
    if use_specialized_gemini:
        model_id = "gemini-2.5-pro" if "pro" in ocr_mode else "gemini-2.5-flash"
        prompt = (
            "You are performing strict OCR and structured extraction on an engineering course syllabus screenshot "
            "for the University of Southeastern Philippines (USeP FM-USeP-MID-01).\n"
            f"{_SYLLABUS_OCR_SECTION_PROMPTS[section_key]}\n"
            "Return ONLY valid JSON without markdown code fences or commentary."
        )
        try:
            resp_g = _req.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={gemini_key}",
                json={
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": mime_type, "data": img_b64}},
                        ]
                    }]
                },
                timeout=45,
            )
            if not resp_g.ok:
                err_msg = f"Specialized Vision model returned HTTP {resp_g.status_code}."
                return jsonify({"success": False, "error": err_msg, "section_key": section_key}), 502

            raw_cand = (
                resp_g.json()
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_cand, flags=re.IGNORECASE).strip()
            try:
                parsed_json = _json.loads(cleaned)
                if not isinstance(parsed_json, dict):
                    parsed_json = {"items": parsed_json}
                return jsonify({
                    "success": True,
                    "engine": "gemini_vision",
                    "model": model_id,
                    "section_key": section_key,
                    "raw_text": raw_cand,
                    "data": parsed_json,
                })
            except Exception:
                parsed = _parse_ocr_raw_text_fallback(section_key, cleaned)
                return jsonify({
                    "success": True,
                    "engine": "gemini_vision_text_fallback",
                    "model": model_id,
                    "section_key": section_key,
                    "raw_text": cleaned,
                    "data": parsed,
                })
        except Exception as exc:
            if ocr_mode.startswith("gemini"):
                return jsonify({"success": False, "error": f"Specialized Vision OCR failed: {exc}", "section_key": section_key}), 502

    # 3. Default Built-In Out-of-the-Box Local OCR Engine (Tesseract / Native Windows WinRT OCR)
    try:
        raw_img_bytes = base64.b64decode(img_b64)
        ocr_text, eng_name = _run_built_in_local_ocr(raw_img_bytes)
        if ocr_text:
            parsed = _parse_ocr_raw_text_fallback(section_key, ocr_text)
            return jsonify({
                "success": True,
                "engine": eng_name,
                "section_key": section_key,
                "raw_text": ocr_text,
                "data": parsed,
            })
        return jsonify({
            "success": True,
            "engine": "built_in_default_ocr",
            "section_key": section_key,
            "raw_text": "",
            "data": {},
            "warning": "No readable text detected in this image. You can paste/type text directly in the Raw Text box or select a specialized Vision model under Advanced.",
        })
    except Exception as exc:
        return jsonify({
            "success": False,
            "section_key": section_key,
            "error": f"Built-in OCR could not process the uploaded image: {exc}",
        }), 400


@app.route("/api/admin/faculty-list", methods=["GET"])
def api_admin_faculty_list():
    user = current_user()
    if not user or user.get("role") != "admin":
        return jsonify({"error": "Admin access required."}), 403
    from auth import _load_users
    users = _load_users()
    rows = []
    for uname, u in users.items():
        if uname.startswith("committee_") or uname.startswith("programhead_"):
            continue
        rows.append({
            "username": uname,
            "full_name": u.get("full_name") or uname,
            "role": u.get("role") or "faculty",
            "position_title": u.get("position_title") or "Faculty Member",
            "workflow_roles": u.get("workflow_roles") or [],
            "program_codes": u.get("program_codes") or ["EE"],
            "college": u.get("college") or "COLLEGE OF ENGINEERING",
        })
    rows.sort(key=lambda x: x["full_name"])
    return jsonify({"faculty": rows})


@app.route("/api/admin/users/<username>/update-role", methods=["POST"])
def api_admin_update_user_role(username):
    user = current_user()
    if not user or user.get("role") != "admin":
        return jsonify({"error": "Admin access required."}), 403
    from auth import _load_users, _save_users, _lock
    import auth
    data = request.get_json(silent=True) or {}

    roles = data.get("roles")
    if not roles and data.get("designation"):
        roles = [data.get("designation")]
    prog_codes = data.get("program_codes")
    if not prog_codes and data.get("program_code"):
        prog_codes = [data.get("program_code")]
    custom_title = (data.get("position_title") or "").strip()
    is_admin_flag = bool(data.get("is_admin")) or ("admin" in (roles or []))

    with _lock:
        all_users = _load_users()
        uname = auth.LEGACY_USERNAME_ALIASES.get(username, username)
        if uname not in all_users:
            return jsonify({"error": f"Faculty account '{username}' not found."}), 404
        target = all_users[uname]

        auth.apply_roles_to_user_dict(target, roles, prog_codes, custom_title, is_admin_flag)

        _save_users(all_users)

    return jsonify({
        "success": True,
        "message": f"Successfully updated role for {target.get('full_name') or uname} to {target.get('position_title')}.",
        "user": {
            "username": uname,
            "full_name": target.get("full_name"),
            "role": target.get("role"),
            "position_title": target.get("position_title"),
            "workflow_roles": target.get("workflow_roles"),
            "program_codes": target.get("program_codes"),
        }
    })

def _calculate_single_student_performance(st, categories, clos, meta, ttable, passing_pct, course_id=None):
    """
    Computes performance metrics, CLO competency grades, and item breakdown for a single student.
    """
    st_scores = st.get("scores") or {}
    st_clo_scores = st.get("clo_scores") or st.get("scores") or {}

    grading_type = str(meta.get("grading_system_type") or "two_term").lower()
    mid_wt = float(meta.get("midterm_weight") if meta.get("midterm_weight") is not None else 50.0)
    fin_wt = float(meta.get("finals_weight") if meta.get("finals_weight") is not None else 50.0)
    prj_wt = float(meta.get("project_weight") if meta.get("project_weight") is not None else 0.0)
    lec_wt = float(meta.get("lecture_weight") if meta.get("lecture_weight") is not None else 75.0)
    lab_wt = float(meta.get("lab_weight") if meta.get("lab_weight") is not None else 25.0)

    term_scores = {"Midterm": {"earned_wt": 0.0, "total_wt": 0.0}, "Finals": {"earned_wt": 0.0, "total_wt": 0.0}, "Major Assessment": {"earned_wt": 0.0, "total_wt": 0.0}}
    cats_data = []
    clo_points_earned = {co.get("co_id", "").upper(): 0.0 for co in clos}
    clo_points_possible = {co.get("co_id", "").upper(): 0.0 for co in clos}
    item_pcts = {}
    item_raw_scores = {}

    for cat in categories:
        term = cat.get("term", "Midterm")
        if term not in term_scores:
            term_scores[term] = {"earned_wt": 0.0, "total_wt": 0.0}
        a_type = (cat.get("assessment_type") or "SA").upper()
        cat_wt = float(cat.get("weight_pct") or 0.0)
        is_summative = (a_type in ("SA", "SUMMATIVE") or (a_type not in ("FA", "FORMATIVE") and cat_wt > 0))
        a_code = (cat.get("assessment_code") or ("SA1" if is_summative else "FA1")).upper()
        items = cat.get("items") or []
        n_items = max(1, len(items))
        def_item_wt = cat_wt / n_items if is_summative else 0.0

        items_breakdown = []
        for it in items:
            item_id = it.get("item_id", "")
            name = it.get("name") or item_id
            pts_map = it.get("clo_points") or {}
            raw_clos = it.get("co_id") or it.get("aligned_clos") or []
            if isinstance(raw_clos, str):
                aligned_clos = [c.strip().upper() for c in raw_clos.replace(";", ",").split(",") if c.strip()]
            else:
                aligned_clos = [str(c).strip().upper() for c in raw_clos if str(c).strip()]

            it_wt = float(it.get("weight_pct") or 0.0) if is_summative else 0.0
            if it_wt <= 0 and is_summative:
                it_wt = def_item_wt

            tot_max = sum(float(pts_map.get(c, 0.0)) for c in aligned_clos) if pts_map else float(it.get("max_score") or 30.0)
            if tot_max <= 0:
                tot_max = float(it.get("max_score") or 30.0)

            st_raw = 0.0
            has_clo_entry = False
            for c in aligned_clos:
                c_key = f"{item_id}__{c}"
                if c_key in st_clo_scores and st_clo_scores[c_key] is not None and str(st_clo_scores[c_key]).strip() != "":
                    st_raw += float(st_clo_scores[c_key] or 0.0)
                    has_clo_entry = True
                    clo_points_earned[c] = clo_points_earned.get(c, 0.0) + float(st_clo_scores[c_key] or 0.0)
                c_max = float(pts_map.get(c, 0.0)) if pts_map else (tot_max / max(1, len(aligned_clos)))
                clo_points_possible[c] = clo_points_possible.get(c, 0.0) + c_max

            has_direct_entry = False
            if not has_clo_entry and item_id in st_scores and st_scores[item_id] is not None and str(st_scores[item_id]).strip() != "":
                has_direct_entry = True
                st_raw = float(st_scores[item_id] or 0.0)
            is_recorded = bool(has_clo_entry or has_direct_entry)

            pct = (st_raw / tot_max * 100.0) if tot_max > 0 else 0.0
            item_pcts[item_id] = round(pct, 1)
            item_raw_scores[item_id] = round(st_raw, 1)

            if is_summative and tot_max > 0:
                is_standalone_project = (term == "Major Assessment" or (cat.get("major_scope") == "independent" and cat.get("is_major_assessment")))
                is_separate_project = (grading_type in ("term_project", "lecture_major") and is_standalone_project)
                if not is_separate_project:
                    term_scores[term]["earned_wt"] += (st_raw / tot_max) * it_wt
                    term_scores[term]["total_wt"] += it_wt

            # Check assessment score acknowledgment
            ack_map = st.get("assessment_acknowledgments") or {}
            item_ack = ack_map.get(item_id) or {}
            is_acked = bool(item_ack.get("acknowledged"))
            acked_at = item_ack.get("acknowledged_at") or ""
            sig_data = item_ack.get("signature_data") or ""
            if not is_acked or not sig_data:
                try:
                    from student_store import _load_students, _normalize_id
                    all_s = _load_students()
                    st_norm = _normalize_id(st.get("student_id") or "")
                    s_prof = all_s.get(st_norm) or {}
                    s_acks = (s_prof.get("assessment_acknowledgments") or {}).get(course_id) or {}
                    if item_id in s_acks and s_acks[item_id].get("acknowledged"):
                        is_acked = True
                        if not acked_at:
                            acked_at = s_acks[item_id].get("acknowledged_at") or ""
                        if not sig_data:
                            sig_data = s_acks[item_id].get("signature_data") or ""
                    if not sig_data:
                        sig_data = s_prof.get("signature_data") or ""
                except Exception:
                    pass

            items_breakdown.append({
                "item_id": item_id,
                "name": name,
                "max_score": round(tot_max, 1),
                "is_recorded": is_recorded,
                "student_score": round(st_raw, 1),
                "percentage": round(pct, 1),
                "weight_pct": round(it_wt, 1) if a_type == "SA" else 0.0,
                "aligned_clos": aligned_clos,
                "acknowledged": is_acked,
                "acknowledged_at": acked_at,
                "signature_data": sig_data,
            })

        cat_weighted_ratio_sum = 0.0
        cat_weight_sum = 0.0
        for it in items_breakdown:
            it_max = float(it.get("max_score", 0.0) or 0.0)
            it_sc = float(it.get("student_score", 0.0) or 0.0)
            it_w = float(it.get("weight_pct", 0.0) or 0.0)
            if it_w <= 0:
                it_w = 1.0
            if it_max > 0:
                cat_weighted_ratio_sum += (it_sc / it_max) * it_w
                cat_weight_sum += it_w

        cat_grade = round(((cat_weighted_ratio_sum / cat_weight_sum) * 50.0 + 50.0), 2) if cat_weight_sum > 0 else 50.0
        cats_data.append({
            "term": term,
            "category_name": cat.get("name") or "Assessment Category",
            "assessment_type": a_type,
            "assessment_code": a_code,
            "lec_lab": cat.get("lec_lab") or "Lecture",
            "assessment_grade": cat_grade,
            "weight_pct": cat_wt,
            "items": items_breakdown,
        })

    grading_type = str(meta.get("grading_system_type") or "two_term").lower()
    mid_wt = float(meta.get("midterm_weight") if meta.get("midterm_weight") is not None else 50.0)
    fin_wt = float(meta.get("finals_weight") if meta.get("finals_weight") is not None else 50.0)
    prj_wt = float(meta.get("project_weight") if meta.get("project_weight") is not None else 0.0)
    lec_wt = float(meta.get("lecture_weight") if meta.get("lecture_weight") is not None else 75.0)
    lab_wt = float(meta.get("lab_weight") if meta.get("lab_weight") is not None else 25.0)

    mg_ratio = (term_scores["Midterm"]["earned_wt"] / term_scores["Midterm"]["total_wt"]) if term_scores["Midterm"]["total_wt"] > 0 else 0.5
    fg_ratio = (term_scores["Finals"]["earned_wt"] / term_scores["Finals"]["total_wt"]) if term_scores["Finals"]["total_wt"] > 0 else 0.5
    mg = round(mg_ratio * 50.0 + 50.0, 1)
    fg = round(fg_ratio * 50.0 + 50.0, 1)

    standalone_maj_cats = [c for c in cats_data if c.get("term") == "Major Assessment" or (c.get("is_major_assessment") and c.get("term") not in ("Midterm", "Finals"))]
    maj_weighted_sum = sum(c["assessment_grade"] * float(c.get("weight_pct", 0.0) or 0.0) for c in standalone_maj_cats)
    standalone_maj_total_wt = sum(float(c.get("weight_pct", 0.0) or 0.0) for c in standalone_maj_cats)
    maj_grade = round(maj_weighted_sum / standalone_maj_total_wt, 1) if standalone_maj_total_wt > 0 else round((mg + fg) / 2.0, 1)

    if grading_type == "term_project":
        effective_prj_wt = standalone_maj_total_wt if standalone_maj_total_wt > 0 else prj_wt
        maj_contrib = maj_weighted_sum if standalone_maj_total_wt > 0 else (maj_grade * effective_prj_wt)
        tot_wt = (mid_wt + fin_wt + effective_prj_wt) or 100.0
        afg = round(((mg * mid_wt) + (fg * fin_wt) + maj_contrib) / tot_wt, 1)
    elif grading_type == "lecture_major":
        lec_cats = [c for c in cats_data if c.get("term") != "Major Assessment" and not (c.get("is_major_assessment") and c.get("term") not in ("Midterm", "Finals")) and c.get("assessment_type") == "SA"]
        lec_grade = round(sum(c["assessment_grade"] * (c.get("weight_pct", 1.0) or 1.0) for c in lec_cats) / sum((c.get("weight_pct", 1.0) or 1.0) for c in lec_cats), 1) if lec_cats else round((mg + fg) / 2.0, 1)
        effective_prj_wt = standalone_maj_total_wt if standalone_maj_total_wt > 0 else prj_wt
        maj_contrib = maj_weighted_sum if standalone_maj_total_wt > 0 else (maj_grade * effective_prj_wt)
        tot_wt = (lec_wt + effective_prj_wt) or 100.0
        afg = round(((lec_grade * lec_wt) + maj_contrib) / tot_wt, 1)
    elif grading_type == "lecture_lab":
        lec_cats = [c for c in cats_data if (c.get("lec_lab") or "lecture").lower() != "laboratory" and c.get("assessment_type") == "SA" and c.get("term") != "Major Assessment"]
        lab_cats = [c for c in cats_data if (c.get("lec_lab") or "").lower() == "laboratory" and c.get("assessment_type") == "SA" and c.get("term") != "Major Assessment"]
        lec_grade = round(sum(c["assessment_grade"] * (c.get("weight_pct", 1.0) or 1.0) for c in lec_cats) / sum((c.get("weight_pct", 1.0) or 1.0) for c in lec_cats), 1) if lec_cats else round((mg + fg) / 2.0, 1)
        lab_grade = round(sum(c["assessment_grade"] * (c.get("weight_pct", 1.0) or 1.0) for c in lab_cats) / sum((c.get("weight_pct", 1.0) or 1.0) for c in lab_cats), 1) if lab_cats else round((mg + fg) / 2.0, 1)
        maj_contrib = maj_weighted_sum if standalone_maj_total_wt > 0 else 0.0
        tot_wt = (lec_wt + lab_wt + standalone_maj_total_wt) or 100.0
        afg = round(((lec_grade * lec_wt) + (lab_grade * lab_wt) + maj_contrib) / tot_wt, 1)
    else:
        if standalone_maj_total_wt > 0:
            # Term grades share the remaining (100 - majors)% in the midterm:final ratio
            term_share = max(0.0, 100.0 - standalone_maj_total_wt)
            term_avg = ((mg * mid_wt) + (fg * fin_wt)) / ((mid_wt + fin_wt) or 100.0)
            afg = round(((term_avg * term_share) + maj_weighted_sum) / ((term_share + standalone_maj_total_wt) or 100.0), 1)
        else:
            tot_wt = (mid_wt + fin_wt) or 100.0
            afg = round(((mg * mid_wt) + (fg * fin_wt)) / tot_wt, 1)
    passed = afg >= passing_pct

    final_gp = "5.00"
    for r in ttable:
        if r["min_pct"] <= afg <= r["max_pct"]:
            g = r["grade"]
            final_gp = f"{g:.2f}" if isinstance(g, float) else str(g)
            break
    if afg >= 98.0:
        final_gp = "1.00"

    clo_summary = []
    clo_grades_map = {}
    for co in clos:
        cid = co.get("co_id", "").upper()
        matching_cols = []
        for cat in categories:
            a_type = (cat.get("assessment_type") or "SA").upper()
            cat_wt = float(cat.get("weight_pct") or 0.0)
            is_summative = (a_type in ("SA", "SUMMATIVE") or (a_type not in ("FA", "FORMATIVE") and cat_wt > 0))
            items = cat.get("items") or []
            n_items = max(1, len(items))
            def_item_wt = cat_wt / n_items if is_summative else 0.0
            for it in items:
                it_id = it.get("item_id", "")
                pts_map = it.get("clo_points") or {}
                raw_clos = it.get("co_id") or it.get("aligned_clos") or []
                if isinstance(raw_clos, str):
                    aligned = [c.strip().upper() for c in raw_clos.replace(";", ",").split(",") if c.strip()]
                else:
                    aligned = [str(c).strip().upper() for c in raw_clos if str(c).strip()]

                if cid in aligned:
                    tot_max = sum(float(pts_map.get(c, 0.0)) for c in aligned) if pts_map else float(it.get("max_score") or 30.0)
                    if tot_max <= 0:
                        tot_max = float(it.get("max_score") or 30.0)
                    clo_max = float(pts_map.get(cid, 0.0)) if pts_map else (tot_max / max(1, len(aligned)))
                    if clo_max <= 0:
                        clo_max = tot_max / max(1, len(aligned))

                    it_wt = float(it.get("weight_pct") or 0.0) if is_summative else 0.0
                    if it_wt <= 0 and is_summative:
                        it_wt = def_item_wt

                    c_key = f"{it_id}__{cid}"
                    if c_key in st_clo_scores:
                        st_sc = float(st_clo_scores[c_key] or 0.0)
                    else:
                        m_num = re.search(r"(\d+)$", cid)
                        legacy_key = f"{it_id}_{m_num.group(1)}" if m_num else None
                        if legacy_key and legacy_key in st_clo_scores:
                            st_sc = float(st_clo_scores[legacy_key] or 0.0)
                        elif it_id in st_scores:
                            st_sc = float(st_scores[it_id] or 0.0) * (clo_max / tot_max if tot_max > 0 else 1.0)
                        else:
                            st_sc = 0.0
                    matching_cols.append({
                        "a_type": "SA" if is_summative else "FA",
                        "weight": it_wt,
                        "score": st_sc,
                        "max_score": clo_max,
                    })

        sa_matching = [m for m in matching_cols if m["a_type"] == "SA"]
        calc_matching = sa_matching if sa_matching else matching_cols
        clo_num = sum((m["score"] / m["max_score"]) * m["weight"] for m in calc_matching if m["max_score"] > 0)
        clo_den = sum(m["weight"] for m in calc_matching)
        final_clo_grade = round((clo_num / clo_den * 50.0 + 50.0), 2) if clo_den > 0 else 50.0

        target = float(co.get("target_score_pct") or 75.0)
        is_competent = final_clo_grade >= target
        p_earned = clo_points_earned.get(cid, 0.0)
        p_poss = clo_points_possible.get(cid, 0.0)

        clo_grades_map[cid] = final_clo_grade
        clo_summary.append({
            "co_id": cid,
            "description": co.get("description", ""),
            "final_clo_grade": final_clo_grade,
            "target_score_pct": target,
            "is_competent": is_competent,
            "status_label": "Competent" if is_competent else "Developing",
            "points_earned": round(p_earned, 1),
            "points_possible": round(p_poss, 1),
        })

    return {
        "midterm_grade": mg,
        "finals_grade": fg,
        "average_final_grade": afg,
        "transmuted_grade": final_gp,
        "passed": passed,
        "clo_summary": clo_summary,
        "clo_grades": clo_grades_map,
        "categories": cats_data,
        "item_pcts": item_pcts,
        "item_raw_scores": item_raw_scores,
    }


def _compute_baseline_passing_recommendations(matched_st, categories, clos, meta, ttable, passing_pct, course_id):
    """
    Computes baseline scores on unrecorded summative assessments so the student
    knows how many points are needed to achieve a passing grade (AFG >= passing_pct / Grade 3.00).
    Assessments that already have a recorded score are automatically excluded from the recommendations.
    """
    st_scores = matched_st.get("scores") or {}
    st_clo_scores = matched_st.get("clo_scores") or {}

    unrecorded_items = []
    recorded_items = []

    for cat in categories:
        a_type = (cat.get("assessment_type") or "SA").upper()
        cat_wt = float(cat.get("weight_pct") or 0.0)
        is_summative = (a_type in ("SA", "SUMMATIVE") or (a_type not in ("FA", "FORMATIVE") and cat_wt > 0))
        if not is_summative:
            continue

        for it in (cat.get("items") or []):
            item_id = it.get("item_id", "")
            pts_map = it.get("clo_points") or {}
            raw_clos = it.get("co_id") or it.get("aligned_clos") or []
            if isinstance(raw_clos, str):
                aligned_clos = [c.strip().upper() for c in raw_clos.replace(";", ",").split(",") if c.strip()]
            else:
                aligned_clos = [str(c).strip().upper() for c in raw_clos if str(c).strip()]

            tot_max = sum(float(pts_map.get(c, 0.0)) for c in aligned_clos) if pts_map else float(it.get("max_score") or 30.0)
            if tot_max <= 0:
                tot_max = float(it.get("max_score") or 30.0)

            has_clo_entry = any(
                (f"{item_id}__{c}" in st_clo_scores and st_clo_scores[f"{item_id}__{c}"] is not None and str(st_clo_scores[f"{item_id}__{c}"]).strip() != "")
                for c in aligned_clos
            )
            has_direct_score = (
                item_id in st_scores and st_scores[item_id] is not None and str(st_scores[item_id]).strip() != ""
            )

            if has_clo_entry or has_direct_score:
                recorded_items.append({"item_id": item_id, "max_score": tot_max})
            else:
                unrecorded_items.append({"item_id": item_id, "max_score": tot_max, "term": cat.get("term") or "Midterm"})

    unrecorded_count = len(unrecorded_items)
    if unrecorded_count == 0:
        return {
            "unrecorded_count": 0,
            "passing_status": "all_recorded",
            "required_pct": None,
            "target_grade": passing_pct,
            "message": "All assessment activities have recorded grades.",
            "item_targets": {it["item_id"]: {"is_recorded": True, "target_score": None, "target_pct": None, "max_score": it["max_score"]} for it in recorded_items}
        }

    def _sim_afg(r_val):
        mock_st = copy.deepcopy(matched_st)
        mock_scores = dict(mock_st.get("scores") or {})
        mock_clo_scores = dict(mock_st.get("clo_scores") or {})
        for unrec in unrecorded_items:
            iid = unrec["item_id"]
            m_score = r_val * unrec["max_score"]
            mock_scores[iid] = m_score
            mock_clo_scores[iid] = m_score
        mock_st["scores"] = mock_scores
        mock_st["clo_scores"] = mock_clo_scores
        perf = _calculate_single_student_performance(mock_st, categories, clos, meta, ttable, passing_pct, course_id)
        return perf["average_final_grade"]

    afg_0 = _sim_afg(0.0)
    afg_1 = _sim_afg(1.0)

    if afg_0 >= passing_pct:
        status = "already_passed"
        r_req = 0.0
        r_pct = 0.0
        msg = f"Your recorded scores have already secured a passing mark for this course (AFG ≥ {passing_pct:.1f}%). 0 additional points needed to pass."
    elif afg_1 < passing_pct:
        status = "critical"
        r_req = 1.0
        r_pct = round(((passing_pct - afg_0) / max(0.01, afg_1 - afg_0)) * 100.0, 1)
        msg = f"Passing this course (AFG ≥ {passing_pct:.1f}%) requires maximum possible performance on all remaining unrecorded assessments. Please consult your instructor during consultation hours."
    else:
        status = "achievable"
        r_req = (passing_pct - afg_0) / max(0.001, (afg_1 - afg_0))
        r_req = max(0.0, min(1.0, r_req))
        r_pct = round(r_req * 100.0, 1)
        msg = f"To achieve a passing grade of {passing_pct:.1f}% (Grade 3.00), you need an average baseline score of {r_pct:.1f}% across your {unrecorded_count} unrecorded assessment(s)."

    item_targets = {}
    for it in recorded_items:
        item_targets[it["item_id"]] = {
            "is_recorded": True,
            "target_score": None,
            "target_pct": None,
            "max_score": it["max_score"]
        }

    for it in unrecorded_items:
        target_score = round(r_req * it["max_score"], 1)
        item_targets[it["item_id"]] = {
            "is_recorded": False,
            "target_score": target_score,
            "target_pct": r_pct,
            "max_score": it["max_score"]
        }

    return {
        "unrecorded_count": unrecorded_count,
        "passing_status": status,
        "required_pct": r_pct,
        "target_grade": passing_pct,
        "message": msg,
        "item_targets": item_targets
    }


@app.route("/api/student/courses/<course_id>/performance", methods=["GET"])
def api_student_course_performance(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401

    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    students = bp.get("students") or []
    categories = bp.get("categories") or []
    clos = bp.get("course_outcomes") or bp.get("clos") or []

    passing_pct = float(meta.get("passing_percentage") or 75.0)
    from models import build_transmutation_table
    ttable = build_transmutation_table(passing_pct)

    req_sid = (request.args.get("student_id") or "").strip().lower()
    if req_sid and user.get("role") != "student":
        sid = req_sid
    else:
        sid = (user.get("student_id") or user.get("username") or "").strip().lower()

    sid_digits = re.sub(r"\D", "", sid)
    matched_st = None
    for st in students:
        curr_sid = str(st.get("student_id") or "").strip().lower()
        curr_digits = re.sub(r"\D", "", curr_sid)
        st_full = f"{st.get('last_name', '')}, {st.get('first_name', '')}".strip(", ").lower()
        st_name = str(st.get("name") or "").strip().lower()
        if (curr_sid and curr_sid == sid) or \
           (curr_digits and sid_digits and len(curr_digits) >= 4 and curr_digits == sid_digits) or \
           (user.get("full_name") and user["full_name"].lower() in (st_full, st_name)):
            matched_st = st
            break

    # If faculty/admin is previewing and not found, show first student or fallback
    if not matched_st and user.get("role") != "student" and students:
        matched_st = students[0]

    if not matched_st:
        matched_st = {
            "student_id": user.get("student_id") or user.get("username"),
            "name": user.get("full_name") or "Enrolled Student",
            "scores": {},
            "clo_scores": {},
        }

    # 1. Compute target student's individual performance
    matched_perf = _calculate_single_student_performance(matched_st, categories, clos, meta, ttable, passing_pct, course_id)

    # 2. Compute performance across all enrolled students in the class
    class_students = students if students else [matched_st]
    all_perf = []
    for s in class_students:
        p = _calculate_single_student_performance(s, categories, clos, meta, ttable, passing_pct, course_id)
        all_perf.append(p)

    n_st = len(all_perf)
    all_afg_list = [p["average_final_grade"] for p in all_perf]
    all_mg_list = [p["midterm_grade"] for p in all_perf]
    all_fg_list = [p["finals_grade"] for p in all_perf]

    class_avg_afg = round(sum(all_afg_list) / n_st, 1) if n_st else matched_perf["average_final_grade"]
    class_avg_midterm = round(sum(all_mg_list) / n_st, 1) if n_st else matched_perf["midterm_grade"]
    class_avg_finals = round(sum(all_fg_list) / n_st, 1) if n_st else matched_perf["finals_grade"]
    class_highest_afg = round(max(all_afg_list), 1) if all_afg_list else matched_perf["average_final_grade"]
    class_lowest_afg = round(min(all_afg_list), 1) if all_afg_list else matched_perf["average_final_grade"]
    pass_cnt = sum(1 for p in all_perf if p["passed"])
    class_passing_rate = round((pass_cnt / n_st * 100.0), 1) if n_st else 100.0

    class_avg_transmuted = "5.00"
    for r in ttable:
        if r["min_pct"] <= class_avg_afg <= r["max_pct"]:
            g = r["grade"]
            class_avg_transmuted = f"{g:.2f}" if isinstance(g, float) else str(g)
            break
    if class_avg_afg >= 98.0:
        class_avg_transmuted = "1.00"

    # CLO class averages
    class_clo_averages = {}
    for co in clos:
        cid = co.get("co_id", "").upper()
        c_vals = [p["clo_grades"].get(cid, 50.0) for p in all_perf]
        class_clo_averages[cid] = round(sum(c_vals) / len(c_vals), 2) if c_vals else 50.0

    # Assessment item class averages
    class_item_averages = {}
    for cat in categories:
        for it in (cat.get("items") or []):
            iid = it.get("item_id", "")
            p_vals = [p["item_pcts"].get(iid, 0.0) for p in all_perf]
            r_vals = [p["item_raw_scores"].get(iid, 0.0) for p in all_perf]
            class_item_averages[iid] = {
                "avg_percentage": round(sum(p_vals) / len(p_vals), 1) if p_vals else 0.0,
                "avg_score": round(sum(r_vals) / len(r_vals), 1) if r_vals else 0.0,
            }

    # 3. Student vs Class Comparison metrics
    afg_diff = round(matched_perf["average_final_grade"] - class_avg_afg, 1)
    mg_diff = round(matched_perf["midterm_grade"] - class_avg_midterm, 1)
    fg_diff = round(matched_perf["finals_grade"] - class_avg_finals, 1)

    sorted_afgs = sorted(all_afg_list, reverse=True)
    try:
        student_rank = sorted_afgs.index(matched_perf["average_final_grade"]) + 1
    except ValueError:
        student_rank = 1

    percentile = round((student_rank / max(1, n_st)) * 100.0, 1)

    if afg_diff >= 2.0:
        standing_label = "Above Class Average"
    elif afg_diff <= -2.0:
        standing_label = "Below Class Average"
    else:
        standing_label = "At Class Average"

    # Merge benchmark into CLO summary
    for c_entry in matched_perf["clo_summary"]:
        cid = c_entry["co_id"]
        c_avg = class_clo_averages.get(cid, 50.0)
        c_diff = round(c_entry["final_clo_grade"] - c_avg, 2)
        c_entry["class_avg_grade"] = c_avg
        c_entry["variance_vs_avg"] = c_diff
        c_entry["is_above_avg"] = (c_diff >= 0)

    # Merge benchmark into categories / items breakdown
    for cat_entry in matched_perf["categories"]:
        for it_entry in cat_entry.get("items", []):
            iid = it_entry["item_id"]
            c_stats = class_item_averages.get(iid, {"avg_percentage": 0.0, "avg_score": 0.0})
            it_diff = round(it_entry["percentage"] - c_stats["avg_percentage"], 1)
            it_entry["class_avg_percentage"] = c_stats["avg_percentage"]
            it_entry["class_avg_score"] = c_stats["avg_score"]
            it_entry["variance_vs_avg"] = it_diff
            it_entry["is_above_avg"] = (it_diff >= 0)

    # 3b. Compute baseline passing recommendations for unrecorded assessments
    passing_recommendation = _compute_baseline_passing_recommendations(
        matched_st, categories, clos, meta, ttable, passing_pct, course_id
    )
    item_targets = passing_recommendation.get("item_targets", {})
    for cat_entry in matched_perf["categories"]:
        for it_entry in cat_entry.get("items", []):
            iid = it_entry.get("item_id")
            rec_target = item_targets.get(iid)
            if rec_target:
                it_entry["is_recorded"] = rec_target.get("is_recorded", it_entry.get("is_recorded", False))
                it_entry["target_score"] = rec_target.get("target_score")
                it_entry["target_pct"] = rec_target.get("target_pct")
            else:
                it_entry["target_score"] = None
                it_entry["target_pct"] = None

    # 4. Enrolled courses list for fast switching between courses in dashboard
    all_enrolled_courses = []
    try:
        import student_store
        st_courses_data = student_store.find_courses_for_student(matched_st.get("student_id") or sid)
        seen_cids = set()
        for group_key in ("pending", "acknowledged", "in_review"):
            for sc in st_courses_data.get(group_key, []):
                cid_key = sc.get("course_id")
                if cid_key and cid_key not in seen_cids:
                    seen_cids.add(cid_key)
                    all_enrolled_courses.append({
                        "course_id": cid_key,
                        "course_code": sc.get("course_code"),
                        "course_title": sc.get("course_title"),
                        "section": sc.get("section"),
                        "semester_ay": sc.get("semester_ay"),
                        "is_current": (cid_key == course_id)
                    })
    except Exception:
        pass

    # 4b. Per-Course Exit Survey & Final Grade Visibility Gate
    unrecorded_count = int(passing_recommendation.get("unrecorded_count", 0))
    total_sa_items = sum(
        len(c.get("items") or [])
        for c in categories
        if (c.get("assessment_type") or "SA").upper() in ("SA", "SUMMATIVE")
        or ((c.get("assessment_type") or "SA").upper() not in ("FA", "FORMATIVE") and float(c.get("weight_pct") or 0.0) > 0)
    )
    cr_approved = ((doc.get("class_record_workflow") or {}).get("status") == "approved")
    all_assessments_finalized = bool((total_sa_items > 0 and unrecorded_count == 0) or cr_approved)

    matched_sid = str(matched_st.get("student_id") or user.get("student_id") or user.get("username") or "").strip()
    survey_rec = None
    try:
        import db_persistence
        survey_rec = db_persistence.get_student_survey_response_db(matched_sid, course_id)
    except Exception:
        survey_rec = None

    survey_completed = bool(survey_rec and survey_rec.get("is_completed"))
    final_grade_unlocked = bool(all_assessments_finalized and survey_completed)

    grades_payload = {
        "midterm_grade": matched_perf["midterm_grade"],
        "finals_grade": matched_perf["finals_grade"] if final_grade_unlocked else None,
        "average_final_grade": matched_perf["average_final_grade"] if final_grade_unlocked else None,
        "transmuted_grade": matched_perf["transmuted_grade"] if final_grade_unlocked else None,
        "passed": matched_perf["passed"] if final_grade_unlocked else None,
        "status_label": (
            ("PASSED" if matched_perf["passed"] else "IN PROGRESS / DEFICIENT")
            if final_grade_unlocked
            else ("LOCKED_SURVEY_REQUIRED" if (all_assessments_finalized and not survey_completed) else "PENDING_COMPLETION")
        ),
        "passing_cutoff": passing_pct,
    }

    return jsonify({
        "success": True,
        "student": {
            "student_id": matched_st.get("student_id"),
            "name": matched_st.get("name") or (f"{matched_st.get('last_name')}, {matched_st.get('first_name')}".strip(", ") if (matched_st.get('last_name') or matched_st.get('first_name')) else (matched_st.get('student_id') or "Student")),
            "program_year": matched_st.get("program_year") or meta.get("section") or "",
        },
        "course": {
            "course_id": course_id,
            "course_code": doc.get("course_code") or meta.get("course_code"),
            "course_title": doc.get("course_title") or meta.get("course_title"),
            "credit_units": doc.get("credit_units") or meta.get("credit_units"),
            "section": doc.get("section") or meta.get("section"),
            "semester_ay": doc.get("semester_ay") or meta.get("semester_ay"),
            "faculty_name": doc.get("faculty_name") or meta.get("faculty_name"),
            "consultation_hours": meta.get("consultation_hours") or "Monday-Friday 8:00 AM - 5:00 PM",
            "schedule": meta.get("schedule") or "TBA",
        },
        "all_enrolled_courses": all_enrolled_courses,
        "grade_visibility": {
            "all_assessments_finalized": all_assessments_finalized,
            "unrecorded_count": unrecorded_count,
            "total_sa_items": total_sa_items,
            "survey_completed": survey_completed,
            "survey_submitted_at": survey_rec.get("submitted_at") if survey_rec else None,
            "final_grade_unlocked": final_grade_unlocked,
            "lock_reason": (
                None if final_grade_unlocked else (
                    "survey_required" if (all_assessments_finalized and not survey_completed) else "pending_grades"
                )
            ),
        },
        "grades": grades_payload,
        "class_average": {
            "midterm_grade": class_avg_midterm,
            "finals_grade": class_avg_finals,
            "average_final_grade": class_avg_afg,
            "class_avg_midterm": class_avg_midterm,
            "class_avg_finals": class_avg_finals,
            "class_avg_afg": class_avg_afg,
            "transmuted_grade": class_avg_transmuted,
            "class_avg_transmuted": class_avg_transmuted,
            "highest_afg": class_highest_afg,
            "lowest_afg": class_lowest_afg,
            "passing_rate": class_passing_rate,
            "total_students": n_st,
            "passing_cutoff": passing_pct,
        },
        "class_statistics": {
            "midterm_grade": class_avg_midterm,
            "finals_grade": class_avg_finals,
            "average_final_grade": class_avg_afg,
            "class_avg_midterm": class_avg_midterm,
            "class_avg_finals": class_avg_finals,
            "class_avg_afg": class_avg_afg,
            "transmuted_grade": class_avg_transmuted,
            "class_avg_transmuted": class_avg_transmuted,
            "highest_afg": class_highest_afg,
            "lowest_afg": class_lowest_afg,
            "passing_rate": class_passing_rate,
            "total_students": n_st,
            "passing_cutoff": passing_pct,
        },
        "comparison": {
            "afg_diff": afg_diff if final_grade_unlocked else None,
            "midterm_diff": mg_diff,
            "finals_diff": fg_diff if final_grade_unlocked else None,
            "rank": student_rank if final_grade_unlocked else None,
            "total_students": n_st,
            "percentile": percentile if final_grade_unlocked else None,
            "standing_label": standing_label if final_grade_unlocked else ("Survey Required" if (all_assessments_finalized and not survey_completed) else "In Progress"),
            "is_above_average": (afg_diff >= 0) if final_grade_unlocked else None,
        },
        "clo_attainment": matched_perf["clo_summary"],
        "categories": matched_perf["categories"],
        "passing_recommendation": passing_recommendation,
    })


EXIT_SURVEY_GENERAL_QUESTIONS = [
    {
        "key": "syllabus_clarity",
        "label": "Syllabus & CLO Clarity",
        "cqi_anchor_key": "instructional_delivery_pacing",
        "cqi_category": "Category I: Instructional Delivery & Pacing",
        "prompt": "The syllabus clearly communicated Course Learning Outcomes (CLOs), grading policies, and requirements.",
        "required": True,
    },
    {
        "key": "teaching_delivery",
        "label": "Instructional Delivery & Weekly Pacing",
        "cqi_anchor_key": "instructional_delivery_pacing",
        "cqi_category": "Category I: Instructional Delivery & Pacing",
        "prompt": "Topic pacing followed the weekly delivery timeline effectively, and lectures/activities explained core concepts clearly.",
        "required": True,
    },
    {
        "key": "assessment_fairness",
        "label": "Assessment Fairness, Rubrics & TOS Alignment",
        "cqi_anchor_key": "assessment_tos_rubrics",
        "cqi_category": "Category II: Assessment Fairness, Rubrics & TOS Alignment",
        "prompt": "Formative tasks, summative exams, and measurement rubrics fairly and accurately measured the stated Course Learning Outcomes.",
        "required": True,
    },
    {
        "key": "resources_facilities",
        "label": "Learning Resources, Lab Equipment & Facilities",
        "cqi_anchor_key": "learning_resources_labs",
        "cqi_category": "Category III: Learning Resources, Lab Equipment & Facilities",
        "prompt": "References, instructional manuals, software tools, laboratory equipment, and lab hours were adequate for this course.",
        "required": False,
    },
    {
        "key": "feedback_consultation",
        "label": "Feedback, Transparency & Consultation Support",
        "cqi_anchor_key": "student_support_consultation",
        "cqi_category": "Category IV: Feedback & Student Support",
        "prompt": "Timely assessment feedback, transparent grading, and faculty consultation helped address learning difficulties.",
        "required": True,
    },
]


@app.route("/api/student/courses/<course_id>/exit-survey", methods=["GET", "POST"])
def api_student_course_exit_survey(course_id):
    """
    Dynamic per-course Student Exit Survey endpoint (CLOs pulled from course syllabus +
    CQI-anchored delivery/fairness/resource questions + diagnostic topic prompt).
    Persists submissions to SQLite `survey_responses` and unlocks Final Grade visibility.
    """
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401

    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    clos_raw = bp.get("course_outcomes") or bp.get("clos") or []
    clos = [
        {
            "co_id": str(c.get("co_id") or f"CO{idx}").strip().upper(),
            "description": str(c.get("description") or "").strip(),
            "program_outcomes": str(c.get("program_outcomes") or "").strip(),
        }
        for idx, c in enumerate(clos_raw, 1)
    ]

    sid = str(user.get("student_id") or user.get("username") or "").strip()
    import db_persistence

    if request.method == "GET":
        existing = db_persistence.get_student_survey_response_db(sid, course_id)
        return jsonify({
            "success": True,
            "course": {
                "course_id": course_id,
                "course_code": doc.get("course_code") or meta.get("course_code") or "",
                "course_title": doc.get("course_title") or meta.get("course_title") or "",
                "section": doc.get("section") or meta.get("section") or "",
                "semester_ay": doc.get("semester_ay") or meta.get("semester_ay") or "",
                "faculty_name": doc.get("faculty_name") or meta.get("faculty_name") or "",
            },
            "clos": clos,
            "general_questions": EXIT_SURVEY_GENERAL_QUESTIONS,
            "response": existing,
            "is_completed": bool(existing and existing.get("is_completed")),
        })

    payload = request.get_json(silent=True) or {}
    raw_clo_ratings = payload.get("clo_ratings") or {}
    raw_gen_ratings = payload.get("general_ratings") or {}
    challenging_topics = str(payload.get("challenging_topics") or "").strip()
    comments = str(payload.get("comments") or "").strip()

    clo_ratings = {}
    for co in clos:
        cid = co["co_id"]
        val = raw_clo_ratings.get(cid)
        try:
            r_int = int(val)
        except (TypeError, ValueError):
            return jsonify({"error": f"Please select a rating (1 to 5) for {cid}."}), 400
        if not 1 <= r_int <= 5:
            return jsonify({"error": f"Rating for {cid} must be between 1 and 5."}), 400
        clo_ratings[cid] = r_int

    general_ratings = {}
    anchor_accum = {}
    for q in EXIT_SURVEY_GENERAL_QUESTIONS:
        qk = q["key"]
        val = raw_gen_ratings.get(qk)
        if val is None or val == "":
            if q.get("required", True):
                return jsonify({"error": f"Please rate '{q['label']}' (1 to 5)."}), 400
            continue
        try:
            r_int = int(val)
        except (TypeError, ValueError):
            return jsonify({"error": f"Please rate '{q['label']}' (1 to 5)."}), 400
        if not 1 <= r_int <= 5:
            return jsonify({"error": f"Rating for '{q['label']}' must be between 1 and 5."}), 400
        general_ratings[qk] = r_int
        anchor_accum.setdefault(q["cqi_anchor_key"], []).append(r_int)

    cqi_anchors = {
        ak: round(sum(vals) / len(vals), 2)
        for ak, vals in anchor_accum.items() if vals
    }

    saved = db_persistence.save_survey_response_db(
        student_id=sid,
        subject_id=course_id,
        course_code=doc.get("course_code") or meta.get("course_code") or "",
        clo_ratings=clo_ratings,
        general_ratings=general_ratings,
        comments=comments,
        cqi_anchors=cqi_anchors,
        challenging_topics=challenging_topics,
    )
    return jsonify({
        "success": True,
        "survey": saved,
        "is_completed": True,
        "message": "Thank you! Your Course Exit Survey has been recorded.",
    })


@app.route("/api/courses/<course_id>/exit-survey-summary", methods=["GET"])
@faculty_tools_required
def api_course_exit_survey_summary(course_id):
    """Returns aggregated Course Exit Survey metrics & anonymized feedback for CQI / CLO analysis."""
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    bp = doc.get("blueprint") or {}
    clos = bp.get("course_outcomes") or bp.get("clos") or []
    import db_persistence
    summary = db_persistence.get_course_survey_aggregates_db(course_id, clos)
    return jsonify({
        "success": True,
        "course_id": course_id,
        "general_questions": EXIT_SURVEY_GENERAL_QUESTIONS,
        **summary,
    })


# =========================================================================
# STEP 8 CQI PLAN AUTO-SYNTHESIS & PROGRAM HEAD SUBMISSION / REVISIT WORKFLOW
# =========================================================================

@app.route("/api/courses/<course_id>/cqi/plan", methods=["GET"])
@faculty_tools_required
def api_get_course_cqi_plan(course_id):
    """Returns 3-source consolidated data and saved Step 8 CQI Plan submission status."""
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    import cqi_engine
    import db_persistence

    three_source = cqi_engine.collect_three_source_cqi_data(doc)
    plan_row = db_persistence.get_cqi_plan_db(course_id)
    if plan_row:
        plan_row["revisit_status"] = cqi_engine.evaluate_revisit_status(plan_row, courses_store.list_all_workflow_courses())

    bp_cqi = (doc.get("blueprint") or {}).get("cqi_plan") or {}
    return jsonify({
        "success": True,
        "course_id": course_id,
        "three_source_summary": three_source,
        "cqi_plan_record": plan_row,
        "blueprint_cqi": bp_cqi,
    })


@app.route("/api/courses/<course_id>/cqi/synthesize", methods=["POST"])
@faculty_tools_required
def api_synthesize_course_cqi_plan(course_id):
    """
    Auto-generates and synthesizes Step 8 CQI Plan fields by correlating Step 4 Class Record,
    Step 7 MID-10 CLO Attainment, and Student Course Exit Survey responses.
    """
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    payload = request.get_json(silent=True) or {}
    use_ai = bool(payload.get("use_ai"))
    gemini_key = str(payload.get("gemini_api_key") or "").strip()

    import cqi_engine
    import db_persistence

    draft = cqi_engine.synthesize_cqi_plan(doc, use_ai=use_ai, gemini_api_key=gemini_key)
    bp = doc.setdefault("blueprint", {})
    cqi_obj = bp.setdefault("cqi_plan", {})
    for field in ("key_strengths", "areas_for_improvement", "gap_analysis", "root_causes", "action_plan", "target_kpis", "indicators", "targeted_clos", "revisit_date", "revisit_term"):
        cqi_obj[field] = draft.get(field)

    existing = db_persistence.get_cqi_plan_db(course_id)
    user = current_user() or {}
    meta = bp.get("metadata") or {}
    plan_rec = db_persistence.save_cqi_plan_db({
        "course_id": course_id,
        "course_code": doc.get("course_code") or meta.get("course_code") or "",
        "course_title": doc.get("course_title") or meta.get("course_title") or "",
        "section": doc.get("section") or meta.get("section") or "",
        "program_code": doc.get("program_code") or meta.get("program_code") or "EE",
        "semester_ay": doc.get("semester_ay") or meta.get("semester_ay") or "",
        "faculty_username": doc.get("owner") or user.get("username") or "faculty",
        "faculty_name": doc.get("faculty_name") or meta.get("faculty_name") or user.get("full_name") or "",
        "targeted_clos": draft.get("targeted_clos") or [],
        "synthesis": {
            "engine": draft.get("engine"),
            "clo_correlations": draft["three_source_summary"]["clo_correlations"],
            "bottleneck_items": draft["three_source_summary"]["bottleneck_items"],
            "survey_total_responses": draft["three_source_summary"]["exit_survey"].get("total_responses", 0),
            "survey_overall_rating": draft["three_source_summary"]["exit_survey"].get("overall_avg_rating"),
        },
        "key_strengths": draft["key_strengths"],
        "areas_for_improvement": draft["areas_for_improvement"],
        "gap_analysis": draft["gap_analysis"],
        "root_causes": draft["root_causes"],
        "action_plan": draft["action_plan"],
        "target_kpis": draft["target_kpis"],
        "indicators": draft["indicators"],
        "status": existing["status"] if existing else "draft",
        "revisit_date": existing["revisit_date"] if (existing and existing.get("revisit_date")) else draft["revisit_date"],
        "revisit_term": existing["revisit_term"] if (existing and existing.get("revisit_term")) else draft["revisit_term"],
        "revisit_status": existing["revisit_status"] if existing else "Upcoming",
    })
    courses_store.save_course_doc(doc)

    return jsonify({
        "success": True,
        "engine": draft["engine"],
        "cqi_plan": cqi_obj,
        "cqi_plan_record": plan_rec,
        "three_source_summary": draft["three_source_summary"],
    })


@app.route("/api/courses/<course_id>/cqi/submit", methods=["POST"])
@faculty_tools_required
def api_submit_course_cqi_plan(course_id):
    """
    Submits a completed Step 8 CQI Plan to the Program Head, setting status='submitted',
    calculating the Mandatory Revisit Date (1 Year post-submission / Next AY Same Semester),
    and surfacing it inside Requests for Approval -> Submitted CQI Plans.
    """
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404

    payload = request.get_json(silent=True) or {}
    user = current_user() or {}
    bp = doc.setdefault("blueprint", {})
    meta = bp.get("metadata") or {}
    cqi_obj = bp.setdefault("cqi_plan", {})

    for fld in ("key_strengths", "areas_for_improvement", "gap_analysis", "root_causes", "action_plan", "target_kpis"):
        if fld in payload:
            cqi_obj[fld] = str(payload.get(fld) or "").strip()
    if isinstance(payload.get("indicators"), list):
        cqi_obj["indicators"] = payload["indicators"]

    import cqi_engine
    import db_persistence

    three_source = cqi_engine.collect_three_source_cqi_data(doc)
    now_dt = datetime.now()
    now_ts = now_dt.isoformat(timespec="seconds")
    sem_ay = doc.get("semester_ay") or meta.get("semester_ay") or ""
    default_revisit_date, revisit_term = cqi_engine.compute_cqi_revisit_schedule(sem_ay, now_dt)
    revisit_date = str(payload.get("revisit_date") or "").strip() or default_revisit_date

    targeted_clos = payload.get("targeted_clos") or [
        c["co_id"] for c in (three_source["unmet_clos"] or three_source["borderline_clos"])
    ] or [c["co_id"] for c in three_source["clo_correlations"]]

    cqi_obj["status"] = "submitted"
    cqi_obj["submitted_at"] = now_ts
    cqi_obj["revisit_date"] = revisit_date
    cqi_obj["revisit_term"] = revisit_term
    cqi_obj["revisit_status"] = "Upcoming"
    cqi_obj["targeted_clos"] = targeted_clos

    plan_rec = db_persistence.save_cqi_plan_db({
        "course_id": course_id,
        "course_code": doc.get("course_code") or meta.get("course_code") or "",
        "course_title": doc.get("course_title") or meta.get("course_title") or "",
        "section": doc.get("section") or meta.get("section") or "",
        "program_code": doc.get("program_code") or meta.get("program_code") or "EE",
        "semester_ay": sem_ay,
        "faculty_username": doc.get("owner") or user.get("username") or "faculty",
        "faculty_name": doc.get("faculty_name") or meta.get("faculty_name") or user.get("full_name") or "",
        "targeted_clos": targeted_clos,
        "synthesis": {
            "clo_correlations": three_source["clo_correlations"],
            "bottleneck_items": three_source["bottleneck_items"],
            "survey_total_responses": three_source["exit_survey"].get("total_responses", 0),
            "survey_overall_rating": three_source["exit_survey"].get("overall_avg_rating"),
        },
        "key_strengths": cqi_obj.get("key_strengths") or "",
        "areas_for_improvement": cqi_obj.get("areas_for_improvement") or "",
        "gap_analysis": cqi_obj.get("gap_analysis") or "",
        "root_causes": cqi_obj.get("root_causes") or "",
        "action_plan": cqi_obj.get("action_plan") or "",
        "target_kpis": cqi_obj.get("target_kpis") or "",
        "indicators": cqi_obj.get("indicators") or [],
        "status": "submitted",
        "submitted_at": now_ts,
        "revisit_date": revisit_date,
        "revisit_term": revisit_term,
        "revisit_status": "Upcoming",
    })
    courses_store.save_course_doc(doc)

    return jsonify({
        "success": True,
        "message": f"CQI Plan submitted to Program Head! Mandatory Revisit scheduled for {revisit_date} ({revisit_term}).",
        "cqi_plan_record": plan_rec,
    })


def _can_review_cqi_plans(user: Optional[Dict[str, Any]]) -> bool:
    if not user:
        return False
    role = str(user.get("role") or "").strip().lower()
    wf_roles = {str(r).strip().lower() for r in (user.get("workflow_roles") or [])}
    return role == "admin" or bool(wf_roles.intersection({"program_head", "qa_head", "dean", "associate_dean"}))


@app.route("/api/workflow/cqi-plans", methods=["GET"])
def api_get_submitted_cqi_plans():
    """
    Returns Submitted CQI Plans segregated by Academic Year & Semester for the Program Head /
    Oversight Portal ('Submitted CQI Plans' sub-ribbon) and Faculty tracking.
    """
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.get("role") == "student":
        return jsonify({"error": "Forbidden"}), 403

    import cqi_engine
    import db_persistence

    all_plans = db_persistence.list_cqi_plans_db(include_drafts=False)
    all_courses = courses_store.list_all_workflow_courses()
    can_view_all = is_authorized_oversight_user(user)
    can_review = _can_review_cqi_plans(user)

    wf_roles = {str(r).strip().lower() for r in (user.get("workflow_roles") or [])}
    is_college_wide = (
        user.get("role") in ("admin", "staff")
        or bool(wf_roles.intersection({"dean", "associate_dean", "qa_head", "staff"}))
    )
    user_progs = {str(p).strip().upper() for p in (user.get("program_codes") or []) if str(p).strip()}
    uname_low = str(user.get("username") or "").strip().lower()

    visible_plans = []
    for pl in all_plans:
        p_code = str(pl.get("program_code") or "EE").strip().upper()
        if p_code.startswith("BS") and len(p_code) > 2:
            p_code = p_code[2:]
        if not can_view_all:
            if str(pl.get("faculty_username") or "").strip().lower() != uname_low:
                continue
        elif not is_college_wide and user_progs and "*" not in user_progs:
            if p_code not in user_progs:
                continue
        pl["revisit_status"] = cqi_engine.evaluate_revisit_status(pl, all_courses)
        visible_plans.append(pl)

    # Group per Semester / Academic Year
    sem_rank = {"1st Semester": 1, "2nd Semester": 2, "3rd Trimester": 3, "Summer / Midyear": 4}
    groups_map: Dict[str, List[Dict[str, Any]]] = {}
    for pl in visible_plans:
        sem_raw = str(pl.get("semester_ay") or "Unassigned Term").strip()
        _, _, grp_lbl = courses_store.parse_semester_ay(sem_raw)
        key_lbl = sem_raw or grp_lbl
        groups_map.setdefault(key_lbl, []).append(pl)

    def _term_sort_key(item):
        lbl = item[0]
        sy, sem, _ = courses_store.parse_semester_ay(lbl)
        m_yr = re.search(r"(\d{4})", sy)
        yr = int(m_yr.group(1)) if m_yr else 0
        return (-yr, sem_rank.get(sem, 9), lbl)

    groups = [
        {"semester_ay": lbl, "plans": plist, "count": len(plist)}
        for lbl, plist in sorted(groups_map.items(), key=_term_sort_key)
    ]

    return jsonify({
        "success": True,
        "can_review": can_review,
        "can_view_all": can_view_all,
        "total_count": len(visible_plans),
        "plans": visible_plans,
        "groups": groups,
    })


@app.route("/api/workflow/cqi-plans/<course_id>/review", methods=["POST"])
def api_review_submitted_cqi_plan(course_id):
    """Program Head / QA Head / Dean action: Approve & Schedule Revisit, Verify/Close Revisit, Return, or Update Revisit Date."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if not _can_review_cqi_plans(user):
        return jsonify({"error": "Forbidden: Only Program Heads, QA Head, Associate Dean, Dean, or Admin can review CQI Plans."}), 403

    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or "approve").strip().lower()
    remarks = str(payload.get("remarks") or "").strip()
    revisit_date = str(payload.get("revisit_date") or "").strip() or None

    status_map = {
        "approve": ("approved_scheduled", "Upcoming"),
        "close": ("verified", "Closed/Verified"),
        "verify": ("verified", "Closed/Verified"),
        "return": ("returned", "Upcoming"),
    }
    if action in status_map:
        new_status, new_rev_status = status_map[action]
    elif action == "update_revisit":
        import db_persistence
        cur_row = db_persistence.get_cqi_plan_db(course_id)
        if not cur_row:
            return jsonify({"error": "Submitted CQI Plan not found."}), 404
        new_status = cur_row["status"]
        new_rev_status = str(payload.get("revisit_status") or cur_row.get("revisit_status") or "Upcoming")
    else:
        return jsonify({"error": f"Unknown CQI review action '{action}'."}), 400

    import cqi_engine
    import db_persistence

    updated = db_persistence.update_cqi_plan_review_db(
        course_id=course_id,
        status=new_status,
        reviewed_by=user.get("username") or "",
        reviewed_by_name=user.get("full_name") or user.get("username") or "",
        remarks=remarks,
        revisit_date=revisit_date,
        revisit_status=new_rev_status,
    )
    if not updated:
        return jsonify({"error": f"CQI Plan for course '{course_id}' not found."}), 404

    updated["revisit_status"] = cqi_engine.evaluate_revisit_status(updated, courses_store.list_all_workflow_courses())

    # Sync back onto course blueprint.cqi_plan
    doc = courses_store.find_course(course_id)
    if doc:
        bp = doc.setdefault("blueprint", {})
        bp_cqi = bp.setdefault("cqi_plan", {})
        bp_cqi["status"] = updated["status"]
        bp_cqi["revisit_date"] = updated["revisit_date"]
        bp_cqi["revisit_term"] = updated["revisit_term"]
        bp_cqi["revisit_status"] = updated["revisit_status"]
        bp_cqi["program_head_remarks"] = updated["program_head_remarks"]
        bp_cqi["reviewed_by_name"] = updated["reviewed_by_name"]
        courses_store.save_course_doc(doc)

    return jsonify({
        "success": True,
        "cqi_plan_record": updated,
        "message": f"CQI Plan updated ({updated['status']}) — Revisit Date: {updated.get('revisit_date')}.",
    })


@app.route("/api/courses/<course_id>/assessment-acknowledgments", methods=["GET"])
def api_get_course_assessment_acknowledgments(course_id):
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    err = check_syllabus_approved_for_step(doc, 4)
    if err:
        return err

    bp = doc.get("blueprint") or {}
    students = bp.get("students") or []

    # Map student_id -> dict of item_id -> ack_data
    ack_data = {}
    for st in students:
        sid = str(st.get("student_id") or "").strip()
        if sid:
            ack_data[sid] = st.get("assessment_acknowledgments") or {}

    return jsonify({
        "success": True,
        "course_id": course_id,
        "acknowledgments": ack_data,
    })


@app.route("/api/student/courses/<course_id>/acknowledge-assessment", methods=["POST"])
def api_student_acknowledge_assessment(course_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json(silent=True) or {}
    item_id = str(data.get("item_id") or "").strip()
    if not item_id:
        return jsonify({"error": "Assessment item_id is required."}), 400

    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
    err = check_syllabus_approved_for_step(doc, 4)
    if err:
        return err

    bp = doc.get("blueprint") or {}
    students = bp.get("students") or []

    sid = (user.get("student_id") or user.get("username") or "").strip().lower()
    sid_digits = re.sub(r"\D", "", sid)
    matched_st = None
    for st in students:
        curr_sid = str(st.get("student_id") or "").strip().lower()
        curr_digits = re.sub(r"\D", "", curr_sid)
        st_full = f"{st.get('last_name', '')}, {st.get('first_name', '')}".strip(", ").lower()
        st_name = str(st.get("name") or "").strip().lower()
        if (curr_sid and curr_sid == sid) or            (curr_digits and sid_digits and len(curr_digits) >= 4 and curr_digits == sid_digits) or            (user.get("full_name") and user["full_name"].lower() in (st_full, st_name)):
            matched_st = st
            break

    if not matched_st and user.get("role") != "student" and students:
        req_sid = (data.get("student_id") or "").strip().lower()
        if req_sid:
            for st in students:
                if str(st.get("student_id") or "").strip().lower() == req_sid:
                    matched_st = st
                    break
        if not matched_st:
            matched_st = students[0]

    if not matched_st:
        return jsonify({"error": "Enrolled student record not found in this course."}), 404

    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    now_iso = datetime.now().isoformat()

    sig_data = (data.get("signature_data") or "").strip()
    if not sig_data:
        sig_data = (user.get("signature_data") or "").strip()
    if not sig_data:
        try:
            from student_store import _load_students, _normalize_id
            all_s = _load_students()
            st_norm = _normalize_id(matched_st.get("student_id") or sid)
            sig_data = (all_s.get(st_norm) or {}).get("signature_data") or ""
        except Exception:
            pass

    if "assessment_acknowledgments" not in matched_st:
        matched_st["assessment_acknowledgments"] = {}

    matched_st["assessment_acknowledgments"][item_id] = {
        "acknowledged": True,
        "acknowledged_at": now_str,
        "acknowledged_iso": now_iso,
        "signature_data": sig_data,
        "student_id": matched_st.get("student_id"),
        "student_name": matched_st.get("name") or f"{matched_st.get('last_name', '')}, {matched_st.get('first_name', '')}".strip(", "),
        "statement": "Student accepted the score, received test paper, and acknowledged that the score is final and reconsideration will not be entertained."
    }

    courses_store.save_course_doc(doc)

    # Also mirror into student store if registered
    try:
        from student_store import _load_students, _save_students, _normalize_id
        all_s = _load_students()
        st_norm = _normalize_id(matched_st.get("student_id") or sid)
        if st_norm in all_s:
            s_obj = all_s[st_norm]
            if "assessment_acknowledgments" not in s_obj:
                s_obj["assessment_acknowledgments"] = {}
            if course_id not in s_obj["assessment_acknowledgments"]:
                s_obj["assessment_acknowledgments"][course_id] = {}
            s_obj["assessment_acknowledgments"][course_id][item_id] = {
                "acknowledged": True,
                "acknowledged_at": now_str,
                "signature_data": sig_data,
            }
            if sig_data and not s_obj.get("signature_data"):
                s_obj["signature_data"] = sig_data
            _save_students(all_s)
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": f"Score for {item_id} successfully acknowledged with affixed signature.",
        "item_id": item_id,
        "acknowledged_at": now_str,
        "signature_data": sig_data,
    })


if __name__ == "__main__":
    if not os.path.exists(SAMPLE_PDF_PATH):
        try:
            generate_sample_syllabus_pdf(SAMPLE_PDF_PATH)
        except Exception as _pdf_err:
            logging.getLogger(__name__).warning(f"Could not generate sample PDF: {_pdf_err}")

    host = config.HOST or "0.0.0.0"
    port = config.PORT
    debug = config.DEBUG
    local_ip = config.get_local_ip()

    print("=" * 72)
    print("  USeP OBE Syllabus-to-Class Record Generator - Local & LAN Server")
    print("=" * 72)
    print("  Server is active and bound to 0.0.0.0 (multi-device LAN enabled):")
    print()
    print(f"  [Local Machine (This PC)]")
    print(f"     Faculty / Admin Portal : http://127.0.0.1:{port}")
    print(f"     Student Portal         : http://127.0.0.1:{port}/student")
    print()
    print(f"  [Network / LAN Access (Same Wi-Fi or Local Network)]")
    print(f"     Faculty / Admin Portal : http://{local_ip}:{port}")
    print(f"     Student Portal         : http://{local_ip}:{port}/student")
    print(f"     Student Login Direct   : http://{local_ip}:{port}/student/login")
    print()
    print("  Default Faculty & Admin Credentials:")
    print("     Admin Username   : admin")
    print("     Admin Password   : admin123")
    print("=" * 72)

    app.run(host=host, port=port, debug=debug, threaded=True)
