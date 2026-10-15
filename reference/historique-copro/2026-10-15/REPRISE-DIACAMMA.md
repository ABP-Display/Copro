# Suivi de la reprise intégrale de Diacamma

> Complément du 15 octobre 2026 : les descriptions ci-dessous retracent les livraisons antérieures. Le [cycle comptable](COMPTABILITE-CYCLE.md), l’[AG guidée](AG-OUTILS.md) et l’[audit courant](AUDIT-FONCTIONNALITES.md) remplacent les anciennes listes de fonctions restantes.

## État au 14 octobre 2026

**La reprise intégrale n'est pas terminée.** La présence du code dans `reference/`
ne signifie pas que ses fonctions existent dans l'interface React.
L'inventaire `../reference/diacamma-inventory.json` répertorie les classes de modèles et les
294 classes d'actions/écrans trouvées dans les sept modules installés. Ce nombre
inclut des actions techniques distinctes, et n'est pas un nombre de fonctions
métier indépendantes. Les compteurs de tests sont ceux du code de référence,
pas des tests exécutés dans la nouvelle application.

| Module | Classes dans models.py | Actions / écrans | Méthodes de test présentes |
|---|---:|---:|---:|
| Copropriété | 21 | 69 | 110 |
| Application Syndic | 0 | 0 | 4 |
| Comptabilité | 13 | 93 | 141 |
| Règlements | 7 | 35 | 2 |
| Contacts | 14 | 57 | 47 |
| Documents | 4 | 17 | 15 |
| Courriels | 4 | 23 | 47 |

Les modèles techniques et les champs virtuels des classes d'origine ne sont
pas transposables tels quels : ils dépendent de Lucterios. La nouvelle
application réimplémente des comportements et doit faire vérifier leur parité
avant qu'une action soit marquée `react_parity_verified` dans l'inventaire.
Ces indicateurs restent tous faux à ce stade : la présence d'un écran similaire
ne constitue pas une vérification complète.

## Fonctions exécutables dans React

- Annuaire, lots, tantièmes généraux, recherche et validation.
- Comptes copropriétaires générés à partir du courriel, mots de passe hashés,
  changement obligatoire à la première connexion, réinitialisation explicite.
- Courriel préparé par un lien `mailto:` ; l'application n'envoie rien seule.
- Lecture seule avec contrôles côté serveur et masquage des données privées.
- Catégories de charges et budget annuel **indicatif**.
- Clés générales ou tantièmes spécifiques à chaque lot.
- Exercices sans chevauchement ; vérification des dates de comptabilisation.
- Appels de fonds en brouillon, prévisualisation et validation de la répartition.
- Répartition exacte au centime selon les plus forts restes, figeant lot,
  copropriétaire, tantièmes et montant à la validation.
- Factures fournisseurs, règlements intégraux ou partiels et encaissements
  copropriétaires.
- Journal d'écritures équilibrées, comptes personnalisés et balance générale CSV.
- Mouvement bancaire net par exercice.
- Publication d'un instantané de synthèse globale accessible aux membres.
- Verrouillage technique d'un exercice (pas une clôture réglementaire complète).
- Gestion comptable : plan éditable, import explicite et idempotent du plan
  français fourni par Diacamma, journaux configurables et journal par défaut.
- Centres analytiques, affectation des écritures et budgets par exercice,
  compte et centre analytique facultatif.
- Modèles d'écritures équilibrées, réutilisation à une date choisie et
  contrepassation des écritures manuelles, sans effacer les originaux.
- Rapports filtrables : balance, grand livre avec solde antérieur à la période,
  journal, compte de résultat, bilan à date et budget/réalisé ; export CSV et
  impression/enregistrement PDF par le navigateur.
- Configuration des coordonnées, longueur des codes comptables, analytique
  obligatoire, préfixe des rapports et date du jour par défaut.
- Administration des rôles gestionnaire/lecture et de l'activation des comptes
  par le superadministrateur ; journal des opérations comptables et de configuration.
- Paiements fournisseurs successifs, historique et reste à payer, avec reprise
  des anciens règlements intégraux sans création de nouvelles écritures.
- Balance auxiliaire native des copropriétaires (comptes 450), avec solde avant
  période, débits/crédits et solde final, réservée aux gestionnaires.
- Documents PDF/PNG/JPEG jusqu'à 10 Mo : dossiers, recherche, dépôt privé par
  défaut, versions, partage explicite avec tous les membres, archivage/restauration.
  Les versions précédentes sont téléchargeables par les gestionnaires uniquement.
- Annuaire des entreprises, contrats avec dates/préavis et coûts déclarés,
  attestations liées et alertes d’accueil ; choix d’un fournisseur dans les devis.
- Annonces en brouillon, publication explicite, retrait et archive/restauration
  dans le portail membre. Aucun envoi automatique.

La comparaison avec les menus de l'instance locale est détaillée dans
`COMPARAISON-DIACAMMA.md`.

## Limites financières de ce premier socle

