"""
notification_service.py - Email Notification & Signature Queue Bottleneck Service
Handles automated email notifications for syllabus review submissions, sequential endorsements,
approvals, returns, revision requests, and 3-day queue bottleneck reminders.
"""

import os
import re
import json
import smtplib
import threading
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
NOTIFICATIONS_LOG_FILE = os.path.join(DATA_DIR, "sent_notifications.json")
_notif_lock = threading.Lock()

# Configuration from Environment
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
SENDER_EMAIL = os.environ.get("NOTIFICATION_SENDER_EMAIL", "noreply-obe@usep.edu.ph")
SENDER_NAME = os.environ.get("NOTIFICATION_SENDER_NAME", "USeP College of Engineering • OBE Portal")
BOTTLENECK_SLA_DAYS = 3.0


def derive_email_for_user(username: str, full_name: str = "") -> str:
    """Derives a realistic, official USeP institutional email address."""
    name = re.sub(r"^(Engr\.|Dr\.|Dean|Prof\.|Mr\.|Ms\.|Mrs\.)\s*", "", full_name or "", flags=re.IGNORECASE).strip()
    name = re.sub(r",.*$", "", name).strip()
    parts = [p.lower() for p in re.findall(r"[A-Za-z]+", name) if len(p) > 1]
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[-1]}@usep.edu.ph"
    elif len(parts) == 1:
        return f"{parts[0]}@usep.edu.ph"
    clean_u = username.lower().replace("faculty_", "").replace("programhead_", "").replace("committee_", "")
    return f"{clean_u}@usep.edu.ph"


def resolve_user_contact(username_or_dict: Any) -> Tuple[str, str]:
    """Returns (email, full_name) for a given username or user dict."""
    uname = ""
    fname = ""
    email = ""
    if isinstance(username_or_dict, dict):
        uname = str(username_or_dict.get("username") or "").strip()
        fname = username_or_dict.get("full_name") or username_or_dict.get("name") or uname
        email = username_or_dict.get("email") or ""
    else:
        uname = str(username_or_dict or "").strip()

    try:
        import auth
        users = auth._load_users()
        user = users.get(uname) or users.get(auth.LEGACY_USERNAME_ALIASES.get(uname, uname))
        if user:
            fname = fname or user.get("full_name") or uname
            email = email or user.get("email") or derive_email_for_user(uname, fname)
            return email, fname
    except Exception:
        pass

    if not email:
        email = derive_email_for_user(uname, fname) if (uname or fname) else "noreply@usep.edu.ph"
    return email, fname or uname


