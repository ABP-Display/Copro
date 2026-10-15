# Parcours comptables

Livraison du 14 octobre 2026, pour la gestion d'un syndicat bénévole ou coopératif.

## Premier démarrage

Créer les exercices, identifier les copropriétaires et lots, vérifier les clés,
enregistrer les fournisseurs et les comptes bancaires. Dans **Gestion comptable →
Reprise des soldes**, saisir une balance équilibrée des classes 1 à 5, avec chaque
tiers et chaque lot du fonds travaux. La reprise est unique ; une correction
conserve la contrepassation avant une nouvelle reprise. Une clôture antérieure
utilise le report automatique, jamais une seconde reprise.

## Au fil de l'année

- Choisir le compte de charge et la clé de chaque facture, son fournisseur,
  sa pièce et son échéance. Les travaux exceptionnels sont rattachés à un projet.
- Préparer les appels courants, travaux, fonds ou avances. Un échéancier produit
  des brouillons distincts, conserve les centimes et demande une décision pour
  un calendrier différent des quatre trimestres.
- Enregistrer les règlements, y compris partiels, dans le bon exercice et sur
  la bonne banque. Ce sont des inscriptions comptables, sans ordre bancaire.
- Dans **Affecter les règlements**, lettrer les débits et crédits du même tiers.
  Le suivi des impayés conserve les avoirs et distingue les échéances futures.
- Importer le relevé au format CSV normalisé `date;libelle;montant;reference`.
  Un crédit bancaire est positif, un débit négatif. Confirmer les correspondances
  et expliquer les opérations en transit avant validation du relevé.

Les répartitions par lot sont figées avec l'opération. Une modification ultérieure
des tantièmes ne recalcule pas les anciennes charges. Les écritures historiques
sans répartition doivent être examinées dans **Répartitions à vérifier**.

## Fonds, travaux et changements de propriétaire

**Fonds & travaux votés** suit les appels, versements effectivement lettrés et
affectations du compte 105 par lot. Une affectation exige un projet, une décision,
des versements disponibles et une trésorerie suffisante sur une banque de travaux.
La fin d'une opération calcule son résultat ; les opérations non terminées sont
reportées séparément au compte 120.

**Changements de propriétaire** conserve la date et la référence de notification,
présente les corrections avant confirmation et réattribue les appels exigibles
après la cession. Le fonds déjà versé reste attaché au lot. Une mutation tardive
corrige un exercice ouvert sans réécrire une clôture. L'annulation est tracée.
L'ancien propriétaire sans lot conserve seulement son compte personnel.

La régularisation revient au propriétaire à la date d'approbation des comptes.
Les accords privés de prorata entre vendeur et acquéreur ne sont pas inventés.
Voir [Service Public](https://www.service-public.gouv.fr/particuliers/vosdroits/F32920)
et [article 6-2 du décret](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000053191265).

## Fin d'exercice

1. Vérifier factures, clés, appels, tiers, comptes d'attente et banques.
2. Dans **Exercice & clôture**, choisir la date d'approbation effective et examiner
   la régularisation par lot et clé. La décision déclarée est conservée ; elle ne
   remplace pas un vote ou son procès-verbal.
3. Enregistrer la régularisation après approbation. Les charges courantes sont
   ensuite figées ; une annulation préalable permet de corriger avant clôture.
4. Résoudre les contrôles bloquants et choisir l'exercice contigu suivant.
5. Clôturer : extinction des charges/produits, report détaillé des classes 1 à 5,
   conservation d'un instantané et d'une empreinte. La clôture définitive ne se
   rouvre pas ; une correction conserve une écriture inverse dans un exercice ouvert.

## Documents et limites

**Dossier comptable annuel** fournit cinq états de préparation, les comparatifs
budgétaires N−1/N/N+1/N+2, une impression/PDF par le navigateur et une archive JSON.
Cette archive contient les données, pas les fichiers des pièces justificatives.
Les modèles ne sont pas présentés comme des annexes réglementaires certifiées.
Le fichier comptable à 18 colonnes conserve les groupes entièrement lettrés ;
sa disponibilité ne constitue pas une certification fiscale.

Le plan et les comptes de régularisation s'appuient sur
l'[arrêté du 14 mars 2005](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000258165).
Le mode simplifié des petites copropriétés, les formats bancaires OFX/CFONB,
les ordres SEPA, les cas fiscaux spécifiques et le dossier de mutation notarial
complet restent à développer. Les décisions saisies peuvent désormais être reliées
au vote adopté et au PV signé dans le [parcours AG](AG-OUTILS.md).

Les réessais portant le même identifiant d'opération ne créent pas de double
règlement. Les corrections, décisions, rapprochements et clôtures sont journalisés.
Les tests utilisent une base PostgreSQL distincte ; aucune écriture d'essai n'est
créée dans les comptes utilisés par l'utilisateur.
