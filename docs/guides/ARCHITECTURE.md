# Architecture de Copro.

## Interface, API et données

React / TypeScript fournit l’interface. Nginx sert les fichiers et transmet `/api/`
à Django sur la même origine. Django vérifie la session, les droits et les données,
puis lit ou écrit dans PostgreSQL. Les pièces résident dans un volume distinct et
leurs téléchargements passent par un contrôle d’accès Django.

La session utilise un cookie HttpOnly. Les mutations nécessitent un jeton CSRF.
Les cookies Secure sont activés par `HTTPS_ONLY=1` pour une installation HTTPS.
Les fichiers ne sont pas exposés directement par Nginx.

## Modules

| Module | Responsabilité |
| --- | --- |
| `core` | Copropriétaires, lots, sessions, compte initial et accès |
| `finance` | Écritures atomiques, appels, factures, règlements, banques, rapports et clôture |
| `governance` | Dossiers AG, convocations, votes, PV, preuves et décisions |
| `council` | Mandats datés, capacités par rôle, avis du conseil et contrôle indépendant |
| `documents` | Dossiers, pièces, versions, archivage et partage |
| `operations` | Fournisseurs, contrats, travaux/sinistres, relances et métriques |

Le rôle de gestion est calculé par `council.access.is_manager` : accès permanent de
gestion ou mandat de syndic effectivement actif. Les rôles du conseil, du trésorier
et du contrôleur ne rendent pas le compte gestionnaire. Leur espace utilise les routes
spécifiques `/api/council/`. Les droits sont vérifiés côté serveur, y compris pour les
fichiers, les avis et les rapports. Les accès temporaires imposent un changement de mot
de passe avant l’accès aux données.

Les mandats sont liés à un compte déterminé. Ils ont des dates, une désignation et une
pièce ; le retrait est motivé et conservé. La présidence dépend de son mandat de membre
du conseil. Un contrôleur indépendant ne cumule pas une mission de gestion ou de conseil
sur la même période. Les comptes permanents restent sous contrôle de l’administrateur.

## Écritures et contrôle

Les montants utilisent Decimal. Les écritures sont équilibrées et numérotées sous
verrou d’exercice. Les règlements fournisseurs prennent en compte les paiements partiels.
Les répartitions, corrections et clôtures conservent leurs traces.

Le contrôle du conseil fige les données et la version de la pièce. Un refus, un dossier
modifié ou un nombre insuffisant d’avis bloque la suite. Le contrôle intervient avant
la sélection du devis et avant l’enregistrement du règlement fournisseur, selon la règle
configurée. Une préparation de dépense n’écrit rien en comptabilité avant sa reprise
explicite par le syndic.

Les rapports indépendants finalisés sont conservés avec une empreinte des comptes,
budgets, répartitions et rapprochements examinés. Les changements ultérieurs sont signalés.
Les contrôles internes ne remplacent pas les décisions collectives nécessaires.

## Déploiement et maintenance

`compose.yaml` crée PostgreSQL, Django et le frontend. Le port publié appartient à Nginx.
Le démarrage backend applique les migrations et crée le compte initial s’il n’existe pas.
Les schémas sont versionnés dans les migrations des applications.

Sauvegarder PostgreSQL et le volume des pièces ensemble. Les tests utilisent une base
séparée et des répertoires temporaires. Le frontend est compilé avec TypeScript et Vite,
puis les parcours sont contrôlés dans le navigateur, sur ordinateur et mobile.

Le dépôt courant est [abp-display/Copro](https://github.com/abp-display/Copro).
Les sources et notices de provenance restent séparées de l’interface du produit.
L’application demeure mono-copropriété ; la [feuille de route](PROCHAINS-CHANTIERS.md)
suit les limites et évolutions prévues.
