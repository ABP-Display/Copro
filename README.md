<<<<<<< HEAD
# Copro. — la copropriété, ensemble
=======
# Copro. — gestion de copropriété
>>>>>>> 3e028e5a5dd0ce389a24f3c2dd8cf7a94deaf6b2

Application libre pour les syndics bénévoles et coopératifs, avec React / TypeScript,
Django / Python et PostgreSQL.

Dépôt : [abp-display/Copro](https://github.com/abp-display/Copro).
La présentation autonome se trouve dans `docs/` : ouvrir `docs/index.html` directement
ou publier ce dossier avec GitHub Pages.

## Fonctionnalités disponibles

- Copropriétaires, lots, tantièmes et clés de répartition.
- Exercices, reprise des soldes, factures, appels de fonds, règlements et lettrage.
- Banques, import de relevés, rapprochement, fonds par lot, régularisation et clôture.
- Plan comptable, budgets, journaux, écritures équilibrées et rapports exportables.
- AG : préparation, convocations, présences, pouvoirs, correspondance, votes,
  procès-verbal, pièces signées, notifications, décisions et registre.
- Guide AG intégré en six étapes, FAQ, lexique, mémo et impression.
- Conseil syndical : mandats datés, responsabilités et accès ciblés, règles de contrôle
  des dépenses, avis motivés, préparation par un trésorier et contrôle indépendant.
- Fournisseurs, contrats, attestations, dossiers travaux et sinistres, relances préparées.
- Documents versionnés, partage explicite, annonces et espace copropriétaire.
- Alertes d’accueil calculées localement depuis les données saisies.

L’application gère actuellement **une seule copropriété**. Les signatures et notifications
sont réalisées à l’extérieur, puis leurs preuves sont conservées. Les écritures de
règlement enregistrent des opérations ; elles ne déclenchent pas de virement bancaire.
Les modèles réglementaires et les cas particuliers restent à fiabiliser. Aucune
certification juridique ou comptable ni moteur IA puissant n’est annoncé.

Consulter l’[audit du cahier](docs/guides/AUDIT-FONCTIONNALITES.md), la
[couverture fonctionnelle](docs/guides/COUVERTURE-FONCTIONNELLE.md) et les
[prochains chantiers](docs/guides/PROCHAINS-CHANTIERS.md).

## Installer avec Docker

Prérequis : Docker et Docker Compose, conteneurs Linux.

```sh
git clone https://github.com/abp-display/Copro.git
cd Copro
cp .env.example .env
# Renseigner les trois secrets avec des valeurs différentes et aléatoires.
docker compose up -d --build
docker compose ps
```

Sous PowerShell, utiliser `Copy-Item .env.example .env` à la place de `cp` si nécessaire.
Ouvrir [localhost:8081](http://localhost:8081). L’identifiant initial est `admin`
(ou `ADMIN_USERNAME`) ; son mot de passe est `ADMIN_PASSWORD`. Il doit comporter au moins
12 caractères. Le compte est créé une seule fois : modifier `.env` ne change pas un
mot de passe déjà enregistré. Le fichier `.env` reste privé et exclu de Git.

```sh
docker compose down                    # Arrêt conservant les données
docker compose logs --tail 100 backend # Journaux
docker compose up -d --build           # Mise à jour après modification
docker compose exec backend python manage.py changepassword admin
```

PostgreSQL et les pièces résident dans deux volumes distincts : sauvegarder les deux
ensemble. `docker compose down -v` supprime les volumes et leurs données.

## Accès et responsabilités

Créer les copropriétaires depuis l’annuaire. Avec un courriel, un compte et un mot de
passe temporaire sont générés. Le mot de passe est affiché une seule fois, puis doit
être remplacé à la première connexion. « Préparer le courriel » ouvre la messagerie ;
aucun courriel n’est envoyé automatiquement. Les comptes suspendus restent suspendus.

L’administrateur principal attribue les mandats dans **Conseil syndical → Composition
& mandats**. Les droits prennent effet aux dates prévues et cessent à l’échéance ou au
retrait. Le trésorier prépare, le conseil examine et donne son avis, le syndic
comptabilise et enregistre les règlements, le contrôleur rédige son rapport indépendant.
Les accès permanents de gestion restent gérés séparément dans Administration → Utilisateurs.
Voir le [guide du conseil](docs/guides/CONSEIL-SYNDICAL.md).

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

## Structure et vérifications

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

```sh
docker compose exec backend python manage.py test --noinput
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose build frontend
```

Les tests utilisent une base séparée et des fichiers temporaires. Le rôle PostgreSQL
de développement doit pouvoir créer cette base. Le build frontend vérifie TypeScript
puis compile Vite.

Sans Docker : Python 3.12 avec `backend/requirements.txt`, migrations et serveur Django ;
Node.js 22 avec `npm ci` puis `npm run dev` dans `frontend/`. Vite transmet `/api/`
à `127.0.0.1:8000`. Sans `POSTGRES_HOST`, Django utilise SQLite pour le développement.
Voir l’[architecture](docs/guides/ARCHITECTURE.md).

## Licence

GPL-3.0 : [LICENSE](LICENSE). Les notices et provenances des éléments redistribués
sont conservées dans [NOTICE.md](NOTICE.md) et avec les fichiers concernés.
