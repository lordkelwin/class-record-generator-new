"""
Official USeP Table of Specifications (FM-USeP-MID-03)
and TOS Test Review Form (FM-USeP-MID-04) PDF Generator.

Strictly conforms to:
  - samples/FM-USeP-MID-03_Table of Specification_rev00.docx
  - samples/FM-USeP-MID-04_TOS Test Review Form_rev00.docx
  - Official Folio Legal format (215.9 x 330.2 mm)
  - Cinzel Bold typography and USeP Controlled Document standards.
"""
import base64
import os
import re
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from fpdf import FPDF


def _clean_text(val: Any, has_ttf: bool = True) -> str:
    """Sanitizes text for PDF rendering."""
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
        "\t": " ",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    return s


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


class OfficialTosBasePDF(FPDF):
    """Base class for USeP Controlled Document TOS PDFs."""

    def __init__(self, course_meta: Dict[str, Any]):
        super().__init__(orientation="P", unit="mm", format=(215.9, 330.2))
        self.set_auto_page_break(auto=False)
        self.set_margins(11.0, 12.0, 11.0)
        self.course_meta = course_meta

        base_dir = os.path.dirname(os.path.abspath(__file__))
        win_fonts = "C:/Windows/Fonts"
        self.has_ttf = False

        arial_path = os.path.join(win_fonts, "arial.ttf")
        arialbd_path = os.path.join(win_fonts, "arialbd.ttf")
        if os.path.exists(arial_path) and os.path.exists(arialbd_path):
            try:
                self.add_font("Arial", "", arial_path)
                self.add_font("Arial", "B", arialbd_path)
                if os.path.exists(os.path.join(win_fonts, "ariali.ttf")):
                    self.add_font("Arial", "I", os.path.join(win_fonts, "ariali.ttf"))
                self.font_main = "Arial"
                self.has_ttf = True
            except Exception:
                self.font_main = "Helvetica"
        else:
            self.font_main = "Helvetica"

        cinzel_local = os.path.join(base_dir, "fonts", "Cinzel-Bold.otf")
        cinzel_win = os.path.join(win_fonts, "Cinzel-Bold.otf")
        cinzel_path = cinzel_local if os.path.exists(cinzel_local) else cinzel_win
        if os.path.exists(cinzel_path):
            try:
                self.add_font("Cinzel", "B", cinzel_path)
                self.font_cinzel = "Cinzel"
            except Exception:
                self.font_cinzel = self.font_main
        else:
            self.font_cinzel = self.font_main

    def draw_controlled_header(self, form_no: str, title: str, x0: float = 11.0, y: float = 14.0, table_w: float = 194.0):
        """Draws the official USeP header with logo, university address, and document control block."""
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.25)
        self.rect(x0, y, table_w, 32.5)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "static", "logo_1_Image39.jpg")
        if os.path.exists(logo_path):
            try:
                self.image(logo_path, x=x0 + 2.8, y=y + 3.5, w=25.0, h=25.0)
            except Exception:
                pass

        # University details (center block)
        self.set_xy(x0 + 30.6, y + 2.5)
        self.set_font(self.font_main, "", 8.0)
        self.cell(99.8, 4.0, "Republic of the Philippines", align="C")
        self.set_xy(x0 + 30.6, y + 6.8)
        self.set_font(self.font_cinzel, "B", 10.5)
        self.cell(99.8, 4.5, "University of Southeastern Philippines", align="C")
        self.set_xy(x0 + 30.6, y + 11.5)
        self.set_font(self.font_main, "", 7.5)
        self.cell(99.8, 3.8, "Iñigo St., Bo. Obrero, Davao City 8000", align="C")
        self.set_xy(x0 + 30.6, y + 15.3)
        self.cell(99.8, 3.8, "Telephone: (082) 227-8192", align="C")
        self.set_xy(x0 + 30.6, y + 19.1)
        self.cell(99.8, 3.8, "Website: www.usep.edu.ph", align="C")
        self.set_xy(x0 + 30.6, y + 22.9)
        self.cell(99.8, 3.8, "Email: president@usep.edu.ph", align="C")

        # Document Control Table (right block)
        ctrl_rows = [
            ("Form No.", form_no),
            ("Issue Status", "01"),
            ("Revision No.", "00"),
            ("Date Effective", "05 January 2026"),
            ("Approved by", "President"),
        ]
        cx = x0 + 30.6 + 99.8
        for r_i, (k, v) in enumerate(ctrl_rows):
            ry = y + r_i * 6.5
            self.set_xy(cx, ry)
            self.set_font("Helvetica", "", 7.5)
            self.cell(26.8, 6.5, k, border=1, align="L")
            self.set_font("Helvetica", "B" if r_i == 0 else "", 7.5)
            self.cell(36.8, 6.5, v, border=1, align="L")

        # Title Row
        self.set_xy(x0, y + 32.5)
        self.set_font("Helvetica", "B", 11.0)
        self.cell(table_w, 7.0, title, border=1, align="C")

    def draw_checkbox(self, x: float, y: float, checked: bool = False, size: float = 3.2):
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.25)
        self.rect(x, y, size, size)
        if checked:
            self.set_line_width(0.4)
            self.line(x + 0.6, y + 0.6, x + size - 0.6, y + size - 0.6)
            self.line(x + size - 0.6, y + 0.6, x + 0.6, y + size - 0.6)
            self.set_line_width(0.25)

    def draw_footer_bar(self, page_num: int, total_pages: int = 1, unit_label: str = "College of Engineering"):
        self.set_xy(11.0, 314.0)
        self.set_font(getattr(self, "font_main", "Helvetica"), "I", 8.5)
        self.cell(145.0, 5.0, unit_label, border=0, align="L")
        self.cell(49.0, 5.0, f"Page {page_num} of {total_pages}", border=0, align="R")


