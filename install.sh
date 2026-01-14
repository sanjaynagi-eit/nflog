#!/usr/bin/env bash
# Simple installer that clones the repository and installs nflog in editable mode.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/sanjaynagi-eit/nflog.git}"
TARGET_DIR="${TARGET_DIR:-$HOME/.local/share/nflog-src}"
BRANCH="${BRANCH:-main}"

echo "Installing nflog from $REPO_URL (branch: $BRANCH) into $TARGET_DIR"

if [ -d "$TARGET_DIR/.git" ]; then
  echo "Updating existing checkout..."
  git -C "$TARGET_DIR" fetch --quiet
  git -C "$TARGET_DIR" checkout "$BRANCH" >/dev/null 2>&1 || true
  git -C "$TARGET_DIR" pull --ff-only --quiet
else
  git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
python -m pip install --upgrade pip >/dev/null
python -m pip install -e .

echo "nflog installed from $TARGET_DIR"
