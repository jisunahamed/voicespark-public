from django.db import models
from django.contrib.auth.models import User
from workspace.models import Workspace

# Create your models here.

class LinkedinUser(models.Model):
    """
    Stores the LinkedIn profile data for a Django user.
    """
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='linkedin_profile')
    email        = models.EmailField(blank=True)
    first_name   = models.CharField(max_length=100, blank=True)
    last_name    = models.CharField(max_length=100, blank=True)
    full_name    = models.CharField(max_length=500, blank=True)
    picture_url  = models.URLField(blank=True, max_length=1000)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,related_name='workspace_linkedin_profile')

    class Meta:
        db_table = 'linkedin_user'

class LinkedinToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='linkedin_token')
    access_token  = models.TextField()
    id_token      = models.TextField()
    token_type    = models.CharField(max_length=50, default='bearer')
    expires_in    = models.IntegerField(null=True, blank=True)
    issued_at     = models.DateTimeField(auto_now=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,related_name='workspace_linkedin_token')

    class Meta:
        db_table = 'linkedin_Token'

class LinkedinPage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='linkedin_pages')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='linkedin_pages')
    organization_id = models.CharField(max_length=100)
    organization_urn = models.CharField(max_length=200)
    name = models.CharField(max_length=500)
    vanity_name = models.CharField(max_length=500, blank=True, null=True)
    logo_url = models.URLField(max_length=1000, blank=True, null=True)
    role = models.CharField(max_length=100) # ADMINISTRATOR, CONTENT_ADMIN, etc.
    is_selected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'linkedin_page'
        unique_together = ('workspace', 'organization_id')

    def __str__(self):
        return f"{self.name} ({self.organization_id})"