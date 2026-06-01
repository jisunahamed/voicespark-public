import json
import logging
import re
import threading

from django.http import JsonResponse
from django.test import RequestFactory
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

import workspace
from utils.celery.tasks import make_posts
from datetime import datetime, timedelta, timezone
from django.contrib.auth.models import User
from nano_banana.views import ScheduleGeneratePost
from workspace.models import Workspace, WorkspaceMembership
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)

logger = logging.getLogger(__name__)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import UploadImages
from .serializers import UploadImagesSerializer

from .models import ImageUrl, UserProfile, UploadImages, ScheduledPost
from fb_auth.models import FacebookPage, FacebookToken, InstagramToken
from linkedin_auth.models import LinkedinToken
from x_auth.models import Auth1Xtoken, XToken
from utils.chatbot import ChatGPT
from utils.public_urls import public_media_url

DEFAULT_BRAND_STYLE = {
    "logos": [],
    "colors": [],
    "fonts": [
        {"role": "title", "family": "Inter", "weight": "Bold"},
        {"role": "body", "family": "Inter", "weight": "Regular"},
    ],
    "visual_identity": "",
    "visual_style": {"label": "Website Inspired", "image_url": ""},
}


def get_workspace_for_user(raw_workspace_id, user):
    if raw_workspace_id in (None, ''):
        return None, 'workspace_id is required.'
    workspace = Workspace.objects.filter(id=str(raw_workspace_id)).first()
    if not workspace:
        return None, 'Workspace not found.'
    if not user or not user.is_authenticated:
        return workspace, ''
    if workspace.owner_id == user.id or WorkspaceMembership.objects.filter(workspace=workspace, user=user).exists():
        return workspace, ''
    return None, 'You do not have access to this workspace.'


def request_user_from_payload(request):
    if request.user and request.user.is_authenticated:
        return request.user
    user_id = request.data.get('user_id', '')
    if user_id in (None, ''):
        return None
    try:
        return User.objects.filter(id=int(user_id)).first()
    except (TypeError, ValueError):
        return None

STYLE_ID_ALIASES = {
    "ultra-realistic": "ultra_realistic",
    "ultra realistic": "ultra_realistic",
    "photo": "ultra_realistic",
    "infographic": "infographic",
    "cartoon-animation": "cartoon_animated",
    "cartoon animated": "cartoon_animated",
    "cartoon / animated": "cartoon_animated",
    "product-studio": "product_studio",
    "product studio": "product_studio",
    "editorial-lifestyle": "editorial_lifestyle",
    "editorial lifestyle": "editorial_lifestyle",
}

DEFAULT_CONTENT_PREFERENCES = {
    "language": {"code": "en", "label": "English"},
    "content_style": {
        "id": "ultra_realistic",
        "name": "Ultra Realistic",
        "label": "Ultra Realistic",
        "image_url": "https://images.unsplash.com/photo-1556761175-b413da4baf72?w=900&q=85",
        "description": "Real humans, real places, natural light, premium commercial photography.",
        "prompt": "ultra-realistic commercial photography with real humans or real places, natural skin texture, authentic environments, premium lighting, no cartoon or illustration",
    },
    "timezone": "Asia/Dhaka",
    "default_schedule_time": "09:00",
    "smart_captions": {"enabled": True},
}


