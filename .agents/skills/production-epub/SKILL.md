---
name: production-epub
description: Reconstruit et vérifie les livres Oark au format EPUB ou PDF à partir des manuscrits et illustrations locaux.
---

# Production EPUB et PDF

1. Lire `00 - SOMMAIRE DES MANUSCRITS.md` et l'état des exports avant d'agir ; trois EPUB et trois PDF existaient lors du relais, sans garantie qu'ils soient encore à jour.
2. L'outil déterministe est `scripts\build_books.py` ; les lanceurs sont `exports\rebuild_epub_books.bat` et `exports\rebuild_pdf_books.bat`. Lire leur aide et vérifier les dépendances Pandoc et, pour le PDF, Microsoft Edge avant d'installer quoi que ce soit.
3. Depuis la racine, lancer par exemple `exports\rebuild_epub_books.bat --book I` uniquement si la reconstruction est demandée ; elle peut remplacer un export existant. Placer les temporaires sur D:.
4. Contrôler les erreurs, le nombre et l'ordre des chapitres, les illustrations et le fichier final. Un code de sortie zéro ne prouve pas à lui seul la qualité du contenu.
5. Consigner commande, résultat, fichiers et limites dans `journal_ia`.
