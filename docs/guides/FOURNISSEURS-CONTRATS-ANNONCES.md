# Fournisseurs, contrats, attestations et annonces

Livraison du 14 octobre 2026. Les fournisseurs, contrats et attestations se trouvent
dans **Fournisseurs & contrats** ; les annonces dans **Communication**.

## Fournisseurs et devis

Créer une entreprise avec son métier, ses coordonnées et un SIRET facultatif de 14 chiffres. Le format est contrôlé ; aucune vérification auprès du registre des entreprises n’est faite. L’archivage conserve les contrats et les devis historiques. Un fournisseur archivé peut être restauré, mais ne peut recevoir de nouveau devis ou contrat.

Lors de l’ajout d’un devis à un dossier travaux ou sinistre, choisir l’entreprise dans l’annuaire, ou laisser « Saisir un nom libre ». Le nom conservé au moment du devis ne change pas si le fournisseur est renommé. Choisir un devis n’émet ni commande ni paiement.

L’annuaire affiche le nombre de contrats actifs et la somme de leurs coûts annuels **déclarés** ; les coûts inconnus sont signalés séparément. Il est désormais relié aux factures natives et à leurs lignes comptables. Voir le [guide des fournisseurs comptables](BANQUES-FOURNISSEURS-BUDGETS.md) pour les comptes auxiliaires et les limites des anciennes écritures.

## Contrats et préavis

Ajouter le fournisseur, le titre, la date de début, une date de fin facultative, le préavis en jours calendaires, le coût annuel facultatif et les pièces de la bibliothèque. Cocher la reconduction tacite si elle est indiquée au contrat. Une date de fin est requise pour un préavis ou une reconduction ; le préavis ne peut dépasser la durée saisie.

La date limite calculée est **fin moins préavis**. Vérifier les clauses réelles, la méthode de calcul et les conditions de notification avant une démarche. Les dates proches (30 jours) ou dépassées alimentent l’accueil. Aucun contrat n’est automatiquement résilié ou reconduit. Déclarer terminé ou archiver pour le sortir des alertes.

L’export CSV contient les contrats enregistrés, y compris terminés/archivés. Il reste réservé aux gestionnaires et neutralise les formules. Les coûts n’alimentent aucune écriture comptable.

## Attestations

Choisir un fournisseur, le type de pièce, le titre et la date de validité déclarée. Une pièce documentaire peut être liée. Archiver les anciennes attestations lors de leur remplacement : seules les attestations non archivées d’un fournisseur actif alimentent les alertes. Ni le caractère obligatoire ni l’authenticité d’une pièce ne sont déduits automatiquement.

## Annonces partagées

Enregistrer d’abord le titre et le message en **brouillon**. Le bouton **Publier aux copropriétaires** rend le texte visible dans le portail des comptes copropriétaires connectés. Le texte est partagé à tous ces membres : éviter les coordonnées privées et les comptes individuels.

**Retirer la publication** replace l’annonce en brouillon avant modification. **Archiver** la retire également du portail. Une restauration revient en brouillon et demande une nouvelle publication. Aucune annonce n’est envoyée par email/SMS et aucun accusé de lecture n’est collecté.

## Droits et vérifications

Les fournisseurs, contrats et attestations restent réservés aux gestionnaires. Le portail reçoit uniquement les annonces publiées. Le changement initial du mot de passe est requis avant toute consultation. Les mutations produisent un événement d’historique avec auteur, date, action et identifiant ; cet historique n’est pas un coffre-fort inaltérable.

Les 12 tests de `backend/operations/test_partners.py` vérifient notamment dates, montants, conservation des pièces, noms historiques, exclusions d’alertes, coûts inconnus, CSV, publication/retrait, accès privés et CSRF.

Le [rapport d’audit](AUDIT-FONCTIONNALITES.md) détaille les exigences plus larges encore partielles : seuils de mise en concurrence, approbation du conseil, commandes, assurance et garanties.
