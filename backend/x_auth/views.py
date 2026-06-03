import os
import base64
import json
import logging
import requests
import io
import time
import uuid
from datetime import timedelta
import mimetypes
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.conf import settings
from django.utils import timezone as django_timezone
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from requests_oauthlib import OAuth1Session

from workspace.models import Workspace
from .models import XToken
from .utils.security import generate_code_verifier, generate_code_challenge, generate_state
from .utils.token_store import decrypt_token, encrypt_token
from nano_banana.models import NanoBananaImage
from utils.public_urls import public_media_url

logger = logging.getLogger(__name__)

X_CLIENT_ID = os.getenv("X_CLIENT_ID")
X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET")
DEFAULT_BACKEND_URL = (
    os.getenv("PUBLIC_BACKEND_URL")
    or os.getenv("BACKEND_URL")
    or "https://api.voicespark.ai"
).rstrip("/")
X_REDIRECT_URI = os.getenv("X_REDIRECT_URI") or os.getenv("X_OAUTH1_CALLBACK") or f"{DEFAULT_BACKEND_URL}/auth/x/callback/"
X_AUTH_URL = "https://x.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_OAUTH_SCOPES = os.getenv("X_OAUTH_SCOPES", "tweet.read tweet.write users.read offline.access media.write")

# OAuth 1.0a (Legacy for media fallback if needed)
X_API_KEY = os.getenv("X_CONSUMER_KEY")
X_API_SECRET = os.getenv("X_CONSUMER_SECRET")
X_OAUTH1_REQUEST_TOKEN_URL = "https://api.x.com/oauth/request_token"
X_OAUTH1_AUTHORIZE_URL = "https://api.x.com/oauth/authorize"
X_OAUTH1_ACCESS_TOKEN_URL = "https://api.x.com/oauth/access_token"
X_OAUTH1_VERIFY_CREDENTIALS_URL = "https://api.x.com/1.1/account/verify_credentials.json"
X_OAUTH1_MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
X_POST_CREATE_URL = "https://api.x.com/2/tweets"


def decrypt_stored_token(value):
    if not value:
        return None
    try:
        return decrypt_token(value)
    except Exception:
        return value


def encrypted_token_value(value):
    if not value:
        return value
    try:
        decrypt_token(value)
        return value
    except Exception:
        return encrypt_token(value)


def workspace_for_user(user, workspace_id):
    if not user or not workspace_id:
        return None
    try:
        workspace_uuid = uuid.UUID(str(workspace_id))
    except (TypeError, ValueError, AttributeError):
        return None
    return (
        Workspace.objects
        .filter(id=workspace_uuid)
        .filter(Q(owner=user) | Q(memberships__user=user))
        .distinct()
        .first()
    )


def json_error(message, status_code=400):
    return JsonResponse({"error": message}, status=status_code)


def x_oauth1_configured():
    return bool(X_API_KEY and X_API_SECRET and X_REDIRECT_URI)


def get_x_oauth1_credentials(user, workspace):
    token_obj = XToken.objects.filter(user=user, workspace=workspace, scopes='oauth1').first()
    if not token_obj:
        return None, None
    return decrypt_stored_token(token_obj.access_token), decrypt_stored_token(token_obj.refresh_token)

# ── Token Refresh Helper ──────────────────────────────────────────────────

def refresh_x_token(token_obj):
    """
    Refresh the X OAuth 2.0 access token using the refresh token.
    """
    refresh_token = decrypt_stored_token(token_obj.refresh_token)
    if not refresh_token:
        logger.error(f"No refresh token for XToken ID {token_obj.id}")
        return None

    credentials = base64.b64encode(f"{X_CLIENT_ID}:{X_CLIENT_SECRET}".encode()).decode()
    
    try:
        response = requests.post(
            X_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"X token refresh failed: {response.text}")
            return None

        tokens = response.json()
        token_obj.access_token = encrypted_token_value(tokens["access_token"])
        if tokens.get("refresh_token"):
            token_obj.refresh_token = encrypted_token_value(tokens["refresh_token"])
        
        expires_in = tokens.get("expires_in", 7200)
        token_obj.expires_at = django_timezone.now() + timedelta(seconds=expires_in)
        token_obj.scopes = tokens.get("scope", getattr(token_obj, 'scopes', ''))
        token_obj.save()
        
        logger.info(f"X token refreshed successfully for user {token_obj.user.id}")
        return token_obj.access_token
    except Exception as e:
        logger.exception(f"Error refreshing X token: {str(e)}")
        return None

