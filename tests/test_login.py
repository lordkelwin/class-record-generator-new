import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import app

c = app.app.test_client()
r = c.get("/login")
assert r.status_code == 200, f"Expected 200 from /login, got {r.status_code}"
m = re.search(r'name="_csrf"\s+value="([^"]+)"', r.text)
assert m, "CSRF token not found in /login"
csrf_token = m.group(1)

# Post login
login_res = c.post(
    "/login",
    data={
        "username": "admin",
        "password": "admin123",
        "_csrf": csrf_token,
    },
    follow_redirects=False,
)

print("Status Code:", login_res.status_code)
print("Location Header:", login_res.headers.get("Location"))
assert login_res.status_code == 302, f"Expected 302 redirect, got {login_res.status_code}"
assert login_res.headers.get("Location") in ("/", "http://localhost/"), f"Unexpected redirect: {login_res.headers.get('Location')}"

# Follow redirect and check landing page
landing_res = c.get(login_res.headers.get("Location"))
print("Landing Status Code:", landing_res.status_code)
assert "System Administrator" in landing_res.text or "Manage Users" in landing_res.text or "USeP OBE" in landing_res.text
print(">>> Admin login with credentials 'admin' / 'admin123' VERIFIED SUCCESSFULLY! <<<")
