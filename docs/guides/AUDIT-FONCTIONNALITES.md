# État de Copro. — syndics bénévoles et coopératifs

Revue du **15 octobre 2026**, après livraison des parcours comptables, AG, conseil syndical et sauvegarde/sécurité, sur le [cahier fourni](../reference/cahier-fonctionnalites.md).

**Le cycle comptable et une AG conduite par le gestionnaire avec papier/scans et notifications extérieures sont utilisables.** Les services connectés, le mode simplifié, les modèles réglementaires à valider et les cas particuliers de gouvernance restent à compléter. Aucun pourcentage de conformité globale.

## Périmètre et lecture du comptage

Une instance gère une copropriété. Le sélecteur visuel ne cloisonne pas plusieurs syndicats. Les fonctions de cabinet professionnel restent exclues. Les 156 puces sont évaluées en entier ; les 11 rôles et deux besoins transverses sont séparés car ils recoupent les modules.

| État des exigences | Nombre |
| --- | ---: |
| Complètes dans les limites indiquées | 22 |
| Partielles | 91 |
| Absentes | 43 |
| Total | 156 |

Avant ces parcours : **6 complètes, 84 partielles, 66 absentes**. L’[instantané précédent](../reference/historique/2026-10-14-avant-parcours/audit-fonctionnalites.json) est conservé. Le [premier audit général](../reference/historique/2026-10-14-general/README.md) portait sur un autre cahier, avec fonctions de cabinet.

## Parcours disponibles et prochaines étapes

| Thème | Livré | Limites importantes |
| --- | --- | --- |
| Comptabilité | Reprise, factures/appels spécialisés, règlements et lettrage, banque CSV, fonds/travaux, régularisation, clôture et reports, mutations, corrections et exports | États annuels préparatoires ; mode simplifié, minima du fonds, fiscalité particulière et SEPA connectés absents |
| AG | Bibliothèque/pièces, corps électoral figé, convocations/preuves, présences/pouvoirs, votes enregistrés, PV/scans, notifications/recours, décisions et résumé publié | Gestionnaire opérateur ; aucun prestataire de signature/LRE, visio ou vote direct des membres ; modèles et cas particuliers à vérifier |
| Conseil et coopératif | Mandats datés, droits ciblés, présidence/syndic coopératif, préparation des dépenses, avis motivés, lecture des pièces et contrôle indépendant | Réunions, délégations collectives, personnes/cas dérogatoires et passation à compléter |
| Immeuble / extranet | Lots/tantièmes/annuaire, compte personnel et publications ; ancien vendeur sans lot limité au compte individuel | Bâtiments, indivision, occupants, messagerie et isolation multi-copropriété à compléter |
| Travaux et prestataires | Dossiers, devis, contrats, attestations et opérations financières créées depuis les décisions | Chantier/réception/garanties, commandes et mise en concurrence formalisée à compléter |
| Exploitation | TOTP/codes de secours, limites des tentatives, récupération serveur, archives chiffrées base/pièces, restauration comparée, rétention et reprise après interruption | Programmation/copie hors site à configurer ; supervision, audit inaltérable et RGPD à compléter |

Guides : [cycle comptable](COMPTABILITE-CYCLE.md), [AG de préparation à archivage](AG-OUTILS.md), [périmètre produit](PERIMETRE-PRODUIT.md). Les opérations sensibles demandent une confirmation dans l’application et conservent une trace ; aucun envoi extérieur automatique ni moteur IA puissant.

Sauvegarde/restauration vérifiée et double authentification livrées : voir le [guide de sécurité](SAUVEGARDE-SECURITE.md). Documents et financements renforcés : voir le [guide des annexes, fonds et avances](DOCUMENTS-FONDS-AVANCES.md). Validation métier des modèles à poursuivre ; prochain chantier produit : calendrier de gestion et entretien. Voir la [feuille de route](PROCHAINS-CHANTIERS.md) et le [guide du conseil](CONSEIL-SYNDICAL.md).

## Règles à interpréter correctement

