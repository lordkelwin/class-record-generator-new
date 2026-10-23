import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app, courses_store

client = app.app.test_client()
with client.session_transaction() as sess:
    sess["username"] = "faculty_tano"

# 1. Create a draft test course
test_course = courses_store.create_course(
    "faculty_tano",
    course_code="AEE 321",
    course_title="Feedback and Control Systems",
    section="EE 3A-TEST",
    semester_ay="1st Semester, A.Y. 2026-2027",
    from_catalog=False
)
c_id = test_course["id"]
print(f"Created temporary draft course: {c_id}")

try:
    # 2. Fetch course via client
    res = client.get(f"/api/courses/{c_id}")
    assert res.status_code == 200
    course_data = res.get_json()
    bp = course_data["blueprint"]
    print(f"Initial rubrics count: {len(bp.get('rubrics', []))}")

    # 3. Add dynamic custom rubric: 4 custom columns (levels) and 4 custom rows (criteria)
    custom_rubric = {
        "id": "rub_dynamic_test",
        "assessment_code": "SA1",
        "target_part": "Design Problem Section (Part B)",
        "title": "SA1: Engineering Design & Calculation Rubric",
        "scale_type": "custom",
        "levels": [
            {"level": 4, "label": "Exemplary (4 pts / 100%)"},
            {"level": 3, "label": "Competent (3 pts / 85%)"},
            {"level": 2, "label": "Developing (2 pts / 70%)"},
            {"level": 1, "label": "Beginning (1 pt / 50%)"}
        ],
        "criteria": [
            {
                "name": "System Modeling & Governing Equations",
                "clo": "CLO 2",
                "weight": 25,
                "descriptors": [
                    "Formulates complete, exact mathematical models with correct boundary conditions.",
                    "Formulates standard models with minor algebraic approximations.",
                    "Formulates incomplete models with several missing parameters.",
                    "Unable to formulate mathematical model."
                ]
            },
            {
                "name": "Circuit Analysis & Node Formulations",
                "clo": "CLO 2",
                "weight": 25,
                "descriptors": [
                    "Rigorous KVL/KCL and matrix state-space formulations without error.",
                    "Accurate formulation with minor arithmetic slip.",
                    "Frequent sign and node reference errors.",
                    "Incorrect circuit topological formulation."
                ]
            },
            {
                "name": "Safety Factor & Component Sizing",
                "clo": "CLO 3",
                "weight": 30,
                "descriptors": [
                    "Standard-compliant component sizing with thorough thermal and safety margins.",
                    "Correct component selection with adequate safety rating.",
                    "Marginal component ratings without derating factors.",
                    "Violates standard ratings or hazardous component selection."
                ]
            },
            {
                "name": "Validation & Simulation Synthesis",
                "clo": "CLO 3",
                "weight": 20,
                "descriptors": [
                    "Comprehensive waveform and transient analysis with numerical convergence check.",
                    "Simulation aligns with analytical values within 5% tolerance.",
                    "Divergent simulation results without troubleshooting.",
                    "No validation attempted."
                ]
            }
        ]
    }

    bp["rubrics"].append(custom_rubric)

    # 4. Save course blueprint via PUT API
    save_res = client.put(f"/api/courses/{c_id}", json=course_data)
    assert save_res.status_code == 200, f"Failed to save course: {save_res.data}"
    print("Successfully saved draft course with dynamic custom rubric!")

    # 5. Verify persistence
    verify_res = client.get(f"/api/courses/{c_id}")
    saved_rubrics = verify_res.get_json()["blueprint"]["rubrics"]
    dyn_rub = next((r for r in saved_rubrics if r.get("id") == "rub_dynamic_test"), None)
    assert dyn_rub is not None, "Saved dynamic rubric not found in blueprint!"
    assert len(dyn_rub["levels"]) == 4, f"Expected 4 levels, got {len(dyn_rub['levels'])}"
    assert len(dyn_rub["criteria"]) == 4, f"Expected 4 criteria, got {len(dyn_rub['criteria'])}"
    assert dyn_rub["target_part"] == "Design Problem Section (Part B)"
    print("Verification passed: 4 levels and 4 criteria persisted accurately with target portion.")

    # 6. Test PDF generation with dynamic rubric
    pdf_res = client.get(f"/api/courses/{c_id}/export-pdf")
    assert pdf_res.status_code == 200, f"PDF export failed: {pdf_res.status_code}"
    assert len(pdf_res.data) > 10000, f"PDF size too small: {len(pdf_res.data)}"
    print(f"Landscape syllabus PDF generated successfully with dynamic rubrics: {len(pdf_res.data):,} bytes.")

    print(">>> DYNAMIC RUBRICS API & PDF VERIFICATION TEST PASSED! <<<")

finally:
    # 7. Clean up test course
    courses_store.delete_course("faculty_tano", c_id)
    print(f"Deleted temporary test course: {c_id}")
