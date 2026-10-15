"""A recorded, manager-operated assembly; no email, signature or banking provider."""

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from core.models import Owner, Lot
from documents.models import Version
from finance.cycle import digest
from finance.models import ChargeKey, Share, AuditEvent
from finance.models import FiscalYear
from .models import AssemblyWorkflow, AssemblyDelivery, AssemblyVote, AssemblyEvent
from .roster import normalize_roster
from .calculations import vote_result
from .templates import TEMPLATES
from .deadlines import latest_notification, notice_expires


def day_of(meeting):
    return timezone.localtime(meeting.scheduled_at).date()


def add_month(day, count):
    month = day.month - 1 + count
    year = day.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def text(value, maximum=500, required=True):
    result = str(value or "").strip()
    if len(result) > maximum or (required and not result):
        raise ValueError(f"Texte requis, limité à {maximum} caractères.")
    return result


def boolean(data, name):
    if data.get(name) is not True:
        raise ValueError("Confirmez les vérifications indiquées avant de poursuivre.")


def evidence(workflow, pk, retain=True):
    if isinstance(pk, dict):
        pk = pk.get("id")
    version = Version.objects.select_related("document").get(pk=pk)
    if version.document.archived:
        raise ValueError("La pièce est archivée. Choisissez une pièce accessible.")
    if retain:
        workflow.evidence.add(version)
    return {
        "id": version.pk,
        "title": version.document.title,
        "filename": version.filename,
        "checksum": version.checksum,
    }


def event(workflow, user, action, data=None):
    AssemblyEvent.objects.create(
        workflow=workflow, actor=user, action=action, data=data or {}
    )
    AuditEvent.objects.create(
        actor=user, action="assembly." + action, target=str(workflow.meeting_id)
    )


def ensure_draft(meeting):
    if AssemblyWorkflow.objects.filter(meeting=meeting).exclude(phase="draft").exists():
        raise ValueError(
            "Le dossier convoqué est figé. Préparez une nouvelle AG pour modifier l’ordre du jour."
        )


def identity(row):
    return (
        f"owner:{row['owner_id']}"
        if row.get("owner_id")
        else "free:" + row["name"].casefold()
    )


def corrected(rows, two=False):
    total = sum(Decimal(r["raw_shares"]) for r in rows)
    for row in rows:
        raw = Decimal(row["raw_shares"])
        row["shares"] = str(min(raw, total - raw) if len(rows) > 1 and not two else raw)
    return rows


