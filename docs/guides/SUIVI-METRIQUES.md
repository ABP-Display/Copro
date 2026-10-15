# Dossiers, relances et analyses métriques

> Complément du 15 octobre 2026 : les descriptions ci-dessous retracent les livraisons antérieures. Le [cycle comptable](COMPTABILITE-CYCLE.md), l’[AG guidée](AG-OUTILS.md) et l’[audit courant](AUDIT-FONCTIONNALITES.md) remplacent les anciennes listes de fonctions restantes.

Livraison du 14 octobre 2026. Les calculs sont déterministes, sans moteur IA.

## Accueil gestionnaire

Les points à suivre regroupent les dossiers ouverts en retard ou à échéance
dans les 30 jours, les AG à venir dans cette période, les factures avec reste à
régler, les comptes débiteurs et les brouillons de relance à valider.
Les contrats actifs avec une fin ou une date limite de préavis proche/dépassée,
ainsi que les attestations fournisseurs à vérifier, sont également inclus.
Les alertes se recalculent à l’ouverture de l’accueil. Aucun courriel, push ou
notification extérieure n’est envoyé. Un dossier sans date ne produit pas
d’alerte d’échéance. Les dossiers terminés et archivés sont exclus.

Le reste fournisseurs cumule les montants de factures moins leurs paiements,
tous exercices confondus. Le solde copropriétaire cumule débit moins crédit sur
ses lignes de comptes 450 jusqu’au jour courant. Un solde débiteur ne prouve pas
un retard : le lettrage, les dates d’exigibilité et les règlements sont à vérifier.

## Dossiers et devis

Un dossier travaux, sinistre ou échéance porte une description, une date,
un budget indicatif, un statut, une source HTTPS, des documents et une résolution
liée. Les devis fournisseurs sont comparés par montant et écart au budget.
Un choix est explicite, tracé et réversible ; il ne passe pas commande et ne
crée ni facture ni écriture comptable. Le budget ne bloque pas le choix d’un devis.
Les droits sur les documents restent ceux de la bibliothèque existante.

Les devis choisissent désormais un fournisseur dans l’annuaire ou un nom libre.
Le nom enregistré dans le devis reste conservé si l’entreprise est renommée.

Le suivi d’obligations est manuel : le logiciel ne détermine pas automatiquement
si ALUR, ELAN, DPE ou PPT impose une échéance à cet immeuble. Le gestionnaire
renseigne une source vérifiée et une date adaptée à sa situation.

## Relances

Choisir un copropriétaire pour produire un brouillon depuis son solde débiteur.
Le texte neutre demande une vérification des mouvements ; il ne constitue pas
une mise en demeure. La date et les identifiants des lignes sources sont conservés.
Une seule relance active est autorisée par copropriétaire.

Enregistrer les corrections, puis valider après contrôle. Une comptabilité
modifiée bloque la validation du brouillon ancien. Le brouillon doit alors être
annulé et régénéré. Après validation, le texte est verrouillé, le courriel peut
être préparé dans la messagerie et l’envoi peut être déclaré manuellement.
Cette déclaration n’est pas une preuve d’envoi ni de réception.

## Compte personnel et confidentialité

Le portail membre affiche son propre solde et ses 100 derniers mouvements.
Le serveur détermine l’identité depuis la session ; un paramètre propriétaire
ne permet pas de lire un autre compte. Les gestionnaires seuls accèdent aux
dossiers, devis, métriques et relances. Les comptes dont le mot de passe
temporaire doit être changé restent bloqués avant l’accès aux données.

## Validation et suites

7 nouveaux tests vérifient dossiers, budgets, choix réversible, fenêtre
d’échéances, validation des relances, changements de comptabilité, CSRF et
confidentialité. Les 112 tests passent sur PostgreSQL dans une base séparée,
dont 12 nouveaux tests des fournisseurs, contrats, attestations et annonces.

Les nouveaux parcours sont décrits dans [le guide dédié](FOURNISSEURS-CONTRATS-ANNONCES.md).
L’[audit du cahier](AUDIT-FONCTIONNALITES.md) recense les fonctions complètes,
partielles et absentes avec leur périmètre précis.

Restent à développer : conformité contextualisée, déroulement complet des AG,
rapprochement et lettrage, régularisation, clôture et annexes, communication
automatisée, collecte des votes par les membres et suivi détaillé des travaux.
Ces modules complètent la reprise progressive ; ils ne constituent pas une
couverture fonctionnelle complète du cahier.

## Interface des dossiers et relances

Les trois pages proposent une recherche, un filtre de statut et des indicateurs.
Les dossiers et devis s’éditent dans une fenêtre adaptée au mobile. Les pièces
se sélectionnent par cases à cocher. Les documents et résolutions déjà liés
restent conservés même lorsqu’ils sont archivés. Les devis présentent une
comparaison au budget uniquement quand celui-ci a été renseigné.
Les relances séparent le choix du copropriétaire, la modification du texte,
les preuves du calcul et les actions de validation.

Les pages sont maintenant regroupées : dossiers/échéances dans **Travaux & entretien**, relances dans **Charges & finances**, entreprises dans **Fournisseurs & contrats**, annonces dans **Communication**. Les anciennes destinations des points à suivre ouvrent leur catégorie actuelle.
