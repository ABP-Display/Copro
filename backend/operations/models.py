from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import timedelta


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    trade = models.CharField(max_length=100, blank=True)
    siret = models.CharField(max_length=14, blank=True)
    contact = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(max_length=1000, blank=True)
    notes = models.TextField(max_length=5000, blank=True)
    archived = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['name', 'id']


class Contract(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='contracts')
    title = models.CharField(max_length=150)
    reference = models.CharField(max_length=100, blank=True)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    notice_days = models.PositiveSmallIntegerField(default=0)
    tacit_renewal = models.BooleanField(default=False)
    annual_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                     validators=[MinValueValidator(Decimal('0'))])
    status = models.CharField(max_length=15, choices=[('active', 'Actif'), ('ended', 'Terminé'), ('archived', 'Archivé')], default='active')
    notes = models.TextField(max_length=5000, blank=True)
    documents = models.ManyToManyField('documents.Document', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['ends_on', 'id']
        constraints = [
            models.CheckConstraint(condition=models.Q(ends_on__isnull=True) | models.Q(ends_on__gte=models.F('starts_on')), name='contract_dates_valid'),
            models.CheckConstraint(condition=models.Q(annual_cost__isnull=True) | models.Q(annual_cost__gte=0), name='contract_cost_nonnegative'),
            models.CheckConstraint(condition=models.Q(notice_days__lte=3650), name='contract_notice_bounded'),
        ]

    @property
    def notice_on(self):
        return self.ends_on - timedelta(days=self.notice_days) if self.ends_on else None


class SupplierCertificate(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='certificates')
    kind = models.CharField(max_length=20, choices=[('insurance', 'Assurance'), ('urssaf', 'Attestation URSSAF'), ('kbis', 'Extrait Kbis'), ('other', 'Autre')])
    title = models.CharField(max_length=150)
    valid_until = models.DateField()
    document = models.ForeignKey('documents.Document', null=True, blank=True, on_delete=models.PROTECT)
    archived = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['valid_until', 'id']


class Notice(models.Model):
    title = models.CharField(max_length=150)
    text = models.TextField(max_length=10000)
    status = models.CharField(max_length=15, choices=[('draft', 'Brouillon'), ('published', 'Publié'), ('archived', 'Archivé')], default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-created_at', '-id']


class Case(models.Model):
    kind=models.CharField(max_length=15,choices=[('works','Travaux'),('incident','Sinistre'),('obligation','Échéance')])
    title=models.CharField(max_length=150)
    description=models.TextField(blank=True,max_length=5000)
    due_date=models.DateField(null=True,blank=True)
    status=models.CharField(max_length=15,choices=[('open','En cours'),('done','Terminé'),('archived','Archivé')],default='open')
    budget=models.DecimalField(max_digits=12,decimal_places=2,default=0,validators=[MinValueValidator(Decimal('0'))])
    source_url=models.URLField(blank=True,max_length=500)
    resolution=models.ForeignKey('governance.Resolution',null=True,blank=True,on_delete=models.PROTECT)
    documents=models.ManyToManyField('documents.Document',blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        ordering=['due_date','id']
        constraints=[models.CheckConstraint(condition=models.Q(budget__gte=0),name='case_budget_nonnegative')]


class Quote(models.Model):
    case=models.ForeignKey(Case,on_delete=models.PROTECT,related_name='quotes')
    supplier=models.CharField(max_length=150)
    supplier_record=models.ForeignKey(Supplier,null=True,blank=True,on_delete=models.PROTECT,related_name='quotes')
    amount=models.DecimalField(max_digits=12,decimal_places=2,validators=[MinValueValidator(Decimal('0.01'))])
    notes=models.TextField(blank=True,max_length=2000)
    document=models.ForeignKey('documents.Document',null=True,blank=True,on_delete=models.PROTECT)
    selected_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.PROTECT)
    selected_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        ordering=['amount','id']
        constraints=[models.CheckConstraint(condition=models.Q(amount__gt=0),name='quote_amount_positive')]


class Reminder(models.Model):
    owner=models.ForeignKey('core.Owner',on_delete=models.PROTECT)
    balance=models.DecimalField(max_digits=14,decimal_places=2)
    text=models.TextField(max_length=10000)
    evidence=models.JSONField()
    status=models.CharField(max_length=15,default='draft',choices=[('draft','À relire'),('approved','Validé'),('sent','Envoi déclaré'),('cancelled','Annulé')])
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    validated_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    created_at=models.DateTimeField(auto_now_add=True)
    validated_at=models.DateTimeField(null=True)
    class Meta:
        ordering=['-id']
        constraints=[models.UniqueConstraint(fields=['owner'],condition=models.Q(status__in=['draft','approved']),name='one_active_reminder_per_owner')]
