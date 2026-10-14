# -*- coding: utf-8 -*-
'''
lucterios.contacts package
@author: Laurent GAY & Hassan Guermoule
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2026 sd-libre.fr
@license: This file is part of Lucterios.
'''
from __future__ import unicode_literals

from diacamma.accounting.system.default import DefaultSystemAccounting


class MoroccoSystemAcounting(DefaultSystemAccounting):

    GENERAL_CHARTS_ACCOUNT = [
        ("111", "11199999", "Capital social ou personnel", 2),
        ("112", "11299999", "Primes d’émission, de fusion et d’apport", 2),
        ("113", "11399999", "Ecarts de réévaluation", 2),
        ("114", "11499999", "Réserve légale", 2),
        ("115", "11599999", "Autres réserves", 2),
        ("1161", "11619999", "Report à nouveau - solde créditeur", 2),
        ("1169", "11699999", "Report à nouveau - solde débiteur", 2),
        ("1191", "11919999", "Résultat net de l’exercice - solde créditeur", 2),
        ("1199", "11999999", "Résultat net de l’exercice - solde débiteur", 2),
        ("130", "13999999", "Capitaux propres assimilés", 2),
        ("141", "14199999", "Emprunts obligataires", 2),
        ("148", "14899999", "Autres dettes de financement", 2),
        ("150", "15999999", "Provisions durables pour risques et charges", 2),
        ("160", "16999999", "Comptes de liaison des établissements et succursales", 2),
        ("170", "17999999", "Ecarts de conversion – Passif", 2),
        ("210", "21999999", "Immobilisations en non-valeurs", 0),
        ("220", "22999999", "immobilisations incorporelles", 0),
        ("230", "23999999", "Immobilisations corporelles", 0),
        ("241", "24199999", "Prêts immobilisés", 0),
        ("248", "24899999", "Autres créances financières", 0),
        ("251", "25199999", "Titres de participation", 0),
        ("258", "25899999", "Autres titres immobilisés", 0),
        ("270", "27999999", "Ecarts de conversion – actif", 0),
        ("280", "28999999", "Amortissements des immobilisations", 0),
        ("290", "29999999", "Provisions pour dépréciation des immobilisations", 0),
        ("310", "31999999", "Stocks", 0),
        ("341", "34199999", "Fournisseurs débiteurs, avances et acomptes", 0),
        ("342", "34299999", "Clients et comptes rattachés", 0),
        ("343", "34399999", "Personnel – débiteur", 0),
        ("345", "34599999", "Etat – débiteur", 0),
        ("346", "34699999", "Comptes d’associés – débiteurs", 1),
        ("348", "34899999", "Autres débiteurs", 0),
        ("349", "34999999", "Comptes de régularisation – actif", 0),
        ("350", "35099999", "Titres et valeurs de placement", 1),
        ("370", "37099999", "Ecart de conversion – Actif (éléments circulants)", 0),
        ("390", "39999999", "Provisions pour dépréciation des comptes de l’actif circulant", 0),
        ("441", "44199999", "Fournisseurs et comptes rattachés", 1),
        ("442", "44299999", "Clients créditeurs, avances et acomptes", 1),
        ("443", "44399999", "Personnel – créditeur", 1),
        ("444", "44499999", "Organismes sociaux", 1),
        ("445", "44599999", "Etat – créditeur", 1),
        ("446", "44699999", "Comptes d’associés – créditeurs", 1),
        ("448", "44899999", "Autres créanciers", 1),
        ("449", "44999999", "Comptes de régularisation – passif", 1),
        ("450", "45999999", "Autres provisions pour risques et charges", 0),
        ("470", "47099999", "Ecarts de conversion – passif - Eléments circulants", 1),
        ("511", "51199999", "Chèques et valeurs à encaisser", 0),
        ("512", "51299999", "Banques", 0),
        ("514", "51499999", "Banques, Trésorerie Générale et chèques postaux débiteurs", 0),
        ("516", "51699999", "Caisses, régies d’avances et accréditifs", 0),
        ("552", "55299999", "Crédits d’escompte", 0),
        ("553", "55399999", "Crédits de trésorerie", 0),
        ("554", "55499999", "Banques (solde créditeur)", 0),
        ("590", "59099999", "Provisions pour dépréciation des comptes de trésorerie", 0),
        ("611", "61199999", "Achats revendus de marchandises", 4),
        ("612", "61299999", "Achats consommés de matières et fournitures", 4),
        ("613", "61399999", "Autres charges externes", 4),
        ("614", "61499999", "Autres charges externes", 4),
        ("616", "61699999", "Impôts et taxes", 4),
        ("617", "61799999", "Charges de personnel", 4),
        ("618", "61899999", "Autres charges d’exploitation", 4),
        ("619", "61999999", "Dotations d’exploitation", 4),
        ("631", "63199999", "Charges d’intérêts", 4),
        ("633", "63399999", "Pertes de change", 4),
        ("638", "63899999", "Autres charges financières", 4),
        ("639", "63999999", "Dotations financières", 4),
        ("651", "65199999", "Valeurs nettes d’amortissements des immobilisations cédées", 4),
        ("656", "65699999", "Subventions accordées", 4),
        ("658", "65899999", "Autres charges non courantes", 4),
        ("659", "65999999", "Dotations non courantes", 4),
        ("670", "67099999", "Impôts sur les résultats", 4),
        ("691", "69199999", "Participation des salariés aux résultats", 4),
        ("711", "71199999", "Ventes de marchandises", 3),
        ("712", "71299999", "Ventes de biens et services produits", 3),
        ("713", "71399999", "Variation des stocks de produits", 3),
        ("714", "71499999", "Immobilisations produites par l’entreprise pour elle même", 3),
        ("716", "71699999", "Subventions d’exploitation", 3),
        ("718", "71899999", "Autres produits d’exploitation", 3),
        ("719", "71999999", "Reprise d’exploitation, transferts de charges", 3),
        ("732", "73299999", "Produits des titres de participation et des autres titres immobilisés", 3),
        ("733", "73399999", "Gains de change", 3),
        ("738", "73899999", "Intérêts et autres produits financiers", 3),
        ("739", "73999999", "Reprises financières, transferts de charges", 3),
        ("751", "75199999", "Produits des cessions d’immobilisations", 3),
        ("756", "75699999", "Subventions d’équilibre", 3),
        ("757", "75799999", "Reprise sur subventions d’investissements", 3),
        ("758", "75899999", "Autres produits non courants", 3),
        ("759", "75999999", "Reprises non courantes, transferts de charges", 3),
        ("791", "79199999", "Transfert de charges d'exploitation", 3),
        ("810", "81999999", "Résultat d’exploitation", 5),
        ("830", "83099999", "Résultat financier", 5),
        ("840", "84099999", "Résultat courant", 5),
        ("850", "85099999", "Résultat non courant", 5),
        ("860", "86099999", "Résultat avant impôts", 5),
        ("880", "88099999", "Résultat après impôts", 5)]

    NEGATIF_ACCOUNT = "1199"
    POSITIF_ACCOUNT = "1191"

    GENERAL_MASK = r'^[0-8][0-9]{2}[0-9a-zA-Z]*$'

    CASH_MASK = r'^5[0-9][0-9][0-9a-zA-Z]*$'

    CASH_MASK_BEGIN = '5'

    PROVIDER_MASK = r'^44[0-9][0-9a-zA-Z]*$'

    CUSTOMER_MASK = r'^41[0-9][0-9a-zA-Z]*$'

    EMPLOYED_MASK = r'^44[0-9][0-9a-zA-Z]*$'

    SOCIETARY_MASK = r'^34[0-9][0-9a-zA-Z]*$'

    REVENUE_MASK = r'^7[0-9][0-9][0-9a-zA-Z]*$'

    EXPENSE_MASK = r'^6[0-9][0-9][0-9a-zA-Z]*$'

    # THIRD_MASK = "%s|%s|%s|%s" % (PROVIDER_MASK, CUSTOMER_MASK, EMPLOYED_MASK, SOCIETARY_MASK)
    THIRD_MASK = r'^[3-4][0-9][0-9][0-9a-zA-Z]*$'

    ANNEXE_MASK = r'^8[0-9][0-9][0-9a-zA-Z]*$'

    VAT_DEDUCTIVE_MASK = r'^3455[0-9a-zA-Z]*$'

    VAT_COLLECTED_MASK = r'^4455[0-9a-zA-Z]*$'

    VAT_INTRACOMMUNITY_MASK = ''

    EINVOICE = ''
