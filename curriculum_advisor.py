"""
Curriculum Guide AI Agent & Academic Advising Engine.

Provides graph-aware academic advising for undergraduate engineering programs
(e.g., BSEE from PGO-PI-IGA.accdb and other engineering curricula from academic_catalog.db).
Computes exact dependency impact for failed courses, blocked vs. eligible subjects,
retake priorities, credit load guidelines, and visual flowchart highlight actions.
Runs natively on a deterministic local graph-traversal engine, so it works
without any external LLM API key, network access, or rate-limit dependency.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple

import curriculum_flowchart

logger = logging.getLogger(__name__)


def normalize_code(code: str) -> str:
    """Normalizes course codes to clean uppercase form with consistent spacing."""
    if not code:
        return ""
    c = code.strip().upper()
    # Normalize e.g. "EE211" -> "EE 211", "MATH121" -> "MATH 121"
    m = re.match(r"^([A-Z]{2,5})\s*(\d{2,4}[A-Z]?\*?)$", c)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return c


def extract_course_codes(text: str, valid_codes: Optional[Set[str]] = None) -> List[str]:
    """Extracts course code candidates from natural language query."""
    if not text:
        return []
    # Pattern matching typical course codes like EE 211, Math 121, BES 101, etc.
    pat = re.compile(r"\b([A-Za-z]{2,5}\s*\d{2,4}[A-Za-z]?\*?)\b")
    matches = pat.findall(text)
    results: List[str] = []
    seen: Set[str] = set()

    # 1. Direct scan for every valid curriculum code (handles multi-word codes such as
    #    "Nat Sci 2" and spacing/case variants such as "ee211" or "math 121").
    if valid_codes:
        positioned: List[Tuple[int, str]] = []
        for vc in valid_codes:
            if not vc:
                continue
            parts = [re.escape(p) for p in re.split(r"\s+", vc.strip()) if p]
            if not parts:
                continue
            vc_pat = r"(?<![A-Za-z0-9])" + r"\s*".join(parts) + r"(?![A-Za-z0-9])"
            hit = re.search(vc_pat, text, flags=re.IGNORECASE)
            if hit:
                positioned.append((hit.start(), vc))
        for _, vc in sorted(positioned):
            if vc not in seen:
                seen.add(vc)
                results.append(vc)

    for m in matches:
        norm = normalize_code(m)
        if valid_codes:
            # Check direct or case-insensitive match against valid codes in graph
            matched_code = None
            for vc in valid_codes:
                if normalize_code(vc) == norm:
                    matched_code = vc
                    break
            if matched_code and matched_code not in seen:
                seen.add(matched_code)
                results.append(matched_code)
        else:
            if norm not in seen:
                seen.add(norm)
                results.append(norm)

    return results


def find_all_downstream_blocked(failed_codes: List[str], courses_by_code: Dict[str, Dict[str, Any]]) -> Tuple[Set[str], Dict[str, List[str]]]:
    """
    Recursively discovers all courses blocked (directly and transitively) by failed courses.
    Returns:
      (blocked_set, reasons_map)
      where reasons_map maps blocked course code -> list of explanation strings.
    """
    blocked: Set[str] = set()
    reasons: Dict[str, List[str]] = {}
    failed_norm = {normalize_code(c) for c in failed_codes}

    queue: List[str] = list(failed_codes)
    visited: Set[str] = set(queue)

    while queue:
        curr_code = queue.pop(0)
        curr_norm = normalize_code(curr_code)
        curr_course = None
        for code, c_data in courses_by_code.items():
            if normalize_code(code) == curr_norm:
                curr_course = c_data
                break

        # Check all courses that have curr_code as a prerequisite or co-requisite
        for target_code, target_data in courses_by_code.items():
            target_norm = normalize_code(target_code)
            if target_norm in failed_norm:
                continue

            prereqs_norm = [normalize_code(p) for p in target_data.get("prerequisites", [])]
            coreqs_norm = [normalize_code(co) for co in target_data.get("corequisites", [])]

            is_blocked = False
            reason_text = ""

            if curr_norm in prereqs_norm:
                is_blocked = True
                if curr_norm in failed_norm:
                    reason_text = f"Requires failed prerequisite {curr_code}"
                else:
                    reason_text = f"Prerequisite {curr_code} is blocked downstream"
            elif curr_norm in coreqs_norm:
                is_blocked = True
                reason_text = f"Concurrent co-requisite {curr_code} is unavailable"

            if is_blocked:
                blocked.add(target_code)
                if target_code not in reasons:
                    reasons[target_code] = []
                if reason_text not in reasons[target_code]:
                    reasons[target_code].append(reason_text)

                if target_code not in visited:
                    visited.add(target_code)
                    queue.append(target_code)

    return blocked, reasons


def determine_next_term(term_key: str, terms: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Finds the chronological next term in the curriculum roadmap."""
    keys_order = [t["key"] for t in terms]
    if term_key not in keys_order:
        # Fallback to standard term sequence
        standard = ["Y1S1", "Y1S2", "Y1Mid", "Y2S1", "Y2S2", "Y2Mid", "Y3S1", "Y3S2", "Y4S1", "Y4S2"]
        if term_key in standard:
            idx = standard.index(term_key)
            for next_k in standard[idx + 1:]:
                match = next((t for t in terms if t["key"] == next_k), None)
                if match:
                    return match
        return None

    idx = keys_order.index(term_key)
    if idx + 1 < len(terms):
        return terms[idx + 1]
    return None


