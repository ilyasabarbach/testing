from urllib.parse import urlparse

from app.config import SUPPORTED_HTTP_SCHEMES, get_settings


LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def validate_target_url(url: str) -> None:
    parsed = urlparse(url)
    settings = get_settings()

    if not parsed.scheme:
        raise ValueError("URL must include http:// or https:// scheme.")

    if parsed.scheme not in SUPPORTED_HTTP_SCHEMES:
        raise ValueError("Only http and https URLs are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must include a hostname.")

    normalized_host = hostname.lower()
    mode = settings.url_access_mode

    if mode == "open":
        return

    if mode == "local_only":
        if normalized_host in LOCAL_HOSTS:
            return
        raise ValueError(
            "URL host is not allowed in local_only mode. Use localhost or 127.0.0.1."
        )

    if normalized_host in settings.allowed_hosts:
        return

    raise ValueError("URL host is not allowed in allowlist mode.")
