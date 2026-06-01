# views.py
import base64
import json
import logging
import secrets
import requests
from html import escape
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from requests_oauthlib.compliance_fixes import facebook

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import redirect

from dotenv import load_dotenv
import os


from nano_banana.models import NanoBananaImage
from workspace.models import Workspace
from x_auth.models import XToken
from linkedin_auth.models import LinkedinToken
from .models import FacebookUser, FacebookToken, InstagramUser, InstagramToken, FacebookPage
from utils.public_urls import public_media_url as shared_public_media_url

logger = logging.getLogger(__name__)


def graph_error_message(response, fallback='Meta request failed.'):
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    error = payload.get('error') if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get('message') or fallback
        code = error.get('code')
        subcode = error.get('error_subcode')
        if code or subcode:
            return f"{message} (code={code}, subcode={subcode})"
        return message
    return response.text or fallback


def validate_facebook_page_token(page):
    if not page.access_token:
        return False, 'Facebook Page token is missing.', {}
    try:
        response = requests.get(
            f'https://graph.facebook.com/v19.0/{page.page_id}',
            params={
                'fields': 'id,name,instagram_business_account',
                'access_token': page.access_token,
            },
            timeout=8,
        )
    except requests.RequestException as exc:
        return False, f'Unable to validate Facebook Page connection: {exc}', {}
    if response.status_code >= 400:
        return False, graph_error_message(response, 'Facebook Page connection is not valid.'), {}
    try:
        return True, None, response.json()
    except ValueError:
        return False, 'Facebook Page validation returned an invalid response.', {}


def sync_facebook_pages(user, workspace, access_token):
    try:
        resp = requests.get(
            "https://graph.facebook.com/v19.0/me/accounts",
            params={"access_token": access_token},
            timeout=10
        )
    except requests.RequestException as exc:
        return False, f'Failed to fetch Facebook pages: {exc}', []
    if resp.status_code >= 400:
        return False, graph_error_message(resp, 'Failed to fetch Facebook pages.'), []

    pages_data = resp.json()
    pages = pages_data.get('data', []) if isinstance(pages_data, dict) else []
    if not pages:
        FacebookPage.objects.filter(user=user, workspace=workspace).delete()
        return False, (
            'No publishable Facebook Page was returned by Meta. '
            'Reconnect with a Page admin/editor/moderator account and enable Facebook two-factor authentication if the business requires it.'
        ), []

    valid_pages = []
    errors = []
    returned_page_ids = [str(pg.get('id')) for pg in pages if pg.get('id')]
    FacebookPage.objects.filter(user=user, workspace=workspace).exclude(page_id__in=returned_page_ids).delete()
    for pg in pages:
        if not pg.get('id'):
            continue
        fb_page = FacebookPage.objects.filter(
            user=user,
            page_id=pg['id'],
            workspace=workspace,
        ).first()
        if fb_page is None:
            fb_page = FacebookPage(user=user, page_id=pg['id'], workspace=workspace)
        fb_page.name = pg.get('name', '')
        fb_page.access_token = pg.get('access_token', '')
        fb_page.category = pg.get('category', '')
        fb_page.tasks = pg.get('tasks', [])
        fb_page.workspace = workspace
        fb_page.save()

        is_valid, page_error, _ = validate_facebook_page_token(fb_page)
        if is_valid:
            valid_pages.append(fb_page)
        else:
            errors.append(page_error)
            fb_page.delete()

    if not valid_pages:
        return False, errors[0] if errors else 'No valid Facebook Page connection was available for publishing.', []
    return True, None, valid_pages


META_AUTH_URL  = "https://www.facebook.com/v19.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
META_USER_URL  = "https://graph.facebook.com/v19.0/me"
load_dotenv()
META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI")
INSTAGRAM_REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI", META_REDIRECT_URI)
FACEBOOK_CONFIG_ID = os.getenv("FACEBOOK_CONFIG_ID")
INSTAGRAM_CONFIG_ID = os.getenv("INSTAGRAM_CONFIG_ID")


def public_media_url(value, request=None):
    return shared_public_media_url(value)


