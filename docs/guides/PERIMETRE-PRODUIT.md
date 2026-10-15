# Périmètre du produit et présentation publique

État au 14 octobre 2026. La cible est désormais **les syndics bénévoles et coopératifs**, selon le nouveau [cahier](../reference/cahier-fonctionnalites.md). Le cabinet professionnel est exclu. L’application actuelle reste mono-copropriété, avec mode bénévole/coopératif et responsabilités datées de conseil/contrôle ; la cible de plusieurs copropriétés est conservée pour une évolution ultérieure. Le [point d’avancement](AUDIT-FONCTIONNALITES.md) détaille les écarts.

La page `/presentation` présente le projet actuel et
ses objectifs. Elle ne lit aucune donnée de copropriété ; son illustration
contient uniquement des données fictives. La racine affiche cette présentation
aux visiteurs non connectés. `/connexion` conserve le formulaire d’accès.

La présentation décrit les parcours de Copro. selon le cahier fourni. Son contenu
et son design sont propres au projet.

| Domaine | Disponible dans Copro. | À compléter pour atteindre le périmètre souhaité |
| --- | --- | --- |
| Comptabilité | Reprise, factures/appels spécialisés, règlements/lettrage, rapprochement CSV, fonds par lot, régularisation, clôture et reports, corrections et mutations, rapports et données annuelles | Modèles réglementaires des annexes à valider, mode simplifié, fiscalité particulière et services bancaires connectés |
| Assemblées générales | Résolutions types/pièces, convocations figées, preuves d’envoi, présences/pouvoirs, votes enregistrés, PV, scans signés, notifications/recours, décisions et résumé publié | Certification des modèles, vote direct des membres, visio, signature/LRE connectées et cas juridiques particuliers |
| Obligations | Explications des règles utilisées par le calculateur de majorité du cas général | Détection contextualisée des obligations ALUR/ELAN/DPE/PPT ; le suivi manuel des dates et sources est disponible |
| Extranet | Connexion membre, changement du mot de passe temporaire, informations globales, compte personnel, documents et annonces publiés | Messagerie, participation aux votes et notifications extérieures |
| Travaux et sinistres | Dossiers travaux/sinistres, devis comparés, pièces, budgets indicatifs et liens vers résolutions | Avancement détaillé et suivi comptable intégré |
| Fournisseurs et contrats | Annuaire, coordonnées, fournisseur dans les devis/factures, balance auxiliaire native, contrats/préavis/coûts déclarés, attestations et alertes | Reprise des tiers historiques, seuils de concurrence, commandes, garanties et validations du conseil |
| Relances | Soldes et échéances à vérifier, vieillissement, lettrage, brouillons avec preuves, validation humaine, courriel préparé et historique | Accords de paiement et suivi des échanges/preuves ; l’envoi intégré reste à décider |
| Analyses métriques | Règles déterministes et alertes sur l’accueil | Calendrier annuel guidé, obligations contextualisées et contrôles de cohérence ; IA puissante reportée |
| Gouvernance bénévole/coopérative | Mandats datés, accès ciblés, présidence liée au conseil, préparation des dépenses, avis motivés et contrôle indépendant | Délégations collectives avancées, réunions du conseil et passation complète |

Les calculs actuels sont déterministes. Aucune facture n’est automatiquement
lue par IA et aucun courrier de relance ou de convocation n’est envoyé.
Le suivi des dossiers travaux est disponible, mais son budget reste indicatif
et ne génère pas d’écriture comptable. Les décisions d’AG signées peuvent créer
des projets financiers et des appels en brouillon. Les envois/signatures se font
hors de l’application avec conservation des preuves. Les parcours et documents
disponibles ne constituent pas une certification de conformité.

Le périmètre cible suit une règle : les opérations sensibles doivent présenter
les données et pièces utilisées, une proposition modifiable et une validation
avant exécution, puis une trace de l’action. Ce parcours d’assistance reste à
développer ; il n’est pas annoncé comme disponible dans la page publique.

Les évolutions fonctionnelles sont suivies dans `SUIVI-DEVELOPPEMENT.md`. Les limites des AG
et outils sont dans `AG-OUTILS.md`. La page publique doit être mise à jour quand
une fonction est livrée et vérifiée, sans transformer une intention en promesse.
