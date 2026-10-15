import hashlib
from pathlib import Path
from django.db import transaction
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from core.access import member_required, is_manager
from core.views import manager_required, payload
from finance.models import AuditEvent
from finance.views import errors
from .models import Folder, Document, Version

MAX_SIZE = 10 * 1024 * 1024


def visible(request):
    query = Document.objects.select_related("folder", "current")
    if not is_manager(request.user):
        query = query.filter(published=True, archived=False, current__isnull=False)
    return query


def serialize(document, manager=False):
    version = document.current
    return {"id":document.pk, "title":document.title,"folder":document.folder_id,
        "folder_name":document.folder.name if document.folder else "Sans dossier",
        "published":document.published, "archived":document.archived,
        "filename":version.filename if version else "", "size":version.size if version else 0,
        "updated_at":version.created_at if version else None,
        "versions":[{"id":v.pk,"filename":v.filename,"size":v.size,"created_at":v.created_at,"author":v.created_by.username} for v in document.versions.all()] if manager else []}


def validate_upload(file):
    if not file or file.size <= 0 or file.size > MAX_SIZE:
        raise ValueError("Choisissez un fichier non vide de 10 Mo maximum.")
    filename = Path(file.name.replace("\\", "/")).name
    if len(filename) > 200:raise ValueError("Le nom du fichier est trop long.")
    head = file.read(16); file.seek(0)
    allowed = {".pdf":("application/pdf",lambda h:h.startswith(b"%PDF-")),
        ".png":("image/png",lambda h:h.startswith(b"\x89PNG\r\n\x1a\n")),
        ".jpg":("image/jpeg",lambda h:h.startswith(b"\xff\xd8\xff")),
        ".jpeg":("image/jpeg",lambda h:h.startswith(b"\xff\xd8\xff"))}
    rule = allowed.get(Path(filename).suffix.lower())
    if not rule or not rule[1](head):raise ValueError("Formats acceptés : PDF, PNG et JPEG. Le contenu doit correspondre au format annoncé.")
    digest = hashlib.sha256()
    for chunk in file.chunks():digest.update(chunk)
    file.seek(0)
    return filename,rule[0],digest.hexdigest()


def add_version(document, file, info, user):
    filename, mime, checksum = info
    version = Version(document=document,filename=filename,size=file.size,content_type=mime,checksum=checksum,created_by=user)
    version.file.save(filename, file, save=False)
    try:
        version.save()
        document.current=version;document.save(update_fields=["current"])
        AuditEvent.objects.create(actor=user,action="document.upload",target=str(document.pk))
    except Exception:
        version.file.delete(save=False)
        raise
    return version


@require_http_methods(["GET", "POST", "PATCH"])
@member_required
@errors
def folders(request, pk=None):
    if request.method == "GET":
        query=Folder.objects.all()
        if not is_manager(request.user):query=query.filter(document__in=visible(request)).distinct()
        return JsonResponse({"items":list(query.values("id","name"))})
    data=payload(request); name=str(data.get("name", "")).strip()
    if not name or len(name)>150:raise ValueError("Nom de dossier requis (150 caractères maximum).")
    with transaction.atomic():
        folder=Folder.objects.select_for_update().get(pk=pk) if pk else Folder()
        folder.name=name;folder.full_clean();folder.save()
        AuditEvent.objects.create(actor=request.user,action="folder.save",target=str(folder.pk))
    return JsonResponse({"id":folder.pk,"name":folder.name},status=200 if pk else 201)


@require_http_methods(["GET", "POST"])
@member_required
@errors
def items(request):
    if request.method == "GET":
        query=visible(request)
        if is_manager(request.user) and request.GET.get("archived")!="1":query=query.filter(archived=False)
        if request.GET.get("folder"):query=query.filter(folder_id=int(request.GET["folder"]))
        if is_manager(request.user):query=query.prefetch_related("versions__created_by")
        return JsonResponse({"items":[serialize(doc,is_manager(request.user)) for doc in query]})
    title=str(request.POST.get("title", "")).strip()
    if not title or len(title)>150:raise ValueError("Titre requis (150 caractères maximum).")
    file=request.FILES.get("file");info=validate_upload(file)
    folder=Folder.objects.get(pk=request.POST["folder"]) if request.POST.get("folder") else None
    shared=request.POST.get("published", "false")
    if shared not in ["true", "false"]:raise ValueError("Choix de partage invalide.")
    with transaction.atomic():
        doc=Document.objects.create(title=title,folder=folder,published=shared=="true")
        add_version(doc,file,info,request.user)
    return JsonResponse({"id":doc.pk},status=201)


@require_http_methods(["PATCH"])
@manager_required
@errors
def item(request, pk):
    data=payload(request)
    if set(data)-{"title", "folder", "published", "archived"}:raise ValueError("Champ inconnu.")
    with transaction.atomic():
        doc=Document.objects.select_for_update().get(pk=pk)
        for field in ["published", "archived"]:
            if field in data:
                if not isinstance(data[field],bool):raise ValueError("Choix de partage ou archivage invalide.")
                setattr(doc,field,data[field])
        if "title" in data:doc.title=str(data["title"]).strip()
        if "folder" in data:doc.folder=Folder.objects.get(pk=data["folder"]) if data["folder"] else None
        doc.full_clean();doc.save()
        AuditEvent.objects.create(actor=request.user,action="document.update",target=str(doc.pk))
    return JsonResponse({"ok":True})


@require_http_methods(["POST"])
@manager_required
@errors
def upload(request, pk):
    file=request.FILES.get("file");info=validate_upload(file)
    with transaction.atomic():
        doc=Document.objects.select_for_update().get(pk=pk)
        if doc.archived:raise ValueError("Restaurez ce document avant d’ajouter une version.")
        add_version(doc,file,info,request.user)
    return JsonResponse({"ok":True},status=201)


@require_http_methods(["GET"])
@member_required
def download(request, pk=None, version=None):
    if version is not None:
        if not is_manager(request.user):raise Http404()
        item=get_object_or_404(Version,pk=version)
    else:
        doc=get_object_or_404(visible(request),pk=pk)
        if not doc.current_id:raise Http404()
        item=doc.current
    try:stream=item.file.open("rb")
    except FileNotFoundError:raise Http404()
    response=FileResponse(stream,as_attachment=True,filename=item.filename,content_type=item.content_type)
    response["X-Content-Type-Options"]="nosniff"
    return response
