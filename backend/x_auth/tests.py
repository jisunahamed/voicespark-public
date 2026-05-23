import json
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from workspace.models import Workspace
from nano_banana.models import NanoBananaImage

from .models import XToken
from .views import XCallbackView, XLoginView, get_x_oauth1_credentials, post_tweet


def add_session(request):
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request


class XOAuthTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='x-user', password='pass')
        self.workspace = Workspace.objects.create(name='X Workspace', owner=self.user)

    def test_login_accepts_uuid_workspace_and_redirects(self):
        request = add_session(self.factory.get('/auth/x/login/', {
            'user_id': self.user.id,
            'workspace_id': str(self.workspace.id),
        }))

        session = Mock()
        session.fetch_request_token.return_value = {
            'oauth_token': 'request-token',
            'oauth_token_secret': 'request-secret',
            'oauth_callback_confirmed': 'true',
        }
        session.authorization_url.return_value = 'https://api.x.com/oauth/authorize?oauth_token=request-token'
        with patch('x_auth.views.X_API_KEY', 'consumer-key'), \
             patch('x_auth.views.X_API_SECRET', 'consumer-secret'), \
             patch('x_auth.views.X_REDIRECT_URI', 'https://134-209-146-170.sslip.io/auth/x/callback/'), \
             patch('x_auth.views.OAuth1Session', return_value=session):
            response = XLoginView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://api.x.com/oauth/authorize?oauth_token=request-token')
        self.assertEqual(request.session['x_oauth1_request_token'], 'request-token')
        self.assertEqual(request.session['x_oauth1_workspace_id'], str(self.workspace.id))

    def test_login_rejects_workspace_not_owned_by_user(self):
        other = User.objects.create_user(username='other', password='pass')
        other_workspace = Workspace.objects.create(name='Other Workspace', owner=other)
        request = add_session(self.factory.get('/auth/x/login/', {
            'user_id': self.user.id,
            'workspace_id': str(other_workspace.id),
        }))

        with patch('x_auth.views.X_API_KEY', 'consumer-key'), \
             patch('x_auth.views.X_API_SECRET', 'consumer-secret'), \
             patch('x_auth.views.X_REDIRECT_URI', 'https://134-209-146-170.sslip.io/auth/x/callback/'):
            response = XLoginView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['error'], 'Invalid workspace_id for this user.')

    def test_login_rejects_malformed_workspace_id(self):
        request = add_session(self.factory.get('/auth/x/login/', {
            'user_id': self.user.id,
            'workspace_id': 'not-a-workspace',
        }))

        with patch('x_auth.views.X_API_KEY', 'consumer-key'), \
             patch('x_auth.views.X_API_SECRET', 'consumer-secret'), \
             patch('x_auth.views.X_REDIRECT_URI', 'https://134-209-146-170.sslip.io/auth/x/callback/'):
            response = XLoginView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['error'], 'Invalid workspace_id for this user.')

    def test_callback_stores_encrypted_token_for_user_workspace(self):
        request = add_session(self.factory.get('/auth/x/callback/', {
            'oauth_token': 'request-token',
            'oauth_verifier': 'verifier-value',
        }))
        request.session['x_oauth1_request_token'] = 'request-token'
        request.session['x_oauth1_request_token_secret'] = 'request-secret'
        request.session['x_oauth1_user_id'] = str(self.user.id)
        request.session['x_oauth1_workspace_id'] = str(self.workspace.id)
        request.session.save()

        exchange = Mock()
        exchange.fetch_access_token.return_value = {
            'oauth_token': 'plain-access-token',
            'oauth_token_secret': 'plain-access-secret',
            'user_id': '123',
            'screen_name': 'voicespark',
        }
        verify = Mock()
        verify_response = Mock(status_code=200)
        verify_response.json.return_value = {'id_str': '123', 'screen_name': 'voicespark'}
        verify.get.return_value = verify_response

        with patch('x_auth.views.X_API_KEY', 'consumer-key'), \
             patch('x_auth.views.X_API_SECRET', 'consumer-secret'), \
             patch('x_auth.views.OAuth1Session', side_effect=[exchange, verify]):
            response = XCallbackView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        token = XToken.objects.get(user=self.user, workspace=self.workspace)
        self.assertNotEqual(token.access_token, 'plain-access-token')
        self.assertEqual(token.scopes, 'oauth1')
        self.assertEqual(get_x_oauth1_credentials(self.user, self.workspace), ('plain-access-token', 'plain-access-secret'))

    def test_post_tweet_uses_oauth1_with_v2_create_endpoint(self):
        nano = NanoBananaImage.objects.create(
            user=self.user,
            workspace=self.workspace,
            caption='Hello from tests',
            picture_url='',
            platform_captions={
                'twitter': 'Twitter caption',
                '__meta': {'approved_platforms': ['twitter']},
            },
        )
        XToken.objects.create(
            user=self.user,
            workspace=self.workspace,
            access_token='plain-access-token',
            refresh_token='plain-access-secret',
            scopes='oauth1',
        )
        session = Mock()
        post_response = Mock(status_code=201)
        post_response.json.return_value = {'data': {'id': 'tweet-123'}}
        session.post.return_value = post_response
        request = self.factory.post('/auth/x/tweet/', {
            'user_id': self.user.id,
            'nano_banana_id': str(nano.id),
        }, content_type='application/json')

        with patch('x_auth.views.X_API_KEY', 'consumer-key'), \
             patch('x_auth.views.X_API_SECRET', 'consumer-secret'), \
             patch('x_auth.views.OAuth1Session', return_value=session):
            response = post_tweet(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['external_post_id'], 'tweet-123')
        session.post.assert_called_once()
        self.assertEqual(session.post.call_args.args[0], 'https://api.x.com/2/tweets')
        self.assertEqual(session.post.call_args.kwargs['json'], {'text': 'Twitter caption'})