def build_packet(workflow, retain=False):
    meeting, config = workflow.meeting, workflow.config
    if not meeting.location or not meeting.resolutions.exists():
        raise ValueError("Renseignez le lieu et au moins une résolution.")
    if day_of(meeting) <= timezone.localdate():
        raise ValueError("La date de l’AG doit permettre les convocations à venir.")
    normalized = normalize_roster(meeting.roster, voting=False)
    actual_owners = set(
        Lot.objects.filter(owner__isnull=False, shares__gt=0).values_list(
            "owner_id", flat=True
        )
    )
    loaded_owners = {r["owner_id"] for r in normalized if r["owner_id"]}
    if actual_owners - loaded_owners:
        raise ValueError(
            "Ajoutez tous les copropriétaires détenteurs de lots, y compris les absents."
        )
    if (
        not actual_owners
        or Lot.objects.filter(owner__isnull=True, shares__gt=0).exists()
    ):
        raise ValueError("Attribuez les lots avant de figer le corps électoral.")
    raw = []
    contacts = config.get("contacts", {})
    for row in normalized:
        if Decimal(row["shares"]) <= 0:
            raise ValueError(
                f"Droits de {row['name']} : renseignez des tantièmes strictement positifs."
            )
        owner = Owner.objects.get(pk=row["owner_id"]) if row["owner_id"] else None
        if owner:
            expected = sum(owner.lots.values_list("shares", flat=True))
            if Decimal(row["shares"]) != expected:
                raise ValueError(
                    "Rechargez les tantièmes généraux depuis les lots avant de figer l’AG."
                )
            row["name"] = str(owner)
        else:
            if not config.get("manual_electorate_reason"):
                raise ValueError("Expliquez les lignes libres du corps électoral.")
        key = identity(row)
        contact = contacts.get(key, {})
        address = text(contact.get("address"), 500)
        raw.append(
            {
                **row,
                "elector": key,
                "raw_shares": row["shares"],
                "attendance": "absent",
                "vote": "pending",
                "email": (
                    owner.email if owner else text(contact.get("email"), 254, False)
                ),
                "address": address,
                "lots": (
                    list(owner.lots.values_list("number", flat=True)) if owner else []
                ),
            }
        )
    if len(raw) < 2:
        raise ValueError(
            "Le syndicat doit compter au moins deux copropriétaires pour ce parcours."
        )
    two = len(raw) == 2
    electors = corrected(raw, two)
    resolutions = []
    template_map = {r["id"]: r for r in TEMPLATES}
    for res in meeting.resolutions.all():
        if not res.text or "[" in res.text or not res.title:
            raise ValueError(
                f"Résolution {res.position} : complétez le texte et les champs entre crochets."
            )
        settings = config.get("resolutions", {}).get(str(res.pk), {})
        template = template_map.get(settings.get("template")) or next(
            (t for t in TEMPLATES if t["title"] == res.title), None
        )
        pieces = settings.get("pieces", [])
        required = (template or {}).get("pieces", [])
        if any(
            not any(p.get("label") == label and p.get("version") for p in pieces)
            for label in required
        ):
            raise ValueError(
                f"Résolution {res.position} : rattachez les pièces demandées."
            )
        docs = [
            {
                "label": text(p.get("label"), 150),
                **evidence(workflow, p["version"], retain),
            }
            for p in pieces
        ]
        question = None
        if settings.get("request_owner") or settings.get("request_version"):
            requester = Owner.objects.get(pk=settings["request_owner"])
            received = date.fromisoformat(settings["request_received_on"])
            if received > timezone.localdate():
                raise ValueError(
                    "La réception de la demande écrite doit être datée au plus tard aujourd’hui."
                )
            question = {
                "owner": requester.pk,
                "name": str(requester),
                "received_on": str(received),
                "proof": evidence(workflow, settings["request_version"], retain),
            }
        voting_key = (
            ChargeKey.objects.get(pk=settings["key"]) if settings.get("key") else None
        )
        rights = []
        if voting_key:
            if any(r["owner_id"] is None for r in electors):
                raise ValueError(
                    "Une clé spéciale nécessite des copropriétaires et lots identifiés."
                )
            boolean(settings, "key_confirmed")
            weights = {s.lot_id: s.value for s in Share.objects.filter(key=voting_key)}
            for elector in electors:
                value = sum(
                    (
                        weights.get(l.pk, Decimal(0))
                        if not voting_key.general
                        else l.shares
                    )
                    for l in Lot.objects.filter(owner_id=elector["owner_id"])
                )
                if value:
                    rights.append(
                        {"elector": elector["elector"], "raw_shares": str(value)}
                    )
            corrected(rights, two)
            if not rights:
                raise ValueError("Cette clé de vote ne comporte aucun tantième.")
        else:
            rights = [
                {
                    "elector": r["elector"],
                    "raw_shares": r["raw_shares"],
                    "shares": r["shares"],
                }
                for r in electors
            ]
        resolutions.append(
            {
                "id": res.pk,
                "position": res.position,
                "title": res.title,
                "text": res.text,
                "majority": res.majority,
                "template": settings.get("template", ""),
                "pieces": docs,
                "rights": rights,
                "question": question,
                "key_name": voting_key.name if voting_key else "Tantièmes généraux",
            }
        )
    boolean(config, "legal_checked")
    notice_days = int(config.get("notice_days", 21))
    if not 21 <= notice_days <= 365:
        raise ValueError(
            "Délai de convocation : au moins 21 jours, selon le règlement."
        )
    account_year = None
    if config.get("fiscal_year"):
        year = FiscalYear.objects.get(pk=config["fiscal_year"])
        account_year = {
            "id": year.pk,
            "name": year.name,
            "ends_on": str(year.ends_on),
            "approval_deadline": str(add_month(year.ends_on, 6)),
        }
    accounts = any(r['template']=='accounts' or r['title']=='Approbation des comptes' for r in resolutions)
    if accounts:
        if not account_year:
            raise ValueError('Approbation des comptes : choisissez l’exercice présenté et relisez son dossier annuel.')
        year = FiscalYear.objects.select_for_update().get(pk=account_year['id'])
        if year.ends_on >= day_of(meeting):
            raise ValueError('L’exercice soumis à approbation doit être terminé avant l’assemblée.')
        from finance.cycle import annexes
        from finance.models import YearClosure
        closed = YearClosure.objects.filter(year=year).first()
        annual = (closed.snapshot if closed else annexes(year)).get('regulatory')
        if not annual:
            raise ValueError('Dossier clôturé dans un ancien format : préparer et contrôler ses annexes réglementaires séparément.')
        if annual['errors']:
            raise ValueError('Dossier comptable : '+' · '.join(annual['errors']))
        boolean(config,'accounts_reviewed')
        if config.get('accounts_source_hash') != annual['source_hash']:
            raise ValueError('Le dossier annuel a changé : rechargez et relisez les annexes avant de figer la convocation.')
        account_year['dossier'] = annual
    return {
        "title": meeting.title,
        "scheduled_at": meeting.scheduled_at.isoformat(),
        "location": meeting.location,
        "notes": meeting.notes,
        "electors": electors,
        "resolutions": resolutions,
        "two_owners": two,
        "account_year": account_year,
        "notice_days": notice_days,
        "latest_notification": str(
            latest_notification(
                day_of(meeting), notice_days, config.get("local_holidays") is True
            )
        ),
        "local_holidays": config.get("local_holidays") is True,
        "syndic_elector": config.get("syndic_elector", ""),
        "correspondence_deadline": str(day_of(meeting) - timedelta(days=4)),
        "consultation": text(config.get("consultation"), 2000),
        "organizer": text(config.get("organizer"), 200),
        "return_address": text(config.get("return_address"), 500),
    }


