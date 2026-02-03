# Generated manually for converting description field to multilingual format

from django.db import migrations


def convert_descriptions_to_dict(apps, schema_editor):
    """Convert existing string descriptions to dict format with 'en' key"""
    Plan = apps.get_model('billing', 'Plan')
    
    for plan in Plan.objects.filter(description__isnull=False).exclude(description=''):
        # If it's already a dict, skip
        if isinstance(plan.description, dict):
            continue
        
        # Convert string to dict with 'en' key
        if isinstance(plan.description, str):
            plan.description = {'en': plan.description}
            plan.save()


def reverse_convert_descriptions(apps, schema_editor):
    """Reverse migration: convert dict back to string (take 'en' value)"""
    Plan = apps.get_model('billing', 'Plan')
    
    for plan in Plan.objects.filter(description__isnull=False):
        if isinstance(plan.description, dict) and 'en' in plan.description:
            plan.description = plan.description['en']
            plan.save()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0012_stripeerrorlog'),
    ]

    operations = [
        migrations.RunPython(
            convert_descriptions_to_dict,
            reverse_convert_descriptions
        ),
    ]