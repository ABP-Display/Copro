import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
from django.utils import timezone

from core.models import Owner
from documents.models import Document
from finance.models import AuditEvent, Entry
from .models import Supplier, Contract, SupplierCertificate, Notice, Case, Quote


class PartnersTests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user('manager', is_staff=True)
        self.client.force_login(self.manager)
        self.supplier = Supplier.objects.create(name='Entreprise A', created_by=self.manager)
        self.member_user = get_user_model().objects.create_user('member')
        self.owner = Owner.objects.create(first_name='Alice', last_name='Test', email='alice@example.test', user=self.member_user)
        self.member = Client()
        self.member.force_login(self.member_user)

    def send(self, resource, data, method='post', client=None):
        return getattr(client or self.client, method)(f'/api/operations/{resource}/', json.dumps(data), content_type='application/json')

    def contract_payload(self, **values):
        return {'supplier': self.supplier.id, 'title': 'Entretien', 'starts_on': '2026-01-01', 'ends_on': '2026-12-31', **values}

    def test_supplier_directory_persists_and_validates_contacts(self):
        data = {'name': 'Entreprise B', 'siret': '12345678901234', 'email': 'contact@example.test', 'trade': 'Électricité'}
        response = self.send('suppliers', data)
        self.assertEqual(response.status_code, 201, response.content)
        pk = response.json()['id']
        self.assertEqual(self.send(f'suppliers/{pk}', {'phone': '0123456789'}, 'patch').status_code, 200)
        self.assertEqual(Supplier.objects.get(pk=pk).email, data['email'])
        for invalid in [{'siret': '123'}, {'email': 'invalide'}, {'archived': 'false'}, {'unknown': True}, {'phone': {'secret': 'no'}}]:
            self.assertEqual(self.send(f'suppliers/{pk}', invalid, 'patch').status_code, 400)
        self.assertTrue(AuditEvent.objects.filter(action='supplier.create', target=str(pk)).exists())

    def test_contract_defaults_notice_and_decimal_cost(self):
        response = self.send('contracts', self.contract_payload(notice_days=60, annual_cost='1200.25', tacit_renewal=True))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['notice_on'], '2026-11-01')
        self.assertEqual(response.json()['annual_cost'], '1200.25')
        minimal = self.send('contracts', self.contract_payload(ends_on=None))
        self.assertEqual(minimal.status_code, 201, minimal.content)
        self.assertIsNone(minimal.json()['notice_on'])
        self.assertIsNone(minimal.json()['annual_cost'])
        self.assertEqual(minimal.json()['status'], 'active')

    def test_contract_invalid_dates_cost_and_unknown_fields_roll_back(self):
        for invalid in [{'ends_on': '2025-12-31'}, {'notice_days': -1}, {'notice_days': 4000}, {'notice_days': 1.5},
                        {'annual_cost': '-1'}, {'annual_cost': '1.001'}, {'ends_on': None, 'tacit_renewal': True},
                        {'ends_on': None, 'notice_days': 10}, {'status': 'cancelled'}, {'documents': '1'}, {'reference': {'a': 1}}]:
            response = self.send('contracts', self.contract_payload(**invalid))
            self.assertEqual(response.status_code, 400, (invalid, response.content))
        self.assertEqual(Contract.objects.count(), 0)
        self.assertFalse(AuditEvent.objects.exists())

    def test_contract_partial_update_preserves_documents_and_historical_supplier(self):
        document = Document.objects.create(title='Contrat signé')
        response = self.send('contracts', self.contract_payload(documents=[document.id], tacit_renewal=True))
        self.assertEqual(response.status_code, 201, response.content)
        pk = response.json()['id']
        document.archived = True; document.save()
        self.supplier.archived = True; self.supplier.save()
        updated = self.send(f'contracts/{pk}', {'status': 'ended'}, 'patch')
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()['documents'], [document.id])
        self.assertTrue(updated.json()['tacit_renewal'])
        self.assertEqual(self.send('contracts', self.contract_payload()).status_code, 400)
        other = Supplier.objects.create(name='Entreprise active', created_by=self.manager)
        self.assertEqual(self.send('contracts', self.contract_payload(supplier=other.pk, documents=[document.pk])).status_code, 400)
        with self.assertRaises(ProtectedError):
            self.supplier.delete()

    def test_directory_quote_snapshots_name_and_supports_free_entry(self):
        case = Case.objects.create(kind='works', title='Toiture', created_by=self.manager)
        path = f'cases/{case.pk}/quotes'
        self.assertEqual(self.send(path, {'supplier_record': self.supplier.pk, 'amount': '1200'}).status_code, 201)
        quote = Quote.objects.get()
        self.supplier.name = 'Nouveau nom'; self.supplier.save()
        quote.refresh_from_db()
        self.assertEqual(quote.supplier, 'Entreprise A')
        self.assertEqual(quote.supplier_record_id, self.supplier.pk)
        self.assertEqual(self.send(path, {'supplier': 'Entreprise libre', 'amount': '1000'}).status_code, 201)
        self.supplier.archived = True; self.supplier.save()
        self.assertEqual(self.send(path, {'supplier_record': self.supplier.pk, 'amount': '1200'}).status_code, 400)
        self.assertEqual(self.send(path, {'amount': '1200'}).status_code, 400)
        self.assertEqual(Entry.objects.count(), 0)

    def test_contract_and_certificate_alerts_omit_ended_archived_and_far_future(self):
        today = timezone.localdate()
        for title, end, status, notice in [('Préavis proche', 80, 'active', 60), ('Fin proche', 2, 'active', 0), ('Expiré', -1, 'active', 0), ('Lointain', 100, 'active', 0),
                                           ('Terminé', 2, 'ended', 0), ('Archivé', -1, 'archived', 0)]:
            Contract.objects.create(supplier=self.supplier, title=title, starts_on=today-timedelta(days=365), ends_on=today+timedelta(days=end),
                                    notice_days=notice, status=status, created_by=self.manager)
        for title, days, archived in [('Assurance proche', 15, False), ('Ancienne assurance', -10, True), ('Assurance lointaine', 90, False)]:
            SupplierCertificate.objects.create(supplier=self.supplier, kind='insurance', title=title, valid_until=today+timedelta(days=days), archived=archived, created_by=self.manager)
        data = self.client.get('/api/operations/metrics/').json()
        titles = ' '.join(item['title'] for item in data['alerts'])
        for title in ['Préavis proche', 'Fin proche', 'Expiré', 'Assurance proche']: self.assertIn(title, titles)
        self.assertIn('Contrat bientôt à échéance : Fin proche', titles)
        for title in ['Lointain', 'Terminé', 'Archivé', 'Ancienne assurance', 'Assurance lointaine']: self.assertNotIn(title, titles)
        self.assertTrue(any(a['section'] == 'certificates' for a in data['alerts']))
        self.assertEqual(Entry.objects.count(), 0)

    def test_certificates_preserve_archived_document_and_support_archive_restore(self):
        doc = Document.objects.create(title='Attestation')
        response = self.send('certificates', {'supplier': self.supplier.pk, 'kind': 'insurance', 'title': 'Assurance', 'valid_until': '2027-01-01', 'document': doc.pk})
        self.assertEqual(response.status_code, 201, response.content)
        pk = response.json()['id']
        doc.archived = True; doc.save()
        response = self.send(f'certificates/{pk}', {'archived': True}, 'patch')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['document'], doc.pk)
        self.assertEqual(self.send(f'certificates/{pk}', {'archived': False}, 'patch').status_code, 200)
        self.assertEqual(self.send('certificates', {'supplier': self.supplier.pk, 'kind': 'wrong', 'title': 'A', 'valid_until': 'bad'}).status_code, 400)

    def test_supplier_costs_only_active_contracts_and_unknown_cost_is_explicit(self):
        for cost, status in [('100.25', 'active'), (None, 'active'), ('999', 'ended')]:
            Contract.objects.create(supplier=self.supplier, title='C', starts_on=date(2026, 1, 1), annual_cost=cost, status=status, created_by=self.manager)
        data = self.client.get('/api/operations/suppliers/').json()['items'][0]
        self.assertEqual(data['annual_cost'], '100.25')
        self.assertEqual(data['unknown_costs'], 1)
        self.assertEqual(data['active_contracts'], 2)

    def test_contract_csv_neutralizes_formulas_and_preserves_zero(self):
        self.send('contracts', self.contract_payload(title='=HYPERLINK("x")', annual_cost='0'))
        response = self.client.get('/api/operations/contracts/?format=csv')
        self.assertEqual(response.status_code, 200)
        text = response.content.decode('utf-8-sig')
        self.assertIn("'=HYPERLINK", text)
        self.assertIn(';0.00;', text)
        self.assertEqual(self.member.get('/api/operations/contracts/?format=csv').status_code, 403)

    def test_notices_only_explicit_publication_is_shared_and_member_cannot_write(self):
        response = self.send('notices', {'title': 'Travaux', 'text': 'Informations aux voisins'})
        self.assertEqual(response.status_code, 201, response.content)
        pk = response.json()['id']
        self.assertEqual(self.member.get('/api/operations/notices/?status=draft').json()['items'], [])
        self.assertEqual(self.send(f'notices/{pk}', {'status': 'published'}, 'patch').status_code, 200)
        shared = self.member.get('/api/operations/notices/').json()['items']
        self.assertEqual(len(shared), 1)
        self.assertIsNotNone(shared[0]['published_at'])
        self.assertEqual(self.send(f'notices/{pk}', {'text': 'Modifié'}, 'patch').status_code, 400)
        self.assertEqual(self.send('notices', {'title': 'Interdit', 'text': 'No'}, client=self.member).status_code, 403)
        self.assertEqual(self.send(f'notices/{pk}', {'status': 'draft'}, 'patch', self.member).status_code, 403)
        self.assertEqual(self.send(f'notices/{pk}', {'status': 'draft'}, 'patch').status_code, 200)
        self.assertEqual(self.member.get('/api/operations/notices/').json()['items'], [])
        self.assertEqual(self.send(f'notices/{pk}', {'text': 'Texte relu'}, 'patch').status_code, 200)
        self.assertTrue(AuditEvent.objects.filter(action='notice.published').exists())

    def test_notice_archive_restore_requires_publication_again(self):
        pk = self.send('notices', {'title': 'Titre', 'text': 'Texte'}).json()['id']
        self.assertEqual(self.send(f'notices/{pk}', {'status': 'archived'}, 'patch').status_code, 200)
        self.assertEqual(self.send(f'notices/{pk}', {'status': 'published'}, 'patch').status_code, 400)
        self.assertEqual(self.send(f'notices/{pk}', {'status': 'draft'}, 'patch').status_code, 200)
        self.assertEqual(self.member.get('/api/operations/notices/').json()['items'], [])
        self.assertEqual(self.send('notices', {'title': 'Titre', 'text': ' ', 'status': 'published'}).status_code, 400)

    def test_private_endpoints_anonymous_password_gate_missing_and_csrf(self):
        for resource in ['suppliers', 'contracts', 'certificates', 'notices']:
            self.assertEqual(Client().get(f'/api/operations/{resource}/').status_code, 401)
        for resource in ['suppliers', 'contracts', 'certificates']:
            self.assertEqual(self.member.get(f'/api/operations/{resource}/').status_code, 403)
        self.owner.must_change_password = True; self.owner.save()
        self.assertEqual(self.member.get('/api/operations/notices/').status_code, 403)
        self.assertEqual(self.send('contracts/99999', {'status': 'ended'}, 'patch').status_code, 404)
        protected = Client(enforce_csrf_checks=True); protected.force_login(self.manager)
        self.assertEqual(self.send('suppliers', {'name': 'No'}, client=protected).status_code, 403)
