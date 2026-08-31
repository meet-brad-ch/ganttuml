#!/usr/bin/env bash
# Generate + render a Gantt source. Writes output/<project.output> with the Python
# generator, then renders PNG + SVG with the plantuml/plantuml docker (run here, not
# from Python). Run from anywhere — it cd's to its own folder.
#   ./render.sh <source.json>     e.g. ./render.sh example.json
set -euo pipefail
cd "$(dirname "$0")"

src="${1:?usage: render.sh <source.json>}"

# PlantUML image pinned to the tested version: the tag is documentation, the digest is
# what docker actually resolves (immutable). To upgrade: bump both from
# https://hub.docker.com/r/plantuml/plantuml/tags and re-check the rendered examples.
# To track the newest release instead (renders may change between runs), use:
#   plantuml_image="plantuml/plantuml:latest"
# Upgrade note: 1.2026.7+ draws a task table (Start/End/Duration columns) by default.
# Before an upgrade, decide on it: "hide column start/end/duration" removes it, and the
# Phases band needs a re-check (its three items per row overprint one table row).
plantuml_image="plantuml/plantuml:1.2026.6@sha256:47870c1f76cfb3747bc7090bfe83013a4e3105b5a0bb1515e2baf5d3e2b3ee9d"

# Run the generator and keep its schedule report visible. Its stdout is captured so
# the .puml filename can be taken from the "wrote output/<name>.puml" line — ganttuml.py
# is the single source of truth for that path (no JSON re-parsing here).
out=$(python3 ganttuml.py --input "$src")
echo "$out"
puml=$(sed -n 's|^wrote .*/||p' <<<"$out")

# Fail fast if the "wrote" line wasn't found — otherwise docker would be handed a bare
# "/data/" and fail with a confusing plantuml error far from the real cause.
[[ "$puml" == *.puml ]] || { echo "error: no 'wrote .../<name>.puml' line in generator output" >&2; exit 1; }

# Render inside the plantuml container: -v mounts ./output as /data, so the container
# reads /data/<name>.puml and writes the .png/.svg (plus a .cmapx image map for the
# PNG's clickable links) back into output/.
for fmt in png svg; do
    docker run --rm -v "$PWD/output:/data" "$plantuml_image" "-t$fmt" "/data/$puml"
done
echo "rendered output/${puml%.puml}.png and output/${puml%.puml}.svg"
