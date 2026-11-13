# -*- coding: utf-8 -*-
"""
Course Delivery Gantt Chart (Ideal vs. Actual Timeline) Module
==============================================================
Manages 18-week instructional delivery schedules, weekly capacity calculations
(1 hr/unit Lecture, 3 hrs/unit Laboratory), Philippine regular and special
holidays, local Davao City holidays, custom non-class suspensions/leaves,
and dual-timeline (Ideal vs. Actual) topic completion tracking.
"""

import re
import datetime
from typing import Dict, List, Any, Optional, Tuple


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Philippine Holidays & Davao City Non-Working Days
# ---------------------------------------------------------------------------

def compute_easter_sunday(year: int) -> datetime.date:
    """Computes Easter Sunday for a given year using the Anonymous Gregorian algorithm (Meeus/Jones/Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def get_last_monday_of_month(year: int, month: int) -> datetime.date:
    """Finds the last Monday of the given month and year (e.g. National Heroes Day in August)."""
    # Start from last day of month and walk backwards
    if month == 12:
        next_month_first = datetime.date(year + 1, 1, 1)
    else:
        next_month_first = datetime.date(year, month + 1, 1)
    last_day = next_month_first - datetime.timedelta(days=1)
    offset = (last_day.weekday() - 0) % 7  # 0 is Monday
    return last_day - datetime.timedelta(days=offset)


def get_kadayawan_indigenous_peoples_day(year: int) -> datetime.date:
    """
    Kadayawan Indigenous Peoples Day / Thanksgiving in Davao City:
    Observed on the 3rd Friday of August.
    """
    aug1 = datetime.date(year, 8, 1)
    # 4 is Friday
    days_to_first_friday = (4 - aug1.weekday()) % 7
    first_friday = aug1 + datetime.timedelta(days=days_to_first_friday)
    third_friday = first_friday + datetime.timedelta(weeks=2)
    return third_friday


def get_philippine_holidays(year: int) -> List[Dict[str, Any]]:
    """
    Returns pre-populated National Philippine Regular, Special Non-Working,
    and official Local Davao City holidays for the specified calendar year.
    """
    easter = compute_easter_sunday(year)
    maundy_thursday = easter - datetime.timedelta(days=3)
    good_friday = easter - datetime.timedelta(days=2)
    black_saturday = easter - datetime.timedelta(days=1)
    natl_heroes_day = get_last_monday_of_month(year, 8)
    kadayawan_day = get_kadayawan_indigenous_peoples_day(year)

    holidays = [
        # Regular National Holidays
        {
            "id": f"ph_{year}_0101",
            "date": f"{year}-01-01",
            "name": "New Year's Day",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_maundy",
            "date": maundy_thursday.strftime("%Y-%m-%d"),
            "name": "Maundy Thursday",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": False,
        },
        {
            "id": f"ph_{year}_goodfri",
            "date": good_friday.strftime("%Y-%m-%d"),
            "name": "Good Friday",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": False,
        },
        {
            "id": f"ph_{year}_0409",
            "date": f"{year}-04-09",
            "name": "Araw ng Kagitingan (Day of Valor)",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_0501",
            "date": f"{year}-05-01",
            "name": "Labor Day",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_0612",
            "date": f"{year}-06-12",
            "name": "Independence Day",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_heroes",
            "date": natl_heroes_day.strftime("%Y-%m-%d"),
            "name": "National Heroes Day",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": False,
        },
        {
            "id": f"ph_{year}_1130",
            "date": f"{year}-11-30",
            "name": "Bonifacio Day",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_1225",
            "date": f"{year}-12-25",
            "name": "Christmas Day",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_1230",
            "date": f"{year}-12-30",
            "name": "Rizal Day",
            "type": "regular",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },

        # Special Non-Working National Holidays
        {
            "id": f"ph_{year}_blacksat",
            "date": black_saturday.strftime("%Y-%m-%d"),
            "name": "Black Saturday",
            "type": "special_non_working",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": False,
        },
        {
            "id": f"ph_{year}_0821",
            "date": f"{year}-08-21",
            "name": "Ninoy Aquino Day",
            "type": "special_non_working",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_1101",
            "date": f"{year}-11-01",
            "name": "All Saints' Day",
            "type": "special_non_working",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_1102",
            "date": f"{year}-11-02",
            "name": "All Souls' Day",
            "type": "special_non_working",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_1208",
            "date": f"{year}-12-08",
            "name": "Feast of the Immaculate Conception of Mary",
            "type": "special_non_working",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_1224",
            "date": f"{year}-12-24",
            "name": "Christmas Eve",
            "type": "special_non_working",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_1231",
            "date": f"{year}-12-31",
            "name": "Last Day of the Year",
            "type": "special_non_working",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },
        {
            "id": f"ph_{year}_0225",
            "date": f"{year}-02-25",
            "name": "EDSA People Power Revolution Anniversary",
            "type": "special_non_working",
            "category": "national_holiday",
            "scope": "National",
            "is_fixed": True,
        },

        # Local Davao City Holidays
        {
            "id": f"davao_{year}_araw",
            "date": f"{year}-03-01",
            "name": "Araw ng Dabaw (Davao City Charter Day)",
            "type": "local_davao",
            "category": "davao_holiday",
            "scope": "Davao City",
            "is_fixed": True,
        },
        {
            "id": f"davao_{year}_kadayawan",
            "date": kadayawan_day.strftime("%Y-%m-%d"),
            "name": "Indigenous Peoples Day (Kadayawan Festival)",
            "type": "local_davao",
            "category": "davao_holiday",
            "scope": "Davao City",
            "is_fixed": False,
        },
    ]

    holidays.sort(key=lambda x: x["date"])
    return holidays


# ---------------------------------------------------------------------------
# Weekly Contact-Hours & Capacity Calculation
# ---------------------------------------------------------------------------

def calculate_weekly_contact_hours(lec_units: float, lab_units: float) -> Dict[str, float]:
    """
    Computes weekly contact hours according to CHED / OBE policy:
    - Lecture: 1 hour/week per Lecture unit
    - Laboratory: 3 hours/week per Laboratory unit
    - Total = (Lec Units * 1) + (Lab Units * 3)
    """
    lec = max(0.0, float(lec_units or 0.0))
    lab = max(0.0, float(lab_units or 0.0))
    lec_hours = lec * 1.0
    lab_hours = lab * 3.0
    total_hours = lec_hours + lab_hours
    return {
        "lecture_units": lec,
        "lab_units": lab,
        "lecture_hours_per_week": lec_hours,
        "lab_hours_per_week": lab_hours,
        "total_hours_per_week": total_hours if total_hours > 0 else 3.0,
    }


def parse_course_credit_units(metadata: Dict[str, Any]) -> Dict[str, float]:
    """
    Extracts lecture and laboratory units from metadata fields or parses credit_units string.
    Strictly calculates weekly contact hours based on official formula:
      - 1 Unit Lecture = 1 Hour/week (Weekly Lecture Hours = Lecture Units * 1)
      - 1 Unit Laboratory = 3 Hours/week (Weekly Lab Hours = Lab Units * 3)
      - Total Weekly Contact Hours = (Lecture Units * 1) + (Lab Units * 3)
    """
    cred_str = str(metadata.get("credit_units") or "").strip()
    contact_str = str(metadata.get("contact_hours") or "").strip()
    course_code = str(metadata.get("course_code") or "").strip()

    # 1. Check contact_hours for explicit lecture and laboratory breakdown
    # e.g., "5 Hours/Week (2 hours Lecture, 3 hours Lab)"
    m_ch_lec = re.search(r"(\d+(?:\.\d+)?)\s*(?:hrs?|hours?)?\s*(?:lec|lecture)", contact_str, re.IGNORECASE)
    m_ch_lab = re.search(r"(\d+(?:\.\d+)?)\s*(?:hrs?|hours?)?\s*(?:lab|laboratory)", contact_str, re.IGNORECASE)
    if m_ch_lec and m_ch_lab:
        try:
            lec_hrs = float(m_ch_lec.group(1))
            lab_hrs = float(m_ch_lab.group(1))
            lec_u = lec_hrs / 1.0
            lab_u = lab_hrs / 3.0
            return calculate_weekly_contact_hours(lec_u, lab_u)
        except Exception:
            pass

    # 2. Check credit_units for explicit breakdown: e.g. "4.0 Units (3.0 Lec, 1.0 Lab)" or "2.0 Units – Lecture"
    m_combo_lec = re.search(r"(\d+(?:\.\d+)?)\s*(?:unit[s]?\s*)?[–\-:]?\s*(?:lec|lecture)\b", cred_str, re.IGNORECASE)
    m_combo_lab = re.search(r"(\d+(?:\.\d+)?)\s*(?:unit[s]?\s*)?[–\-:]?\s*(?:lab|laboratory)\b", cred_str, re.IGNORECASE)

    if not m_combo_lec:
        m_combo_lec = re.search(r"(?:lec|lecture)[–\-:\s]*(\d+(?:\.\d+)?)", cred_str, re.IGNORECASE)
    if not m_combo_lab:
        m_combo_lab = re.search(r"(?:lab|laboratory)[–\-:\s]*(\d+(?:\.\d+)?)", cred_str, re.IGNORECASE)

    lower_cred = cred_str.lower()
    has_lec = "lec" in lower_cred
    has_lab = "lab" in lower_cred

    if m_combo_lec and m_combo_lab:
        try:
            return calculate_weekly_contact_hours(float(m_combo_lec.group(1)), float(m_combo_lab.group(1)))
        except Exception:
            pass
    elif m_combo_lec and not has_lab:
        try:
            return calculate_weekly_contact_hours(float(m_combo_lec.group(1)), 0.0)
        except Exception:
            pass
    elif m_combo_lab and not has_lec:
        try:
            return calculate_weekly_contact_hours(0.0, float(m_combo_lab.group(1)))
        except Exception:
            pass

    # 3. Direct metadata fields if present and valid
    lec_units = metadata.get("lecture_units")
    lab_units = metadata.get("lab_units")
    if lec_units is not None or lab_units is not None:
        try:
            lec_val = float(lec_units) if lec_units is not None else 0.0
            lab_val = float(lab_units) if lab_units is not None else 0.0
            if lec_val > 0 or lab_val > 0:
                return calculate_weekly_contact_hours(lec_val, lab_val)
        except (ValueError, TypeError):
            pass

    # 4. Catalog lookup fallback by course code
    if course_code:
        try:
            import catalog_data
            cat = catalog_data.get_full_catalog()
            for col in cat.get("colleges", []):
                for dept in col.get("departments", []):
                    for c in dept.get("courses", []):
                        if c.get("code") == course_code:
                            c_lec = c.get("lecture_units")
                            c_lab = c.get("lab_units")
                            if c_lec is not None and c_lab is not None:
                                return calculate_weekly_contact_hours(float(c_lec), float(c_lab))
        except Exception:
            pass

    parsed_lec = 0.0
    parsed_lab = 0.0
    if m_combo_lec:
        try:
            parsed_lec = float(m_combo_lec.group(1))
        except Exception:
            pass
    if m_combo_lab:
        try:
            parsed_lab = float(m_combo_lab.group(1))
        except Exception:
            pass

    lower_cred = cred_str.lower()
    has_lec = "lec" in lower_cred
    has_lab = "lab" in lower_cred

    # If both lec and lab are in cred_str, only accept if BOTH parsed numbers were found
    # (otherwise a single leading number like "4.0 Units – Lecture and Laboratory" is the combined total)
    if parsed_lec > 0 and parsed_lab > 0:
        return calculate_weekly_contact_hours(parsed_lec, parsed_lab)
    elif not (has_lec and has_lab):
        if parsed_lec > 0:
            return calculate_weekly_contact_hours(parsed_lec, 0.0)
        if parsed_lab > 0:
            return calculate_weekly_contact_hours(0.0, parsed_lab)

    # Parse numeric total and evaluate lecture vs laboratory combination
    m_num = re.search(r"(\d+(?:\.\d+)?)", cred_str)
    val = float(m_num.group(1)) if m_num else 3.0

    if has_lec and has_lab:
        # Combined lecture and laboratory course
        if val >= 4.0:
            return calculate_weekly_contact_hours(3.0, 1.0)
        elif val >= 3.0:
            return calculate_weekly_contact_hours(2.0, 1.0)
        elif val >= 2.0:
            return calculate_weekly_contact_hours(1.0, 1.0)
        else:
            return calculate_weekly_contact_hours(0.0, 1.0)
    elif has_lab and not has_lec:
        # Pure laboratory course (e.g. "1.0 Units – Laboratory")
        return calculate_weekly_contact_hours(0.0, val)
    else:
        # Pure lecture course (e.g. "2.0 Units – Lecture")
        return calculate_weekly_contact_hours(val, 0.0)


# ---------------------------------------------------------------------------
# Schedule & Meeting Days Parser
# ---------------------------------------------------------------------------

DAY_NAME_TO_INT = {
    "mon": 0, "monday": 0,
    "tue": 1, "tues": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}

INT_TO_DAY_CODE = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}


def parse_schedule_meeting_days(schedule_str: str) -> List[str]:
    """
    Parses day codes (e.g. ['Mon', 'Wed', 'Fri']) from a schedule string
    such as 'MWF 08:00 AM - 09:00 AM', 'TTh 10:30 AM - 12:00 PM', 'Sat 08:00 AM - 11:00 AM'.
    """
    if not schedule_str:
        return ["Mon", "Wed", "Fri"]

    s = schedule_str.strip()
    upper_s = s.upper()

    days: List[str] = []

    # Check common composite patterns first
    if "MWF" in upper_s:
        return ["Mon", "Wed", "Fri"]
    if "TTH" in upper_s or "T-TH" in upper_s or "T/TH" in upper_s:
        return ["Tue", "Thu"]
    if "MW" in upper_s:
        return ["Mon", "Wed"]
    if "TF" in upper_s:
        return ["Tue", "Fri"]
    if "FS" in upper_s:
        return ["Fri", "Sat"]

    # Match tokens
    tokens = re.split(r"[\s,\-/]+", s)
    for tok in tokens:
        clean = tok.strip().lower()
        if clean in DAY_NAME_TO_INT:
            day_code = INT_TO_DAY_CODE[DAY_NAME_TO_INT[clean]]
            if day_code not in days:
                days.append(day_code)

    if days:
        return days

    # Single-letter parsing if no words matched
    if "M" in upper_s and "Mon" not in days:
        days.append("Mon")
    if ("TH" in upper_s or "H" in upper_s) and "Thu" not in days:
        days.append("Thu")
    elif "T" in upper_s and "Tue" not in days:
        days.append("Tue")
    if "W" in upper_s and "Wed" not in days:
        days.append("Wed")
    if "F" in upper_s and "Fri" not in days:
        days.append("Fri")
    if ("SAT" in upper_s or "S" in upper_s) and "Sat" not in days:
        days.append("Sat")

    return days or ["Mon", "Wed", "Fri"]


# ---------------------------------------------------------------------------
# 18-Week Calendar Generator
# ---------------------------------------------------------------------------

def get_default_semester_start_date(semester_ay: str = "") -> str:
    """
    Determines default semester start date:
    - 1st Semester: 3rd Monday of August
    - 2nd Semester: 3rd Monday of January
    - Summer / Mid-Year: 2nd Monday of June
    """
    curr_year = datetime.date.today().year
    sem_str = (semester_ay or "").lower()

    target_year = curr_year
    m_yr = re.search(r"20\d{2}", semester_ay or "")
    if m_yr:
        target_year = int(m_yr.group(0))

    if "2nd" in sem_str or "second" in sem_str:
        # 3rd Monday of January
        jan1 = datetime.date(target_year + 1 if "1st" not in sem_str and target_year == curr_year else target_year, 1, 1)
        # 0 is Monday
        days_to_monday = (0 - jan1.weekday()) % 7
        first_monday = jan1 + datetime.timedelta(days=days_to_monday)
        third_monday = first_monday + datetime.timedelta(weeks=2)
        return third_monday.strftime("%Y-%m-%d")

    if "summer" in sem_str or "midyear" in sem_str:
        # 2nd Monday of June
        jun1 = datetime.date(target_year, 6, 1)
        days_to_monday = (0 - jun1.weekday()) % 7
        first_monday = jun1 + datetime.timedelta(days=days_to_monday)
        second_monday = first_monday + datetime.timedelta(weeks=1)
        return second_monday.strftime("%Y-%m-%d")

    # Default: 1st Semester -> 3rd Monday of August
    aug1 = datetime.date(target_year, 8, 1)
    days_to_monday = (0 - aug1.weekday()) % 7
    first_monday = aug1 + datetime.timedelta(days=days_to_monday)
    third_monday = first_monday + datetime.timedelta(weeks=2)
    return third_monday.strftime("%Y-%m-%d")


def build_18_week_calendar(
    start_date_str: str,
    meeting_days: List[str],
    weekly_hours: float,
    all_non_class_dates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Builds the 18 instructional weeks of the semester.
    Calculates specific dates for scheduled meetings, checks against
    holidays and custom non-class suspensions, and computes hours lost
    and effective remaining capacity per week.
    """
    try:
        sem_start = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except Exception:
        sem_start = datetime.datetime.strptime(get_default_semester_start_date(), "%Y-%m-%d").date()

    # Align start date to its Monday
    start_monday = sem_start - datetime.timedelta(days=sem_start.weekday())

    # Map meeting days to day offsets from Monday (0 to 6)
    meeting_day_ints = [DAY_NAME_TO_INT[d.lower()] for d in meeting_days if d.lower() in DAY_NAME_TO_INT]
    if not meeting_day_ints:
        meeting_day_ints = [0, 2, 4]  # Mon, Wed, Fri

    # Calculate hours per meeting day
    num_meetings = max(1, len(meeting_day_ints))
    hours_per_meeting = round(weekly_hours / num_meetings, 2)

    # Index non-class dates by YYYY-MM-DD
    # Active only if enabled is True or not specified
    disruptions_by_date: Dict[str, List[Dict[str, Any]]] = {}
    for ncd in all_non_class_dates:
        if ncd.get("enabled", True) is not False:
            d_str = str(ncd.get("date") or "").strip()
            if d_str:
                if d_str not in disruptions_by_date:
                    disruptions_by_date[d_str] = []
                disruptions_by_date[d_str].append(ncd)

    calendar_weeks = []
    for w in range(1, 19):
        week_monday = start_monday + datetime.timedelta(weeks=(w - 1))
        week_friday = week_monday + datetime.timedelta(days=4)
        week_saturday = week_monday + datetime.timedelta(days=5)
        week_end = week_saturday if 5 in meeting_day_ints else week_friday

        date_range_label = f"{week_monday.strftime('%b %d')} – {week_end.strftime('%b %d')}"

        week_disruptions = []
        hours_lost_this_week = 0.0

        for d_offset in meeting_day_ints:
            meet_date = week_monday + datetime.timedelta(days=d_offset)
            meet_date_str = meet_date.strftime("%Y-%m-%d")
            day_name = INT_TO_DAY_CODE[meet_date.weekday()]

            if meet_date_str in disruptions_by_date:
                day_items = disruptions_by_date[meet_date_str]
                # If multiple holidays/suspensions coincide on the same day, class is cancelled once
                # We determine the maximum hours lost on that day (defaulting to hours_per_meeting)
                day_lost_hrs = hours_per_meeting
                titles = []
                for d_item in day_items:
                    specified_hrs = d_item.get("hours_affected")
                    if specified_hrs is not None:
                        try:
                            day_lost_hrs = max(day_lost_hrs, float(specified_hrs))
                        except Exception:
                            pass
                    t_name = d_item.get("title") or d_item.get("name") or "Non-Class Day"
                    if t_name not in titles:
                        titles.append(t_name)

                # Cap daily lost hours at hours_per_meeting unless explicitly higher
                hours_lost_this_week += day_lost_hrs

                for d_item in day_items:
                    week_disruptions.append({
                        "date": meet_date_str,
                        "day": day_name,
                        "title": d_item.get("title") or d_item.get("name") or "Non-Class Day",
                        "category": d_item.get("category") or "custom",
                        "scope": d_item.get("scope") or "Local",
                        "type": d_item.get("type") or "suspension",
                        "hours_lost": day_lost_hrs / len(day_items),
                    })

        # Cap hours lost at weekly capacity
        effective_hours_lost = min(weekly_hours, hours_lost_this_week)
        effective_capacity = max(0.0, weekly_hours - effective_hours_lost)

        calendar_weeks.append({
            "week_number": w,
            "start_date": week_monday.strftime("%Y-%m-%d"),
            "end_date": week_end.strftime("%Y-%m-%d"),
            "date_range_label": date_range_label,
            "planned_hours": weekly_hours,
            "hours_lost": effective_hours_lost,
            "effective_hours": round(effective_capacity, 2),
            "is_disrupted": effective_hours_lost > 0,
            "disruptions": week_disruptions,
        })

    return calendar_weeks


