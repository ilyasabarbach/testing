const urlInput = document.getElementById("chapter-url");
const previewButton = document.getElementById("preview-button");
const downloadButton = document.getElementById("download-button");

const errorPanel = document.getElementById("error-panel");
const errorMessage = document.getElementById("error-message");

const previewPanel = document.getElementById("preview-panel");
const previewLoading = document.getElementById("preview-loading");
const previewSummary = document.getElementById("preview-summary");
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

function renderPreview(data) {
  previewPanel.classList.remove("hidden");
  previewSummary.innerHTML = [
    buildSummaryItem("Source URL", data.sourceUrl),
    buildSummaryItem("Image Count", data.imageCount),
  ].join("");

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

async function callJsonApi(path, url) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url }),
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
    const data = await callJsonApi("/api/chapters/preview", url);
    renderPreview(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading("preview", false);
  }
});

downloadButton.addEventListener("click", async () => {
  const url = readUrlOrShowError();
  if (!url) {
    return;
  }

  setLoading("download", true);
  try {
    const data = await callJsonApi("/api/chapters/download", url);
    renderDownloadReport(data);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading("download", false);
  }
});
