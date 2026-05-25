from app.schemas import NetworkInspectResponse
from app.services.http_client import get_response


BODY_PREVIEW_LIMIT = 500


async def inspect_network(url: str, follow_redirects: bool) -> NetworkInspectResponse:
    response = await get_response(url, follow_redirects, request_kind="html")

    redirect_location = response.headers.get("location")
    content_type = response.headers.get("content-type")
    server = response.headers.get("server")
    body_preview = response.text[:BODY_PREVIEW_LIMIT]

    return NetworkInspectResponse(
        url=url,
        finalUrl=str(response.url),
        statusCode=response.status_code,
        isRedirect=response.is_redirect,
        redirectLocation=redirect_location,
        contentType=content_type,
        server=server,
        bodyPreview=body_preview,
    )