def _append_notification_log(entry: Dict[str, Any]) -> None:
    """Thread-safe append of notification record to data/sent_notifications.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with _notif_lock:
        logs = []
        if os.path.exists(NOTIFICATIONS_LOG_FILE):
            try:
                with open(NOTIFICATIONS_LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
            except Exception:
                logs = []

        logs.insert(0, entry)
        # Retain last 300 notification logs
        logs = logs[:300]
        try:
            with open(NOTIFICATIONS_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"[Notifications] Error writing log: {e}")


def get_recent_notifications(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns the most recent notification records."""
    if not os.path.exists(NOTIFICATIONS_LOG_FILE):
        return []
    with _notif_lock:
        try:
            with open(NOTIFICATIONS_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
                return logs[:limit] if isinstance(logs, list) else []
        except Exception:
            return []


def send_email(
    to_emails: Any,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    category: str = "general",
    course_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Sends an email via SMTP if configured, or records to sent_notifications.json.
    Never throws unhandled exceptions that interrupt the main workflow.
    """
    if isinstance(to_emails, str):
        recipients = [e.strip() for e in to_emails.split(",") if e.strip()]
    elif isinstance(to_emails, (list, tuple, set)):
        recipients = [str(e).strip() for e in to_emails if str(e).strip()]
    else:
        recipients = []

    recipients = list(dict.fromkeys(recipients))  # deduplicate preserving order
    if not recipients:
        return {"success": False, "error": "No recipients provided."}

    now_iso = datetime.now().isoformat(timespec="seconds")
    entry = {
        "id": f"notif_{int(datetime.now().timestamp()*1000)}",
        "timestamp": now_iso,
        "category": category,
        "course_id": course_id,
        "subject": subject,
        "recipients": recipients,
        "preview": text_body[:250] + ("..." if len(text_body) > 250 else ""),
        "status": "pending",
        "metadata": metadata or {},
    }

    # Attempt live SMTP if configured
    if SMTP_HOST:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, recipients, msg.as_string())

            entry["status"] = "delivered_smtp"
            _append_notification_log(entry)
            print(f"[Notifications] Email sent via SMTP to {recipients}: {subject}")
            return {"success": True, "mode": "smtp", "recipients": recipients, "subject": subject}
        except Exception as e:
            print(f"[Notifications] SMTP error (falling back to logged delivery): {e}")
            entry["status"] = "logged_fallback"
            entry["smtp_error"] = str(e)
            _append_notification_log(entry)
            return {"success": True, "mode": "logged_fallback", "recipients": recipients, "subject": subject, "note": str(e)}

    # Local development / simulation mode
    entry["status"] = "delivered_simulated"
    _append_notification_log(entry)
    print(f"[Notifications: Sim-Mail] To: {recipients} | Subj: {subject}")
    return {"success": True, "mode": "simulated", "recipients": recipients, "subject": subject}


# --------------------------------------------------------------------------
# HTML Email Template Helper
# --------------------------------------------------------------------------
def _wrap_html_email(title: str, preheader: str, content_html: str, callout_html: str = "") -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ margin:0; padding:0; background:#f8fafc; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color:#1e293b; line-height:1.5; }}
    .container {{ max-width:600px; margin:24px auto; background:#ffffff; border-radius:10px; overflow:hidden; border:1px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background:#7f1d1d; color:#ffffff; padding:24px 28px; text-align:left; }}
    .header h1 {{ margin:0; font-size:1.25rem; font-weight:800; letter-spacing:-0.02em; }}
    .header p {{ margin:4px 0 0; font-size:0.85rem; color:#fecaca; }}
    .body {{ padding:28px; }}
    .callout {{ background:#f1f5f9; border-left:4px solid #7f1d1d; padding:16px 20px; border-radius:0 8px 8px 0; margin-bottom:20px; }}
    .sla-box {{ background:#fef3c7; border:1px solid #f59e0b; border-radius:8px; padding:14px 18px; margin:22px 0; font-size:0.85rem; color:#92400e; }}
    .footer {{ background:#f8fafc; padding:20px 28px; text-align:center; font-size:0.75rem; color:#64748b; border-top:1px solid #e2e8f0; }}
    .btn {{ display:inline-block; background:#7f1d1d; color:#ffffff !important; text-decoration:none; padding:11px 22px; font-weight:700; font-size:0.9rem; border-radius:6px; margin-top:14px; }}
    table.meta-table {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:0.88rem; }}
    table.meta-table td {{ padding:6px 0; vertical-align:top; }}
    table.meta-table td.label {{ width:140px; font-weight:700; color:#475569; }}
  </style>
</head>
<body>
  <div style="display:none; font-size:1px; color:#f8fafc; line-height:1px; max-height:0px; max-width:0px; opacity:0; overflow:hidden;">
    {preheader}
  </div>
  <div class="container">
    <div class="header">
      <h1>University of Southeastern Philippines</h1>
      <p>College of Engineering • OBE Syllabus Management &amp; Approvals</p>
    </div>
    <div class="body">
      <h2 style="margin:0 0 16px; font-size:1.15rem; color:#0f172a;">{title}</h2>
      {callout_html}
      {content_html}
      <div class="sla-box">
        <strong>⏱️ Review Turnaround &amp; Bottleneck Guideline (3-Day Policy):</strong><br/>
        In accordance with College of Engineering review policies, assigned reviewers are requested to complete syllabus evaluations and signatures within <strong>three (3) working days</strong>. Requests exceeding 3 days are flagged as queue bottlenecks.
      </div>
      <p style="font-size:0.88rem; color:#475569;">
        Please sign in to the USeP Class Record &amp; Syllabus Portal to view the document, complete your checklist (FM-USeP-MID-02), and record your signature.
      </p>
    </div>
    <div class="footer">
      This is an automated institutional notification from the USeP College of Engineering OBE Syllabus System.<br/>
      Please do not reply directly to this email. For questions, contact your Program Head or College QA Office.
    </div>
  </div>
</body>
</html>"""


# --------------------------------------------------------------------------
# High-Level Workflow Notification Triggers
# --------------------------------------------------------------------------
def notify_coauthor_submission_needed(doc: Dict[str, Any], submitter_user: Dict[str, Any], pending_authors: List[Dict[str, Any]]) -> None:
    """Notifies co-authors that an author has initiated submission and their endorsement click is needed."""
    code = doc.get("course_code") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_code") or "Course"
    title = doc.get("course_title") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_title") or "Subject"
    program = doc.get("program") or "Engineering"
    submitter_name = submitter_user.get("full_name") or submitter_user.get("username")
    wf = doc.get("workflow") or {}
    notes = wf.get("submission_notes") or ""

    recipients = []
    for a in pending_authors:
        em, _ = resolve_user_contact(a.get("username") or a)
        if not em and a.get("email"):
            em = a["email"]
        if em and em not in recipients:
            recipients.append(em)

    subject = f"📝 [Action Required: Co-Author Submission] {code} - {title}"
    plain = f"""USeP College of Engineering • Co-Author Syllabus Submission Confirmation

Dear Faculty Co-Author,

Engr. {submitter_name} has submitted the course syllabus for:
Course: {code} – {title}
Program: {program}

Because this syllabus has multiple designated faculty authors, all involved faculty must click Submit individually before the syllabus is officially forwarded to the Syllabus Review Committee.

Please sign in to the USeP OBE Portal, review the course syllabus, and confirm your submission endorsement.
"""
    callout = f"""
    <div class="callout" style="border-left-color:#2563eb; background:#eff6ff;">
      <h4 style="margin:0 0 6px; color:#1e40af;">👥 Multi-Faculty Co-Author Submission Required</h4>
      <table class="meta-table">
        <tr><td class="label">Course:</td><td><strong>{code}</strong> – {title}</td></tr>
        <tr><td class="label">Initiated By:</td><td>{submitter_name}</td></tr>
        <tr><td class="label">Action Required:</td><td><strong>Review & Confirm Submission</strong></td></tr>
      </table>
    </div>
    """
    content = f"""
    <p>Engr. <strong>{submitter_name}</strong> has submitted the syllabus for <strong>{code} ({title})</strong> for review.</p>
    <p>As an author/co-author of this course, university policy requires that all involved faculty confirm submission individually before it is forwarded to the Review Committee.</p>
    """
    html = _wrap_html_email(
        title=f"Co-Author Submission Needed: {code}",
        preheader=f"Submission confirmation required for {code} co-authored with {submitter_name}",
        content_html=content,
        callout_html=callout
    )

    send_email(recipients, subject, plain, html, category="coauthor_submission_needed", course_id=doc.get("id"))


def notify_syllabus_submitted(doc: Dict[str, Any], submitter_user: Dict[str, Any], committee_members: List[Dict[str, Any]]) -> None:
    """Notifies Review Committee members that a syllabus has been submitted for review."""
    code = doc.get("course_code") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_code") or "Course"
    title = doc.get("course_title") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_title") or "Subject"
    program = doc.get("program") or "Engineering"
    submitter_name = submitter_user.get("full_name") or submitter_user.get("username")
    submission_notes = (doc.get("workflow") or {}).get("submission_notes") or "Standard curriculum review submission."

    recipients = []
    for m in (committee_members or []):
        em, _ = resolve_user_contact(m)
        if em:
            recipients.append(em)

    subject = f"[OBE Syllabus Review Request] {code} - {title}"
    plain = f"""USeP College of Engineering • Syllabus Review Request

Dear Review Committee Member,

A syllabus review request has been submitted for:
Course: {code} – {title}
Program: {program}
Submitted By: {submitter_name}
Submission Notes: {submission_notes}

SLA Guideline: Under College of Engineering guidelines, committee members are requested to evaluate the syllabus within 3 working days to prevent signature bottlenecks.

Please log in to the OBE Portal to fill out Review Checklist Form FM-USeP-MID-02 and endorse this syllabus.
"""

    callout = f"""
    <div class="callout">
      <table class="meta-table">
        <tr><td class="label">Course:</td><td><strong>{code}</strong> – {title}</td></tr>
        <tr><td class="label">Program:</td><td>{program}</td></tr>
        <tr><td class="label">Faculty Owner:</td><td>{submitter_name}</td></tr>
        <tr><td class="label">Review Stage:</td><td>Review Committee Evaluation (FM-USeP-MID-02)</td></tr>
        <tr><td class="label">Notes:</td><td><em>"{submission_notes}"</em></td></tr>
      </table>
    </div>
    """
    content = f"""
    <p>Engr. <strong>{submitter_name}</strong> has submitted the syllabus for <strong>{code} ({title})</strong> for formal review and committee evaluation.</p>
    <p>You have been designated as a member of the Review Committee for this course. Please inspect the course outcomes, assessment tasks, and alignment matrix against institutional standards.</p>
    """
    html = _wrap_html_email(
        title=f"Syllabus Review Requested: {code}",
        preheader=f"Syllabus review requested for {code} by {submitter_name}",
        content_html=content,
        callout_html=callout
    )

    send_email(recipients, subject, plain, html, category="review_request", course_id=doc.get("id"))


def notify_syllabus_forwarded(
    doc: Dict[str, Any],
    next_step_label: str,
    reviewer_recipients: List[Any],
    previous_signer: Optional[Dict[str, Any]] = None,
    remarks: str = ""
) -> None:
    """Notifies next reviewer(s) in the sequential approval chain."""
    code = doc.get("course_code") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_code") or "Course"
    title = doc.get("course_title") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_title") or "Subject"
    program = doc.get("program") or "Engineering"
    prev_name = (previous_signer or {}).get("full_name") or "Review Committee"

    recipients = []
    for r in reviewer_recipients:
        em, _ = resolve_user_contact(r)
        if em:
            recipients.append(em)

    subject = f"[OBE Syllabus Endorsement Awaiting Action] {code} - {title} ({next_step_label})"
    plain = f"""USeP College of Engineering • Syllabus Endorsement Awaiting Action

Dear Colleague,

The syllabus for {code} ({title}) has been endorsed by {prev_name} and is now awaiting your action as: {next_step_label}.
Remarks: {remarks or 'None provided.'}

SLA Guideline: Reviews are expected within 3 working days to prevent queue bottlenecks.

Please sign in to the portal to review and sign off.
"""
    callout = f"""
    <div class="callout">
      <table class="meta-table">
        <tr><td class="label">Course:</td><td><strong>{code}</strong> – {title}</td></tr>
        <tr><td class="label">Program:</td><td>{program}</td></tr>
        <tr><td class="label">Current Stage:</td><td><strong>{next_step_label}</strong></td></tr>
        <tr><td class="label">Endorsed By:</td><td>{prev_name}</td></tr>
        <tr><td class="label">Remarks:</td><td><em>"{remarks or 'Approved and forwarded.'}"</em></td></tr>
      </table>
    </div>
    """
    content = f"""
    <p>This syllabus has advanced through the sequential review workflow and is now queued for your official sign-off as <strong>{next_step_label}</strong>.</p>
    """
    html = _wrap_html_email(
        title=f"Action Required: {code} ({next_step_label})",
        preheader=f"{code} syllabus forwarded to {next_step_label}",
        content_html=content,
        callout_html=callout
    )

    send_email(recipients, subject, plain, html, category="forwarded_step", course_id=doc.get("id"))


def notify_syllabus_decision(doc: Dict[str, Any], decision: str, reviewer_user: Dict[str, Any], remarks: str = "") -> None:
    """Notifies course owner of final approval or return for revision."""
    code = doc.get("course_code") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_code") or "Course"
    title = doc.get("course_title") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_title") or "Subject"
    owner_uname = doc.get("owner")
    owner_email, owner_name = resolve_user_contact(owner_uname)
    reviewer_name = reviewer_user.get("full_name") or reviewer_user.get("username")

    if decision == "approve":
        subject = f"✅ [OBE Syllabus Approved & Locked] {code} - {title}"
        plain = f"""USeP College of Engineering • Syllabus Approved & Locked

Dear Engr. {owner_name},

Congratulations! Your course syllabus for {code} ({title}) has successfully passed all sequential review committee endorsements and has been officially approved by the College Dean.

Status: Officially Approved & Locked
Class Record & Grade Scoring: Completely Unlocked

Thank you for your commitment to OBE academic excellence.
"""
        callout = f"""
        <div class="callout" style="border-left-color:#16a34a; background:#f0fdf4;">
          <h4 style="margin:0 0 6px; color:#166534;">🎉 Official Syllabus Approved by College Dean</h4>
          <p style="margin:0; font-size:0.88rem; color:#15803d;">
            <strong>{code} – {title}</strong> is officially locked for institutional accreditation. Class record setup and grade recording are now fully unlocked.
          </p>
        </div>
        """
        content = f"<p>The final approval signature of <strong>{reviewer_name}</strong> has been affixed. You can now download the official signed syllabus PDF and FM-USeP-MID-02 evaluation document from the studio.</p>"
        html = _wrap_html_email(title="Syllabus Officially Approved & Locked", preheader=f"{code} syllabus approved by College Dean", content_html=content, callout_html=callout)
        send_email([owner_email], subject, plain, html, category="syllabus_approved", course_id=doc.get("id"))

    elif decision == "return":
        subject = f"↩️ [OBE Syllabus Returned for Revision] {code} - {title}"
        plain = f"""USeP College of Engineering • Syllabus Returned for Revision

Dear Engr. {owner_name},

Your syllabus for {code} ({title}) was returned for revision by {reviewer_name}.
Remarks / Required Modifications:
"{remarks}"

Please log in to make the required corrections and re-submit the syllabus for review.
"""
        callout = f"""
        <div class="callout" style="border-left-color:#dc2626; background:#fef2f2;">
          <h4 style="margin:0 0 6px; color:#991b1b;">Syllabus Returned for Revision</h4>
          <p style="margin:0; font-size:0.88rem; color:#7f1d1d;">
            <strong>Reviewer:</strong> {reviewer_name}<br/>
            <strong>Remarks:</strong> <em>"{remarks}"</em>
          </p>
        </div>
        """
        content = f"<p>The syllabus has been returned to your workspace in <strong>Returned</strong> status. You can edit the required sections and resubmit once complete.</p>"
        html = _wrap_html_email(title="Syllabus Returned for Revision", preheader=f"{code} returned by {reviewer_name}", content_html=content, callout_html=callout)
        send_email([owner_email], subject, plain, html, category="syllabus_returned", course_id=doc.get("id"))


def notify_revision_requested(doc: Dict[str, Any], owner_user: Dict[str, Any], target_role: str, reviewers: List[Any], reason: str) -> None:
    """Notifies reviewers of a request to unlock an approved syllabus for a new revision cycle."""
    code = doc.get("course_code") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_code") or "Course"
    title = doc.get("course_title") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_title") or "Subject"
    owner_name = owner_user.get("full_name") or owner_user.get("username")

    recipients = []
    for r in reviewers:
        em, _ = resolve_user_contact(r)
        if em:
            recipients.append(em)

    subject = f"📝 [OBE Syllabus Revision Request] {code} - {title} ({target_role})"
    plain = f"""USeP College of Engineering • Syllabus Revision Request

Dear {target_role},

Engr. {owner_name} has requested an official revision cycle for the approved syllabus:
Course: {code} – {title}
Reason for Revision: "{reason}"

Under College of Engineering policy, revision requests must be endorsed by the {target_role} and approved by the Dean before the syllabus can be unlocked.

Please review this request in the Approvals Portal within 3 working days.
"""
    callout = f"""
    <div class="callout" style="border-left-color:#d97706; background:#fffbeb;">
      <h4 style="margin:0 0 6px; color:#92400e;">Syllabus Revision Request</h4>
      <table class="meta-table">
        <tr><td class="label">Course:</td><td><strong>{code}</strong> – {title}</td></tr>
        <tr><td class="label">Faculty Owner:</td><td>{owner_name}</td></tr>
        <tr><td class="label">Reason:</td><td><em>"{reason}"</em></td></tr>
        <tr><td class="label">Action:</td><td>Endorse or Reject Revision Request</td></tr>
      </table>
    </div>
    """
    content = f"<p>A request to unlock <strong>{code}</strong> for a new revision cycle is awaiting your action.</p>"
    html = _wrap_html_email(title="Syllabus Revision Request Submitted", preheader=f"Revision requested for {code}", content_html=content, callout_html=callout)
    send_email(recipients, subject, plain, html, category="revision_requested", course_id=doc.get("id"))


def notify_revision_decision(doc: Dict[str, Any], action: str, reviewer_user: Dict[str, Any], remarks: str = "") -> None:
    """Notifies course owner of revision approval or rejection."""
    code = doc.get("course_code") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_code") or "Course"
    title = doc.get("course_title") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_title") or "Subject"
    owner_uname = doc.get("owner")
    owner_email, owner_name = resolve_user_contact(owner_uname)
    reviewer_name = reviewer_user.get("full_name") or reviewer_user.get("username")

    if action in ("approve", "approved"):
        subject = f"✅ [OBE Syllabus Revision Approved] {code} - {title}"
        plain = f"""USeP College of Engineering • Syllabus Revision Request Approved

Dear Engr. {owner_name},

Your request for a syllabus revision cycle for {code} ({title}) has been approved by {reviewer_name}.
The syllabus is now unlocked for Cycle editing in your workspace.

Remarks: {remarks or 'Approved for updates.'}
"""
        callout = f"""
        <div class="callout" style="border-left-color:#16a34a; background:#f0fdf4;">
          <h4 style="margin:0 0 6px; color:#166534;">Syllabus Revision Approved</h4>
          <p style="margin:0; font-size:0.88rem; color:#15803d;">
            <strong>Course:</strong> {code} – {title}<br/>
            <strong>Approved By:</strong> {reviewer_name}<br/>
            <strong>Remarks:</strong> <em>"{remarks or 'Approved for syllabus updates.'}"</em>
          </p>
        </div>
        """
        content = f"<p>Your syllabus has been unlocked and placed back into <strong>Draft</strong> status. You may now perform the necessary curricular updates and re-submit for review.</p>"
        html = _wrap_html_email(title="Syllabus Revision Approved", preheader=f"Revision request approved for {code}", content_html=content, callout_html=callout)
        send_email([owner_email], subject, plain, html, category="revision_approved", course_id=doc.get("id"))

    elif action in ("reject", "rejected"):
        subject = f"❌ [OBE Syllabus Revision Request Rejected] {code} - {title}"
        plain = f"""USeP College of Engineering • Syllabus Revision Request Rejected

Dear Engr. {owner_name},

Your request for syllabus revision for {code} ({title}) was rejected by {reviewer_name}.
Remarks / Reason:
"{remarks}"

The official syllabus remains approved and locked.
"""
        callout = f"""
        <div class="callout" style="border-left-color:#dc2626; background:#fef2f2;">
          <h4 style="margin:0 0 6px; color:#991b1b;">Revision Request Rejected</h4>
          <p style="margin:0; font-size:0.88rem; color:#7f1d1d;">
            <strong>Reviewer:</strong> {reviewer_name}<br/>
            <strong>Reason:</strong> <em>"{remarks}"</em>
          </p>
        </div>
        """
        content = f"<p>The syllabus remains officially approved and locked from direct edits.</p>"
        html = _wrap_html_email(title="Syllabus Revision Rejected", preheader=f"Revision request rejected for {code}", content_html=content, callout_html=callout)
        send_email([owner_email], subject, plain, html, category="revision_rejected", course_id=doc.get("id"))


def notify_bottleneck_reminder(doc: Dict[str, Any], reviewers: List[Any], days_in_queue: float) -> None:
    """Sends a follow-up reminder email for requests stalled in queue for more than 3 days."""
    code = doc.get("course_code") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_code") or "Course"
    title = doc.get("course_title") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_title") or "Subject"
    wf = doc.get("workflow") or {}
    step_label = wf.get("current_step_label") or "Pending Review"
    owner_uname = doc.get("owner")
    _, owner_name = resolve_user_contact(owner_uname)

    recipients = []
    for r in reviewers:
        em, _ = resolve_user_contact(r)
        if em:
            recipients.append(em)

    subject = f"⚠️ [REMINDER: OVERDUE (>3 Days)] Syllabus Review Needed: {code} - {title}"
    plain = f"""USeP College of Engineering • Overdue Signature Queue Reminder

Dear Reviewer,

This is a follow-up reminder that the syllabus review request for:
Course: {code} – {title}
Faculty Owner: {owner_name}
Current Step: {step_label}

This request has been pending in your signature queue for {days_in_queue} days, which exceeds the College of Engineering 3-day turnaround SLA guideline.

Please log in to the OBE Portal at your earliest opportunity to complete your review and endorse or return this syllabus.
"""
    callout = f"""
    <div class="callout" style="border-left-color:#ea580c; background:#fff7ed;">
      <h4 style="margin:0 0 6px; color:#9a3412;">⚠️ Overdue Bottleneck Notice (&gt;3 Days in Queue)</h4>
      <table class="meta-table">
        <tr><td class="label">Course:</td><td><strong>{code}</strong> – {title}</td></tr>
        <tr><td class="label">Faculty Owner:</td><td>{owner_name}</td></tr>
        <tr><td class="label">Current Queue:</td><td><strong>{step_label}</strong></td></tr>
        <tr><td class="label">Time Pending:</td><td><strong style="color:#c2410c;">{days_in_queue} days</strong> (Guideline: max 3 days)</td></tr>
      </table>
    </div>
    """
    content = f"""
    <p>This request has remained in the <strong>{step_label}</strong> queue for <strong>{days_in_queue} days</strong>, triggering institutional bottleneck tracking. Your prompt action helps ensure that faculty and students have timely access to officially approved course syllabi.</p>
    """
    html = _wrap_html_email(
        title=f"Follow-up Reminder: {code} Review Pending",
        preheader=f"{code} review pending for {days_in_queue} days in queue",
        content_html=content,
        callout_html=callout
    )

    send_email(recipients, subject, plain, html, category="bottleneck_reminder", course_id=doc.get("id"), metadata={"days_in_queue": days_in_queue})


def check_and_dispatch_bottleneck_reminders(all_courses: Optional[List[Dict[str, Any]]] = None, force: bool = False) -> Dict[str, Any]:
    """
    Scans all courses for review requests pending > 3 days.
    Sends reminder emails and logs bottleneck follow-up actions.
    Avoids re-sending if a reminder was dispatched in the last 24 hours unless force=True.
    """
    import courses_store
    import syllabus_workflow

    if all_courses is None:
        all_courses = courses_store.list_all_workflow_courses()

    reminded_count = 0
    reminded_courses = []
    now = datetime.now()

    for item in all_courses:
        doc = item.get("doc_raw")
        if not doc or not doc.get("blueprint"):
            cid = item.get("id")
            owner = item.get("owner")
            if cid and owner:
                doc = courses_store.get_course(owner, cid) if (owner and cid) else (courses_store.find_course(cid) if cid else None)
        if not doc or not doc.get("blueprint"):
            continue
        cid = doc.get("id")
        wf = doc.get("workflow") or {}
        status = wf.get("status")

        if status in syllabus_workflow.EDITABLE_STATUSES or status == "approved":
            continue

        q_age = syllabus_workflow.get_queue_age(doc, now_dt=now)
        days = q_age.get("days_in_queue", 0.0)

        if days < BOTTLENECK_SLA_DAYS:
            continue

        # Check last reminder timestamp (throttle to once per 24 hours unless forced)
        last_rem = wf.get("last_reminder_sent_at")
        if last_rem and not force:
            try:
                last_dt = datetime.fromisoformat(last_rem.replace("Z", "").split("+")[0])
                if (now - last_dt).total_seconds() < 86400:
                    continue  # already reminded within 24 hours
            except Exception:
                pass

        # Resolve reviewers for current step
        reviewers = syllabus_workflow.get_reviewers_for_step(doc)
        if not reviewers:
            continue

        notify_bottleneck_reminder(doc, reviewers, days)
        wf["last_reminder_sent_at"] = now.isoformat(timespec="seconds")
        syllabus_workflow._log(
            wf,
            by="system_bottleneck_monitor",
            action="bottleneck_reminder",
            remarks=f"Overdue reminder sent ({days} days in queue; exceeds 3-day SLA guideline)",
            step=wf.get("current_step") or status
        )
        courses_store.save_course_doc(doc)

        reminded_count += 1
        reminded_courses.append({
            "id": cid,
            "course_code": doc.get("course_code") or (doc.get("blueprint") or {}).get("metadata", {}).get("course_code"),
            "days_in_queue": days,
            "status": status,
            "reviewers_count": len(reviewers)
        })

    return {
        "reminded_count": reminded_count,
        "reminded_courses": reminded_courses,
        "checked_at": now.isoformat(timespec="seconds")
    }
