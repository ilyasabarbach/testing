import asyncio
import json
import logging
from pathlib import Path
import subprocess
import sys

from app.config import get_settings
from app.schemas import (
    ChapterImagePreview,
    ChapterPreviewDiagnostics,
    ChapterPreviewResponse,
)
from app.services.browser_dom_extractor import extract_images_from_rendered_dom
from app.services.chapter_preview import build_filename
from app.services.http_client import TargetFetchError


PLAYWRIGHT_INSTALL_MESSAGE = (
    "Browser render mode requires Playwright and installed browser binaries."
)
MISSING_EXECUTABLE_MESSAGE = "Configured browser executable was not found."
LAUNCH_FAILURE_MESSAGE = "Browser render mode could not launch the browser."
NAVIGATION_FAILURE_MESSAGE = "Browser render mode failed during page navigation."
EXTRACTION_FAILURE_MESSAGE = "Browser render mode failed while extracting rendered HTML."
WORKER_FAILURE_MESSAGE = "Browser render worker failed."
PERSISTENT_CONTEXT_MESSAGE = "Persistent browser context requires BROWSER_USER_DATA_DIR."
PERSISTENT_LAUNCH_FAILURE_MESSAGE = "Browser persistent context could not be launched."
logger = logging.getLogger(__name__)


async def build_browser_chapter_preview(source_url: str) -> ChapterPreviewResponse:
    rendered_html, final_url, worker_diagnostics = await fetch_rendered_html(source_url)
    image_urls, browser_diagnostics = extract_images_from_rendered_dom(
        final_url, rendered_html
    )
    browser_notes = (
        browser_diagnostics["browserExtractionNotes"]
        + worker_diagnostics["browserSessionNotes"]
        + worker_diagnostics["browserScrollNotes"]
    )

    diagnostics = {
        "htmlLength": len(rendered_html),
        "imgTagCount": browser_diagnostics["domImageCount"],
        "imagesFromSrc": 0,
        "imagesFromDataSrc": 0,
        "imagesFromDataLazySrc": 0,
        "imagesFromDataOriginal": 0,
        "imagesFromDataUrl": 0,
        "imagesFromSrcset": 0,
        "imagesFromSourceSrcset": 0,
        "imagesFromMeta": 0,
        "jsonScriptCount": 0,
        "embeddedImageUrlCount": 0,
        "imagesFromEmbeddedJson": 0,
        "deduplicatedCount": browser_diagnostics["domImageCount"] - len(image_urls),
        "looksDynamic": browser_diagnostics["domImageCount"] <= 1,
        "hasAppRootShell": False,
        "possibleApiDrivenPage": False,
        "renderModeUsed": "browser",
        "browserRendered": True,
        "domImageCount": browser_diagnostics["domImageCount"],
        "browserFilteredImageCount": browser_diagnostics["browserFilteredImageCount"],
        "browserHeadless": worker_diagnostics["browserHeadless"],
        "browserPersistentContextEnabled": worker_diagnostics["browserPersistentContextEnabled"],
        "browserUserDataDirConfigured": worker_diagnostics["browserUserDataDirConfigured"],
        "browserSessionMode": worker_diagnostics["browserSessionMode"],
        "browserScrollEnabled": worker_diagnostics["browserScrollEnabled"],
        "browserScrollSteps": worker_diagnostics["browserScrollSteps"],
        "browserScrollHeightBefore": worker_diagnostics["browserScrollHeightBefore"],
        "browserScrollHeightAfter": worker_diagnostics["browserScrollHeightAfter"],
        "browserLazyLoadWaitMs": worker_diagnostics["browserLazyLoadWaitMs"],
        "browserScrollableContainerCount": worker_diagnostics["browserScrollableContainerCount"],
        "browserScrolledContainerCount": worker_diagnostics["browserScrolledContainerCount"],
        "browserMouseWheelSteps": worker_diagnostics["browserMouseWheelSteps"],
        "browserImageCountBeforeScroll": worker_diagnostics["browserImageCountBeforeScroll"],
        "browserImageCountAfterScroll": worker_diagnostics["browserImageCountAfterScroll"],
        "browserImageCountStableRounds": worker_diagnostics["browserImageCountStableRounds"],
        "browserScrollStrategy": worker_diagnostics["browserScrollStrategy"],
        "browserExtractionNotes": browser_notes,
        "notes": browser_notes,
    }

    images = [
        ChapterImagePreview(
            index=index,
            url=image_url,
            filename=build_filename(index, image_url),
        )
        for index, image_url in enumerate(image_urls, start=1)
    ]

    return ChapterPreviewResponse(
        sourceUrl=source_url,
        imageCount=len(images),
        images=images,
        diagnostics=ChapterPreviewDiagnostics(**diagnostics),
    )


