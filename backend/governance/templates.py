"""Editable proposals. The manager must check the rule for the actual object."""

TEMPLATES = [
    {
        'id':'scrutineer', 'title':'Désignation d’un scrutateur', 'majority':'24',
        'text':'L’assemblée désigne [nom] comme scrutateur. Soumettre chaque candidat à un vote distinct.', 'pieces':[],
    },
    {
        'id':'reserve-advance', 'title':'Constitution de la réserve de trésorerie', 'majority':'26',
        'text':'L’assemblée décide [constitution ou modification] de la réserve prévue par [clause du règlement], d’un montant de [montant] €, inférieur ou égal au sixième du budget prévisionnel. Les soldes déjà constitués, la répartition, les échéances et le remboursement des avances sont précisés dans [pièce]. Vérifier la majorité et le règlement selon l’objet exact de la décision.',
        'pieces':['Clause du règlement et budget voté','Calcul du plafond et échéancier'],
    },
    {
        'id':'temporary-advance', 'title':'Avance pour un manque temporaire de trésorerie', 'majority':'26',
        'text':'Pour faire face au besoin temporaire [motif], l’assemblée décide une avance remboursable de [montant] €, selon [répartition et échéancier]. Le remboursement interviendra selon [conditions et date].',
        'pieces':['État de trésorerie et justification du besoin','Répartition, échéancier et modalités de restitution'],
    },
    {
        'id':'ppt-advance', 'title':'Avances prévues par le PPT adopté', 'majority':'24',
        'text':'Au titre du PPT adopté le [date], l’assemblée approuve les avances de [montant] € selon [échéancier et clé]. Ces avances remboursables sont distinctes des cotisations non remboursables du fonds travaux. Vérifier la majorité propre à la décision et au plan.',
        'pieces':['PPT adopté et décision','Échéancier des avances et conditions de remboursement'],
    },
    {
        'id':'fund-suspension', 'title':'Suspension des cotisations au fonds travaux', 'majority':'25',
        'text':'Après examen du fonds constitué de [montant] €, du budget de [montant] € et du PPT [situation et montant], l’assemblée se prononce sur la suspension des cotisations pour [période]. Le fonds doit dépasser le budget et, en présence d’un PPT adopté, également 50 % du montant de ses travaux. Aucun remboursement du fonds aux copropriétaires n’est décidé.',
        'pieces':['État du fonds, budget et PPT','Vérification des seuils de suspension'],
    },
    {
        'id':'fund-use', 'title':'Affectation du fonds travaux à une opération', 'majority':'25',
        'text':'L’assemblée affecte [montant] € du fonds travaux à [opération], selon [clé, lots concernés et intérêts attachés]. Appliquer la même majorité que celle de la dépense concernée et vérifier la disponibilité des versements par lot.',
        'pieces':['Décision et financement des travaux','Fonds disponibles par lot et répartition'],
    },
    {
        "id": "president",
        "title": "Désignation du président de séance",
        "majority": "24",
        "text": "L’assemblée désigne [nom] comme président de séance.",
        "pieces": [],
    },
    {
        "id": "secretary",
        "title": "Désignation du secrétaire de séance",
        "majority": "24",
        "text": "L’assemblée désigne [nom] comme secrétaire de séance.",
        "pieces": [],
    },
    {
        "id": "accounts",
        "title": "Approbation des comptes",
        "majority": "24",
        "text": "Après examen des comptes et annexes de l’exercice [dates], l’assemblée approuve les comptes présentés, sous les réserves suivantes : [réserves].",
        "pieces": [
            "Annexe 1 — état financier",
            "Annexe 2 — compte de gestion général",
            "Annexe 3 — opérations courantes",
            "Annexe 4 — opérations terminées",
            "Annexe 5 — opérations non terminées",
            "Projet d’état individuel de répartition",
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