def freeze(workflow, user):
    if workflow.phase != "draft":
        raise ValueError("Le dossier est déjà figé.")
    packet = build_packet(workflow, retain=True)
    if timezone.localdate() > date.fromisoformat(packet["latest_notification"]):
        raise ValueError(
            "Il est trop tard pour respecter le délai ordinaire. Reportez la date de l’AG."
        )
    workflow.packet = packet
    workflow.digest = digest(packet)
    workflow.participants = [
        {"elector": r["elector"], "attendance": "absent"} for r in packet["electors"]
    ]
    workflow.phase = "convened"
    workflow.frozen_at = timezone.now()
    workflow.save()
    event(workflow, user, "freeze", {"digest": workflow.digest})


def register_delivery(workflow, user, data):
    kind = data.get("kind")
    allowed = (
        workflow.phase == "convened"
        if kind == "invitation"
        else workflow.phase in ["signed", "closed"]
    )
    if kind not in ["invitation", "minutes"] or not allowed:
        raise ValueError("Cette étape ne permet pas cet enregistrement d’envoi.")
    elector = next(
        (r for r in workflow.packet["electors"] if r["elector"] == data.get("elector")),
        None,
    )
    if not elector:
        raise ValueError("Destinataire absent du dossier figé.")
    method = data.get("method")
    if method not in ["lrar", "lre", "qualified", "hand"] or (
        kind == "minutes" and method == "hand"
    ):
        raise ValueError(
            "Utilisez une notification recommandée/qualifiée ; la remise contre émargement est réservée à la convocation."
        )
    boolean(data, "proof_checked")
    sent, effective = date.fromisoformat(data["sent_on"]), date.fromisoformat(
        data["effective_on"]
    )
    if sent > effective or effective > timezone.localdate():
        raise ValueError(
            "Indiquez les dates réelles d’envoi et de prise d’effet, au plus tard aujourd’hui."
        )
    if kind == "invitation":
        if sent < timezone.localtime(workflow.frozen_at).date() or notice_expires(
            effective,
            workflow.packet["notice_days"],
            workflow.packet.get("local_holidays", False),
        ) >= day_of(workflow.meeting):
            raise ValueError(
                "La notification doit suivre le dossier figé et respecter le délai avant l’AG."
            )
    elif sent < day_of(workflow.meeting) or sent < date.fromisoformat(
        workflow.minutes["signed_on"]
    ):
        raise ValueError("Le PV doit être signé avant son envoi.")
    evidence(workflow, data["proof"])
    item = AssemblyDelivery.objects.create(
        workflow=workflow,
        kind=kind,
        elector=elector["elector"],
        recipient={k: elector[k] for k in ["name", "email", "address"]},
        method=method,
        sent_on=sent,
        effective_on=effective,
        reference=text(data.get("reference"), 250),
        proof_id=data["proof"],
        recorded_by=user,
    )
    event(
        workflow,
        user,
        "delivery",
        {"id": item.pk, "kind": kind, "elector": elector["elector"]},
    )


