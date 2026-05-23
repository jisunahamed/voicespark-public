from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (LoginView, RegisterView, LogoutView, ProfileView, MakeScheduledPost, CreateUserProfile,
                    GetData, GetMarkdown, GetWebsiteLink, GetApprovalToggle, ChangeApprovalToggle, MediaUploadView,
                    CreateBrandVoice, FetchBrandVoice, UpdateMarkdown, DeleteMediaView, FetchBrandStyle,
                    UpdateBrandStyle, UploadBrandStyleLogo, FetchContentPreferences,
                    UpdateContentPreferences, SocialInsights)
from .views_schedule import ScheduledPost

urlpatterns = [
    # Auth endpoints
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Protected profile endpoint
    path('profile/', ProfileView.as_view(), name='profile'),
    path('create-userprofile/', CreateUserProfile.as_view(), name='create_userprofile'),

    path('make-schedule-post/', MakeScheduledPost.as_view(), name='make-schedule-post'),
    path('schedule-post', ScheduledPost.as_view(), name='scheduled_post'),
    path('schedule-post/', ScheduledPost.as_view(), name='scheduled_post_slash'),

    path('get-data/', GetData.as_view(), name='get_data'),
    path('get-markdown/', GetMarkdown.as_view(), name='get_markdown'),
    path('get-website/', GetWebsiteLink.as_view(), name='get_website'),
    path('social-insights/', SocialInsights.as_view(), name='social_insights'),
    path('get-toggle/', GetApprovalToggle.as_view(), name='get_toggle'),
    path('change-toggle/', ChangeApprovalToggle.as_view(), name='change_toggle'),

    path('media-upload/', MediaUploadView.as_view(), name='media_upload'),
    path('delete-media/', DeleteMediaView.as_view(), name='delete_media'),
    path('create-brand-voice/', CreateBrandVoice.as_view(), name='create_brand_voice'),
    path('fetch-brand-voice/', FetchBrandVoice.as_view(), name='fetch_brand_voice'),
    path('fetch-brand-style/', FetchBrandStyle.as_view(), name='fetch_brand_style'),
    path('update-brand-style/', UpdateBrandStyle.as_view(), name='update_brand_style'),
    path('upload-brand-style-logo/', UploadBrandStyleLogo.as_view(), name='upload_brand_style_logo'),
    path('fetch-content-preferences/', FetchContentPreferences.as_view(), name='fetch_content_preferences'),
    path('update-content-preferences/', UpdateContentPreferences.as_view(), name='update_content_preferences'),
    path('update-markdown/', UpdateMarkdown.as_view(), name='update_markdown'),

]
