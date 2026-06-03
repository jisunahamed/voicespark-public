import os
from io import BytesIO
import zipfile
from urllib.parse import urlparse, urlunparse
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from workspace.models import Workspace
from .models import WordpressConnection
from nano_banana.models import NanoBananaImage
from auth_user.models import ScheduledPost
from utils.public_urls import public_media_url
from .utils import encrypt_data
from .wordpress_service import WordpressService


def normalize_wordpress_site_url(site_url):
    site_url = str(site_url or '').strip().rstrip('/')
    if not site_url:
        return ''
    if not site_url.startswith(('http://', 'https://')):
        site_url = 'https://' + site_url
    parsed = urlparse(site_url)
    path = parsed.path.rstrip('/')
    for suffix in ('/wp-admin', '/wp-login.php'):
        if path.endswith(suffix):
            path = path[:-len(suffix)]
            break
    normalized = parsed._replace(path=path or '', params='', query='', fragment='')
    return urlunparse(normalized).rstrip('/')


class ConnectWordpressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        site_url = request.data.get('site_url')
        username = request.data.get('username')
        password = request.data.get('password')
        workspace_id = request.data.get('workspace_id')

        if not all([site_url, username, password, workspace_id]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        # Accept either the public site URL or the admin/login URL and store the base URL.
        site_url = normalize_wordpress_site_url(site_url)

        # Encrypt password
        encrypted_pw = encrypt_data(password)

        # Validate connection BEFORE saving — build a temporary object for auth test
        temp_connection = WordpressConnection(
            site_url=site_url,
            wp_username=username,
            encrypted_password=encrypted_pw,
        )
        try:
            service = WordpressService(temp_connection)
            service.authenticate()
        except Exception as e:
            return Response(
                {'error': f'Failed to connect to WordPress: {str(e)}'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Auth succeeded — now persist the connection
        connection, created = WordpressConnection.objects.update_or_create(
            workspace=workspace,
            site_url=site_url,
            defaults={
                'user': request.user,
                'wp_username': username,
                'encrypted_password': encrypted_pw,
                'is_active': True,
            }
        )

        return Response({
            'message': 'WordPress connected successfully',
            'site_url': connection.site_url,
            'username': connection.wp_username,
        })

class WordpressStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workspace_id = request.data.get('workspace_id')
        try:
            connection = WordpressConnection.objects.filter(workspace_id=workspace_id, is_active=True).first()
            if not connection:
                return Response({'connected': False})
            
            return Response({
                'connected': True,
                'site_url': connection.site_url,
                'username': connection.wp_username,
                'connected_at': connection.connected_at
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WordpressMetadataView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workspace_id = request.data.get('workspace_id')
        connection = WordpressConnection.objects.filter(workspace_id=workspace_id, is_active=True).first()
        if not connection:
            return Response({'error': 'WordPress not connected'}, status=status.HTTP_404_NOT_FOUND)

        service = WordpressService(connection)
        try:
            categories = service.fetch_categories()
            tags = service.fetch_tags()
            return Response({
                'categories': categories,
                'tags': tags
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DisconnectWordpressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workspace_id = request.data.get('workspace_id')
        WordpressConnection.objects.filter(workspace_id=workspace_id).update(is_active=False)
        return Response({'message': 'WordPress disconnected'})

from rest_framework.permissions import AllowAny

class DownloadPluginView(APIView):
    # Allow anyone to download the plugin via direct window.open link
    permission_classes = [AllowAny]

    def get(self, request):
        plugin_path = os.path.join(settings.BASE_DIR, '..', 'voicespark.zip')
        if os.path.exists(plugin_path):
            response = FileResponse(open(plugin_path, 'rb'), as_attachment=True, filename='voicespark.zip')
            response['Cache-Control'] = 'no-store'
            return response
        else:
            # Fallback to current dir if not in parent
            plugin_path = os.path.join(settings.BASE_DIR, 'voicespark.zip')
            if os.path.exists(plugin_path):
                response = FileResponse(open(plugin_path, 'rb'), as_attachment=True, filename='voicespark.zip')
                response['Cache-Control'] = 'no-store'
                return response
            source_dir = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'wordpress-plugin', 'voicespark'))
            if os.path.isdir(source_dir):
                buffer = BytesIO()
                with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                    for root, _, files in os.walk(source_dir):
                        for filename in files:
                            full_path = os.path.join(root, filename)
                            relative_path = os.path.relpath(full_path, os.path.dirname(source_dir))
                            archive.write(full_path, relative_path)
                buffer.seek(0)
                response = FileResponse(buffer, as_attachment=True, filename='voicespark.zip')
                response['Cache-Control'] = 'no-store'
                return response
            raise Http404("Plugin file not found on server")


def _meta_from_captions(captions):
    if not isinstance(captions, dict):
        return {}
    meta = captions.get('__meta') or captions.get('__meta__')
    return meta if isinstance(meta, dict) else {}


def _text_value(value):
    if isinstance(value, str):
        return value.strip()
    if value in (None, ''):
        return ''
    return str(value).strip()


def _dict_value(data, *keys):
    if not isinstance(data, dict):
        return ''
    for key in keys:
        value = data.get(key)
        if isinstance(value, dict):
            for nested_key in ('caption', 'content', 'body', 'text', 'title', 'meta_description'):
                nested = _text_value(value.get(nested_key))
                if nested:
                    return nested
        text = _text_value(value)
        if text:
            return text
    return ''


class WordpressPostView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        nano_banana_id = request.data.get('nano_banana_id')
        workspace_id = request.data.get('workspace_id')
        user = request.user

        if not nano_banana_id:
            return Response({'error': 'nano_banana_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        nano_banana = NanoBananaImage.objects.filter(id=nano_banana_id).first()
        if not nano_banana:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        workspace = nano_banana.workspace
        connection = WordpressConnection.objects.filter(workspace=workspace, is_active=True).first()
        if not connection:
            return Response({'error': 'WordPress not connected for this workspace'}, status=status.HTTP_404_NOT_FOUND)

        service = WordpressService(connection)
        
        captions = nano_banana.platform_captions or {}
        meta = _meta_from_captions(captions)
        blog_data = captions.get('blog') if isinstance(captions.get('blog'), dict) else {}
        blog_text = captions.get('blog') if isinstance(captions.get('blog'), str) else ''
        wp_meta = meta.get('wordpress') if isinstance(meta.get('wordpress'), dict) else {}
        explicit_blog_content = bool(
            blog_data
            or _text_value(blog_text)
            or _dict_value(meta, 'blog_content', 'content', 'body', 'markdown')
            or _dict_value(wp_meta, 'content', 'body', 'markdown')
        )

        title = (
            _text_value(meta.get('title'))
            or _dict_value(blog_data, 'title', 'headline')
            or _text_value(nano_banana.caption)
            or 'Untitled Post'
        )
        blog_content = (
            _dict_value(blog_data, 'caption', 'content', 'body', 'markdown', 'html')
            or _dict_value(meta, 'blog_content', 'content', 'body', 'markdown')
            or _text_value(blog_text)
            or _text_value(nano_banana.caption)
        )
        excerpt = (
            _text_value(meta.get('meta_description'))
            or _dict_value(blog_data, 'meta_description', 'excerpt', 'summary')
        )
        featured_media_url = (
            _text_value(nano_banana.picture_url)
            or _text_value(meta.get('featured_image_url'))
            or _text_value(meta.get('reference_image_url'))
        )
        featured_media_url = public_media_url(featured_media_url)
        content_type = _text_value(meta.get('content_type') or request.data.get('content_type')).lower()
        if content_type == 'social' and not explicit_blog_content:
            return Response({'error': 'WordPress publishing requires blog content for this post.'}, status=status.HTTP_400_BAD_REQUEST)
        if not blog_content:
            return Response({'error': 'WordPress content is missing for this post.'}, status=status.HTTP_400_BAD_REQUEST)

        allowed_statuses = {'publish', 'draft', 'future', 'pending'}
        requested_status = _text_value(request.data.get('status') or wp_meta.get('status') or meta.get('wordpress_status')).lower()
        wp_status = requested_status if requested_status in allowed_statuses else 'publish'
        scheduled_date = None
        if wp_status == 'future':
            schedule_obj = ScheduledPost.objects.filter(nano_banana=nano_banana).first()
            if schedule_obj and schedule_obj.scheduled_at:
                scheduled_date = schedule_obj.scheduled_at.isoformat()
            else:
                return Response({'error': 'WordPress future status requires a scheduled time.'}, status=status.HTTP_400_BAD_REQUEST)

        categories = wp_meta.get('categories', [])
        tags = wp_meta.get('tags', [])

        try:
            result = service.publish_post(
                title=title,
                content=blog_content,
                status=wp_status,
                scheduled_date=scheduled_date,
                categories=categories,
                tags=tags,
                featured_media_url=featured_media_url,
                excerpt=excerpt,
            )
            return Response({
                'message': 'Published to WordPress successfully',
                'external_post_id': result.get('id'),
                'link': result.get('link')
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
