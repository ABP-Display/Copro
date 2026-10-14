# Banques, fournisseurs comptables et budgets

Livraison du 14 octobre 2026, avec 19 nouveaux tests financiers. Le menu regroupe
les pages en cinq thèmes : Votre immeuble, Gestion financière, Entretien &
prestataires, Vie de la copropriété, Outils & paramètres.

## Où retrouver les fonctions

- **Charges & finances** : charges, appels, factures, encaissements/trésorerie,
  comptes bancaires, relances et synthèses partagées.
- **Gestion comptable** : plan, analytique, budgets, modèles et écritures.
- **Rapports comptables** : comptes propriétaires **et fournisseurs**, journaux,
  balance, résultat, bilan et budget/réalisé.
- **Travaux & entretien** : dossiers travaux/sinistres et échéances.
- **Fournisseurs & contrats** : annuaire, contrats, préavis et attestations.
- **Communication** : annonces publiées dans le portail.

Le titre d’une catégorie ouvre son guide ; la flèche ouvre ses raccourcis. Les
points à suivre de l’accueil continuent d’ouvrir la bonne catégorie après le
déplacement des relances et des contrats.

## Identifier les banques

Dans **Charges & finances → Comptes bancaires**, associer chaque banque réelle
à un compte comptable commençant par 512. Les comptes historiques comportant des
écritures et sans fiche bancaire sont signalés. Une association conserve ces
écritures : elle ne les déplace pas et ne crée pas de solde d’ouverture.

Nom, établissement, IBAN déclaré et usage (courant/épargne/fonds travaux) sont
réservés aux gestionnaires. Le format de l’IBAN est contrôlé ; son titulaire et
son existence ne sont pas vérifiés. Le premier compte créé actif est proposé
par défaut ; le bouton dédié permet de choisir un autre compte. Changer le
défaut ne modifie jamais les anciens règlements.

Le compte comptable d’une fiche créée reste fixe, afin de préserver son historique.
Pour désactiver la banque par défaut, choisir d’abord une autre banque active.
Le compte comptable peut aussi être inactif : il n’est alors pas proposé pour un
nouveau règlement.

Le solde cumule les écritures disponibles sur ce compte, tous exercices
confondus, jusqu’à la date choisie. La continuité des soldes dépend de la reprise
initiale ; le rapprochement, les à-nouveaux automatiques et la certification des
soldes restent à développer. L’usage « fonds travaux » est une classification,
sans calcul des cotisations ou droits attachés aux lots.

## Choisir la banque d’un règlement

Les factures et encaissements demandent maintenant le compte bancaire utilisé.
La banque choisie est conservée dans l’historique, avec la date, le montant et
l’écriture. Si aucune banque n’est configurée, le fonctionnement historique
sur 512 reste disponible. Dès que des banques sont configurées, une banque active
doit être choisie ou définie par défaut.

Les règlements de factures restent dans l’exercice de la facture. Le transfert
inter-exercices de dettes nécessite encore les reports et la clôture.

## Enregistrer un transfert effectué

Le formulaire enregistre un transfert **déjà effectué** entre deux banques
différentes. Il crée une écriture BQ équilibrée, conserve la référence et respecte
l’exercice ouvert et la règle analytique. Aucun ordre n’est envoyé à une banque.

Un identifiant d’opération protège les nouvelles tentatives contre les doublons.
Réutiliser cet identifiant avec d’autres données est refusé. Les 100 derniers
transferts sont affichés. La contrepassation manuelle est bloquée pour cette
opération métier ; un parcours d’annulation dédié reste à développer.

## Identifier les fournisseurs dans les factures

Choisir une entreprise dans l’annuaire, ou saisir un nom libre. Une pièce de
la bibliothèque peut être jointe. Pour un fournisseur identifié, les lignes
de dette et de règlement conservent sa référence. Le nom de facture historique
reste conservé si l’entreprise est renommée. Une même référence de facture ne
peut être recréée pour ce fournisseur et cet exercice après un renommage.

Les anciennes factures/écritures sans fournisseur identifié ne sont pas
réaffectées automatiquement à partir d’un nom, pour éviter un rapprochement
erroné. Elles restent dans la rubrique « Fournisseur non identifié » du rapport.

Dans la saisie manuelle, choisir le fournisseur sur la ligne d’un compte 40.
La contrepassation d’une écriture manuelle conserve cette référence. Les factures
et règlements métier restent protégés contre cette contrepassation générique.

## Lire les comptes fournisseurs

**Rapports comptables → Comptes fournisseurs** calcule le solde avant la période,
les débits/crédits et le solde final. Un solde positif représente une dette envers
le fournisseur. Les filtres, CSV et impression/PDF restent réservés aux gestionnaires.
L’état porte sur l’exercice choisi et inclut les soldes reportés par la clôture.
Le lettrage et le paiement d'une dette reprise sont accessibles dans le
[parcours comptable](COMPTABILITE-CYCLE.md). Un fournisseur archivé reste consultable
dans les états historiques.

## Expliquer les écarts budgétaires

Dans **Gestion comptable → Budgets**, renseigner l’explication de l’écart ou le
contexte du poste, avec le montant annuel. Le commentaire reste lié à
l’exercice, au compte et au centre analytique. Le verrouillage de l’exercice
protège aussi ce budget et son commentaire.

Le rapport **Budget / réalisé** montre budget, réalisé, écart, explication et
réalisé/budget de l’exercice précédent enregistré. Le précédent est l’exercice
qui se termine le plus récemment avant le début de l’exercice courant.
Les données précédentes couvrent l’exercice entier ; le réalisé courant suit
les dates sélectionnées ; les budgets restent annuels. Les filtres analytiques
s’appliquent au comparatif.

Sans précédent ou sans budget précédent, la cellule est laissée vide et affichée
« — », sans inventer un zéro. Les commentaires sont saisis par le gestionnaire,
sans IA. Le comparatif et les explications sont inclus dans les exports CSV,
avec neutralisation des formules.
