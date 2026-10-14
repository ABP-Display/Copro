"""Editable proposals. The manager must check the rule for the actual object."""

TEMPLATES = [
    {
        "id": "president",
        "title": "Désignation du président de séance",
        "majority": "24",
        "text": "L’assemblée désigne [nom] comme président de séance.",
        "pieces": [],
    },
    {
        "id": "secretary",
        "title": "Désignation du secrétaire et des scrutateurs",
        "majority": "24",
        "text": "L’assemblée désigne [nom] comme secrétaire et [noms] comme scrutateurs.",
        "pieces": [],
    },
    {
        "id": "accounts",
        "title": "Approbation des comptes",
        "majority": "24",
        "text": "Après examen des comptes et annexes de l’exercice [dates], l’assemblée approuve les comptes présentés, sous les réserves suivantes : [réserves].",
        "pieces": [
            "Comptes et annexes",
            "État des dépenses et modalités de consultation des justificatifs",
        ],
    },
    {
        "id": "budget",
        "title": "Vote du budget prévisionnel",
        "majority": "24",
        "text": "L’assemblée adopte le budget de [montant] € pour l’exercice [dates], détaillé dans la pièce jointe. Les provisions seront exigibles aux dates suivantes : [dates].",
        "pieces": ["Projet de budget comparatif"],
    },
    {
        "id": "syndic",
        "title": "Désignation du syndic bénévole",
        "majority": "25",
        "text": "L’assemblée désigne le copropriétaire [nom] comme syndic non professionnel du [date] au [date], selon les conditions et éventuelle indemnité jointes.",
        "pieces": ["Projet de mandat et conditions"],
    },
    {
        "id": "council",
        "title": "Élection d’un membre du conseil syndical",
        "majority": "25",
        "text": "L’assemblée élit [nom] au conseil syndical pour une durée de [durée]. Voter séparément pour chaque candidat.",
        "pieces": [],
    },
    {
        "id": "maintenance",
        "title": "Travaux d’entretien ou de conservation",
        "majority": "24",
        "text": "L’assemblée décide les travaux [description] selon le devis [référence], pour un plafond de [montant] €. Financement, clé, échéances et conditions : [détails]. Vérifier que l’objet relève effectivement de l’article 24.",
        "pieces": [
            "Devis et conditions des contrats",
            "Plan de financement et répartition",
        ],
    },
    {
        "id": "works",
        "title": "Travaux à majorité absolue",
        "majority": "25",
        "text": "L’assemblée décide [travaux précisément décrits], selon [devis], pour [montant] €, financés selon [clé et échéances]. Vérifier la majorité propre à l’objet des travaux.",
        "pieces": [
            "Devis et conditions des contrats",
            "Plan de financement et répartition",
        ],
    },
    {
        "id": "fund",
        "title": "Cotisation annuelle au fonds travaux",
        "majority": "25",
        "text": "L’assemblée fixe la cotisation annuelle au fonds travaux à [montant] €, après vérification des minima applicables, selon [clé et échéances].",
        "pieces": ["Budget et PPT adopté, s’il existe", "Calcul de cotisation"],
    },
    {
        "id": "quitus",
        "title": "Quitus de gestion — décision distincte",
        "majority": "24",
        "text": "Après examen du rapport d’activité et des informations connues, l’assemblée se prononce sur le quitus pour [période], avec les réserves [détails]. Cette décision est distincte de l’approbation des comptes ; elle n’est pas obligatoire.",
        "pieces": ["Rapport de gestion et réserves"],
    },
]
