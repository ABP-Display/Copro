import csv
import io
from datetime import date
from functools import wraps
from decimal import Decimal
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Exists, OuterRef
from django.views.decorators.http import require_http_methods
from core.access import member_required
from core.views import payload
from core.models import Owner, Lot
from .models import FiscalYear, Account, Entry, Line, ChargeKey, Share, FundCall, Expense, Receipt, PublishedReport, CostCenter
from .forms import YearForm, KeyForm, CallForm, ExpenseForm
from .services import amount, open_year, post_entry, publish_call, balance, public_summary, distribute, key_weights, pay_expense, bank_for_posting
from .idempotency import idempotent


def errors(view):
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if request.method != "GET" and not request.user.is_staff:
            return JsonResponse({"error":"Accès en lecture uniquement."},status=403)
        try:
            return view(request,*args,**kwargs)
        except ObjectDoesNotExist:
            return JsonResponse({"error":"Élément introuvable."},status=404)
        except (ValueError,TypeError,KeyError,ValidationError) as error:
            return JsonResponse({"error":str(error)},status=400)
        except IntegrityError:
            return JsonResponse({"error":"Conflit : cette référence existe déjà ou des données ont changé."},status=409)
    return wrapped


def form_value(form_class,data):
    if any(isinstance(v,(list,dict)) for v in data.values()):
        raise ValueError("Les champs du formulaire doivent être simples.")
    form=form_class(data)
    if not form.is_valid():
        raise ValueError(" · ".join(f"{key} : {' '.join(value)}" for key,value in form.errors.items()))
    return form


def call_data(item):
    return {"id":item.pk,"label":item.label,"year":item.year_id,"key":item.key_id,"key_name":item.key.name,'kind':item.kind,'project':item.project_id,'decision':item.decision,
            "date":str(item.date),"due_date":str(item.due_date),"amount":str(item.amount),"posted":bool(item.entry_id),'cancelled':bool(item.entry_id and Entry.objects.filter(reversal_of_id=item.entry_id).exists())}


def expense_data(item):
    payments=[p for p in item.payments.all() if not Entry.objects.filter(reversal_of=p.entry_id).exists()]
    paid=sum((p.amount for p in payments), Decimal("0"))
    cancelled=Entry.objects.filter(reversal_of_id=item.entry_id).exists()
    return {"id":item.pk,"year":item.year_id,"key":item.key_id,"supplier":item.supplier,"reference":item.reference,'cancelled':cancelled,
        "supplier_record":item.supplier_record_id,"document":item.document_id,'project':item.project_id,
        "label":item.label,"date":item.date,"amount":str(item.amount),"paid":paid==item.amount,
        "amount_paid":str(paid),"remaining":str(0 if cancelled else item.amount-paid),
        "payments":[{"id":p.pk,"date":str(p.entry.date),"amount":str(p.amount),"number":p.entry.number,"bank":p.bank_id,"bank_name":p.bank.name if p.bank else "Banque historique"} for p in payments]}


