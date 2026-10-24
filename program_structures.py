"""
Official USeP College of Engineering Program Structures Catalog
Integrated directly from the official documents in the 'Program Structure/' folder:
  1. BSEE-Program-Structure_REVISED-1_new_IGAv1.pdf (BS Electrical Engineering)
  2. PROGRAM_STRUCTURE-_STRUCTURAL.pdf (BS Civil Engineering)
  3. Prog Structure_BSECE_revised_july2019.pdf (BS Electronics Engineering)
  4. BSME_Approved-Program-Structure.pdf (BS Mechanical Engineering)
  5. BSSE Approved Program Structure (1).pdf (BS Sanitary Engineering)
  6. 9.-Program-Structure_SY2020-2021_revision1.pdf & 8. Program Structure_ABE.pdf (BS Agricultural and Biosystems Engineering)
  7. BSGE Approved Program Structure.pdf (BS Geodetic Engineering)
  8. BSEM-Approved-Program-Structure (1).pdf (BS Mining Engineering)
  9. Program-Structure-with-CMO_Geology.docx (BS Geology)

Includes:
  - Institutionalized Graduate Attributes (IGAs):
      * New USeP 5-IGA Framework (IGA1 - IGA5, FM-USeP-MID-01 & New IGAv1)
      * Program Structure 6-IGA Framework (IGA1 - IGA6)
  - Program Educational Objectives (PEOs)
  - Program Graduate Outcomes (PGOs)
  - Respective Performance Indicators (PIs) and IGA alignments per PGO/PI
"""

from copy import deepcopy
from typing import Dict, List, Any

# ==============================================================================
# 1. INSTITUTIONALIZED GRADUATE ATTRIBUTES (IGAs)
# ==============================================================================
NEW_USEP_IGAS: List[Dict[str, str]] = [
    {
        "code": "IGA1",
        "title": "Leadership Skills",
        "short_label": "IGA1 – Leadership Skills",
        "description": "Creates and inspires positive changes in the organization; exercises responsibility with integrity and accountability.",
    },
    {
        "code": "IGA2",
        "title": "Critical and Analytical Thinking Skills",
        "short_label": "IGA2 – Critical & Analytical Thinking",
        "description": "Demonstrates creativity, innovativeness, and intellectual curiosity in optimizing available resources to develop new knowledge and methods.",
    },
    {
        "code": "IGA3",
        "title": "Service Oriented",
        "short_label": "IGA3 – Service Oriented",
        "description": "Demonstrates concern for others, practices professional ethics, honesty, and exemplifies socio-cultural, environmental concern, and sustainability.",
    },
    {
        "code": "IGA4",
        "title": "Lifelong Learning",
        "short_label": "IGA4 – Lifelong Learning",
        "description": "Demonstrates enthusiasm and passion for continuous personal and professional development.",
    },
    {
        "code": "IGA5",
        "title": "Professional Competence",
        "short_label": "IGA5 – Professional Competence",
        "description": "Demonstrates proficiency and flexibility in the area of specialization and in conveying information in accordance with global standards.",
    },
]

PROGRAM_STRUCTURE_6_IGAS: List[Dict[str, str]] = [
    {
        "code": "IGA1",
        "title": "Critical Analysis",
        "short_label": "IGA1 – Critical Analysis",
        "description": "Applies analytical, critical, and problem-solving skills using scientific and engineering methods.",
    },
    {
        "code": "IGA2",
        "title": "Leadership and Teamwork",
        "short_label": "IGA2 – Leadership and Teamwork",
        "description": "Functions effectively as a member and leader in multidisciplinary and multicultural teams.",
    },
    {
        "code": "IGA3",
        "title": "Service-Oriented",
        "short_label": "IGA3 – Service-Oriented",
        "description": "Demonstrates social awareness, civic responsibility, and sustainable engineering solutions for the community.",
    },
    {
        "code": "IGA4",
        "title": "Professional Competence",
        "short_label": "IGA4 – Professional Competence",
        "description": "Exhibits mastery of core engineering principles, modern tools, design standards, and ethical practice.",
    },
    {
        "code": "IGA5",
        "title": "Communication",
        "short_label": "IGA5 – Communication",
        "description": "Articulates complete engineering thought and technical information effectively in oral, written, and graphical forms.",
    },
    {
        "code": "IGA6",
        "title": "Life-Long Learning",
        "short_label": "IGA6 – Life-Long Learning",
        "description": "Recognizes the need for, and engages in independent, continuous professional learning and development.",
    },
]


