"""
Direct Curriculum Data Access Layer for PGO-PI-IGA.accdb (Microsoft Access).
Provides authoritative curriculum data for Bachelor of Science in Electrical Engineering (BSEE):
  - Course Codes & Titles
  - Authoritative Course Descriptions
  - Lecture, Lab, and Total Units / Hours
  - Pre-requisites and Co-requisites
  - PGO-PI-IGA (IED) Alignment Mappings

All queries use direct SQL through pyodbc with graceful caching and fallback.
"""

import os
import re
import copy
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

try:
    import config
    ACCDB_PATH = config.ACCDB_PATH
    CONN_STR = config.ACCDB_CONN_STR
except Exception:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ACCDB_PATH = os.environ.get("ACCDB_PATH", os.path.join(BASE_DIR, "prospectus", "PGO-PI-IGA.accdb"))
    CONN_STR = os.environ.get(
        "ACCDB_CONN_STR",
        f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ACCDB_PATH};"
    )

_CACHED_BSEE_COURSES: Optional[List[Dict[str, Any]]] = None
_CACHED_PGO_PI_TREE: Optional[List[Dict[str, Any]]] = None

# Authoritative BSEE PGO and Performance Indicator hierarchy fallback
FALLBACK_PGO_PI_TREE: List[Dict[str, Any]] = [
  {
    "pgo_id": "a",
    "label": "PGO A: Engineering Rigor & Foundational Competence",
    "keyword": "Engineering Rigor & Foundational Competence",
    "description": "Apply knowledge of mathematics and sciences to solve engineering problems",
    "pis": [
      {
        "pi_id": "a.1",
        "pgo_id": "a",
        "description": "Apply math and science to analyze technical systems",
        "label": "a.1: Apply math and science to analyze technical systems"
      },
      {
        "pi_id": "a.2",
        "pgo_id": "a",
        "description": "Apply principles in chemical sciences to solve engineering problems",
        "label": "a.2: Apply principles in chemical sciences to solve engineering problems"
      },
      {
        "pi_id": "a.3",
        "pgo_id": "a",
        "description": "Apply principles in physical sciences to solve engineering problems",
        "label": "a.3: Apply principles in physical sciences to solve engineering problems"
      }
    ]
  },
  {
    "pgo_id": "b",
    "label": "PGO B: Impactful Research & Empirical Investigation",
    "keyword": "Impactful Research & Empirical Investigation",
    "description": "Design and conduct experiments, as well as to analyze and interpret data",
    "pis": [
      {
        "pi_id": "b.1",
        "pgo_id": "b",
        "description": "Perform laboratory experiments as prescribed by standard procedures.",
        "label": "b.1: Perform laboratory experiments as prescribed by standard procedures."
      },
      {
        "pi_id": "b.2",
        "pgo_id": "b",
        "description": "Design an experiment to achieve a specific objective.",
        "label": "b.2: Design an experiment to achieve a specific objective."
      }
    ]
  },
  {
    "pgo_id": "c",
    "label": "PGO C: Sustainable Systems Innovation",
    "keyword": "Sustainable Systems Innovation",
    "description": "Design a system, component, or process to meet desired needs within realistic constraints such as economic, environmental, social, political, ethical, health and safety, manufacturability, and sustainability, in accordance with standards.",
    "pis": [
      {
        "pi_id": "c.1",
        "pgo_id": "c",
        "description": "Develop an engineering solution that have various constraints as factors",
        "label": "c.1: Develop an engineering solution that have various constraints as factors"
      },
      {
        "pi_id": "c.2",
        "pgo_id": "c",
        "description": "Design a system or process based on various constraints",
        "label": "c.2: Design a system or process based on various constraints"
      }
    ]
  },
  {
    "pgo_id": "d",
    "label": "PGO D: Inclusive Collaboration & Team Dynamics",
    "keyword": "Inclusive Collaboration & Team Dynamics",
    "description": "Function on multidisciplinary teams",
    "pis": [
      {
        "pi_id": "d.1",
        "pgo_id": "d",
        "description": "Shows tact in dealing with people he/she comes in contact with.",
        "label": "d.1: Shows tact in dealing with people he/she comes in contact with."
      },
      {
        "pi_id": "d.2",
        "pgo_id": "d",
        "description": "Capable of learning from and listening to co-members.",
        "label": "d.2: Capable of learning from and listening to co-members."
      },
      {
        "pi_id": "d.3",
        "pgo_id": "d",
        "description": "Shows respect and courtesy in dealing with peers and superiors.",
        "label": "d.3: Shows respect and courtesy in dealing with peers and superiors."
      }
    ]
  },
  {
    "pgo_id": "e",
    "label": "PGO E: Critical Analysis & Complex Problem Solving",
    "keyword": "Critical Analysis & Complex Problem Solving",
    "description": "Identify, formulate, and solve engineering problems",
    "pis": [
      {
        "pi_id": "e.1",
        "pgo_id": "e",
        "description": "Interpret statement problems into mathematical expressions.",
        "label": "e.1: Interpret statement problems into mathematical expressions."
      },
      {
        "pi_id": "e.2",
        "pgo_id": "e",
        "description": "Apply concepts, theories, and principles in solving engineering problem(s).",
        "label": "e.2: Apply concepts, theories, and principles in solving engineering problem(s)."
      },
      {
        "pi_id": "e.3",
        "pgo_id": "e",
        "description": "Solve specific engineering problem related to discipline.",
        "label": "e.3: Solve specific engineering problem related to discipline."
      }
    ]
  },
  {
    "pgo_id": "f",
    "label": "PGO F: Conscience-Guided Ethics & Accountability",
    "keyword": "Conscience-Guided Ethics & Accountability",
    "description": "Understand professional, social, and ethical responsibility",
    "pis": [
      {
        "pi_id": "f.1",
        "pgo_id": "f",
        "description": "Internalizes the professional code of ethics for specific discipline.",
        "label": "f.1: Internalizes the professional code of ethics for specific discipline."
      },
      {
        "pi_id": "f.2",
        "pgo_id": "f",
        "description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
        "label": "f.2: Applies the principles of professional ethical standard and social responsibility to actual practice."
      }
    ]
  },
  {
    "pgo_id": "g",
    "label": "PGO G: Global Technical Communication",
    "keyword": "Global Technical Communication",
    "description": "Communicate effectively",
    "pis": [
      {
        "pi_id": "g.1",
        "pgo_id": "g",
        "description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
        "label": "g.1: Articulate the convention and style in oral communication that conveys complete thought and information."
      },
      {
        "pi_id": "g.2",
        "pgo_id": "g",
        "description": "Articulate the convention and style in written communication that conveys complete thought and information.",
        "label": "g.2: Articulate the convention and style in written communication that conveys complete thought and information."
      },
      {
        "pi_id": "g.3",
        "pgo_id": "g",
        "description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
        "label": "g.3: Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline."
      }
    ]
  },
  {
    "pgo_id": "h",
    "label": "PGO H: Community Transformation & Sustainability",
    "keyword": "Community Transformation & Sustainability",
    "description": "Understand the impact of engineering solutions in a global, economic, environmental, & societal context through broad education",
    "pis": [
      {
        "pi_id": "h.1",
        "pgo_id": "h",
        "description": "Relate engineering solutions to global, economic, environmental, and societal context.",
        "label": "h.1: Relate engineering solutions to global, economic, environmental, and societal context."
      },
      {
        "pi_id": "h.2",
        "pgo_id": "h",
        "description": "Describe engineering solutions in application to global, economic, environmental, and societal context.",
        "label": "h.2: Describe engineering solutions in application to global, economic, environmental, and societal context."
      }
    ]
  },
  {
    "pgo_id": "i",
    "label": "PGO I: Continuous Learning & Adaptive Growth",
    "keyword": "Continuous Learning & Adaptive Growth",
    "description": "Recognize the need for, and an ability to engage in life-long learning",
    "pis": [
      {
        "pi_id": "i.1",
        "pgo_id": "i",
        "description": "Demonstrate ability to learn independently.",
        "label": "i.1: Demonstrate ability to learn independently."
      },
      {
        "pi_id": "i.2",
        "pgo_id": "i",
        "description": "Shows appreciation and understanding of the engineering profession.",
        "label": "i.2: Shows appreciation and understanding of the engineering profession."
      },
      {
        "pi_id": "i.3",
        "pgo_id": "i",
        "description": "Understand the linkage or connection between his/her task to previous, intervening, and subsequent tasks.",
        "label": "i.3: Understand the linkage or connection between his/her task to previous, intervening, and subsequent tasks."
      }
    ]
  },
  {
    "pgo_id": "j",
    "label": "PGO J: Proactive Social Awareness",
    "keyword": "Proactive Social Awareness",
    "description": "Apply knowledge of contemporary issues",
    "pis": [
      {
        "pi_id": "j.1",
        "pgo_id": "j",
        "description": "Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
        "label": "j.1: Identify the socio-economic, political, and environmental issues related to the practice of engineering."
      },
      {
        "pi_id": "j.2",
        "pgo_id": "j",
        "description": "Explain the possible impact of technology to local, national, and international issues.",
        "label": "j.2: Explain the possible impact of technology to local, national, and international issues."
      },
      {
        "pi_id": "j.3",
        "pgo_id": "j",
        "description": "Shows leadership skills in managing a multidisciplinary group.",
        "label": "j.3: Shows leadership skills in managing a multidisciplinary group."
      }
    ]
  },
  {
    "pgo_id": "k",
    "label": "PGO K: Modern Tool Mastery & Digital Innovation",
    "keyword": "Modern Tool Mastery & Digital Innovation",
    "description": "Use techniques, skills, and modern engineering tools necessary for engineering practice",
    "pis": [
      {
        "pi_id": "k.1",
        "pgo_id": "k",
        "description": "Handles the details of the work assigned to him/her",
        "label": "k.1: Handles the details of the work assigned to him/her"
      },
      {
        "pi_id": "k.2",
        "pgo_id": "k",
        "description": "Demonstrate the ability to operate the equipment needed in the engineering practice",
        "label": "k.2: Demonstrate the ability to operate the equipment needed in the engineering practice"
      },
      {
        "pi_id": "k.3",
        "pgo_id": "k",
        "description": "Use modern technology in performing engineering practice",
        "label": "k.3: Use modern technology in performing engineering practice"
      }
    ]
  },
  {
    "pgo_id": "l",
    "label": "PGO L: Transformative Leadership & Project Management",
    "keyword": "Transformative Leadership & Project Management",
    "description": "Apply knowledge of engineering and management principles as a member and leader in team, and to manage projects and in multidisciplinary environments",
    "pis": [
      {
        "pi_id": "l.1",
        "pgo_id": "l",
        "description": "Capable of learning from and listening to co-members.",
        "label": "l.1: Capable of learning from and listening to co-members."
      },
      {
        "pi_id": "l.2",
        "pgo_id": "l",
        "description": "Shows leadership skills in managing a multidisciplinary group.",
        "label": "l.2: Shows leadership skills in managing a multidisciplinary group."
      },
      {
        "pi_id": "l.3",
        "pgo_id": "l",
        "description": "Participates in discussions and comes up with sound suggestions to problems",
        "label": "l.3: Participates in discussions and comes up with sound suggestions to problems"
      }
    ]
  },
  {
    "pgo_id": "m",
    "label": "PGO M: Specialized Global Competence",
    "keyword": "Specialized Global Competence",
    "description": "Understand at least one specialized field of electrical engineering practice",
    "pis": [
      {
        "pi_id": "m.1",
        "pgo_id": "m",
        "description": "Demonstrate leadership and team management in a multidisciplinary group.",
        "label": "m.1: Demonstrate leadership and team management in a multidisciplinary group."
      },
      {
        "pi_id": "m.2",
        "pgo_id": "m",
        "description": "Capable of learning from and listening to co-members",
        "label": "m.2: Capable of learning from and listening to co-members"
      },
      {
        "pi_id": "m.3",
        "pgo_id": "m",
        "description": "Apply designed system to process to solve engineering problems.",
        "label": "m.3: Apply designed system to process to solve engineering problems."
      }
    ]
  }
]


