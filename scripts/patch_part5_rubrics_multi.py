# scripts/patch_part5_rubrics_multi.py
import re

def patch_syllabus_pdf_generator():
    with open("syllabus_pdf_generator.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update rubric title line in Part VII
    old_title_part = """            r_title = rub.get("title") or f"Rubric {r_idx+1}"

            part_str = f" [Graded Portion: {rub['target_part']}]" if rub.get("target_part") else ""

            pdf.set_font("Helvetica", "B", 8.5)

            pdf.cell(0, 4.8, _clean_text(f"Assessment Activity: {r_title}{part_str}"), new_x="LMARGIN", new_y="NEXT")"""

    new_title_part = """            r_title = rub.get("title") or f"Rubric {r_idx+1}"

            part_str = f" [Graded Portion: {rub['target_part']}]" if rub.get("target_part") else ""

            codes_list = [str(c).strip() for c in (rub.get("assessment_codes") or []) if str(c).strip()]
            if not codes_list and rub.get("assessment_code"):
                codes_list = [c.strip() for c in str(rub.get("assessment_code")).split(",") if c.strip()]
            codes_str = f" [Accommodated Assessments: {', '.join(codes_list)}]" if len(codes_list) > 1 else ""

            pdf.set_font("Helvetica", "B", 8.5)

            pdf.cell(0, 4.8, _clean_text(f"Assessment Activity: {r_title}{codes_str}{part_str}"), new_x="LMARGIN", new_y="NEXT")"""

    # 2. Update criteria clo_tag to respect enable_criteria_clos (disabled by default)
    old_crit_tag = """                    clo_tag = f" ({crit.get('clo_id')})" if crit.get("clo_id") else """""
    new_crit_tag = """                    clo_tag = f" ({crit.get('clo_id')})" if (rub.get("enable_criteria_clos") and crit.get("clo_id")) else """""

    # 3. Update Part VIII rubric matching to support multiple accommodated assessments
    old_matching = """                    matching_rubs = [r for r in rubrics if (r.get("assessment_code") or "").upper().strip() == code or code in (r.get("title") or "").upper()]"""
    new_matching = """                    matching_rubs = [
                        r for r in rubrics
                        if code in [str(c).upper().strip() for c in (r.get("assessment_codes") or [])]
                        or code in [c.upper().strip() for c in str(r.get("assessment_code") or "").split(",") if c.strip()]
                        or (r.get("assessment_code") or "").upper().strip() == code
                        or code in (r.get("title") or "").upper()
                    ]"""

    content_norm = content.replace("\r\n", "\n")
    if old_title_part not in content_norm:
        raise Exception("old_title_part not found in syllabus_pdf_generator.py")
    content_norm = content_norm.replace(old_title_part, new_title_part, 1)

    if old_crit_tag not in content_norm:
        raise Exception("old_crit_tag not found in syllabus_pdf_generator.py")
    content_norm = content_norm.replace(old_crit_tag, new_crit_tag, 1)

    if old_matching not in content_norm:
        raise Exception("old_matching not found in syllabus_pdf_generator.py")
    content_norm = content_norm.replace(old_matching, new_matching, 1)

    with open("syllabus_pdf_generator.py", "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content_norm.replace("\n", "\r\n"))
    print("Successfully patched syllabus_pdf_generator.py")


def patch_templates_index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        content = f.read()
    content_norm = content.replace("\r\n", "\n")

    # 1. Request 1: Remove duplicate Passing Grade Conditions from Part III, IV & V
    old_part5_passing = """        <div class="form-group">

          <label>Workload of Students (Part V)</label>

          <textarea id="meta_workload_description" rows="4" oninput="syncMetaFromInputs()"></textarea>

        </div>

        <div class="form-group">

          <label>Passing Grade Conditions (Part VIII)</label>

          <textarea id="meta_passing_grade_conditions" rows="4" oninput="syncMetaFromInputs()"></textarea>

        </div>"""

    new_part5_passing = """        <div class="form-group">

          <label>Workload of Students (Part V)</label>

          <textarea id="meta_workload_description" rows="4" oninput="syncMetaFromInputs()"></textarea>

        </div>"""

    if old_part5_passing not in content_norm:
        raise Exception("old_part5_passing target not found in templates/index.html!")
    content_norm = content_norm.replace(old_part5_passing, new_part5_passing, 1)
    print("1. Removed duplicate Passing Grade Conditions from Part III, IV & V")

    # 2. Update Part VI attachedRubrics to use rubricAccommodatesAssessment
    old_part6_attached = """      // Find all rubrics attached to this assessment code

      const actCode = (act.code || "").toUpperCase().trim();

      const attachedRubrics = rubrics.filter((r, rIdx) => {

        r._origIdx = rIdx;

        return (r.assessment_code || "").toUpperCase().trim() === actCode || (!r.assessment_code && (r.title || "").toUpperCase().includes(actCode));

      });"""

    new_part6_attached = """      // Find all rubrics attached to this assessment code (supports multiple assessments per rubric)

      const actCode = (act.code || "").toUpperCase().trim();

      const attachedRubrics = rubrics.filter((r, rIdx) => {

        r._origIdx = rIdx;

        return rubricAccommodatesAssessment(r, actCode);

      });"""

    if old_part6_attached not in content_norm:
        raise Exception("old_part6_attached target not found in templates/index.html!")
    content_norm = content_norm.replace(old_part6_attached, new_part6_attached, 1)
    print("2. Updated Part VI attachedRubrics matching")

    # 3. Update Part VIII matchingRubrics to use rubricAccommodatesAssessment
    old_part8_attached = """      const actCode = (sa.code || "").toUpperCase().trim();

      const matchingRubrics = rubrics.filter(r => (r.assessment_code || "").toUpperCase().trim() === actCode || (r.title || "").toUpperCase().includes(actCode));"""

    new_part8_attached = """      const actCode = (sa.code || "").toUpperCase().trim();

      const matchingRubrics = rubrics.filter(r => rubricAccommodatesAssessment(r, actCode));"""

    if old_part8_attached not in content_norm:
        raise Exception("old_part8_attached target not found in templates/index.html!")
    content_norm = content_norm.replace(old_part8_attached, new_part8_attached, 1)
    print("3. Updated Part VIII matchingRubrics matching")

    # 4. Update Part VII renderRubrics header and criterion rendering
    # Look for rubric header in renderRubrics
    old_rubric_header_part = """            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">

              <!-- Aligned Assessment Activity -->

              <label style="font-size:0.75rem; font-weight:700; color:#475569; display:flex; align-items:center; gap:4px;">

                Assessment:

                <select style="font-size:0.75rem; font-weight:700; padding:4px 6px;"

                  onchange="updateRubricField(${rIdx}, 'assessment_code', this.value); renderSyllabusAssessmentActivitiesTable(); renderPart8GradingPlan();">

                  <option value="">-- General / Multi-Item --</option>

                  ${actSelectOptions}

                </select>

              </label>



              <!-- Weight sum badge -->

              <span style="font-size:0.75rem; font-weight:700; color:${weightColor}; background:#fff; padding:4px 8px; border-radius:4px; border:1px solid #e2e8f0;" title="Sum of criteria weights">

                Weight: ${weightSum.toFixed(0)}% ${isWeight100 ? '✓' : '⚠️'}

              </span>



              <button class="btn btn-outline-secondary btn-xs" onclick="duplicateRubric(${rIdx})" title="Duplicate rubric">📋 Duplicate</button>

              <button class="btn btn-outline-danger btn-xs" onclick="deleteRubric(${rIdx})" title="Delete rubric">&times; Delete</button>

            </div>"""

    new_rubric_header_part = """            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">

              <!-- Accommodated Assessments Group -->

              <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; background:#f1f5f9; padding:4px 8px; border-radius:6px; border:1px solid #cbd5e1;">

                <span style="font-size:0.73rem; font-weight:800; color:#334155;">Accommodates:</span>

                ${acts.length ? acts.map(a => {
                  const aCode = (a.code || "").trim();
                  const isChecked = rubricAccommodatesAssessment(rub, aCode);
                  return `
                    <label style="font-size:0.72rem; font-weight:700; padding:2px 7px; border-radius:4px; cursor:pointer; display:inline-flex; align-items:center; gap:3px; border:1px solid ${isChecked ? '#2563eb' : '#94a3b8'}; background:${isChecked ? '#dbeafe' : '#ffffff'}; color:${isChecked ? '#1e40af' : '#475569'}; user-select:none;" title="Click to toggle accommodation for ${escapeHtml(aCode)} (${escapeHtml(a.activity)})">
                      <input type="checkbox" style="margin:0; width:12px; height:12px;" ${isChecked ? "checked" : ""}
                        onchange="toggleRubricAssessmentCode(${rIdx}, '${escapeHtml(aCode)}')" />
                      ${escapeHtml(aCode)}
                    </label>
                  `;
                }).join("") : `<span style="font-size:0.71rem; color:#64748b; font-style:italic;">No Part VI activities</span>`}

                <input type="text" value="${escapeHtml(Array.isArray(rub.assessment_codes) ? rub.assessment_codes.join(', ') : (rub.assessment_code || ''))}"
                  placeholder="e.g. SA1, SA2" title="Type comma-separated assessment codes"
                  style="width:90px; font-size:0.72rem; font-weight:700; padding:2px 5px; border:1px solid #cbd5e1; border-radius:4px;"
                  oninput="updateRubricAssessmentCodes(${rIdx}, this.value)" />

              </div>



              <!-- Weight sum badge -->

              <span style="font-size:0.75rem; font-weight:700; color:${weightColor}; background:#fff; padding:4px 8px; border-radius:4px; border:1px solid #e2e8f0;" title="Sum of criteria weights">

                Weight: ${weightSum.toFixed(0)}% ${isWeight100 ? '✓' : '⚠️'}

              </span>



              <button class="btn btn-outline-secondary btn-xs" onclick="duplicateRubric(${rIdx})" title="Duplicate rubric">📋 Duplicate</button>

              <button class="btn btn-outline-danger btn-xs" onclick="deleteRubric(${rIdx})" title="Delete rubric">&times; Delete</button>

            </div>"""

    if old_rubric_header_part not in content_norm:
        raise Exception("old_rubric_header_part target not found in templates/index.html!")
    content_norm = content_norm.replace(old_rubric_header_part, new_rubric_header_part, 1)
    print("4. Updated rubric header with multi-assessment chip group")

    # 5. Add toggle for Aligned CLO per Criteria in toolbar
    old_scale_presets = """              <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">

                <span style="font-size:0.74rem; font-weight:700; color:#475569;">Scale Presets:</span>

                <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_6_points')" title="USeP 6-level score scale (5, 4, 3, 2, 1, 0)">6-Level (5 to 0)</button>

                <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_6_pct')" title="6-level percentage scale (100% to 0%)">6-Level (100%-0%)</button>

                <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_5_points')" title="5-level scale (5 to 1)">5-Level (5 to 1)</button>

                <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_4_mastery')" title="4-level mastery scale (Exemplary to Beginning)">4-Level Mastery</button>

                <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_3_rating')" title="3-level rating scale (Exceeds, Meets, Needs Improvement)">3-Level Scale</button>

              </div>"""

    new_scale_presets = """              <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">

                <div style="display:flex; align-items:center; gap:5px; flex-wrap:wrap;">

                  <span style="font-size:0.74rem; font-weight:700; color:#475569;">Scale Presets:</span>

                  <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_6_points')" title="USeP 6-level score scale (5, 4, 3, 2, 1, 0)">6-Level (5 to 0)</button>

                  <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_6_pct')" title="6-level percentage scale (100% to 0%)">6-Level (100%-0%)</button>

                  <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_5_points')" title="5-level scale (5 to 1)">5-Level (5 to 1)</button>

                  <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_4_mastery')" title="4-level mastery scale (Exemplary to Beginning)">4-Level Mastery</button>

                  <button type="button" class="btn btn-light btn-xs" onclick="setRubricPresetScale(${rIdx}, 'scale_3_rating')" title="3-level rating scale (Exceeds, Meets, Needs Improvement)">3-Level Scale</button>

                </div>

                <!-- Aligned CLO per criteria toggle (disabled by default) -->

                <label style="font-size:0.73rem; font-weight:700; color:${rub.enable_criteria_clos ? '#1e40af' : '#64748b'}; background:${rub.enable_criteria_clos ? '#eff6ff' : '#f8fafc'}; border:1px solid ${rub.enable_criteria_clos ? '#93c5fd' : '#cbd5e1'}; padding:3px 8px; border-radius:5px; display:inline-flex; align-items:center; gap:5px; cursor:pointer;" title="Enable or disable assigning a specific CLO to each individual criterion (disabled by default)">

                  <input type="checkbox" style="margin:0; width:13px; height:13px;" ${rub.enable_criteria_clos ? 'checked' : ''} onchange="toggleRubricCriteriaClos(${rIdx})" />

                  🏷️ Aligned CLO per Criteria: <strong>${rub.enable_criteria_clos ? 'Enabled' : 'Disabled (Default)'}</strong>

                </label>

              </div>"""

    if old_scale_presets not in content_norm:
        raise Exception("old_scale_presets target not found in templates/index.html!")
    content_norm = content_norm.replace(old_scale_presets, new_scale_presets, 1)
    print("5. Added Aligned CLO per Criteria toggle toolbar button")

    # 6. Update criteria row to conditionally render CLO selector only when enable_criteria_clos is true
    old_crit_clo_block = """                          <div style="display:flex; align-items:center; gap:4px; font-size:0.72rem;">

                            <span>CLO:</span>

                            <input type="text" value="${escapeHtml(crit.clo_id || '')}" placeholder="e.g. CLO1"

                              style="width:65px; font-size:0.72rem; font-weight:700;"

                              oninput="updateCriterionField(${rIdx}, ${cIdx}, 'clo_id', this.value)" />

                          </div>"""

    new_crit_clo_block = """                          ${rub.enable_criteria_clos ? `

                            <div style="display:flex; align-items:center; gap:4px; font-size:0.72rem; margin-top:3px; background:#eff6ff; padding:2px 4px; border-radius:4px; border:1px solid #bfdbfe;">

                              <span style="font-weight:700; color:#1e40af;">CLO:</span>

                              <select style="font-size:0.72rem; font-weight:700; padding:1px 3px; border:1px solid #93c5fd; border-radius:3px; background:#fff;"

                                onchange="updateCriterionField(${rIdx}, ${cIdx}, 'clo_id', this.value)">

                                <option value="">-- None --</option>

                                ${((blueprint.course_outcomes || []).map(co => `<option value="${escapeHtml(co.co_id)}" ${crit.clo_id === co.co_id ? 'selected' : ''}>${escapeHtml(co.co_id)}</option>`)).join("")}

                              </select>

                            </div>

                          ` : ''}"""

    if old_crit_clo_block not in content_norm:
        raise Exception("old_crit_clo_block target not found in templates/index.html!")
    content_norm = content_norm.replace(old_crit_clo_block, new_crit_clo_block, 1)
    print("6. Updated criterion row CLO rendering to respect enable_criteria_clos")

    # 7. Add helper functions before function renderRubrics()
    helper_code = """  // Helper functions for Multiple Accommodated Assessments per Rubric & Criteria CLO Toggle
  function rubricAccommodatesAssessment(rub, actCode) {
    if (!rub || !actCode) return false;
    const target = String(actCode).trim().toUpperCase();
    let list = [];
    if (Array.isArray(rub.assessment_codes) && rub.assessment_codes.length) {
      list = rub.assessment_codes.map(c => String(c).trim().toUpperCase());
    } else if (rub.assessment_code) {
      list = String(rub.assessment_code).split(/[,;/]+/).map(c => c.trim().toUpperCase()).filter(Boolean);
    }
    if (list.includes(target)) return true;
    if (!list.length && rub.title && rub.title.toUpperCase().includes(target)) return true;
    return false;
  }

  function toggleRubricAssessmentCode(rIdx, actCode) {
    if (!blueprint || !blueprint.rubrics || !blueprint.rubrics[rIdx]) return;
    const rub = blueprint.rubrics[rIdx];
    const code = String(actCode).trim().toUpperCase();
    let list = Array.isArray(rub.assessment_codes)
      ? [...rub.assessment_codes]
      : (rub.assessment_code ? String(rub.assessment_code).split(/[,;/]+/).map(c => c.trim().toUpperCase()).filter(Boolean) : []);
    if (list.includes(code)) {
      list = list.filter(c => c !== code);
    } else {
      list.push(code);
    }
    rub.assessment_codes = list;
    rub.assessment_code = list.join(", ");
    renderRubrics();
    renderSyllabusAssessmentActivitiesTable();
    renderPart8GradingPlan();
    queueAutoSave();
  }

  function updateRubricAssessmentCodes(rIdx, val) {
    if (!blueprint || !blueprint.rubrics || !blueprint.rubrics[rIdx]) return;
    const rub = blueprint.rubrics[rIdx];
    const list = (val || "").split(/[,;/]+/).map(s => s.trim().toUpperCase()).filter(Boolean);
    rub.assessment_codes = list;
    rub.assessment_code = list.join(", ");
    renderSyllabusAssessmentActivitiesTable();
    renderPart8GradingPlan();
    queueAutoSave();
  }

  function toggleRubricCriteriaClos(rIdx) {
    if (!blueprint || !blueprint.rubrics || !blueprint.rubrics[rIdx]) return;
    const rub = blueprint.rubrics[rIdx];
    rub.enable_criteria_clos = !Boolean(rub.enable_criteria_clos);
    renderRubrics();
    queueAutoSave();
  }
"""

    old_render_rubrics_def = """  function renderRubrics() {"""
    new_render_rubrics_def = helper_code + "\n  function renderRubrics() {"
    if old_render_rubrics_def not in content_norm:
        raise Exception("old_render_rubrics_def target not found in templates/index.html!")
    content_norm = content_norm.replace(old_render_rubrics_def, new_render_rubrics_def, 1)
    print("7. Inserted multi-assessment and criteria CLO helper functions")

    # 8. Update addNewRubric() to set enable_criteria_clos: false and assessment_codes: []
    old_add_new_rubric = """  function addNewRubric() {

    if (!blueprint) return;

    if (!Array.isArray(blueprint.rubrics)) blueprint.rubrics = [];

    blueprint.rubrics.push({

      rubric_id: "rubric_" + Math.random().toString(36).substring(2, 6),

      title: "New Assessment Rubric",

      assessment_code: "",

      target_part: "Entire Assessment","""

    new_add_new_rubric = """  function addNewRubric() {

    if (!blueprint) return;

    if (!Array.isArray(blueprint.rubrics)) blueprint.rubrics = [];

    blueprint.rubrics.push({

      rubric_id: "rubric_" + Math.random().toString(36).substring(2, 6),

      title: "New Assessment Rubric",

      assessment_code: "",

      assessment_codes: [],

      enable_criteria_clos: false,

      target_part: "Entire Assessment","""

    if old_add_new_rubric not in content_norm:
        raise Exception("old_add_new_rubric target not found in templates/index.html!")
    content_norm = content_norm.replace(old_add_new_rubric, new_add_new_rubric, 1)
    print("8. Updated addNewRubric() defaults")

    with open("templates/index.html", "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content_norm.replace("\n", "\r\n"))
    print("Successfully patched templates/index.html")

if __name__ == "__main__":
    patch_syllabus_pdf_generator()
    patch_templates_index()
