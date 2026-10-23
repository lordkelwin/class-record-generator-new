import io
import re
from typing import Dict, List, Tuple
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule
from openpyxl.chart import BarChart, Reference

from models import (
    SyllabusBlueprint,
    AssessmentCategory,
    AssessmentItem,
    CourseOutcome,
    get_default_cqi_indicators,
)


def openpyxl_col_idx(col_letter: str) -> int:
    result = 0
    for ch in col_letter:
        result = result * 26 + (ord(ch.upper()) - ord("A") + 1)
    return result


def _parse_clo_list(co_id_str: str) -> List[str]:
    """
    Extracts a list of CLO identifiers from a single or multi-CLO string
    (e.g. 'CLO1, CLO2' -> ['CLO1', 'CLO2'], 'CLO1' -> ['CLO1']).
    """
    raw = str(co_id_str or "").strip()
    if not raw:
        return ["CLO1"]
    parts = [p.strip().upper() for p in re.split(r"[,;/]+", raw) if p.strip()]
    seen: List[str] = []
    for p in parts:
        # Handle if someone wrote "CLO1:15"
        clo_code = p.split(":")[0].strip()
        if clo_code and clo_code not in seen:
            seen.append(clo_code)
    return seen or ["CLO1"]


def _item_has_clo(co_id_str: str, target_co_id: str) -> bool:
    """Returns True if target_co_id is among the CLOs aligned to an assessment item."""
    target = str(target_co_id or "").strip().upper()
    return target in _parse_clo_list(co_id_str)


def _get_item_clo_points(it: AssessmentItem) -> List[Tuple[str, float]]:
    """
    Returns an ordered list of (clo_id, max_points_for_clo) for an AssessmentItem.
    Each aligned CLO gets its explicit point allocation from it.clo_points
    (or an even split of it.max_score if not explicitly specified).
    """
    clos = _parse_clo_list(it.co_id)
    n = max(1, len(clos))
    default_each = round(float(it.max_score or 30.0) / n, 2)
    raw_map = it.clo_points if isinstance(getattr(it, "clo_points", None), dict) else {}
    norm_map: Dict[str, float] = {}
    for k, v in raw_map.items():
        try:
            val = float(v)
            if val > 0:
                norm_map[str(k).strip().upper()] = val
        except (ValueError, TypeError):
            pass

    result: List[Tuple[str, float]] = []
    for c in clos:
        pts = norm_map.get(c.upper(), default_each)
        result.append((c.upper(), pts))
    return result


def _format_clo_points(it: AssessmentItem) -> str:
    """
    Formats 'CLOs and corresponding points' for the Setup sheet using explicit per-CLO points:
    - Single CLO ('CLO1', 30 pts) -> 'CLO1:30'
    - Multi-CLO ('CLO1, CLO2', 50/50) -> 'CLO1:50, CLO2:50'
    - Multi-CLO ('CLO1, CLO2', 20/10) -> 'CLO1:20, CLO2:10'
    """
    pairs = _get_item_clo_points(it)
    formatted = []
    for c, pts in pairs:
        pts_str = f"{pts:.0f}" if abs(pts - round(pts)) < 1e-6 else f"{pts:.1f}"
        formatted.append(f"{c}:{pts_str}")
    return ", ".join(formatted)


def _get_student_clo_score(st_obj, it: AssessmentItem, clo_id: str, clo_pts: float, total_pts: float):
    """
    Retrieves a student's score for a specific (AssessmentItem, CLO) pair.
    Checks:
      1. Explicit per-CLO key: f"{it.item_id}__{clo_id}" (e.g. "Q1__CLO1", "MTE__CLO1")
      2. Legacy split key: f"{it.item_id}_{clo_num}" (e.g. "MTE_1", "FTE_2")
      3. Item-level key: it.item_id (scaled proportionally by clo_pts / total_pts)
    """
    if not st_obj or not getattr(st_obj, "scores", None):
        return ""
    scores = st_obj.scores
    clo_key = f"{it.item_id}__{clo_id.upper()}"
    if clo_key in scores and scores[clo_key] != "":
        return scores[clo_key]

    m_num = re.search(r"(\d+)$", clo_id)
    if m_num:
        alt_key = f"{it.item_id}_{m_num.group(1)}"
        if alt_key in scores and scores[alt_key] != "":
            return scores[alt_key]

    if it.item_id in scores and scores[it.item_id] != "":
        try:
            raw_total = float(scores[it.item_id])
            ratio = (clo_pts / total_pts) if total_pts > 0 else 1.0
            scaled = round(raw_total * ratio, 2)
            return int(round(scaled)) if abs(scaled - round(scaled)) < 1e-6 else scaled
        except (ValueError, TypeError):
            return ""
    return ""


