from fastapi import APIRouter, HTTPException

from app.schemas import (
    ChapterCaptureRequest,
    ChapterCaptureResponse,
    ChapterDownloadResponse,
    NetworkInspectRequest,
    NetworkInspectResponse,
    ChapterPreviewRequest,
    ChapterPreviewResponse,
)
from app.services.browser_capture import capture_chapter_images
from app.services.chapter_preview import build_chapter_preview
from app.services.image_downloader import download_chapter_images
from app.services.http_client import TargetFetchError
from app.services.network_inspector import inspect_network
from app.services.report_writer import ReportWriteError
from app.services.url_policy import validate_target_url


router = APIRouter()


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
