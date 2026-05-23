from django.urls import path
from .views import (
    ConnectWordpressView,
    WordpressStatusView,
    WordpressMetadataView,
    DisconnectWordpressView,
    DownloadPluginView,
    WordpressPostView
)

urlpatterns = [
    path('connect/', ConnectWordpressView.as_view(), name='wp_connect'),
    path('status/', WordpressStatusView.as_view(), name='wp_status'),
    path('metadata/', WordpressMetadataView.as_view(), name='wp_metadata'),
    path('disconnect/', DisconnectWordpressView.as_view(), name='wp_disconnect'),
    path('download-plugin/', DownloadPluginView.as_view(), name='wp_download_plugin'),
    path('publish/', WordpressPostView.as_view(), name='wp_publish'),
]