def parse_credit_units(units_val: Any) -> float:
    """Extracts numeric credit units from string or float."""
    if isinstance(units_val, (int, float)):
        return float(units_val)
    m = re.search(r"(\d+(\.\d+)?)", str(units_val or ""))
    return float(m.group(1)) if m else 3.0


def analyze_failed_courses(failed_codes: List[str], program_code: str = "BSEE") -> Dict[str, Any]:
    """
    Core Advising Engine:
    Computes exact blocked courses, eligible next-term courses, and retake study load recommendations.
    """
    flowchart_data = curriculum_flowchart.get_curriculum_flowchart_data(program_code)
    courses = flowchart_data.get("courses", [])
    terms = flowchart_data.get("terms", [])
    courses_by_code: Dict[str, Dict[str, Any]] = {c["code"]: c for c in courses}

    # Match failed courses against the curriculum
    matched_failed: List[Dict[str, Any]] = []
    failed_keys: Set[str] = set()

    for fc in failed_codes:
        norm = normalize_code(fc)
        matched = None
        for code, data in courses_by_code.items():
            if normalize_code(code) == norm:
                matched = data
                break
        if matched:
            matched_failed.append(matched)
            failed_keys.add(matched["code"])

    if not matched_failed:
        return {
            "intent": "failed_course_not_found",
            "message": f"Could not find course '{', '.join(failed_codes)}' in the {program_code} curriculum graph.",
            "highlight_action": {"blocked": [], "eligible": [], "retake": []}
        }

    # Find all blocked courses across entire curriculum
    blocked_codes, reasons_map = find_all_downstream_blocked(list(failed_keys), courses_by_code)

    # Determine highest term among failed courses to pinpoint next target term
    term_rank = {t["key"]: i for i, t in enumerate(terms)}
    highest_term_key = "Y1S1"
    highest_rank = -1
    for fc in matched_failed:
        # Locate term for fc
        for t in terms:
            if any(normalize_code(c["code"]) == normalize_code(fc["code"]) for c in t["courses"]):
                r = term_rank.get(t["key"], 0)
                if r > highest_rank:
                    highest_rank = r
                    highest_term_key = t["key"]
                break

    next_term = determine_next_term(highest_term_key, terms)
    if not next_term and terms:
        # Fallback to last term or next semester
        next_term = terms[-1]

    # Evaluate courses scheduled in target next term
    target_term_courses = next_term.get("courses", []) if next_term else []
    blocked_in_target: List[Dict[str, Any]] = []
    eligible_in_target: List[Dict[str, Any]] = []

    for tc in target_term_courses:
        tc_code = tc["code"]
        u_val = parse_credit_units(tc.get("credit_units"))
        if tc_code in blocked_codes:
            blocked_in_target.append({
                "code": tc_code,
                "title": tc.get("title", ""),
                "credit_units": u_val,
                "reasons": reasons_map.get(tc_code, ["Prerequisite unfulfilled"])
            })
        else:
            # Check if all other prerequisites are satisfied
            prereqs = tc.get("prerequisites", [])
            unsatisfied = [p for p in prereqs if normalize_code(p) in {normalize_code(c) for c in failed_keys}]
            if unsatisfied:
                blocked_in_target.append({
                    "code": tc_code,
                    "title": tc.get("title", ""),
                    "credit_units": u_val,
                    "reasons": [f"Prerequisite {p} was not passed" for p in unsatisfied]
                })
            else:
                eligible_in_target.append({
                    "code": tc_code,
                    "title": tc.get("title", ""),
                    "credit_units": u_val,
                    "prerequisites": prereqs,
                    "corequisites": tc.get("corequisites", [])
                })

    # Other future blocked courses outside the immediate next term
    future_blocked: List[Dict[str, Any]] = []
    for bc in blocked_codes:
        if not any(b["code"] == bc for b in blocked_in_target):
            b_course = courses_by_code.get(bc, {})
            future_blocked.append({
                "code": bc,
                "title": b_course.get("title", ""),
                "year_level": b_course.get("year_level", ""),
                "semester": b_course.get("semester", ""),
                "credit_units": parse_credit_units(b_course.get("credit_units")),
                "reasons": reasons_map.get(bc, [])
            })

    # Retake recommendations
    retake_list = []
    retake_units_total = 0.0
    for fc in matched_failed:
        u = parse_credit_units(fc.get("credit_units"))
        retake_units_total += u
        # Count downstream impact
        direct_post = fc.get("postrequisites", [])
        retake_list.append({
            "code": fc["code"],
            "title": fc["title"],
            "credit_units": u,
            "year_level": fc.get("year_level"),
            "semester": fc.get("semester"),
            "direct_postrequisites": direct_post,
            "total_downstream_blocked": len(blocked_codes),
            "priority": "CRITICAL" if len(blocked_codes) > 0 else "NORMAL"
        })

    eligible_units_total = sum(c["credit_units"] for c in eligible_in_target)
    recommended_total_units = retake_units_total + eligible_units_total
    max_regular_load = 23.0

    # Build rich advising narrative markdown
    lines = []
    failed_titles = ", ".join([f"**{f['code']}** ({f['title']})" for f in matched_failed])
    lines.append(f"### 📋 Academic Advising Report: Failed Course Impact\n")
    lines.append(f"**Program:** {flowchart_data.get('program_title')} (`{program_code}`)\n")
    lines.append(f"**Failed Course(s):** {failed_titles}\n")

    # 1. Blocked Courses
    lines.append(f"#### ⛔ 1. Blocked Courses for Upcoming Term ({next_term.get('label', 'Next Semester')})")
    if blocked_in_target:
        lines.append(f"You **cannot enroll** in the following **{len(blocked_in_target)} course(s)** next semester because their required prerequisites or co-requisites are unfulfilled:\n")
        for b in blocked_in_target:
            reason_str = "; ".join(b["reasons"])
            lines.append(f"- 🔴 **{b['code']}**: {b['title']} (*{b['credit_units']} units*) — `{reason_str}`")
    else:
        lines.append(f"Good news! None of the courses directly scheduled in **{next_term.get('label')}** require the failed subject as a strict prerequisite.")

    if future_blocked:
        lines.append(f"\n*⚠️ Downstream Cascading Impact:* Failing {', '.join(failed_keys)} also transitively blocks **{len(future_blocked)} future course(s)** in subsequent years (e.g., {', '.join([f['code'] for f in future_blocked[:6]])}{'...' if len(future_blocked) > 6 else ''}).\n")

    # 2. Available / Eligible Courses
    lines.append(f"#### ✅ 2. Eligible Courses You Can Take ({next_term.get('label', 'Next Semester')})")
    if eligible_in_target:
        lines.append(f"You **are cleared and eligible** to enroll in **{len(eligible_in_target)} course(s)** ({eligible_units_total:.1f} units total) whose prerequisites and standing are satisfied:\n")
        for e in eligible_in_target:
            lines.append(f"- 🟢 **{e['code']}**: {e['title']} (*{e['credit_units']} units*)")
    else:
        lines.append(f"No regular courses in {next_term.get('label')} meet the prerequisite requirements at this time.")

    # 3. Retake & Study Load Advice
    lines.append(f"\n#### 💡 3. Retake Recommendation & Study Load Guidance")
    for r in retake_list:
        lines.append(f"- 🔄 **Prioritize Retake of {r['code']}** (*{r['credit_units']} units*): This course directly unlocks **{len(r['direct_postrequisites'])} immediate course(s)** and **{r['total_downstream_blocked']} total downstream courses**. Retaking it next term prevents multi-semester graduation delays.")

    lines.append(f"\n**Suggested Study Load for {next_term.get('label')}:**")
    lines.append(f"- **Retake Courses:** {retake_units_total:.1f} units")
    lines.append(f"- **Eligible Regular Courses:** {eligible_units_total:.1f} units")
    lines.append(f"- **Total Recommended Load:** **{recommended_total_units:.1f} units** (Regular limit: {max_regular_load:.1f} units)")

    if recommended_total_units > max_regular_load:
        lines.append(f"⚠️ *Load Notice:* The combined total of {recommended_total_units:.1f} units exceeds the maximum regular limit of {max_regular_load:.1f} units. Consult your Academic Advisor / Department Chair to drop 1-2 non-prerequisite general education or elective courses to prioritize your major retake.")
    else:
        lines.append(f"✅ *Healthy Study Load:* Your combined total of {recommended_total_units:.1f} units fits comfortably within the university's maximum regular load.")

    highlight_action = {
        "blocked": [b["code"] for b in blocked_in_target] + [f["code"] for f in future_blocked],
        "eligible": [e["code"] for e in eligible_in_target],
        "retake": [r["code"] for r in retake_list],
        "failed": list(failed_keys)
    }

    return {
        "success": True,
        "intent": "failed_course_impact",
        "program_code": program_code,
        "failed_courses": matched_failed,
        "target_term": next_term,
        "blocked_courses_target": blocked_in_target,
        "future_blocked_courses": future_blocked,
        "eligible_courses_target": eligible_in_target,
        "retake_recommendations": retake_list,
        "study_load": {
            "eligible_units": eligible_units_total,
            "retake_units": retake_units_total,
            "recommended_total_units": recommended_total_units,
            "max_regular_load": max_regular_load,
            "overloaded": recommended_total_units > max_regular_load
        },
        "highlight_action": highlight_action,
        "advice_markdown": "\n".join(lines)
    }


