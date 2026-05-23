import uuid

from django.conf import settings
from django.db import models

from workspace.models import Workspace


class TimestampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BusinessProfile(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='business_profiles')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name='business_profiles')
    full_name = models.CharField(max_length=255, blank=True)
    monthly_marketing_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    business_category = models.CharField(max_length=255, blank=True)
    website_url = models.URLField(max_length=1000)
    tone = models.CharField(max_length=255, blank=True)
    services = models.JSONField(default=list, blank=True)
    audience = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    profile = models.JSONField(default=dict, blank=True)
    editable_markdown = models.TextField(blank=True)
    source_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'workspace']),
            models.Index(fields=['website_url']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['user', 'workspace'], name='unique_business_profile_per_workspace')
        ]


class BrandSetting(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='brand_settings')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name='brand_settings')
    business_profile = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='brand_settings')
    visual_style = models.CharField(max_length=32, blank=True)
    recommended_visual_style = models.JSONField(default=dict, blank=True)
    font = models.JSONField(default=dict, blank=True)
    tone = models.CharField(max_length=255, blank=True)
    image_style = models.TextField(blank=True)
    colors = models.JSONField(default=list, blank=True)
    logos = models.JSONField(default=list, blank=True)
    brand_context = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'workspace'])]
        constraints = [
            models.UniqueConstraint(fields=['user', 'workspace'], name='unique_brand_setting_per_workspace')
        ]


class SourceMatrixEntry(TimestampedModel):
    SOURCE_TYPES = [
        ('my_website', 'My Website'),
        ('competitor', 'Competitor Website'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('analyzing', 'Analyzing'),
        ('analyzed', 'Analyzed'),
        ('failed', 'Failed'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='source_matrix_entries')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='source_matrix_entries')
    url = models.URLField(max_length=1000)
    source_type = models.CharField(max_length=32, choices=SOURCE_TYPES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending')
    last_analyzed_at = models.DateTimeField(null=True, blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'workspace', 'source_type', 'status']),
            models.Index(fields=['workspace', 'url']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['workspace', 'url', 'source_type'], name='unique_source_per_workspace_type')
        ]


class CompetitorAnalysis(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='competitor_analyses')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='competitor_analyses')
    source = models.ForeignKey(SourceMatrixEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='competitor_analyses')
    name = models.CharField(max_length=255)
    website_url = models.URLField(max_length=1000, blank=True)
    pricing_model = models.TextField(blank=True)
    key_features = models.JSONField(default=list, blank=True)
    differentiators = models.JSONField(default=list, blank=True)
    swot = models.JSONField(default=dict, blank=True)
    objection_handling = models.JSONField(default=dict, blank=True)
    raw_analysis = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'workspace']),
            models.Index(fields=['workspace', 'website_url']),
        ]


class WorkspaceIntelligenceJob(TimestampedModel):
    JOB_TYPES = [
        ('brand_enrichment', 'Brand enrichment'),
        ('competitor_discovery', 'Competitor discovery'),
    ]
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_intelligence_jobs')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='intelligence_jobs')
    business_profile = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='intelligence_jobs')
    job_type = models.CharField(max_length=64, choices=JOB_TYPES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='queued')
    attempts = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'workspace', 'status']),
            models.Index(fields=['workspace', 'job_type', 'status']),
        ]


class ChannelVoiceConfig(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='channel_voice_configs')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='channel_voice_configs')
    platform = models.CharField(max_length=64)
    tone = models.TextField(blank=True)
    emotion = models.TextField(blank=True)
    character = models.TextField(blank=True)
    syntax = models.TextField(blank=True)
    language = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'workspace', 'platform'])]
        constraints = [
            models.UniqueConstraint(fields=['workspace', 'platform'], name='unique_channel_voice_per_workspace')
        ]


