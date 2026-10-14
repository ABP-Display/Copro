# Diacamma Syndic : structure et lancement web

## Ce que contient ce dépôt

Le dépôt est une application métier installable en Python, et non un projet
Django autonome. `setup.py` déclare les dépendances Lucterios et Diacamma Financial.
Il n'y avait pas de `manage.py`, de configuration de base de données ni de Dockerfile.

```text
syndic/
├── diacamma/
│   ├── syndic/                 Assemblage de l'application Diacamma Syndic
│   │   ├── __init__.py         Version et liste des modules (link)
│   │   ├── appli_settings.py  Identité, logo et style de l'application
│   │   ├── views.py           Initialisation du plan comptable
│   │   ├── init_*.csv         Paramétrages comptables par pays
│   │   ├── migrations/        Initialisation propre au syndic
│   │   ├── docs/ et pdf/      Documentation Sphinx
│   │   └── tests.py           Tests d'intégration de l'application
│   └── condominium/           Fonctionnalités métier de copropriété
│       ├── models.py         Lots, copropriétaires, charges, appels, dépenses
│       ├── editors.py        Édition et validation des objets
│       ├── views*.py          Écrans/actions Lucterios, regroupés par fonction
│       ├── system/            Règles France, Belgique et Maroc
│       ├── printmodel/        Modèles d'impression
│       ├── migrations/        Évolution du schéma de données
│       └── tests*.py          Tests métier existants
├── deployment/               Configuration web ajoutée
│   ├── settings.py           Modules, PostgreSQL/SQLite, stockage et paramètres
│   ├── bootstrap.py          Migrations et sécurisation du premier compte admin
│   ├── manage.py             Commandes Django
│   └── wsgi.py               Point d'entrée du serveur web
├── Dockerfile
├── compose.yaml              Services web et db
├── requirements-web.txt
├── setup.py / MANIFEST.in    Installation et ressources du paquet Python
└── build.xml / .gitlab-ci.yml Construction et intégration continue historiques
```

Le cœur technique et l'interface générique viennent de `lucterios`. Les contacts
et courriels viennent de `lucterios-contacts`, les documents de
`lucterios-documents`, et la comptabilité/règlements de `diacamma-financial`.
Les paquets `diacamma` sont partagés entre plusieurs distributions Python.

Les vues métier construisent des composants `Xfer*` et des actions. Lucterios
génère les routes et les réponses utilisées par son client web. Ce n'est donc
pas une collection de templates Django classiques. La version Lucterios
2.7.9 téléchargée pour cette intégration contient un client Vue compilé,
servi sous `/web/`. Ses sources d'interface ne sont pas dans ce dépôt.
Pour une refonte générale, il faudra travailler sur le client Lucterios ou
créer une interface et des API complémentaires.

## Lancement avec Docker Desktop

Utiliser Docker Desktop avec les conteneurs Linux et Docker Compose v2.
Depuis PowerShell :

```powershell
cd D:\Conceptions\Code\Projects\Syndic\syndic
# Seulement si .env n'existe pas encore :
Copy-Item .env.example .env
```