# ---------------------------------------------------------------------------
# Topic Parsing & Hour Extraction
# ---------------------------------------------------------------------------

def parse_hours_from_time_frame(time_frame: str, fallback_hours: float = 3.0) -> float:
    """Extracts numeric instructional hours from time frame strings like 'Week 1-2 (6 hours)' or '4.5 hrs'."""
    if not time_frame:
        return fallback_hours
    s = str(time_frame).lower()
    m_hrs = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours|hour|hrs|hr)", s)
    if m_hrs:
        try:
            return float(m_hrs.group(1))
        except Exception:
            pass
    m_weeks = re.search(r"week[s]?\s*(\d+)(?:\s*-\s*(\d+))?", s)
    if m_weeks:
        w_start = int(m_weeks.group(1))
        w_end = int(m_weeks.group(2)) if m_weeks.group(2) else w_start
        weeks_count = max(1, (w_end - w_start) + 1)
        return float(weeks_count * fallback_hours)
    m_num = re.search(r"(\d+(?:\.\d+)?)", s)
    if m_num:
        try:
            return float(m_num.group(1))
        except Exception:
            pass
    return fallback_hours


def clean_topic_title(raw_topics: str) -> str:
    """Extracts a concise, readable title from a syllabus topic string."""
    if not raw_topics:
        return "Untitled Topic"
    lines = [l.strip() for l in raw_topics.split("\n") if l.strip()]
    if not lines:
        return "Untitled Topic"

    # Prefer the first prominent line without bullet or prefix
    first = lines[0]
    cleaned = re.sub(r"^[•\-\*o\d\.\)\s]+", "", first).strip()
    if cleaned:
        return cleaned
    return lines[0][:80]


