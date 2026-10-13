#!/usr/bin/env bash
# Create .venv and install reachy_mini_grokbot (macOS / Linux).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.10+ (e.g. brew install python@3.12)." >&2
  exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ]]; then
  echo "Python 3.10+ required; found $PY_VERSION" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating .venv with python3 ($PY_VERSION)..."
  python3 -m venv .venv
else
  echo "Using existing .venv"
fi

# shellcheck source=/dev/null
source .venv/bin/activate

python -m pip install --upgrade pip wheel
python -m pip install -e .

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your Grok webhook and tunnel settings."
fi

echo ""
echo "Done. Activate the venv in new terminals with:"
echo "  source .venv/bin/activate"
echo ""
echo "Install the Reachy Mini SDK separately if pip could not install reachy-mini:"
echo "  https://github.com/pollen-robotics/reachy_mini"
echo ""
echo "Then: reachy-mini-daemon   # terminal 1"
echo "      python -m reachy_mini_grokbot.main   # terminal 2"
