const POLL_INTERVAL_MS = 3000;

const urlInput = document.getElementById("chapter-url");
const followRedirectsInput = document.getElementById("follow-redirects");
const previewButton = document.getElementById("preview-button");
const inspectButton = document.getElementById("inspect-button");
const downloadButton = document.getElementById("download-button");

const batchUrlsInput = document.getElementById("batch-urls");
const batchAnalysisModeInput = document.getElementById("batch-analysis-mode");
const batchDurationSecondsInput = document.getElementById("batch-duration-seconds");
const batchStopPolicyInput = document.getElementById("batch-stop-policy");
const batchDemoPresetButton = document.getElementById("batch-demo-preset-button");
const batchRunButton = document.getElementById("batch-run-button");
const batchDownloadButton = document.getElementById("batch-download-button");

const errorPanel = document.getElementById("error-panel");
const errorMessage = document.getElementById("error-message");

const inspectPanel = document.getElementById("inspect-panel");
const inspectLoading = document.getElementById("inspect-loading");
const inspectSummary = document.getElementById("inspect-summary");
const inspectDetailsBody = document.getElementById("inspect-details-body");

const previewPanel = document.getElementById("preview-panel");
const previewLoading = document.getElementById("preview-loading");
const previewSummary = document.getElementById("preview-summary");
const previewDiagnostics = document.getElementById("preview-diagnostics");
const previewDiagnosticsSummary = document.getElementById("preview-diagnostics-summary");
const previewDiagnosticsBody = document.getElementById("preview-diagnostics-body");
const previewTableBody = document.getElementById("preview-table-body");

const downloadPanel = document.getElementById("download-panel");
const downloadLoading = document.getElementById("download-loading");
const downloadSummary = document.getElementById("download-summary");
const downloadTableBody = document.getElementById("download-table-body");

const batchStatusPanel = document.getElementById("batch-status-panel");
const batchLoading = document.getElementById("batch-loading");
const batchSummary = document.getElementById("batch-summary");
const batchCurrentItem = document.getElementById("batch-current-item");
const batchItemsBody = document.getElementById("batch-items-body");

const batchDownloadPanel = document.getElementById("batch-download-panel");
const batchDownloadLoading = document.getElementById("batch-download-loading");
const batchDownloadSummary = document.getElementById("batch-download-summary");
const batchDownloadTableWrap = document.getElementById("batch-download-table-wrap");
const batchDownloadItemsBody = document.getElementById("batch-download-items-body");

const runtimeConfigPanel = document.getElementById("runtime-config-panel");
const runtimeConfigBadge = document.getElementById("runtime-config-badge");
const runtimeConfigSummary = document.getElementById("runtime-config-summary");
const runtimeConfigDetails = document.getElementById("runtime-config-details");

const batchDetailsPanel = document.getElementById("batch-details-panel");
const batchDetailsTitle = document.getElementById("batch-details-title");
const batchDetailsSummary = document.getElementById("batch-details-summary");
const batchDetailsNotes = document.getElementById("batch-details-notes");
const batchDetailsNotesBody = document.getElementById("batch-details-notes-body");
const batchDetailsImagesBody = document.getElementById("batch-details-images-body");

const state = {
  batchJobId: null,
  batchStatusUrl: null,
  batchPollingTimer: null,
  batchIsRunning: false,
  batchDownloadIsRunning: false,
  selectedBatchItemIndex: null,
  batchJob: null,
  runtimeConfig: null,
};

function showError(message) {
  errorPanel.classList.remove("hidden");
  errorMessage.textContent = message;
}

function clearError() {
  errorPanel.classList.add("hidden");
  errorMessage.textContent = "";
}

function readUrlOrShowError() {
  const url = urlInput.value.trim();
  clearError();

  if (!url) {
    showError("Please enter a chapter URL before continuing.");
    return null;
  }

  return url;
}