- En forme coopérative, le syndic exerce aussi la présidence du conseil dans le cas général ; organiser les fonctions et le contrôle indépendant. [Service Public](https://www.service-public.gouv.fr/particuliers/vosdroits/F38886).
- Le régime simplifié vise au plus cinq lots principaux **OU** un budget moyen inférieur à 15 000 € sur trois exercices ; les engagements restent à constater. [Article 41-8](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000039301997/), [article 41-10](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000039302006).
- La régularisation appartient au propriétaire à la date d’approbation ; un accord privé de prorata n’est pas imposé au syndicat. [Service Public](https://www.service-public.gouv.fr/particuliers/vosdroits/F32920).
- Les minima du fonds/PPT et les seuils cumulatifs de suspension sont calculés après paramétrage annuel ; le calendrier historique reste à vérifier. Le compte séparé reste nécessaire. Les pièces et majorités spécifiques demandent une vérification humaine.

## Vérification

**221 tests PostgreSQL**, dont 25 de sécurité et 25 sur le conseil et ses permissions, 4 tests du format d’archive, scénario Docker de perte de pièce et interruption/reprise, compilation TypeScript/Vite, migrations et contrôles visuels sur copie isolée fictive, y compris mobile. Les données réelles ont été sauvegardées avant migration ; aucun vote réel, envoi ou écriture d’essai n’a été créé pour la vérification. Les tests et documents ne constituent pas une certification juridique ou comptable.

Les accès du conseil et du syndic dépendent des mandats actifs ; les accès permanents d’administration/gestion restent distincts. Les rôles sont contrôlés côté serveur. Les JSON exportent les données, sans les fichiers de pièces.

## Rôles

| Rôle | État | Constat |
| --- | --- | --- |
| Administrateur de la plateforme | partiel | Administrateur principal : attribution/retrait des accès, règles et comptes externes tracés. Une copropriété seulement ; TOTP et récupération serveur disponibles ; passation à compléter. |
| Syndic bénévole | partiel | Mandat de syndic bénévole donnant accès à la gestion pendant sa période, désignation documentée et retrait motivé. Indemnités et passation complète à compléter. |
| Syndic coopératif / président | partiel | Président/syndic coopératif avec droits de gestion dépendants du mandat de membre du conseil ; contrôle séparé. Cas dérogatoires et gouvernance collective avancée à compléter. |
| Trésorier / référent comptable | partiel | Lecture des comptes, dépôt de pièces et préparation/correction de factures sans écriture ni règlement. Préparation des appels/budgets et rapprochement délégués restent à étendre. |
| Président du conseil en mode bénévole | partiel | Mandat de présidence lié au mandat de membre du conseil ; lecture et avis motivés sans droits de gestion. Réunions et délégations détaillées absentes. |
| Membre du conseil syndical | partiel | Mandats datés, accès de lecture aux pièces et comptes, avis du conseil distincts de la préparation. Réunions, tâches et délégations détaillées à compléter. |
| Copropriétaire | partiel | Compte personnel, données globales et publications, résumés d’AG signées ; ancien vendeur sans lot limité au compte individuel. Pas de paiement en ligne ni vote direct du membre. |
| Occupant (optionnel) | absent | Aucun rôle ou portail de signalement. |
| Fournisseur (optionnel) | absent | Annuaire disponible mais sans compte utilisateur fournisseur. |
| Notaire (optionnel) | absent | Pas d’accès temporaire ni dossier de mutation. |
| Contrôleur des comptes / expert externe | complet | Contrôleur propriétaire ou extérieur, compte temporaire protégé, accès de lecture, dépôt de pièces, rapport indépendant final avec preuves et état comptable contrôlé. Aucun droit de gestion ou d’avis du conseil ; pas de réécriture du rapport final. |

## Besoins transverses

| Besoin | État | Constat |
| --- | --- | --- |
| Gestion d’une ou plusieurs copropriétés | absent | Une seule organisation (pk=1) et aucun lien de copropriété sur les propriétaires/lots/opérations. Le sélecteur visuel ne fournit pas d’isolation. Évolution non professionnelle toujours dans la cible ; commencer par fiabiliser une copropriété. |
| Mode comptable simplifié pour les petits syndicats | absent | Paragraphe nouveau hors des puces comptées : aucun choix de régime, calcul d’éligibilité ou parcours simplifié. Les articles 41-8 et 41-10 doivent guider les règles ; les engagements restent à constater en fin d’exercice. |

## Les 66 fonctions utilisables de périmètre plus étroit

| Fonction | Disponible | Limite |
| --- | --- | --- |
| Annuaire | Créer/modifier/rechercher un propriétaire physique ; courriel unique. | Pas d’indivision, démembrement ou historique de mutation. |
| Lots | Créer/modifier/rechercher et attribuer un propriétaire ; surface et tantièmes. | Bâtiments et escaliers non structurés. |
| Accès membre | Login courriel, mot de passe temporaire, TOTP, codes de secours, limitation des tentatives et récupération serveur. | Activation individuelle ; aucun envoi automatique. |
| Sauvegarde et reprise | Archive chiffrée base et pièces, restauration isolée comparée, rétention et reprise après interruption. | Programmation, secret et copie hors site à configurer ; même schéma et PostgreSQL 16. |
| Permissions actuelles | Contrôles serveur gestionnaire/lecture, protection de données privées et activation réservée au superadministrateur. | Trois niveaux seulement ; une copropriété. |
| Clés de charges | Clés générales ou poids spécifiques par lot. | Pas de validation juridique du règlement. |
| Appel générique | Brouillon, aperçu, validation et répartition figée lot/propriétaire/poids/montant, exacte au centime. | Pas de calendrier légal ni type fonds/travaux structuré. |
| Factures | Facture avec fournisseur identifié ou nom libre, pièce de bibliothèque et dette auxiliaire. | Pas d’OCR ni validation du conseil ; anciennes factures libres non réaffectées automatiquement. |
| Règlements fournisseurs | Paiements partiels, fournisseur et banque choisis, historique et contrôle du reste à payer. | Dans l’exercice de la facture ; sans SEPA ni lettrage. |
| Encaissements | Règlement manuel sur le compte d’un propriétaire et une banque choisie/par défaut. | Pas d’affectation à une créance ni paiement en ligne. |
| Écritures manuelles | Validation équilibrée, atomique et numérotation conservée ; aucun effacement par l’API. | Pas de régularisation, clôture et à-nouveaux. |
| Journaux | Créer/configurer/activer un journal et définir le journal par défaut. | Les à-nouveaux automatiques restent à développer. |
| Plan comptable | Créer des comptes et compléter explicitement le plan français sans écraser l’existant. | L’import ne prouve pas la conformité des affectations actuelles. |
| Analytique | Centres et affectations d’écriture, filtres et option obligatoire. | Pas de clôture analytique. |
| Budgets | Budget par exercice/compte/centre, comparatif précédent et explications des écarts enregistrées. | Pas de vote appliqué automatiquement ni simulation de budget ; notes modifiables avant verrouillage. |
| Modèles d’écriture | Enregistrer et appliquer une structure équilibrée à une date choisie. | Modèles comptables simples. |
| Contrepassation | Créer une écriture inverse manuelle en conservant l’original. | Ne couvre pas l’annulation des opérations métier. |
| Rapports généraux | Balance, journal, grand livre, résultat, bilan à date et budget/réalisé. | Rapports techniques ; aucune annexe réglementaire. |
| Comptes copropriétaires | Balance auxiliaire 450 avec solde antérieur, mouvements et solde final. | Pas de balance âgée, de lettrage ou de reports à nouveau. |
| Exports CSV | Exports de rapports avec neutralisation des formules ; impression/PDF navigateur. | Pas de FEC, XLSX ou PDF serveur. |
| Synthèses partagées | Publier un instantané global consultable en lecture. | Aucun détail privé d’un autre propriétaire. |
| Fichiers et versions | Dépôt PDF/PNG/JPEG, 10 Mo max, versions et téléchargements contrôlés. | Pas d’OCR, sous-dossiers ou retention légale. |
| Dossiers documentaires | Créer et renommer des dossiers plats. | Pas de hiérarchie imbriquée. |
| Partage documentaire | Publication explicite, archive/restauration et accès privé aux versions anciennes. | Publication globale pour tous les membres ; pas de groupe fin. |
| Préparation d’AG | Créer réunion, lieu/date, résolutions ordonnées et dossier de travail imprimable. | Aucun PV ou convocation officielle. |
| Présences de travail | Choisir depuis l’annuaire ou saisie libre, sommer les tantièmes et conserver une liste. | Émargement, mandats et correction article 22 non automatisés. |
| Calculs de majorité | Simuler 24/25/26/unanimité et les passerelles dans le cas général pris en charge. | Copropriété à deux exclue ; droits de vote corrigés à fournir ; pas de scrutin officiel. |
| Historique des simulations | Premier et second vote distincts, calcul serveur et protection de l’électorat. | Simulations de travail seulement. |
| Répartition d’un montant | Conserver exactement le total au centime entre poids libres. | Aucun effet comptable. |
| Échéancier simulé | Répartir une somme en 1 à 60 échéances exactes. | Aucun accord ni échéance de recouvrement persistante. |
| Dossiers | Travaux/sinistre/échéance avec budget indicatif, pièces, état et résolution liée. | Pas de cycle de chantier ni écritures liées. |
| Comparaison de devis | Montants, pièces, notes, un choix réversible et fournisseur réel ou nom libre. | Choisir un devis n’est pas passer commande. |
| Relances préparées | Solde débiteur, mouvements sources, brouillon modifiable, validation et courriel préparé. | Solde non lettré, sans preuve de retard ; aucun envoi. |
| Alertes d’accueil | Dates proches/dépassées, contrats, attestations, dépenses restantes, AG et soldes. | Analyse déterministe à l’ouverture de page ; pas d’IA ni push. |
| Compte personnel | Chaque membre lit uniquement son solde et ses 100 derniers mouvements 450. | Historique non paginé et limité à 100 mouvements. |
| Fournisseurs | Contacts, métier, SIRET déclaré, notes et archive/restauration. | Pas de validation de l’existence du SIRET ni rôle fournisseur. |
| Contrats | Dates, préavis en jours calendaires, reconduction déclarée, pièces, coût et export CSV. | Suivi manuel ; pas de résiliation/reconduction effective ni facturation. |
| Attestations | Pièce facultative, type, date de validité, archivage et alerte d’accueil. | Date déclarée ; l’authenticité et l’exigibilité ne sont pas vérifiées. |
| Annonces | Brouillon, publication explicite, retrait et archive/restauration ; lecture membre. | Panneau de texte partagé, sans messagerie ni envoi externe. |
| Navigation et mobile | Cinq thèmes, catégories déroulantes/compactes, pages explicatives et volet mobile. | Pas de PWA ni audit RGAA complet. |
| Vitrine et installation | Présentation statique docs/index.html et démarrage application avec Docker Compose. | La vitrine fonctionne sans serveur ; l’application de gestion nécessite backend/base. |
| Banques | Comptes distincts, association au compte existant, solde comptable à date et compte par défaut. | Solde comptable ; rapprochement CSV assisté maintenant disponible. Pas de connexion bancaire ; minima/PPT calculés dans Fonds & avances après paramétrage. |
| Transferts enregistrés | Écriture équilibrée entre banques, référence et protection contre les doublons lors d’une nouvelle tentative. | Transfert déjà effectué, aucun ordre envoyé ; affichage des 100 derniers. |
| Comptes fournisseurs | Balance auxiliaire 40, solde antérieur, règlements et dette finale par fournisseur, filtres et CSV. | Sur l’exercice sélectionné avec reports ; lettrage et paiement des soldes repris disponibles dans le cycle comptable. |
| Reprise des soldes | Balance initiale équilibrée, tiers et fonds par lot, correction conservée. | Pas d’import automatique de données externes. |
| Affectation des règlements | Lettrage partiel par tiers, montants restants, annulation contrôlée, paiement de dette fournisseur reprise. | Affectation confirmée par gestionnaire ; pas de prélèvement connecté. |
| Rapprochement bancaire | CSV normalisé, suggestions, pointage groupé, soldes, transit justifié et validation. | Pas de CFONB/OFX/agrégateur. |
| Régularisation annuelle | Répartitions figées, delta par clé/lot, propriétaire à l’approbation et écriture traçable. | Décision/PV à vérifier ; aucune convention privée de prorata supposée. |
| Clôture et reports | Contrôles, extinction 6/7, travaux 120, à-nouveaux détaillés et instantané. | Clôture définitive immuable ; états réglementaires non certifiés. |
| Fonds et travaux | Suivi 105, décisions/pièces, minima/PPT et suspension, affectation et solde. | Paramétrage annuel nécessaire ; situations exceptionnelles et ordres bancaires extérieurs. |
| Avances et restitutions | Catégories 103, plafond de réserve, versements par titulaire, ventes, restitution ou affectation PPT, corrections tracées. | Décisions et preuves requises ; aucun ordre bancaire ; correction du résultat nécessaire après solde des travaux. |
| Mutations comptables | Aperçu, référence/date, appels exigibles, corrections tardives et annulation avec traces. | Cas d’indivision et pièces notariales non couverts. |
| Suivi des échéances | Créances, crédits, exigibilité et tranches d’ancienneté. | Un solde comptable ne prouve pas à lui seul un impayé. |
| Données annuelles | Cinq annexes structurées, comparatifs disponibles, contrôles de concordance, fichier comptable 18 colonnes et archive JSON. | Modèles non certifiés ; JSON sans fichiers de pièces. |
| Dossier de convocation | Types, pièces/version, adresses, demandes écrites, échéance ordinaire et dossier figé. | Cas légaux particuliers et modèles à vérifier. |
| Présences et pouvoirs | Annuaire, droits, réduction, mandataires/pièces, correspondance et changements de présence. | Éligibilité personnelle vérifiée humainement ; exceptions complexes absentes. |
| Votes de séance | Choix individuels persistés, calcul serveur, second tour et corrections conservés. | Gestionnaire opérateur ; pas de vote direct ou visio native. |
| PV et registre | PV depuis votes, versions signées/présence, historique et archivage contrôlé. | Scans/signatures extérieures ; modèle non certifié. |
| Notifications et recours | Destinataires opposants/défaillants, preuves/dates, alertes et suivi de recours déclaré. | Pas de LRE/courrier connecté ni dépôt judiciaire. |
| Décisions exécutées | Régularisation, budget, appels en brouillon, projets, mandats et résumé publié depuis PV signé. | Paramètres recopiés/confirmés ; présidence coopérative et rôles fins absents. |
| Mandats et accès datés | Désignation documentée, dates, présidence dépendante, retrait motivé et droits contrôlés par le serveur. | Copropriétaires avec compte pour les fonctions de conseil ; droits permanents de gestion distincts. |
| Consultation du conseil | Factures, écritures, banques/relevés, budget, contrats, travaux et pièces sans droits de gestion. | Une seule copropriété ; documents consultables par l’équipe habilitée. |
| Préparation par un trésorier | Déposer une pièce, préparer/corriger une dépense et la soumettre ; reprise comptable explicite par le syndic. | Appels, budgets et rapprochement délégués non couverts par ce rôle. |
| Avis du conseil | Dossier et preuve conservés, quorum de personnes distinctes, refus motivé et contrôle avant sélection/règlement. | Contrôle interne ; ne vaut pas délégation juridique ni ordre bancaire. |
| Contrôle indépendant | Checklist, observations, pièces, conclusion, rapport final conservé et changements ultérieurs détectés. | Rapport téléchargé en Markdown sans les fichiers joints ; rapport de mission propre au conseil à compléter. |
| Organisation et traçabilité du conseil | Mode bénévole/coopératif et règles documentées ; historique des accès, avis et rapports. | Réunions, délégations collectives, cas dérogatoires et passation complète à compléter. |

## Évaluation des 156 exigences

Les preuves et textes source détaillés sont conservés dans l’[audit structuré](../reference/audit-fonctionnalites.json).


### 4.1

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.1.01 | Fiche copropriété : nom, adresse, nombre de bâtiments, de lots, année de construction, date de fin d'exercice, numéro d'immatriculation au registre national des copropriétés, coordonnées bancaires. | partiel | Nom, adresse, contacts, immatriculation et fiches bancaires présents ; les dates d’exercice sont séparées. Ajouter bâtiments, année de construction et fiche consolidée. |
| 4.1.02 | Structure : bâtiments, escaliers, étages, lots (principaux et annexes : cave, parking), usages (habitation, commerce, bureau). | partiel | Lots, type, étage et surface présents. Ajouter bâtiments, escaliers et usages détaillés. |
| 4.1.03 | Tantièmes : tantièmes généraux et clés de répartition multiples (charges générales, ascenseur, chauffage, eau, bâtiment, escalier, etc.), avec contrôle que le total de chaque clé est cohérent avec le règlement de copropriété. | partiel | Clés multiples et poids par lot opérationnels. Ajouter total attendu selon le règlement et contrôles de cohérence. |
| 4.1.04 | Copropriétaires : personnes physiques / morales (SCI, sociétés), indivision, usufruitier / nu-propriétaire, démembrement, mandataire commun, représentant légal, coordonnées, préférences de communication (papier / mail / recommandé électronique). | partiel | Annuaire de personnes physiques et accès courriel présents. Ajouter personnes morales, indivision, démembrement et préférences. |
| 4.1.05 | Historique des mutations : dates, anciens et nouveaux propriétaires, répartition des charges au prorata. | partiel | Mutations datées, ancien/nouveau propriétaire, référence, aperçu et corrections conservées. Les appels exigibles et la régularisation sont réattribués ; un prorata privé vendeur/acquéreur ne modifie pas les comptes du syndicat. |
| 4.1.06 | Occupants : locataires, coordonnées utiles (gestion d'accès, incidents). | absent | Créer le référentiel des occupants, distinct des propriétaires et des comptes de connexion. |
| 4.1.07 | Import initial : reprise de données depuis Excel / un autre logiciel (lots, tantièmes, soldes, balances d'ouverture). | partiel | Reprise manuelle équilibrée de la balance initiale, tiers et fonds par lot ; correction conservée. Import Excel des lots/tantièmes et conversion automatique des anciens logiciels restent absents. |
| 4.1.08 | Gestion du règlement de copropriété et de l'état descriptif de division (stockage, versions, modifications votées en AG). | partiel | Stockage et versions via la GED. Relier les changements aux décisions d’AG et distinguer les documents réglementaires. |

### 4.2

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.2.01 | Plan comptable des syndicats de copropriétaires (classes 1 à 7), comptes de tiers (copropriétaires, fournisseurs), comptes bancaires. | complet | Plan français classes 1 à 7 disponible, comptes actifs/désactivés, tiers, banques distinctes et métadonnées de lots/clés/travaux ; les catégories fiscales particulières restent conditionnelles. |
| 4.2.02 | Exercice comptable (ouverture, clôture, réouverture, reports à nouveau). | partiel | Reprise initiale, clôture contrôlée, extinction 6/7, travaux 120, report détaillé et archive. La clôture définitive reste immuable ; seuls les anciens verrous sans report peuvent être levés. Aucune réouverture générale. |
| 4.2.03 | Journaux : achats, banque, opérations diverses, à-nouveaux. | complet | Création, édition, activation des journaux et choix du journal par défaut. Les écritures d’à-nouveaux automatiques relèvent de la clôture, encore absente. |
| 4.2.04 | Gestion de la TVA si applicable (cas minoritaire, mais à prévoir pour certains syndicats). | absent | Ajouter un régime et des taux de TVA contextualisés, les ventilations et états nécessaires. |
| 4.2.05 | Budget prévisionnel : saisie par poste, simulation, comparaison avec N-1 et le réalisé, vote en AG. | partiel | Budgets par poste/clé, commentaires, N−1/réalisé et projections saisies N+1/N+2 ; reprise des postes depuis une décision signée. Scénarios budgétaires dédiés et contrôles de toutes les modalités restent à compléter. |
| 4.2.06 | Appels de fonds provisionnels (en principe par quarts, avec dates d'exigibilité conformes à la loi), calcul automatique par lot selon les clés de répartition. | partiel | Appels par lot/clé, tantièmes figés et échéancier trimestriel au centime ; décision conservée et appels issus du PV signé. Les dates/modalités exactes sont vérifiées par le gestionnaire, pas toutes déduites du régime juridique. |
| 4.2.07 | Appels de fonds pour travaux votés (provisions spéciales hors budget) avec échéancier voté en AG. | complet | Projets de travaux, comptes 102/67/120, financement et calendrier référencés ; un vote adopté et signé crée l’opération et les appels en brouillon, puis la publication répartit par lot/clé. |
| 4.2.08 | Fonds de travaux (loi ALUR) : cotisation obligatoire (minimum 5 % du budget prévisionnel, sauf exceptions), suivi par lot, attaché au lot et non remboursable au vendeur, placement sur compte dédié. | partiel | Profil de réception/habitation, budget et PPT, minimum annuel 5 % / 2,5 %, suspension avec les deux seuils et décision/pièce, plafond des appels votés. Suivi 105 par lot/banque et fonds versé attaché au lot après vente. Contrôles actifs après paramétrage annuel ; calendrier historique/anniversaire pendant exercice à vérifier. |
| 4.2.09 | Avances (trésorerie permanente, avances de travaux) et leur suivi par copropriétaire. | complet | Trois catégories 1031/1032/1033 ; réserve plafonnée soldes antérieurs compris, suivi constitué/versé/restitué/affecté par lot et titulaire historique. Restitutions partielles avec preuve et crédit 450 ou paiement enregistré, correction conservée ; vente et versements sources protégés. Avance PPT affectable à des travaux votés, prise en compte au solde sans double facturation. Correction isolée bloquée après solde des travaux. |
| 4.2.10 | Saisie des factures fournisseurs, OCR et reconnaissance automatique, workflow de validation (gestionnaire → conseil syndical selon les seuils). | partiel | Factures avec fournisseur et pièce, préparation sans écriture par un trésorier, demandes figées, avis du conseil et seuil/quorum contrôlés avant règlement. OCR absent. |
| 4.2.11 | Règlements fournisseurs : chèques, virements, fichiers SEPA, prélèvement. | partiel | Paiements partiels dans l’exercice ouvert et banque choisie, lettrage fournisseur, dettes initiales payables et corrections conservées. Pas d’ordre bancaire, fichier SEPA ou prélèvement connecté. |
| 4.2.12 | Encaissements copropriétaires : chèque, virement, prélèvement SEPA, carte bancaire en ligne, lettrage automatique. | partiel | Encaissements et affectations exactes au même tiers, protection contre réessai double, échéances et crédits visibles. Pas de carte, mandat SEPA ou connexion bancaire. |
| 4.2.13 | Compte bancaire séparé au nom de chaque syndicat : le logiciel doit empêcher la confusion des fonds. | partiel | Fiches bancaires privées avec compte comptable distinct et historique conservé pour la copropriété actuelle. Cloisonnement multi-copropriété et vérification de titulaires/conformité bancaire manquants. |
| 4.2.14 | Rapprochement bancaire automatisé (import de relevés CFONB / OFX / connexion bancaire via agrégateur), pointage assisté. | partiel | Import CSV normalisé, dédoublonnage, suggestions montant/date, pointage groupé, soldes et transits justifiés/figés. OFX, CFONB et agrégateur restent absents. |
| 4.2.15 | Gestion des comptes bancaires multiples : compte courant, compte épargne du fonds travaux. | complet | Comptes courant/épargne/fonds distincts, compte par défaut, association à un 512 existant sans réécriture, soldes comptables à date, banque sur règlements/encaissements et transferts équilibrés avec protection contre les doublons. Ces soldes restent issus des seules écritures disponibles ; fonds travaux et rapprochement sont des exigences séparées. |
| 4.2.16 | Régularisation des charges (réel vs provisions) et répartition par lot. | complet | Charges et provisions figées par clé/lot, delta attribué au propriétaire à l’approbation, aperçu avec empreinte, référence de décision, écriture et correction conservées. Le PV signé peut déclencher la régularisation. |
| 4.2.17 | Régularisation des charges à l'ouverture pour les copropriétaires entrants/sortants. | partiel | Reprise des tiers et mutation datée avec appels exigibles transférés et correction de régularisation dans l’exercice ouvert, y compris notification tardive après clôture. Cas d’indivision et dossier notarial complet restent absents. |
| 4.2.18 | États financiers et annexes obligatoires : situation financière et trésorerie, compte de gestion général, compte de gestion pour opérations courantes, compte de gestion pour travaux et opérations exceptionnelles, état des dettes et créances, annexes 1 à 5 (comparaison budget/réalisé, état des travaux, etc.). | partiel | Cinq annexes structurées et imprimables, comparatifs disponibles, tiers identifiés non compensés, provisions avant régularisation, dates/détails travaux, contrôles grand livre et concordance, version/empreinte et instantanés. Aides/prêts/indemnités signalés pour états complémentaires ; conformité exhaustive des modèles à faire valider par métier. |
| 4.2.19 | Exports comptables : journaux, grand livre, balance, FEC (utile pour les contrôles), export vers un expert-comptable si besoin. | partiel | Rapports CSV, dossier JSON et fichier comptable 18 colonnes avec groupes entièrement lettrés. Le format technique ne constitue pas une certification DGFiP ou un connecteur expert-comptable. |
| 4.2.20 | Verrouillage des périodes, contrôle d'intégrité, traçabilité des écritures (aucune suppression, extournes uniquement). | complet | Écritures équilibrées sans suppression financière, contrepassations, contrôles de tiers/répartitions/banque, clôture immuable, empreintes et événements d’audit. Pas de promesse d’inaltérabilité contre l’administrateur de base. |

### 4.3

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.3.01 | Définition des catégories de charges (générales, spéciales, individuelles) conformément à l'article 10 de la loi de 1965. | partiel | Catégories et clés générales/spécifiques présentes. Ajouter nature juridique, charges individuelles et contrôles article 10. |
| 4.3.02 | Distinction charges de conservation, d'entretien et d'administration vs charges d'équipements spécifiques. | partiel | Des clés distinctes sont possibles. Ajouter qualification des dépenses et contrôles de leur affectation. |
| 4.3.03 | Charges récupérables sur les locataires : état récapitulatif par lot pour les bailleurs (base : liste des charges récupérables fixée par décret), avec export pour le propriétaire. | absent | Créer la ventilation récupérable/non récupérable et le décompte exportable par lot. |
| 4.3.04 | Individualisation des frais (compteurs d'eau, répartiteurs de chauffage) : import des relevés, répartition automatique, décompte individuel. | absent | Créer compteurs, relevés datés/imports, consommations et règles de répartition. |
| 4.3.05 | Simulation de l'impact d'un changement de clé de répartition. | partiel | Outil de répartition générique disponible. Ajouter comparaison avant/après d’une clé réelle, par lot. |

### 4.4

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.4.01 | Suivi des soldes, vieillissement des créances, tableau de bord des impayés. | complet | Créances/crédits restants calculés depuis le lettrage, dates d’exigibilité, tranches de vieillissement et tableau d’impayés ; un solde seul ne prouve pas un défaut de paiement. |
| 4.4.02 | Relances automatisées configurables : relance simple, relance ferme, mise en demeure (LRAR ou LRE), avec modèles de courriers. | partiel | Brouillon neutre avec mouvements sources, validation humaine et mailto présents. Pas de relance automatique, mise en demeure ou LRE. |
| 4.4.03 | Gestion des frais de recouvrement imputables uniquement lorsqu'ils sont légalement justifiés (frais nécessaires de recouvrement, article 10-1 de la loi). | absent | Ajouter frais justifiés, décision humaine et traçabilité ; aucun frais automatique à partir d’un solde. |
| 4.4.04 | Suivi des échéanciers convenus avec les copropriétaires. | partiel | Simulateur d’échéancier sans écritures présent. Ajouter accord daté, échéances persistantes, affectation et suivi des règlements. |
| 4.4.05 | Dossier contentieux : transmission à un avocat ou à un commissaire de justice, suivi des procédures (injonction de payer, procédure accélérée, hypothèque légale, privilège immobilier spécial), des honoraires et des décisions de justice. | absent | Créer dossiers contentieux, acteurs, étapes et documents avec contrôle juridique contextualisé. |
| 4.4.06 | Déchéance du terme (exigibilité immédiate des provisions non échues en cas d'impayé) : alertes et génération de documents. | absent | Ajouter conditions, contrôles et documents de procédure après validation des règles applicables. |
| 4.4.07 | Gestion des procédures spécifiques : copropriétés en difficulté (mandataire ad hoc, administrateur provisoire), saisies, ventes forcées. | absent | Créer le suivi des procédures particulières ; hors du socle actuel de syndic bénévole. |

### 4.5

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.5.01 | Planification de l'AG annuelle (dans les six mois suivant la clôture de l'exercice), rappel des échéances. | partiel | Planification, exercice présenté et échéance annuelle, alertes locales des étapes. Régimes d’AG exceptionnels et calendrier dépendant de tous les profils d’immeuble restent à compléter. |
| 4.5.02 | Ordre du jour : construction de résolutions à partir d'une bibliothèque de résolutions types (approbation des comptes, quitus, budget, désignation syndic, conseil syndical, travaux, etc.), avec la majorité requise associée à chaque résolution. | complet | Bibliothèque de résolutions types, textes/majorités éditables, pièces types et contrôle des champs à compléter avant convocation. La majorité propre à l’objet est vérifiée par le gestionnaire. |
| 4.5.03 | Gestion des questions des copropriétaires et de leur inscription à l'ordre du jour (demandes écrites avec délai). | partiel | Demande écrite, auteur, réception et version rattachés à un point avant convocation ; dossier figé ensuite. Pas de collecte directe ni boîte de demandes différées des membres. |
| 4.5.04 | Documents joints obligatoires : comptes, budget, devis, contrat-type de syndic, projet de contrat, etc., avec liste de contrôle selon les résolutions. | partiel | Pièces versionnées selon modèle ; approbation des comptes avec cinq annexes, décomptes et consultation, exercice terminé, relecture et empreinte du dossier comptable figée. Modification après relecture et erreurs bloquent la convocation. Vérification humaine du contenu réel des PDF et des cas particuliers. |
| 4.5.05 | Calcul automatique des tantièmes de présence et de vote. | complet | Corps électoral lié aux lots ou lignes libres expliquées, totaux de présence distincts, réduction article 22 et régime à deux, droits par clé confirmée et instantanés. |
| 4.5.06 | Respect du délai minimal de 21 jours (délai spécifique pour certaines AG) : le logiciel calcule et empêche l'envoi trop tardif. | partiel | Blocage d’une notification ordinaire trop tardive : 21 jours ou délai RCP supérieur, prise d’effet, week-ends/jours fériés et option Alsace-Moselle. Urgence et outre-mer non traités. |
| 4.5.07 | Envoi par courrier, LRAR, lettre recommandée électronique (avec consentement), email simple selon les cas, avec suivi des accusés de réception. | partiel | Convocation/formulaire/pouvoir imprimables, courriel préparé et preuves d’envoi/réception conservées avec modalité et dates. Envoi recommandé/LRE réalisé hors application ; aucun prestataire connecté. |
| 4.5.08 | Gestion des pouvoirs (limite de mandats par mandataire : règles d'exception selon le total des voix détenues), des procurations, du vote par correspondance (formulaire avant l'AG). | partiel | Mandataire réel/extérieur, domicile, version signée, éligibilité déclarée, trois pouvoirs/exception 10 %, syndic interdit ; formulaire et réception à trois jours francs. Syndicats secondaires, familles et subdélégations complexes restent à vérifier. |
| 4.5.09 | Feuille de présence (papier numérisé ou tablette), émargement, tantièmes présents / représentés / par correspondance. | complet | Feuille de présence papier imprimable avec domiciles, lots, voix et mandataires, contrôle des participations, pièce signée/certifiée rattachée au PV. |
| 4.5.10 | Vote par résolution avec calcul automatique des majorités (art. 24, 25, 25-1, 26, 26-1, unanimité) et règles de second vote (passerelle de l'art. 25-1). | complet | Votes individuels enregistrés, 24/25/26/unanimité, régime à deux, passerelles en second tour distinct, calcul serveur, incidents/amendements/correspondants défaillants et corrections conservées. |
| 4.5.11 | Désignation du président de séance, des scrutateurs, du secrétaire (avec contrôles de cohérence). | complet | Bureau élu déclaré avec président présent/éligible, syndic déclaré interdit, secrétaire et scrutateurs, confirmé avant séance. Les élections et relations personnelles sont contrôlées humainement. |
| 4.5.12 | Support de l'AG en visioconférence et du vote en ligne en direct (si autorisé et paramétré). | absent | Créer un parcours autorisé de présence à distance et vote authentifié ; aucun service de visioconférence intégré. |
| 4.5.13 | Saisie en temps réel, récapitulatif live pour le conseil syndical, gestion des arrivées / départs en cours de séance. | partiel | Saisie de séance, instantané par tour et arrivées/départs conservés. Pas de vue live dédiée au conseil, diffusion WebSocket ou rôle CS distinct. |
| 4.5.14 | Génération du procès-verbal (modèle réglementaire), signature (physique ou électronique), registre des PV. | partiel | PV avec votes, noms/voix, opposants/abstentionnistes et assimilés défaillants distincts, rappel article 42 alinéa 2, scans signés et registre. Feuille de présence avec réception des correspondances. Validation métier des modèles et signature qualifiée extérieure. |
| 4.5.15 | Notification du PV aux copropriétaires opposants ou défaillants dans le délai légal (généralement un mois), suivi des accusés de réception. | partiel | Opposants/défaillants calculés, délai d’un mois, preuves et dates avec retards visibles, archivage bloqué sans notifications. Les envois et accusés sont réalisés/vérifiés à l’extérieur. |
| 4.5.16 | Gestion du délai de contestation (deux mois à compter de la notification) : alerte, suivi des recours. | complet | Terme de deux mois par notification effective, calendrier procédural, alertes et suivi des recours déclarés avec référence, pièce, statut et historique. Aucun dépôt judiciaire automatisé. |
| 4.5.17 | Reprise automatique des décisions : budget voté, travaux votés (création des appels de fonds), nomination du syndic, mandats du conseil syndical. | partiel | Après PV signé : régularisation, postes budgétaires, appels en brouillon/projets et mandats du syndic bénévole/membres copropriétaires du conseil. Recopie confirmée des paramètres ; présidence coopérative et droits automatiques absents. |
| 4.5.18 | Résumé des décisions pour le portail copropriétaires. | complet | Publication explicite des textes retenus et résultats globaux du PV signé dans l’espace membre ; contacts/preuves/votes individuels restent privés. |

### 4.6

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.6.01 | Composition et mandats (durée, renouvellement), rôle (président, membres). | partiel | Composition, responsabilités, dates, pièces, renouvellement par nouveau mandat et retrait motivé ; droits effectifs selon les mandats. Parcours limité aux copropriétaires avec accès pour les fonctions de conseil ; autres personnes éligibles et suivi avancé des renouvellements à compléter. |
| 4.6.02 | Espace dédié : budget en temps réel, factures, contrats, travaux, relevés bancaires (consultation selon droits). | complet | Espace dédié en lecture : budget/réalisé, balance, écritures, factures/règlements, banques, relevés/rapprochements, contrats, travaux/sinistres et pièces versionnées. Accès contrôlé côté serveur sans droits de gestion ; l’instance demeure mono-copropriété. |
| 4.6.03 | Validation en ligne des devis, engagements de dépenses, mises en concurrence. | partiel | Avis motivés du conseil sur devis/factures/préparations, seuil et avis distincts, blocage de sélection/règlement sans contrôle ; auteur et pièces conservés. Engagements/commandes et mise en concurrence formalisée restent à compléter. |
| 4.6.04 | Gestion des réunions : convocations, ordres du jour, comptes rendus, tâches suivies. | absent | Créer réunions du conseil, invitations, comptes rendus et tâches. |
| 4.6.05 | Accès aux pièces comptables pour le contrôle des comptes (rendez-vous, consultation, copie). | partiel | Conseil et contrôleur consultent et téléchargent les pièces privées de gestion sans modifier les comptes. Rapport indépendant final conservé et changements ultérieurs signalés. Prise de rendez-vous spécialisée absente. |
| 4.6.06 | Suivi des délégations de pouvoir éventuelles en dehors de l'AG. | absent | Créer délégations bornées par date, périmètre et décision. |

### 4.7

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.7.01 | Base fournisseurs : coordonnées, SIRET, domaine d'intervention, attestations obligatoires (assurance, URSSAF, Kbis), alertes d'expiration. | partiel | Ajout livré : annuaire, contacts, SIRET déclaré, métier, attestations liées et alertes. Détermination des pièces exigibles et vérification juridique non automatiques. |
| 4.7.02 | Contrats : ascenseur, chauffage, nettoyage, espaces verts, gardiennage, assurance, etc. avec dates, échéances, préavis, reconduction tacite, alertes de renégociation ou mise en concurrence. | partiel | Ajout livré : dates, préavis, reconduction déclarée, coût, pièces, archive et alertes. Renégociations et cycles formels de mise en concurrence à ajouter. |
| 4.7.03 | Mise en concurrence : demandes de devis comparatives, grille de comparaison, historique, décision (avec transmission au conseil syndical et à l'AG au-dessus du seuil voté). | partiel | Devis comparables, notes, pièce et sélection réversible présents, avec choix du fournisseur réel ajouté. Grille multicritère, demandes et seuils/validation du conseil manquants. |
| 4.7.04 | Ordres de service et bons de commande. | absent | Créer commandes/ordres de service distincts du simple choix d’un devis. |
| 4.7.05 | Suivi des sinistres et garanties (décennale, dommages-ouvrage, parfait achèvement) avec échéances. | partiel | Dossiers sinistres et échéances manuelles présents. Garanties structurées, dates de réception et délais spécifiques manquants. |

### 4.8

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.8.01 | Gestion des incidents : tickets de signalement (parties communes), priorité, assignation à un prestataire, suivi, photos, délais. | partiel | Dossiers incident/sinistre gestionnaire et pièces présents. Ajouter signalement membre, priorités, affectation, photos et échanges. |
| 4.8.02 | Carnet d'entretien de l'immeuble : dates, travaux, contrats, garanties (obligation légale à tenir à jour). | absent | Créer carnet structuré et exportable, avec interventions, équipements, contrats et garanties. |
| 4.8.03 | Diagnostic technique global (DTG) et projet de plan pluriannuel de travaux (PPT) : stockage, suivi des travaux sur 10 ans, budget prévisionnel, lien avec le fonds travaux. | partiel | GED et dossiers travaux utilisables manuellement. Ajouter diagnostic, programme sur 10 ans, financement et liens avec les fonds. |
| 4.8.04 | Audit énergétique / DPE collectif : dates, résultats, obligations selon la taille et l'âge de la copropriété. | partiel | Pièces et échéances manuelles disponibles. Ajouter données d’immeuble, résultats et règles d’applicabilité datées. |
| 4.8.05 | Projets de travaux : cycle complet (idée → devis → vote en AG → ordre de service → suivi de chantier → réception → levée des réserves → garanties), maître d'œuvre, architecte, assurances (dommages-ouvrage). | partiel | Budget indicatif, devis, pièces, résolution et état général présents. Commande, chantier, réception, réserves et garanties manquants. |
| 4.8.06 | Appels de fonds travaux automatiques selon le vote, suivi des subventions (MaPrimeRénov' Copropriété, CEE, aides locales) et des prêts collectifs. | absent | Créer décisions de financement, échéanciers, subventions et prêts avec suivi comptable. |
| 4.8.07 | Maintenance préventive : planning des vérifications obligatoires (ascenseurs, extincteurs, installations électriques, gaz, chaudières, toitures, désenfumage, etc.). | partiel | Suivi manuel des dates présent. Ajouter équipements, récurrence, attestations et journal des interventions. |
| 4.8.08 | Cas spécifiques : IRVE (bornes de recharge), accessibilité, sécurité incendie. | partiel | Dossiers génériques possibles. Aucun parcours spécifique IRVE/accessibilité/incendie ni règles contextualisées. |

### 4.9

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.9.01 | Pré-état daté et état daté (documents financiers destinés au notaire) avec plafonnement des tarifs pour ce qui est facturable au vendeur. | absent | Créer états vendeur/acquéreur/notaire depuis une comptabilité régularisée et contrôler la facturation applicable. |
| 4.9.02 | Questionnaire notarié, attestations de solde, certificat de l'article 20 (opposition du syndic). | absent | Créer questionnaires, attestations de solde et certificats depuis des données validées. |
| 4.9.03 | Fiche synthétique de la copropriété (à jour, mise à disposition des candidats acquéreurs). | absent | Créer fiche synthétique complète, annuelle et exportable. |
| 4.9.04 | Documents à fournir à l'acheteur : règlement de copropriété, PV des trois dernières AG, carnet d'entretien, DTG / PPT, etc., assemblés automatiquement. | partiel | Documents peuvent être rangés et téléchargés individuellement. Ajouter checklist et dossier de vente assemblé automatiquement. |
| 4.9.05 | Gestion de l'ancien / nouveau copropriétaire : répartition des charges, transfert du fonds travaux, mise à jour du référentiel. | partiel | Ancien/nouveau propriétaire, historique, aperçu, appels exigibles et régularisations corrigés, fonds versé attaché au lot et accès ancien membre réduit au compte personnel. Démembrements et dossier notarial restent à développer. |

### 4.10

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.10.01 | Contrats d'assurance de l'immeuble (multirisque, responsabilité civile, dommages-ouvrage), échéances, franchises, capitaux. | partiel | Contrats génériques et dates ajoutés. Ajouter nature d’assurance, franchise, garanties et capitaux. |
| 4.10.02 | Déclaration de sinistre : dégât des eaux, incendie, vandalisme, avec suivi du dossier et application des conventions inter-assureurs. | partiel | Dossier sinistre, pièces et devis présents. Déclaration et conventions inter-assureurs manquantes. |
| 4.10.03 | Suivi des indemnisations et de leur comptabilisation. | absent | Relier indemnités, dépenses et règlements au sinistre et à la comptabilité. |
| 4.10.04 | Alertes de renouvellement et comparatifs. | partiel | Échéances de contrat ajoutées et devis comparables présents. Ajouter renouvellement d’assurance et comparaison des garanties. |

### 4.11

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.11.01 | Fiche des gardiens, concierges et employés d'immeuble (convention collective applicable), contrats, avenants, congés, absences. | absent | Créer personnel, contrats, temps de présence et absences si l’immeuble emploie du personnel. |
| 4.11.02 | Paie et déclarations sociales (DSN, URSSAF) – intégration native ou connecteur vers un logiciel de paie (module complexe, souvent externalisé). | absent | Prévoir un connecteur paie/DSN ; aucun moteur de paie actuellement. |
| 4.11.03 | Logement de fonction, avantages en nature, répartition des charges de personnel. | absent | Ajouter avantages, logement et ventilation des charges salariales. |

### 4.12

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.12.01 | Gestion électronique des documents structurée par copropriété : règlement, PV, contrats, comptes, factures, courriers, diagnostics, plans, assurances. | partiel | Dossiers plats et GED disponibles pour une seule copropriété. Ajouter classement métier et structure par copropriété. |
| 4.12.02 | Métadonnées, droits d'accès fins, versions, recherche plein texte (OCR). | partiel | Versions, intitulé et publication globale présents. Ajouter métadonnées, droits fins et recherche OCR/plein texte. |
| 4.12.03 | Archivage légal : conservation des pièces comptables (au moins 10 ans), des PV, des documents de la copropriété ; gestion des durées de conservation et suppression conforme RGPD. | partiel | Archive réversible présente. Aucun calendrier de conservation légale ni purge RGPD. |
| 4.12.04 | Transmission du dossier au syndic suivant (restitution des archives à la fin du mandat) : export complet standardisé. | absent | Créer export intégral contrôlé des pièces, versions, références et données avec inventaire vérifiable. |
| 4.12.05 | Modèles de courriers et documents (mise en demeure, convocation, attestations). | partiel | Courriels d’accès et brouillons de relance présents. Ajouter modèles paramétrables et documents officiels. |

### 4.13

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.13.01 | Accès en ligne sécurisé aux documents de gestion pour les copropriétaires et le conseil syndical bénévole/coopératif. | partiel | Connexion, droits documentaires contrôlés et TOTP avec codes de secours disponibles. Vérification complète du périmètre documentaire et des parcours de l’extranet cible encore à mener. |
| 4.13.02 | Espace copropriétaire : solde du compte, historique des appels et paiements, documents de l'AG, règlement, PV, contrats, carnet d'entretien, coordonnées du gestionnaire. | partiel | Compte personnel, derniers mouvements, appels globaux et documents publiés présents. Ajouter historique personnel paginé, pièces liées aux appels et fiche gestionnaire complète. |
| 4.13.03 | Paiement en ligne (carte, virement instantané, prélèvement). | absent | Créer intégration de paiement avec suivi signé des statuts et rapprochement ; aucun paiement en ligne actuellement. |
| 4.13.04 | Signalement d'incidents, suivi des demandes. | absent | Créer tickets membres et suivi de leurs propres demandes avec isolation des données. |
| 4.13.05 | Messagerie interne et notifications (email, SMS, push mobile). | absent | Créer messagerie et notifications ; les annonces ajoutées sont un panneau de lecture, sans échanges. |
| 4.13.06 | Annonces et panneau d'affichage numérique. | complet | Ajout livré : brouillon, publication explicite, retrait, archive/restauration et lecture des seuls messages publiés dans le portail. |
| 4.13.07 | Courrier hybride : envoi postal automatisé (impression, mise sous pli, affranchissement) via prestataire. | absent | Intégration prestataire courrier postal à définir ; aucun envoi hybride actuel. |
| 4.13.08 | Application mobile (PWA ou native) pour copropriétaires et conseil syndical. | partiel | Interface responsive et navigation mobile présentes. PWA installable/offline et application native absentes. |

### 4.14

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.14.01 | Immatriculation au registre national des copropriétés : numéro, mise à jour annuelle, alertes. | partiel | Champ immatriculation présent. Ajouter date de mise à jour, contrôle de fiche et rappel annuel contextualisé. |
| 4.14.02 | Fonds de travaux : cotisation, solde, placement. | absent | Dépend des fonds travaux, de leurs cotisations et des banques dédiées. |
| 4.14.03 | PPT / DTG / DPE collectif / audit énergétique : échéances selon l'âge et la taille. | partiel | Échéances manuelles et sources disponibles. Aucun calcul des obligations selon âge, taille et situation de l’immeuble. |
| 4.14.04 | Fiche synthétique : mise à jour annuelle. | absent | Créer fiche synthétique et suivi de sa mise à jour annuelle. |
| 4.14.05 | Carnet d'entretien : date de dernière mise à jour. | absent | Créer carnet d’entretien et date de dernière révision. |
| 4.14.06 | Contrat de syndic : date de fin de mandat du syndic bénévole ou coopératif, rappel de la désignation à voter en AG. | partiel | Dates de dossiers/contrats et alertes génériques présentes. Aucun mandat du syndic identifié, fin de mandat dédiée, renouvellement ou résolution de désignation reliée. À traiter avec 4.15.01. |
| 4.14.07 | Assurance : attestation en cours de validité. | partiel | Attestations fournisseurs et contrats ajoutés. Ajouter attestation d’assurance de la copropriété distincte du fournisseur. |
| 4.14.08 | Échéances d'AG : délai de convocation, approbation des comptes. | partiel | Dates d’AG et alertes de proximité présentes. Contrôles des convocations/approbations manquants. |
| 4.14.09 | Vérifications périodiques obligatoires (ascenseur, sécurité). | partiel | Échéances manuelles présentes. Ajouter référentiel équipements, cycles et contrôles effectués. |
| 4.14.10 | Calendrier et notifications automatiques vers le gestionnaire. | partiel | Alertes d’accueil sur dates saisies, contrats, attestations, soldes et AG présentes. Ajouter agenda unifié, obligations contextualisées et notifications extérieures. |

### 4.15

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 4.15.01 | Mandat du syndic : désignation en AG, durée, éventuelle indemnité (à voter), renouvellement, révocation et passation à un successeur. | partiel | Mandats datés reliés aux votes/PV ou pièces de désignation, droits automatiques de syndic, retrait motivé et renouvellement par nouvelle période. Indemnité, personnes/cas particuliers et export complet de passation restent à compléter. |
| 4.15.02 | Mode guidé pas à pas : calendrier annuel (clôture, budget, convocation, AG, PV, appels de fonds), checklist des tâches obligatoires, explication en langage simple de la règle juridique à chaque étape. | partiel | Parcours comptables et AG présents. Guide AG intégré en six étapes avec vérifications, FAQ, lexique, mémo et impression. Calendrier et checklist légale annuelle selon tous les profils et régimes encore incomplets. |
| 4.15.03 | Contrôle croisé par le conseil syndical : validation des paiements, accès en lecture aux comptes, rapport de contrôle des comptes, afin de limiter les erreurs et les soupçons. | partiel | Conseil en lecture des comptes/pièces et avis distincts avant règlement selon une règle documentée ; rapport du contrôleur indépendant avec pièces et empreinte des comptes. Le rapport propre au conseil et les délégations collectives avancées restent à compléter. |
| 4.15.04 | Responsabilité et assurance : suivi de l'assurance responsabilité civile du syndicat et de la couverture du syndic non professionnel (à vérifier), journal des actions et décisions du syndic. | partiel | Journal technique de certaines actions et dossiers d’échéances manuels présents. Assurance du syndicat/syndic et décisions de mandat non structurées ; journal incomplet et modifiable en base. Les attestations fournisseurs ne couvrent pas cette exigence. |
| 4.15.05 | Continuité : délégation temporaire, accès de secours, export complet de passation en cas d'indisponibilité, de changement de syndic ou de passage futur à un syndic professionnel. | partiel | Exports CSV de rapports et téléchargements documentaires disponibles individuellement. Pas de délégation temporaire, accès de secours organisé ou export complet et vérifiable de passation. |
| 4.15.06 | Syndic coopératif : séparation claire entre les fonctions de syndic et de président du conseil syndical, vote du quitus sans conflit d'intérêts apparent. | partiel | Mode coopératif, présidence/syndic réunis et dépendants d’un mandat de conseil, vice-présidence, contrôleur indépendant et rapport natifs. Cas dérogatoires des petites copropriétés, personnes non propriétaires éligibles et gouvernance collective détaillée à compléter. |
| 4.15.07 | Aide intégrée : fiches pratiques, modèles de courriers, FAQ juridique, renvois vers des ressources d'information (par exemple associations de copropriétaires, ADIL). | partiel | Explications des catégories, aide du calculateur et guides du dépôt présents. Guide AG intégré avec six étapes, FAQ d’utilisation, lexique, mémo et impression. Les fiches juridiques, courriers et ressources contextualisées restent à compléter. |

### 5

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 5.01 | États financiers et annexes comptables (voir §4.2), comptes rendus d'exercice. | partiel | Dossier annuel structuré avec cinq annexes, comparatifs, décomptes, contrôles et empreinte ; conservation à la clôture. Modèles et situations exceptionnelles à faire valider, fichiers joints conservés séparément en GED. |
| 5.02 | Rapport d'activité du syndic présenté en AG. | absent | Créer rapport d’activité structuré par exercice avec pièces et décisions. |
| 5.03 | Convocation, PV, feuille de présence (modèles conformes). | partiel | Convocation figée, pièces par résolution, correspondance avec qualité/pages/paraphes et aide réglementaire, présence avec réception du formulaire, PV distinguant assimilés défaillants et rappel de recours. Vérifier l’intégralité des mentions du modèle officiel ; aucune certification ou signature qualifiée intégrée. |
| 5.04 | Fiche synthétique, état daté, pré-état daté. | absent | Dépend du référentiel complet et des mutations/régularisations. |
| 5.05 | Budget vs réalisé par poste, avec écarts expliqués. | complet | Budget/réalisé et écarts par poste, commentaires persistants saisis par le gestionnaire, comparaison avec l’exercice précédent enregistré (entier), filtres analytiques et export CSV. Les budgets restent annuels ; le réalisé courant suit la période sélectionnée. |
| 5.06 | Balance des copropriétaires, état des impayés et vieillissement. | partiel | Balances auxiliaires propriétaires et fournisseurs présents. Aucun vieillissement ou preuve de retard sans lettrage et échéances. |
| 5.07 | Trésorerie prévisionnelle, situation des fonds travaux. | absent | Ajouter soldes d’ouverture, banque, échéanciers futurs et fonds travaux avant projection. |
| 5.08 | Liste des contrats avec échéances, coûts annuels par fournisseur. | complet | Ajout livré : liste de contrats avec fin/préavis et export CSV ; agrégat des coûts annuels déclarés des contrats actifs par fournisseur, avec coûts inconnus signalés. |
| 5.09 | Suivi des travaux (avancement, coûts engagés / prévus). | partiel | Devis, budget indicatif et statut général présents. Coûts engagés/réels, étapes et évolution manquants. |
| 5.10 | Indicateurs de qualité : délai de traitement des incidents, délai de réponse, taux d'encaissement. | absent | Ajouter dates d’événements et indicateurs calculés à partir d’historiques fiables. |
| 5.11 | PDF, Excel / CSV, FEC, formats d'échange (SEPA, CFONB). | partiel | CSV des rapports, des comptes fournisseurs et des écarts commentés ; impression/PDF navigateur. PDF serveur, XLSX, FEC, SEPA et CFONB manquants. |
| 5.12 | API pour intégration avec d'autres systèmes. | partiel | API interne de session existante. API publique documentée, versionnée et avec autorisations d’intégration absente. |

### 6

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 6.01 | Modèles de documents personnalisables (publipostage, champs dynamiques). | absent | Créer modèles de courrier/document à champs dynamiques et versions. |
| 6.02 | Signature électronique (simple, avancée, qualifiée selon l'usage). | absent | Intégration de signature à définir après documents officiels et signataires. |
| 6.03 | Lettre recommandée électronique (LRE) avec valeur probante. | absent | Intégration LRE avec preuve d’envoi/réception et archivage à définir. |
| 6.04 | Workflows et automatisations (relances, validations, alertes). | partiel | Validations de relance, de devis et d’annonce présentes, alertes déterministes. Aucun moteur général de workflows ou tâches planifiées. |
| 6.05 | Agenda et rappels, gestion des tâches. | partiel | Échéances manuelles et liste de points à suivre présentes. Ajouter vue agenda, tâches, affectation et récurrence. |
| 6.06 | Recherche globale transversale. | partiel | Recherches locales par écran présentes. Ajouter recherche transversale limitée aux droits de l’utilisateur. |
| 6.07 | Notifications multicanales (email, SMS, push). | absent | Aucun envoi email/SMS/push ; choix utilisateur actuel : courriel préparé dans sa messagerie. |
| 6.08 | Import / export de données, outils de migration. | partiel | CSV de rapports, import du plan de référence et migration des anciens paiements présents. Reprise contrôlée des données externes et export complet manquants. |
| 6.09 | Multilingue (au minimum français, éventuellement anglais pour copropriétaires étrangers). | partiel | Interface française présente. Aucun mécanisme de traduction ou changement de langue ; l’anglais est une option du cahier. |
| 6.10 | Aide contextuelle et rappel des règles juridiques dans les écrans (ex. majorité requise à côté d'une résolution). | partiel | Pages de catégorie et explications des calculateurs présentes. Guide AG accessible depuis le menu et chaque rubrique AG, avec liens vers les écrans de travail. Aide contextuelle à généraliser aux autres procédures. |

### 7

| ID | Exigence | État | Constat |
| --- | --- | --- | --- |
| 7.01 | Registre des traitements, base légale pour chaque traitement, information des personnes. | absent | Créer registre, notices d’information et bases légales contextualisées. |
| 7.02 | Droits des personnes : accès, rectification, effacement, portabilité, opposition. | partiel | Accès à son compte et correction par gestionnaire possibles. Ajouter demandes formelles, export personnel et règles d’effacement/opposition. |
| 7.03 | Durées de conservation paramétrées, purge ou anonymisation automatiques. | absent | Créer politiques de conservation et processus de purge/anonymisation avec exceptions comptables. |
| 7.04 | Sous-traitants (hébergeur, SMS, courrier) : contrats conformes, hébergement en Union européenne. | absent | Déploiement Docker local disponible ; localisation, sous-traitants et contrats dépendent de l’installation, non vérifiés. |
| 7.05 | Analyse d'impact (AIPD) recommandée compte tenu du volume de données (identités, adresses, situation financière). | absent | Évaluer la nécessité d’une AIPD selon l’usage réel ; aucune analyse réalisée. |
| 7.06 | Authentification forte (2FA), gestion des mots de passe. | complet | TOTP avec confirmation, codes de secours à usage unique, secrets chiffrés, limitation des tentatives partagée et récupération serveur tracée. Règle obligatoire possible pour les accès de gestion ; activation individuelle par chaque titulaire. |
| 7.07 | Chiffrement des données en transit et au repos, gestion des clés. | partiel | Secrets TOTP chiffrés en base et archives chiffrées AES-256-GCM avec phrase dérivée par scrypt. HTTPS_ONLY disponible. Protection complète des disques, rotation des clés, stockage hors site et configuration HTTPS restent du ressort de l’exploitation. |
| 7.08 | Cloisonnement strict entre copropriétés (architecture multi-tenant sécurisée). | absent | Une seule copropriété globale. Aucun tenant, attribution ou test d’isolation entre copropriétés. |
| 7.09 | Journalisation et audit (qui a fait quoi, quand), logs inaltérables sur les opérations comptables. | partiel | Historique acteur/date d’actions comptables et dossiers présent. Audit exhaustif avant/après et stockage inaltérable absents. |
| 7.10 | Sauvegardes régulières, tests de restauration, plan de reprise d'activité. | complet | Archive chiffrée PostgreSQL et toutes les versions documentaires, inventaires avant/après, restauration isolée comparée et rétention. Reprise réelle, perte de pièce et interruption/reprise testées. Lanceur Windows et procédure Linux/PRA livrés ; fréquence, secret, copie hors site et surveillance sont à configurer par l’exploitant. |
| 7.11 | Tests de pénétration, gestion des vulnérabilités, politique de mise à jour. | partiel | 221 tests fonctionnels et compilation passent. Pas de pentest, suivi de dépendances ou politique de mise à jour attestée. |
| 7.12 | Disponibilité cible (par ex. 99,9 %), supervision, alertes. | partiel | Healthchecks Docker/API présents. Aucun SLO mesuré, supervision externe ni alerte d’incident. |
| 7.13 | Intégrité comptable : transactions atomiques, contrôles d'équilibre, verrouillage des périodes. | complet | Création atomique et équilibrée des écritures, numérotation verrouillée et refus des dates/exercices verrouillés testés. Ce contrôle technique ne constitue pas une clôture réglementaire. |
| 7.14 | Traçabilité juridique : horodatage des envois, preuves de notification, conservation des accusés. | absent | Dates de validation interne présentes mais aucun envoi probant, accusé de réception ni preuve de notification. |
| 7.15 | Accessibilité (RGAA / WCAG) et ergonomie, notamment sur mobile. | partiel | Responsive, libellés accessibles et dialogues clavier présents. Pas d’audit de conformité RGAA/WCAG complet ; contrastes et tous parcours à auditer. |
