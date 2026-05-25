import asyncio
import json
import logging
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse

from app.config import get_settings
from app.schemas import (
    ChapterCaptureDiagnostics,
    ChapterCaptureImage,
    ChapterCaptureResponse,
)
from app.services.chapter_preview import build_filename
from app.services.http_client import TargetFetchError


PLAYWRIGHT_INSTALL_MESSAGE = (
    "Browser render mode requires Playwright and installed browser binaries."
)
MISSING_EXECUTABLE_MESSAGE = "Configured browser executable was not found."
PERSISTENT_CONTEXT_MESSAGE = "Persistent browser context requires BROWSER_USER_DATA_DIR."
CAPTURE_WORKER_FAILURE_MESSAGE = "Browser capture worker failed."
CAPTURE_LAUNCH_FAILURE_MESSAGE = "Browser capture mode could not launch the browser."
CAPTURE_NAVIGATION_FAILURE_MESSAGE = "Browser capture mode failed during page navigation."
logger = logging.getLogger(__name__)


async def capture_chapter_images(
    source_url: str,
    requested_duration_seconds: int,
    capture_mode: str = "assisted",
    stop_policy: str | None = None,
) -> ChapterCaptureResponse:
    settings = get_settings()
    effective_stop_policy = stop_policy or settings.browser_capture_stop_policy
    duration_seconds = clamp_capture_duration(
        requested_duration_seconds,
        default_seconds=settings.browser_capture_default_seconds,
        max_seconds=settings.browser_capture_max_seconds,
    )
    command = build_capture_worker_command(
        source_url=source_url,
        duration_seconds=duration_seconds,
        timeout_seconds=settings.http_timeout_seconds,
        browser_executable_path=settings.browser_executable_path,
        browser_channel=settings.playwright_browser_channel,
        headless=settings.browser_headless,
        user_data_dir=settings.browser_user_data_dir,
        persistent_context_enabled=settings.browser_persistent_context_enabled,
        capture_mode=capture_mode,
        stop_policy=effective_stop_policy,
        autonomous_enabled=settings.browser_autonomous_capture_enabled,
        autonomous_max_steps=settings.browser_autonomous_max_steps,
        autonomous_step_wait_ms=settings.browser_autonomous_step_wait_ms,
        autonomous_stable_rounds=settings.browser_autonomous_stable_rounds,
        autonomous_enable_keyboard=settings.browser_autonomous_enable_keyboard,
        autonomous_enable_mouse_wheel=settings.browser_autonomous_enable_mouse_wheel,
        reader_readiness_enabled=settings.browser_reader_readiness_enabled,
        overlay_dismiss_enabled=settings.browser_overlay_dismiss_enabled,
        overlay_max_attempts=settings.browser_overlay_max_attempts,
        carousel_exploration_enabled=settings.browser_carousel_exploration_enabled,
        carousel_max_steps=settings.browser_carousel_max_steps,
        sequence_stable_rounds=settings.browser_sequence_stable_rounds,
    )
    payload = await asyncio.to_thread(
        run_capture_worker,
        command,
        duration_seconds,
        settings.http_timeout_seconds,
    )
    capture_items = deduplicate_capture_items(payload.get("images", []))
    parent_deduplicated_count = len(payload.get("images", [])) - len(capture_items)
    selected_items, selection_diagnostics = select_reader_sequence(capture_items)

    images = [
        ChapterCaptureImage(
            index=index,
            url=item["url"],
            filename=build_filename(index, item["url"]),
            source=item["source"],
        )
        for index, item in enumerate(selected_items, start=1)
    ]

    return ChapterCaptureResponse(
        sourceUrl=source_url,
        captureDurationSeconds=duration_seconds,
        imageCount=len(images),
        images=images,
        diagnostics=ChapterCaptureDiagnostics(
            browserRendered=True,
            captureMode=capture_mode,
            networkImageCount=int(payload.get("networkImageCount", 0)),
            domImageCount=int(payload.get("domImageCount", 0)),
            deduplicatedCount=int(payload.get("deduplicatedCount", 0))
            + parent_deduplicated_count,
            browserHeadless=bool(payload.get("browserHeadless", settings.browser_headless)),
            browserPersistentContextEnabled=bool(
                payload.get(
                    "browserPersistentContextEnabled",
                    settings.browser_persistent_context_enabled,
                )
            ),
            browserUserDataDirConfigured=bool(
                payload.get(
                    "browserUserDataDirConfigured",
                    bool(settings.browser_user_data_dir),
                )
            ),
            browserSessionMode=str(payload.get("browserSessionMode", "ephemeral")),
            captureStopPolicy=effective_stop_policy,
            captureRequestedDurationSeconds=duration_seconds,
            captureActualDurationSeconds=float(
                payload.get("captureActualDurationSeconds", 0.0)
            ),
            stoppedBecauseSequenceStable=bool(
                payload.get("stoppedBecauseSequenceStable", False)
            ),
            autonomousModeEnabled=bool(payload.get("autonomousModeEnabled", False)),
            autonomousStepsExecuted=int(payload.get("autonomousStepsExecuted", 0)),
            autonomousActionsUsed=list(payload.get("autonomousActionsUsed", [])),
            imageCountBeforeAutonomousActions=int(
                payload.get("imageCountBeforeAutonomousActions", 0)
            ),
            imageCountAfterAutonomousActions=int(
                payload.get("imageCountAfterAutonomousActions", len(capture_items))
            ),
            imageCountStableRounds=int(payload.get("imageCountStableRounds", 0)),
            observedImageCount=len(capture_items),
            selectedImageCount=len(selected_items),
            excludedImageCount=len(capture_items) - len(selected_items),
            selectionStrategy=selection_diagnostics["selectionStrategy"],
            dominantSequenceDetected=selection_diagnostics["dominantSequenceDetected"],
            dominantSequenceLength=selection_diagnostics["dominantSequenceLength"],
            numericOrderingApplied=selection_diagnostics["numericOrderingApplied"],
            duplicatePageNumberCount=selection_diagnostics["duplicatePageNumberCount"],
            missingPageNumbers=selection_diagnostics["missingPageNumbers"],
            selectedPageNumbers=selection_diagnostics["selectedPageNumbers"],
            orderingStrategy=selection_diagnostics["orderingStrategy"],
            readerReadinessEnabled=bool(payload.get("readerReadinessEnabled", False)),
            overlayDismissEnabled=bool(payload.get("overlayDismissEnabled", False)),
            overlayDismissAttempts=int(payload.get("overlayDismissAttempts", 0)),
            overlayDismissedCount=int(payload.get("overlayDismissedCount", 0)),
            carouselExplorationEnabled=bool(payload.get("carouselExplorationEnabled", False)),
            carouselStepsExecuted=int(payload.get("carouselStepsExecuted", 0)),
            sequenceLengthBeforeExploration=int(
                payload.get("sequenceLengthBeforeExploration", 0)
            ),
            sequenceLengthAfterExploration=int(
                payload.get("sequenceLengthAfterExploration", 0)
            ),
            sequenceStableRounds=int(payload.get("sequenceStableRounds", 0)),
            autonomousStopReason=str(payload.get("autonomousStopReason", "none")),
            blockedByOverlaySuspected=bool(payload.get("blockedByOverlaySuspected", False)),
            manualInteractionExpected=capture_mode == "assisted",
            notes=list(payload.get("notes", [])),
        ),
    )


