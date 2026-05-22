from pydantic import BaseModel


class ChapterPreviewRequest(BaseModel):
    url: str


class ChapterImagePreview(BaseModel):
    index: int
    url: str
    filename: str


class ChapterPreviewResponse(BaseModel):
    sourceUrl: str
    imageCount: int
    images: list[ChapterImagePreview]


class ChapterDownloadImageResult(BaseModel):
    index: int
    url: str
    filename: str
    status: str
    path: str | None
    error: str | None


class ChapterDownloadResponse(BaseModel):
    runId: str
    sourceUrl: str
    imageCount: int
    downloadDirectory: str
    startedAt: str
    finishedAt: str
    durationMs: int
    successCount: int
    failedCount: int
    images: list[ChapterDownloadImageResult]
