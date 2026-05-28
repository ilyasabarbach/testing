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
    stopPolicy: Literal["sequence_stable", "duration", "smart"] | None = None


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
    captureStopPolicy: Literal["sequence_stable", "duration", "smart"]
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
    numericOrderingApplied: bool
    duplicatePageNumberCount: int
    missingPageNumbers: list[int]
    selectedPageNumbers: list[int]
    orderingStrategy: str
    readerReadinessEnabled: bool
    overlayDismissEnabled: bool
    overlayDismissAttempts: int
    overlayDismissedCount: int
    carouselExplorationEnabled: bool
    carouselStepsExecuted: int
    sequenceLengthBeforeExploration: int
    sequenceLengthAfterExploration: int
    sequenceStableRounds: int
    smartStopEnabled: bool
    smartStopMinSteps: int
    smartStopStableRounds: int
    smartStopMinSequenceLength: int
    smartStopTriggered: bool
    smartStopReason: str
    readerBoundarySuspected: bool
    readerBoundaryMinSequenceLength: int
    readerBoundaryRecentGrowthWindow: int
    readerBoundaryStableRoundsRequired: int
    readerBoundaryBlockedBecauseSequenceTooSmall: bool
    readerBoundaryBlockedBecauseRecentGrowth: bool
    readerBoundaryBlockedBecauseNotStableEnough: bool
    lastSequenceGrowthStep: int
    largeSequenceModeEnabled: bool
    largeSequenceModeTriggered: bool
    largeSequenceMinLength: int
    largeSequenceMaxSteps: int
    largeSequenceStepsExecuted: int
    largeSequenceStopReason: str
    sustainedArrowDownEnabled: bool
    sustainedArrowDownRoundsExecuted: int
    sustainedArrowDownPressesSent: int
    sustainedArrowDownSequenceBefore: int
    sustainedArrowDownSequenceAfter: int
    sustainedArrowDownGrowthEvents: int
    sustainedArrowDownStableRounds: int
    sustainedArrowDownStopReason: str
    sustainedArrowDownProductive: bool
    readerNavigationStrategy: Literal["generic", "right_arrow_only"]
    rightArrowNavigationEnabled: bool
    rightArrowStepsExecuted: int
    rightArrowPressesSent: int
    rightArrowSequenceBefore: int
    rightArrowSequenceAfter: int
    rightArrowGrowthEvents: int
    rightArrowStableRounds: int
    rightArrowStopReason: str
    rightArrowProductive: bool
    rightArrowUrlChanged: bool
    rightArrowInitialUrl: str
    rightArrowFinalUrl: str
    forbiddenNavigationKeysUsed: bool
    productiveActions: list[str]
    lastProductiveAction: str
    sequenceGrowthEvents: int
    sequenceLengthAtNormalStepLimit: int
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


class ChapterBatchRequest(BaseModel):
    urls: list[str]
    analysisMode: Literal[
        "static_preview",
        "browser_preview",
        "autonomous_capture",
    ] = "autonomous_capture"
    durationSeconds: int | None = None
    stopPolicy: Literal["sequence_stable", "duration", "smart"] | None = None


class ChapterBatchCreateResponse(BaseModel):
    jobId: str
    status: Literal["queued", "running", "completed", "completed_with_errors", "failed"]
    totalUrls: int
    completedUrls: int
    failedUrls: int
    createdAt: str
    statusUrl: str


class ChapterBatchItemStatus(BaseModel):
    index: int
    url: str
    status: Literal["pending", "running", "success", "failed"]
    imageCount: int
    startedAt: str | None
    finishedAt: str | None
    durationMs: int | None
    error: str | None
    result: dict | None


class ChapterBatchStatusResponse(BaseModel):
    jobId: str
    status: Literal["queued", "running", "completed", "completed_with_errors", "failed"]
    analysisMode: Literal[
        "static_preview",
        "browser_preview",
        "autonomous_capture",
    ]
    totalUrls: int
    completedUrls: int
    failedUrls: int
    createdAt: str
    startedAt: str | None
    finishedAt: str | None
    durationMs: int | None
    items: list[ChapterBatchItemStatus]
    reportPath: str


class ChapterBatchDownloadItemResponse(BaseModel):
    index: int
    url: str
    folder: str
    imageCount: int
    downloadedImages: int
    failedImages: int
    error: str | None


class ChapterBatchDownloadResponse(BaseModel):
    jobId: str
    status: Literal["completed", "completed_with_errors"]
    downloadBaseDirectory: str
    successfulItems: int
    failedItems: int
    totalImages: int
    downloadedImages: int
    failedImages: int
    items: list[ChapterBatchDownloadItemResponse]
    reportPath: str


class RuntimeConfigResponse(BaseModel):
    urlAccessMode: str
    browserHeadless: bool
    browserPersistentContextEnabled: bool
    browserUserDataDirConfigured: bool
    browserCaptureMaxSeconds: int
    browserAutonomousMaxSteps: int
    browserAutonomousStepWaitMs: int
    browserSmartStopMinSteps: int
    browserSmartStopStableRounds: int
    browserLargeSequenceModeEnabled: bool
    browserLargeSequenceMinLength: int
    browserLargeSequenceMaxSteps: int
    browserLargeSequenceStepWaitMs: int
    browserLargeSequenceExtendWhileGrowing: bool
    browserLargeSequenceStableRounds: int
    batchMaxUrls: int
    batchReportBaseDir: str
    batchDownloadBaseDir: str


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
