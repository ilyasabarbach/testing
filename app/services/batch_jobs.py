import asyncio
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.schemas import (
    ChapterBatchCreateResponse,
    ChapterBatchItemStatus,
    ChapterBatchStatusResponse,
    ChapterCaptureResponse,
    ChapterPreviewResponse,
)
from app.services.browser_capture import capture_chapter_images
from app.services.chapter_preview import build_chapter_preview
from app.services.http_client import TargetFetchError


JOB_NOT_FOUND_MESSAGE = "Batch job was not found."
MAX_URLS_EXCEEDED_TEMPLATE = "Batch request exceeds maximum URL count of {max_urls}."


@dataclass
class BatchJobItem:
    index: int
    url: str
    status: str = "pending"
    image_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    error: str | None = None
    result: dict | None = None


@dataclass
class BatchJob:
    job_id: str
    analysis_mode: str
    total_urls: int
    created_at: str
    report_path: str
    duration_seconds: int
    stop_policy: str
    status: str = "queued"
    completed_urls: int = 0
    failed_urls: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    items: list[BatchJobItem] = field(default_factory=list)


_jobs: dict[str, BatchJob] = {}
_job_tasks: dict[str, asyncio.Task[None]] = {}
_jobs_lock = threading.Lock()


def create_batch_job(
    urls: list[str],
    analysis_mode: str,
    duration_seconds: int | None,
    stop_policy: str | None,
) -> ChapterBatchCreateResponse:
    settings = get_settings()
    if not urls:
        raise ValueError("Batch request must include at least one URL.")
    if len(urls) > settings.batch_max_urls:
        raise ValueError(
            MAX_URLS_EXCEEDED_TEMPLATE.format(max_urls=settings.batch_max_urls)
        )

    job_id = uuid4().hex
    created_at = _utc_now()
    report_path = _build_report_path(job_id)
    effective_duration_seconds = (
        duration_seconds
        if duration_seconds is not None
        else settings.browser_capture_default_seconds
    )
    effective_stop_policy = stop_policy or settings.browser_capture_stop_policy
    job = BatchJob(
        job_id=job_id,
        analysis_mode=analysis_mode,
        total_urls=len(urls),
        created_at=created_at,
        report_path=report_path,
        duration_seconds=effective_duration_seconds,
        stop_policy=effective_stop_policy,
        items=[
            BatchJobItem(index=index, url=url)
            for index, url in enumerate(urls, start=1)
        ],
    )

    with _jobs_lock:
        _jobs[job_id] = job

    task = asyncio.create_task(_run_batch_job(job_id))
    with _jobs_lock:
        _job_tasks[job_id] = task
    task.add_done_callback(lambda finished_task, current_job_id=job_id: _discard_task(current_job_id))

    return ChapterBatchCreateResponse(
        jobId=job_id,
        status=job.status,
        totalUrls=job.total_urls,
        completedUrls=job.completed_urls,
        failedUrls=job.failed_urls,
        createdAt=job.created_at,
        statusUrl=f"/api/chapters/batch/{job_id}",
    )


def get_batch_job(job_id: str) -> ChapterBatchStatusResponse:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise ValueError(JOB_NOT_FOUND_MESSAGE)
        return _serialize_job(job)


async def _run_batch_job(job_id: str) -> None:
    job_started_monotonic = time.monotonic()
    _set_job_started(job_id)

    try:
        with _jobs_lock:
            job = _jobs[job_id]
            analysis_mode = job.analysis_mode
            duration_seconds = job.duration_seconds
            stop_policy = job.stop_policy
            items = list(job.items)

        for item in items:
            item_started_monotonic = time.monotonic()
            _set_item_running(job_id, item.index)

            try:
                result = await _run_batch_item(
                    item.url,
                    analysis_mode,
                    duration_seconds,
                    stop_policy,
                )
            except (TargetFetchError, ValueError) as exc:
                _set_item_failed(
                    job_id,
                    item.index,
                    str(exc),
                    _duration_ms_since(item_started_monotonic),
                )
            except Exception:
                _set_item_failed(
                    job_id,
                    item.index,
                    "Batch item failed.",
                    _duration_ms_since(item_started_monotonic),
                )
            else:
                _set_item_success(
                    job_id,
                    item.index,
                    _serialize_result(result),
                    result.imageCount,
                    _duration_ms_since(item_started_monotonic),
                )

            _write_batch_report(job_id)

        _set_job_finished(job_id, _duration_ms_since(job_started_monotonic))
        _write_batch_report(job_id)
    except Exception:
        _set_job_failed(job_id, _duration_ms_since(job_started_monotonic))
        _write_batch_report(job_id)


