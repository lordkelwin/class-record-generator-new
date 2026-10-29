"""
Official University of Southeastern Philippines (USeP)
Course Learning Outcome Evaluation Result Excel Generator (FM-USeP-MID-10).

Strictly conforms to 'FM-USeP-MID-10 Course Learning Outcome Evaluation Result.xlsx'.
Features:
  - Official Document Control Box (FM-USeP-MID-10, Issue 01, Rev 00, Date Effective, Approved by President)
  - Embedded USeP seal logo
  - University address block
  - Basic details retrieved automatically from syllabus creation / metadata
  - Table 1: Course Assessment Plan (As declared in the Syllabus) with gold OBTL styling
  - Table 2: Course Learning Outcome Evaluation Result (Based on Class Record) with green styling
  - Excel weighted average formula (=C27*(20/70) + C29*(50/70))
  - Signatory block (Prepared by Faculty, Reviewed and Noted by Program Head)
  - Actions Needed block
  - Dynamic table height & text wrap optimization to maximize space and avoid wastage
"""

import io
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from models import SyllabusBlueprint
from clo_report_pdf_generator import (
    _compute_clo_report_metrics,
    _format_program_short,
    _format_units_short,
    _short_sa_component_label,
    DEFAULT_ASSESSMENT_PLAN_CELL_TEXT,
)


THIN_BORDER_SIDE = Side(style="thin", color="000000")
THIN_BOX_BORDER = Border(
    left=THIN_BORDER_SIDE,
    right=THIN_BORDER_SIDE,
    top=THIN_BORDER_SIDE,
    bottom=THIN_BORDER_SIDE,
)

FILL_WHITE = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
FILL_CAP_HDR_DARK = PatternFill(start_color="F1C232", end_color="F1C232", fill_type="solid")  # Gold dark
FILL_CAP_HDR_LIGHT = PatternFill(start_color="FFD966", end_color="FFD966", fill_type="solid")  # Gold light
FILL_CAP_DATA = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")  # Cream

FILL_EVAL_HDR_DARK = PatternFill(start_color="6AA84F", end_color="6AA84F", fill_type="solid")  # Green dark
FILL_EVAL_HDR_LIGHT = PatternFill(start_color="93C47D", end_color="93C47D", fill_type="solid")  # Green light
FILL_EVAL_DATA = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")  # Light green


def _apply_box_border(ws: Any, min_col: int, min_row: int, max_col: int, max_row: int, fill: Optional[PatternFill] = None) -> None:
    """Applies thin border around and inside a cell range, with optional fill."""
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = THIN_BOX_BORDER
            if fill is not None:
                cell.fill = fill


def _estimate_text_lines(text: str, col_chars: int = 16) -> int:
    """Estimates the line count required for text wrapped at approximately col_chars."""
    if not text:
        return 1
    total_lines = 0
    for para in str(text).split("\n"):
        para = para.strip()
        if not para:
            continue
        words = para.split()
        cur_len = 0
        p_lines = 1
        for w in words:
            w_len = len(w)
            if cur_len + w_len + (1 if cur_len > 0 else 0) <= col_chars:
                cur_len += w_len + (1 if cur_len > 0 else 0)
            else:
                p_lines += 1
                cur_len = w_len
        total_lines += p_lines
    return max(1, total_lines)


