from django.contrib import admin

from .models import (
    BlogEmailPlan,
    BrandSetting,
    BusinessProfile,
    CampaignWeek,
    ContentPlan,
    GeneratedPost,
    GenerationJob,
    MediaAsset,
    Topic,
)


admin.site.register(BusinessProfile)
admin.site.register(BrandSetting)
admin.site.register(ContentPlan)
admin.site.register(CampaignWeek)
admin.site.register(Topic)
admin.site.register(BlogEmailPlan)
admin.site.register(MediaAsset)
admin.site.register(GenerationJob)
admin.site.register(GeneratedPost)
