import urllib.request
import urllib.parse
import http.cookiejar
import json
import re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
html = opener.open("http://127.0.0.1:5000/login").read().decode("utf-8")
csrf = re.search(r'name="_csrf"\s+value="([^"]+)"', html).group(1)
post_data = urllib.parse.urlencode({
    "username": "admin",
    "password": "admin123",
    "_csrf": csrf
}).encode("utf-8")
opener.open("http://127.0.0.1:5000/login", data=post_data)

# Test /api/faculty-roster
resp = opener.open("http://127.0.0.1:5000/api/faculty-roster")
roster = json.loads(resp.read().decode("utf-8"))
print("Successfully fetched /api/faculty-roster!")
for prog, grp in roster.items():
    print(f"  {prog}: {len(grp['full_time'])} full-time, {len(grp['part_time'])} part-time")

# Test /api/workflow/signatories
resp2 = opener.open("http://127.0.0.1:5000/api/workflow/signatories")
sigs = json.loads(resp2.read().decode("utf-8"))
print(f"Review Committee signatories count: {len(sigs['review_committee'])}")
print(f"Program Heads count: {len(sigs['program_heads'])}")
print(f"Deans count: {len(sigs['deans'])}")

# Check Basan title
basan = next((s for s in sigs['review_committee'] if "Basan" in s['full_name']), None)
assert basan is not None, "Basan should be in signatories!"
assert basan['position_title'] == "Faculty Member", f"Basan title should be Faculty Member, got: {basan['position_title']}"
print(f"Verified Basan: {basan['full_name']} | Title: {basan['position_title']}")

# Test switch to Basan
switch_data_b = json.dumps({"username": "faculty_basan"}).encode("utf-8")
req_b = urllib.request.Request("http://127.0.0.1:5000/api/switch-demo-account", data=switch_data_b, headers={"Content-Type": "application/json"})
resp_b = opener.open(req_b)
b_user = json.loads(resp_b.read().decode("utf-8"))["user"]
assert b_user["position_title"] == "Faculty Member"

# Test switch to Sheena Arcega
switch_data = json.dumps({"username": "faculty_arcega"}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:5000/api/switch-demo-account", data=switch_data, headers={"Content-Type": "application/json"})
resp3 = opener.open(req)
switched_user = json.loads(resp3.read().decode("utf-8"))["user"]
print(f"Switched to: {switched_user['full_name']} | Has e-signature? {switched_user['has_signature']}")
assert switched_user["has_signature"] is True, "Sheena Arcega should have e-signature!"

# Test switch to Dean Cataytay
switch_data2 = json.dumps({"username": "dean_cataytay"}).encode("utf-8")
req2 = urllib.request.Request("http://127.0.0.1:5000/api/switch-demo-account", data=switch_data2, headers={"Content-Type": "application/json"})
resp4 = opener.open(req2)
dean_user = json.loads(resp4.read().decode("utf-8"))["user"]
print(f"Switched to: {dean_user['full_name']} | Has e-signature? {dean_user['has_signature']}")
assert dean_user["has_signature"] is True, "Dean Cataytay should have e-signature!"

# Verify Program Heads from updated document (without honorific titles)
head_names = [h['full_name'] for h in sigs['program_heads']]
expected_heads = [
    "Charito O. Claro",
    "Rosanna C. Ucat",
    "Randy B. Tongson",
    "Fillmore D. Masancay",
    "Mark John S. Pag-alaman",
    "Dean Lester P. Rejas",
    "Bonifacio T. Aznar Jr.",
    "Sheena S. Arcega",
    "Ruel Tuyogon"
]
for eh in expected_heads:
    assert any(eh in hn for hn in head_names), f"Expected program head {eh} not found in {head_names}"
print(f"All 9 official Program Heads verified in signatories: {expected_heads}")

# Verify no duplicate names in Review Committee or Program Heads
comm_names = [s['full_name'] for s in sigs['review_committee']]
assert len(comm_names) == len(set(comm_names)), f"Duplicates found in review committee: {[x for x in comm_names if comm_names.count(x) > 1]}"

head_names = [s['full_name'] for s in sigs['program_heads']]
assert len(head_names) == len(set(head_names)), f"Duplicates found in program heads: {[x for x in head_names if head_names.count(x) > 1]}"
print("Verified ZERO duplicates in review committee and program heads dropdown lists!")

# Verify Claro has no PECE
claro = next(s for s in sigs['program_heads'] if 'Claro' in s['full_name'])
assert 'PECE' not in claro['full_name'], f"Claro should not have PECE: {claro['full_name']}"
print(f"Verified Claro without PECE: {claro['full_name']}")


print(">>> ALL FACULTY & SIGNATORY VERIFICATIONS PASSED! <<<")
