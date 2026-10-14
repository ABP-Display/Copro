import json
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from core.models import Owner
from core.access import provision_access
from finance.models import AuditEvent
from .models import Document, Version, Folder


class DocumentTests(TestCase):
    def setUp(self):
        directory=TemporaryDirectory();self.addCleanup(directory.cleanup)
        settings=override_settings(MEDIA_ROOT=directory.name);settings.enable();self.addCleanup(settings.disable)
        self.manager=get_user_model().objects.create_user("manager",is_staff=True)
        self.client.force_login(self.manager)
        self.owner=Owner.objects.create(first_name="Alice",last_name="Test",email="alice@example.test")
        provision_access(self.owner);self.owner.must_change_password=False;self.owner.save()
        self.member=Client();self.member.force_login(self.owner.user)

    def pdf(self, name="document.pdf"):
        return SimpleUploadedFile(name,b"%PDF-1.4\nfixture for upload validation\n%%EOF",content_type="application/pdf")

    def upload(self, shared="false", folder=None):
        data={"title":"Compte rendu","file":self.pdf(),"published":shared}
        if folder:data["folder"]=folder.pk
        return self.client.post("/api/documents/items/",data)

    def patch(self, pk, data):
        return self.client.patch(f"/api/documents/items/{pk}/",json.dumps(data),content_type="application/json")

    def test_default_private_and_download_authorization(self):
        folder=Folder.objects.create(name="Privé")
        result=self.upload(folder=folder);self.assertEqual(result.status_code,201,result.content)
        pk=result.json()["id"]
        self.assertEqual(self.member.get("/api/documents/items/").json()["items"],[])
        self.assertEqual(self.member.get("/api/documents/folders/").json()["items"],[])
        self.assertEqual(self.member.get(f"/api/documents/items/{pk}/download/").status_code,404)
        self.assertEqual(Client().get(f"/api/documents/items/{pk}/download/").status_code,401)
        response=self.client.get(f"/api/documents/items/{pk}/download/")
        self.assertEqual(response.status_code,200)
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))
        self.assertEqual(b"".join(response.streaming_content),b"%PDF-1.4\nfixture for upload validation\n%%EOF")

    def test_publish_archive_restore_and_unpublish(self):
        pk=self.upload().json()["id"]
        self.assertEqual(self.patch(pk,{"published":True}).status_code,200)
        self.assertEqual(len(self.member.get("/api/documents/items/").json()["items"]),1)
        response=self.member.get(f"/api/documents/items/{pk}/download/");self.assertEqual(response.status_code,200);b"".join(response.streaming_content)
        self.assertEqual(self.patch(pk,{"archived":True}).status_code,200)
        self.assertEqual(self.member.get(f"/api/documents/items/{pk}/download/").status_code,404)
        self.assertEqual(self.client.get("/api/documents/items/").json()["items"],[])
        self.assertEqual(len(self.client.get("/api/documents/items/",{"archived":"1"}).json()["items"]),1)
        self.assertEqual(self.patch(pk,{"archived":False,"published":False}).status_code,200)
        self.assertEqual(self.member.get("/api/documents/items/").json()["items"],[])
        self.assertEqual(Version.objects.count(),1)

    def test_new_version_keeps_history_private(self):
        pk=self.upload(shared="true").json()["id"]
        first=Document.objects.get(pk=pk).current
        result=self.client.post(f"/api/documents/items/{pk}/upload/",{"file":self.pdf("version2.pdf")})
        self.assertEqual(result.status_code,201,result.content)
        self.assertEqual(Version.objects.count(),2)
        data=self.member.get("/api/documents/items/").json()["items"][0]
        self.assertEqual(data["filename"],"version2.pdf")
        self.assertEqual(data["versions"],[])
        self.assertEqual(self.member.get(f"/api/documents/versions/{first.pk}/download/").status_code,404)
        self.assertTrue(first.file.storage.exists(first.file.name))
        self.assertEqual(AuditEvent.objects.filter(action="document.upload").count(),2)

    def test_member_cannot_upload_edit_or_create_folders(self):
        pk=self.upload().json()["id"]
        self.assertEqual(self.member.post("/api/documents/items/",{"title":"Test","file":self.pdf()}).status_code,403)
        self.assertEqual(self.member.post(f"/api/documents/items/{pk}/upload/",{"file":self.pdf()}).status_code,403)
        self.assertEqual(self.member.patch(f"/api/documents/items/{pk}/",json.dumps({"published":True}),content_type="application/json").status_code,403)
        self.assertEqual(self.member.post("/api/documents/folders/",json.dumps({"name":"Test"}),content_type="application/json").status_code,403)
        self.assertEqual(Version.objects.count(),1)

    def test_file_validation_and_archived_upload_are_atomic(self):
        for name,content in [("bad.html",b"<html>"),("fake.pdf",b"<script>"),("empty.pdf",b"")]:
            result=self.client.post("/api/documents/items/",{"title":"Test","file":SimpleUploadedFile(name,content)})
            self.assertEqual(result.status_code,400)
        self.assertEqual(Document.objects.count(),0)
        pk=self.upload().json()["id"]
        self.patch(pk,{"archived":True})
        self.assertEqual(self.client.post(f"/api/documents/items/{pk}/upload/",{"file":self.pdf()}).status_code,400)
        self.assertEqual(Version.objects.count(),1)

    def test_folders_rename_and_move_document(self):
        response=self.client.post("/api/documents/folders/",json.dumps({"name":"Contrats"}),content_type="application/json")
        self.assertEqual(response.status_code,201)
        folder_id=response.json()["id"]
        pk=self.upload().json()["id"]
        self.assertEqual(self.patch(pk,{"folder":folder_id,"title":"Contrat entretien"}).status_code,200)
        response=self.client.patch(f"/api/documents/folders/{folder_id}/",json.dumps({"name":"Contrats actifs"}),content_type="application/json")
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.client.get("/api/documents/items/").json()["items"][0]["folder_name"],"Contrats actifs")
