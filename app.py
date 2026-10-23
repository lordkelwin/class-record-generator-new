import syllabus_workflow
from syllabus_evaluation_form import (
    FORM_INFO, CORE_EVALUATION_STATEMENTS, FRAMEWORK_INTEGRATION_AREAS,
    ANNEX_A_SECTIONS, generate_syllabus_evaluation_pdf
)
import io
import os
import re
import tempfile
import uuid
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file



from models import SyllabusBlueprint, StudentRecord, build_transmutation_table
from sample_syllabus import get_default_blueprint, generate_sample_syllabus_pdf
from syllabus_parser import analyze_syllabus_pdf
from excel_generator import generate_class_record_workbook
from catalog_data import get_full_catalog
from syllabus_pdf_generator import generate_usep_syllabus_pdf
from clo_report_pdf_generator import generate_clo_report_pdf_bytes
import auth
from auth import install_auth, current_user
import courses_store



app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit
# Login screen, faculty accounts (admin-managed) and a global login guard for every page/API
install_auth(app)



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EE211_PDF_PATH = os.path.join(BASE_DIR, "EE 211.pdf")
SAMPLE_PDF_PATH = EE211_PDF_PATH if os.path.exists(EE211_PDF_PATH) else os.path.join(BASE_DIR, "samples", "EE211_OBE_Course_Syllabus.pdf")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
os.makedirs(os.path.join(BASE_DIR, "samples"), exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)





@app.route("/")
def index():
    return render_template("index.html")





@app.route("/api/catalog", methods=["GET"])
def api_catalog():
    return jsonify(get_full_catalog())





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
    passing_pct = float(data.get("passing_percentage", 60.0))
    return jsonify({"transmutation": build_transmutation_table(passing_pct)})





@app.route("/api/export-syllabus-pdf", methods=["POST"])
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
def api_export_clo_report_pdf():
    data = request.get_json(silent=True)
    if not data or "blueprint" not in data:
        return jsonify({"error": "Missing syllabus blueprint data."}), 400



    bp = SyllabusBlueprint.from_dict(data["blueprint"])
    pdf_bytes = generate_clo_report_pdf_bytes(bp)



    safe_code = re.sub(r'[\\/*?:"<>|]+', "_", bp.metadata.course_code.strip()) or "Course"
    safe_sec = re.sub(r'[\\/*?:"<>|]+', "_", bp.metadata.section.strip()) or "Section"
    filename = f"{safe_code}_{safe_sec}_CLO Report.pdf"



    local_out = os.path.join(EXPORTS_DIR, filename)
    with open(local_out, "wb") as f_out:
        f_out.write(pdf_bytes)



    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )





@app.route("/api/export-excel", methods=["POST"])
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
    wf_view["can_submit"] = (doc.get("owner") == username) and (wf_view["status"] in syllabus_workflow.EDITABLE_STATUSES)
    wf_view["can_withdraw"] = (doc.get("owner") == username) and (wf_view["status"] == "for_committee_review") and not wf_view["signatures"]
    wf_view["can_sign"] = syllabus_workflow.user_can_act(user, doc)
    return jsonify({
        "course": doc,
        "blueprint": bp_dict,
        "workflow": wf_view,
        "transmutation": build_transmutation_table(passing_pct),
    })





