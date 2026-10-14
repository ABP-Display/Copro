# Cahier des fonctionnalités – Application de gestion de syndic de copropriété

*Rapport de cadrage fonctionnel, juridique et technique – version syndic bénévole et coopératif – octobre 2026*

> **Avertissement** : ce rapport s'appuie sur la législation française de la copropriété telle que je la connais (état mi-2026) et sur les périmètres fonctionnels généralement présentés par les logiciels du marché (LogicielSyndic, Diacamma Syndic, etc.). Je n'ai pas consulté en direct leurs sites : vérifiez leur documentation actuelle et faites valider les points juridiques et comptables par un juriste / expert-comptable avant mise en production.

## 1. Objectif et périmètre

L'application doit permettre à un syndic (bénévole ou coopératif) de gérer **de bout en bout** une ou plusieurs copropriétés : référentiel des lots, comptabilité réglementaire, appels de fonds, recouvrement, assemblées générales, travaux, contrats, documents, communication et conformité légale.

**Cibles retenues** (le syndic professionnel est exclu de cette version) :

- **Syndic bénévole** : un copropriétaire élu par l'AG, sans formation juridique ni comptable, qui a besoin d'être guidé et protégé contre les erreurs.
- **Syndic coopératif** : le président du conseil syndical exerce aussi la fonction de syndic ; l'application doit rendre le contrôle des comptes simple et visible.
- **Conseil syndical et copropriétaires** : portail de consultation, de suivi et de paiement.

**Principe directeur** : remplacer le « cabinet » par l'outil. L'application doit guider pas à pas, automatiser les obligations légales et rendre la gestion lisible pour tous, plutôt que supposer que l'utilisateur connaît la loi.

## 2. Cadre juridique à intégrer

Ces textes déterminent les règles métier que le logiciel doit **appliquer et contrôler**, pas seulement stocker.

| Texte | Ce qu'il impose au logiciel |
| --- | --- |
| **Loi n°65-557 du 10 juillet 1965** (statut de la copropriété, dont le régime du syndicat coopératif et du syndic non professionnel) | Cœur du métier : syndicat, syndic, conseil syndical, charges, majorités d'AG, fonds travaux, recouvrement |
| **Décret n°67-223 du 17 mars 1967** | Procédure d'AG : convocation, délais, documents joints, PV, notification, contestation |
| **Décret n°2005-240 et arrêté du 14 mars 2005** | Comptabilité des syndicats : plan comptable, états financiers, annexes ; régime simplifié possible pour les très petits syndicats |
| **Loi ALUR (2014), loi ELAN (2018)** | Compte bancaire séparé, fonds travaux, fiche synthétique, carnet d'entretien, immatriculation, accès en ligne aux documents |
| **Ordonnance n°2019-1101 et décret n°2020-834** | Réforme du droit de la copropriété : règles de majorité, délais, mandats, règles de contestation |
| **Loi Climat et Résilience (2021)** | DPE collectif, projet de plan pluriannuel de travaux (PPT), obligations de rénovation énergétique |
| **RGPD et loi Informatique et Libertés** | Données personnelles des copropriétaires et occupants |
| **Règlement eIDAS / signature électronique** | Valeur juridique des signatures et envois dématérialisés |
| **Facturation électronique (réforme 2026-2027)** | Réception de factures électroniques selon le statut du syndicat : **à faire expertiser** |
| **Loi Hoguet (1970)** | Ne s'applique pas à un syndic non professionnel (pas de carte professionnelle ni de garantie financière obligatoires) : **hors périmètre de cette version** |

Un syndic bénévole ou coopératif reste soumis aux mêmes obligations de fond qu'un professionnel (comptes, AG, archives, convocations). Le logiciel doit donc les automatiser et les contrôler, et ne pas compter sur la connaissance de l'utilisateur.

## 3. Acteurs et gestion des droits

