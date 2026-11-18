"""
CQI (Continuous Quality Improvement) Synthesis & Revisit Scheduling Engine.

Consolidates three authoritative data sources for a course:
  1. Direct Assessment — Step 4 (Class Record): assessment scores, bottleneck items, at-risk students.
  2. Direct OBE Attainment — Step 7 (CLO Report FM-USeP-MID-10): per-CLO % attainment vs target & PGO-PI alignment.
  3. Indirect Assessment — Student Portal Course Exit Survey: CLO confidence ratings, CQI-anchored
     pedagogical/delivery/resource ratings, and qualitative challenging topic feedback.

Provides rule-based + optional Gemini AI synthesis and Program Head Revisit Scheduling
(1 Year Post-Submission / Next Academic Year under the Same Semester).
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import db_persistence


def _dict_item_clo_points(it: Dict[str, Any], aligned_clos: List[str]) -> Dict[str, float]:
    """Resolves per-CLO max points for an assessment item dictionary."""
    clos = [c.strip().upper() for c in (aligned_clos or []) if c.strip()]
    if not clos:
        return {}
    n = max(1, len(clos))
    max_score = float(it.get("max_score") or 30.0)
    default_each = round(max_score / n, 2)
    raw_map = it.get("clo_points") if isinstance(it.get("clo_points"), dict) else {}
    norm_map: Dict[str, float] = {}
    for k, v in raw_map.items():
        try:
            val = float(v)
            if val > 0:
                norm_map[str(k).strip().upper()] = val
        except (ValueError, TypeError):
            pass
    return {c: norm_map.get(c, default_each) for c in clos}


def _dict_student_clo_score(
    st: Dict[str, Any],
    item_id: str,
    clo_id: str,
    clo_pts: float,
    total_pts: float,
) -> float:
    """Retrieves numeric student score for an (item, CLO) pair from student dict scores."""
    scores = (st or {}).get("scores") or {}
    if not isinstance(scores, dict):
        return 0.0
    clo_upper = str(clo_id or "").strip().upper()
    clo_key = f"{item_id}__{clo_upper}"
    if clo_key in scores and scores[clo_key] not in (None, ""):
        try:
            return float(scores[clo_key])
        except (ValueError, TypeError):
            pass
    m_num = re.search(r"(\d+)$", clo_upper)
    if m_num:
        alt_key = f"{item_id}_{m_num.group(1)}"
        if alt_key in scores and scores[alt_key] not in (None, ""):
            try:
                return float(scores[alt_key])
            except (ValueError, TypeError):
                pass
    if item_id in scores and scores[item_id] not in (None, ""):
        try:
            raw_total = float(scores[item_id])
            ratio = (clo_pts / total_pts) if total_pts > 0 else 1.0
            return round(raw_total * ratio, 4)
        except (ValueError, TypeError):
            pass
    return 0.0


def compute_cqi_revisit_schedule(
    semester_ay: str,
    submitted_dt: Optional[datetime] = None,
) -> Tuple[str, str]:
    """
    Computes the default Mandatory Revisit Date (YYYY-MM-DD) and Target Re-Evaluation Term:
      - Revisit Date: 1 Year (365 days) after submission date.
      - Target Term: Next Academic Year under the same Semester
        (e.g. '1st Semester, A.Y. 2026-2027' -> '1st Semester, A.Y. 2027-2028').
    """
    dt = submitted_dt or datetime.now()
    revisit_date = (dt + timedelta(days=365)).strftime("%Y-%m-%d")

    raw = str(semester_ay or "").strip()
    if not raw:
        next_yr = dt.year + 1
        return revisit_date, f"Next Academic Year ({next_yr}-{next_yr + 1})"

    def _bump_years(m):
        y1 = int(m.group(1)) + 1
        y2 = int(m.group(2)) + 1
        return f"{y1}-{y2}"

    next_term = re.sub(r"\b(20\d{2})\s*[-–]\s*(20\d{2})\b", _bump_years, raw)
    if next_term == raw:
        m_single = re.search(r"\b(20\d{2})\b", raw)
        if m_single:
            yr = int(m_single.group(1))
            next_term = raw.replace(str(yr), str(yr + 1), 1)
        else:
            next_term = f"{raw} (Next Academic Year)"

    return revisit_date, next_term


def evaluate_revisit_status(
    plan_row: Dict[str, Any],
    all_courses: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Evaluates live revisit status: 'Closed/Verified', 'Due for Re-Evaluation', or 'Upcoming'."""
    status = str(plan_row.get("status") or "").lower()
    existing_rev_status = str(plan_row.get("revisit_status") or "").strip()
    if status == "verified" or existing_rev_status == "Closed/Verified":
        return "Closed/Verified"

    rev_date = str(plan_row.get("revisit_date") or "").strip()
    today_str = datetime.now().strftime("%Y-%m-%d")
    if rev_date and today_str >= rev_date:
        return "Due for Re-Evaluation"

    # Also check if the next AY same-semester offering already has submitted grades
    target_term = str(plan_row.get("revisit_term") or "").strip().lower()
    c_code = re.sub(r"\s+", " ", str(plan_row.get("course_code") or "").strip().upper())
    cid = str(plan_row.get("course_id") or "")
    if target_term and c_code and all_courses:
        for doc in all_courses:
            if doc.get("id") == cid:
                continue
            d_code = re.sub(r"\s+", " ", str(doc.get("course_code") or "").strip().upper())
            d_sem = str(doc.get("semester_ay") or "").strip().lower()
            cr_status = str((doc.get("class_record_workflow") or {}).get("status") or "").lower()
            if d_code == c_code and target_term in d_sem and cr_status in ("for_program_head", "finalized", "approved"):
                return "Due for Re-Evaluation"

    return "Upcoming"


