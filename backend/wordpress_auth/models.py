from django.db import models
from django.contrib.auth.models import User
from workspace.models import Workspace

class WordpressConnection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wordpress_connections')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='wordpress_connections')
    site_url = models.URLField(max_length=500)
    wp_username = models.CharField(max_length=255)
    # Stored encrypted via cryptography.fernet
    encrypted_password = models.TextField()
    
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wordpress_connections'
        unique_together = ('workspace', 'site_url')

    def __str__(self):
        return f"WP Connection: {self.site_url} ({self.wp_username})"
