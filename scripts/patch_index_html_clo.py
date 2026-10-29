with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Tab 4 buttons
old_tab4_btn = '<button class="btn btn-primary" style="background:#0284c7; border-color:#0369a1;" onclick="exportCloReportPdf()">Export CLO Assessment Report (.pdf)</button>'
new_tab4_btn = (
    '<button class="btn btn-primary" style="background:#0284c7; border-color:#0369a1;" onclick="exportCloReportPdf()">'
    'Export CLO Report (.pdf) [FM-USeP-MID-10]</button>\n'
    '          <button class="btn btn-success" style="background:#15803d; border-color:#166534;" onclick="exportCloReportExcel()">'
    '📊 Export CLO Evaluation Result (.xlsx) [FM-USeP-MID-10]</button>'
)

if old_tab4_btn in content:
    content = content.replace(old_tab4_btn, new_tab4_btn, 1)
    print("Updated Tab 4 buttons")
else:
    print("Warning: old_tab4_btn not found in index.html")

# 2. Update Gradebook action bar button (around line 2031)
old_gb_btn = '<button class="btn btn-primary btn-sm" style="background:#0284c7; border-color:#0369a1;" onclick="exportCloReportPdf()">Export CLO Report (.pdf)</button>'
new_gb_btn = (
    '<button class="btn btn-primary btn-sm" style="background:#0284c7; border-color:#0369a1;" onclick="exportCloReportPdf()">Export CLO Report (.pdf)</button>\n'
    '          <button class="btn btn-success btn-sm" style="background:#15803d; border-color:#166534;" onclick="exportCloReportExcel()">Export CLO Report (.xlsx)</button>'
)
if old_gb_btn in content:
    content = content.replace(old_gb_btn, new_gb_btn, 1)
    print("Updated Gradebook action bar buttons")
else:
    print("Warning: old_gb_btn not found in index.html")

# 3. Update top action bar button (around line 992)
old_top_btn = '<button class="btn btn-primary" style="background:#0284c7; color:#ffffff; border-color:#0369a1;" onclick="exportCloReportPdf()">Export CLO Report (.pdf)</button>'
new_top_btn = (
    '<button class="btn btn-primary" style="background:#0284c7; color:#ffffff; border-color:#0369a1;" onclick="exportCloReportPdf()">Export CLO Report (.pdf)</button>\n'
    '      <button class="btn btn-success" style="background:#15803d; color:#ffffff; border-color:#166534;" onclick="exportCloReportExcel()">Export CLO Report (.xlsx)</button>'
)
if old_top_btn in content:
    content = content.replace(old_top_btn, new_top_btn, 1)
    print("Updated top action bar buttons")
else:
    print("Warning: old_top_btn not found in index.html")

# 4. Add exportCloReportExcel JS function and pass course_id in exportCloReportPdf
target_js = 'async function exportCloReportPdf() {'
if target_js in content:
    old_pdf_call = 'body: JSON.stringify({ blueprint })'
    new_pdf_call = 'body: JSON.stringify({ blueprint, course_id: currentCourseId })'
    
    excel_fn = '''  async function exportCloReportExcel() {
    syncMetaFromInputs();
    const res = await fetch("/api/export-clo-report-excel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ blueprint, course_id: currentCourseId })
    });
    if (!res.ok) {
      alert("Failed to generate CLO Evaluation Result Excel (FM-USeP-MID-10).");
      return;
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    const code = (blueprint.metadata.course_code || "Course").trim();
    const sec = (blueprint.metadata.section || "Section").trim();
    a.href = url;
    a.download = `${code}_${sec}_CLO_Evaluation_Result_FM-USeP-MID-10.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }

'''
    content = content.replace(target_js, excel_fn + '  async function exportCloReportPdf() {', 1)
    if old_pdf_call in content:
        content = content.replace(old_pdf_call, new_pdf_call, 1)
    print("Added exportCloReportExcel function and updated exportCloReportPdf")
else:
    print("Warning: target_js not found in index.html")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Saved templates/index.html successfully!")
