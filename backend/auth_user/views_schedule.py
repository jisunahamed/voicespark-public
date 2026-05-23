from django.http import JsonResponse
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
# from utils.celery.tasks import make_posts
from datetime import datetime, timedelta, timezone
from django.test import RequestFactory
from django.db import transaction
import json
import uuid
import logging
from x_auth.views import post_tweet

logger = logging.getLogger(__name__)
from x_auth.models import XToken
from fb_auth.views import FacebookPostView, InstagramPostView
from fb_auth.models import FacebookPage, FacebookToken, InstagramToken
from linkedin_auth.views import LinkedinCreatePost
from linkedin_auth.models import LinkedinToken
from wordpress_auth.views import WordpressPostView
from wordpress_auth.models import WordpressConnection
from nano_banana.models import NanoBananaImage
from .models import ScheduledPost as SchedulePostModel, UserProfile
from django.contrib.auth.models import User
from django.utils import timezone


PLATFORM_ALIASES = {
    'x': 'twitter',
    'twitter': 'twitter',
    'facebook': 'facebook',
    'fb': 'facebook',
    'instagram': 'instagram',
    'ig': 'instagram',
    'linkedin': 'linkedin',
    'li': 'linkedin',
    'wordpress': 'wordpress',
    'wp': 'wordpress',
}


def normalize_platforms(value):
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    normalized = []
    for item in value:
        key = PLATFORM_ALIASES.get(str(item).strip().lower())
        if key and key not in normalized:
            normalized.append(key)
    return normalized


def nano_meta(nano_banana):
    captions = nano_banana.platform_captions or {}
    meta = captions.get('__meta') or captions.get('__meta__')
    return meta if isinstance(meta, dict) else {}


def save_nano_meta(nano_banana, patch):
    captions = nano_banana.platform_captions or {}
    meta = nano_meta(nano_banana)
    meta.update(patch or {})
    captions['__meta'] = meta
    nano_banana.platform_captions = captions
    nano_banana.save(update_fields=['platform_captions'])
    return meta


def extract_external_post_id(response_data):
    if not isinstance(response_data, dict):
        return None
    for key in ('post_urn', 'x-restli-id', 'external_post_id', 'post_id', 'tweet_id', 'media_id', 'share_id', 'activity_id', 'id'):
        value = response_data.get(key)
        if value not in (None, ''):
            return str(value)
    data = response_data.get('data')
    if isinstance(data, dict):
        return extract_external_post_id(data)
    return None


def merge_publish_results(existing, new_results):
    merged = {}
    if isinstance(existing, dict):
        merged.update(existing)
    elif isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict) and item.get('platform'):
                merged[item['platform']] = item
    for item in new_results or []:
        if isinstance(item, dict) and item.get('platform'):
            merged[item['platform']] = item
    return merged


def coerce_error_message(value, fallback='Publish failed.'):
    if value in (None, ''):
        return fallback
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except TypeError:
        return str(value)


def build_publish_error(status_map, selected_platforms):
    platform_labels = {
        'twitter': 'X',
        'facebook': 'Facebook',
        'instagram': 'Instagram',
        'linkedin': 'LinkedIn',
        'wordpress': 'WordPress',
    }
    messages = []
    for platform in selected_platforms:
        data = status_map.get(platform) if isinstance(status_map, dict) else None
        if not isinstance(data, dict) or data.get('status') not in ('failed', 'skipped'):
            continue
        error = coerce_error_message(data.get('error'), fallback='Publish failed.')
        messages.append(f"{platform_labels.get(platform, platform)}: {error}")
    return '; '.join(messages) if messages else None


