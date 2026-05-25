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


def main() -> int:
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
                        _capture_mode_note(args.capture_mode),
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


def _run_autonomous_capture(page, args, add_image, discovered: list[dict]) -> dict:
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
    step = 0
    max_steps = min(args.autonomous_max_steps, getattr(args, "carousel_max_steps", 80))
    stop_policy = getattr(args, "stop_policy", "sequence_stable")

    while (
        time.monotonic() < deadline
        and (
            stop_policy == "duration"
            or (
                step < max_steps
                and stable_rounds < getattr(args, "sequence_stable_rounds", 6)
            )
        )
    ):
        if step < max_steps:
            action_name, action = actions[step % len(actions)]
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

        page.wait_for_timeout(args.autonomous_step_wait_ms)
        for url in _scan_dom_image_urls(page):
            add_image(url, "dom")

        current_sequence_length = _dominant_sequence_length(discovered)
        stable_rounds = (
            stable_rounds + 1
            if current_sequence_length <= last_sequence_length
            else 0
        )
        last_sequence_length = current_sequence_length
        step += 1

    diagnostics["autonomousStepsExecuted"] = min(step, max_steps)
    diagnostics["imageCountStableRounds"] = stable_rounds
    diagnostics["sequenceStableRounds"] = stable_rounds
    diagnostics["imageCountAfterAutonomousActions"] = len(discovered)
    diagnostics["sequenceLengthAfterExploration"] = _dominant_sequence_length(discovered)
    if stop_policy == "duration":
        diagnostics["autonomousStopReason"] = "duration_elapsed"
        diagnostics["stoppedBecauseSequenceStable"] = False
    elif stable_rounds >= getattr(args, "sequence_stable_rounds", 6):
        diagnostics["autonomousStopReason"] = "sequence_stable"
        diagnostics["stoppedBecauseSequenceStable"] = True
    elif step >= max_steps:
        diagnostics["autonomousStopReason"] = "max_steps"
    else:
        diagnostics["autonomousStopReason"] = "duration"
    return diagnostics


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
        "autonomousStopReason": "none",
        "stoppedBecauseSequenceStable": False,
        "blockedByOverlaySuspected": False,
        "notes": [],
    }


def _capture_mode_note(capture_mode: str) -> str:
    if capture_mode == "autonomous":
        return "Autonomous capture used generic scroll, wheel, and keyboard exploration."
    return "Assisted capture expects manual user interaction in visible browser."


def _stop_policy_note(stop_policy: str) -> str:
    if stop_policy == "duration":
        return "Capture stayed open until requested duration elapsed."
    return "Capture stopped after the detected page sequence stabilized."


def _session_notes(persistent_enabled: bool) -> list[str]:
    if persistent_enabled:
        return ["Capture used a persistent browser profile."]
    return []


def _is_true(value: str) -> bool:
    return str(value).strip().lower() == "true"


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
