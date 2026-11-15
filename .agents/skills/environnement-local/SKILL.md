---
name: environnement-local
description: Vérifie et maintient l'environnement local Windows, les modèles IA et les ressources du projet Oark sur D:.
---

# Environnement local

1. Consulter `STUDIO_IA.md` puis vérifier les composants réellement disponibles : `.venv\Scripts\python.exe -m pip show <paquet>`, `ffmpeg -version`, et, au besoin, `nvidia-smi`. Attention : certaines commandes Ollama peuvent démarrer son service.
2. Privilégier les dépendances existantes. Avant toute installation nécessaire, vérifier espace et destinations sur D: : `TEMP`, `TMP`, `PIP_CACHE_DIR`, caches de modèles et `OLLAMA_MODELS`. Ne pas supprimer ni déplacer les installations système préexistantes sur C:.
3. Qwen FP16 local est découpé en cinq fragments pour contourner un plantage de chargement Windows ; conserver les fichiers et l'index existants. `HF_HUB_OFFLINE=1` évite les accès réseau pour un modèle déjà complet.
4. Les téléchargements précédents ont été interrompus par le réseau. `fetch_models.py` peut annoncer un succès sans garantir l'intégrité de tous les octets : vérifier la taille et la somme SHA-256 attendues auprès de la source officielle avant utilisation. Reprendre un téléchargement ciblé plutôt que tout recommencer, sans transmettre les manuscrits.
5. Contrôler GPU, RAM, stockage et autres processus avant calcul ; ne jamais arrêter une application appartenant à une autre session. Un ancien pic thermique à 90 °C a interrompu le projet : une mesure isolée n'est pas une validation de sécurité.
6. Consigner versions, changements, vérifications et blocages dans le journal ; ne jamais affirmer qu'une installation ou un modèle fonctionne sans test.
