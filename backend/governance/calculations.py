from decimal import Decimal, InvalidOperation, ROUND_DOWN

VERIFIED_ON = "2026-10-13"

SOURCES = [
    {
        "title": "Règles de vote en copropriété — Service Public",
        "url": "https://www.service-public.gouv.fr/particuliers/vosdroits/F2137",
    },
    {
        "title": "Loi du 10 juillet 1965 — Légifrance",
        "url": "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000880200",
    },
]


def numeric(value, name, positive=False):

    if isinstance(value, bool):
        raise ValueError(f"{name} : nombre attendu.")

    try:
        result = Decimal(str(value))

    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{name} : nombre invalide.")

    if not result.is_finite() or result < 0 or result > Decimal("1000000000"):

        raise ValueError(
            f"{name} : nombre positif inférieur ou égal à un milliard attendu."
        )

    if result.as_tuple().exponent < -2:
        raise ValueError(f"{name} : deux décimales maximum.")

    if positive and result == 0:
        raise ValueError(f"{name} doit être supérieur à zéro.")

    return result


def integer(value, name):

    result = numeric(value, name)

    if result != result.to_integral_value():
        raise ValueError(f"{name} : nombre entier attendu.")

    return int(result)


def vote_result(data, allow_second=True, assembly=False):

    if "roster" in data:

        from .roster import aggregate_roster

        data = aggregate_roster(data)

    rule = str(data.get("rule", "24"))

    mode = str(data.get("mode", "first"))

    if rule not in ["24", "25", "26", "unanimity"] or mode not in [
        "first",
        "25-1",
        "26-1",
    ]:

        raise ValueError("Majorité ou tour de vote inconnu.")

    if mode != "first":

        if not allow_second:
            raise ValueError("Une passerelle ne peut pas être enchaînée à une autre.")

        initial = data.get("initial")

        if not isinstance(initial, dict) or initial.get("mode", "first") != "first":
            raise ValueError("Les données du premier vote sont requises.")

        if "roster" in initial:

            from .roster import aggregate_roster

            initial = aggregate_roster(initial)

            signature = lambda rows: sorted(
                (str(r["owner_id"]), r["name"], Decimal(r["shares"])) for r in rows
            )

            if "roster" not in data or signature(data["roster"]) != signature(
                initial["roster"]
            ):

                raise ValueError(
                    "Conservez les mêmes copropriétaires et droits entre les deux votes."
                )

        original = vote_result(initial, allow_second=False, assembly=assembly)

        if original["bridge"] != mode:
            raise ValueError("Ce premier vote ne permet pas cette passerelle.")

        expected = "24" if mode == "25-1" else "25"

        if rule != expected:
            raise ValueError(
                "La majorité du second vote ne correspond pas à la passerelle."
            )

        for key in ["total_votes", "total_owners"]:

            if numeric(data.get(key), key) != numeric(initial.get(key), key):
                raise ValueError(
                    "Le corps électoral doit rester identique entre les deux votes."
                )

    total = numeric(data.get("total_votes"), "Total des voix", True)

    yes = numeric(data.get("for_votes", 0), "Voix pour")

    no = numeric(data.get("against_votes", 0), "Voix contre")

    abstain = numeric(data.get("abstain_votes", 0), "Voix abstention")

    owners = integer(data.get("total_owners"), "Nombre total de copropriétaires")

    attending = integer(
        data.get("participating_owners"), "Copropriétaires participants"
    )

    supporters = integer(data.get("for_owners"), "Copropriétaires pour")

    if owners < 3 and not assembly:
        raise ValueError(
            "Ce simulateur du cas général ne traite pas les copropriétés à un ou deux copropriétaires (règles particulières)."
        )

    if not 0 <= supporters <= attending <= owners:
        raise ValueError("Les nombres de copropriétaires sont incohérents.")

    participating = yes + no + abstain

    if participating > total:
        raise ValueError("Les voix pour, contre et abstentions dépassent le total.")

    if (yes > 0) != (supporters > 0) or (participating > 0) != (attending > 0):
        raise ValueError("Les nombres de voix et de copropriétaires sont incohérents.")

    other_groups = int(no > 0) + int(abstain > 0)

    if attending - supporters < other_groups or (
        other_groups == 0 and attending != supporters
    ):
        raise ValueError(
            "Vérifiez les copropriétaires pour, contre et abstentionnistes."
        )

    if owners - attending > 0 and participating == total:
        raise ValueError(
            "Des copropriétaires sont absents mais toutes les voix sont comptées : vérifiez le corps électoral."
        )

    if owners == attending and participating < total:
        raise ValueError(
            "Tous les copropriétaires participent mais des voix sont manquantes."
        )

    expressed = yes + no

    bridge = None

    if rule == "24":

        adopted = expressed > 0 and yes > no

        explanation = "Les voix pour doivent dépasser les voix contre ; les abstentions et les absents ne font pas partie des voix exprimées."

        criterion = f"{yes} voix pour > {no} voix contre"

    elif rule == "25":

        adopted = yes * 2 > total

        explanation = "Les voix pour doivent dépasser la moitié des voix de tous les copropriétaires."

        criterion = f"2 × {yes} > {total}"

        if not adopted and yes * 3 >= total:
            bridge = "25-1"

    elif rule == "26":

        adopted = supporters * 2 > owners and yes * 3 >= total * 2

        explanation = "Il faut plus de la moitié de tous les copropriétaires, détenant au moins les deux tiers de toutes les voix."

        criterion = f"2 × {supporters} > {owners} et 3 × {yes} ≥ 2 × {total}"

        if not adopted and supporters * 2 >= attending and yes * 3 >= total:
            bridge = "26-1"

    else:

        adopted = yes == total and supporters == owners

        explanation = (
            "Tous les copropriétaires doivent voter pour, avec la totalité des voix."
        )

        criterion = f"{yes} = {total} voix et {supporters} = {owners} copropriétaires"

    if mode != "first":
        bridge = None

    bridge_message = {
        "25-1": "Seuil de la passerelle 25-1 atteint : un second vote distinct à l’article 24 est à examiner. La résolution n’est pas adoptée par ce seul résultat.",
        "26-1": "Seuil de la passerelle 26-1 atteint : un second vote distinct à l’article 25 est à examiner. Il ne permet pas une troisième lecture à l’article 24.",
    }.get(bridge, "")

    return {
        "rule": rule,
        "mode": mode,
        "adopted": adopted,
        "status": (
            "adopted"
            if adopted
            else (
                "no_expressed_votes"
                if rule == "24" and expressed == 0
                else "not_adopted"
            )
        ),
        "explanation": explanation,
        "criterion": criterion,
        "bridge": bridge,
        "bridge_message": bridge_message,
        "total_votes": str(total),
        "participating_votes": str(participating),
        "expressed_votes": str(expressed),
        "absent_votes": str(total - participating),
        "for_votes": str(yes),
        "against_votes": str(no),
        "abstain_votes": str(abstain),
        "total_owners": owners,
        "participating_owners": attending,
        "for_owners": supporters,
        "verified_on": VERIFIED_ON,
        "country": "FR",
        "sources": SOURCES,
        "scope": "Cas général, sur les droits de vote corrigés. Vérifiez la majorité applicable, les réductions de voix de l’article 22, les mandats et les cas particuliers avant utilisation en séance.",
    }


