# Historique et relais IA — Oark

> **Obligation pour toute IA intervenant sur ce projet :** avant de travailler, lire ce fichier puis `journal_ia\courant.md` ; après toute intervention significative, ajouter une entrée au journal via `scripts\journal_ia.py` et actualiser cette synthèse si l'état central change. Les archives sont conservées et consultées à la demande. Ne pas inscrire de secrets. Voir `AGENTS.md`.

## Reprise rapide

Racine Windows : `D:\dev\Oark-Copilot`. L'utilisateur veut préserver l'espace de C:, garder les traitements et manuscrits locaux, limiter la consommation de tokens par des scripts déterministes et, lorsque possible, poursuivre sans intervention humaine.

Au 14 novembre 2026 : **aucun des trois audiobooks complets n'a été produit** ; 15 orientations existent pour le livre I. Trois EPUB et trois PDF sont présents dans `exports`. Cet instantané vieillit : `.\.venv\Scripts\python.exe scripts\journal_ia.py etat` compte les fichiers actuels sans juger leur qualité.

Le calcul audio a été arrêté le 12 novembre à **90 °C GPU**, seuil de ralentissement observé à 93 °C ; le GPU était encore à 80 °C peu après l'arrêt. Le 14 novembre, une mesure ponctuelle affichait 75 °C à 0 % d'utilisation. Cela ne démontre pas qu'une charge prolongée est sûre. Diagnostiquer le refroidissement et établir des conditions sûres avant de reprendre ; ne pas réutiliser une mesure ancienne comme feu vert.

## Demandes et décisions, dans l'ordre

1. Produire des livres EPUB dans `exports`, avec lanceur dédié. Les trois EPUB et les trois PDF sont présents ; ne pas les régénérer ou écraser sans besoin.
2. Construire un pipeline audio de trois livres, personnages distincts, nuances entre narration et dialogue, et annonces de chapitres. Les sources sont trois dossiers `Livre ...` ; la sortie est `exports`.
3. Mettre les installations, caches et données volumineuses sur D: : C: est presque plein. Le souhait est de réutiliser les outils installés, pas de réinstaller systématiquement.
4. Remplacer le TTS distant par une solution open source et locale ; conserver une phase d'orientation JSON (locuteur, émotion, valence, activation, dominance, intensité, intention, vocalisation), modifiable par un humain, puis une synthèse. Ces valeurs sont inférées du texte : ce n'est pas du SER sur voix enregistrée.
5. Ensuite, l'utilisateur a demandé une exécution entièrement autonome pour atteindre les trois audiobooks et rejeté l'idée de seulement signaler des locuteurs ou vocalisations non résolus. Il faut chercher des solutions vérifiables, non les maquiller en succès.
6. Une autre discussion a travaillé sur le même projet puis a été arrêtée. Ce résumé provient des échanges accessibles et des points de reprise, pas d'une transcription intégrale de toutes les discussions ; ne pas supposer que l'historique complet est disponible.
7. Qwen3-TTS 1.7B CustomVoice a remplacé Piper dans le chemin de rendu principal ; Piper et Edge TTS restent installés comme anciens composants, non comme solution expressément locale validée pour ce besoin. Les incises de certains verbes sont séparées et l'orientation est stockée par chapitre.
8. Les essais de diarisation sur 22 cas masqués ont donné 5/22 pour mistral, 6/22 pour qwen2.5:7b, puis 7/22 avec alternance déterministe. Échantillon petit et évaluation imparfaite, mais qualité insuffisamment démontrée. Des rôles génériques et des erreurs sont présents dans les pivots : ils ne constituent pas une résolution fiable.
9. Qwen3-TTS dispose de neuf timbres et certains rôles les partagent actuellement. Les consignes pour rire/sanglot/soupir ne garantissent pas la vocalisation demandée. Deux courts extraits ont été générés, mais la qualité finale, l'identité vocale et les vocalisations ne sont pas validées. Aucun résultat ne doit être présenté comme complet sans vérification réelle.
10. Le traitement a été interrompu au chapitre I-16. Une erreur de JSON invalide avait été corrigée par des tentatives supplémentaires ; les chapitres audio achevés sont désormais conservés pour la reprise. La chaîne autonome n'est plus active.
11. L'utilisateur souhaite un transfert vers Google Antigravity et un écosystème de règles, skills, hooks et scripts pour les IA suivantes ; créer et maintenir ce relais sans installer d'outils inutiles.
12. Le 14–15 novembre 2026, l'utilisateur a mis en pause les chantiers audiobook et illustrations V1 pour se concentrer sur l'histoire et l'écriture. Après analyse comparative entre le canon (`archives/`) et les 94 chapitres existants, une réécriture complète puis son **Édition Référence (« Best-Seller ») en 52 chapitres** (21 + 17 + 14, **138 548 mots**) et **58 illustrations fusain et pastels** ont été produites et compilées en 3 EPUB3 dans `exports-v2/` (avec `01_PLAN_ACTION_CORRECTIVE_ET_REGLES.md`, `02_PLAN_DIRECTEUR_TRILOGIE.md` et `00 - SOMMAIRE DES MANUSCRITS V2.md`), intégrant épigraphes en tête de chaque chapitre, nombres en chiffres arabes, curseur d'explicitation lexicale ajusté à ~75 % (sans redondances inter-chapitres), passage explicite du vouvoiement au tutoiement entre ÉCHO et Koda au Livre II Ch. 07, révélation de l'échelle des Niveaux Technologiques (1 à 100 : terrestre 8–9, apogée oarkin 28, régression de l'Exode 11, niveau aqin 15, dizaines 20 à 90, Unités 96 et asymptote 100) au Livre II Ch. 12 lors de la découverte des armes oarkines, histoire parallèle du caporal Soren Valen sur Aqi, secret des yeux d'ambre de Lyss, et réalisme statistique strict (Règle 11), sans modifier ni supprimer les manuscrits V1.