def with_optional_config_id(params, config_id):
    if config_id:
        params['config_id'] = config_id
    return params

# ── Step 1 — Initiate login ───────────────────────────────────────────────────
def encode_state(user_id: int, platform: str = "facebook", workspace_id: str = "") -> str:
    """
    Pack a random nonce + user_id into a base64 string for the OAuth state param.
    e.g. {"nonce": "abc123", "user_id": 1}  →  base64
    """
    payload = {
        'nonce': secrets.token_urlsafe(24),  # CSRF protection
        'user_id': user_id,
        'platform': platform,
        'workspace_id': workspace_id,
    }
    return base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode()


def decode_state(state: str) -> dict:
    """
    Decode the state string back to {"nonce": ..., "user_id": ...}.
    Returns {} on any error.
    """
    try:
        return json.loads(base64.urlsafe_b64decode(state.encode()))
    except Exception:
        return {}


# @api_view(['GET'])
# @permission_classes([AllowAny])
# def meta_login(request):
class MetaLogin(APIView):
    def get(self, request):
        """
        GET /auth/meta/login/

        Builds the Meta OAuth URL and returns it as JSON.
        Your frontend should redirect the browser to `auth_url`.
        """
        user_id = request.query_params.get("user_id", "1")
        platform = request.query_params.get("platform", "facebook")
        workspace_id = request.query_params.get("workspace_id", "")
        try:
            user_id = int(user_id)
            User.objects.get(pk=user_id)  # make sure the user actually exists
        except (ValueError, User.DoesNotExist):
            return Response({'error': f'No user found with id={user_id}.'},
                            status=status.HTTP_404_NOT_FOUND)

        state = encode_state(user_id, platform, workspace_id)


        # state = secrets.token_urlsafe(32)
        request.session['meta_state'] = state          # saved for CSRF check in callback
        request.session['platform'] = platform
        request.session['workspace_id'] = workspace_id
        if platform == 'facebook':
            params = with_optional_config_id({
                'client_id':     META_APP_ID,
                'redirect_uri':  META_REDIRECT_URI,
                'scope':         'email,public_profile,pages_manage_posts,pages_read_engagement,pages_show_list',
                'response_type': 'code',
                'state':         state,
            }, FACEBOOK_CONFIG_ID)
            #
            auth_url = f"{META_AUTH_URL}?{urlencode(params)}"
            return redirect(auth_url)
        elif platform == 'instagram':
            params = with_optional_config_id({
                'client_id':     META_APP_ID,
                'redirect_uri':  META_REDIRECT_URI,
                'scope':         'email,public_profile,pages_show_list,pages_read_engagement,instagram_manage_insights,instagram_content_publish',
                'response_type': 'code',
                'state':         state,
            }, INSTAGRAM_CONFIG_ID)
            #
            auth_url = f"{META_AUTH_URL}?{urlencode(params)}"
            return redirect(auth_url)
        return JsonResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR,data={'error':'platform incompatible'})
        # return Response({'auth_url': auth_url})
        # print(auth_url)




# ── Step 2 — Handle callback from Meta ───────────────────────────────────────