def set_participants(workflow, user, data):
    if workflow.phase not in ["convened", "session"]:
        raise ValueError("Les présences se renseignent avant ou pendant la séance.")
    rows = data.get("participants")
    electors = {r["elector"]: r for r in workflow.packet["electors"]}
    if (
        not isinstance(rows, list)
        or {r.get("elector") for r in rows} != set(electors)
        or len(rows) != len(electors)
    ):
        raise ValueError("Conservez exactement le corps électoral convoqué.")
    normalized, mandates = [], defaultdict(list)
    for row in rows:
        elector = electors[row["elector"]]
        status = row.get("attendance")
        if status not in ["present", "represented", "correspondence", "absent"]:
            raise ValueError("Présence inconnue.")
        extra = {}
        if status == "represented":
            representative = text(row.get("representative"), 200)
            representative_address = row.get("representative_address")
            rep_id = row.get("representative_id") or None
            if rep_id:
                rep = electors.get(rep_id)
                if not rep or rep_id == row["elector"]:
                    raise ValueError(
                        "Choisissez un autre mandataire ou saisissez une personne extérieure."
                    )
                if rep_id == workflow.packet.get("syndic_elector"):
                    raise ValueError("Le syndic ne peut pas recevoir de pouvoirs.")
                representative = rep["name"]
                representative_address = rep["address"]
                rep_status = next(
                    r["attendance"] for r in rows if r["elector"] == rep_id
                )
                if rep_status != "present":
                    raise ValueError(
                        "Un mandataire copropriétaire doit être présent à la séance."
                    )
            boolean(row, "eligible")
            proof = evidence(workflow, row["proof"])
            representative_key = rep_id or "external:" + representative.casefold()
            mandates[representative_key].append(elector)
            extra = {
                "representative": representative,
                "representative_address": text(representative_address, 500),
                "representative_id": rep_id,
                "proof": proof,
                "eligible": True,
            }
        elif status == "correspondence":
            received = date.fromisoformat(row["received_on"])
            if received > timezone.localdate() or received > date.fromisoformat(
                workflow.packet["correspondence_deadline"]
            ):
                raise ValueError(
                    "Le formulaire doit être reçu au plus tard trois jours francs avant l’AG."
                )
            choices = row.get("choices", {})
            if set(choices) != {
                str(r["id"]) for r in workflow.packet["resolutions"]
            } or any(v not in ["for", "against", "abstain"] for v in choices.values()):
                raise ValueError(
                    "Recopiez un choix pour chaque résolution depuis le formulaire signé."
                )
            extra = {
                "received_on": str(received),
                "proof": evidence(workflow, row["proof"]),
                "choices": choices,
            }
        normalized.append({"elector": row["elector"], "attendance": status, **extra})
    total = sum(Decimal(r["shares"]) for r in electors.values())
    for key, delegated in mandates.items():
        own = Decimal(electors[key]["shares"]) if key in electors else Decimal(0)
        if (
            len(delegated) > 3
            and (own + sum(Decimal(r["shares"]) for r in delegated)) * 10 > total
        ):
            raise ValueError(
                "Plus de trois pouvoirs : les voix du mandataire et de ses mandants dépassent 10 % du syndicat."
            )
    workflow.participants = normalized
    workflow.save(update_fields=["participants"])
    event(workflow, user, "attendance", {"participants": normalized})


