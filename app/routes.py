from fastapi import APIRouter, HTTPException

from app.schemas import (
    ChapterDownloadResponse,
    ChapterPreviewRequest,
    ChapterPreviewResponse,
)
from app.services.chapter_preview import build_chapter_preview
from app.services.image_downloader import download_chapter_images
from app.services.http_client import TargetFetchError
from app.services.report_writer import ReportWriteError
from app.services.url_policy import validate_target_url


router = APIRouter()


@router.post("/api/chapters/preview", response_model=ChapterPreviewResponse)
async def preview_chapter(payload: ChapterPreviewRequest) -> ChapterPreviewResponse:
    try:
        validate_target_url(payload.url)
        return await build_chapter_preview(payload.url)
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
