import datetime
from pathlib import Path

from celery import shared_task
import json
from celery.exceptions import MaxRetriesExceededError
import logging
from celery import current_task
from django_celery_results.models import TaskResult
from celery.states import SUCCESS, FAILURE, PENDING, STARTED
import requests
import dotenv
from dotenv import load_dotenv
from auth_user.views_schedule import ScheduledPost
import os
from django.test import RequestFactory

load_dotenv()

# Set up logger
logger = logging.getLogger('celery')


@shared_task(bind=True, queue='make_posts', acks_late=True)
def make_posts(self, payload):
    try:
        payload = dict(payload or {})
        payload.setdefault('expected_task_id', self.request.id)
        result_data = f"{payload}"

        task_result, created = TaskResult.objects.get_or_create(task_id=self.request.id)
        task_result.status = STARTED
        task_result.save()

        # START PROCESSING CODE --------------------------------- START PROCESSING CODE
        # url = f"http://{os.getenv('SERVER_IP', None)}/connection/request/send-request/"
        factory = RequestFactory()
        request = factory.post(
            '/auth/user/schedule-post/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        my_view = ScheduledPost.as_view()
        response = my_view(request)
        # url = ''
        # headers = {
        #     "Content-Type": "application/json"
        # }
        #
        # print(url)
        # # inputData = dict(payload)
        # response = requests.post(url=url, data=payload, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}")

        # YOU ARE ALREADY IN TRY EXCEPT NOTE THAT

        # DO NOT CROSS THIS LINE --------------------------------- DO NOT CROSS THIS LINE

        # Update fields of the TaskResult
        task_result, created = TaskResult.objects.get_or_create(task_id=self.request.id)
        task_result.status = SUCCESS
        task_result.result = json.dumps(result_data)
        task_result.traceback = None  # Set traceback to None if successful
        task_result.worker = self.request.hostname
        task_result.task_name = self.name  # Task name
        task_result.task_args = self.request.args  # Task args
        task_result.task_kwargs = self.request.kwargs
        task_result.meta = self.request.delivery_info

        # Save the changes
        task_result.save()

        return result_data

    except Exception as e:
        # Handle failure, log the error, and store it in the TaskResult
        error_message = str(e)
        # print(f"Error: {error_message}")
        task_result, created = TaskResult.objects.get_or_create(task_id=self.request.id)
        # Update fields of the TaskResult
        task_result.status = FAILURE
        task_result.result = json.dumps({'error': error_message})
        task_result.traceback = None  # Set traceback to None if successful
        task_result.worker = self.request.hostname
        task_result.task_name = self.name  # Task name
        task_result.task_args = self.request.args  # Task args
        task_result.task_kwargs = self.request.kwargs
        task_result.meta = self.request.delivery_info
        task_result.save()

        raise Exception(f'Error:{e}') # Reraise the exception to allow Celery's retry mechanism if needed


