# Chapter Preview API

Professional backend for generic web chapter image extraction and download automation workflow.

Current scope covers preview only:
- receive chapter page URL
- fetch HTML
- extract `<img src>` URLs in page order
- resolve relative image URLs
- return structured JSON preview
- sequentially download extracted images into ordered local files

## Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run backend

```bash
uvicorn app.main:app --reload
```

Server starts on `http://127.0.0.1:8000`.

Open UI in browser:

```text
http://127.0.0.1:8000/
```

## Configuration

Configuration is environment-variable based and beginner-friendly.

```bash
URL_ACCESS_MODE=local_only
ALLOWED_HOSTS=localhost,127.0.0.1
HTTP_TIMEOUT_SECONDS=10
DEFAULT_IMAGE_EXTENSION=.jpg
DOWNLOAD_BASE_DIR=downloads
```

### URL access modes

#### `local_only` (default)

Allows only `localhost` and `127.0.0.1`.

Why default:
- safest starting point against SSRF-style server-side fetching risks
- good for local testing with localhost chapter pages
- predictable for beginner setup

#### `allowlist`

Allows only hosts explicitly listed in `ALLOWED_HOSTS`.

Enterprise use:
- internal approved content domains can be listed centrally
- security team can restrict fetches to trusted environments
- useful for staging, QA, or partner-hosted content pipelines

Example:

```bash
set URL_ACCESS_MODE=allowlist
set ALLOWED_HOSTS=content.example.com,cdn.example.com
```

#### `open`

Allows any valid `http` or `https` URL.

Warning:
- `open` mode is unsafe if backend is exposed publicly
- use only in controlled environments, internal labs, or tightly protected automation setups
- unsupported schemes such as `file://`, `ftp://`, `javascript:`, and `data:` are still rejected

## Run tests

```bash
python -m pytest -q
```

## API

The web UI uses existing API endpoints. No separate frontend server is required.

### Endpoint

`POST /api/chapters/preview`

### Request body

```json
{
  "url": "http://localhost:3001/chapter-1.html"
}
```

### Successful response shape

```json
{
  "sourceUrl": "http://localhost:3001/chapter-1.html",
  "imageCount": 3,
  "images": [
    {
      "index": 1,
      "url": "http://localhost:3001/images/page-001.jpg",
      "filename": "001.jpg"
    }
  ]
}
```

### Download endpoint

`POST /api/chapters/download`

This endpoint:
- validates chapter URL with current URL access policy
- fetches chapter page
- extracts image URLs in order
- downloads images sequentially, one by one
- saves files under `DOWNLOAD_BASE_DIR/<unique-run-id>/`
- writes persistent `report.json` into that run directory
- continues even if one image fails

### Download response shape

```json
{
  "runId": "20260522-143012-a1b2c3",
  "sourceUrl": "http://localhost:3001/chapter-1.html",
  "imageCount": 3,
  "downloadDirectory": "downloads/20260522-143012-a1b2c3",
  "startedAt": "2026-05-22T14:30:12.123456+00:00",
  "finishedAt": "2026-05-22T14:30:12.456789+00:00",
  "durationMs": 333,
  "successCount": 3,
  "failedCount": 0,
  "images": [
    {
      "index": 1,
      "url": "http://localhost:3001/images/page-001.jpg",
      "filename": "001.jpg",
      "status": "downloaded",
      "path": "downloads/20260522-143012-a1b2c3/001.jpg",
      "error": null
    }
  ]
}
```

### Download behavior

- files are saved in DOM order as `001.jpg`, `002.jpg`, `003.jpg`
- downloads are sequential, not parallel
- partial failures do not abort whole run
- failed images return `status: "failed"` and keep clear error message
- chapter with zero images returns empty image list and creates no image files
- each run persists `report.json` for later QA review, debugging, and project demo
- response includes run metadata: `runId`, `startedAt`, `finishedAt`, `durationMs`, `successCount`, `failedCount`

### Persistent report

Each download run creates:

```text
downloads/<run-id>/
  001.jpg
  002.jpg
  report.json
```

`report.json` stores same core data returned by API plus execution metadata. This gives durable artifact for:
- QA automation evidence
- debugging failed runs later
- PFE demo screenshots and audit trail

## Web UI

Root page `GET /` serves lightweight professional interface for:
- entering chapter URL
- previewing ordered image list
- triggering ordered download
- inspecting download execution report
- viewing API errors clearly

Preview flow:
- enter URL
- click `Preview`
- UI calls `POST /api/chapters/preview`
- UI shows `sourceUrl`, `imageCount`, ordered images, and generated filenames

Download flow:
- enter URL
- click `Download`
- UI calls `POST /api/chapters/download`
- UI shows run metadata, download directory, success/failure counts, and per-image results

Loading states:
- `Previewing...`
- `Downloading...`

## Example curl commands

Local testing:

```bash
curl -X POST "http://127.0.0.1:8000/api/chapters/preview" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"http://localhost:3001/chapter-1.html\"}"
```

Allowlist mode example:

```bash
set URL_ACCESS_MODE=allowlist
set ALLOWED_HOSTS=example.com
curl -X POST "http://127.0.0.1:8000/api/chapters/preview" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://example.com/chapter-1.html\"}"
```

Open mode example:

```bash
set URL_ACCESS_MODE=open
curl -X POST "http://127.0.0.1:8000/api/chapters/preview" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://example.com/chapter-1.html\"}"
```

Download example:

```bash
curl -X POST "http://127.0.0.1:8000/api/chapters/download" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"http://localhost:3001/chapter-1.html\"}"
```
