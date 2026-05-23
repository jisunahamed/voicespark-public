from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from rest_framework import status

from nano_banana.models import NanoBananaImage
from workspace.models import Workspace

from .models import WordpressConnection
from .utils import encrypt_data
from .views import WordpressPostView


class WordpressPublishTests(TestCase):
    def test_missing_blog_content_returns_clear_error(self):
        factory = RequestFactory()
        user = User.objects.create_user(username='wp-user', password='pass')
        workspace = Workspace.objects.create(name='WP', owner=user)
        nano = NanoBananaImage.objects.create(
            user=user,
            workspace=workspace,
            caption='',
            picture_url='',
            platform_captions={'__meta': {'title': 'Post title'}},
        )
        WordpressConnection.objects.create(
            user=user,
            workspace=workspace,
            site_url='https://example.com',
            wp_username='editor',
            encrypted_password=encrypt_data('password'),
        )
        request = factory.post(
            '/auth/wordpress/publish/',
            data={'nano_banana_id': str(nano.id)},
            content_type='application/json',
        )
        request.user = user

        response = WordpressPostView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'WordPress content is missing for this post.')