La méthode d'arrondi native conserve exactement le total, mais sa parité avec
toutes les situations Diacamma reste à établir. Les montants sont en EUR et
les écritures créées par ces premiers parcours utilisent un plan réduit
(401, 450, comptes 512 de la banque choisie, 601, 701). Il ne remplace pas le plan comptable de copropriété
complet ni les sous-comptes auxiliaires et les traitements par pays de Diacamma.
Le bouton « Compléter le plan français » ajoute les comptes de la référence
sans écraser les comptes existants. L'import n'est pas automatique.

La trésorerie affichée est un **mouvement net** sur l'exercice, pas un solde
bancaire certifié. Les soldes d'ouverture, reports et rapprochements ne sont
pas encore repris. Les factures créent une dette fournisseur et leur règlement
intégral ou partiel ; la ventilation/régularisation définitive des dépenses par
propriétaire n'est pas encore disponible. Les règlements restent rattachés à
l'exercice de la facture : le règlement inter-exercices requiert encore la reprise
des reports et des comptes auxiliaires.

Les écritures validées ne sont pas modifiables ou supprimables par l'API.
La contrepassation est disponible pour les écritures manuelles uniquement : les
appels de fonds, factures et règlements nécessitent encore leurs propres parcours
d'annulation. Le journal des opérations n'est pas un audit exhaustif de toutes les
actions utilisateur. Les contrôles comptables de clôture restent à développer.
Les budgets de catégories restent indicatifs ; les budgets comptables sont
désormais saisis séparément par exercice et compte dans Gestion comptable.
Le bilan est une synthèse des comptes et du résultat, pas une annexe réglementaire
de copropriété ni un état certifié. Les filtres de tiers/journal/analytique donnent
des vues partielles ; un filtre peut donc déséquilibrer la présentation du bilan.

## Périmètre restant, à ne pas omettre

1. **Copropriété** : indivision et contacts multiples, clés secondaires,
   charges récupérables/locatives, régularisations, travaux exceptionnels,
   avances, fonds, historique des mutations et situations individuelles.
2. **Comptabilité** : plan par pays, tiers et sous-comptes, lettrage,
   parité avancée des modèles et de l'analytique, reports,
   clôture complète, contrôles et réouverture encadrée.
3. **Rapports** : balance auxiliaire des fournisseurs structurés, annexes de copropriété, éditions PDF
   produites côté serveur, modèles personnalisables et archives ; parité détaillée
   des états natifs avec Diacamma.
4. **Règlements et banque** : affectation/lettrage,
   rapprochements, remises de chèques, import de relevés, comptes multiples,
   intégrations bancaires et autres parcours présents dans `payoff`.
5. **Documents** : sous-dossiers imbriqués, droits fins par groupe/personne,
   autres formats, éditeurs collaboratifs et parité des comportements Lucterios.
   Les dossiers, dépôts, téléchargements contrôlés, partage global, versions et
   archivage sont disponibles dans le module natif.
6. **Contacts et courriels** : relations complexes, reprise de tiers historiques, imports/exports,
   groupes, publipostage, pièces jointes, modèles, envoi SMTP et suivi des envois.
7. **Paramètres et administration** : toutes les actions de configuration,
   personnalisations, impressions, traductions, sauvegardes et restauration.

## Votes et assemblées générales

Aucun modèle ni écran de vote n'a été trouvé dans les sources installées
`condominium`, `syndic`, `accounting`, `payoff`, `contacts`, `documents`, `mailing`.
Les mentions d'assemblées générales dans la documentation concernent notamment
la clôture des comptes. Le module natif `governance` apporte désormais la préparation
des AG, les résolutions, leur archivage et des simulations de majorité conservées.
Ce développement distinct ne constitue pas une reprise Diacamma. Les convocations,
présences, pouvoirs, votes individuels, signatures et notifications de PV restent
à développer. Voir `AG-OUTILS.md` pour le périmètre et les règles de calcul.

## Validation

Les 112 tests natifs passent sur PostgreSQL. Ils couvrent les accès, la confidentialité, la conservation du
total au centime, l'équilibre des écritures, les doubles validations, la
protection des exercices verrouillés, les synthèses publiées, les modèles,
la contrepassation, les budgets/rapports, paiements partiels, migrations de règlements,
documents/versions/partage et les permissions d'administration. Ils n'établissent
pas encore la parité avec les centaines de parcours d'origine.
La reprise des données réelles de Diacamma n'a pas été lancée.

L’[audit du cahier de fonctionnalités](AUDIT-FONCTIONNALITES.md) distingue les
43 parcours utilisables de 155 exigences plus larges. Le [guide fournisseurs et annonces](FOURNISSEURS-CONTRATS-ANNONCES.md)
décrit les ajouts natifs de cette revue ; ces ajouts ne prouvent pas la parité
avec les actions Diacamma correspondantes.

Les fournisseurs identifiés sont désormais reliés aux factures et lignes 40, avec pièce de GED et balance auxiliaire. Les banques disposent de comptes 512 distincts, les règlements/encaissements choisissent une banque et les transferts sont enregistrés avec protection contre les doublons. Les budgets incluent commentaire et comparatif précédent. Voir le [guide financier](BANQUES-FOURNISSEURS-BUDGETS.md). Reprise de l’historique, lettrage, à-nouveaux, rapprochement et clôture restent à compléter.
