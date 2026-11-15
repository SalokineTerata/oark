"""Hook Antigravity SessionStart : rappel bref et inventaire local en lecture seule."""

import json
import sys

from journal_ia import ROOT, status


def main() -> None:
    json.load(sys.stdin)
    message = (
        "Projet Oark : lire AGENTS.md, ia/HISTORIQUE_IA.md puis ia/journal_ia/courant.md. "
        "En fin de travail, ajouter une entrée avec outil/journal_ia.py. "
        "Ne pas reprendre les calculs GPU sans contrôle thermique.\n" + status(ROOT)
    )
    print(json.dumps({"injectSteps": [{"systemMessage": {"systemMessage": message}}]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
