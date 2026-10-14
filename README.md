# Copro — gestion de copropriété

Nouvelle application indépendante : React / TypeScript, Django et PostgreSQL.
Le projet historique Diacamma est conservé dans `reference/diacamma/`, avec
son code source, sa licence et sa configuration Docker. Copro utilise le
port 8081 et une base distincte. Sur la machine de développement, l'instance
Diacamma déjà démarrée dans `../syndic/` reste accessible sur le port 8080.

Le dépôt est hébergé sur <https://github.com/Ydoxide/copro.>. L'historique
Diacamma est conservé ; la nouvelle application n'importe pas Lucterios.

## Première version

- Connexion des gestionnaires par session Django, avec protection CSRF.
- Tableau de bord calculé depuis les données enregistrées.
- Création, modification, recherche et suppression des copropriétaires.
- Création, modification, recherche et suppression des lots.
- Attribution d'un propriétaire à chaque lot, surface et tantièmes généraux.
- Validation des données et protection contre la suppression d'un propriétaire
  auquel des lots sont encore attribués.
- Interface responsive, utilisable depuis un téléphone.
- Connexion copropriétaire par courriel, mot de passe temporaire généré puis
  remplacé à la première connexion, et courriel d'accès préparé dans la messagerie.
- Espace membre en lecture seule : lots, charges, appels validés, trésorerie
  globale et synthèses publiées ; données privées masquées côté serveur.
- Catégories de charges, clés spécifiques et budget annuel indicatif.
- Exercices, appels de fonds avec répartition figée, factures, encaissements,
  règlements, écritures équilibrées, balance CSV et rapports de synthèse.
- Gestion comptable : plan français importable, journaux, centres analytiques,
  budgets par compte, modèles et contrepassation des écritures manuelles.
- Rapports filtrables : grand livre, balance, journal, résultat, bilan et suivi
  budgétaire, avec CSV et impression/PDF depuis le navigateur.
- Administration : coordonnées, paramètres comptables, rôles utilisateurs et
  historique des opérations comptables/configuration.
- Navigation déroulante et compacte, pages de présentation avec explications
  des sections, libellés au survol et volet mobile.
- Paiements fournisseurs partiels avec historique et reste à payer ;
  état privé des comptes copropriétaires avec solde de début de période.
- Documents PDF/PNG/JPEG (10 Mo), dossiers, versions, partage explicite,
  archivage réversible et téléchargements soumis aux droits d'accès.
- Fournisseurs, contrats avec préavis et coûts annuels déclarés, attestations
  et alertes d’accueil ; choix du fournisseur réel dans les devis.
- Annonces en brouillon puis publication explicite dans l’espace copropriétaire.
- Menu regroupé par thèmes : immeuble, finances, entretien/prestataires,
  vie collective, outils et paramètres.
- Factures avec fournisseur identifié et pièce de bibliothèque ; balance auxiliaire
  fournisseurs et banques distinctes pour les règlements/encaissements.
- Enregistrement de transferts effectués et budgets avec commentaires des écarts
  et comparaison à l’exercice précédent.

Cette version gère **une seule copropriété**, les gestionnaires (`is_staff`)
et les copropriétaires liés à un compte. **La reprise intégrale de Diacamma
n'est pas terminée.** Le détail des fonctions natives, de leurs limites et
du périmètre restant est dans [docs/guides/REPRISE-DIACAMMA.md](docs/guides/REPRISE-DIACAMMA.md).
La comparaison des menus consultés sur l'instance locale est dans
[docs/guides/COMPARAISON-DIACAMMA.md](docs/guides/COMPARAISON-DIACAMMA.md).
Les votes, les annexes et la clôture comptable complète restent
notamment à développer. Le mouvement bancaire net affiché n'est pas un solde
bancaire certifié sans reprise des soldes d'ouverture et rapprochement.

L’[audit du cahier de fonctionnalités](docs/guides/AUDIT-FONCTIONNALITES.md)
recense les 156 exigences des sections 4 à 7 du cahier bénévole/coopératif, leurs preuves, les écarts et
l’ordre de développement. Il décrit également 43 parcours utilisables dans leur
périmètre actuel. Les rôles et le mode simplifié sont suivis séparément.
Le cabinet professionnel est exclu ; le mode coopératif reste à développer.
Les fonctions partielles ne sont pas annoncées comme complètes.

## Accès copropriétaires

À la création d'un propriétaire ayant un courriel, le compte est généré
automatiquement. Le mot de passe temporaire est affiché une fois ; il n'est
jamais enregistré en clair. Le bouton « Préparer le courriel » ouvre votre
messagerie : **aucun courriel n'est envoyé automatiquement**. Remplacer le lien
localhost par une adresse réellement partagée avant de transmettre les accès.

Un copropriétaire sans courriel peut être enregistré sans compte. Pour un
propriétaire existant, « Créer accès » génère le compte. « Réinitialiser accès »
remplace le mot de passe et invalide les sessions existantes, après confirmation.
Un compte désactivé doit être réactivé par l’administrateur principal avant une
réinitialisation. Une modification de son courriel change son identifiant. La suppression du
propriétaire désactive son compte ; les références comptables bloquent les
suppressions qui feraient perdre l'historique.

