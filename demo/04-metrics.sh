#!/usr/bin/env bash
# Demo 4: Metrics dashboard — show cost tracking and query history
source "$(dirname "$0")/common.sh"

header "4. Metriques et suivi des couts" "GET /api/metrics"

response=$(curl -s "${BASE_URL}/api/metrics?limit=10")

# Summary box
printf "\n  ${BOLD}Resume:${RESET}\n"
echo "$response" | jq -r '
  .summary |
  "    Requetes totales:     \(.total_queries)",
  "    Latence moyenne:      \(.avg_latency_ms | round)ms",
  "    Cout total:           \(.total_cost_eur | . * 10000 | round / 10000) EUR",
  "    Budget restant:       \(.budget_remaining_eur | . * 100 | round / 100) EUR"
'

printf "\n  ${BOLD}Historique recent:${RESET}\n\n"

# Table header
printf "  ${DIM}%-40s %8s %6s %6s %10s${RESET}\n" "Question" "Latence" "In" "Out" "Cout"
hr

# Recent queries table
echo "$response" | jq -r '
  .recent_queries[] |
  "\(.question | .[:38] + if (.|length) > 38 then ".." else "" end)|\(.latency_ms)ms|\(.input_tokens)|\(.output_tokens)|\(.cost_eur)"
' | while IFS='|' read -r question latency input output cost; do
  printf "  %-40s %8s %6s %6s %10s\n" "$question" "$latency" "$input" "$output" "$cost"
done

echo
