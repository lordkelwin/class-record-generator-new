"""
Syllabus review & approval workflow.

Flow (each step must be completed in order before the next can act):
  draft/returned --(faculty submits)--> committee review (checklist + e-signature)
  --> Program Head (e-signature) --> College QA Head countersign (e-signature)
  --> Dean approval (e-signature) --> APPROVED (syllabus locked; class record unlocked)

Any reviewer can instead RETURN the syllabus for revision with remarks, which
unlocks it for the faculty and clears the signatures of the current cycle
(the full history is kept).

The workflow state lives in the stored course document (doc["workflow"]), never in
the client-supplied blueprint, so it cannot be forged from the browser.
"""
import copy
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------
# Step configuration (order matters)
# --------------------------------------------------------------------------
WORKFLOW_STEPS: List[Dict[str, Any]] = [
    {
        "key": "committee_members",
        "role": "review_committee",
        "label": "Review Committee Members",
        "action_label": "Reviewed by Members",
        "status": "for_committee_review",
        "requires_checklist": True,
        "scope": "program",
    },
    {
        "key": "committee_chair",
        "role": "review_committee_chair",
        "label": "Review Committee Chair",
        "action_label": "Endorsed by Chair",
        "status": "for_committee_chair",
        "requires_checklist": True,
        "scope": "program",
    },
    {
        "key": "program_head",
        "role": "program_head",
        "label": "Program Head",
        "action_label": "Recommending Approval",
        "status": "for_program_head",
        "requires_checklist": False,
        "scope": "program",
    },
    {
        "key": "qa_head",
        "role": "qa_head",
        "label": "College QA Head",
        "action_label": "Countersigned by",
        "status": "for_qa_countersign",
        "requires_checklist": False,
        "scope": "college",
    },
    {
        "key": "student_ack",
        "role": "student",
        "label": "Student Acknowledgment",
        "action_label": "Acknowledged by Students (FM-USeP-MID-07)",
        "status": "for_student_acknowledgment",
        "requires_checklist": False,
        "scope": "class",
    },
    {
        "key": "dean",
        "role": "dean",
        "label": "Dean",
        "action_label": "Approved by",
        "status": "for_dean_approval",
        "requires_checklist": False,
        "scope": "college",
    },
]

WORKFLOW_ROLES = {s["role"]: s["label"] for s in WORKFLOW_STEPS}

STATUS_LABELS = {
    "draft": "Draft",
    "returned": "Returned for Revision",
    "for_committee_review": "For Committee Members Review",
    "for_committee_chair": "For Committee Chair Endorsement",
    "for_program_head": "For Program Head Approval",
    "for_qa_countersign": "For QA Head Countersign",
    "for_student_acknowledgment": "For Student Acknowledgment (FM-USeP-MID-07)",
    "for_dean_approval": "For Dean's Approval",
    "approved": "Approved & Locked",
    "revision_for_program_head": "Revision Request: Awaiting Program Head Endorsement",
    "revision_for_associate_dean": "Revision Request: Awaiting Associate Dean Endorsement (Program Head Course)",
    "revision_for_dean": "Revision Request: Awaiting Dean's Final Approval",
}

REVISION_STATUSES = {"revision_for_program_head", "revision_for_associate_dean", "revision_for_dean"}
EDITABLE_STATUSES = {"draft", "returned"}

