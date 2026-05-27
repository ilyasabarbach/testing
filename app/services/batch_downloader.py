from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import re
import time
from urllib.parse import urlparse

from app.config import get_settings
from app.schemas import (
    ChapterBatchDownloadItemResponse,
    ChapterBatchDownloadResponse,
)
from app.services.batch_jobs import get_batch_job
from app.services.http_client import TargetFetchError, fetch_bytes
from app.services.url_policy import validate_target_url


NO_SUCCESSFUL_ITEMS_MESSAGE = "Batch job has no successful items to download."
INVALID_BATCH_ITEM_MESSAGE = "Batch job item was not found."
WINDOWS_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*]+')
CHAPTER_PATTERN = re.compile(r"chapter[-_\s]*(\d+(?:\.\d+)?)", re.IGNORECASE)


async def download_batch_job_results(
    job_id: str,
    item_index: int | None = None,
) -> ChapterBatchDownloadResponse:
    job = get_batch_job(job_id)
    successful_items = [
        item
        for item in job.items
        if item.status == "success"
        and isinstance(item.result, dict)
        and isinstance(item.result.get("images"), list)
    ]

    if item_index is not None:
        successful_items = [
            item for item in successful_items if int(item.index) == int(item_index)
        ]
        if not successful_items:
            raise ValueError(INVALID_BATCH_ITEM_MESSAGE)

    if not successful_items:
        raise ValueError(NO_SUCCESSFUL_ITEMS_MESSAGE)

    settings = get_settings()
    base_directory = Path(settings.batch_download_base_dir)
    base_directory.mkdir(parents=True, exist_ok=True)
    started_time = time.perf_counter()
    item_reports: list[ChapterBatchDownloadItemResponse] = []
    downloaded_images = 0
    failed_images = 0

    for item in successful_items:
        source_url = str(item.url)
        folder = infer_batch_download_folder(base_directory, source_url)
        folder.mkdir(parents=True, exist_ok=True)
        images = item.result.get("images", [])
        item_downloaded = 0
        item_failed = 0
        item_error = None

        for image in images:
            image_url = str(image.get("url", "")).strip()
            filename = str(image.get("filename", "")).strip()
            if not image_url or not filename:
                item_failed += 1
                failed_images += 1
                continue
            try:
                validate_target_url(image_url)
                content = await fetch_bytes(image_url)
                destination = folder / sanitize_filename(filename)
                destination.write_bytes(content)
                item_downloaded += 1
                downloaded_images += 1
            except (ValueError, TargetFetchError) as exc:
                item_failed += 1
                failed_images += 1
                item_error = str(exc)

        item_reports.append(
            ChapterBatchDownloadItemResponse(
                index=item.index,
                url=source_url,
                folder=folder.as_posix(),
                imageCount=len(images),
                downloadedImages=item_downloaded,
                failedImages=item_failed,
                error=item_error,
            )
        )

    response = ChapterBatchDownloadResponse(
        jobId=job.jobId,
        status=(
            "completed"
            if all(item.failedImages == 0 and item.error is None for item in item_reports)
            else "completed_with_errors"
        ),
        downloadBaseDirectory=base_directory.as_posix(),
        successfulItems=sum(1 for item in item_reports if item.error is None),
        failedItems=sum(1 for item in item_reports if item.error is not None),
        totalImages=sum(item.imageCount for item in item_reports),
        downloadedImages=downloaded_images,
        failedImages=failed_images,
        items=item_reports,
        reportPath="",
    )
    response.reportPath = _write_batch_download_report(job.jobId, base_directory, response)
    return response


def infer_batch_download_folder(base_directory: Path, source_url: str) -> Path:
    parsed = urlparse(source_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    title_name = None
    chapter_name = None

    for part in path_parts:
        chapter_match = CHAPTER_PATTERN.search(part)
        if chapter_match:
            chapter_name = f"Chapter {format_chapter_number(chapter_match.group(1))}"
            continue
        if _looks_like_slug(part) or title_name is None:
            title_name = slug_to_title(part)
            continue
        title_name = slug_to_title(part)

    if title_name is None:
        title_name = fallback_title_name(parsed)
    if chapter_name is None:
        chapter_name = fallback_chapter_name(path_parts)

    return base_directory / sanitize_folder_name(title_name) / sanitize_folder_name(
        chapter_name
    )


def slug_to_title(value: str) -> str:
    slug = re.sub(
        r"^(?=[a-z0-9]*\d)[a-z0-9]{4,}-",
        "",
        value.strip(),
        count=1,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[-_]+", " ", slug)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title() or "Untitled"


def sanitize_folder_name(value: str) -> str:
    sanitized = WINDOWS_INVALID_PATH_CHARS.sub(" ", value).replace("..", " ")
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    return sanitized or "Unknown"


def sanitize_filename(value: str) -> str:
    path = PurePosixPath(value)
    suffix = path.suffix
    stem = WINDOWS_INVALID_PATH_CHARS.sub(" ", path.stem).replace("..", " ")
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    if not stem:
        stem = "image"
    return f"{stem}{suffix}"


def format_chapter_number(value: str) -> str:
    cleaned = value.strip()
    if "." in cleaned:
        return cleaned
    return str(int(cleaned))


def fallback_title_name(parsed_url) -> str:
    host = sanitize_folder_name(parsed_url.netloc or "unknown-host")
    return host


def fallback_chapter_name(path_parts: list[str]) -> str:
    if not path_parts:
        return "Root"
    return sanitize_folder_name(path_parts[-1])


def _looks_like_slug(value: str) -> bool:
    lowered = value.lower()
    if CHAPTER_PATTERN.search(lowered):
        return False
    return "-" in lowered or "_" in lowered


def _write_batch_download_report(
    job_id: str,
    base_directory: Path,
    report: ChapterBatchDownloadResponse,
) -> str:
    report_directory = base_directory / job_id
    report_directory.mkdir(parents=True, exist_ok=True)
    report_path = report_directory / "batch-download-report.json"
    payload = report.model_dump()
    payload["reportPath"] = report_path.as_posix()
    payload["createdAt"] = datetime.now(UTC).isoformat()
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return report_path.as_posix()
