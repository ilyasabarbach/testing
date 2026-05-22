from datetime import UTC, datetime
from pathlib import Path
import time
import secrets

from app.config import get_settings
from app.schemas import ChapterDownloadImageResult, ChapterDownloadResponse
from app.services.chapter_preview import build_chapter_preview
from app.services.http_client import TargetFetchError, fetch_bytes
from app.services.report_writer import write_report_json
from app.services.url_policy import validate_target_url


def create_download_directory() -> tuple[str, Path]:
    settings = get_settings()
    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"
    download_directory = Path(settings.download_base_dir) / run_id
    download_directory.mkdir(parents=True, exist_ok=False)
    return run_id, download_directory


async def download_chapter_images(source_url: str) -> ChapterDownloadResponse:
    started_at = datetime.now(UTC)
    started_time = time.perf_counter()
    preview = await build_chapter_preview(source_url)
    run_id, download_directory = create_download_directory()
    image_results: list[ChapterDownloadImageResult] = []

    for image in preview.images:
        try:
            validate_target_url(image.url)
            content = await fetch_bytes(image.url)
            destination = download_directory / image.filename
            destination.write_bytes(content)
            image_results.append(
                ChapterDownloadImageResult(
                    index=image.index,
                    url=image.url,
                    filename=image.filename,
                    status="downloaded",
                    path=destination.as_posix(),
                    error=None,
                )
            )
        except (ValueError, TargetFetchError) as exc:
            image_results.append(
                ChapterDownloadImageResult(
                    index=image.index,
                    url=image.url,
                    filename=image.filename,
                    status="failed",
                    path=None,
                    error=str(exc),
                )
            )

    finished_at = datetime.now(UTC)
    duration_ms = round((time.perf_counter() - started_time) * 1000)
    success_count = sum(1 for image in image_results if image.status == "downloaded")
    failed_count = sum(1 for image in image_results if image.status == "failed")

    report = ChapterDownloadResponse(
        runId=run_id,
        sourceUrl=preview.sourceUrl,
        imageCount=preview.imageCount,
        downloadDirectory=download_directory.as_posix(),
        startedAt=started_at.isoformat(),
        finishedAt=finished_at.isoformat(),
        durationMs=duration_ms,
        successCount=success_count,
        failedCount=failed_count,
        images=image_results,
    )

    write_report_json(report.downloadDirectory, report)
    return report
