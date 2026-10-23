# USeP OBE Syllabus Creator & Consolidated Class Record Generator

An Outcomes-Based Education (OBE) management system tailored for the University of Southeastern Philippines (USeP) College of Engineering. Integrates syllabus drafting, measurement rubric creation, official multi-tier sequential approval workflow, consolidated class record computation, and automated PDF/Excel report exports.

---

## 🌟 Key Features

### 1. Syllabus Creator Studio (FM-USeP-MID-01)
- **Part I & II:** Course details with cascading College $\rightarrow$ Department $\rightarrow$ Course Code with auto-filled descriptions and credit units based on CMO 88 s. 2017 (BS Electrical Engineering).
- **Outcomes Alignment:** Full mapping from Institutional Graduate Attributes (IGAs), Program Educational Objectives (PEOs), Program Graduate Outcomes (PGOs), and Performance Indicators (PIs) to Course Learning Outcomes (CLOs).
- **Part V:** Course learning outline, prerequisites/co-requisites, and UN Sustainable Development Goals (SDG) alignment table.
- **Part VI:** Formative (FA) and Summative (SA) assessment tasks table linked directly to class record setup.
- **Part VII (Measurement System):** Dynamic rubric builder allowing faculty to add/remove/reorder criteria rows and performance rating level columns, choose graded assessment portions, and apply 1-click scale presets.
- **Part VIII:** Grading system and assessment plan distribution with Base-50 transmutation and passing cutoff conditions.

### 2. Multi-Stage Sequential Approval Workflow & Review Portal
- **Sequential 4-Tier Approval:**
  1. **Syllabus Review Committee:** Evaluates syllabus using the official 19-statement review checklist (*FM-USeP-MID-02*).
  2. **Program Head:** Endorses and recommends approval.
  3. **College QA Head:** Countersigns the syllabus (required prior to Dean's review).
  4. **College Dean:** Final approval and lock-in, unlocking the Class Record for grade recording.
- **Committee Composition Selection:** Faculty selects at least three (3) review committee members (Chair and Evaluators) with real-time notification dispatch.
- **Requests for Approval Portal:** Dedicated tab with active notification badges, action-required queue, and live status tracking for faculty.
- **Electronic Signatures & Timestamps:** Captures digital signature stamps, signatory credentials, and verified date & timestamps across all workflow steps and PDF outputs.

### 3. Consolidated Class Record & OBE Assessment
- **Per-CLO Score Input:** Assessments with multiple aligned CLOs provide distinct score inputs per CLO for granular attainment assessment.
- **Transmutation & Base-50:** Automated transmutation from raw scores to official USeP grade equivalents (1.00 to 5.00).
- **Interactive Dashboard:** Student performance heatmaps, class assessment averages, and CLO attainment vs target standards.

### 4. Official Exports
- **Syllabus PDF (FM-USeP-MID-01):** Landscape layout with full tables, Part VII rubrics, and official signature blocks.
- **Evaluation Form PDF (FM-USeP-MID-02):** Official checklist report with findings, recommendations, and committee signatures.
- **CLO Assessment Report PDF:** Official batch and student outcome attainment summary.
- **Excel Class Record (.xlsm):** Formatted spreadsheet matching the university template.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Dependencies listed in `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Run the Application
```bash
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 👥 Default Accounts (Role Switcher Available in UI)

| Username | Default Password | Role / Designation |
| :--- | :--- | :--- |
| `admin` | `admin123` | System Administrator (Full Access) |
| `faculty_tano` | `password123` | Faculty in Charge (Instructor) |
| `committee_basan` | `password123` | Syllabus Review Committee Chair |
| `committee_arenga` | `password123` | Syllabus Review Committee Member |
| `committee_ravida` | `password123` | Syllabus Review Committee Member |
| `programhead_claro` | `password123` | Program Head - Electrical Engineering |
| `qahead_ce` | `password123` | College Quality Assurance Head |
| `dean_cataytay` | `password123` | Dean, College of Engineering |
