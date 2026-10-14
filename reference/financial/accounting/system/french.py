# -*- coding: utf-8 -*-
'''
lucterios.contacts package
@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2015 sd-libre.fr
@license: This file is part of Lucterios.
Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

from diacamma.accounting.system.default import DefaultSystemAccounting
from os.path import dirname, join


class FrenchSystemAcounting(DefaultSystemAccounting):

    GENERAL_CHARTS_ACCOUNT = [
        ("100", "10799999", "Compte de capital et réserves", 2),
        ("108", "10899999", "Compte de l'exploitant", 2),
        ("109", "10999999", "Actionnaires :capital souscrit non appelé", 2),
        ("110", "11899999", "Report à nouveau (solde créditeur)", 2),
        ("119", "11999999", "Report à nouveau (solde débiteur)", 2),
        ("120", "12899999", "Résultat de l'exercice (bénéfice)", 2),
        ("129", "12999999", "Résultat de l'exercice (perte)", 2),
        ("130", "13999999", "Subventions d'investissements", 2),
        ("140", "15999999", "Provisions règlementées", 2),
        ("150", "15999999", "Provisions pour risques et charges", 2),
        ("160", "16999999", "Comptes d'emprunts (ou dettes assimilées)", 2),
        ("170", "17999999", "Dettes rattachées à des participations", 2),
        ("180", "18999999", "Comptes de liaison", 2),
        ("190", "19999999", "Fonds dédiés", 2),
        ("200", "20999999", "Immobilisations incorporelles", 0),
        ("210", "21999999", "Immobilisations corporelles", 0),
        ("220", "22999999", "Immobilisations mises en concession", 0),
        ("230", "23999999", "Immobilisations en cours", 0),
        ("250", "25999999", "Parts dans des entreprises liées et créances sur des entreprises liées", 0),
        ("260", "26999999", "Participations et créances rattachées à des participations", 0),
        ("270", "27999999", "Immobilisations financiéres", 0),
        ("280", "28999999", "Amortissements des immobilisations", 0),
        ("290", "29999999", "Provisions pour dépréciation des immobilisations", 0),
        ("310", "31999999", "Stocks de Matiéres premiéres et fournitures", 0),
        ("320", "32999999", "Stocks d'autres approvisionnements", 0),
        ("330", "33999999", "En-cours de production de biens ", 0),
        ("340", "34999999", "En-cours de production de services", 0),
        ("350", "35999999", "Stocks de produits", 0),
        ("360", "36999999", "Stocks provenant d'immobilisations", 0),
        ("370", "37999999", "Stocks de marchandises", 0),
        ("380", "38999999", "Stocks en voie d'acheminement, mis en dépét ou donnés en consignation", 0),
        ("390", "39999999", "Provisions pour dépréc. comptes de stocks.", 0),
        ("400", "400", "Fournisseurs Collectif", 1),
        ("4000", "40899999", "Fournisseurs et comptes rattachés", 1),
        ("409", "40999999", "Fournisseurs débiteurs", 0),
        ("410", "410", "Clients Collectif", 0),
        ("4100", "41899999", "Clients et comptes rattachés", 0),
        ("419", "41999999", "Clients débiteurs", 1),
        ("420", "42999999", "Personnel et comptes rattachés", 1),
        ("430", "43999999", "Sécurité sociale et autres organismes sociaux", 1),
        ("440", "44099999", "État et autres collectivités publiques", 1),
        ("441", "44199999", "État - Subventions à recevoir ", 0),
        ("442", "44299999", "État - Impôts et taxes recouvrables sur des tiers", 1),
        ("443", "44399999", "Opérations particulières avec l'État, les collectivités publiques, les organismes internationaux", 0),
        ("444", "44499999", "État - Impôts sur les bénéfices", 1),
        ("445", "44509999", "État - Taxes sur le chiffre d'affaires", 1),
        ("4452", "44529999", "TVA due intracommunautaire", 0),
        ("4455", "44559999", "TVA à décaisser", 1),
        ("4456", "44561999", "TVA déductible", 0),
        ("44562", "44562999", "TVA déductible sur immobilisations", 0),
        ("44563", "44569999", "TVA déductible sur 0 et services", 0),
        ("4457", "44579999", "TVA sur ventes due à l'Etat", 1),
        ("4458", "44999999", "Autres impôts et taxes dus à l'état", 1),
        ("447", "44799999", "Autres impôts, taxes et versements assimilés", 1),
        ("448", "44899999", "état - Charges à payer et produits à recevoir", 1),
        ("449", "44999999", "Quotas d'émission à restituer à l'état", 1),
        ("450", "45099999", "Groupe et associés", 0),
        ("451", "45199999", "Groupe", 0),
        ("455", "45599999", "Associés - Comptes courants", 1),
        ("456", "45699999", "Associés - Opérations sur le capital", 1),
        ("457", "45799999", "Associés - Dividendes à payer", 1),
        ("458", "45899999", "Associés - Opérations faites en commun et en G.I.E.", 1),
        ("459", "45999999", "Associés - Créances", 1),
        ("460", "46099999", "Débiteurs divers et créditeurs divers", 1),
        ("461", "46199999", "Débiteurs divers", 0),
        ("462", "46299999", "Créditeurs divers", 1),
        ("464", "46499999", "Dettes sur acquisitions de valeurs mobilières de placement", 0),
        ("465", "46599999", "Créances sur cessions de valeurs mobilières de placement", 1),
        ("467", "46799999", "Autres comptes débiteurs ou créditeurs", 1),
        ("468", "46899999", "Divers - Charges à payer et produits à recevoir", 1),
        ("470", "47099999", "Comptes transitoire ou d'attente", 1),
        ("471", "47199999", "Compte en attente d'imputation débiteur", 0),
        ("472", "47299999", "Compte en attente d'imputation débiteur", 1),
        ("476", "47699999", "Différence de conversion - Actif", 0),
        ("477", "47799999", "Différences de conversion - Passif", 1),
        ("478", "47899999", "Autres comptes transitoires", 1),
        ("481", "48199999", "Charges à répartir sur plusieurs exercices", 0),
        ("486", "48699999", "Charges constatées d'avance", 0),
        ("487", "48799999", "Produits constatés d'avance", 1),
        ("488", "48899999", "Comptes de répartition périodique des charges et des produits", 1),
        ("489", "48999999", "Quotas d'émission alloués par l'État", 1),
        ("490", "49999999", "Provisions pour dépréciation des comptes de tiers", 1),
        ("500", "50999999", "Valeurs mobiliéres de placements", 0),
        ("510", "52999999", "Compte de trésorerie, banque, CCP, etc.", 0),
        ("520", "52999999", "Instruments de trésorerie", 0),
        ("530", "53999999", "Compte de caisse", 0),
        ("540", "54999999", "Régies d'avances et accréditifs", 0),
        ("580", "58999999", "Virements internes", 0),
        ("590", "59999999", "Provisions pour dépréc. comptes financiers", 0),
        ("600", "60299999", "Achats de matiéres premiéres, fournitures, etc.", 4),
        ("603", "60399999", "Variations des stocks (approv., marchandises, ...)", 4),
        ("604", "60699999", "Achats et fournitures divers non stockés", 4),
        ("607", "60799999", "Achats de marchandises", 4),
        ("608", "60899999", "Frais divers sur achats", 4),
        ("609", "60999999", "Rabais, remise, ristournes obtenues sur achats", 4),
        ("610", "62999999", "Services extérieurs", 4),
        ("630", "63999999", "Impéts, taxes et versements assimilés", 4),
        ("640", "64499999", "Rémunération du personnel", 4),
        ("645", "64699999", "Charges de sécurité sociale et prévoyance", 4),
        ("647", "64999999", "Autres charges sociales", 4),
        ("650", "65499999", "Autres charges de gestion courante", 4),
        ("655", "65599999", "Quote-part de résultat sur opérations faites en commun", 4),
        ("656", "65999999", "Autres charges de gestion courante", 4),
        ("660", "66999999", "Charges financiéres", 4),
        ("670", "67999999", "Charges exceptionnelles", 4),
        ("680", "68999999", "Dotations aux amortissements et provisions", 4),
        ("691", "69199999", "Participations des salariés", 4),
        ("695", "69899999", "Impôts sur bénéfices", 4),
        ("699", "699", "Compte pour résultat positif", 4),
        ("700", "70899999", "Ventes de produits, services, marchandises, etc.", 3),
        ("709", "70999999", "Rabais, remises, ristournes accordés", 3),
        ("710", "71999999", "Variations des stocks de production", 3),
        ("720", "72999999", "Production immobilisée", 3),
        ("730", "73999999", "Produits sur opérations à long terme", 3),
        ("740", "74999999", "Subventions d'exploitation", 3),
        ("750", "75499999", "Autres produits de gestion courante", 3),
        ("755", "75599999", "Quote-part de résultat sur opérations faites en commun", 3),
        ("756", "75999999", "Autres produits de gestion courante", 3),
        ("760", "76999999", "Produits financiers", 3),
        ("770", "77999999", "Produits exceptionnels", 3),
        ("780", "79899999", "Autres produits divers", 3),
        ("799", "799", "Compte pour résultat négatif", 3),
        ("80", "80999999", "Engagements", 5),
        ("86", "86999999", "Emplois des contributions volontaires en nature", 5),
        ("87", "87999999", "Contributions volontaires en nature", 5),
        ("88", "88999999", "Résultat en instance d'affectation", 5),
        ("89", "89999999", "Bilan", 5)]

    NEGATIF_ACCOUNT = "129"
    POSITIF_ACCOUNT = "120"

    GENERAL_MASK = r'^[0-8][0-9]{2}[0-9a-zA-Z]*$'

    CASH_MASK = r'^5[0-9][0-9][0-9a-zA-Z]*$'

    CASH_MASK_BEGIN = '5'

    PROVIDER_MASK = r'^40[0-9][0-9a-zA-Z]*$'

    CUSTOMER_MASK = r'^41[0-9][0-9a-zA-Z]*$'

    EMPLOYED_MASK = r'^42[0-9][0-9a-zA-Z]*$'

    SOCIETARY_MASK = r'^45[0-9][0-9a-zA-Z]*$'

    REVENUE_MASK = r'^7[0-9][0-9][0-9a-zA-Z]*$'

    EXPENSE_MASK = r'^6[0-9][0-9][0-9a-zA-Z]*$'

    # THIRD_MASK = "%s|%s|%s|%s" % (PROVIDER_MASK, CUSTOMER_MASK, EMPLOYED_MASK, SOCIETARY_MASK)
    THIRD_MASK = r'^4[0-9][0-9][0-9a-zA-Z]*$'

    ANNEXE_MASK = r'^8[0-9][0-9][0-9a-zA-Z]*$'

    VAT_DEDUCTIVE_MASK = r'^4456[0-9a-zA-Z]*$'

    VAT_COLLECTED_MASK = r'^4457[0-9a-zA-Z]*$'

    VAT_INTRACOMMUNITY_MASK = r'^4452[0-9a-zA-Z]*$'

    EINVOICE = 'facturX'

    def get_export_xmlfiles(self):
        file_path = dirname(__file__)
        return (join(file_path, 'french_accountexport.xml'), join(file_path, 'french_fichedescriptive_6709.xsd'))
