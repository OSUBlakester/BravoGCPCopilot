#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="/Users/blakethomas/Documents/Documents_Macbook_Air/BravoGCPCopilot"
PYTHON_BIN="$ROOT_DIR/venv/bin/python3"
SCRIPT_PATH="$ROOT_DIR/generate_missing_images_free.py"

"$PYTHON_BIN" "$SCRIPT_PATH" "$@"
