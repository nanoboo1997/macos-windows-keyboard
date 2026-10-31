#!/bin/bash
set -euo pipefail
if [[ "$(uname -s)" != Darwin ]]; then
  echo "This installer requires macOS." >&2
  exit 1
fi
if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Run as your normal user, without sudo." >&2
  exit 1
fi
script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/osascript -l JavaScript "$script_dir/manage.js" "$1" "$script_dir/../karabiner/external-windows-shortcuts.json" "${@:2}"