def allocate(total, weights):

    total = numeric(total, "Montant", True)

    if not weights or len(weights) > 200:
        raise ValueError("Saisissez entre 1 et 200 parts.")

    values = [numeric(w, "Poids") for w in weights]

    weight = sum(values)

    if weight == 0:
        raise ValueError("Au moins un poids doit être supérieur à zéro.")

    cents = int(total * 100)

    exact = [Decimal(cents) * value / weight for value in values]

    floors = [int(value.to_integral_value(rounding=ROUND_DOWN)) for value in exact]

    for index in sorted(range(len(values)), key=lambda i: (-(exact[i] - floors[i]), i))[
        : cents - sum(floors)
    ]:
        floors[index] += 1

    return [Decimal(value) / 100 for value in floors]


def split_result(data):

    rows = data.get("rows")

    if not isinstance(rows, list) or not rows or len(rows) > 200:
        raise ValueError("Une liste de 1 à 200 parts est attendue.")

    normalized = []

    for index, row in enumerate(rows):

        if not isinstance(row, dict):
            raise ValueError("Part invalide.")

        label = str(row.get("label", f"Part {index+1}")).strip()

        if not label or len(label) > 100:
            raise ValueError("Libellé de part requis (100 caractères maximum).")

        normalized.append(
            {"label": label, "weight": str(numeric(row.get("weight"), "Poids"))}
        )

    values = allocate(data.get("amount"), [r["weight"] for r in normalized])

    return {
        "rows": [
            {**row, "amount": str(value)} for row, value in zip(normalized, values)
        ],
        "total": str(sum(values)),
        "weight_total": str(sum(Decimal(r["weight"]) for r in normalized)),
    }


def installment_result(data):

    count = integer(data.get("count"), "Nombre d’échéances")

    if not 1 <= count <= 60:
        raise ValueError("Choisissez entre 1 et 60 échéances.")

    values = allocate(data.get("amount"), [1] * count)

    return {
        "rows": [
            {"number": index + 1, "amount": str(value)}
            for index, value in enumerate(values)
        ],
        "total": str(sum(values)),
    }
