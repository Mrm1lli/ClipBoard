#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
# Optional local-only shell configuration. Keep it ignored, private, and trusted.
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi
exec .venv/bin/python -m bellhaven run