def clamp_capture_duration(
    requested_seconds: int,
    default_seconds: int,
    max_seconds: int,
) -> int:
    if requested_seconds <= 0:
        return default_seconds
    return min(max(requested_seconds, 5), max_seconds)


def deduplicate_capture_items(raw_items: list[dict]) -> list[dict]:
    items: list[dict] = []
    seen_urls: set[str] = set()
    for item in raw_items:
        url = str(item.get("url", "")).strip()
        source = str(item.get("source", "dom")).strip()
        if not url or url in seen_urls:
            continue
        if source not in {"network", "dom"}:
            source = "dom"
        seen_urls.add(url)
        items.append({"url": url, "source": source})
    return items


def select_reader_sequence(items: list[dict]) -> tuple[list[dict], dict]:
    buckets: dict[tuple[str, str], list[tuple[dict, int]]] = {}
    for item in items:
        sequence_parts = _numeric_sequence_parts(item["url"])
        if sequence_parts is None:
            continue
        sequence_key, page_number = sequence_parts
        buckets.setdefault(sequence_key, []).append((item, page_number))

    dominant_sequence = max(buckets.values(), key=len, default=[])
    if len(dominant_sequence) >= 3:
        selected_items, ordering_diagnostics = _order_dominant_sequence(
            dominant_sequence
        )
        return selected_items, {
            "selectionStrategy": "dominant_numeric_sequence",
            "dominantSequenceDetected": True,
            "dominantSequenceLength": len(selected_items),
            **ordering_diagnostics,
        }

    fallback_items = [
        item for item in items if not _looks_like_common_asset(item["url"])
    ] or items
    return fallback_items, {
        "selectionStrategy": "discovery_order",
        "dominantSequenceDetected": False,
        "dominantSequenceLength": 0,
        "numericOrderingApplied": False,
        "duplicatePageNumberCount": 0,
        "missingPageNumbers": [],
        "selectedPageNumbers": [],
        "orderingStrategy": "discovery_order",
    }


