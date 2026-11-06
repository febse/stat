#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

pandoc "$script_dir/classroom-survey-kahneman-tversky.md" \
  -o "$script_dir/classroom-survey-kahneman-tversky.pdf" \
  -V documentclass=scrartcl \
  -V fontsize=13pt \
  -V pagestyle=empty
