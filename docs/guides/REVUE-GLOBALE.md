# Revue globale de Copro.

État du 15 octobre 2026. Le suivi courant repose sur le cahier bénévole/coopératif et
l’[audit détaillé](AUDIT-FONCTIONNALITES.md). La [couverture](COUVERTURE-FONCTIONNELLE.md)
distingue les parcours utilisables des exigences encore partielles.

## Accès et collaboration

Les comptes copropriétaires voient leur compte et les informations explicitement publiées.
Le conseil et le contrôleur ont une consultation des pièces de gestion adaptée à leur
mission. Les mandats datés et l’accès permanent de gestion sont distingués. Les contrôles
sont appliqués aux API et aux fichiers, pas seulement aux boutons de l’interface.

La préparation des dépenses, les avis du conseil et leur comptabilisation sont séparés.
Les avis motivés, retraits, désignations et rapports sont conservés avec leur auteur et
leur date. Un contrôleur ne réécrit pas son rapport après finalisation ; les changements
des comptes depuis son contrôle sont signalés.

## Parcours et utilisation

Les menus sont regroupés par thèmes. Une catégorie présente ses sous-pages et leur rôle ;
sa flèche ouvre les raccourcis. Le menu peut être réduit et conserve une navigation mobile.
Le guide AG explique les étapes, vérifications, termes et difficultés courantes.

Les opérations financières passent par les parcours métier : écritures équilibrées,
répartitions, contrôle des règlements, rapprochement, régularisation et clôture. L’AG
conserve les données de séance et les preuves des opérations réalisées à l’extérieur.

## Vérifications et suites

Les tests utilisent PostgreSQL et des pièces temporaires. La compilation TypeScript/Vite
et les contrôles navigateur complètent les tests métier et de permissions. Les décomptes
et résultats du dernier contrôle sont dans l’audit courant.

Les prochaines priorités sont la sauvegarde/restauration vérifiée, la fiabilisation des
modèles et cas réglementaires, le calendrier annuel, les travaux/sinistres et la reprise
des données. La gestion réelle de plusieurs copropriétés nécessite encore une isolation
complète des données. Voir les [prochains chantiers](PROCHAINS-CHANTIERS.md).