def get_accdb_pgo_pi_tree(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Returns the authoritative hierarchy of Program Graduate Outcomes (PGOs)
    and Performance Indicators (PIs) directly from PGO-PI-IGA.accdb, or authoritative fallback.
    """
    global _CACHED_PGO_PI_TREE
    if _CACHED_PGO_PI_TREE is not None and not force_refresh:
        return [copy.deepcopy(p) for p in _CACHED_PGO_PI_TREE]

    if not os.path.exists(ACCDB_PATH):
        for p in FALLBACK_PGO_PI_TREE:
            p.setdefault("pgo", p.get("pgo_id", ""))
            for pi in p.get("pis", []):
                pi.setdefault("pi", pi.get("pi_id", ""))
                pi.setdefault("pgo", p.get("pgo_id", ""))
        _CACHED_PGO_PI_TREE = FALLBACK_PGO_PI_TREE
        return [copy.deepcopy(p) for p in _CACHED_PGO_PI_TREE]

    try:
        import pyodbc
        conn = pyodbc.connect(CONN_STR, autocommit=True)
        cur = conn.cursor()

        # Query PGO
        cur.execute("SELECT [PGO ID], [PGO Keyword], [PGO Description] FROM [PGO] ORDER BY [ID]")
        pgo_lookup = {}
        pgo_list = []
        for pgo_id, kw, desc in cur.fetchall():
            p_id = (pgo_id or "").strip().lower()
            item = {
                "pgo_id": p_id,
                "pgo": p_id,
                "label": f"PGO {p_id.upper()}: {(kw or '').strip()}",
                "keyword": (kw or "").strip(),
                "description": (desc or "").strip(),
                "pis": []
            }
            pgo_lookup[p_id] = item
            pgo_list.append(item)

        # Query PI
        cur.execute("SELECT [PI ID], [PGO ID], [PI Description] FROM [PI] ORDER BY [ID]")
        for pi_id, pgo_id, desc in cur.fetchall():
            clean_pi = (pi_id or "").strip().rstrip(".")
            p_id = (pgo_id or "").strip().lower()
            pi_item = {
                "pi_id": clean_pi,
                "pi": clean_pi,
                "pgo_id": p_id,
                "pgo": p_id,
                "description": (desc or "").strip(),
                "label": f"{clean_pi}: {(desc or '').strip()}"
            }
            if p_id in pgo_lookup:
                pgo_lookup[p_id]["pis"].append(pi_item)

        conn.close()

        if pgo_list:
            _CACHED_PGO_PI_TREE = pgo_list
            return [copy.deepcopy(p) for p in _CACHED_PGO_PI_TREE]
    except Exception as e:
        logger.warning(f"Could not read PGO tree from Access DB: {e}. Using authoritative fallback.")

    _CACHED_PGO_PI_TREE = FALLBACK_PGO_PI_TREE
    return [copy.deepcopy(p) for p in _CACHED_PGO_PI_TREE]


def parse_pgo_pi_string(pgo_pi_str: str) -> List[Dict[str, Any]]:
    """
    Parses composite or legacy pgo_pi string expressions into structured mapping dictionaries.
    Handles formats like:
      - 'PGO-d-d.1 [I], PGO-g-g.3 [I]'
      - 'PGO a-a.1 [E]; PGO e-e.1 [E]'
      - 'PGO1-PI3 [D], PGO5-PI2 [D]'
      - 'PGO -b.1 [E]; PGO c-c.1 [E]'
      - 'PGO-l-l.1 [E], PGO-d-d.1 [I/E]'
    """
    if not pgo_pi_str:
        return []
    mappings: List[Dict[str, Any]] = []
    parts = re.split(r"[;,]", str(pgo_pi_str))
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.search(r"PGO\s*[-]?\s*([a-zA-Z0-9]+)?(?:[- ](?:PI)?([a-zA-Z0-9]+(?:\.[0-9]+)?))?\s*\[([A-Za-z/]+)\]", part, re.I)
        if m:
            pgo_raw = (m.group(1) or "").strip().lower()
            pi_raw = (m.group(2) or "").strip().lower()
            ied_raw = (m.group(3) or "I").strip().upper()
            if not pgo_raw and pi_raw:
                pgo_raw = pi_raw.split(".")[0]
            if not pi_raw and pgo_raw:
                pi_raw = f"{pgo_raw}.1"
            elif pi_raw and not "." in pi_raw and not pi_raw.isdigit():
                m_sub = re.match(r"([a-zA-Z]+)(\d+)", pi_raw)
                if m_sub:
                    pi_raw = f"{m_sub.group(1)}.{m_sub.group(2)}"

            if "D" in ied_raw:
                primary_ied = "D"
            elif "E" in ied_raw:
                primary_ied = "E"
            else:
                primary_ied = "I"

            ied_label_map = {"I": "Introductory", "E": "Enabling", "D": "Demonstrative"}
            ied_label = ied_label_map.get(primary_ied, "Introductory")
            mappings.append({
                "pgo": f"PGO {pgo_raw}",
                "pgo_id": pgo_raw,
                "pi": pi_raw,
                "ied": ied_raw,
                "ied_label": ied_label
            })
    return mappings


def query_accdb_bsee_courses(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Direct SQL extraction from PGO-PI-IGA.accdb.
    Fetches Courses_EE, Course_PI, PI, PGO, IED, PGO_PI_IGA, and Prereq_Coreq.
    """
    global _CACHED_BSEE_COURSES
    if _CACHED_BSEE_COURSES is not None and not force_refresh:
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]

    if not os.path.exists(ACCDB_PATH):
        logger.warning(f"Access database not found at {ACCDB_PATH}. Falling back to program_catalogs.")
        from program_catalogs.courses_ee import BSEE_COURSES
        _CACHED_BSEE_COURSES = BSEE_COURSES
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]

    try:
        import pyodbc
    except ImportError:
        logger.warning("pyodbc is not installed. Falling back to program_catalogs.")
        from program_catalogs.courses_ee import BSEE_COURSES
        _CACHED_BSEE_COURSES = BSEE_COURSES
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]

    try:
        conn = pyodbc.connect(CONN_STR, autocommit=True)
        cur = conn.cursor()

        # 1. PI to IGA Mapping (PGO_PI_IGA)
        cur.execute("SELECT [PI ID], [IGA ID] FROM [PGO_PI_IGA]")
        pi_to_igas: Dict[str, List[str]] = {}
        for pi_id, iga_id in cur.fetchall():
            pi_clean = (pi_id or "").strip().rstrip(".")
            iga_clean = (iga_id or "").strip()
            if pi_clean not in pi_to_igas:
                pi_to_igas[pi_clean] = []
            if iga_clean and iga_clean not in pi_to_igas[pi_clean]:
                pi_to_igas[pi_clean].append(iga_clean)

        # 2. Prerequisites & Co-requisites (Prereq_Coreq)
        cur.execute("SELECT [Course Code], [Prereq Code], [Coreq Code] FROM [Prereq_Coreq]")
        course_prereqs: Dict[str, List[str]] = {}
        course_coreqs: Dict[str, List[str]] = {}
        for code, prereq, coreq in cur.fetchall():
            c_code = (code or "").strip()
            p_code = (prereq or "").strip()
            co_code = (coreq or "").strip()

            if c_code not in course_prereqs:
                course_prereqs[c_code] = []
            if p_code and p_code.lower() != "none" and p_code not in course_prereqs[c_code]:
                course_prereqs[c_code].append(p_code)

            if c_code not in course_coreqs:
                course_coreqs[c_code] = []
            if co_code and co_code.lower() != "none" and co_code not in course_coreqs[c_code]:
                course_coreqs[c_code].append(co_code)
                if co_code not in course_coreqs:
                    course_coreqs[co_code] = []
                if c_code not in course_coreqs[co_code]:
                    course_coreqs[co_code].append(c_code)

        # 3. PGO, PI, and IED Lookup Tables
        cur.execute("SELECT [PGO ID], [PGO Keyword], [PGO Description] FROM [PGO]")
        pgo_lookup: Dict[str, Dict[str, str]] = {}
        for pgo_id, kw, desc in cur.fetchall():
            p_id = (pgo_id or "").strip().lower()
            pgo_lookup[p_id] = {
                "keyword": (kw or "").strip(),
                "description": (desc or "").strip()
            }

        cur.execute("SELECT [PI ID], [PGO ID], [PI Description] FROM [PI]")
        pi_lookup: Dict[str, Dict[str, str]] = {}
        for pi_id, pgo_id, desc in cur.fetchall():
            clean_pi = (pi_id or "").strip().rstrip(".")
            p_id = (pgo_id or "").strip().lower()
            pi_lookup[clean_pi] = {
                "pgo_id": p_id,
                "description": (desc or "").strip()
            }

        cur.execute("SELECT [IED ID], [IED Name] FROM [IED]")
        ied_lookup: Dict[str, str] = {}
        for ied_id, name in cur.fetchall():
            i_id = (ied_id or "").strip().upper()
            ied_lookup[i_id] = (name or "").strip()

        # 4. Course_PI joined in Python with clean_pi normalization
        cur.execute("SELECT [Course Code], [PI ID], [IED ID] FROM [Course_PI] ORDER BY [Course Code], [PI ID]")
        course_pi_map: Dict[str, List[Dict[str, Any]]] = {}
        for code, pi_id, ied_id in cur.fetchall():
            c_code = (code or "").strip()
            clean_pi = (pi_id or "").strip().rstrip(".")
            i_code = (ied_id or "").strip().upper()
            if "D" in i_code:
                effective_ied = "D"
            elif "E" in i_code:
                effective_ied = "E"
            else:
                effective_ied = "I"

            ied_name_map = {"I": "Introductory", "E": "Enabling", "D": "Demonstrative"}
            ied_name = ied_name_map.get(effective_ied, "Introductory")

            pi_info = pi_lookup.get(clean_pi, {})
            pgo_clean = pi_info.get("pgo_id")
            if not pgo_clean and clean_pi:
                pgo_clean = clean_pi.split(".")[0].lower()

            pgo_info = pgo_lookup.get(pgo_clean, {})
            igas_str = ", ".join(pi_to_igas.get(clean_pi, []))

            item = {
                "pgo": f"PGO {pgo_clean}",
                "pgo_id": pgo_clean,
                "pgo_keyword": pgo_info.get("keyword", ""),
                "pgo_description": pgo_info.get("description", ""),
                "pi": clean_pi,
                "pi_description": pi_info.get("description", ""),
                "ied": i_code,
                "ied_label": ied_name,
                "igas": igas_str
            }
            norm_code = re.sub(r"\s+", " ", c_code).strip().upper()
            if norm_code not in course_pi_map:
                course_pi_map[norm_code] = []
            course_pi_map[norm_code].append(item)
            if c_code not in course_pi_map:
                course_pi_map[c_code] = []
            course_pi_map[c_code].append(item)

        # 5. Courses_EE Master Table
        cur.execute("""
            SELECT [Course Code], [Course Title], [Course Description], [Lecture Units], [Laboratory Units], [Year Level], [Semester]
            FROM [Courses_EE]
            ORDER BY [Year Level], [Semester], [Course Code]
        """)
        raw_courses = cur.fetchall()
        conn.close()

        # Existing metadata lookup for topics & sdgs retention
        from program_catalogs.courses_ee import BSEE_COURSES as fallback_bsee
        fallback_lookup = {re.sub(r"\s+", " ", c["code"].split(" - ")[0]).strip().upper(): c for c in fallback_bsee}

        year_map = {1: "First Year", 2: "Second Year", 3: "Third Year", 4: "Fourth Year"}
        sem_map = {1: "1st Semester", 2: "2nd Semester"}

        courses: List[Dict[str, Any]] = []
        for code, title, desc, lec, lab, yr, sem in raw_courses:
            c_code = (code or "").strip()
            c_title = (title or "").strip()
            c_desc = (desc or "").strip()
            norm_code = re.sub(r"\s+", " ", c_code).strip().upper()

            lec_u = int(lec or 0)
            lab_u = int(lab or 0)
            tot_u = lec_u + lab_u

            lec_lab_type = "Lecture and Laboratory" if (lec_u > 0 and lab_u > 0) else ("Laboratory" if lab_u > 0 else "Lecture")
            credit_units_str = f"{tot_u}.0 Units \u2013 {lec_lab_type}"
            hrs_parts = []
            if lec_u > 0:
                hrs_parts.append(f"{lec_u} hours Lecture")
            if lab_u > 0:
                hrs_parts.append(f"{lab_u * 3} hours Laboratory")
            total_hrs = lec_u + (lab_u * 3)
            hours_str = f"{total_hrs} Hours/Week ({', '.join(hrs_parts)})" if hrs_parts else "3 Hours/Week"

            pr_list = course_prereqs.get(c_code, []) or course_prereqs.get(norm_code, [])
            prereq_str = ", ".join(pr_list) if pr_list else "None"

            co_list = course_coreqs.get(c_code, []) or course_coreqs.get(norm_code, [])
            coreq_str = ", ".join(co_list) if co_list else "None"

            pi_mappings = course_pi_map.get(norm_code, []) or course_pi_map.get(c_code, [])
            pgo_pi_summary = "; ".join([f"{m['pgo']}-{m['pi']} [{m['ied']}]" for m in pi_mappings[:3]]) if pi_mappings else ""

            fb = fallback_lookup.get(norm_code, {}) or fallback_lookup.get(c_code, {})
            # If accdb has no PI mapping for this course, fallback to existing mapping
            final_pgo_pi = pgo_pi_summary if pgo_pi_summary else fb.get("pgo_pi", "")
            final_pgo_pi_mappings = pi_mappings if pi_mappings else fb.get("pgo_pi_mappings", [])
            if not final_pgo_pi_mappings and final_pgo_pi:
                final_pgo_pi_mappings = parse_pgo_pi_string(final_pgo_pi)

            # If accdb description was empty (e.g. PE/NSTP/Elective), allow fallback description if available
            final_desc = c_desc if c_desc else fb.get("description", "")
            topics = fb.get("topics", [])
            sdgs = fb.get("sdgs", "SDG 4: Quality Education")

            courses.append({
                "code": c_code,
                "title": c_title,
                "description": final_desc,
                "lecture_units": lec_u,
                "lab_units": lab_u,
                "credit_units": credit_units_str,
                "lec_lab": lec_lab_type,
                "hours": hours_str,
                "year_level": year_map.get(yr, f"Year {yr}"),
                "semester": sem_map.get(sem, f"Semester {sem}"),
                "prereqs": prereq_str,
                "coreqs": coreq_str,
                "pgo_pi": final_pgo_pi,
                "pgo_pi_mappings": final_pgo_pi_mappings,
                "topics": topics,
                "sdgs": sdgs
            })

        _CACHED_BSEE_COURSES = courses
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]

    except Exception as e:
        logger.error(f"Error querying PGO-PI-IGA.accdb: {e}", exc_info=True)
        from program_catalogs.courses_ee import BSEE_COURSES
        fallback_courses = []
        for c in BSEE_COURSES:
            c_copy = copy.deepcopy(c)
            if not c_copy.get("pgo_pi_mappings") and c_copy.get("pgo_pi"):
                c_copy["pgo_pi_mappings"] = parse_pgo_pi_string(c_copy["pgo_pi"])
            fallback_courses.append(c_copy)
        _CACHED_BSEE_COURSES = fallback_courses
        return [copy.deepcopy(c) for c in _CACHED_BSEE_COURSES]