@require_http_methods(["GET","POST"])
@member_required
@errors
@idempotent
def collection(request,resource):
    if request.method=="GET":
        if resource=="years":
            return JsonResponse({"items":list(FiscalYear.objects.values("id","name","starts_on","ends_on","closed"))})
        if resource=="keys":
            return JsonResponse({"items":[{"id":k.pk,"name":k.name,"general":k.general,"annual_budget":str(k.annual_budget),"shares": [{"lot":s.lot_id,"value":str(s.value)} for s in k.shares.all()] if request.user.is_staff else []} for k in ChargeKey.objects.prefetch_related("shares")]})
        if resource=="calls":
            calls=FundCall.objects.select_related("key")
            if not request.user.is_staff: calls=calls.filter(entry__isnull=False)
            return JsonResponse({"items":[call_data(item) for item in calls]})
        if resource=="reports":
            return JsonResponse({"items":[{"id":r.pk,"title":r.title,"year":r.year_id,"published_at":r.published_at,"data":r.data} for r in PublishedReport.objects.all()]})
        if resource=="treasury":
            return JsonResponse({"items":[{"id":y.pk,**public_summary(y)} for y in FiscalYear.objects.all()]})
        if not request.user.is_staff:
            return JsonResponse({"error":"Ces données comptables détaillées sont privées."},status=403)
        if resource=="accounts":
            return JsonResponse({"items":list(Account.objects.filter(active=True).values("id","code","name"))})
        if resource=="entries":
            query=Entry.objects.select_related("year").prefetch_related("lines__account","lines__owner","lines__supplier").annotate(has_reversal=Exists(Entry.objects.filter(reversal_of_id=OuterRef("pk"))))
            if request.GET.get("year"): query=query.filter(year_id=int(request.GET["year"]))
            return JsonResponse({"items":[{"id":e.pk,"year":e.year_id,"number":e.number,"date":e.date,"journal":e.journal,"label":e.label,"reference":e.reference,
                "cost_center":e.cost_center_id,"reversed":e.has_reversal,"lines":[{"code":l.account.code,"debit":str(l.debit),"credit":str(l.credit),"owner":l.owner_id,"supplier":l.supplier_id} for l in e.lines.all()]} for e in query]})
        if resource=="expenses":
            return JsonResponse({"items":[expense_data(e) for e in Expense.objects.prefetch_related("payments__entry", "payments__bank")]})
        if resource=="balance":
            year=FiscalYear.objects.get(pk=int(request.GET["year"]))
            rows=balance(year)
            if request.GET.get("format")=="csv":
                stream=io.StringIO(); writer=csv.writer(stream,delimiter=";")
                writer.writerow(["Compte","Libellé","Débit","Crédit","Solde"])
                for row in rows: writer.writerow([row["code"],safe_csv(row["name"]),row["debit"],row["credit"],row["balance"]])
                response=HttpResponse("\ufeff"+stream.getvalue(),content_type="text/csv; charset=utf-8")
                response["Content-Disposition"]='attachment; filename="balance.csv"'; return response
            return JsonResponse({"items":rows})
        return JsonResponse({"error":"Ressource inconnue."},status=404)

    data=payload(request)
    with transaction.atomic():
        center=CostCenter.objects.get(pk=data["cost_center"]) if data.get("cost_center") else None
        if resource=="years":
            # Lock the chart singleton to serialize overlapping year creation.
            Account.objects.get_or_create(code="512",defaults={"name":"Banque"})
            Account.objects.select_for_update().get(code="512")
            item=form_value(YearForm,data).save()
        elif resource=="keys": item=form_value(KeyForm,data).save()
        elif resource=="calls":
            form=form_value(CallForm,{'kind':'current',**data}); candidate=form.instance
            open_year(candidate.year_id,candidate.date); item=form.save()
        elif resource=="expenses":
            form=form_value(ExpenseForm,data); item=form.instance
            year=open_year(item.year_id,item.date)
            code=str(data.get('charge_code') or ('671' if item.project_id else '601'))
            if not code.startswith('6') or code.startswith('67') != bool(item.project_id):raise ValueError('Choisissez un compte courant 6 ou de travaux 67 avec son opération.')
            item.entry=post_entry(year,item.date,"AC",item.label,[{"code":code,"debit":item.amount,'key':item.key,'project':item.project},{"code":"401","credit":item.amount,"supplier":item.supplier_record,'due_date':item.due_date or item.date}],request.user,item.reference,cost_center=center)
            item.save()
        elif resource=="receipts":
            owner=Owner.objects.get(pk=data["owner"]); value=amount(data["amount"]); day=date.fromisoformat(data["date"])
            year=open_year(data["year"],day)
            reference=str(data.get("reference",""))
            if len(reference)>100: raise ValueError("Référence trop longue.")
            bank=bank_for_posting(data.get('bank'))
            entry=post_entry(year,day,"BQ","Règlement copropriétaire",[{"code":bank.account.code if bank else "512","debit":value},{"code":"450","credit":value,"owner":owner}],request.user,reference,cost_center=center)
            item=Receipt.objects.create(owner=owner,amount=value,entry=entry,bank=bank)
        elif resource=="entries":
            day=date.fromisoformat(data["date"]); year=open_year(data["year"],day)
            label=str(data["label"]).strip(); journal=str(data.get("journal","OD"))
            if not label or len(label)>250 or len(journal)>10: raise ValueError("Libellé ou journal invalide.")
            raw=data["lines"]
            if not isinstance(raw,list) or len(raw)>100: raise ValueError("Liste de lignes invalide (100 maximum).")
            rows=[]
            for row in raw:
                if not isinstance(row,dict): raise ValueError("Ligne invalide.")
                from operations.models import Supplier
                supplier=Supplier.objects.get(pk=row['supplier']) if row.get('supplier') else None
                if supplier and supplier.archived: raise ValueError('Fournisseur archivé.')
                from .models import FinanceProject
                rows.append({**row,"owner":Owner.objects.get(pk=row["owner"]) if row.get("owner") else None,'supplier':supplier,
                    'key':ChargeKey.objects.get(pk=row['key']) if row.get('key') else None,
                    'project':FinanceProject.objects.get(pk=row['project']) if row.get('project') else None,
                    'lot':Lot.objects.get(pk=row['lot']) if row.get('lot') else None})
            item=post_entry(year,day,journal,label,rows,request.user,cost_center=center)
        elif resource=="accounts":
            from .advanced import AccountForm
            item=form_value(AccountForm,{**data,"active":True}).save()
        elif resource=="reports":
            year=FiscalYear.objects.select_for_update().get(pk=data["year"])
            title=str(data.get("title",year.name)).strip()
            if not title or len(title)>150: raise ValueError("Titre invalide.")
            item=PublishedReport.objects.create(year=year,title=title,data=public_summary(year),published_by=request.user)
        else: return JsonResponse({"error":"Ressource inconnue."},status=404)
    return JsonResponse({"id":item.pk},status=201)


