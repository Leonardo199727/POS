import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.apps import apps
for model in apps.get_models():
    print(f"{model._meta.label}: {model._meta.db_table}")
