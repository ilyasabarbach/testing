from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas import (
    ChapterBatchCreateResponse,
    ChapterBatchDownloadResponse,
    ChapterBatchRequest,
    ChapterBatchStatusResponse,
    ChapterCaptureRequest,
    ChapterCaptureResponse,
    ChapterDownloadResponse,
    NetworkInspectRequest,
    NetworkInspectResponse,
    ChapterPreviewRequest,
    ChapterPreviewResponse,
    RuntimeConfigResponse,
)
from app.services.batch_downloader import download_batch_job_results
from app.services.batch_jobs import create_batch_job, get_batch_job
from app.services.browser_capture import capture_chapter_images
from app.services.chapter_preview import build_chapter_preview
from app.services.image_downloader import download_chapter_images
from app.services.http_client import TargetFetchError
from app.services.network_inspector import inspect_network
from app.services.report_writer import ReportWriteError
from app.services.url_policy import validate_target_url


router = APIRouter()


@router.get("/api/runtime/config", response_model=RuntimeConfigResponse)
async def get_runtime_config() -> RuntimeConfigResponse:
    settings = get_settings()
    return RuntimeConfigResponse(
        urlAccessMode=settings.url_access_mode,
        browserHeadless=settings.browser_headless,
        browserPersistentContextEnabled=settings.browser_persistent_context_enabled,
        browserUserDataDirConfigured=bool(settings.browser_user_data_dir),
        browserCaptureMaxSeconds=settings.browser_capture_max_seconds,
        browserAutonomousMaxSteps=settings.browser_autonomous_max_steps,
        browserAutonomousStepWaitMs=settings.browser_autonomous_step_wait_ms,
        browserSmartStopMinSteps=settings.browser_smart_stop_min_steps,
        browserSmartStopStableRounds=settings.browser_smart_stop_stable_rounds,
        browserLargeSequenceModeEnabled=settings.browser_large_sequence_mode_enabled,
        browserLargeSequenceMinLength=settings.browser_large_sequence_min_length,
        browserLargeSequenceMaxSteps=settings.browser_large_sequence_max_steps,
        browserLargeSequenceStepWaitMs=settings.browser_large_sequence_step_wait_ms,
        browserLargeSequenceExtendWhileGrowing=settings.browser_large_sequence_extend_while_growing,
        browserLargeSequenceStableRounds=settings.browser_large_sequence_stable_rounds,
        batchMaxUrls=settings.batch_max_urls,
        batchReportBaseDir=settings.batch_report_base_dir,
        batchDownloadBaseDir=settings.batch_download_base_dir,
    )


@router.post("/api/chapters/preview", response_model=ChapterPreviewResponse)
async def preview_chapter(payload: ChapterPreviewRequest) -> ChapterPreviewResponse:
    try:
        validate_target_url(payload.url)
        return await build_chapter_preview(payload.url, payload.renderMode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TargetFetchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/api/chapters/capture", response_model=ChapterCaptureResponse)
async def capture_chapter(payload: ChapterCaptureRequest) -> ChapterCaptureResponse:
    try:
        validate_target_url(payload.url)
        return await capture_chapter_images(
            payload.url,
            payload.durationSeconds,
            payload.captureMode,
            payload.stopPolicy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TargetFetchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/api/chapters/batch",
    response_model=ChapterBatchCreateResponse,
    status_code=202,
)
async def create_batch(payload: ChapterBatchRequest) -> ChapterBatchCreateResponse:
    try:
        for url in payload.urls:
            validate_target_url(url)
        return create_batch_job(
            payload.urls,
            payload.analysisMode,
            payload.durationSeconds,
            payload.stopPolicy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/chapters/batch/{job_id}",
    response_model=ChapterBatchStatusResponse,
)
async def get_batch(job_id: str) -> ChapterBatchStatusResponse:
    try:
        return get_batch_job(job_id)
    except ValueError as exc:
        if str(exc) == "Batch job was not found.":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/chapters/batch/{job_id}/download",
    response_model=ChapterBatchDownloadResponse,
)
async def download_batch(job_id: str) -> ChapterBatchDownloadResponse:
    try:
        return await download_batch_job_results(job_id)
    except ValueError as exc:
        if str(exc) == "Batch job was not found.":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/chapters/batch/{job_id}/items/{item_index}/download",
    response_model=ChapterBatchDownloadResponse,
)
async def download_batch_item(
    job_id: str,
    item_index: int,
) -> ChapterBatchDownloadResponse:
    try:
        return await download_batch_job_results(job_id, item_index)
    except ValueError as exc:
        if str(exc) == "Batch job was not found.":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/chapters/download", response_model=ChapterDownloadResponse)
async def download_chapter(payload: ChapterPreviewRequest) -> ChapterDownloadResponse:
    try:
        validate_target_url(payload.url)
        return await download_chapter_images(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TargetFetchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ReportWriteError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/network/inspect", response_model=NetworkInspectResponse)
async def inspect_network_route(
    payload: NetworkInspectRequest,
) -> NetworkInspectResponse:
    try:
        validate_target_url(payload.url)
        return await inspect_network(payload.url, payload.followRedirects)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TargetFetchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
