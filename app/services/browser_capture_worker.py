import argparse
import json
import re
import sys
import time
from urllib.parse import urlparse


IMAGE_EXTENSION_PATTERN = re.compile(
    r"\.(?:jpg|jpeg|png|webp|gif|avif)(?:$|[?#])",
    re.IGNORECASE,
)
SAFE_OVERLAY_TEXTS = {
    "close",
    "ok",
    "got it",
    "continue",
    "start",
    "start reading",
    "don't show",
    "do not show",
    "ne plus afficher",
}
FORBIDDEN_OVERLAY_TEXTS = {
    "login",
    "log in",
    "sign in",
    "register",
    "pay",
    "subscribe",
    "captcha",
    "verify",
    "cloudflare",
    "challenge",
    "cookie",
    "cookies",
    "age verification",
}
READER_BOUNDARY_TERMS = ("comments", "comment", "discussion", "replies", "reviews")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        _print_payload(
            {
                "ok": False,
                "stage": "playwright_missing",
                "message": "Playwright package is not installed.",
            }
        )
        return 0

    browser = None
    context = None
    discovered: list[dict] = []
    seen_urls: set[str] = set()
    raw_seen_count = 0
    network_seen_count = 0
    dom_seen_count = 0
    capture_started_at = time.monotonic()

    def add_image(url: str | None, source: str) -> None:
        nonlocal raw_seen_count, network_seen_count, dom_seen_count
        if not url or not _looks_like_image_url(url):
            return
        raw_seen_count += 1
        if source == "network":
            network_seen_count += 1
        else:
            dom_seen_count += 1
        if url in seen_urls:
            return
        seen_urls.add(url)
        discovered.append({"url": url, "source": source})

    try:
        with sync_playwright() as playwright:
            headless = str(args.headless).strip().lower() == "true"
            persistent_enabled = (
                str(args.persistent_context_enabled).strip().lower() == "true"
            )
            user_data_dir = (args.user_data_dir or "").strip() or None
            launch_kwargs = {"headless": headless}
            if args.browser_executable_path:
                launch_kwargs["executable_path"] = args.browser_executable_path
            if args.browser_channel:
                launch_kwargs["channel"] = args.browser_channel

            try:
                if persistent_enabled:
                    if not user_data_dir:
                        _print_payload(
                            {
                                "ok": False,
                                "stage": "launch",
                                "message": "Persistent browser context requires BROWSER_USER_DATA_DIR.",
                            }
                        )
                        return 0
                    context = playwright.chromium.launch_persistent_context(
                        user_data_dir,
                        **launch_kwargs,
                    )
                    browser = context.browser
                else:
                    browser = playwright.chromium.launch(**launch_kwargs)
                    context = browser.new_context()
            except Exception as exc:
                _print_payload({"ok": False, "stage": "launch", "message": str(exc)})
                return 0

            page = context.new_page()

            def handle_response(response) -> None:
                try:
                    if response.request.resource_type == "image" or _looks_like_image_url(
                        response.url
                    ):
                        add_image(response.url, "network")
                except Exception:
                    return

            page.on("response", handle_response)

            try:
                page.goto(
                    args.url,
                    wait_until="domcontentloaded",
                    timeout=args.timeout_ms,
                )
            except Exception as exc:
                _print_payload(
                    {"ok": False, "stage": "navigation", "message": str(exc)}
                )
                return 0

            for url in _scan_dom_image_urls(page):
                add_image(url, "dom")

            capture_started_at = time.monotonic()
            image_count_before_actions = len(discovered)
            autonomous_diagnostics = _default_autonomous_diagnostics(
                args,
                image_count_before_actions,
            )
            if args.capture_mode == "autonomous" and _is_true(args.autonomous_enabled):
                readiness_diagnostics = _run_reader_readiness(page, args)
                autonomous_diagnostics = _run_autonomous_capture(
                    page,
                    args,
                    add_image,
                    discovered,
                    lambda: network_seen_count,
                )
                autonomous_notes = autonomous_diagnostics.get("notes", [])
                autonomous_diagnostics.update(readiness_diagnostics)
                autonomous_diagnostics["notes"] = (
                    readiness_diagnostics.get("notes", []) + autonomous_notes
                )
            else:
                deadline = time.monotonic() + args.duration_seconds
                while time.monotonic() < deadline:
                    for url in _scan_dom_image_urls(page):
                        add_image(url, "dom")
                    page.wait_for_timeout(500)

            for url in _scan_dom_image_urls(page):
                add_image(url, "dom")
            capture_actual_duration = time.monotonic() - capture_started_at
            autonomous_diagnostics["imageCountAfterAutonomousActions"] = len(discovered)

            _print_payload(
                {
                    "ok": True,
                    "images": discovered,
                    "networkImageCount": network_seen_count,
                    "domImageCount": dom_seen_count,
                    "deduplicatedCount": raw_seen_count - len(discovered),
                    "browserHeadless": headless,
                    "browserPersistentContextEnabled": persistent_enabled,
                    "browserUserDataDirConfigured": bool(user_data_dir),
                    "browserSessionMode": "persistent" if persistent_enabled else "ephemeral",
                    "captureStopPolicy": args.stop_policy,
                    "captureRequestedDurationSeconds": args.duration_seconds,
                    "captureActualDurationSeconds": round(capture_actual_duration, 3),
                    **autonomous_diagnostics,
                    "notes": [
                        _capture_mode_note(
                            args.capture_mode,
                            _normalized_navigation_strategy(
                                getattr(args, "reader_navigation_strategy", "generic")
                            ),
                        ),
                        _stop_policy_note(args.stop_policy),
                        *(_session_notes(persistent_enabled)),
                        "Capture collected DOM and network image URLs without automatic clicking.",
                    ]
                    + autonomous_diagnostics.get("notes", []),
                }
            )
            return 0
    except Exception as exc:
        _print_payload({"ok": False, "stage": "unknown", "message": str(exc)})
        return 0
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        elif browser is not None:
            try:
                browser.close()
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--duration-seconds", required=True, type=int)
    parser.add_argument("--timeout-ms", required=True, type=int)
    parser.add_argument("--headless", default="false")
    parser.add_argument("--browser-executable-path")
    parser.add_argument("--browser-channel")
    parser.add_argument("--user-data-dir")
    parser.add_argument("--persistent-context-enabled", default="false")
    parser.add_argument("--capture-mode", default="assisted")
    parser.add_argument("--stop-policy", default="sequence_stable")
    parser.add_argument("--autonomous-enabled", default="true")
    parser.add_argument("--autonomous-max-steps", default=60, type=int)
    parser.add_argument("--autonomous-step-wait-ms", default=700, type=int)
    parser.add_argument("--autonomous-stable-rounds", default=5, type=int)
    parser.add_argument("--autonomous-enable-keyboard", default="true")
    parser.add_argument("--autonomous-enable-mouse-wheel", default="true")
    parser.add_argument("--reader-readiness-enabled", default="true")
    parser.add_argument("--overlay-dismiss-enabled", default="true")
    parser.add_argument("--overlay-max-attempts", default=3, type=int)
    parser.add_argument("--carousel-exploration-enabled", default="true")
    parser.add_argument("--carousel-max-steps", default=80, type=int)
    parser.add_argument("--sequence-stable-rounds", default=6, type=int)
    parser.add_argument("--smart-stop-min-steps", default=20, type=int)
    parser.add_argument("--smart-stop-stable-rounds", default=8, type=int)
    parser.add_argument("--smart-stop-min-sequence-length", default=3, type=int)
    parser.add_argument("--smart-stop-use-reader-boundary", default="true")
    parser.add_argument(
        "--smart-stop-reader-boundary-min-sequence-length",
        default=20,
        type=int,
    )
    parser.add_argument(
        "--smart-stop-reader-boundary-recent-growth-window",
        default=20,
        type=int,
    )
    parser.add_argument(
        "--smart-stop-reader-boundary-stable-rounds",
        default=10,
        type=int,
    )
    parser.add_argument("--large-sequence-mode-enabled", default="true")
    parser.add_argument("--large-sequence-min-length", default=20, type=int)
    parser.add_argument("--large-sequence-max-steps", default=1000, type=int)
    parser.add_argument("--large-sequence-step-wait-ms", default=250, type=int)
    parser.add_argument("--large-sequence-extend-while-growing", default="true")
    parser.add_argument("--large-sequence-stable-rounds", default=25, type=int)
    parser.add_argument("--sustained-arrow-down-enabled", default="true")
    parser.add_argument("--sustained-arrow-down-rounds", default=120, type=int)
    parser.add_argument(
        "--sustained-arrow-down-presses-per-round",
        default=10,
        type=int,
    )
    parser.add_argument(
        "--sustained-arrow-down-press-delay-ms",
        default=40,
        type=int,
    )
    parser.add_argument(
        "--sustained-arrow-down-round-wait-ms",
        default=250,
        type=int,
    )
    parser.add_argument(
        "--sustained-arrow-down-stable-rounds",
        default=20,
        type=int,
    )
    parser.add_argument("--reader-navigation-strategy", default="generic")
    parser.add_argument("--right-arrow-nav-enabled", default="true")
    parser.add_argument("--right-arrow-max-steps", default=1000, type=int)
    parser.add_argument("--right-arrow-wait-ms", default=250, type=int)
    parser.add_argument("--right-arrow-stable-rounds", default=25, type=int)
    parser.add_argument(
        "--right-arrow-presses-per-round",
        default=1,
        type=int,
    )
    parser.add_argument("--right-arrow-stop-on-url-change", default="true")
    return parser