async def fetch_rendered_html(source_url: str) -> tuple[str, str, dict]:
    settings = get_settings()
    worker_command = build_browser_worker_command(
        source_url=source_url,
        timeout_seconds=settings.http_timeout_seconds,
        browser_executable_path=settings.browser_executable_path,
        browser_channel=settings.playwright_browser_channel,
        headless=settings.browser_headless,
        user_data_dir=settings.browser_user_data_dir,
        persistent_context_enabled=settings.browser_persistent_context_enabled,
        scroll_enabled=settings.browser_scroll_enabled,
        max_scroll_steps=settings.browser_max_scroll_steps,
        scroll_wait_ms=settings.browser_scroll_wait_ms,
        initial_wait_ms=settings.browser_initial_wait_ms,
        stable_rounds=settings.browser_scroll_stable_rounds,
        max_scroll_containers=settings.browser_max_scroll_containers,
        scroll_delta_px=settings.browser_scroll_delta_px,
    )

    return await asyncio.to_thread(
        run_browser_render_worker,
        worker_command,
        settings.http_timeout_seconds,
    )


def build_browser_worker_command(
    source_url: str,
    timeout_seconds: float,
    browser_executable_path: str | None,
    browser_channel: str | None,
    headless: bool,
    user_data_dir: str | None,
    persistent_context_enabled: bool,
    scroll_enabled: bool,
    max_scroll_steps: int,
    scroll_wait_ms: int,
    initial_wait_ms: int,
    stable_rounds: int,
    max_scroll_containers: int,
    scroll_delta_px: int,
) -> list[str]:
    if browser_executable_path:
        executable_path = Path(browser_executable_path)
        if not executable_path.exists():
            raise TargetFetchError(MISSING_EXECUTABLE_MESSAGE, 500)

    command = [
        sys.executable,
        "-m",
        "app.services.browser_render_worker",
        "--url",
        source_url,
        "--timeout-ms",
        str(round(timeout_seconds * 1000)),
        "--settle-wait-ms",
        str(initial_wait_ms),
        "--headless",
        "true" if headless else "false",
        "--persistent-context-enabled",
        "true" if persistent_context_enabled else "false",
        "--scroll-enabled",
        "true" if scroll_enabled else "false",
        "--max-scroll-steps",
        str(max_scroll_steps),
        "--scroll-wait-ms",
        str(scroll_wait_ms),
        "--scroll-stable-rounds",
        str(stable_rounds),
        "--max-scroll-containers",
        str(max_scroll_containers),
        "--scroll-delta-px",
        str(scroll_delta_px),
    ]

    if browser_executable_path:
        command.extend(["--browser-executable-path", browser_executable_path])

    if browser_channel:
        command.extend(["--browser-channel", browser_channel])
    if persistent_context_enabled and user_data_dir:
        command.extend(["--user-data-dir", user_data_dir])

    return command


