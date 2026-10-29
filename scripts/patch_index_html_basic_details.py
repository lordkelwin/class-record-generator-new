with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Basic Details Card right before <div class="grid-4" style="grid-template-columns: 1fr 1fr;">
target_grid = '<div class="grid-4" style="grid-template-columns: 1fr 1fr;">'
basic_details_card = '''    <div class="card" style="margin-bottom:14px; border:1px solid #cbd5e1; background:#ffffff;">
      <div class="card-header" style="background:#f8fafc; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center;">
        <h2 style="font-size:0.92rem; margin:0; color:#1e293b;">FM-USeP-MID-10 Basic Details (Retrieved from Syllabus Creation)</h2>
        <span class="badge" style="background:#e0f2fe; color:#0369a1; font-size:0.75rem; font-weight:700;">FM-USeP-MID-10 Issue 01 Rev 00</span>
      </div>
      <div style="padding:12px 16px; display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:10px; font-size:0.83rem;">
        <div><strong>Name of Faculty:</strong> <span id="cloReportFaculty" style="color:#0f172a;">—</span></div>
        <div><strong>Course Title, Desc. &amp; Units:</strong> <span id="cloReportCourse" style="color:#0f172a;">—</span></div>
        <div><strong>Semester &amp; Academic Year:</strong> <span id="cloReportSemAy" style="color:#0f172a;">—</span></div>
        <div><strong>Program:</strong> <span id="cloReportProgram" style="color:#0f172a;">—</span></div>
        <div><strong>Academic Unit:</strong> <span id="cloReportAcademicUnit" style="color:#0f172a;">—</span></div>
      </div>
    </div>

'''

if target_grid in content and 'id="cloReportFaculty"' not in content:
    content = content.replace(target_grid, basic_details_card + target_grid, 1)
    print("Added Basic Details Card to Tab 4")
else:
    print("Target grid not found or card already present")

# 2. In renderTab4Reports, update the basic details card spans
target_fn = 'function renderTab4Reports('
if target_fn in content:
    update_spans_code = '''    // Populate FM-USeP-MID-10 Basic Details
    const fSpan = document.getElementById("cloReportFaculty");
    if (fSpan) fSpan.textContent = blueprint.metadata.faculty_name || "—";
    const cSpan = document.getElementById("cloReportCourse");
    if (cSpan) {
      const code = (blueprint.metadata.course_code || "").trim();
      const title = (blueprint.metadata.course_title || "").trim();
      const desc = (blueprint.metadata.course_description || "").trim();
      const units = (blueprint.metadata.credit_units || "").trim();
      cSpan.textContent = `${code} - ${title}${desc ? ', ' + desc : ''}${units ? ' (' + units + ')' : ''}`;
    }
    const sSpan = document.getElementById("cloReportSemAy");
    if (sSpan) sSpan.textContent = blueprint.metadata.semester_ay || "—";
    const pSpan = document.getElementById("cloReportProgram");
    if (pSpan) pSpan.textContent = blueprint.metadata.program_name || blueprint.metadata.department || "—";
    const uSpan = document.getElementById("cloReportAcademicUnit");
    if (uSpan) uSpan.textContent = blueprint.metadata.academic_unit || blueprint.metadata.college || "Engineering";

'''
    # Find start of renderTab4Reports body
    fn_idx = content.find(target_fn)
    brace_idx = content.find('{', fn_idx)
    content = content[:brace_idx + 1] + "\n" + update_spans_code + content[brace_idx + 1:]
    print("Added metadata update code into renderTab4Reports")
else:
    print("renderTab4Reports function not found")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Saved templates/index.html")
