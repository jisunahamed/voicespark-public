from django.urls import path
from .views import MetaLogin, MetaCallback, FacebookPostView, InstagramPostView, ConnectedAccountsView

urlpatterns = [
    path("login/",    MetaLogin.as_view(),    name="meta_login"),
    path("callback/", MetaCallback.as_view(), name="meta_callback"),
    path("instagram/callback/", MetaCallback.as_view(), name="instagram_meta_callback"),
    path("connected-accounts/", ConnectedAccountsView.as_view(), name="connected_accounts"),
    path("facebook-post/", FacebookPostView.as_view(), name="facebook_post"),
    path("instagram-post/", InstagramPostView.as_view(), name='instagram_post')
    # path("tweet/",    PostTweetView.as_view(),  name="post_tweet"),
]
