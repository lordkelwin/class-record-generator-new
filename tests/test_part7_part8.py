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
print(f"Course blueprint has {len(rubrics)} rubrics:")
for r in rubrics:
    print(f" - {r.get('title')} (scale: {r.get('scale_type')}, criteria: {len(r.get('criteria', []))})")
assert len(rubrics) >= 4, f"Expected at least 4 rubrics, got {len(rubrics)}"

# Test export PDF
res = client.get(f"/api/courses/{c_id}/export-pdf")
print("PDF Export status code:", res.status_code)
assert res.status_code == 200, f"PDF export failed: {res.status_code}"
assert len(res.data) > 10000, f"PDF too small: {len(res.data)} bytes"
print(f"PDF successfully generated: {len(res.data):,} bytes")

print(">>> ALL TESTS PASSED SUCCESSFULLY! <<<")
