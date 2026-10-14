from .calculations import numeric


def normalize_roster(rows, voting=False):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
        raise ValueError("Saisissez entre 1 et 500 copropriétaires, y compris les absents.")
    result, identities = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Copropriétaire invalide.")
        owner = row.get("owner_id")
        if owner is not None and (isinstance(owner, bool) or not isinstance(owner, int) or owner < 1):
            raise ValueError("Identifiant de copropriétaire invalide.")
        name = str(row.get("name", "")).strip()
        if not name or len(name) > 200:
            raise ValueError("Nom du copropriétaire requis (200 caractères maximum).")
        identity = ("owner", owner) if owner else ("free", name.casefold())
        if identity in identities:
            raise ValueError("Un copropriétaire ne peut apparaître qu’une fois, même avec plusieurs lots.")
        identities.add(identity)
        shares = numeric(row.get("shares"), f"Droits de vote de {name}", positive=voting)
        attendance = row.get("attendance", "absent")
        vote = row.get("vote", "pending")
        if attendance not in ["absent", "present", "represented", "correspondence"]:
            raise ValueError("Présence inconnue.")
        if vote not in ["pending", "for", "against", "abstain"]:
            raise ValueError("Vote inconnu.")
        if attendance == "absent":
            vote = "pending"
        elif voting and vote == "pending":
            raise ValueError(f"Choisissez le vote de {name}.")
        result.append({"owner_id": owner, "name": name, "shares": str(shares),
                       "attendance": attendance, "vote": vote})
    return result


def aggregate_roster(data):
    rows = normalize_roster(data["roster"], voting=True)
    participating = [r for r in rows if r["attendance"] != "absent"]
    return {**data, "roster": rows, "total_owners": len(rows),
            "participating_owners": len(participating),
            "for_owners": sum(r["vote"] == "for" for r in participating),
            "total_votes": str(sum(numeric(r["shares"], "Voix") for r in rows)),
            **{key: str(sum(numeric(r["shares"], "Voix") for r in participating if r["vote"] == vote))
               for key, vote in [("for_votes", "for"), ("against_votes", "against"), ("abstain_votes", "abstain")]}}
