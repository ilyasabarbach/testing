# Chapter Preview API

Professional backend for generic web chapter image extraction and download automation workflow.

Current scope covers preview only:
- receive chapter page URL
- fetch HTML
- extract image URLs from common static HTML patterns in page order
- resolve relative image URLs
- return structured JSON preview
- sequentially download extracted images into ordered local files
- recover additional image URLs from embedded JSON blocks commonly used by modern app-shell pages

## Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy example environment file if needed:

```bash
copy .env.example .env
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

Configuration is environment-variable based, beginner-friendly, and supports loading from `.env`.

```bash
URL_ACCESS_MODE=local_only
ALLOWED_HOSTS=localhost,127.0.0.1
HTTP_TIMEOUT_SECONDS=10
DEFAULT_IMAGE_EXTENSION=.jpg
DOWNLOAD_BASE_DIR=downloads
HTTP_USER_AGENT=Mozilla/5.0 ChapterDownloaderTool/1.0
SSL_VERIFY_MODE=default
BROWSER_EXECUTABLE_PATH=
PLAYWRIGHT_BROWSER_CHANNEL=
BROWSER_HEADLESS=true
BROWSER_USER_DATA_DIR=
BROWSER_PERSISTENT_CONTEXT_ENABLED=false
BROWSER_SCROLL_ENABLED=true
BROWSER_MAX_SCROLL_STEPS=30
BROWSER_SCROLL_WAIT_MS=500
BROWSER_INITIAL_WAIT_MS=1200
BROWSER_SCROLL_STABLE_ROUNDS=3
BROWSER_MAX_SCROLL_CONTAINERS=5
BROWSER_SCROLL_DELTA_PX=1000
BROWSER_CAPTURE_DEFAULT_SECONDS=30
BROWSER_CAPTURE_MAX_SECONDS=120
BROWSER_CAPTURE_STOP_POLICY=sequence_stable
BROWSER_AUTONOMOUS_CAPTURE_ENABLED=true
BROWSER_AUTONOMOUS_MAX_STEPS=60
BROWSER_AUTONOMOUS_STEP_WAIT_MS=700
BROWSER_AUTONOMOUS_STABLE_ROUNDS=5
BROWSER_AUTONOMOUS_ENABLE_KEYBOARD=true
BROWSER_AUTONOMOUS_ENABLE_MOUSE_WHEEL=true
BROWSER_READER_READINESS_ENABLED=true
BROWSER_OVERLAY_DISMISS_ENABLED=true
BROWSER_OVERLAY_MAX_ATTEMPTS=3
BROWSER_CAROUSEL_EXPLORATION_ENABLED=true
BROWSER_CAROUSEL_MAX_STEPS=80
BROWSER_SEQUENCE_STABLE_ROUNDS=6
```

Project includes [.env.example](C:/Users/ilyas.abarbach/Documents/testing/.env.example:1) with safe defaults.

### Environment variables

- `URL_ACCESS_MODE`: `local_only`, `allowlist`, or `open`
- `ALLOWED_HOSTS`: comma-separated host allowlist for `allowlist` mode
- `HTTP_TIMEOUT_SECONDS`: timeout used for inspect, preview page fetch, and image downloads
- `DOWNLOAD_BASE_DIR`: base directory for saved runs
- `DEFAULT_IMAGE_EXTENSION`: fallback extension when image URL has none
- `HTTP_USER_AGENT`: outgoing `User-Agent` header used for all requests
- `SSL_VERIFY_MODE`: `default`, `truststore`, or `disabled`
- `BROWSER_EXECUTABLE_PATH`: optional full path to existing Chrome/Edge executable for browser preview mode
- `PLAYWRIGHT_BROWSER_CHANNEL`: optional Playwright browser channel like `chrome` or `msedge` when no explicit executable path is set
- `BROWSER_HEADLESS`: run browser preview headless by default; set `false` for visible local debugging
- `BROWSER_USER_DATA_DIR`: optional persistent browser profile directory for cookies/local storage reuse
- `BROWSER_PERSISTENT_CONTEXT_ENABLED`: enable persistent browser context when `true`
- `BROWSER_SCROLL_ENABLED`: enable controlled browser scrolling for lazy-loaded pages
- `BROWSER_MAX_SCROLL_STEPS`: maximum controlled scroll steps in browser mode
- `BROWSER_SCROLL_WAIT_MS`: wait between browser scroll steps
- `BROWSER_INITIAL_WAIT_MS`: initial browser settle wait after first navigation
- `BROWSER_SCROLL_STABLE_ROUNDS`: stop after this many non-growing image-count rounds
- `BROWSER_MAX_SCROLL_CONTAINERS`: maximum internal scrollable containers to probe
- `BROWSER_SCROLL_DELTA_PX`: generic scroll delta used for window and container scrolling
- `BROWSER_CAPTURE_DEFAULT_SECONDS`: default assisted capture duration
- `BROWSER_CAPTURE_MAX_SECONDS`: maximum assisted capture duration
- `BROWSER_CAPTURE_STOP_POLICY`: default capture stop policy, `sequence_stable` or `duration`
- `BROWSER_AUTONOMOUS_CAPTURE_ENABLED`: enable autonomous generic capture strategy
- `BROWSER_AUTONOMOUS_MAX_STEPS`: maximum autonomous exploration actions
- `BROWSER_AUTONOMOUS_STEP_WAIT_MS`: wait after each autonomous action
- `BROWSER_AUTONOMOUS_STABLE_ROUNDS`: stop after image count stops growing for this many rounds
- `BROWSER_AUTONOMOUS_ENABLE_KEYBOARD`: allow generic keyboard actions like PageDown and ArrowRight
- `BROWSER_AUTONOMOUS_ENABLE_MOUSE_WHEEL`: allow generic mouse wheel actions
- `BROWSER_READER_READINESS_ENABLED`: run generic reader readiness checks before autonomous exploration
- `BROWSER_OVERLAY_DISMISS_ENABLED`: allow capped safe overlay dismissal attempts
- `BROWSER_OVERLAY_MAX_ATTEMPTS`: maximum Escape/safe dismiss attempts
- `BROWSER_CAROUSEL_EXPLORATION_ENABLED`: enable carousel-style repeated navigation actions
- `BROWSER_CAROUSEL_MAX_STEPS`: maximum carousel-style exploration steps
- `BROWSER_SEQUENCE_STABLE_ROUNDS`: stop after dominant sequence length stays stable this many rounds

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

### SSL verify modes

#### `default` (default)

Uses normal `httpx` SSL verification. Safe default.

#### `truststore`

Uses operating system certificate store through optional `truststore` package.

Use when:
- Windows or corporate environments have custom/intermediate certificates
- normal Python certificate bundle causes `CERTIFICATE_VERIFY_FAILED`

If package is missing, API returns clean runtime error:
- `SSL truststore mode requires the truststore package.`

#### `disabled`

Passes `verify=False` to outgoing HTTPS requests.

Warning:
- unsafe
- never default
- use only for local diagnostics or temporary troubleshooting
- do not use for public or production-facing deployments

### Example `.env` for local demo

```env
URL_ACCESS_MODE=local_only
ALLOWED_HOSTS=localhost,127.0.0.1
HTTP_TIMEOUT_SECONDS=10
DOWNLOAD_BASE_DIR=downloads
DEFAULT_IMAGE_EXTENSION=.jpg
HTTP_USER_AGENT=Mozilla/5.0 ChapterDownloaderTool/1.0
SSL_VERIFY_MODE=default
BROWSER_EXECUTABLE_PATH=
PLAYWRIGHT_BROWSER_CHANNEL=
```

### Example `.env` for controlled open-mode diagnostics

```env
URL_ACCESS_MODE=open
HTTP_TIMEOUT_SECONDS=10
DOWNLOAD_BASE_DIR=downloads
DEFAULT_IMAGE_EXTENSION=.jpg
HTTP_USER_AGENT=Mozilla/5.0 ChapterDownloaderTool/1.0
SSL_VERIFY_MODE=truststore
BROWSER_EXECUTABLE_PATH=
PLAYWRIGHT_BROWSER_CHANNEL=msedge
```

### Windows HTTPS troubleshooting

If this environment shows:

```text
SSL: CERTIFICATE_VERIFY_FAILED unable to get local issuer certificate
```

Try:
- inspect target first with `POST /api/network/inspect`
- test `followRedirects=false` to see HTTP `301` to HTTPS behavior
- switch `SSL_VERIFY_MODE=truststore` if machine trust store has needed certificates
- install optional `truststore` package if using truststore mode
- use `SSL_VERIFY_MODE=disabled` only for local diagnostics, never as normal setup

### Browser preview setup

Browser preview mode can use either:
- Playwright-installed browser binaries
- an existing system browser executable

For Windows/Uvicorn stability, browser preview is isolated in a separate Python worker process instead of running Playwright directly inside the main API server process.
Browser preview can also scroll the page in controlled steps, probe internal scrollable containers, and wait for image-count stabilization to help trigger lazy-loaded reader images before final DOM extraction.
Browser preview can optionally use persistent browser profile and visible browser window for legitimate local testing and manual session preparation.

Priority rule:
- `BROWSER_EXECUTABLE_PATH` takes priority when configured
- if it is empty, browser preview falls back to normal Playwright browser resolution
- if `PLAYWRIGHT_BROWSER_CHANNEL` is set and no explicit executable path is configured, Playwright can target channels like `chrome` or `msedge`
- if `BROWSER_PERSISTENT_CONTEXT_ENABLED=true` and `BROWSER_USER_DATA_DIR` is set, browser preview reuses persistent profile state like cookies and local storage
- if `BROWSER_HEADLESS=false`, browser preview launches visible browser window for local debugging only

Useful on Windows when Playwright browser downloads fail because of SSL, proxy, or corporate network restrictions.
Playwright package is still required for browser preview mode, and either Playwright-managed browser binaries or a valid system browser executable must be available.
Scrolling improves support for lazy-loaded pages, internal scroll containers, and virtual readers, but does not guarantee every dynamic site will fully render all reader images.
Tool still does not click modals or buttons automatically, log in automatically, or perform site-specific bypass logic.

Common Windows examples:

```text
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\Program Files\Microsoft\Edge\Application\msedge.exe
```

If configured executable path does not exist, API returns clean error:
- `Configured browser executable was not found.`

If persistent mode is enabled without user data directory, API returns clean error:
- `Persistent browser context requires BROWSER_USER_DATA_DIR.`

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
  ],
  "diagnostics": {
    "htmlLength": 12345,
    "imgTagCount": 7,
    "imagesFromSrc": 2,
    "imagesFromDataSrc": 1,
    "imagesFromDataLazySrc": 0,
    "imagesFromDataOriginal": 0,
    "imagesFromDataUrl": 0,
    "imagesFromSrcset": 2,
    "imagesFromSourceSrcset": 1,
    "imagesFromMeta": 1,
    "jsonScriptCount": 1,
    "embeddedImageUrlCount": 2,
    "imagesFromEmbeddedJson": 1,
    "deduplicatedCount": 2,
    "looksDynamic": false,
    "hasAppRootShell": true,
    "possibleApiDrivenPage": false,
    "notes": [
      "Page contains embedded JSON scripts.",
      "Some images were recovered from lazy-load attributes.",
      "Srcset strategy uses the last candidate as the deterministic best image.",
      "Embedded JSON image URLs may be metadata assets rather than chapter pages."
    ]
  }
}
```

