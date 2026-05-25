import importlib
import httpx
import ssl

from app.config import get_settings


class TargetFetchError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


HTML_ACCEPT_HEADER = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
)
IMAGE_ACCEPT_HEADER = "image/*,*/*;q=0.8"


async def fetch_text(url: str) -> str:
    return await _fetch_response_content(url, expect_text=True, request_kind="html")


async def fetch_bytes(url: str) -> bytes:
    return await _fetch_response_content(url, expect_text=False, request_kind="image")


async def get_response(
    url: str,
    follow_redirects: bool,
    request_kind: str = "html",
) -> httpx.Response:
    settings = get_settings()

    try:
        async with httpx.AsyncClient(
            follow_redirects=follow_redirects,
            timeout=settings.http_timeout_seconds,
            headers=_build_headers(request_kind),
            verify=_build_verify_config(),
        ) as client:
            return await client.get(url)
    except httpx.TimeoutException as exc:
        raise TargetFetchError(
            "Target request timed out.",
            504,
        ) from exc
    except httpx.ConnectError as exc:
        if _is_ssl_verification_error(exc):
            raise TargetFetchError(
                "SSL certificate verification failed for target.",
                502,
            ) from exc
        raise TargetFetchError(
            "Target page could not be reached.",
            502,
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise TargetFetchError(
            "Target server returned an error response.",
            502,
        ) from exc
    except httpx.HTTPError as exc:
        raise TargetFetchError(
            "Target page could not be reached.",
            502,
        ) from exc
    except ImportError as exc:
        raise TargetFetchError(
            str(exc),
            500,
        ) from exc


async def _fetch_response_content(
    url: str, expect_text: bool, request_kind: str
) -> str | bytes:
    try:
        response = await get_response(url, follow_redirects=True, request_kind=request_kind)
        response.raise_for_status()
        if expect_text:
            return response.text
        return response.content
    except httpx.HTTPStatusError as exc:
        raise TargetFetchError(
            "Target server returned an error response.",
            502,
        ) from exc


def _is_ssl_verification_error(exc: httpx.ConnectError) -> bool:
    cause = exc.__cause__
    if isinstance(cause, ssl.SSLCertVerificationError):
        return True

    message = str(exc).lower()
    return "certificate verify failed" in message or "certificate verification failed" in message


def _build_headers(request_kind: str) -> dict[str, str]:
    settings = get_settings()
    accept = HTML_ACCEPT_HEADER if request_kind == "html" else IMAGE_ACCEPT_HEADER
    return {
        "User-Agent": settings.http_user_agent,
        "Accept": accept,
    }


def _build_verify_config():
    settings = get_settings()

    if settings.ssl_verify_mode == "disabled":
        return False

    if settings.ssl_verify_mode == "truststore":
        try:
            truststore = importlib.import_module("truststore")
        except ModuleNotFoundError as exc:
            raise ImportError(
                "SSL truststore mode requires the truststore package."
            ) from exc
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    return True
