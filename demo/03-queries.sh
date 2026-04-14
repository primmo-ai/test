#!/usr/bin/env bash
# Demo 3: Core query showcase — targeted, cross-dossier, and coherence queries
source "$(dirname "$0")/common.sh"

header "3. Requetes RAG" "POST /api/query"

# ── 3a. Targeted: who are the sellers? ──────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 3a. Requete ciblee (filtre par dossier) ---${RESET}\n"

Q1="Qui sont les vendeurs du dossier 1?"
print_question "$Q1"
R1=$(ask "$Q1")
print_answer "$R1"

wait_for_keypress

# ── 3b. Targeted: property description ──────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 3b. Description du bien ---${RESET}\n"

Q2="Quel est le bien concerne par la transaction de Bordeaux?"
print_question "$Q2"
R2=$(ask "$Q2")
print_answer "$R2"

wait_for_keypress

# ── 3c. Compliance: DPE check ──────────────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 3c. Verification de conformite (DPE) ---${RESET}\n"

Q3="Le DPE correspond-il au bien du dossier 2?"
print_question "$Q3"
R3=$(ask "$Q3")
print_answer "$R3"

wait_for_keypress

# ── 3d. Cross-dossier: find a person ───────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 3d. Recherche cross-dossier ---${RESET}\n"

Q4="M. BENALI achete dans quelle ville?"
print_question "$Q4"
R4=$(ask "$Q4")
print_answer "$R4"

wait_for_keypress

# ── 3e. Coherence: full dossier audit ──────────────────────────────
printf "\n  ${BOLD}${CYAN}--- 3e. Analyse de coherence (audit complet) ---${RESET}\n"

Q5="Y a-t-il des incoherences entre les documents du dossier 1?"
print_question "$Q5"
R5=$(ask "$Q5")
print_answer "$R5"

echo