def _scan_dom_image_urls(page) -> list[str]:
    return page.evaluate(
        """() => {
            const attrs = ["currentSrc", "src", "data-src", "data-lazy-src", "data-original", "data-url"];
            const urls = [];
            for (const image of Array.from(document.querySelectorAll("img"))) {
                for (const attr of attrs) {
                    const value = attr === "currentSrc" ? image.currentSrc : image.getAttribute(attr);
                    if (!value) continue;
                    try {
                        urls.push(new URL(value, document.baseURI).href);
                    } catch (_) {
                    }
                }
            }
            return urls;
        }"""
    )


def _run_autonomous_capture(
    page,
    args,
    add_image,
    discovered: list[dict],
    get_network_image_count=None,
) -> dict:
    actions = _build_autonomous_actions(args)
    diagnostics = _default_autonomous_diagnostics(args, len(discovered))
    diagnostics["autonomousModeEnabled"] = True
    diagnostics["carouselExplorationEnabled"] = _is_true(
        getattr(args, "carousel_exploration_enabled", "true")
    )
    diagnostics["sequenceLengthBeforeExploration"] = _dominant_sequence_length(discovered)
    deadline = time.monotonic() + args.duration_seconds
    stable_rounds = 0
    last_sequence_length = diagnostics["sequenceLengthBeforeExploration"]
    last_sequence_growth_step = 0
    last_network_growth_step = 0
    productive_action_counts: dict[str, int] = {}
    action_lookup = _build_action_lookup(actions)
    last_network_image_count = (
        int(get_network_image_count()) if callable(get_network_image_count) else 0
    )
    (
        diagnostics,
        productive_action_counts,
        last_sequence_length,
        last_sequence_growth_step,
        last_network_image_count,
        last_network_growth_step,
    ) = (
        _run_sustained_arrow_down_phase(
            page=page,
            args=args,
            add_image=add_image,
            discovered=discovered,
            deadline=deadline,
            diagnostics=diagnostics,
            productive_action_counts=productive_action_counts,
            get_network_image_count=get_network_image_count,
            last_network_image_count=last_network_image_count,
        )
        if diagnostics["readerNavigationStrategy"] != "right_arrow_only"
        else (
            diagnostics,
            productive_action_counts,
            last_sequence_length,
            last_sequence_growth_step,
            last_network_image_count,
            last_network_growth_step,
        )
    )
    if diagnostics["readerNavigationStrategy"] == "right_arrow_only":
        return _run_right_arrow_only_phase(
            page=page,
            args=args,
            add_image=add_image,
            discovered=discovered,
            deadline=deadline,
            diagnostics=diagnostics,
            productive_action_counts=productive_action_counts,
            get_network_image_count=get_network_image_count,
            last_network_image_count=last_network_image_count,
        )
    step = 0
    normal_max_steps = min(
        args.autonomous_max_steps,
        getattr(args, "carousel_max_steps", 80),
    )
    max_steps = normal_max_steps
    stop_policy = getattr(args, "stop_policy", "sequence_stable")
    if last_sequence_length >= diagnostics["smartStopMinSequenceLength"]:
        last_sequence_growth_step = 0

    while time.monotonic() < deadline:
        action_name = ""
        if step < max_steps:
            action_name, action = _choose_next_action(
                actions,
                action_lookup,
                step,
                productive_action_counts,
                diagnostics["largeSequenceModeTriggered"],
            )
            try:
                action(page)
                diagnostics["autonomousActionsUsed"].append(action_name)
                if action_name.startswith("keyboard_") or action_name in {
                    "mouse_wheel",
                    "horizontal_wheel",
                }:
                    diagnostics["carouselStepsExecuted"] += 1
            except Exception:
                diagnostics["autonomousActionFailureCount"] += 1
                diagnostics["notes"].append(
                    f"Autonomous capture action failed and was skipped: {action_name}."
                )
        elif stop_policy != "duration":
            diagnostics["autonomousStopReason"] = "max_steps_reached"
            diagnostics["smartStopReason"] = (
                "max_steps_reached" if diagnostics["smartStopEnabled"] else "none"
            )
            if diagnostics["largeSequenceModeTriggered"]:
                diagnostics["largeSequenceStopReason"] = "max_steps_reached"
            break

        page.wait_for_timeout(
            _current_step_wait_ms(
                args,
                diagnostics["largeSequenceModeTriggered"],
            )
        )
        for url in _scan_dom_image_urls(page):
            add_image(url, "dom")

        current_sequence_length = _dominant_sequence_length(discovered)
        if current_sequence_length > last_sequence_length:
            stable_rounds = 0
            last_sequence_growth_step = step + 1
            diagnostics["sequenceGrowthEvents"] += 1
            diagnostics["lastProductiveAction"] = action_name
            if action_name:
                productive_action_counts[action_name] = (
                    productive_action_counts.get(action_name, 0) + 1
                )
                diagnostics["productiveActions"] = _sorted_productive_actions(
                    productive_action_counts
                )
        else:
            stable_rounds += 1
        last_sequence_length = current_sequence_length
        current_network_image_count = (
            int(get_network_image_count()) if callable(get_network_image_count) else 0
        )
        if current_network_image_count > last_network_image_count:
            last_network_growth_step = step + 1
        last_network_image_count = current_network_image_count
        diagnostics["readerBoundarySuspected"] = (
            _detect_reader_boundary(page)
            if _is_true(getattr(args, "smart_stop_use_reader_boundary", "true"))
            else False
        )
        step += 1
        if (
            diagnostics["sequenceLengthAtNormalStepLimit"] == 0
            and step >= normal_max_steps
        ):
            diagnostics["sequenceLengthAtNormalStepLimit"] = current_sequence_length
        if _should_enable_large_sequence_mode(
            diagnostics,
            current_sequence_length,
        ):
            diagnostics["largeSequenceModeTriggered"] = True
            if _is_true(getattr(args, "large_sequence_extend_while_growing", "true")):
                max_steps = max(
                    normal_max_steps,
                    int(getattr(args, "large_sequence_max_steps", normal_max_steps)),
                )
        if diagnostics["largeSequenceModeTriggered"]:
            diagnostics["largeSequenceStepsExecuted"] += 1

        if stop_policy == "duration":
            continue
        if (
            stop_policy == "sequence_stable"
            and stable_rounds >= getattr(args, "sequence_stable_rounds", 6)
        ):
            diagnostics["autonomousStopReason"] = "sequence_stable"
            diagnostics["stoppedBecauseSequenceStable"] = True
            break
        if stop_policy == "smart":
            smart_reason = _evaluate_smart_stop(
                diagnostics=diagnostics,
                step=step,
                stable_rounds=stable_rounds,
                current_sequence_length=current_sequence_length,
                last_network_growth_step=last_network_growth_step,
                last_sequence_growth_step=last_sequence_growth_step,
            )
            if smart_reason:
                diagnostics["smartStopTriggered"] = True
                diagnostics["smartStopReason"] = smart_reason
                diagnostics["autonomousStopReason"] = smart_reason
                if diagnostics["largeSequenceModeTriggered"]:
                    diagnostics["largeSequenceStopReason"] = smart_reason
                diagnostics["stoppedBecauseSequenceStable"] = (
                    smart_reason == "smart_sequence_complete"
                )
                break

    diagnostics["autonomousStepsExecuted"] = step
    diagnostics["imageCountStableRounds"] = stable_rounds
    diagnostics["sequenceStableRounds"] = stable_rounds
    diagnostics["imageCountAfterAutonomousActions"] = len(discovered)
    diagnostics["sequenceLengthAfterExploration"] = _dominant_sequence_length(discovered)
    diagnostics["lastSequenceGrowthStep"] = last_sequence_growth_step
    if stop_policy == "duration":
        diagnostics["autonomousStopReason"] = "duration_elapsed"
        diagnostics["stoppedBecauseSequenceStable"] = False
    elif stop_policy == "sequence_stable" and stable_rounds >= getattr(
        args, "sequence_stable_rounds", 6
    ):
        diagnostics["autonomousStopReason"] = "sequence_stable"
        diagnostics["stoppedBecauseSequenceStable"] = True
    elif stop_policy == "smart" and not diagnostics["smartStopTriggered"]:
        if diagnostics["autonomousStopReason"] not in {"max_steps_reached"}:
            diagnostics["autonomousStopReason"] = "duration_elapsed"
        if diagnostics["smartStopReason"] == "none":
            diagnostics["smartStopReason"] = diagnostics["autonomousStopReason"]
        if diagnostics["largeSequenceModeTriggered"]:
            diagnostics["largeSequenceStopReason"] = diagnostics["autonomousStopReason"]
    elif diagnostics["autonomousStopReason"] == "none" and step >= max_steps:
        diagnostics["autonomousStopReason"] = "max_steps_reached"
    elif diagnostics["autonomousStopReason"] == "none":
        diagnostics["autonomousStopReason"] = "duration_elapsed"
    if diagnostics["largeSequenceModeTriggered"] and diagnostics["largeSequenceStopReason"] == "none":
        diagnostics["largeSequenceStopReason"] = diagnostics["autonomousStopReason"]
    return diagnostics