## Démarrer

Docker Desktop doit être démarré en mode conteneurs Linux.

```powershell
cd D:\Conceptions\Code\Projects\Syndic\copro
docker compose up -d --build
docker compose ps
```

Ouvrir <http://localhost:8081>. Identifiant initial : `admin`.
Le mot de passe est la valeur `ADMIN_PASSWORD` du fichier `.env` local.
Ce fichier a été généré avec des secrets aléatoires pendant la mise en place.
Il est exclu de Git. Ne pas le publier.

Pour une nouvelle installation, copier `.env.example` vers `.env` et compléter
les trois secrets avec des valeurs aléatoires différentes (12 caractères
minimum pour le mot de passe administrateur). Le compte initial est créé une
seule fois ; changer `.env` ne modifie pas le mot de passe d'un compte existant.

```powershell
# Arrêt conservant les données
docker compose down
# Journaux
docker compose logs --tail 100 backend
# Reconstruire après modification
docker compose up -d --build
# Changer le mot de passe
docker compose exec backend python manage.py changepassword admin
# Créer un autre gestionnaire (compte superutilisateur)
docker compose exec backend python manage.py createsuperuser
```

La base est conservée dans le volume `copro_postgres_data`. `down -v` supprime
les volumes et doit être réservé à la suppression volontaire des données.
Les services Django et PostgreSQL n'exposent aucun port sur l'hôte. Nginx
sert React et transmet `/api/` à Django sur la même origine.
Les cookies `copro_sessionid` et `copro_csrftoken` sont propres à Copro :
ouvrir Diacamma sur un autre port localhost ne remplace pas sa session.

L'accès est limité à `127.0.0.1`. Avant une ouverture Internet, ajouter HTTPS,
des sauvegardes et une protection contre les tentatives de connexion répétées ;
activer les cookies sécurisés avec `HTTPS_ONLY=1` et configurer le proxy HTTPS.
Cette première version n'est pas une validation comptable ou réglementaire.

## Structure

```text
backend/
  config/                Paramètres Django, routes et serveur WSGI
  core/
    models.py            Owner et Lot, contraintes de base de données
    forms.py             Validation des champs
    views.py             API JSON, sessions et permissions
    migrations/          Schéma versionné
    tests.py             Tests métier et sécurité
  bootstrap.py           Migrations et création du compte initial
frontend/
  src/
    main.tsx             Point d'entrée React
    App.tsx              Navigation, tableau de bord et annuaires
    components/          Connexion, formulaires et composants visuels
    api.ts               Client API typé et gestion CSRF
    styles.css           Apparence et mise en page responsive
  nginx.conf             Serveur web et proxy de l'API
  package-lock.json      Dépendances JavaScript verrouillées
compose.yaml             Trois services isolés
docs/guides/ARCHITECTURE.md      Choix et étapes de reprise de Diacamma
```

## Vérifier

```powershell
docker compose exec backend python manage.py test core finance documents governance operations --noinput
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
```

Les tests créent et détruisent une **base de test séparée**. Ne pas lancer des
tests contre un serveur PostgreSQL de production. Le rôle PostgreSQL de cette
installation locale permet de créer cette base.

La compilation de l'image frontend exécute `tsc -b` puis `vite build`.
112 tests sont exécutés sur PostgreSQL. Les fichiers de test sont stockés dans
des répertoires temporaires séparés des documents réels.

Les documents réels résident dans le volume Docker `copro_document_data` et leurs
métadonnées dans PostgreSQL. Sauvegarder ces deux volumes ensemble. Les fichiers
ne sont pas servis publiquement : le téléchargement passe par Django.

## Développement sans Docker

Backend : Python 3.12, environnement virtuel, puis
`pip install -r requirements.txt`. Définir `DJANGO_SECRET_KEY` et
`ADMIN_PASSWORD`. Sans `POSTGRES_HOST`, Django utilise SQLite pour le
développement. Lancer `python manage.py migrate`, `python manage.py createsuperuser`,
puis `python manage.py runserver 127.0.0.1:8000` depuis `backend/`.

Frontend : Node.js 22, `npm ci`, puis `npm run dev` depuis `frontend/`.
Vite transmet `/api/` à `127.0.0.1:8000`. Ouvrir l'URL affichée par Vite.
Le lancement natif n'a pas été testé sous Windows ; le lancement Docker l'a été.

## Licence et référence

GPL-3.0, voir `LICENSE`. Cette première base est une implémentation indépendante,
sans import de Lucterios ni copie des calculs comptables Diacamma. Le fichier
du plan français vient de Diacamma ; sa provenance est conservée dans
`backend/finance/data/README.md`. Lors de la
reprise de code GPL, conserver les notices, les auteurs et la provenance des
fichiers concernés. Le dépôt de référence est <https://github.com/Diacamma2/syndic>.

## Assemblées générales et outils

