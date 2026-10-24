import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import app
import courses_store
import syllabus_workflow

client = app.app.test_client()

print("--- 0. Setup clean course ---")
with client.session_transaction() as sess:
    sess["username"] = "faculty_tano"

res = client.get("/api/courses")
c_id = res.get_json()["courses"][0]["id"]
print("Active course ID:", c_id)

# Reset workflow to draft for testing
doc = courses_store.find_course(c_id)
doc["workflow"] = syllabus_workflow.default_workflow()
if not doc.get("blueprint"): doc["blueprint"] = {}
if not doc["blueprint"].get("metadata"): doc["blueprint"]["metadata"] = {}
doc["blueprint"]["metadata"]["course_description"] = "Comprehensive study of electrical networks."
doc["blueprint"]["metadata"]["syllabus_assessment_activities"] = [
    {"code": "FA1", "activity": "Seatwork", "weight_pct": 0, "type": "formative"},
    {"code": "SA1", "activity": "Quizzes", "weight_pct": 50, "type": "summative"},
    {"code": "SA2", "activity": "Exam", "weight_pct": 50, "type": "summative"}
]
courses_store.save_course_doc(doc)

print("\n--- 1. Faculty Submits Syllabus ---")
res = client.get(f"/api/courses/{c_id}/workflow")
wf = res.get_json()
print("Initial status:", wf["status"], "| can_submit?", wf["can_submit"])

# Submit
res = client.post(f"/api/courses/{c_id}/workflow/submit", json={
    "committee_members": [
        {"username": "faculty_arenga", "name": "Engr. Delan Zoe H. Arenga", "role": "Review Committee Member"},
        {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Member"},
        {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Chair"}
    ]
})
print("Submit status code:", res.status_code, res.get_json().get("message") or res.get_json().get("error"))

res = client.get(f"/api/courses/{c_id}/workflow")
wf = res.get_json()
print("Status after submit:", wf["status"])
assert wf["status"] == "for_committee_review", f"Expected for_committee_review, got {wf['status']}"

# Test lock: Faculty cannot save checklist
print("\n--- 2. Verify Committee Lock (Faculty cannot edit checklist) ---")
res = client.put(f"/api/courses/{c_id}/evaluation-form", json={"responses": {}})
print("Faculty PUT checklist status (expected 400):", res.status_code, res.get_json().get("error"))
assert res.status_code == 400

# Step 2: Review Committee Members
print("\n--- 3. Review Committee Members Sign ---")
with client.session_transaction() as sess:
    sess["username"] = "faculty_arenga"

# Save checklist
res = client.put(f"/api/courses/{c_id}/evaluation-form", json={
    "responses": {"core_1": "FULLY", "int_cdio": "FULLY"},
    "comments": {"core_1": "Complete and compliant."},
    "overall_recommendation": "Approved",
    "recommendations": "Syllabus meets all OBE and CMO standards.",
})
print("Committee save checklist:", res.status_code, res.get_json().get("message"))
assert res.status_code == 200

# Member 1 signs
res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Reviewed and fully endorsed by Member 1.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
})
assert res.status_code == 200

# Member 2 signs
with client.session_transaction() as sess:
    sess["username"] = "faculty_ravida"
res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Reviewed and fully endorsed by Member 2.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
})
assert res.status_code == 200

# Chair signs
with client.session_transaction() as sess:
    sess["username"] = "faculty_basan"
res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Chair endorsement.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
})
assert res.status_code == 200

res = client.get(f"/api/courses/{c_id}/workflow")
wf = res.get_json()
print("Status after committee sign:", wf["status"])
assert wf["status"] == "for_program_head"

# Step 3: Program Head
print("\n--- 4. Program Head (Engr. Claro) Endorsement ---")
with client.session_transaction() as sess:
    sess["username"] = "faculty_claro"

res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Endorsed for College QA review.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
})
print("Program Head sign response:", res.status_code, res.get_json().get("message"))
assert res.status_code == 200

res = client.get(f"/api/courses/{c_id}/workflow")
wf = res.get_json()
print("Status after Program Head sign:", wf["status"])
assert wf["status"] == "for_qa_countersign"

# Step 4: QA Head Countersign (Countersigns FIRST before Dean!)
print("\n--- 5. QA Head Countersign ---")
with client.session_transaction() as sess:
    sess["username"] = "qahead_ce"

res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Countersigned: QA audit complete.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
})
print("QA Head countersign response:", res.status_code, res.get_json().get("message"))
assert res.status_code == 200

res = client.get(f"/api/courses/{c_id}/workflow")
wf = res.get_json()
print("Status after QA countersign:", wf["status"])
assert wf["status"] == "for_dean_approval"

# Step 5: Dean Final Approval & Lock-in
print("\n--- 6. Dean (Dr. Cataytay) Final Approval & Lock-in ---")
with client.session_transaction() as sess:
    sess["username"] = "dean_cataytay"

res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Final approval granted. Syllabus locked.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
})
print("Dean approval response:", res.status_code, res.get_json().get("message"))
assert res.status_code == 200

res = client.get(f"/api/courses/{c_id}/workflow")
wf = res.get_json()
print("Final Status:", wf["status"], "| Approved?", wf["approved"], "| Locked?", wf["locked"])
assert wf["status"] == "approved"
assert wf["approved"] is True
assert wf["locked"] is True
assert len(wf["signatures"]) >= 4

# Step 7: Test PDF Exports
print("\n--- 7. Testing Official PDF Exports ---")
res = client.get(f"/api/courses/{c_id}/export-evaluation-pdf")
print("Evaluation PDF (FM-USeP-MID-02) export status:", res.status_code, "bytes:", len(res.data))
assert res.status_code == 200 and len(res.data) > 5000

res = client.get(f"/api/courses/{c_id}/export-pdf")
print("Syllabus PDF export status:", res.status_code, "bytes:", len(res.data))
assert res.status_code == 200 and len(res.data) > 5000

print("\n>>> ALL 7 STAGES OF THE SEQUENTIAL APPROVAL WORKFLOW PASSED WITH FLYING COLORS! <<<")