def safe_csv(value):
    return "'"+value if str(value).lstrip().startswith(("=","+","-","@")) else value


@require_http_methods(["POST","PUT"])
@member_required
@errors
@idempotent
def action(request,resource,pk,operation):
    data=payload(request)
    with transaction.atomic():
        if resource=="calls" and operation in ["preview","publish"]:
            call=FundCall.objects.select_for_update().select_related("key").get(pk=pk)
            if operation=="preview":
                rows=distribute(call.amount,key_weights(call.key,call.due_date))
                return JsonResponse({"items":[{"lot":lot.number,"owner":str(lot.owner),"shares":str(weight),"amount":str(value)} for lot,weight,value in rows]})
            publish_call(call,request.user)
        elif resource=="keys" and operation=="shares":
            key=ChargeKey.objects.select_for_update().get(pk=pk)
            if key.general: raise ValueError("Cette clé utilise les tantièmes généraux des lots.")
            raw=data.get("shares")
            if not isinstance(raw,list): raise ValueError("Une liste de tantièmes est attendue.")
            ids=[]; rows=[]
            for row in raw:
                if not isinstance(row,dict): raise ValueError("Tantième invalide.")
                lot=Lot.objects.get(pk=row["lot"])
                if lot.pk in ids: raise ValueError("Un lot ne peut être présent deux fois.")
                ids.append(lot.pk); rows.append(Share(key=key,lot=lot,value=amount(row["value"],False)))
            key.shares.all().delete(); Share.objects.bulk_create(rows)
        elif resource=="expenses" and operation=="pay":
            expense=Expense.objects.select_for_update().select_related("entry").get(pk=pk)
            pay_expense(expense,date.fromisoformat(data["date"]),data.get("amount"),request.user,data.get('bank'),data.get('year'))
        elif resource=="years" and operation=="close":
            raise ValueError('Utilisez Comptabilité → Exercice & clôture : régularisation, rapprochement et reports sont désormais contrôlés ensemble.')
        else: return JsonResponse({"error":"Action inconnue."},status=404)
    return JsonResponse({"ok":True})
