# Revue de Copro — mise à jour du 14 octobre 2026

Cette revue porte sur le code natif React/Django, les accès et les parcours
disponibles. Elle ne certifie pas une reprise intégrale de Diacamma, la conformité
des comptes ou tous les scénarios possibles du code de référence.

## Navigation et personnes débutantes

- Le titre ou l'icône d'une catégorie ouvre une présentation de son rôle.
- Les cartes expliquent chaque section et ouvrent directement son écran.
- La flèche du menu déroule les raccourcis sans imposer la présentation.
- Le volet se réduit aux icônes sur ordinateur ; les libellés apparaissent au
  survol et au focus clavier. La préférence est mémorisée dans ce navigateur.
- La barre de défilement est masquée, mais le défilement reste actif.
- Sur mobile, le volet conserve les libellés et se ferme après une navigation.
- Chaque sous-page a une explication contextualisée. Les termes « analytique »,
  « contrepassation » et les soldes individuels sont expliqués avant utilisation.
- L'action de création d'exercice s'appelle « Nouvel exercice ». Un exercice
  figé est nommé « verrouillé », pour le distinguer d'une clôture complète.
- Les factures montrent payé/reste à payer et l'historique des règlements.
- Un document est privé lors du dépôt. Le partage fait l'objet d'une confirmation
  qui explique son accès par tous les copropriétaires connectés.

## Corrections fonctionnelles et de confidentialité

- Accès direct à la saisie manuelle préservé après la réorganisation du menu.
- Règlements fournisseurs partiels, validation du reste à payer et protection
  des paiements contre une contrepassation manuelle incohérente.
- Migration des anciens règlements complets sans nouvelle écriture comptable.
- Balance auxiliaire des copropriétaires avec solde antérieur à la période.
  Ces données restent réservées aux gestionnaires.
- Documents, dossiers, versions et archivage réversible. L'API de téléchargement
  vérifie la session et le partage ; connaître l'identifiant d'un document privé
  ne suffit pas à le télécharger. Les anciennes versions sont privées.
- Modifier des coordonnées ou réinitialiser un mot de passe ne réactive plus un
  compte suspendu par l'administrateur principal.
- Un propriétaire lié à un accès gestionnaire ne peut pas être supprimé ou privé
  de courriel depuis l'annuaire. Son rôle doit être traité dans l'administration.
- Le changement obligatoire du mot de passe temporaire reste applicable après
  une promotion au rôle gestionnaire.

## Optimisations

- Les pages comptables et financières chargent leurs ressources utiles plutôt
  que l'ensemble des modules, des écritures et des utilisateurs à chaque ouverture.
- Une réponse ancienne ne remplace plus les données d'une nouvelle sous-page.
- Le chargement des écritures ne lance plus une requête de contrepassation par
  ligne. Un test vérifie que le nombre de requêtes reste constant quand la liste
  passe d'une à six écritures.
- Les comptes liés aux propriétaires sont préchargés dans l'annuaire.
- Les comptes inactifs ne sont plus proposés dans la saisie comptable simple.

## Vérifications

112 tests Django sur PostgreSQL, compilation TypeScript/Vite, vérification des
migrations et contrôles manuels des menus, catégories et formulaires sur ordinateur
et mobile. Les tests utilisent une base séparée et des fichiers temporaires.
La vérification dans le navigateur ne remplace pas un test utilisateur avec les
futurs gestionnaires bénévoles et des opérations représentatives de leur immeuble.

## Reprise Diacamma encore nécessaire

La présence des sources dans `reference/` n'est pas une intégration native.
Le détail reste dans `REPRISE-DIACAMMA.md` et l'inventaire des actions.

Priorités fonctionnelles restantes : régularisation des charges et mutations,
reprise de comptes fournisseurs historiques, lettrage, rapprochement bancaire, remises de
chèques, reports/clôture complète et annexes de copropriété ; ensuite imports,
publipostage, modèles d'impression et permissions documentaires fines.
Les votes/AG n'ont pas été trouvés dans les modules Diacamma installés. Un premier
module natif de préparation et de simulation est livré ; le déroulement officiel
(convocations, présences, pouvoirs, signatures et notifications de PV) reste à développer.

L'application gère toujours une seule copropriété. Le sélecteur prépare son
évolution visuelle ; il n'ajoute pas une isolation de données entre immeubles.
Les fichiers documentaires et PostgreSQL sont dans deux volumes distincts à
sauvegarder ensemble. Une interface de sauvegarde/restauration n'est pas livrée.
Les fonctions financières avancées doivent être comparées à des cas Diacamma
représentatifs avant de considérer leur parité comme vérifiée.

L’[audit du cahier fourni](AUDIT-FONCTIONNALITES.md) ajoute un suivi exhaustif
des 155 exigences des sections 4 à 7, avec preuves et priorités. L’annuaire
fournisseurs, les contrats/préavis, les attestations et les annonces sont livrés
pour un suivi manuel. Les auxiliaires fournisseurs natifs, banques et budgets commentés sont aussi livrés.
Restent les commandes, circuits de validation du conseil et obligations contextualisées.
