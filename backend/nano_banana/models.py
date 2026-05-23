import uuid

from django.db import models
from django.contrib.auth.models import User
from workspace.models import Workspace

# Create your models here.
class NanoBananaImage(models.Model):
    """
    Stores the Facebook profile data for a Django user.
    One-to-one with Django's User model.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nano_banana_images')
    picture_url  = models.TextField(blank=True, null = True)
    caption      = models.TextField(null=True, blank=True)
    platform_captions = models.JSONField(default=dict, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True,
                                  related_name='workspace_nano_banana_images')

    class Meta:
        db_table = 'nano_banana_image'


class NanoGenerationJob(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    JOB_TYPES = [
        ('create_post', 'Create post'),
        ('regenerate_image', 'Regenerate image'),
        ('edit_generated_image', 'Edit generated image'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nano_generation_jobs')
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='nano_generation_jobs',
    )
    nano_banana = models.ForeignKey(
        NanoBananaImage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generation_jobs',
    )
    job_type = models.CharField(max_length=64, choices=JOB_TYPES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='queued')
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nano_generation_job'
        indexes = [
            models.Index(fields=['user', 'workspace', 'status']),
            models.Index(fields=['job_type', 'created_at']),
        ]
