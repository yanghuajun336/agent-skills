#!/bin/bash
# run.sh - wrapper for skill_l10n.py
# Usage: ./run.sh <target_dir> <report_dir> [--src en] [--tgt zh]
set -e
TARGET="$1"
REPORT="$2"
shift 2 || true
export SKILL_L10N_VERIFY=${SKILL_L10N_VERIFY:-false}
python3 "$(dirname "$0")/skill_l10n.py" "$TARGET" "$REPORT" "$@"