def start_session(workflow, user, data):
    if workflow.phase != "convened" or day_of(workflow.meeting) > timezone.localdate():
        raise ValueError("La séance s’ouvre à compter de sa date, après convocation.")
    if workflow.deliveries.filter(kind="invitation").count() != len(
        workflow.packet["electors"]
    ):
        raise ValueError(
            "Enregistrez une preuve de convocation pour chaque copropriétaire."
        )
    boolean(data, "attendance_checked")
    boolean(data, "president_eligible")
    president_id = data.get("president")
    president = next(
        (r for r in workflow.packet["electors"] if r["elector"] == president_id), None
    )
    if (
        not president
        or next(r for r in workflow.participants if r["elector"] == president_id)[
            "attendance"
        ]
        != "present"
    ):
        raise ValueError(
            "Le président choisi doit être présent et éligible ; le syndic ne peut pas présider."
        )
    if president_id == workflow.packet.get("syndic_elector"):
        raise ValueError("Le syndic désigné dans le dossier ne peut pas présider l’AG.")
    secretary = text(data.get("secretary"), 200)
    scrutineers = text(data.get("scrutineers"), 500, False)
    workflow.bureau = {
        "president": president["name"],
        "president_id": president_id,
        "secretary": secretary,
        "scrutineers": scrutineers,
        "confirmed_elected": True,
    }
    boolean(data, "bureau_elected")
    workflow.phase = "session"
    workflow.save(update_fields=["bureau", "phase"])
    event(workflow, user, "start", {"bureau": workflow.bureau})


def recorded_result(workflow, resolution, roster, mode="first", initial=None):
    rule = (
        resolution["majority"] if mode == "first" else "24" if mode == "25-1" else "25"
    )
    if workflow.packet["two_owners"]:
        if mode != "first":
            raise ValueError(
                "Les passerelles du cas général ne sont pas utilisées pour un syndicat de deux copropriétaires."
            )
        total = sum(Decimal(r["shares"]) for r in roster)
        yes = sum(
            Decimal(r["shares"])
            for r in roster
            if r["vote"] == "for" and r["attendance"] != "absent"
        )
        supporters = sum(
            r["vote"] == "for" and r["attendance"] != "absent" for r in roster
        )
        adopted = (
            yes * 2 > total
            if rule == "24"
            else yes * 3 >= total * 2 if rule == "25" else supporters == len(roster)
        )
        return {
            "rule": rule,
            "mode": mode,
            "adopted": adopted,
            "status": "adopted" if adopted else "not_adopted",
            "bridge": None,
            "total_votes": str(total),
            "total_owners": len(roster),
            "for_votes": str(yes),
            "against_votes": str(
                sum(Decimal(r["shares"]) for r in roster if r["vote"] == "against")
            ),
            "abstain_votes": str(
                sum(Decimal(r["shares"]) for r in roster if r["vote"] == "abstain")
            ),
            "explanation": "Syndicat à deux copropriétaires : article 41-16, sans réduction de l’article 22 ni passerelle du cas général. Articles 26/unanimité : accord de tous les votants concernés.",
        }
    return vote_result(
        {
            "rule": rule,
            "mode": mode,
            "roster": roster,
            **({"initial": initial} if initial else {}),
        },
        assembly=True,
    )


