# Sauvegarde, restauration et double authentification

Ce guide couvre l’instance Docker/PostgreSQL de Copro. Les commandes se lancent
depuis la racine du dépôt, sur le serveur où Docker fonctionne. Une sauvegarde
regroupe **la base et tous les fichiers du volume documentaire**, y compris les
anciennes versions et les pièces privées.

## 1. Préparer la sauvegarde

Prérequis : Python 3.12 ou supérieur, Docker Compose v2 et l’image de l’application
à jour. L’outil utilise les programmes PostgreSQL du conteneur de base et les
outils de maintenance du backend ; aucun client PostgreSQL n’est requis sur le PC.

```sh
python -m pip install -r scripts/requirements.txt
```

Choisissez une phrase secrète longue et distincte des mots de passe de connexion.
L’outil la demande sans l’afficher. Elle protège l’archive avec AES-256-GCM et une
clé dérivée par scrypt ; une phrase incorrecte ou une altération bloque l’ouverture.
Il n’existe pas de récupération de cette phrase depuis Copro.

Conservez dans des emplacements séparés et protégés :

- Les archives `.coprobackup`, dont une copie hors du serveur.
- Leur phrase secrète, par exemple dans votre gestionnaire de mots de passe.
- Le fichier `.env` original et la version du code ou des images utilisée.

`DJANGO_SECRET_KEY` protège aussi les secrets des applications d’authentification.
**Conservez cette valeur pour restaurer les accès existants.** La vérification
compare son empreinte sans exporter le secret. L’archive ne contient ni `.env`,
ni identifiants de l’hébergeur, DNS ou certificats du reverse proxy.

Le répertoire temporaire du système contient des données déchiffrées pendant
l’opération, puis est supprimé. Utilisez un compte serveur dédié et un disque
protégé/chiffré ; prévoyez l’espace de l’archive, de sa décompression et d’une copie
restaurée. La limite du format actuel est de 100 Gio déchiffrés.

## 2. Créer et vérifier une sauvegarde

```sh
python scripts/backup.py create --verify --keep 7
```

Cette commande :

1. Verrouille la maintenance pour éviter deux opérations concurrentes sur ce dépôt.
2. Arrête le backend pour suspendre les écritures ; PostgreSQL reste démarré.
3. Contrôle chaque version documentaire, capture la base et toutes les pièces,
   puis compare un inventaire avant/après pour détecter une modification concurrente.
4. Chiffre l’ensemble et relit l’archive pour en vérifier l’authenticité.
5. Redémarre le backend s’il fonctionnait avant la capture.
6. Crée un projet Docker temporaire sans port publié, restaure PostgreSQL et les
   documents, puis compare les empreintes et nombres de lignes de chaque modèle,
   les tables de liaison, les migrations et tous les fichiers.
7. Supprime les conteneurs et volumes de contrôle et enregistre le succès.
8. Conserve les sept dernières archives vérifiées de ce dossier.

La capture occasionne une courte indisponibilité. La restauration de contrôle
peut ensuite continuer pendant que les utilisateurs travaillent. Ces garanties
supposent que tous les écrivains passent par le backend de cette instance :
arrêtez également vos scripts d’import et éventuels services annexes.

`--keep` nécessite `--verify`. La rétention supprime uniquement les archives
`copro-*.coprobackup` accompagnées d’un reçu de vérification correspondant à leur
empreinte. Les archives non vérifiées et celles créées avant une restauration
restent conservées. La rétention ne constitue pas une copie hors site.

Pour choisir un autre dossier ou vérifier plus tard :

```sh
python scripts/backup.py create --output-dir backups
python scripts/backup.py inspect backups/NOM.coprobackup
python scripts/backup.py verify backups/NOM.coprobackup
```

`inspect` vérifie le chiffrement et les empreintes et affiche les métadonnées.
Seul `verify` réalise une restauration de contrôle. Une vérification réussie porte
sur cette archive précise ; elle ne prouve pas que les opérations suivantes ont
été sauvegardées.

Dans **Administration → Sauvegardes & reprise**, l’administrateur principal retrouve
les créations, vérifications et restaurations enregistrées, ainsi que les commandes.
Les archives, phrases secrètes et secrets TOTP ne sont jamais servis par une API web.

