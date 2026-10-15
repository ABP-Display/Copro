# Prochains chantiers de Copro.

Priorisation du 15 octobre 2026, d’après le cahier bénévole/coopératif et les
parcours réellement disponibles. Le cycle comptable et l’AG papier/scans sont
utilisables ; cela ne termine pas toutes les exigences comptables et AG du cahier.

## Responsabilités et conseil syndical : parcours livré

Le [guide du conseil](CONSEIL-SYNDICAL.md) décrit les mandats datés, les accès ciblés,
la préparation des dépenses, les avis motivés, le contrôle avant règlement/sélection
de devis et les rapports indépendants. Le mode coopératif réunit la présidence et
le syndic ; leurs droits dépendent du mandat de membre du conseil.

Les réunions propres au conseil, délégations collectives détaillées, personnes non
propriétaires éligibles, cas dérogatoires et passation complète restent à compléter.
Les accès permanents de gestion demeurent distincts des droits des mandats.

## Sauvegarde, restauration et double authentification : parcours livré

Le [guide de sauvegarde et de sécurité](SAUVEGARDE-SECURITE.md) décrit les archives
chiffrées base/pièces, la restauration isolée comparée, la rétention, la reprise
après interruption, le lanceur Windows et les consignes de programmation Linux.
La double authentification TOTP, les codes de secours, la règle obligatoire pour
les gestionnaires et la récupération serveur sont disponibles. La fréquence, les
copies hors site et la surveillance des échecs restent à configurer sur le serveur.

## Documents et financements : compléments livrés

Les annexes annuelles sont structurées avec comparatifs, tiers non compensés,
contrôles et empreinte ; les pièces de l’approbation des comptes sont reliées au
dossier relu. Les minima du fonds/PPT, les seuils cumulatifs de suspension, les
trois catégories d’avances, la vente, les restitutions et l’affectation PPT aux travaux sont disponibles.
Voir le [guide](DOCUMENTS-FONDS-AVANCES.md). Une validation métier des modèles reste
nécessaire ; prêts/aides et situations exceptionnelles restent à compléter.

## Prochain focus recommandé : guider l’année de gestion

Rendre le profil de l’immeuble et le calendrier des obligations compréhensibles,
puis relier entretien, travaux, pièces et décisions. Maintenir en parallèle la
validation des modèles sur des dossiers représentatifs.

## Ordre des autres améliorations

| Priorité | Chantier | Prochain livrable concret | Exigences concernées |
| --- | --- | --- | --- |
| P0, exploitation | Configurer la protection du serveur | Programmer les sauvegardes avec l’outil livré, conserver une copie hors site, surveiller les échecs et vérifier périodiquement une reprise ; compléter supervision et audit inaltérable | 7.07, 7.09 à 7.12 |
| P0 | Fiabiliser les documents et cas réglementaires | Confronter les annexes 1 à 5 et documents AG aux modèles applicables, corriger les écarts, tester des dossiers représentatifs et obtenir une validation métier | 4.2.18, 4.5.04, 4.5.14, 5.01 à 5.04 |
| P1 | Compléter les règles comptables | Aides/prêts spécifiques, mode simplifié avec critères d’éligibilité et engagements de fin d’exercice | 4.2.08, 4.2.09, besoin transverse du mode simplifié |
| P1 | Guider l’année de gestion | Profil de l’immeuble, calendrier annuel des comptes/budget/AG, échéances contextualisées, carnet d’entretien et checklist avec sources et statut | 4.8.02 à 4.8.04, 4.8.07, 4.14, 4.15.02 |
| P1 | Terminer travaux et sinistres | Relier devis, décision, commande, dépenses, chantier, réception, réserves, garanties et dossier d’assurance | 4.7, 4.8.01, 4.8.05, 4.10 |
| P1 | Faciliter la reprise des données | Import contrôlé des lots/propriétaires/tantièmes, rapprochement des soldes, détection des doublons, aperçu avant import et rapport des anomalies | 4.1.07, 6.08 |
| P1/P2 selon l’usage | Renforcer l’extranet | Signalements avec photos, demandes écrites des copropriétaires, suivi des réponses, recherche et historique personnel paginé | 4.5.03, 4.8.01, 4.12, 4.13, 6.06 |
| P2 | Connecter les services utiles | Choisir les prestataires de recommandé/signature, puis connecter envoi et récupération des preuves ; étudier ensuite vote direct des membres et visio | 4.5.07, 4.5.12, 4.5.15, 6.02, 6.03 |
| P2, avant une deuxième copropriété | Isoler les copropriétés | Rattacher toutes les données à un syndicat, filtrer chaque accès et tester l’absence de fuite entre deux copropriétés ; rendre le sélecteur réellement fonctionnel | Besoin multi-copropriété, 7.08 |

P0 désigne ce qui fiabilise l’usage partagé et les données. P1 complète les parcours
quotidiens. P2 dépend du besoin réel et des choix de services ; ce n’est pas un
calendrier de livraison promis. La validation métier des modèles doit accompagner
leur développement, sans attendre les connecteurs.

## Points à conserver dans le périmètre

- La protection des données : inventaire des traitements, information des personnes,
  droits d’accès/export, conservation et gestion des prestataires (§7). Elle accompagne
  les rôles, l’extranet et les services connectés.
- Les mutations et passations : dossier pour le notaire, pièces de vente, cas
  d’indivision/démembrement, export de passation avec fichiers et accès de secours
  (§4.1.04, 4.9, 4.15.05). Les mutations comptables actuelles ne couvrent pas tout cela.
- Le recouvrement : vrais accords de paiement, frais justifiés, preuves et dossiers
  de procédure (§4.4). Le lettrage et le vieillissement existent déjà.
- La maintenance : accessibilité, mises à jour, supervision et tests adaptés (§7).

TVA du syndicat, paie, prêts collectifs, subventions ou procédures exceptionnelles
sont à traiter si la situation de la copropriété les rend utiles. Les fonctions
de cabinet professionnel ne sont pas dans la cible.

## Choix déjà actés

Les analyses restent métriques et locales avec alertes d’accueil. Aucun moteur IA
puissant n’est prévu à ce stade. Les accès utilisent un courriel préparé dans la
messagerie ; un connecteur d’envoi ultérieur fera l’objet d’un choix explicite.
Le mode « Asso. » reste reporté.

Le sélecteur actuel ne suffit pas à gérer plusieurs copropriétés ; une archive
JSON ne contient pas les fichiers des pièces ; un suivi de notification ne réalise
pas l’envoi recommandé. Ces distinctions évitent de reprendre un chantier déjà
partiellement livré ou de présenter un socle comme une fonction terminée.

Sources du projet : [cahier fourni](../reference/cahier-fonctionnalites.md),
[audit détaillé](AUDIT-FONCTIONNALITES.md), [périmètre](PERIMETRE-PRODUIT.md),
[cycle comptable](COMPTABILITE-CYCLE.md), [parcours AG](AG-OUTILS.md).