# Metadata fields that belong to the individual class/section (not the syllabus content)
# and may still be edited after the syllabus is locked.
SECTION_LEVEL_META_FIELDS = {"section", "schedule", "room", "transmutation_base", "passing_percentage", "grading_mode"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

BOTTLENECK_SLA_DAYS = 3.0


def get_queue_age(doc: Dict[str, Any], now_dt: Optional[datetime] = None) -> Dict[str, Any]:
    """Computes days in queue for active review steps and detects 3-day SLA bottlenecks."""
    wf = get_workflow(doc)
    status = wf.get("status")
    if status in EDITABLE_STATUSES or status == "approved":
        return {
            "days_in_queue": 0.0,
            "is_overdue": False,
            "step_entered_at": None,
            "threshold_days": BOTTLENECK_SLA_DAYS,
            "last_reminder_sent_at": wf.get("last_reminder_sent_at"),
        }

    now = now_dt or datetime.now()
    entered_str = wf.get("step_entered_at")
    if not entered_str:
        if status in REVISION_STATUSES:
            rev_req = wf.get("revision_request") or {}
            entered_str = rev_req.get("requested_at")
            if not entered_str and wf.get("history"):
                for h in reversed(wf["history"]):
                    if h.get("action") in {"revision_requested", "revision_endorsed"}:
                        entered_str = h.get("at")
                        break
        else:
            sigs = wf.get("signatures") or []
        if sigs:
            entered_str = sigs[-1].get("signed_at")
        elif wf.get("submitted_at"):
            entered_str = wf.get("submitted_at")
        elif (wf.get("revision_request") or {}).get("requested_at"):
            entered_str = wf["revision_request"]["requested_at"]
        elif wf.get("history"):
            entered_str = wf["history"][-1].get("at")
        else:
            entered_str = doc.get("created_at")

    days = 0.0
    if entered_str:
        try:
            clean_str = str(entered_str).replace("Z", "").split("+")[0]
            entered_dt = datetime.fromisoformat(clean_str)
            seconds = (now - entered_dt).total_seconds()
            days = max(0.0, round(seconds / 86400.0, 1))
        except Exception:
            days = 0.0

    is_overdue = (days >= BOTTLENECK_SLA_DAYS)
    return {
        "days_in_queue": days,
        "is_overdue": is_overdue,
        "step_entered_at": entered_str,
        "threshold_days": BOTTLENECK_SLA_DAYS,
        "last_reminder_sent_at": wf.get("last_reminder_sent_at"),
    }


def get_reviewers_for_step(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Returns list of reviewer user dictionaries responsible for acting on the current step."""
    wf = get_workflow(doc)
    status = wf.get("status")
    step = current_step(wf)
    if not step or status in EDITABLE_STATUSES or status == "approved":
        return []

    import auth
    users = auth._load_users()
    owner = doc.get("owner")

    def _clean_user(uname: str, udict: Dict[str, Any]) -> Dict[str, Any]:
        fname = udict.get("full_name") or uname
        em = udict.get("email") or auth.derive_email(uname, fname)
        return {
            "username": uname,
            "full_name": fname,
            "email": em,
            "role": udict.get("position_title") or udict.get("role", "faculty"),
        }

    # Step 1: Committee Members Review
    if status == "for_committee_review":
        comm_list = wf.get("committee_members") or []
        non_chair = [m for m in comm_list if m.get("role") != "Review Committee Chair"]
        target_list = non_chair if non_chair else comm_list
        signed_users = {auth.LEGACY_USERNAME_ALIASES.get(s.get("username"), s.get("username"))
                        for s in wf.get("signatures", []) if s.get("step") == "committee_members"}
        reviewers = []
        for m in target_list:
            u_canon = auth.LEGACY_USERNAME_ALIASES.get(m.get("username"), m.get("username"))
            if u_canon not in signed_users and u_canon != owner:
                u_obj = users.get(u_canon) or {"username": u_canon, "full_name": m.get("name", u_canon)}
                reviewers.append(_clean_user(u_canon, u_obj))
        return reviewers

    # Step 2: Committee Chair Endorsement
    if status == "for_committee_chair":
        comm_list = wf.get("committee_members") or []
        chair = next((m for m in comm_list if m.get("role") == "Review Committee Chair"), None)
        chair_uname = (chair.get("username") if chair else None) or wf.get("assigned_committee") or "faculty_basan"
        u_canon = auth.LEGACY_USERNAME_ALIASES.get(chair_uname, chair_uname)
        u_obj = users.get(u_canon) or {"username": u_canon, "full_name": chair.get("name", u_canon) if chair else u_canon}
        return [_clean_user(u_canon, u_obj)]

    # Step 3 or revision: Program Head
    if status in ("for_program_head", "revision_for_program_head"):
        bp = doc.get("blueprint") or {}
        meta = bp.get("metadata") or {}
        prog = (meta.get("program_code") or doc.get("program") or "EE").strip().upper()
        reviewers = []
        for uname, u in users.items():
            if uname == owner:
                continue
            w_roles = u.get("workflow_roles") or []
            if "program_head" in w_roles:
                u_progs = [p.strip().upper() for p in (u.get("program_codes") or [])]
                if "*" in u_progs or prog in u_progs:
                    reviewers.append(_clean_user(uname, u))
        return reviewers

    # Revision: Associate Dean
    if status == "revision_for_associate_dean":
        reviewers = []
        for uname, u in users.items():
            if uname == owner:
                continue
            w_roles = u.get("workflow_roles") or []
            if "associate_dean" in w_roles:
                reviewers.append(_clean_user(uname, u))
        return reviewers

    # Step 5: Student Acknowledgment
    if status == "for_student_acknowledgment":
        return [_clean_user(owner, users.get(owner) or {"username": owner})]

    # Step 4: QA Head
    if status == "for_qa_countersign":
        reviewers = []
        for uname, u in users.items():
            if uname == owner:
                continue
            w_roles = u.get("workflow_roles") or []
            if "qa_head" in w_roles:
                reviewers.append(_clean_user(uname, u))
        return reviewers

    # Step 5 or revision: Dean
    if status in ("for_dean_approval", "revision_for_dean"):
        reviewers = []
        for uname, u in users.items():
            if uname == owner:
                continue
            w_roles = u.get("workflow_roles") or []
            if "dean" in w_roles:
                reviewers.append(_clean_user(uname, u))
        return reviewers

    return []



def is_owner_program_head(owner_username: str) -> bool:
    """Check if the owner of the course holds the Program Head role."""
    import auth
    users = auth._load_users()
    uname = auth.LEGACY_USERNAME_ALIASES.get(owner_username, owner_username)
    u = users.get(uname)
    if not u:
        return False
    w_roles = u.get("workflow_roles") or []
    return "program_head" in w_roles or u.get("role") == "program_head"


def default_workflow() -> Dict[str, Any]:
    return {
        "status": "draft",
        "cycle": 1,
        "content_hash": None,
        "submitted_at": None,
        "submitted_by": None,
        "submitted_by_name": None,
        "assigned_committee": None,
        "assigned_committee_name": None,
        "submission_notes": None,
        "approved_at": None,
        "signatures": [],  # current-cycle signatures [{step, role, username, full_name, title, decision, remarks, signed_at, signature_data, content_hash}]
        "checklist": {"responses": {}, "comments": {}, "overall_recommendation": "", "general_remarks": "",
                      "updated_by": None, "updated_at": None},
        "history": [],  # [{at, by, action, step, remarks, cycle}]
        "revision_request": None,
    }


def get_workflow(doc: Dict[str, Any]) -> Dict[str, Any]:
    wf = doc.get("workflow")
    if not isinstance(wf, dict):
        wf = default_workflow()
        doc["workflow"] = wf
    base = default_workflow()
    for k, v in base.items():
        wf.setdefault(k, copy.deepcopy(v))
    return wf


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def current_step(wf: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = wf.get("status")
    if status == "revision_for_program_head":
        return {
            "key": "revision_program_head",
            "role": "program_head",
            "label": "Program Head (Revision Endorsement)",
            "action_label": "Endorsed by Program Head",
            "status": "revision_for_program_head",
            "requires_checklist": False,
            "scope": "program",
        }
    if status == "revision_for_associate_dean":
        return {
            "key": "revision_associate_dean",
            "role": "associate_dean",
            "label": "Associate Dean (Revision Endorsement - Program Head Course)",
            "action_label": "Endorsed by Associate Dean",
            "status": "revision_for_associate_dean",
            "requires_checklist": False,
            "scope": "college",
        }
    if status == "revision_for_dean":
        return {
            "key": "revision_dean",
            "role": "dean",
            "label": "Dean (Final Revision Approval)",
            "action_label": "Approved by Dean",
            "status": "revision_for_dean",
            "requires_checklist": False,
            "scope": "college",
        }
    for s in WORKFLOW_STEPS:
        if s["status"] == status:
            return s
    return None


def is_syllabus_locked(doc: Dict[str, Any]) -> bool:
    return get_workflow(doc)["status"] not in EDITABLE_STATUSES


def is_approved(doc: Dict[str, Any]) -> bool:
    wf = get_workflow(doc)
    return wf.get("status") == "approved" or (wf.get("status") in REVISION_STATUSES and wf.get("approved_at") is not None)


# --------------------------------------------------------------------------
# Syllabus snapshot / integrity hash
# --------------------------------------------------------------------------
def syllabus_portion(bp: Dict[str, Any]) -> Dict[str, Any]:
    """The part of the blueprint that constitutes the syllabus (what gets reviewed & locked)."""
    meta = {k: v for k, v in (bp.get("metadata") or {}).items() if k not in SECTION_LEVEL_META_FIELDS}
    return {
        "metadata": meta,
        "course_outcomes": bp.get("course_outcomes") or [],
        "rubrics": bp.get("rubrics") or [],
        "terms": bp.get("terms") or [],
    }


def compute_hash(bp: Dict[str, Any]) -> str:
    raw = json.dumps(syllabus_portion(bp), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def enforce_locks(stored_doc: Dict[str, Any], incoming_bp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge an incoming (client) blueprint with the stored one according to the workflow:
      - When the syllabus is locked (submitted/approved), syllabus content is kept from the stored copy.
      - Until the syllabus is approved, the class record roster/scores cannot be changed.
    Returns the blueprint dict that should be saved.
    """
    stored_bp = stored_doc.get("blueprint") or {}
    if not stored_bp:
        return incoming_bp
    merged = copy.deepcopy(incoming_bp)

    if is_syllabus_locked(stored_doc):
        locked = syllabus_portion(stored_bp)
        new_meta = copy.deepcopy(locked["metadata"])
        for k in SECTION_LEVEL_META_FIELDS:
            if k in (incoming_bp.get("metadata") or {}):
                new_meta[k] = incoming_bp["metadata"][k]
            elif k in (stored_bp.get("metadata") or {}):
                new_meta[k] = stored_bp["metadata"][k]
        merged["metadata"] = new_meta
        merged["course_outcomes"] = copy.deepcopy(locked["course_outcomes"])
        merged["rubrics"] = copy.deepcopy(locked["rubrics"])
        merged["terms"] = copy.deepcopy(locked["terms"])

    if not is_approved(stored_doc):
        merged["categories"] = copy.deepcopy(stored_bp.get("categories") or [])
        merged["students"] = copy.deepcopy(stored_bp.get("students") or [])
        if "cqi_plan" in stored_bp:
            merged["cqi_plan"] = copy.deepcopy(stored_bp["cqi_plan"])
    return merged


# --------------------------------------------------------------------------
# Permission helpers
# --------------------------------------------------------------------------
def user_can_act(user: Dict[str, Any], doc: Dict[str, Any], step: Optional[Dict[str, Any]] = None) -> bool:
    """Can this user act on the current step of this course's workflow?"""
    wf = get_workflow(doc)
    step = step or current_step(wf)
    if not step or not user:
        return False
    if user.get("role") == "admin":
        return True
    if doc.get("owner") == user.get("username") and step.get("key") != "student_ack":
        return False  # nobody reviews/approves their own syllabus (except forwarding student ack to dean)
    if user.get("role") == "staff" or (user.get("is_staff") and not user.get("can_access_faculty_tools", True)):
        return False  # staff has oversight only and cannot sign review stages

    status = wf.get("status")
    user_roles = set(user.get("workflow_roles") or [])

    # Revision Request Steps
    if status == "revision_for_program_head":
        if "program_head" not in user_roles and user.get("role") != "admin":
            return False
        return in_scope(user, doc, {"scope": "program"})

    if status == "revision_for_associate_dean":
        return "associate_dean" in user_roles or user.get("role") == "admin"

    if status == "revision_for_dean":
        return "dean" in user_roles or user.get("role") == "admin"

    import auth
    user_canonical = auth.LEGACY_USERNAME_ALIASES.get(user["username"], user["username"])
    comm_list = wf.get("committee_members") or []

    # Step 1: Committee Members Review (Non-chair members must approve first)
    if step["key"] == "committee_members":
        non_chair = [m for m in comm_list if m.get("role") != "Review Committee Chair"]
        if not non_chair:
            # If no non-chair members configured, allow committee members
            comm_canonicals = [auth.LEGACY_USERNAME_ALIASES.get(m.get("username"), m.get("username")) for m in comm_list]
            return user_canonical in comm_canonicals
        non_chair_canonicals = [auth.LEGACY_USERNAME_ALIASES.get(m.get("username"), m.get("username")) for m in non_chair]
        signed_canonicals = {auth.LEGACY_USERNAME_ALIASES.get(s.get("username"), s.get("username")) for s in wf.get("signatures", []) if s.get("step") == "committee_members"}
        # Must be an assigned non-chair member and not yet signed in this cycle
        return user_canonical in non_chair_canonicals and user_canonical not in signed_canonicals

    # Step 2: Committee Chair Endorsement (After members have approved)
    if step["key"] == "committee_chair":
        chair = next((m for m in comm_list if m.get("role") == "Review Committee Chair"), None)
        chair_canonical = auth.LEGACY_USERNAME_ALIASES.get(chair.get("username"), chair.get("username")) if chair else None
        signed_chair = {auth.LEGACY_USERNAME_ALIASES.get(s.get("username"), s.get("username")) for s in wf.get("signatures", []) if s.get("step") == "committee_chair"}
        if chair_canonical:
            return user_canonical == chair_canonical and user_canonical not in signed_chair
        assigned_comm = auth.LEGACY_USERNAME_ALIASES.get(wf.get("assigned_committee"), wf.get("assigned_committee"))
        return user_canonical == assigned_comm and user_canonical not in signed_chair

    user_roles = set(user.get("workflow_roles") or [])
    if step.get("key") == "student_ack":
        if user.get("username") == doc.get("owner"):
            return True
        if user.get("role") in {"admin", "dean", "associate_dean", "program_head", "qa_head"}:
            return True
        return bool(user_roles.intersection({"dean", "associate_dean", "program_head", "qa_head"}))

    step_role = step["role"]
    if step_role == "dean":
        if not ("dean" in user_roles or "associate_dean" in user_roles):
            return False
    elif step_role not in user_roles:
        return False
    return in_scope(user, doc, step)


def in_scope(user: Dict[str, Any], doc: Dict[str, Any], step: Dict[str, Any]) -> bool:
    if step.get("scope") == "college":
        user_college = (user.get("college") or "").strip().lower()
        doc_college = (((doc.get("blueprint") or {}).get("metadata") or {}).get("college") or "").strip().lower()
        return not user_college or not doc_college or user_college == doc_college
    progs = [p.strip().upper() for p in (user.get("program_codes") or []) if p.strip()]
    if not progs or "*" in progs:
        return True
    doc_prog = (((doc.get("blueprint") or {}).get("metadata") or {}).get("program_code") or "").strip().upper()
    return doc_prog in progs


# --------------------------------------------------------------------------
# Transitions
# --------------------------------------------------------------------------
class WorkflowError(Exception):
    pass


def _log(wf, by, action, remarks="", step=None):
    wf["history"].append({"at": _now(), "by": by, "action": action, "step": step, "remarks": remarks, "cycle": wf.get("cycle", 1)})


def submit(doc: Dict[str, Any], user: Dict[str, Any],
           assigned_committee: Optional[str] = None,
           assigned_committee_name: Optional[str] = None,
           committee_members: Optional[List[Dict[str, Any]]] = None,
           submission_notes: Optional[str] = None) -> Dict[str, Any]:
    wf = get_workflow(doc)
    import courses_store
    authors = courses_store.get_doc_authors(doc)
    author_unames = [(a.get("username") or "").strip().lower() for a in authors]
    u_lower = (user.get("username") or "").strip().lower()
    is_admin = (user.get("role") == "admin")
    owner_lower = (doc.get("owner") or "").strip().lower()

    if u_lower != owner_lower and u_lower not in author_unames and not is_admin:
        raise WorkflowError("Only an author/writer of this syllabus can submit it for review.")

    if wf["status"] not in EDITABLE_STATUSES and not wf.get("is_awaiting_coauthors"):
        raise WorkflowError(f"This syllabus is already {status_label(wf['status'])}.")

    bp = doc.get("blueprint") or {}
    problems = validate_for_submission(bp)
    if problems:
        raise WorkflowError("Please complete the syllabus before submitting: " + "; ".join(problems))

    # Committee must have at least three (3) members
    if committee_members is None:
        committee_members = wf.get("committee_members") or [
            {"username": "faculty_basan", "name": "Nikka Samantha A. Basan", "role": "Review Committee Chair"},
            {"username": "faculty_arenga", "name": "Delan Zoe H. Arenga", "role": "Review Committee Member"},
            {"username": "faculty_ravida", "name": "Kim P. Ravida", "role": "Review Committee Member"},
        ]
    if len(committee_members) < 3:
        raise WorkflowError(f"The Syllabus Review Committee must have at least three (3) members (currently has {len(committee_members)}).")

    # Record this author's individual submission
    if "author_submissions" not in wf or not isinstance(wf["author_submissions"], dict):
        wf["author_submissions"] = {}

    now_ts = _now()
    user_name = user.get("full_name") or user.get("username")
    wf["author_submissions"][user["username"]] = {
        "submitted_at": now_ts,
        "name": user_name,
        "notes": (submission_notes or "").strip()
    }

    # Preserve committee members & notes in workflow
    wf["committee_members"] = committee_members
    wf["checklist"]["committee_members"] = committee_members
    chair_member = next((m for m in committee_members if m.get("role") == "Review Committee Chair"), committee_members[0])
    wf["assigned_committee"] = chair_member.get("username") or assigned_committee or "faculty_basan"
    wf["assigned_committee_name"] = ", ".join(m.get("name") for m in committee_members)
    if submission_notes:
        wf["submission_notes"] = (submission_notes or "").strip()

    # Check if all authors have submitted individually
    submitted_unames = set((k or "").strip().lower() for k in wf["author_submissions"].keys())
    pending_authors = [a for a in authors if (a.get("username") or "").strip().lower() not in submitted_unames]

    if pending_authors:
        # Still awaiting confirmation from other co-authors!
        wf["is_awaiting_coauthors"] = True
        wf["status"] = "draft"
        _log(wf, user["username"], "coauthor_submission_confirmed",
             remarks=f"Submission confirmed by {user_name} ({len(submitted_unames)}/{len(authors)} authors confirmed). Awaiting: {', '.join(a['name'] for a in pending_authors)}.",
             step="faculty")
        return wf
    else:
        # All involved authors have submitted individually!
        wf["is_awaiting_coauthors"] = False
        wf["status"] = WORKFLOW_STEPS[0]["status"]
        wf["content_hash"] = compute_hash(bp)
        wf["submitted_at"] = now_ts
        wf["step_entered_at"] = now_ts
        wf["submitted_by"] = ", ".join(a.get("username") or a.get("name") for a in authors)
        wf["submitted_by_name"] = ", ".join(a.get("name") for a in authors)
        wf["signatures"] = []
        wf["approved_at"] = None
        _log(wf, user["username"], "submitted",
             remarks=f"All {len(authors)} faculty author(s) confirmed submission: {wf['submitted_by_name']}.",
             step="faculty")
        return wf


def withdraw(doc: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    wf = get_workflow(doc)
    import courses_store
    authors = courses_store.get_doc_authors(doc)
    author_unames = [(a.get("username") or "").strip().lower() for a in authors]
    u_lower = (user.get("username") or "").strip().lower()
    is_admin = (user.get("role") == "admin")
    owner_lower = (doc.get("owner") or "").strip().lower()

    if u_lower != owner_lower and u_lower not in author_unames and not is_admin:
        raise WorkflowError("Only an author/writer of this syllabus can withdraw its submission.")

    if wf.get("is_awaiting_coauthors"):
        wf["is_awaiting_coauthors"] = False
        wf["author_submissions"] = {}
        wf["status"] = "draft"
        _log(wf, user["username"], "withdrawn", remarks="Submission withdrawn during co-author confirmation.", step="faculty")
        return wf

    if wf["status"] != WORKFLOW_STEPS[0]["status"] or wf["signatures"]:
        raise WorkflowError("A submission can only be withdrawn before the review committee signs it.")
    wf["status"] = "draft"
    wf["is_awaiting_coauthors"] = False
    wf["author_submissions"] = {}
    _log(wf, user["username"], "withdrawn", step="faculty")
    return wf


def save_checklist(doc: Dict[str, Any], user: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    wf = get_workflow(doc)
    step = current_step(wf)
    if not step or not step.get("requires_checklist"):
        raise WorkflowError("The review checklist can only be filled while the syllabus is with the Review Committee.")
    import auth
    user_canonical = auth.LEGACY_USERNAME_ALIASES.get(user["username"], user["username"])
    comm_list = wf.get("committee_members") or []
    comm_canonicals = [auth.LEGACY_USERNAME_ALIASES.get(m.get("username"), m.get("username")) for m in comm_list]
    is_comm = (user_canonical in comm_canonicals) or ("review_committee" in (user.get("workflow_roles") or [])) or (user.get("role") == "admin")
    if doc.get("owner") == user.get("username") and user.get("role") != "admin":
        raise WorkflowError("Faculty owners cannot evaluate or fill out the checklist for their own course syllabus.")
    if not is_comm:
        raise WorkflowError("Only members of the Syllabus Review Committee can fill out the review checklist.")
    cl = wf["checklist"]
    cl["responses"] = {str(k): str(v) for k, v in (data.get("responses") or {}).items()}
    cl["comments"] = {str(k): str(v) for k, v in (data.get("comments") or {}).items()}
    cl["overall_recommendation"] = str(data.get("overall_recommendation") or "")
    cl["general_remarks"] = str(data.get("general_remarks") or "")
    cl["updated_by"] = user["username"]
    cl["updated_at"] = _now()
    return wf



def get_student_acknowledgment_stats(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes FM-USeP-MID-07 student acknowledgment metrics and 80% threshold status.
    Under university policy, at least 80% of enrolled students must sign the
    acknowledgment form before the syllabus can be endorsed to the Dean or approved.
    """
    import math
    bp = doc.get("blueprint") or {}
    students = bp.get("students") or []
    acks = doc.get("student_acknowledgments") or (doc.get("workflow") or {}).get("student_acknowledgments") or []
    
    total = len(students)
    if total == 0:
        total = len(acks)
    
    total_acks = len(acks)
    pct = round((total_acks / total * 100.0), 1) if total > 0 else 0.0
    min_required = max(1, math.ceil(total * 0.80)) if total > 0 else 0
    meets_threshold = (total_acks >= min_required) if total > 0 else False
    
    return {
        "total_students": total,
        "total_acknowledged": total_acks,
        "percentage": pct,
        "min_required": min_required,
        "meets_threshold": meets_threshold,
    }

def sign(doc: Dict[str, Any], user: Dict[str, Any], decision: str, remarks: str,
         required_item_ids: Optional[List[str]] = None,
         overall_recommendation: Optional[str] = None) -> Dict[str, Any]:
    """decision: 'approve' (sign & forward) or 'return' (send back for revision)."""
    wf = get_workflow(doc)
    step = current_step(wf)
    if not step:
        raise WorkflowError("This syllabus is not awaiting any signature.")
    if wf.get("status") in REVISION_STATUSES:
        return handle_revision_action(doc, user, action=decision, remarks=remarks)
    if not user_can_act(user, doc, step):
        raise WorkflowError(f"Only the {step['label']} assigned to this program/college can act on this step.")
    if decision == "approve" and not user.get("has_signature"):
        raise WorkflowError("Please upload or draw your e-signature first (My E-Signature).")

    bp = doc.get("blueprint") or {}
    if compute_hash(bp) != wf.get("content_hash"):
        raise WorkflowError("The syllabus content changed after submission. It must be resubmitted.")

    if decision == "return":
        if not (remarks or "").strip():
            raise WorkflowError("Please write remarks explaining what needs to be revised.")
        wf["status"] = "returned"
        wf["cycle"] = int(wf.get("cycle", 1)) + 1
        wf["signatures"] = []
        wf["author_submissions"] = {}
        wf["is_awaiting_coauthors"] = False
        _log(wf, user["username"], "returned", remarks=remarks, step=step["key"])
        return wf

    if decision != "approve":
        raise WorkflowError("Unknown decision.")

    # 80% Student Acknowledgment Threshold Enforcement
    if step["key"] == "student_ack" and decision == "approve":
        stats = get_student_acknowledgment_stats(doc)
        if not stats["meets_threshold"]:
            raise WorkflowError(
                f"Cannot endorse syllabus to Dean: Student acknowledgment has not reached the required 80% threshold "
                f"({stats['total_acknowledged']}/{stats['total_students']} signed, {stats['percentage']}%. "
                f"Minimum required: {stats['min_required']} students)."
            )

    if step["key"] == "dean" and decision == "approve":
        stats = get_student_acknowledgment_stats(doc)
        if not stats["meets_threshold"]:
            raise WorkflowError(
                f"Cannot sign/approve syllabus: Student acknowledgment has not reached the required 80% threshold "
                f"({stats['total_acknowledged']}/{stats['total_students']} signed, {stats['percentage']}%. "
                f"Minimum required: {stats['min_required']} students)."
            )


    if step.get("requires_checklist"):
        cl = wf.get("checklist")
        if not cl:
            cl = {"responses": {}, "comments": {}, "overall_recommendation": "", "general_remarks": "", "updated_by": None, "updated_at": None}
            wf["checklist"] = cl

        missing = [i for i in (required_item_ids or []) if not cl.get("responses", {}).get(i)]
        if missing:
            raise WorkflowError(f"Please answer all checklist items before signing ({len(missing)} unanswered).")

        if overall_recommendation and overall_recommendation.strip():
            cl["overall_recommendation"] = overall_recommendation.strip()
        elif not cl.get("overall_recommendation"):
            cl["overall_recommendation"] = "Approved" if decision == "approve" else "Revise and Resubmit"

    import auth
    user_canonical = auth.LEGACY_USERNAME_ALIASES.get(user["username"], user["username"])

    # Handle Step 1: committee_members review
    if step["key"] == "committee_members":
        wf["signatures"].append({
            "step": "committee_members",
            "role": "review_committee",
            "label": "Review Committee Member",
            "action_label": "Reviewed by",
            "username": user_canonical,
            "full_name": user.get("full_name") or user["username"],
            "title": user.get("position_title") or "Review Committee Member",
            "decision": "approved",
            "remarks": remarks or "",
            "signed_at": _now(),
            "signature_data": user.get("signature_data") or "",
            "content_hash": wf["content_hash"],
        })
        _log(wf, user["username"], "signed", remarks=remarks, step="committee_members")

        comm_list = wf.get("committee_members") or []
        non_chair = [m for m in comm_list if m.get("role") != "Review Committee Chair"]
        signed_canonicals = {auth.LEGACY_USERNAME_ALIASES.get(s.get("username"), s.get("username")) for s in wf.get("signatures", []) if s.get("step") == "committee_members"}
        all_non_chair_signed = all(auth.LEGACY_USERNAME_ALIASES.get(m.get("username"), m.get("username")) in signed_canonicals for m in non_chair)

        if all_non_chair_signed or not non_chair:
            wf["status"] = "for_committee_chair"
            wf["step_entered_at"] = _now()
        else:
            wf["status"] = "for_committee_review"
        return wf

    # Handle Step 2: committee_chair endorsement
    if step["key"] == "committee_chair":
        wf["signatures"].append({
            "step": "committee_chair",
            "role": "review_committee_chair",
            "label": "Review Committee Chair",
            "action_label": "Endorsed by Chair",
            "username": user_canonical,
            "full_name": user.get("full_name") or user["username"],
            "title": user.get("position_title") or "Review Committee Chair",
            "decision": "approved",
            "remarks": remarks or "",
            "signed_at": _now(),
            "signature_data": user.get("signature_data") or "",
            "content_hash": wf["content_hash"],
        })
        _log(wf, user["username"], "signed", remarks=remarks, step="committee_chair")
        wf["status"] = "for_program_head"
        wf["step_entered_at"] = _now()
        return wf

    # Steps 3-5: Program Head, QA Head, Dean
    wf["signatures"].append({
        "step": step["key"],
        "role": step["role"],
        "label": step["label"],
        "action_label": step["action_label"],
        "username": user_canonical,
        "full_name": user.get("full_name") or user["username"],
        "title": user.get("position_title") or step["label"],
        "decision": "approved",
        "remarks": remarks or "",
        "signed_at": _now(),
        "signature_data": user.get("signature_data") or "",
        "content_hash": wf["content_hash"],
    })
    _log(wf, user["username"], "signed", remarks=remarks, step=step["key"])

    idx = WORKFLOW_STEPS.index(step)
    if idx + 1 < len(WORKFLOW_STEPS):
        wf["status"] = WORKFLOW_STEPS[idx + 1]["status"]
        wf["step_entered_at"] = _now()
    else:
        wf["status"] = "approved"
        wf["approved_at"] = _now()
        wf["step_entered_at"] = None
        _log(wf, user["username"], "approved", step=step["key"])
    return wf


def validate_for_submission(bp: Dict[str, Any]) -> List[str]:
    problems = []
    meta = bp.get("metadata") or {}
    if not (meta.get("course_code") or "").strip():
        problems.append("course code is missing")
    if not (meta.get("course_description") or "").strip():
        problems.append("course description is missing")
    if not bp.get("course_outcomes"):
        problems.append("at least one Course Learning Outcome (CLO) is required")
    if not (meta.get("syllabus_assessment_activities") or []):
        problems.append("Part VI assessment activities are missing")
    return problems


def public_view(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Workflow info safe to send to the browser."""
    wf = get_workflow(doc)
    step = current_step(wf)
    q_age = get_queue_age(doc)
    import courses_store
    authors = courses_store.get_doc_authors(doc)
    author_submissions = wf.get("author_submissions") or {}
    if wf.get("status") == "returned":
        author_submissions = {}
    submitted_unames = set((k or "").strip().lower() for k in author_submissions.keys())
    pending_authors = [a for a in authors if (a.get("username") or "").strip().lower() not in submitted_unames]
    submitted_authors = [a for a in authors if (a.get("username") or "").strip().lower() in submitted_unames]

    # Dynamic status label if awaiting co-author submission
    status_lbl = status_label(wf["status"])
    if wf.get("is_awaiting_coauthors") and wf["status"] == "draft":
        status_lbl = f"Draft (Awaiting Co-Authors: {len(submitted_authors)}/{len(authors)} Submitted)"

    return {
        "authors": authors,
        "author_submissions": author_submissions,
        "is_awaiting_coauthors": wf.get("is_awaiting_coauthors", False),
        "pending_authors": pending_authors,
        "submitted_authors": submitted_authors,
        "all_authors_submitted": len(pending_authors) == 0,
        "is_multi_authored": len(authors) > 1,
        "days_in_queue": q_age["days_in_queue"],
        "is_bottleneck": q_age["is_overdue"],
        "step_entered_at": q_age["step_entered_at"],
        "threshold_days": q_age["threshold_days"],
        "last_reminder_sent_at": q_age.get("last_reminder_sent_at"),
        "status": wf["status"],
        "status_label": status_lbl,
        "locked": wf["status"] not in EDITABLE_STATUSES,
        "approved": wf["status"] == "approved",
        "cycle": wf.get("cycle", 1),
        "current_step": step["key"] if step else None,
        "current_step_label": step["label"] if step else None,
        "submitted_at": wf.get("submitted_at"),
        "submitted_by": wf.get("submitted_by"),
        "submitted_by_name": wf.get("submitted_by_name"),
        "assigned_committee": wf.get("assigned_committee"),
        "assigned_committee_name": wf.get("assigned_committee_name"),
        "submission_notes": wf.get("submission_notes"),
        "approved_at": wf.get("approved_at"),
        "content_hash": wf.get("content_hash"),
        "signatures": wf.get("signatures", []),
        "checklist": wf.get("checklist"),
        "committee_members": wf.get("committee_members") or [],
        "history": wf.get("history", [])[-30:],
        "revision_reason": wf.get("revision_reason", ""),
        "student_ack_stats": get_student_acknowledgment_stats(doc),
        "revision_request": wf.get("revision_request"),
        "is_revision_pending": wf.get("status") in REVISION_STATUSES,
        "steps": [{"key": s["key"], "label": s["label"], "action_label": s["action_label"], "role": s["role"]} for s in WORKFLOW_STEPS],
    }


def request_revision(doc: Dict[str, Any], user: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    wf = get_workflow(doc)
    is_owner = (doc.get("owner") == user.get("username"))
    is_admin = (user.get("role") == "admin")
    if not (is_owner or is_admin):
        raise WorkflowError("Only the faculty who owns this syllabus can request a revision.")
    if wf.get("status") != "approved":
        raise WorkflowError("A revision request can only be submitted for an approved syllabus.")
    if not (reason or "").strip():
        raise WorkflowError("Please state the specific official reason for requesting syllabus revision.")

    owner = doc.get("owner", user["username"])
    is_ph = is_owner_program_head(owner)

    now_ts = _now()
    user_name = user.get("full_name") or user.get("username")
    target_status = "revision_for_associate_dean" if is_ph else "revision_for_program_head"

    wf["status"] = target_status
    wf["step_entered_at"] = now_ts
    wf["revision_reason"] = (reason or "").strip()
    wf["revision_request"] = {
        "requested_by": user["username"],
        "requested_by_name": user_name,
        "requested_at": now_ts,
        "reason": (reason or "").strip(),
        "owner_is_program_head": is_ph,
        "current_reviewer": "associate_dean" if is_ph else "program_head",
        "endorsements": [],
        "status": "pending",
    }
    _log(wf, user["username"], "revision_requested", remarks=reason.strip(), step="faculty")
    return wf


def handle_revision_action(doc: Dict[str, Any], user: Dict[str, Any], action: str, remarks: str = "") -> Dict[str, Any]:
    """
    Handle endorsement, approval, or rejection of a syllabus revision request.
    action: 'endorse' / 'approve' or 'reject'
    """
    wf = get_workflow(doc)
    status = wf.get("status")
    if status not in REVISION_STATUSES:
        raise WorkflowError("This course does not have an active revision request pending action.")

    if not user_can_act(user, doc):
        step = current_step(wf)
        label = step["label"] if step else "authorized reviewer"
        raise WorkflowError(f"Only the {label} can act on this revision request.")

    action_clean = str(action or "").lower().strip()
    is_approve_or_endorse = action_clean in {"approve", "endorse", "yes", "accept"}
    is_reject = action_clean in {"reject", "return", "deny", "no"}
    if not (is_approve_or_endorse or is_reject):
        raise WorkflowError("Invalid action. Must be 'endorse'/'approve' or 'reject'.")

    rev_req = wf.get("revision_request") or {}
    now_ts = _now()
    user_name = user.get("full_name") or user.get("username")

    if is_reject:
        if not (remarks or "").strip():
            raise WorkflowError("Please provide remarks explaining why the revision request was rejected.")
        wf["status"] = "approved"
        rev_req["status"] = "rejected"
        rev_req["rejected_by"] = user["username"]
        rev_req["rejected_by_name"] = user_name
        rev_req["rejected_at"] = now_ts
        rev_req["rejection_remarks"] = remarks.strip()
        wf["revision_request"] = rev_req
        _log(wf, user["username"], "revision_rejected", remarks=remarks.strip(), step=status)
        return wf

    # Endorse / Approve
    if status in {"revision_for_program_head", "revision_for_associate_dean"}:
        endorsement_step = "program_head" if status == "revision_for_program_head" else "associate_dean"
        rev_req["endorsements"] = rev_req.get("endorsements") or []
        rev_req["endorsements"].append({
            "step": endorsement_step,
            "by": user["username"],
            "name": user_name,
            "at": now_ts,
            "remarks": (remarks or "").strip(),
        })
        rev_req["current_reviewer"] = "dean"
        wf["revision_request"] = rev_req
        wf["status"] = "revision_for_dean"
        wf["step_entered_at"] = now_ts
        _log(wf, user["username"], "revision_endorsed", remarks=(remarks or "").strip(), step=endorsement_step)
        return wf

    if status == "revision_for_dean":
        # Dean approves -> unlock syllabus into draft for cycle increment
        prev_cycle = int(wf.get("cycle", 1))
        wf["status"] = "draft"
        wf["cycle"] = prev_cycle + 1
        wf["signatures"] = []
        wf["author_submissions"] = {}
        wf["is_awaiting_coauthors"] = False
        wf["approved_at"] = None
        rev_req["status"] = "approved"
        rev_req["approved_by"] = user["username"]
        rev_req["approved_by_name"] = user_name
        rev_req["approved_at"] = now_ts
        rev_req["approval_remarks"] = (remarks or "").strip()
        wf["revision_request"] = rev_req
        _log(wf, user["username"], "revision_approved", remarks=(remarks or "").strip(), step="dean")
        return wf

    return wf