def _evaluate_smart_stop(
    diagnostics: dict,
    step: int,
    stable_rounds: int,
    current_sequence_length: int,
    last_network_growth_step: int,
    last_sequence_growth_step: int,
) -> str | None:
    if step < diagnostics["smartStopMinSteps"]:
        return None
    if current_sequence_length < diagnostics["smartStopMinSequenceLength"]:
        return None
    stable_threshold = (
        diagnostics["largeSequenceStableRounds"]
        if diagnostics["largeSequenceModeTriggered"]
        else diagnostics["smartStopStableRounds"]
    )
    if stable_rounds < stable_threshold:
        return None
    if last_network_growth_step and step - last_network_growth_step < 2:
        return None
    if diagnostics["readerBoundarySuspected"]:
        if current_sequence_length < diagnostics["readerBoundaryMinSequenceLength"]:
            diagnostics["readerBoundaryBlockedBecauseSequenceTooSmall"] = True
            return None
        if (
            last_sequence_growth_step
            and step - last_sequence_growth_step
            <= diagnostics["readerBoundaryRecentGrowthWindow"]
        ):
            diagnostics["readerBoundaryBlockedBecauseRecentGrowth"] = True
            return None
        if stable_rounds < diagnostics["readerBoundaryStableRoundsRequired"]:
            diagnostics["readerBoundaryBlockedBecauseNotStableEnough"] = True
            return None
        return "smart_reader_boundary"
    return "smart_sequence_complete"