def _numeric_sequence_key(url: str) -> tuple[str, str] | None:
    sequence_parts = _numeric_sequence_parts(url)
    if sequence_parts is None:
        return None
    return sequence_parts[0]


def _numeric_sequence_parts(url: str) -> tuple[tuple[str, str], int] | None:
    parsed = urlparse(url)
    path = parsed.path
    match = re.search(r"(\d+)(?=\.[A-Za-z0-9]+$)", path)
    if not match:
        return None
    prefix = path[: match.start()]
    suffix = path[match.end() :]
    return (prefix, suffix), int(match.group(1))


def _order_dominant_sequence(
    sequence_items: list[tuple[dict, int]],
) -> tuple[list[dict], dict]:
    first_item_by_page: dict[int, dict] = {}
    duplicate_page_number_count = 0

    for item, page_number in sequence_items:
        if page_number in first_item_by_page:
            duplicate_page_number_count += 1
            continue
        first_item_by_page[page_number] = item

    selected_page_numbers = sorted(first_item_by_page)
    selected_items = [
        first_item_by_page[page_number] for page_number in selected_page_numbers
    ]
    missing_page_numbers = _missing_page_numbers(selected_page_numbers)

    return selected_items, {
        "numericOrderingApplied": True,
        "duplicatePageNumberCount": duplicate_page_number_count,
        "missingPageNumbers": missing_page_numbers,
        "selectedPageNumbers": selected_page_numbers,
        "orderingStrategy": "numeric_page_number",
    }


def _missing_page_numbers(selected_page_numbers: list[int]) -> list[int]:
    if not selected_page_numbers:
        return []
    selected = set(selected_page_numbers)
    return [
        page_number
        for page_number in range(
            selected_page_numbers[0],
            selected_page_numbers[-1] + 1,
        )
        if page_number not in selected
    ]


def _looks_like_common_asset(url: str) -> bool:
    normalized = url.lower()
    return any(
        term in normalized
        for term in (
            "logo",
            "icon",
            "avatar",
            "banner",
            "sprite",
            "favicon",
            "ads",
            "advert",
        )
    )


