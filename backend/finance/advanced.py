import csv
import io
from datetime import date
from decimal import Decimal
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from core.views import manager_required, payload
from core.access import user_data
from .models import Organization, Journal, CostCenter, Budget, EntryTemplate, AuditEvent, Account, FiscalYear, Entry, FundCall, Expense, ExpensePayment, Receipt, BankAccount, BankTransfer
from .services import amount, post_entry, open_year, CHART
from .views import errors, safe_csv
from .reporting import report


class OrganizationForm(forms.ModelForm):
    class Meta:
        model=Organization;fields=["name","address","email","phone","registration","code_length","analytic_required","report_prefix","default_today"]
    def clean_code_length(self):
        value=self.cleaned_data["code_length"]
        if not 3<=value<=20:raise forms.ValidationError("Choisir entre 3 et 20 caractères.")
        return value
    def clean_report_prefix(self):
        value=self.cleaned_data["report_prefix"]
        if value and not value.isdigit():raise forms.ValidationError("Un préfixe numérique est attendu.")
        return value

class AccountForm(forms.ModelForm):
    class Meta:
        model=Account;fields=["code","name","active"]
    def clean_code(self):
        value=self.cleaned_data["code"]
        config,_=Organization.objects.get_or_create(pk=1)
        if not value.isdigit() or len(value)<config.code_length:raise forms.ValidationError("Code numérique trop court pour la configuration.")
        if self.instance.pk and self.instance.code!=value and self.instance.line_set.exists():raise forms.ValidationError("Le code d’un compte utilisé ne peut plus être changé.")
        if self.instance.pk and self.instance.code!=value and BankAccount.objects.filter(account=self.instance).exists():raise forms.ValidationError('Ce compte est associé à une banque : conservez son code.')
        return value

class JournalForm(forms.ModelForm):
    class Meta:
        model=Journal;fields=["code","name","active"]
    def clean_code(self):
        value=self.cleaned_data["code"].upper()
        if not value.isalnum():raise forms.ValidationError("Code alphanumérique requis.")
        if self.instance.pk and self.instance.code!=value and (Entry.objects.filter(journal=self.instance.code).exists() or EntryTemplate.objects.filter(journal=self.instance.code).exists()):raise forms.ValidationError("Journal déjà utilisé : son code doit être conservé.")
        return value

class CostForm(forms.ModelForm):
    class Meta:
        model=CostCenter;fields=["name","active"]

class BudgetForm(forms.ModelForm):
    class Meta:
        model=Budget;fields=["year","account","cost_center","key","amount","variance_note"]
    def clean(self):
        data=super().clean()
        if (data.get("year") and data["year"].closed) or (self.instance.pk and self.instance.year.closed):raise forms.ValidationError("Exercice clôturé.")
        if data.get("account") and not data["account"].code.startswith(("6","7")):raise forms.ValidationError("Les budgets portent sur les comptes de charges ou produits.")
        if data.get("amount",0)<0:raise forms.ValidationError("Le budget doit être positif.")
        if data.get('year') and data.get('account'):
            others=Budget.objects.filter(year=data['year'],account=data['account'],cost_center=data.get('cost_center')).exclude(pk=self.instance.pk)
            if data.get('key') and others.filter(key__isnull=True).exists() or not data.get('key') and others.filter(key__isnull=False).exists():
                raise forms.ValidationError('Choisissez un budget global ou une ventilation par clés pour ce poste, sans les additionner.')
        return data


SPECS={"organization":(Organization,OrganizationForm),"accounts":(Account,AccountForm),"journals":(Journal,JournalForm),"centers":(CostCenter,CostForm),"budgets":(Budget,BudgetForm)}

def record(item):
    from django.forms.models import model_to_dict
    fields=SPECS[next(key for key,value in SPECS.items() if isinstance(item,value[0]))][1].Meta.fields
    value=model_to_dict(item,fields=fields);value["id"]=item.pk
    if isinstance(item,Journal):value["is_default"]=item.is_default
    for key,v in value.items():
        if isinstance(v,Decimal):value[key]=str(v)
    return value


