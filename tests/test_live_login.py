import urllib.request
import urllib.parse
import http.cookiejar
import re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# GET /login
resp = opener.open("http://127.0.0.1:5000/login")
html = resp.read().decode("utf-8")
m = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
csrf_token = m.group(1)

# POST /login
post_data = urllib.parse.urlencode({
    "username": "admin",
    "password": "admin123",
    "_csrf": csrf_token
}).encode("utf-8")

req = urllib.request.Request("http://127.0.0.1:5000/login", data=post_data, method="POST")
resp = opener.open(req)
final_url = resp.geturl()
final_html = resp.read().decode("utf-8")

print("Final URL:", final_url)
print("Contains 'System Administrator'?:", "System Administrator" in final_html or "Manage Users" in final_html)
assert "login" not in final_url, "Login failed!"
print(">>> Live server login check PASSED! <<<")
