from django.db import models
from django.contrib.auth.models import User
from workspace.models import Workspace


class XToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,
                                  related_name='workspace_xtoken')
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.TextField(null=True, blank=True)
    x_user_id = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'x_token'
        unique_together = ('user', 'workspace')

# Create your models here.
class Auth1Xtoken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    access_token_secret = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,
                                  related_name='workspace_auth1_xtoken')

    class Meta:
        db_table='auth1_xtoken'