# ==============================================================================
# 2. BASE ENGINEERING PGOs (a - m) & PERFORMANCE INDICATORS FROM PROGRAM STRUCTURE
#    (Matches BSEE, BSCE, BSECE, BSME, BSSE, BSGE, BSEM Program Structure PDFs)
# ==============================================================================
BASE_ENGINEERING_PGOS: List[Dict[str, Any]] = [
    {
        "pgo_code": "PGO a",
        "pgo_id": "PGO-a",
        "letter": "a",
        "description": "a) Apply knowledge of mathematics and sciences to solve engineering problems",
        "short_label": "PGO a – Apply knowledge of mathematics & sciences",
        "igas": "IGA2, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA6",
        "pis": [
            {
                "pi_id": "PI-a.1",
                "pi_code": "a.1",
                "full_text": "a.1. Apply concepts in mathematics to solve engineering problems.",
                "description": "Apply concepts in mathematics to solve engineering problems.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-a.2",
                "pi_code": "a.2",
                "full_text": "a.2. Apply principles in chemical sciences to solve engineering problems.",
                "description": "Apply principles in chemical sciences to solve engineering problems.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-a.3",
                "pi_code": "a.3",
                "full_text": "a.3. Apply principles in physical sciences to solve engineering problems.",
                "description": "Apply principles in physical sciences to solve engineering problems.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO b",
        "pgo_id": "PGO-b",
        "letter": "b",
        "description": "b) Design and conduct experiments, as well as to analyze and interpret data",
        "short_label": "PGO b – Design & conduct experiments, analyze data",
        "igas": "IGA2, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA5, IGA6",
        "pis": [
            {
                "pi_id": "PI-b.1",
                "pi_code": "b.1",
                "full_text": "b.1. Perform laboratory experiments as prescribed by standard procedures.",
                "description": "Perform laboratory experiments as prescribed by standard procedures.",
                "igas": "IGA2, IGA5",
                "igas_legacy": "IGA1, IGA4",
            },
            {
                "pi_id": "PI-b.2",
                "pi_code": "b.2",
                "full_text": "b.2. Design an experiment to achieve a specific objective.",
                "description": "Design an experiment to achieve a specific objective.",
                "igas": "IGA4, IGA5",
                "igas_legacy": "IGA5, IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO c",
        "pgo_id": "PGO-c",
        "letter": "c",
        "description": (
            "c) Design a system, component, or process to meet desired needs within realistic constraints "
            "such as economic, environmental, social, political, ethical, health and safety, manufacturability, "
            "and sustainability, in accordance with standards."
        ),
        "short_label": "PGO c – Design system, component, or process within constraints",
        "igas": "IGA1, IGA2, IGA3, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA2, IGA3, IGA4, IGA5, IGA6",
        "pis": [
            {
                "pi_id": "PI-c.1",
                "pi_code": "c.1",
                "full_text": "c.1. Develop an engineering solution that have various constraints as factors.",
                "description": "Develop an engineering solution that have various constraints as factors.",
                "igas": "IGA1, IGA2, IGA3, IGA4, IGA5",
                "igas_legacy": "IGA1, IGA2, IGA3, IGA4, IGA5, IGA6",
            },
            {
                "pi_id": "PI-c.2",
                "pi_code": "c.2",
                "full_text": "c.2. Design a system or process based on various constraints.",
                "description": "Design a system or process based on various constraints.",
                "igas": "IGA1, IGA2, IGA3, IGA4, IGA5",
                "igas_legacy": "IGA1, IGA2, IGA3, IGA4, IGA5, IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO d",
        "pgo_id": "PGO-d",
        "letter": "d",
        "description": "d) Function on multidisciplinary teams",
        "short_label": "PGO d – Function on multidisciplinary teams",
        "igas": "IGA1, IGA3, IGA4",
        "igas_legacy": "IGA2, IGA3, IGA6",
        "pis": [
            {
                "pi_id": "PI-d.1",
                "pi_code": "d.1",
                "full_text": "d.1. Shows tact in dealing with people he/she comes in contact with.",
                "description": "Shows tact in dealing with people he/she comes in contact with.",
                "igas": "IGA1",
                "igas_legacy": "IGA2",
            },
            {
                "pi_id": "PI-d.2",
                "pi_code": "d.2",
                "full_text": "d.2. Capable of learning from and listening to co-members.",
                "description": "Capable of learning from and listening to co-members.",
                "igas": "IGA3",
                "igas_legacy": "IGA3",
            },
            {
                "pi_id": "PI-d.3",
                "pi_code": "d.3",
                "full_text": "d.3. Shows respect and courtesy in dealing with peers and superiors.",
                "description": "Shows respect and courtesy in dealing with peers and superiors.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO e",
        "pgo_id": "PGO-e",
        "letter": "e",
        "description": "e) Identify, formulate, and solve engineering problems",
        "short_label": "PGO e – Identify, formulate, & solve engineering problems",
        "igas": "IGA2, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA6",
        "pis": [
            {
                "pi_id": "PI-e.1",
                "pi_code": "e.1",
                "full_text": "e.1. Interpret statement problems into mathematical expressions.",
                "description": "Interpret statement problems into mathematical expressions.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-e.2",
                "pi_code": "e.2",
                "full_text": "e.2. Apply concepts, theories, and principles in solving engineering problem(s)",
                "description": "Apply concepts, theories, and principles in solving engineering problem(s)",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-e.3",
                "pi_code": "e.3",
                "full_text": "e.3. Solve specific engineering problem related to discipline.",
                "description": "Solve specific engineering problem related to discipline.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO f",
        "pgo_id": "PGO-f",
        "letter": "f",
        "description": "f) Understand professional, social and ethical responsibility",
        "short_label": "PGO f – Professional, social & ethical responsibility",
        "igas": "IGA4, IGA5",
        "igas_legacy": "IGA4, IGA5, IGA6",
        "pis": [
            {
                "pi_id": "PI-f.1",
                "pi_code": "f.1",
                "full_text": "f.1. Internalizes the professional code of ethics for specific discipline.",
                "description": "Internalizes the professional code of ethics for specific discipline.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-f.2",
                "pi_code": "f.2",
                "full_text": "f.2. Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "igas": "IGA4, IGA5",
                "igas_legacy": "IGA5, IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO g",
        "pgo_id": "PGO-g",
        "letter": "g",
        "description": "g) Communicate effectively",
        "short_label": "PGO g – Communicate effectively",
        "igas": "IGA4, IGA5",
        "igas_legacy": "IGA4, IGA5, IGA6",
        "pis": [
            {
                "pi_id": "PI-g.1",
                "pi_code": "g.1",
                "full_text": "g.1. Articulate the convention and style in oral communication that conveys complete thought and information.",
                "description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-g.2",
                "pi_code": "g.2",
                "full_text": "g.2. Articulate the convention and style in written communication that conveys complete thought and information.",
                "description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "igas": "IGA5",
                "igas_legacy": "IGA5",
            },
            {
                "pi_id": "PI-g.3",
                "pi_code": "g.3",
                "full_text": "g.3. Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO h",
        "pgo_id": "PGO-h",
        "letter": "h",
        "description": "h) Understand the impact of engineering solutions in a global, economic, environmental, & societal context through broad education",
        "short_label": "PGO h – Impact of engineering solutions in global/societal context",
        "igas": "IGA2, IGA3, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA3, IGA4, IGA6",
        "pis": [
            {
                "pi_id": "PI-h.1",
                "pi_code": "h.1",
                "full_text": "h.1. Relate engineering solutions to global, economic, environmental, and societal context.",
                "description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "igas": "IGA2, IGA3",
                "igas_legacy": "IGA1, IGA3",
            },
            {
                "pi_id": "PI-h.2",
                "pi_code": "h.2",
                "full_text": "h.2. Describe engineering solutions in application to global, economic, environmental, and societal context.",
                "description": "Describe engineering solutions in application to global, economic, environmental, and societal context.",
                "igas": "IGA4, IGA5",
                "igas_legacy": "IGA4, IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO i",
        "pgo_id": "PGO-i",
        "letter": "i",
        "description": "i) Recognize the need for, and an ability to engage in life-long learning",
        "short_label": "PGO i – Engage in life-long learning",
        "igas": "IGA1, IGA2, IGA3, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA2, IGA3, IGA4, IGA5, IGA6",
        "pis": [
            {
                "pi_id": "PI-i.1",
                "pi_code": "i.1",
                "full_text": "i.1. Demonstrate ability to learn independently.",
                "description": "Demonstrate ability to learn independently.",
                "igas": "IGA1, IGA2",
                "igas_legacy": "IGA1, IGA2",
            },
            {
                "pi_id": "PI-i.2",
                "pi_code": "i.2",
                "full_text": "i.2. Shows appreciation and understanding of the engineering profession.",
                "description": "Shows appreciation and understanding of the engineering profession.",
                "igas": "IGA3, IGA5",
                "igas_legacy": "IGA3, IGA4",
            },
            {
                "pi_id": "PI-i.3",
                "pi_code": "i.3",
                "full_text": "i.3. Understand the linkage or connection between his/her task to previous, intervening and subsequent tasks.",
                "description": "Understand the linkage or connection between his/her task to previous, intervening and subsequent tasks.",
                "igas": "IGA4, IGA5",
                "igas_legacy": "IGA5, IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO j",
        "pgo_id": "PGO-j",
        "letter": "j",
        "description": "j) Apply knowledge of contemporary issues",
        "short_label": "PGO j – Apply knowledge of contemporary issues",
        "igas": "IGA1, IGA3, IGA4, IGA5",
        "igas_legacy": "IGA2, IGA3, IGA4, IGA5, IGA6",
        "pis": [
            {
                "pi_id": "PI-j.1",
                "pi_code": "j.1",
                "full_text": "j.1. Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
                "description": "Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
                "igas": "IGA1, IGA3",
                "igas_legacy": "IGA2, IGA3",
            },
            {
                "pi_id": "PI-j.2",
                "pi_code": "j.2",
                "full_text": "j.2. Explain the possible impact of technology to local, national, and international issues.",
                "description": "Explain the possible impact of technology to local, national, and international issues.",
                "igas": "IGA5",
                "igas_legacy": "IGA4, IGA5",
            },
            {
                "pi_id": "PI-j.3",
                "pi_code": "j.3",
                "full_text": "j.3. Shows leadership skills in managing a multidisciplinary group.",
                "description": "Shows leadership skills in managing a multidisciplinary group.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO k",
        "pgo_id": "PGO-k",
        "letter": "k",
        "description": "k) Use techniques, skills, and modern engineering tools necessary for engineering practice",
        "short_label": "PGO k – Use modern engineering tools & techniques",
        "igas": "IGA2, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA6",
        "pis": [
            {
                "pi_id": "PI-k.1",
                "pi_code": "k.1",
                "full_text": "k.1. Handles the details of the work assigned to him/her.",
                "description": "Handles the details of the work assigned to him/her.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-k.2",
                "pi_code": "k.2",
                "full_text": "k.2. Demonstrate the ability to operate the equipment needed in the engineering practice.",
                "description": "Demonstrate the ability to operate the equipment needed in the engineering practice.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-k.3",
                "pi_code": "k.3",
                "full_text": "k.3. Use modern technology in performing engineering practice.",
                "description": "Use modern technology in performing engineering practice.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO l",
        "pgo_id": "PGO-l",
        "letter": "l",
        "description": (
            "l) Apply knowledge of engineering and management principles as a member and leader in a team, "
            "and to manage projects and in multidisciplinary environments"
        ),
        "short_label": "PGO l – Engineering & management principles in projects",
        "igas": "IGA1, IGA2, IGA3, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA2, IGA3, IGA4, IGA5, IGA6",
        "pis": [
            {
                "pi_id": "PI-l.1",
                "pi_code": "l.1",
                "full_text": "l.1. Capable of learning from and listening to co-members.",
                "description": "Capable of learning from and listening to co-members.",
                "igas": "IGA1, IGA2",
                "igas_legacy": "IGA1, IGA2",
            },
            {
                "pi_id": "PI-l.2",
                "pi_code": "l.2",
                "full_text": "l.2. Shows leadership skills in managing a multidisciplinary group.",
                "description": "Shows leadership skills in managing a multidisciplinary group.",
                "igas": "IGA3, IGA5",
                "igas_legacy": "IGA3, IGA4",
            },
            {
                "pi_id": "PI-l.3",
                "pi_code": "l.3",
                "full_text": "l.3. Participates in discussions and comes up with sound suggestions to problems.",
                "description": "Participates in discussions and comes up with sound suggestions to problems.",
                "igas": "IGA4, IGA5",
                "igas_legacy": "IGA5, IGA6",
            },
        ],
    },
]


def _build_standard_eng_pgos(specialized_field_name: str = "") -> List[Dict[str, Any]]:
    """
    Returns a copy of PGO a - l, and appends PGO m if the engineering program has
    outcome 'm' (Understand at least one specialized field of <discipline> practice).
    """
    pgos = deepcopy(BASE_ENGINEERING_PGOS)
    if specialized_field_name:
        pgos.append({
            "pgo_code": "PGO m",
            "pgo_id": "PGO-m",
            "letter": "m",
            "description": f"m) Understand at least one specialized field of {specialized_field_name} practice",
            "short_label": f"PGO m – Specialized field of {specialized_field_name.title()} practice",
            "igas": "IGA4",
            "igas_legacy": "IGA6",
            "pis": [
                {
                    "pi_id": "PI-m.1",
                    "pi_code": "m.1",
                    "full_text": "m.1. Demonstrate leadership and team management in a multidisciplinary group.",
                    "description": "Demonstrate leadership and team management in a multidisciplinary group.",
                    "igas": "IGA4",
                    "igas_legacy": "IGA6",
                },
                {
                    "pi_id": "PI-m.2",
                    "pi_code": "m.2",
                    "full_text": "m.2. Capable of learning from and listening to co-members.",
                    "description": "Capable of learning from and listening to co-members.",
                    "igas": "IGA4",
                    "igas_legacy": "IGA6",
                },
                {
                    "pi_id": "PI-m.3",
                    "pi_code": "m.3",
                    "full_text": "m.3. Apply designed system or process to solve engineering problems.",
                    "description": "Apply designed system or process to solve engineering problems.",
                    "igas": "IGA4",
                    "igas_legacy": "IGA6",
                },
            ],
        })
    return pgos


# ==============================================================================
# 3. BS AGRICULTURAL AND BIOSYSTEMS ENGINEERING (BSABE) PGOs & PIs
#    (From '9.-Program-Structure_SY2020-2021_revision1.pdf' & '8. Program Structure_ABE.pdf')
# ==============================================================================
BSABE_PGOS: List[Dict[str, Any]] = [
    {
        "pgo_code": "PGO1",
        "pgo_id": "PGO-1",
        "letter": "a",
        "description": "PGO1 (a) Apply knowledge of mathematics and science to solve complex AB engineering problems",
        "short_label": "PGO1 (a) – Apply math & science to complex AB engineering problems",
        "igas": "IGA2",
        "igas_legacy": "IGA1 (Critical Analysis)",
        "pis": [
            {
                "pi_id": "PI-1.1",
                "pi_code": "1.1",
                "full_text": "1.1. Apply mathematics in designing agricultural structures, irrigation systems, and agricultural machineries.",
                "description": "Apply mathematics in designing agricultural structures, irrigation systems, and agricultural machineries.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-1.2",
                "pi_code": "1.2",
                "full_text": "1.2. Apply knowledge in Physics, thermodynamics, and heat transfer in designing agricultural drying and storage facilities.",
                "description": "Apply knowledge in Physics, thermodynamics, and heat transfer in designing agricultural drying and storage facilities.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-1.3",
                "pi_code": "1.3",
                "full_text": "1.3. Apply chemistry & biological sciences in designing cold storage facilities & biological wastes recovery systems.",
                "description": "Apply chemistry & biological sciences in designing cold storage facilities & biological wastes recovery systems.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
        ],
    },
    {
        "pgo_code": "PGO2",
        "pgo_id": "PGO-2",
        "letter": "b",
        "description": "PGO2 (b) Design and conduct experiments, as well as to analyze and interpret data",
        "short_label": "PGO2 (b) – Design & conduct experiments, analyze & interpret data",
        "igas": "IGA2",
        "igas_legacy": "IGA1 (Critical Analysis)",
        "pis": [
            {
                "pi_id": "PI-2.1",
                "pi_code": "2.1",
                "full_text": "2.1. Formulate and design research proposal.",
                "description": "Formulate and design research proposal.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-2.2",
                "pi_code": "2.2",
                "full_text": "2.2. Conduct scientific research under laboratory and field conditions.",
                "description": "Conduct scientific research under laboratory and field conditions.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-2.3",
                "pi_code": "2.3",
                "full_text": "2.3. Analyze, interpret, and write research results.",
                "description": "Analyze, interpret, and write research results.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
        ],
    },
    {
        "pgo_code": "PGO3",
        "pgo_id": "PGO-3",
        "letter": "c",
        "description": "PGO3 (c) Design a system, component, or process to meet desired needs within realistic constraints, in accordance with standards",
        "short_label": "PGO3 (c) – Design AB system, component, or process within constraints",
        "igas": "IGA5",
        "igas_legacy": "IGA4 (Professional Competence)",
        "pis": [
            {
                "pi_id": "PI-3.1",
                "pi_code": "3.1",
                "full_text": "3.1. Design agricultural structures and electrical systems using computer-aided design software.",
                "description": "Design agricultural structures and electrical systems using computer-aided design software.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-3.2",
                "pi_code": "3.2",
                "full_text": "3.2. Design irrigation systems for cash, annual, and plantation crops.",
                "description": "Design irrigation systems for cash, annual, and plantation crops.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-3.3",
                "pi_code": "3.3",
                "full_text": "3.3. Design, fabricate, and evaluate performance of agricultural machineries and equipment.",
                "description": "Design, fabricate, and evaluate performance of agricultural machineries and equipment.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
        ],
    },
    {
        "pgo_code": "PGO4",
        "pgo_id": "PGO-4",
        "letter": "d",
        "description": "PGO4 (d) Function in multidisciplinary teams",
        "short_label": "PGO4 (d) – Function in multidisciplinary teams",
        "igas": "IGA1",
        "igas_legacy": "IGA2 (Leadership and Teamwork)",
        "pis": [
            {
                "pi_id": "PI-4.1",
                "pi_code": "4.1",
                "full_text": "4.1. Demonstrate to work in a team as team member and/or as team leader.",
                "description": "Demonstrate to work in a team as team member and/or as team leader.",
                "igas": "IGA1",
                "igas_legacy": "IGA2",
            },
            {
                "pi_id": "PI-4.2",
                "pi_code": "4.2",
                "full_text": "4.2. Deliver assigned tasks promptly and comprehensively.",
                "description": "Deliver assigned tasks promptly and comprehensively.",
                "igas": "IGA1",
                "igas_legacy": "IGA2",
            },
            {
                "pi_id": "PI-4.3",
                "pi_code": "4.3",
                "full_text": "4.3. Initiate conduct of group-based laboratory experiments in multi-disciplinary engineering subjects.",
                "description": "Initiate conduct of group-based laboratory experiments in multi-disciplinary engineering subjects.",
                "igas": "IGA1",
                "igas_legacy": "IGA2",
            },
        ],
    },
    {
        "pgo_code": "PGO5",
        "pgo_id": "PGO-5",
        "letter": "e",
        "description": "PGO5 (e) Identify, formulate, and solve complex AB engineering problems",
        "short_label": "PGO5 (e) – Identify, formulate, & solve complex AB engineering problems",
        "igas": "IGA2",
        "igas_legacy": "IGA1 (Critical Analysis)",
        "pis": [
            {
                "pi_id": "PI-5.1",
                "pi_code": "5.1",
                "full_text": "5.1. Identify researchable areas in at least three (3) major fields in Agricultural Engineering.",
                "description": "Identify researchable areas in at least three (3) major fields in Agricultural Engineering.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-5.2",
                "pi_code": "5.2",
                "full_text": "5.2. Formulate solutions to the specified engineering problems identified.",
                "description": "Formulate solutions to the specified engineering problems identified.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
            {
                "pi_id": "PI-5.3",
                "pi_code": "5.3",
                "full_text": "5.3. Produce at least one simulated model as solution to an engineering problem.",
                "description": "Produce at least one simulated model as solution to an engineering problem.",
                "igas": "IGA2",
                "igas_legacy": "IGA1",
            },
        ],
    },
    {
        "pgo_code": "PGO6",
        "pgo_id": "PGO-6",
        "letter": "f",
        "description": "PGO6 (f) Understand professional and ethical responsibility",
        "short_label": "PGO6 (f) – Understand professional and ethical responsibility",
        "igas": "IGA5",
        "igas_legacy": "IGA4 (Professional Competence)",
        "pis": [
            {
                "pi_id": "PI-6.1",
                "pi_code": "6.1",
                "full_text": "6.1. Identify relevant laws in the practice of the profession and the duties and responsibilities of Agricultural Engineers.",
                "description": "Identify relevant laws in the practice of the profession and the duties and responsibilities of Agricultural Engineers.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-6.2",
                "pi_code": "6.2",
                "full_text": "6.2. Describe the important provisions of laws and the responsibilities of Agricultural Engineers.",
                "description": "Describe the important provisions of laws and the responsibilities of Agricultural Engineers.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-6.3",
                "pi_code": "6.3",
                "full_text": "6.3. Comprehend the moral issues and ethical responsibilities of agricultural engineers as practitioner and as member of an organization.",
                "description": "Comprehend the moral issues and ethical responsibilities of agricultural engineers as practitioner and as member of an organization.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
        ],
    },
    {
        "pgo_code": "PGO7",
        "pgo_id": "PGO-7",
        "letter": "g",
        "description": "PGO7 (g) Communicate effectively complex AB engineering activities",
        "short_label": "PGO7 (g) – Communicate effectively complex AB engineering activities",
        "igas": "IGA5",
        "igas_legacy": "IGA5 (Communication)",
        "pis": [
            {
                "pi_id": "PI-7.1",
                "pi_code": "7.1",
                "full_text": "7.1. Produce technical-based reaction papers and reports.",
                "description": "Produce technical-based reaction papers and reports.",
                "igas": "IGA5",
                "igas_legacy": "IGA5",
            },
            {
                "pi_id": "PI-7.2",
                "pi_code": "7.2",
                "full_text": "7.2. Produce and present effective oral communication materials.",
                "description": "Produce and present effective oral communication materials.",
                "igas": "IGA5",
                "igas_legacy": "IGA5",
            },
            {
                "pi_id": "PI-7.3",
                "pi_code": "7.3",
                "full_text": "7.3. Adapt presentation styles and contents to match specific audiences.",
                "description": "Adapt presentation styles and contents to match specific audiences.",
                "igas": "IGA5",
                "igas_legacy": "IGA5",
            },
        ],
    },
    {
        "pgo_code": "PGO8",
        "pgo_id": "PGO-8",
        "letter": "h",
        "description": "PGO8 (h) Understand the impact of engineering solutions in a global, economic, environmental and societal context",
        "short_label": "PGO8 (h) – Impact of engineering solutions in global/societal context",
        "igas": "IGA3",
        "igas_legacy": "IGA3 (Service-Oriented)",
        "pis": [
            {
                "pi_id": "PI-8.1",
                "pi_code": "8.1",
                "full_text": "8.1. Identify issues and impacts of agricultural engineering practices and activities using online and other data sources.",
                "description": "Identify issues and impacts of agricultural engineering practices and activities using online and other data sources.",
                "igas": "IGA3",
                "igas_legacy": "IGA3",
            },
            {
                "pi_id": "PI-8.2",
                "pi_code": "8.2",
                "full_text": "8.2. Prepare feasibility study of one engineering community-based project.",
                "description": "Prepare feasibility study of one engineering community-based project.",
                "igas": "IGA3",
                "igas_legacy": "IGA3",
            },
            {
                "pi_id": "PI-8.3",
                "pi_code": "8.3",
                "full_text": "8.3. Organize technical seminars and evaluate the results.",
                "description": "Organize technical seminars and evaluate the results.",
                "igas": "IGA3",
                "igas_legacy": "IGA3",
            },
        ],
    },
    {
        "pgo_code": "PGO9",
        "pgo_id": "PGO-9",
        "letter": "i",
        "description": "PGO9 (i) Recognize the need for, and an ability to engage in life-long learning",
        "short_label": "PGO9 (i) – Recognize need for & engage in life-long learning",
        "igas": "IGA4",
        "igas_legacy": "IGA6 (Life-Long Learning)",
        "pis": [
            {
                "pi_id": "PI-9.1",
                "pi_code": "9.1",
                "full_text": "9.1. Evaluate community-based engineering problem and recommend solutions.",
                "description": "Evaluate community-based engineering problem and recommend solutions.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
            {
                "pi_id": "PI-9.2",
                "pi_code": "9.2",
                "full_text": "9.2. Prepare feasibility study of one engineering community-based project.",
                "description": "Prepare feasibility study of one engineering community-based project.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
            {
                "pi_id": "PI-9.3",
                "pi_code": "9.3",
                "full_text": "9.3. Organize technical seminars and evaluate the results.",
                "description": "Organize technical seminars and evaluate the results.",
                "igas": "IGA4",
                "igas_legacy": "IGA6",
            },
        ],
    },
    {
        "pgo_code": "PGO10",
        "pgo_id": "PGO-10",
        "letter": "j",
        "description": "PGO10 (j) Know contemporary issues",
        "short_label": "PGO10 (j) – Know contemporary issues",
        "igas": "IGA3",
        "igas_legacy": "IGA3 (Service-Oriented)",
        "pis": [
            {
                "pi_id": "PI-10.1",
                "pi_code": "10.1",
                "full_text": "10.1. Explain the role of Agricultural Engineers on social, economic, political, and environmental issues relevant to nation building, security, and stability.",
                "description": "Explain the role of Agricultural Engineers on social, economic, political, and environmental issues relevant to nation building, security, and stability.",
                "igas": "IGA3",
                "igas_legacy": "IGA3",
            },
            {
                "pi_id": "PI-10.2",
                "pi_code": "10.2",
                "full_text": "10.2. Analyze the effects of current social, economic, political, and environmental issues to national development and stability.",
                "description": "Analyze the effects of current social, economic, political, and environmental issues to national development and stability.",
                "igas": "IGA3",
                "igas_legacy": "IGA3",
            },
            {
                "pi_id": "PI-10.3",
                "pi_code": "10.3",
                "full_text": "10.3. Recognize the impact of Agricultural Engineering Technologies on local, national, and international issues.",
                "description": "Recognize the impact of Agricultural Engineering Technologies on local, national, and international issues.",
                "igas": "IGA3",
                "igas_legacy": "IGA3",
            },
        ],
    },
    {
        "pgo_code": "PGO11",
        "pgo_id": "PGO-11",
        "letter": "k",
        "description": "PGO11 (k) Use techniques, skills, and modern engineering tools necessary for engineering practice",
        "short_label": "PGO11 (k) – Use techniques, skills, & modern AB engineering tools",
        "igas": "IGA5",
        "igas_legacy": "IGA4 (Professional Competence)",
        "pis": [
            {
                "pi_id": "PI-11.1",
                "pi_code": "11.1",
                "full_text": "11.1. Describe the functionality, operation, and application of modern agricultural engineering tools and equipment.",
                "description": "Describe the functionality, operation, and application of modern agricultural engineering tools and equipment.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-11.2",
                "pi_code": "11.2",
                "full_text": "11.2. Prepare an effective and systematic design procedures to enhance skills and techniques in implementing agricultural engineering practice.",
                "description": "Prepare an effective and systematic design procedures to enhance skills and techniques in implementing agricultural engineering practice.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-11.3",
                "pi_code": "11.3",
                "full_text": "11.3. Demonstrate agricultural structure design output as a proof of development in the engineering practice.",
                "description": "Demonstrate agricultural structure design output as a proof of development in the engineering practice.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
        ],
    },
    {
        "pgo_code": "PGO12",
        "pgo_id": "PGO-12",
        "letter": "l",
        "description": "PGO12 (l) Know and understand engineering and management principles as a member and leader in a team, to manage projects and in multidisciplinary environments",
        "short_label": "PGO12 (l) – Engineering & management principles in AB projects",
        "igas": "IGA1",
        "igas_legacy": "IGA2 (Leadership and Teamwork)",
        "pis": [
            {
                "pi_id": "PI-12.1",
                "pi_code": "12.1",
                "full_text": "12.1. Describe managerial concepts and techniques adopted by successful Technical Managers, Project Directors, & other technically oriented managers.",
                "description": "Describe managerial concepts and techniques adopted by successful Technical Managers, Project Directors, & other technically oriented managers.",
                "igas": "IGA1",
                "igas_legacy": "IGA2",
            },
            {
                "pi_id": "PI-12.2",
                "pi_code": "12.2",
                "full_text": "12.2. Understand leadership and management skills necessary in the successful implementation of Ag Engineering projects.",
                "description": "Understand leadership and management skills necessary in the successful implementation of Ag Engineering projects.",
                "igas": "IGA1",
                "igas_legacy": "IGA2",
            },
            {
                "pi_id": "PI-12.3",
                "pi_code": "12.3",
                "full_text": "12.3. Prepare feasibility study of one engineering community-based project.",
                "description": "Prepare feasibility study of one engineering community-based project.",
                "igas": "IGA1",
                "igas_legacy": "IGA2",
            },
        ],
    },
    {
        "pgo_code": "PGO13",
        "pgo_id": "PGO-13",
        "letter": "m",
        "description": "PGO13 (m) Understand at least one specialized field of agricultural and biosystems engineering practice",
        "short_label": "PGO13 (m) – Specialized field of AB engineering practice",
        "igas": "IGA5",
        "igas_legacy": "IGA4 (Professional Competence)",
        "pis": [
            {
                "pi_id": "PI-13.1",
                "pi_code": "13.1",
                "full_text": "13.1. Exemplify the concepts, theories and engineering practices in farm power and machinery.",
                "description": "Exemplify the concepts, theories and engineering practices in farm power and machinery.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-13.2",
                "pi_code": "13.2",
                "full_text": "13.2. Exemplify the concepts, theories and engineering practices in soil and water conservation.",
                "description": "Exemplify the concepts, theories and engineering practices in soil and water conservation.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-13.3",
                "pi_code": "13.3",
                "full_text": "13.3. Exemplify the concepts, theories and engineering practices in crop processing, postharvest technology and renewable energy technology.",
                "description": "Exemplify the concepts, theories and engineering practices in crop processing, postharvest technology and renewable energy technology.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
            {
                "pi_id": "PI-13.4",
                "pi_code": "13.4",
                "full_text": "13.4. Exemplify the concepts, theories and engineering practices in agricultural structures and environmental management.",
                "description": "Exemplify the concepts, theories and engineering practices in agricultural structures and environmental management.",
                "igas": "IGA5",
                "igas_legacy": "IGA4",
            },
        ],
    },
]


# ==============================================================================
# 4. BS GEOLOGY (BSGeo) PGOs (PGO1 - PGO22) & PERFORMANCE INDICATORS
#    (From 'Program-Structure-with-CMO_Geology.docx')
# ==============================================================================
BSGEO_PGOS: List[Dict[str, Any]] = [
    {
        "pgo_code": "PGO1",
        "pgo_id": "PGO-1",
        "letter": "1",
        "description": "PGO1) Engage in lifelong learning and understanding of the need to keep abreast of the developments in the specific field of practice",
        "short_label": "PGO1 – Engage in lifelong learning in Geology",
        "igas": "IGA2, IGA4",
        "igas_legacy": "IGA1, IGA6",
        "pis": [
            {"pi_id": "PI-1.1", "pi_code": "1.1", "full_text": "1.1. Participate in conferences, seminars and workshops in the field of geology and allied sciences.", "description": "Participate in conferences, seminars and workshops in the field of geology and allied sciences.", "igas": "IGA2, IGA4", "igas_legacy": "IGA1, IGA6"},
            {"pi_id": "PI-1.2", "pi_code": "1.2", "full_text": "1.2. Demonstrate ability to learn independently.", "description": "Demonstrate ability to learn independently.", "igas": "IGA2, IGA4", "igas_legacy": "IGA1, IGA6"},
            {"pi_id": "PI-1.3", "pi_code": "1.3", "full_text": "1.3. Contribute to the new knowledge of the Science of Geology through research, publication and innovations.", "description": "Contribute to the new knowledge of the Science of Geology through research, publication and innovations.", "igas": "IGA2, IGA4", "igas_legacy": "IGA1, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO2",
        "pgo_id": "PGO-2",
        "letter": "2",
        "description": "PGO2) Communicate effectively thru oral and in writing using both English and Filipino",
        "short_label": "PGO2 – Communicate effectively in English and Filipino",
        "igas": "IGA4, IGA5",
        "igas_legacy": "IGA5, IGA6",
        "pis": [
            {"pi_id": "PI-2.1", "pi_code": "2.1", "full_text": "2.1. Articulate the convention and style in written communication that conveys complete thought and information.", "description": "Articulate the convention and style in written communication that conveys complete thought and information.", "igas": "IGA4, IGA5", "igas_legacy": "IGA5, IGA6"},
            {"pi_id": "PI-2.2", "pi_code": "2.2", "full_text": "2.2. Describe and discuss the different concepts and issues in Geology as it pertains to real world applications to both scientific and laymen audience.", "description": "Describe and discuss the different concepts and issues in Geology as it pertains to real world applications to both scientific and laymen audience.", "igas": "IGA4, IGA5", "igas_legacy": "IGA5, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO3",
        "pgo_id": "PGO-3",
        "letter": "3",
        "description": "PGO3) Perform effectively and independently in multi-disciplinary and multi-cultural teams",
        "short_label": "PGO3 – Perform effectively in multi-disciplinary & multi-cultural teams",
        "igas": "IGA1, IGA3",
        "igas_legacy": "IGA2, IGA3",
        "pis": [
            {"pi_id": "PI-3.1", "pi_code": "3.1", "full_text": "3.1. Shows tact in dealing with people he/she works and interacts.", "description": "Shows tact in dealing with people he/she works and interacts.", "igas": "IGA1, IGA3", "igas_legacy": "IGA2, IGA3"},
            {"pi_id": "PI-3.2", "pi_code": "3.2", "full_text": "3.2. Capable of learning from and listening to co-members.", "description": "Capable of learning from and listening to co-members.", "igas": "IGA1, IGA3", "igas_legacy": "IGA2, IGA3"},
            {"pi_id": "PI-3.3", "pi_code": "3.3", "full_text": "3.3. Shows respect and courtesy in dealing with peers and superiors.", "description": "Shows respect and courtesy in dealing with peers and superiors.", "igas": "IGA1, IGA3", "igas_legacy": "IGA2, IGA3"},
        ],
    },
    {
        "pgo_code": "PGO4",
        "pgo_id": "PGO-4",
        "letter": "4",
        "description": "PGO4) Recognize professional, social, and ethical responsibility",
        "short_label": "PGO4 – Recognize professional, social, and ethical responsibility",
        "igas": "IGA3, IGA4, IGA5",
        "igas_legacy": "IGA3, IGA4, IGA6",
        "pis": [
            {"pi_id": "PI-4.1", "pi_code": "4.1", "full_text": "4.1. Shows appreciation and understanding of the geology profession.", "description": "Shows appreciation and understanding of the geology profession.", "igas": "IGA3, IGA4, IGA5", "igas_legacy": "IGA3, IGA4, IGA6"},
            {"pi_id": "PI-4.2", "pi_code": "4.2", "full_text": "4.2. State the current social, economic, political, and environmental issues related to the practice of geology.", "description": "State the current social, economic, political, and environmental issues related to the practice of geology.", "igas": "IGA3, IGA4, IGA5", "igas_legacy": "IGA3, IGA4, IGA6"},
            {"pi_id": "PI-4.3", "pi_code": "4.3", "full_text": "4.3. Demonstrate a social awareness and civic responsibility in the practice of the Geology profession.", "description": "Demonstrate a social awareness and civic responsibility in the practice of the Geology profession.", "igas": "IGA3, IGA4, IGA5", "igas_legacy": "IGA3, IGA4, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO5",
        "pgo_id": "PGO-5",
        "letter": "5",
        "description": "PGO5) Appreciate the 'Filipino historical and cultural heritage'",
        "short_label": "PGO5 – Appreciate Filipino historical and cultural heritage",
        "igas": "IGA3, IGA4",
        "igas_legacy": "IGA3, IGA6",
        "pis": [
            {"pi_id": "PI-5.1", "pi_code": "5.1", "full_text": "5.1. Shows appreciation for the rich historical and cultural records of the country.", "description": "Shows appreciation for the rich historical and cultural records of the country.", "igas": "IGA3, IGA4", "igas_legacy": "IGA3, IGA6"},
            {"pi_id": "PI-5.2", "pi_code": "5.2", "full_text": "5.2. Displays the values, culture and work ethics of a uniquely Filipino Geologist.", "description": "Displays the values, culture and work ethics of a uniquely Filipino Geologist.", "igas": "IGA3, IGA4", "igas_legacy": "IGA3, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO6",
        "pgo_id": "PGO-6",
        "letter": "6",
        "description": "PGO6) Demonstrate broad and coherent knowledge and understanding in the core areas of earth science",
        "short_label": "PGO6 – Broad & coherent knowledge in core areas of earth science",
        "igas": "IGA2, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA6",
        "pis": [
            {"pi_id": "PI-6.1", "pi_code": "6.1", "full_text": "6.1. Capable of applying earth science principles in solving real world problems.", "description": "Capable of applying earth science principles in solving real world problems.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
            {"pi_id": "PI-6.2", "pi_code": "6.2", "full_text": "6.2. Recognizes the different field conditions and actual applications of concepts learned from the classroom.", "description": "Recognizes the different field conditions and actual applications of concepts learned from the classroom.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
            {"pi_id": "PI-6.3", "pi_code": "6.3", "full_text": "6.3. Formulate practical and applicable solutions to geological problems.", "description": "Formulate practical and applicable solutions to geological problems.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO7",
        "pgo_id": "PGO-7",
        "letter": "7",
        "description": "PGO7) Apply analytical, critical and problem-solving skills using the Scientific Method",
        "short_label": "PGO7 – Analytical, critical & problem-solving skills (Scientific Method)",
        "igas": "IGA2, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA6",
        "pis": [
            {"pi_id": "PI-7.1", "pi_code": "7.1", "full_text": "7.1. Uses a scientific and systematic approach in analysis and finding solutions to geologic issues.", "description": "Uses a scientific and systematic approach in analysis and finding solutions to geologic issues.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
            {"pi_id": "PI-7.2", "pi_code": "7.2", "full_text": "7.2. Employ geological techniques in obtaining answers to practical and environmental problems.", "description": "Employ geological techniques in obtaining answers to practical and environmental problems.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
            {"pi_id": "PI-7.3", "pi_code": "7.3", "full_text": "7.3. Evaluate and predict responses of natural systems based on geologic principles.", "description": "Evaluate and predict responses of natural systems based on geologic principles.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO8",
        "pgo_id": "PGO-8",
        "letter": "8",
        "description": "PGO8) Interpret relevant scientific data and make judgments that include reflection on relevant scientific and ethical issues",
        "short_label": "PGO8 – Interpret scientific data & make ethical judgments",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA4",
        "pis": [
            {"pi_id": "PI-8.1", "pi_code": "8.1", "full_text": "8.1. Utilize scientific data to solve current issues in environmental, social, economic and politics.", "description": "Utilize scientific data to solve current issues in environmental, social, economic and politics.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
            {"pi_id": "PI-8.2", "pi_code": "8.2", "full_text": "8.2. Incorporates social justice and common good in ascertaining resolutions that are pinned on scientific data and facts.", "description": "Incorporates social justice and common good in ascertaining resolutions that are pinned on scientific data and facts.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
        ],
    },
    {
        "pgo_code": "PGO9",
        "pgo_id": "PGO-9",
        "letter": "9",
        "description": "PGO9) Carry out basic mathematical and statistical computations and use appropriate technologies in data analysis, pattern recognition, and problem solving",
        "short_label": "PGO9 – Mathematical/statistical computations & technologies in data analysis",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA4",
        "pis": [
            {"pi_id": "PI-9.1", "pi_code": "9.1", "full_text": "9.1. Use appropriate mathematical techniques in any given situation.", "description": "Use appropriate mathematical techniques in any given situation.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
            {"pi_id": "PI-9.2", "pi_code": "9.2", "full_text": "9.2. Outline logical and chronological steps in the analysis of problems.", "description": "Outline logical and chronological steps in the analysis of problems.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
            {"pi_id": "PI-9.3", "pi_code": "9.3", "full_text": "9.3. Manipulate various scientific environmental data in order to produce useful information.", "description": "Manipulate various scientific environmental data in order to produce useful information.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
        ],
    },
    {
        "pgo_code": "PGO10",
        "pgo_id": "PGO-10",
        "letter": "10",
        "description": "PGO10) Communicate information, ideas, problems and solutions both orally and in writing to other scientists, decision makers and the public",
        "short_label": "PGO10 – Communicate ideas, problems & solutions to scientists & public",
        "igas": "IGA4, IGA5",
        "igas_legacy": "IGA5, IGA6",
        "pis": [
            {"pi_id": "PI-10.1", "pi_code": "10.1", "full_text": "10.1. Participate in multi-partite scientific discussions and contributes sound suggestions for solutions.", "description": "Participate in multi-partite scientific discussions and contributes sound suggestions for solutions.", "igas": "IGA4, IGA5", "igas_legacy": "IGA5, IGA6"},
            {"pi_id": "PI-10.2", "pi_code": "10.2", "full_text": "10.2. Collaborate with different government agencies and other stakeholders in formulating sound and equitable policies and regulations on earth and environmental issues.", "description": "Collaborate with different government agencies and other stakeholders in formulating sound and equitable policies and regulations on earth and environmental issues.", "igas": "IGA4, IGA5", "igas_legacy": "IGA5, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO11",
        "pgo_id": "PGO-11",
        "letter": "11",
        "description": "PGO11) Connect science and math to the other disciplines",
        "short_label": "PGO11 – Connect science and math to other disciplines",
        "igas": "IGA2, IGA4",
        "igas_legacy": "IGA1, IGA6",
        "pis": [
            {"pi_id": "PI-11.1", "pi_code": "11.1", "full_text": "11.1. Apply mathematical and scientific knowledge in solving multi-disciplinary problems.", "description": "Apply mathematical and scientific knowledge in solving multi-disciplinary problems.", "igas": "IGA2, IGA4", "igas_legacy": "IGA1, IGA6"},
            {"pi_id": "PI-11.2", "pi_code": "11.2", "full_text": "11.2. Participate in multi-disciplinary researches in solving problems using various fields of expertise.", "description": "Participate in multi-disciplinary researches in solving problems using various fields of expertise.", "igas": "IGA2, IGA4", "igas_legacy": "IGA1, IGA6"},
            {"pi_id": "PI-11.3", "pi_code": "11.3", "full_text": "11.3. Combine various scientific and mathematical methodologies to come up with novel solutions to different scientific inquiries.", "description": "Combine various scientific and mathematical methodologies to come up with novel solutions to different scientific inquiries.", "igas": "IGA2, IGA4", "igas_legacy": "IGA1, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO12",
        "pgo_id": "PGO-12",
        "letter": "12",
        "description": "PGO12) Design and perform techniques and procedures following safe and responsible laboratory or field practices",
        "short_label": "PGO12 – Safe and responsible laboratory or field practices",
        "igas": "IGA1, IGA2, IGA5",
        "igas_legacy": "IGA1, IGA2, IGA4",
        "pis": [
            {"pi_id": "PI-12.1", "pi_code": "12.1", "full_text": "12.1. Perform laboratory experiments as prescribed by standard procedures.", "description": "Perform laboratory experiments as prescribed by standard procedures.", "igas": "IGA1, IGA2, IGA5", "igas_legacy": "IGA1, IGA2, IGA4"},
            {"pi_id": "PI-12.2", "pi_code": "12.2", "full_text": "12.2. Design an experiment to achieve a specific objective.", "description": "Design an experiment to achieve a specific objective.", "igas": "IGA1, IGA2, IGA5", "igas_legacy": "IGA1, IGA2, IGA4"},
        ],
    },
    {
        "pgo_code": "PGO13",
        "pgo_id": "PGO-13",
        "letter": "13",
        "description": "PGO13) Accept and critically evaluate input from others",
        "short_label": "PGO13 – Accept and critically evaluate input from others",
        "igas": "IGA1, IGA2, IGA5",
        "igas_legacy": "IGA1, IGA2, IGA4",
        "pis": [
            {"pi_id": "PI-13.1", "pi_code": "13.1", "full_text": "13.1. Capable of learning from colleagues and other professionals.", "description": "Capable of learning from colleagues and other professionals.", "igas": "IGA1, IGA2, IGA5", "igas_legacy": "IGA1, IGA2, IGA4"},
            {"pi_id": "PI-13.2", "pi_code": "13.2", "full_text": "13.2. Form working partnerships and cooperation with professionals in the same field and others.", "description": "Form working partnerships and cooperation with professionals in the same field and others.", "igas": "IGA1, IGA2, IGA5", "igas_legacy": "IGA1, IGA2, IGA4"},
            {"pi_id": "PI-13.3", "pi_code": "13.3", "full_text": "13.3. Able to integrate and adapt into different teams of professionals and work constructively.", "description": "Able to integrate and adapt into different teams of professionals and work constructively.", "igas": "IGA1, IGA2, IGA5", "igas_legacy": "IGA1, IGA2, IGA4"},
        ],
    },
    {
        "pgo_code": "PGO14",
        "pgo_id": "PGO-14",
        "letter": "14",
        "description": "PGO14) Appreciate the limitations and implications of science in everyday life",
        "short_label": "PGO14 – Appreciate limitations & implications of science in everyday life",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA4",
        "pis": [
            {"pi_id": "PI-14.1", "pi_code": "14.1", "full_text": "14.1. Implement practical geotechnical and geologic solutions to real-world problems.", "description": "Implement practical geotechnical and geologic solutions to real-world problems.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
            {"pi_id": "PI-14.2", "pi_code": "14.2", "full_text": "14.2. Determine practical and realistic courses of action in the application of geologic principles.", "description": "Determine practical and realistic courses of action in the application of geologic principles.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
            {"pi_id": "PI-14.3", "pi_code": "14.3", "full_text": "14.3. Appreciate the relevance of scientific classroom concepts to actual conditions.", "description": "Appreciate the relevance of scientific classroom concepts to actual conditions.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
        ],
    },
    {
        "pgo_code": "PGO15",
        "pgo_id": "PGO-15",
        "letter": "15",
        "description": "PGO15) Commitment for the integrity of data",
        "short_label": "PGO15 – Commitment for the integrity of data",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA5",
        "pis": [
            {"pi_id": "PI-15.1", "pi_code": "15.1", "full_text": "15.1. Relate the professional code of ethics into actual practice.", "description": "Relate the professional code of ethics into actual practice.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA5"},
            {"pi_id": "PI-15.2", "pi_code": "15.2", "full_text": "15.2. Displays realistic expectations on data analysis and results.", "description": "Displays realistic expectations on data analysis and results.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA5"},
            {"pi_id": "PI-15.3", "pi_code": "15.3", "full_text": "15.3. Adheres to professional integrity of the scientific process at all times.", "description": "Adheres to professional integrity of the scientific process at all times.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA5"},
        ],
    },
    {
        "pgo_code": "PGO16",
        "pgo_id": "PGO-16",
        "letter": "16",
        "description": "PGO16) Observe and record important geological features as well as the small, subtle and seemingly unimportant details",
        "short_label": "PGO16 – Observe & record geological features and details",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA5",
        "pis": [
            {"pi_id": "PI-16.1", "pi_code": "16.1", "full_text": "16.1. Conduct detailed geological investigations with thoroughness and competence.", "description": "Conduct detailed geological investigations with thoroughness and competence.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA5"},
            {"pi_id": "PI-16.2", "pi_code": "16.2", "full_text": "16.2. Determines the precise geological conditions and provide accurate and relevant recommendations.", "description": "Determines the precise geological conditions and provide accurate and relevant recommendations.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA5"},
        ],
    },
    {
        "pgo_code": "PGO17",
        "pgo_id": "PGO-17",
        "letter": "17",
        "description": "PGO17) Analyze and interpret observations and provide solutions to applied geologic problems",
        "short_label": "PGO17 – Analyze observations & solve applied geologic problems",
        "igas": "IGA2, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA6",
        "pis": [
            {"pi_id": "PI-17.1", "pi_code": "17.1", "full_text": "17.1. Apply geologic principles in analyzing societal problems and formulation solutions.", "description": "Apply geologic principles in analyzing societal problems and formulation solutions.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
            {"pi_id": "PI-17.2", "pi_code": "17.2", "full_text": "17.2. Develop workflows and procedures based on geologic principles for real world applications.", "description": "Develop workflows and procedures based on geologic principles for real world applications.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
            {"pi_id": "PI-17.3", "pi_code": "17.3", "full_text": "17.3. Create and innovate functions based on the science of Geology to address technical considerations in urban settlements and other applications.", "description": "Create and innovate functions based on the science of Geology to address technical considerations in urban settlements and other applications.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO18",
        "pgo_id": "PGO-18",
        "letter": "18",
        "description": "PGO18) Incorporate geologic principles in the evaluation, analysis and interpretation of data",
        "short_label": "PGO18 – Incorporate geologic principles in data evaluation & interpretation",
        "igas": "IGA2, IGA4, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA6",
        "pis": [
            {"pi_id": "PI-18.1", "pi_code": "18.1", "full_text": "18.1. Analyze, interpret and gather useful information from different sources geological information.", "description": "Analyze, interpret and gather useful information from different sources geological information.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
            {"pi_id": "PI-18.2", "pi_code": "18.2", "full_text": "18.2. Provide unbiased sound constructive criticisms on different geological analysis and reports.", "description": "Provide unbiased sound constructive criticisms on different geological analysis and reports.", "igas": "IGA2, IGA4, IGA5", "igas_legacy": "IGA1, IGA4, IGA6"},
        ],
    },
    {
        "pgo_code": "PGO19",
        "pgo_id": "PGO-19",
        "letter": "19",
        "description": "PGO19) Visualize and draw geologic structures/features in multi-dimensions",
        "short_label": "PGO19 – Visualize & draw geologic structures in multi-dimensions",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA4, IGA5",
        "pis": [
            {"pi_id": "PI-19.1", "pi_code": "19.1", "full_text": "19.1. Capable of multi-dimensional analysis of geologic data.", "description": "Capable of multi-dimensional analysis of geologic data.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4, IGA5"},
            {"pi_id": "PI-19.2", "pi_code": "19.2", "full_text": "19.2. Conduct temporal analysis of geological systems predicting future possible environmental issues.", "description": "Conduct temporal analysis of geological systems predicting future possible environmental issues.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4, IGA5"},
            {"pi_id": "PI-19.3", "pi_code": "19.3", "full_text": "19.3. Competently create models of geologic features across time and spatial scales.", "description": "Competently create models of geologic features across time and spatial scales.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4, IGA5"},
        ],
    },
    {
        "pgo_code": "PGO20",
        "pgo_id": "PGO-20",
        "letter": "20",
        "description": "PGO20) Write and communicate geological ideas to other scientists and the public",
        "short_label": "PGO20 – Write & communicate geological ideas to scientists & public",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA5",
        "pis": [
            {"pi_id": "PI-20.1", "pi_code": "20.1", "full_text": "20.1. Proficient in communication scientific results both in oral and written form.", "description": "Proficient in communication scientific results both in oral and written form.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA5"},
            {"pi_id": "PI-20.2", "pi_code": "20.2", "full_text": "20.2. Contributes the written scientific output for the development of Geology as a science in the Philippines.", "description": "Contributes the written scientific output for the development of Geology as a science in the Philippines.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA5"},
        ],
    },
    {
        "pgo_code": "PGO21",
        "pgo_id": "PGO-21",
        "letter": "21",
        "description": "PGO21) Adhere to the Code of Ethics of Geologists",
        "short_label": "PGO21 – Adhere to the Code of Ethics of Geologists",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA4",
        "pis": [
            {"pi_id": "PI-21.1", "pi_code": "21.1", "full_text": "21.1. Practices the profession in line with the Code of Ethics of Geologists.", "description": "Practices the profession in line with the Code of Ethics of Geologists.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
            {"pi_id": "PI-21.2", "pi_code": "21.2", "full_text": "21.2. Performs the technical duties of a Geologist in view of the common good and justice.", "description": "Performs the technical duties of a Geologist in view of the common good and justice.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
        ],
    },
    {
        "pgo_code": "PGO22",
        "pgo_id": "PGO-22",
        "letter": "22",
        "description": "PGO22) Design and manage geology related projects",
        "short_label": "PGO22 – Design and manage geology related projects",
        "igas": "IGA2, IGA5",
        "igas_legacy": "IGA1, IGA4",
        "pis": [
            {"pi_id": "PI-22.1", "pi_code": "22.1", "full_text": "22.1. Able to design and implement different geological campaigns with efficiency and competence.", "description": "Able to design and implement different geological campaigns with efficiency and competence.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
            {"pi_id": "PI-22.2", "pi_code": "22.2", "full_text": "22.2. Organize various geological investigations in different terrain and situations.", "description": "Organize various geological investigations in different terrain and situations.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
            {"pi_id": "PI-22.3", "pi_code": "22.3", "full_text": "22.3. Supervise multi-participatory teams in the conduct of environmental assessments.", "description": "Supervise multi-participatory teams in the conduct of environmental assessments.", "igas": "IGA2, IGA5", "igas_legacy": "IGA1, IGA4"},
        ],
    },
]


# ==============================================================================
# 5. PROGRAM STRUCTURES REGISTRY BY PROGRAM CODE / DEPARTMENT
# ==============================================================================
def _build_bsse_pgos() -> List[Dict[str, Any]]:
    pgos = _build_standard_eng_pgos("")
    for p in pgos:
        if p["letter"] == "k":
            p["pis"][2]["full_text"] = "k.3. Use techniques, skills, and modern engineering tools necessary for engineering practice."
            p["pis"][2]["description"] = "Use techniques, skills, and modern engineering tools necessary for engineering practice."
    return pgos


PROGRAM_STRUCTURES_BY_CODE: Dict[str, Dict[str, Any]] = {
    "EE": {
        "program_code": "EE",
        "program_name": "Bachelor of Science in Electrical Engineering",
        "department": "Department of Electrical Engineering",
        "source_file": "BSEE-Program-Structure_REVISED-1_new_IGAv1.pdf",
        "cmo_reference": "CMO No. 88, s. 2017",
        "peos": [
            {"code": "PEO1", "description": "Demonstrate expertise in the field of Electrical Engineering."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Exhibit globally-competitive skills."},
        ],
        "pgo_pi_catalog": _build_standard_eng_pgos("electrical engineering"),
    },
    "CE": {
        "program_code": "CE",
        "program_name": "Bachelor of Science in Civil Engineering",
        "department": "Department of Civil Engineering",
        "source_file": "PROGRAM_STRUCTURE-_STRUCTURAL.pdf",
        "cmo_reference": "CMO No. 92, s. 2017",
        "peos": [
            {"code": "PEO1", "description": "Demonstrate expertise in the field of Civil Engineering."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate gender-sensitive leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Exhibit globally competitive skills."},
        ],
        "pgo_pi_catalog": _build_standard_eng_pgos("civil engineering"),
    },
    "ECE": {
        "program_code": "ECE",
        "program_name": "Bachelor of Science in Electronics Engineering",
        "department": "Department of Electronics Engineering",
        "source_file": "Prog Structure_BSECE_revised_july2019.pdf",
        "cmo_reference": "CMO No. 101, s. 2017",
        "peos": [
            {"code": "PEO1", "description": "Demonstrate expertise in the field of Electronics Engineering."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate gender sensitive leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Exhibit globally competitive skills."},
        ],
        "pgo_pi_catalog": _build_standard_eng_pgos(""),
    },
    "ME": {
        "program_code": "ME",
        "program_name": "Bachelor of Science in Mechanical Engineering",
        "department": "Department of Mechanical Engineering",
        "source_file": "BSME_Approved-Program-Structure.pdf",
        "cmo_reference": "CMO No. 97, s. 2017",
        "peos": [
            {"code": "PEO1", "description": "Demonstrate expertise in the field of Mechanical Engineering."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate gender sensitive leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Exhibit globally competitive skills."},
        ],
        "pgo_pi_catalog": _build_standard_eng_pgos(""),
    },
    "SE": {
        "program_code": "SE",
        "program_name": "Bachelor of Science in Sanitary Engineering",
        "department": "Department of Sanitary Engineering",
        "source_file": "BSSE Approved Program Structure (1).pdf",
        "cmo_reference": "CMO No. 98, s. 2017",
        "peos": [
            {"code": "PEO1", "description": "Demonstrate expertise in the field of Sanitary Engineering."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate gender sensitive leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Exhibit globally competitive skills."},
        ],
        "pgo_pi_catalog": _build_bsse_pgos(),
    },
    "ABE": {
        "program_code": "ABE",
        "program_name": "Bachelor of Science in Agricultural and Biosystems Engineering",
        "department": "Department of Agricultural and Biosystems Engineering",
        "source_file": "9.-Program-Structure_SY2020-2021_revision1.pdf & 8. Program Structure_ABE.pdf",
        "cmo_reference": "CMO No. 94, s. 2017",
        "peos": [
            {"code": "PEO1", "description": "Practice Agricultural and Biosystems Engineering."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Pursue advance studies in ABE and emerging related fields."},
            {"code": "PEO5", "description": "Occupy responsible positions in ABE education."},
        ],
        "pgo_pi_catalog": BSABE_PGOS,
    },
    "GE": {
        "program_code": "GE",
        "program_name": "Bachelor of Science in Geodetic Engineering",
        "department": "Department of Geodetic Engineering",
        "source_file": "BSGE Approved Program Structure.pdf",
        "cmo_reference": "CMO No. 89, s. 2017",
        "peos": [
            {"code": "PEO1", "description": "Demonstrate expertise in the field of Geodetic Engineering."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate gender sensitive leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Exhibit globally competitive skills."},
        ],
        "pgo_pi_catalog": _build_standard_eng_pgos(""),
    },
    "MinE": {
        "program_code": "MinE",
        "program_name": "Bachelor of Science in Mining Engineering",
        "department": "Department of Mining Engineering",
        "source_file": "BSEM-Approved-Program-Structure (1).pdf",
        "cmo_reference": "CMO No. 100, s. 2017",
        "peos": [
            {"code": "PEO1", "description": "Establish expertise in the field of Mining Engineering."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Strive to be globally competitive."},
        ],
        "pgo_pi_catalog": _build_standard_eng_pgos("mining engineering"),
    },
    "BSGeo": {
        "program_code": "BSGeo",
        "program_name": "Bachelor of Science in Geology",
        "department": "Department of Geology",
        "source_file": "Program-Structure-with-CMO_Geology.docx",
        "cmo_reference": "CMO No. 44, s. 2017 / CMO No. 35, s. 2008",
        "peos": [
            {"code": "PEO1", "description": "Demonstrate expertise in the field of Geology."},
            {"code": "PEO2", "description": "Actively participate in professional communities to nourish ever-developing careers."},
            {"code": "PEO3", "description": "Demonstrate leadership and commitment to work in diverse cultural and interdisciplinary backgrounds."},
            {"code": "PEO4", "description": "Exhibit globally competitive skills."},
        ],
        "pgo_pi_catalog": BSGEO_PGOS,
    },
}


def get_program_structure(program_code_or_dept: str) -> Dict[str, Any]:
    """Returns the program structure (PEOs, PGOs, PIs, IGAs) for a given program code or department."""
    key = (program_code_or_dept or "EE").strip()
    if key in PROGRAM_STRUCTURES_BY_CODE:
        return PROGRAM_STRUCTURES_BY_CODE[key]

    low = key.lower()
    if "agricultur" in low or "biosystem" in low or low == "abe" or low == "bsabe":
        return PROGRAM_STRUCTURES_BY_CODE["ABE"]
    if "geolog" in low or low == "bsgeo" or low == "geo":
        return PROGRAM_STRUCTURES_BY_CODE["BSGeo"]
    if "civil" in low or "structural" in low or low == "ce" or low == "bsce":
        return PROGRAM_STRUCTURES_BY_CODE["CE"]
    if "electronic" in low or low == "ece" or low == "bsece":
        return PROGRAM_STRUCTURES_BY_CODE["ECE"]
    if "mechanic" in low or low == "me" or low == "bsme":
        return PROGRAM_STRUCTURES_BY_CODE["ME"]
    if "sanitar" in low or low == "se" or low == "bsse":
        return PROGRAM_STRUCTURES_BY_CODE["SE"]
    if "geodetic" in low or low == "bsge":
        return PROGRAM_STRUCTURES_BY_CODE["GE"]
    if "mining" in low or low == "mine" or low == "bsem":
        return PROGRAM_STRUCTURES_BY_CODE["MinE"]
    return PROGRAM_STRUCTURES_BY_CODE["EE"]