def normalize_media_url(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.split("#", 1)[0].split("?", 1)[0]
    return raw.rstrip("/")


def normalize_style_id(value):
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    spaced = raw.replace("_", " ")
    return STYLE_ID_ALIASES.get(raw) or STYLE_ID_ALIASES.get(spaced) or spaced.replace(" ", "_")


def normalize_visual_style(value, fallback=None):
    if not isinstance(value, dict):
        value = {}
    base = fallback if isinstance(fallback, dict) else {}
    normalized = {**base, **value}
    style_id = normalize_style_id(normalized.get("id"))
    normalized["id"] = style_id
    normalized["label"] = str(normalized.get("label") or normalized.get("name") or style_id.replace("_", " ").title())
    normalized["name"] = str(normalized.get("name") or normalized.get("label"))
    normalized["image_url"] = str(normalized.get("image_url") or normalized.get("image") or "")
    normalized["description"] = str(normalized.get("description") or "")
    normalized["prompt"] = str(normalized.get("prompt") or "")
    return normalized


def media_url_key(value):
    normalized = normalize_media_url(value)
    if not normalized:
        return ""
    try:
        from content_engine.services.intelligence import image_fingerprint
        return image_fingerprint(normalized)
    except Exception:
        key = normalized.lower()
        key = re.sub(r'[-_](?:\d{2,5}x\d{2,5}|\d{2,5}w|\d{2,5}h|scaled|copy)(?=\.)', '', key)
        key = re.sub(r'@\d+x(?=\.)', '', key)
        return key


def normalize_brand_style(value):
    if not isinstance(value, dict):
        value = {}
    normalized = {
        **DEFAULT_BRAND_STYLE,
        **value,
    }
    normalized["logos"] = [
        item for item in normalized.get("logos", [])
        if isinstance(item, dict) and item.get("url")
    ]
    normalized["colors"] = [
        str(color).strip() for color in normalized.get("colors", [])
        if str(color).strip()
    ][:12]
    fonts = normalized.get("fonts")
    if not isinstance(fonts, list) or not fonts:
        fonts = DEFAULT_BRAND_STYLE["fonts"]
    normalized["fonts"] = [
        {
            "role": str(font.get("role", "body")),
            "family": str(font.get("family", "Inter")),
            "weight": str(font.get("weight", "Regular")),
        }
        for font in fonts
        if isinstance(font, dict)
    ][:8]
    visual_style = normalized.get("visual_style")
    if not isinstance(visual_style, dict):
        visual_style = DEFAULT_BRAND_STYLE["visual_style"]
    normalized["visual_style"] = normalize_visual_style(visual_style, DEFAULT_BRAND_STYLE["visual_style"])
    normalized["visual_identity"] = str(normalized.get("visual_identity", ""))
    return normalized


def get_brand_style(user_profile):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    style = normalize_brand_style(brand_voice.get("brand_style", {}))
    try:
        from content_engine.models import BrandSetting, MediaAsset
        brand = BrandSetting.objects.filter(user=user_profile.user, workspace=user_profile.workspace).first()
        if brand:
            if isinstance(brand.font, dict):
                family = brand.font.get("family") or brand.font.get("displayName")
                weight = brand.font.get("weight") or "Bold"
                if family:
                    style["fonts"] = [
                        {"role": "title", "family": str(family), "weight": str(weight)},
                        {"role": "body", "family": str(family), "weight": "Regular"},
                    ]
            if not style.get("colors") and isinstance(brand.colors, list):
                style["colors"] = [str(color).strip() for color in brand.colors if str(color).strip()][:12]
            if not style.get("logos") and isinstance(brand.logos, list):
                style["logos"] = [
                    item if isinstance(item, dict) else {"url": str(item), "source": "website"}
                    for item in brand.logos
                    if (item.get("url") if isinstance(item, dict) else str(item or "").strip())
                ][:12]
            if not style.get("visual_identity") and brand.image_style:
                style["visual_identity"] = brand.image_style
            visual_style = style.get("visual_style") if isinstance(style.get("visual_style"), dict) else {}
            if isinstance(brand.recommended_visual_style, dict) and brand.recommended_visual_style and not visual_style.get("id"):
                style["visual_style"] = brand.recommended_visual_style
        if not style.get("logos"):
            logos = []
            for asset in MediaAsset.objects.filter(user=user_profile.user, workspace=user_profile.workspace, asset_type="image").order_by("-created_at")[:80]:
                metadata = asset.metadata if isinstance(asset.metadata, dict) else {}
                if metadata.get("label") == "logo" and asset.url:
                    logos.append({"url": asset.url, "source": "website"})
            if logos:
                style["logos"] = logos[:12]
    except Exception:
        pass
    return normalize_brand_style(style)


def save_brand_style(user_profile, brand_style):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    brand_voice["brand_style"] = normalize_brand_style(brand_style)
    preferences = normalize_content_preferences(brand_voice.get("content_preferences", {}))
    visual_style = brand_voice["brand_style"].get("visual_style") if isinstance(brand_voice["brand_style"].get("visual_style"), dict) else {}
    if visual_style.get("id"):
        preferences["content_style"] = visual_style
    brand_voice["content_preferences"] = preferences
    user_profile.brand_voice = brand_voice
    user_profile.save(update_fields=["brand_voice"])
    try:
        from content_engine.models import BrandSetting
        style = brand_voice["brand_style"]
        fonts = style.get("fonts") or []
        title_font = next((font for font in fonts if font.get("role") == "title"), fonts[0] if fonts else {})
        BrandSetting.objects.update_or_create(
            user=user_profile.user,
            workspace=user_profile.workspace,
            defaults={
                "colors": style.get("colors", []),
                "logos": style.get("logos", []),
                "font": {
                    "id": str(title_font.get("family", "Inter")).lower().replace(" ", "-"),
                    "displayName": title_font.get("family", "Inter"),
                    "family": title_font.get("family", "Inter"),
                    "weight": title_font.get("weight", "Bold"),
                },
                "image_style": style.get("visual_identity", ""),
                "recommended_visual_style": style.get("visual_style", {}),
            },
        )
    except Exception:
        pass
    return brand_voice["brand_style"]


def normalize_content_preferences(value):
    if not isinstance(value, dict):
        value = {}
    language = value.get("language") if isinstance(value.get("language"), dict) else {}
    content_style = value.get("content_style") if isinstance(value.get("content_style"), dict) else {}
    smart_captions = value.get("smart_captions") if isinstance(value.get("smart_captions"), dict) else {}
    timezone_name = str(value.get("timezone") or DEFAULT_CONTENT_PREFERENCES["timezone"]).strip()
    schedule_time = str(value.get("default_schedule_time") or DEFAULT_CONTENT_PREFERENCES["default_schedule_time"]).strip()
    if not re.match(r"^\d{2}:\d{2}$", schedule_time):
        schedule_time = DEFAULT_CONTENT_PREFERENCES["default_schedule_time"]
    normalized = {
        "language": {
            "code": str(language.get("code") or value.get("language_code") or DEFAULT_CONTENT_PREFERENCES["language"]["code"]),
            "label": str(language.get("label") or value.get("language_label") or DEFAULT_CONTENT_PREFERENCES["language"]["label"]),
        },
        "content_style": normalize_visual_style(content_style, DEFAULT_CONTENT_PREFERENCES["content_style"]),
        "timezone": timezone_name,
        "default_schedule_time": schedule_time,
        "smart_captions": {
            "enabled": bool(smart_captions.get("enabled", DEFAULT_CONTENT_PREFERENCES["smart_captions"]["enabled"])),
        },
    }
    return normalized


def get_content_preferences(user_profile):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    preferences = brand_voice.get("content_preferences", {})
    normalized = normalize_content_preferences(preferences)
    brand_style = normalize_brand_style(brand_voice.get("brand_style", {}))
    visual_style = brand_style.get("visual_style") if isinstance(brand_style.get("visual_style"), dict) else {}
    if visual_style.get("id") and (
        not isinstance(preferences, dict)
        or not isinstance(preferences.get("content_style"), dict)
        or not preferences.get("content_style", {}).get("id")
        or normalized.get("content_style", {}).get("id") == DEFAULT_CONTENT_PREFERENCES["content_style"]["id"]
    ):
        normalized["content_style"] = {
            **DEFAULT_CONTENT_PREFERENCES["content_style"],
            **visual_style,
            "label": visual_style.get("label") or visual_style.get("name") or visual_style.get("id"),
        }
    return normalized


def save_content_preferences(user_profile, preferences):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    normalized = normalize_content_preferences(preferences)
    brand_voice["content_preferences"] = normalized

    brand_style = normalize_brand_style(brand_voice.get("brand_style", {}))
    brand_style["visual_style"] = normalized["content_style"]
    brand_voice["brand_style"] = brand_style

    user_profile.brand_voice = brand_voice
    user_profile.save(update_fields=["brand_voice"])

    try:
        from content_engine.models import BrandSetting
        BrandSetting.objects.filter(user=user_profile.user, workspace=user_profile.workspace).update(
            recommended_visual_style=normalized["content_style"]
        )
    except Exception:
        pass
    return normalized

class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Returns access + refresh tokens alongside basic user info.
    """
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Creates a new user account and returns tokens immediately.
    """
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens for the newly registered user
        refresh = RefreshToken.for_user(user)
        refresh['username'] = user.username
        refresh['email'] = user.email

        return Response(
            {
                'message': 'Account created successfully.',
                'user': UserProfileSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklists the refresh token (client should also delete local tokens).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        except Exception:
            # Token invalid or already blacklisted — still treat as success
            return Response({'message': 'Logged out.'}, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/profile/  → return current user's profile
    PUT  /api/auth/profile/  → update profile fields
    PATCH /api/auth/profile/ → partial update
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

class MakeScheduledPost(APIView):
    def post(self, request):
        run_at = datetime.now(timezone.utc) + timedelta(seconds=5)
        payload = {
            'user_id':1,
        }
        make_posts.apply_async(
            args=[payload],
            eta=run_at
        )

        return Response(status= status.HTTP_200_OK)

class CreateUserProfile(APIView):
    def post(self, request):
        user_id = request.data.get("user_id", "1")
        website_url = request.data.get("website_url", "")
        markdown = request.data.get("markdown", "")
        image_urls = request.data.get('image_urls', [])
        brand_style = request.data.get('brand_style') or {}
        workspace_id = request.data.get('workspace_id', [])

        workspace = Workspace.objects.filter(id=workspace_id).first()
        if not workspace:
            return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=int(user_id)).first()
        user_profile, created = UserProfile.objects.get_or_create(
            user=user,
            workspace=workspace,
            defaults={
                'website_url': website_url,
                'markdown': markdown,
                'workspace':workspace,
            }
        )
        user_profile.website_url = website_url
        user_profile.markdown = markdown
        user_profile.workspace = workspace
        if brand_style:
            brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
            brand_voice['brand_style'] = normalize_brand_style(brand_style)
            user_profile.brand_voice = brand_voice
            user_profile.save(update_fields=['website_url', 'markdown', 'workspace', 'brand_voice'])
        else:
            user_profile.save(update_fields=['website_url', 'markdown', 'workspace'])

        # 3. Insert into ImageUrl (foreign key — multiple allowed)
        if image_urls:
            existing_keys = {
                media_url_key(url)
                for url in ImageUrl.objects.filter(user=user, workspace=workspace).values_list("image_url", flat=True)
                if media_url_key(url)
            }
            for img in image_urls:
                normalized_url = normalize_media_url(img)
                key = media_url_key(normalized_url)
                if not normalized_url or key in existing_keys:
                    continue
                ImageUrl.objects.create(
                    user=user,
                    image_url=normalized_url,
                    workspace= workspace
                )
                existing_keys.add(key)

        def call_schedule_in_background(user_id, user):
            try:
                factory = RequestFactory()
                internal_request = factory.post(
                    '/auth/user/create-brand-voice/',
                    data=json.dumps({'user_id': user_id, 'workspace_id':workspace_id}),
                    content_type='application/json'
                )
                internal_request.user = user
                create_brand_voice = CreateBrandVoice.as_view()
                create_brand_voice(internal_request)
            except Exception as exc:
                logger.warning("create brand voice background failed: %s", exc)

            # First-week calendar generation is handled by the content-engine
            # onboarding flow after the user confirms exact weekly counts.
            # Keeping the old hard-coded 3-post scheduler here creates
            # duplicate calendar posts when content-engine also generates.

        thread = threading.Thread(target=call_schedule_in_background, args=(user_id, user))
        thread.daemon = True  # dies if main process dies
        thread.start()
        # user_id = request.data.get("user_id", "1")
        # ###########
        # payload = {
        #     'user_id': user_id,
        # }
        # ############
        # factory = RequestFactory()
        # internal_request = factory.post(
        #     '/nano-banana/schedule-post/',
        #     data=json.dumps(payload),
        #     content_type='application/json'
        # )
        # internal_request.user = request.user  # pass current user
        # schedule_generate_post = ScheduleGeneratePost.as_view()
        # response = schedule_generate_post(internal_request)
        return Response(status= status.HTTP_200_OK)


class GetData(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        workspace_id = request.data.get('workspace_id', '')
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id = workspace_id).first()
        if not user or not workspace:
            return Response({'error': 'user_id and workspace_id are required.'}, status=status.HTTP_400_BAD_REQUEST)
        # UserProfile.objects.filter(user=user).first()
        image_urls = ImageUrl.objects.filter(user=user, workspace = workspace).order_by('created_at', 'id')
        try:
            from content_engine.models import CampaignWeek, MediaAsset
            assets = {
                media_url_key(asset.url): asset
                for asset in MediaAsset.objects.filter(user=user, workspace=workspace, asset_type='image')
            }
            referenced_keys = set()
            for week in CampaignWeek.objects.filter(content_plan__user=user, content_plan__workspace=workspace).only('item_plan'):
                item_plan = week.item_plan if isinstance(week.item_plan, dict) else {}
                raw_urls = []
                for value in (item_plan.get('thumbnail_url'),):
                    if value:
                        raw_urls.append(value)
                if isinstance(item_plan.get('reference_media'), list):
                    raw_urls.extend(item_plan.get('reference_media'))
                for prompt in item_plan.get('post_prompts', []) if isinstance(item_plan.get('post_prompts'), list) else []:
                    if not isinstance(prompt, dict):
                        continue
                    if prompt.get('reference_image'):
                        raw_urls.append(prompt.get('reference_image'))
                    if isinstance(prompt.get('reference_images'), list):
                        raw_urls.extend(prompt.get('reference_images'))
                    if isinstance(prompt.get('reference_media'), list):
                        raw_urls.extend(prompt.get('reference_media'))
                referenced_keys.update({media_url_key(url) for url in raw_urls if media_url_key(url)})
        except Exception:
            assets = {}
            referenced_keys = set()
        data=[]
        seen = set()
        duplicate_ids = []
        for img in image_urls:
            normalized_url = normalize_media_url(img.image_url)
            key = media_url_key(normalized_url)
            if not key or key in seen:
                duplicate_ids.append(img.id)
                continue
            seen.add(key)
            if normalized_url != img.image_url:
                img.image_url = normalized_url
                img.save(update_fields=['image_url'])
            asset = assets.get(key)
            metadata = asset.metadata if asset and isinstance(asset.metadata, dict) else {}
            data.append({
                'id': img.id,
                'src': normalized_url,
                'name': metadata.get('label') or metadata.get('alt') or 'image',
                'metadata': metadata,
                'source': asset.source if asset else 'upload',
                'used': key in referenced_keys,
            })
        if duplicate_ids:
            ImageUrl.objects.filter(id__in=duplicate_ids, user=user, workspace=workspace).delete()
        return JsonResponse(data={'data': data})

class DeleteMediaView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        media_id = request.data.get('media_id')
        workspace_id = request.data.get('workspace_id', '')
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id=workspace_id).first()
        image = ImageUrl.objects.filter(id=media_id, user=user, workspace=workspace).first()
        if image is None:
            return Response({'error': 'Media was not found.'}, status=status.HTTP_404_NOT_FOUND)
        image_url = image.image_url
        image.delete()
        upload = UploadImages.objects.filter(user=user, workspace=workspace, image=image_url).first()
        if upload:
            upload.delete()
        try:
            from content_engine.models import MediaAsset
            MediaAsset.objects.filter(user=user, workspace=workspace, url=image_url).delete()
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

class GetMarkdown(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        user = User.objects.filter(id=user_id).first()
        workspace_id = request.data.get('workspace_id', '')
        workspace = Workspace.objects.filter(id = workspace_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        data={
            'markdown':user_profile.markdown,
        }
        return JsonResponse(data=data)

class GetWebsiteLink(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        user = User.objects.filter(id=user_id).first()
        workspace_id = request.data.get('workspace_id', '')
        workspace = Workspace.objects.filter(id = workspace_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        data = {
            'website_url': user_profile.website_url,
        }
        return JsonResponse(data=data)


class SocialInsights(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        workspace_id = request.data.get('workspace_id', '')
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id=workspace_id).first()
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        scheduled_qs = ScheduledPost.objects.filter(user=user, workspace=workspace)
        posted_count = scheduled_qs.filter(approval='posted').count()
        scheduled_count = scheduled_qs.filter(approval='approved').count()
        review_count = scheduled_qs.filter(approval='not_approved').count()

        facebook_pages = FacebookPage.objects.filter(user=user, workspace=workspace).order_by('name')
        valid_facebook_pages = []
        facebook_error = None
        has_instagram_business_account = False
        try:
            from fb_auth.views import validate_facebook_page_token
            for page in facebook_pages:
                is_valid, page_error, page_data = validate_facebook_page_token(page)
                if not is_valid:
                    facebook_error = page_error
                    continue
                valid_facebook_pages.append(page)
                if isinstance(page_data, dict) and page_data.get('instagram_business_account'):
                    has_instagram_business_account = True
        except Exception as exc:
            facebook_error = f'Unable to validate Facebook connection: {exc}'
        facebook_page = valid_facebook_pages[0] if valid_facebook_pages else None
        if facebook_page is None and not facebook_error and FacebookToken.objects.filter(user=user, workspace=workspace).exists():
            facebook_error = (
                'Facebook account is connected, but Meta did not return a publishable Page. '
                'Reconnect with a Page admin/editor/moderator account and enable Facebook two-factor authentication if required.'
            )
        instagram_token_connected = InstagramToken.objects.filter(user=user, workspace=workspace).exists()
        instagram_error = None
        if instagram_token_connected and not has_instagram_business_account:
            instagram_error = 'Instagram is connected, but no Instagram Business account is linked to the selected Facebook Page.'
        data = {
            'x': {
                'connected': Auth1Xtoken.objects.filter(user=user, workspace=workspace).exists() or XToken.objects.filter(user=user, workspace=workspace).exists(),
                'account_name': 'X account',
                'metrics': {
                    'Scheduled': scheduled_count,
                    'Posted': posted_count,
                    'Need Review': review_count,
                },
            },
            'linkedin': {
                'connected': LinkedinToken.objects.filter(user=user, workspace=workspace).exists(),
                'account_name': 'LinkedIn account',
                'metrics': {
                    'Scheduled': scheduled_count,
                    'Posted': posted_count,
                    'Need Review': review_count,
                },
            },
            'facebook': {
                'connected': facebook_page is not None,
                'account_name': facebook_page.name if facebook_page else 'Facebook page',
                'error': facebook_error,
                'metrics': {
                    'Scheduled': scheduled_count,
                    'Posted': posted_count,
                    'Need Review': review_count,
                },
            },
            'instagram': {
                'connected': instagram_token_connected and has_instagram_business_account,
                'account_name': 'Instagram account',
                'error': instagram_error or facebook_error,
                'metrics': {
                    'Scheduled': scheduled_count,
                    'Posted': posted_count,
                    'Need Review': review_count,
                },
            },
        }
        return JsonResponse({'data': data})

class GetApprovalToggle(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workspace_id = request.data.get('workspace_id', '')
        user = request_user_from_payload(request)
        if not user:
            return Response({'error': 'Valid user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        workspace, error = get_workspace_for_user(workspace_id, request.user)
        if error:
            code = status.HTTP_403_FORBIDDEN if 'access' in error else status.HTTP_400_BAD_REQUEST
            return Response({'error': error}, status=code)
        user_profile, _ = UserProfile.objects.get_or_create(user=user, workspace=workspace)
        logger.info('approval_toggle_get user=%s workspace=%s value=%s', user.id, workspace.id, user_profile.approval_toggle)
        data={
            "approval_toggle":user_profile.approval_toggle,
            "workspace_id": str(workspace.id),
        }
        return JsonResponse(data=data)

class ChangeApprovalToggle(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workspace_id = request.data.get('workspace_id', '')
        toggle = request.data.get('toggle', request.data.get('approval_toggle'))
        user = request_user_from_payload(request)
        if not user:
            return Response({'error': 'Valid user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if toggle is None:
            return Response({'error': 'toggle is required.'}, status=status.HTTP_400_BAD_REQUEST)
        workspace, error = get_workspace_for_user(workspace_id, request.user)
        if error:
            code = status.HTTP_403_FORBIDDEN if 'access' in error else status.HTTP_400_BAD_REQUEST
            return Response({'error': error}, status=code)
        user_profile, _ = UserProfile.objects.get_or_create(user=user, workspace=workspace)
        if isinstance(toggle, str):
            normalized_toggle = toggle.strip().lower() in {'1', 'true', 'yes', 'on'}
        else:
            normalized_toggle = bool(toggle)
        user_profile.approval_toggle = normalized_toggle
        user_profile.save(update_fields=['approval_toggle'])
        logger.info('approval_toggle_update user=%s workspace=%s value=%s', user.id, workspace.id, user_profile.approval_toggle)
        data = {
            "approval_toggle": user_profile.approval_toggle,
            "workspace_id": str(workspace.id),
        }
        return JsonResponse(data=data)



class MediaUploadView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id', '')
        image = request.FILES.get('image')
        workspace_id = request.data.get('workspace_id', '')
        workspace = Workspace.objects.filter(id=workspace_id).first()
        if not image:
            return Response({'error': 'image is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not workspace:
            return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        # serializer = UploadImagesSerializer(data=request.data)
        # if serializer.is_valid():
        #     instance = serializer.save()
        #     return Response(serializer.data, status=status.HTTP_201_CREATED)
        user= User.objects.filter(id=user_id).first()
        if not user:
            return Response({'error': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        instance = UploadImages.objects.create(user=user, image=image, workspace=workspace)
        normalized_url = normalize_media_url(instance.image.url)
        image_url, _ = ImageUrl.objects.get_or_create(
            user=user,
            image_url=normalized_url,
            workspace=workspace
        )
        try:
            from content_engine.models import MediaAsset
            asset = MediaAsset.objects.filter(user=user, workspace=workspace, url=image_url.image_url).first()
            if asset:
                asset.asset_type = 'image'
                asset.source = 'upload'
                asset.metadata = {'label': 'upload'}
                asset.save(update_fields=['asset_type', 'source', 'metadata', 'updated_at'])
            else:
                MediaAsset.objects.create(user=user, workspace=workspace, url=image_url.image_url, asset_type='image', source='upload', metadata={'label': 'upload'})
        except Exception:
            pass
        return Response({'id': str(image_url.id), 'image': image_url.image_url}, status=status.HTTP_200_OK)

class FetchBrandStyle(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id=workspace_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        if not user_profile:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse({'data': get_brand_style(user_profile)})

class UpdateBrandStyle(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        patch = request.data.get('brand_style') or {}
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id=workspace_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        if not user_profile:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        current = get_brand_style(user_profile)
        if not isinstance(patch, dict):
            return Response({'error': 'brand_style must be an object.'}, status=status.HTTP_400_BAD_REQUEST)
        current.update(patch)
        return JsonResponse({'data': save_brand_style(user_profile, current)})

class UploadBrandStyleLogo(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'image is required.'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id=workspace_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        if not user_profile:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        instance = UploadImages.objects.create(user=user, image=image, workspace=workspace)
        url = public_media_url(instance.image.url.split('?')[0])
        brand_style = get_brand_style(user_profile)
        brand_style['logos'] = brand_style.get('logos', []) + [{'url': url, 'source': 'upload'}]
        return JsonResponse({'data': save_brand_style(user_profile, brand_style), 'url': url})


class FetchContentPreferences(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id=workspace_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        if not user_profile:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse({'data': get_content_preferences(user_profile)})


class UpdateContentPreferences(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        preferences = request.data.get('content_preferences') or {}
        user = User.objects.filter(id=user_id).first()
        workspace = Workspace.objects.filter(id=workspace_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        if not user_profile:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse({'data': save_content_preferences(user_profile, preferences)})

class CreateBrandVoice(APIView):
    def post(self,request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        workspace = Workspace.objects.filter(id=workspace_id).first()
        user = User.objects.filter(id=int(user_id)).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        if not user_profile or not user_profile.markdown:
            return Response({'error': 'User profile markdown not found.'}, status=status.HTTP_404_NOT_FOUND)

        cg = ChatGPT()
        cg.create_client()
        cg.create_base_system_prompt()
        cg.create_chat_completion()
        message = cg.get_generated_message()
        if not message:
            return Response({'error': 'Could not initialize brand voice model.'}, status=status.HTTP_502_BAD_GATEWAY)
        cg.send_assistant_message(message)
        cg.send_users_message(f"""
                            Based on the following business profile markdown, generate a Brand Voice definition.

                    Return ONLY a valid JSON object with no explanation, no markdown fences, and no extra text.
                    The JSON must have exactly these keys:
                    
                    {{
                      "purpose": "A single string describing the content's purpose (e.g. promote services, highlight expertise). Separate multiple goals with commas.",
                      "audience": "A single string describing the target audience. Separate multiple segments with commas.",
                      "tone": ["Array of short tone descriptors, e.g. 'Professional yet accessible'"],
                      "emotion": ["Array of emotional stances the brand takes, e.g. 'Confident in skills and offerings'"],
                      "character": ["Array of character/persona directives, e.g. 'Position yourself as a knowledgeable expert'"],
                      "syntax": ["Array of sentence structure and formatting guidelines, e.g. 'Use concise, clear sentences'"],
                      "language": ["Array of vocabulary and terminology guidelines, e.g. 'Use technical terminology relevant to the industry'"]
                    }}
                    
                    Rules:
                    - purpose and audience must be plain strings (not arrays)
                    - tone, emotion, character, syntax, language must be arrays of 2-4 short strings each
                    - Base everything strictly on the business profile below
                    
                    Business Profile:
                    {user_profile.markdown}""")
        cg.create_chat_completion()
        message = cg.get_generated_message()
        if not message:
            return Response({'error': 'Brand voice model returned no content.'}, status=status.HTTP_502_BAD_GATEWAY)
        clean = re.sub(r"```(?:json)?|```", "", message).strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            clean = match.group(0)
        try:
            brand_voice_data = json.loads(clean)
        except json.JSONDecodeError as exc:
            return Response({'error': f'Invalid brand voice JSON: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)
        existing_brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
        if existing_brand_voice.get('brand_style'):
            brand_voice_data['brand_style'] = existing_brand_voice['brand_style']
        if existing_brand_voice.get('content_preferences'):
            brand_voice_data['content_preferences'] = existing_brand_voice['content_preferences']
        user_profile.brand_voice=brand_voice_data
        user_profile.workspace=workspace
        user_profile.save()

        return Response(status=status.HTTP_200_OK)

class FetchBrandVoice(APIView):
    def post(self,request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        workspace = Workspace.objects.filter(id=workspace_id).first()
        user = User.objects.filter(id=user_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        if not user_profile or not user_profile.brand_voice:
            return Response({'error': 'Brand voice is not ready yet.'}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse({'data':user_profile.brand_voice})

        pass

class UpdateMarkdown(APIView):
    def post(self,request):
        user_id = request.data.get('user_id', '')
        markdown = request.data.get('markdown', '')
        workspace_id = request.data.get('workspace_id', '')
        workspace = Workspace.objects.filter(id=workspace_id).first()
        user = User.objects.filter(id=user_id).first()
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        if not user_profile:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        user_profile.markdown = markdown
        user_profile.save()
        return Response(status=status.HTTP_200_OK)