@require_http_methods(["GET","POST","PATCH","DELETE"])
@manager_required
@errors
def manage(request,resource,pk=None):
    if resource=="users":return users(request,pk)
    if resource=="audit":
        if request.method!="GET":return JsonResponse({"error":"Historique en lecture seule."},status=405)
        return JsonResponse({"items":list(AuditEvent.objects.select_related("actor").values("id","action","target","created_at","actor__username")[:1000])})
    if resource=="templates":return templates(request,pk)
    if resource not in SPECS:return JsonResponse({"error":"Ressource inconnue."},status=404)
    model,form_class=SPECS[resource]
    if request.method=="GET":
        if resource=="organization":
            instance,_=Organization.objects.get_or_create(pk=1)
            return JsonResponse({"items":[record(instance)],"currency":"EUR","precision":2})
        return JsonResponse({"items":[record(item) for item in model.objects.all()]})
    with transaction.atomic():
        instance=None
        if resource=="organization":instance,_=Organization.objects.get_or_create(pk=1);instance=Organization.objects.select_for_update().get(pk=1)
        elif pk:instance=model.objects.select_for_update().get(pk=pk)
        if isinstance(instance,Budget) and instance.year.closed:raise ValueError('Le budget d’un exercice clôturé est figé.')
        if request.method=="DELETE":
            if not instance or resource=="organization":raise ValueError("Suppression impossible.")
            if isinstance(instance,Journal) and (instance.code in ["OD","BQ","AC","AP","AN"] or Entry.objects.filter(journal=instance.code).exists()):raise ValueError("Journal système ou déjà utilisé.")
            try:instance.delete()
            except ProtectedError:raise ValueError("Cet élément est encore utilisé : désactivez-le plutôt que le supprimer.")
            AuditEvent.objects.create(actor=request.user,action=resource+".delete",target=str(pk));return JsonResponse({"ok":True})
        if request.method=="PATCH" and not instance:raise ValueError("Élément à modifier requis.")
        data=payload(request)
        if instance:
            initial=record(instance);initial.pop("id",None);data=initial|data
        if any(isinstance(v,(list,dict)) for v in data.values()):raise ValueError("Champs simples attendus.")
        if resource=="budgets":
            FiscalYear.objects.select_for_update().get(pk=data.get("year"))
        form=form_class(data,instance=instance)
        if not form.is_valid():raise ValueError(" · ".join(" ".join(value) for value in form.errors.values()))
        item=form.save()
        AuditEvent.objects.create(actor=request.user,action=resource+".save",target=str(item.pk))
    return JsonResponse(record(item),status=200 if instance else 201)


def users(request,pk):
    if not request.user.is_superuser:return JsonResponse({"error":"Réservé à l’administrateur principal."},status=403)
    User=get_user_model()
    if request.method=="GET":
        return JsonResponse({"items":[{"id":u.pk,"username":user_data(u)["username"],"email":u.email,"is_staff":u.is_staff,"is_superuser":u.is_superuser,"is_active":u.is_active,"last_login":u.last_login} for u in User.objects.select_related("owner_profile").order_by("username")]})
    if request.method!="PATCH" or pk is None:raise ValueError("Utilisez la modification d’un compte existant. Les comptes copropriétaires sont créés depuis l’annuaire.")
    data=payload(request)
    if set(data)-{"is_active","is_staff"}:raise ValueError("Seuls l’activation et le rôle gestionnaire sont modifiables ici.")
    if any(not isinstance(v,bool) for v in data.values()):raise ValueError("Valeurs booléennes attendues.")
    with transaction.atomic():
        list(User.objects.select_for_update().filter(is_superuser=True).order_by("id"))
        target=User.objects.select_for_update().get(pk=pk)
        if data.get("is_staff") is True:
            from council.models import Mandate
            from django.utils import timezone
            if Mandate.objects.filter(user=target, role="controller", revoked_at__isnull=True, ends_on__gte=timezone.localdate()).exists():
                raise ValueError("Terminez le mandat de contrôle indépendant avant d’accorder un accès permanent de gestion.")
        if target.is_superuser and (data.get("is_active") is False or data.get("is_staff") is False):raise ValueError("Le compte administrateur principal ne peut pas être désactivé ou rétrogradé ici.")
        if target.pk==request.user.pk:raise ValueError("Votre propre accès ne peut pas être modifié ici.")
        for key,value in data.items():setattr(target,key,value)
        target.save(update_fields=list(data))
        AuditEvent.objects.create(actor=request.user,action="user.update",target=str(target.pk))
    return JsonResponse({"ok":True})


def templates(request,pk):
    if request.method=="GET":return JsonResponse({"items":list(EntryTemplate.objects.values("id","name","journal","lines"))})
    with transaction.atomic():
        instance=EntryTemplate.objects.select_for_update().get(pk=pk) if pk else None
        if request.method=="DELETE":
            if not instance:raise ValueError("Modèle requis.")
            instance.delete();return JsonResponse({"ok":True})
        data=payload(request);name=str(data.get("name","")).strip();journal=str(data.get("journal","OD"));raw=data.get("lines")
        if not name or len(name)>150 or not Journal.objects.filter(code=journal,active=True).exists():raise ValueError("Nom et journal actif requis.")
        if not isinstance(raw,list) or not 2<=len(raw)<=100:raise ValueError("Le modèle doit contenir entre 2 et 100 lignes.")
        rows=[]
        for line in raw:
            if not isinstance(line,dict):raise ValueError("Ligne invalide.")
            code=str(line.get("code",""));debit=amount(line.get("debit") or 0,False);credit=amount(line.get("credit") or 0,False)
            if not Account.objects.filter(code=code,active=True).exists() or (debit>0)==(credit>0):raise ValueError("Compte actif et une seule colonne positive requis par ligne.")
            rows.append({"code":code,"debit":str(debit),"credit":str(credit)})
        if sum(Decimal(r["debit"]) for r in rows)!=sum(Decimal(r["credit"]) for r in rows):raise ValueError("Modèle déséquilibré.")
        item=instance or EntryTemplate();item.name=name;item.journal=journal;item.lines=rows;item.full_clean();item.save()
        AuditEvent.objects.create(actor=request.user,action="template.save",target=str(item.pk))
        return JsonResponse({"id":item.pk},status=200 if instance else 201)


