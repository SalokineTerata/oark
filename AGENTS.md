# Instructions pour toute IA du projet Oark

**Au début** : lire [ia/HISTORIQUE_IA.md](ia/HISTORIQUE_IA.md), puis [ia/journal_ia/courant.md](ia/journal_ia/courant.md). Exécuter `.\.venv\Scripts\python.exe outil\journal_ia.py etat` ; les instantanés ne sont pas un état temps réel.

**À la fin de chaque intervention significative**, toute IA doit ajouter une entrée concise au journal avec `.\.venv\Scripts\python.exe outil\journal_ia.py ajouter --titre "Sujet" --texte "Faits, fichiers, vérifications, limites et prochaine étape."` et actualiser l'état essentiel dans `ia/HISTORIQUE_IA.md` si nécessaire. Le script effectue la rotation ; ne jamais écraser ou supprimer les archives. Ne pas enregistrer de secrets ni de verbatim sensibles.

- Priorité aux scripts déterministes, tests ciblés, outils et modèles déjà installés ; limiter les appels et la surveillance IA coûteux. Ne pas inventer d'automatisation supposée active.
- Installer modèles, caches, environnements et fichiers temporaires sur **D:** ; C: est presque plein. Contrôler aussi les chemins par défaut des installateurs, serveurs et caches avant toute installation. Des outils système préexistants sur C: ne sont pas à déplacer sans raison.
- Manuscrits et code restent locaux : aucun envoi à une API, un TTS ou un service tiers sans autorisation explicite. Demander avant publication externe.
- Machine partagée : ne pas arrêter de processus tiers, ne pas supprimer des données inconnues ni écraser des orientations corrigées.
- Vérifier la température, la charge et la marge thermique avant un traitement long ; il a été arrêté à 90 °C. Ne pas contourner les limites de protection, ni affirmer que le refroidissement est sûr sur la base de cette seule valeur.
- Audio : les objectifs comprennent trois livres complets et vérifiés, annonces de chapitre, personnages distincts et nuances expressives. Les pivots non révisés, les approximations et les essais de synthèse ne démontrent pas leur réussite. Ne pas masquer les ambiguïtés ni attribuer silencieusement une identité arbitraire.
- Examiner les changements existants avant édition ; tester ce qui change ; ne pas effacer de chapitres terminés ni d'archives sans demande explicite.
- Les skills de `.agents\skills` décrivent la reprise, l'audio, l'environnement et l'EPUB. Le hook Antigravity de démarrage est un rappel en lecture seule ; sa disponibilité effective dépend du produit et de ses réglages, il ne remplace jamais l'ajout manuel au journal.
