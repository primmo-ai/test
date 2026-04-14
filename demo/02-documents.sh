#!/usr/bin/env bash
# Demo 2: List ingested documents — shows corpus structure and OCR confidence
source "$(dirname "$0")/common.sh"

header "2. Corpus de documents" "GET /api/documents"

response=$(curl -s "${BASE_URL}/api/documents")

printf "\n"

# Summary
total_docs=$(echo "$response" | jq '.total_documents')
total_chunks=$(echo "$response" | jq '.total_chunks')
num_dossiers=$(echo "$response" | jq '.dossiers | keys | length')
printf "  ${BOLD}%s documents${RESET} dans ${BOLD}%s dossiers${RESET} -> ${BOLD}%s chunks${RESET}\n\n" \
  "$total_docs" "$num_dossiers" "$total_chunks"

# Per-dossier table
echo "$response" | jq -r '
  .dossiers | to_entries[] |
  .key as $dossier |
  .value[] |
  "  \($dossier) | \(.doc_type | . + " " * (30 - length) | .[:30]) | \(.chunks) chunks | OCR \(.ocr_confidence | . * 100 | round / 100)%"
'

echo
