#!/usr/bin/env bash

# Run from the directory containing run_pressure_<number> folders.
# Every execution appends results, so repeated runs create duplicate CSV rows.
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1

for folder in run_pressure_*; do
    [[ -d "$folder" ]] || continue
    [[ "$folder" =~ ^run_pressure_[0-9]+([.][0-9]+)?$ ]] || continue

    python "$script_dir/BurnRate.py" \
        "$folder"
done
