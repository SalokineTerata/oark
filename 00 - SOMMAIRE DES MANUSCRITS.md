# Oark — Manuscrits de la trilogie

Premiers jets complets, rédigés en français à partir des plans et du canon validés. Chaque livre possède une numérotation continue de chapitres entiers.

| Tome | Dossier | Fichiers Markdown | Mots environ |
|---|---|---:|---:|
| I — L’Éveil | [Ouvrir le dossier](<./Livre I - L_éveil/>) | 32 | 68 400 |
| II — La Traque | [Ouvrir le dossier](<./Livre II - La Traque/>) | 30 | 70 700 |
| III — L’Héritage | [Ouvrir le dossier](<./Livre III - L’Héritage/>) | 32 | 70 500 |

Les documents DOCX de référence et les versions originales sont conservés dans [archives](<./archives/>). Les chapitres DOCX initiaux n’ont pas été supprimés.
Les manuscrits, illustrations et manifeste précédant le redécoupage sont conservés dans [avant-redecoupage](<./archives/avant-redecoupage/>).

Les manuscrits sont des premiers jets destinés à une relecture éditoriale complète. Les décomptes sont approximatifs et ne remplacent pas une révision littéraire de fond.

## Reconstruction des PDF illustrés

Sous Windows, avec Python 3, Pandoc et Microsoft Edge installés, exécuter depuis la racine :

```bat
exports\rebuild_pdf_books.bat
```

Il est aussi possible de reconstruire un seul livre, par exemple avec `exports\rebuild_pdf_books.bat --book I`. Si nécessaire, les variables d'environnement `PANDOC` et `EDGE` peuvent contenir les chemins complets de leurs exécutables. Les PDF sont créés dans `exports`. Le script signale une erreur si un chapitre ou son illustration manque.

Les illustrations attendues sont les fichiers `illustrations\livre-i\001.png`, etc., suivant la numérotation des chapitres. Leurs scènes et leurs graines fixes sont définies individuellement dans [le manifeste](./illustrations/manifest.json), afin de conserver les graines d'origine après le redécoupage. Pour les produire, démarrer un serveur ComfyUI local avec le checkpoint `DreamShaper8_LCM.safetensors` installé, puis exécuter :

```bat
python scripts\generate_illustrations.py
```

Le générateur reprend sans écraser les images déjà présentes. Pour refaire un chapitre, utiliser par exemple `python scripts\generate_illustrations.py --book I --chapter 1 --force`. Une autre adresse ComfyUI peut être fournie avec `--server`. La génération d'images et la reconstruction des PDF sont deux étapes distinctes : le fichier `.bat` réutilise les PNG existants.

Le manifeste indique aussi l'empreinte SHA-256 du checkpoint utilisé pour vérifier sa provenance. Certaines scènes possèdent leur propre prompt négatif, utilisé lors de leur régénération. ComfyUI doit exposer le checkpoint sous le nom indiqué dans le manifeste.

Les illustrations du livre I, chapitres 1 à 24, 26, 27, 30 et 31, et du livre II, chapitres 2, 5 et 7, ont été générées séparément dans le style fusain et pastel, puis redimensionnées. Elles ne sont pas issues du checkpoint ComfyUI. Les autres illustrations n'ont pas encore été régénérées dans ce style. Le rendu de ComfyUI doit être vérifié avant de les remplacer : les essais locaux ne représentaient pas correctement les personnages.

La reproductibilité des PDF suppose des manuscrits, images, polices, versions de Pandoc et Edge, et un environnement inchangés. La régénération des images dépend également du modèle et de l'environnement de calcul ; les conserver garantit leur réutilisation à l'identique.

## Reconstruction des EPUB

Avec Python 3 et Pandoc installés, exécuter `exports\rebuild_epub_books.bat` depuis l'Explorateur ou la ligne de commande. Les fichiers EPUB illustrés sont créés dans `exports`. Pour ne reconstruire qu'un livre, ajouter par exemple `--book I`. Si nécessaire, `PANDOC` peut contenir le chemin complet de l'exécutable Pandoc. Les chapitres et illustrations manquants sont signalés comme une erreur.

## Livres audio multivoix

Installer Python 3.12, FFmpeg (avec `ffmpeg` et `ffprobe` dans le PATH) et Ollama, puis démarrer Ollama et installer les modèles `qwen2.5:3b` et `qwen2.5:7b`. Configurer `OLLAMA_MODELS` sur D: pour y stocker les modèles. Si l'environnement virtuel n'existe pas encore, depuis la racine :

```bat
python -m venv .venv
.venv\Scripts\python -m pip install torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -r requirements.txt
```

Le rendu exige un GPU CUDA et le modèle Qwen3-TTS-12Hz-1.7B-CustomVoice préparé en FP16 dans `models\Qwen3-TTS-1.7B-CustomVoice-fp16`.

