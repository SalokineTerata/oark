# Oark — Trilogie Open-Source

Dépôt officiel du projet **Oark** : manuscrits, illustrations, exports EPUB/PDF et outillage local de production éditoriale et audio.

## Structure du projet

- **`exports-v2/`** : Édition Référence V2 (52 chapitres, plans directeurs et 3 EPUB3 illustrés : *Livre I - L'Éveil*, *Livre II - La Traque*, *Livre III - L'Héritage*).
- **`Livre I - L_éveil/`**, **`Livre II - La Traque/`**, **`Livre III - L’Héritage/`** : Manuscrits V1 par chapitre.
- **`exports/`** : Exports EPUB/PDF V1 et orientations audio existantes.
- **`illustrations/`** : Illustrations de la trilogie.
- **`archives/`** : Documents canoniques de référence.
- **`scripts/`**, **`tests/`**, **`*.py`** : Scripts déterministes de construction EPUB (`scripts/build_books_v2.py`), de vérification (`verify_v2.py`), de journalisation (`scripts/journal_ia.py`) et pipeline audiobook local (`main_audiobook.py`).
- **`HISTORIQUE_IA.md`**, **`STUDIO_IA.md`**, **`AGENTS.md`** : Documentation de reprise et d'architecture.

## Prérequis techniques (outillage local)

Les modèles IA volumineux (`models/`), voix (`voices/`) et l'environnement virtuel (`.venv/`) sont exclus de ce dépôt via `.gitignore`. Consultez `STUDIO_IA.md` et `requirements.txt` pour la configuration locale.

## Licences

- **Œuvres littéraires, illustrations et livres** : [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr)
- **Code et scripts de production** : [MIT](LICENSE)
