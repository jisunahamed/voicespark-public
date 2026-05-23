import json
import logging
import time

from celery import shared_task
from django.test import RequestFactory

from .models import NanoGenerationJob

logger = logging.getLogger(__name__)


# Hard timeout — prevents infinite execution
TASK_HARD_TIMEOUT_SECONDS = int(60 * 20)  # 20 min max

# Terminal states — never transition FROM these
TERMINAL_STATES = {'completed', 'failed'}


def _response_payload(response):
    if hasattr(response, 'data'):
        return response.data
    try:
        return json.loads(response.content.decode('utf-8'))
    except Exception:
        return {'raw': getattr(response, 'content', b'').decode('utf-8', errors='ignore')}


def _safe_transition(job, new_status, error='', result=None):
    """Validate state transition before saving. Never revert a terminal state."""
    if job.status in TERMINAL_STATES:
        logger.error(
            'blocked_state_transition current=%s target=%s job=%s type=%s',
            job.status, new_status, job.id, job.job_type,
        )
        return False

    job.status = new_status
    update_fields = ['status', 'updated_at']

    if error:
        job.error = error
        update_fields.append('error')

    if result is not None:
        job.result = result
        update_fields.append('result')

    job.save(update_fields=update_fields)
    return True


@shared_task(bind=True, queue='make_posts', acks_late=True, soft_time_limit=TASK_HARD_TIMEOUT_SECONDS, time_limit=TASK_HARD_TIMEOUT_SECONDS + 30)
def run_nano_generation_job(self, job_id):
    from .views import CreateNewPost, EditGeneratedImage, RegenerateImage

    started = time.monotonic()

    try:
        job = NanoGenerationJob.objects.select_related('user', 'workspace', 'nano_banana').get(id=job_id)
    except NanoGenerationJob.DoesNotExist:
        logger.error('nano_generation_job_not_found job_id=%s', job_id)
        return {'status': 'failed', 'error': 'Job not found.'}

    # Don't re-run terminal jobs (idempotency protection)
    if job.status in TERMINAL_STATES:
        logger.warning(
            'nano_generation_job_already_terminal job=%s status=%s type=%s',
            job.id, job.status, job.job_type,
        )
        return {'status': job.status}

    # Transition: queued → running
    if not _safe_transition(job, 'running'):
        return {'status': 'failed', 'error': 'Invalid state transition.'}

    view_map = {
        'create_post': ('/nano-banana/create-new-post/', CreateNewPost.as_view()),
        'regenerate_image': ('/nano-banana/regenerate-image/', RegenerateImage.as_view()),
        'edit_generated_image': ('/nano-banana/edit-generated-image/', EditGeneratedImage.as_view()),
    }

    if job.job_type not in view_map:
        _safe_transition(job, 'failed', error=f'Unknown job type: {job.job_type}')
        return {'status': 'failed', 'error': f'Unknown job type: {job.job_type}'}

    try:
        path, view = view_map[job.job_type]
        payload = dict(job.payload or {})
        payload['force_sync'] = True
        payload.setdefault('user_id', job.user_id)
        if job.workspace_id and not payload.get('workspace_id'):
            payload['workspace_id'] = str(job.workspace_id)
        if job.nano_banana_id and not payload.get('nano_banana_id'):
            payload['nano_banana_id'] = str(job.nano_banana_id)

        factory = RequestFactory()
        request = factory.post(path, data=json.dumps(payload), content_type='application/json')
        request.user = job.user
        response = view(request)
        data = _response_payload(response)

        duration_ms = int((time.monotonic() - started) * 1000)

        if response.status_code >= 400:
            error_msg = (
                data.get('error') or data.get('detail')
                or f'Generation failed with status {response.status_code}.'
            )
            result_data = data if isinstance(data, dict) else {'data': data}
            result_data['retryable'] = data.get('retryable', True) if isinstance(data, dict) else True
            _safe_transition(job, 'failed', error=error_msg, result=result_data)
            logger.warning(
                'nano_generation_job_failed job=%s type=%s duration_ms=%s error=%s',
                job.id, job.job_type, duration_ms, error_msg,
            )
        else:
            result_data = data if isinstance(data, dict) else {'data': data}
            _safe_transition(job, 'completed', result=result_data)
            logger.info(
                'nano_generation_job_completed job=%s type=%s duration_ms=%s',
                job.id, job.job_type, duration_ms,
            )

    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.exception(
            'nano_generation_job_exception job=%s type=%s duration_ms=%s',
            job_id, getattr(job, 'job_type', ''), duration_ms,
        )
        _safe_transition(
            job, 'failed',
            error=str(exc),
            result={'error': str(exc), 'retryable': True},
        )
        return {'status': 'failed', 'error': str(exc)}
