from typing import Literal

from pydantic import BaseModel


class ChapterPreviewRequest(BaseModel):
    url: str
    renderMode: Literal["static", "browser"] = "static"


class NetworkInspectRequest(BaseModel):
    url: str
    followRedirects: bool = False


class ChapterImagePreview(BaseModel):
    index: int
    url: str
    filename: str


class ChapterPreviewDiagnostics(BaseModel):
    htmlLength: int
    imgTagCount: int
    imagesFromSrc: int
    imagesFromDataSrc: int
    imagesFromDataLazySrc: int
    imagesFromDataOriginal: int
    imagesFromDataUrl: int
    imagesFromSrcset: int
    imagesFromSourceSrcset: int
    imagesFromMeta: int
    jsonScriptCount: int
    embeddedImageUrlCount: int
    imagesFromEmbeddedJson: int
    deduplicatedCount: int
    looksDynamic: bool
    hasAppRootShell: bool
    possibleApiDrivenPage: bool
    renderModeUsed: Literal["static", "browser"]
    browserRendered: bool
    domImageCount: int
    browserFilteredImageCount: int
    browserHeadless: bool
    browserPersistentContextEnabled: bool
    browserUserDataDirConfigured: bool
    browserSessionMode: Literal["ephemeral", "persistent"]
    browserScrollEnabled: bool
    browserScrollSteps: int
    browserScrollHeightBefore: int
    browserScrollHeightAfter: int
    browserLazyLoadWaitMs: int
    browserScrollableContainerCount: int
    browserScrolledContainerCount: int
    browserMouseWheelSteps: int
    browserImageCountBeforeScroll: int
    browserImageCountAfterScroll: int
    browserImageCountStableRounds: int
    browserScrollStrategy: str
    browserExtractionNotes: list[str]
    notes: list[str]


class ChapterPreviewResponse(BaseModel):
    sourceUrl: str
    imageCount: int
    images: list[ChapterImagePreview]
    diagnostics: ChapterPreviewDiagnostics


class ChapterCaptureRequest(BaseModel):
    url: str
    durationSeconds: int = 30
    captureMode: Literal["assisted", "autonomous"] = "assisted"
    stopPolicy: Literal["sequence_stable", "duration"] | None = None


class ChapterCaptureImage(BaseModel):
    index: int
    url: str
    filename: str
    source: Literal["network", "dom"]


class ChapterCaptureDiagnostics(BaseModel):
    browserRendered: bool
    captureMode: Literal["assisted", "autonomous"]
    networkImageCount: int
    domImageCount: int
    deduplicatedCount: int
    browserHeadless: bool
    browserPersistentContextEnabled: bool
    browserUserDataDirConfigured: bool
    browserSessionMode: Literal["ephemeral", "persistent"]
    captureStopPolicy: Literal["sequence_stable", "duration"]
    captureRequestedDurationSeconds: int
    captureActualDurationSeconds: float
    stoppedBecauseSequenceStable: bool
    autonomousModeEnabled: bool
    autonomousStepsExecuted: int
    autonomousActionsUsed: list[str]
    imageCountBeforeAutonomousActions: int
    imageCountAfterAutonomousActions: int
    imageCountStableRounds: int
    observedImageCount: int
    selectedImageCount: int
    excludedImageCount: int
    selectionStrategy: str
    dominantSequenceDetected: bool
    dominantSequenceLength: int
    readerReadinessEnabled: bool
    overlayDismissEnabled: bool
    overlayDismissAttempts: int
    overlayDismissedCount: int
    carouselExplorationEnabled: bool
    carouselStepsExecuted: int
    sequenceLengthBeforeExploration: int
    sequenceLengthAfterExploration: int
    sequenceStableRounds: int
    autonomousStopReason: str
    blockedByOverlaySuspected: bool
    manualInteractionExpected: bool
    notes: list[str]


class ChapterCaptureResponse(BaseModel):
    sourceUrl: str
    captureDurationSeconds: int
    imageCount: int
    images: list[ChapterCaptureImage]
    diagnostics: ChapterCaptureDiagnostics


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


class NetworkInspectResponse(BaseModel):
    url: str
    finalUrl: str
    statusCode: int
    isRedirect: bool
    redirectLocation: str | None
    contentType: str | None
    server: str | None
    bodyPreview: str
