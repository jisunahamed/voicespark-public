# models.py
from django.db import models
from django.contrib.auth.models import User
from workspace.models import Workspace

class FacebookUser(models.Model):
    """
    Stores the Facebook profile data for a Django user.
    One-to-one with Django's User model.
    """
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='facebook_profile')
    facebook_id  = models.CharField(max_length=100,db_index=True)
    email        = models.EmailField(blank=True)
    first_name   = models.CharField(max_length=100, blank=True)
    last_name    = models.CharField(max_length=100, blank=True)
    full_name    = models.CharField(max_length=200, blank=True)
    picture_url  = models.URLField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,
                                  related_name='workspace_facebook_profile')
    # def __str__(self):
    #     return f"FacebookUser({self.full_name}, fb_id={self.facebook_id})"
    class Meta:
        db_table = 'fb_user'

class FacebookPage(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='facebook_pages')
    page_id      = models.CharField(max_length=500)
    name         = models.CharField(max_length=255)
    access_token = models.TextField()
    category     = models.CharField(max_length=100, blank=True, null=True)
    tasks        = models.JSONField(default=list, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,
                                  related_name='workspace_facebook_pages')

    class Meta:
        db_table = 'facebook_page'
class FacebookToken(models.Model):
    """
    Stores the Facebook OAuth token details for a user.
    One-to-one with FacebookUser.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='token')
    access_token  = models.TextField()
    token_type    = models.CharField(max_length=50, default='bearer')
    expires_in    = models.IntegerField(null=True, blank=True)   # seconds, as returned by Meta
    issued_at     = models.DateTimeField(auto_now=True)          # refreshed on every login
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,
                                  related_name='workspace_facebook_token')

    # def __str__(self):
    #     return f"FacebookToken(user={self.facebook_user.full_name}, issued={self.issued_at})"
    class Meta:
        db_table = 'fb_Token'

class InstagramUser(models.Model):
    """
    Stores the Facebook profile data for a Django user.
    One-to-one with Django's User model.
    """
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instagram_profile')
    instagram_id  = models.CharField(max_length=100, unique=True, db_index=True)
    email        = models.EmailField(blank=True)
    first_name   = models.CharField(max_length=100, blank=True)
    last_name    = models.CharField(max_length=100, blank=True)
    full_name    = models.CharField(max_length=200, blank=True)
    picture_url  = models.URLField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,
                                  related_name='workspace_instagram_profile')

    # def __str__(self):
    #     return f"FacebookUser({self.full_name}, fb_id={self.facebook_id})"
    class Meta:
        db_table = 'insta_user'


class InstagramToken(models.Model):
    """
    Stores the Facebook OAuth token details for a user.
    One-to-one with FacebookUser.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='insta_token')
    access_token  = models.TextField()
    token_type    = models.CharField(max_length=50, default='bearer')
    expires_in    = models.IntegerField(null=True, blank=True)   # seconds, as returned by Meta
    issued_at     = models.DateTimeField(auto_now=True)          # refreshed on every login
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,
                                  related_name='workspace_insta_token')

    # def __str__(self):
    #     return f"FacebookToken(user={self.facebook_user.full_name}, issued={self.issued_at})"
    class Meta:
        db_table = 'insta_Token'