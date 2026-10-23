import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import courses_store
import syllabus_workflow

client = app.app.test_client()

print("--- 1. Testing Custom Committee Role Assignment ---")
with client.session_transaction() as sess:
    sess["username"] = "faculty_tano"

res = client.get("/api/courses")
c_id = res.get_json()["courses"][0]["id"]

# Reset course workflow to draft
doc = courses_store.find_course(c_id)
doc["workflow"] = syllabus_workflow.default_workflow()
courses_store.save_course_doc(doc)

# Submit with custom committee roles: Arenga is Chair, Basan is Member, Ravida is Member
custom_committee = [
    {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Member"},
    {"username": "faculty_arenga", "name": "Engr. Delan Zoe H. Arenga", "role": "Review Committee Chair"},
    {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Member"}
]

res = client.post(f"/api/courses/{c_id}/workflow/submit", json={
    "committee_members": custom_committee,
    "assigned_committee": "faculty_arenga",
    "assigned_committee_name": "Engr. Delan Zoe H. Arenga",
    "submission_notes": "Assigned Engr. Arenga as Review Committee Chair via role dropdown."
})

assert res.status_code == 200, f"Submit failed: {res.get_json()}"
wf = res.get_json()["workflow"]
assert wf["status"] == "for_committee_review"
assert wf["assigned_committee"] == "faculty_arenga", f"Expected faculty_arenga as assigned chair, got {wf['assigned_committee']}"
print("Successfully verified appointed Chair is faculty_arenga!")

# Verify committee members roles stored in workflow
members = wf["committee_members"]
assert len(members) == 3
assert members[0]["role"] == "Review Committee Member"
assert members[1]["role"] == "Review Committee Chair"
assert members[2]["role"] == "Review Committee Member"
print("Successfully verified stored roles:", [f"{m['name']}: {m['role']}" for m in members])

# Verify assigned chair can evaluate checklist
with client.session_transaction() as sess:
    sess["username"] = "faculty_arenga"

res = client.put(f"/api/courses/{c_id}/evaluation-form", json={
    "responses": {"core_1": "FULLY"},
    "overall_recommendation": "Approved"
})
assert res.status_code == 200, f"Chair evaluate failed: {res.get_json()}"
print("Successfully verified appointed Chair (Engr. Arenga) can evaluate checklist!")

# Export Evaluation PDF and verify PDF generates cleanly
res = client.get(f"/api/courses/{c_id}/export-evaluation-pdf")
assert res.status_code == 200
assert res.data.startswith(b"%PDF")
print(f"Successfully generated FM-USeP-MID-02 Evaluation PDF ({len(res.data)} bytes) with custom committee roles!")

print("\n>>> ALL COMMITTEE ROLE ASSIGNMENT TESTS PASSED! <<<")