def record_vote(workflow, user, data):
    if workflow.phase != "session":
        raise ValueError("Ouvrez la séance avant d’enregistrer un vote.")
    resolution = next(
        (
            r
            for r in workflow.packet["resolutions"]
            if r["id"] == int(data["resolution"])
        ),
        None,
    )
    if not resolution:
        raise ValueError("Résolution absente de l’ordre du jour convoqué.")
    tour = int(data.get("tour", 1))
    if tour not in [1, 2]:
        raise ValueError(
            "Seuls le premier vote et un second vote distinct sont possibles."
        )
    prior = workflow.votes.filter(
        resolution_id=resolution["id"], voided_at__isnull=True
    ).order_by("tour")
    initial = prior.first()
    if prior.filter(tour=tour).exists() or (tour == 1 and prior.exists()):
        raise ValueError(
            "Ce vote est déjà enregistré. Une correction doit conserver le vote annulé et son motif."
        )
    mode = "first"
    if tour == 2:
        if not initial or not initial.data["result"].get("bridge"):
            raise ValueError("Le premier vote ne permet pas une passerelle.")
        mode = initial.data["result"]["bridge"]
    choices = data.get("choices", {})
    amendment = text(data.get("amendment"), 5000, False)
    if tour == 2 and amendment != initial.data.get("amendment", ""):
        raise ValueError("Conservez le même texte entre les deux tours.")
    participants = {r["elector"]: r for r in workflow.participants}
    electors = {r["elector"]: r for r in workflow.packet["electors"]}
    expected = {
        r["elector"]
        for r in resolution["rights"]
        if participants[r["elector"]]["attendance"] in ["present", "represented"]
    }
    if set(choices) != expected or any(
        v not in ["for", "against", "abstain"] for v in choices.values()
    ):
        raise ValueError(
            "Choisissez un vote pour chaque copropriétaire présent ou représenté concerné, sans vote supplémentaire."
        )
    roster, changed_correspondents = [], []
    for right in resolution["rights"]:
        key = right["elector"]
        participant, elector = participants[key], electors[key]
        status, vote = participant["attendance"], "pending"
        if status == "correspondence":
            vote = participant["choices"][str(resolution["id"])]
            if amendment and vote == "for":
                status, vote = "absent", "pending"
                changed_correspondents.append(key)
        elif status != "absent":
            vote = choices[key]
        roster.append(
            {
                "owner_id": elector["owner_id"],
                "name": elector["name"],
                "shares": right["shares"],
                "attendance": status,
                "vote": vote,
            }
        )
    result = recorded_result(
        workflow, resolution, roster, mode, initial.data["input"] if tour == 2 else None
    )
    item = AssemblyVote.objects.create(
        workflow=workflow,
        resolution_id=resolution["id"],
        tour=tour,
        recorded_by=user,
        data={
            "input": {
                "rule": resolution["majority"] if tour == 1 else result["rule"],
                "mode": mode,
                "roster": roster,
            },
            "result": result,
            "amendment": amendment,
            "incident": text(data.get("incident"), 5000, False),
            "correspondents_deemed_absent": changed_correspondents,
            "participants": workflow.participants,
        },
    )
    event(
        workflow,
        user,
        "vote",
        {"id": item.pk, "resolution": resolution["id"], "tour": tour},
    )


def void_vote(workflow, user, data):
    if workflow.phase != "session":
        raise ValueError(
            "Un vote ne peut être corrigé qu’avant la rédaction finale du PV."
        )
    item = workflow.votes.get(pk=data["vote"], voided_at__isnull=True)
    if (
        item.tour == 1
        and workflow.votes.filter(
            resolution=item.resolution, tour=2, voided_at__isnull=True
        ).exists()
    ):
        raise ValueError("Corrigez d’abord le second tour.")
    item.void_reason = text(data.get("reason"), 500)
    item.voided_at = timezone.now()
    item.save(update_fields=["void_reason", "voided_at"])
    event(workflow, user, "void_vote", {"id": item.pk, "reason": item.void_reason})