@require_http_methods(["POST"])
@manager_required
@errors
def operations(request,resource,pk):
    data=payload(request)
    with transaction.atomic():
        if resource=="initialize-chart":
            from pathlib import Path
            import csv
            source=Path(__file__).parent/"data"/"init_french-avance.csv"
            count=0
            with source.open(encoding="utf-8-sig",newline="") as stream:
                for row in csv.DictReader(stream,delimiter=";"):
                    _,created=Account.objects.get_or_create(code=row["code"],defaults={"name":row["name"]})
                    count+=int(created)
            AuditEvent.objects.create(actor=request.user,action="chart.initialize",target=str(count))
            return JsonResponse({"created":count})
        elif resource=="default-journal":
            journal=Journal.objects.select_for_update().get(pk=pk)
            if not journal.active:raise ValueError("Le journal doit être actif.")
            Journal.objects.filter(is_default=True).update(is_default=False);journal.is_default=True;journal.save(update_fields=["is_default"])
        elif resource=="apply-template":
            template=EntryTemplate.objects.get(pk=pk);day=date.fromisoformat(data["date"]);year=open_year(data["year"],day)
            center=CostCenter.objects.get(pk=data["cost_center"]) if data.get("cost_center") else None
            entry=post_entry(year,day,template.journal,str(data.get("label") or template.name),template.lines,request.user,cost_center=center)
            return JsonResponse({"id":entry.pk},status=201)
        elif resource=="reverse-entry":
            original=Entry.objects.select_for_update().prefetch_related("lines__account","lines__owner","lines__supplier").get(pk=pk)
            if original.kind != 'normal':raise ValueError('Utilisez le parcours de correction dédié pour une écriture de reprise, report, régularisation ou clôture.')
            from .models import BankMatch, Settlement
            if BankMatch.objects.filter(line__entry=original).exists() or Settlement.objects.filter(active=True).filter(Q(debit_line__entry=original)|Q(credit_line__entry=original)).exists():raise ValueError('Annulez les rapprochements et lettrages avant la contrepassation.')
            if original.reversal_of_id or Entry.objects.filter(reversal_of=original).exists():raise ValueError("Cette écriture a déjà été contrepassée ou est elle-même une contrepassation.")
            if FundCall.objects.filter(entry=original).exists() or Expense.objects.filter(entry=original).exists() or Expense.objects.filter(payment_entry=original).exists() or ExpensePayment.objects.filter(entry=original).exists() or Receipt.objects.filter(entry=original).exists() or BankTransfer.objects.filter(entry=original).exists():raise ValueError("Cette écriture est liée à une opération métier. Sa correction nécessite un traitement métier dédié.")
            day=date.fromisoformat(data["date"]);year=open_year(original.year_id,day)
            lines=[{"code":l.account.code,"owner":l.owner,'supplier':l.supplier,'key':l.key,'project':l.project,'lot':l.lot,"debit":l.credit,"credit":l.debit} for l in original.lines.all()]
            entry=post_entry(year,day,original.journal,"Contrepassation : "+original.label[:230],lines,request.user,cost_center=original.cost_center,reversal_of=original)
            return JsonResponse({"id":entry.pk},status=201)
        else:raise ValueError("Action inconnue.")
        AuditEvent.objects.create(actor=request.user,action=resource,target=str(pk))
    return JsonResponse({"ok":True})


@require_http_methods(["GET"])
@manager_required
@errors
def reports(request,kind):
    year=FiscalYear.objects.get(pk=request.GET["year"])
    config,_=Organization.objects.get_or_create(pk=1)
    filters=request.GET.dict()
    if "prefix" not in filters:filters["prefix"]=config.report_prefix
    value=report(year,kind,filters)
    if request.GET.get("format")=="csv":
        stream=io.StringIO();writer=csv.writer(stream,delimiter=";")
        headings={"code":"Compte","name":"Libellé du compte","date":"Date","number":"Écriture","journal":"Journal","label":"Libellé","reference":"Référence","owner":"Copropriétaire","supplier":"Fournisseur","opening":"Solde avant mouvement","debit":"Débit","credit":"Crédit","balance":"Solde","section":"Rubrique","actual":"Réalisé","budget":"Budget annuel","variance":"Écart","amount":"Montant","previous_actual":"Réalisé exercice précédent (entier)","previous_budget":"Budget exercice précédent","variance_note":"Explication de l’écart"}
        keys=list(value["rows"][0]) if value["rows"] else ["code","name"]
        writer.writerow([headings.get(k,k) for k in keys])
        for row in value["rows"]:writer.writerow([safe_csv('' if row.get(k) is None else str(row[k])) for k in keys])
        response=HttpResponse("\ufeff"+stream.getvalue(),content_type="text/csv; charset=utf-8");response["Content-Disposition"]=f'attachment; filename="{kind}.csv"';return response
    return JsonResponse(value)
