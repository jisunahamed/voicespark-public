from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings
from dotenv import load_dotenv
load_dotenv()
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blaze.settings')

# Create a new Celery instance with the project name
app = Celery('blaze')

# Load configuration from Django settings with a 'CELERY_' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(
    result_backend=os.getenv('CELERY_RESULT_BACKEND'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/London',
    enable_utc=True,
    worker_prefetch_multiplier=1,
)
app.conf.worker_prefetch_multiplier = 1
# Autodiscover tasks from installed apps and include tasks from the utils/celery directory
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.autodiscover_tasks(['utils.celery'])  # Explicitly include the celery directory inside utils


# Optional: Define a debug task for testing
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
