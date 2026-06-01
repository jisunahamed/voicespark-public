import json
from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import force_authenticate

from fb_auth.models import FacebookPage
from fb_auth.views import public_media_url
from linkedin_auth.models import LinkedinToken
from nano_banana.models import NanoBananaImage
from nano_banana.views import ChangeApproval, save_nano_meta
from workspace.models import Workspace

from .models import ScheduledPost, UserProfile
from .views import ChangeApprovalToggle, GetApprovalToggle
from .views_schedule import ScheduledPost as ScheduledPostView
from .views_schedule import extract_external_post_id, merge_publish_results
from utils.public_urls import public_media_url as shared_public_media_url


class PublishingSchedulingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='publisher', password='pass')
        self.workspace = Workspace.objects.create(name='Publishing', owner=self.user)
        self.nano = NanoBananaImage.objects.create(
            user=self.user,
            workspace=self.workspace,
            caption='Caption',
            picture_url='https://example.com/image.jpg',
            platform_captions={'facebook': 'Facebook caption'},
        )

    def test_change_approval_requires_explicit_social_platforms(self):
        request = self.factory.post(
            '/nano-banana/change-approval/',
            data={
                'user_id': self.user.id,
                'nano_banana_id': str(self.nano.id),
                'approved_platforms': [],
            },
            content_type='application/json',
        )

        response = ChangeApproval.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'No approved platforms were selected for this post.')
        self.assertFalse(ScheduledPost.objects.filter(nano_banana=self.nano).exists())

    def test_get_approval_toggle_requires_valid_workspace_json_not_500(self):
        request = self.factory.post(
            '/auth/user/get-toggle/',
            data={'user_id': self.user.id, 'workspace_id': ''},
            content_type='application/json',
        )
        force_authenticate(request, user=self.user)

        response = GetApprovalToggle.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'workspace_id is required.')

    def test_approval_toggle_is_workspace_scoped(self):
        other_workspace = Workspace.objects.create(name='Other', owner=self.user)
        UserProfile.objects.create(user=self.user, workspace=self.workspace, approval_toggle=True)
        UserProfile.objects.create(user=self.user, workspace=other_workspace, approval_toggle=True)
        request = self.factory.post(
            '/auth/user/change-toggle/',
            data={'user_id': self.user.id, 'workspace_id': str(self.workspace.id), 'toggle': False},
            content_type='application/json',
        )
        force_authenticate(request, user=self.user)

        response = ChangeApprovalToggle.as_view()(request)
        payload = json.loads(response.content.decode('utf-8'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(payload['approval_toggle'])
        self.assertFalse(UserProfile.objects.get(user=self.user, workspace=self.workspace).approval_toggle)
        self.assertTrue(UserProfile.objects.get(user=self.user, workspace=other_workspace).approval_toggle)

    def test_approval_toggle_accepts_approval_toggle_payload_name(self):
        UserProfile.objects.create(user=self.user, workspace=self.workspace, approval_toggle=False)
        request = self.factory.post(
            '/auth/user/change-toggle/',
            data={'user_id': self.user.id, 'workspace_id': str(self.workspace.id), 'approval_toggle': True},
            content_type='application/json',
        )
        force_authenticate(request, user=self.user)

        response = ChangeApprovalToggle.as_view()(request)
        payload = json.loads(response.content.decode('utf-8'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(payload['approval_toggle'])
        self.assertTrue(UserProfile.objects.get(user=self.user, workspace=self.workspace).approval_toggle)

    def test_scheduled_publish_without_approved_platforms_aborts(self):
        ScheduledPost.objects.create(
            user=self.user,
            workspace=self.workspace,
            nano_banana=self.nano,
            scheduled_at=timezone.now(),
            approval='approved',
            task_id='task-1',
        )
        request = self.factory.post(
            '/auth/user/schedule-post/',
            data={
                'user_id': self.user.id,
                'nano_banana_id': str(self.nano.id),
                'expected_task_id': 'task-1',
            },
            content_type='application/json',
        )

        response = ScheduledPostView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'No approved platforms were selected for this post.')

    def test_stale_task_id_noops(self):
        save_nano_meta(self.nano, {'approved_platforms': ['facebook']})
        ScheduledPost.objects.create(
            user=self.user,
            workspace=self.workspace,
            nano_banana=self.nano,
            scheduled_at=timezone.now(),
            approval='approved',
            task_id='new-task',
        )
        request = self.factory.post(
            '/auth/user/schedule-post/',
            data={
                'user_id': self.user.id,
                'nano_banana_id': str(self.nano.id),
                'expected_task_id': 'old-task',
            },
            content_type='application/json',
        )

        response = ScheduledPostView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Stale scheduled task ignored.')

    def test_future_task_noops_before_scheduled_at(self):
        save_nano_meta(self.nano, {'approved_platforms': ['facebook']})
        ScheduledPost.objects.create(
            user=self.user,
            workspace=self.workspace,
            nano_banana=self.nano,
            scheduled_at=timezone.now() + timedelta(minutes=10),
            approval='approved',
            task_id='task-1',
        )
        request = self.factory.post(
            '/auth/user/schedule-post/',
            data={
                'user_id': self.user.id,
                'nano_banana_id': str(self.nano.id),
                'expected_task_id': 'task-1',
            },
            content_type='application/json',
        )

        response = ScheduledPostView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Post is not due yet.')

    def test_selected_facebook_only_attempts_facebook_and_dedupes_results(self):
        save_nano_meta(self.nano, {'approved_platforms': ['facebook']})
        FacebookPage.objects.create(
            user=self.user,
            workspace=self.workspace,
            page_id='page-1',
            name='Page',
            access_token='token',
        )
        ScheduledPost.objects.create(
            user=self.user,
            workspace=self.workspace,
            nano_banana=self.nano,
            scheduled_at=timezone.now(),
            approval='approved',
            task_id='task-1',
        )
        request = self.factory.post(
            '/auth/user/schedule-post/',
            data={
                'user_id': self.user.id,
                'nano_banana_id': str(self.nano.id),
                'expected_task_id': 'task-1',
            },
            content_type='application/json',
        )

        def fake_facebook_view(internal_request):
            return Response({'external_post_id': 'fb-post-1'}, status=status.HTTP_201_CREATED)

        with patch('auth_user.views_schedule.FacebookPostView.as_view', return_value=fake_facebook_view):
            response = ScheduledPostView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.nano.refresh_from_db()
        meta = self.nano.platform_captions['__meta']
        self.assertEqual(meta['posted_platforms'], ['facebook'])
        self.assertEqual(set(meta['platform_publish_status'].keys()), {'facebook'})
        self.assertEqual(meta['platform_publish_status']['facebook']['external_post_id'], 'fb-post-1')
        self.assertEqual(set(meta['publish_results'].keys()), {'facebook'})

        second_request = self.factory.post(
            '/auth/user/schedule-post/',
            data={
                'user_id': self.user.id,
                'nano_banana_id': str(self.nano.id),
                'expected_task_id': 'task-1',
            },
            content_type='application/json',
        )
        second_response = ScheduledPostView.as_view()(second_request)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.nano.refresh_from_db()
        self.assertEqual(set(self.nano.platform_captions['__meta']['publish_results'].keys()), {'facebook'})

    def test_selected_linkedin_only_attempts_linkedin(self):
        save_nano_meta(self.nano, {'approved_platforms': ['linkedin']})
        LinkedinToken.objects.create(user=self.user, workspace=self.workspace, access_token='token', id_token='id')
        ScheduledPost.objects.create(
            user=self.user,
            workspace=self.workspace,
            nano_banana=self.nano,
            scheduled_at=timezone.now(),
            approval='approved',
            task_id='task-1',
        )
        request = self.factory.post(
            '/auth/user/schedule-post/',
            data={
                'user_id': self.user.id,
                'nano_banana_id': str(self.nano.id),
                'expected_task_id': 'task-1',
            },
            content_type='application/json',
        )

        def fake_linkedin_view(internal_request):
            return Response({'post_urn': 'urn:li:share:1'}, status=status.HTTP_201_CREATED)

        def fail_facebook_view(internal_request):
            raise AssertionError('Facebook should not be attempted for a LinkedIn-only post.')

        with patch('auth_user.views_schedule.LinkedinCreatePost.as_view', return_value=fake_linkedin_view), \
             patch('auth_user.views_schedule.FacebookPostView.as_view', return_value=fail_facebook_view):
            response = ScheduledPostView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.nano.refresh_from_db()
        meta = self.nano.platform_captions['__meta']
        self.assertEqual(meta['posted_platforms'], ['linkedin'])
        self.assertEqual(set(meta['platform_publish_status'].keys()), {'linkedin'})
        self.assertEqual(meta['platform_publish_status']['linkedin']['external_post_id'], 'urn:li:share:1')

    def test_external_id_extraction_supports_linkedin_and_nested_data(self):
        self.assertEqual(extract_external_post_id({'post_urn': 'urn:li:share:1'}), 'urn:li:share:1')
        self.assertEqual(extract_external_post_id({'x-restli-id': 'urn:li:share:2'}), 'urn:li:share:2')
        self.assertEqual(extract_external_post_id({'external_post_id': 'fb-post-1'}), 'fb-post-1')
        self.assertEqual(extract_external_post_id({'media_id': 'ig-media-1'}), 'ig-media-1')
        self.assertEqual(extract_external_post_id({'tweet_id': 'tweet-1'}), 'tweet-1')
        self.assertEqual(extract_external_post_id({'data': {'id': 'nested-id'}}), 'nested-id')

    def test_merge_publish_results_replaces_same_platform(self):
        existing = [{'platform': 'facebook', 'status': 500}]
        merged = merge_publish_results(existing, [{'platform': 'facebook', 'status': 201}])
        self.assertEqual(merged, {'facebook': {'platform': 'facebook', 'status': 201}})

    def test_facebook_media_url_converts_relative_media_path(self):
        with patch.dict('os.environ', {'BACKEND_URL': '', 'PUBLIC_BACKEND_URL': ''}):
            self.assertEqual(
                public_media_url('/media/generated/image.jpg'),
                'https://api.voicespark.ai/media/generated/image.jpg',
            )
            self.assertEqual(
                public_media_url('https://cdn.example.com/image.jpg'),
                'https://cdn.example.com/image.jpg',
            )
            self.assertEqual(
                shared_public_media_url('/media/generated/image.jpg'),
                'https://api.voicespark.ai/media/generated/image.jpg',
            )
            self.assertEqual(
                shared_public_media_url('https://134-209-146-170.sslip.io/media/generated/image.jpg'),
                'https://api.voicespark.ai/media/generated/image.jpg',
            )
