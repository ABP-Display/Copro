# Documents annuels, fonds travaux et avances

Parcours livré le 15 octobre 2026, pour un syndic bénévole ou coopératif en France.

## Préparer les comptes à présenter en AG

1. Dans **Gestion comptable**, vérifier les factures, les répartitions et les budgets.
2. Dans **Charges & finances → Fonds & travaux votés**, renseigner la date du vote
   de chaque opération. Les anciennes opérations ne reçoivent aucune date inventée.
3. Dans **Rapports comptables → Dossier comptable annuel**, sélectionner l’exercice.
   Le nouveau dossier présente cinq annexes, les décomptes individuels, les
   comparatifs disponibles et les points à corriger.
4. Résoudre les erreurs. Une case vide signifie « non renseigné », jamais zéro.
   Créer les exercices suivants et saisir leurs budgets pour compléter N+1/N+2.
5. Imprimer le dossier en PDF, vérifier la pagination et les montants, puis le
   déposer dans **Documents**. Conserver aussi l’archive JSON pour les données sources.
6. Dans la préparation de l’AG, choisir l’exercice présenté et relire son dossier.
   Le modèle **Approbation des comptes** demande les cinq annexes, le projet d’état
   individuel de répartition et les modalités de consultation des justificatifs.
   Un PDF complet peut servir à plusieurs rubriques si son contenu les couvre réellement.
7. Confirmer la relecture, enregistrer puis figer la convocation. Une modification
   des données annuelles après relecture oblige à recharger et vérifier le dossier.
   Son empreinte et sa version sont conservées dans le dossier convoqué.

### Ce que les contrôles vérifient

- L’équilibre de l’état financier après répartition proposée ou comptabilisée.
- Les soldes débiteurs et créditeurs par **identifiant** de tiers : deux personnes
  portant le même nom ne sont pas compensées entre elles.
- Les concordances entre les opérations courantes des annexes 2 et 3, les travaux
  terminés des annexes 2 et 4, le grand livre et les soldes en attente des annexes 1 et 5.
- Les provisions avant régularisation, pour que leur montant ne soit pas remplacé
  dans les comparatifs par le montant des charges approuvées.
- Les dates des décisions et les écritures sources des travaux, avec leurs montants.

L’application conserve dans ses écritures les financements 102 et les coûts en
attente 120. La présentation annuelle les regroupe dans un solde 12 des opérations
non terminées, avec les charges de l’exercice. Cette présentation est expliquée
dans le dossier et ne réécrit aucun journal. Les anciens dossiers clôturés restent
dans leur format et leur instantané d’origine.

## Configurer le fonds travaux et les avances

Dans **Charges & finances → Fonds & avances**, choisir l’exercice, puis renseigner :

- La destination de l’immeuble et sa date de réception.
- Le budget prévisionnel voté et la référence de son approbation.
- L’existence d’un PPT adopté et le **coût total de ses travaux**.
- La cotisation annuelle votée, sa référence et une version de sa pièce justificative.
- Pour les avances, le fondement dans le règlement ou la décision d’AG et l’échéancier.

Un paramétrage incomplet peut être enregistré pour préparation. Ses erreurs sont
affichées et bloquent la publication des appels concernés. Les anciens appels
d’un exercice non configuré restent utilisables, avec un avertissement explicite :
ils ne sont pas déclarés rétroactivement conformes. Enregistrer le paramétrage
avant tout nouvel appel de fonds ou d’avances pour activer ces contrôles.

### Fonds travaux : compte 105

Pour l’habitation totale ou partielle, le régime actuel est contrôlé à partir du
dixième anniversaire de la réception. Le minimum annuel calculé est de 5 % du
budget ; avec un PPT adopté, il est le plus élevé de 5 % du budget et de 2,5 % du
montant total des travaux du plan. Le calcul est arrondi au centime supérieur.

La suspension suppose une décision justifiée : fonds constitué supérieur au
budget **et**, lorsqu’un PPT est adopté, également supérieur à 50 % du coût de ses
travaux. Un seul seuil ne suffit pas. Aucune dispense automatique liée à une
petite copropriété ou à un ancien DTG n’est déduite du régime actuel. L’arrivée
des dix ans pendant l’exercice et les exercices antérieurs à 2025 demandent une
vérification de calendrier, sans prorata inventé.

Le montant cumulé des appels publiés ne peut dépasser la cotisation votée dans
le paramétrage. Le fonds versé reste attaché au lot lors d’une vente ; le syndicat
ne le rembourse pas au vendeur. Une éventuelle compensation privée entre vendeur
et acquéreur ne constitue pas une restitution du compte 105.

