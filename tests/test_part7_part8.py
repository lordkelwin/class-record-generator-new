import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app, courses_store

client = app.app.test_client()
with client.session_transaction() as sess:
    sess["username"] = "faculty_tano"

res = client.get("/api/courses")
assert res.status_code == 200, "Could not list courses"
c_id = res.get_json()["courses"][0]["id"]
print("Testing course ID:", c_id)

# Test GET course
res = client.get(f"/api/courses/{c_id}")
assert res.status_code == 200
bp = res.get_json()["blueprint"]
rubrics = bp.get("rubrics", [])
print(f"Course blueprint has {len(rubrics)} rubrics by default (should be empty):")
for r in rubrics:
    print(f" - {r.get('title')} (scale: {r.get('scale_type')}, criteria: {len(r.get('criteria', []))})")
assert len(rubrics) == 0, f"Expected 0 rubrics by default, got {len(rubrics)}"

# Test faculty creating their own custom rubric
custom_rubric = {
    "rubric_id": "rub_custom_fac_1",
    "title": "Custom Analytic Rubric",
    "assessment_code": "SA1",
    "target_part": "Entire Assessment",
    "used_for": "Faculty Defined Assessment",
    "clo_ids": ["CLO1"],
    "scale_type": "points_5",
    "levels": [
        {"level": 5, "label": "Excellent (5)"},
        {"level": 3, "label": "Satisfactory (3)"},
        {"level": 0, "label": "Unacceptable (0)"}
    ],
    "criteria": [
        {"name": "Accuracy", "weight_pct": 50.0, "descriptors": ["Exact", "Partial", "Wrong"]},
        {"name": "Clarity", "weight_pct": 50.0, "descriptors": ["Clear", "Adequate", "Unclear"]}
    ],
    "notes": "Faculty custom rubric"
}
bp["rubrics"] = [custom_rubric]
save_res = client.put(f"/api/courses/{c_id}", json={"blueprint": bp})
assert save_res.status_code == 200

# Test export PDF
res = client.get(f"/api/courses/{c_id}/export-pdf")
print("PDF Export status code:", res.status_code)
assert res.status_code == 200, f"PDF export failed: {res.status_code}"
assert len(res.data) > 10000, f"PDF too small: {len(res.data)} bytes"
print(f"PDF successfully generated: {len(res.data):,} bytes")

# Clean rubrics back to empty
bp["rubrics"] = []
client.put(f"/api/courses/{c_id}", json={"blueprint": bp})

print(">>> ALL TESTS PASSED SUCCESSFULLY! <<<")
