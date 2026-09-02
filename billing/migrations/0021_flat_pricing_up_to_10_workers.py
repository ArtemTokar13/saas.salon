from django.db import migrations


def set_flat_worker_pricing(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    Plan.objects.update(base_workers=10, additional_worker_price=0)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0020_add_manual_invoice'),
    ]

    operations = [
        migrations.RunPython(set_flat_worker_pricing, noop),
    ]
