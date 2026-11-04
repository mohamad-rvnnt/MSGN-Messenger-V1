import urllib.request
import urllib.error
import json
import getpass

BASE = "https://msgn-messenger.i-mohamadsgn.workers.dev"

username = input("Username: ").strip()
password = getpass.getpass("Password: ")

data = json.dumps({
    "username": username,
    "password": password
}).encode()

req = urllib.request.Request(
    BASE + "/login",
    data=data,
    headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-J600G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json",
        "Origin": BASE
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode())
        print("\nHTTP:", r.status)
        print("Response:", json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("token"):
            print("\nLOGIN TOKEN RECEIVED: YES")
        else:
            print("\nLOGIN TOKEN RECEIVED: NO")
except urllib.error.HTTPError as e:
    print("\nHTTP:", e.code)
    print(e.read().decode("utf-8", "replace"))
