#!/usr/bin/env bash
# Startet das VRC OSC Tool unter Linux (legt beim ersten Mal automatisch eine venv an)
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/python vrc_osc_tool.py "$@"
