#!/usr/bin/env bash
# Generate + render the advanced (every-feature) example Gantt (thin wrapper over render.sh).
set -euo pipefail
exec "$(dirname "$0")/render.sh" example-advanced.json
