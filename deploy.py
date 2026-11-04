import json
import getpass
import urllib.request
import urllib.error
import secrets
from pathlib import Path
from datetime import datetime

ACCOUNT = "99d29e358ddf8727652881de4b34cc40"
WORKER = "msgn-messenger"
DB_ID = "f17a6128-4857-42d7-8d4c-e2a106f00f15"

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "worker/src/worker.js"

def request(url, token, method="GET", data=None, headers=None):
    h = {"Authorization": "Bearer " + token}
    if headers:
        h.update(headers)

    req = urllib.request.Request(
        url, data=data, headers=h, method=method
    )

    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def main():
    print("\n===== MSGN // NECRO DEPLOY =====")

    if not SOURCE.is_file():
        raise RuntimeError("Worker source not found.")

    code = SOURCE.read_bytes()
    source_text = code.decode("utf-8")

    if "export default" not in source_text:
        raise RuntimeError("Invalid Module Worker entry point.")

    if "iterations: 100000" not in source_text:
        raise RuntimeError("PBKDF2 setting is not 100000.")

    if "310000" in source_text:
        raise RuntimeError("Old PBKDF2 setting still exists.")

    token = getpass.getpass("\nCloudflare API Token: ")

    base = (
        "https://api.cloudflare.com/client/v4/accounts/"
        + ACCOUNT + "/workers/scripts/" + WORKER
    )

    print("\n[1/4] Reading current Worker settings...")

    raw = request(base + "/settings", token)
    settings = json.loads(raw)

    if not settings.get("success"):
        raise RuntimeError("Could not read Worker settings.")

    current = settings["result"]
    bindings = current.get("bindings", [])

    db = next(
        (b for b in bindings
         if b.get("name") == "DB" and b.get("type") == "d1"),
        None
    )

    if not db or db.get("database_id") != DB_ID:
        raise RuntimeError("D1 binding verification failed.")

    secret = next(
        (b for b in bindings
         if b.get("name") == "TOKEN_SECRET"),
        None
    )

    if not secret:
        raise RuntimeError("TOKEN_SECRET binding not found.")

    if secret.get("type") != "plain_text" or not secret.get("text"):
        raise RuntimeError(
            "TOKEN_SECRET is not readable as plain_text. "
            "Deployment stopped to protect existing configuration."
        )

    metadata = {
        "main_module": "worker.js",
        "compatibility_date": current.get(
            "compatibility_date", "2026-11-04"
        ),
        "bindings": bindings
    }

    for key in (
        "compatibility_flags",
        "usage_model",
        "logpush",
        "tail_consumers",
        "placement",
        "limits",
        "tags"
    ):
        if key in current:
            metadata[key] = current[key]

    print("[2/4] Configuration verified.")
    print("Worker:", WORKER)
    print("Database: DB -> msgn-messenger-db")
    print("Secret binding: preserved (value hidden)")
    print("Compatibility:", metadata["compatibility_date"])

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = SOURCE.with_name("workes.js.predeploy_" + stamp)
    backup.write_bytes(code)

    meta_backup = ROOT / ("deploy_metadata_" + stamp + ".json")
    safe_metadata = dict(metadata)
    safe_metadata["bindings"] = [
        {k: v for k, v in b.items() if k != "text"}
        for b in bindings
    ]
    meta_backup.write_text(
        json.dumps(safe_metadata, indent=2),
        encoding="utf-8"
    )

    print("[3/4] Local backup created:", backup.name)

    print("\n===== DEPLOY PREVIEW =====")
    print("Source: worker/src/worker.js")
    print("Size:", len(code), "bytes")
    print("Bindings:", len(bindings))
    print("No database migration will be executed.")

    confirm = input(
        "\nType DEPLOY to publish this Worker: "
    ).strip()

    if confirm != "DEPLOY":
        print("Deployment cancelled. No remote changes made.")
        return

    print("\n[4/4] Uploading Worker...")

    boundary = "----MSGN" + secrets.token_hex(16)

    body = bytearray()

    body.extend(
        ("--" + boundary + "\r\n").encode()
    )
    body.extend(
        b'Content-Disposition: form-data; name="metadata"\r\n'
    )
    body.extend(b"Content-Type: application/json\r\n\r\n")
    body.extend(json.dumps(metadata).encode("utf-8"))
    body.extend(b"\r\n")

    body.extend(
        ("--" + boundary + "\r\n").encode()
    )
    body.extend(
        b'Content-Disposition: form-data; name="worker.js"; '
        b'filename="worker.js"\r\n'
    )
    body.extend(
        b"Content-Type: application/javascript+module\r\n\r\n"
    )
    body.extend(code)
    body.extend(b"\r\n")

    body.extend(
        ("--" + boundary + "--\r\n").encode()
    )

    result_raw = request(
        base,
        token,
        method="PUT",
        data=bytes(body),
        headers={
            "Content-Type": "multipart/form-data; boundary=" + boundary
        }
    )

    result = json.loads(result_raw)

    if not result.get("success"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        raise RuntimeError("Cloudflare rejected deployment.")

    info = result.get("result", {})

    print("\n================================")
    print("       DEPLOY SUCCESSFUL")
    print("================================")
    print("Worker:", info.get("id", WORKER))
    print("Startup time:", info.get("startup_time_ms"))
    print("Backup:", backup.name)
    print("\nNext: test /health and registration.")

if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        print("\nHTTP ERROR:", e.code)
        print(e.read().decode("utf-8", "replace"))
    except Exception as e:
        print("\nERROR:", str(e))