def _run_sustained_arrow_down_phase(
    page,
    args,
    add_image,
    discovered: list[dict],
    deadline: float,
    diagnostics: dict,
    productive_action_counts: dict[str, int],
    get_network_image_count=None,
    last_network_image_count: int = 0,
) -> tuple[dict, dict[str, int], int, int, int, int]:
    sequence_before = _dominant_sequence_length(discovered)
    diagnostics["sustainedArrowDownSequenceBefore"] = sequence_before
    last_sequence_length = sequence_before
    last_sequence_growth_step = 0
    last_network_growth_step = 0

    if not diagnostics["sustainedArrowDownEnabled"]:
        diagnostics["sustainedArrowDownSequenceAfter"] = sequence_before
        return (
            diagnostics,
            productive_action_counts,
            last_sequence_length,
            last_sequence_growth_step,
            last_network_image_count,
            last_network_growth_step,
        )

    stable_rounds = 0
    max_rounds = int(getattr(args, "sustained_arrow_down_rounds", 120))
    presses_per_round = int(
        getattr(args, "sustained_arrow_down_presses_per_round", 10)
    )
    press_delay_ms = int(
        getattr(args, "sustained_arrow_down_press_delay_ms", 40)
    )
    round_wait_ms = int(
        getattr(args, "sustained_arrow_down_round_wait_ms", 250)
    )
    stable_rounds_required = int(
        getattr(args, "sustained_arrow_down_stable_rounds", 20)
    )

    for round_index in range(max_rounds):
        if time.monotonic() >= deadline:
            diagnostics["sustainedArrowDownStopReason"] = "duration_elapsed"
            break
        try:
            page.evaluate("() => { if (document.body) document.body.focus(); }")
        except Exception:
            pass
        for _ in range(presses_per_round):
            if time.monotonic() >= deadline:
                diagnostics["sustainedArrowDownStopReason"] = "duration_elapsed"
                break
            try:
                page.keyboard.press("ArrowDown")
                diagnostics["sustainedArrowDownPressesSent"] += 1
            except Exception:
                diagnostics["autonomousActionFailureCount"] += 1
            if press_delay_ms > 0:
                page.wait_for_timeout(press_delay_ms)
        if diagnostics["sustainedArrowDownStopReason"] == "duration_elapsed":
            break
        if round_wait_ms > 0:
            page.wait_for_timeout(round_wait_ms)
        for url in _scan_dom_image_urls(page):
            add_image(url, "dom")
        diagnostics["sustainedArrowDownRoundsExecuted"] = round_index + 1
        current_sequence_length = _dominant_sequence_length(discovered)
        current_network_image_count = (
            int(get_network_image_count()) if callable(get_network_image_count) else 0
        )
        if current_network_image_count > last_network_image_count:
            last_network_growth_step = round_index + 1
        last_network_image_count = current_network_image_count
        if current_sequence_length > last_sequence_length:
            stable_rounds = 0
            last_sequence_growth_step = round_index + 1
            diagnostics["sustainedArrowDownGrowthEvents"] += 1
            diagnostics["sequenceGrowthEvents"] += 1
            diagnostics["sustainedArrowDownProductive"] = True
            diagnostics["lastProductiveAction"] = "sustained_arrow_down"
            productive_action_counts["sustained_arrow_down"] = (
                productive_action_counts.get("sustained_arrow_down", 0) + 1
            )
            diagnostics["productiveActions"] = _sorted_productive_actions(
                productive_action_counts
            )
        else:
            stable_rounds += 1
        last_sequence_length = current_sequence_length
        diagnostics["sustainedArrowDownStableRounds"] = stable_rounds
        diagnostics["sustainedArrowDownSequenceAfter"] = current_sequence_length
        if _should_enable_large_sequence_mode(diagnostics, current_sequence_length):
            diagnostics["largeSequenceModeTriggered"] = True
        if stable_rounds >= stable_rounds_required:
            diagnostics["sustainedArrowDownStopReason"] = "stable_rounds_reached"
            break
    else:
        diagnostics["sustainedArrowDownStopReason"] = "max_rounds_reached"

    if diagnostics["sustainedArrowDownStopReason"] == "none":
        diagnostics["sustainedArrowDownStopReason"] = "duration_elapsed"
    return (
        diagnostics,
        productive_action_counts,
        last_sequence_length,
        last_sequence_growth_step,
        last_network_image_count,
        last_network_growth_step,
    )


