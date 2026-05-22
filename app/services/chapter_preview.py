from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

from app.config import get_settings
from app.schemas import ChapterImagePreview, ChapterPreviewResponse
from app.services.http_client import fetch_text


class ImageSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.image_sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return

        attributes = dict(attrs)
        src = attributes.get("src")
        if src:
            self.image_sources.append(src)


def extract_image_urls(source_url: str, html: str) -> list[str]:
    parser = ImageSrcParser()
    parser.feed(html)
    return [urljoin(source_url, src) for src in parser.image_sources]


def build_filename(index: int, image_url: str) -> str:
    settings = get_settings()
    path = urlparse(image_url).path
    suffix = PurePosixPath(path).suffix.lower() or settings.default_image_extension
    return f"{index:03d}{suffix}"


async def build_chapter_preview(source_url: str) -> ChapterPreviewResponse:
    html = await fetch_text(source_url)
    return build_chapter_preview_from_html(source_url, html)


def build_chapter_preview_from_html(
    source_url: str, html: str
) -> ChapterPreviewResponse:
    image_urls = extract_image_urls(source_url, html)

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
    )