## 3. Programmer les sauvegardes

Le programme retourne `0` en cas de succès et un code non nul en cas d’échec.
Le planificateur du serveur doit conserver les journaux et signaler les échecs.
La programmation reste un choix de l’exploitant ; l’application n’active pas de
tâche système ni de copie distante à votre insu.

### Windows

Créez le fichier de secret avec le **compte Windows qui exécutera la tâche**, sans
inscrire la phrase dans une commande ou dans l’historique PowerShell :

```powershell
Read-Host 'Phrase secrète des sauvegardes' -AsSecureString |
  Export-Clixml -LiteralPath 'C:\Sauvegardes-Copro\secret.xml'
```

Le dossier doit exister et être privé. Le secret est protégé par Windows pour ce
compte et cette machine. Gardez également la phrase dans un gestionnaire de mots
de passe : ce fichier seul ne suffit pas après la perte du serveur.

Testez le lanceur :

```powershell
powershell.exe -NoProfile -File .\scripts\backup-scheduled.ps1 `
  -SecretFile 'C:\Sauvegardes-Copro\secret.xml' `
  -OutputDirectory 'C:\Sauvegardes-Copro\archives' -Keep 7
```

Dans le Planificateur de tâches, créez une tâche quotidienne avec cette commande,
des chemins absolus, le compte qui a créé le secret et un environnement où Docker
Desktop est disponible. `-PythonExecutable` permet de désigner un Python précis.
Vérifiez le résultat de la première exécution programmée. La tâche est configurée
par l’exploitant ; le dépôt fournit le lanceur.

### Linux

Utilisez cron ou un timer systemd. Fournissez `COPRO_BACKUP_PASSPHRASE` depuis un
gestionnaire de secrets ou un fichier de service accessible uniquement au compte
de maintenance, puis exécutez `python scripts/backup.py create --verify --keep 7`
dans le dépôt. N’inscrivez pas la phrase en clair dans la ligne cron ou les arguments.
Le compte doit pouvoir joindre Docker. Contrôlez les journaux et les copies hors site.

## 4. Restaurer après une perte ou une erreur

La restauration **remplace les données actuelles**. Prévenez les utilisateurs et
choisissez l’archive correspondant au point de reprise voulu. Les opérations
postérieures à cette archive ne seront pas conservées dans l’état restauré.

Sur le serveur de reprise, récupérez le code/image correspondant aux migrations
de l’archive et votre `.env`, construisez l’application et démarrez une instance
initialisée. Le format actuel utilise PostgreSQL 16. Une archive issue d’un schéma
différent doit être restaurée avec sa version de l’application ; mettez à jour
l’application et ses migrations après la reprise.

```sh
python scripts/backup.py restore backups/NOM.coprobackup --confirm copro
```

`copro` est le nom du projet défini dans `compose.yaml`. Pour une installation
utilisant un autre projet ou une surcharge :

```sh
python scripts/backup.py --project MON_PROJET --file compose.yaml --file surcharge.yaml restore backups/NOM.coprobackup --confirm MON_PROJET
```

Avant de toucher à la cible, l’outil restaure et vérifie le candidat dans une
instance isolée. Il arrête ensuite le backend et sauvegarde automatiquement l’état
précédent dans `backups/avant-restauration-….coprobackup`, avec la même phrase.
PostgreSQL est restauré dans une transaction, puis les documents sont remplacés.
Le contrôle complet est répété avant réouverture de l’application.

Si des pièces étaient déjà perdues ou altérées dans l’état courant, l’archive de
secours conserve la base et tous les fichiers encore disponibles, avec l’anomalie
signalée. Elle sert à récupérer cet état endommagé ; elle ne peut pas être validée
pour une remise en service tant que les pièces ne sont pas réparées. Cela ne bloque
pas la restauration d’un candidat complet et vérifié.

Toutes les sessions sont révoquées après reprise. Les configurations TOTP et codes
de secours reviennent à **leur état au moment de l’archive**. Reconnectez-vous et
renouvelez vos codes après un retour à une archive ancienne : un code consommé
depuis peut redevenir disponible. Une sauvegarde restaure aussi les comptes et
droits présents à cette date ; contrôlez les suspensions et mandats après reprise.