# @api_view(['GET'])
# @permission_classes([AllowAny])
# def meta_callback(request):
class MetaCallback(APIView):
    def get(self, request):
        def popup_response(message, success=False, status_code=200):
            event = "fb_login_success" if success else "fb_login_failure"
            safe_message = escape(str(message))
            response = HttpResponse(f"""
                <html>
                    <body>
                        <script>
                            (function () {{
                                try {{
                                    if (window.opener && !window.opener.closed) {{
                                        window.opener.postMessage({json.dumps(event)}, "*");
                                    }}
                                }} catch (error) {{}}
                                window.close();
                                setTimeout(function () {{
                                    window.close();
                                    document.body.innerHTML = "{safe_message}<br/>This window can be closed.";
                                }}, 300);
                            }})();
                        </script>
                        <noscript>
                            {safe_message}
                        </noscript>
                    </body>
                </html>
            """, status=status_code)
            response["Cross-Origin-Opener-Policy"] = "unsafe-none"
            return response



        # ── 1. Check for errors from Meta ────────────────────────────
        if request.GET.get('error'):
            return popup_response(
                request.GET.get('error_description', 'Meta login was denied.'),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        code  = request.GET.get('code')
        state = request.GET.get('state')
        state_data = decode_state(state) if state else {}

        if not code:
            return popup_response('Missing code parameter.', status_code=status.HTTP_400_BAD_REQUEST)

        # ── 2. Validate state (CSRF) ──────────────────────────────────
        saved_state = request.session.pop('meta_state', None)
        if saved_state and saved_state != state:
            return popup_response('Invalid state. Possible CSRF attack.', status_code=status.HTTP_400_BAD_REQUEST)
        if not state_data.get('user_id'):
            return popup_response('Invalid OAuth state.', status_code=status.HTTP_400_BAD_REQUEST)

        # ── 3. Exchange code → access token ──────────────────────────
        try:
            token_resp = requests.get(META_TOKEN_URL, params={
                'client_id':     META_APP_ID,
                'client_secret': META_APP_SECRET,
                'redirect_uri':  META_REDIRECT_URI,
                'code':          code,
            }, timeout=10)
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get('access_token')
            token_type   = token_data.get('token_type', 'bearer')
            expires_in   = token_data.get('expires_in')          # seconds until expiry
        except requests.RequestException as exc:
            return popup_response(
                f'Token exchange failed: {exc}',
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        if not access_token:
            return popup_response('No access token returned by Meta.', status_code=status.HTTP_400_BAD_REQUEST)

        # ── 4. Fetch user profile from Graph API ──────────────────────
        try:
            user_resp = requests.get(META_USER_URL, params={
                'fields':       'id,name,email,first_name,last_name,picture.type(large)',
                'access_token': access_token,
            }, timeout=10)
            user_resp.raise_for_status()
            meta_user = user_resp.json()
        except requests.RequestException as exc:
            return popup_response(
                f'Failed to fetch Meta profile: {exc}',
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        meta_id    = meta_user.get('id')
        email      = meta_user.get('email', '')
        first_name = meta_user.get('first_name', '')
        last_name  = meta_user.get('last_name', '')
        full_name   = meta_user.get('name', '')
        picture_url = meta_user.get('picture', {}).get('data', {}).get('url', '')


        if not meta_id:
            return popup_response('Could not retrieve Meta user ID.', status_code=status.HTTP_400_BAD_REQUEST)

        # ── 5. Create or update Django User ──────────────────────────
        #
        # Strategy: use meta_id as a stable unique key stored in username
        # (or swap for a SocialProfile model if you need to store more data).
        #

        user_id    = state_data.get('user_id')
        username = f"meta_{meta_id}"
        is_new   = False

        try:
            user = User.objects.get(id=int(user_id))
        except (TypeError, ValueError, User.DoesNotExist) as exc:
            return popup_response(
                f'Unable to load local user for Meta callback: {exc}',
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        # if created:
        #     is_new = True
        #     user.set_unusable_password()        # no password — OAuth only

        # Always keep profile fields fresh
        platform = request.session.pop('platform', None) or state_data.get('platform')
        workspace_id = request.session.pop('workspace_id', None) or state_data.get('workspace_id')
        workspace = Workspace.objects.filter(id=workspace_id).first() if workspace_id else None

        if platform == 'facebook':
            try:
                fb_user, created = FacebookUser.objects.get_or_create(
                    user=user,
                    defaults={'facebook_id': meta_id},
                )
                if email:
                    fb_user.email = email
                fb_user.first_name  = first_name
                fb_user.last_name   = last_name
                fb_user.full_name   = full_name
                fb_user.picture_url = picture_url
                fb_user.facebook_id = meta_id
                fb_user.workspace = workspace
                fb_user.save()

                # user.first_name = first_name
                # user.last_name  = last_name
                # user.save()
                FacebookToken.objects.update_or_create(
                    user=user,
                    defaults={
                        'access_token': access_token,
                        'token_type':   token_type,
                        'expires_in':   expires_in,
                        'workspace':    workspace
                    },
                )
            except Exception as exc:
                return popup_response(
                    f'Failed to save Facebook account: {exc}',
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            pages_ok, pages_error, valid_pages = sync_facebook_pages(user, workspace, access_token)
            if pages_ok:
                return popup_response(
                    'Facebook Page Login successful. You can close this window.',
                    success=True,
                )
            return popup_response(
                f'Facebook Page Login unsuccessful. {pages_error}',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

            return JsonResponse({'page': [page.page_id for page in valid_pages]})



        elif platform == 'instagram':
            try:
                insta_user, created = InstagramUser.objects.get_or_create(
                    user=user,
                    defaults={'instagram_id': meta_id},
                )
                if email:
                    insta_user.email = email
                insta_user.instagram_id = meta_id
                insta_user.first_name = first_name
                insta_user.last_name = last_name
                insta_user.full_name = full_name
                insta_user.picture_url = picture_url
                insta_user.workspace = workspace
                insta_user.save()

                # user.first_name = first_name
                # user.last_name  = last_name
                # user.save()
                InstagramToken.objects.update_or_create(
                    user=user,
                    defaults={
                        'access_token': access_token,
                        'token_type': token_type,
                        'expires_in': expires_in,
                        'workspace': workspace,
                    },
                )
            except Exception as exc:
                return popup_response(
                    f'Failed to save Instagram account: {exc}',
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            if not FacebookPage.objects.filter(user=user, workspace=workspace).exists():
                pages_ok, pages_error, _ = sync_facebook_pages(user, workspace, access_token)
                if not pages_ok:
                    return popup_response(
                        f'Instagram Login saved, but publishing is not ready. {pages_error}',
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                invalid_errors = []
                for page in FacebookPage.objects.filter(user=user, workspace=workspace):
                    is_valid, page_error, page_data = validate_facebook_page_token(page)
                    if not is_valid:
                        invalid_errors.append(page_error)
                        page.delete()
                if invalid_errors:
                    return popup_response(
                        f'Instagram Login saved, but publishing is not ready. {invalid_errors[0]}',
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            return popup_response(
                'Instagram Login successful. You can close this window.',
                success=True,
            )
        else:
            return popup_response('Platform incompatible.', status_code=status.HTTP_400_BAD_REQUEST)
        # ── 6. Return DRF token ───────────────────────────────────────
        # token, _ = Token.objects.get_or_create(user=user)

        return JsonResponse({
            # 'token':  token.key,
            'is_new': is_new,
            'user': {
                'id':         user.id,
                # 'username':   fb_user.username,
                'email':      email,
                'first_name': first_name,
                'last_name':  last_name,
            },
        }, status=status.HTTP_200_OK)

class FacebookPostView(APIView):
    """
    POST /api/facebook/post/
    Uploads an image + caption to the authenticated user's Facebook feed.
    """
    # permission_classes = [IsAuthenticated]
    # parser_classes     = [MultiPartParser, FormParser]   # needed for file uploads


    # ------------------------------------------------------------------ #
    #  POST handler                                                        #
    # ------------------------------------------------------------------ #

    def post(self, request, *args, **kwargs):
        # ── 1. Validate incoming data ──────────────────────────────────
        # image = request.FILES.get("image")
        # caption = request.data.get("caption", "").strip()
        user_id = request.data.get("user_id", "2")
        nano_banana_id = request.data.get("nano_banana_id", "")
        user = User.objects.get(id=int(user_id))
        nano_banana = NanoBananaImage.objects.filter(id=nano_banana_id).first()
        if nano_banana is None:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        caption = (nano_banana.platform_captions or {}).get('facebook') or nano_banana.caption
        facebook_page = FacebookPage.objects.filter(user=user, workspace=nano_banana.workspace)

        if not facebook_page.exists():
            return Response({'error': 'Facebook page not connected for this workspace'}, status=status.HTTP_404_NOT_FOUND)

        image_url = public_media_url(nano_banana.picture_url, request=request)
        if not image_url:
            return Response({'error': 'Facebook post image URL is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        published_posts = []
        for fb_page in facebook_page:
            url = f"https://graph.facebook.com/v19.0/{fb_page.page_id}/photos"

            response = requests.post(
                url,
                data={
                    "url": image_url,
                    "message": caption,
                    "access_token": fb_page.access_token,
                    "published": False,
                }
            )

            if response.status_code != 200:
                error_detail = graph_error_message(response, 'Facebook photo upload failed.')
                logger.error("Facebook photo upload failed for page %s: %s", fb_page.page_id, error_detail)
                return Response({'error': error_detail}, status=status.HTTP_502_BAD_GATEWAY)

            photo_id = response.json().get('id')

            url = f"https://graph.facebook.com/v19.0/{fb_page.page_id}/feed"

            response = requests.post(
                url,
                json={
                    "message": caption,
                    "attached_media": [{"media_fbid": photo_id}],
                    "access_token": fb_page.access_token,
                }
            )

            if response.status_code >= 400:
                error_detail = graph_error_message(response, 'Facebook feed publish failed.')
                logger.error("Facebook feed publish failed for page %s: %s", fb_page.page_id, error_detail)
                return Response({'error': error_detail}, status=status.HTTP_502_BAD_GATEWAY)
            feed_data = response.json()
            post_id = feed_data.get('id')
            published_posts.append({
                'page_id': fb_page.page_id,
                'post_id': post_id,
                'photo_id': photo_id,
            })


        # ── 5. Success ─────────────────────────────────────────────────
        return Response(
            {
                "message":  "Photo posted to Facebook successfully.",
                "external_post_id": published_posts[0].get('post_id') if published_posts else None,
                "post_id": published_posts[0].get('post_id') if published_posts else None,
                "posts": published_posts,
            },
            status=status.HTTP_201_CREATED,
        )

class InstagramPostView(APIView):
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id", "2")
        nano_banana_id = request.data.get("nano_banana_id")
        user = User.objects.get(id=int(user_id))
        nano_banana = NanoBananaImage.objects.filter(id=nano_banana_id).first()
        if nano_banana is None:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        caption = (nano_banana.platform_captions or {}).get('instagram') or nano_banana.caption
        facebook_page = FacebookPage.objects.filter(user=user, workspace=nano_banana.workspace).first()
        insta_token = InstagramToken.objects.filter(user=user, workspace=nano_banana.workspace).first()
        if facebook_page and insta_token:
            image_url = public_media_url(nano_banana.picture_url, request=request)
            if not image_url:
                return Response({'error': 'Instagram post image URL is missing.'}, status=status.HTTP_400_BAD_REQUEST)

            def get_instagram_account_id(page_id, page_access_token):
                url = f"https://graph.facebook.com/v19.0/{page_id}"

                response = requests.get(
                    url,
                    params={
                        "fields": "instagram_business_account",
                        "access_token": page_access_token,
                    }
                )

                if response.status_code >= 400:
                    return None, graph_error_message(response, 'Unable to load Instagram Business account from Facebook Page.')
                data = response.json()
                instagram_account = data.get("instagram_business_account") or {}
                instagram_account_id = instagram_account.get("id")
                if not instagram_account_id:
                    return None, 'Selected Facebook Page is not linked to an Instagram Business account.'
                return instagram_account_id, None

            # Usage
            instagram_account_id, account_error = get_instagram_account_id(
                page_id=facebook_page.page_id,
                page_access_token=facebook_page.access_token,
            )
            if account_error:
                return Response({'error': account_error}, status=status.HTTP_400_BAD_REQUEST)

            # print(instagram_account_id)

            # Step 1: Create media container
            def create_media_container(image_url, caption=""):
                url = f"https://graph.facebook.com/v19.0/{instagram_account_id}/media"

                response = requests.post(
                    url,
                    data={
                        "image_url": image_url,  # Must be a publicly accessible URL
                        "caption": caption,
                        "access_token": facebook_page.access_token,
                    }
                )

                if response.status_code >= 400:
                    return None, graph_error_message(response, 'Instagram media container creation failed.')
                return response.json()["id"], None  # creation_id

            # Step 2: Publish the container
            def publish_media(creation_id):
                url = f"https://graph.facebook.com/v19.0/{instagram_account_id}/media_publish"

                response = requests.post(
                    url,
                    data={
                        "creation_id": creation_id,
                        "access_token": facebook_page.access_token,
                    }
                )

                if response.status_code >= 400:
                    return None, graph_error_message(response, 'Instagram media publish failed.')
                return response.json(), None

            # Usage
            try:
                creation_id, create_error = create_media_container(
                    image_url=image_url,
                    caption=caption
                )
                if create_error:
                    return Response({'error': create_error}, status=status.HTTP_502_BAD_GATEWAY)

                post, publish_error = publish_media(creation_id)
                if publish_error:
                    return Response({'error': publish_error}, status=status.HTTP_502_BAD_GATEWAY)
                # {'id': 'media_id'}
                media_id = post.get('id') if isinstance(post, dict) else None

            except requests.exceptions.HTTPError as e:
                error_detail = 'Instagram post failed.'
                response = getattr(e, 'response', None)
                if response is not None:
                    try:
                        error_detail = response.json().get('error') or response.text or error_detail
                    except ValueError:
                        error_detail = response.text or error_detail
                return Response(
                    {'error': error_detail},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            return Response(
                {
                    'message': 'Published to Instagram successfully',
                    'external_post_id': media_id,
                    'media_id': media_id,
                },
                status=status.HTTP_200_OK,
            )
        return Response({'error': 'Instagram not connected for this workspace'}, status=status.HTTP_404_NOT_FOUND)


class ConnectedAccountsView(APIView):
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        workspace_id = request.data.get("workspace_id")
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id=workspace_id).first() if workspace_id else None
        if user is None:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        facebook_pages = FacebookPage.objects.filter(user=user)
        if workspace is not None:
            facebook_pages = facebook_pages.filter(workspace=workspace)

        instagram_connected = InstagramToken.objects.filter(user=user)
        if workspace is not None:
            instagram_connected = instagram_connected.filter(workspace=workspace)

        # Include Twitter and LinkedIn status
        twitter_connected = XToken.objects.filter(user=user)
        if workspace is not None:
            twitter_connected = twitter_connected.filter(workspace=workspace)

        linkedin_connected = LinkedinToken.objects.filter(user=user)
        if workspace is not None:
            linkedin_connected = linkedin_connected.filter(workspace=workspace)

        validated_pages = []
        connection_errors = {}
        has_instagram_business_account = False
        for page in facebook_pages.order_by('name'):
            is_valid, page_error, page_data = validate_facebook_page_token(page)
            if not is_valid:
                connection_errors['facebook'] = page_error
                continue
            instagram_account = page_data.get('instagram_business_account') if isinstance(page_data, dict) else None
            has_instagram_business_account = has_instagram_business_account or bool(instagram_account)
            validated_pages.append({
                'id': str(page.id),
                'page_id': page.page_id,
                'name': page.name,
                'picture_url': f'https://graph.facebook.com/v19.0/{page.page_id}/picture?type=large',
                'instagram_business_account': instagram_account,
            })
        instagram_ready = instagram_connected.exists() and has_instagram_business_account
        if not validated_pages and not connection_errors.get('facebook') and FacebookToken.objects.filter(user=user, workspace=workspace).exists():
            connection_errors['facebook'] = (
                'Facebook account is connected, but Meta did not return a publishable Page. '
                'Reconnect with a Page admin/editor/moderator account and enable Facebook two-factor authentication if required.'
            )
        if instagram_connected.exists() and not has_instagram_business_account:
            connection_errors['instagram'] = 'Instagram is connected, but no Instagram Business account is linked to the selected Facebook Page.'

        return Response({
            'facebook_pages': validated_pages,
            'instagram_connected': instagram_ready,
            'connection_errors': connection_errors,
            'facebook': bool(validated_pages),
            'instagram': instagram_ready,
            'twitter': twitter_connected.exists(),
            'linkedin': linkedin_connected.exists(),
        }, status=status.HTTP_200_OK)