### Supported image extraction strategies

Preview supports many common static HTML patterns:
- `img[src]`
- `img[data-src]`
- `img[data-lazy-src]`
- `img[data-original]`
- `img[data-url]`
- `img[srcset]`
- `source[srcset]` inside `picture`
- `meta[property="og:image"]`
- `meta[name="twitter:image"]`
- `script[type="application/json"]`
- `script[type="application/ld+json"]`

Rules:
- relative URLs are resolved against page URL
- duplicate resolved URLs are removed
- order is preserved as much as possible from DOM encounter order
- filenames still use `001.jpg`, `002.jpg`, `003.jpg`
- embedded JSON image discovery is appended after direct HTML discovery, preserving stable order as much as practical

For `srcset`, tool uses deterministic strategy:
- choose last candidate in `srcset`
- this is usually highest-quality candidate in common markup

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
- download automatically benefits from improved preview extraction logic

### Browser capture endpoint

`POST /api/chapters/capture`

Browser capture opens browser through worker process and observes image URLs from DOM and network. It is meant for legitimate local testing on authorized pages where virtual readers, swipers, or modals affect image loading.

Request body:

```json
{
  "url": "https://example.com/chapter-1.html",
  "durationSeconds": 30,
  "captureMode": "assisted",
  "stopPolicy": "sequence_stable"
}
```