async def _run_batch_item(
    url: str,
    analysis_mode: str,
    duration_seconds: int,
    stop_policy: str,
) -> ChapterPreviewResponse | ChapterCaptureResponse:
    if analysis_mode == "static_preview":
        return await build_chapter_preview(url, "static")
    if analysis_mode == "browser_preview":
        return await build_chapter_preview(url, "browser")
    return await capture_chapter_images(
        url,
        duration_seconds,
        "autonomous",
        stop_policy,
    )


def _set_job_started(job_id: str) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        job.status = "running"
        job.started_at = _utc_now()


def _set_item_running(job_id: str, item_index: int) -> None:
    with _jobs_lock:
        item = _jobs[job_id].items[item_index - 1]
        item.status = "running"
        item.started_at = _utc_now()


def _set_item_success(
    job_id: str,
    item_index: int,
    result: dict,
    image_count: int,
    duration_ms: int,
) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        item = job.items[item_index - 1]
        item.status = "success"
        item.image_count = image_count
        item.finished_at = _utc_now()
        item.duration_ms = duration_ms
        item.result = result
        item.error = None
        job.completed_urls = sum(
            1 for current_item in job.items if current_item.status == "success"
        )
        job.failed_urls = sum(
            1 for current_item in job.items if current_item.status == "failed"
        )


def _set_item_failed(
    job_id: str,
    item_index: int,
    error: str,
    duration_ms: int,
) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        item = job.items[item_index - 1]
        item.status = "failed"
        item.finished_at = _utc_now()
        item.duration_ms = duration_ms
        item.error = error
        item.result = None
        item.image_count = 0
        job.completed_urls = sum(
            1 for current_item in job.items if current_item.status == "success"
        )
        job.failed_urls = sum(
            1 for current_item in job.items if current_item.status == "failed"
        )


def _set_job_finished(job_id: str, duration_ms: int) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        job.finished_at = _utc_now()
        job.duration_ms = duration_ms
        if job.failed_urls == 0:
            job.status = "completed"
        elif job.completed_urls == 0:
            job.status = "failed"
        else:
            job.status = "completed_with_errors"


def _set_job_failed(job_id: str, duration_ms: int) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        job.finished_at = _utc_now()
        job.duration_ms = duration_ms
        job.status = "failed"


def _write_batch_report(job_id: str) -> None:
    settings = get_settings()
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        payload = _serialize_job(job).model_dump()

    report_directory = Path(settings.batch_report_base_dir) / job_id
    report_directory.mkdir(parents=True, exist_ok=True)
    report_path = report_directory / "batch-report.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _serialize_job(job: BatchJob) -> ChapterBatchStatusResponse:
    return ChapterBatchStatusResponse(
        jobId=job.job_id,
        status=job.status,
        analysisMode=job.analysis_mode,
        totalUrls=job.total_urls,
        completedUrls=job.completed_urls,
        failedUrls=job.failed_urls,
        createdAt=job.created_at,
        startedAt=job.started_at,
        finishedAt=job.finished_at,
        durationMs=job.duration_ms,
        items=[
            ChapterBatchItemStatus(
                index=item.index,
                url=item.url,
                status=item.status,
                imageCount=item.image_count,
                startedAt=item.started_at,
                finishedAt=item.finished_at,
                durationMs=item.duration_ms,
                error=item.error,
                result=item.result,
            )
            for item in job.items
        ],
        reportPath=job.report_path,
    )


def _serialize_result(result: ChapterPreviewResponse | ChapterCaptureResponse) -> dict:
    return result.model_dump()


def _build_report_path(job_id: str) -> str:
    settings = get_settings()
    return f"{settings.batch_report_base_dir.rstrip('/\\\\')}/{job_id}/batch-report.json"


def _duration_ms_since(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _discard_task(job_id: str) -> None:
    with _jobs_lock:
        _job_tasks.pop(job_id, None)
