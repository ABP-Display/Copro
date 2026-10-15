# Copro. — la copropriété, ensemble

Application libre et auto-hébergeable pour gérer une copropriété avec un syndic
bénévole ou coopératif : comptes, assemblées générales, conseil syndical, documents
et suivi des dossiers. L’interface est en français, avec React / TypeScript,
Django / Python et PostgreSQL.

[Code source](https://github.com/abp-display/Copro) ·
[Documentation](docs/README.md) ·
[Guide de la première AG](docs/guides/AG-PREMIERS-PAS.md) ·
[Prochains chantiers](docs/guides/PROCHAINS-CHANTIERS.md)

## Fonctionnalités disponibles

| Thème | Ce que permet l’application |
| --- | --- |
| Copropriété | Annuaire des copropriétaires, lots, tantièmes, clés de répartition et changements de propriétaire avec historique. |
| Comptabilité | Exercices, reprise des soldes, plan comptable, budgets, factures fournisseurs, appels de fonds et échéanciers, règlements partiels, lettrage et suivi des impayés. |
| Trésorerie et clôture | Comptes bancaires, import de relevés CSV, rapprochement, fonds travaux par lot, affectations aux travaux, régularisation, contrôles de clôture et report vers l’exercice suivant. |
| Rapports | Journaux, balance, comparatifs budgétaires, dossier comptable annuel, impressions et exports de données. |
| Assemblées générales | Préparation, résolutions, convocations, présences, pouvoirs, correspondance, calculs et enregistrement des votes, PV, pièces signées, suivi des notifications, décisions et registre. |
| Conseil syndical | Mandats datés, responsabilités et permissions ciblées, préparation des dépenses par le trésorier, avis motivés, contrôle avant règlement ou sélection d’un devis et rapports indépendants. |
| Dossiers et suivi | Fournisseurs, contrats, attestations, dossiers travaux et sinistres, devis, relances préparées et annonces. |
| Documents et extranet | Pièces versionnées, partage explicite, compte personnel du copropriétaire et consultation des informations publiées. |
| Aide au quotidien | Menu regroupé par catégories, navigation repliable, guide AG en six étapes avec FAQ et lexique, analyses métriques locales et alertes sur l’accueil. |

### Un parcours comptable de la reprise à la clôture

La reprise enregistre une balance équilibrée. Les dépenses et appels conservent
leurs répartitions, les règlements peuvent être partiels et le lettrage permet
de suivre les sommes restant dues. Les relevés CSV servent au rapprochement bancaire.
En fin d’exercice, le gestionnaire prépare la régularisation, résout les contrôles,
puis clôture avec conservation d’un instantané et report détaillé des soldes.

Le [guide comptable](docs/guides/COMPTABILITE-CYCLE.md) explique le démarrage,
la gestion courante, les fonds travaux, les mutations et la fin d’exercice.

### Une AG accompagnée en six étapes

1. Créer l’assemblée, les résolutions et la liste des votants depuis l’annuaire.
2. Relire et figer le dossier de convocation, préparer les documents et conserver les preuves de notification.
3. Enregistrer les présences réelles, les pouvoirs, les formulaires de correspondance et le bureau élu.
4. Saisir les votes, consulter le calcul des majorités et enregistrer les éventuels seconds tours.
5. Préparer le procès-verbal et rattacher les versions signées du PV et de la feuille de présence.
6. Suivre les notifications, reprendre les décisions adoptées et clore le dossier au registre.

Les simulations restent distinctes des votes enregistrés en séance. Les décisions
peuvent alimenter les budgets, appels, régularisations et mandats après vérification
par le gestionnaire. Le [guide pas à pas](docs/guides/AG-PREMIERS-PAS.md) est aussi
disponible dans la section Assemblée générale de l’application.

### Conseil syndical et contrôle des dépenses

Les mandats ont une période de validité et peuvent être révoqués avec un motif.
Le mode coopératif lie les droits de présidence/syndic au mandat de membre du conseil.
Les demandes de validation conservent les justificatifs, les avis et l’historique ;
un avis doit être motivé et son auteur ne peut pas approuver sa propre demande.

Le trésorier peut préparer une dépense sans créer d’écriture. Le syndic la
comptabilise après les validations requises. Un contrôleur indépendant peut rédiger
un rapport avec observations et preuves ; un rapport finalisé est figé, et une
modification ultérieure des comptes contrôlés est signalée.

**Le contrôle obligatoire des dépenses est désactivé par défaut.** L’administrateur
configure les seuils et le nombre d’avis dans **Conseil syndical → Mode & règles**.
Voir le [guide des mandats et du contrôle](docs/guides/CONSEIL-SYNDICAL.md).

## Installer avec Docker

Prérequis : Docker et Docker Compose, conteneurs Linux.

```sh
git clone https://github.com/abp-display/Copro.git
cd Copro
cp .env.example .env
```

Sous PowerShell, utiliser `Copy-Item .env.example .env` à la place de `cp` si nécessaire.

Avant de démarrer, compléter `.env` :

| Variable | Utilisation |
| --- | --- |
| `POSTGRES_PASSWORD` | Mot de passe de PostgreSQL. |
| `DJANGO_SECRET_KEY` | Secret aléatoire de l’application Django. |
| `ADMIN_PASSWORD` | Mot de passe initial de l’administrateur, au moins 12 caractères. |
| `ADMIN_USERNAME` | Identifiant initial, `admin` par défaut. |
| `WEB_PORT` / `WEB_BIND_ADDRESS` | Port et interface d’écoute, `8081` et `0.0.0.0` par défaut. |
| `DJANGO_ALLOWED_HOSTS` | Noms de domaine et IP autorisés, séparés par des virgules. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origines de confiance, avec leur préfixe `https://` ou `http://`. |
| `HTTPS_ONLY` | `1` pour les cookies sécurisés en HTTPS, `0` pour le développement HTTP. |

Choisir trois secrets différents et aléatoires. Le fichier `.env` reste privé et exclu de Git.

```sh
docker compose up -d --build
docker compose ps
```

Ouvrir [localhost:8081](http://localhost:8081). L’identifiant initial est `admin`
(ou `ADMIN_USERNAME`) ; son mot de passe est `ADMIN_PASSWORD`. Il doit comporter au moins
12 caractères. Le compte est créé une seule fois : modifier `.env` ne change pas un
mot de passe déjà enregistré.

```sh
docker compose down                    # Arrêt conservant les données
docker compose logs --tail 100 backend # Journaux
docker compose up -d --build           # Mise à jour après modification
docker compose exec backend python manage.py changepassword admin
```

PostgreSQL et les pièces résident dans deux volumes distincts : sauvegarder les deux
ensemble. `docker compose down -v` supprime les volumes et leurs données.

## Premiers pas

1. Renseigner la copropriété et choisir le mode bénévole ou coopératif.
2. Créer les copropriétaires et leurs lots, puis vérifier les tantièmes et clés de répartition.
3. Créer l’exercice, les banques et fournisseurs, puis préparer la reprise des soldes.
4. Attribuer les mandats et configurer les règles de validation des dépenses si elles sont souhaitées.
5. Ajouter les justificatifs, saisir les opérations courantes et préparer la prochaine AG.

Les rubriques du menu latéral regroupent les outils par thème. Cliquer sur le titre
d’une catégorie ouvre sa présentation ; sa flèche affiche directement les sous-pages.

## Accès et responsabilités

Créer les copropriétaires depuis l’annuaire. Avec un courriel, un compte et un mot de
passe temporaire sont générés. Le mot de passe est affiché une seule fois, puis doit
être remplacé à la première connexion. « Préparer le courriel » ouvre la messagerie ;
aucun courriel n’est envoyé automatiquement. Les comptes suspendus restent suspendus.

| Accès | Responsabilité principale |
| --- | --- |
| Administrateur principal | Configuration et attribution ou révocation des mandats. |
| Syndic bénévole / président-syndic coopératif | Gestion, comptabilisation et enregistrement des règlements. |
| Président, vice-président ou membre du conseil | Consultation des comptes et justificatifs, avis sur les dépenses. |
| Trésorier | Consultation et préparation des dépenses avec leurs pièces. |
| Contrôleur indépendant | Consultation et rédaction des rapports de contrôle. |
| Copropriétaire | Consultation de son compte et des informations explicitement partagées ; les données privées des autres restent protégées. |

L’administrateur principal attribue les mandats dans **Conseil syndical → Composition
& mandats**. Les droits prennent effet aux dates prévues et cessent à l’échéance ou au
retrait. Les accès permanents de gestion restent gérés séparément dans
**Administration → Utilisateurs**. Le [guide du conseil](docs/guides/CONSEIL-SYNDICAL.md)
précise les incompatibilités et les conditions de chaque rôle.

## Site de présentation et GitHub Pages

La vitrine est un site statique autonome : ouvrir [docs/index.html](docs/index.html)
dans un navigateur, sans serveur, installation ni compilation.

Pour la publier, envoyer les fichiers sur GitHub puis choisir **Settings → Pages →
Deploy from a branch → branche contenant les fichiers → /docs → Save**.
Les ressources de la vitrine sont dans `docs/assets/` ; `docs/_config.yml` exclut les
guides et fichiers de travail de cette publication.

GitHub Pages héberge la présentation. L’application de gestion et sa base de données
se déploient avec Docker sur votre serveur. Voir le
[guide de publication](docs/guides/GITHUB-PAGES.md).

## Réseau et HTTPS

Seul le port web est publié. Nginx sert l’interface et transmet `/api/` à Django ;
le navigateur n’accède pas directement à PostgreSQL.

- Réseau local : `WEB_BIND_ADDRESS=0.0.0.0`, `WEB_PORT=8081` et ajouter l’IP du serveur
  dans `DJANGO_ALLOWED_HOSTS`. Depuis un autre PC, utiliser l’IP réelle du serveur.
- Accès limité au PC : `WEB_BIND_ADDRESS=127.0.0.1`.
- Domaine configuré : `copro.ydoxide.fr`, avec origine `https://copro.ydoxide.fr` dans
  `DJANGO_CSRF_TRUSTED_ORIGINS`. Le DNS et le certificat restent gérés à l’extérieur.
- Reverse proxy sur le même PC : destination `127.0.0.1:8081` pour un proxy natif,
  ou `host.docker.internal:8081` pour un proxy dans Docker Desktop.
- Installation uniquement HTTPS : `HTTPS_ONLY=1` pour les cookies Secure. Conserver
  `0` pendant le développement HTTP local. Recréer les services après modification.

## Documentation

| Besoin | Guide |
| --- | --- |
| Trouver tous les documents | [Index de la documentation](docs/README.md) |
| Comprendre le périmètre bénévole / coopératif | [Périmètre du produit](docs/guides/PERIMETRE-PRODUIT.md) |
| Tenir les comptes et clôturer | [Parcours comptables](docs/guides/COMPTABILITE-CYCLE.md) |
| Organiser sa première assemblée | [Première AG, pas à pas](docs/guides/AG-PREMIERS-PAS.md) |
| Approfondir les votes et le dossier AG | [Assemblées générales et outils](docs/guides/AG-OUTILS.md) |
| Attribuer les rôles et contrôler les dépenses | [Conseil syndical et contrôle](docs/guides/CONSEIL-SYNDICAL.md) |
| Comprendre les alertes et dossiers | [Suivi et analyses métriques](docs/guides/SUIVI-METRIQUES.md) |
| Connaître les fonctions complètes, partielles et absentes | [Audit du cahier](docs/guides/AUDIT-FONCTIONNALITES.md) |
| Consulter les priorités restantes | [Prochains chantiers](docs/guides/PROCHAINS-CHANTIERS.md) |
| Comprendre le code | [Architecture](docs/guides/ARCHITECTURE.md) |

## État du projet et prochaines étapes

Les parcours décrits sont disponibles, mais toutes les exigences du cahier ne sont
pas terminées. L’[audit détaillé](docs/guides/AUDIT-FONCTIONNALITES.md) et la
[couverture fonctionnelle](docs/guides/COUVERTURE-FONCTIONNELLE.md) distinguent les
fonctions utilisables des développements partiels.

- **Une seule copropriété actuellement** : le sélecteur visuel ne fournit pas encore l’isolation nécessaire pour plusieurs copropriétés.
- **Envois et signatures externes** : l’application prépare les documents et conserve les preuves. Les courriels préparés ouvrent votre messagerie ; signature électronique, recommandé connecté, visioconférence et vote direct depuis l’extranet restent à développer.
- **Règlements enregistrés en comptabilité** : aucune opération ne déclenche de virement bancaire.
- **Documents et règles à fiabiliser** : les modèles annuels et AG ainsi que certains cas particuliers nécessitent encore une validation métier. Aucune certification juridique ou comptable n’est annoncée.
- **Analyses locales** : les alertes sont calculées depuis les données saisies, sans moteur IA externe.
- **Exports et sauvegardes distincts** : une archive JSON ne contient pas les fichiers des pièces justificatives.

Les priorités suivantes sont la sauvegarde et la restauration vérifiée de la base
avec les pièces, la double authentification et l’accès de secours, puis la
fiabilisation des modèles réglementaires. Les chantiers suivants portent notamment
sur les cas comptables complémentaires, le calendrier de gestion, les travaux et
sinistres, les imports de données et l’extranet. Les réunions et délégations
collectives du conseil restent également à compléter.

Le [plan des prochains chantiers](docs/guides/PROCHAINS-CHANTIERS.md) détaille leur
priorité et le livrable attendu. Les fonctions de cabinet professionnel et le mode
association ne font pas partie du développement actuel.

## Structure et développement

```text
backend/
  core/         Personnes, lots, sessions et contrôles d’accès
  finance/      Comptabilité, banques, fonds et clôture
  governance/   Assemblées générales et calculs de vote
  council/      Mandats, permissions, avis et contrôle indépendant
  documents/    Bibliothèque et versions des pièces
  operations/   Fournisseurs, contrats, dossiers et alertes
frontend/       Interface React / TypeScript et Nginx
compose.yaml    Services web, Django et PostgreSQL
docs/           Présentation autonome, guides et cahier
```

### Vérifications avec Docker

```sh
docker compose exec backend python manage.py test --noinput
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose build frontend
```

Les tests utilisent une base séparée et des fichiers temporaires. Le rôle PostgreSQL
de développement doit pouvoir créer cette base. Le build frontend vérifie TypeScript
puis compile Vite.

### Développement sans Docker

Python 3.12 avec `backend/requirements.txt`, migrations et serveur Django ;
Node.js 22 avec `npm ci` puis `npm run dev` dans `frontend/`. Vite transmet `/api/`
à `127.0.0.1:8000`. Sans `POSTGRES_HOST`, Django utilise SQLite pour le développement.
La variable `DJANGO_SECRET_KEY` doit être définie dans l’environnement du processus
Django ; le fichier `.env` est transmis automatiquement par Compose, pas par
`manage.py`. Voir l’[architecture](docs/guides/ARCHITECTURE.md).

## Contribuer

Pour signaler un problème, préciser la page, les étapes suivies, le comportement
attendu et celui observé, avec des données anonymisées. Pour proposer une évolution,
décrire le besoin d’un syndic bénévole ou coopératif et le parcours concerné.

Les contributions peuvent passer par une
[issue](https://github.com/abp-display/Copro/issues) ou une
[pull request](https://github.com/abp-display/Copro/pulls). Pour une modification du
code, effectuer les vérifications adaptées ci-dessus, mettre à jour les guides
concernés et conserver les notices de licence. Ne pas publier de mots de passe,
de base réelle ni de pièces privées.

## Licence

GPL-3.0 : [LICENSE](LICENSE). Les notices et provenances des éléments redistribués
sont conservées dans [NOTICE.md](NOTICE.md) et avec les fichiers concernés.