@app.route("/api/courses", methods=["POST"])
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
        sec = (data.get("section") or meta.get("section") or "1A").strip()
        sem_ay = (data.get("semester_ay") or meta.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()
        new_doc = courses_store.save_course(
            username,
            course_id=f"c_{uuid.uuid4().hex[:10]}",
            payload={
                "course_code": c_code,
                "course_title": c_title,
                "section": sec,
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
    sec = (data.get("section") or "EE 2A").strip()
    sem_ay = (data.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()



    doc = courses_store.create_course(
        username=username,
        course_code=c_code,
        course_title=c_title,
        section=sec,
        semester_ay=sem_ay,
        from_catalog=from_cat,
        catalog_course_data=cat_course,
        faculty_name=faculty_name,
    )
    return jsonify({
        "course": doc,
        "message": f"Subject '{c_code} ({sec})' created under {sem_ay}."
    }), 201





@app.route("/api/courses/<course_id>", methods=["PUT"])
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
    wf_view["can_submit"] = (doc.get("owner") == uname) and (wf_view["status"] in syllabus_workflow.EDITABLE_STATUSES)
    wf_view["can_withdraw"] = (doc.get("owner") == uname) and (wf_view["status"] == "for_committee_review") and not wf_view["signatures"]
    wf_view["can_sign"] = syllabus_workflow.user_can_act(user, doc)
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
        if "review_committee" in w_roles or is_admin:
            committee_members.append(item)
        if "program_head" in w_roles or is_admin:
            program_heads.append(item)
        if "qa_head" in w_roles or is_admin:
            qa_heads.append(item)
        if "dean" in w_roles or is_admin:
            deans.append(item)
    return jsonify({
        "review_committee": committee_members,
        "program_heads": program_heads,
        "qa_heads": qa_heads,
        "deans": deans,
    })





@app.route("/api/workflow/requests", methods=["GET"])
def api_get_workflow_requests():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    all_courses = courses_store.list_all_workflow_courses()

    

    pending_action_for_me = []
    my_submitted_requests = []
    institutional_requests = []



    for c in all_courses:
        doc_raw = c.pop("doc_raw", None)
        wf = c.get("workflow") or {}
        is_owner = (c.get("owner") == user["username"])
        can_act = False
        if doc_raw and not is_owner:
            can_act = syllabus_workflow.user_can_act(user, doc_raw)
        c["user_can_act"] = can_act
        c["is_owner"] = is_owner



        if can_act and wf.get("status") in {"for_committee_review", "for_program_head", "for_qa_countersign", "for_dean_approval"}:
            pending_action_for_me.append(c)



        if is_owner:
            my_submitted_requests.append(c)



        institutional_requests.append(c)



    return jsonify({
        "pending_count": len(pending_action_for_me),
        "pending_action_for_me": pending_action_for_me,
        "my_submitted_requests": my_submitted_requests,
        "institutional_requests": institutional_requests,
        "user_info": {
            "username": user["username"],
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "workflow_roles": user.get("workflow_roles") or [],
            "position_title": user.get("position_title"),
            "has_signature": user.get("has_signature"),
        }
    })





@app.route("/api/courses/<course_id>/workflow/submit", methods=["POST"])
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
    try:
        wf = syllabus_workflow.submit(
            doc, user,
            assigned_committee=assigned_committee,
            assigned_committee_name=assigned_committee_name,
            committee_members=committee_members,
            submission_notes=submission_notes
        )
        courses_store.save_course_doc(doc)
        comm_name = wf.get("assigned_committee_name") or "the Review Committee"
        return jsonify({
            "success": True,
            "message": f"Syllabus submitted and notification sent to {comm_name}.",
            "workflow": syllabus_workflow.public_view(doc),
        })
    except syllabus_workflow.WorkflowError as e:
        return jsonify({"error": str(e)}), 400





@app.route("/api/courses/<course_id>/workflow/withdraw", methods=["POST"])
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
    can_edit = ("review_committee" in (user.get("workflow_roles") or [])) or (user.get("role") == "admin")
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
    if sig_data and not user.get("has_signature"):
        from auth import _load_users, _save_users, _lock
        with _lock:
            all_users = _load_users()
            if user["username"] in all_users:
                all_users[user["username"]]["signature_data"] = sig_data
                _save_users(all_users)
        user["has_signature"] = True
        user["signature_data"] = sig_data



    # Temporary allow signing if signature_data is supplied in the request body
    if sig_data:
        user["has_signature"] = True



    try:
        wf = syllabus_workflow.sign(doc, user, decision=decision, remarks=remarks)
        courses_store.save_course_doc(doc)
        step_label = (syllabus_workflow.current_step(wf) or {}).get("label") or "Next Step"
        action_msg = "Syllabus returned for revision." if decision == "return" else (
            "Syllabus approved and locked! Class record is now unlocked." if wf.get("status") == "approved" else
            f"Step signed and forwarded to {step_label}."
        )
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







if __name__ == "__main__":
    if not os.path.exists(SAMPLE_PDF_PATH):
        generate_sample_syllabus_pdf(SAMPLE_PDF_PATH)
    app.run(host="127.0.0.1", port=5000, debug=False)

