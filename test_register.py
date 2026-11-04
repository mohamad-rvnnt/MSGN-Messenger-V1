import urllib.request
import urllib.error
import json
import getpass

BASE = "https://msgn-messenger.i-mohamadsgn.workers.dev"

username = input("Username: ").strip()
password = getpass.getpass("Password: ")

if len(password) < 10:
    raise SystemExit("Password must be at least 10 characters.")

data = json.dumps({
    "username": username,
    "password": password
}).encode("utf-8")

req = urllib.request.Request(
    BASE + "/register",
    data=data,
    headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-J600G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://msgn-messenger.i-mohamadsgn.workers.dev"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=30) as response:
        print("\nHTTP:", response.status)
        print(response.read().decode("utf-8", "replace"))
except urllib.error.HTTPError as e:
    print("\nHTTP:", e.code)
    print(e.read().decode("utf-8", "replace"))
except Exception as e:
    print("\nERROR:", repr(e))
