from django.urls import path
from .views import (GenerateImageView, GetGeneratedImage, GetGeneratedImageById, AnalyseWebsiteLink, EditImageView,
                    ScheduleGeneratePost, GenerateCaptionAndImagePost, EditGeneratedImage, ChangeScheduleTime,
                    GetApprovalPost, RegenerateImage, CreateNewPost, ChangeApproval, ReturnNextPreviousId,
                    VisualFeedback, SavePlatformCaptions, DeleteGeneratedImage, DownloadGeneratedImage,
                    NanoGenerationJobStatus)

urlpatterns = [
    path("generate/",    GenerateImageView.as_view(),    name="meta_login"),
    path("get-generated-image/", GetGeneratedImage.as_view(), name="get_generated_image"),
    path('get-image-id/', GetGeneratedImageById.as_view(), name="get_image_id"),
    path('analyse-website-link/', AnalyseWebsiteLink.as_view(), name="analyse_website_link"),
    path('edit-image/', EditImageView.as_view(), name="edit_image"),
    path('generate-post/', GenerateCaptionAndImagePost.as_view(), name="generate_post"),
    path('schedule-post/', ScheduleGeneratePost.as_view(), name="schedule_post"),
    path('edit-generated-image/', EditGeneratedImage.as_view(), name="edit_generated_image"),

    path('regenerate-image/', RegenerateImage.as_view(), name="regenerate_image"),

    path('change-schedule-time/', ChangeScheduleTime.as_view(), name="change_schedule_time"),
    path('get-approval-post/', GetApprovalPost.as_view(), name="get_approval_post"),

    path('create-new-post/', CreateNewPost.as_view(), name="create_new_post"),

    path('change-approval/', ChangeApproval.as_view(), name="change_approval"),
    path('visual-feedback/', VisualFeedback.as_view(), name="visual_feedback"),
    path('save-platform-captions/', SavePlatformCaptions.as_view(), name="save_platform_captions"),
    path('delete-image/', DeleteGeneratedImage.as_view(), name="delete_image"),
    path('download-image/', DownloadGeneratedImage.as_view(), name="download_image"),
    path('return-id/', ReturnNextPreviousId.as_view(), name="return_id"),
    path('generation-job/<uuid:job_id>/', NanoGenerationJobStatus.as_view(), name="generation_job_status"),
    # path("tweet/",    PostTweetView.as_view(),  name="post_tweet"),
]
