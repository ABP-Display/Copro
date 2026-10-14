from django.db import migrations

def migrate_metadata(apps, schema_editor):
    Expense=apps.get_model('finance','Expense')
    FundCall=apps.get_model('finance','FundCall')
    Line=apps.get_model('finance','Line')
    for expense in Expense.objects.all().iterator():
        Line.objects.filter(entry_id=expense.entry_id,account__code__startswith='6').update(key_id=expense.key_id)
    for call in FundCall.objects.exclude(entry_id=None).iterator():
        Line.objects.filter(entry_id=call.entry_id).update(key_id=call.key_id)
        Line.objects.filter(entry_id=call.entry_id,account__code__startswith='450').update(due_date=call.due_date)
    # No historical ownership/share distribution is invented. The UI lists
    # existing costs for an explicit review before annual regularization.

class Migration(migrations.Migration):
    dependencies=[('finance','0007_entry_kind_fundcall_decision_fundcall_kind_and_more')]
    operations=[migrations.RunPython(migrate_metadata,migrations.RunPython.noop)]
