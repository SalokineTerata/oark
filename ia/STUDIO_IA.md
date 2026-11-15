# Studio de production et relais IA

## Outils constatés le 14 novembre 2026

| Composant | État observé / usage |
|---|---|
| Python 3.12 | `.venv` sur D: ; Python système préexistant sur C:. |
| FFmpeg et ffprobe | Disponibles dans le PATH via un lien WinGet sur C: ; assemblage et inspection. |
| Ollama | Modèles observés : `qwen2.5:3b`, `qwen2.5:7b`, `qwen2.5:1.5b`, `mistral`, `qwen2.5-coder:7b` ; stockage antérieur dans `D:\ollama_models`, à vérifier avant nouvelle installation. |
| PyTorch / torchaudio | `2.11.0+cu128` ; calcul CUDA. |
| qwen-tts / transformers / gradio | `0.1.1` / `4.57.3` / `5.49.1` ; TTS local expressif. |
| ollama Python / piper-tts / edge-tts | `0.6.3` / `1.8.0` / `7.3.1`. Edge est un ancien moteur distant, pas la voie locale actuelle. |
| Modèles locaux | `models\Qwen3-TTS-1.7B-CustomVoice-fp16`, `models\Qwen3-TTS-12Hz-1.7B-CustomVoice`, `models\Qwen3-TTS-Tokenizer-12Hz`, `models\whisper-small` ; Piper dans `voices`. |
| Matériel observé | RTX 2060 6 Go ; machine partagée. Ressources et températures peuvent évoluer. |

`requirements.txt` indique les dépendances, mais ne prouve pas qu'elles fonctionnent actuellement. Le modèle Qwen FP16 a été fragmenté car un chargement en un seul fichier provoquait une violation d'accès ; ne pas le remplacer sans test. Les téléchargements précédents étaient instables. Éviter les installations et téléchargements tant qu'ils ne sont pas nécessaires ; tous les nouveaux caches, temporaires et modèles doivent aller sur D:.

## Journal et rotation déterministes

Depuis la racine :

```powershell
.\.venv\Scripts\python.exe scripts\journal_ia.py etat
.\.venv\Scripts\python.exe scripts\journal_ia.py lire
.\.venv\Scripts\python.exe scripts\journal_ia.py ajouter --titre "Sujet" --texte "Faits ; tests ; limites ; suite."
.\.venv\Scripts\python.exe scripts\journal_ia.py ajouter --titre "Sujet" --fichier D:\dev\Oark-Copilot\exports\temp_audio\entree.txt
.\.venv\Scripts\python.exe scripts\journal_ia.py rotation
```

Le fichier actif est limité à 16 000 octets UTF-8 : avant dépassement, l'ancien actif est déplacé vers une archive numérotée non écrasée. Une entrée trop longue est refusée : la résumer ou la scinder en entrées distinctes. La commande prend un verrou ; si un crash laisse `journal_ia\.verrou`, vérifier qu'aucune écriture n'est active avant de l'enlever. Il n'y a pas de nettoyage automatique des archives. Toute IA doit actualiser l'état essentiel dans `HISTORIQUE_IA.md` et ajouter son entrée elle-même ; les hooks ne peuvent pas rédiger un bilan fiable à sa place.

## Règles, skills et hooks

- `AGENTS.md` est le point d'entrée commun ; `.agents\skills` contient les procédures ciblées de reprise, audio, environnement local et EPUB/PDF. Antigravity documente `.agents\skills` comme emplacement de skills d'espace de travail.
- `.agents\hooks.json` configure un hook Antigravity `SessionStart` en lecture seule : `scripts\hook_session_ia.py` renvoie un rappel et un inventaire compact au format JSON documenté. Le chemin Python est absolu pour ce poste ; l'adapter si le projet est déplacé. Son exécution effective dans votre version et vos réglages Antigravity n'a pas été vérifiée ici. Aucun hook ne prétend mettre à jour automatiquement un résumé sémantique ou valider un rendu.
- Références officielles : https://antigravity.google/docs/skills et https://antigravity.google/docs/hooks. Les autres assistants peuvent ignorer ces fichiers : ils doivent néanmoins suivre `AGENTS.md` et utiliser le journal.

## Vérification

```powershell
$env:TEMP='D:\dev\Oark-Copilot\exports\temp_audio'
$env:TMP=$env:TEMP
$env:OPENBLAS_NUM_THREADS='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Le test de synthèse réel, les évaluations de diarisation et l'inspection des MP3 sont des vérifications séparées ; les tests unitaires ne certifient pas les livres finaux. `exports\temp_audio` contient des journaux et essais potentiellement utiles ; ne pas le vider systématiquement.