| Rôle | Droits principaux |
| --- | --- |
| **Administrateur de la plateforme** | Paramétrage global, comptes |
| **Syndic bénévole** | Gestion complète de sa copropriété : comptabilité, appels de fonds, AG, contrats, documents |
| **Syndic coopératif (président du conseil syndical)** | Mêmes droits que le syndic bénévole, avec séparation visible des rôles « syndic » et « président du conseil syndical » |
| **Trésorier / référent comptable** (optionnel) | Saisie et rapprochement délégués par le syndic, sans pouvoir de clôture |
| **Président du conseil syndical** (en mode bénévole) | Consultation étendue, validation de pièces, contrôle du budget |
| **Membre du conseil syndical** | Consultation, suivi des travaux et contrats |
| **Copropriétaire** | Ses lots, son compte, ses documents, les AG, ses paiements |
| **Locataire / occupant** (optionnel) | Signalement d'incidents, documents d'information |
| **Prestataire / fournisseur** (optionnel) | Réception d'ordres de service, dépôt de devis et factures |
| **Notaire** (optionnel) | Accès sécurisé aux documents de vente (état daté, pré-état daté) |
| **Expert-comptable / contrôleur externe** (optionnel) | Lecture seule des comptes pour un contrôle ou un audit ponctuel |

Exigences : **permissions par copropriété et par module**, journal d'audit des actions sensibles, authentification forte, délégation temporaire (ex. syndic absent ou en transition).

## 4. Modules fonctionnels

### 4.1 Référentiel de la copropriété

