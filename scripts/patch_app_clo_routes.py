import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update api_export_clo_report_pdf and add api_export_clo_report_excel
old_func_pattern = r'@app\.route\("/api/export-clo-report-pdf", methods=\["POST"\]\)\s*@faculty_tools_required\s*def api_export_clo_report_pdf\(\):.*?(?=@app\.route\("/api/export-excel")'

new_funcs = '''@app.route("/api/export-clo-report-pdf", methods=["POST"])
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

    safe_code = re.sub(r'[\\\\/*?:"<>|]+', "_", bp.metadata.course_code.strip()) or "Course"
    safe_sec = re.sub(r'[\\\\/*?:"<>|]+', "_", bp.metadata.section.strip()) or "Section"
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

    safe_code = re.sub(r'[\\\\/*?:"<>|]+', "_", bp.metadata.course_code.strip()) or "Course"
    safe_sec = re.sub(r'[\\\\/*?:"<>|]+', "_", bp.metadata.section.strip()) or "Section"
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


'''

match = re.search(old_func_pattern, content, flags=re.DOTALL)
if match:
    content = content[:match.start()] + new_funcs + content[match.end():]
    print("Replaced api_export_clo_report_pdf and added api_export_clo_report_excel")
else:
    print("Could not find old api_export_clo_report_pdf function!")

# 2. Add course GET routes if not present
if '/api/courses/<course_id>/export-clo-report-excel' not in content:
    target = '@app.route("/api/courses/<course_id>/export-pdf", methods=["GET"])'
    pos = content.find(target)
    if pos != -1:
        get_routes = '''@app.route("/api/courses/<course_id>/export-clo-report-excel", methods=["GET"])
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


'''
        content = content[:pos] + get_routes + content[pos:]
        print("Added GET routes for courses clo-report-excel and clo-report-pdf")
    else:
        print("Target for GET routes not found!")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Saved app.py successfully!")
