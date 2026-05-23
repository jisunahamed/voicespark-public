import requests
import logging
import base64
from .utils import decrypt_data
from utils.public_urls import public_media_url

logger = logging.getLogger(__name__)

# Common headers sent with every request to identify VoiceSpark traffic
_BASE_HEADERS = {
    'User-Agent': 'VoiceSpark/1.0',
}


class WordpressService:
    def __init__(self, connection):
        self.connection = connection
        self.site_url = connection.site_url.rstrip('/')
        self.username = connection.wp_username
        self.password = decrypt_data(connection.encrypted_password)
        self.token = None
        self.auth_mode = None

    def _headers(self):
        """Return headers dict including JWT auth when available."""
        headers = dict(_BASE_HEADERS)
        if not self.auth_mode:
            self.authenticate()
        if self.auth_mode == 'bearer':
            headers['Authorization'] = f'Bearer {self.token}'
            headers['X-VoiceSpark-Auth'] = self.token
        elif self.auth_mode == 'basic':
            credentials = f'{self.username}:{self.password}'.encode('utf-8')
            headers['Authorization'] = f'Basic {base64.b64encode(credentials).decode("ascii")}'
        return headers

    def _authenticate_basic(self):
        url = f"{self.site_url}/wp-json/wp/v2/users/me"
        credentials = f'{self.username}:{self.password}'.encode('utf-8')
        headers = dict(_BASE_HEADERS)
        headers['Authorization'] = f'Basic {base64.b64encode(credentials).decode("ascii")}'
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        self.auth_mode = 'basic'
        self.token = None
        return True

    def authenticate(self):
        basic_error = None
        try:
            self._authenticate_basic()
            return True
        except Exception as exc:
            basic_error = exc

        url = f"{self.site_url}/wp-json/voicespark/v1/token"
        try:
            response = requests.post(
                url,
                json={'username': self.username, 'password': self.password},
                headers=_BASE_HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            self.token = data.get('token')
            if not self.token:
                raise Exception("No token received from WordPress")
            self.auth_mode = 'bearer'
            return self.token
        except requests.exceptions.ConnectionError:
            raise Exception(
                f"Could not connect to {self.site_url}. "
                "Please verify the URL is correct and the VoiceSpark plugin is installed."
            )
        except requests.exceptions.Timeout:
            raise Exception(f"Connection to {self.site_url} timed out.")
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 'unknown'
            if status_code == 404:
                raise Exception(
                    f"VoiceSpark plugin not found at {self.site_url}, and WordPress application password authentication failed: {basic_error}"
                )
            if status_code in (401, 403):
                raise Exception(f"Invalid WordPress credentials. Application password authentication failed: {basic_error}")
            raise Exception(f"WordPress returned HTTP {status_code}: {str(e)}")
        except Exception as e:
            logger.error("WordPress Auth Failed for %s: %s", self.site_url, str(e))
            raise

    def fetch_categories(self):
        url = f"{self.site_url}/wp-json/wp/v2/categories"
        try:
            response = requests.get(url, headers=self._headers(), params={'per_page': 100}, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to fetch WP categories: %s", str(e))
            return []

    def fetch_tags(self):
        url = f"{self.site_url}/wp-json/wp/v2/tags"
        try:
            response = requests.get(url, headers=self._headers(), params={'per_page': 100}, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to fetch WP tags: %s", str(e))
            return []

    def publish_post(self, title, content, status='draft', scheduled_date=None,
                     categories=None, tags=None, featured_media_url=None, excerpt=None):
        url = f"{self.site_url}/wp-json/wp/v2/posts"

        # Featured image handling (WP requires uploading media first to get ID)
        featured_id = None
        if featured_media_url:
            featured_id = self._upload_media(featured_media_url)

        payload = {
            'title': title,
            'content': content,
            'status': status,
        }
        if excerpt:
            payload['excerpt'] = excerpt
        if scheduled_date:
            payload['date'] = scheduled_date
            payload['status'] = 'future'
        if categories:
            payload['categories'] = categories
        if tags:
            payload['tags'] = tags
        if featured_id:
            payload['featured_media'] = featured_id

        try:
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to publish to WP: %s", str(e))
            raise

    def _upload_media(self, image_url):
        """Download image from URL and upload to WP media library. Returns media ID or None."""
        try:
            image_url = public_media_url(image_url)
            if not image_url:
                return None
            img_response = requests.get(image_url, timeout=15, stream=True)
            img_response.raise_for_status()
            content_type = img_response.headers.get('Content-Type', 'image/jpeg')
            filename = image_url.split('/')[-1].split('?')[0] or 'featured.jpg'
            upload_headers = dict(self._headers())
            upload_headers['Content-Type'] = content_type
            upload_headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            upload_response = requests.post(
                f"{self.site_url}/wp-json/wp/v2/media",
                headers=upload_headers,
                data=img_response.content,
                timeout=30,
            )
            upload_response.raise_for_status()
            return upload_response.json().get('id')
        except Exception as e:
            logger.warning("Failed to upload featured media to WP: %s", str(e))
            return None