def minutes_data(workflow):
    results, opponents, absent = [], set(), set()
    for resolution in workflow.packet["resolutions"]:
        votes = list(
            workflow.votes.filter(
                resolution_id=resolution["id"], voided_at__isnull=True
            )
        )
        if not votes:
            raise ValueError(
                f"Résolution {resolution['position']} : enregistrez le vote avant de préparer le PV."
            )
        final = votes[-1]
        group = {"for": [], "against": [], "abstain": [], "absent": [], 'deemed_default': []}
        for row in final.data["input"]["roster"]:
            deemed = identity(row) in final.data.get('correspondents_deemed_absent',[])
            group['deemed_default' if deemed else "absent" if row["attendance"] == "absent" else row["vote"]].append(
                row
            )
            elector = identity(row)
            if row["attendance"] == "absent":
                absent.add(elector)
            elif row["vote"] == (
                "against" if final.data["result"]["adopted"] else "for"
            ):
                opponents.add(elector)
        results.append(
            {
                "resolution": resolution,
                "votes": [{"id": v.pk, "tour": v.tour, **v.data} for v in votes],
                "groups": group,
                "adopted": final.data["result"]["adopted"],
            }
        )
    return {
        "title": workflow.packet["title"],
        "scheduled_at": workflow.packet["scheduled_at"],
        "location": workflow.packet["location"],
        "bureau": workflow.bureau,
        "resolutions": results,
        "attendance": workflow.participants,
        "electors": workflow.packet["electors"],
        "required_notifications": sorted(opponents | absent),
        "signature_deadline": str(day_of(workflow.meeting) + timedelta(days=8)),
        "notification_deadline": str(add_month(day_of(workflow.meeting), 1)),
        "packet_digest": workflow.digest,
        "appeal_notice": "Article 42, alinéa 2, de la loi n° 65-557 du 10 juillet 1965 : « Les actions en contestation des décisions des assemblées générales doivent, à peine de déchéance, être introduites par les copropriétaires opposants ou défaillants dans un délai de deux mois à compter de la notification du procès-verbal d’assemblée, sans ses annexes. Cette notification est réalisée par le syndic dans le délai d’un mois à compter de la tenue de l’assemblée générale. »",
    }


def prepare_minutes(workflow, user, data):
    if workflow.phase != "session":
        raise ValueError("La rédaction finale intervient après les votes de la séance.")
    boolean(data, "reviewed")
    workflow.minutes = {
        **minutes_data(workflow),
        "remarks": text(data.get("remarks"), 5000, False),
    }
    workflow.minutes["digest"] = digest(workflow.minutes)
    workflow.phase = "minutes"
    workflow.save(update_fields=["minutes", "phase"])
    event(workflow, user, "minutes", {"digest": workflow.minutes["digest"]})


def sign_minutes(workflow, user, data):
    if workflow.phase != "minutes":
        raise ValueError("Préparez le PV avant de rattacher ses signatures.")
    boolean(data, "signatures_checked")
    signed_on = date.fromisoformat(data["signed_on"])
    if not day_of(workflow.meeting) <= signed_on <= timezone.localdate():
        raise ValueError(
            "Indiquez la date réelle de signature après la séance et au plus tard aujourd’hui."
        )
    signed = evidence(workflow, data["signed_proof"])
    attendance = evidence(workflow, data["attendance_proof"])
    workflow.minutes = {
        **workflow.minutes,
        "signed_on": str(signed_on),
        "signed_proof": signed,
        "attendance_proof": attendance,
    }
    workflow.phase = "signed"
    workflow.save(update_fields=["minutes", "phase"])
    event(
        workflow,
        user,
        "signatures",
        {
            "signed_on": str(signed_on),
            "signed_proof": signed,
            "attendance_proof": attendance,
        },
    )


def close_assembly(workflow, user, data):
    if workflow.phase != "signed":
        raise ValueError(
            "Rattachez le PV signé et la feuille de présence avant l’archivage."
        )
    required = set(workflow.minutes["required_notifications"])
    delivered = set(
        workflow.deliveries.filter(kind="minutes").values_list("elector", flat=True)
    )
    if required - delivered:
        raise ValueError(
            "Enregistrez les preuves de notification aux opposants et défaillants."
        )
    boolean(data, "reviewed")
    workflow.phase = "closed"
    workflow.closed_at = timezone.now()
    workflow.save(update_fields=["phase", "closed_at"])
    workflow.meeting.archived = True
    workflow.meeting.save(update_fields=["archived"])
    event(workflow, user, "close", {"digest": digest(workflow.minutes)})
