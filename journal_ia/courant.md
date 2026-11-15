# Journal actif des IA

Entrées récentes ; archives dans `archives`.

## 2026-11-14T11:26:40+01:00 — Relais Antigravity et journal

Création de AGENTS.md, HISTORIQUE_IA.md, STUDIO_IA.md, deux skills, hook de démarrage et gestionnaire de journal avec rotation à 16000 octets. Vérifications : 21 tests unitaires réussis ; hook simulé et inventaire vérifiés. État observé : 15 orientations Livre 1, aucun audiobook final ; GPU précédemment arrêté à 90 C, 75 C à 0 % lors du contrôle ponctuel. Hook non testé dans Antigravity lui-même. Suite : diagnostiquer refroidissement, améliorer diarisation et voix/vocalisations, puis produire et vérifier les trois livres.

## 2026-11-14T11:27:08+01:00 — Skills et validation du hook

Ajout des skills environnement-local et production-epub pour compléter reprise-projet et production-audiobook. Le hook SessionStart et sa configuration JSON ont été testés localement via cmd.exe ; intégration dans Antigravity encore à vérifier. Aucune installation supplémentaire ni lancement de génération audio.

## 2026-11-14T12:36:21+01:00 — Analyse comparative du canon et réécriture complète V2 dans exports-v2

Mise en pause de l'audio et des illustrations à la demande de l'utilisateur. Extraction et analyse comparative des 10 DOCX canoniques de archives/ face aux 94 chapitres V1 (dilution 94 vs 45 chapitres prévus, chapitres tampons logistiques, tics passifs de Koda, aplatissement des arcs de Bricole et ÉCHO). Création dans exports-v2/ de 01_PLAN_ACTION_CORRECTIVE_ET_REGLES.md, 02_PLAN_DIRECTEUR_TRILOGIE.md, 00 - SOMMAIRE DES MANUSCRITS V2.md et des 45 chapitres de la trilogie (Livre I : 19 ch / 29544 mots ; Livre II : 13 ch / 21590 mots ; Livre III : 13 ch / 19353 mots ; total 70487 mots). Vérification par script Python : réduction de 95 à 100 % des tics passifs, présence des 6 ancres de continuité, 0 occurrence hors-canon. Manuscrits V1 conservés intacts. Prochaine étape : relecture/retours de l'utilisateur sur exports-v2.

## 2026-11-14T12:48:27+01:00 — Purge des niveaux technologiques dans le récit V2 et respect strict du PdV de Koda

Suite au retour de l'utilisateur sur les chapitres 1 et 2 de exports-v2 : (1) Suppression dans les chapitres 01 à 07 du Livre I de toute omniscience prématurée sur les Semeurs, la Terre ou la Sublimation afin que le lecteur découvre ces révélations à travers Koda aux chapitres 07-08. (2) Remplacement intégral dans les 45 chapitres des 3 tomes (113 occurrences) de toute mention méta de 'Niveau 15/28/96' ou 'Indice 96' par des descriptions internes à l'univers, et renommage du chapitre II-08 en 'CHAPITRE 08 - Le Laboratoire de l'Âge d'Or.md'. Mise à jour de la règle 2 dans 01_PLAN_ACTION_CORRECTIVE_ET_REGLES.md.

## 2026-11-14T13:46:23+01:00 — Édition Référence V2 (52 chapitres, 130 134 mots) dans exports-v2

