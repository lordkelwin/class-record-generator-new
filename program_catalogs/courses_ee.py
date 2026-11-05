# program_catalogs/courses_ee.py
"""
Complete official course catalog for the Bachelor of Science in Electrical Engineering (BSEE).
Synchronized directly from the official database 'prospectus/PGO-PI-IGA.accdb' and CMO 88 s. 2017.
Contains full course descriptions and comprehensive PGO-PI-IGA (IED) alignment mappings.
Total Courses: 81 official curriculum courses.
"""

from typing import List, Dict, Any

BSEE_COURSES: List[Dict[str, Any]] = [
    {
        "code": "GE 111",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "Purposive Communication",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-g-g.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 4: Quality Education",
        "description": "Writing, speaking, and presenting to different audiences and for various purposes.",
        "topics": [
            "Communication Principles and Ethics in Globalized Engineering",
            "Technical Communication and Engineering Documentation",
            "Public Speaking and Technical Briefings",
            "Cross-Cultural Communication in Diverse Engineering Teams"
        ]
    },
    {
        "code": "GE 112",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "Mathematics in the Modern World",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 4: Quality Education",
        "description": "Nature of mathematics, appreciation of its practical, intellectual, and aesthetic dimensions, and application of mathematical tools in daily life.",
        "topics": [
            "Patterns and Numbers in Nature and Signals",
            "Mathematical Language, Logic, and Problem Formulation",
            "Descriptive Statistics and Data Management",
            "Linear Programming and Resource Optimization"
        ]
    },
    {
        "code": "GE 215",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "The Life and Works of Rizal",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 4 (Quality Education), SDG 16 (Peace, Justice and Strong Institutions)",
        "description": "The life, works, and writings of Dr. Jose Rizal, particularly his novels Noli Me Tangere and El Filibusterismo, and their role in the development of Filipino national consciousness.",
        "topics": [
            "Rizal in the 19th-Century Colonial Context and Socio-Political Landscape",
            "Noli Me Tangere and Socio-Political Critiques",
            "El Filibusterismo and Revolutionary Ideals",
            "Rizalian Scientific Outlook, Nation Building, and Professional Engineering Integrity"
        ]
    },
    {
        "code": "GE 216",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "Readings in Philippine History",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-h-h.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 16: Peace, Justice and Strong Institutions",
        "description": "Philippine history viewed from the lens of selected primary sources in different periods, analysis and interpretations.",
        "topics": [
            "Primary vs. Secondary Historical Sources",
            "Electrification and Public Infrastructure History in the Philippines",
            "Evolution of the Philippine Constitution",
            "Historical Context of Regional Development in Mindanao"
        ]
    },
    {
        "code": "Math 111",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "Engineering Calculus 1",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [I], PGO-e-e.1 [I], PGO-e-e.2 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.1",
                "pi_description": "Interpret statement problems into mathematical expressions.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 4: Quality Education",
        "description": "Basic concepts of calculus such as limits, continuity and differentiability of functions; differentiation of algebraic and transcendental functions involving one or more variables; applications of differential calculus to problems on optimization, rates of change, related rates, tangents and normals, and approximations; partial differentiation and transcendental curve tracing.",
        "topics": [
            "Limits and Continuity of Functions",
            "Differentiation Rules for Algebraic, Trigonometric, and Exponential Functions",
            "Related Rates and Rate of Change in Electrical Circuits",
            "Optimization and Maximum Power Transfer Curve Analysis"
        ]
    },
    {
        "code": "Nat Sci 1",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "Chemistry for Engineers",
        "credit_units": "4.0 Units (3 Lec, 1 Lab)",
        "lecture_units": 3,
        "lab_units": 1,
        "lec_lab": "Lecture/Lab",
        "hours": "6 Hours/Week (3 hours Lecture, 3 hours Lab)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.2 [I], PGO-b-b.1 [I], PGO-e-e.2 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.2",
                "pi_description": "Apply principles in chemical sciences to solve engineering problems",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 7: Affordable and Clean Energy, SDG 12: Responsible Consumption and Production",
        "description": "Basic concepts of matter and its classification; mass relationships in chemical reactions; properties of gases, liquids, and solids; concepts of thermochemistry; quantum theory and electronic behavior; periodic relationship of elements in the periodic table; intramolecular forces; and solutions.",
        "topics": [
            "Atomic Structure, Periodic Trends, and Semiconductor Solid State",
            "Chemical Equilibrium and Solution Chemistry",
            "Electrochemistry: Galvanic Cells, Battery Storage, and Corrosion",
            "Thermodynamics and Reaction Kinetics in Power Systems",
            "Laboratory Volumetric Analysis and Electrochemical Testing"
        ]
    },
    {
        "code": "BES 101",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "Engineering Drawing and Plans",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-d-d.1 [I], PGO-g-g.3 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 9: Industry, Innovation, and Infrastructure",
        "description": "This laboratory course is design to develop abilities needed to develop, accurately locate, and interpret dimensions on and read engineering designs.",
        "topics": [
            "Drafting Instruments, Lettering, and Line Conventions",
            "Orthographic Multi-View Projections and Auxiliary Views",
            "Isometric Drawings and Electrical Panel Assembly Views",
            "Reading Architectural Blueprints and Electrical Single-Line Diagrams"
        ]
    },
    {
        "code": "PE 111",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "Movement Enhancement",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-d-d.1 [I]; PGO-f-f.1 [I]; PGO-i-i.1 [I]; PGO-j-j.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 3",
        "description": "Physical fitness, biomechanics, movement fundamentals, and health-related fitness components for personal wellness and career longevity.",
        "topics": [
            "Physical Fitness Concepts and Health Assessments",
            "Fundamental Movement Patterns and Core Stability",
            "Aerobic Conditioning and Personalized Exercise Regimens"
        ]
    },
    {
        "code": "NSTP 111",
        "year_level": "First Year",
        "semester": "1st Semester",
        "title": "National Service Training Program 1",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-d-d.1 [I]; PGO-f-f.1 [I]; PGO-i-i.1 [I]; PGO-j-j.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 11, SDG 16",
        "description": "Civic consciousness, disaster preparedness, community development, and leadership in national defense and social welfare services.",
        "topics": [
            "National Security Concerns and Citizen Responsibilities",
            "Disaster Risk Reduction and Management (DRRM)",
            "Community Needs Assessment and Civic Engagement"
        ]
    },
    {
        "code": "GE 113",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "Understanding the Self",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 16: Peace, Justice and Strong Institutions",
        "description": "Nature of identity; factors and forces that affect the development and maintenance of personal identity.",
        "topics": [
            "Rizal in the 19th-Century Colonial Context",
            "Noli Me Tangere and Socio-Political Critiques",
            "El Filibusterismo and Revolutionary Ideals",
            "Rizalian Scientific Outlook and Professional Integrity"
        ]
    },
    {
        "code": "GE 114",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "Ethics",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-h-h.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 16: Peace, Justice and Strong Institutions",
        "description": "Principles of ethical behavior in modern society at the level of the person, society, and in interaction with the environment and other shared resources.",
        "topics": [
            "Primary vs. Secondary Historical Sources",
            "Electrification and Public Infrastructure History in the Philippines",
            "Evolution of the Philippine Constitution",
            "Historical Context of Regional Development in Mindanao"
        ]
    },
    {
        "code": "Math 121",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "Engineering Calculus 2",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Math 111",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 4: Quality Education",
        "description": "Concept of integration and its application to physical problems such as evaluation of areas, volumes of revolution, force, and work; fundamental formulas and various techniques of integration applied to both single variable and multi-variable functions; tracing of functions of two variables.",
        "topics": [
            "Definite Integrals and Fundamental Theorem of Calculus",
            "Integration Techniques: Substitution, Parts, Partial Fractions",
            "Root-Mean-Square (RMS) and Average Value Calculation of Signals",
            "Improper Integrals and Energy Storage in Capacitors and Inductors"
        ]
    },
    {
        "code": "Math 212",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "Engineering Data Analysis",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Math 111",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [I], PGO-e-e.2 [I], PGO-h-h.1 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            }
        ],
        "sdgs": "SDG 9",
        "description": "This course introduces different methods of data collection and the suitability of using a particular method for a given situation. It includes a coverage and discussion of the relationship of probability to statistics, probability distributions of random variables and their uses, linear functions of random variables within the context of their application to data analysis and inference, estimation techniques for unknown parameters, and hypothesis testing used in making inferences from sample to population, inference for regression parameters and build models for estimating means and predicting future values of key variables under study. Statistically based experimental design techniques and analysis of outcomes of experiments are discussed with the aid of statistical software.",
        "topics": [
            "Descriptive Statistics and Probability Distributions (Normal, Binomial, Poisson)",
            "Sampling Distributions, Confidence Intervals, and Hypothesis Testing",
            "Linear Regression, Correlation Analysis, and Statistical Quality Control in Construction"
        ]
    },
    {
        "code": "Nat Sci 2",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "Physics for Engineers",
        "credit_units": "4.0 Units (3 Lec, 1 Lab)",
        "lecture_units": 3,
        "lab_units": 1,
        "lec_lab": "Lecture/Lab",
        "hours": "6 Hours/Week (3 hours Lecture, 3 hours Lab)",
        "prereqs": "None",
        "coreqs": "Math 121",
        "pgo_pi": "PGO-a-a.3 [E], PGO-b-b.1 [I], PGO-d-d.2 [I], PGO-e-e.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.3",
                "pi_description": "Apply principles in physical sciences to solve engineering problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.2",
                "pi_description": "Capable of learning from and listening to co-members.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA3"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7: Affordable and Clean Energy, SDG 9: Industry, Innovation, and Infrastructure",
        "description": "Vectors; kinematics; dynamics; work, energy, and power; impulse and momentum; rotation; dynamics of rotation; elasticity; and oscillation.",
        "topics": [
            "Kinematics, Dynamics, and Gravitational Field Models",
            "Work, Energy, Power, and Conservation of Energy",
            "Electric Charges, Coulomb's Law, Electric Fields, and Gauss's Law",
            "Magnetic Fields, Biot-Savart Law, and Electromagnetic Induction",
            "Laboratory Verification of Physical Mechanics and Electrical Laws"
        ]
    },
    {
        "code": "BES 102",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "Computer Aided Drafting",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "BES 101",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.1 [I], PGO-g-g.3 [I], PGO-i-i.1 [I], PGO-k-k.1 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.1",
                "pi_description": "Internalizes the professional code of ethics for specific discipline.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.1",
                "pi_description": "Demonstrate ability to learn independently.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.1",
                "pi_description": "Handles the details of the work assigned to him/her",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA2"
            }
        ],
        "sdgs": "SDG 9",
        "description": "Concepts of computer-aided drafting (CAD); introduction to the CAD environment; terminologies; and the general operating procedures and techniques in entering and executing basic CAD commands.",
        "topics": [
            "2D Drafting Fundamentals and Layer Management",
            "Electronic Schematics Capture and Symbol Libraries",
            "Printed Circuit Board (PCB) Footprint Creation and Board Routing"
        ]
    },
    {
        "code": "BES 103",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "Computer Fundamentals and Programming",
        "credit_units": "3.0 Units (1 Lec, 2 Lab)",
        "lecture_units": 1,
        "lab_units": 2,
        "lec_lab": "Lecture/Lab",
        "hours": "7 Hours/Week (1 hours Lecture, 6 hours Lab)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-b-b.1 [I], PGO-i-i.1 [I], PGO-k-k.2 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.1",
                "pi_description": "Demonstrate ability to learn independently.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.2",
                "pi_description": "Demonstrate the ability to operate the equipment needed in the engineering practice",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 4 (Quality Education), SDG 9 (Industry, Innovation, and Infrastructure)",
        "description": "Basic information technology concepts; fundamentals of algorithm development; high-level language and programming applications.",
        "topics": [
            "Computer Architecture Fundamentals, Number Systems, and Algorithm Flowcharting",
            "Structured Programming Principles and Development Environment (C / C++ / Python)",
            "Data Types, Variables, Expressions, and Conditional Statements",
            "Iteration, Looping Constructs, and Control Flow",
            "Modular Programming with User-Defined Functions and Scope",
            "Single and Multidimensional Arrays, String Manipulation, and Pointer Arithmetic",
            "File Input/Output, Engineering Data Structures, and Algorithmic Problem Solving"
        ]
    },
    {
        "code": "PE 122",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "Fitness Exercises",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "PE 111",
        "coreqs": "None",
        "pgo_pi": "PGO-d-d.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 3: Good Health and Well-being",
        "description": "Cardiorespiratory conditioning, resistance exercises, agility, and muscular endurance for lifelong health.",
        "topics": [
            "Aerobic Conditioning and Cardiovascular Health",
            "Resistance Training and Core Strengthening Workouts",
            "Flexibility and Muscular Fatigue Prevention",
            "Personal Physical Fitness Management"
        ]
    },
    {
        "code": "NSTP 122",
        "year_level": "First Year",
        "semester": "2nd Semester",
        "title": "National Service Training Program 2",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "NSTP 111",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.2 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 11: Sustainable Cities and Communities",
        "description": "Community outreach implementation: residential electrical safety checks, disaster assistance, and civic welfare projects.",
        "topics": [
            "Community Needs Assessment and Engagement",
            "Conducting Residential Electrical Safety Audits in Barangays",
            "Monitoring and Evaluating Community Outreach Programs",
            "Final Outreach Reporting and Community Presentation"
        ]
    },
    {
        "code": "BES 106",
        "year_level": "First Year",
        "semester": "Off-Semester",
        "title": "Engineering Economics",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Math 212",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [E], PGO-f-f.2 [I], PGO-h-h.1 [I], PGO-j-j.2 [I], PGO-l-l.3 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.2",
                "pi_description": "Explain the possible impact of technology to local, national, and international issues.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.3",
                "pi_description": "Participates in discussions and comes up with sound suggestions to problems",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 8: Decent Work and Economic Growth, SDG 12: Responsible Consumption and Production",
        "description": "Concepts of the time value of money and equivalence; basic economy study methods; decisions under certainty; decisions recognizing risk; and decisions admitting uncertainty.",
        "topics": [
            "Time Value of Money and Compound Interest Formulations",
            "Present Worth, Annual Worth, and Future Worth Methodologies",
            "Internal Rate of Return (IRR) and Benefit-Cost (B/C) Ratios",
            "Depreciation, Capital Recovery, and Power Asset Replacement Analysis"
        ]
    },
    {
        "code": "BES 112",
        "year_level": "First Year",
        "semester": "Off-Semester",
        "title": "Environmental Science and Engineering",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Nat Sci 1",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.2 [E], PGO-h-h.1 [E], PGO-j-j.1 [E], PGO-l-l.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.1",
                "pi_description": "Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.3",
                "pi_description": "Participates in discussions and comes up with sound suggestions to problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 7: Affordable and Clean Energy, SDG 13: Climate Action",
        "description": "Ecological framework of sustainable development; pollution environments: water, air, and solid; waste treatment processes, disposal, and management; government legislation, rules, and regulation related to the environment and waste management; and environmental management system.",
        "topics": [
            "Ecosystem Dynamics and Ecological Cycles",
            "Environmental Footprint of Thermal and Hydroelectric Power Plants",
            "Renewable Energy Transition and Carbon Footprint Reduction",
            "Philippine Environmental Impact Statement System (PD 1586)"
        ]
    },
    {
        "code": "Math 211",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Differential Equations",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Math 121",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.1",
                "pi_description": "Interpret statement problems into mathematical expressions.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            }
        ],
        "sdgs": "SDG 4: Quality Education",
        "description": "Differentiation and integration in solving first order, first-degree differential and linear differential equations of order n; Laplace transforms in solving differential equations.",
        "topics": [
            "First-Order Differential Equations and Separation of Variables",
            "First-Order Transient Response of RL and RC Circuits",
            "Second-Order Linear ODEs: Overdamped, Critically Damped, Underdamped RLC Circuits",
            "Laplace Transforms and Transfer Function Formulation"
        ]
    },
    {
        "code": "EE 211",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Electrical Circuits 1",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Nat Sci 2, Math 121",
        "coreqs": "EE 211L",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.2 [E], PGO-a-a.3 [E], PGO-e-e.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.3",
                "pi_description": "Apply principles in physical sciences to solve engineering problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7 (Affordable and Clean Energy), SDG 9 (Industry, Innovation, and Infrastructure)",
        "description": "The course covers nodal and mesh analysis; application of network theorems in circuit analysis; analysis of circuits with controlled sources and ideal op-amps; fundamentals of capacitors and inductors; analysis of dc-driven RL, RC, and RLC circuits; sinusoidal steady-state analysis of general RLC circuits.",
        "topics": [
            "Course Orientation, USeP Vision, Mission, Goals, and OBE Framework",
            "Fundamental Electric Circuit Concepts: Charge, Current, Voltage, Power & Energy, Ohm's Law",
            "Kirchhoff's Current Law (KCL) & Kirchhoff's Voltage Law (KVL), Series/Parallel & Wye-Delta Transformations",
            "Nodal Analysis and Mesh Analysis (with Independent and Dependent Sources)",
            "Circuit Theorems: Linearity, Superposition, Source Transformation, Thevenin's, Norton's & Max Power Transfer",
            "Capacitors and Inductors; First-Order Circuits (Source-Free & Step Response of RC and RL Circuits)",
            "Second-Order Circuits (Series and Parallel RLC Transient Response)",
            "Sinusoids and Phasors; Sinusoidal Steady-State Analysis (Nodal, Mesh, and Network Theorems in AC)"
        ]
    },
    {
        "code": "EE 211L",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Electrical Circuits 1 Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 211",
        "pgo_pi": "PGO-b-b.1 [E], PGO-k-k.1 [E], PGO-b-b.1 [E], PGO-k-k.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.1",
                "pi_description": "Handles the details of the work assigned to him/her",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.1",
                "pi_description": "Handles the details of the work assigned to him/her",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            }
        ],
        "sdgs": "SDG 4, SDG 7, SDG 9",
        "description": "Laboratory component of Electrical Circuits 1. The course covers nodal and mesh analysis; application of network theorems in circuit analysis; analysis of circuits with controlled sources and ideal op-amps; fundamentals of capacitors and inductors; analysis of dc-driven RL, RC, and RLC circuits; sinusoidal steady-state analysis of general RLC circuits.",
        "topics": [
            "Laboratory Safety Rules and Familiarization with Measuring Instruments",
            "Series and Parallel Resistive Circuits & Ohm's Law Verification",
            "Kirchhoff's Voltage and Current Laws (KVL & KCL)",
            "Superposition and Thevenin's Theorem Verification",
            "RC and RL Transient Response & Oscilloscope Measurements",
            "Sinusoidal Steady-State AC Circuits and Phasor Measurements"
        ]
    },
    {
        "code": "BES 104",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Engineering Mechanics",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Nat Sci 2, Math 121",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.3 [E], PGO-e-e.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.3",
                "pi_description": "Apply principles in physical sciences to solve engineering problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 9: Industry, Innovation, and Infrastructure",
        "description": "Force, moment, and motion concepts. Newton's Laws of Motion. Analysis of particles and rigid bodies in static and dynamic equilibrium using vector mechanics and energy and momentum methods. Geometric properties of lines, areas, and volumes.",
        "topics": [
            "Force Systems, Resultants, and Free-Body Equilibrium",
            "Analysis of Transmission Line Towers, Trusses, and Supports",
            "Centroids, Centers of Gravity, and Moments of Inertia",
            "Kinematics and Dynamics of Rotating Electric Machine Rotors"
        ]
    },
    {
        "code": "BES 108",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Fluid Mechanics",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Nat Sci 2",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.3 [E], PGO-e-e.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.3",
                "pi_description": "Apply principles in physical sciences to solve engineering problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 7: Affordable and Clean Energy, SDG 6: Clean Water and Sanitation",
        "description": "The course deals with the nature and physical properties of fluids as well as the identification and measurement of fluid properties. It emphasizes the application of conservation laws on mass, energy and momentum to fluid systems either incompressible or compressible flow, inviscid or viscous flow as well as head loss calculation on pipes and fittings.",
        "topics": [
            "Fluid Properties, Hydrostatic Pressure, and Forces on Submerged Gates",
            "Continuity, Energy (Bernoulli), and Momentum Principles",
            "Frictional Head Loss in Penstocks and Water Hammer Phenomenon",
            "Operating Principles of Impulse (Pelton) and Reaction (Francis, Kaplan) Turbines"
        ]
    },
    {
        "code": "AEE 213",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Basic Thermodynamics",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "Nat Sci 2",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7: Affordable and Clean Energy",
        "description": "Thermodynamic properties of pure substances, ideal and real gases and the study and application of the laws of thermodynamics in the analysis of processes and cycles; introduction to vapor and gas cycles.",
        "topics": [
            "First Law of Thermodynamics for Open and Closed Systems",
            "Second Law of Thermodynamics, Entropy, and Thermal Efficiency",
            "Properties of Steam and Mollier Enthalpy-Entropy Diagrams",
            "Rankine Steam Cycle and Brayton Gas Turbine Power Generation Cycles"
        ]
    },
    {
        "code": "BES 113",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Basic Occupational Health and Safety",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.1 [E], PGO-h-h.1 [E], PGO-j-j.1 [E], PGO-l-l.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.1",
                "pi_description": "Internalizes the professional code of ethics for specific discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.1",
                "pi_description": "Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.3",
                "pi_description": "Participates in discussions and comes up with sound suggestions to problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 3: Good Health and Well-being, SDG 8: Decent Work and Economic Growth",
        "description": "The course tackles key Occupational, Health and Safety (OSH) concepts, principles and practices that are foundational knowledge requirements acceptable in almost all industries; determination of existing and potential safety and health hazards; identification of control measures; provisions of Philippine laws that refer to occupational safety and health.",
        "topics": [
            "Occupational Safety Standards and DOLE OSH Legislation",
            "Hazard Identification, Risk Assessment, and Hierarchy of Controls (HIRAC)",
            "Confined Space Entry and Toxic Gas Safety in Sewers and Digesters",
            "Chemical, Biological, and Ergonomic Hazards in Treatment Facilities",
            "Emergency Preparedness, Disaster Management, and Accident Investigation"
        ]
    },
    {
        "code": "GE 217",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Science and Technology and Society",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-h-h.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 9: Industry, Innovation, and Infrastructure, SDG 13: Climate Action",
        "description": "Interactions between science and technology and social, cultural, political, and economic contexts which shape and are shaped by them; application of science and technology towards human flourishing.",
        "topics": [
            "Historical Revolutions in Electricity, Telecommunications, and Computing",
            "Science and Technology Policies in the Philippine Energy Sector",
            "Digital Transformation, Artificial Intelligence, and Ethical Frontiers",
            "Smart Grids, Climate Change, and Societal Energy Transition"
        ]
    },
    {
        "code": "PE 213",
        "year_level": "Second Year",
        "semester": "1st Semester",
        "title": "Physical Activities Towards Health and Fitness I",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "PE 122",
        "coreqs": "None",
        "pgo_pi": "PGO-d-d.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 3: Good Health and Well-being",
        "description": "Individual and dual sports focusing on agility, precision, balance, and endurance.",
        "topics": [
            "Rules, Regulations, and Safety Standards in Individual Sports",
            "Fundamental Techniques and Execution Drills",
            "Tactical Skills and Strategy Execution",
            "Competitive Sportsmanship and Lifelong Physical Fitness"
        ]
    },
    {
        "code": "EGE 311",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "General Education Elective 1",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-g-g.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 4: Quality Education",
        "description": "Interdisciplinary exploration of human culture, Philippine indigenous communities, or environmental philosophy.",
        "topics": [
            "Interdisciplinary Perspectives on Philippine Society",
            "Indigenous Knowledge Systems and Traditional Technologies",
            "Cultural Ecology and Resource Conservation",
            "Contemporary Societal Discourse"
        ]
    },
    {
        "code": "GE 218",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Arts Appreciation",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-g-g.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 4: Quality Education",
        "description": "Nature, function, and appreciation of the arts in contemporary society.",
        "topics": [
            "Elements and Principles of Visual Art",
            "Historical Movements and World Art Traditions",
            "Indigenous and Contemporary Philippine Arts",
            "Aesthetic Integration in Lighting and Architectural Design"
        ]
    },
    {
        "code": "EE 221",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Electrical Circuits 2",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 211, EE 211L",
        "coreqs": "EE 221L",
        "pgo_pi": "PGO-a-a.3 [E]; PGO-e-e.2 [E]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 7, SDG 9, SDG 12",
        "description": "The course deals with sinusoidal steady-state analysis in the frequency domain; AC circuit power analysis; analysis of polyphase circuits and magnetically-coupled circuits; frequency response; per unit system and symmetrical components; and two-port networks.",
        "topics": [
            "AC Steady-State Power Analysis: Instantaneous, Average, Complex Power, and Power Factor Correction",
            "Balanced Three-Phase Circuits (Y-Y, Y-Delta, Delta-Delta, Delta-Y Connections)",
            "Unbalanced Three-Phase Systems and Three-Phase Power Measurement (Two-Wattmeter Method)",
            "Magnetically Coupled Circuits, Mutual Inductance, and Linear/Ideal Transformers",
            "Frequency Response, Series & Parallel Resonance, and Passive Filters",
            "Two-Port Networks (Impedance, Admittance, Hybrid, and Transmission Parameters)"
        ]
    },
    {
        "code": "EE 221L",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Electrical Circuits 2 Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 221",
        "pgo_pi": "PGO-b-b.2 [E]; PGO-d-d.1 [E]; PGO-g-g.3 [E]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 7, SDG 9",
        "description": "Laboratory component of Electrical Circuits 2. The course deals with sinusoidal steady-state analysis in the frequency domain; AC circuit power analysis; analysis of polyphase circuits and magnetically-coupled circuits; frequency response; per unit system and symmetrical components; and two-port networks.",
        "topics": [
            "Single-Phase AC Power and Power Factor Correction",
            "Series and Parallel Resonance Characteristics",
            "Balanced Wye and Delta Three-Phase Circuits",
            "Three-Phase Power Measurement Using Wattmeters",
            "Two-Port Network Parameter Measurement"
        ]
    },
    {
        "code": "EE 222",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Advanced Engineering Mathematics for EE",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Math 211",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.2 [E], PGO-m-m.3 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.3",
                "pi_description": "Apply designed system to process to solve engineering problems.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 9",
        "description": "The study of mathematical methods for solving engineering problems such as complex number, complex variables, Cauchy-Riemann equations, Laplace transformation and Laplace transform analysis, Fourier series and Fourier transform, z-transform, power series solutions of ordinary differential equations, partial differential equation, and hypergeometric equations such as Legendre and Bessel functions.",
        "topics": [
            "Complex Numbers, Polar/Exponential Forms, and Analytic Functions",
            "Laplace Transforms and Inverse Laplace Transforms in Circuit/System Analysis",
            "Power Series and Fourier Series Analysis",
            "Fourier Transforms and Z-Transforms",
            "Vector Calculus and Matrix Eigenvalue Problems"
        ]
    },
    {
        "code": "EE 223",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Electromagnetics 1",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Nat Sci 2, Math 211",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.3 [E], PGO-e-e.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.3",
                "pi_description": "Apply principles in physical sciences to solve engineering problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 4, SDG 7, SDG 9",
        "description": "The course deals with the study of electric and magnetic fields; resistive, dielectric and magnetic materials, coupled circuits, magnetic circuits and fields; and time-varying electromagnetic fields. It involves a review of vector analysis and types of coordinate system (Cartesian, cylindrical and spherical coordinate systems). Topics covered are dot and cross products of vector, Coulomb's law and electric field intensity of different charge configuration (volume, point, line sheet charge), electric flux density, Gauss's Law, divergence, Maxwell's equations and energy and potential.",
        "topics": [
            "Vector Algebra, Coordinate Systems (Cartesian, Cylindrical, Spherical), and Vector Calculus",
            "Coulomb's Law, Electric Field Intensity, Electric Flux Density, and Gauss's Law",
            "Electric Potential, Energy Density, Conductors, Dielectrics, and Capacitance",
            "Steady Magnetic Fields: Biot-Savart Law, Ampere's Law, and Magnetic Flux Density",
            "Magnetic Forces, Materials, Inductance, Faraday's Law, and Maxwell's Equations"
        ]
    },
    {
        "code": "AEE 221",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Electronic Circuits: Devices and Analysis",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 211, EE 211L",
        "coreqs": "AEE 221L",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "The course covers the fundamentals of electronics and electronic circuits with their basic applications. This includes diode and transistor characteristics necessary for elementary analysis of electronic circuits with discrete components. The second half of the course covers integrated circuits commonly used in electrical engineering. The course introduces students to the design of electronic circuits for basic applications such as filters, power supplies and op amp signal processors.",
        "topics": [
            "Semiconductor Fundamentals and PN Junction Diode Characteristics",
            "Diode Applications: Rectifiers, Clippers, Clampers, and Zener Voltage Regulators",
            "Bipolar Junction Transistors (BJT): DC Biasing and Load Line Analysis",
            "BJT Small-Signal AC Analysis and Amplifier Configurations",
            "Field Effect Transistors (JFET and MOSFET) Biasing and Amplification",
            "Operational Amplifiers (Op-Amps) and Linear/Nonlinear Applications"
        ]
    },
    {
        "code": "AEE 221L",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Electronic Circuits: Devices and Analysis Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "AEE 221",
        "pgo_pi": "PGO-b-b.2 [E], PGO-c-c.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.2",
                "pi_description": "Design an experiment to achieve a specific objective.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.2",
                "pi_description": "Design a system or process based on various constraints",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA3",
                    "IGA4",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "Laboratory component of Electronic Circuits: Devices and Analysis. The course covers the fundamentals of electronics and electronic circuits with their basic applications. This includes diode and transistor characteristics necessary for elementary analysis of electronic circuits with discrete components. The second half of the course covers integrated circuits commonly used in electrical engineering. The course introduces students to the design of electronic circuits for basic applications such as filters, power supplies and op amp signal processors.",
        "topics": [
            "Semiconductor Diode & Zener Diode Characteristics",
            "Half-Wave and Full-Wave Bridge Rectifiers with Filters",
            "BJT DC Biasing and Common-Emitter Amplifier",
            "FET Characteristics and Operational Amplifier Circuits"
        ]
    },
    {
        "code": "AEE 222",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Fundamentals of Deformable Bodies",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "BES 104",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.3 [E], PGO-e-e.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.3",
                "pi_description": "Apply principles in physical sciences to solve engineering problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 4, SDG 7, SDG 9",
        "description": "The course deals with the study of strength of materials where the understanding of how bodies and materials respond to applied loads is the main emphasis. The course covers the fundamental concepts of stresses and strains experienced and/or developed by different materials in their loaded state and subjected to different conditions of constraint that includes axial stress, shearing stress, bearing stress, torsion, flexural stress, and stress-strain relationships.",
        "topics": [
            "Vector Algebra, Coordinate Systems (Cartesian, Cylindrical, Spherical), and Vector Calculus",
            "Coulomb's Law, Electric Field Intensity, Electric Flux Density, and Gauss's Law",
            "Electric Potential, Energy Density, Conductors, Dielectrics, and Capacitance",
            "Steady Magnetic Fields: Biot-Savart Law, Ampere's Law, and Magnetic Flux Density",
            "Magnetic Forces, Materials, Inductance, Faraday's Law, and Maxwell's Equations"
        ]
    },
    {
        "code": "PE 224",
        "year_level": "Second Year",
        "semester": "2nd Semester",
        "title": "Physical Activities Towards Health and Fitness II",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "PE 213",
        "coreqs": "None",
        "pgo_pi": "PGO-d-d.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 3: Good Health and Well-being",
        "description": "Team sports engagement emphasizing strategy, tactical teamwork, collaborative play, and leadership under competitive scenarios.",
        "topics": [
            "Team Dynamics and Sportsmanship Principles",
            "Sport-Specific Tactical Drills and Formations",
            "Officiating Rules, Regulations, and Scorekeeping",
            "Lifelong Fitness and Community Sports Leadership"
        ]
    },
    {
        "code": "GE 319",
        "year_level": "Second Year",
        "semester": "Off-Semester",
        "title": "Contemporary World",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-h-h.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 17: Partnerships for the Goals",
        "description": "Examines economic, political, and cultural globalization, international trade, and global energy markets and supply chains.",
        "topics": [
            "Economic and Financial Dimensions of Globalization",
            "Global Energy Politics, OPEC, and International Power Grids",
            "Global Environmental Governance and Climate Accords",
            "Technological Interdependence and International Engineering Standards"
        ]
    },
    {
        "code": "EGE 312",
        "year_level": "Second Year",
        "semester": "Off-Semester",
        "title": "General Education Elective 2",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-g-g.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 4: Quality Education",
        "description": "Selected topics in Philippine society, cultural geography, or environmental ethics.",
        "topics": [
            "Cultural Geography and Human Landscapes of the Philippines",
            "Social Dimensions of Energy Policy and Rural Electrification",
            "Global Perspectives on Sustainable Development",
            "Policy Advocacy for Transparent Energy Governance"
        ]
    },
    {
        "code": "EGE 313",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "General Education Elective 3",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-g-g.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 4: Quality Education",
        "description": "Studies Philippine cultural identity, regional history, or environmental philosophy.",
        "topics": [
            "Mindanao Cultural Traditions and Indigenous Heritage",
            "Land Tenure Dynamics in Multi-Cultural Communities",
            "Sustainable Development and Regional Resource Politics",
            "Public Advocacy for Transparent Governance"
        ]
    },
    {
        "code": "EE 311",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Electrical Machines 1",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 221, EE 221L",
        "coreqs": "EE 311L",
        "pgo_pi": "PGO-e-e.2 [E], PGO-g-g.2 [E], PGO-m-m.3 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.3",
                "pi_description": "Apply designed system to process to solve engineering problems.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "The course deals with the fundamentals of DC machinery; DC motors and generators.",
        "topics": [
            "Magnetic Circuits, Losses, and Principles of Electromechanical Energy Conversion",
            "Single-Phase Transformers: Equivalent Circuit, Voltage Regulation, and Efficiency",
            "Autotransformers, Instrument Transformers, and Three-Phase Transformer Connections",
            "DC Machine Fundamentals, Armature Winding, and Commutation",
            "DC Generators: Types, Characteristics, and Voltage Build-Up",
            "DC Motors: Torque-Speed Characteristics, Speed Control, and Starting"
        ]
    },
    {
        "code": "EE 311L",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Electrical Machines 1 Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 311",
        "pgo_pi": "PGO-e-e.2 [E], PGO-g-g.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "Laboratory component of Electrical Machines 1. The course deals with the fundamentals of DC machinery; DC motors and generators.",
        "topics": [
            "Transformer Polarity, Ratio, Open-Circuit, and Short-Circuit Tests",
            "Three-Phase Transformer Connections (Delta-Delta, Wye-Wye, Delta-Wye)",
            "DC Shunt and Compound Generator Characteristics",
            "DC Motor Load Characteristics and Speed Control"
        ]
    },
    {
        "code": "EE 312",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "EE Laws, Codes, and Professional Ethics",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "GE 114",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.2 [E], PGO-g-g.1 [E], PGO-h-h.1 [E], PGO-l-l.3 [E], PGO-m-m.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.3",
                "pi_description": "Participates in discussions and comes up with sound suggestions to problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.3",
                "pi_description": "Apply designed system to process to solve engineering problems.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 9",
        "description": "The course is designed to prepare electrical engineering students for professional practice. Topics include education and practice of the New Electrical Engineering Law and other laws governing the profession, Philippine Grid Code, Philippine Distribution Code, Basic Contracts and ethics in relation to the practice of the electrical engineering profession.",
        "topics": [
            "Applications of Differential & Integral Calculus to Electrical Circuits",
            "First and Higher-Order Differential Equations in Transient Circuit Analysis",
            "Complex Numbers, Phasors, and Matrix Methods in Network Analysis",
            "Laplace Transform Applications in Transfer Functions and Dynamic Systems"
        ]
    },
    {
        "code": "EE 313",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Feedback Control Systems",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 222, AEE 221",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.3 [E], PGO-e-e.3 [E], PGO-g-g.3 [E], PGO-k-k.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.3",
                "pi_description": "Apply principles in physical sciences to solve engineering problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.1",
                "pi_description": "Handles the details of the work assigned to him/her",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            }
        ],
        "sdgs": "SDG 8, SDG 16",
        "description": "This course deals with the basics of control systems; terminologies and diagrams; homogeneous and transient responses of systems; systems representation such as transfer functions; state-space analysis of phase variables and techniques, nth order linear differential equations; modeling, pole-zero gain data and frequency response data; Laplace transforms; block diagrams interconnections and simplifications; signal flow graphs; conversion of block diagrams to signal flow graphs and vice versa; root locus; Bode, Nyquist and Polar plots; PID controllers; sensitivity and stability criteria; linear feedback systems; and compensation techniques.",
        "topics": [
            "Basic Principles of Law, Obligations, and Contracts",
            "RA 7920: The New Electrical Engineering Law & Implementing Rules",
            "Code of Ethics for Electrical Practitioners",
            "RA 9136 (EPIRA), Philippine Grid & Distribution Codes, and Regulatory Bodies (ERC, DOE, NGCP)"
        ]
    },
    {
        "code": "BES 114",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Material Science and Engineering",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Nat Sci 1, AEE 222",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.1 [E], PGO-g-g.1 [I], PGO-h-h.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.1",
                "pi_description": "Internalizes the professional code of ethics for specific discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            }
        ],
        "sdgs": "SDG 9: Industry, Innovation, and Infrastructure, SDG 12: Responsible Consumption and Production",
        "description": "The course deals with the properties of engineering materials including mechanical, acoustical, electrical, magnetic, chemical, optical and thermal properties.",
        "topics": [
            "Atomic Structure, Crystallography, and Band Theory of Solids",
            "Electrical Conduction in Metals, Alloys, and Superconductors",
            "Dielectric Materials, Polarization, Breakdown Voltage, and Insulators",
            "Magnetic Properties: Diamagnetism, Paramagnetism, Ferromagnetism, Hysteresis Loops",
            "Optoelectronic Materials, Photovoltaic Materials, and Thermal Degradation"
        ]
    },
    {
        "code": "AEE 311",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Industrial Electronics",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "AEE 221, AEE 221L",
        "coreqs": "AEE 311L",
        "pgo_pi": "PGO-e-e.2 [E], PGO-g-g.3 [I], PGO-b-b.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "This course teaches the theory and operation of solid-state devices and control circuits for industrial processes; industrial control applications; electronics instrumentation; transducers; data acquisition system, power supply and voltage regulator. It also covers photo electronics, sensors and instruments used in industrial applications. It includes variable-frequency drives, DC motor, servomotors and stepper motor drives; application of relay logic circuits; and interfacing and programming of PLCs.",
        "topics": [
            "Power Semiconductor Switches: Thyristors (SCR, TRIAC, GTO), Power MOSFETs, and IGBTs",
            "Single-Phase and Three-Phase Controlled Rectifiers (AC-to-DC Converters)",
            "DC-to-DC Converters (Buck, Boost, and Buck-Boost Choppers)",
            "DC-to-AC Inverters (Push-Pull, Half-Bridge, Full-Bridge, and PWM Techniques)",
            "Industrial Motor Control, Relay Ladder Logic, and Programmable Logic Controllers (PLCs)"
        ]
    },
    {
        "code": "AEE 311L",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Industrial Electronics Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "AEE 311",
        "pgo_pi": "PGO-b-b.1 [E], PGO-e-e.2 [E], PGO-g-g.3 [I]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "I",
                "ied_label": "Introductory",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "Laboratory component of Industrial Electronics. This course teaches the theory and operation of solid-state devices and control circuits for industrial processes; industrial control applications; electronics instrumentation; transducers; data acquisition system, power supply and voltage regulator. It also covers photo electronics, sensors and instruments used in industrial applications. It includes variable-frequency drives, DC motor, servomotors and stepper motor drives; application of relay logic circuits; and interfacing and programming of PLCs.",
        "topics": [
            "SCR and TRIAC Triggering and Phase Control Circuits",
            "Controlled Rectifiers and DC-DC Converter Experiments",
            "Electro-Pneumatic / Magnetic Contactor Motor Control",
            "PLC Ladder Logic Programming and Industrial Automation Project"
        ]
    },
    {
        "code": "AEE 313",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Logic Circuits Design and Switching Theory",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "AEE 221, AEE 221L",
        "coreqs": "AEE 313L",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.2 [E], PGO-c-c.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.1",
                "pi_description": "Develop an engineering solution that have various constraints as factors",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            }
        ],
        "sdgs": "SDG 9",
        "description": "This course provides a review of number systems, coding and Boolean algebra; inputs and outputs; gates and gating networks; combinational circuits; standard form; minimization; sequential circuits; state and machine equivalence; asynchronous sequential circuits; race conditions; algorithmic state machines; and design of digital sub-systems.",
        "topics": [
            "Number Systems, Codes, Boolean Algebra, and Logic Gates",
            "Boolean Function Minimization: Karnaugh Maps and Quine-McCluskey Method",
            "Combinational Logic Design: Adders, Subtractors, Encoders, Decoders, and Multiplexers",
            "Sequential Logic: Latches, Flip-Flops (SR, JK, D, T), Counters, and Shift Registers",
            "Finite State Machine (Mealy and Moore) Analysis and Design"
        ]
    },
    {
        "code": "AEE 313L",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Logic Circuits Design and Switching Theory Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "AEE 313",
        "pgo_pi": "PGO-b-b.1 [E], PGO-g-g.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 9",
        "description": "Laboratory component of Logic Circuits Design and Switching Theory. This course provides a review of number systems, coding and Boolean algebra; inputs and outputs; gates and gating networks; combinational circuits; standard form; minimization; sequential circuits; state and machine equivalence; asynchronous sequential circuits; race conditions; algorithmic state machines; and design of digital sub-systems.",
        "topics": [
            "Basic Logic Gates and Universal Gate Implementation",
            "Combinational Logic Circuits and Karnaugh Map Simplification",
            "Adders, Multiplexers, Seven-Segment Decoders, and Sequential Counters"
        ]
    },
    {
        "code": "ECE 222",
        "year_level": "Third Year",
        "semester": "1st Semester",
        "title": "Principles of Communication Systems",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.3 [E], PGO-e-e.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.3",
                "pi_description": "Apply principles in physical sciences to solve engineering problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 9",
        "description": "Fundamental principles of electronic communications theory and its applications. Emphasis is on the introduction of electronic communication systems, analysis and calculations of analog and digital modulation, transmission and reception. Provides insights, framework, knowledge and competencies necessary in analyzing basic communication system as a preparation for electronics.",
        "topics": [
            "Elements of Communication Systems, Signal Spectra, and Electrical Noise Analysis",
            "Amplitude Modulation (AM, DSB-SC, SSB, VSB) Generation and Demodulation",
            "Frequency (FM) and Phase (PM) Modulation, Bandwidth, and Superheterodyne Receivers"
        ]
    },
    {
        "code": "BES 109",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Engineering Management",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Math 212",
        "coreqs": "None",
        "pgo_pi": "PGO-d-d.2 [E], PGO-f-f.2 [E], PGO-g-g.3 [E], PGO-h-h.1 [E], PGO-j-j.2 [E], PGO-l-l.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.2",
                "pi_description": "Capable of learning from and listening to co-members.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA3"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.2",
                "pi_description": "Explain the possible impact of technology to local, national, and international issues.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.3",
                "pi_description": "Participates in discussions and comes up with sound suggestions to problems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 8: Decent Work and Economic Growth, SDG 9: Industry, Innovation, and Infrastructure",
        "description": "The course covers the principles of management, theory and practice, various approaches to decision making, managing production and services operations; and project management. Emphasis is also given on the managerial functions of planning, organizing, staffing, leading and controlling.",
        "topics": [
            "Management Theories, Organizational Structures, and Corporate Culture",
            "Project Planning, Staffing, and Performance Motivation in Engineering Teams",
            "Total Quality Management (TQM) and Reliability Engineering in Utilities",
            "Strategic Decision Making and Financial Budgeting in Power Enterprises"
        ]
    },
    {
        "code": "BES 110",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Technopreneurship",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "BES 109",
        "pgo_pi": "PGO-d-d.2 [E], PGO-f-f.2 [E], PGO-g-g.1 [E], PGO-g-g.3 [E], PGO-l-l.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.2",
                "pi_description": "Capable of learning from and listening to co-members.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA3"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.1",
                "pi_description": "Capable of learning from and listening to co-members.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            }
        ],
        "sdgs": "SDG 8: Decent Work and Economic Growth, SDG 9: Industry, Innovation, and Infrastructure",
        "description": "Technopreneurship is a philosophy, a way of building a career or perspective in life. The course covers the value of professional and life skills in entrepreneurial thought, investment decisions, and action that students can utilize in starting technology companies or executing R&D projects in companies as they start their careers. The net result is a positive outlook towards wealth creation, high value adding, and wellness in society.",
        "topics": [
            "Clean Energy and Smart Hardware Opportunity Recognition",
            "Lean Startup Methodology and Customer Discovery for Tech Products",
            "Intellectual Property Rights, Patents, and Trademark Protection",
            "Financial Modeling, Pitching, and Business Plan Defense for Energy Startups"
        ]
    },
    {
        "code": "EE 321",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Electrical Machines 2",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 311, EE 311L",
        "coreqs": "EE 321L",
        "pgo_pi": "PGO-b-b.2 [E], PGO-e-e.2 [E], PGO-g-g.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.2",
                "pi_description": "Design an experiment to achieve a specific objective.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7, SDG 9, SDG 12",
        "description": "The course deals with the fundamentals of AC machinery; synchronous generators and motors; induction motors; single-phase and special-purpose motors.",
        "topics": [
            "AC Machine Windings, Rotating Magnetic Field, and Induced EMF",
            "Synchronous Generators (Alternators): Equivalent Circuit, Voltage Regulation, and Parallel Operation",
            "Synchronous Motors: V-Curves, Power Factor Correction, and Starting Methods",
            "Three-Phase Induction Motors: Equivalent Circuit, Power Flow, Torque-Speed Characteristics, and Starting/Speed Control",
            "Single-Phase Induction Motors and Special-Purpose Electric Machines"
        ]
    },
    {
        "code": "EE 321L",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Electrical Machines 2 Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 321",
        "pgo_pi": "PGO-b-b.1 [E], PGO-e-e.2 [E], PGO-g-g.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "Laboratory component of Electrical Machines 2. The course deals with the fundamentals of AC machinery; synchronous generators and motors; induction motors; single-phase and special-purpose motors.",
        "topics": [
            "Synchronous Generator Open-Circuit, Short-Circuit, and Voltage Regulation Tests",
            "Synchronization and Parallel Operation of Three-Phase Alternators",
            "Synchronous Motor V-Curves and Power Factor Control",
            "Three-Phase Induction Motor Equivalent Circuit Parameter Determination and Load Test"
        ]
    },
    {
        "code": "EE 322L",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Electrical Standards and Practice",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "EE 312",
        "coreqs": "None",
        "pgo_pi": "PGO-c-c.2 [E], PGO-f-f.2 [D], PGO-g-g.1 [E], PGO-i-i.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.2",
                "pi_description": "Design a system or process based on various constraints",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA3",
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.1",
                "pi_description": "Demonstrate ability to learn independently.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "This course provides the different electrical practices in accordance to local and international standards.",
        "topics": [
            "Testing of Instrument Transformers (CT and PT Ratio and Polarity)",
            "Overcurrent and Differential Protective Relay Characteristics",
            "Insulation Resistance and Dielectric Breakdown Testing"
        ]
    },
    {
        "code": "EE 323",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Instrumentation and Control",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 313",
        "coreqs": "EE 323L",
        "pgo_pi": "PGO-b-b.2 [E], PGO-g-g.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.2",
                "pi_description": "Design an experiment to achieve a specific objective.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 9",
        "description": "The course deals with the study on control and testing: electromechanical analog and digital measuring and testing instruments; R, L and C measurements; calibration; graphic and waveform analyzing instruments; detectors for the measurements of process variables; analysis of performance characteristics of control systems; electronics, magnetic, hydraulic and mechanical control. It includes principles of controls and test measurements involving sensors, pneumatic controls, actuators, thermal detectors, thermocouples, thermistors, transducers, PID controllers.",
        "topics": [
            "Introduction to Control Systems, Laplace Modeling of Electrical & Mechanical Systems",
            "Transfer Functions, Block Diagram Reduction, and Mason's Gain Formula",
            "Time-Domain Analysis of First-Order and Second-Order Systems & Steady-State Error",
            "Stability Analysis: Routh-Hurwitz Criterion, Root Locus, and Frequency Response (Bode Plots)",
            "PID Controllers and Industrial Sensors, Transducers, and Transmitters"
        ]
    },
    {
        "code": "EE 323L",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Instrumentation and Control Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 323",
        "pgo_pi": "PGO-b-b.1 [E], PGO-g-g.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 9",
        "description": "Laboratory component of Instrumentation and Control. The course deals with the study on control and testing: electromechanical analog and digital measuring and testing instruments; R, L and C measurements; calibration; graphic and waveform analyzing instruments; detectors for the measurements of process variables; analysis of performance characteristics of control systems; electronics, magnetic, hydraulic and mechanical control. It includes principles of controls and test measurements involving sensors, pneumatic controls, actuators, thermal detectors, thermocouples, thermistors, transducers, PID controllers.",
        "topics": [
            "Sensors, Transducers, Signal Conditioning, and Data Acquisition",
            "Temperature, Pressure, Flow, and Level Process Measurement",
            "Closed-Loop On-Off and PID Controller Tuning and Simulation"
        ]
    },
    {
        "code": "AEE 321",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Microprocessor Systems",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "AEE 313, AEE 313L",
        "coreqs": "AEE 321L",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 9, SDG 11",
        "description": "The course includes history and evolution, principles, and applications of microprocessors. The focus is on the basic understanding of the architectural design, functional parts, operations, function and programming. It also covers the study of various types of microprocessors and the fundamental concepts of microcontrollers.",
        "topics": [
            "Microprocessor and Microcontroller Architecture (ALU, Registers, Control Unit, Buses)",
            "Fetch-Decode-Execute Cycle, Addressing Modes, and Instruction Set",
            "Memory Organization and Input/Output (I/O) Interfacing",
            "Timers, Interrupts, ADC/DAC, and Serial Communication Protocols (UART, SPI, I2C)"
        ]
    },
    {
        "code": "AEE 321L",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Microprocessor Systems Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "AEE 321",
        "pgo_pi": "PGO-b-b.1 [E], PGO-c-c.1 [E], PGO-g-g.2 [E], PGO-k-k.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.1",
                "pi_description": "Perform laboratory experiments as prescribed by standard procedures.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.1",
                "pi_description": "Develop an engineering solution that have various constraints as factors",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.3",
                "pi_description": "Use modern technology in performing engineering practice",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 9, SDG 11",
        "description": "Laboratory component of Microprocessor systems. The course includes history and evolution, principles, and applications of microprocessors. The focus is on the basic understanding of the architectural design, functional parts, operations, function and programming. It also covers the study of various types of microprocessors and the fundamental concepts of microcontrollers.",
        "topics": [
            "Microcontroller Digital I/O, Timers, and Interrupt Programming",
            "Analog-to-Digital Conversion, LCD/Display Interfacing, and PWM Motor Control",
            "Embedded Microcontroller System Design Project"
        ]
    },
    {
        "code": "BES 107",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Methods of Research",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "Math 212, GE 111",
        "coreqs": "None",
        "pgo_pi": "PGO-f-f.2 [E], PGO-g-g.1 [E], PGO-g-g.2 [E], PGO-h-h.1 [E], PGO-j-j.1 [E], PGO-l-l.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.1",
                "pi_description": "Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.2",
                "pi_description": "Shows leadership skills in managing a multidisciplinary group.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA3",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 9",
        "description": "This course covers the study of the methodologies used in conducting an engineering research. It includes the types and application of research, characteristics of a good research, research design, research instrument and data gathering procedures. It also deals with the study of writing a research proposal and various formats.",
        "topics": [
            "Research Frameworks, Identification of Engineering Research Problems, and Literature Review",
            "Experimental Design, Sampling Techniques, and Data Collection Protocols",
            "Technical Writing, Statistical Validation, Ethics, and Capstone Proposal Preparation"
        ]
    },
    {
        "code": "EE EL1",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "EE Elective 1",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 311",
        "coreqs": "None",
        "pgo_pi": "PGO-e-e.3 [E], PGO-f-f.2 [E], PGO-g-g.3 [D], PGO-h-h.1 [D], PGO-h-h.2 [D], PGO-i-i.2 [D], PGO-i-i.3 [D], PGO-j-j.2 [E], PGO-k-k.1 [E], PGO-m-m.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.2",
                "pi_description": "Describe engineering solutions in application to global, economic, environmental, and societal context.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.2",
                "pi_description": "Shows appreciation and understanding of the engineering profession.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.3",
                "pi_description": "Understand the linkage or connection between his/her task to previous, intervening, and subsequent tasks.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.2",
                "pi_description": "Explain the possible impact of technology to local, national, and international issues.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.1",
                "pi_description": "Handles the details of the work assigned to him/her",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.3",
                "pi_description": "Apply designed system to process to solve engineering problems.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7, SDG 9, SDG 13",
        "description": "Specialized elective course in Electrical Engineering (such as Renewable Energy Systems, Smart Grid Technologies, or Power Quality and Energy Management).",
        "topics": [
            "Overview of Specialized Electrical Engineering Domain and Standards",
            "Resource Assessment, System Modeling, and Technical Sizing",
            "Design, Grid Integration, Protection, and Economic Evaluation"
        ]
    },
    {
        "code": "EE 324",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Numerical Methods and Analysis",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "EE 222",
        "coreqs": "EE 324L",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.2 [E], PGO-k-k.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.3",
                "pi_description": "Use modern technology in performing engineering practice",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 9: Industry, Innovation, and Infrastructure, SDG 11: Sustainable Cities and Communities",
        "description": "This course covers the concepts of numerical analysis and computer software tools in dealing with engineering problems. It includes techniques in finding the roots of an equation, solving systems of linear and non-linear equations, eigenvalue problems, polynomial approximation and interpolation, ordinary and partial differential equations. The Monte-Carlo method, simulation, error propagation and analysis, the methods of least squares and goodness-of-fit tests are also covered.",
        "topics": [
            "Philippine Electrical Code (PEC) Volumes 1 & 2 In-Depth Applications",
            "Philippine Grid Code (PGC) Connection and Operational Requirements",
            "Philippine Distribution Code (PDC) Performance and Reliability Metrics",
            "IEEE, ANSI, and IEC Equipment Standards and Conformity Assessment"
        ]
    },
    {
        "code": "EE 324L",
        "year_level": "Third Year",
        "semester": "2nd Semester",
        "title": "Numerical Methods and Analysis Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 324",
        "pgo_pi": "PGO-a-a.1 [E], PGO-e-e.2 [E], PGO-k-k.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.3",
                "pi_description": "Use modern technology in performing engineering practice",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7, SDG 9, SDG 13",
        "description": "Laboratory component of Numerical Methods and Analysis. This course covers the concepts of numerical analysis and computer software tools in dealing with engineering problems. It includes techniques in finding the roots of an equation, solving systems of linear and non-linear equations, eigenvalue problems, polynomial approximation and interpolation, ordinary and partial differential equations. The Monte-Carlo method, simulation, error propagation and analysis, the methods of least squares and goodness-of-fit tests are also covered.",
        "topics": [
            "Computational Implementation of Root-Finding Algorithms",
            "Matrix Solvers and Gauss-Seidel Load Flow Iterations",
            "Curve Fitting, Numerical Integration, and Runge-Kutta ODE Simulation"
        ]
    },
    {
        "code": "EE 400",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Capstone Design Project",
        "credit_units": "3.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 3,
        "lec_lab": "Laboratory",
        "hours": "9 Hours/Week (9 hours Lab)",
        "prereqs": "BES 107",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [D], PGO-b-b.2 [D], PGO-c-c.1 [D], PGO-e-e.2 [D], PGO-e-e.3 [D], PGO-f-f.2 [D], PGO-g-g.1 [D], PGO-g-g.2 [D], PGO-g-g.3 [D], PGO-h-h.1 [D], PGO-h-h.2 [D], PGO-i-i.1 [D], PGO-i-i.2 [D], PGO-i-i.3 [D], PGO-j-j.1 [D], PGO-j-j.2 [D], PGO-j-j.3 [D], PGO-k-k.3 [D], PGO-l-l.1 [D], PGO-l-l.2 [D], PGO-l-l.3 [D], PGO-m-m.1 [D], PGO-m-m.2 [D], PGO-m-m.3 [D]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO a",
                "pgo_keyword": "Engineering Rigor & Foundational Competence",
                "pi": "a.1",
                "pi_description": "Apply math and science to analyze technical systems",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.2",
                "pi_description": "Design an experiment to achieve a specific objective.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.1",
                "pi_description": "Develop an engineering solution that have various constraints as factors",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.2",
                "pi_description": "Describe engineering solutions in application to global, economic, environmental, and societal context.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.1",
                "pi_description": "Demonstrate ability to learn independently.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.2",
                "pi_description": "Shows appreciation and understanding of the engineering profession.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.3",
                "pi_description": "Understand the linkage or connection between his/her task to previous, intervening, and subsequent tasks.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.1",
                "pi_description": "Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA1",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.2",
                "pi_description": "Explain the possible impact of technology to local, national, and international issues.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.3",
                "pi_description": "Shows leadership skills in managing a multidisciplinary group.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.3",
                "pi_description": "Use modern technology in performing engineering practice",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.1",
                "pi_description": "Capable of learning from and listening to co-members.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.2",
                "pi_description": "Shows leadership skills in managing a multidisciplinary group.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO l",
                "pgo_keyword": "Transformative Leadership & Project Management",
                "pi": "l.3",
                "pi_description": "Participates in discussions and comes up with sound suggestions to problems",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.1",
                "pi_description": "Demonstrate leadership and team management in a multidisciplinary group.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.2",
                "pi_description": "Capable of learning from and listening to co-members",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.3",
                "pi_description": "Apply designed system to process to solve engineering problems.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7 (Affordable and Clean Energy), SDG 9 (Industry, Innovation, and Infrastructure), SDG 11 (Sustainable Cities and Communities)",
        "description": "Culminating engineering design project Phase 1: Problem formulation, literature search, conceptual design, engineering standards compliance, simulation, prototyping, and proposal oral defense.",
        "topics": [
            "OBE Framework and Capstone Engineering Design Methodology",
            "Problem Identification, Literature Review, and State of the Art Evaluation",
            "Conceptual Design Alternatives, Trade-Off Studies, and Component Sizing",
            "Simulation, Preliminary Hardware-Software Prototyping, and Standards Compliance",
            "Preparation of Capstone Project Manuscript and Formal Proposal Defense"
        ]
    },
    {
        "code": "EE 411",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Power System Analysis",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 321, EE 321L, EE 322L, EE 323, EE 323L, EE EL1, EE 324, EE 324L",
        "coreqs": "EE 411L",
        "pgo_pi": "PGO-c-c.1 [E], PGO-e-e.2 [D], PGO-g-g.3 [D], PGO-j-j.3 [E], PGO-k-k.1 [D]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.1",
                "pi_description": "Develop an engineering solution that have various constraints as factors",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.3",
                "pi_description": "Shows leadership skills in managing a multidisciplinary group.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.1",
                "pi_description": "Handles the details of the work assigned to him/her",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA2"
            }
        ],
        "sdgs": "SDG 7, SDG 9, SDG 13",
        "description": "This course deals with the study on the basic structure of power systems, recent trends and innovations in power systems, transmission line parameters, network modeling and calculations, load flow studies, short circuit calculations and use of computer software for simulation.",
        "topics": [
            "Power System Structure, One-Line Diagrams, and Per-Unit (p.u.) System Representation",
            "Transmission Line Parameters (Series Impedance, Shunt Capacitance) and ABCD Models",
            "Network Modeling (Ybus and Zbus) and Power Flow Analysis (Gauss-Seidel & Newton-Raphson)",
            "Symmetrical Three-Phase Short-Circuit Fault Analysis",
            "Symmetrical Components, Sequence Networks, and Unsymmetrical Fault Analysis (SLG, LL, DLG)",
            "Power System Stability and Protection Coordination Overview"
        ]
    },
    {
        "code": "EE 411L",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Power System Analysis Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 411",
        "pgo_pi": "PGO-c-c.2 [E], PGO-e-e.3 [D], PGO-g-g.1 [D], PGO-j-j.1 [E], PGO-k-k.1 [D], PGO-k-k.3 [D]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.2",
                "pi_description": "Design a system or process based on various constraints",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA3",
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.1",
                "pi_description": "Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.1",
                "pi_description": "Handles the details of the work assigned to him/her",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.3",
                "pi_description": "Use modern technology in performing engineering practice",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7, SDG 9, SDG 13",
        "description": "Laboratory component of Power System Analysis. This course deals with the study on the basic structure of power systems, recent trends and innovations in power systems, transmission line parameters, network modeling and calculations, load flow studies, short circuit calculations and use of computer software for simulation.",
        "topics": [
            "One-Line Diagram Modeling and Per-Unit System Setup in Power System Software",
            "Load Flow Simulation and Voltage Profile Optimization",
            "Symmetrical and Unsymmetrical Short-Circuit Fault Studies"
        ]
    },
    {
        "code": "EE 412",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Industrial Plant Vists and Seminars",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 411, EE 411L",
        "pgo_pi": "PGO-g-g.1 [D], PGO-g-g.2 [D], PGO-h-h.1 [D], PGO-i-i.1 [D], PGO-j-j.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.1",
                "pi_description": "Demonstrate ability to learn independently.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.2",
                "pi_description": "Explain the possible impact of technology to local, national, and international issues.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 9: Industry, Innovation, and Infrastructure, SDG 7: Affordable and Clean Energy",
        "description": "The course involves the attendance and participation of EE graduating students in technical seminars/workshops related to the field of Electrical Engineering. Students are also required to attend non-technical seminars and training for the enhancement of their personality. It also involves short lectures on current trends and recent developments in the EE field. It may include educational visits to selected companies and manufacturing plants.",
        "topics": [
            "Power Generation Plant Operations: Hydroelectric, Geothermal, Solar, Coal",
            "High-Voltage Transmission Substation Tours and Switchyard Walkthroughs",
            "Industrial Plant Power Distribution, Motor Control Centers, and Switchgear Tours",
            "Technical Seminar Reports, Synthesis, and Professional Critique"
        ]
    },
    {
        "code": "EE 413",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Electrical Systems & Illumination Engineering Design",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "EE 321, EE 321L",
        "coreqs": "EE 413L",
        "pgo_pi": "PGO-c-c.2 [D], PGO-d-d.2 [E], PGO-e-e.2 [D], PGO-f-f.1 [E], PGO-g-g.2 [D], PGO-j-j.1 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.2",
                "pi_description": "Design a system or process based on various constraints",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.2",
                "pi_description": "Capable of learning from and listening to co-members.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA3"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.1",
                "pi_description": "Internalizes the professional code of ethics for specific discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.1",
                "pi_description": "Identify the socio-economic, political, and environmental issues related to the practice of engineering.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA1",
                    "IGA3"
                ]
            }
        ],
        "sdgs": "SDG 7, SDG 11, SDG 13",
        "description": "The course provides knowledge, understanding and skills in designing electrical wiring system for residential, commercial buildings, and industrial facilities through the specifications and standards mandated by the Philippine Electrical Code and provisions from the Local Government on electrical wiring installation. The course includes illumination design and cost estimation; energy-efficient lighting systems for residential, commercial, and industrial establishments; roadway lighting, and lighting maintenance.",
        "topics": [
            "Philippine Electrical Code (PEC) Provisions for Wiring Design and Protection",
            "Illumination Engineering Principles, Lumen & Point-by-Point Methods, and Energy-Efficient Lighting Design",
            "Residential and Commercial Lighting & Power Layout Design",
            "Schedule of Loads, Branch Circuit, Feeder, Conduit, and Service Entrance Calculations",
            "Overcurrent Protection Sizing, Voltage Drop, Grounding, and Short-Circuit Calculations",
            "Bill of Materials and Electrical Cost Estimation"
        ]
    },
    {
        "code": "EE 413L",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Electrical Systems & Illumination Engineering Design Lab",
        "credit_units": "2.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 2,
        "lec_lab": "Laboratory",
        "hours": "6 Hours/Week (6 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 413",
        "pgo_pi": "PGO-c-c.2 [D], PGO-d-d.1 [E], PGO-e-e.3 [D], PGO-f-f.2 [E], PGO-g-g.1 [D], PGO-g-g.3 [D], PGO-j-j.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.2",
                "pi_description": "Design a system or process based on various constraints",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.1",
                "pi_description": "Shows tact in dealing with people he/she comes in contact with.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA1"
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.1",
                "pi_description": "Articulate the convention and style in oral communication that conveys complete thought and information.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.2",
                "pi_description": "Explain the possible impact of technology to local, national, and international issues.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 7, SDG 11, SDG 13",
        "description": "Laboratory component of Electrical Systems & Illumination Engineering Design. The course provides knowledge, understanding and skills in designing electrical wiring system for residential, commercial buildings, and industrial facilities through the specifications and standards mandated by the Philippine Electrical Code and provisions from the Local Government on electrical wiring installation. The course includes illumination design and cost estimation; energy-efficient lighting systems for residential, commercial, and industrial establishments; roadway lighting, and lighting maintenance.",
        "topics": [
            "Illumination Simulation and Lighting Plan Preparation",
            "Complete Residential and Commercial Building Electrical Plan & Schedule of Loads",
            "Industrial Facility Power Distribution, Single-Line Diagram, and Design Analysis"
        ]
    },
    {
        "code": "EE 414L",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Fundamentals of Power Plant Engineering Design",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 411, EE 411L",
        "pgo_pi": "PGO-c-c.2 [E], PGO-f-f.2 [E], PGO-g-g.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.2",
                "pi_description": "Design a system or process based on various constraints",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA3",
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 7, SDG 9, SDG 11, SDG 13",
        "description": "It covers topics on load graphics, types of power plants, power plant operation and protection, interconnections, economics of electric service, and arrangement of equipment for modern plants and includes the design of a power plant, its interconnection, operation, economics, and protection.",
        "topics": [
            "Load Curves, Demand Factor, Diversity Factor, Load Factor, and Capacity Factor",
            "Conventional and Renewable Power Plant Technologies & Operations",
            "Power Plant Economics, Tariff Structures, and Substation Layout Design"
        ]
    },
    {
        "code": "EE 415",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Distribution Systems and Substation Design",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "None",
        "coreqs": "EE 411, EE 411L, EE 415L",
        "pgo_pi": "PGO-c-c.2 [D], PGO-d-d.3 [D], PGO-f-f.2 [E], PGO-g-g.2 [E], PGO-h-h.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.2",
                "pi_description": "Design a system or process based on various constraints",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.3",
                "pi_description": "Shows respect and courtesy in dealing with peers and superiors.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.2",
                "pi_description": "Describe engineering solutions in application to global, economic, environmental, and societal context.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 7: Affordable and Clean Energy, SDG 9: Industry, Innovation, and Infrastructure",
        "description": "The course deals with study and design of primary and secondary distribution networks, load characteristics, voltage regulation, metering techniques and systems, and protection of distribution systems.",
        "topics": [
            "Load Curves, Load Duration Curves, Demand Factors, and Plant Capacity Factor",
            "Synchronous Generator Sizing, Capability Curves, and Excitation Systems",
            "Unit Step-Up (GSU) Transformers and Station Service Electrical Single-Line Layouts",
            "Synchronization Systems, Governor Controls, and Islanding Protections"
        ]
    },
    {
        "code": "EE 415L",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Distribution Systems and Substation Design Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 415",
        "pgo_pi": "PGO-c-c.2 [D], PGO-e-e.2 [E], PGO-f-f.2 [E], PGO-g-g.2 [E], PGO-h-h.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO c",
                "pgo_keyword": "Sustainable Systems Innovation",
                "pi": "c.2",
                "pi_description": "Design a system or process based on various constraints",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.2",
                "pi_description": "Describe engineering solutions in application to global, economic, environmental, and societal context.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            }
        ],
        "sdgs": "SDG 7, SDG 9, SDG 11",
        "description": "Laboratory component of Distribution Systems and Substation Design. The course deals with study and design of primary and secondary distribution networks, load characteristics, voltage regulation, metering techniques and systems, and protection of distribution systems.",
        "topics": [
            "Distribution Feeder Modeling and Load Flow Simulation using Software Tools",
            "Voltage Drop Profile and Capacitor Bank Placement Simulation",
            "Substation Single-Line Diagram (SLD) Drafting and Equipment Sizing",
            "Time-Current Characteristic (TCC) Curves and Protection Coordination",
            "Substation Grounding Grid Resistance and Step/Touch Potential Simulation"
        ]
    },
    {
        "code": "EE EL2",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "EE Elective 2",
        "credit_units": "3.0 Units \u2013 Lecture",
        "lecture_units": 3,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "3 Hours/Week (3 hours Lecture)",
        "prereqs": "None",
        "coreqs": "EE 411, EE 411L",
        "pgo_pi": "PGO-e-e.3 [E], PGO-f-f.2 [E], PGO-g-g.3 [D], PGO-h-h.1 [D], PGO-h-h.2 [D], PGO-i-i.2 [D], PGO-i-i.3 [D], PGO-j-j.2 [E], PGO-k-k.3 [E], PGO-m-m.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.3",
                "pi_description": "Solve specific engineering problem related to discipline.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.1",
                "pi_description": "Relate engineering solutions to global, economic, environmental, and societal context.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA2",
                    "IGA3"
                ]
            },
            {
                "pgo": "PGO h",
                "pgo_keyword": "Community Transformation & Sustainability",
                "pi": "h.2",
                "pi_description": "Describe engineering solutions in application to global, economic, environmental, and societal context.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.2",
                "pi_description": "Shows appreciation and understanding of the engineering profession.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.3",
                "pi_description": "Understand the linkage or connection between his/her task to previous, intervening, and subsequent tasks.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.2",
                "pi_description": "Explain the possible impact of technology to local, national, and international issues.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.3",
                "pi_description": "Use modern technology in performing engineering practice",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.3",
                "pi_description": "Apply designed system to process to solve engineering problems.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7 (Affordable and Clean Energy), SDG 13 (Climate Action)",
        "description": "Principles, resource assessment, modeling, and grid integration of renewable energy technologies including solar photovoltaic, wind turbine generators, biomass, small hydro, and battery energy storage systems (BESS). Covers microgrid architecture, islanding detection, and renewable energy policy.",
        "topics": [
            "Renewable Energy Resource Assessment and Solar / Wind Resource Potential",
            "Solar Photovoltaic Cell Physics, PV Array Sizing, and Inverter Topologies",
            "Wind Turbine Aerodynamics, Generator Architectures, and Power Curves",
            "Battery Energy Storage Systems (BESS) and Hybrid Microgrid System Architectures",
            "Grid Interconnection Standards (Philippine Grid Code for Renewables) and Anti-Islanding Protection"
        ]
    },
    {
        "code": "EE 416",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Electrical Apparatus and Devices",
        "credit_units": "2.0 Units \u2013 Lecture",
        "lecture_units": 2,
        "lab_units": 0,
        "lec_lab": "Lecture",
        "hours": "2 Hours/Week (2 hours Lecture)",
        "prereqs": "EE 221, EE 221L",
        "coreqs": "EE 416L",
        "pgo_pi": "PGO-b-b.2 [E], PGO-e-e.2 [E], PGO-g-g.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.2",
                "pi_description": "Design an experiment to achieve a specific objective.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 7, SDG 9, SDG 11",
        "description": "This course provides characteristics, principle of operation, and applications of single-phase and three-phase transformers, and protective devices such as fuses and circuit breakers. It includes various types of transformers based on different criteria, types of fuses and circuit breakers, parallel operation of transformers, and standard ratings.",
        "topics": [
            "Fundamentals of Electrical Switching, Arc Interruption, and Fault Protection",
            "Power Fuses, Low-Voltage and Medium/High-Voltage Circuit Breakers",
            "Instrument Transformers (Current Transformers & Potential Transformers) and Protective Relays",
            "Surge Arresters, Insulation Coordination, Power Capacitors, and Reactors"
        ]
    },
    {
        "code": "EE 416L",
        "year_level": "Fourth Year",
        "semester": "1st Semester",
        "title": "Electrical Apparatus and Devices Lab",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "None",
        "coreqs": "EE 416",
        "pgo_pi": "PGO-b-b.2 [E], PGO-e-e.2 [E], PGO-g-g.2 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO b",
                "pgo_keyword": "Impactful Research & Empirical Investigation",
                "pi": "b.2",
                "pi_description": "Design an experiment to achieve a specific objective.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO e",
                "pgo_keyword": "Critical Analysis & Complex Problem Solving",
                "pi": "e.2",
                "pi_description": "Apply concepts, theories, and principles in solving engineering problem(s).",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.2",
                "pi_description": "Articulate the convention and style in written communication that conveys complete thought and information.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA5"
            }
        ],
        "sdgs": "SDG 7, SDG 9",
        "description": "Laboratory Component of Electrical Apparatus and Devices. This course provides characteristics, principle of operation, and applications of single-phase and three-phase transformers, and protective devices such as fuses and circuit breakers. It includes various types of transformers based on different criteria, types of fuses and circuit breakers, parallel operation of transformers, and standard ratings.",
        "topics": [
            "Testing of Instrument Transformers (CT and PT Ratio and Polarity)",
            "Overcurrent and Differential Protective Relay Characteristics",
            "Insulation Resistance and Dielectric Breakdown Testing"
        ]
    },
    {
        "code": "EE 400*",
        "year_level": "Fourth Year",
        "semester": "2nd Semester",
        "title": "Capstone Design Project",
        "credit_units": "3.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 3,
        "lec_lab": "Laboratory",
        "hours": "9 Hours/Week (9 hours Lab)",
        "prereqs": "EE 411, EE 411L, EE 412, EE 413, EE 413L, EE 414L, EE 415, EE 415L, EE EL2, EE 416, EE 416L",
        "coreqs": "None",
        "pgo_pi": "PGO-a-a.1 [I]",
        "pgo_pi_mappings": [],
        "sdgs": "SDG 7: Affordable and Clean Energy, SDG 9: Industry, Innovation, and Infrastructure",
        "description": "Culminating engineering application course requiring students to undergo an independent or group research investigation or capstone design project in electrical engineering. It integrates competencies in engineering analysis, design, simulation, prototyping, testing, economic viability, and environmental sustainability, culminating in a written thesis/capstone project report and oral defense.",
        "topics": [
            "Fundamental Principles and Theoretical Framework of Capstone Design Project",
            "Engineering Analysis, Modeling, and Applications in Capstone Design Project",
            "Design Calculations, Standard Specifications, and Laboratory Testing",
            "Contemporary Developments and Professional Practice in Capstone Design Project"
        ]
    },
    {
        "code": "EE 421",
        "year_level": "Fourth Year",
        "semester": "2nd Semester",
        "title": "On-the-Job Training (320 hours)",
        "credit_units": "2.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 2,
        "lec_lab": "Laboratory",
        "hours": "6 Hours/Week (6 hours Lab)",
        "prereqs": "EE 411L, EE 412, EE 413, EE 413L, EE 414L, EE 415, EE 415L, EE EL2, EE 416, EE 416L, EE 411",
        "coreqs": "None",
        "pgo_pi": "PGO-d-d.1 [D], PGO-d-d.2 [D], PGO-d-d.3 [D], PGO-f-f.2 [D], PGO-g-g.3 [D], PGO-i-i.1 [D], PGO-i-i.2 [D], PGO-i-i.3 [D], PGO-j-j.3 [D], PGO-k-k.1 [D], PGO-m-m.2 [D]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.1",
                "pi_description": "Shows tact in dealing with people he/she comes in contact with.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA1"
            },
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.2",
                "pi_description": "Capable of learning from and listening to co-members.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA3"
            },
            {
                "pgo": "PGO d",
                "pgo_keyword": "Inclusive Collaboration & Team Dynamics",
                "pi": "d.3",
                "pi_description": "Shows respect and courtesy in dealing with peers and superiors.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO f",
                "pgo_keyword": "Conscience-Guided Ethics & Accountability",
                "pi": "f.2",
                "pi_description": "Applies the principles of professional ethical standard and social responsibility to actual practice.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO g",
                "pgo_keyword": "Global Technical Communication",
                "pi": "g.3",
                "pi_description": "Demonstrate proficiency in using graphs, tables, drawings, symbols, etc. applicable in the discipline.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.1",
                "pi_description": "Demonstrate ability to learn independently.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA1",
                    "IGA2"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.2",
                "pi_description": "Shows appreciation and understanding of the engineering profession.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA3",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO i",
                "pgo_keyword": "Continuous Learning & Adaptive Growth",
                "pi": "i.3",
                "pi_description": "Understand the linkage or connection between his/her task to previous, intervening, and subsequent tasks.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": [
                    "IGA4",
                    "IGA5"
                ]
            },
            {
                "pgo": "PGO j",
                "pgo_keyword": "Proactive Social Awareness",
                "pi": "j.3",
                "pi_description": "Shows leadership skills in managing a multidisciplinary group.",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO k",
                "pgo_keyword": "Modern Tool Mastery & Digital Innovation",
                "pi": "k.1",
                "pi_description": "Handles the details of the work assigned to him/her",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA2"
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.2",
                "pi_description": "Capable of learning from and listening to co-members",
                "ied": "D",
                "ied_label": "Demonstrative",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 8 (Decent Work and Economic Growth), SDG 9, SDG 17",
        "description": "Industry exposure of students for them to match school acquired competencies and knowledge with the realities and problems of industry. This may include involvement in industry manpower requirements, development and research concerns, training, and applications of principles, environmental concerns, ethical and behavioral concerns, decision-making, equipment and materials management. The student shall prepare a report on a topic covered by his/her experiences.",
        "topics": [
            "Company Orientation, Safety Protocols, and Industrial Facility Operations",
            "Hands-on Technical Work in Electrical Generation, Transmission, Distribution, or Industrial Maintenance",
            "Professional Ethics, Work Discipline, and Team Collaboration in an Industry Setting",
            "Preparation and Submission of OJT Weekly Progress Reports and Final Industry Portfolio"
        ]
    },
    {
        "code": "EE EL3",
        "year_level": "Fourth Year",
        "semester": "2nd Semester",
        "title": "EE Elective 3: Correlation Course 1",
        "credit_units": "2.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 2,
        "lec_lab": "Laboratory",
        "hours": "6 Hours/Week (6 hours Lab)",
        "prereqs": "EE 411, EE 411L, EE 412, EE 413, EE 413L, EE 414L, EE 415, EE 415L, EE EL2, EE 416, EE 416L",
        "coreqs": "None",
        "pgo_pi": "PGO-m-m.2 [E], PGO-m-m.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.2",
                "pi_description": "Capable of learning from and listening to co-members",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            },
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.3",
                "pi_description": "Apply designed system to process to solve engineering problems.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 4: Quality Education",
        "description": "Comprehensive review, synthesis, and mock licensure examination drills covering Mathematics, Engineering Sciences, and Electrical Engineering subjects.",
        "topics": [
            "Electrical Engineering Mathematics and Sciences Refresher",
            "Electrical Circuits, Machines, and Power Systems Problem Solving",
            "Philippine Electrical Code (PEC) and Safety Standards Drills",
            "Comprehensive Mock Registered Electrical Engineer (REE) Licensure Exams"
        ]
    },
    {
        "code": "EE EL4",
        "year_level": "Fourth Year",
        "semester": "2nd Semester",
        "title": "Free Elective",
        "credit_units": "1.0 Units \u2013 Laboratory",
        "lecture_units": 0,
        "lab_units": 1,
        "lec_lab": "Laboratory",
        "hours": "3 Hours/Week (3 hours Lab)",
        "prereqs": "EE 411, EE 411L, EE 412, EE 413, EE 413L, EE 414L, EE 415, EE 415L, EE EL2, EE 416, EE 416L",
        "coreqs": "None",
        "pgo_pi": "PGO-m-m.3 [E]",
        "pgo_pi_mappings": [
            {
                "pgo": "PGO m",
                "pgo_keyword": "Specialized Global Competence",
                "pi": "m.3",
                "pi_description": "Apply designed system to process to solve engineering problems.",
                "ied": "E",
                "ied_label": "Enabling",
                "igas": "IGA4"
            }
        ],
        "sdgs": "SDG 7 (Affordable and Clean Energy), SDG 9 (Industry, Innovation, and Infrastructure)",
        "description": "Special topic elective expanding technical breadth in emerging electrical engineering practices, renewable energy systems, microgrid design, battery energy storage systems (BESS), or AI in power system operations.",
        "topics": [
            "Specialized Technical Seminars in Emerging Electrical Engineering Systems",
            "Investigation of Advanced Tools, Technologies, and Modern Engineering Software",
            "Technical Report Preparation, Case Study Analysis, and Engineering Seminar Presentation"
        ]
    }
]
