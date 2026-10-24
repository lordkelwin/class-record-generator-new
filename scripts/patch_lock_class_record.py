# scripts/patch_lock_class_record.py
import re

def patch_courses_store():
    with open("courses_store.py", "r", encoding="utf-8") as f:
        content = f.read()

    target = """    # Enforce syllabus workflow locks on blueprint
    wf = payload.get("workflow") or existing.get("workflow") or syllabus_workflow.default_workflow()
    temp_doc = {"blueprint": existing.get("blueprint"), "workflow": wf, "owner": username}
    bp_dict = syllabus_workflow.enforce_locks(temp_doc, bp_dict)

    # Enforce class record grade locks (freeze student scores when under sign-off or finalized)
    cr_wf = payload.get("class_record_workflow") or existing.get("class_record_workflow") or class_record_workflow.default_class_record_workflow(username)
    if existing and class_record_workflow.is_class_record_locked({"class_record_workflow": cr_wf}):
        old_bp = existing.get("blueprint") or {}
        if "students" in old_bp:
            bp_dict["students"] = old_bp["students"]
        if "categories" in old_bp:
            bp_dict["categories"] = old_bp["categories"]"""

    replacement = """    # Enforce syllabus workflow locks on blueprint (existing workflow cannot be forged)
    wf = existing.get("workflow") or payload.get("workflow") or syllabus_workflow.default_workflow()
    temp_doc = {"blueprint": existing.get("blueprint"), "workflow": wf, "owner": username}
    bp_dict = syllabus_workflow.enforce_locks(temp_doc, bp_dict)

    # Enforce syllabus approval barrier for Class Record Setup (categories) and Grades (students)
    is_syllabus_approved = (wf or {}).get("status") == "approved"
    if existing and not is_syllabus_approved:
        old_bp = existing.get("blueprint") or {}
        if "students" in old_bp:
            bp_dict["students"] = old_bp["students"]
        if "categories" in old_bp:
            bp_dict["categories"] = old_bp["categories"]

    # Enforce class record grade locks (freeze student scores when under sign-off or finalized)
    cr_wf = existing.get("class_record_workflow") or payload.get("class_record_workflow") or class_record_workflow.default_class_record_workflow(username)
    if existing and class_record_workflow.is_class_record_locked({"class_record_workflow": cr_wf}):
        old_bp = existing.get("blueprint") or {}
        if "students" in old_bp:
            bp_dict["students"] = old_bp["students"]
        if "categories" in old_bp:
            bp_dict["categories"] = old_bp["categories"]"""

    # Normalize line endings for replacement
    content_norm = content.replace("\r\n", "\n")
    target_norm = target.replace("\r\n", "\n")
    replacement_norm = replacement.replace("\r\n", "\n")

    if target_norm not in content_norm:
        raise Exception("Target not found in courses_store.py!")

    content_norm = content_norm.replace(target_norm, replacement_norm, 1)
    with open("courses_store.py", "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content_norm.replace("\n", "\r\n"))
    print("Successfully patched courses_store.py")


def patch_templates_index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        content = f.read()

    content_norm = content.replace("\r\n", "\n")

    # 1. Tab 2 and Tab 3 markup wrapping
    old_tabs_markup = """    </div>
    <div class="card">
      <div class="card-header">
        <div>
          <h2>Setup: Midterm &amp; Finals Formative (FA) and Summative (SA) Assessments (Per-CLO Points &amp; Auto-Sum Total Points)</h2>
          <div style="font-size:0.78rem; color:#475569; margin-top:2px;">
            Specify the number of points for each aligned CLO. <strong>Total Points</strong> is automatically summed from the aligned CLOs (or equals the single CLO's points if only one CLO is aligned).
          </div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn btn-success btn-sm" onclick="syncClassRecordSetupFromSyllabus(false)" title="Rebuild/Sync Assessments & Aligned CLOs from Tab 1 Syllabus Creator">Sync from Syllabus Creator (Tab 1)</button>
          <button class="btn btn-light btn-sm" onclick="addAssessmentCategory('Midterm', 'FA')">+ Midterm FA</button>
          <button class="btn btn-primary btn-sm" onclick="addAssessmentCategory('Midterm', 'SA')">+ Midterm SA</button>
          <button class="btn btn-light btn-sm" onclick="addAssessmentCategory('Finals', 'FA')">+ Finals FA</button>
          <button class="btn btn-primary btn-sm" onclick="addAssessmentCategory('Finals', 'SA')">+ Finals SA</button>
        </div>
      </div>
      <div id="categoriesContainer"></div>
    </div>
  </div>

  <!-- TAB 3: CONSOLIDATED CLASS RECORD & CLO GRADES -->
  <div id="tab-gradebook" class="tab-panel">
    <!-- CLASS RECORD LOCK BARRIER (Tab 3) -->
    <div id="classRecordLockBannerGradebook" class="lock-barrier-banner" style="display:none; background:#fff7ed; border:2px solid #f97316; border-radius:8px; padding:18px 22px; margin-bottom:18px; text-align:center;">
      <div style="font-size:2rem; margin-bottom:6px;">🔒</div>
      <h3 style="margin:0 0 6px; color:#9a3412; font-size:1.15rem;">Consolidated Class Record Locked</h3>
      <p style="margin:0 auto 12px; max-width:650px; font-size:0.85rem; color:#7c2d12;">
        Before entering student scores or generating grades, <strong>the syllabus must be approved first</strong> by the Review Committee, Program Head, College QA Head (countersigned), and Dean.
      </p>
      <div style="display:flex; justify-content:center; gap:10px;">
        <button class="btn btn-primary btn-sm" onclick="switchTab('tab-syllabus')">View Syllabus &amp; Approval Stepper &rarr;</button>
        <button class="btn btn-outline-primary btn-sm" onclick="openEvaluationToolModal()">Open Syllabus Evaluation Tool</button>
      </div>
    </div>

    <!-- CLASS RECORD SEQUENTIAL SIGN-OFF & GRADE FREEZE WORKFLOW BANNER -->"""

    new_tabs_markup = """    </div>
    <div id="setupTabContent" class="card">
      <div class="card-header">
        <div>
          <h2>Setup: Midterm &amp; Finals Formative (FA) and Summative (SA) Assessments (Per-CLO Points &amp; Auto-Sum Total Points)</h2>
          <div style="font-size:0.78rem; color:#475569; margin-top:2px;">
            Specify the number of points for each aligned CLO. <strong>Total Points</strong> is automatically summed from the aligned CLOs (or equals the single CLO's points if only one CLO is aligned).
          </div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button id="btnSyncFromSyllabus" class="btn btn-success btn-sm" onclick="syncClassRecordSetupFromSyllabus(false)" title="Rebuild/Sync Assessments & Aligned CLOs from Tab 1 Syllabus Creator">Sync from Syllabus Creator (Tab 1)</button>
          <button id="btnAddMidtermFa" class="btn btn-light btn-sm" onclick="addAssessmentCategory('Midterm', 'FA')">+ Midterm FA</button>
          <button id="btnAddMidtermSa" class="btn btn-primary btn-sm" onclick="addAssessmentCategory('Midterm', 'SA')">+ Midterm SA</button>
          <button id="btnAddFinalsFa" class="btn btn-light btn-sm" onclick="addAssessmentCategory('Finals', 'FA')">+ Finals FA</button>
          <button id="btnAddFinalsSa" class="btn btn-primary btn-sm" onclick="addAssessmentCategory('Finals', 'SA')">+ Finals SA</button>
        </div>
      </div>
      <div id="categoriesContainer"></div>
    </div>
  </div>

  <!-- TAB 3: CONSOLIDATED CLASS RECORD & CLO GRADES -->
  <div id="tab-gradebook" class="tab-panel">
    <!-- CLASS RECORD LOCK BARRIER (Tab 3) -->
    <div id="classRecordLockBannerGradebook" class="lock-barrier-banner" style="display:none; background:#fff7ed; border:2px solid #f97316; border-radius:8px; padding:18px 22px; margin-bottom:18px; text-align:center;">
      <div style="font-size:2rem; margin-bottom:6px;">🔒</div>
      <h3 style="margin:0 0 6px; color:#9a3412; font-size:1.15rem;">Consolidated Class Record Locked</h3>
      <p style="margin:0 auto 12px; max-width:650px; font-size:0.85rem; color:#7c2d12;">
        Before entering student scores or generating grades, <strong>the syllabus must be approved first</strong> by the Review Committee, Program Head, College QA Head (countersigned), and Dean.
      </p>
      <div style="display:flex; justify-content:center; gap:10px;">
        <button class="btn btn-primary btn-sm" onclick="switchTab('tab-syllabus')">View Syllabus &amp; Approval Stepper &rarr;</button>
        <button class="btn btn-outline-primary btn-sm" onclick="openEvaluationToolModal()">Open Syllabus Evaluation Tool</button>
      </div>
    </div>

    <!-- WRAPPER FOR TAB 3 CONTENT (LOCKED UNTIL SYLLABUS IS APPROVED) -->
    <div id="gradebookTabContent">
      <!-- CLASS RECORD SEQUENTIAL SIGN-OFF & GRADE FREEZE WORKFLOW BANNER -->"""

    if old_tabs_markup not in content_norm:
        raise Exception("Markup target 1 not found in templates/index.html!")
    content_norm = content_norm.replace(old_tabs_markup, new_tabs_markup, 1)

    # Closing tag for gradebookTabContent:
    old_tab3_end = """        <table id="liveGradebookTable"></table>
      </div>
    </div>
  </div>

  <!-- TAB 4: CLO ASSESSMENT REPORT & CO ASSESSMENT TOOL -->"""

    new_tab3_end = """        <table id="liveGradebookTable"></table>
      </div>
    </div>
    </div>
  </div>

  <!-- TAB 4: CLO ASSESSMENT REPORT & CO ASSESSMENT TOOL -->"""

    if old_tab3_end not in content_norm:
        raise Exception("Markup target 2 (tab 3 end) not found in templates/index.html!")
    content_norm = content_norm.replace(old_tab3_end, new_tab3_end, 1)

    # 2. checkClassRecordLock() implementation
    old_check_lock = """  // Enforce Class Record Lock Barrier on Tabs 2 & 3 & Grade Freeze
  function checkClassRecordLock() {
    const isSyllabusApproved = currentWorkflow && (currentWorkflow.status === "approved");
    const b2 = document.getElementById("classRecordLockBannerAssessments");
    const b3 = document.getElementById("classRecordLockBannerGradebook");
    if (b2) b2.style.display = isSyllabusApproved ? "none" : "block";
    if (b3) b3.style.display = isSyllabusApproved ? "none" : "block";

    // Disable / Dim setup and gradebook interactive controls if syllabus not approved
    const setupContent = document.getElementById("setupTabContent");
    if (setupContent) {
      setupContent.style.opacity = isSyllabusApproved ? "1" : "0.55";
      setupContent.style.pointerEvents = isSyllabusApproved ? "auto" : "none";
    }
    const gradebookContent = document.getElementById("gradebookTabContent");
    if (gradebookContent) {
      gradebookContent.style.opacity = isSyllabusApproved ? "1" : "0.55";
      gradebookContent.style.pointerEvents = isSyllabusApproved ? "auto" : "none";
    }

    // Class record grade freeze banner
    const isCrLocked = currentClassRecordWorkflow && Boolean(currentClassRecordWorkflow.is_locked);
    const crFreezeBanner = document.getElementById("classRecordFrozenBanner");
    if (crFreezeBanner) {
      crFreezeBanner.style.display = isCrLocked ? "block" : "none";
      if (isCrLocked && currentClassRecordWorkflow) {
        const stageEl = document.getElementById("crFreezeStageLabel");
        if (stageEl) stageEl.textContent = currentClassRecordWorkflow.status_label || currentClassRecordWorkflow.status;
      }
    }
  }"""

    new_check_lock = """  // Enforce Class Record Lock Barrier on Tabs 2 & 3 & Grade Freeze
  function checkClassRecordLock() {
    const isSyllabusApproved = currentWorkflow && (currentWorkflow.status === "approved");
    const b2 = document.getElementById("classRecordLockBannerAssessments");
    const b3 = document.getElementById("classRecordLockBannerGradebook");
    if (b2) b2.style.display = isSyllabusApproved ? "none" : "block";
    if (b3) b3.style.display = isSyllabusApproved ? "none" : "block";

    // Disable / Dim setup interactive controls if syllabus not approved
    const setupContent = document.getElementById("setupTabContent");
    if (setupContent) {
      setupContent.style.opacity = isSyllabusApproved ? "1" : "0.5";
      setupContent.style.pointerEvents = isSyllabusApproved ? "auto" : "none";
      setupContent.style.userSelect = isSyllabusApproved ? "auto" : "none";
      setupContent.querySelectorAll("input, select, textarea, button").forEach(el => {
        el.disabled = !isSyllabusApproved;
        if (!isSyllabusApproved) {
          el.title = "Locked: Syllabus must be approved through the review chain before setting up assessments.";
          el.style.cursor = "not-allowed";
        } else {
          el.removeAttribute("title");
          el.style.cursor = "";
        }
      });
    }

    // Disable / Dim gradebook interactive controls if syllabus not approved
    const gradebookContent = document.getElementById("gradebookTabContent");
    if (gradebookContent) {
      gradebookContent.style.opacity = isSyllabusApproved ? "1" : "0.5";
      gradebookContent.style.pointerEvents = isSyllabusApproved ? "auto" : "none";
      gradebookContent.style.userSelect = isSyllabusApproved ? "auto" : "none";
      gradebookContent.querySelectorAll("input, select, textarea, button").forEach(el => {
        el.disabled = !isSyllabusApproved;
        if (!isSyllabusApproved) {
          el.title = "Locked: Syllabus must be approved through the review chain before entering student scores.";
          el.style.cursor = "not-allowed";
        } else {
          el.removeAttribute("title");
          el.style.cursor = "";
        }
      });
    }

    // Class record grade freeze banner
    const isCrLocked = currentClassRecordWorkflow && Boolean(currentClassRecordWorkflow.is_locked);
    const crFreezeBanner = document.getElementById("classRecordFrozenBanner");
    if (crFreezeBanner) {
      crFreezeBanner.style.display = (isSyllabusApproved && isCrLocked) ? "block" : "none";
      if (isCrLocked && currentClassRecordWorkflow) {
        const stageEl = document.getElementById("crFreezeStageLabel");
        if (stageEl) stageEl.textContent = currentClassRecordWorkflow.status_label || currentClassRecordWorkflow.status;
      }
    }
  }"""

    if old_check_lock not in content_norm:
        raise Exception("checkClassRecordLock target not found!")
    content_norm = content_norm.replace(old_check_lock, new_check_lock, 1)

    # 3. switchTab(tabId, btnEl)
    old_switch_tab = """    if (tabId === "tab-approvals") {
      loadApprovalRequests(true);
    } else {
      renderLiveGradebookAndReports();
    }
  }"""

    new_switch_tab = """    if (tabId === "tab-approvals") {
      loadApprovalRequests(true);
    } else {
      renderLiveGradebookAndReports();
    }
    checkClassRecordLock();
    checkSyllabusLock();
  }"""

    if old_switch_tab not in content_norm:
        raise Exception("switchTab target not found!")
    content_norm = content_norm.replace(old_switch_tab, new_switch_tab, 1)

    # 4. renderCategories()
    old_render_cats_start = """  function renderCategories() {
    if (!blueprint) return;
    const coOptions = (blueprint.course_outcomes || []).map(c => c.co_id);
    const container = document.getElementById("categoriesContainer");"""

    new_render_cats_start = """  function renderCategories() {
    if (!blueprint) return;
    const isSyllabusApproved = currentWorkflow && (currentWorkflow.status === "approved");
    const disAttr = !isSyllabusApproved ? 'disabled="disabled"' : '';
    const disStyle = !isSyllabusApproved ? 'cursor:not-allowed; opacity:0.6;' : '';
    const coOptions = (blueprint.course_outcomes || []).map(c => c.co_id);
    const container = document.getElementById("categoriesContainer");"""

    if old_render_cats_start not in content_norm:
        raise Exception("renderCategories start target not found!")
    content_norm = content_norm.replace(old_render_cats_start, new_render_cats_start, 1)

    # Update item and category controls in renderCategories
    old_cat_inputs = """        const cloChipsHtml = coOptions.map(cid => {
          const isChecked = selectedClos.includes(cid);
          return `
            <label class="clo-chip ${isChecked ? 'active' : ''}" title="Toggle ${escapeHtml(cid)} alignment">
              <input type="checkbox" ${isChecked ? "checked" : ""}
                onchange="toggleItemClo(${cIdx}, ${iIdx}, '${escapeHtml(cid)}')" />
              ${escapeHtml(cid)}
            </label>
          `;
        }).join("");
        const allBtnHtml = coOptions.length > 1
          ? `<button type="button" class="btn btn-light btn-sm" style="padding:2px 7px; font-size:0.71rem; ${allChecked ? 'background:#dbeafe; color:#1e40af; border-color:#93c5fd;' : ''}"
               onclick="setItemAllClos(${cIdx}, ${iIdx})" title="Align item to all CLOs">All CLOs</button>`
          : "";
        const ptsPreview = formatCloPointsPreview(it);

        // Separate score max points input cell for every CLO in the course:
        // Only aligned CLOs have active point inputs; Total Points is automatically summed from aligned CLOs!
        const perCloPtCellsHtml = coOptions.map(cid => {
          const isAligned = selectedClos.includes(cid);
          const cloVal = isAligned ? (ptsMap[cid.toUpperCase()] || 0) : 0;
          if (!isAligned) {
            return `
              <td style="width:110px; text-align:center; background:#f8fafc; color:#94a3b8; font-size:0.75rem;">
                <div>&mdash;</div>
                <div style="font-size:0.68rem;">Not Aligned</div>
              </td>
            `;
          }
          return `
            <td style="width:110px; text-align:center; background:#fffbeb;">
              <input type="number" min="1" step="1" value="${cloVal}"
                title="Specify points for ${escapeHtml(cid)} in ${escapeHtml(it.item_id)}"
                style="text-align:center; font-weight:700; border-color:#f59e0b; background:#ffffff;"
                onchange="updateItemCloPoint(${cIdx}, ${iIdx}, '${escapeHtml(cid)}', this.value)" />
              <div style="font-size:0.68rem; color:#92400e; font-weight:600; margin-top:2px;">${escapeHtml(cid)} Pts</div>
            </td>
          `;
        }).join("");

        const sumFormulaHint = selectedClos.length === 1
          ? `= ${selectedClos[0]} (${ptsMap[selectedClos[0].toUpperCase()] || it.max_score} pts)`
          : `= ${selectedClos.map(c => ptsMap[c.toUpperCase()] || 0).join(" + ")} pts`;

        return `
        <tr>
          <td style="width:90px;"><input type="text" value="${escapeHtml(it.item_id)}" style="font-weight:700;" onchange="blueprint.categories[${cIdx}].items[${iIdx}].item_id=this.value.trim(); renderLiveGradebookAndReports();" /></td>
          <td><input type="text" value="${escapeHtml(it.name)}" onchange="blueprint.categories[${cIdx}].items[${iIdx}].name=this.value;" /></td>
          <td style="width:225px;">
            <div class="clo-multi-wrap">
              ${cloChipsHtml}
              ${allBtnHtml}
            </div>
            <div class="clo-pts-hint">Setup Mapping: <strong>${escapeHtml(ptsPreview)}</strong></div>
          </td>
          ${perCloPtCellsHtml}
          <td style="width:120px; text-align:center; background:#eff6ff;">
            <input type="number" value="${it.max_score}" readonly
              style="font-weight:800; text-align:center; background:#dbeafe; color:#1e3a8a; border-color:#93c5fd; cursor:not-allowed;"
              title="Automatically summed from aligned CLO points (${escapeHtml(sumFormulaHint)})" />
            <div style="font-size:0.68rem; color:#1e40af; font-weight:700; margin-top:2px;">${escapeHtml(sumFormulaHint)}</div>
          </td>
          <td style="width:105px;">
            <input type="number" value="${it.weight_pct}" min="0" max="100" style="text-align:center;"
              onchange="blueprint.categories[${cIdx}].items[${iIdx}].weight_pct=parseFloat(this.value)||0; renderLiveGradebookAndReports();" />
          </td>
          <td style="width:55px;"><button class="btn btn-danger btn-sm" onclick="removeAssessmentItem(${cIdx}, ${iIdx})">&times;</button></td>
        </tr>
        `;
      }).join("");

      const perCloHeadersHtml = coOptions.map(cid => `
        <th style="text-align:center; background:#fef3c7; color:#92400e;">${escapeHtml(cid)} Points</th>
      `).join("");

      return `
        <div class="cat-block">
          <div class="cat-top">
            <span class="badge ${isFa ? 'badge-fa' : 'badge-sa'}">${isFa ? 'FORMATIVE (FA)' : 'SUMMATIVE (SA)'}</span>
            <select style="width:110px; padding:5px;" onchange="blueprint.categories[${cIdx}].term=this.value; updateWeightSummaryBadge(); renderLiveGradebookAndReports();">
              <option value="Midterm" ${cat.term === "Midterm" ? "selected" : ""}>Midterm</option>
              <option value="Finals" ${cat.term === "Finals" ? "selected" : ""}>Finals</option>
            </select>
            <select style="width:75px; padding:5px;" onchange="blueprint.categories[${cIdx}].assessment_type=this.value; renderCategories(); renderLiveGradebookAndReports();">
              <option value="FA" ${isFa ? "selected" : ""}>FA</option>
              <option value="SA" ${!isFa ? "selected" : ""}>SA</option>
            </select>
            <input type="text" style="width:70px; padding:5px; font-weight:700;" value="${escapeHtml(cat.assessment_code)}"
              onchange="blueprint.categories[${cIdx}].assessment_code=this.value.trim(); renderLiveGradebookAndReports();" />
            <input type="text" style="width:255px; padding:5px; font-weight:600;" value="${escapeHtml(cat.name)}"
              onchange="blueprint.categories[${cIdx}].name=this.value; renderLiveGradebookAndReports();" />
            <label style="font-size:0.8rem; font-weight:700;">SA Term Weight (%):</label>
            <input type="number" style="width:70px; padding:5px;" value="${cat.weight_pct}" min="0" max="100"
              onchange="blueprint.categories[${cIdx}].weight_pct=parseFloat(this.value)||0; updateWeightSummaryBadge(); renderLiveGradebookAndReports();" />
            <button type="button" class="btn btn-light btn-sm" onclick="setCategoryAllItemsClo(${cIdx}, 'ALL')" title="Align all items in this assessment to all CLOs">Align All Items &rarr; All CLOs</button>
            <button class="btn btn-light btn-sm" onclick="addAssessmentItem(${cIdx})">+ Add Item</button>
            <button class="btn btn-danger btn-sm" onclick="removeAssessmentCategory(${cIdx})">Delete</button>
          </div>"""

    new_cat_inputs = """        const cloChipsHtml = coOptions.map(cid => {
          const isChecked = selectedClos.includes(cid);
          return `
            <label class="clo-chip ${isChecked ? 'active' : ''}" title="Toggle ${escapeHtml(cid)} alignment">
              <input type="checkbox" ${isChecked ? "checked" : ""} ${disAttr} style="${disStyle}"
                onchange="toggleItemClo(${cIdx}, ${iIdx}, '${escapeHtml(cid)}')" />
              ${escapeHtml(cid)}
            </label>
          `;
        }).join("");
        const allBtnHtml = coOptions.length > 1
          ? `<button type="button" class="btn btn-light btn-sm" ${disAttr} style="padding:2px 7px; font-size:0.71rem; ${allChecked ? 'background:#dbeafe; color:#1e40af; border-color:#93c5fd;' : ''} ${disStyle}"
               onclick="setItemAllClos(${cIdx}, ${iIdx})" title="Align item to all CLOs">All CLOs</button>`
          : "";
        const ptsPreview = formatCloPointsPreview(it);

        // Separate score max points input cell for every CLO in the course:
        // Only aligned CLOs have active point inputs; Total Points is automatically summed from aligned CLOs!
        const perCloPtCellsHtml = coOptions.map(cid => {
          const isAligned = selectedClos.includes(cid);
          const cloVal = isAligned ? (ptsMap[cid.toUpperCase()] || 0) : 0;
          if (!isAligned) {
            return `
              <td style="width:110px; text-align:center; background:#f8fafc; color:#94a3b8; font-size:0.75rem;">
                <div>&mdash;</div>
                <div style="font-size:0.68rem;">Not Aligned</div>
              </td>
            `;
          }
          return `
            <td style="width:110px; text-align:center; background:#fffbeb;">
              <input type="number" min="1" step="1" value="${cloVal}" ${disAttr}
                title="Specify points for ${escapeHtml(cid)} in ${escapeHtml(it.item_id)}"
                style="text-align:center; font-weight:700; border-color:#f59e0b; background:#ffffff; ${disStyle}"
                onchange="updateItemCloPoint(${cIdx}, ${iIdx}, '${escapeHtml(cid)}', this.value)" />
              <div style="font-size:0.68rem; color:#92400e; font-weight:600; margin-top:2px;">${escapeHtml(cid)} Pts</div>
            </td>
          `;
        }).join("");

        const sumFormulaHint = selectedClos.length === 1
          ? `= ${selectedClos[0]} (${ptsMap[selectedClos[0].toUpperCase()] || it.max_score} pts)`
          : `= ${selectedClos.map(c => ptsMap[c.toUpperCase()] || 0).join(" + ")} pts`;

        return `
        <tr>
          <td style="width:90px;"><input type="text" value="${escapeHtml(it.item_id)}" ${disAttr} style="font-weight:700; ${disStyle}" onchange="blueprint.categories[${cIdx}].items[${iIdx}].item_id=this.value.trim(); renderLiveGradebookAndReports();" /></td>
          <td><input type="text" value="${escapeHtml(it.name)}" ${disAttr} style="${disStyle}" onchange="blueprint.categories[${cIdx}].items[${iIdx}].name=this.value;" /></td>
          <td style="width:225px;">
            <div class="clo-multi-wrap">
              ${cloChipsHtml}
              ${allBtnHtml}
            </div>
            <div class="clo-pts-hint">Setup Mapping: <strong>${escapeHtml(ptsPreview)}</strong></div>
          </td>
          ${perCloPtCellsHtml}
          <td style="width:120px; text-align:center; background:#eff6ff;">
            <input type="number" value="${it.max_score}" readonly
              style="font-weight:800; text-align:center; background:#dbeafe; color:#1e3a8a; border-color:#93c5fd; cursor:not-allowed;"
              title="Automatically summed from aligned CLO points (${escapeHtml(sumFormulaHint)})" />
            <div style="font-size:0.68rem; color:#1e40af; font-weight:700; margin-top:2px;">${escapeHtml(sumFormulaHint)}</div>
          </td>
          <td style="width:105px;">
            <input type="number" value="${it.weight_pct}" min="0" max="100" ${disAttr} style="text-align:center; ${disStyle}"
              onchange="blueprint.categories[${cIdx}].items[${iIdx}].weight_pct=parseFloat(this.value)||0; renderLiveGradebookAndReports();" />
          </td>
          <td style="width:55px;"><button class="btn btn-danger btn-sm" ${disAttr} style="${disStyle}" onclick="removeAssessmentItem(${cIdx}, ${iIdx})">&times;</button></td>
        </tr>
        `;
      }).join("");

      const perCloHeadersHtml = coOptions.map(cid => `
        <th style="text-align:center; background:#fef3c7; color:#92400e;">${escapeHtml(cid)} Points</th>
      `).join("");

      return `
        <div class="cat-block">
          <div class="cat-top">
            <span class="badge ${isFa ? 'badge-fa' : 'badge-sa'}">${isFa ? 'FORMATIVE (FA)' : 'SUMMATIVE (SA)'}</span>
            <select style="width:110px; padding:5px; ${disStyle}" ${disAttr} onchange="blueprint.categories[${cIdx}].term=this.value; updateWeightSummaryBadge(); renderLiveGradebookAndReports();">
              <option value="Midterm" ${cat.term === "Midterm" ? "selected" : ""}>Midterm</option>
              <option value="Finals" ${cat.term === "Finals" ? "selected" : ""}>Finals</option>
            </select>
            <select style="width:75px; padding:5px; ${disStyle}" ${disAttr} onchange="blueprint.categories[${cIdx}].assessment_type=this.value; renderCategories(); renderLiveGradebookAndReports();">
              <option value="FA" ${isFa ? "selected" : ""}>FA</option>
              <option value="SA" ${!isFa ? "selected" : ""}>SA</option>
            </select>
            <input type="text" style="width:70px; padding:5px; font-weight:700; ${disStyle}" ${disAttr} value="${escapeHtml(cat.assessment_code)}"
              onchange="blueprint.categories[${cIdx}].assessment_code=this.value.trim(); renderLiveGradebookAndReports();" />
            <input type="text" style="width:255px; padding:5px; font-weight:600; ${disStyle}" ${disAttr} value="${escapeHtml(cat.name)}"
              onchange="blueprint.categories[${cIdx}].name=this.value; renderLiveGradebookAndReports();" />
            <label style="font-size:0.8rem; font-weight:700;">SA Term Weight (%):</label>
            <input type="number" style="width:70px; padding:5px; ${disStyle}" ${disAttr} value="${cat.weight_pct}" min="0" max="100"
              onchange="blueprint.categories[${cIdx}].weight_pct=parseFloat(this.value)||0; updateWeightSummaryBadge(); renderLiveGradebookAndReports();" />
            <button type="button" class="btn btn-light btn-sm" ${disAttr} style="${disStyle}" onclick="setCategoryAllItemsClo(${cIdx}, 'ALL')" title="Align all items in this assessment to all CLOs">Align All Items &rarr; All CLOs</button>
            <button class="btn btn-light btn-sm" ${disAttr} style="${disStyle}" onclick="addAssessmentItem(${cIdx})">+ Add Item</button>
            <button class="btn btn-danger btn-sm" ${disAttr} style="${disStyle}" onclick="removeAssessmentCategory(${cIdx})">Delete</button>
          </div>"""

    if old_cat_inputs not in content_norm:
        raise Exception("Category inputs target not found!")
    content_norm = content_norm.replace(old_cat_inputs, new_cat_inputs, 1)

    # Call checkClassRecordLock at end of renderCategories
    old_cat_end = """    updateWeightSummaryBadge();
  }"""

    new_cat_end = """    updateWeightSummaryBadge();
    checkClassRecordLock();
  }"""

    if old_cat_end not in content_norm:
        raise Exception("renderCategories end target not found!")
    content_norm = content_norm.replace(old_cat_end, new_cat_end, 1)

    # 5. renderLiveGradebookAndReports()
    old_gradebook_start = """  function renderLiveGradebookAndReports() {
    if (!blueprint) return;
    const tbl = document.getElementById("liveGradebookTable");
    const isCrLocked = currentClassRecordWorkflow && Boolean(currentClassRecordWorkflow.is_locked);
    const btnAddSt = document.getElementById("btnCrAddStudent");
    if (btnAddSt) {
      btnAddSt.disabled = isCrLocked;
      btnAddSt.title = isCrLocked ? "Class record is locked during sign-off / finalization" : "+ Add Student";
    }
    const btnImpRoster = document.getElementById("btnCrImportRoster");
    if (btnImpRoster) {
      btnImpRoster.disabled = isCrLocked;
      btnImpRoster.title = isCrLocked ? "Class record is locked during sign-off / finalization" : "Import Roster";
    }"""

    new_gradebook_start = """  function renderLiveGradebookAndReports() {
    if (!blueprint) return;
    const tbl = document.getElementById("liveGradebookTable");
    const isSyllabusApproved = currentWorkflow && (currentWorkflow.status === "approved");
    const isCrLocked = (currentClassRecordWorkflow && Boolean(currentClassRecordWorkflow.is_locked)) || !isSyllabusApproved;
    const btnAddSt = document.getElementById("btnCrAddStudent");
    if (btnAddSt) {
      btnAddSt.disabled = isCrLocked;
      btnAddSt.title = !isSyllabusApproved
        ? "Class record is locked until syllabus is approved"
        : (isCrLocked ? "Class record is locked during sign-off / finalization" : "+ Add Student");
    }
    const btnImpRoster = document.getElementById("btnCrImportRoster");
    if (btnImpRoster) {
      btnImpRoster.disabled = isCrLocked;
      btnImpRoster.title = !isSyllabusApproved
        ? "Class record is locked until syllabus is approved"
        : (isCrLocked ? "Class record is locked during sign-off / finalization" : "Import Roster");
    }
    const rosterInp = document.getElementById("rosterFileInput");
    if (rosterInp) {
      rosterInp.disabled = isCrLocked;
      rosterInp.title = !isSyllabusApproved
        ? "Class record is locked until syllabus is approved"
        : "Import Roster";
    }"""

    if old_gradebook_start not in content_norm:
        raise Exception("Gradebook start target not found!")
    content_norm = content_norm.replace(old_gradebook_start, new_gradebook_start, 1)

    # Call checkClassRecordLock at end of renderLiveGradebookAndReports
    old_gradebook_end = """    gradebookCache = { allCloCols, itemGroups, saCodes, saWeights, saNames, saCloPairs, saCloPassCounts, cloFinalPassCounts, studentResults };
    const dashPanel = document.getElementById("tab-dashboard");
    if (dashPanel && dashPanel.classList.contains("active")) renderDashboard();
  }"""

    new_gradebook_end = """    gradebookCache = { allCloCols, itemGroups, saCodes, saWeights, saNames, saCloPairs, saCloPassCounts, cloFinalPassCounts, studentResults };
    const dashPanel = document.getElementById("tab-dashboard");
    if (dashPanel && dashPanel.classList.contains("active")) renderDashboard();
    checkClassRecordLock();
  }"""

    if old_gradebook_end not in content_norm:
        raise Exception("Gradebook end target not found!")
    content_norm = content_norm.replace(old_gradebook_end, new_gradebook_end, 1)

    # 6. renderClassRecordWorkflowBar()
    old_cr_bar_start = """  function renderClassRecordWorkflowBar() {
    const banner = document.getElementById("crWorkflowBanner");
    if (!banner) return;
    const wf = currentClassRecordWorkflow || {
      status: "draft",
      status_label: "Draft (Scores Editable)",
      is_locked: false,
      is_finalized: false,
      signatures: [],
      can_submit: true,
      can_sign: false,
      can_request_revision: false
    };

    const statusBadge = document.getElementById("crStatusBadge");
    const freezeBadge = document.getElementById("crGradeFreezeBadge");
    const statusDetail = document.getElementById("crStatusDetail");
    const actionButtons = document.getElementById("crActionButtons");
    const stepperContainer = document.getElementById("crStepperContainer");"""

    new_cr_bar_start = """  function renderClassRecordWorkflowBar() {
    const banner = document.getElementById("crWorkflowBanner");
    if (!banner) return;
    const wf = currentClassRecordWorkflow || {
      status: "draft",
      status_label: "Draft (Scores Editable)",
      is_locked: false,
      is_finalized: false,
      signatures: [],
      can_submit: true,
      can_sign: false,
      can_request_revision: false
    };

    const statusBadge = document.getElementById("crStatusBadge");
    const freezeBadge = document.getElementById("crGradeFreezeBadge");
    const statusDetail = document.getElementById("crStatusDetail");
    const actionButtons = document.getElementById("crActionButtons");
    const stepperContainer = document.getElementById("crStepperContainer");

    const isSyllabusApproved = currentWorkflow && (currentWorkflow.status === "approved");
    if (!isSyllabusApproved) {
      if (statusBadge) {
        statusBadge.textContent = "Awaiting Syllabus Approval";
        statusBadge.style.background = "#fff7ed";
        statusBadge.style.color = "#c2410c";
      }
      if (freezeBadge) {
        freezeBadge.style.display = "none";
      }
      if (statusDetail) {
        statusDetail.innerHTML = '<span style="color:#c2410c; font-weight:700;">🔒 Syllabus Approval Required:</span> The syllabus must be approved through the official review chain (Review Committee &rarr; Program Head &rarr; College QA Head &rarr; Dean) before class record grading and sign-off can begin.';
      }
      if (actionButtons) {
        actionButtons.innerHTML = '<span style="font-size:0.78rem; color:#9a3412; font-weight:600; padding:4px 8px; background:#fff7ed; border-radius:6px; border:1px solid #fed7aa;">🔒 Sign-off locked until syllabus approval</span>';
      }
      if (stepperContainer) {
        stepperContainer.innerHTML = '<div style="font-size:0.75rem; color:#64748b; text-align:center; padding:6px 0;">Class record review stepper will activate after syllabus is officially approved.</div>';
      }
      return;
    }"""

    if old_cr_bar_start not in content_norm:
        raise Exception("renderClassRecordWorkflowBar start target not found!")
    content_norm = content_norm.replace(old_cr_bar_start, new_cr_bar_start, 1)

    # 7. Add guards to interaction functions
    old_sync_func = """  function maybeAutoSyncSetupFromSyllabus() {
    const autoEl = document.getElementById("autoSyncSyllabusToSetup");
    if (!autoEl || autoEl.checked) {
      syncClassRecordSetupFromSyllabus(false);
    }
  }

  function syncClassRecordSetupFromSyllabus(switchToSetupTab) {
    if (!blueprint) return;"""

    new_sync_func = """  function maybeAutoSyncSetupFromSyllabus() {
    const isSyllabusApproved = currentWorkflow && (currentWorkflow.status === "approved");
    if (!isSyllabusApproved) return;
    const autoEl = document.getElementById("autoSyncSyllabusToSetup");
    if (!autoEl || autoEl.checked) {
      syncClassRecordSetupFromSyllabus(false);
    }
  }

  function syncClassRecordSetupFromSyllabus(switchToSetupTab) {
    if (!blueprint) return;
    const isSyllabusApproved = currentWorkflow && (currentWorkflow.status === "approved");
    if (!isSyllabusApproved) {
      if (switchToSetupTab) {
        alert("Class Record Setup & Grades are locked until the syllabus is approved by the Review Committee, Program Head, College QA Head, and Dean.");
        switchTab("tab-assessments", null);
      }
      return;
    }"""

    if old_sync_func not in content_norm:
        raise Exception("sync functions target not found!")
    content_norm = content_norm.replace(old_sync_func, new_sync_func, 1)

    # Add guards to toggleItemClo, setItemAllClos, setCategoryAllItemsClo, updateItemCloPoint, updateItemTotalPoints
    old_item_clo_funcs = """  function toggleItemClo(cIdx, iIdx, cloId) {
    const coOptions = (blueprint.course_outcomes || []).map(c => c.co_id);"""

    new_item_clo_funcs = """  function toggleItemClo(cIdx, iIdx, cloId) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") return;
    const coOptions = (blueprint.course_outcomes || []).map(c => c.co_id);"""

    if old_item_clo_funcs not in content_norm:
        raise Exception("toggleItemClo target not found!")
    content_norm = content_norm.replace(old_item_clo_funcs, new_item_clo_funcs, 1)

    old_set_all_clos = """  function setItemAllClos(cIdx, iIdx) {"""
    new_set_all_clos = """  function setItemAllClos(cIdx, iIdx) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") return;"""
    content_norm = content_norm.replace(old_set_all_clos, new_set_all_clos, 1)

    old_set_cat_clos = """  function setCategoryAllItemsClo(cIdx, cloMode) {"""
    new_set_cat_clos = """  function setCategoryAllItemsClo(cIdx, cloMode) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") return;"""
    content_norm = content_norm.replace(old_set_cat_clos, new_set_cat_clos, 1)

    old_update_point = """  function updateItemCloPoint(cIdx, iIdx, cloId, rawVal) {"""
    new_update_point = """  function updateItemCloPoint(cIdx, iIdx, cloId, rawVal) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") return;"""
    content_norm = content_norm.replace(old_update_point, new_update_point, 1)

    old_update_total = """  function updateItemTotalPoints(cIdx, iIdx, rawTotal) {"""
    new_update_total = """  function updateItemTotalPoints(cIdx, iIdx, rawTotal) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") return;"""
    content_norm = content_norm.replace(old_update_total, new_update_total, 1)

    # Add guards to addAssessmentCategory, removeAssessmentCategory, addAssessmentItem, removeAssessmentItem
    old_add_cat = """  function addAssessmentCategory(termName, aType) {"""
    new_add_cat = """  function addAssessmentCategory(termName, aType) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") {
      alert("Class Record Setup & Grades are locked until the syllabus is approved through the official review chain.");
      return;
    }"""
    content_norm = content_norm.replace(old_add_cat, new_add_cat, 1)

    old_rem_cat = """  function removeAssessmentCategory(cIdx) {"""
    new_rem_cat = """  function removeAssessmentCategory(cIdx) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") {
      alert("Class Record Setup & Grades are locked until the syllabus is approved through the official review chain.");
      return;
    }"""
    content_norm = content_norm.replace(old_rem_cat, new_rem_cat, 1)

    old_add_item = """  function addAssessmentItem(cIdx) {"""
    new_add_item = """  function addAssessmentItem(cIdx) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") {
      alert("Class Record Setup & Grades are locked until the syllabus is approved through the official review chain.");
      return;
    }"""
    content_norm = content_norm.replace(old_add_item, new_add_item, 1)

    old_rem_item = """  function removeAssessmentItem(cIdx, iIdx) {"""
    new_rem_item = """  function removeAssessmentItem(cIdx, iIdx) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") {
      alert("Class Record Setup & Grades are locked until the syllabus is approved through the official review chain.");
      return;
    }"""
    content_norm = content_norm.replace(old_rem_item, new_rem_item, 1)

    # Add guards to updateStudentCloScore, addStudentRow, removeStudentRow, uploadStudentRoster
    old_update_score = """  function updateStudentCloScore(sIdx, itemId, cloId, val) {"""
    new_update_score = """  function updateStudentCloScore(sIdx, itemId, cloId, val) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") return;"""
    content_norm = content_norm.replace(old_update_score, new_update_score, 1)

    old_add_st = """  function addStudentRow() {"""
    new_add_st = """  function addStudentRow() {
    if (!currentWorkflow || currentWorkflow.status !== "approved") {
      alert("Class Record is locked until the syllabus is approved through the official review chain.");
      return;
    }"""
    content_norm = content_norm.replace(old_add_st, new_add_st, 1)

    old_rem_st = """  function removeStudentRow(sIdx) {"""
    new_rem_st = """  function removeStudentRow(sIdx) {
    if (!currentWorkflow || currentWorkflow.status !== "approved") {
      alert("Class Record is locked until the syllabus is approved through the official review chain.");
      return;
    }"""
    content_norm = content_norm.replace(old_rem_st, new_rem_st, 1)

    old_upload_roster = """  async function uploadStudentRoster() {"""
    new_upload_roster = """  async function uploadStudentRoster() {
    if (!currentWorkflow || currentWorkflow.status !== "approved") {
      alert("Class Record is locked until the syllabus is approved through the official review chain.");
      return;
    }"""
    content_norm = content_norm.replace(old_upload_roster, new_upload_roster, 1)

    with open("templates/index.html", "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content_norm.replace("\n", "\r\n"))
    print("Successfully patched templates/index.html")

if __name__ == "__main__":
    patch_courses_store()
    patch_templates_index()
