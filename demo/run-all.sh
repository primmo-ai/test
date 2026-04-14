#!/usr/bin/env bash
# Master demo runner — executes all demos in sequence
set -euo pipefail

DEMO_DIR="$(dirname "$0")"

BOLD='\033[1m'
CYAN='\033[36m'
DIM='\033[2m'
RESET='\033[0m'

cat <<'BANNER'

  ╔═══════════════════════════════════════════════╗
  ║       Agent RAG Notarial — Demo               ║
  ║       Analyse de dossiers immobiliers          ║
  ╚═══════════════════════════════════════════════╝

BANNER

printf "  ${DIM}URL: ${RAG_URL:-http://localhost:8000}${RESET}\n"
printf "  ${DIM}Appuyez sur Entree entre chaque etape${RESET}\n"

for script in "$DEMO_DIR"/0[1-5]-*.sh; do
  bash "$script"
  printf "\n  ${DIM}Appuyez sur Entree pour la suite...${RESET}"
  read -r
done

cat <<'DONE'

  ╔═══════════════════════════════════════════════╗
  ║                  Fin de la demo                ║
  ╚═══════════════════════════════════════════════╝

DONE
