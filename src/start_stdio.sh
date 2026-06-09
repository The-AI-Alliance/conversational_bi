#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONUNBUFFERED=1
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export PYTHONPATH="${SCRIPT_DIR}/src"
cd "${SCRIPT_DIR}"
exec "${SCRIPT_DIR}/.pixi/envs/default/bin/python" start_stdio.py
