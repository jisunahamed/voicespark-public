from django.contrib.auth.models import User
from rest_framework import serializers

# class RegisterSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = User
#         fields = ["username", "email", "password"]
#         extra_kwargs = {"password": {"write_only": True}}
#
#     def create(self, validated_data):
#         user = User.objects.create_user(
#             username=validated_data["username"],
#             email=validated_data["email"],
#             password=validated_data["password"]
#         )
#         return user
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UploadImages

class CustomTokenObtainPairSerializer(serializers.Serializer):
    # Completely bypass TokenObtainPairSerializer's __init__
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    @classmethod
    def get_token(cls, user):
        refresh = RefreshToken.for_user(user)
        refresh['username'] = user.username
        refresh['email'] = user.email
        refresh['first_name'] = user.first_name
        refresh['last_name'] = user.last_name
        return refresh

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('No account found with this email.')

        if not user.check_password(password):
            raise serializers.ValidationError('Incorrect password.')

        if not user.is_active:
            raise serializers.ValidationError('This account is inactive.')

        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm password')

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password2')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def generate_username(self, email):
        base = email.split('@')[0]  # e.g. "john.doe"
        base = ''.join(c for c in base if c.isalnum())  # strip dots/symbols → "johndoe"
        base = base.lower()

        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1

        return username

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})

        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        validated_data['username'] = self.generate_username(validated_data['email'])
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'date_joined')


class UploadImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadImages
        fields = ["id", "image", "updated_at"]
