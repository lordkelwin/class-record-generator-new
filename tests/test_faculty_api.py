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
print("Sample Review Committee members (sorted):")
for s in sigs['review_committee'][:6]:
    print(f"  - {s['full_name']} ({s['position_title']})")

# Test demo account switch to an official faculty (e.g. Sheena Arcega or Charito Claro or Tano)
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

print(">>> ALL FACULTY & SIGNATORY VERIFICATIONS PASSED! <<<")
