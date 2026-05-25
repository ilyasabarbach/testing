import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout-ms", required=True, type=int)
    parser.add_argument("--settle-wait-ms", required=True, type=int)
    parser.add_argument("--browser-executable-path")
    parser.add_argument("--browser-channel")
    parser.add_argument("--headless", default="true")
    parser.add_argument("--user-data-dir")
    parser.add_argument("--persistent-context-enabled", default="false")
    parser.add_argument("--scroll-enabled", default="true")
    parser.add_argument("--max-scroll-steps", required=True, type=int)
    parser.add_argument("--scroll-wait-ms", required=True, type=int)
    parser.add_argument("--scroll-stable-rounds", required=True, type=int)
    parser.add_argument("--max-scroll-containers", required=True, type=int)
    parser.add_argument("--scroll-delta-px", required=True, type=int)
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
                _print_payload(
                    {
                        "ok": False,
                        "stage": "launch",
                        "message": str(exc),
                    }
                )
                return 0

            page = context.new_page()
            try:
                page.goto(
                    args.url,
                    wait_until="domcontentloaded",
                    timeout=args.timeout_ms,
                )
                page.wait_for_timeout(args.settle_wait_ms)
                scroll_diagnostics = _perform_controlled_scroll(page, args)
            except Exception as exc:
                _print_payload(
                    {
                        "ok": False,
                        "stage": "navigation",
                        "message": str(exc),
                    }
                )
                return 0

            try:
                html = page.content()
                final_url = page.url
            except Exception as exc:
                _print_payload(
                    {
                        "ok": False,
                        "stage": "content",
                        "message": str(exc),
                    }
                )
                return 0

            _print_payload(
                {
                    "ok": True,
                    "html": html,
                    "finalUrl": final_url,
                    "browserHeadless": headless,
                    "browserPersistentContextEnabled": persistent_enabled,
                    "browserUserDataDirConfigured": bool(user_data_dir),
                    "browserSessionMode": (
                        "persistent" if persistent_enabled else "ephemeral"
                    ),
                    "browserSessionNotes": _build_session_notes(
                        persistent_enabled,
                        headless,
                    ),
                    **scroll_diagnostics,
                }
            )
            return 0
    except Exception as exc:
        _print_payload(
            {
                "ok": False,
                "stage": "unknown",
                "message": str(exc),
            }
        )
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


