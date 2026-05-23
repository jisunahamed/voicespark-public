"""
URL configuration for blaze project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from .health import health_check

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('auth/x/', include('x_auth.urls')),  # 👈 add this
    path('auth/linkedin/', include('linkedin_auth.urls')),  # 👈 add this
    path('auth/fb/', include('fb_auth.urls')),  # 👈 add this
    path('auth/user/', include('auth_user.urls')),
    path('content-engine/', include('content_engine.urls')),
    path('nano-banana/', include('nano_banana.urls')),
    path('auth/wordpress/', include('wordpress_auth.urls')),
    path('workspace/', include('workspace.urls'))
]

if settings.DEBUG:
    urlpatterns += static(getattr(settings, 'MEDIA_URL', '/media/'), document_root=getattr(settings, 'MEDIA_ROOT', None))
