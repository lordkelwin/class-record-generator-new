"""
Generates the official University of Southeastern Philippines (USeP)
Course Learning Outcome (CLO) Assessment Report PDF, matching the exact layout,
colors, typography, tables, and signatory blocks of 'AEE 321_EE 3A_CLO Report.pdf'.
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Tuple
from fpdf import FPDF

from models import SyllabusBlueprint, AssessmentItem
from excel_generator import _get_item_clo_points, _get_student_clo_score


def _clean_pdf_text(val: str) -> str:
    """Sanitizes text to Latin-1 safe characters for standard PDF core fonts."""
    if val is None:
        return ""
    s = str(val)
    replacements = {
        "\u2013": "-",
        "\u2014": "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u25cf": "*",
        "\u2713": "[/]",
        "\u2714": "[/]",
        "\u2717": "[x]",
        "\u2718": "[x]",
        "\u2192": "->",
        "\u2265": ">=",
        "\u2264": "<=",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def _short_sa_component_label(cat_name: str, sa_code: str, weight_pct: float) -> str:
    """
    Formats Summative Assessment component label to match 'AEE 321_EE 3A_CLO Report.pdf':
      - 'Summative Assessment 1 (Quizzes)' (40%) -> 'Quiz (40%)'
      - 'Summative Assessment 2 (Term Examination)' (60%) -> 'Exam (60%)'
    """
    low = (cat_name or "").lower()
    wt_str = f"{weight_pct:.0f}%"
    if "quiz" in low:
        return f"Quiz ({wt_str})"
    if "exam" in low:
        return f"Exam ({wt_str})"
    # Extract parenthetical label if present
    m_par = re.search(r"\(([^)]+)\)", cat_name or "")
    if m_par:
        inner = m_par.group(1).strip()
        if inner.lower() == "quizzes":
            inner = "Quiz"
        elif "examination" in inner.lower():
            inner = "Exam"
        return f"{inner} ({wt_str})"
    clean_name = re.sub(r"^Summative\s+Assessment\s*\d*\s*[-:]?\s*", "", cat_name or sa_code, flags=re.I).strip()
    return f"{clean_name or sa_code} ({wt_str})"


def _format_units_short(credit_units: str) -> str:
    """Formats '3.0 Units – Lecture' -> '3 Units' or '2.0 Units' -> '2 Units'."""
    raw = str(credit_units or "3 Units").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*Unit", raw, re.I)
    if m:
        val = float(m.group(1))
        val_str = f"{int(val)}" if abs(val - round(val)) < 1e-6 else f"{val:.1f}"
        return f"{val_str} Units" if val != 1 else "1 Unit"
    return raw


def _format_program_short(program_name: str, department: str, program_code: str) -> str:
    """Formats 'Bachelor of Science in Electrical Engineering' -> 'Electrical Engineering'."""
    pname = str(program_name or "").strip()
    if "," in pname:
        parts = [re.sub(r"^Bachelor\s+of\s+Science\s+in\s+", "", p.strip(), flags=re.I).strip() for p in pname.split(",") if p.strip()]
        if parts:
            return ", ".join(parts)
    cleaned = re.sub(r"^Bachelor\s+of\s+Science\s+in\s+", "", pname, flags=re.I).strip()
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    if cleaned:
        return cleaned
    dept_clean = re.sub(r"^Department\s+of\s+", "", str(department or ""), flags=re.I).strip()
    return dept_clean or program_code or "Engineering"


DEFAULT_ASSESSMENT_PLAN_CELL_TEXT = (
    "Objective / Concept-type\n"
    "Items Score / Problem Solving\n"
    "Items Score (with Rubric in\n"
    "Problem Solving) / Short\n"
    "Essay Items Score (with\n"
    "Rubric in Short Essay)"
)


def _compute_clo_report_metrics(blueprint: SyllabusBlueprint) -> Tuple[List[Dict], Dict[str, float]]:
    """
    Computes the per-SA CLO achievement percentages and Overall Weighted Average (%)
    using the exact separated per-CLO student scores and weights from the Class Record.
    """
    outcomes = blueprint.course_outcomes or []
    students = blueprint.students or []
    n_students = max(1, len(students))

    # Expand all SA items into separated per-CLO score columns
    all_sa_clo_cols: List[Dict] = []
    sa_codes_ordered: List[str] = []
    sa_code_names: Dict[str, str] = {}
    sa_code_weights: Dict[str, float] = {}

    for cat in blueprint.categories:
        a_type = (cat.assessment_type or "SA").upper()
        if a_type != "SA":
            continue
        a_code = (cat.assessment_code or "SA1").upper()
        if a_code not in sa_codes_ordered:
            sa_codes_ordered.append(a_code)
            sa_code_names[a_code] = cat.name
            sa_code_weights[a_code] = float(cat.weight_pct or 0.0)

        n_items = max(1, len(cat.items))
        def_wt = float(cat.weight_pct or 0.0) / n_items
        for it in cat.items:
            it_wt = float(it.weight_pct) if float(it.weight_pct or 0.0) > 0 else def_wt
            clo_pairs = _get_item_clo_points(it)
            total_it_pts = sum(pts for _, pts in clo_pairs) or float(it.max_score or 30.0)
            n_clos = max(1, len(clo_pairs))
            for clo_id, clo_pts in clo_pairs:
                col_wt = round(it_wt * (clo_pts / total_it_pts), 4) if total_it_pts > 0 else round(it_wt / n_clos, 4)
                all_sa_clo_cols.append({
                    "term": cat.term,
                    "assessment_code": a_code,
                    "item": it,
                    "clo_id": clo_id.upper(),
                    "clo_pts": float(clo_pts),
                    "total_it_pts": float(total_it_pts),
                    "col_wt": col_wt,
                })

    sa_rows: List[Dict] = []
    overall_weighted: Dict[str, float] = {co.co_id: 0.0 for co in outcomes}
    weight_sums: Dict[str, float] = {co.co_id: 0.0 for co in outcomes}

    for sa_code in sa_codes_ordered:
        sa_wt = sa_code_weights.get(sa_code, 0.0)
        cat_name = sa_code_names.get(sa_code, sa_code)
        label = _short_sa_component_label(cat_name, sa_code, sa_wt)

        clo_pass_pcts: Dict[str, float] = {}
        clo_aligned_flags: Dict[str, bool] = {}

        for co in outcomes:
            co_key = co.co_id.upper()
            matching_cols = [
                col for col in all_sa_clo_cols
                if col["assessment_code"] == sa_code and col["clo_id"] == co_key
            ]
            if not matching_cols:
                clo_aligned_flags[co.co_id] = False
                clo_pass_pcts[co.co_id] = 0.0
                continue

            clo_aligned_flags[co.co_id] = True
            deg_cutoff = float(co.target_score_pct or 75.0)
            if deg_cutoff <= 1.0:
                deg_cutoff *= 100.0

            pass_cnt = 0
            sum_wt = sum(c["col_wt"] for c in matching_cols)
            for st in students:
                num = 0.0
                for c in matching_cols:
                    raw_sc = _get_student_clo_score(st, c["item"], c["clo_id"], c["clo_pts"], c["total_it_pts"])
                    sc_val = float(raw_sc) if raw_sc != "" and raw_sc is not None else 0.0
                    max_p = c["clo_pts"] if c["clo_pts"] > 0 else 1.0
                    num += sc_val * c["col_wt"] / max_p
                base50_grade = (num / sum_wt) * 50.0 + 50.0 if sum_wt > 0 else 50.0
                if base50_grade >= deg_cutoff:
                    pass_cnt += 1

            pct_val = (pass_cnt / n_students) * 100.0 if students else 0.0
            clo_pass_pcts[co.co_id] = pct_val
            w_dec = sa_wt / 100.0
            overall_weighted[co.co_id] += pct_val * w_dec
            weight_sums[co.co_id] += w_dec

        sa_rows.append({
            "sa_code": sa_code,
            "label": label,
            "weight_pct": sa_wt,
            "clo_aligned": clo_aligned_flags,
            "clo_pass_pcts": clo_pass_pcts,
        })

    for co in outcomes:
        w_tot = weight_sums.get(co.co_id, 0.0)
        if w_tot > 0:
            overall_weighted[co.co_id] = overall_weighted[co.co_id] / w_tot
        else:
            overall_weighted[co.co_id] = 0.0

    return sa_rows, overall_weighted


def generate_clo_report_pdf_bytes(blueprint: SyllabusBlueprint) -> bytes:
    """
    Generates the USeP Course Learning Outcome Assessment Report PDF
    matching 'AEE 321_EE 3A_CLO Report.pdf'.
    """
    meta = blueprint.metadata
    outcomes = blueprint.course_outcomes or []
    sa_rows, overall_weighted = _compute_clo_report_metrics(blueprint)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14.0)
    pdf.set_margins(left=18.0, top=14.0, right=18.0)
    pdf.add_page()

    page_w = 210.0
    left_m = 18.0
    usable_w = page_w - 2 * left_m  # 174.0 mm

    # 1. Centered USeP Seal & University Name Header
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "static", "logo_1_Image39.jpg")
    if os.path.exists(logo_path):
        try:
            logo_w = 26.0
            pdf.image(logo_path, x=(page_w - logo_w) / 2.0, y=13.0, w=logo_w, h=logo_w)
            pdf.set_y(41.0)
        except Exception:
            pdf.set_y(18.0)
    else:
        pdf.set_y(18.0)

    pdf.set_font("Times", "B", 13.5)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(usable_w, 6.5, _clean_pdf_text(meta.university.upper()), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4.5)

    # 2. Metadata Block (5 rows: unbordered bold label on left, bordered box on right)
    lbl_w = 58.0
    val_w = usable_w - lbl_w  # 116.0 mm
    row_h = 5.4

    units_short = _format_units_short(meta.credit_units)
    prog_short = _format_program_short(meta.program_name, meta.department, meta.program_code)
    faculty_title_case = meta.faculty_name.title() if meta.faculty_name.isupper() else meta.faculty_name

    meta_rows = [
        ("Name of Faculty:", faculty_title_case),
        ("Course Title, Description and Units:", f"{meta.course_code} - {meta.course_title} ({units_short})"),
        ("Semester and Academic Year:", meta.semester_ay),
        ("Program:", prog_short),
        ("Academic Unit:", meta.academic_unit or "Engineering"),
    ]

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.25)
    for k_lbl, v_txt in meta_rows:
        pdf.set_font("Helvetica", "B", 9.0)
        pdf.cell(lbl_w, row_h, _clean_pdf_text(k_lbl), border=0, align="L")
        pdf.set_font("Helvetica", "", 9.0)
        pdf.cell(val_w, row_h, _clean_pdf_text(v_txt), border=1, align="L", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4.5)

    # 3. TABLE 1: COURSE ASSESSMENT PLAN (As declared in the Syllabus)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(usable_w, 5.5, "COURSE ASSESSMENT PLAN (As declared in the Syllabus)", align="C", new_x="LMARGIN", new_y="NEXT")

    n_clos = max(1, len(outcomes))
    comp_col_w = 58.0
    clo_area_w = usable_w - comp_col_w  # 116.0 mm
    clo_col_w = clo_area_w / n_clos

    # Gold/Amber Header matching sample PDF
    y_cap_hdr = pdf.get_y()
    hdr_h1 = 5.2
    hdr_h2 = 5.2

    pdf.set_draw_color(255, 255, 255)
    pdf.set_line_width(0.35)

    # Left merged header cell: "Assessment Component"
    pdf.set_fill_color(246, 204, 102)
    pdf.rect(left_m, y_cap_hdr, comp_col_w, hdr_h1 + hdr_h2, style="DF")
    pdf.set_xy(left_m + 1.5, y_cap_hdr + 2.8)
    pdf.set_font("Helvetica", "B", 9.0)
    pdf.cell(comp_col_w - 3.0, 5.0, "Assessment Component", border=0, align="L")

    # Right top header cell: "Course Assessment Plan"
    pdf.set_fill_color(244, 194, 72)
    pdf.set_xy(left_m + comp_col_w, y_cap_hdr)
    pdf.cell(clo_area_w, hdr_h1, "Course Assessment Plan", border=1, align="C", fill=True)

    # Right sub-header cells: CLO1, CLO2, ...
    pdf.set_fill_color(248, 213, 118)
    pdf.set_xy(left_m + comp_col_w, y_cap_hdr + hdr_h1)
    for co in outcomes:
        pdf.cell(clo_col_w, hdr_h2, _clean_pdf_text(co.co_id), border=1, align="C", fill=True)

    pdf.set_y(y_cap_hdr + hdr_h1 + hdr_h2)

    # Table 1 Data Rows (Cream background #FDF2D0, white grid lines)
    # Check if a custom / synchronized Course Assessment Plan is defined in blueprint metadata
    cap_data = meta.course_assessment_plan if getattr(meta, "course_assessment_plan", None) else []
    if cap_data:
        plan_rows = [
            {
                "label": r.get("component_name") or r.get("code") or "Assessment",
                "clo_plans": r.get("clo_plans") or {},
            }
            for r in cap_data
        ]
    else:
        plan_rows = [
            {
                "label": sa_r["label"],
                "clo_plans": {
                    co.co_id: (DEFAULT_ASSESSMENT_PLAN_CELL_TEXT if sa_r["clo_aligned"].get(co.co_id, True) else "N/A")
                    for co in outcomes
                },
            }
            for sa_r in sa_rows
        ]

    body_row_h = 28.0
    for r_idx, pr in enumerate(plan_rows):
        y_r = pdf.get_y()
        if r_idx % 2 == 0:
            pdf.set_fill_color(252, 238, 197)
        else:
            pdf.set_fill_color(253, 244, 215)

        # Draw left component cell
        pdf.rect(left_m, y_r, comp_col_w, body_row_h, style="DF")
        pdf.set_xy(left_m + 1.5, y_r + (body_row_h - 5.0) / 2.0)
        pdf.set_font("Helvetica", "B", 9.0)
        pdf.cell(comp_col_w - 3.0, 5.0, _clean_pdf_text(pr["label"]), border=0, align="L")

        # Draw each CLO column cell with multi-line rubric / plan description
        pdf.set_font("Helvetica", "", 8.5)
        for c_idx, co in enumerate(outcomes):
            cx = left_m + comp_col_w + c_idx * clo_col_w
            pdf.rect(cx, y_r, clo_col_w, body_row_h, style="DF")
            cell_txt = pr["clo_plans"].get(co.co_id, DEFAULT_ASSESSMENT_PLAN_CELL_TEXT)
            if not cell_txt or not str(cell_txt).strip():
                cell_txt = "N/A"
            lines = cell_txt.split("\n")
            line_h = 4.1
            total_txt_h = len(lines) * line_h
            start_y = y_r + max(1.5, (body_row_h - total_txt_h) / 2.0)
            for l_i, line_str in enumerate(lines):
                pdf.set_xy(cx + 1.5, start_y + l_i * line_h)
                pdf.cell(clo_col_w - 3.0, line_h, _clean_pdf_text(line_str), border=0, align="C")

        pdf.set_y(y_r + body_row_h)

    pdf.ln(4.5)

    # 4. TABLE 2: COURSE LEARNING OUTCOME EVALUATION RESULT (Based on Class Record)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(
        usable_w,
        5.5,
        "COURSE LEARNING OUTCOME EVALUATION RESULT (Based on Class Record)",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    y_eval_hdr = pdf.get_y()
    pdf.set_draw_color(255, 255, 255)
    pdf.set_line_width(0.35)

    # Left merged header cell: "Assessment Component" (Green #9CC37E)
    pdf.set_fill_color(156, 195, 126)
    pdf.rect(left_m, y_eval_hdr, comp_col_w, hdr_h1 + hdr_h2, style="DF")
    pdf.set_xy(left_m + 1.5, y_eval_hdr + 2.8)
    pdf.set_font("Helvetica", "B", 9.0)
    pdf.cell(comp_col_w - 3.0, 5.0, "Assessment Component", border=0, align="L")

    # Right top header cell: "Course Assessment Plan"
    pdf.set_fill_color(138, 184, 103)
    pdf.set_xy(left_m + comp_col_w, y_eval_hdr)
    pdf.cell(clo_area_w, hdr_h1, "Course Assessment Plan", border=1, align="C", fill=True)

    # Right sub-header cells: CLO1, CLO2, ...
    pdf.set_fill_color(168, 204, 140)
    pdf.set_xy(left_m + comp_col_w, y_eval_hdr + hdr_h1)
    for co in outcomes:
        pdf.cell(clo_col_w, hdr_h2, _clean_pdf_text(co.co_id), border=1, align="C", fill=True)

    pdf.set_y(y_eval_hdr + hdr_h1 + hdr_h2)

    eval_row_h = 5.4
    for r_idx, sa_r in enumerate(sa_rows):
        if r_idx % 2 == 0:
            pdf.set_fill_color(226, 239, 218)
        else:
            pdf.set_fill_color(237, 245, 232)

        pdf.set_font("Helvetica", "B", 9.0)
        pdf.cell(comp_col_w, eval_row_h, _clean_pdf_text(sa_r["label"]), border=1, align="L", fill=True)

        pdf.set_font("Helvetica", "", 9.0)
        for co in outcomes:
            pct = sa_r["clo_pass_pcts"].get(co.co_id, 0.0)
            pdf.cell(clo_col_w, eval_row_h, f"{pct:.2f}%", border=1, align="C", fill=True)
        pdf.ln(eval_row_h)

    # Overall (Weighted Average %) Row
    pdf.set_fill_color(226, 239, 218)
    pdf.set_font("Helvetica", "B", 9.0)
    pdf.cell(comp_col_w, eval_row_h, "Overall (Weighted Average %)", border=1, align="L", fill=True)
    for co in outcomes:
        ov_pct = overall_weighted.get(co.co_id, 0.0)
        pdf.cell(clo_col_w, eval_row_h, f"{ov_pct:.2f}%", border=1, align="C", fill=True)
    pdf.ln(eval_row_h + 1.5)

    # 5. Explanatory Note below Table 2
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 7.8)
    note_text = (
        "Note: Weighted Average is computed as **Summation of Score x (weight/total applicable weights)**. "
        "An overall rating of below 50% indicates non-attainment of the course outcome and adjustment in "
        "the TLAs and assessment activities may be required. Submit this together with the Class Record."
    )
    pdf.multi_cell(usable_w, 3.8, _clean_pdf_text(note_text), align="L", markdown=True)
    pdf.ln(3.5)

    # 6. Signatories & Actions Needed Boxes (Matching bottom of AEE 321_EE 3A_CLO Report.pdf)
    sig_y = pdf.get_y()
    left_sig_x = left_m
    right_sig_x = left_m + 112.0

    pdf.set_font("Helvetica", "", 9.0)
    pdf.set_xy(left_sig_x, sig_y)
    pdf.cell(60.0, 5.0, "Prepared by:", border=0, align="L")
    pdf.set_xy(right_sig_x, sig_y)
    pdf.cell(60.0, 5.0, "Reviewed and Noted by:", border=0, align="L")

    name_y = sig_y + 10.5
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_xy(left_sig_x, name_y)
    pdf.cell(85.0, 5.0, _clean_pdf_text(meta.faculty_name.upper()), border=0, align="L")
    pdf.set_xy(right_sig_x, name_y)
    pdf.cell(62.0, 5.0, _clean_pdf_text(meta.program_head.upper()), border=0, align="L")

    now = datetime.now()
    date_str = f"Date: {now.month}/{now.day:02d}/{now.year}"
    date_y = name_y + 4.8
    pdf.set_font("Helvetica", "", 9.0)
    pdf.set_xy(left_sig_x, date_y)
    pdf.cell(85.0, 4.8, date_str, border=0, align="L")
    pdf.set_xy(right_sig_x, date_y)
    pdf.cell(62.0, 4.8, date_str, border=0, align="L")

    # Actions Needed bordered rectangular boxes
    box_y = date_y + 5.2
    box_h = 10.5
    left_box_w = 112.0
    right_box_w = usable_w - left_box_w  # 62.0 mm

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.25)
    pdf.rect(left_m, box_y, left_box_w, box_h)
    pdf.rect(left_m + left_box_w, box_y, right_box_w, box_h)

    pdf.set_font("Helvetica", "", 8.8)
    pdf.set_xy(left_m + 1.0, box_y + 1.0)
    pdf.cell(50.0, 4.2, "Actions Needed:", border=0, align="L")
    pdf.set_xy(left_m + left_box_w + 1.0, box_y + 1.0)
    pdf.cell(50.0, 4.2, "Actions Needed:", border=0, align="L")

    return bytes(pdf.output())