### Si une restauration est interrompue

Le backend reste arrêté dès qu’une modification a commencé. Le journal
`.local-data/restore-pending.json` indique la cible et la sauvegarde de retour.
Ne relancez pas simplement l’application : la base et les fichiers pourraient
représenter des états différents.

Vérifiez qu’aucun processus de maintenance ne tourne encore. Si une interruption
brutale a laissé `.backup-lock`, retirez seulement ce fichier après cette vérification.
Relancez avec le candidat initial, ou avec l’archive de retour indiquée dans le
journal :

```sh
python scripts/backup.py restore backups/avant-restauration-ID.coprobackup --confirm copro --resume-interrupted
```

Ce mode exige le journal et une sauvegarde de retour lisible ; il les conserve
pendant la nouvelle tentative. Après succès, le journal est supprimé et le backend
retrouve son état de fonctionnement précédent. Gardez l’archive de retour jusqu’à
la validation de la reprise.

## 5. Activer la double authentification

Elle est proposée à tous les comptes, gestionnaires, conseil et copropriétaires.

1. Ouvrir **Mon compte**, puis renseigner le mot de passe actuel.
2. Cliquer sur **Configurer mon application**.
3. Scanner le QR code dans une application compatible TOTP, ou recopier la clé
   manuelle. Le QR code est généré sur votre serveur, sans service externe.
4. Recopier le code à six chiffres pour confirmer l’activation.
5. Télécharger ou conserver les dix codes de secours, à part du téléphone.

À la connexion suivante, le mot de passe ouvre une étape de vérification, sans
donner encore accès aux données. Cette étape expire après cinq minutes. Saisir un
code de l’application ou un code de secours. Un code déjà consommé est refusé ;
attendez le suivant si vous venez d’utiliser celui du téléphone.

Les tentatives sont limitées côté serveur, y compris entre plusieurs sessions et
processus. Les secrets sont chiffrés en base et les codes de secours ne sont
conservés que sous forme d’empreintes. Utilisez HTTPS pour l’accès partagé et
gardez l’heure du téléphone et du serveur synchronisée.

**Mon compte** permet de renouveler les codes de secours ou de désactiver le second
facteur avec le mot de passe et un code valide. Ces changements révoquent les autres
sessions. La désactivation est refusée si la règle de gestion l’impose.

## 6. Exiger cette protection pour les gestionnaires

L’administrateur principal active d’abord son propre second facteur, puis ouvre
**Administration → Sauvegardes & reprise** et coche la règle obligatoire. Sa
modification exige le mot de passe et le second facteur de l’administrateur.

Un gestionnaire sans second facteur doit alors terminer son inscription avant
d’accéder aux données de gestion, y compris par l’API. La règle suit aussi les
droits de gestion accordés par mandat. Les comptes en lecture peuvent activer
leur propre protection sans que cette règle leur soit imposée.

## 7. Téléphone perdu et récupération serveur

Avec un code de secours, connectez-vous puis renouvelez les codes ou reconfigurez
le second facteur. Si aucun code n’est disponible, l’administrateur du serveur
peut effectuer une récupération après vérification du titulaire :

```sh
docker compose exec backend python manage.py recover_access --username admin --confirm admin --reason "Téléphone perdu et identité du titulaire vérifiée"
```

La commande vise l’identifiant interne exact, affiche un nouveau mot de passe
temporaire une seule fois, révoque l’ancien mot de passe, les sessions et le second
facteur, puis exige un changement de mot de passe. Elle trace le motif et ne
réactive pas un compte suspendu. Si la protection des gestionnaires est obligatoire,
le compte doit ensuite configurer un nouveau facteur avant d’accéder à la gestion.

Cette procédure est réservée à l’accès au serveur. Le mot de passe défini dans
`.env` n’écrase jamais celui d’un compte existant au redémarrage.

## Références techniques

- [PyOTP : recommandations sur les codes, leur réutilisation et les tentatives](https://pyauth.github.io/pyotp/).
- [Django : authentification et invalidation des sessions](https://docs.djangoproject.com/en/5.2/topics/auth/default/).
- [PostgreSQL 16 : restauration transactionnelle avec pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html).
- [Cryptography : chiffrement authentifié](https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/).
