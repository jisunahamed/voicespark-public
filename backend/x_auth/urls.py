from django.urls import path
from .views import XLoginView, XCallbackView, PostTweetView, post_tweet,XOAuth1LoginView, XOAuth1CallbackView

urlpatterns = [
    path("login/",    XLoginView.as_view(),    name="x_login"),
    path("callback/", XCallbackView.as_view(), name="x_callback"),
    path("tweet/",    post_tweet,  name="post_tweet"),
]
