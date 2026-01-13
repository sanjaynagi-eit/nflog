#!/usr/bin/env bash
# Simple installer that clones the repository and installs nextlog in editable mode.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/your-org/nextlog.git}"
TARGET_DIR="${TARGET_DIR:-$HOME/.local/share/nextlog-src}"
BRANCH="${BRANCH:-main}"

echo "Installing nextlog from $REPO_URL (branch: $BRANCH) into $TARGET_DIR"

if [ -d "$TARGET_DIR/.git" ]; then
  echo "Updating existing checkout..."
  git -C "$TARGET_DIR" fetch --quiet
  git -C "$TARGET_DIR" checkout "$BRANCH" >/dev/null 2>&1 || true
  git -C "$TARGET_DIR" pull --ff-only --quiet
else
  git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR/nextlog"
python -m pip install --upgrade pip >/dev/null
python -m pip install -e .

echo "nextlog installed from $TARGET_DIR/nextlog"
