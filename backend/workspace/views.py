import logging

from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Workspace, WorkspaceMembership
from .serializers import (
    WorkspaceInviteSerializer,
    WorkspaceMembershipSerializer,
    WorkspaceSerializer,
)

logger = logging.getLogger(__name__)


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(
            Q(owner=self.request.user) | Q(memberships__user=self.request.user)
        ).distinct()

    def list(self, request, *args, **kwargs):
        for workspace in Workspace.objects.filter(owner=request.user):
            WorkspaceMembership.objects.get_or_create(
                workspace=workspace,
                user=request.user,
                defaults={'role': WorkspaceMembership.ROLE_OWNER},
            )
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        workspace = serializer.save(owner=self.request.user)
        WorkspaceMembership.objects.get_or_create(
            workspace=workspace,
            user=self.request.user,
            defaults={'role': WorkspaceMembership.ROLE_OWNER},
        )

    def perform_update(self, serializer):
        old_name = getattr(self.get_object(), 'name', '')
        workspace = serializer.save()
        if old_name != workspace.name:
            logger.info('workspace_renamed user=%s workspace=%s old_name=%s new_name=%s', self.request.user.id, workspace.id, old_name, workspace.name)

    def destroy(self, request, *args, **kwargs):
        workspace = self.get_object()
        if workspace.owner_id != request.user.id:
            return Response(
                {'error': 'Only the workspace owner can delete this workspace.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    def get_workspace(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        workspace = self.get_workspace()

        if request.method == 'GET':
            memberships = workspace.memberships.select_related('user').order_by('created_at')
            return Response(WorkspaceMembershipSerializer(memberships, many=True).data)

        serializer = WorkspaceInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['email']
        membership, created = WorkspaceMembership.objects.update_or_create(
            workspace=workspace,
            user=user,
            defaults={'role': serializer.validated_data['role']},
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(WorkspaceMembershipSerializer(membership).data, status=response_status)

    @action(
        detail=True,
        methods=['delete', 'patch'],
        url_path=r'members/(?P<user_id>[^/.]+)',
    )
    def member_detail(self, request, pk=None, user_id=None):
        workspace = self.get_workspace()
        membership = get_object_or_404(workspace.memberships, user_id=user_id)

        if request.method == 'DELETE':
            membership.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        role = request.data.get('role')
        valid_roles = {choice[0] for choice in WorkspaceMembership.ROLE_CHOICES}
        if role not in valid_roles:
            return Response({'role': 'Invalid role.'}, status=status.HTTP_400_BAD_REQUEST)

        membership.role = role
        membership.save(update_fields=['role', 'updated_at'])
        return Response(WorkspaceMembershipSerializer(membership).data)
