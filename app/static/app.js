const urlInput = document.getElementById("chapter-url");
const followRedirectsInput = document.getElementById("follow-redirects");
const previewButton = document.getElementById("preview-button");
const inspectButton = document.getElementById("inspect-button");
const downloadButton = document.getElementById("download-button");

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
}

function buildSummaryItem(label, value) {
  return `
    <article class="summary-item">
      <span class="summary-label">${label}</span>
      <span class="summary-value">${value ?? ""}</span>
    </article>
  `;
}

function renderNotes(notes) {
  if (!notes || notes.length === 0) {
    return "";
  }

  return `
    <ul class="note-list">
      ${notes.map((note) => `<li>${note}</li>`).join("")}
    </ul>
  `;
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
        <td>${image.url}</td>
        <td>${image.filename}</td>
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
    buildSummaryItem("Looks Dynamic", diagnostics.looksDynamic ? "Yes" : "No"),
    buildSummaryItem("App Root Shell", diagnostics.hasAppRootShell ? "Yes" : "No"),
    buildSummaryItem(
      "API-Driven Signals",
      diagnostics.possibleApiDrivenPage ? "Yes" : "No",
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
    ["Has App Root Shell", diagnostics.hasAppRootShell ? "Yes" : "No"],
    [
      "Possible API-Driven Page",
      diagnostics.possibleApiDrivenPage ? "Yes" : "No",
    ],
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
    buildSummaryItem("Redirect", data.isRedirect ? "Yes" : "No"),
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
        <td>${value}</td>
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
        <td>${image.url}</td>
        <td>${image.filename}</td>
        <td>${image.status}</td>
        <td>${image.path ?? ""}</td>
        <td>${image.error ?? ""}</td>
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
