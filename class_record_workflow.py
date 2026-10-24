"""
class_record_workflow.py
Sequential Sign-off & Grade Lock-in Workflow Engine for USeP OBE Class Records.

Signatory Sequences:
1. Ordinary Faculty Member:
   Faculty in Charge (Finalize & Submit)
   -> Program Head (Review & Endorse)
   -> College QA Head (Countersign)
   -> College Dean (Final Approval & Permanent Grade Lock)

2. Program Head:
   Faculty in Charge / Program Head (Finalize & Submit)
   -> Associate Dean (Review & Endorse instead of Program Head)
   -> College QA Head (Countersign)
   -> College Dean (Final Approval & Permanent Grade Lock)

Once finalized or in sign-off, grades and student scores are locked and cannot be edited.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import auth

EDITABLE_CR_STATUSES = {"draft", "returned"}
LOCKED_CR_STATUSES = {"for_program_head", "for_associate_dean", "for_qa_countersign", "for_dean_approval", "finalized"}

CR_STATUS_LABELS = {
    "draft": "Draft (Scores Editable)",
    "for_program_head": "Step 1: Awaiting Program Head Endorsement",
    "for_associate_dean": "Step 1: Awaiting Associate Dean Endorsement (Program Head Course)",
    "for_qa_countersign": "Step 2: Awaiting College QA Countersign",
    "for_dean_approval": "Step 3: Awaiting College Dean Final Approval",
    "finalized": "Official Final Grades Locked & Sealed 🔒",
    "returned": "Returned for Grade Revision ↩️",
}

class ClassRecordWorkflowError(Exception):
    pass

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def is_owner_program_head(owner_username: str) -> bool:
    """Check if the owner of the course holds the Program Head role."""
    users = auth._load_users()
    uname = auth.LEGACY_USERNAME_ALIASES.get(owner_username, owner_username)
    u = users.get(uname)
    if not u:
        return False
    w_roles = u.get("workflow_roles") or []
    return "program_head" in w_roles or u.get("role") == "program_head"

def default_class_record_workflow(owner: str = "") -> Dict[str, Any]:
    is_ph = is_owner_program_head(owner) if owner else False
    return {
        "status": "draft",
        "cycle": 1,
        "is_owner_program_head": is_ph,
        "submitted_at": None,
        "finalized_at": None,
        "submission_notes": "",
        "return_remarks": "",
        "signatures": [],
        "history": [],
    }

def get_class_record_workflow(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return default_class_record_workflow()
    cr_wf = doc.get("class_record_workflow")
    if not isinstance(cr_wf, dict) or not cr_wf.get("status"):
        owner = doc.get("owner", "")
        cr_wf = default_class_record_workflow(owner)
        doc["class_record_workflow"] = cr_wf
    # Ensure is_owner_program_head is synchronized
    owner = doc.get("owner", "")
    if owner:
        cr_wf["is_owner_program_head"] = is_owner_program_head(owner)
    return cr_wf

def status_label(status: str) -> str:
    return CR_STATUS_LABELS.get(status, status.replace("_", " ").title())

def is_class_record_locked(doc: Dict[str, Any]) -> bool:
    cr_wf = get_class_record_workflow(doc)
    return cr_wf.get("status") in LOCKED_CR_STATUSES

def is_class_record_finalized(doc: Dict[str, Any]) -> bool:
    cr_wf = get_class_record_workflow(doc)
    return cr_wf.get("status") == "finalized"

def current_cr_step(cr_wf: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = cr_wf.get("status", "draft")
    is_ph = bool(cr_wf.get("is_owner_program_head"))

    if status == "for_program_head":
        return {
            "key": "program_head",
            "label": "Program Head",
            "action_label": "Endorse Class Record",
            "step_num": 1,
            "total_steps": 3,
        }
    elif status == "for_associate_dean":
        return {
            "key": "associate_dean",
            "label": "Associate Dean",
            "action_label": "Endorse Class Record (for Program Head)",
            "step_num": 1,
            "total_steps": 3,
        }
    elif status == "for_qa_countersign":
        return {
            "key": "qa_head",
            "label": "College QA Head",
            "action_label": "Countersign Class Record",
            "step_num": 2,
            "total_steps": 3,
        }
    elif status == "for_dean_approval":
        return {
            "key": "dean",
            "label": "College Dean",
            "action_label": "Approve & Lock Final Grades",
            "step_num": 3,
            "total_steps": 3,
        }
    return None

def user_can_sign_class_record(user: Optional[Dict[str, Any]], doc: Dict[str, Any]) -> bool:
    """Determine if user is authorized to sign the current class record step."""
    if not user:
        return False
    # Staff accounts have oversight capability only
    if user.get("role") == "staff" or (user.get("is_staff") and not user.get("can_access_faculty_tools", True)):
        return False

    cr_wf = get_class_record_workflow(doc)
    step = current_cr_step(cr_wf)
    if not step:
        return False

    if user.get("role") == "admin":
        return True

    # Owner cannot endorse or sign their own institutional endorsement steps
    if doc.get("owner") == user.get("username"):
        return False

    w_roles = user.get("workflow_roles") or []
    step_key = step["key"]

    if step_key == "program_head":
        if "program_head" not in w_roles:
            return False
        # Scope program
        p_codes = user.get("program_codes") or []
        c_prog = (doc.get("program_code") or (doc.get("blueprint", {}).get("metadata", {}).get("program_code")) or "EE").upper()
        return ("*" in p_codes) or (c_prog in p_codes)

    elif step_key == "associate_dean":
        return "associate_dean" in w_roles or "dean" in w_roles

    elif step_key == "qa_head":
        return "qa_head" in w_roles

    elif step_key == "dean":
        return "dean" in w_roles

    return False

def submit_class_record(doc: Dict[str, Any], user: Dict[str, Any], notes: str = "", signature_data: str = "") -> Dict[str, Any]:
    """Faculty in charge finalizes and submits class record for institutional sign-off."""
    cr_wf = get_class_record_workflow(doc)
    status = cr_wf.get("status", "draft")

    if status not in EDITABLE_CR_STATUSES:
        raise ClassRecordWorkflowError("Class record is already submitted or finalized.")

    owner = doc.get("owner", "")
    username = user.get("username", "")
    is_admin = (user.get("role") == "admin")

    if owner and owner != username and not is_admin:
        raise ClassRecordWorkflowError("Only the faculty owner can finalize and submit this class record.")

    # Validation: Ensure students and assessments exist
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    students = bp.get("students") or []
    if not students:
        raise ClassRecordWorkflowError("Cannot submit an empty class record. Please input student scores first.")

    now_ts = _now()
    sig_data = signature_data or user.get("signature_data") or ""
    if not sig_data:
        raise ClassRecordWorkflowError("Please upload or draw your e-signature first to finalize this class record.")

    is_ph = is_owner_program_head(owner or username)
    cr_wf["is_owner_program_head"] = is_ph
    next_status = "for_associate_dean" if is_ph else "for_program_head"

    faculty_sig = {
        "step": "faculty_submission",
        "role_key": "faculty",
        "role": "Faculty in Charge",
        "username": username,
        "name": user.get("full_name") or username,
        "position_title": user.get("position_title") or "Faculty in Charge",
        "decision": "submit",
        "remarks": notes or "Finalized student scores and grades submitted for sign-off.",
        "signed_at": now_ts,
        "signature_data": sig_data,
    }

    cr_wf["status"] = next_status
    cr_wf["submitted_at"] = now_ts
    cr_wf["submission_notes"] = notes
    cr_wf["return_remarks"] = ""
    cr_wf["signatures"] = [faculty_sig]
    cr_wf["history"].append({
        "at": now_ts,
        "by": username,
        "name": user.get("full_name") or username,
        "action": f"Submitted class record (Next: {status_label(next_status)})",
        "notes": notes,
    })

    return cr_wf

def sign_class_record(doc: Dict[str, Any], user: Dict[str, Any], decision: str, remarks: str = "", signature_data: str = "") -> Dict[str, Any]:
    """Sign an institutional review step for a class record."""
    cr_wf = get_class_record_workflow(doc)
    step = current_cr_step(cr_wf)
    if not step:
        raise ClassRecordWorkflowError("This class record is not awaiting any signature.")

    if not user_can_sign_class_record(user, doc):
        raise ClassRecordWorkflowError(f"Only the authorized {step['label']} can act on this step.")

    decision_clean = decision.strip().lower()
    now_ts = _now()
    username = user.get("username", "")
    full_name = user.get("full_name") or username
    title = user.get("position_title") or step["label"]

    if decision_clean == "return":
        if not remarks.strip():
            raise ClassRecordWorkflowError("Please provide return remarks explaining what needs revision.")
        cr_wf["status"] = "returned"
        cr_wf["return_remarks"] = remarks.strip()
        cr_wf["history"].append({
            "at": now_ts,
            "by": username,
            "name": full_name,
            "action": f"Returned class record at step {step['label']}",
            "remarks": remarks.strip(),
        })
        return cr_wf

    # Approval / Endorsement
    sig_data = signature_data or user.get("signature_data") or ""
    if not sig_data:
        raise ClassRecordWorkflowError(f"Please provide your electronic signature to endorse as {step['label']}.")

    sig_entry = {
        "step": step["key"],
        "role_key": step["key"],
        "role": step["label"],
        "username": username,
        "name": full_name,
        "position_title": title,
        "decision": "approve",
        "remarks": remarks.strip(),
        "signed_at": now_ts,
        "signature_data": sig_data,
    }
    cr_wf["signatures"].append(sig_entry)

    # Advance workflow
    if step["key"] in {"program_head", "associate_dean"}:
        next_status = "for_qa_countersign"
    elif step["key"] == "qa_head":
        next_status = "for_dean_approval"
    elif step["key"] == "dean":
        next_status = "finalized"
        cr_wf["finalized_at"] = now_ts
    else:
        next_status = "draft"

    cr_wf["status"] = next_status
    cr_wf["history"].append({
        "at": now_ts,
        "by": username,
        "name": full_name,
        "action": f"Signed and endorsed as {step['label']} -> {status_label(next_status)}",
        "remarks": remarks.strip(),
    })

    return cr_wf

def request_class_record_revision(doc: Dict[str, Any], user: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    """Request unlocking a finalized class record for grade adjustments (requires owner or admin)."""
    cr_wf = get_class_record_workflow(doc)
    if cr_wf.get("status") != "finalized":
        raise ClassRecordWorkflowError("Only finalized class records can be requested for grade revision.")

    owner = doc.get("owner", "")
    username = user.get("username", "")
    is_admin = (user.get("role") == "admin")

    if owner and owner != username and not is_admin:
        raise ClassRecordWorkflowError("Only the faculty owner or administrator can request a grade revision.")

    if not reason.strip():
        raise ClassRecordWorkflowError("Please specify a valid official reason for the grade revision.")

    now_ts = _now()
    cr_wf["status"] = "draft"
    cr_wf["cycle"] = int(cr_wf.get("cycle", 1)) + 1
    cr_wf["signatures"] = []
    cr_wf["return_remarks"] = f"Grade revision unlocked (Cycle {cr_wf['cycle']}): {reason.strip()}"
    cr_wf["history"].append({
        "at": now_ts,
        "by": username,
        "name": user.get("full_name") or username,
        "action": f"Grade revision requested and unlocked (Cycle {cr_wf['cycle']})",
        "reason": reason.strip(),
    })
    return cr_wf

def public_cr_view(doc: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return clean public view of class record workflow state with action permissions."""
    cr_wf = get_class_record_workflow(doc)
    status = cr_wf.get("status", "draft")
    step = current_cr_step(cr_wf)
    owner = doc.get("owner", "")
    username = user.get("username") if user else ""
    is_owner = (owner == username)
    is_admin = bool(user and user.get("role") == "admin")

    can_submit = (is_owner or is_admin) and (status in EDITABLE_CR_STATUSES)
    can_sign = user_can_sign_class_record(user, doc) if user else False
    can_request_revision = (is_owner or is_admin) and (status == "finalized")

    return {
        "status": status,
        "status_label": status_label(status),
        "is_locked": status in LOCKED_CR_STATUSES,
        "is_finalized": status == "finalized",
        "cycle": cr_wf.get("cycle", 1),
        "is_owner_program_head": bool(cr_wf.get("is_owner_program_head")),
        "submitted_at": cr_wf.get("submitted_at"),
        "finalized_at": cr_wf.get("finalized_at"),
        "submission_notes": cr_wf.get("submission_notes", ""),
        "return_remarks": cr_wf.get("return_remarks", ""),
        "signatures": cr_wf.get("signatures", []),
        "history": cr_wf.get("history", []),
        "current_step": step,
        "current_step_label": step["label"] if step else ("Official Final Grades Locked" if status == "finalized" else "Draft"),
        "can_submit": can_submit,
        "can_sign": can_sign,
        "can_request_revision": can_request_revision,
    }

