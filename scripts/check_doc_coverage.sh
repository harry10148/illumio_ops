#!/usr/bin/env bash
# Verify docs/User_Manual.md mentions every report module, subcommand, and bundle script.
# Exits non-zero with a list of missing terms.
set -euo pipefail

DOC=docs/User_Manual.md
[ -f "$DOC" ] || { echo "FATAL: $DOC not found"; exit 2; }

missing=()

# Report analysis modules (file basename without .py)
while IFS= read -r path; do
  mod=$(basename "$path" .py)
  grep -q -- "$mod" "$DOC" || missing+=("module:$mod")
done < <(find src/report/analysis -maxdepth 1 -name 'mod*.py' -not -name '__init__.py')

# Policy Usage modules
while IFS= read -r path; do
  mod=$(basename "$path" .py)
  grep -q -- "$mod" "$DOC" || missing+=("pu_module:$mod")
done < <(find src/report/analysis/policy_usage -maxdepth 1 -name 'pu_*.py')

# CLI subcommands (excluding -h/--help meta entries)
for sub in cache monitor gui report rule siem workload config status version; do
  grep -qE "(\`|\b)${sub}(\`|\b)" "$DOC" || missing+=("subcommand:$sub")
done

# Offline bundle scripts
for s in build_offline_bundle.sh install.sh uninstall.sh; do
  grep -q -- "$s" "$DOC" || missing+=("script:$s")
done

if [ ${#missing[@]} -ne 0 ]; then
  printf 'MISSING in %s:\n' "$DOC"
  printf '  %s\n' "${missing[@]}"
  exit 1
fi

echo "OK — all required terms present in $DOC"
