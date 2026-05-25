from pathlib import PurePosixPath
from urllib.parse import urlparse

from app.config import get_settings
from app.schemas import (
    ChapterImagePreview,
    ChapterPreviewDiagnostics,
    ChapterPreviewResponse,
)
from app.services.embedded_json_extractor import extract_images_from_embedded_json
from app.services.html_image_extractor import extract_images_with_diagnostics
from app.services.http_client import fetch_text


def build_filename(index: int, image_url: str) -> str:
    settings = get_settings()
    path = urlparse(image_url).path
    suffix = PurePosixPath(path).suffix.lower() or settings.default_image_extension
    return f"{index:03d}{suffix}"


def build_preview_response(
    source_url: str, image_urls: list[str], diagnostics: dict
) -> ChapterPreviewResponse:
    images = [
        ChapterImagePreview(
            index=index,
            url=image_url,
            filename=build_filename(index, image_url),
        )
        for index, image_url in enumerate(image_urls, start=1)
    ]

    return ChapterPreviewResponse(
        sourceUrl=source_url,
        imageCount=len(images),
        images=images,
        diagnostics=ChapterPreviewDiagnostics(**diagnostics),
    )


async def build_chapter_preview(
    source_url: str, render_mode: str = "static"
) -> ChapterPreviewResponse:
    if render_mode == "browser":
        from app.services.browser_preview import build_browser_chapter_preview

        return await build_browser_chapter_preview(source_url)

    html = await fetch_text(source_url)
    return build_chapter_preview_from_html(source_url, html)


def build_chapter_preview_from_html(
    source_url: str, html: str
) -> ChapterPreviewResponse:
    image_urls, diagnostics = extract_images_with_diagnostics(source_url, html)
    embedded_json_urls, json_diagnostics = extract_images_from_embedded_json(
        source_url,
        html,
        existing_urls=image_urls,
    )
    image_urls.extend(embedded_json_urls)
    diagnostics.update(
        {
            "jsonScriptCount": json_diagnostics["jsonScriptCount"],
            "embeddedImageUrlCount": json_diagnostics["embeddedImageUrlCount"],
            "imagesFromEmbeddedJson": json_diagnostics["imagesFromEmbeddedJson"],
            "hasAppRootShell": json_diagnostics["hasAppRootShell"],
            "possibleApiDrivenPage": json_diagnostics["possibleApiDrivenPage"],
            "renderModeUsed": "static",
            "browserRendered": False,
            "domImageCount": 0,
            "browserFilteredImageCount": 0,
            "browserExtractionNotes": [],
        }
    )
    diagnostics["notes"] = diagnostics["notes"] + [
        note for note in json_diagnostics["jsonNotes"] if note not in diagnostics["notes"]
    ]
    return build_preview_response(source_url, image_urls, diagnostics)
