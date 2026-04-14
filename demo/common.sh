#!/usr/bin/env bash
# Shared helpers for demo scripts
set -euo pipefail

BASE_URL="${RAG_URL:-http://localhost:8000}"

# Colors
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
MAGENTA='\033[35m'
RESET='\033[0m'

hr() { printf "${DIM}%.0s─${RESET}" {1..60}; echo; }

header() {
  echo
  hr
  printf "  ${BOLD}${CYAN}%s${RESET}\n" "$1"
  [ -n "${2:-}" ] && printf "  ${DIM}%s${RESET}\n" "$2"
  hr
}

ask() {
  local question="$1"
  local payload
  payload=$(jq -n --arg q "$question" '{question: $q}')

  curl -s -X POST "${BASE_URL}/api/query" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

ask_with_filter() {
  local question="$1"
  local dossier="$2"
  local payload
  payload=$(jq -n --arg q "$question" --arg d "$dossier" '{question: $q, dossier: $d}')

  curl -s -X POST "${BASE_URL}/api/query" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

print_question() {
  printf "\n  ${BOLD}${YELLOW}Question:${RESET} %s\n\n" "$1"
}

print_answer() {
  local response="$1"

  # Answer
  printf "  ${BOLD}${GREEN}Reponse:${RESET}\n"
  echo "$response" | jq -r '.answer' | fold -s -w 76 | sed 's/^/    /'
  echo

  # Sources table
  printf "  ${BOLD}${MAGENTA}Sources:${RESET}\n"
  echo "$response" | jq -r '
    .sources[] |
    "    \(.dossier) | \(.doc_type) | \(.filename)" +
    (if .section then " > \(.section)" else "" end) +
    " (\(.relevance_score))"
  '
  echo

  # Metrics one-liner
  printf "  ${DIM}Latence: %sms | Tokens: %s in / %s out | Cout: %s EUR | Chunks: %s${RESET}\n" \
    "$(echo "$response" | jq '.metrics.latency_ms')" \
    "$(echo "$response" | jq '.metrics.input_tokens')" \
    "$(echo "$response" | jq '.metrics.output_tokens')" \
    "$(echo "$response" | jq '.metrics.cost_eur')" \
    "$(echo "$response" | jq '.metrics.retrieval_count')"
}

wait_for_keypress() {
  printf "\n  ${DIM}Appuyez sur Entree pour continuer...${RESET}"
  read -r
}
