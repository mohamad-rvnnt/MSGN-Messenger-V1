#!/usr/bin/env python3

import os
import sys
import json
import time
import re
import getpass
import hashlib
import urllib.request
import urllib.error
import select
import termios
import tty
import shutil
import unicodedata
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    TEHRAN = ZoneInfo("Asia/Tehran")
except Exception:
    TEHRAN = timezone(timedelta(hours=3, minutes=30))

API = os.environ.get(
    "MSGN_API",
    "https://msgn-messenger.i-mohamadsgn.workers.dev"
).rstrip("/")

HOME = os.path.expanduser("~")
TF = HOME + "/.msgn_token"
UF = HOME + "/.msgn_user"

R = "\033[0m"
C = "\033[96m"
G = "\033[92m"
Y = "\033[93m"
X = "\033[91m"
B = "\033[1m"
M = "\033[95m"
DIM = "\033[2m"
WHITE = "\033[97m"
BLINK = "\033[5m"

USER_COLORS = [
    "\033[91m",
    "\033[92m",
    "\033[93m",
    "\033[94m",
    "\033[95m",
    "\033[96m",
    "\033[97m",
    "\033[38;5;208m",
    "\033[38;5;45m",
    "\033[38;5;141m",
    "\033[38;5;118m",
    "\033[38;5;220m",
]

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None


def display(text):
    text = str(text)

    if arabic_reshaper and get_display:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            pass

    return text


def clear():
    print("\033[2J\033[H", end="", flush=True)


def banner():
    print(C + B)
    print("╭────────────────────────────────────────────╮")
    print("│             MSGN // NECRO                  │")
    print("│              MESSENGER 1.1                 │")
    print("│                 m_sgn                      │")
    print("╰────────────────────────────────────────────╯")
    print(R)

    print(M + B + BLINK +
          "  RevenanT never fades. It always returns." +
          R)

    print(
        Y + BLINK + B + "                 @m_sgn" + R
    )
    print()


def api(path, method="GET", data=None, token=None):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; SM-J600G) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json",
        "Origin": API
    }

    if token:
        headers["Authorization"] = "Bearer " + token

    payload = None

    if data is not None:
        payload = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

    req = urllib.request.Request(
        API + path,
        data=payload,
        headers=headers,
        method=method
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"error": str(e)}

    except Exception as e:
        return {"error": "Connection: " + str(e)}


def credentials():
    try:
        with open(TF) as f:
            token = f.read().strip()

        with open(UF) as f:
            username = f.read().strip()

        return token, username

    except Exception:
        return None, None


def save_credentials(token, username):
    for path, value in ((TF, token), (UF, username)):
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600
        )

        with os.fdopen(fd, "w") as f:
            f.write(value)


def logout():
    for path in (TF, UF):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def pause():
    input("\nPress Enter to continue...")


def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)

        if ch == b"\x1b":
            seq = os.read(fd, 2)

            if seq == b"[A":
                return "UP"
            if seq == b"[B":
                return "DOWN"
            if seq == b"[C":
                return "RIGHT"
            if seq == b"[D":
                return "LEFT"

            return "ESC"

        if ch in (b"\r", b"\n"):
            return "ENTER"

        if ch == b"\x03":
            return "CTRL_C"

        if ch == b"\x7f":
            return "BACKSPACE"

        return ch.decode("utf-8", "ignore")

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def menu(title, options):
    selected = 0

    while True:
        clear()
        banner()

        print(B + C + title + R)
        print("─" * 44)

        for i, item in enumerate(options):
            if i == selected:
                print(G + "  ❯ " + B + item + R)
            else:
                print("    " + item)

        print("\n" + DIM + "Use UP / DOWN and ENTER" + R)

        key = get_key()

        if key == "UP":
            selected = (selected - 1) % len(options)

        elif key == "DOWN":
            selected = (selected + 1) % len(options)

        elif key == "ENTER":
            return selected

        elif key == "CTRL_C":
            return len(options) - 1


def register():
    clear()
    banner()

    print(B + C + "CREATE ACCOUNT" + R)
    print()

    username = input("Username: ").strip()

    if not re.fullmatch(r"[a-z]{5,20}", username):
        print(X + "Username must be 5-20 lowercase English letters." + R)
        pause()
        return

    password = getpass.getpass("Password: ")

    if not re.fullmatch(
        r"(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])[A-Za-z0-9]{8}",
        password
    ):
        print(X + "Password must be exactly 8 characters." + R)
        pause()
        return

    result = api(
        "/register",
        "POST",
        {
            "username": username,
            "password": password
        }
    )

    if result.get("ok"):
        print(G + "Account created successfully." + R)
    else:
        print(X + result.get("error", "Registration failed.") + R)

    pause()