## Architecture à connaître

- `main_audiobook.py` : phases `analyse` et `generer`, sélecteurs de modèles, mode `--auto` ; `exports\rebuild_audio_books.bat` orchestre les deux phases et demande confirmation par défaut.
- `orientation.py` : segments et JSON validés avec empreinte des sources ; `speakers.py` : attribution explicite, alternance et LLM. Les pivots existants sont conservés, pas réanalysés automatiquement.
- `qwen_renderer.py` : TTS local par lots, instructions expressives et cache par chapitre ; `assembler.py` : assemblage MP3. `renderer.py` est l'ancien rendu Piper.
- `tests\test_audiobook.py` et `tests\test_journal_ia.py` : tests ; `00 - SOMMAIRE DES MANUSCRITS.md` : documentation utilisateur ; `STUDIO_IA.md` : composants et commandes.
- `journal_ia\courant.md` : événements récents ; `journal_ia\archives` : anciennes entrées. `.agents\skills` : procédures réutilisables ; `.agents\hooks.json` : rappel Antigravity au démarrage.

## Suite recommandée

1. Diagnostiquer le GPU et vérifier les processus avant tout calcul. Ne pas relancer à l'aveugle ou toucher aux processus d'autres utilisateurs.
2. Améliorer et mesurer la diarisation sur une vérité terrain représentative ; revoir les 15 pivots existants et la séparation narration/dialogue sans écraser d'éventuelles corrections humaines.
3. Trouver et vérifier une solution locale aux voix réellement distinctes et aux vocalisations ; tester sur des extraits représentatifs et conserver les résultats mesurables. Les instructions TTS et la durée seules ne suffisent pas.
4. Lorsque faisable en sécurité, reprendre l'analyse et la synthèse avec les mécanismes de reprise ; vérifier pour chacun des trois MP3 la couverture, les chapitres, l'intelligibilité, les voix et vocalisations. Prévoir un contrôle objectif et auditif lorsque possible.
5. Mettre à jour ce fichier et le journal à chaque jalon, y compris les résultats négatifs ou interruptions.