def _run_right_arrow_only_phase(
    page,
    args,
    add_image,
    discovered: list[dict],
    deadline: float,
    diagnostics: dict,
    productive_action_counts: dict[str, int],
    get_network_image_count=None,
    last_network_image_count: int = 0,
) -> dict:
    sequence_before = _dominant_sequence_length(discovered)
    diagnostics["rightArrowSequenceBefore"] = sequence_before
    diagnostics["rightArrowSequenceAfter"] = sequence_before
    last_sequence_length = sequence_before
    last_sequence_growth_step = 0
    stable_rounds = 0
    steps_executed = 0
    stop_policy = getattr(args, "stop_policy", "sequence_stable")
    max_steps = int(getattr(args, "right_arrow_max_steps", 1000))
    presses_per_round = int(getattr(args, "right_arrow_presses_per_round", 1))
    round_wait_ms = int(getattr(args, "right_arrow_wait_ms", 250))
    stable_rounds_required = int(getattr(args, "right_arrow_stable_rounds", 25))
    stop_on_url_change = _is_true(
        getattr(args, "right_arrow_stop_on_url_change", "true")
    )
    last_network_growth_step = 0
    initial_url = _current_page_url(page)
    diagnostics["rightArrowInitialUrl"] = initial_url
    diagnostics["rightArrowFinalUrl"] = initial_url

    if not diagnostics["rightArrowNavigationEnabled"]:
        diagnostics["rightArrowStopReason"] = "disabled"
        diagnostics["autonomousStopReason"] = "duration_elapsed"
        diagnostics["sequenceLengthAfterExploration"] = sequence_before
        diagnostics["imageCountAfterAutonomousActions"] = len(discovered)
        return diagnostics

    for round_index in range(max_steps):
        if time.monotonic() >= deadline:
            diagnostics["rightArrowStopReason"] = "duration_elapsed"
            break
        try:
            page.evaluate("() => { if (document.body) document.body.focus(); }")
        except Exception:
            pass
        for _ in range(presses_per_round):
            if time.monotonic() >= deadline:
                diagnostics["rightArrowStopReason"] = "duration_elapsed"
                break
            try:
                page.keyboard.press("ArrowRight")
                diagnostics["rightArrowPressesSent"] += 1
            except Exception:
                diagnostics["autonomousActionFailureCount"] += 1
        if diagnostics["rightArrowStopReason"] == "duration_elapsed":
            break
        if round_wait_ms > 0:
            page.wait_for_timeout(round_wait_ms)
        current_url = _current_page_url(page)
        diagnostics["rightArrowFinalUrl"] = current_url
        if stop_on_url_change and current_url and initial_url and current_url != initial_url:
            diagnostics["rightArrowUrlChanged"] = True
            diagnostics["rightArrowStopReason"] = "url_changed"
            break
        for url in _scan_dom_image_urls(page):
            add_image(url, "dom")

        steps_executed = round_index + 1
        diagnostics["rightArrowStepsExecuted"] = steps_executed
        current_sequence_length = _dominant_sequence_length(discovered)
        diagnostics["readerBoundarySuspected"] = (
            _detect_reader_boundary(page)
            if _is_true(getattr(args, "smart_stop_use_reader_boundary", "true"))
            else False
        )
        current_network_image_count = (
            int(get_network_image_count()) if callable(get_network_image_count) else 0
        )
        if current_network_image_count > last_network_image_count:
            last_network_growth_step = steps_executed
        last_network_image_count = current_network_image_count

        if current_sequence_length > last_sequence_length:
            stable_rounds = 0
            last_sequence_growth_step = steps_executed
            diagnostics["rightArrowGrowthEvents"] += 1
            diagnostics["sequenceGrowthEvents"] += 1
            diagnostics["rightArrowProductive"] = True
            diagnostics["lastProductiveAction"] = "right_arrow_only"
            productive_action_counts["right_arrow_only"] = (
                productive_action_counts.get("right_arrow_only", 0) + 1
            )
            diagnostics["productiveActions"] = _sorted_productive_actions(
                productive_action_counts
            )
        else:
            stable_rounds += 1

        last_sequence_length = current_sequence_length
        diagnostics["rightArrowSequenceAfter"] = current_sequence_length
        diagnostics["rightArrowStableRounds"] = stable_rounds
        diagnostics["carouselStepsExecuted"] = steps_executed
        diagnostics["autonomousActionsUsed"].append("right_arrow_only")

        if _should_enable_large_sequence_mode(diagnostics, current_sequence_length):
            diagnostics["largeSequenceModeTriggered"] = True
        if diagnostics["largeSequenceModeTriggered"]:
            diagnostics["largeSequenceStepsExecuted"] += 1

        if stop_policy == "duration":
            continue
        if stop_policy == "sequence_stable" and stable_rounds >= stable_rounds_required:
            diagnostics["rightArrowStopReason"] = "right_arrow_sequence_stable"
            diagnostics["autonomousStopReason"] = "right_arrow_sequence_stable"
            diagnostics["stoppedBecauseSequenceStable"] = True
            break
        if stop_policy == "smart" and stable_rounds >= stable_rounds_required:
            smart_reason = _evaluate_smart_stop(
                diagnostics=diagnostics,
                step=steps_executed,
                stable_rounds=stable_rounds,
                current_sequence_length=current_sequence_length,
                last_network_growth_step=last_network_growth_step,
                last_sequence_growth_step=last_sequence_growth_step,
            )
            if smart_reason:
                diagnostics["smartStopTriggered"] = True
                diagnostics["smartStopReason"] = smart_reason
                diagnostics["autonomousStopReason"] = (
                    "right_arrow_sequence_stable"
                    if smart_reason == "smart_sequence_complete"
                    else smart_reason
                )
                diagnostics["rightArrowStopReason"] = diagnostics["autonomousStopReason"]
                diagnostics["stoppedBecauseSequenceStable"] = (
                    smart_reason == "smart_sequence_complete"
                )
                if diagnostics["largeSequenceModeTriggered"]:
                    diagnostics["largeSequenceStopReason"] = smart_reason
                break
    else:
        diagnostics["rightArrowStopReason"] = "max_steps_reached"

    if diagnostics["rightArrowStopReason"] == "none":
        diagnostics["rightArrowStopReason"] = "duration_elapsed"

    diagnostics["autonomousStepsExecuted"] = steps_executed
    diagnostics["imageCountStableRounds"] = stable_rounds
    diagnostics["sequenceStableRounds"] = stable_rounds
    diagnostics["imageCountAfterAutonomousActions"] = len(discovered)
    diagnostics["sequenceLengthAfterExploration"] = _dominant_sequence_length(discovered)
    diagnostics["lastSequenceGrowthStep"] = last_sequence_growth_step

    if diagnostics["largeSequenceModeTriggered"] and diagnostics["largeSequenceStopReason"] == "none":
        diagnostics["largeSequenceStopReason"] = diagnostics["rightArrowStopReason"]
    if stop_policy == "duration":
        diagnostics["autonomousStopReason"] = diagnostics["rightArrowStopReason"]
        diagnostics["stoppedBecauseSequenceStable"] = False
    elif diagnostics["autonomousStopReason"] == "none":
        diagnostics["autonomousStopReason"] = diagnostics["rightArrowStopReason"]
    return diagnostics


