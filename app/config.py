import os
from dataclasses import dataclass


SUPPORTED_URL_ACCESS_MODES = {"local_only", "allowlist", "open"}
SUPPORTED_HTTP_SCHEMES = {"http", "https"}


@dataclass
class Settings:
    url_access_mode: str
    allowed_hosts: list[str]
    http_timeout_seconds: float
    default_image_extension: str
    download_base_dir: str


def _parse_allowed_hosts(raw_value: str) -> list[str]:
    return [host.strip().lower() for host in raw_value.split(",") if host.strip()]


def get_settings() -> Settings:
    url_access_mode = os.getenv("URL_ACCESS_MODE", "local_only").strip().lower()
    if url_access_mode not in SUPPORTED_URL_ACCESS_MODES:
        url_access_mode = "local_only"

    allowed_hosts = _parse_allowed_hosts(
        os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    )

    timeout_raw = os.getenv("HTTP_TIMEOUT_SECONDS", "10").strip()
    try:
        http_timeout_seconds = float(timeout_raw)
    except ValueError:
        http_timeout_seconds = 10.0

    if http_timeout_seconds <= 0:
        http_timeout_seconds = 10.0

    default_image_extension = os.getenv("DEFAULT_IMAGE_EXTENSION", ".jpg").strip()
    if not default_image_extension.startswith("."):
        default_image_extension = f".{default_image_extension}"

    download_base_dir = os.getenv("DOWNLOAD_BASE_DIR", "downloads").strip() or "downloads"

    return Settings(
        url_access_mode=url_access_mode,
        allowed_hosts=allowed_hosts,
        http_timeout_seconds=http_timeout_seconds,
        default_image_extension=default_image_extension.lower(),
        download_base_dir=download_base_dir,
    )