Production et vérification complète de l'Édition Référence de la trilogie dans exports-v2/ : 52 chapitres (Livre I : 21 ch / 53 341 mots ; Livre II : 17 ch / 41 140 mots ; Livre III : 14 ch / 35 653 mots, total 130 134 mots). Intégration des 6 axes validés : 52 épigraphes d'ouverture, 7 nouveaux chapitres (dont l'arc parallèle du caporal Soren Valen sur le front glacé d'Aqi, la vie clandestine avec Bricole à Zêta-3, l'ivresse de puissance de Koda et les bivouacs sous les étoiles/aurores), 10 scènes de mimétisme et d'humour d'ÉCHO (incluant le ressort couic de Bricole), et le secret des yeux d'ambre de Lyss. Contrôle verify_v2.py : 0 mention de niveau technologique, 0 spoiler prématuré, 0 tic passif Koda regarda/nota/vérifia/observa. Prochaine étape : relecture utilisateur et suite selon ses instructions.

## 2026-11-14T14:50:12+01:00 — Révision Règles 11 (Zéro coïncidence) et 12 (Explicitation lexicale) sur les 52 chapitres

Reprise et finalisation complète sur les 52 chapitres de exports-v2/ (passés de 130 134 à 137 511 mots : Livre I 55 849 mots, Livre II 44 182 mots, Livre III 37 480 mots). Application de la Règle 11 (suppression de tout lien de parenté Kael/Tali, remplacement de la réapparition de Tali au pôle par un soldat afistéaan inconnu nommé Yoren sauvé par Borras, et remplacement du voyage physique de la cassette de Soren par l'enregistrement radio d'urgence de 47 secondes de la vanne B-12 relayé par les boîtes noires d'Aqi et capté par ÉCHO) et de la Règle 12 (explicitation sensorielle fluide de chaque terme rare, scientifique, médical, géologique ou philosophique au fil des 52 chapitres). Vérification verify_v2.py : 0 erreur.

## 2026-11-14T14:58:47+01:00 — Génération des 3 EPUB3 V2 dans exports-v2

Création du script déterministe scripts/build_books_v2.py (Pandoc EPUB3, temporaires sur D:, mise en forme CSS incluant les épigraphes en blockquote) et génération vérifiée des trois livres dans exports-v2/ : Oark - Livre I - L'Éveil.epub (21 chapitres, 173 Ko), Oark - Livre II - La Traque.epub (17 chapitres, 135 Ko), Oark - Livre III - L'Héritage.epub (14 chapitres, 114 Ko).

## 2026-11-14T15:28:03+01:00 — Conversion des nombres en chiffres arabes et régénération des 3 EPUB3 V2

Conversion de 2 265 nombres écrits en toutes lettres vers les chiffres arabes sur les 52 chapitres de exports-v2/ (incluant décimaux, pourcentages, heures, mesures, grands nombres avec séparateur d'espace, et correction des composés 17-19 et 97-99), tout en préservant les articles indéfinis (un/une) et les expressions figées. Vérification verify_v2.py (137 014 mots, 0 erreur) et régénération des 3 EPUB3 dans exports-v2/ via scripts/build_books_v2.py.

## 2026-11-14T16:01:39+01:00 — Illustrations fusain-pastel V2 liees et EPUB3 regeneres

58 illustrations fusain et pastels liees dans les 52 chapitres de exports-v2/ (52 en debut de chapitre apres l'epigraphe + 6 moments cles : L1 Ch08/Ch21, L2 Ch13/Ch16, L3 Ch13/Ch14). scripts/build_books_v2.py mis a jour avec --resource-path exports-v2 et controle EPUB/media/. 3 EPUB3 regeneres et verifies : Livre I (21 ch, 23 images, 17050 Ko), Livre II (17 ch, 19 images, 11273 Ko), Livre III (14 ch, 16 images, 9729 Ko). verify_v2.py OK (52/52 chapitres, 0 violation).

## 2026-11-15T14:44:02+01:00 — Configuration du depot GitHub open-source Oark

Ajout de .gitignore (exclusion de .venv, models, wheels, pip-cache, voices, exports/temp_audio, caches), LICENSE (CC BY-SA 4.0 pour les oeuvres litteraires/artistiques et MIT pour les scripts) et README.md. Initialisation Git locale sur main et ajout du remote origin https://github.com/SalokineTerata/oark.git.

## 2026-11-15T14:46:59+01:00 — Ajustements Livre I-III : curseur explications 75%, vouvoiement-tutoiement L2 Ch07, Niveaux 1-100 L2 Ch12

Application des 3 retours de lecture apres le Livre I : (1) Allègement de 121 definitions redondantes ou scolaires sur les 52 chapitres pour ramener le curseur d'explication des notions complexes de 100 % a ~75 % (suppression des doublons inter-chapitres et des gloses dans les dialogues). (2) Maintien strict du vouvoiement d'ECHO envers Koda sur tout le Livre I et le debut du Livre II (Ch 01-07), puis scene de bascule explicite au tutoiement a la fin du Chapitre 07 du Livre II (apres la boiterie par sympathie). (3) Ajout au Chapitre 12 du Livre II (armurerie de Kelar) de la revelation de l'echelle des Niveaux Technologiques 1 a 100 par ECHO : premiers paliers 1-10 et niveau terrestre (8-9), apogee Oarkin (Niveau 28), regression de l'Exode sur Aqi (Niveau 11), remontee Aqine actuelle (Niveau 15) et choc de Koda decouvrant la superiorite Oarkine, puis ascension des dizaines 20, 30, 40, 50, 60, 70, 80, 90 jusqu'au Niveau 96 des Unites et au plafond asymptotique inatteignable du Niveau 100. Regeneration et verification des 3 EPUB3 illustres dans exports-v2/.

## 2026-11-15T14:56:02+01:00 — Reorganisation professionnelle du depot (archives/v1, livres, exports)

Archivage de la V1 (manuscrits V1, illustrations V1, EPUB/PDF V1 et scripts .bat) dans archives/v1/. Promotion de l'Edition Reference V2 vers livres/ (52 chapitres, 58 illustrations, plans directeurs) et des EPUB3 V2 dans exports/. Mise a jour de scripts/build_books_v2.py, scripts/generate_illustrations_v2.py, scripts/journal_ia.py et README.md. Verifications : 21/21 tests unitaires OK, journal_ia.py etat OK (21+17+14 sources), build_books_v2.py OK (3 EPUB3 regeneres et verifies).