def get_valid_x_token(user, workspace):
    """
    Get a valid access token, refreshing if necessary.
    """
    token_obj = XToken.objects.filter(user=user, workspace=workspace).first()
    if not token_obj:
        return None

    # Check if expired (with 1 minute buffer)
    if not token_obj.expires_at or token_obj.expires_at <= django_timezone.now() + timedelta(minutes=1):
        return refresh_x_token(token_obj)
    
    return decrypt_stored_token(token_obj.access_token)

# ── View 1: Start OAuth 2.0 PKCE Flow ─────────────────────────────────────

class XLoginView(View):
    def get(self, request):
        user_id = request.GET.get("user_id")
        workspace_id = request.GET.get("workspace_id")

        if not user_id or not workspace_id:
            return json_error("user_id and workspace_id are required.")
        if not x_oauth1_configured():
            return json_error("X OAuth 1.0a is not configured for this environment.", 503)
        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return json_error("Invalid user_id.")
        workspace = workspace_for_user(user, workspace_id)
        if not workspace:
            return json_error("Invalid workspace_id for this user.")

        try:
            oauth = OAuth1Session(
                X_API_KEY,
                client_secret=X_API_SECRET,
                callback_uri=X_REDIRECT_URI,
            )
            request_token = oauth.fetch_request_token(X_OAUTH1_REQUEST_TOKEN_URL)
            oauth_token = request_token.get("oauth_token")
            oauth_token_secret = request_token.get("oauth_token_secret")
            callback_confirmed = request_token.get("oauth_callback_confirmed")
            if not oauth_token or not oauth_token_secret or callback_confirmed not in (True, "true", "True"):
                logger.error("X OAuth1 request token response was incomplete.")
                return json_error("X OAuth request token failed.", 502)

            request.session["x_oauth1_request_token"] = oauth_token
            request.session["x_oauth1_request_token_secret"] = oauth_token_secret
            request.session["x_oauth1_user_id"] = str(user.id)
            request.session["x_oauth1_workspace_id"] = str(workspace.id)
            request.session.save()

            auth_url = oauth.authorization_url(X_OAUTH1_AUTHORIZE_URL)
            logger.info("Redirecting user %s workspace %s to X OAuth1.", user.id, workspace.id)
            return redirect(auth_url)
        except Exception:
            logger.exception("X OAuth1 login failed.")
            return json_error("X OAuth login failed. Please confirm the Consumer Key, callback URL, and app permissions.", 502)

# ── View 2: OAuth 2.0 Callback ──────────────────────────────────────────