def collect_three_source_cqi_data(course_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Correlates Step 4 (Class Record), Step 7 (MID-10 CLO Attainment), and Student Course Exit Survey
    for the selected course.
    """
    cid = course_doc.get("id") or course_doc.get("course_id") or ""
    bp = course_doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    clos = bp.get("course_outcomes") or []
    cats = bp.get("categories") or []
    students = bp.get("students") or []
    passing_pct = float(meta.get("passing_percentage") or 75.0)

    # 1. Step 4 (Class Record) Item-Level Analysis
    item_stats: List[Dict[str, Any]] = []
    at_risk_students = 0
    assessed_students = 0

    for st in students:
        st_scores = st.get("scores") or {}
        if any(v is not None and str(v).strip() != "" for v in st_scores.values()):
            assessed_students += 1

    for cat in cats:
        a_type = (cat.get("assessment_type") or "SA").upper()
        term = cat.get("term") or "Midterm"
        for it in (cat.get("items") or []):
            iid = it.get("item_id") or ""
            aligned_clos = [
                c.strip().upper()
                for c in str(it.get("co_id") or "").replace(";", ",").split(",")
                if c.strip()
            ]
            pts_map = _dict_item_clo_points(it, aligned_clos)
            max_pts = sum(pts_map.values()) if pts_map else float(it.get("max_score") or 0.0)
            if max_pts <= 0:
                max_pts = float(it.get("max_score") or 30.0)

            pcts: List[float] = []
            pass_cnt = 0
            for st in students:
                if aligned_clos:
                    earned = sum(
                        _dict_student_clo_score(st, iid, c, float(pts_map.get(c, 0.0)), max_pts)
                        for c in aligned_clos
                    )
                else:
                    raw = (st.get("scores") or {}).get(iid)
                    earned = float(raw) if raw is not None and str(raw).strip() != "" else 0.0
                base50 = (earned / max_pts) * 50.0 + 50.0 if max_pts > 0 else 50.0
                pcts.append(base50)
                if base50 >= passing_pct:
                    pass_cnt += 1

            avg_score = round(sum(pcts) / len(pcts), 2) if pcts else None
            pass_rate = round((pass_cnt / len(pcts)) * 100.0, 1) if pcts else None
            item_stats.append({
                "item_id": iid,
                "name": it.get("name") or iid,
                "term": term,
                "assessment_type": a_type,
                "aligned_clos": aligned_clos,
                "avg_base50": avg_score,
                "pass_rate_pct": pass_rate,
                "is_bottleneck": bool(avg_score is not None and (avg_score < passing_pct or (pass_rate is not None and pass_rate < 60.0))),
            })

    # 2. Step 7 (CLO Assessment MID-10) + 3. Indirect Exit Survey Correlation
    survey_agg = db_persistence.get_course_survey_aggregates_db(cid, clos)
    survey_by_clo = {
        str(c.get("co_id") or "").upper(): c
        for c in (survey_agg.get("clo_ratings_summary") or [])
    }

    clo_correlations: List[Dict[str, Any]] = []
    unmet_clos: List[Dict[str, Any]] = []
    borderline_clos: List[Dict[str, Any]] = []

    for co in clos:
        co_id = str(co.get("co_id") or "").strip().upper()
        if not co_id:
            continue
        degree_tgt = float(co.get("degree_target") or 75.0)
        cohort_tgt_pct = float(co.get("target_pct") or 50.0)

        student_clo_grades: List[float] = []
        reaching_cnt = 0
        for st in students:
            earned_tot = 0.0
            max_tot = 0.0
            for cat in cats:
                a_type = (cat.get("assessment_type") or "SA").upper()
                cat_wt = float(cat.get("weight_pct") or 0.0)
                if not (a_type in ("SA", "SUMMATIVE") or (a_type not in ("FA", "FORMATIVE") and cat_wt > 0)):
                    continue
                for it in (cat.get("items") or []):
                    aligned = [
                        c.strip().upper()
                        for c in str(it.get("co_id") or "").replace(";", ",").split(",")
                        if c.strip()
                    ]
                    if co_id not in aligned:
                        continue
                    pts_map = _dict_item_clo_points(it, aligned)
                    tot_pts = sum(pts_map.values()) if pts_map else float(it.get("max_score") or 0.0)
                    c_max = float(pts_map.get(co_id, 0.0))
                    if c_max > 0:
                        max_tot += c_max
                        earned_tot += _dict_student_clo_score(st, it.get("item_id") or "", co_id, c_max, tot_pts)
            if max_tot > 0:
                g50 = round((earned_tot / max_tot) * 50.0 + 50.0, 2)
                student_clo_grades.append(g50)
                if g50 >= degree_tgt:
                    reaching_cnt += 1

        avg_direct = round(sum(student_clo_grades) / len(student_clo_grades), 2) if student_clo_grades else None
        attained_pct = round((reaching_cnt / len(student_clo_grades)) * 100.0, 1) if student_clo_grades else None
        direct_passed = bool(attained_pct is not None and attained_pct >= cohort_tgt_pct)
        is_borderline = bool(attained_pct is not None and cohort_tgt_pct <= attained_pct < (cohort_tgt_pct + 7.5))

        srv = survey_by_clo.get(co_id) or {}
        srv_rating = srv.get("avg_rating")
        srv_pct = srv.get("pct_equivalent")

        discrepancy = "Aligned"
        if attained_pct is not None and srv_pct is not None:
            if not direct_passed and srv_pct >= 75.0:
                discrepancy = "Overconfidence Gap (High Survey, Low Direct)"
            elif direct_passed and srv_pct < 70.0:
                discrepancy = "Confidence Deficit (Passed Direct, Low Survey)"

        row = {
            "co_id": co_id,
            "description": str(co.get("description") or "").strip(),
            "pgo": str(co.get("program_outcomes") or "").strip(),
            "pi": str(co.get("performance_indicator") or "").strip(),
            "degree_target": degree_tgt,
            "cohort_target_pct": cohort_tgt_pct,
            "direct_avg_grade": avg_direct,
            "direct_attainment_pct": attained_pct,
            "direct_passed": direct_passed,
            "is_borderline": is_borderline,
            "survey_avg_rating": srv_rating,
            "survey_pct_equiv": srv_pct,
            "survey_responses": srv.get("responses_count", 0),
            "correlation_note": discrepancy,
        }
        clo_correlations.append(row)
        if attained_pct is not None and not direct_passed:
            unmet_clos.append(row)
        elif is_borderline or (srv_rating is not None and srv_rating < 3.5):
            borderline_clos.append(row)

    # Approximate at-risk student count from CLOs failing average threshold
    if students and clo_correlations:
        for st in students:
            # quick check across items
            pass_items = 0
            tot_items = 0
            for it_s in item_stats:
                pass_items += 1 if (it_s["pass_rate_pct"] or 0) >= 50 else 0
                tot_items += 1
            if tot_items and pass_items == 0:
                at_risk_students += 1

    return {
        "course_id": cid,
        "course_code": course_doc.get("course_code") or meta.get("course_code") or "",
        "course_title": course_doc.get("course_title") or meta.get("course_title") or "",
        "section": course_doc.get("section") or meta.get("section") or "",
        "semester_ay": course_doc.get("semester_ay") or meta.get("semester_ay") or "",
        "students_enrolled": len(students),
        "students_assessed": assessed_students,
        "item_stats": item_stats,
        "bottleneck_items": [i for i in item_stats if i["is_bottleneck"]],
        "clo_correlations": clo_correlations,
        "unmet_clos": unmet_clos,
        "borderline_clos": borderline_clos,
        "exit_survey": survey_agg,
    }


def synthesize_cqi_plan(
    course_doc: Dict[str, Any],
    use_ai: bool = False,
    gemini_api_key: str = "",
) -> Dict[str, Any]:
    """
    Synthesizes structured CQI Plan recommendations from Class Record + MID-10 + Student Exit Survey.
    Uses deterministic rule-based correlation by default and upgrades narrative polish via
    Gemini when `use_ai=True` and an API key is configured.
    """
    data = collect_three_source_cqi_data(course_doc)
    c_code = data["course_code"] or "Course"
    clo_corr = data["clo_correlations"]
    unmet = data["unmet_clos"]
    borderline = data["borderline_clos"]
    bottlenecks = data["bottleneck_items"]
    srv = data["exit_survey"]
    anchors = srv.get("cqi_anchors_summary") or {}
    challenging = srv.get("challenging_topics") or []
    comments = srv.get("comments") or []

    # Build Strengths
    strong_clos = [c for c in clo_corr if c["direct_passed"] and not c["is_borderline"]]
    strength_lines = []
    if strong_clos:
        strength_lines.append(
            "Attained CLOs meeting or exceeding cohort targets: "
            + ", ".join(f"{c['co_id']} ({c['direct_attainment_pct']}%)" for c in strong_clos)
            + "."
        )
    if srv.get("overall_avg_rating") is not None:
        strength_lines.append(
            f"Student Exit Survey overall satisfaction averaged {srv['overall_avg_rating']:.2f}/5.00 across {srv['total_responses']} respondent(s)."
        )
    high_anchors = [k for k, v in anchors.items() if (v.get("avg_rating") or 0) >= 4.0]
    if high_anchors:
        strength_lines.append("Strong CQI evaluation dimensions (>=4.0/5.0): " + ", ".join(high_anchors) + ".")
    if not strength_lines:
        strength_lines.append(f"Syllabus & assessment framework for {c_code} aligned across PGOs/PIs; baseline student data collected.")

    # Build Areas for Improvement & Gap Analysis
    gap_lines = []
    for c in clo_corr:
        dir_str = f"{c['direct_attainment_pct']}%" if c["direct_attainment_pct"] is not None else "Pending"
        srv_str = f"{c['survey_avg_rating']:.2f}/5 ({c['survey_pct_equiv']}%)" if c["survey_avg_rating"] is not None else "No responses"
        status_tag = "UNMET" if (c["direct_attainment_pct"] is not None and not c["direct_passed"]) else ("BORDERLINE" if c["is_borderline"] else "MET")
        gap_lines.append(f"• {c['co_id']} [{status_tag}]: Direct MID-10 = {dir_str} (Target >= {c['cohort_target_pct']}%) | Indirect Exit Survey = {srv_str} — {c['correlation_note']}.")

    impr_lines = []
    if unmet:
        impr_lines.append("Priority unmet CLOs requiring curriculum intervention: " + ", ".join(f"{c['co_id']} ({c['direct_attainment_pct']}%)" for c in unmet) + ".")
    if borderline:
        impr_lines.append("Borderline/low-confidence CLOs needing reinforcement: " + ", ".join(c["co_id"] for c in borderline) + ".")
    if bottlenecks:
        impr_lines.append(
            "Low-performing Step 4 assessment tasks: "
            + ", ".join(f"{b['item_id']} ({b['name']}: avg {b['avg_base50']}, {b['pass_rate_pct']}% passing)" for b in bottlenecks[:4])
            + "."
        )
    low_anchors = [(k, v.get("avg_rating")) for k, v in anchors.items() if (v.get("avg_rating") or 5.0) < 3.8]
    if low_anchors:
        impr_lines.append("Survey CQI anchors below 3.80/5.00: " + ", ".join(f"{k} ({val:.2f})" for k, val in low_anchors) + ".")
    if not impr_lines:
        impr_lines.append("No critical CLO deficits observed; focus on sustaining >80% cohort attainment and deeper higher-order problem solving.")

    # Root Causes mapped directly from anchors + bottlenecks + challenging topics
    root_lines = []
    if any("pacing" in k or "delivery" in k for k, _ in low_anchors) or unmet:
        root_lines.append("• Instructional Pacing & Scaffolding: Complex derivations/design topics need additional guided worked examples prior to summative exams.")
    if any("assessment" in k or "rubric" in k or "tos" in k for k, _ in low_anchors) or bottlenecks:
        root_lines.append("• Assessment & TOS Readiness Gap: Students underperformed on multi-step application items due to limited formative practice aligned to rubric criteria.")
    if any("resource" in k or "lab" in k for k, _ in low_anchors):
        root_lines.append("• Learning Resources & Laboratory Support: Exit survey feedback indicates need for updated lab manuals, simulation walkthroughs, or reference sets.")
    if challenging:
        root_lines.append("• Student-Reported Challenging Areas: " + " | ".join(challenging[:3]))
    if not root_lines:
        root_lines.append("• Baseline diagnostic analysis across Class Record scores, MID-10 CLO results, and student feedback shows balanced alignment with minor topic-level variance.")

    # Action Plan & Target KPIs
    targeted_clos = [c["co_id"] for c in (unmet or borderline)] or [c["co_id"] for c in clo_corr[:2]]
    action_lines = []
    if unmet or borderline:
        action_lines.append(
            f"1. Targeted CLO Remediation ({', '.join(targeted_clos)}): Conduct structured pre-exam review drills and add 1–2 formative problem sets before SA1/SA2."
        )
    else:
        action_lines.append("1. Enrichment & Sustainment: Integrate capstone/case-based engineering design scenarios to elevate distinction rates.")
    if bottlenecks:
        action_lines.append(
            f"2. Assessment Calibration: Review TOS cognitive-level balance and provide worked rubric exemplars prior to {', '.join(b['item_id'] for b in bottlenecks[:3])}."
        )
    else:
        action_lines.append("2. Formative Feedback Loop: Maintain prompt return of evaluated papers (MID-07/Receipt) with annotated solution keys.")
    if comments:
        action_lines.append("3. Cohort Feedback Integration: Address student recommendations regarding laboratory guides and consultation scheduling in next offering's Part IX Learning Plan.")
    else:
        action_lines.append("3. Resource Enhancement: Update Part X references and digital handouts ahead of next academic year same-semester offering.")

    revisit_date, revisit_term = compute_cqi_revisit_schedule(data["semester_ay"])
    kpi_lines = [
        f"• Achieve >= 75.0% cohort CLO attainment across all CLOs (especially {', '.join(targeted_clos) or 'all outcomes'}) by {revisit_term}.",
        "• Attain Student Course Exit Survey mean rating >= 4.00 / 5.00 across all 4 CQI categories.",
        "• Improve bottleneck summative assessment passing rate to >= 80.0% upon next academic year re-evaluation.",
    ]

    # Auto-mark systematic CQI indicators (Categories I-IV)
    def _anchor_ok(substr: str, fallback: bool = True) -> str:
        matches = [v.get("avg_rating") for k, v in anchors.items() if substr in k and v.get("avg_rating") is not None]
        if matches:
            return "✓" if (sum(matches) / len(matches)) >= 3.7 else "✗"
        return "✓" if fallback else "✗"

    bp_inds = (course_doc.get("blueprint") or {}).get("cqi_plan", {}).get("indicators") or []
    base_titles = [
        ("Category I: Instructional Delivery & Pacing", "Topics covered within allocated weekly timeline", _anchor_ok("delivery", not bool(unmet)), "Correlated with Exit Survey delivery & pacing ratings."),
        ("Category II: Assessment & TOS Alignment", "Summative & formative tools accurately measured CLOs", _anchor_ok("assessment", not bool(bottlenecks)), "Correlated with Step 4 bottleneck analysis & rubric feedback."),
        ("Category III: Learning Resources & Facilities", "References, lab tools & manuals adequate for cohort", _anchor_ok("resource", True), "Based on student resource/lab survey ratings."),
        ("Category IV: Feedback & Student Support", "Consultation & timely return of evaluated outputs", _anchor_ok("feedback", True), "Correlated with student feedback & Receipt of Scores tracking."),
    ]
    indicators = []
    for idx, (cat_lbl, ttl, mrk, rmk) in enumerate(base_titles):
        sub = bp_inds[idx].get("subtitle", "") if idx < len(bp_inds) else ""
        indicators.append({
            "number": idx + 1,
            "category": cat_lbl,
            "title": ttl,
            "subtitle": sub,
            "mark": mrk,
            "remarks": rmk,
        })

    draft = {
        "engine": "rule_based_three_source_correlation",
        "targeted_clos": targeted_clos,
        "key_strengths": "\n".join(strength_lines),
        "areas_for_improvement": "\n".join(impr_lines),
        "gap_analysis": "\n".join(gap_lines),
        "root_causes": "\n".join(root_lines),
        "action_plan": "\n".join(action_lines),
        "target_kpis": "\n".join(kpi_lines),
        "indicators": indicators,
        "revisit_date": revisit_date,
        "revisit_term": revisit_term,
        "three_source_summary": data,
    }

    # Optional Gemini AI polish if requested and key configured
    api_key = str(gemini_api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if use_ai and api_key:
        try:
            import requests
            prompt = (
                "You are an engineering OBE (Outcome-Based Education) Continuous Quality Improvement specialist at USeP.\n"
                "Synthesize the following three-source course assessment summary (Step 4 Class Record, Step 7 MID-10 CLO Attainment, "
                "and Student Portal Course Exit Survey) into concise, evidence-based academic text.\n"
                f"Data JSON:\n{json.dumps({'course': c_code, 'clos': clo_corr, 'bottlenecks': bottlenecks, 'survey_overall': srv.get('overall_avg_rating'), 'anchors': anchors, 'challenging_topics': challenging[:5], 'comments': [cm.get('comment') for cm in comments[:5]]}, ensure_ascii=False)}\n\n"
                "Return ONLY valid JSON with string keys: key_strengths, areas_for_improvement, gap_analysis, root_causes, action_plan, target_kpis."
            )
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=35,
            )
            if resp.ok:
                txt = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.IGNORECASE).strip()
                ai_json = json.loads(txt)
                if isinstance(ai_json, dict):
                    for k in ("key_strengths", "areas_for_improvement", "gap_analysis", "root_causes", "action_plan", "target_kpis"):
                        if ai_json.get(k):
                            draft[k] = str(ai_json[k]).strip()
                    draft["engine"] = "gemini_ai_assisted"
        except Exception:
            pass

    return draft
