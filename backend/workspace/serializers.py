from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Workspace, WorkspaceMembership


class WorkspaceSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source='owner.id', read_only=True)

    class Meta:
        model = Workspace
        fields = ('id', 'name', 'owner_id', 'created_at', 'updated_at')
        read_only_fields = ('id', 'owner_id', 'created_at', 'updated_at')


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = (
            'id',
            'workspace',
            'user_id',
            'email',
            'first_name',
            'last_name',
            'role',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'workspace',
            'user_id',
            'email',
            'first_name',
            'last_name',
            'created_at',
            'updated_at',
        )


class WorkspaceInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=WorkspaceMembership.ROLE_CHOICES,
        default=WorkspaceMembership.ROLE_MEMBER,
    )

    def validate_email(self, value):
        try:
            return User.objects.get(email=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError('No user found with this email.') from exc