def sync_accdb_to_catalog_and_db() -> int:
    """
    Syncs the authoritative BSEE records from PGO-PI-IGA.accdb into:
      1. catalog_data.py runtime caches (COLLEGE_DEPARTMENT_CATALOG & BSEE_COURSES)
      2. data/academic_catalog.db (SQLite database)
    Returns number of BSEE courses synced.
    """
    courses = query_accdb_bsee_courses(force_refresh=True)
    if not courses:
        return 0

    # 1. Update catalog_data
    try:
        import catalog_data
        catalog_data.BSEE_COURSES = courses
        for college in catalog_data.COLLEGE_DEPARTMENT_CATALOG:
            for dept in college.get("departments", []):
                if dept.get("program_code") == "EE":
                    dept["courses"] = courses
    except Exception as e:
        logger.error(f"Failed to update catalog_data: {e}")

    # 2. Update SQLite database data/academic_catalog.db
    try:
        import academic_db
        with academic_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM courses WHERE program_code = 'BSEE'")
            
            rows = []
            for c in courses:
                rows.append((
                    "BSEE",
                    c.get("code", "").strip(),
                    c.get("title", "").strip(),
                    c.get("year_level", ""),
                    c.get("credit_units", ""),
                    c.get("lec_lab", "Lecture"),
                    c.get("hours", ""),
                    c.get("prereqs", "None"),
                    c.get("coreqs", "None"),
                    c.get("description", ""),
                    json.dumps(c.get("topics", [])),
                    c.get("sdgs", ""),
                    c.get("pgo_pi", "")
                ))
            cur.executemany("""
                INSERT INTO courses (program_code, course_code, course_title, year_level, credit_units, lec_lab, contact_hours, prerequisites, corequisites, description, topics, sdgs, pgo_pi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update academic_db: {e}")

    return len(courses)
