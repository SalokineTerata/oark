---
name: production-audiobook
description: Diagnostique, améliore et reprend la production audio locale multivoix et la validation des livres Oark.
---

# Production audio locale

1. Lire les consignes et l'état du projet ; vérifier le refroidissement GPU, l'espace sur D:, les processus existants et l'état Ollama avant un calcul prolongé.
2. Pipeline actuel : `main_audiobook.py analyse` produit un JSON par chapitre (`orientation.py`, `speakers.py`) ; `generer` utilise `qwen_renderer.py` puis `assembler.py`. Le batch `exports\rebuild_audio_books.bat` demande validation par défaut, `--auto` l'omet. Lire `--help` et la documentation avant lancement.
3. Conserver les pivots existants : leur source est vérifiée par SHA-256 ; une nouvelle analyse ne les met pas à jour automatiquement. Les cache audio par chapitre sont conservés pour reprise. Ne pas remplacer une correction humaine.
4. Diarisation : incises explicites d'abord, alternance et LLM pour le reste. L'alternance n'est pas une preuve ; l'évaluation passée était faible. Tester sur des exemples de référence variés avant de considérer la qualité suffisante.
5. Les métadonnées sont inférées du texte, pas une reconnaissance SER d'enregistrements. Les instructions Qwen ne prouvent pas que rires, sanglots et soupirs sont audibles. Les neuf timbres et leur partage ne satisfont pas automatiquement l'exigence de voix distinctes. Chercher des solutions et les vérifier.
6. Tests ciblés : `.\.venv\Scripts\python.exe -m unittest discover -s tests`. Vérifier chaque MP3 réel avec ffprobe et écoute ou contrôle pertinent, le nombre de chapitres, la durée, la couverture du texte, les voix et vocalisations. Une durée plausible ou une sortie factice n'est pas une validation finale.
7. Journaliser les résultats et le travail restant. Ne pas annoncer trois audiobooks complets avant qu'ils existent et soient vérifiés.
