#!/usr/bin/env bash

# Create an array including both endpoints: 5 divisions produces 6 values.
start=0
end=10
divisions=5  # Must be a positive integer.

read -r -a numbers <<< "$(awk -v s="$start" -v e="$end" -v n="$divisions" \
  'BEGIN { for (i=0; i<=n; i++) printf "%.10g ", s+(e-s)*i/n }')"

printf '%s\n' "${numbers[@]}"