def build_capture_worker_command(
    source_url: str,
    duration_seconds: int,
    timeout_seconds: float,
    browser_executable_path: str | None,
    browser_channel: str | None,
    headless: bool,
    user_data_dir: str | None,
    persistent_context_enabled: bool,
    capture_mode: str,
    stop_policy: str,
    autonomous_enabled: bool,
    autonomous_max_steps: int,
    autonomous_step_wait_ms: int,
    autonomous_stable_rounds: int,
    autonomous_enable_keyboard: bool,
    autonomous_enable_mouse_wheel: bool,
    reader_readiness_enabled: bool,
    overlay_dismiss_enabled: bool,
    overlay_max_attempts: int,
    carousel_exploration_enabled: bool,
    carousel_max_steps: int,
    sequence_stable_rounds: int,
) -> list[str]:
    if browser_executable_path:
        executable_path = Path(browser_executable_path)
        if not executable_path.exists():
            raise TargetFetchError(MISSING_EXECUTABLE_MESSAGE, 500)

    command = [
        sys.executable,
        "-m",
        "app.services.browser_capture_worker",
        "--url",
        source_url,
        "--duration-seconds",
        str(duration_seconds),
        "--timeout-ms",
        str(round(timeout_seconds * 1000)),
        "--headless",
        "true" if headless else "false",
        "--persistent-context-enabled",
        "true" if persistent_context_enabled else "false",
        "--capture-mode",
        capture_mode,
        "--stop-policy",
        stop_policy,
        "--autonomous-enabled",
        "true" if autonomous_enabled else "false",
        "--autonomous-max-steps",
        str(autonomous_max_steps),
        "--autonomous-step-wait-ms",
        str(autonomous_step_wait_ms),
        "--autonomous-stable-rounds",
        str(autonomous_stable_rounds),
        "--autonomous-enable-keyboard",
        "true" if autonomous_enable_keyboard else "false",
        "--autonomous-enable-mouse-wheel",
        "true" if autonomous_enable_mouse_wheel else "false",
        "--reader-readiness-enabled",
        "true" if reader_readiness_enabled else "false",
        "--overlay-dismiss-enabled",
        "true" if overlay_dismiss_enabled else "false",
        "--overlay-max-attempts",
        str(overlay_max_attempts),
        "--carousel-exploration-enabled",
        "true" if carousel_exploration_enabled else "false",
        "--carousel-max-steps",
        str(carousel_max_steps),
        "--sequence-stable-rounds",
        str(sequence_stable_rounds),
    ]
    if browser_executable_path:
        command.extend(["--browser-executable-path", browser_executable_path])
    if browser_channel:
        command.extend(["--browser-channel", browser_channel])
    if user_data_dir:
        command.extend(["--user-data-dir", user_data_dir])
    return command


def run_capture_worker(
    worker_command: list[str],
    duration_seconds: int,
    timeout_seconds: float,
) -> dict:
    try:
        completed_process = subprocess.run(
            worker_command,
            capture_output=True,
            timeout=duration_seconds + timeout_seconds + 10,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Browser capture worker timed out: %s", exc)
        raise TargetFetchError(CAPTURE_WORKER_FAILURE_MESSAGE, 502) from exc
    except Exception as exc:
        logger.error("Browser capture worker crashed: %s: %s", type(exc).__name__, exc)
        raise TargetFetchError(CAPTURE_WORKER_FAILURE_MESSAGE, 502) from exc

    stdout_text = _decode_worker_output(completed_process.stdout)
    stderr_text = _decode_worker_output(completed_process.stderr)
    if stderr_text.strip():
        logger.error("Browser capture worker stderr: %s", stderr_text.strip())

    if not stdout_text.strip():
        logger.error(
            "Browser capture worker returned empty stdout. rc=%s stderr=%r",
            completed_process.returncode,
            stderr_text,
        )
        raise TargetFetchError(CAPTURE_WORKER_FAILURE_MESSAGE, 502)

    try:
        payload = json.loads(stdout_text)
    except (TypeError, json.JSONDecodeError) as exc:
        logger.error(
            "Browser capture worker returned invalid JSON. rc=%s stdout=%r stderr=%r",
            completed_process.returncode,
            stdout_text,
            stderr_text,
        )
        raise TargetFetchError(CAPTURE_WORKER_FAILURE_MESSAGE, 502) from exc

    if payload.get("ok") is True:
        return payload

    raise map_capture_worker_failure(payload)


def map_capture_worker_failure(payload: dict) -> TargetFetchError:
    stage = str(payload.get("stage", "unknown"))
    message = str(payload.get("message", ""))
    logger.error("Browser capture worker stage=%s message=%s", stage, message)

    if stage == "playwright_missing":
        return TargetFetchError(PLAYWRIGHT_INSTALL_MESSAGE, 500)
    if stage == "launch":
        if message == PERSISTENT_CONTEXT_MESSAGE:
            return TargetFetchError(PERSISTENT_CONTEXT_MESSAGE, 500)
        return TargetFetchError(CAPTURE_LAUNCH_FAILURE_MESSAGE, 502)
    if stage == "navigation":
        return TargetFetchError(CAPTURE_NAVIGATION_FAILURE_MESSAGE, 502)
    return TargetFetchError(CAPTURE_WORKER_FAILURE_MESSAGE, 502)


def _decode_worker_output(output: bytes | str | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)