function readBatchUrlsOrShowError() {
  clearError();
  const urls = batchUrlsInput.value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (urls.length === 0) {
    showError("Please enter at least one batch URL before continuing.");
    return null;
  }

  return urls;
}

function setLoading(target, isLoading) {
  if (target === "preview") {
    previewLoading.classList.toggle("hidden", !isLoading);
    previewButton.disabled = isLoading;
  }

  if (target === "inspect") {
    inspectLoading.classList.toggle("hidden", !isLoading);
    inspectButton.disabled = isLoading;
  }

  if (target === "download") {
    downloadLoading.classList.toggle("hidden", !isLoading);
    downloadButton.disabled = isLoading;
  }

  if (target === "batch") {
    batchLoading.classList.toggle("hidden", !isLoading);
    batchRunButton.disabled = isLoading;
    state.batchIsRunning = isLoading;
    updateBatchDownloadControls(state.batchJob);
  }

  if (target === "batch-download") {
    batchDownloadLoading.classList.toggle("hidden", !isLoading);
    state.batchDownloadIsRunning = isLoading;
    updateBatchDownloadControls(state.batchJob);
  }
}

function buildSummaryItem(label, value) {
  return `
    <article class="summary-item">
      <span class="summary-label">${label}</span>
      <span class="summary-value">${value ?? ""}</span>
    </article>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

function renderNotes(notes) {
  if (!notes || notes.length === 0) {
    return "";
  }

  return `
    <ul class="note-list">
      ${notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
    </ul>
  `;
}

function formatBoolean(value) {
  return value ? "Yes" : "No";
}

function formatDuration(milliseconds) {
  if (milliseconds === null || milliseconds === undefined) {
    return "";
  }
  return `${milliseconds} ms`;
}

function getBatchDurationDefault(mode) {
  return mode === "autonomous_capture" ? "900" : "120";
}

function getBatchStopPolicyDefault(mode) {
  return mode === "autonomous_capture" ? "smart" : "duration";
}

function hasDownloadableBatchItems(job) {
  return Boolean(
    job &&
      Array.isArray(job.items) &&
      job.items.some(
        (item) =>
          item.status === "success" &&
          Number(item.imageCount ?? item.result?.imageCount ?? 0) > 0,
      ),
  );
}

function buildStatusBadge(status) {
  const normalized = String(status || "unknown");
  return `<span class="badge badge-${normalized}">${escapeHtml(normalized)}</span>`;
}

function isDemoReady(config) {
  return Boolean(
    config &&
      config.browserPersistentContextEnabled === true &&
      config.browserLargeSequenceModeEnabled === true &&
      Number(config.browserCaptureMaxSeconds ?? 0) >= 900 &&
      Number(config.browserLargeSequenceMaxSteps ?? 0) >= 2000 &&
      Boolean(config.batchDownloadBaseDir),
  );
}

function renderRuntimeConfig(config) {
  runtimeConfigPanel.classList.remove("hidden");
  state.runtimeConfig = config;
  const demoReady = isDemoReady(config);
  runtimeConfigBadge.className = `badge ${demoReady ? "badge-completed" : "badge-completed_with_errors"}`;
  runtimeConfigBadge.textContent = demoReady ? "Demo Ready" : "Demo Config Incomplete";

  runtimeConfigSummary.innerHTML = [
    buildSummaryItem("Persistent Profile", formatBoolean(config.browserPersistentContextEnabled)),
    buildSummaryItem("Large Sequence Mode", formatBoolean(config.browserLargeSequenceModeEnabled)),
    buildSummaryItem("Capture Max Seconds", config.browserCaptureMaxSeconds),
    buildSummaryItem("Autonomous Max Steps", config.browserAutonomousMaxSteps),
    buildSummaryItem("Large Sequence Max Steps", config.browserLargeSequenceMaxSteps),
    buildSummaryItem("Large Sequence Step Wait", `${config.browserLargeSequenceStepWaitMs} ms`),
    buildSummaryItem("Batch Download Directory", config.batchDownloadBaseDir),
  ].join("");

  runtimeConfigDetails.innerHTML = [
    buildSummaryItem("URL Access Mode", config.urlAccessMode),
    buildSummaryItem("Browser Headless", formatBoolean(config.browserHeadless)),
    buildSummaryItem("User Data Dir Configured", formatBoolean(config.browserUserDataDirConfigured)),
    buildSummaryItem("Smart Stop Min Steps", config.browserSmartStopMinSteps),
    buildSummaryItem("Smart Stop Stable Rounds", config.browserSmartStopStableRounds),
    buildSummaryItem("Large Sequence Min Length", config.browserLargeSequenceMinLength),
    buildSummaryItem(
      "Large Sequence Extend While Growing",
      formatBoolean(config.browserLargeSequenceExtendWhileGrowing),
    ),
    buildSummaryItem("Large Sequence Stable Rounds", config.browserLargeSequenceStableRounds),
    buildSummaryItem("Batch Max URLs", config.batchMaxUrls),
    buildSummaryItem("Batch Report Directory", config.batchReportBaseDir),
  ].join("");
}

function renderPreview(data) {
  previewPanel.classList.remove("hidden");
  previewSummary.innerHTML = [
    buildSummaryItem("Source URL", data.sourceUrl),
    buildSummaryItem("Image Count", data.imageCount),
  ].join("");

  renderPreviewDiagnostics(data.diagnostics);

  previewTableBody.innerHTML = data.images
    .map((image) => `
      <tr>
        <td>${image.index}</td>
        <td>${escapeHtml(image.url)}</td>
        <td>${escapeHtml(image.filename)}</td>
      </tr>
    `)
    .join("");
}

function renderPreviewDiagnostics(diagnostics) {
  if (!diagnostics) {
    previewDiagnostics.classList.add("hidden");
    return;
  }

  previewDiagnostics.classList.remove("hidden");
  previewDiagnosticsSummary.innerHTML = [
    buildSummaryItem("HTML Length", diagnostics.htmlLength),
    buildSummaryItem("IMG Tag Count", diagnostics.imgTagCount),
    buildSummaryItem("Looks Dynamic", formatBoolean(diagnostics.looksDynamic)),
    buildSummaryItem("App Root Shell", formatBoolean(diagnostics.hasAppRootShell)),
    buildSummaryItem(
      "API-Driven Signals",
      formatBoolean(diagnostics.possibleApiDrivenPage),
    ),
    buildSummaryItem("Deduplicated", diagnostics.deduplicatedCount),
  ].join("");

  const details = [
    ["Images From src", diagnostics.imagesFromSrc],
    ["Images From data-src", diagnostics.imagesFromDataSrc],
    ["Images From data-lazy-src", diagnostics.imagesFromDataLazySrc],
    ["Images From data-original", diagnostics.imagesFromDataOriginal],
    ["Images From data-url", diagnostics.imagesFromDataUrl],
    ["Images From srcset", diagnostics.imagesFromSrcset],
    ["Images From source srcset", diagnostics.imagesFromSourceSrcset],
    ["Images From meta", diagnostics.imagesFromMeta],
    ["JSON Script Count", diagnostics.jsonScriptCount],
    ["Embedded JSON Image URL Count", diagnostics.embeddedImageUrlCount],
    ["Images From Embedded JSON", diagnostics.imagesFromEmbeddedJson],
    ["Has App Root Shell", formatBoolean(diagnostics.hasAppRootShell)],
    ["Possible API-Driven Page", formatBoolean(diagnostics.possibleApiDrivenPage)],
    ["Notes", renderNotes(diagnostics.notes ?? [])],
  ];

  previewDiagnosticsBody.innerHTML = details
    .map(([label, value]) => `
      <tr>
        <th>${label}</th>
        <td>${value ?? ""}</td>
      </tr>
    `)
    .join("");
}

function renderInspectReport(data) {
  inspectPanel.classList.remove("hidden");
  inspectSummary.innerHTML = [
    buildSummaryItem("Original URL", data.url),
    buildSummaryItem("Final URL", data.finalUrl),
    buildSummaryItem("Status Code", data.statusCode),
    buildSummaryItem("Redirect", formatBoolean(data.isRedirect)),
  ].join("");

  const details = [
    ["Redirect Location", data.redirectLocation ?? ""],
    ["Content Type", data.contentType ?? ""],
    ["Server", data.server ?? ""],
    ["Body Preview", data.bodyPreview ?? ""],
  ];

  inspectDetailsBody.innerHTML = details
    .map(([label, value]) => `
      <tr>
        <th>${label}</th>
        <td>${escapeHtml(value)}</td>
      </tr>
    `)
    .join("");
}

function renderDownloadReport(data) {
  downloadPanel.classList.remove("hidden");
  downloadSummary.innerHTML = [
    buildSummaryItem("Run ID", data.runId),
    buildSummaryItem("Source URL", data.sourceUrl),
    buildSummaryItem("Image Count", data.imageCount),
    buildSummaryItem("Download Directory", data.downloadDirectory),
    buildSummaryItem("Started At", data.startedAt),
    buildSummaryItem("Finished At", data.finishedAt),
    buildSummaryItem("Duration (ms)", data.durationMs),
    buildSummaryItem("Success Count", data.successCount),
    buildSummaryItem("Failed Count", data.failedCount),
  ].join("");

  downloadTableBody.innerHTML = data.images
    .map((image) => `
      <tr>
        <td>${image.index}</td>
        <td>${escapeHtml(image.url)}</td>
        <td>${escapeHtml(image.filename)}</td>
        <td>${escapeHtml(image.status)}</td>
        <td>${escapeHtml(image.path ?? "")}</td>
        <td>${escapeHtml(image.error ?? "")}</td>
      </tr>
    `)
    .join("");
}

function renderBatchStatus(job) {
  batchStatusPanel.classList.remove("hidden");
  batchDownloadPanel.classList.remove("hidden");
  state.batchJob = job;

  const runningItem = (job.items || []).find((item) => item.status === "running");
  batchSummary.innerHTML = [
    buildSummaryItem("Job ID", job.jobId),
    buildSummaryItem("Status", buildStatusBadge(job.status)),
    buildSummaryItem("Analysis Mode", job.analysisMode),
    buildSummaryItem("Total URLs", job.totalUrls),
    buildSummaryItem("Completed URLs", job.completedUrls),
    buildSummaryItem("Failed URLs", job.failedUrls),
    buildSummaryItem("Duration", formatDuration(job.durationMs)),
    buildSummaryItem("Report Path", job.reportPath),
  ].join("");

  if (runningItem) {
    batchCurrentItem.classList.remove("hidden");
    batchCurrentItem.textContent = `Running item ${runningItem.index}: ${runningItem.url}`;
  } else {
    batchCurrentItem.classList.add("hidden");
    batchCurrentItem.textContent = "";
  }

  renderBatchItems(job);
  renderBatchDetails(job, state.selectedBatchItemIndex);
  updateBatchDownloadControls(job);
}

function renderBatchItems(job) {
  const items = job.items || [];
  if (items.length > 0 && !items.some((item) => item.index === state.selectedBatchItemIndex)) {
    state.selectedBatchItemIndex = items[0].index;
  }

  batchItemsBody.innerHTML = items
    .map((item) => {
      const diagnostics = item.result?.diagnostics || {};
      const isSelected = item.index === state.selectedBatchItemIndex;
      return `
        <tr class="batch-item-row ${isSelected ? "batch-item-row-selected" : ""}" data-item-index="${item.index}">
          <td>${item.index}</td>
          <td>${escapeHtml(item.url)}</td>
          <td>${buildStatusBadge(item.status)}</td>
          <td>${item.imageCount ?? 0}</td>
          <td>${escapeHtml(formatDuration(item.durationMs))}</td>
          <td>${diagnostics.selectedImageCount ?? ""}</td>
          <td>${diagnostics.dominantSequenceLength ?? ""}</td>
          <td>${diagnostics.numericOrderingApplied ?? ""}</td>
          <td>${escapeHtml(diagnostics.orderingStrategy ?? "")}</td>
          <td>${escapeHtml(item.error ?? "")}</td>
          <td>
            <button
              type="button"
              class="inline-button batch-item-download-button"
              data-item-download-index="${item.index}"
              ${canDownloadItem(job, item) ? "" : "disabled"}
            >
              Download Item
            </button>
          </td>
        </tr>
      `;
    })
    .join("");

  document.querySelectorAll(".batch-item-row").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedBatchItemIndex = Number(row.dataset.itemIndex);
      renderBatchItems(job);
      renderBatchDetails(job, state.selectedBatchItemIndex);
    });
  });

  document.querySelectorAll(".batch-item-download-button").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const itemIndex = Number(button.dataset.itemDownloadIndex);
      await runBatchItemDownload(job.jobId, itemIndex);
    });
  });
}

function renderBatchDetails(job, itemIndex) {
  const item = (job.items || []).find((entry) => entry.index === itemIndex);
  if (!item) {
    batchDetailsPanel.classList.add("hidden");
    return;
  }

  batchDetailsPanel.classList.remove("hidden");
  const diagnostics = item.result?.diagnostics || {};
  const images = item.result?.images || [];
  batchDetailsTitle.textContent = `${item.url}`;

  batchDetailsSummary.innerHTML = [
    buildSummaryItem("Item Status", buildStatusBadge(item.status)),
    buildSummaryItem("Image Count", item.imageCount ?? 0),
    buildSummaryItem("Selected Image Count", diagnostics.selectedImageCount ?? ""),
    buildSummaryItem("Dominant Sequence Length", diagnostics.dominantSequenceLength ?? ""),
    buildSummaryItem("Numeric Ordering Applied", diagnostics.numericOrderingApplied ?? ""),
    buildSummaryItem("Ordering Strategy", diagnostics.orderingStrategy ?? ""),
    buildSummaryItem(
      "Action Count",
      Array.isArray(diagnostics.autonomousActionsUsed)
        ? diagnostics.autonomousActionsUsed.length
        : "",
    ),
    buildSummaryItem("Manual Interaction Expected", diagnostics.manualInteractionExpected ?? ""),
  ].join("");

  if (Array.isArray(diagnostics.notes) && diagnostics.notes.length > 0) {
    batchDetailsNotes.classList.remove("hidden");
    batchDetailsNotesBody.innerHTML = renderNotes(diagnostics.notes);
  } else {
    batchDetailsNotes.classList.add("hidden");
    batchDetailsNotesBody.innerHTML = "";
  }

  batchDetailsImagesBody.innerHTML = images
    .map((image) => `
      <tr>
        <td>${image.index}</td>
        <td>${escapeHtml(image.url)}</td>
        <td>${escapeHtml(image.filename)}</td>
        <td>${escapeHtml(image.source ?? "")}</td>
      </tr>
    `)
    .join("");
}

function canDownloadItem(job, item) {
  return (
    Boolean(job) &&
    isBatchTerminal(job.status) &&
    !state.batchDownloadIsRunning &&
    item.status === "success" &&
    Number(item.imageCount ?? item.result?.imageCount ?? 0) > 0
  );
}

function updateBatchDownloadControls(job) {
  if (!batchDownloadButton) {
    return;
  }

  const hasDownloadableItems = hasDownloadableBatchItems(job);
  const ready =
    Boolean(job) &&
    isBatchTerminal(job.status) &&
    hasDownloadableItems &&
    !state.batchIsRunning &&
    !state.batchDownloadIsRunning;

  batchDownloadButton.disabled = !ready;
  batchDownloadButton.textContent = state.batchDownloadIsRunning
    ? "Downloading..."
    : "Download All Detected Images";
}

function renderBatchDownloadReport(data) {
  batchDownloadPanel.classList.remove("hidden");
  batchDownloadSummary.classList.remove("hidden");
  batchDownloadTableWrap.classList.remove("hidden");

  batchDownloadSummary.innerHTML = [
    buildSummaryItem("Status", buildStatusBadge(data.status)),
    buildSummaryItem("Download Base Directory", data.downloadBaseDirectory),
    buildSummaryItem("Successful Items", data.successfulItems),
    buildSummaryItem("Failed Items", data.failedItems),
    buildSummaryItem("Total Images", data.totalImages),
    buildSummaryItem("Downloaded Images", data.downloadedImages),
    buildSummaryItem("Failed Images", data.failedImages),
    buildSummaryItem("Report Path", data.reportPath),
  ].join("");

  batchDownloadItemsBody.innerHTML = (data.items || [])
    .map((item) => `
      <tr>
        <td>${item.index ?? ""}</td>
        <td>${escapeHtml(item.url ?? "")}</td>
        <td>${escapeHtml(item.folder ?? "")}</td>
        <td>${item.imageCount ?? ""}</td>
        <td>${item.downloadedImages ?? ""}</td>
        <td>${item.failedImages ?? ""}</td>
        <td>${escapeHtml(item.error ?? "")}</td>
      </tr>
    `)
    .join("");
}

async function callJsonApi(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail ?? "Unexpected error.";
    throw new Error(`Error ${response.status}: ${detail}`);
  }

  return data;
}

async function fetchJson(path) {
  const response = await fetch(path);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail ?? "Unexpected error.";
    throw new Error(`Error ${response.status}: ${detail}`);
  }
  return data;
}

async function loadRuntimeConfig() {
  try {
    const config = await fetchJson("/api/runtime/config");
    renderRuntimeConfig(config);
  } catch (error) {
    showError(`Runtime config load failed. ${error.message}`);
  }
}

function stopBatchPolling() {
  if (state.batchPollingTimer) {
    clearTimeout(state.batchPollingTimer);
    state.batchPollingTimer = null;
  }
  setLoading("batch", false);
}

function scheduleBatchPoll() {
  stopBatchPolling();
  setLoading("batch", true);
  state.batchPollingTimer = window.setTimeout(async () => {
    await pollBatchJob();
  }, POLL_INTERVAL_MS);
}

function isBatchTerminal(status) {
  return ["completed", "completed_with_errors", "failed"].includes(status);
}

async function pollBatchJob() {
  if (!state.batchJobId && !state.batchStatusUrl) {
    return;
  }

  const fallbackStatusUrl = `/api/chapters/batch/${state.batchJobId}`;
  const statusUrl = state.batchStatusUrl || fallbackStatusUrl;

  try {
    const job = await fetchJson(statusUrl);
    renderBatchStatus(job);
    if (isBatchTerminal(job.status)) {
      stopBatchPolling();
      return;
    }
    scheduleBatchPoll();
  } catch (error) {
    stopBatchPolling();
    showError(`Batch polling failed. ${error.message}`);
  }
}

async function runBatchJob() {
  const urls = readBatchUrlsOrShowError();
  if (!urls || state.batchIsRunning) {
    return;
  }

  batchStatusPanel.classList.remove("hidden");
  batchDownloadPanel.classList.remove("hidden");
  batchDownloadSummary.classList.add("hidden");
  batchDownloadTableWrap.classList.add("hidden");
  batchDownloadItemsBody.innerHTML = "";
  batchDownloadSummary.innerHTML = "";
  batchDetailsPanel.classList.add("hidden");
  state.selectedBatchItemIndex = null;
  state.batchJob = null;
  setLoading("batch", true);

  try {
    const payload = {
      urls,
      analysisMode: batchAnalysisModeInput.value,
      durationSeconds: Number(batchDurationSecondsInput.value),
      stopPolicy: batchStopPolicyInput.value,
    };
    const job = await callJsonApi("/api/chapters/batch", payload);
    state.batchJobId = job.jobId;
    state.batchStatusUrl = job.statusUrl || `/api/chapters/batch/${job.jobId}`;
    renderBatchStatus({
      ...job,
      analysisMode: payload.analysisMode,
      durationMs: null,
      reportPath: "",
      items: urls.map((url, index) => ({
        index: index + 1,
        url,
        status: "pending",
        imageCount: 0,
        durationMs: null,
        error: null,
        result: null,
      })),
    });
    scheduleBatchPoll();
  } catch (error) {
    stopBatchPolling();
    showError(error.message);
  }
}

async function runBatchDownload(jobId) {
  if (!jobId || state.batchDownloadIsRunning) {
    return;
  }

  setLoading("batch-download", true);
  try {
    const data = await callJsonApi(`/api/chapters/batch/${jobId}/download`, {});
    renderBatchDownloadReport(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading("batch-download", false);
  }
}

async function runBatchItemDownload(jobId, itemIndex) {
  if (!jobId || !itemIndex || state.batchDownloadIsRunning) {
    return;
  }

  setLoading("batch-download", true);
  try {
    const data = await callJsonApi(
      `/api/chapters/batch/${jobId}/items/${itemIndex}/download`,
      {},
    );
    renderBatchDownloadReport(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading("batch-download", false);
  }
}

function applyManagerDemoPreset() {
  batchAnalysisModeInput.value = "autonomous_capture";
  batchDurationSecondsInput.value = "900";
  batchStopPolicyInput.value = "smart";
}

function syncBatchControlsForMode() {
  const mode = batchAnalysisModeInput.value;
  if (mode === "autonomous_capture") {
    if (!["30", "60", "90", "120", "180", "300", "600", "900"].includes(batchDurationSecondsInput.value)) {
      batchDurationSecondsInput.value = "900";
    }
    if (!["smart", "duration", "sequence_stable"].includes(batchStopPolicyInput.value)) {
      batchStopPolicyInput.value = "smart";
    }
    return;
  }
  batchDurationSecondsInput.value = getBatchDurationDefault(mode);
  batchStopPolicyInput.value = getBatchStopPolicyDefault(mode);
}

previewButton.addEventListener("click", async () => {
  const url = readUrlOrShowError();
  if (!url) {
    return;
  }

  setLoading("preview", true);
  try {
    const data = await callJsonApi("/api/chapters/preview", { url });
    renderPreview(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading("preview", false);
  }
});

inspectButton.addEventListener("click", async () => {
  const url = readUrlOrShowError();
  if (!url) {
    return;
  }

  setLoading("inspect", true);
  try {
    const data = await callJsonApi("/api/network/inspect", {
      url,
      followRedirects: followRedirectsInput.checked,
    });
    renderInspectReport(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading("inspect", false);
  }
});

downloadButton.addEventListener("click", async () => {
  const url = readUrlOrShowError();
  if (!url) {
    return;
  }

  setLoading("download", true);
  try {
    const data = await callJsonApi("/api/chapters/download", { url });
    renderDownloadReport(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading("download", false);
  }
});

batchRunButton.addEventListener("click", async () => {
  await runBatchJob();
});

batchDownloadButton.addEventListener("click", async () => {
  await runBatchDownload(state.batchJobId);
});

batchDemoPresetButton.addEventListener("click", () => {
  applyManagerDemoPreset();
});

batchAnalysisModeInput.addEventListener("change", () => {
  syncBatchControlsForMode();
});

syncBatchControlsForMode();
loadRuntimeConfig();
