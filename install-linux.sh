#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo 'Necesitas Python 3.9 o posterior.' >&2; exit 1; }
exec python3 "$script_dir/eva/install_linux.py" "$@"