def analyze_prerequisite_inquiry(course_code: str, program_code: str = "BSEE") -> Dict[str, Any]:
    """Answers prerequisite, co-requisite, and standing inquiries for a course."""
    details = curriculum_flowchart.get_course_details(course_code, program_code)
    if not details:
        return {
            "intent": "course_not_found",
            "message": f"Course '{course_code}' was not found in the {program_code} curriculum.",
            "highlight_action": {"blocked": [], "eligible": [], "retake": []}
        }

    lines = []
    lines.append(f"### 🔍 Course Dependency Inspector: **{details['code']}**\n")
    lines.append(f"**Title:** {details.get('title')}\n")
    lines.append(f"**Curriculum Placement:** {details.get('year_level')} • {details.get('semester')}\n")
    lines.append(f"**Credit Units:** {details.get('credit_units')} ({details.get('lec_lab', 'Lecture')})\n")
    lines.append(f"**Year Level Requirement:** 🎓 **{details.get('year_level_requirement', '1st Year Standing / Regular Standing')}**\n")

    prereqs = details.get("prerequisites", [])
    coreqs = details.get("corequisites", [])
    postreqs = details.get("postrequisites", [])

    lines.append("#### ⬆️ Pre-requisites (Must be passed prior):")
    if prereqs:
        for p in prereqs:
            lines.append(f"- 📌 **{p}**")
    else:
        lines.append("- *None (Direct entry subject)*")

    lines.append("\n#### ↔️ Co-requisites (Concurrent enrollment):")
    if coreqs:
        for co in coreqs:
            lines.append(f"- 🔗 **{co}**")
    else:
        lines.append("- *None*")

    lines.append("\n#### ⬇️ Post-requisites (Subsequent courses unlocked):")
    if postreqs:
        for po in postreqs:
            lines.append(f"- 🚀 **{po}**")
    else:
        lines.append("- *None (Terminal or elective course)*")

    highlight_action = {
        "blocked": [],
        "eligible": prereqs + coreqs,
        "retake": [details["code"]],
        "target": [details["code"]],
        "prereqs": prereqs,
        "coreqs": coreqs,
        "postreqs": postreqs
    }

    return {
        "success": True,
        "intent": "prerequisite_inquiry",
        "course": details,
        "highlight_action": highlight_action,
        "advice_markdown": "\n".join(lines)
    }


