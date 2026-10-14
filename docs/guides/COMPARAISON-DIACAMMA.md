# Comparaison de l'instance locale et de Copro

Inspection du 13 octobre 2026 de `http://localhost:8080/web/index.html`, connecté
en administrateur. Consultation des menus et des écrans de configuration sans
modifier les données de cette instance. Les sources présentes dans `reference/`
complètent cette inspection ; celle-ci n'est pas un test exhaustif de chaque action.

| Menu observé dans Diacamma | Disponible dans Copro | Écart restant |
|---|---|---|
| Gestion comptable / Écritures | Saisie équilibrée, filtres, contrepassation manuelle | Modification encadrée, lettrage, annulations métier |
| Plan comptable | Création, édition, activation, import du plan français de référence | Autres pays, auxiliaires structurés |
| Comptabilités analytiques | Centres, affectations des écritures, filtres | Parité des traitements et de la clôture analytique |
| Modèles d'écriture | Modèles de lignes équilibrées et application | Options avancées de la référence |
| Rapports / Bilan | Synthèse à date, résultat inclus | Présentation réglementaire, reports initiaux |
| Compte de résultat | Charges, produits, résultat, budgets annuels, comparatif précédent et commentaires d’écarts | Annexes et présentations personnalisées |
| Grand livre | Mouvements, solde avant période et solde progressif | Éditions détaillées de référence |
| Balance | Débits, crédits, soldes, comptes non soldés, balances auxiliaires copropriétaires et fournisseurs | Reprise des tiers historiques et lettrage |
| Tiers / Remises de chèques | Copropriétaires, factures fournisseurs textuelles, encaissements | Annuaire de tiers comptables, remises et rapprochement |
| Configuration comptable / Exercices | Exercices et verrouillage technique | Clôture complète, à-nouveaux et réouverture |
| Configuration comptable / Journaux | Journaux configurables et journal par défaut | Parité des options spécifiques |
| Configuration comptable / Paramètres | Codes, analytique obligatoire, préfixe, date par défaut ; EUR à 2 décimales | TVA, autres monnaies/pays, champs personnalisés et e-facturation |
| Configuration générale / Nos coordonnées | Nom, coordonnées et immatriculation | Ensemble des préférences Lucterios |
| Groupes, utilisateurs, sessions, tâches, audit | Rôles lecture/gestionnaire, activation, historique partiel | Groupes fins, sessions, tâches et audit exhaustif |
| Configuration copropriété / Nature relation / Charges récupérables | Clés et quotes-parts simples | Relations multiples et charges récupérables |
| Contacts / Imports / Codes postaux / Possessions | Annuaire et lots | Imports et sous-modules de contacts |
| Dossiers / Documents | Dossiers, PDF/images, versions, publication, archivage et téléchargement contrôlé | Sous-dossiers, permissions fines et éditeurs collaboratifs |
| Courrier / SMS / Patrons / Étiquettes | Courriel d'accès préparé et synthèses publiées | Courrier/SMS, modèles et étiquettes |
| Règlements fournisseurs | Règlements partiels successifs, historique et reste à payer | Affectation avancée, lettrage et paiements inter-exercices |

## Accès aux nouveaux écrans

- **Gestion comptable** : plan, analytique, budgets, modèles, écritures.
- **Rapports comptables** : balance, grand livre, journal, résultat, bilan et budget.
- **Administration** : coordonnées et paramètres, journaux, utilisateurs, historique.
- **Documents** : bibliothèque, dossiers, partage et versions.

Le titre d'une catégorie ouvre une page de présentation expliquant ses sections.
Sa flèche déroule directement les sous-pages. Le volet est scrollable sans barre
visible, peut se réduire aux icônes sur ordinateur, et conserve ce choix localement.

Les écrans comptables restent réservés aux gestionnaires. Les utilisateurs en
lecture continuent de voir les données globales publiées, sans les coordonnées
ou soldes individuels des autres copropriétaires. Seul un superadministrateur
peut changer les rôles et activer/désactiver les comptes. Il ne peut modifier ses
propres droits ni ceux d'un autre superadministrateur par cet écran.

Pour importer le plan français : Gestion comptable → Plan comptable →
« Compléter le plan français ». Cette opération ajoute les comptes manquants,
préserve les comptes existants et reste sûre à répéter.

Les rapports s'impriment ou s'enregistrent en PDF via la boîte d'impression du
navigateur. Les exports CSV neutralisent les cellules susceptibles d'être
interprétées comme des formules. Un budget est annuel, même lorsque la période
des mouvements est filtrée. Le bilan cumule depuis le début de l'exercice jusqu'à
la date de fin ; il ne possède pas de date de début indépendante.

## Validation et limites

112 tests sur PostgreSQL, compilation TypeScript/Vite et vérification des écrans
dans le navigateur. Les tests utilisent une base séparée. Aucun import des
données réelles Diacamma, aucune suppression de données existantes.

Cette livraison élargit l'application mais ne constitue pas la reprise intégrale
de Diacamma. Voir `REPRISE-DIACAMMA.md` pour les fonctions restantes, en particulier
les régularisations, annexes, rapprochements et clôture complète. La préparation
des AG et les simulations sont disponibles ; le déroulement officiel reste à
développer (voir `AG-OUTILS.md`).

Au 14 octobre 2026, l’annuaire fournisseurs, les contrats/préavis, les attestations
et les annonces ont été ajoutés. Les fournisseurs comptables natifs, banques et commentaires budgétaires sont désormais livrés.
La reprise des fournisseurs historiques reste à traiter. Le [rapport d’audit](AUDIT-FONCTIONNALITES.md) suit les exigences
du cahier fourni, sans les confondre avec le nombre d’actions Diacamma.