class XCallbackView(View):
    def get(self, request):
        oauth_token = request.GET.get("oauth_token")
        oauth_verifier = request.GET.get("oauth_verifier")
        denied = request.GET.get("denied")

        if denied:
            return json_error("X authorization was denied.")
        if not oauth_token or not oauth_verifier:
            return json_error("Missing OAuth token or verifier.")

        session_token = request.session.get("x_oauth1_request_token")
        token_secret = request.session.get("x_oauth1_request_token_secret")
        user_id = request.session.get("x_oauth1_user_id")
        workspace_id = request.session.get("x_oauth1_workspace_id")

        if not session_token or session_token != oauth_token or not token_secret or not user_id or not workspace_id:
            return json_error("OAuth session expired or invalid. Please reconnect X.", 400)

        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return json_error("Invalid user_id.")
        workspace = workspace_for_user(user, workspace_id)
        if not workspace:
            return json_error("Invalid workspace_id for this user.")

        try:
            oauth = OAuth1Session(
                X_API_KEY,
                client_secret=X_API_SECRET,
                resource_owner_key=oauth_token,
                resource_owner_secret=token_secret,
                verifier=oauth_verifier,
            )
            tokens = oauth.fetch_access_token(X_OAUTH1_ACCESS_TOKEN_URL)
            access_token = tokens.get("oauth_token")
            access_token_secret = tokens.get("oauth_token_secret")
            if not access_token or not access_token_secret:
                return json_error("X access token response was incomplete.", 400)

            x_user_id = tokens.get("user_id")
            username = tokens.get("screen_name")
            verify = OAuth1Session(
                X_API_KEY,
                client_secret=X_API_SECRET,
                resource_owner_key=access_token,
                resource_owner_secret=access_token_secret,
            )
            me_resp = verify.get(X_OAUTH1_VERIFY_CREDENTIALS_URL, params={"skip_status": "true"}, timeout=30)
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                x_user_id = me_data.get("id_str") or x_user_id
                username = me_data.get("screen_name") or username

            XToken.objects.update_or_create(
                user=user,
                workspace=workspace,
                defaults={
                    "access_token": encrypted_token_value(access_token),
                    "refresh_token": encrypted_token_value(access_token_secret),
                    "expires_at": None,
                    "scopes": "oauth1",
                    "x_user_id": x_user_id,
                    "username": username,
                }
            )

            for key in (
                "x_oauth1_request_token",
                "x_oauth1_request_token_secret",
                "x_oauth1_user_id",
                "x_oauth1_workspace_id",
            ):
                request.session.pop(key, None)

            return HttpResponse("""
                <html>
                    <body>
                        <script>
                            window.opener.postMessage("x_login_success", "*");
                            window.close();
                        </script>
                        X account connected successfully. You can close this window.
                    </body>
                </html>
            """)

        except Exception as e:
            logger.exception(f"Error in X callback: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

# ── Media Upload & Posting Logic ──────────────────────────────────────────

def upload_x_media(access_token, access_token_secret, image_url):
    """
    Download image from URL and upload to X media endpoint using OAuth 1.0a.
    """
    try:
        image_url = public_media_url(image_url)
        if not image_url:
            return None
        # 1. Download image
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        img_data = img_resp.content
        content_type = img_resp.headers.get("Content-Type") or mimetypes.guess_type(image_url)[0] or "image/jpeg"

        oauth = OAuth1Session(
            X_API_KEY,
            client_secret=X_API_SECRET,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
        files = {
            "media": ("image", img_data, content_type)
        }
        response = oauth.post(X_OAUTH1_MEDIA_UPLOAD_URL, files=files, timeout=60)
        
        if response.status_code not in (200, 201):
            logger.error("X OAuth1 media upload failed status=%s body=%s", response.status_code, response.text[:500])
            return None

        media_id = response.json().get("media_id_string") or response.json().get("media_id")
        return media_id
    except Exception as e:
        logger.exception(f"Exception during X media upload: {str(e)}")
        return None

@api_view(['POST'])
@csrf_exempt
def post_tweet(request):
    """
    Unified post handler for X using API v2.
    """
    data = request.data
    user_id = data.get('user_id')
    nano_banana_id = data.get('nano_banana_id') or data.get('nana_banana_id')
    
    if not user_id or not nano_banana_id:
        return Response({"error": "Missing user_id or nano_banana_id"}, status=400)

    try:
        user = User.objects.get(id=user_id)
        nano_banana = NanoBananaImage.objects.get(id=nano_banana_id)
        workspace = nano_banana.workspace

        # Enforcement: Check if 'twitter' or 'x' is in approved_platforms
        from auth_user.views_schedule import normalize_platforms, nano_meta
        meta = nano_meta(nano_banana)
        approved = normalize_platforms(meta.get('approved_platforms'))
        if 'twitter' not in approved and 'x' not in approved:
            logger.info(f"X publish skipped: Not in approved platforms for nano_banana {nano_banana.id}")
            return Response({"message": "Platform not approved"}, status=200)

        access_token, access_token_secret = get_x_oauth1_credentials(user, workspace)
        if not access_token or not access_token_secret:
            return Response({"error": "X not connected. Please reconnect X."}, status=status.HTTP_401_UNAUTHORIZED)

        # Prepare Content
        captions = nano_banana.platform_captions or {}
        text = captions.get('twitter') or captions.get('x') or nano_banana.caption or "Posted via VoiceSpark"
        image_url = nano_banana.picture_url

        payload = {"text": text}
        
        # Handle Image
        if image_url:
            media_id = upload_x_media(access_token, access_token_secret, image_url)
            if media_id:
                payload["media"] = {"media_ids": [str(media_id)]}
            else:
                return Response({"error": "X media upload failed."}, status=502)

        oauth = OAuth1Session(
            X_API_KEY,
            client_secret=X_API_SECRET,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
        response = oauth.post(
            X_POST_CREATE_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        if response.status_code not in (200, 201):
            logger.error("X OAuth1 post failed status=%s body=%s", response.status_code, response.text[:500])
            return Response(
                {"error": response.text or f"X API returned HTTP {response.status_code}", "status_code": response.status_code},
                status=response.status_code,
            )

        result = response.json()
        tweet_id = result.get("data", {}).get("id") or result.get("id_str") or result.get("id")
        
        return Response({
            "message": "Tweet posted successfully!",
            "id": tweet_id,
            "external_post_id": tweet_id,
            "url": f"https://x.com/i/status/{tweet_id}"
        }, status=201)

    except Exception as e:
        logger.exception(f"Unexpected error in X publishing: {str(e)}")
        return Response({"error": str(e)}, status=500)

class PostTweetView(View):
    @method_decorator(csrf_exempt)
    def post(self, request):
        return post_tweet(request)

class XOAuth1LoginView(XLoginView):
    pass

class XOAuth1CallbackView(XCallbackView):
    pass