def query_curriculum_guide_agent(
    query: str,
    program_code: str = "BSEE",
    history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Resilient public entrypoint for the Curriculum Guide AI Agent.

    Sanitizes inputs, executes the deterministic local curriculum graph-traversal
    engine (no external LLM is required), and normalizes every response so the
    frontend always receives ``success``, ``intent``, ``advice_markdown`` and a
    complete ``highlight_action`` payload. Any unexpected exception is caught and
    converted into a safe, user-readable advising reply instead of an HTTP error.
    """
    q = query if isinstance(query, str) else ("" if query is None else str(query))
    prog = program_code if isinstance(program_code, str) else ""
    prog = prog.strip().upper() or "BSEE"
    hist = history if isinstance(history, list) else []

    try:
        res = _query_curriculum_guide_agent_core(q, program_code=prog, history=hist)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Curriculum Guide AI Agent failed for query %r: %s", q, exc)
        res = {
            "intent": "engine_fallback",
            "advice_markdown": (
                "⚠️ I couldn't fully analyze that question against the curriculum graph.\n\n"
                "Please mention a specific course code, for example:\n"
                "- *'What courses can I take next semester if I failed EE 211?'*\n"
                "- *'What are the prerequisites for EE 415?'*"
            ),
        }

    if not isinstance(res, dict):
        res = {"intent": "general_guidance", "advice_markdown": str(res or "")}

    if not res.get("advice_markdown"):
        res["advice_markdown"] = res.get("message") or (
            "I couldn't find a matching answer. Try asking about a specific course code "
            "(e.g., *'What happens if I fail EE 211?'*)."
        )

    hl = res.get("highlight_action")
    if not isinstance(hl, dict):
        hl = {}
    for key in ("blocked", "eligible", "retake"):
        if not isinstance(hl.get(key), list):
            hl[key] = []
    res["highlight_action"] = hl
    res.setdefault("intent", "general_guidance")
    res.setdefault("program_code", prog)
    res["success"] = True
    res["engine"] = "local_graph_traversal"
    return res


def _query_curriculum_guide_agent_core(
    query: str,
    program_code: str = "BSEE",
    history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Core deterministic engine for the Curriculum Guide AI Agent.
    Interprets user intent, executes deterministic graph reasoning,
    and returns rich academic advice with flowchart highlight actions.
    """
    q_lower = (query or "").strip().lower()
    if not q_lower:
        return {
            "intent": "empty_query",
            "advice_markdown": "Please enter a question about your curriculum, prerequisites, or failed course scenario.",
            "highlight_action": {"blocked": [], "eligible": [], "retake": []}
        }

    flowchart_data = curriculum_flowchart.get_curriculum_flowchart_data(program_code) or {}
    courses = flowchart_data.get("courses", []) or []
    if not courses:
        return {
            "intent": "program_not_found",
            "advice_markdown": f"⚠️ No curriculum data is available for program `{program_code}`. Please select a valid program on the flowchart.",
            "highlight_action": {"blocked": [], "eligible": [], "retake": []}
        }
    valid_codes = {c.get("code") for c in courses if c.get("code")}

    extracted_codes = extract_course_codes(query, valid_codes)

    # 1. Check for Failed Course Impact Intent
    failure_keywords = ["fail", "failed", "failing", "flunk", "didn't pass", "did not pass", "conditional", "drop", "dropped", "next sem", "next semester"]
    is_failure_query = any(k in q_lower for k in failure_keywords)

    if is_failure_query or (extracted_codes and any(k in q_lower for k in ["what can i take", "can i take", "what happen", "what if"])):
        if not extracted_codes:
            # Try searching by title keywords (e.g. circuits 1)
            for c in courses:
                t_lower = c.get("title", "").lower()
                if len(t_lower) > 4 and t_lower in q_lower:
                    extracted_codes.append(c["code"])
                    break

        if extracted_codes:
            return analyze_failed_courses(extracted_codes, program_code=program_code)
        else:
            return {
                "intent": "failed_course_missing_code",
                "advice_markdown": "⚠️ Please specify which course code you failed or are inquiring about (e.g., `EE 211`, `Math 121`, or `BES 101`).",
                "highlight_action": {"blocked": [], "eligible": [], "retake": []}
            }

    # 2. Check for Specific Course Prerequisite / Description Intent
    if extracted_codes:
        target = extracted_codes[0]
        return analyze_prerequisite_inquiry(target, program_code=program_code)

    # 3. Check for Standing / Year Level Rules Inquiry
    if any(k in q_lower for k in ["standing", "year level", "requirement", "units", "graduation", "load"]):
        stats = flowchart_data.get("stats", {})
        terms = flowchart_data.get("terms", [])
        lines = [
            f"### 🎓 Curriculum Standing & Academic Load Policy\n",
            f"**Program:** {flowchart_data.get('program_title')} (`{program_code}`)\n",
            f"- **Total Curriculum Courses:** {stats.get('total_courses', 0)} courses",
            f"- **Total Credit Units:** {stats.get('total_credit_units', 0.0)} units",
            f"- **Maximum Normal Load:** 23.0 units per regular semester\n",
            "#### Year Level Standing Requirements:",
            "- 🎓 **1st Year Standing / Regular Standing:** Clear admission / enrolled in first-year subjects.",
            "- 🎓 **2nd Year Standing:** Satisfactory completion of foundational Math & Natural Science subjects (e.g., Math 121, Nat Sci 1 & 2).",
            "- 🎓 **3rd Year Standing:** Completion of second-year engineering circuits and applied mathematics (EE 211, Math 211, Math 221).",
            "- 🎓 **4th Year Standing:** Clear standing across all 1st through 3rd-year major requirements; mandatory prerequisite for Capstone Design (EE 414L) and On-the-Job Training / Practicum (EE 400).",
            "\n💡 *Tip:* Ask me about any specific course to check its individual Year Level Requirement (e.g., *'What is required for EE 414?'*)."
        ]
        return {
            "intent": "general_curriculum_info",
            "advice_markdown": "\n".join(lines),
            "highlight_action": {"blocked": [], "eligible": [], "retake": []}
        }

    # 4. Default Guidance
    return {
        "intent": "general_guidance",
        "advice_markdown": (
            "👋 **Curriculum Guide AI Agent Ready!**\n\n"
            "I can assist with academic advising and graph dependency analysis for your program. Try asking:\n"
            "- *'What courses can I take next semester if I failed EE 211?'*\n"
            "- *'What happens if I fail Math 121 in 1st year?'*\n"
            "- *'What are the prerequisites for EE 415?'*\n"
            "- *'Which subjects are unlocked by EE 221?'*"
        ),
        "highlight_action": {"blocked": [], "eligible": [], "retake": []}
    }
