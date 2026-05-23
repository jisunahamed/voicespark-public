import os
from urllib.parse import urlparse


def public_media_url(value, base_url=None):
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https"):
        return raw
    if raw.startswith("//"):
        return f"https:{raw}"
    if not raw.startswith("/"):
        raw = f"/media/{raw.lstrip('/')}"
    host = (
        base_url
        or os.getenv("PUBLIC_BACKEND_URL")
        or os.getenv("BACKEND_URL")
        or "https://134-209-146-170.sslip.io"
    )
    return f"{host.rstrip('/')}/{raw.lstrip('/')}"