class ScheduledPost(APIView):
    def post(self, request):
        approve = request.data.get('approve', "")
        nano_banana_id = request.data.get("nano_banana_id", "")
        user_id = request.data.get('user_id', '')
        logger.info(
            'Scheduled publish attempt started user_id=%s nano_banana_id=%s approve=%s',
            user_id,
            nano_banana_id,
            approve,
        )
        nano_banana = NanoBananaImage.objects.filter(id=nano_banana_id).first()
        if nano_banana is None:
            logger.warning('Scheduled publish aborted: post image not found nano_banana_id=%s', nano_banana_id)
            return Response(
                {'error': 'Post image was not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        schedule_obj = SchedulePostModel.objects.filter(nano_banana=nano_banana).first()
        if schedule_obj is None:
            logger.warning('Scheduled publish aborted: scheduled post not found nano_banana_id=%s', nano_banana_id)
            return Response(
                {'error': 'Scheduled post was not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        user = User.objects.filter(id=user_id).first() if user_id else nano_banana.user
        if user is None:
            logger.warning('Scheduled publish aborted: user not found user_id=%s nano_banana_id=%s', user_id, nano_banana_id)
            return Response({'error': 'User was not found.'}, status=status.HTTP_404_NOT_FOUND)
        if schedule_obj.nano_banana_id != nano_banana.id:
            logger.warning(
                'Scheduled publish aborted: schedule object mismatch schedule_id=%s nano_banana_id=%s expected=%s',
                schedule_obj.id,
                nano_banana.id,
                schedule_obj.nano_banana_id,
            )
            return Response({'error': 'Scheduled post mismatch.'}, status=status.HTTP_400_BAD_REQUEST)
        if schedule_obj.workspace_id != nano_banana.workspace_id:
            logger.warning(
                'Scheduled publish aborted: workspace mismatch schedule_id=%s schedule_workspace=%s nano_workspace=%s',
                schedule_obj.id,
                schedule_obj.workspace_id,
                nano_banana.workspace_id,
            )
            return Response({'error': 'Scheduled post workspace mismatch.'}, status=status.HTTP_400_BAD_REQUEST)
        expected_task_id = request.data.get('expected_task_id')
        if expected_task_id and str(expected_task_id) != str(schedule_obj.task_id):
            logger.info(
                'Scheduled publish no-op: stale task schedule_id=%s expected_task_id=%s current_task_id=%s',
                schedule_obj.id,
                expected_task_id,
                schedule_obj.task_id,
            )
            return Response({'message': 'Stale scheduled task ignored.'}, status=status.HTTP_200_OK)
        if schedule_obj.approval == 'posted':
            logger.info('Scheduled publish skipped: already posted schedule_id=%s', schedule_obj.id)
            return Response({'message': 'Post already published.', 'results': nano_meta(nano_banana).get('publish_results', [])}, status=status.HTTP_200_OK)
        if approve == 'approved' and schedule_obj.approval != 'posted':
            # If platforms are provided in the request, save them to the post metadata
            req_platforms = normalize_platforms(request.data.get('approved_platforms'))
            if req_platforms:
                save_nano_meta(nano_banana, {'approved_platforms': req_platforms})
                logger.info('Scheduled publish: updated approved_platforms from request data schedule_id=%s platforms=%s', schedule_obj.id, req_platforms)

            schedule_obj.approval = 'approved'
            schedule_obj.scheduled_at = timezone.now()
            schedule_obj.save(update_fields=['approval', 'scheduled_at'])

        if schedule_obj.approval not in ('approved', 'posted'):
            logger.info(
                'Scheduled publish skipped: not eligible schedule_id=%s approval=%s',
                schedule_obj.id,
                schedule_obj.approval,
            )
            return Response({'message': 'Post is not approved for publishing yet.'}, status=status.HTTP_200_OK)

        if schedule_obj.scheduled_at and schedule_obj.scheduled_at > timezone.now():
            logger.info(
                'Scheduled publish skipped: not due yet schedule_id=%s scheduled_at=%s now=%s',
                schedule_obj.id,
                schedule_obj.scheduled_at,
                timezone.now(),
            )
            return Response({'message': 'Post is not due yet.'}, status=status.HTTP_200_OK)

        meta = nano_meta(nano_banana)
        approved_platforms = normalize_platforms(meta.get('approved_platforms'))
        posted_platforms = normalize_platforms(meta.get('posted_platforms'))
        logger.info(
            'Scheduled publish platform state schedule_id=%s approved_platforms=%s posted_platforms=%s',
            schedule_obj.id,
            approved_platforms,
            posted_platforms,
        )
        if not approved_platforms:
            logger.warning('Scheduled publish aborted: approved platforms missing schedule_id=%s', schedule_obj.id)
            return Response(
                {'error': 'No approved platforms were selected for this post.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        selected_platforms = [platform for platform in approved_platforms if platform not in posted_platforms]
        logger.info(
            'Scheduled publish remaining platforms schedule_id=%s selected=%s remaining=%s',
            schedule_obj.id,
            approved_platforms,
            selected_platforms,
        )
        if not selected_platforms:
            logger.info('Scheduled publish skipped: all selected platforms already posted schedule_id=%s', schedule_obj.id)
            schedule_obj.approval = 'posted'
            save_nano_meta(nano_banana, {
                'publish_results': meta.get('publish_results', []),
                'posted_platforms': posted_platforms,
                'last_publish_attempt_at': timezone.now().isoformat(),
                'posted_at': meta.get('posted_at') or timezone.now().isoformat(),
                'publish_error': None,
                'publishing_started_at': None,
                'publish_attempt_count': int(meta.get('publish_attempt_count') or 0),
                'platform_publish_status': meta.get('platform_publish_status') or {},
            })
            schedule_obj.save(update_fields=['approval'])
            return Response({'message': 'Post already published.'}, status=status.HTTP_200_OK)

        user_profile = UserProfile.objects.filter(user=user, workspace=nano_banana.workspace).first()
        payload = request.data.copy()
        payload['user_id'] = user.id
        payload['nano_banana_id'] = str(nano_banana.id)
        payload['nana_banana_id'] = str(nano_banana.id)
        results = []
        platform_publish_status = dict(meta.get('platform_publish_status') or {}) if isinstance(meta.get('platform_publish_status'), dict) else {}
        selected_set = set(selected_platforms)
        attempt_count = int(meta.get('publish_attempt_count') or 0) + 1
        publishing_started_at = timezone.now().isoformat()
        save_nano_meta(nano_banana, {
            'publishing_started_at': publishing_started_at,
            'publish_attempt_count': attempt_count,
            'publish_error': None,
            'last_publish_attempt_at': publishing_started_at,
            'platform_publish_status': platform_publish_status,
            'posted_platforms': posted_platforms,
        })
        logger.info(
            'Scheduled publish attempt marker saved schedule_id=%s attempt_count=%s',
            schedule_obj.id,
            attempt_count,
        )

        facebook_pages_connected = FacebookPage.objects.filter(user=user, workspace=nano_banana.workspace).exists()
        facebook_token_connected = FacebookToken.objects.filter(user=user, workspace=nano_banana.workspace).exists()
        instagram_token_connected = InstagramToken.objects.filter(user=user, workspace=nano_banana.workspace).exists()

        def facebook_missing_credentials_error():
            if facebook_token_connected:
                return (
                    'Facebook account is connected, but no Facebook Page was authorized for this workspace. '
                    'Reconnect Facebook and choose a Page; publishing to personal profiles is not supported.'
                )
            return 'Facebook Page is not connected for this workspace.'

        def instagram_missing_credentials_error():
            missing = []
            if not instagram_token_connected:
                missing.append('Instagram publishing permission is not connected or was not granted for this workspace.')
            if not facebook_pages_connected:
                missing.append('Instagram publishing requires a connected Facebook Page with an Instagram Business account.')
            return ' '.join(missing) or 'Instagram is not connected for this workspace.'

        platform_configs = [
            ('twitter', XToken.objects.filter(user=user, workspace=nano_banana.workspace).exists(), '/auth/x/tweet/', post_tweet, 'x', 'X is not connected for this workspace.'),
            ('facebook', facebook_pages_connected, '/auth/fb/facebook-post/', FacebookPostView.as_view(), 'facebook', facebook_missing_credentials_error()),
            ('instagram', facebook_pages_connected and instagram_token_connected, '/auth/fb/instagram-post/', InstagramPostView.as_view(), 'instagram', instagram_missing_credentials_error()),
            ('linkedin', LinkedinToken.objects.filter(user=user, workspace=nano_banana.workspace).exists(), '/auth/linkedin/post/', LinkedinCreatePost.as_view(), 'linkedin', 'LinkedIn Company Page is not connected for this workspace.'),
            ('wordpress', WordpressConnection.objects.filter(workspace=nano_banana.workspace, is_active=True).exists(), '/auth/wordpress/publish/', WordpressPostView.as_view(), 'wordpress', 'WordPress is not connected for this workspace.'),
        ]
        platform_results = []

        def mark_platform_status(platform, status_value, error=None, published_at=None, external_post_id=None):
            platform_publish_status[platform] = {
                'status': status_value,
                'published_at': published_at,
                'external_post_id': external_post_id,
                'error': error,
            }

        def persist_progress(*, approval_value=None, publish_error=None, posted_at=None):
            latest_meta = nano_meta(nano_banana)
            patch = {
                'publish_results': merge_publish_results(latest_meta.get('publish_results'), platform_results),
                'posted_platforms': [],
                'last_publish_attempt_at': timezone.now().isoformat(),
                'platform_publish_status': platform_publish_status,
                'publishing_started_at': publishing_started_at,
                'publish_attempt_count': attempt_count,
                'publish_error': publish_error,
            }
            current_posted = normalize_platforms(latest_meta.get('posted_platforms'))
            for item_platform in current_posted:
                if item_platform not in patch['posted_platforms']:
                    patch['posted_platforms'].append(item_platform)
            for item_platform, item_data in platform_publish_status.items():
                if item_data.get('status') == 'published' and item_platform not in patch['posted_platforms']:
                    patch['posted_platforms'].append(item_platform)
            if posted_at:
                patch['posted_at'] = posted_at
            if approval_value:
                schedule_obj.approval = approval_value
            schedule_obj.save(update_fields=['approval'])
            save_nano_meta(nano_banana, patch)
            return patch

        def publish(platform, path, view_callable):
            latest_meta = nano_meta(nano_banana)
            latest_posted = normalize_platforms(latest_meta.get('posted_platforms'))
            latest_status_map = latest_meta.get('platform_publish_status') if isinstance(latest_meta.get('platform_publish_status'), dict) else {}
            if platform in latest_posted or (isinstance(latest_status_map, dict) and latest_status_map.get(platform, {}).get('status') == 'published'):
                logger.info('Scheduled publish skipped already published platform schedule_id=%s platform=%s', schedule_obj.id, platform)
                mark_platform_status(platform, 'published', published_at=(latest_status_map.get(platform, {}) or {}).get('published_at') or latest_meta.get('posted_at'))
                return True
            factory = RequestFactory()
            internal_request = factory.post(
                path,
                data=json.dumps(payload),
                content_type='application/json'
            )
            internal_request.user = user
            try:
                response = view_callable(internal_request)
                status_code = getattr(response, 'status_code', status.HTTP_200_OK)
                response_data = getattr(response, 'data', {}) if hasattr(response, 'data') else {}
                external_post_id = extract_external_post_id(response_data)
                response_error = response_data.get('error') if isinstance(response_data, dict) else None
                response_error = coerce_error_message(response_error, fallback=None)
                platform_results.append({'platform': platform, 'status': status_code, 'external_post_id': external_post_id, 'error': response_error})
                logger.info('Scheduled publish platform result schedule_id=%s platform=%s status=%s external_post_id=%s', schedule_obj.id, platform, status_code, external_post_id)
                if 200 <= status_code < 300:
                    mark_platform_status(platform, 'published', published_at=timezone.now().isoformat(), external_post_id=external_post_id)
                    persist_progress(approval_value='approved')
                    return True
                error_msg = response_error or f'http_{status_code}'
                mark_platform_status(platform, 'failed', error=error_msg, external_post_id=external_post_id)
                persist_progress(approval_value='approved', publish_error=error_msg)
                return False
            except Exception as exc:
                error_msg = str(exc)
                if hasattr(exc, 'response') and hasattr(exc.response, 'text'):
                    error_msg = f"{exc} - {exc.response.text}"
                platform_results.append({'platform': platform, 'status': 'error', 'error': error_msg})
                mark_platform_status(platform, 'failed', error=error_msg)
                try:
                    persist_progress(approval_value='approved', publish_error=error_msg)
                except Exception as p_exc:
                    logger.error(f"Failed to persist progress after publish error: {p_exc}")
                logger.exception('Scheduled publish platform error schedule_id=%s platform=%s: %s', schedule_obj.id, platform, error_msg)
                return False

        any_attempted = False
        any_success = False
        for platform, is_connected, path, view_callable, alias, missing_credentials_error in platform_configs:
            if platform not in selected_set:
                logger.info('Scheduled publish skipped unselected platform schedule_id=%s platform=%s', schedule_obj.id, platform)
                continue
            if platform in posted_platforms:
                logger.info('Scheduled publish skipped already posted platform schedule_id=%s platform=%s', schedule_obj.id, platform)
                mark_platform_status(platform, 'published', published_at=meta.get('posted_at'), error=None)
                continue
            if not is_connected:
                logger.warning('Scheduled publish skipped missing credentials schedule_id=%s platform=%s', schedule_obj.id, platform)
                platform_results.append({'platform': platform, 'status': 'skipped', 'error': missing_credentials_error})
                mark_platform_status(platform, 'skipped', error=missing_credentials_error)
                persist_progress(approval_value='approved', publish_error=missing_credentials_error)
                continue
            any_attempted = True
            if publish(platform, path, view_callable):
                any_success = True

        if not any_attempted and not platform_results:
            logger.warning('Scheduled publish aborted: no eligible platforms schedule_id=%s', schedule_obj.id)
            persist_progress(approval_value='approved', publish_error='No eligible platforms available for publishing.')
            return Response({'error': 'No eligible platforms available for publishing.'}, status=status.HTTP_400_BAD_REQUEST)

        latest_meta = nano_meta(nano_banana)
        latest_posted = normalize_platforms(latest_meta.get('posted_platforms'))
        latest_status_map = latest_meta.get('platform_publish_status') if isinstance(latest_meta.get('platform_publish_status'), dict) else {}
        completed_platforms = []
        for platform in latest_posted:
            if platform not in completed_platforms:
                completed_platforms.append(platform)
        for platform, data in (latest_status_map or {}).items():
            if isinstance(data, dict) and data.get('status') == 'published' and platform not in completed_platforms:
                completed_platforms.append(platform)
        patch = {
            'publish_results': merge_publish_results(latest_meta.get('publish_results'), platform_results),
            'posted_platforms': completed_platforms,
            'last_publish_attempt_at': timezone.now().isoformat(),
            'platform_publish_status': latest_status_map or platform_publish_status,
        }
        all_selected_published = set(selected_platforms).issubset(set(completed_platforms))
        if all_selected_published and selected_platforms:
            schedule_obj.approval = 'posted'
            patch['posted_at'] = latest_meta.get('posted_at') or timezone.now().isoformat()
            patch['publish_error'] = None
            patch['published_at'] = latest_meta.get('published_at') or timezone.now().isoformat()
            schedule_obj.save(update_fields=['approval'])
            logger.info('Scheduled publish completed schedule_id=%s status=posted posted_platforms=%s', schedule_obj.id, completed_platforms)
        else:
            schedule_obj.approval = 'approved'
            failed_platforms = [platform for platform, data in (latest_status_map or {}).items() if isinstance(data, dict) and data.get('status') in ('failed', 'skipped')]
            patch['publish_error'] = build_publish_error(latest_status_map or platform_publish_status, selected_platforms) or latest_meta.get('publish_error') or ('Partial or failed publish attempt.' if failed_platforms else None)
            schedule_obj.save(update_fields=['approval'])
            logger.info('Scheduled publish partially completed schedule_id=%s posted_platforms=%s failed_platforms=%s', schedule_obj.id, completed_platforms, failed_platforms)
        save_nano_meta(nano_banana, patch)

        if not any_success:
            return Response(
                {'error': 'Post failed on all selected platforms.', 'results': platform_results},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'results': platform_results}, status=status.HTTP_200_OK)
