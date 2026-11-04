# MSGN Messenger V1

Terminal-based chat client for Termux/Android (including ARM 32-bit) with a Cloudflare Workers + D1 backend.

## Features
- Account registration/login (PBKDF2 password hashing; signed expiring token)
- Public room, groups, direct messages
- Terminal UI and periodic message refresh while typing
- Python standard library only; no pip dependencies
- API-side membership checks

## Important limitations
- V1 refreshes messages by HTTP polling (roughly every 1.2 seconds while typing), not WebSocket. This is near-real-time, not a persistent socket.
- Transport is HTTPS. Messages are not end-to-end encrypted; server/database operators can read them.
- This is a starter release. Before public production use add rate limits, abuse reporting/moderation, email/phone recovery, account deletion, privacy policy, backups and stronger operational monitoring.
- GitHub hosts source/install files; it is NOT the chat server or user database.

## Deploy backend
1. Cloudflare Dashboard → Workers & Pages → Create Worker.
2. Paste `worker/src/index.js` into the Worker editor and Deploy.
3. Workers & Pages → Storage & databases → D1 → Create database, e.g. `msgn-messenger-db`.
4. D1 Console: run all SQL in `worker/schema.sql`.
5. Worker → Settings → Bindings → Add D1 database binding:
   - Variable name: `DB`
   - Database: `msgn-messenger-db`
6. Worker → Settings → Variables and Secrets → add secret `TOKEN_SECRET`, value a random secret at least 32 bytes (do not commit it).
7. Deploy again and test `https://YOUR-WORKER.workers.dev/health`.

## Install client
On Termux:
```bash
pkg update -y
pkg install python git -y
git clone https://github.com/YOUR-GITHUB/MSGN-Messenger.git
cd MSGN-Messenger
bash install.sh
export MSGN_API="https://YOUR-WORKER.workers.dev"
source ~/.bashrc
msgn
```
Set MSGN_API permanently by adding this line to `~/.bashrc`:
```bash
export MSGN_API="https://YOUR-WORKER.workers.dev"
```

## Menu
1 register; 2 login; 3 public chat; 4 rooms; 5 create group; 6 join group by ID; 7 DM by username; 8 logout.

## GitHub publish
Create a repository named `MSGN-Messenger`, then:
```bash
git init
git add .
git commit -m "MSGN Messenger V1"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB/MSGN-Messenger.git
git push -u origin main
```

## Security
- Never put `TOKEN_SECRET` in GitHub, Termux client, screenshots, or chat.
- Use a unique strong password. This V1 does not include password reset.
- Do not use this V1 for highly sensitive communications.
