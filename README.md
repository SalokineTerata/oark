# Oark — Trilogie Open-Source

Dépôt officiel du projet **Oark** : manuscrits, illustrations, exports EPUB/PDF et outillage local de production éditoriale et audio.

## Structure du projet

- **`cadre/`** : Documents cadres — bibles d'univers et de personnages, trames narratives, plans détaillés, charte d'écriture V2 et plan directeur (52 chapitres).
- **`livres/`** : Référentiel des livres (fichiers `.md` de l'Édition Référence V2 : *Livre I - L'Éveil*, *Livre II - La Traque*, *Livre III - L'Héritage*).
- **`illustrations/`** : Référentiel des illustrations (58 illustrations fusain & pastel + `manifest_v2.json`).
- **`exports-epub/`** : Export des livres en EPUB3 illustrés.
- **`exports-audiobook/`** : Export des audiobooks et orientations JSON (`orientations/`).
- **`voix/`** : Référentiel des voix de synthèse (`voix.json` et modèles vocaux locaux).
- **`outil/`** : Boîte à outils Python (tout le code source du projet, CSS, `requirements.txt` et scripts utilitaires).
- **`tests/`** : Suite de tests unitaires.
- **`ia/`** : Configuration et historisation pour les IA (`HISTORIQUE_IA.md`, `STUDIO_IA.md`, `journal_ia/`).
- **`archives/`** : Archives canoniques (`.docx`) et ancienne version V1 (`archives/v1/`).
- **`.agents/`** & **`AGENTS.md`** : Règles, skills et hooks Antigravity (à la racine pour la découverte automatique).

## Prérequis techniques (outillage local)

Les modèles IA volumineux (`models/`), fichiers audio de voix (`voix/*` hors `voix.json`), caches (`exports-audiobook/temp_audio/`) et l'environnement virtuel (`.venv/`) sont exclus de ce dépôt via `.gitignore`. Consultez `ia/STUDIO_IA.md` et `outil/requirements.txt` pour la configuration locale.

## Licences

- **Œuvres littéraires, illustrations et livres** : [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr)
- **Code et scripts de production** : [MIT](LICENSE)
