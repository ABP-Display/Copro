# Publication GitHub Pages

La vitrine autonome est `docs/index.html`, avec ses ressources dans `docs/assets/`.
Elle s’ouvre directement dans un navigateur, sans serveur ni compilation.
Les guides sont dans `docs/guides/`, l’inventaire dans `docs/reference/` et les
anciens aperçus dans `docs/apercus/`. Ces dossiers sont exclus de la publication.
Ne pas ajouter `.nojekyll` à la racine de `docs/` : les exclusions de `_config.yml`
doivent rester appliquées lors d’une publication depuis une branche.

## Depuis une branche

Envoyer les changements dans le dépôt utilisé par GitHub Pages, puis sélectionner
Settings → Pages → Deploy from a branch → master → /docs → Save.
Le déploiement GitHub natif applique `docs/_config.yml` et publie la vitrine.

## Avec le workflow manuel

Choisir GitHub Actions comme Source et lancer « Publier la présentation sur
GitHub Pages ». Le workflow copie uniquement `docs/index.html` et `docs/assets/`
dans l’artefact. Il ne publie ni guides, ni inventaire, ni aperçus. Aucun npm
ou build React n’est nécessaire.

Le dépôt courant est [abp-display/Copro](https://github.com/abp-display/Copro).
Le remote `origin` vise ce dépôt. Envoyer les fichiers dans sa branche `master`, puis
configurer sa source Pages. L’application Django/PostgreSQL reste sur `copro.ydoxide.fr`.
