import os
from urllib.parse import urlparse


LEGACY_MEDIA_HOSTS = {
    "134-209-146-170.sslip.io",
}


def public_media_url(value, base_url=None):
    raw = str(value or "").strip()
    if not raw:
        return ""
    host = (
        base_url
        or os.getenv("PUBLIC_BACKEND_URL")
        or os.getenv("BACKEND_URL")
        or "https://api.voicespark.ai"
    )
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https"):
        if parsed.netloc in LEGACY_MEDIA_HOSTS and parsed.path.startswith("/media/"):
            return f"{host.rstrip('/')}/{parsed.path.lstrip('/')}"
        return raw
    if raw.startswith("//"):
        return f"https:{raw}"
    if not raw.startswith("/"):
        raw = f"/media/{raw.lstrip('/')}"
    return f"{host.rstrip('/')}/{raw.lstrip('/')}"
