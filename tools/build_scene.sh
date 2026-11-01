#!/usr/bin/env bash
set -euo pipefail
# Blender must be installed locally. All material/model generation uses original procedural geometry.
SCENE="${1:-01}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$PROJECT_ROOT/game/assets/models" "$PROJECT_ROOT/docs/previews"
blender -b -P "$PROJECT_ROOT/blender/scene_generator.py" -- \
  --scene "$SCENE" \
  --output "$PROJECT_ROOT/game/assets/models/scene_${SCENE}.glb" \
  --blend "$PROJECT_ROOT/blender/scene_${SCENE}.blend" \
  --preview "$PROJECT_ROOT/docs/previews/scene_${SCENE}.png"
python "$PROJECT_ROOT/tools/audit_project.py"
echo "FINISHED scene_${SCENE}; examine preview PNG and QA JSON, then import GLB in Godot."
