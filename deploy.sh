#!/usr/bin/env bash
set -euo pipefail

# deploy.sh
# Usage: Edit variables below or export them as env vars, then run:
#   bash deploy.sh
#
# This script will rsync the current project directory to the remote host,
# create a Python virtualenv (if missing), install `requirements.txt`, run
# migrations and attempt to compile message files.

########################################
# Configuration (override via environment variables)
REMOTE_USER="${REMOTE_USER:-ubuntu}"
REMOTE_HOST="${REMOTE_HOST:-ec2-13-51-177-252.eu-north-1.compute.amazonaws.com}"
SSH_KEY="${SSH_KEY:-~/.ssh/touch_all.pem}"
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu/reserva-ya-saas}"
LOCAL_DIR="${LOCAL_DIR:-$(pwd)}"

# Rsync excludes (adjust as needed)
EXCLUDES=(--exclude ".git" --exclude "venv" --exclude ".venv" --exclude "__pycache__" --exclude "uploads" --exclude "db.sqlite3" --exclude ".env"  --exclude "app/local_settings.py" --exclude "staticfiles" --exclude "deploy.sh")

echo "Deploying ${LOCAL_DIR} -> ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"

# Sync files to remote
rsync -az --delete "${EXCLUDES[@]}" -e "ssh -i '${SSH_KEY}' -o StrictHostKeyChecking=no" "${LOCAL_DIR}/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

# echo "Files synced. Running remote commands..."

# Run remote commands: create dir, create venv if needed, install, migrate, compilemessages
# ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" bash -lc "'
# set -e
# mkdir -p '${REMOTE_DIR}'
# cd '${REMOTE_DIR}'
# create venv if it doesn't exist (try python3 then python)
# if [ ! -d venv ]; then
#   if command -v python3 >/dev/null 2>&1; then
#     python3 -m venv venv
#   else
#     python -m venv venv
#   fi
# fi
# source venv/bin/activate
# pip install --upgrade pip
# if [ -f requirements.txt ]; then
#   pip install -r requirements.txt
# fi
# run migrations
# if [ -f manage.py ]; then
#   python manage.py migrate --noinput
  # compilemessages may fail if gettext isn't installed; ignore failure
#   python manage.py compilemessages || true
# fi
# deactivate
# '"

# echo "Remote deployment steps finished."

echo "Done."