def _should_enable_large_sequence_mode(
    diagnostics: dict,
    current_sequence_length: int,
) -> bool:
    return diagnostics["largeSequenceModeEnabled"] and (
        current_sequence_length >= diagnostics["largeSequenceMinLength"]
    )


def _build_action_lookup(actions: list[tuple[str, object]]) -> dict[str, tuple[str, object]]:
    lookup: dict[str, tuple[str, object]] = {}
    for action_name, action in actions:
        lookup.setdefault(action_name, (action_name, action))
    return lookup


def _choose_next_action(
    actions: list[tuple[str, object]],
    action_lookup: dict[str, tuple[str, object]],
    step: int,
    productive_action_counts: dict[str, int],
    large_sequence_mode_triggered: bool,
) -> tuple[str, object]:
    if not large_sequence_mode_triggered or not productive_action_counts:
        return actions[step % len(actions)]
    ranked_actions = _sorted_productive_actions(productive_action_counts)
    if step % 3 != 2:
        return action_lookup[ranked_actions[0]]
    fallback_actions = [
        action_lookup[action_name]
        for action_name in ranked_actions[:3]
        if action_name in action_lookup
    ]
    if not fallback_actions:
        return actions[step % len(actions)]
    return fallback_actions[step % len(fallback_actions)]


