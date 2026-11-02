"""
Generates an official University of Southeastern Philippines (USeP)
OBE Course Syllabus Acknowledgement Form (FM-USeP-MID-07) in 8.5 x 13 in Portrait format,
matching the exact structure, tables, and typography of FM-USeP-MID-07_Syllabus Acknowledgement Form.docx.
"""

import os
import copy
import base64
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from fpdf import FPDF
from fpdf.fonts import FontFace


def _save_data_url_image(data_url: str) -> Optional[str]:
    """Helper to write data URL PNG/JPEG into a temp file for FPDF."""
    if not data_url or not isinstance(data_url, str) or not data_url.startswith("data:image"):
        return None
    try:
        header, b64_data = data_url.split(",", 1)
        ext = ".png" if "png" in header else ".jpg"
        raw_bytes = base64.b64decode(b64_data)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(raw_bytes)
        tmp.close()
        return tmp.name
    except Exception:
        return None


def _clean_text(val: str, has_ttf: bool = True) -> str:
    """Sanitizes text for PDF rendering, supporting rich typographic characters."""
    if val is None:
        return ""
    s = str(val)
    replacements = {
        "\u2013": "–" if has_ttf else "-",
        "\u2014": "—" if has_ttf else "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "•" if has_ttf else "*",
        "\u25cf": "•" if has_ttf else "*",
        "\u2713": "[X]",
        "\u2714": "[X]",
        "\u2717": "[x]",
        "\u2718": "[x]",
        "\u2192": "->",
        "\u2265": ">=",
        "\u2264": "<=",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    if not has_ttf:
        return s.encode("latin-1", "replace").decode("latin-1")
    return s


class USePAcknowledgmentPDF(FPDF):
    def __init__(self, course_code: str = "EE 211", course_title: str = "ELECTRICAL CIRCUITS 1", college: str = "COLLEGE OF ENGINEERING"):
        # Official USeP Folio format: 8.5 x 13 inches (215.9 mm x 330.2 mm) in Portrait
        super().__init__(orientation="P", unit="mm", format=(215.9, 330.2))
        self.course_code = course_code.strip()
        self.course_title = course_title.strip().upper()
        self.college = college.strip().upper()
        self.set_margins(left=19.05, top=19.05, right=19.05)
        self.set_auto_page_break(auto=True, margin=19.05)

        # Detect Windows standard TrueType fonts for exact Arial & Cinzel match
        win_fonts = "C:/Windows/Fonts"
        self.has_ttf = False
        if os.path.exists(os.path.join(win_fonts, "arial.ttf")) and os.path.exists(os.path.join(win_fonts, "arialbd.ttf")):
            try:
                self.add_font("Arial", "", os.path.join(win_fonts, "arial.ttf"))
                self.add_font("Arial", "B", os.path.join(win_fonts, "arialbd.ttf"))
                if os.path.exists(os.path.join(win_fonts, "ariali.ttf")):
                    self.add_font("Arial", "I", os.path.join(win_fonts, "ariali.ttf"))
                self.font_main = "Arial"
                self.has_ttf = True
            except Exception:
                self.font_main = "Helvetica"
        else:
            self.font_main = "Helvetica"

        if os.path.exists(os.path.join(win_fonts, "ARIALN.TTF")) and os.path.exists(os.path.join(win_fonts, "ARIALNB.TTF")):
            try:
                self.add_font("ArialNarrow", "", os.path.join(win_fonts, "ARIALN.TTF"))
                self.add_font("ArialNarrow", "B", os.path.join(win_fonts, "ARIALNB.TTF"))
                self.font_narrow = "ArialNarrow"
            except Exception:
                self.font_narrow = self.font_main
        else:
            self.font_narrow = self.font_main

        # Cinzel font for official University header
        if os.path.exists(os.path.join(win_fonts, "Cinzel-Bold.otf")):
            try:
                self.add_font("Cinzel", "B", os.path.join(win_fonts, "Cinzel-Bold.otf"))
                self.font_cinzel = "Cinzel"
            except Exception:
                self.font_cinzel = self.font_main
        else:
            self.font_cinzel = self.font_main

    def footer(self):
        self.set_y(-15.0)
        self.set_font(self.font_main, "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(130.0, 4.0, _clean_text(f"FM-USeP-MID-07 • {self.course_code} - {self.course_title}", self.has_ttf), border=0, align="L")
        self.cell(47.8, 4.0, f"Page {self.page_no()} of {{nb}}", border=0, align="R")


def generate_syllabus_acknowledgment_pdf(bp_or_doc: Any, doc: Optional[Dict[str, Any]] = None, user: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Renders official FM-USeP-MID-07 Syllabus Acknowledgement Form PDF with:
      - Document Control Header with Cinzel Bold
      - Course details (Course Code & Title, Faculty, Semester/AY)
      - Acknowledgment declaration
      - Student roster with embedded digital signatures and timestamps
    """
    if doc is not None:
        target_doc = copy.deepcopy(doc)
        if hasattr(bp_or_doc, "to_dict"):
            target_doc["blueprint"] = bp_or_doc.to_dict()
        elif isinstance(bp_or_doc, dict) and "blueprint" not in target_doc:
            target_doc["blueprint"] = bp_or_doc
    else:
        target_doc = bp_or_doc if isinstance(bp_or_doc, dict) else ({"blueprint": bp_or_doc.to_dict()} if hasattr(bp_or_doc, "to_dict") else {})

    bp = target_doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    wf = target_doc.get("workflow") or {}

    c_code = (target_doc.get("course_code") or meta.get("course_code") or "EE 211").strip()
    c_title = (target_doc.get("course_title") or meta.get("course_title") or "Electrical Circuits 1").strip()
    fac_name = (meta.get("faculty_name") or target_doc.get("faculty_name") or "Faculty Member").strip()
    sem_ay = (target_doc.get("semester_ay") or meta.get("semester_ay") or "1st Semester, A.Y. 2026-2027").strip()
    college = (meta.get("college") or "COLLEGE OF ENGINEERING").strip()

    pdf = USePAcknowledgmentPDF(course_code=c_code, course_title=c_title, college=college)
    pdf.add_page()

    x0 = 19.05
    y0 = 19.05
    page_w = pdf.epw
    left_w = 127.8
    ctrl_label_w = 23.0
    ctrl_val_w = 27.0
    row_h = 5.2
    total_h = row_h * 5  # 26.0 mm

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    pdf.rect(x0, y0, left_w, total_h)

    # Embed USeP logo if available
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "static", "logo_1_Image39.jpg")
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=x0 + 2.5, y=y0 + 1.5, w=23.0, h=23.0)
        except Exception:
            pass

    # University header text inside left box
    pdf.set_xy(x0 + 27.0, y0 + 1.2)
    pdf.set_font(pdf.font_main, "", 7.5)
    pdf.cell(left_w - 29.0, 3.5, "Republic of the Philippines", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 27.0)
    pdf.set_font(pdf.font_cinzel, "B", 10.5)
    pdf.cell(left_w - 29.0, 4.6, "University of Southeastern Philippines", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 27.0)
    pdf.set_font(pdf.font_main, "", 6.8)
    pdf.cell(left_w - 29.0, 3.2, "Iñigo St., Bo. Obrero, Davao City 8000", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 27.0)
    pdf.set_font(pdf.font_main, "", 6.5)
    pdf.cell(left_w - 29.0, 3.0, "Telephone: (082) 227-8192 | Website: www.usep.edu.ph", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 27.0)
    pdf.cell(left_w - 29.0, 3.0, "Email: president@usep.edu.ph", align="C", new_x="LMARGIN", new_y="NEXT")

    # Document Control Table (Right 5 rows)
    ctrl_rows = [
        ("Form No.", "FM-USeP-MID-07"),
        ("Issue Status", "01"),
        ("Revision No.", "00"),
        ("Date Effective", "18 August 2026"),
        ("Approved by", "President"),
    ]
    cx = x0 + left_w
    for idx, (k, v) in enumerate(ctrl_rows):
        ry = y0 + idx * row_h
        pdf.set_xy(cx, ry)
        pdf.set_font(pdf.font_narrow, "", 7.0)
        pdf.cell(ctrl_label_w, row_h, k, border=1, align="L")
        pdf.set_font(pdf.font_narrow, "B" if idx == 0 else "", 7.0)
        pdf.cell(ctrl_val_w, row_h, v, border=1, align="L")

    # Title Bar
    pdf.set_xy(x0, y0 + total_h + 3.0)
    pdf.set_font(pdf.font_main, "B", 11.0)
    pdf.cell(page_w, 6.0, "SYLLABUS ACKNOWLEDGEMENT FORM", border=0, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2.0)

    # Course Metadata Table
    pdf.set_font(pdf.font_narrow, "B", 8.5)
    meta_rows = [
        ("Course Code and Title", f"{c_code} – {c_title}"),
        ("Faculty", fac_name),
        ("Semester/Academic Year", sem_ay),
    ]
    with pdf.table(col_widths=(45.0, 5.0, pdf.epw - 50.0), width=page_w, line_height=4.6, align="L") as t_meta:
        for k, v in meta_rows:
            r = t_meta.row()
            r.cell(_clean_text(k, pdf.has_ttf), style=FontFace(emphasis="BOLD"))
            r.cell(":")
            r.cell(_clean_text(v, pdf.has_ttf))

    pdf.ln(3.0)

    # Acknowledgment Text
    pdf.set_font(pdf.font_main, "", 8.0)
    decl1 = (
        "I acknowledge that I have received, read, and understood the Course Syllabus for the course stated above. "
        "The syllabus includes important information about the course outcomes, intended learning outcomes, requirements, "
        "grading system, assessment methods, consultation hours, and classroom policies, including those related to academic "
        "honesty, gender sensitivity, AI use, and plagiarism."
    )
    pdf.multi_cell(page_w, 3.8, _clean_text(decl1, pdf.has_ttf), align="J")
    pdf.ln(1.5)

    decl2 = (
        "I understand that it is my responsibility to comply with the expectations and requirements outlined in the "
        "syllabus and to seek clarification from the faculty when necessary."
    )
    pdf.multi_cell(page_w, 3.8, _clean_text(decl2, pdf.has_ttf), align="J")
    pdf.ln(3.5)

    # Student Signatures Table
    # Match students from bp["students"] or class record
    raw_students = bp.get("students") or []
    # Index acknowledgments by student_id or student_name
    acks = target_doc.get("student_acknowledgments") or wf.get("student_acknowledgments") or []
    ack_map = {}
    for a in acks:
        sid = (a.get("student_id") or "").strip().lower()
        sname = (a.get("student_name") or "").strip().lower()
        if sid:
            ack_map[sid] = a
        if sname:
            ack_map[sname] = a

    gray_hdr = FontFace(fill_color=(230, 230, 230), emphasis="BOLD")

    # Table 3: STUDENT NAME (70 mm) | SIGNATURE (60 mm) | DATE (47.8 mm)
    col_w = (65.0, 60.0, pdf.epw - 125.0)
    pdf.set_font(pdf.font_narrow, "B", 8.0)

    temp_files = []
    try:
        is_student_user = bool(user and str(user.get("role", "")).lower() == "student")
        user_sid = str(user.get("student_id") or user.get("username") or "").strip().lower() if user else ""
        user_name = str(user.get("full_name") or user.get("name") or "").strip().lower() if user else ""
        user_digits = "".join(filter(str.isdigit, user_sid))

        student_rows = []
        if raw_students:
            for s in raw_students:
                s_id = (s.get("student_id") or "").strip()
                s_name = (s.get("name") or s.get("student_name") or f"{s.get('last_name', '')}, {s.get('first_name', '')}".strip(", ") or s.get("last_name") or "").strip()
                ack = ack_map.get(s_id.lower()) or ack_map.get(s_name.lower())
                has_signed = bool(ack and (ack.get("signature_data") or ack.get("acknowledged_at")))
                sig_raw = ack.get("signature_data") if (ack and ack.get("signature_data")) else ""
                ack_ts = (ack.get("acknowledged_at") or ack.get("date") or "") if ack else ""
                date_display = ack_ts.replace("T", " ")[:16] if ack_ts else ""

                curr_digits = "".join(filter(str.isdigit, s_id))
                is_self = False
                if is_student_user:
                    if (s_id and s_id.lower() == user_sid) or \
                       (curr_digits and user_digits and len(curr_digits) >= 4 and curr_digits == user_digits) or \
                       (user_name and (user_name == s_name.lower() or user_name in s_name.lower() or s_name.lower() in user_name)):
                        is_self = True

                if is_student_user and not is_self:
                    display_name = "(Name of the Student)"
                    if has_signed:
                        display_sig = "(Electronically Signed)"
                        display_date = "(Date)"
                    else:
                        display_sig = ""
                        display_date = ""
                    sig_img = None
                else:
                    display_name = s_name
                    display_date = date_display
                    sig_img = None
                    if sig_raw:
                        tmp_img = _save_data_url_image(sig_raw)
                        if tmp_img:
                            temp_files.append(tmp_img)
                            sig_img = tmp_img
                    display_sig = "(Electronically Signed)" if (has_signed and not sig_img) else ""

                student_rows.append({
                    "student_id": s_id,
                    "name": s_name,
                    "display_name": display_name,
                    "sig_img": sig_img,
                    "display_sig": display_sig,
                    "display_date": display_date,
                })
        else:
            for i in range(1, 21):
                student_rows.append({
                    "student_id": "",
                    "name": "",
                    "display_name": "",
                    "sig_img": None,
                    "display_sig": "",
                    "display_date": "",
                })

        with pdf.table(col_widths=col_w, width=page_w, line_height=7.0, align="L") as t_stud:
            hdr = t_stud.row(style=gray_hdr)
            hdr.cell("STUDENT NAME")
            hdr.cell("SIGNATURE")
            hdr.cell("DATE")

            for s in student_rows:
                r = t_stud.row()
                r.cell(_clean_text(s["display_name"], pdf.has_ttf))
                if s.get("sig_img"):
                    r.cell(img=s["sig_img"], align="C")
                elif s.get("display_sig"):
                    r.cell(_clean_text(s["display_sig"], pdf.has_ttf), align="C")
                else:
                    r.cell("")
                r.cell(_clean_text(s["display_date"], pdf.has_ttf), align="C" if s.get("display_date") == "(Date)" else "L")

        return bytes(pdf.output())
    finally:
        for tf in temp_files:
            try:
                if os.path.exists(tf):
                    os.remove(tf)
            except Exception:
                pass
