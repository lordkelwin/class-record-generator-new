import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import courses_store
import syllabus_workflow

client = app.app.test_client()

print("--- 1. Setup Active Course for Testing ---")
with client.session_transaction() as sess:
    sess["username"] = "faculty_tano"

# Create dedicated temporary course for testing approval actions
test_course = courses_store.create_course("faculty_tano", course_code="EE 399", course_title="Temporary Test Approval Subject", section="EE 3A")
c_id = test_course["id"]
print("Testing course ID:", c_id)

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

# 1. Faculty submits syllabus
res = client.post(f"/api/courses/{c_id}/workflow/submit", json={
    "committee_members": [
        {"username": "faculty_basan", "name": "Engr. Nikka Samantha A. Basan", "role": "Review Committee Member"},
        {"username": "faculty_arenga", "name": "Engr. Delan Zoe H. Arenga", "role": "Review Committee Member"},
        {"username": "faculty_ravida", "name": "Engr. Kim P. Ravida", "role": "Review Committee Chair"}
    ]
})
print("STATUS:", res.status_code, res.get_json())
assert res.status_code == 200
print("Course submitted for review.")

# 2. Check requests endpoint for Review Committee member (Engr. Basan)
print("\n--- 2. Verify Approval Requests Visibility for Committee ---")
with client.session_transaction() as sess:
    sess["username"] = "faculty_basan"

res = client.get("/api/workflow/requests")
print("STATUS:", res.status_code, res.get_json())
assert res.status_code == 200
reqs = res.get_json()
pending_ids = [c["id"] for c in reqs.get("pending_action_for_me", [])]
assert c_id in pending_ids, f"Expected {c_id} in pending_action_for_me"
req_item = next(c for c in reqs["pending_action_for_me"] if c["id"] == c_id)
assert req_item["user_can_act"] is True
print("Verified user_can_act is TRUE for Review Committee member (Engr. Basan)!")

# 3. Test Fill Review Checklist
print("\n--- 3. Test Fill Review Checklist (FM-USeP-MID-02) ---")
res = client.get(f"/api/courses/{c_id}/evaluation-form")
print("STATUS:", res.status_code, res.get_json())
assert res.status_code == 200
eval_data = res.get_json()
assert eval_data["is_reviewer"] is True
assert eval_data["is_locked_for_user"] is False

# Save checklist
res = client.put(f"/api/courses/{c_id}/evaluation-form", json={
    "responses": {"core_1": "PARTIALLY", "int_cdio": "FULLY"},
    "comments": {"core_1": "Assessment tasks need more rubrics."},
    "recommendations": "Add criteria for laboratory components.",
    "overall_recommendation": "Revise and Resubmit"
})
print("STATUS:", res.status_code, res.get_json())
assert res.status_code == 200, f"Checklist save failed: {res.get_json()}"
print("Verified Review Checklist saved successfully by Committee Member!")

# 4. Test Return for Revision (without needing signature)
print("\n--- 4. Test Return for Revision ---")
res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "return",
    "remarks": "Please address observations in Part VII rubrics.",
})
print("STATUS:", res.status_code, res.get_json())
assert res.status_code == 200, f"Return failed: {res.get_json()}"
wf = res.get_json()["workflow"]
assert wf["status"] == "returned"
assert wf["cycle"] == 2
print(f"Verified Return for Revision successful! Status: {wf['status']}, Cycle: {wf['cycle']}")

# 5. Faculty sees returned course, can edit and resubmit
print("\n--- 5. Verify Faculty sees Returned status and can Resubmit ---")
with client.session_transaction() as sess:
    sess["username"] = "faculty_tano"

res = client.get(f"/api/courses/{c_id}/workflow")
wf = res.get_json()
assert wf["status"] == "returned"
assert wf["can_submit"] is True

# Resubmit
res = client.post(f"/api/courses/{c_id}/workflow/submit", json={
    "submission_notes": "Revised rubric criteria as requested."
})
print("STATUS:", res.status_code, res.get_json())
assert res.status_code == 200
print("Verified Faculty successfully resubmitted course after revision!")

# 6. Committee Signs & Approves
print("\n--- 6. Test Sign & Approve through Workflow ---")
# Member 1: Arenga
with client.session_transaction() as sess:
    sess["username"] = "faculty_arenga"

res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Member 1 approved.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
})
assert res.status_code == 200

# Member 2: Basan
with client.session_transaction() as sess:
    sess["username"] = "faculty_basan"

res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Member 2 approved.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
})
assert res.status_code == 200
wf = res.get_json()["workflow"]
assert wf["status"] == "for_committee_chair"

# Chair: Ravida
with client.session_transaction() as sess:
    sess["username"] = "faculty_ravida"

res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "All revisions satisfactory. Approved.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
})
assert res.status_code == 200
wf = res.get_json()["workflow"]
assert wf["status"] == "for_program_head"
print("Verified Committee Sign & Approve forwarded to Program Head!")

# 7. Program Head Signs & Endorses
print("\n--- 7. Test Program Head Endorsement ---")
with client.session_transaction() as sess:
    sess["username"] = "faculty_claro"

res = client.post(f"/api/courses/{c_id}/workflow/sign", json={
    "decision": "approve",
    "remarks": "Endorsed for QA review.",
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
})
print("STATUS:", res.status_code, res.get_json())
assert res.status_code == 200
wf = res.get_json()["workflow"]
assert wf["status"] == "for_qa_countersign"
print("Verified Program Head Sign & Endorse forwarded to QA Countersign!")

courses_store.delete_course("faculty_tano", c_id)
print("Cleaned up temporary test course:", c_id)
print("\n>>> ALL APPROVAL REQUEST ACTIONS (CHECKLIST, SIGN & APPROVE, RETURN FOR REVISION) PASSED! <<<")