def _sorted_productive_actions(productive_action_counts: dict[str, int]) -> list[str]:
    return [
        action_name
        for action_name, _ in sorted(
            productive_action_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def _current_step_wait_ms(args, large_sequence_mode_triggered: bool) -> int:
    if large_sequence_mode_triggered:
        return int(
            getattr(
                args,
                "large_sequence_step_wait_ms",
                getattr(args, "autonomous_step_wait_ms", 700),
            )
        )
    return int(getattr(args, "autonomous_step_wait_ms", 700))


def _build_autonomous_actions(args) -> list[tuple[str, object]]:
    def focus_body(page) -> None:
        page.evaluate("() => { if (document.body) document.body.focus(); }")

    actions = []
    if _is_true(args.autonomous_enable_keyboard):
        actions.extend(
            [
                ("focus_body", focus_body),
                ("keyboard_arrowright", lambda page: page.keyboard.press("ArrowRight")),
                ("keyboard_arrowright", lambda page: page.keyboard.press("ArrowRight")),
            ]
        )
    actions.extend(
        [
            ("window_scroll", lambda page: page.evaluate("window.scrollBy(0, 1000)")),
            ("internal_scroll", _scroll_internal_containers),
        ]
    )
    if _is_true(args.autonomous_enable_mouse_wheel):
        actions.append(("mouse_wheel", lambda page: page.mouse.wheel(0, 1000)))
        actions.append(("horizontal_wheel", lambda page: page.mouse.wheel(1000, 0)))
    if _is_true(args.autonomous_enable_keyboard):
        actions.extend(
            [
                ("keyboard_arrowdown", lambda page: page.keyboard.press("ArrowDown")),
                ("keyboard_pagedown", lambda page: page.keyboard.press("PageDown")),
                ("keyboard_space", lambda page: page.keyboard.press("Space")),
                ("keyboard_end", lambda page: page.keyboard.press("End")),
            ]
        )
    return actions


def _run_reader_readiness(page, args) -> dict:
    diagnostics = _readiness_defaults(args)
    if not _is_true(args.reader_readiness_enabled):
        return diagnostics

    diagnostics["notes"].append(
        "Autonomous capture ran generic reader readiness checks."
    )
    try:
        page.wait_for_timeout(500)
        before_count = _count_visible_overlay_candidates(page)
        if _is_true(args.overlay_dismiss_enabled):
            diagnostics["notes"].append(
                "Autonomous capture attempted safe overlay dismissal."
            )
            for _ in range(args.overlay_max_attempts):
                diagnostics["overlayDismissAttempts"] += 1
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                clicked = _click_safe_overlay_button(page)
                if clicked:
                    diagnostics["overlayDismissedCount"] += 1
                page.wait_for_timeout(250)
        after_count = _count_visible_overlay_candidates(page)
        diagnostics["blockedByOverlaySuspected"] = (
            before_count > 0 and after_count >= before_count
        )
    except Exception:
        diagnostics["notes"].append(
            "Autonomous reader readiness failed; capture continued with available page state."
        )
    return diagnostics


def _readiness_defaults(args) -> dict:
    return {
        "readerReadinessEnabled": _is_true(args.reader_readiness_enabled),
        "overlayDismissEnabled": _is_true(args.overlay_dismiss_enabled),
        "overlayDismissAttempts": 0,
        "overlayDismissedCount": 0,
        "blockedByOverlaySuspected": False,
        "notes": [
            "Autonomous capture used carousel-style generic exploration.",
            "No site-specific selectors or bypass logic were used.",
        ],
    }


def _count_visible_overlay_candidates(page) -> int:
    return int(
        page.evaluate(
            """() => {
                const nodes = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .modal, .overlay, .popup'));
                return nodes.filter((node) => {
                  const rect = node.getBoundingClientRect();
                  const style = window.getComputedStyle(node);
                  return rect.width > 100 && rect.height > 100 && style.visibility !== "hidden" && style.display !== "none";
                }).length;
            }"""
        )
    )


def _click_safe_overlay_button(page) -> bool:
    return bool(
        page.evaluate(
            """(safeTexts, forbiddenTexts) => {
                const candidates = Array.from(document.querySelectorAll('button, [role="button"], a'));
                const normalize = (value) => (value || "").trim().toLowerCase();
                for (const element of candidates) {
                  const text = normalize([
                    element.innerText,
                    element.getAttribute('aria-label'),
                    element.getAttribute('title')
                  ].filter(Boolean).join(' '));
                  if (!text) continue;
                  if (forbiddenTexts.some((term) => text.includes(term))) continue;
                  if (!safeTexts.some((term) => text === term || text.includes(term))) continue;
                  const tag = element.tagName.toLowerCase();
                  if (['input', 'textarea', 'select'].includes(tag)) continue;
                  const rect = element.getBoundingClientRect();
                  if (rect.width <= 0 || rect.height <= 0) continue;
                  element.click();
                  return true;
                }
                return false;
            }""",
            {
                "safeTexts": sorted(SAFE_OVERLAY_TEXTS),
                "forbiddenTexts": sorted(FORBIDDEN_OVERLAY_TEXTS),
            },
        )
    )


def _scroll_internal_containers(page) -> None:
    page.evaluate(
        """() => {
            const preferredTerms = ["reader", "read", "page", "viewer", "scroll", "swiper", "slide", "chapter", "content"];
            const elements = Array.from(document.querySelectorAll("*"))
              .filter((element) => {
                const tag = element.tagName.toLowerCase();
                if (["textarea", "input", "select"].includes(tag)) return false;
                const rect = element.getBoundingClientRect();
                if (rect.width < 200 || rect.height < 200) return false;
                if (element.scrollHeight <= element.clientHeight + 40) return false;
                return true;
              })
              .sort((a, b) => {
                const textA = `${a.id || ""} ${a.className || ""}`.toLowerCase();
                const textB = `${b.id || ""} ${b.className || ""}`.toLowerCase();
                const scoreA = preferredTerms.some((term) => textA.includes(term)) ? 1 : 0;
                const scoreB = preferredTerms.some((term) => textB.includes(term)) ? 1 : 0;
                return scoreB - scoreA;
              })
              .slice(0, 5);
            for (const element of elements) {
              element.scrollTop = Math.min(element.scrollTop + 1000, element.scrollHeight);
            }
        }"""
    )


def _detect_reader_boundary(page) -> bool:
    try:
        return bool(
            page.evaluate(
                """(terms) => {
                    const isVisible = (element) => {
                      const rect = element.getBoundingClientRect();
                      const style = window.getComputedStyle(element);
                      return rect.width > 80 && rect.height > 20 && style.visibility !== "hidden" && style.display !== "none";
                    };
                    const candidates = Array.from(document.querySelectorAll("section, div, aside, main, article"))
                      .filter((element) => isVisible(element))
                      .slice(0, 120);
                    for (const element of candidates) {
                      const markerText = `${element.id || ""} ${element.className || ""} ${element.getAttribute("aria-label") || ""} ${element.textContent || ""}`
                        .trim()
                        .toLowerCase()
                        .slice(0, 400);
                      if (terms.some((term) => markerText.includes(term))) {
                        return true;
                      }
                    }
                    return false;
                }""",
                list(READER_BOUNDARY_TERMS),
            )
        )
    except TypeError:
        return False


def _default_autonomous_diagnostics(args, image_count_before_actions: int) -> dict:
    return {
        "autonomousModeEnabled": args.capture_mode == "autonomous"
        and _is_true(args.autonomous_enabled),
        "autonomousStepsExecuted": 0,
        "autonomousActionsUsed": [],
        "autonomousActionFailureCount": 0,
        "imageCountBeforeAutonomousActions": image_count_before_actions,
        "imageCountAfterAutonomousActions": image_count_before_actions,
        "imageCountStableRounds": 0,
        "readerReadinessEnabled": args.capture_mode == "autonomous"
        and _is_true(getattr(args, "reader_readiness_enabled", "true")),
        "overlayDismissEnabled": args.capture_mode == "autonomous"
        and _is_true(getattr(args, "overlay_dismiss_enabled", "true")),
        "overlayDismissAttempts": 0,
        "overlayDismissedCount": 0,
        "carouselExplorationEnabled": args.capture_mode == "autonomous"
        and _is_true(getattr(args, "carousel_exploration_enabled", "true")),
        "carouselStepsExecuted": 0,
        "sequenceLengthBeforeExploration": 0,
        "sequenceLengthAfterExploration": 0,
        "sequenceStableRounds": 0,
        "smartStopEnabled": getattr(args, "stop_policy", "sequence_stable") == "smart",
        "smartStopMinSteps": int(getattr(args, "smart_stop_min_steps", 20)),
        "smartStopStableRounds": int(
            getattr(args, "smart_stop_stable_rounds", 8)
        ),
        "smartStopMinSequenceLength": int(
            getattr(args, "smart_stop_min_sequence_length", 3)
        ),
        "smartStopTriggered": False,
        "smartStopReason": "none",
        "readerBoundarySuspected": False,
        "readerBoundaryMinSequenceLength": int(
            getattr(
                args,
                "smart_stop_reader_boundary_min_sequence_length",
                20,
            )
        ),
        "readerBoundaryRecentGrowthWindow": int(
            getattr(
                args,
                "smart_stop_reader_boundary_recent_growth_window",
                20,
            )
        ),
        "readerBoundaryStableRoundsRequired": int(
            getattr(
                args,
                "smart_stop_reader_boundary_stable_rounds",
                10,
            )
        ),
        "readerBoundaryBlockedBecauseSequenceTooSmall": False,
        "readerBoundaryBlockedBecauseRecentGrowth": False,
        "readerBoundaryBlockedBecauseNotStableEnough": False,
        "lastSequenceGrowthStep": 0,
        "largeSequenceModeEnabled": _is_true(
            getattr(args, "large_sequence_mode_enabled", "true")
        ),
        "largeSequenceModeTriggered": False,
        "largeSequenceMinLength": int(
            getattr(args, "large_sequence_min_length", 20)
        ),
        "largeSequenceMaxSteps": int(
            getattr(args, "large_sequence_max_steps", 1000)
        ),
        "largeSequenceStableRounds": int(
            getattr(args, "large_sequence_stable_rounds", 25)
        ),
        "largeSequenceStepsExecuted": 0,
        "largeSequenceStopReason": "none",
        "sustainedArrowDownEnabled": _normalized_navigation_strategy(
            getattr(args, "reader_navigation_strategy", "generic")
        )
        != "right_arrow_only"
        and _is_true(getattr(args, "sustained_arrow_down_enabled", "true")),
        "sustainedArrowDownRoundsExecuted": 0,
        "sustainedArrowDownPressesSent": 0,
        "sustainedArrowDownSequenceBefore": 0,
        "sustainedArrowDownSequenceAfter": 0,
        "sustainedArrowDownGrowthEvents": 0,
        "sustainedArrowDownStableRounds": 0,
        "sustainedArrowDownStopReason": "none",
        "sustainedArrowDownProductive": False,
        "readerNavigationStrategy": _normalized_navigation_strategy(
            getattr(args, "reader_navigation_strategy", "generic")
        ),
        "rightArrowNavigationEnabled": _is_true(
            getattr(args, "right_arrow_nav_enabled", "true")
        ),
        "rightArrowStepsExecuted": 0,
        "rightArrowPressesSent": 0,
        "rightArrowSequenceBefore": 0,
        "rightArrowSequenceAfter": 0,
        "rightArrowGrowthEvents": 0,
        "rightArrowStableRounds": 0,
        "rightArrowStopReason": "none",
        "rightArrowProductive": False,
        "rightArrowUrlChanged": False,
        "rightArrowInitialUrl": "",
        "rightArrowFinalUrl": "",
        "forbiddenNavigationKeysUsed": False,
        "productiveActions": [],
        "lastProductiveAction": "",
        "sequenceGrowthEvents": 0,
        "sequenceLengthAtNormalStepLimit": 0,
        "autonomousStopReason": "none",
        "stoppedBecauseSequenceStable": False,
        "blockedByOverlaySuspected": False,
        "notes": [],
    }


def _capture_mode_note(capture_mode: str, navigation_strategy: str = "generic") -> str:
    if capture_mode == "autonomous":
        if navigation_strategy == "right_arrow_only":
            return "Autonomous capture used deterministic ArrowRight-only reader traversal."
        return "Autonomous capture used generic scroll, wheel, and keyboard exploration."
    return "Assisted capture expects manual user interaction in visible browser."


def _stop_policy_note(stop_policy: str) -> str:
    if stop_policy == "smart":
        return "Smart stop used durationSeconds as maximum timeout and may finish earlier when the reader sequence looks complete."
    if stop_policy == "duration":
        return "Capture stayed open until requested duration elapsed."
    return "Capture stopped after the detected page sequence stabilized."


def _session_notes(persistent_enabled: bool) -> list[str]:
    if persistent_enabled:
        return ["Capture used a persistent browser profile."]
    return []


def _is_true(value: str) -> bool:
    return str(value).strip().lower() == "true"


def _normalized_navigation_strategy(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized == "down_arrow_only":
        return "right_arrow_only"
    if normalized in {"generic", "right_arrow_only"}:
        return normalized
    return "generic"


def _current_page_url(page) -> str:
    return str(getattr(page, "url", "") or "")


def _dominant_sequence_length(items: list[dict]) -> int:
    buckets: dict[tuple[str, str], int] = {}
    for item in items:
        key = _numeric_sequence_key(str(item.get("url", "")))
        if key is None:
            continue
        buckets[key] = buckets.get(key, 0) + 1
    return max(buckets.values(), default=0)


def _numeric_sequence_key(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    path = parsed.path
    match = re.search(r"(\d+)(?=\.[A-Za-z0-9]+$)", path)
    if not match:
        return None
    return (path[: match.start()], path[match.end() :])


def _is_safe_overlay_text(text: str) -> bool:
    normalized = text.strip().lower()
    if _is_forbidden_overlay_text(normalized):
        return False
    return any(term == normalized or term in normalized for term in SAFE_OVERLAY_TEXTS)


def _is_forbidden_overlay_text(text: str) -> bool:
    normalized = text.strip().lower()
    return any(term in normalized for term in FORBIDDEN_OVERLAY_TEXTS)


def _looks_like_image_url(url: str) -> bool:
    return bool(IMAGE_EXTENSION_PATTERN.search(url))


def _print_payload(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
