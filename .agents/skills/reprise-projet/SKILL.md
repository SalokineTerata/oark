---
name: reprise-projet
description: Reprend et transmet le projet Oark entre sessions ou agents avec son journal rotatif et son inventaire local.
---

# Reprise et transmission

1. Lire `AGENTS.md`, `HISTORIQUE_IA.md`, puis `journal_ia\courant.md` ; ne consulter les archives que pour le sujet nécessaire.
2. Exécuter `.\.venv\Scripts\python.exe scripts\journal_ia.py etat`. Vérifier les processus et journaux avant tout nouveau lancement, sans arrêter de processus tiers.
3. Vérifier les commandes avec `.\.venv\Scripts\python.exe scripts\journal_ia.py --help`. `lire` affiche l'actif ; `rotation` archive explicitement ; `ajouter --titre "..." --texte "..."` ajoute une entrée. `--fichier chemin` accepte un texte UTF-8 long.
4. En fin d'intervention, inscrire objectif, décisions, fichiers, tests/résultats, tâches restantes et blocages. Ne pas recopier des manuscrits ou des secrets. Mettre à jour la synthèse si l'état central a changé.
5. Si un verrou `.verrou` subsiste après un crash, vérifier qu'aucune autre écriture du journal n'est active avant de le supprimer explicitement. Les archives ne sont jamais à supprimer automatiquement.

Les scripts et chemins décrits ici sont des outils existants, pas des substituts à la vérification des résultats.