class AudienceProfile(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audience_profiles')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='audience_profiles')
    name = models.CharField(max_length=255)
    age_range = models.CharField(max_length=128, blank=True)
    location = models.TextField(blank=True)
    occupation = models.TextField(blank=True)
    pain_points = models.JSONField(default=list, blank=True)
    frustrations = models.JSONField(default=list, blank=True)
    goals = models.JSONField(default=list, blank=True)
    behaviors = models.JSONField(default=list, blank=True)
    buying_patterns = models.JSONField(default=list, blank=True)
    awareness_level = models.CharField(max_length=128, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'workspace', 'name'])]


class BrandManualData(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='brand_manual_data')
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='brand_manual_data')
    processes = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    deliverables = models.TextField(blank=True)
    pricing = models.TextField(blank=True)
    onboarding = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'workspace'])]


class ContentPlan(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='content_plans')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name='content_plans')
    business_profile = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='content_plans')
    brand_setting = models.ForeignKey(BrandSetting, on_delete=models.SET_NULL, null=True, blank=True, related_name='content_plans')
    platforms = models.JSONField(default=list, blank=True)
    posts_per_week = models.PositiveIntegerField(default=5)
    blog_posts_per_week = models.PositiveIntegerField(default=0)
    emails_per_week = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default='draft')

    class Meta:
        indexes = [models.Index(fields=['user', 'workspace', 'status'])]


class CampaignWeek(TimestampedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('generated', 'Generated'),
    ]
    content_plan = models.ForeignKey(ContentPlan, on_delete=models.CASCADE, related_name='campaign_weeks')
    week_number = models.PositiveIntegerField(default=1)
    theme = models.TextField(blank=True)
    funnel_goal = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft')
    item_plan = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['week_number', 'created_at']
        indexes = [models.Index(fields=['content_plan', 'week_number', 'status'])]
        constraints = [
            models.UniqueConstraint(fields=['content_plan', 'week_number'], name='unique_campaign_week_per_plan')
        ]


class Topic(TimestampedModel):
    content_plan = models.ForeignKey(ContentPlan, on_delete=models.CASCADE, related_name='topics')
    week_number = models.PositiveIntegerField(default=1)
    position = models.PositiveIntegerField(default=1)
    title = models.TextField()
    kind = models.CharField(max_length=32, default='social')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['week_number', 'position', 'created_at']
        indexes = [models.Index(fields=['content_plan', 'week_number', 'kind'])]


class BlogEmailPlan(TimestampedModel):
    content_plan = models.OneToOneField(ContentPlan, on_delete=models.CASCADE, related_name='blog_email_plan')
    blog_plan = models.JSONField(default=dict, blank=True)
    email_plan = models.JSONField(default=dict, blank=True)


class MediaAsset(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='content_media_assets')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name='content_media_assets')
    url = models.TextField()
    asset_type = models.CharField(max_length=32, default='image')
    source = models.CharField(max_length=32, default='generated')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'workspace', 'asset_type'])]


class GenerationJob(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='content_generation_jobs')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name='content_generation_jobs')
    content_plan = models.ForeignKey(ContentPlan, on_delete=models.CASCADE, related_name='generation_jobs')
    campaign_week = models.ForeignKey(CampaignWeek, on_delete=models.SET_NULL, null=True, blank=True, related_name='generation_jobs')
    status = models.CharField(max_length=32, default='queued')
    error = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=['user', 'workspace', 'status'])]


class GeneratedPost(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='content_generated_posts')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name='content_generated_posts')
    content_plan = models.ForeignKey(ContentPlan, on_delete=models.CASCADE, related_name='generated_posts')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_posts')
    job = models.ForeignKey(GenerationJob, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_posts')
    image = models.ForeignKey(MediaAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_posts')
    platform_outputs = models.JSONField(default=dict, blank=True)
    image_prompt = models.TextField(blank=True)
    status = models.CharField(max_length=32, default='draft')
    scheduled_for = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'workspace', 'status', 'scheduled_for'])]