### Avances : comptes 1031, 1032 et 1033

Dans **Appels de fonds**, choisir **Avance remboursable**, puis sa catégorie :

| Compte | Usage | Contrôle spécifique |
| --- | --- | --- |
| 1031 | Réserve de trésorerie | Réserve prévue au règlement ; plafond global d’un sixième du budget, soldes antérieurs compris. Les appels antidatés ne peuvent dépasser un pic ultérieur connu de l’exercice. |
| 1032 | Avance du PPT | Plan adopté, décision et échéancier justifiés. Distincte de la cotisation 105. |
| 1033 | Besoin temporaire de trésorerie | Décision d’AG, justification et conditions de restitution. |

Les modèles d’AG proposent des résolutions distinctes pour ces avances,
l’affectation du fonds et la suspension de ses cotisations. La majorité proposée
doit être vérifiée selon l’objet précis et le règlement ; le logiciel ne déduit
pas la qualification juridique d’un texte libre.

## Restituer une avance

1. Enregistrer le versement réellement reçu, puis le **lettrer** avec l’appel.
2. Dans **Fonds & avances**, retrouver le lot, le titulaire et le compte 103.
3. Cliquer **Restituer** : le disponible est limité aux sommes effectivement
   versées et encore constituées, déduction faite des restitutions précédentes.
4. Choisir un crédit du compte copropriétaire 450 ou enregistrer un règlement
   bancaire déjà effectué. Joindre une pièce et une référence, puis confirmer.
   Aucun virement n’est envoyé par Copro. Le compte dédié au fonds travaux est exclu.
5. Pour une avance PPT 1032, choisir aussi l’affectation à une opération votée encore
   ouverte. Le titulaire doit toujours posséder le lot à cette date et le lot doit
   participer à la clé des travaux. L’affectation débite 1032 et crédite le financement
   102 de l’opération ; le résultat final tient compte de ce financement sans le
   demander une seconde fois. Une avance du vendeur ne finance pas automatiquement
   les travaux de l’acquéreur.
6. Pour corriger une erreur, utiliser **Corriger** dans l’historique. Retirer d’abord
   les rapprochements/lettrages éventuels. L’écriture inverse conserve l’opération originale.

Une vente conserve l’avance versée au nom de son titulaire historique. Seule la
part non versée d’un appel réattribuable est transférée à l’acquéreur. Le titulaire
historique peut donc être remboursé sans attribuer sa restitution au propriétaire
actuel. La correction d’un paiement source est bloquée tant que sa restitution
reste active. Une reprise initiale d’avance doit identifier son lot et son titulaire
et porter uniquement sur les sommes effectivement versées.

## Documents AG : compléments

La feuille de présence imprimée indique la réception des formulaires de
correspondance. Le formulaire précise la qualité du signataire, les pièces lues,
les votes, le nombre de pages à compléter, les paraphes et la signature ; il
comporte une aide rappelant les dispositions applicables. Vérifier sa concordance
avec le modèle officiel et joindre ses rappels réglementaires lors de la notification.
Le PV distingue les assimilés défaillants en cas de vote favorable par correspondance
sur une résolution amendée. Le rappel de l’article 42, alinéa 2, accompagne le PV.
Les signatures et notifications effectives restent réalisées hors application.

## Limites à conserver

Ces contrôles ne certifient ni les imputations, ni les décisions, ni la conformité
graphique exhaustive des formulaires officiels. Une validation métier reste requise
avant leur usage réel. Les subventions, prêts collectifs et indemnités de travaux
sont signalés comme nécessitant des états complémentaires : leur cycle complet
et leurs engagements à recevoir ne sont pas automatisés ici. L’affectation d’une avance PPT à des travaux votés est disponible avec décision,
pièce, contrôle du titulaire et du lot. Après le solde des travaux, une correction
nécessite de traiter aussi leur résultat ; l’application bloque une simple annulation
isolée de l’affectation. Le mode de comptabilité simplifiée reste un chantier distinct. Les exports JSON annuels ne contiennent pas les fichiers ; la
sauvegarde chiffrée complète rassemble la base et toutes les pièces.

Références consultées le 15 octobre 2026 :

- [Décret n° 2005-240, comptes et annexes](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000258200/).
- [Article 14-2-1, fonds travaux](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000043967792).
- [Article 35, provisions et avances](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000053191341/2026-02-09).
- [Article 45-1, avances remboursables](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042078810).
- [Service Public, budget et avances](https://www.service-public.gouv.fr/particuliers/vosdroits/F896).
- [Modèle de correspondance, arrêté du 2 juillet 2020](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000042075372/2026-05-21).