def _print_payload(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def _build_session_notes(persistent_enabled: bool, headless: bool) -> list[str]:
    notes: list[str] = []
    if persistent_enabled:
        notes.append("Browser mode used a persistent browser profile.")
    if not headless:
        notes.append("Browser mode launched a visible browser window for local debugging.")
    return notes


def _perform_controlled_scroll(page, args) -> dict:
    scroll_enabled = str(args.scroll_enabled).strip().lower() == "true"
    diagnostics = {
        "browserScrollEnabled": scroll_enabled,
        "browserScrollSteps": 0,
        "browserScrollHeightBefore": 0,
        "browserScrollHeightAfter": 0,
        "browserLazyLoadWaitMs": args.scroll_wait_ms,
        "browserScrollableContainerCount": 0,
        "browserScrolledContainerCount": 0,
        "browserMouseWheelSteps": 0,
        "browserImageCountBeforeScroll": 0,
        "browserImageCountAfterScroll": 0,
        "browserImageCountStableRounds": 0,
        "browserScrollStrategy": "none",
        "browserScrollNotes": [],
    }

    if not scroll_enabled:
        return diagnostics

    try:
        initial_height = int(page.evaluate("() => document.body.scrollHeight || 0"))
        diagnostics["browserScrollHeightBefore"] = initial_height
        diagnostics["browserImageCountBeforeScroll"] = _count_dom_images(page)
        scroll_state = _scroll_window_with_stabilization(page, args, diagnostics)
        container_diagnostics = _scroll_internal_containers(page, args)
        diagnostics["browserScrollSteps"] = scroll_state["steps"]
        diagnostics["browserScrollHeightAfter"] = scroll_state["height_after"]
        diagnostics["browserMouseWheelSteps"] = scroll_state["mouse_wheel_steps"]
        diagnostics["browserImageCountStableRounds"] = scroll_state["stable_rounds"]
        diagnostics["browserScrollableContainerCount"] = container_diagnostics["container_count"]
        diagnostics["browserScrolledContainerCount"] = container_diagnostics["scrolled_count"]
        diagnostics["browserImageCountAfterScroll"] = _count_dom_images(page)
        diagnostics["browserScrollStrategy"] = (
            "window_and_internal"
            if container_diagnostics["scrolled_count"] > 0
            else "window_only"
        )
        diagnostics["browserScrollNotes"].append(
            "Browser mode scrolled the page to trigger lazy-loaded content."
        )
        diagnostics["browserScrollNotes"].append(
            "Browser mode checked internal scrollable containers."
        )
        diagnostics["browserScrollNotes"].append(
            "Browser mode waited for image count stabilization."
        )
        if diagnostics["browserScrollHeightBefore"] == diagnostics["browserScrollHeightAfter"]:
            diagnostics["browserScrollNotes"].append(
                "Window scrolling was limited because document height did not increase."
            )
        return diagnostics
    except Exception:
        diagnostics["browserScrollNotes"].append(
            "Browser scrolling failed; extraction used the available rendered DOM."
        )
        return diagnostics


def _scroll_window_with_stabilization(page, args, diagnostics: dict) -> dict:
    current_height = diagnostics["browserScrollHeightBefore"]
    current_position = 0
    steps = 0
    stable_rounds = 0
    mouse_wheel_steps = 0
    last_image_count = diagnostics["browserImageCountBeforeScroll"]

    while steps < args.max_scroll_steps and stable_rounds < args.scroll_stable_rounds:
        viewport_height = int(page.evaluate("() => window.innerHeight || 1000"))
        increment = max(viewport_height, args.scroll_delta_px)
        current_position = min(current_position + increment, max(current_height, increment))

        page.evaluate(f"window.scrollTo(0, {current_position})")
        page.mouse.wheel(0, args.scroll_delta_px)
        mouse_wheel_steps += 1
        page.wait_for_timeout(args.scroll_wait_ms)
        steps += 1

        new_height = int(page.evaluate("() => document.body.scrollHeight || 0"))
        new_image_count = _count_dom_images(page)
        if new_image_count > last_image_count:
            stable_rounds = 0
        else:
            stable_rounds += 1

        last_image_count = new_image_count
        if (
            current_position >= new_height
            and new_height <= current_height
            and stable_rounds >= args.scroll_stable_rounds
        ):
            current_height = new_height
            break
        current_height = new_height

    page.evaluate("window.scrollTo(0, 0)")
    return {
        "steps": steps,
        "height_after": current_height,
        "mouse_wheel_steps": mouse_wheel_steps,
        "stable_rounds": stable_rounds,
    }


def _scroll_internal_containers(page, args) -> dict:
    container_state = page.evaluate(
        """(maxContainers) => {
            const preferredTerms = ["reader", "read", "page", "viewer", "scroll", "swiper", "slide", "chapter", "content"];
            const elements = Array.from(document.querySelectorAll("*"));
            const candidates = elements
              .filter((element) => {
                const tag = element.tagName.toLowerCase();
                if (["textarea", "input", "select"].includes(tag)) return false;
                const rect = element.getBoundingClientRect();
                if (rect.width < 200 || rect.height < 200) return false;
                if (element.scrollHeight <= element.clientHeight + 40) return false;
                const text = `${element.id || ""} ${element.className || ""}`.toLowerCase();
                const score = preferredTerms.some((term) => text.includes(term)) ? 1 : 0;
                return score >= 0;
              })
              .sort((a, b) => {
                const textA = `${a.id || ""} ${a.className || ""}`.toLowerCase();
                const textB = `${b.id || ""} ${b.className || ""}`.toLowerCase();
                const scoreA = preferredTerms.some((term) => textA.includes(term)) ? 1 : 0;
                const scoreB = preferredTerms.some((term) => textB.includes(term)) ? 1 : 0;
                return scoreB - scoreA;
              })
              .slice(0, maxContainers);
            return candidates.map((element, index) => ({ index }));
        }"""
        ,
        args.max_scroll_containers,
    )

    scrolled_count = 0
    for container in container_state:
        did_scroll = page.evaluate(
            """(payload) => {
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
                  .slice(0, payload.maxContainers);
                const element = elements[payload.index];
                if (!element) return false;
                element.scrollTop = Math.min(element.scrollTop + payload.delta, element.scrollHeight);
                return true;
            }""",
            {
                "index": container["index"],
                "delta": args.scroll_delta_px,
                "maxContainers": args.max_scroll_containers,
            },
        )
        if did_scroll:
            page.wait_for_timeout(args.scroll_wait_ms)
            scrolled_count += 1

    return {
        "container_count": len(container_state),
        "scrolled_count": scrolled_count,
    }


def _count_dom_images(page) -> int:
    return int(page.evaluate("() => document.querySelectorAll('img').length"))


if __name__ == "__main__":
    raise SystemExit(main())
