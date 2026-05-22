import httpx

from app.config import get_settings


class TargetFetchError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def fetch_text(url: str) -> str:
    return await _fetch_response_content(url, expect_text=True)


async def fetch_bytes(url: str) -> bytes:
    return await _fetch_response_content(url, expect_text=False)


async def _fetch_response_content(url: str, expect_text: bool) -> str | bytes:
    settings = get_settings()

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.http_timeout_seconds,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            if expect_text:
                return response.text
            return response.content
    except httpx.TimeoutException as exc:
        raise TargetFetchError(
            "Target request timed out.",
            504,
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
