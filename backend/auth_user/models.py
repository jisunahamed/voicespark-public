import uuid

from django.db import models
from django.contrib.auth.models import User
from nano_banana.models import NanoBananaImage
from storages.backends.s3boto3 import S3Boto3Storage
from workspace.models import Workspace
class UserProfile(models.Model):
    """
    Stores the Facebook profile data for a Django user.
    One-to-one with Django's User model.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_profile')
    website_url = models.TextField(null=True, blank = True)
    markdown = models.TextField(null=True, blank = True)
    approval_toggle = models.BooleanField(default=True)
    brand_voice = models.JSONField(blank=True, null=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,related_name='workspace_user_profile')
    class Meta:
        db_table='user_profile'

class ImageUrl(models.Model):
    """
    Stores the Facebook profile data for a Django user.
    One-to-one with Django's User model.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='image_url')
    created_at = models.DateTimeField(auto_now_add=True)
    image_url = models.TextField(null=True, blank = True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,related_name='workspace_image_url')

    class Meta:
        db_table='image_url'

class ScheduledPost(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_posts')
    task_id      = models.CharField(max_length=255, unique=True, null=True, blank=True)  # celery task id
    scheduled_at = models.DateTimeField()
    nano_banana  = models.ForeignKey(NanoBananaImage, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,related_name='schedule_post')

    APPROVAL_CHOICES = [
        ('approved', 'Approved'),
        ('not_approved', 'Not Approved'),
        ('ready', 'Ready for Approval'),
        ('posted', 'Posted'),
    ]
    approval = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default='not_approved',
        # null= True,
        # blank=True
    )
    class Meta:
        db_table = 'scheduled_post'



class UploadImages(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        =  models.ForeignKey(User, on_delete=models.CASCADE, related_name='upload_images')
    image = models.FileField(
        upload_to='images/',
        blank=True,
        null=True
    )
    updated_at  = models.DateTimeField(auto_now=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,related_name='workspace_upload_images')

    class Meta:
        db_table = 'upload_images'
