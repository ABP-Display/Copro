from datetime import date
from decimal import Decimal
from django.db.models import Sum
from .models import Line, Budget, FiscalYear


def report(year,kind,filters):
    start=date.fromisoformat(filters.get("start") or str(year.starts_on))
    end=date.fromisoformat(filters.get("end") or str(year.ends_on))
    if start>end or start<year.starts_on or end>year.ends_on:
        raise ValueError("La période doit être comprise dans l’exercice.")
    prefix=filters.get("prefix","")
    if prefix and (not prefix.isdigit() or len(prefix)>20): raise ValueError("Préfixe de compte invalide.")
    query=Line.objects.filter(entry__year=year,account__code__startswith=prefix)
    if kind in ('income','budget'):query=query.exclude(entry__kind='closing')
    if filters.get("center"):query=query.filter(entry__cost_center_id=int(filters["center"]))
    if filters.get("owner"):query=query.filter(owner_id=int(filters["owner"]))
    if filters.get('supplier'):query=query.filter(supplier_id=int(filters['supplier']))
    if filters.get("journal"):query=query.filter(entry__journal=filters["journal"])
    selected=query.filter(entry__date__gte=start,entry__date__lte=end)
    grouped=selected.values("account__code","account__name").annotate(debit=Sum("debit"),credit=Sum("credit")).order_by("account__code")
    balances=[{"code":r["account__code"],"name":r["account__name"],"debit":str(r["debit"]),"credit":str(r["credit"]),"balance":str(r["debit"]-r["credit"])} for r in grouped]
    rows=[]; totals={}; previous_year=None
    if kind == 'supplier-auxiliary':
        auxiliary=query.filter(account__code__startswith='40', entry__date__lte=end)
        identities={r['supplier_id']:r['supplier__name'] or 'Fournisseur non identifié (historique / saisie libre)' for r in auxiliary.values('supplier_id','supplier__name').distinct()}
        previous={r['supplier_id']:r['credit']-r['debit'] for r in auxiliary.filter(entry__date__lt=start).values('supplier_id').annotate(debit=Sum('debit'),credit=Sum('credit'))}
        period={r['supplier_id']:r for r in auxiliary.filter(entry__date__gte=start).values('supplier_id').annotate(debit=Sum('debit'),credit=Sum('credit'))}
        for supplier_id,name in sorted(identities.items(),key=lambda item:(item[1].casefold(),item[0] or 0)):
            opening=previous.get(supplier_id,Decimal(0));movement=period.get(supplier_id,{'debit':Decimal(0),'credit':Decimal(0)})
            closing=opening+movement['credit']-movement['debit']
            if filters.get('nonzero')=='1' and closing==0:continue
            rows.append({'supplier':name,'opening':str(opening),'debit':str(movement['debit']),'credit':str(movement['credit']),'balance':str(closing)})
        totals={key:str(sum((Decimal(r[key]) for r in rows),Decimal(0))) for key in ['opening','debit','credit','balance']}
    elif kind == "auxiliary":
        # Separate individual balances on copropriétaire accounts; never shared publicly.
        auxiliary=query.filter(account__code__startswith="450",entry__date__lte=end)
        identities={r["owner_id"]:r for r in auxiliary.values("owner_id","owner__first_name","owner__last_name").distinct()}
        previous={r["owner_id"]:r["debit"]-r["credit"] for r in auxiliary.filter(entry__date__lt=start).values("owner_id").annotate(debit=Sum("debit"),credit=Sum("credit"))}
        period={r["owner_id"]:r for r in auxiliary.filter(entry__date__gte=start).values("owner_id").annotate(debit=Sum("debit"),credit=Sum("credit"))}
        for owner_id,identity in sorted(identities.items(),key=lambda item:((item[1]["owner__last_name"] or "").casefold(),item[0] or 0)):
            opening=previous.get(owner_id,Decimal("0")); movement=period.get(owner_id,{"debit":Decimal("0"),"credit":Decimal("0")})
            closing=opening+movement["debit"]-movement["credit"]
            if filters.get("nonzero")=="1" and closing==0:continue
            rows.append({"owner":(" ".join([identity["owner__first_name"] or "",identity["owner__last_name"] or ""]).strip() or "Non attribué"),"opening":str(opening),"debit":str(movement["debit"]),"credit":str(movement["credit"]),"balance":str(closing)})
        totals={key:str(sum((Decimal(r[key]) for r in rows),Decimal("0"))) for key in ["opening","debit","credit","balance"]}
    elif kind in ["balance","ledger","journal"]:
        if kind=="balance":
            rows=balances
            if filters.get("nonzero")=="1":rows=[r for r in rows if Decimal(r["balance"])!=0]
        else:
            running={r["account__code"]:r["debit"]-r["credit"] for r in query.filter(entry__date__lt=start).values("account__code").annotate(debit=Sum("debit"),credit=Sum("credit"))}
            ordering=["account__code","entry__date","entry__number","id"] if kind=="ledger" else ["entry__date","entry__number","id"]
            for line in selected.select_related("account","entry","owner","supplier").order_by(*ordering):
                code=line.account.code;opening=running.get(code,Decimal(0));running[code]=opening+line.debit-line.credit
                rows.append({"code":code,"name":line.account.name,"date":str(line.entry.date),"number":line.entry.number,"journal":line.entry.journal,"label":line.entry.label,"reference":line.entry.reference,"owner":str(line.owner) if line.owner else "","supplier":line.supplier.name if line.supplier else "","opening":str(opening),"debit":str(line.debit),"credit":str(line.credit),"balance":str(running[code])})
        totals={"debit":str(sum(Decimal(r["debit"]) for r in balances)),"credit":str(sum(Decimal(r["credit"]) for r in balances))}
    elif kind in ["income","budget"]:
        budget_query=Budget.objects.filter(year=year,account__code__startswith=prefix)
        if filters.get("center"):budget_query=budget_query.filter(cost_center_id=int(filters["center"]))
        else:budget_query=budget_query.filter(cost_center__isnull=True)
        planned={r["account__code"]:r["total"] for r in budget_query.values("account__code").annotate(total=Sum("amount"))}
        names={r["account__code"]:r["account__name"] for r in budget_query.values("account__code","account__name")}
        notes={}
        for r in budget_query.select_related('account','key'):
            if r.variance_note:
                notes.setdefault(r.account.code,[]).append((r.key.name+' : ' if r.key_id else '')+r.variance_note)
        notes={code:' · '.join(values) for code,values in notes.items()}
        previous_year=FiscalYear.objects.filter(ends_on__lt=year.starts_on).order_by('-ends_on').first()
        previous_actual={}; previous_budget={}
        if previous_year:
            old=Line.objects.filter(entry__year=previous_year,account__code__startswith=prefix).exclude(entry__kind='closing')
            if filters.get('center'):old=old.filter(entry__cost_center_id=int(filters['center']))
            if filters.get('journal'):old=old.filter(entry__journal=filters['journal'])
            if filters.get('owner'):old=old.filter(owner_id=int(filters['owner']))
            if filters.get('supplier'):old=old.filter(supplier_id=int(filters['supplier']))
            for r in old.values('account__code','account__name').annotate(debit=Sum('debit'),credit=Sum('credit')):
                code=r['account__code']
                previous_actual[code]=(r['debit']-r['credit'])*(1 if code.startswith('6') else -1)
                names.setdefault(code,r['account__name'])
            old_budget=Budget.objects.filter(year=previous_year,account__code__startswith=prefix)
            old_budget=old_budget.filter(cost_center_id=int(filters['center'])) if filters.get('center') else old_budget.filter(cost_center__isnull=True)
            previous_budget={r['account__code']:r['total'] for r in old_budget.values('account__code').annotate(total=Sum('amount'))}
            names.update({r['account__code']:r['account__name'] for r in old_budget.values('account__code','account__name')})
        actual={r["code"]:r for r in balances}
        for code in sorted(set(actual)|set(planned)|set(previous_actual)|set(previous_budget)):
            if not code.startswith(("6","7")):continue
            row=actual.get(code,{"name":names.get(code,""),"balance":"0"})
            value=Decimal(row["balance"])*(1 if code.startswith("6") else -1)
            plan=planned.get(code,Decimal(0))
            rows.append({"code":code,"name":row["name"],"section":"Charges" if code.startswith("6") else "Produits","actual":str(value),"budget":str(plan),"variance":str(value-plan),
                         'previous_actual':str(previous_actual.get(code,Decimal(0))) if previous_year else None,
                         'previous_budget':str(previous_budget[code]) if code in previous_budget else None,
                         'variance_note':notes.get(code,'')})
        charges=sum(Decimal(r["actual"]) for r in rows if r["section"]=="Charges")
        products=sum(Decimal(r["actual"]) for r in rows if r["section"]=="Produits")
        totals={"charges":str(charges),"products":str(products),"result":str(products-charges)}
    elif kind=="sheet":
        # A balance sheet is an instant at end date, including earlier movements.
        start=year.starts_on
        all_rows=query.filter(entry__date__lte=end).values("account__code","account__name").annotate(debit=Sum("debit"),credit=Sum("credit")).order_by("account__code")
        result=Decimal(0);assets=Decimal(0);liabilities=Decimal(0)
        for r in all_rows:
            value=r["debit"]-r["credit"];code=r["account__code"]
            if code.startswith(("6","7")):result-=value;continue
            if not code.startswith(tuple("12345")):continue
            if value==0:continue
            section="Actif" if value>0 else "Passif"
            if value>0:assets+=value
            else:liabilities-=value
            rows.append({"code":code,"name":r["account__name"],"section":section,"amount":str(abs(value))})
        rows.append({"code":"RESULTAT","name":"Résultat de la période","section":"Passif","amount":str(result)})
        totals={"assets":str(assets),"liabilities":str(liabilities+result),"result":str(result),"difference":str(assets-liabilities-result)}
    else:raise ValueError("Rapport inconnu.")
    return {"kind":kind,"year":year.name,"start":str(start),"end":str(end),"rows":rows,"totals":totals,'previous_year':previous_year.name if previous_year else None}