def login():
    clear()
    banner()

    print(B + C + "LOGIN" + R)
    print()

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    result = api(
        "/login",
        "POST",
        {
            "username": username,
            "password": password
        }
    )

    if result.get("token"):
        save_credentials(
            result["token"],
            result["username"]
        )

        print(G + "Login successful." + R)
        time.sleep(0.7)

        return True

    print(X + result.get("error", "Login failed.") + R)
    pause()

    return False


def user_color(username):
    digest = hashlib.sha256(
        username.encode("utf-8")
    ).digest()

    index = digest[0] % len(USER_COLORS)

    return USER_COLORS[index]


def jalali_date(gy, gm, gd):
    g_days = [
        31, 28, 31, 30, 31, 30,
        31, 31, 30, 31, 30, 31
    ]

    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    day_no = (
        365 * gy2
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
    )

    for i in range(gm2):
        day_no += g_days[i]

    if gm2 > 1 and (
        gy % 4 == 0 and
        (gy % 100 != 0 or gy % 400 == 0)
    ):
        day_no += 1

    day_no += gd2
    day_no -= 79

    j_np = day_no // 12053
    day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (day_no // 1461)
    day_no %= 1461

    if day_no >= 366:
        jy += (day_no - 1) // 365
        day_no = (day_no - 1) % 365

    if day_no < 186:
        jm = 1 + day_no // 31
        jd = 1 + day_no % 31
    else:
        jm = 7 + (day_no - 186) // 30
        jd = 1 + (day_no - 186) % 30

    return jy, jm, jd


def persian_timestamp(value):
    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        dt = dt.astimezone(TEHRAN)

        jy, jm, jd = jalali_date(
            dt.year,
            dt.month,
            dt.day
        )

        return (
            f"{jy:04d}/{jm:02d}/{jd:02d}"
            f"  {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
        )

    except Exception:
        return "Unknown date"


def width(text):
    total = 0

    for ch in text:
        if unicodedata.combining(ch):
            continue

        total += (
            2 if unicodedata.east_asian_width(ch) in ("W", "F")
            else 1
        )

    return total


def wrap_text(text, max_width):
    lines = []
    current = ""
    current_width = 0

    for ch in text:
        ch_width = (
            2 if unicodedata.east_asian_width(ch) in ("W", "F")
            else 1
        )

        if current and current_width + ch_width > max_width:
            lines.append(current)
            current = ""
            current_width = 0

        current += ch
        current_width += ch_width

    if current:
        lines.append(current)

    return lines or [""]


def fetch_initial(token, room_id):
    result = api(
        f"/messages?room_id={room_id}&limit=50",
        token=token
    )

    if result.get("error"):
        return None, result

    return result.get("messages", []), result


def fetch_new(token, room_id, last_id):
    return api(
        f"/messages?room_id={room_id}&after={last_id}&limit=80",
        token=token
    )


def fetch_older(token, room_id, first_id):
    return api(
        f"/messages?room_id={room_id}&before={first_id}&limit=50",
        token=token
    )


def send_message(token, room_id, message):
    return api(
        "/messages",
        "POST",
        {
            "room_id": room_id,
            "message": message
        },
        token
    )


def get_room(token):
    result = api("/rooms", token=token)

    if result.get("error"):
        return None

    rooms = result.get("rooms", [])

    if not rooms:
        return None

    return rooms[0]


def render_chat(messages, username, offset=0):
    clear()
    banner()

    size = shutil.get_terminal_size((80, 24))
    terminal_width = size.columns
    terminal_height = size.lines

    print(G + B + "PUBLIC CHAT" + R)
    print(C + "Logged in as: " + B + username + R)
    print(DIM + "ONLINE SYNC: ACTIVE  |  INTERVAL: 1s" + R)
    print("─" * min(terminal_width, 70))

    available = max(3, terminal_height - 15)

    end = max(0, len(messages) - offset)
    start = max(0, end - available)

    visible = messages[start:end]

    for msg in visible:
        name = msg.get("username", "?")
        content = display(msg.get("message", ""))
        timestamp = persian_timestamp(
            msg.get("created_at", "")
        )

        color = user_color(name)

        if name == username:
            marker = G + "YOU" + R
        else:
            marker = DIM + "USER" + R

        print(
            color + B + "@" + name + R
            + "  " + marker
        )

        for line in wrap_text(
            content,
            max(20, terminal_width - 5)
        ):
            print("  " + WHITE + line + R)

        print(
            "  " + DIM + "◷ " + timestamp + R
        )

        print()


    print("─" * min(terminal_width, 70))
    print(Y + "↑ Older messages | ↓ Newer messages" + R)
    print(DIM + "/exit  /refresh  /older  /newer" + R)
    print()


def redraw_input(username, raw):
    value = raw.decode("utf-8", "replace")

    print("\r\033[K", end="")
    print(
        G + username + "> " + R + display(value),
        end="",
        flush=True
    )


def chat(token, username, room):
    room_id = room["id"]

    messages, initial = fetch_initial(token, room_id)

    if messages is None:
        print(X + initial.get("error", "Cannot load messages.") + R)
        pause()
        return

    last_id = max(
        (m["id"] for m in messages),
        default=0
    )

    first_id = min(
        (m["id"] for m in messages),
        default=0
    )

    offset = 0
    last_poll = time.monotonic()
    poll_interval = 1.0

    while True:
        render_chat(messages, username, offset)

        print(G + username + "> " + R, end="", flush=True)

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        raw = bytearray()
        typing = True
        command = None

        try:
            tty.setcbreak(fd)

            while typing:
                ready, _, _ = select.select(
                    [fd],
                    [],
                    [],
                    0.20
                )

                if ready:
                    ch = os.read(fd, 1)

                    if ch in (b"\n", b"\r"):
                        print()
                        typing = False
                        break

                    if ch == b"\x03":
                        command = "/exit"
                        print()
                        typing = False
                        break

                    if ch == b"\x7f":
                        if raw:
                            raw.pop()

                            while raw and (
                                raw[-1] & 0xC0
                            ) == 0x80:
                                raw.pop()

                            redraw_input(username, raw)

                        continue

                    if ch == b"\x1b":
                        if select.select([fd], [], [], 0.03)[0]:
                            seq = os.read(fd, 2)

                            if seq == b"[A":
                                command = "/older"
                                typing = False
                                break

                            if seq == b"[B":
                                command = "/newer"
                                typing = False
                                break

                        continue

                    raw.extend(ch)

                    try:
                        raw.decode("utf-8")
                        redraw_input(username, raw)
                    except UnicodeDecodeError:
                        pass

                # AUTOMATIC ONLINE SYNC
                if time.monotonic() - last_poll >= poll_interval:
                    result = fetch_new(
                        token,
                        room_id,
                        last_id
                    )

                    if not result.get("error"):
                        new_messages = result.get("messages", [])

                        if new_messages:
                            known = {
                                m["id"] for m in messages
                            }

                            added = False

                            for msg in new_messages:
                                if msg["id"] not in known:
                                    messages.append(msg)
                                    known.add(msg["id"])
                                    added = True

                            last_id = max(
                                last_id,
                                max(m["id"] for m in new_messages)
                            )

                            if added:
                                render_chat(
                                    messages,
                                    username,
                                    offset
                                )

                                redraw_input(
                                    username,
                                    raw
                                )

                    last_poll = time.monotonic()

            termios.tcsetattr(
                fd,
                termios.TCSADRAIN,
                old
            )

        except Exception:
            termios.tcsetattr(
                fd,
                termios.TCSADRAIN,
                old
            )
            return

        text = (
            command if command is not None
            else raw.decode("utf-8", "replace").strip()
        )

        if text == "/exit":
            return

        if text == "/refresh":
            continue

        if text in ("/older",):
            if first_id > 0:
                result = fetch_older(
                    token,
                    room_id,
                    first_id
                )

                if not result.get("error"):
                    older = result.get("messages", [])

                    if older:
                        known = {
                            m["id"] for m in messages
                        }

                        older = [
                            m for m in older
                            if m["id"] not in known
                        ]

                        messages = older + messages

                        first_id = min(
                            (m["id"] for m in messages),
                            default=first_id
                        )

                        offset += 5

            continue

        if text == "/newer":
            offset = max(0, offset - 5)
            continue

        if text:
            result = send_message(
                token,
                room_id,
                text
            )

            if not result.get("ok"):
                print(
                    X + result.get("error", "Send failed.") + R
                )
                time.sleep(1)

            else:
                new = fetch_new(
                    token,
                    room_id,
                    last_id
                )

                if not new.get("error"):
                    known = {
                        m["id"] for m in messages
                    }

                    for msg in new.get("messages", []):
                        if msg["id"] not in known:
                            messages.append(msg)
                            known.add(msg["id"])

                    if messages:
                        last_id = max(
                            m["id"] for m in messages
                        )

                offset = 0


def main():
    while True:
        token, username = credentials()

        if token and username:
            selected = menu(
                "MSGN MAIN MENU",
                [
                    "Public Chat",
                    "Logout",
                    "Exit"
                ]
            )

            if selected == 0:
                room = get_room(token)

                if not room:
                    print(X + "Public room unavailable." + R)
                    pause()
                else:
                    chat(token, username, room)

            elif selected == 1:
                logout()

            else:
                break

        else:
            selected = menu(
                "MSGN MAIN MENU",
                [
                    "Register",
                    "Login",
                    "Exit"
                ]
            )

            if selected == 0:
                register()

            elif selected == 1:
                if login():
                    token, username = credentials()
                    room = get_room(token)

                    if room:
                        chat(token, username, room)
                    else:
                        print(X + "Public room unavailable." + R)
                        pause()

            else:
                break


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("\n" + Y + "MSGN // NECRO CLOSED" + R)