def run_browser_render_worker(
    worker_command: list[str],
    timeout_seconds: float,
) -> tuple[str, str, dict]:
    try:
        completed_process = subprocess.run(
            worker_command,
            capture_output=True,
            timeout=timeout_seconds + 5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Browser render worker timed out: %s", exc)
        raise TargetFetchError(WORKER_FAILURE_MESSAGE, 502) from exc
    except UnicodeDecodeError as exc:
        logger.error("Browser render worker decode failure: %s", exc)
        raise TargetFetchError(WORKER_FAILURE_MESSAGE, 502) from exc
    except Exception as exc:
        logger.error("Browser render worker crashed: %s: %s", type(exc).__name__, exc)
        raise TargetFetchError(WORKER_FAILURE_MESSAGE, 502) from exc

    stdout_text = _decode_worker_output(completed_process.stdout)
    stderr_text = _decode_worker_output(completed_process.stderr)

    if stderr_text.strip():
        logger.error("Browser render worker stderr: %s", stderr_text.strip())

    if not stdout_text.strip():
        logger.error(
            "Browser render worker returned empty stdout. rc=%s stderr=%r",
            completed_process.returncode,
            stderr_text,
        )
        raise TargetFetchError(WORKER_FAILURE_MESSAGE, 502)

    try:
        payload = json.loads(stdout_text)
    except (TypeError, json.JSONDecodeError) as exc:
        logger.error(
            "Browser render worker returned invalid JSON. rc=%s stdout=%r stderr=%r",
            completed_process.returncode,
            stdout_text,
            stderr_text,
        )
        raise TargetFetchError(WORKER_FAILURE_MESSAGE, 502) from exc

    if payload.get("ok") is True:
        return (
            payload["html"],
            payload["finalUrl"],
            {
                "browserHeadless": bool(payload.get("browserHeadless", True)),
                "browserPersistentContextEnabled": bool(payload.get("browserPersistentContextEnabled", False)),
                "browserUserDataDirConfigured": bool(payload.get("browserUserDataDirConfigured", False)),
                "browserSessionMode": str(payload.get("browserSessionMode", "ephemeral")),
                "browserScrollEnabled": bool(payload.get("browserScrollEnabled", False)),
                "browserScrollSteps": int(payload.get("browserScrollSteps", 0)),
                "browserScrollHeightBefore": int(payload.get("browserScrollHeightBefore", 0)),
                "browserScrollHeightAfter": int(payload.get("browserScrollHeightAfter", 0)),
                "browserLazyLoadWaitMs": int(payload.get("browserLazyLoadWaitMs", 0)),
                "browserScrollableContainerCount": int(payload.get("browserScrollableContainerCount", 0)),
                "browserScrolledContainerCount": int(payload.get("browserScrolledContainerCount", 0)),
                "browserMouseWheelSteps": int(payload.get("browserMouseWheelSteps", 0)),
                "browserImageCountBeforeScroll": int(payload.get("browserImageCountBeforeScroll", 0)),
                "browserImageCountAfterScroll": int(payload.get("browserImageCountAfterScroll", 0)),
                "browserImageCountStableRounds": int(payload.get("browserImageCountStableRounds", 0)),
                "browserScrollStrategy": str(payload.get("browserScrollStrategy", "window_only")),
                "browserSessionNotes": list(payload.get("browserSessionNotes", [])),
                "browserScrollNotes": list(payload.get("browserScrollNotes", [])),
            },
        )

    raise map_browser_worker_failure(payload)


def map_browser_worker_failure(payload: dict) -> TargetFetchError:
    stage = str(payload.get("stage", "unknown"))
    message = str(payload.get("message", ""))
    logger.error("Browser render worker stage=%s message=%s", stage, message)

    if stage == "playwright_missing":
        return TargetFetchError(PLAYWRIGHT_INSTALL_MESSAGE, 500)
    if stage == "launch":
        if message == MISSING_EXECUTABLE_MESSAGE:
            return TargetFetchError(MISSING_EXECUTABLE_MESSAGE, 500)
        if message == PERSISTENT_CONTEXT_MESSAGE:
            return TargetFetchError(PERSISTENT_CONTEXT_MESSAGE, 500)
        if "launch_persistent_context" in message:
            return TargetFetchError(PERSISTENT_LAUNCH_FAILURE_MESSAGE, 502)
        return TargetFetchError(LAUNCH_FAILURE_MESSAGE, 502)
    if stage == "navigation":
        return TargetFetchError(NAVIGATION_FAILURE_MESSAGE, 502)
    if stage == "content":
        return TargetFetchError(EXTRACTION_FAILURE_MESSAGE, 502)
    return TargetFetchError(WORKER_FAILURE_MESSAGE, 502)


def _decode_worker_output(output: bytes | str | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)
