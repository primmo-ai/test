#!/usr/bin/env bash
# Demo 1: Health check — verify the system is up and documents are ingested
source "$(dirname "$0")/common.sh"

header "1. Verification du systeme" "GET /api/health"

response=$(curl -s "${BASE_URL}/api/health")

printf "\n"
echo "$response" | jq '{
  status,
  documents_ingested: .documents_ingested,
  chunks_indexed: .chunks_indexed,
  qdrant_connected
}'
printf "\n"

status=$(echo "$response" | jq -r '.status')
if [ "$status" = "ready" ]; then
  printf "  ${GREEN}Systeme pret.${RESET}\n"
else
  printf "  ${YELLOW}Statut: %s${RESET}\n" "$status"
fi

echo
