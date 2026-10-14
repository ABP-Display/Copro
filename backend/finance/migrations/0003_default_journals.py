from django.db import migrations

def seed(apps,schema_editor):
    Journal=apps.get_model("finance","Journal")
    for code,name in [("OD","Opérations diverses"),("BQ","Banque"),("AC","Achats"),("AP","Appels de fonds")]:
        Journal.objects.get_or_create(code=code,defaults={"name":name,"is_default":code=="OD"})

class Migration(migrations.Migration):
    dependencies=[("finance","0002_costcenter_entrytemplate_organization_account_active_and_more")]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