def extract_syllabus_learning_plan_topics(
    doc: Dict[str, Any],
    weekly_hours: float = 3.0,
) -> List[Dict[str, Any]]:
    """
    Extracts structured topics from the course blueprint's learning plan table.
    """
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    lp_table = meta.get("learning_plan_table") or meta.get("learning_plan_topics") or bp.get("learning_plan") or meta.get("learning_plan") or []

    topics = []
    for idx, row in enumerate(lp_table):
        raw_topics = str(row.get("topics") or row.get("topic") or row.get("topic_title") or row.get("title") or row.get("content") or "").strip()
        time_frame = str(row.get("time_frame") or row.get("hours") or row.get("planned_hours") or "").strip()
        clo = str(row.get("clo") or row.get("clo_aligned") or row.get("clo_ids") or "").strip()
        ilo = str(row.get("ilo") or row.get("intended_learning_outcomes") or "").strip()
        assessments = str(row.get("assessment_activities") or row.get("assessments") or "").strip()

        title = clean_topic_title(raw_topics)
        parsed_hours = parse_hours_from_time_frame(time_frame, fallback_hours=weekly_hours)

        topics.append({
            "topic_id": f"topic_{idx}",
            "topic_num": idx + 1,
            "title": title,
            "topic_title": title,
            "full_topics": raw_topics,
            "time_frame": time_frame,
            "planned_hours": parsed_hours,
            "hours_allocated": parsed_hours,
            "clo": clo,
            "clo_ids": [c.strip() for c in re.split(r"[,\s\n]+", clo) if c.strip()],
            "ilo": ilo,
            "assessment_activities": assessments,
        })

    return topics