Le pipeline comporte deux phases locales :

1. **Analyse** : Ollama propose un locuteur et une orientation expressive pour chaque segment. Un fichier modifiable `exports\orientations\Livre-1\chapitre-001.json` est créé par chapitre. Les fichiers existants sont conservés ; si la source change, l'analyse s'arrête pour éviter d'écraser une révision.
2. **Validation humaine et rendu** : vérifier et modifier les fichiers JSON, notamment les attributions incertaines, puis vérifier `exports\orientations\voix.json`. Ce dernier associe chaque nom à un timbre Qwen et une description de personnage, communs aux trois livres. Le modèle propose neuf timbres : certains personnages partagent donc un timbre, avec une consigne différente. La génération refuse les locuteurs `INCONNU`, les profils manquants et les données invalides. Elle annonce les chapitres et assemble les sorties `exports\Livre-1_Audiobook.mp3`, etc.

Lancer `exports\rebuild_audio_books.bat`, ou ajouter `--book 1` pour traiter un seul livre. Le script s'arrête après l'analyse ; taper `OUI` après vérification pour démarrer la génération. Les options `--model` et `--speaker-model` sélectionnent les modèles Ollama d'orientation et d'attribution. Chaque phase peut également être lancée séparément :

```bat
.venv\Scripts\python main_audiobook.py analyse --book 1
.venv\Scripts\python main_audiobook.py generer --book 1 --approuve
```

Le marqueur `--approuve` confirme que la révision humaine a réellement eu lieu. Pour réanalyser un chapitre modifié, déplacer ou supprimer explicitement son ancien fichier d'orientation après avoir sauvegardé les corrections. Les chapitres audio terminés restent dans `exports\temp_audio` pour permettre la reprise après interruption ou assemblage. Aucun manuscrit n'est envoyé à un service de synthèse distant.

L'option `--auto` permet, explicitement et sans confirmation, de générer après l'analyse. Les JSON sont conservés pour une révision ultérieure ; les locuteurs `INCONNU` interrompent le rendu.

### Taxonomie et limites

Chaque segment comprend `texte`, `locuteur`, `fiabilite_locuteur` (`explicite`, `deduit` ou `incertain`), `type`, `emotion`, `valence` (−1 à 1), `activation`, `dominance` et `intensite` (0 à 1), `intention` et `vocalisation`. La fiabilité est une indication du modèle, non une probabilité calibrée. Les dimensions valence–activation–dominance sont utilisées dans des corpus de reconnaissance des émotions vocales comme IEMOCAP ; les étiquettes émotionnelles détaillées s'inspirent notamment de la [Geneva Emotion Wheel](https://archive-ouverte.unige.ch/unige:97384), sans prétendre en reproduire une mesure clinique. L'intention communicative et le type de vocalisation sont des champs séparés.

Les valeurs acceptées pour `type` sont `chapitre`, `narration` et `dialogue`. Les émotions acceptées sont `neutre`, `interet`, `joie`, `plaisir`, `amour`, `admiration`, `soulagement`, `fierte`, `espoir`, `compassion`, `tristesse`, `peur`, `colere`, `degout`, `mepris`, `honte`, `culpabilite`, `regret`, `deception`, `inquietude`, `surprise`, `confusion` et `ennui`. Les intentions acceptées sont `narrer`, `informer`, `questionner`, `repondre`, `ordonner`, `rassurer`, `persuader`, `avertir`, `menacer`, `protester`, `plaisanter`, `hesiter`, `confier`, `saluer`, `remercier` et `autre`.

Il s'agit ici d'**orientations inférées du texte**, pas de reconnaissance d'émotions à partir d'une voix enregistrée : elles sont incertaines, tout comme l'identification des locuteurs. Un essai limité a retrouvé 7 attributions sur 22 ; une vérification systématique est nécessaire. Le modèle reçoit des consignes textuelles pour l'émotion, l'activation, l'intensité, l'intention et la vocalisation ; il n'est pas garanti qu'il les respecte, notamment pour le rire, les sanglots et les soupirs. Les timbres disponibles ne sont pas natifs du français et peuvent avoir un accent. Une narration confiée à Koda peut être indiquée avec `locuteur: "KODA"` et `type: "narration"` ; une consigne narrative est alors ajoutée à sa voix. Les incises utilisant certains verbes de parole sont séparées pour être lues par le narrateur ; les autres peuvent encore être lues avec la voix du personnage. Les orientations existantes sont conservées et ne bénéficient pas automatiquement de ce découpage. Écouter et corriger le résultat reste indispensable.

Vérifier les licences de Qwen3-TTS et des modèles Ollama choisis avant redistribution.
