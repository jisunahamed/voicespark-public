from django.urls import path
from .views import (
    LinkedinLogin, LinkedinAuthCallback, LinkedinCreatePost,
    ConnectedPagesView, SelectLinkedinPageView
)

urlpatterns = [
    path("login/",    LinkedinLogin.as_view(),    name="linkedin_login"),
    path("callback/", LinkedinAuthCallback.as_view(), name="linkedin_callback"),
    path("pages/",    ConnectedPagesView.as_view(), name="linkedin_pages"),
    path("select-page/", SelectLinkedinPageView.as_view(), name="linkedin_select_page"),

    path("post/",    LinkedinCreatePost.as_view(),  name="linkedin_create_post"),
]