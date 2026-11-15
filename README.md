# Oark — Trilogie Open-Source

Dépôt officiel du projet **Oark** : manuscrits, illustrations, exports EPUB/PDF et outillage local de production éditoriale et audio.

## Structure du projet

- **`cadre/`** : Bibles d'univers et de personnages, trames narratives, plans détaillés par tome, charte d'écriture V2 et plan directeur (52 chapitres).
- **`livres/`** : Édition Référence active (V2 — 52 chapitres et 58 illustrations fusain & pastel dans `livres/illustrations/`).
- **`exports/`** : Livrables générés actifs (3 EPUB3 illustrés : *Livre I - L'Éveil*, *Livre II - La Traque*, *Livre III - L'Héritage*, et orientations audio).
- **`archives/`** : Documents canoniques de référence et ancienne version V1 archivée (`archives/v1/` : manuscrits V1, illustrations V1 et anciens exports EPUB/PDF).
- **`scripts/`**, **`tests/`**, **`*.py`** : Scripts déterministes de construction EPUB (`scripts/build_books_v2.py`), de journalisation (`scripts/journal_ia.py`) et pipeline audiobook local (`main_audiobook.py`).
- **`HISTORIQUE_IA.md`**, **`STUDIO_IA.md`**, **`AGENTS.md`**, **`journal_ia/`** : Documentation de reprise, architecture et journal rotatif des IA.

## Prérequis techniques (outillage local)

Les modèles IA volumineux (`models/`), voix (`voices/`) et l'environnement virtuel (`.venv/`) sont exclus de ce dépôt via `.gitignore`. Consultez `STUDIO_IA.md` et `requirements.txt` pour la configuration locale.

## Licences

- **Œuvres littéraires, illustrations et livres** : [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr)
- **Code et scripts de production** : [MIT](LICENSE)