# =========================================================================
# 1. FM-USeP-MID-03 Table of Specifications Generator
# =========================================================================
def generate_tos_pdf_bytes(doc: Dict[str, Any], term: str = "midterm") -> bytes:
    """Renders the official FM-USeP-MID-03 Table of Specifications PDF."""
    from tos_workflow import get_course_tos

    tos = get_course_tos(doc, term)
    course_meta = {
        "course_code": _clean_text(tos.get("course_code") or doc.get("course_code") or "EE 211"),
        "course_title": _clean_text(tos.get("course_title") or doc.get("course_title") or "Course Title"),
        "credit_units": _clean_text(tos.get("credit_units") or "3.0 Units"),
        "examination_period": _clean_text(tos.get("examination_period") or f"{term.title()} Examination"),
        "semester": _clean_text(tos.get("semester") or "1st Semester"),
        "academic_year": _clean_text(tos.get("academic_year") or "2026-2027"),
        "revision_type": str(tos.get("revision_type") or "new").lower(),
        "no_change_sem_ay": _clean_text(tos.get("no_change_sem_ay") or ""),
        "college": _clean_text(tos.get("college") or "COLLEGE OF ENGINEERING"),
        "academic_unit": _clean_text(tos.get("academic_unit") or "College of Engineering"),
        "faculty_name": _clean_text(tos.get("faculty_name") or "FACULTY"),
        "committee_chair_name": _clean_text(tos.get("committee_chair_name") or "COMMITTEE CHAIR"),
        "dean_name": _clean_text(tos.get("dean_name") or "JOIE D. CATAYTAY"),
    }

    pdf = OfficialTosBasePDF(course_meta)
    pdf.add_page()

    x0 = 11.0
    table_w = 194.0

    # 1. Header Box
    y = 14.0
    pdf.draw_controlled_header("FM-USeP-MID-03", "TABLE OF SPECIFICATIONS (TOS)", x0=x0, y=y, table_w=table_w)

    # 2. Course Details & Revision Checkboxes
    y_meta = y + 39.5 + 3.0
    pdf.set_xy(x0, y_meta)
    pdf.set_font(pdf.font_main, "B", 10.0)
    course_header_str = f"{course_meta['course_code']} - {course_meta['course_title']}"
    pdf.cell(table_w, 5.5, course_header_str, border=0, align="L")

    y_meta += 5.5
    pdf.set_xy(x0, y_meta)
    pdf.set_font(pdf.font_main, "", 9.0)
    pdf.cell(table_w, 5.0, course_meta["examination_period"], border=0, align="L")

    # Checkboxes: New / Revised / No change
    y_meta += 5.5
    pdf.set_xy(x0, y_meta)
    is_new = course_meta["revision_type"] == "new"
    is_rev = course_meta["revision_type"] == "revised"
    is_nc = course_meta["revision_type"] == "no_change"

    cb_y = y_meta + 0.8
    pdf.draw_checkbox(x0, cb_y, checked=is_new, size=3.2)
    pdf.set_xy(x0 + 4.5, y_meta)
    pdf.write(4.5, "New        ")

    pdf.draw_checkbox(pdf.get_x(), cb_y, checked=is_rev, size=3.2)
    pdf.set_x(pdf.get_x() + 4.5)
    pdf.write(4.5, "Revised        ")

    pdf.draw_checkbox(pdf.get_x(), cb_y, checked=is_nc, size=3.2)
    pdf.set_x(pdf.get_x() + 4.5)
    nc_label = f"No change, last used in {course_meta['no_change_sem_ay']}" if course_meta["no_change_sem_ay"] else "No change, last used in ______________"
    pdf.write(4.5, nc_label)

    # 3. Table of Specifications Grid
    y_grid = y_meta + 7.5
    col_w = {
        "lo": 58.0,
        "rem": 20.0,
        "und": 20.0,
        "app": 26.0,
        "eva": 26.0,
        "pts": 18.0,
        "place": 26.0,
    }

    # Header row
    pdf.set_xy(x0, y_grid)
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(col_w["lo"], 8.0, "Learning Outcomes (Topic breakdown)", border=1, align="C")
    pdf.cell(col_w["rem"], 8.0, "Remembering", border=1, align="C")
    pdf.cell(col_w["und"], 8.0, "Understanding", border=1, align="C")
    pdf.cell(col_w["app"], 8.0, "Application/Analysis", border=1, align="C")
    pdf.cell(col_w["eva"], 8.0, "Evaluation/Creation", border=1, align="C")
    pdf.cell(col_w["pts"], 8.0, "Points", border=1, align="C")
    pdf.cell(col_w["place"], 8.0, "Item Placement", border=1, align="C")

    # Rows
    y_curr = y_grid + 8.0
    rows = tos.get("rows") or []
    pdf.set_font(pdf.font_main, "", 7.5)

    for r_idx, r in enumerate(rows):
        topic_txt = _clean_text(r.get("topic") or f"Topic {r_idx + 1}")
        clo_str = _clean_text(r.get("clo") or "")
        display_text = f"{topic_txt} [{clo_str}]" if clo_str else topic_txt

        # Calculate needed height
        line_count = max(1, len(display_text) // 34 + 1)
        row_h = max(7.0, line_count * 4.2)

        if y_curr + row_h > 265.0:
            # Avoid overflowing into signatory block
            break

        pdf.set_xy(x0, y_curr)
        # Multi-cell for topic
        pdf.multi_cell(col_w["lo"], 4.0, display_text, border=1, align="L")
        actual_h = max(row_h, pdf.get_y() - y_curr)

        # Render cells with matching height
        cx = x0 + col_w["lo"]
        pdf.set_xy(cx, y_curr)
        pdf.cell(col_w["rem"], actual_h, str(r.get("remembering") or "0"), border=1, align="C")
        cx += col_w["rem"]

        pdf.set_xy(cx, y_curr)
        pdf.cell(col_w["und"], actual_h, str(r.get("understanding") or "0"), border=1, align="C")
        cx += col_w["und"]

        pdf.set_xy(cx, y_curr)
        pdf.cell(col_w["app"], actual_h, str(r.get("applying_analyzing") or "0"), border=1, align="C")
        cx += col_w["app"]

        pdf.set_xy(cx, y_curr)
        pdf.cell(col_w["eva"], actual_h, str(r.get("evaluating_creating") or "0"), border=1, align="C")
        cx += col_w["eva"]

        pdf.set_xy(cx, y_curr)
        pdf.cell(col_w["pts"], actual_h, str(r.get("total_points") or "0"), border=1, align="C")
        cx += col_w["pts"]

        pdf.set_xy(cx, y_curr)
        pdf.cell(col_w["place"], actual_h, _clean_text(r.get("item_placement") or ""), border=1, align="C")

        y_curr += actual_h

    # Totals Row
    totals = tos.get("totals") or {}
    pdf.set_xy(x0, y_curr)
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(col_w["lo"], 7.0, "TOTAL", border=1, align="C")
    pdf.cell(col_w["rem"], 7.0, str(totals.get("remembering") or 0), border=1, align="C")
    pdf.cell(col_w["und"], 7.0, str(totals.get("understanding") or 0), border=1, align="C")
    pdf.cell(col_w["app"], 7.0, str(totals.get("applying_analyzing") or 0), border=1, align="C")
    pdf.cell(col_w["eva"], 7.0, str(totals.get("evaluating_creating") or 0), border=1, align="C")
    pdf.cell(col_w["pts"], 7.0, str(totals.get("total_points") or 0), border=1, align="C")
    placement_total = f"1 - {totals.get('total_points', 0)}" if totals.get("total_points") else ""
    pdf.cell(col_w["place"], 7.0, placement_total, border=1, align="C")

    # Percentage Balance Row
    y_curr += 7.0
    pdf.set_xy(x0, y_curr)
    pdf.set_font(pdf.font_main, "I", 7.5)
    pdf.cell(col_w["lo"], 6.0, "Cognitive Domain Balance (%)", border=1, align="C")
    pdf.cell(col_w["rem"], 6.0, f"{totals.get('pct_remembering', 0)}%", border=1, align="C")
    pdf.cell(col_w["und"], 6.0, f"{totals.get('pct_understanding', 0)}%", border=1, align="C")
    pdf.cell(col_w["app"], 6.0, f"{totals.get('pct_applying_analyzing', 0)}%", border=1, align="C")
    pdf.cell(col_w["eva"], 6.0, f"{totals.get('pct_evaluating_creating', 0)}%", border=1, align="C")
    pdf.cell(col_w["pts"], 6.0, "100%", border=1, align="C")
    pdf.cell(col_w["place"], 6.0, "", border=1, align="C")

    # 4. Signatory Block (3 Columns)
    y_sig = max(y_curr + 12.0, 268.0)
    sig_w = table_w / 3.0  # ~64.6 mm each

    sigs = tos.get("signatures") or {}
    fac_sig = sigs.get("faculty") or {}
    chair_sig = sigs.get("committee_chair") or {}
    dean_sig = sigs.get("dean") or {}

    temp_files = []

    # Column 1: Prepared by (Faculty)
    pdf.set_xy(x0, y_sig)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.cell(sig_w, 4.5, "Prepared by:", align="L")

    fac_tmp = _save_data_url_image(fac_sig.get("signature_data"))
    if fac_tmp:
        temp_files.append(fac_tmp)
        try:
            pdf.image(fac_tmp, x=x0 + 8.0, y=y_sig + 4.5, w=35.0, h=14.0)
        except Exception:
            pass

    pdf.set_xy(x0, y_sig + 19.0)
    pdf.cell(sig_w - 6.0, 0.2, "", border="B")
    pdf.set_xy(x0, y_sig + 20.0)
    pdf.set_font(pdf.font_main, "B", 8.5)
    faculty_display = fac_sig.get("name") or course_meta["faculty_name"]
    pdf.cell(sig_w, 4.5, faculty_display.upper(), align="L")
    pdf.set_xy(x0, y_sig + 24.5)
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(sig_w, 4.0, "Faculty", align="L")

    # Column 2: Reviewed by (Committee Chair)
    x_chair = x0 + sig_w
    pdf.set_xy(x_chair, y_sig)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.cell(sig_w, 4.5, "Reviewed by:", align="L")

    chair_tmp = _save_data_url_image(chair_sig.get("signature_data"))
    if chair_tmp:
        temp_files.append(chair_tmp)
        try:
            pdf.image(chair_tmp, x=x_chair + 8.0, y=y_sig + 4.5, w=35.0, h=14.0)
        except Exception:
            pass

    pdf.set_xy(x_chair, y_sig + 19.0)
    pdf.cell(sig_w - 6.0, 0.2, "", border="B")
    pdf.set_xy(x_chair, y_sig + 20.0)
    pdf.set_font(pdf.font_main, "B", 8.5)
    chair_display = chair_sig.get("name") or course_meta["committee_chair_name"]
    pdf.cell(sig_w, 4.5, chair_display.upper(), align="L")
    pdf.set_xy(x_chair, y_sig + 24.5)
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(sig_w, 4.0, "Committee Chair", align="L")

    # Column 3: Approved by (Dean)
    x_dean = x0 + sig_w * 2.0
    pdf.set_xy(x_dean, y_sig)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.cell(sig_w, 4.5, "Approved by:", align="L")

    dean_tmp = _save_data_url_image(dean_sig.get("signature_data"))
    if dean_tmp:
        temp_files.append(dean_tmp)
        try:
            pdf.image(dean_tmp, x=x_dean + 8.0, y=y_sig + 4.5, w=35.0, h=14.0)
        except Exception:
            pass

    pdf.set_xy(x_dean, y_sig + 19.0)
    pdf.cell(sig_w - 6.0, 0.2, "", border="B")
    pdf.set_xy(x_dean, y_sig + 20.0)
    pdf.set_font(pdf.font_main, "B", 8.5)
    dean_display = dean_sig.get("name") or course_meta["dean_name"]
    pdf.cell(sig_w, 4.5, dean_display.upper(), align="L")
    pdf.set_xy(x_dean, y_sig + 24.5)
    pdf.set_font(pdf.font_main, "", 8.0)
    college_label = f"Dean, {course_meta['college']}"
    pdf.cell(sig_w, 4.0, college_label, align="L")

    # Footer
    pdf.draw_footer_bar(1, 1, course_meta["college"])

    # Clean up temp files
    for tf in temp_files:
        try:
            os.remove(tf)
        except Exception:
            pass

    return bytes(pdf.output())


# =========================================================================
# 2. FM-USeP-MID-04 TOS Test Review Form Generator
# =========================================================================
def generate_tos_review_form_pdf_bytes(doc: Dict[str, Any], term: str = "midterm") -> bytes:
    """Renders the official FM-USeP-MID-04 TOS Test Review Form PDF."""
    from tos_workflow import get_course_tos

    tos = get_course_tos(doc, term)
    course_meta = {
        "course_code": _clean_text(tos.get("course_code") or doc.get("course_code") or "EE 211"),
        "course_title": _clean_text(tos.get("course_title") or doc.get("course_title") or "Course Title"),
        "course_description": _clean_text(tos.get("course_description") or "Course description and fundamentals."),
        "faculty_name": _clean_text(tos.get("faculty_name") or "FACULTY"),
        "program": _clean_text(tos.get("program_name") or "ELECTRICAL ENGINEERING"),
        "academic_unit": _clean_text(tos.get("academic_unit") or "Engineering"),
        "semester": _clean_text(tos.get("semester") or "1st Semester"),
        "academic_year": _clean_text(tos.get("academic_year") or "2026-2027"),
        "dean_name": _clean_text(tos.get("dean_name") or "JOIE D. CATAYTAY"),
    }

    pdf = OfficialTosBasePDF(course_meta)
    pdf.add_page()

    x0 = 11.0
    table_w = 194.0

    # 1. Header Box
    y = 14.0
    pdf.draw_controlled_header("FM-USeP-MID-04", "TOS/TEST REVIEW FORM", x0=x0, y=y, table_w=table_w)

    # 2. Course Details Table
    y_meta = y + 39.5 + 2.0

    # Choose One: Midterm / Final Exam
    is_mid = term.lower() == "midterm"
    pdf.rect(x0, y_meta, table_w, 6.5)
    pdf.set_xy(x0 + 4.0, y_meta + 1.2)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.write(4.2, "Choose One:  ")
    cb_y = y_meta + 1.5
    pdf.draw_checkbox(pdf.get_x(), cb_y, checked=is_mid, size=3.2)
    pdf.set_x(pdf.get_x() + 4.5)
    pdf.write(4.2, "Midterm Exam        ")
    pdf.draw_checkbox(pdf.get_x(), cb_y, checked=(not is_mid), size=3.2)
    pdf.set_x(pdf.get_x() + 4.5)
    pdf.write(4.2, "Final Exam")

    # Faculty Name Row
    y_meta += 6.5
    pdf.set_xy(x0, y_meta)
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(35.0, 6.2, "Faculty Name", border=1, align="L")
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(159.0, 6.2, course_meta["faculty_name"].upper(), border=1, align="L")

    # Program | Academic Unit
    y_meta += 6.2
    pdf.set_xy(x0, y_meta)
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(35.0, 6.2, "Program", border=1, align="L")
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(75.0, 6.2, course_meta["program"].upper(), border=1, align="L")
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(30.0, 6.2, "Academic Unit", border=1, align="L")
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(54.0, 6.2, course_meta["academic_unit"].upper(), border=1, align="L")

    # Course Title
    y_meta += 6.2
    pdf.set_xy(x0, y_meta)
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(35.0, 6.2, "Course Title", border=1, align="L")
    pdf.set_font(pdf.font_main, "", 8.0)
    full_course_title = f"{course_meta['course_code']} - {course_meta['course_title']}"
    pdf.cell(159.0, 6.2, full_course_title, border=1, align="L")

    # Course Description
    y_meta += 6.2
    desc_txt = course_meta["course_description"]
    desc_lines = max(2, len(desc_txt) // 85 + 1)
    desc_h = min(22.0, max(12.0, desc_lines * 4.5))

    pdf.set_xy(x0, y_meta)
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(35.0, desc_h, "Course Description", border=1, align="L")
    pdf.set_xy(x0 + 35.0, y_meta)
    pdf.set_font(pdf.font_main, "", 7.5)
    pdf.multi_cell(159.0, 4.0, desc_txt[:350], border=1, align="L")
    pdf.set_xy(x0 + 35.0, y_meta)
    pdf.cell(159.0, desc_h, "", border=1)

    # Semester | Academic Year
    y_meta += desc_h
    pdf.set_xy(x0, y_meta)
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(35.0, 6.2, "Semester", border=1, align="L")
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(75.0, 6.2, course_meta["semester"], border=1, align="L")
    pdf.set_font(pdf.font_main, "B", 8.0)
    pdf.cell(30.0, 6.2, "Academic Year", border=1, align="L")
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(54.0, 6.2, course_meta["academic_year"], border=1, align="L")

    # 3. Comments and Suggestions Box
    y_comments = y_meta + 8.5
    pdf.set_xy(x0, y_comments)
    pdf.set_font(pdf.font_main, "B", 8.5)
    pdf.cell(table_w, 6.5, "Comments and Suggestions:", border=1, align="L")

    y_comments_box = y_comments + 6.5
    comments_h = 65.0
    pdf.rect(x0, y_comments_box, table_w, comments_h)
    rf = tos.get("review_form") or {}
    comments_str = _clean_text(rf.get("comments_suggestions") or "")

    pdf.set_xy(x0 + 4.0, y_comments_box + 3.0)
    pdf.set_font(pdf.font_main, "", 8.0)
    if comments_str:
        pdf.multi_cell(table_w - 8.0, 4.5, comments_str, border=0, align="L")

    # 4. Recommendations Checkboxes
    y_recom = y_comments_box + comments_h + 5.0
    pdf.set_xy(x0, y_recom)
    pdf.set_font(pdf.font_main, "B", 8.5)
    pdf.cell(table_w, 5.0, "Recommendations:", border=0, align="L")

    y_recom += 6.0
    rec_val = (rf.get("recommendation") or "approved_without_revision").lower()
    is_app_norev = "approved_without_revision" in rec_val or "without" in rec_val
    is_revise = "revise" in rec_val

    pdf.draw_checkbox(x0 + 4.0, y_recom + 0.6, checked=is_app_norev, size=3.2)
    pdf.set_xy(x0 + 9.0, y_recom)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.cell(table_w - 9.0, 4.5, "Approved without revision", border=0, align="L")

    y_recom += 6.0
    pdf.draw_checkbox(x0 + 4.0, y_recom + 0.6, checked=is_revise, size=3.2)
    pdf.set_xy(x0 + 9.0, y_recom)
    pdf.cell(table_w - 9.0, 4.5, "Revise as recommended before submitting to the Office of the Dean", border=0, align="L")

    # 5. Signatories Block (3 Columns)
    y_sig = max(y_recom + 14.0, 260.0)
    sig_w = table_w / 3.0
    sigs = tos.get("signatures") or {}
    comm_sigs = sigs.get("committee_members") or []
    fac_sig = sigs.get("faculty") or {}
    dean_sig = sigs.get("dean") or {}

    temp_files = []

    # Column 1: Reviewed by (Course Review Committee)
    pdf.set_xy(x0, y_sig)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.cell(sig_w, 4.5, "Reviewed by:", align="L")

    # Render up to 2 committee member signatures
    c_y = y_sig + 4.5
    for c_idx, cs in enumerate(comm_sigs[:2]):
        c_tmp = _save_data_url_image(cs.get("signature_data"))
        if c_tmp:
            temp_files.append(c_tmp)
            try:
                pdf.image(c_tmp, x=x0 + 4.0, y=c_y, w=30.0, h=10.0)
            except Exception:
                pass
        c_y += 8.0

    pdf.set_xy(x0, y_sig + 23.0)
    pdf.cell(sig_w - 6.0, 0.2, "", border="B")
    pdf.set_xy(x0, y_sig + 24.0)
    pdf.set_font(pdf.font_main, "B", 8.5)
    comm_names = ", ".join(m.get("name") for m in comm_sigs if m.get("name")) or "Course Review Committee"
    pdf.cell(sig_w, 4.5, comm_names.upper()[:30], align="L")
    pdf.set_xy(x0, y_sig + 28.5)
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(sig_w, 4.0, "Course Review Committee", align="L")

    # Column 2: Conforme (Faculty)
    x_fac = x0 + sig_w
    pdf.set_xy(x_fac, y_sig)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.cell(sig_w, 4.5, "Conforme:", align="L")

    fac_tmp = _save_data_url_image(fac_sig.get("signature_data"))
    if fac_tmp:
        temp_files.append(fac_tmp)
        try:
            pdf.image(fac_tmp, x=x_fac + 8.0, y=y_sig + 5.0, w=35.0, h=14.0)
        except Exception:
            pass

    pdf.set_xy(x_fac, y_sig + 23.0)
    pdf.cell(sig_w - 6.0, 0.2, "", border="B")
    pdf.set_xy(x_fac, y_sig + 24.0)
    pdf.set_font(pdf.font_main, "B", 8.5)
    fac_display = fac_sig.get("name") or course_meta["faculty_name"]
    pdf.cell(sig_w, 4.5, fac_display.upper(), align="L")
    pdf.set_xy(x_fac, y_sig + 28.5)
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(sig_w, 4.0, "Faculty", align="L")

    # Column 3: Approved by (Dean)
    x_dean = x0 + sig_w * 2.0
    pdf.set_xy(x_dean, y_sig)
    pdf.set_font(pdf.font_main, "", 8.5)
    pdf.cell(sig_w, 4.5, "Approved by:", align="L")

    dean_tmp = _save_data_url_image(dean_sig.get("signature_data"))
    if dean_tmp:
        temp_files.append(dean_tmp)
        try:
            pdf.image(dean_tmp, x=x_dean + 8.0, y=y_sig + 5.0, w=35.0, h=14.0)
        except Exception:
            pass

    pdf.set_xy(x_dean, y_sig + 23.0)
    pdf.cell(sig_w - 6.0, 0.2, "", border="B")
    pdf.set_xy(x_dean, y_sig + 24.0)
    pdf.set_font(pdf.font_main, "B", 8.5)
    dean_display = dean_sig.get("name") or course_meta["dean_name"]
    pdf.cell(sig_w, 4.5, dean_display.upper(), align="L")
    pdf.set_xy(x_dean, y_sig + 28.5)
    pdf.set_font(pdf.font_main, "", 8.0)
    pdf.cell(sig_w, 4.0, "Dean", align="L")

    # Footer
    pdf.draw_footer_bar(1, 1, course_meta["academic_unit"])

    for tf in temp_files:
        try:
            os.remove(tf)
        except Exception:
            pass

    return bytes(pdf.output())
