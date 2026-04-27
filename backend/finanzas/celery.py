import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finanzas.settings')

app = Celery('finanzas')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
