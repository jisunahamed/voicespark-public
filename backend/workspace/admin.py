from django.contrib import admin

from .models import Workspace, WorkspaceMembership


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'created_at')
    search_fields = ('name', 'owner__email', 'owner__username')


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'workspace', 'user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('workspace__name', 'user__email', 'user__username')
