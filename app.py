import syllabus_workflow
import class_record_workflow
import oversight_report_generator

from syllabus_evaluation_form import (

    FORM_INFO, CORE_EVALUATION_STATEMENTS, FRAMEWORK_INTEGRATION_AREAS,

    ANNEX_A_SECTIONS, generate_syllabus_evaluation_pdf

)

import io

import os

import re

import tempfile

import uuid
from datetime import datetime

import pandas as pd

from flask import Flask, render_template, request, jsonify, send_file, Response, session, redirect, url_for, flash







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







app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit
app.config["TEMPLATES_AUTO_RELOAD"] = True

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







BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EE211_PDF_PATH = os.path.join(BASE_DIR, "EE 211.pdf")

SAMPLE_PDF_PATH = EE211_PDF_PATH if os.path.exists(EE211_PDF_PATH) else os.path.join(BASE_DIR, "samples", "EE211_OBE_Course_Syllabus.pdf")

EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

os.makedirs(os.path.join(BASE_DIR, "samples"), exist_ok=True)

os.makedirs(EXPORTS_DIR, exist_ok=True)











@app.context_processor
def inject_current_user():
    return dict(current_user=current_user())

@app.route("/")

def index():

    return render_template("index.html")











@app.route("/api/catalog", methods=["GET"])

def api_catalog():

    return jsonify(get_full_catalog())


@app.route("/api/faculty-roster", methods=["GET"])
def api_faculty_roster():
    return jsonify(OFFICIAL_FACULTY_ROSTER)












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
            meta["dean_name"] = "Engr. Joie D. Cataytay, Ph.D."
        meta["passing_percentage"] = meta.get("passing_percentage") or 75.0

        sec = (data.get("section") or meta.get("section") or "1A").strip()

        sem_ay = (data.get("semester_ay") or meta.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()

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
    can_view_institutional = is_admin or is_staff or any(r in w_roles for r in ["program_head", "qa_head", "dean", "associate_dean"])

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

        can_sign_cr = False
        if doc_raw and (is_admin or not is_owner):
            can_sign_cr = class_record_workflow.user_can_sign_class_record(user, doc_raw)
        c["user_can_sign_cr"] = can_sign_cr
        c["is_owner"] = is_owner

        ACTIVE_SYL_REVIEW_STATUSES = {
            "for_committee_review", "for_committee_chair", "for_program_head",
            "for_qa_countersign", "for_dean_approval",
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

    analytics = class_record_workflow.compute_institutional_analytics(all_courses)

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
    sig_data = data.get("signature_data") or ""
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

    can_edit = (syllabus_workflow.user_can_act(user, doc) and wf.get("status") == "for_committee_review") or (user.get("role") == "admin")

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











@app.route("/api/courses/<course_id>/export-clo-report-excel", methods=["GET"])
def api_export_course_clo_report_excel(course_id):
    doc = courses_store.find_course(course_id)
    if not doc:
        return jsonify({"error": f"Course '{course_id}' not found."}), 404
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

        courses_store.save_course_doc(doc)
        return jsonify({
            "success": True,
            "message": f"Syllabus acknowledgment recorded for {student_name}.",
            "acknowledgments": acks,
            "total_acknowledged": len(acks),
        })

    return jsonify({
        "course_id": course_id,
        "course_code": doc.get("course_code"),
        "course_title": doc.get("course_title"),
        "section": doc.get("section"),
        "semester_ay": doc.get("semester_ay"),
        "is_approved": (doc.get("workflow") or {}).get("status") == "approved",
        "students": students,
        "acknowledgments": acks,
        "total_students": len(students),
        "total_acknowledged": len(acks),
    })


import student_store


@app.route("/student/login", methods=["GET", "POST"], endpoint="student_login")
def student_login():
    user = current_user()
    if user and user.get("role") == "student":
        return redirect(url_for("student_dashboard"))

    error = None
    success = None
    student_id = ""
    next_url = request.args.get("next") or ""

    if request.method == "POST":
        student_id = (request.form.get("student_id") or "").strip()
        secret = (request.form.get("secret") or "").strip()

        ok, st, err_msg = student_store.verify_student_login(student_id, secret)
        if ok and st:
            session.clear()
            session.permanent = True
            session["username"] = st["student_id"]
            session["student_id"] = st["student_id"]
            session["student_name"] = st["full_name"]
            session["role"] = "student"
            session["email"] = st.get("email") or f"{st['student_id']}@usep.edu.ph"
            session["has_signature"] = bool(st.get("signature_data"))
            session["signature_data"] = st.get("signature_data", "")
            auth.get_csrf_token()

            if next_url and next_url.startswith("/student"):
                return redirect(next_url)
            return redirect(url_for("student_dashboard"))
        else:
            error = err_msg or "Authentication failed. Please verify your Student ID and Last Name."

    return render_template("student_login.html", error=error, success=success, student_id=student_id, next_url=next_url)


@app.route("/student/logout", methods=["GET", "POST"], endpoint="student_logout")
def student_logout():
    session.clear()
    flash("You have been signed out from the Student Portal.", "info")
    return redirect(url_for("student_login"))


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
        return render_template("student_dashboard.html", student=preview_st, pending=[], acknowledged=[], in_review=[], stats={"total": 0, "pending_count": 0, "acknowledged_count": 0, "in_review_count": 0})

    return render_template(
        "student_dashboard.html",
        student=cdata["student"] or {"student_id": sid, "full_name": user.get("full_name") or sid, "signature_data": user.get("signature_data", "")},
        pending=cdata["pending"],
        acknowledged=cdata["acknowledged"],
        in_review=cdata["in_review"],
        stats=cdata["stats"]
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
        ip_address=request.remote_addr or ""
    )

    if not ok:
        return jsonify({"error": msg}), 400

    session["signature_data"] = sig_data
    session["has_signature"] = True

    return jsonify({
        "success": True,
        "message": msg,
        "acknowledgment": ack_rec
    })


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
        session["signature_data"] = sig_data
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
    pdf_bytes = syllabus_acknowledgment_form.generate_syllabus_acknowledgment_pdf(bp, doc)

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
    all_courses = courses_store.list_all_workflow_courses()
    analytics = class_record_workflow.compute_institutional_analytics(all_courses)
    return jsonify(analytics)


@app.route("/api/workflow/oversight-report", methods=["GET"])
def api_download_oversight_report():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
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

if __name__ == "__main__":

    if not os.path.exists(SAMPLE_PDF_PATH):

        generate_sample_syllabus_pdf(SAMPLE_PDF_PATH)

    app.run(host="127.0.0.1", port=5000, debug=False)