- Fiche copropriété : nom, adresse, nombre de bâtiments, de lots, année de construction, date de fin d'exercice, **numéro d'immatriculation au registre national des copropriétés**, coordonnées bancaires.
- Structure : bâtiments, escaliers, étages, **lots** (principaux et annexes : cave, parking), usages (habitation, commerce, bureau).
- **Tantièmes** : tantièmes généraux et **clés de répartition multiples** (charges générales, ascenseur, chauffage, eau, bâtiment, escalier, etc.), avec contrôle que le total de chaque clé est cohérent avec le règlement de copropriété.
- **Copropriétaires** : personnes physiques / morales (SCI, sociétés), **indivision, usufruitier / nu-propriétaire, démembrement**, mandataire commun, représentant légal, coordonnées, préférences de communication (papier / mail / recommandé électronique).
- **Historique des mutations** : dates, anciens et nouveaux propriétaires, répartition des charges au prorata.
- Occupants : locataires, coordonnées utiles (gestion d'accès, incidents).
- Import initial : reprise de données depuis Excel / un autre logiciel (lots, tantièmes, soldes, balances d'ouverture).
- **Gestion du règlement de copropriété et de l'état descriptif de division** (stockage, versions, modifications votées en AG).

### 4.2 Comptabilité réglementaire

La comptabilité d'un syndicat est **en partie double, d'engagement**, avec un plan comptable spécifique. C'est le module le plus lourd et celui où les erreurs sont les plus coûteuses.

**Fondations**

- Plan comptable des syndicats de copropriétaires (classes 1 à 7), comptes de tiers (copropriétaires, fournisseurs), comptes bancaires.
- **Exercice comptable** (ouverture, clôture, réouverture, reports à nouveau).
- Journaux : achats, banque, opérations diverses, à-nouveaux.
- Gestion de la **TVA** si applicable (cas minoritaire, mais à prévoir pour certains syndicats).

**Mode simplifié pour les petits syndicats** : pour les copropriétés de moins de 10 lots dont le budget moyen est inférieur à 15 000 €, la loi permet une comptabilité de trésorerie. Prévoir ce mode en plus de la comptabilité d'engagement (seuils à valider avec un expert-comptable).

**Budget et appels de fonds**

- **Budget prévisionnel** : saisie par poste, simulation, comparaison avec N-1 et le réalisé, vote en AG.
- **Appels de fonds provisionnels** (en principe par quarts, avec dates d'exigibilité conformes à la loi), calcul automatique par lot selon les clés de répartition.
- **Appels de fonds pour travaux votés** (provisions spéciales hors budget) avec échéancier voté en AG.
- **Fonds de travaux (loi ALUR)** : cotisation obligatoire (minimum 5 % du budget prévisionnel, sauf exceptions), suivi par lot, **attaché au lot et non remboursable au vendeur**, placement sur compte dédié.
- Avances (trésorerie permanente, avances de travaux) et leur suivi par copropriétaire.

**Opérations courantes**

- Saisie des factures fournisseurs, **OCR** et reconnaissance automatique, workflow de validation (gestionnaire → conseil syndical selon les seuils).
- Règlements fournisseurs : chèques, virements, **fichiers SEPA**, prélèvement.
- Encaissements copropriétaires : chèque, virement, prélèvement SEPA, carte bancaire en ligne, **lettrage automatique**.
- **Compte bancaire séparé** pour chaque copropriété (obligation légale ; l'AG peut en dispenser un syndic non professionnel dans de très petites copropriétés, conditions à vérifier) : le logiciel doit **empêcher la confusion des fonds**.
- **Rapprochement bancaire** automatisé (import de relevés CFONB / OFX / connexion bancaire via agrégateur), pointage assisté.
- Gestion des **comptes bancaires multiples** : compte courant, compte épargne du fonds travaux.

**Clôture et états financiers**

- Régularisation des charges (réel vs provisions) et répartition par lot.
- **Régularisation des charges à l'ouverture** pour les copropriétaires entrants/sortants.
- **États financiers et annexes** obligatoires : situation financière et trésorerie, compte de gestion général, compte de gestion pour opérations courantes, compte de gestion pour travaux et opérations exceptionnelles, état des dettes et créances, annexes 1 à 5 (comparaison budget/réalisé, état des travaux, etc.).
- **Exports comptables** : journaux, grand livre, balance, FEC (utile pour les contrôles), export vers un expert-comptable si besoin.
- Verrouillage des périodes, contrôle d'intégrité, traçabilité des écritures (aucune suppression, extournes uniquement).

### 4.3 Charges et répartition

- Définition des **catégories de charges** (générales, spéciales, individuelles) conformément à l'article 10 de la loi de 1965.
- Distinction **charges de conservation, d'entretien et d'administration** vs charges d'équipements spécifiques.
- **Charges récupérables sur les locataires** : état récapitulatif par lot pour les bailleurs (base : liste des charges récupérables fixée par décret), avec export pour le propriétaire.
- Individualisation des frais (compteurs d'eau, répartiteurs de chauffage) : import des relevés, répartition automatique, décompte individuel.
- Simulation de l'impact d'un changement de clé de répartition.

### 4.4 Recouvrement des impayés

- Suivi des soldes, **vieillissement des créances**, tableau de bord des impayés.
- **Relances automatisées** configurables : relance simple, relance ferme, **mise en demeure** (LRAR ou LRE), avec modèles de courriers.
- Gestion des **frais de recouvrement imputables** uniquement lorsqu'ils sont légalement justifiés (frais nécessaires de recouvrement, article 10-1 de la loi).
- Suivi des **échéanciers** convenus avec les copropriétaires.
- Dossier **contentieux** : transmission à un avocat ou à un commissaire de justice, suivi des procédures (injonction de payer, procédure accélérée, hypothèque légale, **privilège immobilier spécial**), des honoraires et des décisions de justice.
- **Déchéance du terme** (exigibilité immédiate des provisions non échues en cas d'impayé) : alertes et génération de documents.
- Gestion des procédures spécifiques : **copropriétés en difficulté** (mandataire ad hoc, administrateur provisoire), saisies, ventes forcées.

### 4.5 Assemblées générales

Module critique : une erreur de procédure peut entraîner l'annulation d'une décision. Le logiciel doit **guider** l'utilisateur et **bloquer** les non-conformités.

**Préparation**

- Planification de l'AG annuelle (dans les six mois suivant la clôture de l'exercice), rappel des échéances.
- **Ordre du jour** : construction de résolutions à partir d'une **bibliothèque de résolutions types** (approbation des comptes, quitus, budget, désignation syndic, conseil syndical, travaux, etc.), avec la **majorité requise** associée à chaque résolution.
- Gestion des **questions des copropriétaires** et de leur inscription à l'ordre du jour (demandes écrites avec délai).
- **Documents joints obligatoires** : comptes, budget, devis, contrat-type de syndic, projet de contrat, etc., avec liste de contrôle selon les résolutions.
- Calcul automatique des **tantièmes de présence et de vote**.

**Convocation**

- Respect du **délai minimal de 21 jours** (délai spécifique pour certaines AG) : le logiciel calcule et empêche l'envoi trop tardif.
- Envoi par **courrier, LRAR, lettre recommandée électronique** (avec consentement), email simple selon les cas, avec suivi des accusés de réception.
- Gestion des **pouvoirs** (limite de mandats par mandataire : règles d'exception selon le total des voix détenues), des procurations, du **vote par correspondance** (formulaire avant l'AG).

**Pendant l'AG**

- **Feuille de présence** (papier numérisé ou tablette), émargement, tantièmes présents / représentés / par correspondance.
- **Vote par résolution** avec calcul automatique des **majorités** (art. 24, 25, 25-1, 26, 26-1, unanimité) et règles de **second vote** (passerelle de l'art. 25-1).
- **Désignation** du président de séance, des scrutateurs, du secrétaire (avec contrôles de cohérence).
- Support de l'**AG en visioconférence** et du vote en ligne en direct (si autorisé et paramétré).
- Saisie en temps réel, **récapitulatif live** pour le conseil syndical, gestion des **arrivées / départs en cours de séance**.

**Après l'AG**

- Génération du **procès-verbal** (modèle réglementaire), signature (physique ou électronique), **registre des PV**.
- **Notification du PV** aux copropriétaires opposants ou défaillants dans le **délai légal** (généralement un mois), suivi des accusés de réception.
- **Gestion du délai de contestation** (deux mois à compter de la notification) : alerte, suivi des recours.
- Reprise automatique des décisions : budget voté, travaux votés (création des appels de fonds), nomination du syndic, mandats du conseil syndical.
- **Résumé des décisions** pour le portail copropriétaires.

### 4.6 Conseil syndical

- Composition et **mandats** (durée, renouvellement), rôle (président, membres).
- Espace dédié : budget en temps réel, factures, contrats, travaux, relevés bancaires (consultation selon droits).
- **Validation en ligne** des devis, engagements de dépenses, mises en concurrence.
- Gestion des **réunions** : convocations, ordres du jour, comptes rendus, tâches suivies.
- Accès aux **pièces comptables** pour le **contrôle des comptes** (rendez-vous, consultation, copie).
- Suivi des **délégations de pouvoir** éventuelles en dehors de l'AG.

### 4.7 Fournisseurs, contrats et mise en concurrence

- Base **fournisseurs** : coordonnées, SIRET, domaine d'intervention, **attestations obligatoires** (assurance, URSSAF, Kbis), alertes d'expiration.
- **Contrats** : ascenseur, chauffage, nettoyage, espaces verts, gardiennage, assurance, etc. avec dates, échéances, préavis, reconduction tacite, alertes de **renégociation ou mise en concurrence**.
- **Mise en concurrence** : demandes de devis comparatives, grille de comparaison, historique, décision (avec transmission au conseil syndical et à l'AG au-dessus du seuil voté).
- **Ordres de service** et bons de commande.
- Suivi des **sinistres et garanties** (décennale, dommages-ouvrage, parfait achèvement) avec échéances.

### 4.8 Travaux et maintenance

- **Gestion des incidents** : tickets de signalement (parties communes), priorité, assignation à un prestataire, suivi, photos, délais.
- **Carnet d'entretien** de l'immeuble : dates, travaux, contrats, garanties (obligation légale à tenir à jour).
- **Diagnostic technique global (DTG)** et **projet de plan pluriannuel de travaux (PPT)** : stockage, suivi des travaux sur 10 ans, budget prévisionnel, lien avec le fonds travaux.
- **Audit énergétique / DPE collectif** : dates, résultats, obligations selon la taille et l'âge de la copropriété.
- **Projets de travaux** : cycle complet (idée → devis → vote en AG → ordre de service → suivi de chantier → réception → levée des réserves → garanties), maître d'œuvre, architecte, assurances (dommages-ouvrage).
- **Appels de fonds travaux** automatiques selon le vote, suivi des **subventions** (MaPrimeRénov' Copropriété, CEE, aides locales) et des **prêts collectifs**.
- **Maintenance préventive** : planning des vérifications obligatoires (ascenseurs, extincteurs, installations électriques, gaz, chaudières, toitures, désenfumage, etc.).
- Cas spécifiques : **IRVE** (bornes de recharge), accessibilité, sécurité incendie.

### 4.9 Ventes de lots (mutations)

- **Pré-état daté** et **état daté** (documents financiers destinés au notaire) avec **plafonnement des tarifs** pour ce qui est facturable au vendeur.
- Questionnaire notarié, **attestations de solde**, certificat de l'article 20 (opposition du syndic).
- **Fiche synthétique** de la copropriété (à jour, mise à disposition des candidats acquéreurs).
- Documents à fournir à l'acheteur : règlement de copropriété, PV des trois dernières AG, carnet d'entretien, DTG / PPT, etc., **assemblés automatiquement**.
- Gestion de l'**ancien / nouveau copropriétaire** : répartition des charges, transfert du fonds travaux, mise à jour du référentiel.

### 4.10 Assurances et sinistres

- Contrats d'assurance de l'immeuble (multirisque, responsabilité civile, dommages-ouvrage), échéances, franchises, capitaux.
- **Déclaration de sinistre** : dégât des eaux, incendie, vandalisme, avec suivi du dossier et application des **conventions inter-assureurs**.
- Suivi des **indemnisations** et de leur comptabilisation.
- Alertes de renouvellement et comparatifs.

### 4.11 Personnel de l'immeuble (si applicable)

- Fiche des **gardiens, concierges et employés d'immeuble** (convention collective applicable), contrats, avenants, congés, absences.
- **Paie et déclarations sociales** (DSN, URSSAF) – intégration native ou **connecteur vers un logiciel de paie** (module complexe, souvent externalisé).
- Logement de fonction, avantages en nature, répartition des charges de personnel.

### 4.12 Documents et archivage (GED)

- **Gestion électronique des documents** structurée par copropriété : règlement, PV, contrats, comptes, factures, courriers, diagnostics, plans, assurances.
- Métadonnées, droits d'accès fins, versions, **recherche plein texte (OCR)**.
- **Archivage légal** : conservation des pièces comptables (au moins 10 ans), des PV, des documents de la copropriété ; gestion des **durées de conservation** et suppression conforme RGPD.
- **Transmission du dossier au syndic suivant** (restitution des archives à la fin du mandat) : export complet standardisé.
- Modèles de courriers et documents (mise en demeure, convocation, attestations).

### 4.13 Communication et portail copropriétaires (extranet)

- **Accès en ligne sécurisé** aux documents de gestion (obligatoire pour les syndics professionnels, fortement recommandé pour un syndic bénévole car il rend la gestion transparente pour le conseil syndical).
- Espace copropriétaire : **solde du compte**, historique des appels et paiements, documents de l'AG, règlement, PV, contrats, carnet d'entretien, coordonnées du gestionnaire.
- **Paiement en ligne** (carte, virement instantané, prélèvement).
- Signalement d'incidents, suivi des demandes.
- **Messagerie interne** et notifications (email, SMS, push mobile).
- **Annonces et panneau d'affichage** numérique.
- **Courrier hybride** : envoi postal automatisé (impression, mise sous pli, affranchissement) via prestataire.
- **Application mobile** (PWA ou native) pour copropriétaires et conseil syndical.

### 4.14 Conformité réglementaire et alertes

Tableau de bord de conformité par copropriété :

- **Immatriculation au registre national des copropriétés** : numéro, mise à jour annuelle, alertes.
- **Fonds de travaux** : cotisation, solde, placement.
- **PPT / DTG / DPE collectif / audit énergétique** : échéances selon l'âge et la taille.
- **Fiche synthétique** : mise à jour annuelle.
- **Carnet d'entretien** : date de dernière mise à jour.
- **Contrat de syndic** : date de fin de mandat du syndic bénévole ou coopératif, rappel de la désignation à voter en AG.
- **Assurance** : attestation en cours de validité.
- **Échéances d'AG** : délai de convocation, approbation des comptes.
- **Vérifications périodiques obligatoires** (ascenseur, sécurité).
- Calendrier et **notifications automatiques** vers le gestionnaire.

### 4.15 Fonctions propres au syndic bénévole et coopératif

- **Mandat du syndic** : désignation en AG, durée, éventuelle indemnité (à voter), renouvellement, révocation et **passation à un successeur**.
- **Mode guidé pas à pas** : calendrier annuel (clôture, budget, convocation, AG, PV, appels de fonds), checklist des tâches obligatoires, explication en langage simple de la règle juridique à chaque étape.
- **Contrôle croisé par le conseil syndical** : validation des paiements, accès en lecture aux comptes, rapport de contrôle des comptes, afin de limiter les erreurs et les soupçons.
- **Responsabilité et assurance** : suivi de l'assurance responsabilité civile du syndicat et de la couverture du syndic non professionnel (à vérifier), **journal des actions et décisions** du syndic.
- **Continuité** : délégation temporaire, accès de secours, export complet de passation en cas d'indisponibilité, de changement de syndic ou de passage futur à un syndic professionnel.
- **Syndic coopératif** : séparation claire entre les fonctions de syndic et de président du conseil syndical, vote du quitus sans conflit d'intérêts apparent.
- **Aide intégrée** : fiches pratiques, modèles de courriers, FAQ juridique, renvois vers des ressources d'information (par exemple associations de copropriétaires, ADIL).

## 5. Rapports et tableaux de bord

**Rapports réglementaires**

- États financiers et annexes comptables (voir §4.2), **comptes rendus d'exercice**.
- **Rapport d'activité du syndic** présenté en AG.
- **Convocation, PV, feuille de présence** (modèles conformes).
- **Fiche synthétique**, état daté, pré-état daté.

**Rapports de gestion**

- Budget vs réalisé par poste, avec écarts expliqués.
- Balance des copropriétaires, **état des impayés** et vieillissement.
- Trésorerie prévisionnelle, situation des fonds travaux.
- Liste des contrats avec échéances, coûts annuels par fournisseur.
- Suivi des travaux (avancement, coûts engagés / prévus).
- **Indicateurs de qualité** : délai de traitement des incidents, délai de réponse, taux d'encaissement.

**Exports**

- PDF, Excel / CSV, FEC, formats d'échange (SEPA, CFONB).
- **API** pour intégration avec d'autres systèmes.

## 6. Outils transverses

- **Modèles de documents** personnalisables (publipostage, champs dynamiques).
- **Signature électronique** (simple, avancée, qualifiée selon l'usage).
- **Lettre recommandée électronique (LRE)** avec valeur probante.
- **Workflows et automatisations** (relances, validations, alertes).
- **Agenda** et rappels, **gestion des tâches**.
- **Recherche globale** transversale.
- **Notifications multicanales** (email, SMS, push).
- **Import / export** de données, outils de migration.
- **Multilingue** (au minimum français, éventuellement anglais pour copropriétaires étrangers).
- **Aide contextuelle** et rappel des règles juridiques dans les écrans (ex. majorité requise à côté d'une résolution).

## 7. Sécurité, conformité et exigences non fonctionnelles

**Protection des données (RGPD)**

- Registre des traitements, **base légale** pour chaque traitement, information des personnes.
- Droits des personnes : accès, rectification, effacement, portabilité, opposition.
- **Durées de conservation** paramétrées, purge ou anonymisation automatiques.
- **Sous-traitants** (hébergeur, SMS, courrier) : contrats conformes, hébergement en Union européenne.
- **Analyse d'impact** (AIPD) recommandée compte tenu du volume de données (identités, adresses, situation financière).

**Sécurité technique**

- **Authentification forte (2FA)**, gestion des mots de passe, SSO pour les cabinets.
- **Chiffrement** des données en transit et au repos, gestion des clés.
- **Cloisonnement strict** entre copropriétés et entre clients (architecture multi-tenant sécurisée).
- **Journalisation et audit** (qui a fait quoi, quand), logs inaltérables sur les opérations comptables.
- **Sauvegardes** régulières, tests de restauration, **plan de reprise d'activité**.
- Tests de pénétration, gestion des vulnérabilités, **politique de mise à jour**.

**Fiabilité et performance**

- Disponibilité cible (par ex. 99,9 %), supervision, alertes.
- Intégrité comptable : transactions atomiques, contrôles d'équilibre, verrouillage des périodes.
- **Traçabilité juridique** : horodatage des envois, preuves de notification, conservation des accusés.
- Accessibilité (RGAA / WCAG) et ergonomie, notamment sur mobile.

## 8. Comparaison avec les solutions du marché (benchmark indicatif)

| Domaine | Attendu du marché professionnel | Remarque pour votre produit |
| --- | --- | --- |
| Comptabilité | Plan comptable syndic, annexes, rapprochement bancaire | Non négociable : la conformité comptable est le cœur de la valeur |
| AG | Convocations, pouvoirs, votes, PV, majorités automatiques | Principal facteur de différenciation (guidage juridique, visio, vote en ligne) |
| Extranet | Portail copropriétaire / conseil syndical | Attendu aujourd'hui, c'est un standard du secteur |
| Recouvrement | Relances, mises en demeure, suivi contentieux | À soigner : la trésorerie de la copropriété en dépend |
| GED et travaux | Documents, carnet d'entretien, suivi de chantier | Fort impact sur la satisfaction des conseils syndicaux |
| Open source (type Diacamma) | Modules lots, appels de fonds, comptabilité, AG | Utile comme référence fonctionnelle et pour ce qu'un petit syndic bénévole attend |

Pour affiner : testez en démo (ou en version d'essai) 2 ou 3 logiciels existants et listez, écran par écran, ce qui est indispensable, redondant ou manquant.

## 9. Priorisation : MVP, V1, V2

**MVP (cœur indispensable, 4 à 6 mois pour une petite équipe)**

- Référentiel copropriété / lots / tantièmes / copropriétaires.
- Comptabilité de base : plan comptable, budget, appels de fonds, encaissements, factures, rapprochement bancaire, états de clôture.
- Relances et suivi des impayés (sans contentieux avancé).
- AG : ordre du jour, convocation, pouvoirs, saisie des votes, calcul des majorités, PV.
- GED simple et portail copropriétaire en lecture (solde, documents).
- **Mode guidé du syndic bénévole** : calendrier annuel, checklist des obligations, rappels juridiques à chaque étape.
- Sécurité, rôles, journal d'audit, RGPD de base.

**V1 (produit complet pour une copropriété)**

- Annexes comptables complètes, fonds travaux, régularisation de charges, SEPA.
- AG hybrides (visio, vote par correspondance), signatures électroniques, LRE.
- Fournisseurs, contrats, mises en concurrence, incidents, carnet d'entretien.
- Mutations (état daté, pré-état daté), fiche synthétique.
- Extranet complet avec paiement en ligne, application mobile.
- Tableau de bord de conformité.

**V2 (différenciation)**

- Contentieux et recouvrement avancés.
- Travaux : PPT, subventions, prêts collectifs, suivi de chantier détaillé.
- Paie / personnel de l'immeuble, intégration bancaire avancée.
- API publique, intégrations (comptabilité, notaires, assureurs).
- Assistance par IA : rédaction de résolutions, lecture de factures, détection d'anomalies comptables, résumé de PV.
- Module syndic professionnel (carte professionnelle, honoraires, multi-copropriétés) : **hors périmètre actuel**, à envisager plus tard.

## 10. Architecture technique recommandée (à adapter)

- **Application web** responsive + PWA mobile ; API REST ou GraphQL documentée.
- **Back-end** typé et robuste (Python/Django comme Diacamma, Node/NestJS, Java/Spring ou .NET), avec une **base PostgreSQL** (transactions, contraintes d'intégrité, row-level security pour le multi-tenant).
- **Moteur comptable isolé** (module dédié, tests unitaires exhaustifs, aucune modification directe des écritures).
- **Moteur de règles juridiques** (majorités, délais, seuils) configurable et versionné, pour s'adapter aux évolutions législatives sans refonte.
- **Moteur de documents** (génération PDF, modèles), stockage objet chiffré, OCR.
- **Files de tâches** (relances, envois, imports bancaires), notifications.
- Intégrations : banques (agrégateur / CFONB), SEPA, LRE, signature électronique, paiement en ligne, courrier hybride, SMS.
- **Hébergement en UE**, environnements séparés (dev / recette / production), CI/CD, supervision.

## 11. Risques et points d'attention

1. **Conformité comptable** : un moteur mal conçu invalide tout le produit. Faites relire le modèle par un expert-comptable spécialisé en copropriété.
2. **Évolution législative fréquente** : prévoyez une veille juridique et un moteur de règles paramétrable.
3. **Valeur probante** des convocations, notifications et PV : conservez les preuves d'envoi et de réception.
4. **Responsabilité** : le syndic bénévole engage sa responsabilité personnelle ; le logiciel doit réduire le risque (alertes, blocages) sans donner l'illusion d'un conseil juridique.
5. **Sécurité et confidentialité** : données financières et personnelles sensibles, cible attractive pour des attaques.
6. **Migration de données** : la reprise des données d'un ancien logiciel est souvent le principal frein commercial.
7. **Périmètre trop large dès le début** : commencez par la comptabilité et les AG, qui sont le cœur.
8. **Réforme de la facturation électronique** : vérifier les obligations applicables aux syndicats et aux syndics.

## 12. Checklist synthétique de fonctionnalités

| Domaine | Fonctionnalités clés | Priorité |
| --- | --- | --- |
| Référentiel | Lots, tantièmes, clés de répartition, copropriétaires, mutations | MVP |
| Comptabilité | Plan comptable, budget, appels de fonds, banque, clôture, annexes, mode simplifié | MVP / V1 |
| Fonds travaux | Cotisation, suivi par lot, compte dédié | V1 |
| Charges | Clés multiples, charges récupérables, individualisation | V1 |
| Recouvrement | Relances, mises en demeure, contentieux | MVP / V2 |
| AG | Ordre du jour, convocation, pouvoirs, votes, majorités, PV, notifications | MVP / V1 |
| Conseil syndical | Espace dédié, validations, réunions, contrôle des comptes | V1 |
| Fournisseurs et contrats | Base, échéances, mise en concurrence | V1 |
| Travaux | Incidents, carnet d'entretien, DTG/PPT, chantiers, subventions | V1 / V2 |
| Mutations | État daté, pré-état daté, fiche synthétique | V1 |
| Assurances | Contrats, sinistres | V1 |
| Personnel | Fiches, paie (connecteur) | V2 |
| GED | Documents, OCR, archivage, passation de dossier | MVP / V1 |
| Extranet | Portail, paiement, messagerie, mobile | MVP / V1 |
| Conformité | Tableau de bord, alertes, immatriculation | V1 |
| Syndic bénévole / coopératif | Mandat, mode guidé, contrôle croisé, responsabilité, passation | MVP / V1 |
| Sécurité / RGPD | Rôles, 2FA, audit, chiffrement, sauvegardes | MVP |
| Outils | Signature électronique, LRE, workflows, API | V1 / V2 |

## 13. Prochaines étapes recommandées

1. **Choisir la cible** (bénévole seul, coopératif seul ou les deux ; le professionnel est exclu pour l'instant) et le modèle économique.
2. **Rencontrer 3 à 5 syndics bénévoles ou coopératifs et conseils syndicaux** pour valider les priorités.
3. **Tester 2 à 3 logiciels concurrents** (dont Diacamma Syndic en open source) et documenter les manques.
4. Faire valider le **modèle comptable** et les **règles d'AG** par un expert-comptable et un juriste en droit de la copropriété.
5. Rédiger les **user stories** détaillées du MVP, puis les maquettes des écrans critiques (appel de fonds, saisie de facture, AG).
6. Choisir la **stack technique** et poser l'architecture (comptabilité, règles juridiques, GED).
7. Lancer un **pilote** sur une ou deux copropriétés réelles avant le déploiement.