def generate_clo_evaluation_excel_bytes(
    blueprint: SyllabusBlueprint,
    doc: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generates the official FM-USeP-MID-10 Course Learning Outcome Evaluation Result
    Excel spreadsheet matching the controlled sample file.
    """
    meta = blueprint.metadata
    doc = doc or {}
    outcomes = blueprint.course_outcomes or []
    sa_rows, overall_weighted = _compute_clo_report_metrics(blueprint)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.views.sheetView[0].showGridLines = True

    # 1. Base Column Widths (Optimized layout matching sample)
    col_widths = {
        "A": 18.88,
        "B": 13.13,
        "C": 15.25,
        "D": 16.13,
        "E": 15.88,
        "F": 17.25,
        "G": 18.63,
    }
    # Ensure all CLO columns have adequate width if there are more than 5 CLOs
    n_clos = max(5, len(outcomes))
    for c_i in range(1, 3 + n_clos):
        let = get_column_letter(c_i)
        if let in col_widths:
            ws.column_dimensions[let].width = col_widths[let]
        else:
            ws.column_dimensions[let].width = 16.5

    last_col_idx = max(7, 2 + len(outcomes))
    last_col_let = get_column_letter(last_col_idx)

    # 2. Header: Logo (A2:A6), Address (B2:E6), Document Control Box (F2:G6)
    ws.row_dimensions[1].height = 15.75
    for r in range(2, 7):
        ws.row_dimensions[r].height = 18.75

    # A2:A6 Merged for Logo Image
    ws.merge_cells("A2:A6")
    _apply_box_border(ws, 1, 2, 1, 6)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "static", "image1.jpg")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(base_dir, "static", "logo_1_Image39.jpg")
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path)
            img.width = 105
            img.height = 105
            ws.add_image(img, "A2")
        except Exception:
            pass

    # B2:E6 Address Block
    ws.merge_cells("B2:E6")
    _apply_box_border(ws, 2, 2, 5, 6)
    cell_b2 = ws["B2"]
    cell_b2.value = (
        "Republic of the Philippines\n"
        "University of Southeastern Philippines \n"
        "Iñigo St., Bo. Obrero, Davao City 8000\n"
        "Telephone: (082) 227-8192\n"
        "Website: www.usep.edu.ph\n"
        "Email: president@usep.edu.ph"
    )
    cell_b2.font = Font(name="Arial", size=9, bold=False, color="000000")
    cell_b2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # F2:G6 Document Control Box
    doc_ctrl_data = [
        ("Form No.", "FM-USeP-MID-10"),
        ("Issue Status", "01"),
        ("Revision No.", "00"),
        ("Date Effective", "18 August 2026"),
        ("Approved by", "President"),
    ]
    for idx, (label, val) in enumerate(doc_ctrl_data):
        r = 2 + idx
        c_f = ws.cell(row=r, column=6, value=label)
        c_g = ws.cell(row=r, column=7, value=val)
        c_f.font = Font(name="Arial", size=9, bold=False, color="000000")
        c_g.font = Font(name="Arial", size=9, bold=False, color="000000")
        c_f.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        c_g.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        c_f.border = THIN_BOX_BORDER
        c_g.border = THIN_BOX_BORDER

    # Row 7: Document Title (A7:G7 merged)
    ws.row_dimensions[7].height = 30.0
    ws.merge_cells(f"A7:{last_col_let}7")
    _apply_box_border(ws, 1, 7, last_col_idx, 7)
    cell_title = ws["A7"]
    cell_title.value = "COURSE LEARNING OUTCOME EVALUATION RESULT"
    cell_title.font = Font(name="Arial", size=14, bold=True, color="000000")
    cell_title.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Row 8: Blank spacer
    ws.row_dimensions[8].height = 15.75

    # 3. Rows 9 to 13: Basic Details (Retrieved from Syllabus Creation)
    faculty_name = (doc.get("faculty_name") or meta.faculty_name or "").strip()
    if faculty_name.isupper():
        faculty_name = faculty_name.title()

    course_code = (doc.get("course_code") or meta.course_code or "").strip()
    course_title = (doc.get("course_title") or meta.course_title or "").strip()
    # Clean course title if course code is redundantly prefixed
    if course_code and course_title.upper().startswith(course_code.upper()):
        course_title = re.sub(r"^" + re.escape(course_code) + r"\s*[-–:]?\s*", "", course_title, flags=re.I).strip()

    course_desc = (doc.get("course_description") or meta.course_description or "").strip()
    credit_units_raw = doc.get("credit_units") or meta.credit_units or "3 Units"
    units_short = _format_units_short(credit_units_raw)

    if course_desc:
        course_full_info = f"{course_code} - {course_title}, {course_desc} ({units_short})"
    else:
        course_full_info = f"{course_code} - {course_title} ({units_short})"

    semester_ay = (doc.get("semester_ay") or meta.semester_ay or "").strip()
    program_str = (doc.get("program_name") or meta.program_name or doc.get("department") or meta.department or "").strip()
    academic_unit_str = (doc.get("academic_unit") or meta.academic_unit or doc.get("college") or meta.college or "Engineering").strip()

    meta_items = [
        ("Name of Faculty:", faculty_name),
        ("Course Title, Description and Units:", course_full_info),
        ("Semester and Academic Year:", semester_ay),
        ("Program:", program_str),
        ("Academic Unit:", academic_unit_str),
    ]

    for idx, (lbl, val_str) in enumerate(meta_items):
        r_num = 9 + idx
        ws.merge_cells(f"A{r_num}:B{r_num}")
        ws.merge_cells(f"C{r_num}:{last_col_let}{r_num}")
        _apply_box_border(ws, 1, r_num, last_col_idx, r_num, fill=FILL_WHITE)

        c_lbl = ws.cell(row=r_num, column=1, value=lbl)
        c_lbl.font = Font(name="Arial", size=10, bold=True, color="000000")
        c_lbl.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        c_val = ws.cell(row=r_num, column=3, value=val_str)
        c_val.font = Font(name="Arial", size=10, bold=False, color="000000")
        c_val.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # Dynamic space optimization for Basic Details
        if idx == 1:  # Course Title, Description and Units may wrap
            est_lines = _estimate_text_lines(val_str, col_chars=75)
            ws.row_dimensions[r_num].height = max(19.5, est_lines * 14.5 + 5.0)
        else:
            ws.row_dimensions[r_num].height = 19.5

    # Row 14: Blank spacer
    ws.row_dimensions[14].height = 15.75

    # 4. TABLE 1: COURSE ASSESSMENT PLAN (As declared in the Syllabus)
    cap_title_row = 15
    ws.row_dimensions[cap_title_row].height = 18.0
    ws.merge_cells(f"A{cap_title_row}:{last_col_let}{cap_title_row}")
    _apply_box_border(ws, 1, cap_title_row, last_col_idx, cap_title_row)
    cell_cap_title = ws[f"A{cap_title_row}"]
    cell_cap_title.value = "COURSE ASSESSMENT PLAN (As declared in the Syllabus)"
    cell_cap_title.font = Font(name="Arial", size=10, bold=True, color="000000")
    cell_cap_title.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Table 1 Header Rows (16 & 17)
    ws.row_dimensions[16].height = 16.5
    ws.row_dimensions[17].height = 16.5
    ws.merge_cells("A16:B17")
    _apply_box_border(ws, 1, 16, 2, 17, fill=FILL_CAP_HDR_LIGHT)
    c_cap_h1 = ws["A16"]
    c_cap_h1.value = "Assessment Component"
    c_cap_h1.font = Font(name="Arial", size=10, bold=True, color="000000")
    c_cap_h1.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.merge_cells(f"C16:{last_col_let}16")
    _apply_box_border(ws, 3, 16, last_col_idx, 16, fill=FILL_CAP_HDR_DARK)
    c_cap_h2 = ws["C16"]
    c_cap_h2.value = "Course Assessment Plan"
    c_cap_h2.font = Font(name="Arial", size=10, bold=True, color="000000")
    c_cap_h2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Subheaders for CLOs
    for c_i, co in enumerate(outcomes):
        col_num = 3 + c_i
        cell_clo = ws.cell(row=17, column=col_num, value=co.co_id.upper())
        cell_clo.font = Font(name="Arial", size=10, bold=True, color="000000")
        cell_clo.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell_clo.fill = FILL_CAP_HDR_LIGHT
        cell_clo.border = THIN_BOX_BORDER

    # Fill remaining columns if outcomes < 5
    if len(outcomes) < 5:
        for extra_i in range(len(outcomes), 5):
            col_num = 3 + extra_i
            cell_clo = ws.cell(row=17, column=col_num, value=f"CLO{extra_i+1}")
            cell_clo.font = Font(name="Arial", size=10, bold=True, color="000000")
            cell_clo.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell_clo.fill = FILL_CAP_HDR_LIGHT
            cell_clo.border = THIN_BOX_BORDER

    # Table 1 Data Rows (Cream Fill, Optimized Row Heights)
    cap_data = meta.course_assessment_plan if getattr(meta, "course_assessment_plan", None) else []
    if cap_data:
        plan_rows = [
            {
                "label": r.get("component_name") or r.get("code") or "Summative Assessment",
                "clo_plans": r.get("clo_plans") or {},
                "weight_pct": float(r.get("weight_pct") or 0.0),
                "custom_h": float(r.get("block_height") or 0.0) if r.get("block_height") else None,
            }
            for r in cap_data
            if not str(r.get("code") or "").upper().startswith("FA")
        ]
    else:
        plan_rows = [
            {
                "label": sa_r["label"],
                "clo_plans": {
                    co.co_id: (DEFAULT_ASSESSMENT_PLAN_CELL_TEXT if sa_r["clo_aligned"].get(co.co_id, True) else "")
                    for co in outcomes
                },
                "weight_pct": sa_r["weight_pct"],
                "custom_h": None,
            }
            for sa_r in sa_rows
        ]

    cur_row = 18
    table1_start_row = cur_row
    for pr in plan_rows:
        ws.merge_cells(f"A{cur_row}:B{cur_row}")
        _apply_box_border(ws, 1, cur_row, last_col_idx, cur_row, fill=FILL_CAP_DATA)

        c_comp = ws.cell(row=cur_row, column=1, value=pr["label"])
        c_comp.font = Font(name="Arial", size=10, bold=True, color="000000")
        c_comp.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        max_lines_in_row = _estimate_text_lines(pr["label"], col_chars=30)
        for c_i, co in enumerate(outcomes):
            col_num = 3 + c_i
            raw_text = pr["clo_plans"].get(co.co_id, "")
            if str(raw_text).strip().upper() == "N/A":
                cell_text = ""
            else:
                cell_text = str(raw_text).strip()

            c_plan = ws.cell(row=cur_row, column=col_num, value=cell_text or None)
            c_plan.font = Font(name="Arial", size=9.5, bold=False, color="000000")
            c_plan.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            if cell_text:
                n_l = _estimate_text_lines(cell_text, col_chars=16)
                if n_l > max_lines_in_row:
                    max_lines_in_row = n_l

        # Dynamic space optimization: row height strictly conforms to lines of text
        computed_h = max(22.0, max_lines_in_row * 13.0 + 6.0)
        if pr.get("custom_h") and pr["custom_h"] > 20:
            ws.row_dimensions[cur_row].height = min(pr["custom_h"], computed_h * 1.3)
        else:
            ws.row_dimensions[cur_row].height = computed_h

        cur_row += 1

    table1_end_row = cur_row - 1

    # Spacer between Table 1 and Table 2
    ws.row_dimensions[cur_row].height = 15.75
    cur_row += 1

    # 5. TABLE 2: COURSE LEARNING OUTCOME EVALUATION RESULT (Based on Class Record)
    eval_title_row = cur_row
    ws.row_dimensions[eval_title_row].height = 18.0
    ws.merge_cells(f"A{eval_title_row}:{last_col_let}{eval_title_row}")
    _apply_box_border(ws, 1, eval_title_row, last_col_idx, eval_title_row)
    c_eval_title = ws[f"A{eval_title_row}"]
    c_eval_title.value = "COURSE LEARNING OUTCOME EVALUATION RESULT (Based on Class Record)"
    c_eval_title.font = Font(name="Arial", size=10, bold=True, color="000000")
    c_eval_title.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    cur_row += 1
    # Table 2 Header Rows (Green)
    eval_h1_row = cur_row
    eval_h2_row = cur_row + 1
    ws.row_dimensions[eval_h1_row].height = 16.5
    ws.row_dimensions[eval_h2_row].height = 16.5

    ws.merge_cells(f"A{eval_h1_row}:B{eval_h2_row}")
    _apply_box_border(ws, 1, eval_h1_row, 2, eval_h2_row, fill=FILL_EVAL_HDR_LIGHT)
    c_ev_h1 = ws[f"A{eval_h1_row}"]
    c_ev_h1.value = "Assessment Component"
    c_ev_h1.font = Font(name="Arial", size=10, bold=True, color="000000")
    c_ev_h1.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.merge_cells(f"C{eval_h1_row}:{last_col_let}{eval_h1_row}")
    _apply_box_border(ws, 3, eval_h1_row, last_col_idx, eval_h1_row, fill=FILL_EVAL_HDR_DARK)
    c_ev_h2 = ws[f"C{eval_h1_row}"]
    c_ev_h2.value = "Course Assessment Plan"
    c_ev_h2.font = Font(name="Arial", size=10, bold=True, color="000000")
    c_ev_h2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Subheaders for CLOs
    for c_i, co in enumerate(outcomes):
        col_num = 3 + c_i
        cell_clo = ws.cell(row=eval_h2_row, column=col_num, value=co.co_id.upper())
        cell_clo.font = Font(name="Arial", size=10, bold=True, color="000000")
        cell_clo.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell_clo.fill = FILL_EVAL_HDR_LIGHT
        cell_clo.border = THIN_BOX_BORDER

    if len(outcomes) < 5:
        for extra_i in range(len(outcomes), 5):
            col_num = 3 + extra_i
            cell_clo = ws.cell(row=eval_h2_row, column=col_num, value=f"CLO{extra_i+1}")
            cell_clo.font = Font(name="Arial", size=10, bold=True, color="000000")
            cell_clo.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell_clo.fill = FILL_EVAL_HDR_LIGHT
            cell_clo.border = THIN_BOX_BORDER

    cur_row += 2
    table2_start_row = cur_row

    # Table 2 Data Rows (Attainment % formatted as 0%)
    # Keep track of row index and weights for dynamic weighted average formula
    clo_aligned_rows: Dict[str, List[Tuple[int, float]]] = {co.co_id: [] for co in outcomes}

    for idx, sa_r in enumerate(sa_rows):
        ws.merge_cells(f"A{cur_row}:B{cur_row}")
        _apply_box_border(ws, 1, cur_row, last_col_idx, cur_row, fill=FILL_EVAL_DATA)
        ws.row_dimensions[cur_row].height = 24.0

        c_comp = ws.cell(row=cur_row, column=1, value=sa_r["label"])
        c_comp.font = Font(name="Arial", size=10, bold=True, color="000000")
        c_comp.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        sa_wt = float(sa_r.get("weight_pct") or 0.0)

        for c_i, co in enumerate(outcomes):
            col_num = 3 + c_i
            is_aligned = sa_r["clo_aligned"].get(co.co_id, False)
            if is_aligned:
                pass_pct = sa_r["clo_pass_pcts"].get(co.co_id, 0.0)
                # In Excel, 0.8 formatted with number_format="0%" renders as 80%
                decimal_val = round(pass_pct / 100.0, 4)
                c_val = ws.cell(row=cur_row, column=col_num, value=decimal_val)
                c_val.number_format = "0%"
                clo_aligned_rows[co.co_id].append((cur_row, sa_wt))
            else:
                c_val = ws.cell(row=cur_row, column=col_num, value=None)

            c_val.font = Font(name="Arial", size=10, bold=False, color="000000")
            c_val.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        cur_row += 1

    # Overall (Weighted Average %) Row
    overall_row = cur_row
    ws.row_dimensions[overall_row].height = 25.5
    ws.merge_cells(f"A{overall_row}:B{overall_row}")
    _apply_box_border(ws, 1, overall_row, last_col_idx, overall_row, fill=FILL_EVAL_DATA)

    c_ov_lbl = ws.cell(row=overall_row, column=1, value="Overall (Weighted Average %)")
    c_ov_lbl.font = Font(name="Arial", size=10, bold=True, color="000000")
    c_ov_lbl.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # Build dynamic weighted average formula for each CLO column
    # e.g.: =C27*(20/70) + C29*(50/70)
    for c_i, co in enumerate(outcomes):
        col_num = 3 + c_i
        col_let = get_column_letter(col_num)
        aligned_items = clo_aligned_rows.get(co.co_id, [])

        total_applicable_weight = sum(w for _, w in aligned_items)
        if total_applicable_weight > 0 and aligned_items:
            # Build formula
            tot_w_str = f"{int(total_applicable_weight)}" if abs(total_applicable_weight - round(total_applicable_weight)) < 1e-4 else f"{total_applicable_weight:.2f}"
            parts = []
            for r_num, w_val in aligned_items:
                w_str = f"{int(w_val)}" if abs(w_val - round(w_val)) < 1e-4 else f"{w_val:.2f}"
                parts.append(f"{col_let}{r_num}*({w_str}/{tot_w_str})")
            formula_str = "=" + " + ".join(parts)
        else:
            formula_str = "0.00%"

        c_ov_val = ws.cell(row=overall_row, column=col_num, value=formula_str)
        c_ov_val.font = Font(name="Arial", size=10, bold=True, color="000000")
        c_ov_val.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c_ov_val.number_format = "0.00%"

    cur_row += 1

    # 6. Row Note: Exact USeP weighted average formula note
    note_row = cur_row
    ws.row_dimensions[note_row].height = 28.5
    ws.merge_cells(f"A{note_row}:{last_col_let}{note_row}")
    _apply_box_border(ws, 1, note_row, last_col_idx, note_row, fill=FILL_WHITE)
    c_note = ws.cell(row=note_row, column=1)
    c_note.value = (
        "Note: Weighted Average is computed as Summation of Score x (weight/total applicable weights). "
        "An overall rating of below 50% indicates non-attainment of the course outcome and adjustment in "
        "the TLAs and assessment activities may be required. Submit this together with the Class Record."
    )
    c_note.font = Font(name="Arial", size=9, bold=False, color="000000")
    c_note.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    cur_row += 1
    # Spacer
    ws.row_dimensions[cur_row].height = 14.0
    cur_row += 1

    # 7. Signatories Block (Rows 33 to 37 style)
    # Left box (Faculty) in A:B, Right box (Program Head) in D:G
    sig_r1 = cur_row
    sig_r2 = cur_row + 1
    sig_r3 = cur_row + 2
    sig_r4 = cur_row + 3
    sig_r5 = cur_row + 4

    ws.row_dimensions[sig_r1].height = 16.0
    ws.row_dimensions[sig_r2].height = 14.0
    ws.row_dimensions[sig_r3].height = 18.0
    ws.row_dimensions[sig_r4].height = 16.0
    ws.row_dimensions[sig_r5].height = 20.0

    # Prepared by:
    ws.merge_cells(f"A{sig_r1}:B{sig_r1}")
    ws.merge_cells(f"D{sig_r1}:{last_col_let}{sig_r1}")
    _apply_box_border(ws, 1, sig_r1, 2, sig_r5, fill=FILL_WHITE)
    _apply_box_border(ws, 4, sig_r1, last_col_idx, sig_r5, fill=FILL_WHITE)

    c_sig_p = ws.cell(row=sig_r1, column=1, value="Prepared by:")
    c_sig_p.font = Font(name="Arial", size=10, bold=False, color="000000")
    c_sig_p.alignment = Alignment(horizontal="left", vertical="center")

    c_sig_r = ws.cell(row=sig_r1, column=4, value="Reviewed and Noted by:")
    c_sig_r.font = Font(name="Arial", size=10, bold=False, color="000000")
    c_sig_r.alignment = Alignment(horizontal="left", vertical="center")

    # Faculty Name & Program Head Name
    faculty_sig_name = faculty_name.upper() if faculty_name else "FACULTY NAME"
    prog_head_name = (doc.get("program_head") or meta.program_head or "PROGRAM HEAD").strip().upper()

    ws.merge_cells(f"A{sig_r3}:B{sig_r3}")
    ws.merge_cells(f"D{sig_r3}:{last_col_let}{sig_r3}")
    c_fn = ws.cell(row=sig_r3, column=1, value=faculty_sig_name)
    c_fn.font = Font(name="Arial", size=10, bold=True, color="000000")
    c_fn.alignment = Alignment(horizontal="center", vertical="center")

    c_ph = ws.cell(row=sig_r3, column=4, value=prog_head_name)
    c_ph.font = Font(name="Arial", size=10, bold=True, color="000000")
    c_ph.alignment = Alignment(horizontal="center", vertical="center")

    # Title: "Faculty" and "Program Head"
    ws.merge_cells(f"A{sig_r4}:B{sig_r4}")
    ws.merge_cells(f"D{sig_r4}:{last_col_let}{sig_r4}")
    c_ft = ws.cell(row=sig_r4, column=1, value="Faculty")
    c_ft.font = Font(name="Arial", size=10, bold=False, color="000000")
    c_ft.alignment = Alignment(horizontal="center", vertical="center")

    c_pt = ws.cell(row=sig_r4, column=4, value="Program Head")
    c_pt.font = Font(name="Arial", size=10, bold=False, color="000000")
    c_pt.alignment = Alignment(horizontal="center", vertical="center")

    # Date
    now = datetime.now()
    date_display = f"Date: {now.strftime('%B %d, %Y')}"
    ws.merge_cells(f"A{sig_r5}:B{sig_r5}")
    ws.merge_cells(f"D{sig_r5}:{last_col_let}{sig_r5}")
    c_fd = ws.cell(row=sig_r5, column=1, value=date_display)
    c_fd.font = Font(name="Arial", size=10, bold=False, color="000000")
    c_fd.alignment = Alignment(horizontal="left", vertical="center")

    c_pd = ws.cell(row=sig_r5, column=4, value=date_display)
    c_pd.font = Font(name="Arial", size=10, bold=False, color="000000")
    c_pd.alignment = Alignment(horizontal="left", vertical="center")

    cur_row = sig_r5 + 1
    # Spacer
    ws.row_dimensions[cur_row].height = 10.0
    cur_row += 1

    # 8. Actions Needed Boxes (Optimized height ~ 70pt)
    act_row = cur_row
    ws.row_dimensions[act_row].height = 70.0

    # Left: A to C
    ws.merge_cells(f"A{act_row}:C{act_row}")
    _apply_box_border(ws, 1, act_row, 3, act_row, fill=FILL_WHITE)
    c_act1 = ws.cell(row=act_row, column=1, value="Actions Needed:")
    c_act1.font = Font(name="Arial", size=9.5, bold=False, color="000000")
    c_act1.alignment = Alignment(horizontal="left", vertical="top")

    # Right: D to last column
    ws.merge_cells(f"D{act_row}:{last_col_let}{act_row}")
    _apply_box_border(ws, 4, act_row, last_col_idx, act_row, fill=FILL_WHITE)
    c_act2 = ws.cell(row=act_row, column=4, value="Actions Needed:")
    c_act2.font = Font(name="Arial", size=9.5, bold=False, color="000000")
    c_act2.alignment = Alignment(horizontal="left", vertical="top")

    # 9. Page Setup: Fit to 1 Page Wide, Portrait, A4
    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins.left = 0.5
    ws.page_margins.right = 0.5
    ws.page_margins.top = 0.6
    ws.page_margins.bottom = 0.6

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