# ---------------------------------------------------------------------------
# Ideal Schedule Allocation
# ---------------------------------------------------------------------------

def calculate_ideal_topic_schedule(
    topics: List[Dict[str, Any]],
    weekly_capacity: float,
) -> List[Dict[str, Any]]:
    """
    Sequentially maps planned topic hours across Weeks 1 to 18 based on weekly capacity.
    Computes ideal_start_week and ideal_end_week for each topic.
    """
    cap = max(1.0, weekly_capacity)
    current_hour_marker = 0.0

    scheduled_topics = []
    for t in topics:
        topic_copy = dict(t)
        hours = max(0.5, float(topic_copy.get("planned_hours") or cap))

        start_h = current_hour_marker
        end_h = current_hour_marker + hours

        # Week is 1-indexed: 0..cap -> Week 1, cap..2*cap -> Week 2, etc.
        start_w = int(start_h // cap) + 1
        # If end falls exactly on boundary, it belongs to the previous week
        if end_h % cap == 0:
            end_w = max(start_w, int(end_h // cap))
        else:
            end_w = max(start_w, int(end_h // cap) + 1)

        # Clamp to 1..18
        start_w = max(1, min(18, start_w))
        end_w = max(start_w, min(18, end_w))

        topic_copy["ideal_start_week"] = start_w
        topic_copy["ideal_end_week"] = end_w
        topic_copy["ideal_weeks"] = list(range(start_w, end_w + 1))
        topic_copy["ideal_week_span"] = f"Week {start_w}" if start_w == end_w else f"Week {start_w} – {end_w}"

        current_hour_marker = end_h
        scheduled_topics.append(topic_copy)

    return scheduled_topics


# ---------------------------------------------------------------------------
# Actual Schedule & Pacing / Variance Calculation
# ---------------------------------------------------------------------------

def compute_topic_pacing_and_variance(
    topic: Dict[str, Any],
    calendar_weeks: List[Dict[str, Any]],
    cumulative_disruptions_by_week: Dict[int, float],
) -> Dict[str, Any]:
    """
    Computes the status badge and visual bar positions for a topic:
    - Status: 'pending', 'in_progress', 'done'
    - Variance: 'on_track', 'ahead', 'behind', 'shifted'
    """
    ideal_start = topic.get("ideal_start_week", 1)
    ideal_end = topic.get("ideal_end_week", 1)

    s_stat = str(topic.get("status") or "").lower().strip()
    s_comp = str(topic.get("completion_status") or "").lower().strip()

    if s_comp in ["completed", "done"] or s_stat in ["done", "completed"]:
        status = "done"
    elif s_comp in ["in_progress", "inprogress", "active"] or s_stat in ["in_progress", "inprogress", "active"]:
        status = "in_progress"
    else:
        status = "pending"

    actual_start = topic.get("actual_start_week")
    actual_end = topic.get("actual_end_week")

    try:
        actual_start = int(actual_start) if actual_start is not None else None
    except Exception:
        actual_start = None

    try:
        actual_end = int(actual_end) if actual_end is not None else None
    except Exception:
        actual_end = None

    variance_status = "on_track"

    if status == "done":
        # Check actual completion
        effective_actual_end = actual_end or actual_start or ideal_end
        if effective_actual_end < ideal_end:
            variance_status = "ahead"
        elif effective_actual_end == ideal_end:
            variance_status = "on_track"
        else:
            variance_status = "behind"
    elif status == "in_progress":
        effective_actual_start = actual_start or ideal_start
        if effective_actual_start < ideal_start:
            variance_status = "ahead"
        elif effective_actual_start == ideal_start:
            variance_status = "on_track"
        else:
            variance_status = "behind"
    else:  # pending
        # Check if cumulative non-class disruptions up to ideal_start have caused a shift
        lost_up_to_start = cumulative_disruptions_by_week.get(ideal_start, 0.0)
        weekly_cap = topic.get("weekly_capacity", 3.0) or 3.0
        if lost_up_to_start >= (weekly_cap * 0.5):
            variance_status = "shifted"
        else:
            variance_status = "on_track"

    actual_weeks = []
    if actual_start is not None:
        act_e = actual_end or actual_start
        actual_weeks = list(range(actual_start, act_e + 1))

    return {
        "status": status,
        "completion_status": "completed" if status == "done" else status,
        "actual_start_week": actual_start,
        "actual_end_week": actual_end,
        "actual_weeks": actual_weeks,
        "variance_status": variance_status,
        "pacing_status": variance_status,
    }


# ---------------------------------------------------------------------------
# Full Gantt Chart Workflow Operations
# ---------------------------------------------------------------------------

def initialize_course_gantt(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initializes a fresh Gantt Chart state for a course document,
    extracting topics from syllabus learning plan and preloading holidays.
    """
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}

    credit_info = parse_course_credit_units(meta)
    schedule_str = meta.get("schedule") or ""
    meeting_days = parse_schedule_meeting_days(schedule_str)
    semester_ay = meta.get("semester_ay") or ""
    start_date_str = get_default_semester_start_date(semester_ay)

    # Determine year for holidays
    try:
        sem_year = int(start_date_str.split("-")[0])
    except Exception:
        sem_year = datetime.date.today().year

    # Pre-populate Philippine holidays for the semester year (and next year if 2nd sem)
    holidays = get_philippine_holidays(sem_year)
    if "1st" in semester_ay.lower() or "first" in semester_ay.lower():
        # 1st sem crosses into end of year, add Jan holidays of next year too
        holidays.extend(get_philippine_holidays(sem_year + 1))
    elif "2nd" in semester_ay.lower() or "second" in semester_ay.lower():
        # 2nd sem is usually Jan-May of target year
        pass

    # Deduplicate holidays
    seen_h_ids = set()
    dedup_holidays = []
    for h in holidays:
        if h["id"] not in seen_h_ids:
            seen_h_ids.add(h["id"])
            dedup_holidays.append(h)

    # Extract topics
    raw_topics = extract_syllabus_learning_plan_topics(doc, weekly_hours=credit_info["total_hours_per_week"])
    ideal_topics = calculate_ideal_topic_schedule(raw_topics, credit_info["total_hours_per_week"])

    # Build calendar
    calendar_weeks = build_18_week_calendar(
        start_date_str=start_date_str,
        meeting_days=meeting_days,
        weekly_hours=credit_info["total_hours_per_week"],
        all_non_class_dates=dedup_holidays,
    )

    # Compute cumulative disruptions
    cum_disruptions = {}
    cum_hrs = 0.0
    for w in calendar_weeks:
        cum_hrs += w["hours_lost"]
        cum_disruptions[w["week_number"]] = cum_hrs

    # Finalize topics with status & pacing
    final_topics = []
    for t in ideal_topics:
        t["weekly_capacity"] = credit_info["total_hours_per_week"]
        pacing = compute_topic_pacing_and_variance(t, calendar_weeks, cum_disruptions)
        t.update(pacing)
        final_topics.append(t)

    gantt_state = {
        "version": 1,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "semester_start_date": start_date_str,
        "meeting_days": meeting_days,
        "lecture_units": credit_info["lecture_units"],
        "lab_units": credit_info["lab_units"],
        "lecture_hours_per_week": credit_info["lecture_hours_per_week"],
        "lab_hours_per_week": credit_info["lab_hours_per_week"],
        "total_hours_per_week": credit_info["total_hours_per_week"],
        "non_class_dates": dedup_holidays,
        "topics": final_topics,
        "calendar_weeks": calendar_weeks,
    }

    return gantt_state


def get_course_gantt(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves or lazily initializes the course delivery Gantt Chart state.
    Recalculates dynamic weeks and variance to ensure live accuracy.
    """
    stored = doc.get("gantt_chart")
    if not stored or not isinstance(stored, dict) or not stored.get("topics"):
        return initialize_course_gantt(doc)

    # Ensure dynamic calendar and pacing are fresh
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    credit_info = parse_course_credit_units(meta)

    # Allow custom overrides in stored if present
    weekly_hours = stored.get("total_hours_per_week") or credit_info["total_hours_per_week"]
    meeting_days = stored.get("meeting_days") or parse_schedule_meeting_days(meta.get("schedule") or "")
    start_date = stored.get("semester_start_date") or get_default_semester_start_date(meta.get("semester_ay") or "")
    non_class_dates = stored.get("non_class_dates") or []

    calendar_weeks = build_18_week_calendar(
        start_date_str=start_date,
        meeting_days=meeting_days,
        weekly_hours=weekly_hours,
        all_non_class_dates=non_class_dates,
    )

    cum_disruptions = {}
    cum_hrs = 0.0
    for w in calendar_weeks:
        cum_hrs += w["hours_lost"]
        cum_disruptions[w["week_number"]] = cum_hrs

    # Re-evaluate topic pacing
    refreshed_topics = []
    stored_topics = stored.get("topics") or []
    for t in stored_topics:
        t["weekly_capacity"] = weekly_hours
        if "topic_title" not in t and "title" in t:
            t["topic_title"] = t["title"]
        elif "title" not in t and "topic_title" in t:
            t["title"] = t["topic_title"]
        if "hours_allocated" not in t and "planned_hours" in t:
            t["hours_allocated"] = t["planned_hours"]
        elif "planned_hours" not in t and "hours_allocated" in t:
            t["planned_hours"] = t["hours_allocated"]
        if "ideal_weeks" not in t or not t.get("ideal_weeks"):
            start_w = t.get("ideal_start_week")
            end_w = t.get("ideal_end_week")
            if start_w is not None and end_w is not None:
                try:
                    t["ideal_weeks"] = list(range(int(start_w), int(end_w) + 1))
                except Exception:
                    pass
        if "clo_ids" not in t and "clo" in t:
            clo_val = t.get("clo")
            t["clo_ids"] = [clo_val] if isinstance(clo_val, str) else (clo_val or [])
        pacing = compute_topic_pacing_and_variance(t, calendar_weeks, cum_disruptions)
        t.update(pacing)
        refreshed_topics.append(t)

    stored["calendar_weeks"] = calendar_weeks
    stored["topics"] = refreshed_topics
    stored["lecture_units"] = credit_info["lecture_units"]
    stored["lab_units"] = credit_info["lab_units"]
    stored["lecture_hours_per_week"] = credit_info["lecture_hours_per_week"]
    stored["lab_hours_per_week"] = credit_info["lab_hours_per_week"]
    stored["total_hours_per_week"] = weekly_hours
    stored["meeting_days"] = meeting_days
    stored["semester_start_date"] = start_date

    return stored


def save_course_gantt(doc: Dict[str, Any], incoming_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and persists updated delivery timeline state (topic statuses,
    actual weeks, custom non-class dates, schedule settings) to doc['gantt_chart'].
    """
    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    credit_info = parse_course_credit_units(meta)

    existing = doc.get("gantt_chart") or {}

    start_date = (incoming_data.get("semester_start_date") or existing.get("semester_start_date") or
                  get_default_semester_start_date(meta.get("semester_ay") or "")).strip()
    meeting_days = incoming_data.get("meeting_days") or existing.get("meeting_days") or parse_schedule_meeting_days(meta.get("schedule") or "")
    non_class_dates = incoming_data.get("non_class_dates")
    if non_class_dates is None:
        non_class_dates = existing.get("non_class_dates") or []

    weekly_hours = credit_info["total_hours_per_week"]
    if incoming_data.get("total_hours_per_week"):
        try:
            weekly_hours = float(incoming_data["total_hours_per_week"])
        except Exception:
            pass

    # Build updated calendar
    calendar_weeks = build_18_week_calendar(
        start_date_str=start_date,
        meeting_days=meeting_days,
        weekly_hours=weekly_hours,
        all_non_class_dates=non_class_dates,
    )

    cum_disruptions = {}
    cum_hrs = 0.0
    for w in calendar_weeks:
        cum_hrs += w["hours_lost"]
        cum_disruptions[w["week_number"]] = cum_hrs

    # Topics update: preserve user input for status, actual_start_week, actual_end_week, remarks
    incoming_topics = incoming_data.get("topics")
    if incoming_topics is None:
        incoming_topics = existing.get("topics") or []

    final_topics = []
    for t in incoming_topics:
        t_copy = dict(t)
        t_copy["weekly_capacity"] = weekly_hours
        if "topic_title" not in t_copy and "title" in t_copy:
            t_copy["topic_title"] = t_copy["title"]
        elif "title" not in t_copy and "topic_title" in t_copy:
            t_copy["title"] = t_copy["topic_title"]
        if "hours_allocated" not in t_copy and "planned_hours" in t_copy:
            t_copy["hours_allocated"] = t_copy["planned_hours"]
        elif "planned_hours" not in t_copy and "hours_allocated" in t_copy:
            t_copy["planned_hours"] = t_copy["hours_allocated"]
        if "ideal_weeks" not in t_copy or not t_copy.get("ideal_weeks"):
            start_w = t_copy.get("ideal_start_week")
            end_w = t_copy.get("ideal_end_week")
            if start_w is not None and end_w is not None:
                try:
                    t_copy["ideal_weeks"] = list(range(int(start_w), int(end_w) + 1))
                except Exception:
                    pass
        if "clo_ids" not in t_copy and "clo" in t_copy:
            clo_val = t_copy.get("clo")
            t_copy["clo_ids"] = [clo_val] if isinstance(clo_val, str) else (clo_val or [])
        pacing = compute_topic_pacing_and_variance(t_copy, calendar_weeks, cum_disruptions)
        t_copy.update(pacing)
        final_topics.append(t_copy)

    gantt_state = {
        "version": existing.get("version", 1),
        "created_at": existing.get("created_at") or _now_iso(),
        "updated_at": _now_iso(),
        "semester_start_date": start_date,
        "meeting_days": meeting_days,
        "lecture_units": credit_info["lecture_units"],
        "lab_units": credit_info["lab_units"],
        "lecture_hours_per_week": credit_info["lecture_hours_per_week"],
        "lab_hours_per_week": credit_info["lab_hours_per_week"],
        "total_hours_per_week": weekly_hours,
        "non_class_dates": non_class_dates,
        "topics": final_topics,
        "calendar_weeks": calendar_weeks,
    }

    doc["gantt_chart"] = gantt_state
    return gantt_state


def sync_gantt_from_syllabus(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Re-synchronizes topics from the course blueprint learning_plan_table,
    while carefully preserving any recorded actual completions and custom non-class dates.
    """
    existing = doc.get("gantt_chart") or {}
    existing_topics_by_id = {t.get("topic_id"): t for t in existing.get("topics") or []}

    bp = doc.get("blueprint") or {}
    meta = bp.get("metadata") or {}
    credit_info = parse_course_credit_units(meta)
    weekly_hours = credit_info["total_hours_per_week"]

    # Re-extract topics from learning plan
    fresh_topics = extract_syllabus_learning_plan_topics(doc, weekly_hours=weekly_hours)
    ideal_topics = calculate_ideal_topic_schedule(fresh_topics, weekly_hours)

    start_date = existing.get("semester_start_date") or get_default_semester_start_date(meta.get("semester_ay") or "")
    meeting_days = existing.get("meeting_days") or parse_schedule_meeting_days(meta.get("schedule") or "")
    non_class_dates = existing.get("non_class_dates") or []

    calendar_weeks = build_18_week_calendar(
        start_date_str=start_date,
        meeting_days=meeting_days,
        weekly_hours=weekly_hours,
        all_non_class_dates=non_class_dates,
    )

    cum_disruptions = {}
    cum_hrs = 0.0
    for w in calendar_weeks:
        cum_hrs += w["hours_lost"]
        cum_disruptions[w["week_number"]] = cum_hrs

    merged_topics = []
    for t in ideal_topics:
        old = existing_topics_by_id.get(t.get("topic_id"))
        if old:
            # Preserve user's actual execution data
            t["status"] = old.get("status", "pending")
            t["actual_start_week"] = old.get("actual_start_week")
            t["actual_end_week"] = old.get("actual_end_week")
            t["completion_date"] = old.get("completion_date")
            t["remarks"] = old.get("remarks", "")

        t["weekly_capacity"] = weekly_hours
        pacing = compute_topic_pacing_and_variance(t, calendar_weeks, cum_disruptions)
        t.update(pacing)
        merged_topics.append(t)

    gantt_state = {
        "version": existing.get("version", 1),
        "created_at": existing.get("created_at") or _now_iso(),
        "updated_at": _now_iso(),
        "semester_start_date": start_date,
        "meeting_days": meeting_days,
        "lecture_units": credit_info["lecture_units"],
        "lab_units": credit_info["lab_units"],
        "lecture_hours_per_week": credit_info["lecture_hours_per_week"],
        "lab_hours_per_week": credit_info["lab_hours_per_week"],
        "total_hours_per_week": weekly_hours,
        "non_class_dates": non_class_dates,
        "topics": merged_topics,
        "calendar_weeks": calendar_weeks,
    }

    doc["gantt_chart"] = gantt_state
    return gantt_state
