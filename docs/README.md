# Organisation de docs

```text
docs/
  index.html       Vitrine publique, ouvrable sans serveur
  assets/          Styles et logo de la vitrine
  guides/          Architecture, fonctionnalités et guides techniques
  reference/       Cahiers et instantanés d’audit
  apercus/         Anciens aperçus visuels du développement
  _config.yml      Exclusions pour GitHub Pages
```

Modifier `index.html` et les fichiers d’`assets/` pour actualiser le site public.
Le dossier source reste `/docs` dans GitHub Pages. Les autres sous-dossiers sont
exclus de la publication depuis une branche. Le workflow manuel ne copie que
la vitrine et ses ressources.

- [Publication GitHub Pages](guides/GITHUB-PAGES.md)
- [Architecture](guides/ARCHITECTURE.md)
- [État du cahier bénévoles et coopératifs](guides/AUDIT-FONCTIONNALITES.md)
- [Fournisseurs, contrats, attestations et annonces](guides/FOURNISSEURS-CONTRATS-ANNONCES.md)
- [Banques, fournisseurs comptables et budgets](guides/BANQUES-FOURNISSEURS-BUDGETS.md)
- [Parcours comptables et clôture](guides/COMPTABILITE-CYCLE.md)
- [Annexes annuelles, pièces AG, fonds et avances](guides/DOCUMENTS-FONDS-AVANCES.md)
- [Suivi du développement](guides/SUIVI-DEVELOPPEMENT.md)
- [Assemblées générales et outils](guides/AG-OUTILS.md)
- [Première AG : guide pas à pas](guides/AG-PREMIERS-PAS.md)
- [Prochains chantiers selon le cahier](guides/PROCHAINS-CHANTIERS.md)
- [Conseil syndical, mandats et contrôle](guides/CONSEIL-SYNDICAL.md)
- [Sauvegarde, restauration et double authentification](guides/SAUVEGARDE-SECURITE.md)
- [Dossiers et analyses métriques](guides/SUIVI-METRIQUES.md)
- [Inventaire de référence](reference/diacamma-inventory.json)
- [État structuré des 156 exigences bénévoles/coopératives](reference/audit-fonctionnalites.json)
- [Cahier fourni pour l’audit](reference/cahier-fonctionnalites.md)

Les aperçus sont des fichiers de travail et ne font pas partie de la vitrine.

L’audit courant suit le nouveau cahier bénévole/coopératif. Le [premier audit général](reference/historique/2026-10-14-general/README.md) est conservé comme historique ; les fonctions de cabinet professionnel sont exclues du périmètre actuel.