Le menu « Assemblées générales » permet de préparer une réunion, rédiger son
ordre du jour et conserver une simulation par résolution. Le menu « Outils »
contient le calcul de majorité, une répartition au centime et un échéancier.
Il s’agit d’une première aide à la préparation, sans convocation ni PV signé.
Consulter [le périmètre AG et outils](docs/guides/AG-OUTILS.md) avant utilisation.

## Accès depuis un autre PC du réseau local

Dans `.env`, configurer `WEB_BIND_ADDRESS=0.0.0.0`, `WEB_PORT=8081` et
`DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,ADRESSE_IP_DU_SERVEUR` (remplacer
le dernier élément par l’IPv4 du PC hébergeant Docker, visible avec `ipconfig`).
Puis exécuter `docker compose up -d` depuis ce dossier.

Sur l’autre PC connecté au même réseau, ouvrir `http://ADRESSE_IP_DU_SERVEUR:8081`.
`0.0.0.0` est une adresse d’écoute, pas l’adresse à saisir dans le navigateur.
Si l’IPv4 du serveur change, mettre à jour `DJANGO_ALLOWED_HOSTS` et recréer
les conteneurs. Une réservation DHCP évite ces changements.

Seul le port web est publié. Le navigateur passe par Nginx pour toutes les
requêtes : Django et PostgreSQL restent dans le réseau Docker. Il n’est pas
nécessaire de publier les ports 8000 ou 5432 pour utiliser le site à distance.

Si Windows bloque encore l’accès, autoriser le port TCP 8081 pour le sous-réseau
local dans le pare-feu. Ne pas créer de redirection sur la box pour cet accès LAN.
Pour limiter ultérieurement le site au PC serveur, utiliser
`WEB_BIND_ADDRESS=127.0.0.1` puis relancer `docker compose up -d`.

Exemple pour le réseau actuel `192.168.1.0/24`, dans un PowerShell lancé
**en tant qu’administrateur** :

```powershell
New-NetFirewallRule -Name "Copro-Web-LAN-8081" -DisplayName "Copro Web LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8081 -RemoteAddress 192.168.1.0/24
```

Adapter le port et le sous-réseau à l’installation. Cette règle permet l’accès
depuis le réseau local même si Windows classe le Wi-Fi en profil Public.

## Domaine copro.ydoxide.fr

Le domaine est autorisé via `DJANGO_ALLOWED_HOSTS` et son origine HTTPS via
`DJANGO_CSRF_TRUSTED_ORIGINS`. Conserver l’en-tête Host d’origine dans le reverse
proxy. Dans Nginx Proxy Manager, utiliser le domaine `copro.ydoxide.fr`, le schéma
HTTP et la destination `host.docker.internal`, port `8081` si le proxy est dans
Docker Desktop. Pour un proxy natif sur ce PC, la destination est
`127.0.0.1:8081`. Le certificat HTTPS est géré sur le reverse proxy.

L’ajout du domaine dans Copro ne crée pas de configuration DNS, de certificat
ou d’hôte proxy. Aucun en-tête de proxy arbitraire n’est considéré fiable dans
Django ; l’origine HTTPS exacte est explicitement autorisée pour les formulaires.

## Présentation publique

`/presentation` présente le projet sans connexion ni requête aux données privées.
Les visiteurs non connectés sur `/` voient également cette présentation ;
`/connexion` ouvre le formulaire. Les utilisateurs connectés conservent leur
espace habituel. La vitrine décrit les fonctions disponibles, les modules
partiels et les évolutions à développer, sans annoncer de moteur IA intégré.

## GitHub Pages et nouveaux suivis

La vitrine autonome est dans `docs/` : ouvrir `docs/index.html` par double-clic.
Voir `docs/guides/GITHUB-PAGES.md` pour publier directement ce dossier HTML/CSS/SVG,
sans serveur ni compilation. Le workflow est manuel : aucun
déploiement n’est déclenché simplement par un push. L’application reste hébergée
sur `copro.ydoxide.fr`.

Le module `operations` apporte les dossiers travaux/sinistres, les devis, les
échéances, les brouillons de relance et les métriques de l’accueil. L’extranet
affiche le compte personnel du membre. Les indicateurs sont déterministes ;
aucun moteur IA ni envoi automatique n’est intégré. Voir `docs/guides/SUIVI-METRIQUES.md`.

Il contient aussi l’annuaire fournisseurs, les contrats/préavis, les attestations
et les annonces publiées. Voir le [guide dédié](docs/guides/FOURNISSEURS-CONTRATS-ANNONCES.md).

Pour une installation utilisée **uniquement en HTTPS**, définir `HTTPS_ONLY=1`
dans `.env` puis exécuter `docker compose up -d` pour que les cookies de session
et CSRF soient marqués Secure. Conserver `0` pendant le développement HTTP local.
Cette option ne crée pas le certificat ni le reverse proxy et ne remplace pas
la vérification du déploiement HTTPS.

Les banques, factures identifiées, comptes auxiliaires fournisseurs et écarts budgétaires sont décrits dans le [guide financier](docs/guides/BANQUES-FOURNISSEURS-BUDGETS.md).
