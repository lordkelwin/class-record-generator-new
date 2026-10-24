"""
oversight_report_generator.py
Auto-generates official PDF and printable compliance reports for the Staff Oversight Portal.
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from fpdf import FPDF

class OversightReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(15, 23, 42)
        self.cell(0, 5, "UNIVERSITY OF SOUTHEASTERN PHILIPPINES", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(71, 85, 105)
        self.cell(0, 4, "COLLEGE OF ENGINEERING | OFFICE OF ACADEMIC AFFAIRS & OVERSIGHT", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 58, 138)
        self.cell(0, 6, "INSTITUTIONAL SYLLABUS REVIEW & CLASS RECORD FINALIZATION REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.4)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, f"FM-USeP-MID Institutional Oversight Audit Document  |  Page {self.page_no()}/{{nb}}", align="C")

def generate_oversight_report_pdf(analytics_data: Dict[str, Any], items: List[Dict[str, Any]], generated_by: str = "Academic Staff") -> bytes:
    pdf = OversightReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.alias_nb_pages()
    pdf.add_page()

    now_str = datetime.now().strftime("%B %d, %Y, %I:%M %p")

    # Meta bar
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(100, 5, f"Generated On: {now_str}")
    pdf.cell(90, 5, f"Prepared By: {generated_by}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Executive Summary Card
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(10, pdf.get_y(), 190, 28, style="DF")
    pdf.set_xy(14, pdf.get_y() + 3)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5, "EXECUTIVE SUMMARY & COMPLIANCE METRICS", new_x="LMARGIN", new_y="NEXT")

    syl_tot = analytics_data.get("syllabus_total", 0)
    syl_app = analytics_data.get("syllabus_approved", 0)
    syl_ong = analytics_data.get("syllabus_ongoing", 0)
    syl_pct = analytics_data.get("syllabus_compliance_pct", 0.0)

    cr_tot = analytics_data.get("class_record_total", 0)
    cr_fin = analytics_data.get("class_record_finalized", 0)
    cr_ong = analytics_data.get("class_record_in_signoff", 0)
    cr_pct = analytics_data.get("class_record_compliance_pct", 0.0)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(51, 65, 85)
    pdf.set_x(14)
    pdf.cell(95, 4.5, f"* Total Course Syllabi Monitored: {syl_tot}  (Approved: {syl_app}, In Review: {syl_ong})")
    pdf.cell(95, 4.5, f"* Syllabus Approval Compliance Rate: {syl_pct:.1f}%", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(14)
    pdf.cell(95, 4.5, f"* Total Class Records Monitored: {cr_tot}  (Finalized: {cr_fin}, Under Sign-off: {cr_ong})")
    pdf.cell(95, 4.5, f"* Class Record Finalization Rate: {cr_pct:.1f}%", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)

    # Program Compliance Table
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 6, "PROGRAM-BY-PROGRAM COMPLIANCE BREAKDOWN", new_x="LMARGIN", new_y="NEXT")

    prog_list = analytics_data.get("programs", [])
    col_w = [30, 24, 28, 28, 28, 26, 26]
    headers = ["Program", "Total Courses", "Syllabi Appr.", "Syllabi Pend.", "CR Finalized", "CR In-Process", "Overall %"]

    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 7.5)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(15, 23, 42)
    alt = False
    for p in prog_list:
        fill = alt
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_w[0], 5.5, f"  {p.get('code', '')}", border=1, fill=fill)
        pdf.cell(col_w[1], 5.5, str(p.get("courses_count", 0)), border=1, align="C", fill=fill)
        pdf.cell(col_w[2], 5.5, str(p.get("syllabi_approved", 0)), border=1, align="C", fill=fill)
        pdf.cell(col_w[3], 5.5, str(p.get("syllabi_pending", 0)), border=1, align="C", fill=fill)
        pdf.cell(col_w[4], 5.5, str(p.get("cr_finalized", 0)), border=1, align="C", fill=fill)
        pdf.cell(col_w[5], 5.5, str(p.get("cr_pending", 0)), border=1, align="C", fill=fill)
        comp = p.get("compliance_pct", 0.0)
        pdf.cell(col_w[6], 5.5, f"{comp:.1f}%", border=1, align="C", fill=fill)
        pdf.ln()
        alt = not alt

    pdf.ln(5)

    # Bottleneck Distribution
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 6, "APPROVAL STAGE & SIGNATORY QUEUE BOTTLENECK ANALYSIS", new_x="LMARGIN", new_y="NEXT")

    b_queue = analytics_data.get("bottlenecks", {})
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(51, 65, 85)

    b_items = [
        ("Review Committee Members", b_queue.get("committee_members", 0)),
        ("Review Committee Chair", b_queue.get("committee_chair", 0)),
        ("Program Head Endorsement", b_queue.get("program_head", 0)),
        ("Associate Dean Endorsement (PH Courses)", b_queue.get("associate_dean", 0)),
        ("College QA Countersign", b_queue.get("qa_head", 0)),
        ("College Dean Final Approval", b_queue.get("dean", 0)),
    ]

    for label, count in b_items:
        color = "#16a34a" if count == 0 else ("#ca8a04" if count < 3 else "#dc2626")
        pdf.cell(90, 5, f"- {label}:", border=0)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(100, 5, f"{count} request(s) awaiting accommodation", border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)

    pdf.ln(5)

    # Itemized Course Table
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 6, f"DETAILED ROSTER OF INSTITUTIONAL COURSES ({len(items)} Tracked)", new_x="LMARGIN", new_y="NEXT")

    r_cols = [22, 48, 16, 42, 32, 30]
    r_headers = ["Code", "Course Title", "Sec", "Faculty in Charge", "Syllabus Status", "Class Record Status"]

    pdf.set_fill_color(71, 85, 105)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 7)
    for i, h in enumerate(r_headers):
        pdf.cell(r_cols[i], 5.5, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 6.8)
    pdf.set_text_color(15, 23, 42)
    alt = False

    for c in items:
        # Check page overflow
        if pdf.get_y() > 265:
            pdf.add_page()
            pdf.set_fill_color(71, 85, 105)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 7)
            for i, h in enumerate(r_headers):
                pdf.cell(r_cols[i], 5.5, h, border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 6.8)
            pdf.set_text_color(15, 23, 42)

        fill = alt
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)

        c_code = str(c.get("course_code", ""))[:12]
        c_title = str(c.get("course_title", ""))[:28]
        sec = str(c.get("section", ""))[:6]
        fac = str(c.get("faculty_name", "") or c.get("owner", ""))[:24]

        syl_st = str(c.get("workflow", {}).get("status", "draft"))
        if syl_st == "approved":
            syl_label = "Approved & Sealed"
        elif syl_st == "returned":
            syl_label = "Returned"
        elif syl_st == "draft":
            syl_label = "Draft"
        else:
            syl_label = "In Review"

        cr_st = str(c.get("class_record_workflow", {}).get("status", "draft"))
        if cr_st == "finalized":
            cr_label = "Finalized (Locked)"
        elif cr_st == "returned":
            cr_label = "Returned"
        elif cr_st == "draft":
            cr_label = "Draft"
        else:
            cr_label = "In Sign-Off"

        pdf.cell(r_cols[0], 5, c_code, border=1, fill=fill)
        pdf.cell(r_cols[1], 5, c_title, border=1, fill=fill)
        pdf.cell(r_cols[2], 5, sec, border=1, align="C", fill=fill)
        pdf.cell(r_cols[3], 5, fac, border=1, fill=fill)
        pdf.cell(r_cols[4], 5, syl_label, border=1, align="C", fill=fill)
        pdf.cell(r_cols[5], 5, cr_label, border=1, align="C", fill=fill)
        pdf.ln()
        alt = not alt

    pdf.ln(8)

    # Certification Sign-off Block
    if pdf.get_y() > 245:
        pdf.add_page()

    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 5, "OFFICIAL OVERSIGHT VERIFICATION & AUDIT CERTIFICATION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.multi_cell(0, 4, "This audit document has been auto-generated by the USeP OBE System Staff Oversight Portal. All syllabus evaluations and class record signatures recorded herein are sealed with verified timestamps and cryptographic hashes.")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(90, 4, "Certified and Monitored By:")
    pdf.cell(90, 4, "Noted By:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.cell(90, 4, "________________________________________")
    pdf.cell(90, 4, "________________________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(90, 4, f"{generated_by} / Academic Staff")
    pdf.cell(90, 4, "College Dean / QA Head", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
