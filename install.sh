#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y
pkg install -y python git
mkdir -p "$HOME/.local/bin"
cp client/msgn.py "$HOME/.local/bin/msgn"
chmod +x "$HOME/.local/bin/msgn"
if ! grep -q 'HOME/.local/bin' "$HOME/.bashrc" 2>/dev/null; then
 echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi
echo
echo "نصب تمام شد. ابتدا MSGN_API را تنظیم کن:"
echo 'export MSGN_API="https://YOUR-WORKER.workers.dev"'
echo "سپس: source ~/.bashrc && msgn"
