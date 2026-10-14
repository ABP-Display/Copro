# Architecture et reprise progressive

## Découpage

Le navigateur exécute React. L'interface transmet des requêtes JSON à Django
sur `/api/`. Django valide les données, contrôle la session et les droits, puis
lit ou écrit dans PostgreSQL. Nginx expose ces deux parties sur une même origine :
aucun jeton d'accès n'est stocké dans localStorage, et CORS n'est pas nécessaire.

La session utilise un cookie HttpOnly. La connexion, la déconnexion et toutes
les écritures nécessitent un jeton CSRF. Les écrans de gestion sont réservés
aux utilisateurs actifs avec `is_staff`. Les comptes liés à un propriétaire
disposent d'un espace de lecture distinct ; les droits sont contrôlés sur
chaque endpoint, y compris les données financières détaillées. L'endpoint session délivre le jeton
et l'identité ; aucune donnée de copropriété n'est accessible anonymement.
`/api/health/` vérifie la connexion à la base sans exposer ses identifiants.

Les données de ce premier périmètre sont volontairement simples : un propriétaire
par lot, des tantièmes généraux stockés en Decimal, des surfaces facultatives.
Les lots sans propriétaire sont autorisés pendant la saisie initiale.
La suppression d'un propriétaire avec des lots est bloquée au niveau ORM/SQL.
Les numéros de lot sont uniques. Les tantièmes et surfaces négatifs sont rejetés
à la fois par validation et par contraintes SQL.

Le module `finance` apporte un premier moteur natif : écritures en partie
double atomiques, numérotation sous verrou d'exercice, appels de fonds figés,
factures, règlements, catégories et synthèses publiques. Les données comptables
détaillées restent privées. Le suivi exhaustif de la reprise, qui **n'est pas
terminée**, est documenté dans `REPRISE-DIACAMMA.md` et `../reference/diacamma-inventory.json`.

## Séparation de la référence

`reference/diacamma/` conserve Diacamma et ses ajouts Docker précédents. Son
historique Git est préservé dans ce fork. Le dépôt est relié à
`https://github.com/Ydoxide/copro..git`. L'instance locale historique dans
`../syndic/` reste indépendante. Les bases et les volumes sont séparés.
Aucune migration ou import des données Diacamma n'a encore été exécuté.

## Ordre de reprise proposé

1. **Livré :** sessions, annuaire, lots et tantièmes généraux.
2. **Clés de charges :** analyser `Set`, `Partition`, `SetCost` et les clés
   secondaires dans `diacamma/condominium/models.py`. Ajouter les quotes-parts
   propres à chaque catégorie et leur validation.
3. **Appels de fonds :** étudier `CallFunds`, `CallDetail`, leurs transitions
   et tests. Extraire les calculs de l'affichage Xfer. Comparer les résultats
   avec des cas Diacamma connus avant d'activer toute écriture comptable.
4. **Dépenses et règlements :** analyser `Expense`, `ExpenseDetail`,
   `ExpenseRatio` et les modules `diacamma.accounting` / `diacamma.payoff`, qui
   sont des dépendances externes absentes du dépôt métier cloné.
5. **Comptabilité :** exercices, journaux, écritures équilibrées, clôture,
   régularisations et éditions. Préserver la précision Decimal, les arrondis,
   les contrôles et les traces de modification. Prévoir la validation avec
   des données fictives représentatives avant l'utilisation réelle.
6. **Collaboration :** documents, incidents, tâches, historique et droits
   individuels des copropriétaires, avec des tests d'isolement des données.

Cette nouvelle application n'hérite pas automatiquement de la couverture
fonctionnelle de Diacamma. Chaque fonctionnalité reprise doit disposer de ses
propres tests et d'un contrôle de cohérence avec le comportement de référence.

## Vérifications du premier périmètre

Les tests `core`, `finance`, `documents`, `governance` et `operations` sont exécutés sur PostgreSQL : absence d'accès anonyme,
refus des comptes non gestionnaires, validation et modification partielle,
tantièmes décimaux, protection des propriétaires référencés, JSON invalide,
méthodes HTTP, connexion et déconnexion avec CSRF imposé. Les 112 tests actuels
couvrent aussi les accès membres et les premiers parcours financiers décrits
dans `REPRISE-DIACAMMA.md`.
La gestion comptable avancée, ses rapports et la configuration disposent de
routes séparées dans `finance/advanced.py`, avec les calculs d'états dans
`finance/reporting.py`. `COMPARAISON-DIACAMMA.md` décrit la couverture des menus
observés dans l'instance historique et les écarts restant à traiter.
`documents` gère les dossiers, métadonnées et versions ; les fichiers UUID résident
dans un volume dédié non exposé par Nginx. Les téléchargements passent par les
contrôles Django. Les anciens règlements complets sont rattachés au nouveau modèle
de paiements par la migration finance 0004, sans réécrire le journal comptable.
Le frontend est vérifié par TypeScript et compilation Vite, puis par un parcours
dans le navigateur avec des coordonnées fictives.

`operations/partners.py` regroupe les API privées fournisseurs/contrats/attestations
et l’API d’annonces publiée pour les membres. Les nouveaux modèles conservent les
liens historiques ; leurs créations/modifications sont journalisées. Aucun compte
fournisseur ni écriture comptable n’est créé par ces parcours de suivi manuel.

Documentation de référence :
- <https://docs.djangoproject.com/en/5.2/howto/csrf/>
- <https://react.dev/learn/creating-a-react-app>
- <https://vite.dev/guide/>

Le module `governance` expose `/api/ag/` pour les dossiers de préparation, les
résolutions et trois outils. Les accès sont réservés aux gestionnaires, avec
CSRF sur les écritures. Les simulations sont recalculées côté serveur ; un second
vote conserve le premier. La modification d’une résolution efface son calcul
devenu obsolète. Les dossiers archivés sont verrouillés jusqu’à restauration.
Les outils de répartition et d’échéancier n’écrivent rien en comptabilité.

`finance/banking.py` gère les banques et transferts enregistrés. `Line.supplier` relie les dettes/règlements à un fournisseur, sans deviner l’identité des anciennes lignes. Les migrations finance 0005/0006 sont additives. Les commentaires budgétaires et le comparatif précédent sont calculés dans `finance/reporting.py`.