Renseigner dans `.env` des valeurs différentes et aléatoires pour
`POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY` et `SYNDIC_ADMIN_PASSWORD` (12 caractères
minimum pour ce dernier). Lors de la mise en place locale, un `.env` avec des
valeurs aléatoires a déjà été créé : le conserver. Il est exclu de Git et de
l'image Docker.

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 web
```

Ouvrir <http://localhost:8080/web/index.html>. Identifiant : `admin`.
Le mot de passe initial est la valeur `SYNDIC_ADMIN_PASSWORD` de votre `.env`.
L'application lance automatiquement les migrations avant le serveur.
Le mot de passe admin n'est pas réinitialisé à chaque redémarrage. Après
changement dans l'application, c'est le nouveau mot de passe qui s'applique.

Le service `web` utilise Python 3.12, Django fourni par Lucterios, Gunicorn et
WhiteNoise pour les fichiers statiques Django. Le client `/web/` est servi par
les routes Lucterios. Un seul processus Gunicorn est utilisé pour éviter de
dupliquer le planificateur de tâches intégré au framework.

Le service `db` utilise PostgreSQL 16 et n'expose pas de port sur l'hôte.
Les volumes `postgres_data` (base) et `syndic_data` (documents, cache, statiques)
conservent les données entre les redémarrages.

```powershell
# Arrêter sans supprimer les données
docker compose down
# Redémarrer
docker compose up -d
# Après modification du code : reconstruire l'image
docker compose up -d --build
# Vérifier Django
docker compose exec web python -m deployment.manage check
# Changer le mot de passe admin si nécessaire
docker compose exec web python -m deployment.manage changepassword admin
```

Ne pas utiliser `docker compose down -v` pour un simple arrêt : cela supprime
les volumes et les données. Sauvegarder la base ET les documents avant une
mise à jour. Une sauvegarde de base seule ne contient pas les fichiers déposés.

Cette configuration écoute sur `127.0.0.1` pour un usage local. Une ouverture
Internet nécessite un domaine, HTTPS, un proxy adapté, une revue de sécurité
du framework et une stratégie de sauvegarde. Le `.env` ne doit pas être publié.

## Lancement sans Docker pour le développement

Python 3.12 et un environnement virtuel sont recommandés. Sous Windows,
installer Python si la commande `py` n'est pas disponible.

```powershell
cd D:\Conceptions\Code\Projects\Syndic\syndic
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
$env:DJANGO_SECRET_KEY = 'remplacer-par-une-cle-aleatoire-longue'
$env:SYNDIC_ADMIN_PASSWORD = 'remplacer-par-un-mot-de-passe-fort'
.\.venv\Scripts\python.exe -m deployment.bootstrap
.\.venv\Scripts\python.exe -m deployment.manage runserver 127.0.0.1:8000 --noreload
```

Sans `POSTGRES_HOST`, cette configuration utilise SQLite dans `.local-data/`.
Ouvrir <http://localhost:8000/web/index.html>. Le fichier `.env` de Compose
n'est pas chargé automatiquement par ce lancement Python. Gunicorn est utilisé
uniquement dans le conteneur Linux ; le développement Windows utilise runserver.
Le lancement natif Windows est documenté mais doit être vérifié séparément.

## Initialisation fonctionnelle

Une instance vide est créée, sans données réelles de copropriété. Dans Diacamma,
renseigner les coordonnées, le pays et les paramètres comptables, puis créer
l'exercice, les copropriétaires, les lots et les clés de répartition. Reprendre
les soldes et les écritures transmis par le syndic sortant avant usage réel.
Voir aussi `diacamma/syndic/docs/fr/first_step.rst`.

## Vérifications réalisées le 12 octobre 2026

- Construction de l'image et démarrage des deux services : réussis.
- Migrations sur PostgreSQL 16 : appliquées ; compteurs d'identifiants
  synchronisés après les insertions explicites des migrations historiques.
- Services `web` et `db` : état `healthy`.
- `python -m deployment.manage check` : aucune anomalie.
- `pip check` : aucune dépendance cassée.
- HTML, ressources JavaScript/CSS et connexion HTTP administrateur : vérifiés.
- Mot de passe d'origine `admin` : refusé.
- Insertion avec identifiant automatique dans PostgreSQL : vérifiée puis
  annulée dans une transaction de contrôle.
- Conservation de l'instance et de l'accès administrateur après reconstruction
  et recréation du conteneur : vérifiée.
- Les quatre tests existants `diacamma.syndic.tests` passent dans un conteneur
  isolé utilisant SQLite. Commande de reproduction :

```powershell
docker run --rm --entrypoint python -w /tmp -e PYTHONPATH=/app -e DJANGO_SECRET_KEY=integration-test-only -e SYNDIC_DATA_DIR=/tmp/test-state diacamma-syndic-web -m deployment.manage test diacamma.syndic.tests --testrunner django.test.runner.DiscoverRunner --noinput
```

Le lancement direct de ces tests historiques sur PostgreSQL échoue dans la
préparation des données : les fixtures supposent des identifiants fixes et les
séquences PostgreSQL ne sont pas annulées entre les cas comme les données.
Ce point reste à adapter pour une suite métier complète sur PostgreSQL.
Les contrôles fonctionnels PostgreSQL ci-dessus sont distincts de ces tests.
L'ensemble de la comptabilité, les envois de courriel et tous les exports PDF
n'ont pas été validés par cette mise en place.
