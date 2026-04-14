#!/usr/bin/env bash
# Demo 5: Edge cases — low OCR confidence, price extraction, identity validation
source "$(dirname "$0")/common.sh"

header "5. Cas limites" "POST /api/query"

# ── 5a. Low OCR confidence document ─────────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 5a. Document avec OCR de faible qualite ---${RESET}\n"

Q1="Quelle est la piece d'identite d'Alexandre FONTAINE dans le dossier 3?"
print_question "$Q1"
R1=$(ask "$Q1")
print_answer "$R1"

wait_for_keypress

# ── 5b. Price extraction ────────────────────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 5b. Extraction du prix de vente ---${RESET}\n"

Q2="Quel est le prix de vente dans le dossier 1?"
print_question "$Q2"
R2=$(ask "$Q2")
print_answer "$R2"

wait_for_keypress

# ── 5c. Identity document validation ────────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 5c. Verification des pieces d'identite ---${RESET}\n"

Q3="Les pieces d'identite sont-elles en ordre dans le dossier 1?"
print_question "$Q3"
R3=$(ask "$Q3")
print_answer "$R3"

wait_for_keypress

# ── 5d. Proof of address compliance ─────────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 5d. Conformite des justificatifs de domicile ---${RESET}\n"

Q4="Les justificatifs de domicile sont-ils conformes dans le dossier 2?"
print_question "$Q4"
R4=$(ask "$Q4")
print_answer "$R4"

echo
