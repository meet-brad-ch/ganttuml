#!/usr/bin/env bash
# Generate + render the example Gantt (thin wrapper over render.sh).
set -euo pipefail
exec "$(dirname "$0")/render.sh" example.json
