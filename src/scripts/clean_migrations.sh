#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  src/scripts/clean_migrations.sh [--dry-run] [root]

Deletes every Python migration file under */migrations/*.py except
*/migrations/__init__.py.

Arguments:
  root       Directory to scan. Defaults to src/apps.

Options:
  --dry-run  Print files that would be deleted without deleting them.
  -h, --help Show this help.
EOF
}

dry_run=false
root="src/apps"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      root="$1"
      shift
      ;;
  esac
done

if [[ ! -d "$root" ]]; then
  echo "Root directory not found: $root" >&2
  exit 1
fi

count=0
while IFS= read -r -d '' file; do
  count=$((count + 1))
  if [[ "$dry_run" == true ]]; then
    printf 'would delete: %s\n' "$file"
  else
    rm -f -- "$file"
    printf 'deleted: %s\n' "$file"
  fi
done < <(find "$root" -type f -path '*/migrations/*.py' ! -name '__init__.py' -print0)

if [[ "$dry_run" == true ]]; then
  printf 'Total files that would be deleted: %d\n' "$count"
else
  printf 'Total files deleted: %d\n' "$count"
fi