def generate_class_record_workbook(blueprint: SyllabusBlueprint) -> bytes:
    """
    Generates a USeP College of Engineering OBE Class Record Excel (.xlsx) workbook
    modeled directly after 'Math 211_Class Records_1st Sem SY 2026-2027.xlsm' and 'EE 211.pdf':
      1. 'Setup' sheet: Course Metadata, Midterm/Finals FA & SA Assessment Setup, and CLO-PGO-PI Mapping.
      2. '{Course}_{Section}' sheet: Consolidated Class Record with Midterm & Finals Base-50 grades,
         Per-Summative-Assessment CLO Grades, CLO Final Grades, side-by-side Course Learning Outcome
         Assessment Report, CO Assessment Tool (linked to PGO & Performance Indicator), and
         Continuous Quality Improvement (CQI) Evaluation & Action Plan.
      3. 'CLO & CQI Report' sheet: Dedicated print-ready CLO Assessment Report, CO Assessment Tool + Chart,
         and CQI Plan.
    """
    wb = Workbook()

    # Common Fonts & Fills
    maroon_fill = PatternFill("solid", fgColor="7F1D1D")  # USeP Maroon accent
    navy_fill = PatternFill("solid", fgColor="1E3A8A")
    slate_fill = PatternFill("solid", fgColor="334155")
    midterm_fill = PatternFill("solid", fgColor="0F766E")
    finals_fill = PatternFill("solid", fgColor="4338CA")
    clo_hdr_fill = PatternFill("solid", fgColor="1E293B")
    gold_fill = PatternFill("solid", fgColor="FEF3C7")
    soft_blue_fill = PatternFill("solid", fgColor="EFF6FF")
    soft_gray_fill = PatternFill("solid", fgColor="F1F5F9")
    grade_col_fill = PatternFill("solid", fgColor="E0F2FE")
    pass_fill = PatternFill("solid", fgColor="DCFCE7")
    fail_fill = PatternFill("solid", fgColor="FEE2E2")

    f_white_bold = Font(name="Calibri", size=10.5, bold=True, color="FFFFFF")
    f_white_sm = Font(name="Calibri", size=9, bold=True, color="FFFFFF")
    f_title = Font(name="Calibri", size=12, bold=True, color="0F172A")
    f_sub = Font(name="Calibri", size=10, bold=True, color="1E293B")
    f_bold = Font(name="Calibri", size=9.5, bold=True, color="0F172A")
    f_sm_bold = Font(name="Calibri", size=8.5, bold=True, color="1E293B")
    f_reg = Font(name="Calibri", size=9.5, color="0F172A")
    f_sm = Font(name="Calibri", size=8.5, color="334155")
    f_formula = Font(name="Calibri", size=9.5, bold=True, color="1E3A8A")
    f_pass = Font(name="Calibri", size=9.5, bold=True, color="166534")
    f_fail = Font(name="Calibri", size=9.5, bold=True, color="991B1B")

    thin = Side(border_style="thin", color="CBD5E1")
    med = Side(border_style="medium", color="475569")
    b_grid = Border(left=thin, right=thin, top=thin, bottom=thin)
    b_hdr = Border(left=thin, right=thin, top=thin, bottom=med)

    al_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    al_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    al_right = Alignment(horizontal="right", vertical="center", wrap_text=True)

    meta = blueprint.metadata
    outcomes = blueprint.course_outcomes
    students = blueprint.students
    num_students = max(len(students), 10)
    degree_cutoff = float(outcomes[0].target_score_pct if outcomes else 75.0)
    if degree_cutoff <= 1.0:
        degree_cutoff *= 100.0

    # =========================================================================
    # SHEET 1: SETUP (Exact USeP Setup Sheet Structure)
    # =========================================================================
    ws_setup = wb.active
    ws_setup.title = "Setup"
    ws_setup.views.sheetView[0].showGridLines = True

    setup_meta_rows = [
        ("Subject Code", meta.course_code),
        ("Subject Title", meta.course_title.upper()),
        ("Schedule", meta.schedule),
        ("Room", meta.room),
        ("Section", meta.section),
        ("Units", meta.credit_units),
        ("Sem/Year", meta.semester_ay.upper()),
        ("No. of Students", num_students),
        ("Program", meta.program_code),
        ("Faculty Name", meta.faculty_name),
        ("Lecture/Laboratory", meta.lec_lab),
    ]
    for r_i, (k_lbl, v_val) in enumerate(setup_meta_rows, start=1):
        ca = ws_setup.cell(row=r_i, column=1, value=k_lbl)
        cb = ws_setup.cell(row=r_i, column=2, value=v_val)
        ca.font = f_bold
        ca.fill = soft_gray_fill
        ca.border = b_grid
        cb.font = f_reg
        cb.border = b_grid

    setup_headers = [
        "Term",
        "Assessment",
        "Lecture/Laboratory",
        "Type of Assessment",
        "Assessment Code",
        "Label",
        "Total Points",
        "CLOs and corresponding points",
        "Weight (%)",
    ] + [f"{co.co_id} Max Points" for co in outcomes]

    for c_i, h_lbl in enumerate(setup_headers, start=1):
        c = ws_setup.cell(row=14, column=c_i, value=h_lbl)
        c.fill = maroon_fill if c_i <= 9 else navy_fill
        c.font = f_white_sm
        c.alignment = al_center
        c.border = b_hdr

    curr_setup_row = 15
    first_clo_col_let = get_column_letter(10)
    last_clo_col_let = get_column_letter(9 + max(1, len(outcomes)))
    for cat in blueprint.categories:
        for it in cat.items:
            wt_for_setup = 0.0 if cat.assessment_type.upper() == "FA" else float(it.weight_pct)
            clo_pairs = dict(_get_item_clo_points(it))
            total_pts_formula = (
                f"=SUM({first_clo_col_let}{curr_setup_row}:{last_clo_col_let}{curr_setup_row})"
                if outcomes
                else float(it.max_score)
            )
            row_vals = [
                cat.term,
                cat.name,
                cat.lec_lab or meta.lec_lab,
                cat.assessment_type,
                cat.assessment_code,
                it.item_id,
                total_pts_formula,
                _format_clo_points(it),
                wt_for_setup,
            ] + [
                float(clo_pairs[co.co_id.upper()]) if co.co_id.upper() in clo_pairs else None
                for co in outcomes
            ]

            for c_i, val in enumerate(row_vals, start=1):
                c = ws_setup.cell(row=curr_setup_row, column=c_i, value=val)
                if c_i == 7:
                    c.font = f_formula
                    c.fill = soft_blue_fill
                elif c_i > 9 and val is not None and val > 0:
                    c.font = f_bold
                    c.fill = gold_fill
                else:
                    c.font = f_reg
                c.alignment = al_center if c_i != 2 else al_left
                c.border = b_grid
            curr_setup_row += 1

    clo_tbl_start = curr_setup_row + 2
    clo_setup_headers = [
        "CLO#",
        "Course Outcome",
        "Graduate Outcomes",
        "Performance Indicator",
        "Degree (from CO)",
        "Target (Number of Students Achieving CO, %)",
    ]
    for c_i, h_lbl in enumerate(clo_setup_headers, start=1):
        c = ws_setup.cell(row=clo_tbl_start, column=c_i, value=h_lbl)
        c.fill = navy_fill
        c.font = f_white_sm
        c.alignment = al_center
        c.border = b_hdr

    for idx_co, co in enumerate(outcomes, start=1):
        r_co = clo_tbl_start + idx_co
        deg_dec = co.target_score_pct / 100.0 if co.target_score_pct > 1.0 else co.target_score_pct
        tgt_dec = co.target_class_pass_pct / 100.0 if co.target_class_pass_pct > 1.0 else co.target_class_pass_pct
        vals = [
            co.co_id,
            co.description,
            co.graduate_outcome_desc,
            co.performance_indicator,
            deg_dec,
            tgt_dec,
        ]
        for c_i, val in enumerate(vals, start=1):
            c = ws_setup.cell(row=r_co, column=c_i, value=val)
            c.font = f_bold if c_i == 1 else f_reg
            c.alignment = al_center if c_i in (1, 5, 6) else al_left
            c.border = b_grid
            if c_i in (5, 6):
                c.number_format = "0%"
        ws_setup.row_dimensions[r_co].height = 32

    for c_let, w in [("A", 20), ("B", 42), ("C", 36), ("D", 36), ("E", 18), ("F", 24), ("G", 14), ("H", 26), ("I", 14)]:
        ws_setup.column_dimensions[c_let].width = w
    for idx_co in range(len(outcomes)):
        ws_setup.column_dimensions[get_column_letter(10 + idx_co)].width = 16

    # =========================================================================
    # SHEET 2: CONSOLIDATED CLASS RECORD, CLO GRADE, ASSESSMENT REPORT & CQI
    # =========================================================================
    safe_sheet_title = re.sub(r"[\[\]\*\?\/\\:]", "_", f"{meta.course_code}_{meta.section}")[:31]
    ws = wb.create_sheet(title=safe_sheet_title)
    ws.views.sheetView[0].showGridLines = True

    # Left Metadata Header (Rows 1-17, Cols A-C)
    ws["A1"] = "REPUBLIC OF THE PHILIPPINES"
    ws["A2"] = meta.university
    ws["A3"] = meta.college
    ws["A4"] = meta.address
    for r_i in range(1, 5):
        ws.cell(row=r_i, column=1).font = f_bold if r_i in (2, 3) else f_sm

    ws["A6"] = "CLASS RECORD"
    ws["A6"].font = Font(name="Calibri", size=13, bold=True, color="7F1D1D")

    ws["A7"] = meta.course_code
    ws["A7"].font = f_title
    ws["C7"] = meta.course_title.upper()
    ws["C7"].font = f_title

    left_labels = [
        (9, "TIME", meta.schedule),
        (10, "ROOM", meta.room),
        (11, "SECTION", meta.section),
        (13, "COURSE OUTCOME ALIGNMENT", ""),
        (14, "ITEMS", ""),
        (15, "UNITS", meta.credit_units),
        (16, "SEM/YEAR", meta.semester_ay.upper()),
    ]
    for r_i, lbl_a, val_c in left_labels:
        ca = ws.cell(row=r_i, column=1, value=lbl_a)
        ca.font = f_sm_bold
        if val_c != "":
            cc = ws.cell(row=r_i, column=3, value=val_c)
            cc.font = f_bold

    for col_i, h_txt in [(1, "#"), (2, "ID #"), (3, "Name")]:
        c = ws.cell(row=17, column=col_i, value=h_txt)
        c.fill = slate_fill
        c.font = f_white_sm
        c.alignment = al_center
        c.border = b_hdr

    # Build Term Columns (Midterm, Finals) starting at Column D (col=4)
    curr_col = 4
    term_names = ["Midterm", "Finals"]
    term_grade_col_letters: Dict[str, str] = {}

    # Track item columns for CLO Grade & CLO Final Grade calculations:
    # item_col_info: list of dicts {col_let, term, assessment_type, assessment_code, cat_name, cat_weight, co_id}
    item_col_info: List[Dict] = []

    for t_idx, t_name in enumerate(term_names):
        t_cats = [c for c in blueprint.categories if c.term.lower().startswith(t_name[:3].lower())]
        if not t_cats:
            continue

        term_start_col = curr_col
        sa_grade_And_weight_refs: List[Tuple[str, str, str]] = []  # (sa_grade_col_let, first_item_let, last_item_let)
        t_fill = midterm_fill if t_idx == 0 else finals_fill

        for cat in t_cats:
            cat_start_col = curr_col
            cat_item_letters: List[str] = []
            cat_clo_entries: List[Tuple[int, AssessmentItem, str, float, float]] = []

            # Distribute category weight across items if item weights are not explicitly set
            n_items = max(1, len(cat.items))
            default_it_wt = 100.0 if cat.assessment_type.upper() == "FA" else round(cat.weight_pct / n_items, 2)

            for it in cat.items:
                it_wt = 100.0 if cat.assessment_type.upper() == "FA" else (float(it.weight_pct) if it.weight_pct > 0 else default_it_wt)
                clo_pairs = _get_item_clo_points(it)
                total_it_pts = sum(pts for _, pts in clo_pairs) or float(it.max_score or 30.0)
                n_clos_for_it = max(1, len(clo_pairs))

                for clo_id, clo_pts in clo_pairs:
                    c_let = get_column_letter(curr_col)
                    cat_item_letters.append(c_let)
                    col_wt = round(it_wt * (clo_pts / total_it_pts), 4) if total_it_pts > 0 else round(it_wt / n_clos_for_it, 4)
                    col_label = f"{it.item_id} ({clo_id})" if n_clos_for_it > 1 else it.item_id

                    # Row 10: Item Label separated per CLO (e.g., Q1 (CLO1), Q1 (CLO2), MTE (CLO1), MTE (CLO2))
                    c10 = ws.cell(row=10, column=curr_col, value=col_label)
                    c10.fill = soft_gray_fill
                    c10.font = f_sm_bold
                    c10.alignment = al_center
                    c10.border = b_grid

                    # Row 12: Weight (%) allocated to this (item, CLO) column
                    c12 = ws.cell(row=12, column=curr_col, value=col_wt)
                    c12.fill = soft_blue_fill
                    c12.font = f_sm_bold
                    c12.alignment = al_center
                    c12.border = b_grid
                    c12.number_format = "0.##"

                    # Row 13: Single CLO Alignment for this score column (e.g., "CLO1" or "CLO2")
                    c13 = ws.cell(row=13, column=curr_col, value=clo_id)
                    c13.fill = gold_fill
                    c13.font = f_sm_bold
                    c13.alignment = al_center
                    c13.border = b_grid

                    # Row 14: ITEMS (Max Score / HPS allocated specifically to this CLO)
                    c14 = ws.cell(row=14, column=curr_col, value=float(clo_pts))
                    c14.fill = soft_gray_fill
                    c14.font = f_bold
                    c14.alignment = al_center
                    c14.border = b_hdr
                    c14.number_format = "0.##"

                    ws.column_dimensions[c_let].width = 10.0 if n_clos_for_it > 1 else 8.5

                    cat_clo_entries.append((curr_col, it, clo_id, clo_pts, total_it_pts))
                    item_col_info.append({
                        "col_let": c_let,
                        "term": t_name,
                        "assessment_type": cat.assessment_type.upper(),
                        "assessment_code": cat.assessment_code.upper(),
                        "cat_name": cat.name,
                        "cat_weight": float(cat.weight_pct),
                        "co_id": clo_id,
                        "item_id": it.item_id,
                        "col_wt": col_wt,
                    })
                    curr_col += 1

            # Category Grade Column (e.g., FORMATIVE ASSESSMENT 1 GRADE or SUMMATIVE ASSESSMENT 1 GRADE)
            grd_col = curr_col
            grd_let = get_column_letter(grd_col)

            # Merge Row 9 across category items + grade col for Assessment Code (FA1, SA1, SA2)
            ws.merge_cells(start_row=9, start_column=cat_start_col, end_row=9, end_column=grd_col)
            c9 = ws.cell(row=9, column=cat_start_col, value=cat.assessment_code)
            c9.fill = slate_fill
            c9.font = f_white_sm
            c9.alignment = al_center
            for mc in range(cat_start_col, grd_col + 1):
                ws.cell(row=9, column=mc).border = b_grid

            c10_g = ws.cell(row=10, column=grd_col, value=f"{cat.name.upper()} GRADE")
            c10_g.fill = grade_col_fill
            c10_g.font = f_sm_bold
            c10_g.alignment = al_center
            c10_g.border = b_grid
            ws.column_dimensions[grd_let].width = 12.5

            if cat.assessment_type.upper() == "SA":
                sa_grade_And_weight_refs.append((grd_let, cat_item_letters[0], cat_item_letters[-1]))

            # Populate Student Per-CLO Scores & Base-50 Category Grade Formula (Rows 18 .. 17+num_students)
            for s_idx in range(num_students):
                r_num = 18 + s_idx
                st_obj = students[s_idx] if s_idx < len(students) else None

                for ic, it_obj, clo_id, clo_pts, total_it_pts in cat_clo_entries:
                    sc_val = _get_student_clo_score(st_obj, it_obj, clo_id, clo_pts, total_it_pts)
                    sc_cell = ws.cell(row=r_num, column=ic, value=sc_val if sc_val != "" else None)
                    sc_cell.font = f_reg
                    sc_cell.alignment = al_center
                    sc_cell.border = b_grid
                    sc_cell.number_format = "0.##"

                # Exact USeP Base-50 Category Grade Formula across all per-CLO columns in the category:
                # =((H18*$H$12/$H$14 + I18*$I$12/$I$14 + ...)/SUM($H$12:$K$12))*50 + 50
                weighted_terms = [f"{cl}{r_num}*${cl}$12/${cl}$14" for cl in cat_item_letters]
                numerator = "+".join(weighted_terms)
                sum_wts = f"SUM(${cat_item_letters[0]}$12:${cat_item_letters[-1]}$12)"
                base50_formula = f"=(({numerator})/{sum_wts})*50+50"

                cg = ws.cell(row=r_num, column=grd_col, value=base50_formula)
                cg.fill = grade_col_fill
                cg.font = f_formula
                cg.alignment = al_center
                cg.border = b_grid
                cg.number_format = "0.00"

            curr_col += 1

        # Term Grade Column (MIDTERM GRADE / FINAL GRADE)
        t_grd_col = curr_col
        t_grd_let = get_column_letter(t_grd_col)
        term_grade_col_letters[t_name] = t_grd_let

        # Merge Row 7 Term Header (MIDTERM / FINALS) across term_start_col .. t_grd_col - 1
        ws.merge_cells(start_row=7, start_column=term_start_col, end_row=7, end_column=t_grd_col - 1)
        c7_t = ws.cell(row=7, column=term_start_col, value=t_name.upper())
        c7_t.fill = t_fill
        c7_t.font = f_white_bold
        c7_t.alignment = al_center

        ws.merge_cells(start_row=8, start_column=term_start_col, end_row=8, end_column=t_grd_col - 1)
        c8_t = ws.cell(row=8, column=term_start_col, value=meta.lec_lab.upper())
        c8_t.fill = slate_fill
        c8_t.font = f_white_sm
        c8_t.alignment = al_center

        c8_mg = ws.cell(row=8, column=t_grd_col, value=f"{t_name.upper()} GRADE")
        c8_mg.fill = t_fill
        c8_mg.font = f_white_sm
        c8_mg.alignment = al_center
        c8_mg.border = b_grid

        c13_mg = ws.cell(row=13, column=t_grd_col, value="MG" if t_idx == 0 else "FG")
        c13_mg.fill = gold_fill
        c13_mg.font = f_sm_bold
        c13_mg.alignment = al_center
        c13_mg.border = b_grid
        ws.column_dimensions[t_grd_let].width = 13.0

        for s_idx in range(num_students):
            r_num = 18 + s_idx
            # Exact USeP Term Grade formula:
            # =(J18*SUM($H$12:$I$12))/100 + (L18*SUM($K$12:$K$12))/100 + ...
            sa_parts = [f"({g_let}{r_num}*SUM(${f_let}$12:${l_let}$12))/100" for g_let, f_let, l_let in sa_grade_And_weight_refs]
            t_formula = "=" + "+".join(sa_parts) if sa_parts else "=50"
            cmg = ws.cell(row=r_num, column=t_grd_col, value=t_formula)
            cmg.fill = soft_blue_fill
            cmg.font = f_bold
            cmg.alignment = al_center
            cmg.border = b_grid
            cmg.number_format = "0.00"

        curr_col += 1

    # Semestral Consolidation Columns: AVERAGE FINAL GRADE (AFG), GRADES (FINAL), REMARKS
    afg_col = curr_col
    fin_col = curr_col + 1
    rem_col = curr_col + 2
    afg_let = get_column_letter(afg_col)
    fin_let = get_column_letter(fin_col)
    rem_let = get_column_letter(rem_col)

    for col_i, lbl8, lbl13, width in [
        (afg_col, "AVERAGE FINAL GRADE", "AFG", 13.5),
        (fin_col, "GRADES", "FINAL", 11.0),
        (rem_col, "REMARKS", "", 12.5),
    ]:
        c8 = ws.cell(row=8, column=col_i, value=lbl8)
        c8.fill = maroon_fill
        c8.font = f_white_sm
        c8.alignment = al_center
        c8.border = b_grid
        if lbl13:
            c13 = ws.cell(row=13, column=col_i, value=lbl13)
            c13.fill = gold_fill
            c13.font = f_sm_bold
            c13.alignment = al_center
            c13.border = b_grid
        ws.column_dimensions[get_column_letter(col_i)].width = width

    curr_col += 3

    # =========================================================================
    # PORTION 1: DEDICATED CLO GRADE SECTION (Right of REMARKS, matching AE..AI)
    # =========================================================================
    # 1A. Per-Summative-Assessment CLO Grade columns (e.g. SUMMATIVE ASSESSMENT 1 CLO GRADE -> CLO1, CLO2)
    sa_codes_ordered: List[str] = []
    sa_code_names: Dict[str, str] = {}
    sa_code_weights: Dict[str, float] = {}
    for info in item_col_info:
        if info["assessment_type"] == "SA":
            code = info["assessment_code"]
            if code not in sa_codes_ordered:
                sa_codes_ordered.append(code)
                sa_code_names[code] = info["cat_name"]
                sa_code_weights[code] = info["cat_weight"]

    # Map (sa_code, co_id) -> col_letter of that SA CLO Grade column
    sa_clo_grade_cols: Dict[Tuple[str, str], str] = {}

    for sa_code in sa_codes_ordered:
        sa_start_col = curr_col
        for co in outcomes:
            matching_items = [
                inf for inf in item_col_info
                if inf["assessment_type"] == "SA"
                and inf["assessment_code"] == sa_code
                and _item_has_clo(inf["co_id"], co.co_id)
            ]
            if not matching_items:
                continue

            col_let = get_column_letter(curr_col)
            sa_clo_grade_cols[(sa_code, co.co_id)] = col_let

            c15 = ws.cell(row=15, column=curr_col, value=co.co_id)
            c15.fill = gold_fill
            c15.font = f_sm_bold
            c15.alignment = al_center
            c15.border = b_grid
            ws.column_dimensions[col_let].width = 11.5

            # Student formula: =SUM(H18*$H$12/$H$14, ...)/SUM($H$12, ...)*50+50
            for s_idx in range(num_students):
                r_num = 18 + s_idx
                num_parts = [f"{inf['col_let']}{r_num}*${inf['col_let']}$12/${inf['col_let']}$14" for inf in matching_items]
                den_parts = [f"${inf['col_let']}$12" for inf in matching_items]
                f_str = f"=SUM({','.join(num_parts)})/SUM({','.join(den_parts)})*50+50"
                c_val = ws.cell(row=r_num, column=curr_col, value=f_str)
                c_val.font = f_reg
                c_val.alignment = al_center
                c_val.border = b_grid
                c_val.number_format = "0.00"

            curr_col += 1

        if curr_col > sa_start_col:
            ws.merge_cells(start_row=7, start_column=sa_start_col, end_row=14, end_column=curr_col - 1)
            c7_sa = ws.cell(
                row=7,
                column=sa_start_col,
                value=f"SUMMATIVE ASSESSMENT {sa_code[-1]} CLO GRADE",
            )
            c7_sa.fill = clo_hdr_fill
            c7_sa.font = f_white_sm
            c7_sa.alignment = al_center
            for r_i in range(7, 15):
                for c_i in range(sa_start_col, curr_col):
                    ws.cell(row=r_i, column=c_i).border = b_grid

    # 1B. Consolidated CLO FINAL GRADE Columns (CLO1, CLO2, ...)
    clo_final_start_col = curr_col
    clo_final_col_letters: Dict[str, str] = {}

    for co in outcomes:
        matching_all_sa = [
            inf for inf in item_col_info
            if inf["assessment_type"] == "SA" and _item_has_clo(inf["co_id"], co.co_id)
        ]
        if not matching_all_sa:
            matching_all_sa = [inf for inf in item_col_info if _item_has_clo(inf["co_id"], co.co_id)]

        col_let = get_column_letter(curr_col)
        clo_final_col_letters[co.co_id] = col_let

        c15 = ws.cell(row=15, column=curr_col, value=co.co_id)
        c15.fill = gold_fill
        c15.font = f_bold
        c15.alignment = al_center
        c15.border = b_grid
        ws.column_dimensions[col_let].width = 12.0

        for s_idx in range(num_students):
            r_num = 18 + s_idx
            if matching_all_sa:
                num_parts = [f"{inf['col_let']}{r_num}*${inf['col_let']}$12/${inf['col_let']}$14" for inf in matching_all_sa]
                den_parts = [f"${inf['col_let']}$12" for inf in matching_all_sa]
                f_str = f"=(SUM({','.join(num_parts)})/SUM({','.join(den_parts)}))*50+50"
            else:
                f_str = "=50"
            c_val = ws.cell(row=r_num, column=curr_col, value=f_str)
            c_val.fill = soft_blue_fill
            c_val.font = f_formula
            c_val.alignment = al_center
            c_val.border = b_grid
            c_val.number_format = "0.00"

        curr_col += 1

    if curr_col > clo_final_start_col:
        ws.merge_cells(start_row=7, start_column=clo_final_start_col, end_row=14, end_column=curr_col - 1)
        c7_cf = ws.cell(row=7, column=clo_final_start_col, value="CLO FINAL GRADE")
        c7_cf.fill = navy_fill
        c7_cf.font = f_white_bold
        c7_cf.alignment = al_center
        for r_i in range(7, 15):
            for c_i in range(clo_final_start_col, curr_col):
                ws.cell(row=r_i, column=c_i).border = b_grid

    # =========================================================================
    # TRANSMUTATION LOOKUP TABLE (Matches AK7:AL17 in Math 211.xlsm)
    # =========================================================================
    curr_col += 1  # Spacer column
    lookup_col_min = curr_col
    lookup_col_grd = curr_col + 1
    lk_min_let = get_column_letter(lookup_col_min)
    lk_grd_let = get_column_letter(lookup_col_grd)

    usep_lookup_rows = [
        (0, "UW"),
        (50, 5.00),
        (75, 3.00),
        (77, 2.75),
        (80, 2.50),
        (83, 2.25),
        (86, 2.00),
        (89, 1.75),
        (92, 1.50),
        (95, 1.25),
        (98, 1.00),
    ]
    for idx_lk, (cut_val, grd_val) in enumerate(usep_lookup_rows, start=7):
        c_m = ws.cell(row=idx_lk, column=lookup_col_min, value=cut_val)
        c_g = ws.cell(row=idx_lk, column=lookup_col_grd, value=grd_val)
        c_m.font = f_sm
        c_g.font = f_sm_bold
        c_m.alignment = al_center
        c_g.alignment = al_center
        c_m.border = b_grid
        c_g.border = b_grid
        if isinstance(grd_val, float):
            c_g.number_format = "0.00"

    ws.column_dimensions[lk_min_let].width = 6.5
    ws.column_dimensions[lk_grd_let].width = 7.5

    # Now fill Student Identity, AFG, GRADES (VLOOKUP), and REMARKS (Rows 18 .. 17+num_students)
    mg_let = term_grade_col_letters.get("Midterm", "O")
    fg_let = term_grade_col_letters.get("Finals", "AA")
    last_student_row = 17 + num_students

    for s_idx in range(num_students):
        r_num = 18 + s_idx
        st_obj = students[s_idx] if s_idx < len(students) else None

        c_no = ws.cell(row=r_num, column=1, value=s_idx + 1)
        c_id = ws.cell(row=r_num, column=2, value=st_obj.student_id if st_obj else f"2026-{1001 + s_idx}")
        c_nm = ws.cell(row=r_num, column=3, value=st_obj.full_name if st_obj else f"Student #{s_idx + 1}")
        c_no.alignment = al_center
        c_id.alignment = al_center
        c_nm.alignment = al_left
        for ci in (1, 2, 3):
            ws.cell(row=r_num, column=ci).font = f_reg
            ws.cell(row=r_num, column=ci).border = b_grid

        # AFG = (MG + FG) * 0.5
        c_afg = ws.cell(row=r_num, column=afg_col, value=f"=({mg_let}{r_num}+{fg_let}{r_num})*0.5")
        c_afg.font = f_bold
        c_afg.alignment = al_center
        c_afg.border = b_grid
        c_afg.number_format = "0.00"

        # GRADES = VLOOKUP(AFG, $AK$7:$AL$17, 2, TRUE)
        c_fin = ws.cell(
            row=r_num,
            column=fin_col,
            value=f"=VLOOKUP({afg_let}{r_num},${lk_min_let}$7:${lk_grd_let}$17,2,TRUE)",
        )
        c_fin.font = f_bold
        c_fin.alignment = al_center
        c_fin.border = b_grid
        c_fin.number_format = "0.00"

        # REMARKS = IF(OR(AC18>3, AC18="UW"), "FAILED", "PASSED")
        c_rem = ws.cell(
            row=r_num,
            column=rem_col,
            value=f'=IF(OR({fin_let}{r_num}>3,{fin_let}{r_num}="UW"),"FAILED","PASSED")',
        )
        c_rem.font = f_bold
        c_rem.alignment = al_center
        c_rem.border = b_grid

    ws.conditional_formatting.add(
        f"{rem_let}18:{rem_let}{last_student_row}",
        CellIsRule(operator="equal", formula=['"PASSED"'], fill=pass_fill, font=f_pass),
    )
    ws.conditional_formatting.add(
        f"{rem_let}18:{rem_let}{last_student_row}",
        CellIsRule(operator="equal", formula=['"FAILED"'], fill=fail_fill, font=f_fail),
    )

    ws.cell(row=last_student_row + 1, column=3, value="---nothing follows---").font = f_sm_bold
    ws.cell(row=last_student_row + 1, column=3).alignment = al_center

    # =========================================================================
    # PORTION 2: SIDE PANEL — COURSE LEARNING OUTCOME ASSESSMENT REPORT
    # (Matching Columns AQ..AT in Math 211.xlsm)
    # =========================================================================
    rpt_col = lookup_col_grd + 2
    rpt_let_1 = get_column_letter(rpt_col)
    ws.column_dimensions[rpt_let_1].width = 32.0
    for idx_co in range(len(outcomes)):
        ws.column_dimensions[get_column_letter(rpt_col + 1 + idx_co)].width = 16.0

    ws.cell(row=8, column=rpt_col, value=meta.university).font = f_title
    ws.cell(row=9, column=rpt_col, value="COURSE LEARNING OUTCOME ASSESSMENT REPORT").font = Font(name="Calibri", size=11, bold=True, color="7F1D1D")
    rpt_meta = [
        (11, "Name of Faculty:", meta.faculty_name),
        (13, "Course Title, Description and Units:", f"{meta.course_code} - {meta.course_title.upper()} ({meta.credit_units})"),
        (14, "Semester and Academic Year:", meta.semester_ay),
        (15, "Program:", meta.program_code),
        (16, "Academic Unit:", meta.academic_unit),
    ]
    for r_m, k_m, v_m in rpt_meta:
        ws.cell(row=r_m, column=rpt_col, value=k_m).font = f_sm_bold
        ws.cell(row=r_m, column=rpt_col + 1, value=v_m).font = f_bold

    # Table 1: COURSE ASSESSMENT PLAN (As declared in the Syllabus)
    ws.cell(row=18, column=rpt_col, value="COURSE ASSESSMENT PLAN (As declared in the Syllabus)").font = f_sub
    ws.cell(row=19, column=rpt_col, value="Assessment Component").fill = maroon_fill
    ws.cell(row=19, column=rpt_col).font = f_white_sm
    ws.cell(row=19, column=rpt_col).alignment = al_center
    ws.cell(row=19, column=rpt_col).border = b_grid

    end_clo_rpt_col = rpt_col + len(outcomes)
    ws.merge_cells(start_row=19, start_column=rpt_col + 1, end_row=19, end_column=end_clo_rpt_col)
    c_cap = ws.cell(row=19, column=rpt_col + 1, value="Course Assessment Plan")
    c_cap.fill = maroon_fill
    c_cap.font = f_white_sm
    c_cap.alignment = al_center
    for ci in range(rpt_col + 1, end_clo_rpt_col + 1):
        ws.cell(row=19, column=ci).border = b_grid

    ws.cell(row=20, column=rpt_col, value="").border = b_grid
    for idx_co, co in enumerate(outcomes, start=1):
        c = ws.cell(row=20, column=rpt_col + idx_co, value=co.co_id)
        c.fill = gold_fill
        c.font = f_bold
        c.alignment = al_center
        c.border = b_grid

    plan_row = 21
    for sa_code in sa_codes_ordered:
        sa_wt = sa_code_weights.get(sa_code, 0.0)
        c_lbl = ws.cell(row=plan_row, column=rpt_col, value=f"Summative Assessment {sa_code[-1]} ({sa_wt:.0f}%)")
        c_lbl.font = f_reg
        c_lbl.border = b_grid
        # Compute exact share per CLO in Midterm + Finals from separated per-CLO column weights
        sa_cols_all = [inf for inf in item_col_info if inf["assessment_type"] == "SA" and inf["assessment_code"] == sa_code]
        total_sa_col_wt = sum(float(inf.get("col_wt", 0.0)) for inf in sa_cols_all)
        measured_clos = [co.co_id for co in outcomes if (sa_code, co.co_id) in sa_clo_grade_cols]
        fallback_share = (sa_wt / len(measured_clos)) if measured_clos else 0.0
        for idx_co, co in enumerate(outcomes, start=1):
            if total_sa_col_wt > 0:
                co_wt = sum(
                    float(inf.get("col_wt", 0.0))
                    for inf in sa_cols_all
                    if _item_has_clo(inf["co_id"], co.co_id)
                )
                share_pct = sa_wt * (co_wt / total_sa_col_wt)
            else:
                share_pct = fallback_share if co.co_id in measured_clos else 0.0
            c_v = ws.cell(
                row=plan_row,
                column=rpt_col + idx_co,
                value=share_pct / 100.0,
            )
            c_v.font = f_reg
            c_v.alignment = al_center
            c_v.border = b_grid
            c_v.number_format = "0.0%"
        plan_row += 1

    # Table 2: COURSE LEARNING OUTCOME EVALUATION RESULT (Based on Class Record)
    eval_start_row = plan_row + 2
    ws.cell(
        row=eval_start_row,
        column=rpt_col,
        value="COURSE LEARNING OUTCOME EVALUATION RESULT (Based on Class Record)",
    ).font = f_sub

    hdr_r1 = eval_start_row + 1
    hdr_r2 = eval_start_row + 2
    ws.cell(row=hdr_r1, column=rpt_col, value="Assessment Component").fill = navy_fill
    ws.cell(row=hdr_r1, column=rpt_col).font = f_white_sm
    ws.cell(row=hdr_r1, column=rpt_col).alignment = al_center
    ws.cell(row=hdr_r1, column=rpt_col).border = b_grid

    ws.merge_cells(start_row=hdr_r1, start_column=rpt_col + 1, end_row=hdr_r1, end_column=end_clo_rpt_col)
    c_cer = ws.cell(row=hdr_r1, column=rpt_col + 1, value="Course Assessment Plan")
    c_cer.fill = navy_fill
    c_cer.font = f_white_sm
    c_cer.alignment = al_center
    for ci in range(rpt_col + 1, end_clo_rpt_col + 1):
        ws.cell(row=hdr_r1, column=ci).border = b_grid

    ws.cell(row=hdr_r2, column=rpt_col, value="").border = b_grid
    for idx_co, co in enumerate(outcomes, start=1):
        c = ws.cell(row=hdr_r2, column=rpt_col + idx_co, value=co.co_id)
        c.fill = gold_fill
        c.font = f_bold
        c.alignment = al_center
        c.border = b_grid

    eval_row = hdr_r2 + 1
    # Map co_id -> list of (cell_ref_in_eval_table, sa_weight_decimal)
    clo_eval_cell_weights: Dict[str, List[Tuple[str, float]]] = {co.co_id: [] for co in outcomes}

    for sa_code in sa_codes_ordered:
        sa_wt = sa_code_weights.get(sa_code, 0.0)
        c_lbl = ws.cell(row=eval_row, column=rpt_col, value=f"Summative Assessment {sa_code[-1]} ({sa_wt:.0f}%)")
        c_lbl.font = f_reg
        c_lbl.border = b_grid

        for idx_co, co in enumerate(outcomes, start=1):
            target_col_idx = rpt_col + idx_co
            target_col_let = get_column_letter(target_col_idx)
            sa_clo_let = sa_clo_grade_cols.get((sa_code, co.co_id))
            if sa_clo_let:
                # Exact formula from Math 211.xlsm: =COUNTIF($AE$18:$AE$59, ">=75")/N
                f_eval = f'=COUNTIF(${sa_clo_let}$18:${sa_clo_let}${last_student_row},">={degree_cutoff:.0f}")/{num_students}'
                clo_eval_cell_weights[co.co_id].append((f"${target_col_let}${eval_row}", sa_wt / 100.0))
            else:
                f_eval = 0.0

            c_ev = ws.cell(row=eval_row, column=target_col_idx, value=f_eval)
            c_ev.font = f_formula if sa_clo_let else f_sm
            c_ev.alignment = al_center
            c_ev.border = b_grid
            c_ev.number_format = "0.0%"
        eval_row += 1

    # Overall (Weighted Average %) Row
    c_ov_lbl = ws.cell(row=eval_row, column=rpt_col, value="Overall (Weighted Average %)")
    c_ov_lbl.font = f_bold
    c_ov_lbl.fill = soft_blue_fill
    c_ov_lbl.border = b_hdr

    for idx_co, co in enumerate(outcomes, start=1):
        target_col_idx = rpt_col + idx_co
        pairs = clo_eval_cell_weights.get(co.co_id, [])
        if pairs:
            total_w = sum(w for _, w in pairs)
            sum_terms = ",".join([f"{cref}*{w:.2f}" for cref, w in pairs])
            ov_formula = f"=SUM({sum_terms})/{total_w:.2f}"
        else:
            ov_formula = "=0"
        c_ov = ws.cell(row=eval_row, column=target_col_idx, value=ov_formula)
        c_ov.font = f_formula
        c_ov.fill = soft_blue_fill
        c_ov.alignment = al_center
        c_ov.border = b_hdr
        c_ov.number_format = "0.0%"

    note_row = eval_row + 1
    ws.merge_cells(start_row=note_row, start_column=rpt_col, end_row=note_row + 1, end_column=end_clo_rpt_col)
    c_note = ws.cell(
        row=note_row,
        column=rpt_col,
        value=(
            "Note: Weighted Average is computed as Summation of Score x (weight/total applicable weights). "
            "An overall rating of below 50% indicates non-attainment of the course outcome and adjustment "
            "in the TLAs and assessment activities may be required. Submit this together with the Class Record."
        ),
    )
    c_note.font = f_sm
    c_note.alignment = al_left

    sig_rpt_row = note_row + 3
    ws.cell(row=sig_rpt_row, column=rpt_col, value="Prepared by:").font = f_sm_bold
    ws.cell(row=sig_rpt_row, column=rpt_col + 1, value="Reviewed and Noted by:").font = f_sm_bold
    ws.cell(row=sig_rpt_row + 2, column=rpt_col, value=meta.faculty_name.upper()).font = f_bold
    ws.cell(row=sig_rpt_row + 2, column=rpt_col + 1, value=meta.program_head.upper()).font = f_bold
    ws.cell(row=sig_rpt_row + 3, column=rpt_col, value="Faculty").font = f_sm
    ws.cell(row=sig_rpt_row + 3, column=rpt_col + 1, value="Program Head").font = f_sm
    ws.cell(row=sig_rpt_row + 4, column=rpt_col, value="Actions Needed:").font = f_sm_bold
    ws.cell(row=sig_rpt_row + 4, column=rpt_col + 1, value="Actions Needed:").font = f_sm_bold

    # =========================================================================
    # PORTION 3: BELOW STUDENT ROSTER — SIGNATORIES, SUMMARY & CO ASSESSMENT TOOL
    # (Matching Rows 62..85 in Math 211.xlsm)
    # =========================================================================
    sub_row = last_student_row + 3
    ws.cell(row=sub_row, column=1, value="SUBMITTED BY:").font = f_sm_bold
    ws.cell(row=sub_row, column=3, value=meta.faculty_name.upper()).font = f_bold
    ws.cell(row=sub_row, column=6, value="=TODAY()").number_format = "m/dd/yyyy"
    ws.cell(row=sub_row, column=12, value=meta.program_head.upper()).font = f_bold
    ws.cell(row=sub_row, column=18, value="=TODAY()").number_format = "m/dd/yyyy"

    ws.cell(row=sub_row + 1, column=3, value="Faculty").font = f_sm
    ws.cell(row=sub_row + 1, column=6, value="Date").font = f_sm
    ws.cell(row=sub_row + 1, column=12, value="Program Head").font = f_sm
    ws.cell(row=sub_row + 1, column=18, value="Date").font = f_sm

    # Pass / Fail / Dropped / Incomplete Count Block
    cnt_start_row = sub_row + 4
    status_labels = ["Passed", "Failed", "Dropped", "Incomplete"]
    for idx_s, s_lbl in enumerate(status_labels):
        r_s = cnt_start_row + idx_s
        c_cnt = ws.cell(
            row=r_s,
            column=2,
            value=f"=COUNTIF(${rem_let}$18:${rem_let}${last_student_row},UPPER($C${r_s}))",
        )
        c_lbl = ws.cell(row=r_s, column=3, value=s_lbl)
        c_cnt.font = f_bold
        c_cnt.alignment = al_center
        c_cnt.border = b_grid
        c_lbl.font = f_reg
        c_lbl.border = b_grid

    tot_cnt_row = cnt_start_row + 4
    ws.cell(
        row=tot_cnt_row,
        column=2,
        value=f"=$B${cnt_start_row}+$B${cnt_start_row+1}+$B${cnt_start_row+2}+$B${cnt_start_row+3}",
    ).font = f_bold
    ws.cell(row=tot_cnt_row, column=2).alignment = al_center
    ws.cell(row=tot_cnt_row, column=2).border = b_hdr
    ws.cell(row=tot_cnt_row, column=3, value="TOTAL").font = f_bold
    ws.cell(row=tot_cnt_row, column=3).border = b_hdr

    # CO Assessment Tool Table (Linked to Program Graduate Outcome & Performance Indicator)
    co_tool_row = tot_cnt_row + 3
    ws.cell(row=co_tool_row, column=1, value="CO Assessment Tool").font = f_title

    co_hdr_row = co_tool_row + 1
    # Merge layout matching Math 211.xlsm:
    # A: CO# | B..C: Course Outcome | D..H: Graduate Outcome | I..N: Performance Indicator |
    # O..R: Degree (from CO) | S..V: CO Achievement | W..Z: Target (% of Students achieving CLO) | AA..AD: Remarks
    co_tool_spans = [
        (1, 1, "CO#"),
        (2, 3, "Course Outcome"),
        (4, 8, "Graduate Outcome"),
        (9, 14, "Performance Indicator"),
        (15, 18, "Degree (from CO)"),
        (19, 22, "CO Achievement"),
        (23, 26, "Target (% of Students achieving CLO)"),
        (27, 30, "Remarks"),
    ]
    for c_start, c_end, h_lbl in co_tool_spans:
        if c_end > c_start:
            ws.merge_cells(start_row=co_hdr_row, start_column=c_start, end_row=co_hdr_row, end_column=c_end)
        c = ws.cell(row=co_hdr_row, column=c_start, value=h_lbl)
        c.fill = maroon_fill
        c.font = f_white_sm
        c.alignment = al_center
        for ci in range(c_start, c_end + 1):
            ws.cell(row=co_hdr_row, column=ci).border = b_hdr

    for idx_co, co in enumerate(outcomes, start=1):
        r_co = co_hdr_row + idx_co
        for c_start, c_end, _ in co_tool_spans:
            if c_end > c_start:
                ws.merge_cells(start_row=r_co, start_column=c_start, end_row=r_co, end_column=c_end)

        deg_dec = co.target_score_pct / 100.0 if co.target_score_pct > 1.0 else co.target_score_pct
        tgt_dec = co.target_class_pass_pct / 100.0 if co.target_class_pass_pct > 1.0 else co.target_class_pass_pct
        clo_f_let = clo_final_col_letters.get(co.co_id, "AH")

        ws.cell(row=r_co, column=1, value=co.co_id).alignment = al_center
        ws.cell(row=r_co, column=1).font = f_bold
        ws.cell(row=r_co, column=2, value=co.description).alignment = al_left
        ws.cell(row=r_co, column=2).font = f_reg
        ws.cell(row=r_co, column=4, value=co.graduate_outcome_desc).alignment = al_left
        ws.cell(row=r_co, column=4).font = f_reg
        ws.cell(row=r_co, column=9, value=co.performance_indicator).alignment = al_left
        ws.cell(row=r_co, column=9).font = f_reg

        c_deg = ws.cell(row=r_co, column=15, value=deg_dec)
        c_deg.alignment = al_center
        c_deg.font = f_bold
        c_deg.number_format = "0%"

        # Exact formula from Math 211.xlsm: =COUNTIF($AH$18:$AH$59, ">= 75")/N
        c_ach = ws.cell(
            row=r_co,
            column=19,
            value=f'=COUNTIF(${clo_f_let}$18:${clo_f_let}${last_student_row},">= {co.target_score_pct:.0f}")/{num_students}',
        )
        c_ach.alignment = al_center
        c_ach.font = f_formula
        c_ach.number_format = "0.0%"

        c_tgt = ws.cell(row=r_co, column=23, value=tgt_dec)
        c_tgt.alignment = al_center
        c_tgt.font = f_bold
        c_tgt.number_format = "0%"

        c_rem_co = ws.cell(
            row=r_co,
            column=27,
            value=f'=IF($S${r_co}>={tgt_dec:.2f},"PASSED","FAILED")',
        )
        c_rem_co.alignment = al_center
        c_rem_co.font = f_bold

        for ci in range(1, 31):
            ws.cell(row=r_co, column=ci).border = b_grid
        ws.row_dimensions[r_co].height = 36

    # =========================================================================
    # PORTION 4: CONTINUOUS QUALITY IMPROVEMENT (CQI) EVALUATION & ACTION PLAN
    # (Matching Rows 90..156 in Math 211.xlsm)
    # =========================================================================
    cqi_start_row = co_hdr_row + len(outcomes) + 3
    cqi_meta_rows = [
        ("Course:", f"{meta.course_code} - {meta.course_title.upper()}"),
        ("Instructor:", meta.faculty_name.upper()),
        ("Academic Year/Semester:", meta.semester_ay.upper()),
        ("Date of Evaluation:", "=TODAY()"),
    ]
    for idx_m, (m_lbl, m_val) in enumerate(cqi_meta_rows):
        rm = cqi_start_row + idx_m
        ws.cell(row=rm, column=1, value=m_lbl).font = f_bold
        cm_v = ws.cell(row=rm, column=3, value=m_val)
        cm_v.font = f_bold
        if m_val == "=TODAY()":
            cm_v.number_format = "m/dd/yyyy"

    purp_row = cqi_start_row + 5
    ws.merge_cells(start_row=purp_row, start_column=1, end_row=purp_row + 1, end_column=26)
    c_purp = ws.cell(
        row=purp_row,
        column=1,
        value=(
            "PURPOSE: This evaluation tool is designed to help you systematically assess factors influencing "
            "your course delivery during the past academic period. Your insights will inform the Continuous "
            "Quality Improvement (CQI) process, allowing us to enhance teaching and learning effectiveness "
            "in our engineering programs."
        ),
    )
    c_purp.font = f_bold
    c_purp.alignment = al_left

    inst_row = purp_row + 3
    instructions_lines = [
        (1, "INSTRUCTIONS:", f_bold),
        (1, "1. Review Each Factor: Go through each indicator/factor listed below.", f_sm),
        (1, "2. Mark Contribution:", f_sm),
        (2, "Tick (✓): If the indicator/factor was positively contributory to the course's success, or if it was achieved/well-managed.", f_sm),
        (2, "Cross (✗): If the indicator/factor was negatively contributory, needs significant improvement, or was not adequately addressed.", f_sm),
        (1, "3. Add Notes/Remarks: In the 'Notes/Remarks for Improvement' column, provide specific details and elaborations.", f_sm),
        (1, "4. Overall Reflection: At the end, use the 'Overall Reflection & Action Plan' section to summarize key takeaways and propose initial action steps.", f_sm),
    ]
    for idx_il, (col_il, txt_il, fnt_il) in enumerate(instructions_lines):
        ws.cell(row=inst_row + idx_il, column=col_il, value=txt_il).font = fnt_il

    cqi_tbl_hdr_row = inst_row + len(instructions_lines) + 1
    cqi_spans = [
        (1, 2, "Category"),
        (3, 3, "Indicator/Factor"),
        (4, 7, "Mark (✓ or ✗)"),
        (8, 26, "Notes/Remarks for Improvement"),
    ]
    for c_start, c_end, h_lbl in cqi_spans:
        if c_end > c_start:
            ws.merge_cells(start_row=cqi_tbl_hdr_row, start_column=c_start, end_row=cqi_tbl_hdr_row, end_column=c_end)
        c = ws.cell(row=cqi_tbl_hdr_row, column=c_start, value=h_lbl)
        c.fill = navy_fill
        c.font = f_white_sm
        c.alignment = al_center
        for ci in range(c_start, c_end + 1):
            ws.cell(row=cqi_tbl_hdr_row, column=ci).border = b_hdr

    indicators = blueprint.cqi_plan.indicators or get_default_cqi_indicators()
    curr_cqi_r = cqi_tbl_hdr_row + 1
    last_cat_written = ""
    for ind in indicators:
        r_title = curr_cqi_r
        r_sub = curr_cqi_r + 1

        ws.merge_cells(start_row=r_title, start_column=1, end_row=r_sub, end_column=2)
        ws.merge_cells(start_row=r_title, start_column=4, end_row=r_sub, end_column=7)
        ws.merge_cells(start_row=r_title, start_column=8, end_row=r_sub, end_column=26)

        if ind.category != last_cat_written:
            c_cat = ws.cell(row=r_title, column=1, value=ind.category)
            c_cat.font = f_bold
            c_cat.alignment = al_left
            last_cat_written = ind.category

        c_t = ws.cell(row=r_title, column=3, value=ind.title)
        c_t.font = f_bold
        c_t.alignment = al_left

        c_s = ws.cell(row=r_sub, column=3, value=ind.subtitle)
        c_s.font = f_sm
        c_s.alignment = al_left

        c_mk = ws.cell(row=r_title, column=4, value=ind.mark)
        c_mk.font = f_pass if ind.mark == "✓" else f_fail
        c_mk.alignment = al_center

        c_rm = ws.cell(row=r_title, column=8, value=ind.remarks)
        c_rm.font = f_reg
        c_rm.alignment = al_left

        for rr in (r_title, r_sub):
            for ci in range(1, 27):
                ws.cell(row=rr, column=ci).border = b_grid

        curr_cqi_r += 2

    # OVERALL REFLECTION AND ACTION PLAN (Rows 154-156 in Math 211.xlsm)
    refl_row = curr_cqi_r + 2
    ws.cell(row=refl_row, column=1, value="OVERALL REFLECTION AND ACTION PLAN").font = f_title

    refl_hdr_row = refl_row + 1
    refl_val_row = refl_row + 2
    refl_spans = [
        (1, 2, "Key Strengths:", blueprint.cqi_plan.key_strengths),
        (3, 3, "Main Areas for Improvement:", blueprint.cqi_plan.areas_for_improvement),
        (4, 26, "Action Plan:", blueprint.cqi_plan.action_plan),
    ]
    for c_start, c_end, h_lbl, v_txt in refl_spans:
        if c_end > c_start:
            ws.merge_cells(start_row=refl_hdr_row, start_column=c_start, end_row=refl_hdr_row, end_column=c_end)
            ws.merge_cells(start_row=refl_val_row, start_column=c_start, end_row=refl_val_row, end_column=c_end)
        ch = ws.cell(row=refl_hdr_row, column=c_start, value=h_lbl)
        ch.fill = maroon_fill
        ch.font = f_white_sm
        ch.alignment = al_left

        cv = ws.cell(row=refl_val_row, column=c_start, value=v_txt)
        cv.font = f_reg
        cv.alignment = al_left
        for rr in (refl_hdr_row, refl_val_row):
            for ci in range(c_start, c_end + 1):
                ws.cell(row=rr, column=ci).border = b_grid
    ws.row_dimensions[refl_val_row].height = 65

    ws.column_dimensions["A"].width = 6.5
    ws.column_dimensions["B"].width = 14.5
    ws.column_dimensions["C"].width = 34.0
    ws.freeze_panes = "D18"

    # =========================================================================
    # SHEET 3: CLO & CQI REPORT (Clean Print-Ready View + OBE Attainment Chart)
    # =========================================================================
    ws_rep = wb.create_sheet(title="CLO & CQI Report")
    ws_rep.views.sheetView[0].showGridLines = True

    ws_rep.merge_cells("A1:H1")
    ws_rep["A1"] = f"{meta.university.upper()} — {meta.college}"
    ws_rep["A1"].fill = maroon_fill
    ws_rep["A1"].font = f_white_bold
    ws_rep["A1"].alignment = al_center
    ws_rep.row_dimensions[1].height = 24

    ws_rep.merge_cells("A2:H2")
    ws_rep["A2"] = f"COURSE LEARNING OUTCOME (CLO) ASSESSMENT REPORT & CQI PLAN — {meta.course_code}: {meta.course_title.upper()}"
    ws_rep["A2"].fill = navy_fill
    ws_rep["A2"].font = f_white_bold
    ws_rep["A2"].alignment = al_center
    ws_rep.row_dimensions[2].height = 22

    ws_rep.merge_cells("A3:H3")
    ws_rep["A3"] = f"Faculty: {meta.faculty_name}   |   Section: {meta.section}   |   {meta.semester_ay}   |   Program: {meta.program_name}"
    ws_rep["A3"].fill = slate_fill
    ws_rep["A3"].font = f_white_sm
    ws_rep["A3"].alignment = al_center

    # Section A: CO Assessment Tool Table (linked directly to Sheet 2)
    ws_rep["A5"] = "I. COURSE OUTCOME (CLO) ASSESSMENT TOOL (Linked to PGO & Performance Indicators)"
    ws_rep["A5"].font = f_title

    rep_co_headers = [
        "CLO#",
        "Course Learning Outcome (CLO)",
        "Program Graduate Outcome (PGO)",
        "Performance Indicator (PI)",
        "Degree Cutoff",
        "Actual Achievement (%)",
        "Target KPI (%)",
        "Remarks",
    ]
    for ci, h_txt in enumerate(rep_co_headers, start=1):
        c = ws_rep.cell(row=6, column=ci, value=h_txt)
        c.fill = maroon_fill
        c.font = f_white_sm
        c.alignment = al_center
        c.border = b_hdr

    for idx_co, co in enumerate(outcomes, start=1):
        r_rep = 6 + idx_co
        src_r = co_hdr_row + idx_co
        ws_rep.cell(row=r_rep, column=1, value=co.co_id).alignment = al_center
        ws_rep.cell(row=r_rep, column=1).font = f_bold
        ws_rep.cell(row=r_rep, column=2, value=co.description).alignment = al_left
        ws_rep.cell(row=r_rep, column=2).font = f_reg
        ws_rep.cell(row=r_rep, column=3, value=co.graduate_outcome_desc).alignment = al_left
        ws_rep.cell(row=r_rep, column=3).font = f_reg
        ws_rep.cell(row=r_rep, column=4, value=co.performance_indicator).alignment = al_left
        ws_rep.cell(row=r_rep, column=4).font = f_reg

        c_d = ws_rep.cell(row=r_rep, column=5, value=float(co.target_score_pct))
        c_d.alignment = al_center
        c_d.font = f_bold
        c_d.number_format = '0"%"'

        # Link Actual Achievement (%) from Sheet 2 CO Assessment Tool
        c_a = ws_rep.cell(row=r_rep, column=6, value=f"='{safe_sheet_title}'!S{src_r}*100")
        c_a.alignment = al_center
        c_a.font = f_formula
        c_a.number_format = "0.0"

        c_t = ws_rep.cell(row=r_rep, column=7, value=float(co.target_class_pass_pct))
        c_t.alignment = al_center
        c_t.font = f_bold
        c_t.number_format = "0.0"

        c_r = ws_rep.cell(row=r_rep, column=8, value=f"='{safe_sheet_title}'!AA{src_r}")
        c_r.alignment = al_center
        c_r.font = f_bold

        for ci in range(1, 9):
            ws_rep.cell(row=r_rep, column=ci).border = b_grid
        ws_rep.row_dimensions[r_rep].height = 38

    last_rep_co_row = 6 + len(outcomes)
    ws_rep.conditional_formatting.add(
        f"H7:H{last_rep_co_row}",
        CellIsRule(operator="equal", formula=['"PASSED"'], fill=pass_fill, font=f_pass),
    )
    ws_rep.conditional_formatting.add(
        f"H7:H{last_rep_co_row}",
        CellIsRule(operator="equal", formula=['"FAILED"'], fill=fail_fill, font=f_fail),
    )

    # Section B: Continuous Quality Improvement (CQI) Plan Summary Table
    cqi_rep_start = last_rep_co_row + 3
    ws_rep.cell(row=cqi_rep_start, column=1, value="II. CONTINUOUS QUALITY IMPROVEMENT (CQI) REFLECTION & ACTION PLAN").font = f_title

    cqi_box_rows = [
        ("Key Strengths", blueprint.cqi_plan.key_strengths),
        ("Main Areas for Improvement", blueprint.cqi_plan.areas_for_improvement),
        ("CQI Action Plan", blueprint.cqi_plan.action_plan),
    ]
    for idx_b, (b_lbl, b_val) in enumerate(cqi_box_rows, start=1):
        rb = cqi_rep_start + idx_b
        ws_rep.merge_cells(start_row=rb, start_column=1, end_row=rb, end_column=2)
        ws_rep.merge_cells(start_row=rb, start_column=3, end_row=rb, end_column=8)
        cl = ws_rep.cell(row=rb, column=1, value=b_lbl)
        cl.fill = soft_gray_fill
        cl.font = f_bold
        cl.alignment = al_left
        cv = ws_rep.cell(row=rb, column=3, value=b_val)
        cv.font = f_reg
        cv.alignment = al_left
        for ci in range(1, 9):
            ws_rep.cell(row=rb, column=ci).border = b_grid
        ws_rep.row_dimensions[rb].height = 48

    # Add OBE CLO Attainment Bar Chart
    if outcomes:
        chart = BarChart()
        chart.type = "col"
        chart.style = 10
        chart.title = f"CLO Attainment vs Target KPI ({meta.course_code})"
        chart.y_axis.title = "Percentage of Students (%)"
        chart.x_axis.title = "Course Learning Outcome"
        chart.y_axis.scaling.min = 0
        chart.y_axis.scaling.max = 100
        d_ref = Reference(ws_rep, min_col=6, min_row=6, max_col=7, max_row=last_rep_co_row)
        c_ref = Reference(ws_rep, min_col=1, min_row=7, max_row=last_rep_co_row)
        chart.add_data(d_ref, titles_from_data=True)
        chart.set_categories(c_ref)
        chart.width = 16
        chart.height = 9
        ws_rep.add_chart(chart, f"A{cqi_rep_start + 5}")

    for c_let, w in [("A", 10), ("B", 38), ("C", 34), ("D", 34), ("E", 14), ("F", 18), ("G", 15), ("H", 14)]:
        ws_rep.column_dimensions[c_let].width = w

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out.getvalue()