def extract_program_code(c: Dict[str, Any]) -> str:
    prog = c.get("program_code")
    if not prog and "doc_raw" in c and isinstance(c["doc_raw"], dict):
        meta = (c["doc_raw"].get("blueprint") or {}).get("metadata") or {}
        prog = meta.get("program_code")
    if not prog:
        cc = str(c.get("course_code", "")).strip()
        parts = cc.split()
        if parts and parts[0].isalpha():
            prog = parts[0].upper()
    return (prog or "EE").upper()

def compute_institutional_analytics(all_courses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute cross-college completion metrics, compliance percentages, and signatory queue bottlenecks."""
    total = len(all_courses)
    syl_approved = 0
    syl_ongoing = 0
    cr_finalized = 0
    cr_in_signoff = 0

    bottlenecks = {
        "committee_members": 0,
        "committee_chair": 0,
        "program_head": 0,
        "associate_dean": 0,
        "qa_head": 0,
        "dean": 0,
    }

    programs_map: Dict[str, Dict[str, Any]] = {}

    for c in all_courses:
        p_code = extract_program_code(c)
        if p_code not in programs_map:
            programs_map[p_code] = {
                "code": p_code,
                "courses_count": 0,
                "syllabi_approved": 0,
                "syllabi_pending": 0,
                "cr_finalized": 0,
                "cr_pending": 0,
                "compliance_pct": 0.0,
            }
        p_entry = programs_map[p_code]
        p_entry["courses_count"] += 1

        # Syllabus workflow
        wf = c.get("workflow") or {}
        s_st = wf.get("status", "draft")
        if s_st == "approved":
            syl_approved += 1
            p_entry["syllabi_approved"] += 1
        elif s_st in {"for_committee_review", "for_committee_chair", "for_program_head", "for_qa_countersign", "for_dean_approval"}:
            syl_ongoing += 1
            p_entry["syllabi_pending"] += 1
            if s_st == "for_committee_review":
                bottlenecks["committee_members"] += 1
            elif s_st == "for_committee_chair":
                bottlenecks["committee_chair"] += 1
            elif s_st == "for_program_head":
                bottlenecks["program_head"] += 1
            elif s_st == "for_qa_countersign":
                bottlenecks["qa_head"] += 1
            elif s_st == "for_dean_approval":
                bottlenecks["dean"] += 1

        # Class record workflow
        cr_wf = c.get("class_record_workflow") or {}
        c_st = cr_wf.get("status", "draft")
        if c_st == "finalized":
            cr_finalized += 1
            p_entry["cr_finalized"] += 1
        elif c_st in {"for_program_head", "for_associate_dean", "for_qa_countersign", "for_dean_approval"}:
            cr_in_signoff += 1
            p_entry["cr_pending"] += 1
            if c_st == "for_program_head":
                bottlenecks["program_head"] += 1
            elif c_st == "for_associate_dean":
                bottlenecks["associate_dean"] += 1
            elif c_st == "for_qa_countersign":
                bottlenecks["qa_head"] += 1
            elif c_st == "for_dean_approval":
                bottlenecks["dean"] += 1

    programs_list = []
    for p_code, p_entry in sorted(programs_map.items()):
        cnt = p_entry["courses_count"]
        comp = ((p_entry["syllabi_approved"] + p_entry["cr_finalized"]) / (cnt * 2.0)) * 100.0 if cnt > 0 else 0.0
        p_entry["compliance_pct"] = round(comp, 1)
        programs_list.append(p_entry)

    syl_pct = round((syl_approved / total * 100.0), 1) if total > 0 else 0.0
    cr_pct = round((cr_finalized / total * 100.0), 1) if total > 0 else 0.0

    return {
        "total_courses": total,
        "syllabus_total": total,
        "syllabus_approved": syl_approved,
        "syllabus_ongoing": syl_ongoing,
        "syllabus_compliance_pct": syl_pct,
        "class_record_total": total,
        "class_record_finalized": cr_finalized,
        "class_record_in_signoff": cr_in_signoff,
        "class_record_compliance_pct": cr_pct,
        "programs": programs_list,
        "bottlenecks": bottlenecks,
    }