Behavior:
- validates URL with same URL policy
- collects image URLs from DOM `img` fields and network image responses
- deduplicates URLs while preserving discovery order
- clamps duration to safe range, default `30`, minimum `5`, maximum from `BROWSER_CAPTURE_MAX_SECONDS`
- does not click buttons, close modals, log in, or use site-specific selectors
- does not bypass anti-bot systems

Capture modes:
- `assisted`: default; visible browser stays open during capture window and user manually interacts with reader
- `autonomous`: worker tries generic safe exploration actions without manual input

Stop policies:
- `sequence_stable`: default; autonomous capture may stop early after detected page sequence stabilizes
- `duration`: autonomous capture stays open until requested duration elapses, useful when virtual readers load slowly or need more time for generic actions

Autonomous actions may include:
- window scroll
- internal scroll container movement
- mouse wheel
- keyboard PageDown, Space, ArrowDown, ArrowRight, End

Reader readiness:
- waits briefly for initial DOM
- may press Escape a capped number of times
- may click only neutral visible dismiss controls such as close, ok, got it, continue, start, start reading, do not show, or ne plus afficher
- never clicks login, sign in, register, pay, subscribe, CAPTCHA, verify, challenge, cookie consent, age verification, form fields, credentials, or payment flows

Autonomous mode tracks dominant reader sequence length. It also tries to prefer dominant numeric reader image sequences like `01.webp` through `16.webp`, while excluding common asset names like logo/icon/avatar/banner when they do not belong to the reader sequence.

Capture ordering:
- when a dominant numeric sequence is detected, selected images are sorted by detected page number, so `01.webp`, `03.webp`, `02.webp` becomes `01.webp`, `02.webp`, `03.webp`
- filenames are regenerated after filtering and ordering, for example `01.webp` becomes `001.webp`
- duplicate URLs for the same detected page number keep the first discovered valid URL
- gaps are reported in diagnostics when practical, but the tool does not invent missing image URLs

Persistent capture profile:
- capture worker respects `BROWSER_HEADLESS`, `BROWSER_PERSISTENT_CONTEXT_ENABLED`, `BROWSER_USER_DATA_DIR`, `BROWSER_EXECUTABLE_PATH`, and `PLAYWRIGHT_BROWSER_CHANNEL`
- when persistent context is enabled with user data dir, cookies/localStorage/session state can be reused across captures
- this can remember legitimate user-prepared reader state, such as dismissed help overlays
- if persistent mode is enabled without user data dir, API returns `Persistent browser context requires BROWSER_USER_DATA_DIR.`

Use capture when browser preview sees only first virtual slides and more images load only after reader interaction. Autonomous mode is generic exploration, not site-specific automation.

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

### Network inspect endpoint

`POST /api/network/inspect`

Use this endpoint for diagnostics before preview or download. It does not download images.

Request body:

```json
{
  "url": "http://example.com",
  "followRedirects": false
}
```

Behavior:
- `followRedirects: false` keeps HTTP 3xx visible and returns `redirectLocation`
- `followRedirects: true` follows redirect chain and returns final reached URL
- useful for diagnosing cases like `http://example.com` returning `301` to `https://example.com/`
- SSL verification failures return clean error message

Example response:

```json
{
  "url": "http://example.com",
  "finalUrl": "http://example.com",
  "statusCode": 301,
  "isRedirect": true,
  "redirectLocation": "https://example.com/",
  "contentType": "text/html; charset=UTF-8",
  "server": "cloudflare",
  "bodyPreview": "Moved permanently"
}
```

## Web UI

Root page `GET /` serves lightweight professional interface for:
- entering chapter URL
- inspecting network behavior
- previewing ordered image list
- triggering ordered download
- inspecting download execution report
- viewing API errors clearly

Inspect flow:
- enter URL
- choose whether redirects should be followed
- click `Inspect Network`
- UI calls `POST /api/network/inspect`
- UI shows status code, final URL, redirect location, headers, and body preview

Preview flow:
- enter URL
- click `Preview`
- UI calls `POST /api/chapters/preview`
- UI shows `sourceUrl`, `imageCount`, ordered images, generated filenames, and preview diagnostics

Download flow:
- enter URL
- click `Download`
- UI calls `POST /api/chapters/download`
- UI shows run metadata, download directory, success/failure counts, and per-image results

Loading states:
- `Previewing...`
- `Downloading...`

### Preview diagnostics

Preview response includes diagnostics block to help explain why images were or were not found.

Important fields:
- `htmlLength`
- `imgTagCount`
- extraction counts by source type
- `jsonScriptCount`
- `embeddedImageUrlCount`
- `imagesFromEmbeddedJson`
- `deduplicatedCount`
- `looksDynamic`
- `hasAppRootShell`
- `possibleApiDrivenPage`
- `notes`

`looksDynamic` is heuristic only. It becomes `true` when page shows signals like:
- many script tags
- very few direct image tags
- framework/root markers such as `app`, `root`, or `__next`

`hasAppRootShell` becomes `true` when raw HTML contains common app-shell markers such as:
- `id="app"`
- `id="root"`
- `id="app-root"`
- `__next`

`possibleApiDrivenPage` becomes `true` when the page looks like an app shell, contains embedded JSON scripts, has script activity, and has very few direct HTML image matches.

Embedded JSON support is useful for pages that return HTTP `200` with app-shell HTML plus initial data blobs instead of plain `<img>` tags. Tool scans:
- `script[type="application/json"]`
- `script[type="application/ld+json"]`

Important warning:
- embedded JSON image URLs may be poster, cover, share, or other metadata assets
- they are not guaranteed to be actual reading-page images

This helps explain cases where page returns HTTP `200` but raw HTML still does not contain directly usable image URLs.

Important limitation:
- tool supports many common static patterns
- tool does not guarantee extraction from every modern dynamic, protected, or JavaScript-rendered site
- tool does not execute browser JavaScript or render app state in a headless browser
- this ticket does not add browser rendering or anti-bot bypass logic

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

Network inspect example:

```bash
curl -X POST "http://127.0.0.1:8000/api/network/inspect" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"http://example.com\",\"followRedirects\":false}"
```
