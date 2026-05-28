import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


SUPPORTED_URL_ACCESS_MODES = {"local_only", "allowlist", "open"}
SUPPORTED_HTTP_SCHEMES = {"http", "https"}
SUPPORTED_SSL_VERIFY_MODES = {"default", "truststore", "disabled"}
SUPPORTED_CAPTURE_STOP_POLICIES = {"sequence_stable", "duration", "smart"}
SUPPORTED_BATCH_ANALYSIS_MODES = {
    "static_preview",
    "browser_preview",
    "autonomous_capture",
}


@dataclass
class Settings:
    url_access_mode: str
    allowed_hosts: list[str]
    http_timeout_seconds: float
    default_image_extension: str
    download_base_dir: str
    http_user_agent: str
    ssl_verify_mode: str
    browser_executable_path: str | None
    playwright_browser_channel: str | None
    browser_headless: bool
    browser_user_data_dir: str | None
    browser_persistent_context_enabled: bool
    browser_scroll_enabled: bool
    browser_max_scroll_steps: int
    browser_scroll_wait_ms: int
    browser_initial_wait_ms: int
    browser_scroll_stable_rounds: int
    browser_max_scroll_containers: int
    browser_scroll_delta_px: int
    browser_capture_default_seconds: int
    browser_capture_max_seconds: int
    browser_capture_stop_policy: str
    browser_autonomous_capture_enabled: bool
    browser_autonomous_max_steps: int
    browser_autonomous_step_wait_ms: int
    browser_autonomous_stable_rounds: int
    browser_autonomous_enable_keyboard: bool
    browser_autonomous_enable_mouse_wheel: bool
    browser_reader_readiness_enabled: bool
    browser_overlay_dismiss_enabled: bool
    browser_overlay_max_attempts: int
    browser_carousel_exploration_enabled: bool
    browser_carousel_max_steps: int
    browser_sequence_stable_rounds: int
    browser_smart_stop_min_steps: int
    browser_smart_stop_stable_rounds: int
    browser_smart_stop_min_sequence_length: int
    browser_smart_stop_use_reader_boundary: bool
    browser_smart_stop_reader_boundary_min_sequence_length: int
    browser_smart_stop_reader_boundary_recent_growth_window: int
    browser_smart_stop_reader_boundary_stable_rounds: int
    browser_large_sequence_mode_enabled: bool
    browser_large_sequence_min_length: int
    browser_large_sequence_max_steps: int
    browser_large_sequence_step_wait_ms: int
    browser_large_sequence_extend_while_growing: bool
    browser_large_sequence_stable_rounds: int
    browser_sustained_arrow_down_enabled: bool
    browser_sustained_arrow_down_rounds: int
    browser_sustained_arrow_down_presses_per_round: int
    browser_sustained_arrow_down_press_delay_ms: int
    browser_sustained_arrow_down_round_wait_ms: int
    browser_sustained_arrow_down_stable_rounds: int
    browser_reader_navigation_strategy: str
    browser_adaptive_arrow_enabled: bool
    browser_adaptive_arrow_candidates: list[str]
    browser_adaptive_arrow_probe_rounds: int
    browser_adaptive_arrow_presses_per_round: int
    browser_adaptive_arrow_wait_ms: int
    browser_adaptive_arrow_min_sequence_gain: int
    browser_adaptive_arrow_stop_on_url_change: bool
    browser_adaptive_arrow_max_steps: int
    browser_adaptive_arrow_stable_rounds: int
    browser_adaptive_arrow_presses_per_step: int
    browser_adaptive_arrow_step_wait_ms: int
    browser_right_arrow_nav_enabled: bool
    browser_right_arrow_max_steps: int
    browser_right_arrow_wait_ms: int
    browser_right_arrow_stable_rounds: int
    browser_right_arrow_presses_per_round: int
    browser_right_arrow_stop_on_url_change: bool
    batch_max_urls: int
    batch_report_base_dir: str
    batch_download_base_dir: str


def _parse_allowed_hosts(raw_value: str) -> list[str]:
    return [host.strip().lower() for host in raw_value.split(",") if host.strip()]


def _parse_bool(raw_value: str, default: bool) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_adaptive_arrow_candidates(raw_value: str) -> list[str]:
    allowed = {"ArrowRight", "ArrowDown"}
    candidates = [value.strip() for value in raw_value.split(",") if value.strip()]
    normalized = [value for value in candidates if value in allowed]
    return normalized or ["ArrowRight", "ArrowDown"]


def get_settings() -> Settings:
    url_access_mode = os.getenv("URL_ACCESS_MODE", "local_only").strip().lower()
    if url_access_mode not in SUPPORTED_URL_ACCESS_MODES:
        url_access_mode = "local_only"

    allowed_hosts = _parse_allowed_hosts(
        os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    )

    timeout_raw = os.getenv("HTTP_TIMEOUT_SECONDS", "10").strip()
    try:
        http_timeout_seconds = float(timeout_raw)
    except ValueError:
        http_timeout_seconds = 10.0

    if http_timeout_seconds <= 0:
        http_timeout_seconds = 10.0

    default_image_extension = os.getenv("DEFAULT_IMAGE_EXTENSION", ".jpg").strip()
    if not default_image_extension.startswith("."):
        default_image_extension = f".{default_image_extension}"

    download_base_dir = os.getenv("DOWNLOAD_BASE_DIR", "downloads").strip() or "downloads"
    http_user_agent = (
        os.getenv(
            "HTTP_USER_AGENT",
            "Mozilla/5.0 ChapterDownloaderTool/1.0",
        ).strip()
        or "Mozilla/5.0 ChapterDownloaderTool/1.0"
    )
    ssl_verify_mode = os.getenv("SSL_VERIFY_MODE", "default").strip().lower()
    if ssl_verify_mode not in SUPPORTED_SSL_VERIFY_MODES:
        ssl_verify_mode = "default"
    browser_executable_path = os.getenv("BROWSER_EXECUTABLE_PATH", "").strip() or None
    playwright_browser_channel = (
        os.getenv("PLAYWRIGHT_BROWSER_CHANNEL", "").strip() or None
    )
    browser_headless = _parse_bool(
        os.getenv("BROWSER_HEADLESS", "true"),
        True,
    )
    browser_user_data_dir = os.getenv("BROWSER_USER_DATA_DIR", "").strip() or None
    browser_persistent_context_enabled = _parse_bool(
        os.getenv("BROWSER_PERSISTENT_CONTEXT_ENABLED", "false"),
        False,
    )
    browser_autonomous_capture_enabled = _parse_bool(
        os.getenv("BROWSER_AUTONOMOUS_CAPTURE_ENABLED", "true"),
        True,
    )
    browser_autonomous_enable_keyboard = _parse_bool(
        os.getenv("BROWSER_AUTONOMOUS_ENABLE_KEYBOARD", "true"),
        True,
    )
    browser_autonomous_enable_mouse_wheel = _parse_bool(
        os.getenv("BROWSER_AUTONOMOUS_ENABLE_MOUSE_WHEEL", "true"),
        True,
    )
    browser_reader_readiness_enabled = _parse_bool(
        os.getenv("BROWSER_READER_READINESS_ENABLED", "true"),
        True,
    )
    browser_overlay_dismiss_enabled = _parse_bool(
        os.getenv("BROWSER_OVERLAY_DISMISS_ENABLED", "true"),
        True,
    )
    browser_carousel_exploration_enabled = _parse_bool(
        os.getenv("BROWSER_CAROUSEL_EXPLORATION_ENABLED", "true"),
        True,
    )
    browser_scroll_enabled = _parse_bool(
        os.getenv("BROWSER_SCROLL_ENABLED", "true"),
        True,
    )
    max_scroll_steps_raw = os.getenv("BROWSER_MAX_SCROLL_STEPS", "30").strip()
    scroll_wait_ms_raw = os.getenv("BROWSER_SCROLL_WAIT_MS", "500").strip()
    initial_wait_ms_raw = os.getenv("BROWSER_INITIAL_WAIT_MS", "1200").strip()
    stable_rounds_raw = os.getenv("BROWSER_SCROLL_STABLE_ROUNDS", "3").strip()
    max_scroll_containers_raw = os.getenv("BROWSER_MAX_SCROLL_CONTAINERS", "5").strip()
    scroll_delta_px_raw = os.getenv("BROWSER_SCROLL_DELTA_PX", "1000").strip()
    capture_default_seconds_raw = os.getenv("BROWSER_CAPTURE_DEFAULT_SECONDS", "30").strip()
    capture_max_seconds_raw = os.getenv("BROWSER_CAPTURE_MAX_SECONDS", "120").strip()
    browser_capture_stop_policy = (
        os.getenv("BROWSER_CAPTURE_STOP_POLICY", "sequence_stable").strip().lower()
    )
    if browser_capture_stop_policy not in SUPPORTED_CAPTURE_STOP_POLICIES:
        browser_capture_stop_policy = "sequence_stable"
    autonomous_max_steps_raw = os.getenv("BROWSER_AUTONOMOUS_MAX_STEPS", "60").strip()
    autonomous_step_wait_ms_raw = os.getenv("BROWSER_AUTONOMOUS_STEP_WAIT_MS", "700").strip()
    autonomous_stable_rounds_raw = os.getenv("BROWSER_AUTONOMOUS_STABLE_ROUNDS", "5").strip()
    overlay_max_attempts_raw = os.getenv("BROWSER_OVERLAY_MAX_ATTEMPTS", "3").strip()
    carousel_max_steps_raw = os.getenv("BROWSER_CAROUSEL_MAX_STEPS", "80").strip()
    sequence_stable_rounds_raw = os.getenv("BROWSER_SEQUENCE_STABLE_ROUNDS", "6").strip()
    smart_stop_min_steps_raw = os.getenv("BROWSER_SMART_STOP_MIN_STEPS", "20").strip()
    smart_stop_stable_rounds_raw = os.getenv("BROWSER_SMART_STOP_STABLE_ROUNDS", "8").strip()
    smart_stop_min_sequence_length_raw = os.getenv("BROWSER_SMART_STOP_MIN_SEQUENCE_LENGTH", "3").strip()
    browser_smart_stop_use_reader_boundary = _parse_bool(
        os.getenv("BROWSER_SMART_STOP_USE_READER_BOUNDARY", "true"),
        True,
    )
    smart_stop_reader_boundary_min_sequence_length_raw = os.getenv(
        "BROWSER_SMART_STOP_READER_BOUNDARY_MIN_SEQUENCE_LENGTH",
        "20",
    ).strip()
    smart_stop_reader_boundary_recent_growth_window_raw = os.getenv(
        "BROWSER_SMART_STOP_READER_BOUNDARY_RECENT_GROWTH_WINDOW",
        "20",
    ).strip()
    smart_stop_reader_boundary_stable_rounds_raw = os.getenv(
        "BROWSER_SMART_STOP_READER_BOUNDARY_STABLE_ROUNDS",
        "10",
    ).strip()
    browser_large_sequence_mode_enabled = _parse_bool(
        os.getenv("BROWSER_LARGE_SEQUENCE_MODE_ENABLED", "true"),
        True,
    )
    large_sequence_min_length_raw = os.getenv(
        "BROWSER_LARGE_SEQUENCE_MIN_LENGTH",
        "20",
    ).strip()
    large_sequence_max_steps_raw = os.getenv(
        "BROWSER_LARGE_SEQUENCE_MAX_STEPS",
        "1000",
    ).strip()
    large_sequence_step_wait_ms_raw = os.getenv(
        "BROWSER_LARGE_SEQUENCE_STEP_WAIT_MS",
        "250",
    ).strip()
    browser_large_sequence_extend_while_growing = _parse_bool(
        os.getenv("BROWSER_LARGE_SEQUENCE_EXTEND_WHILE_GROWING", "true"),
        True,
    )
    large_sequence_stable_rounds_raw = os.getenv(
        "BROWSER_LARGE_SEQUENCE_STABLE_ROUNDS",
        "25",
    ).strip()
    browser_sustained_arrow_down_enabled = _parse_bool(
        os.getenv("BROWSER_SUSTAINED_ARROW_DOWN_ENABLED", "true"),
        True,
    )
    browser_reader_navigation_strategy = (
        os.getenv("BROWSER_READER_NAVIGATION_STRATEGY", "generic").strip().lower()
        or "generic"
    )
    if browser_reader_navigation_strategy == "down_arrow_only":
        browser_reader_navigation_strategy = "right_arrow_only"
    if browser_reader_navigation_strategy not in {
        "generic",
        "right_arrow_only",
        "adaptive_arrow",
    }:
        browser_reader_navigation_strategy = "generic"
    browser_adaptive_arrow_enabled = _parse_bool(
        os.getenv("BROWSER_ADAPTIVE_ARROW_ENABLED", "true"),
        True,
    )
    browser_adaptive_arrow_candidates = _parse_adaptive_arrow_candidates(
        os.getenv(
            "BROWSER_ADAPTIVE_ARROW_CANDIDATES",
            "ArrowRight,ArrowDown",
        )
    )
    adaptive_arrow_probe_rounds_raw = os.getenv(
        "BROWSER_ADAPTIVE_ARROW_PROBE_ROUNDS",
        "3",
    ).strip()
    adaptive_arrow_presses_per_round_raw = os.getenv(
        "BROWSER_ADAPTIVE_ARROW_PRESSES_PER_ROUND",
        "3",
    ).strip()
    adaptive_arrow_wait_ms_raw = os.getenv(
        "BROWSER_ADAPTIVE_ARROW_WAIT_MS",
        "300",
    ).strip()
    adaptive_arrow_min_sequence_gain_raw = os.getenv(
        "BROWSER_ADAPTIVE_ARROW_MIN_SEQUENCE_GAIN",
        "1",
    ).strip()
    browser_adaptive_arrow_stop_on_url_change = _parse_bool(
        os.getenv("BROWSER_ADAPTIVE_ARROW_STOP_ON_URL_CHANGE", "true"),
        True,
    )
    adaptive_arrow_max_steps_raw = os.getenv(
        "BROWSER_ADAPTIVE_ARROW_MAX_STEPS",
        "1000",
    ).strip()
    adaptive_arrow_stable_rounds_raw = os.getenv(
        "BROWSER_ADAPTIVE_ARROW_STABLE_ROUNDS",
        "20",
    ).strip()
    adaptive_arrow_presses_per_step_raw = os.getenv(
        "BROWSER_ADAPTIVE_ARROW_PRESSES_PER_STEP",
        "1",
    ).strip()
    adaptive_arrow_step_wait_ms_raw = os.getenv(
        "BROWSER_ADAPTIVE_ARROW_STEP_WAIT_MS",
        "200",
    ).strip()
    browser_right_arrow_nav_enabled = _parse_bool(
        os.getenv(
            "BROWSER_RIGHT_ARROW_NAV_ENABLED",
            os.getenv("BROWSER_DOWN_ONLY_ENABLED", "true"),
        ),
        True,
    )
    right_arrow_max_steps_raw = os.getenv(
        "BROWSER_RIGHT_ARROW_MAX_STEPS",
        os.getenv("BROWSER_DOWN_ONLY_MAX_ROUNDS", "1000"),
    ).strip()
    right_arrow_wait_ms_raw = os.getenv(
        "BROWSER_RIGHT_ARROW_WAIT_MS",
        os.getenv("BROWSER_DOWN_ONLY_ROUND_WAIT_MS", "250"),
    ).strip()
    right_arrow_stable_rounds_raw = os.getenv(
        "BROWSER_RIGHT_ARROW_STABLE_ROUNDS",
        os.getenv("BROWSER_DOWN_ONLY_STABLE_ROUNDS", "25"),
    ).strip()
    right_arrow_presses_per_round_raw = os.getenv(
        "BROWSER_RIGHT_ARROW_PRESSES_PER_ROUND",
        os.getenv("BROWSER_DOWN_ONLY_PRESSES_PER_ROUND", "1"),
    ).strip()
    browser_right_arrow_stop_on_url_change = _parse_bool(
        os.getenv("BROWSER_RIGHT_ARROW_STOP_ON_URL_CHANGE", "true"),
        True,
    )
    sustained_arrow_down_rounds_raw = os.getenv(
        "BROWSER_SUSTAINED_ARROW_DOWN_ROUNDS",
        "120",
    ).strip()
    sustained_arrow_down_presses_per_round_raw = os.getenv(
        "BROWSER_SUSTAINED_ARROW_DOWN_PRESSES_PER_ROUND",
        "10",
    ).strip()
    sustained_arrow_down_press_delay_ms_raw = os.getenv(
        "BROWSER_SUSTAINED_ARROW_DOWN_PRESS_DELAY_MS",
        "40",
    ).strip()
    sustained_arrow_down_round_wait_ms_raw = os.getenv(
        "BROWSER_SUSTAINED_ARROW_DOWN_ROUND_WAIT_MS",
        "250",
    ).strip()
    sustained_arrow_down_stable_rounds_raw = os.getenv(
        "BROWSER_SUSTAINED_ARROW_DOWN_STABLE_ROUNDS",
        "20",
    ).strip()
    batch_max_urls_raw = os.getenv("BATCH_MAX_URLS", "20").strip()
    batch_report_base_dir = (
        os.getenv("BATCH_REPORT_BASE_DIR", "downloads/batches").strip()
        or "downloads/batches"
    )
    batch_download_base_dir = (
        os.getenv("BATCH_DOWNLOAD_BASE_DIR", "").strip()
        or str((Path(download_base_dir) / "batch-downloads").as_posix())
    )
    try:
        browser_max_scroll_steps = int(max_scroll_steps_raw)
    except ValueError:
        browser_max_scroll_steps = 30
    try:
        browser_scroll_wait_ms = int(scroll_wait_ms_raw)
    except ValueError:
        browser_scroll_wait_ms = 500
    try:
        browser_initial_wait_ms = int(initial_wait_ms_raw)
    except ValueError:
        browser_initial_wait_ms = 1200
    try:
        browser_scroll_stable_rounds = int(stable_rounds_raw)
    except ValueError:
        browser_scroll_stable_rounds = 3
    try:
        browser_max_scroll_containers = int(max_scroll_containers_raw)
    except ValueError:
        browser_max_scroll_containers = 5
    try:
        browser_scroll_delta_px = int(scroll_delta_px_raw)
    except ValueError:
        browser_scroll_delta_px = 1000
    try:
        browser_capture_default_seconds = int(capture_default_seconds_raw)
    except ValueError:
        browser_capture_default_seconds = 30
    try:
        browser_capture_max_seconds = int(capture_max_seconds_raw)
    except ValueError:
        browser_capture_max_seconds = 120
    try:
        browser_autonomous_max_steps = int(autonomous_max_steps_raw)
    except ValueError:
        browser_autonomous_max_steps = 60
    try:
        browser_autonomous_step_wait_ms = int(autonomous_step_wait_ms_raw)
    except ValueError:
        browser_autonomous_step_wait_ms = 700
    try:
        browser_autonomous_stable_rounds = int(autonomous_stable_rounds_raw)
    except ValueError:
        browser_autonomous_stable_rounds = 5
    try:
        browser_overlay_max_attempts = int(overlay_max_attempts_raw)
    except ValueError:
        browser_overlay_max_attempts = 3
    try:
        browser_carousel_max_steps = int(carousel_max_steps_raw)
    except ValueError:
        browser_carousel_max_steps = 80
    try:
        browser_sequence_stable_rounds = int(sequence_stable_rounds_raw)
    except ValueError:
        browser_sequence_stable_rounds = 6
    try:
        browser_smart_stop_min_steps = int(smart_stop_min_steps_raw)
    except ValueError:
        browser_smart_stop_min_steps = 20
    try:
        browser_smart_stop_stable_rounds = int(smart_stop_stable_rounds_raw)
    except ValueError:
        browser_smart_stop_stable_rounds = 8
    try:
        browser_smart_stop_min_sequence_length = int(
            smart_stop_min_sequence_length_raw
        )
    except ValueError:
        browser_smart_stop_min_sequence_length = 3
    try:
        browser_smart_stop_reader_boundary_min_sequence_length = int(
            smart_stop_reader_boundary_min_sequence_length_raw
        )
    except ValueError:
        browser_smart_stop_reader_boundary_min_sequence_length = 20
    try:
        browser_smart_stop_reader_boundary_recent_growth_window = int(
            smart_stop_reader_boundary_recent_growth_window_raw
        )
    except ValueError:
        browser_smart_stop_reader_boundary_recent_growth_window = 20
    try:
        browser_smart_stop_reader_boundary_stable_rounds = int(
            smart_stop_reader_boundary_stable_rounds_raw
        )
    except ValueError:
        browser_smart_stop_reader_boundary_stable_rounds = 10
    try:
        browser_large_sequence_min_length = int(large_sequence_min_length_raw)
    except ValueError:
        browser_large_sequence_min_length = 20
    try:
        browser_large_sequence_max_steps = int(large_sequence_max_steps_raw)
    except ValueError:
        browser_large_sequence_max_steps = 1000
    try:
        browser_large_sequence_step_wait_ms = int(large_sequence_step_wait_ms_raw)
    except ValueError:
        browser_large_sequence_step_wait_ms = 250
    try:
        browser_large_sequence_stable_rounds = int(large_sequence_stable_rounds_raw)
    except ValueError:
        browser_large_sequence_stable_rounds = 25
    try:
        browser_sustained_arrow_down_rounds = int(sustained_arrow_down_rounds_raw)
    except ValueError:
        browser_sustained_arrow_down_rounds = 120
    try:
        browser_sustained_arrow_down_presses_per_round = int(
            sustained_arrow_down_presses_per_round_raw
        )
    except ValueError:
        browser_sustained_arrow_down_presses_per_round = 10
    try:
        browser_sustained_arrow_down_press_delay_ms = int(
            sustained_arrow_down_press_delay_ms_raw
        )
    except ValueError:
        browser_sustained_arrow_down_press_delay_ms = 40
    try:
        browser_sustained_arrow_down_round_wait_ms = int(
            sustained_arrow_down_round_wait_ms_raw
        )
    except ValueError:
        browser_sustained_arrow_down_round_wait_ms = 250
    try:
        browser_sustained_arrow_down_stable_rounds = int(
            sustained_arrow_down_stable_rounds_raw
        )
    except ValueError:
        browser_sustained_arrow_down_stable_rounds = 20
    try:
        browser_adaptive_arrow_probe_rounds = int(adaptive_arrow_probe_rounds_raw)
    except ValueError:
        browser_adaptive_arrow_probe_rounds = 3
    try:
        browser_adaptive_arrow_presses_per_round = int(
            adaptive_arrow_presses_per_round_raw
        )
    except ValueError:
        browser_adaptive_arrow_presses_per_round = 3
    try:
        browser_adaptive_arrow_wait_ms = int(adaptive_arrow_wait_ms_raw)
    except ValueError:
        browser_adaptive_arrow_wait_ms = 300
    try:
        browser_adaptive_arrow_min_sequence_gain = int(
            adaptive_arrow_min_sequence_gain_raw
        )
    except ValueError:
        browser_adaptive_arrow_min_sequence_gain = 1
    try:
        browser_adaptive_arrow_max_steps = int(adaptive_arrow_max_steps_raw)
    except ValueError:
        browser_adaptive_arrow_max_steps = 1000
    try:
        browser_adaptive_arrow_stable_rounds = int(adaptive_arrow_stable_rounds_raw)
    except ValueError:
        browser_adaptive_arrow_stable_rounds = 20
    try:
        browser_adaptive_arrow_presses_per_step = int(
            adaptive_arrow_presses_per_step_raw
        )
    except ValueError:
        browser_adaptive_arrow_presses_per_step = 1
    try:
        browser_adaptive_arrow_step_wait_ms = int(adaptive_arrow_step_wait_ms_raw)
    except ValueError:
        browser_adaptive_arrow_step_wait_ms = 200
    try:
        browser_right_arrow_max_steps = int(right_arrow_max_steps_raw)
    except ValueError:
        browser_right_arrow_max_steps = 1000
    try:
        browser_right_arrow_wait_ms = int(right_arrow_wait_ms_raw)
    except ValueError:
        browser_right_arrow_wait_ms = 250
    try:
        browser_right_arrow_stable_rounds = int(right_arrow_stable_rounds_raw)
    except ValueError:
        browser_right_arrow_stable_rounds = 25
    try:
        browser_right_arrow_presses_per_round = int(right_arrow_presses_per_round_raw)
    except ValueError:
        browser_right_arrow_presses_per_round = 1
    try:
        batch_max_urls = int(batch_max_urls_raw)
    except ValueError:
        batch_max_urls = 20

    if browser_max_scroll_steps < 0:
        browser_max_scroll_steps = 30
    if browser_scroll_wait_ms < 0:
        browser_scroll_wait_ms = 500
    if browser_initial_wait_ms < 0:
        browser_initial_wait_ms = 1200
    if browser_scroll_stable_rounds < 0:
        browser_scroll_stable_rounds = 3
    if browser_max_scroll_containers < 0:
        browser_max_scroll_containers = 5
    if browser_scroll_delta_px <= 0:
        browser_scroll_delta_px = 1000
    if browser_capture_max_seconds < 5:
        browser_capture_max_seconds = 120
    if browser_capture_default_seconds < 5:
        browser_capture_default_seconds = 30
    if browser_capture_default_seconds > browser_capture_max_seconds:
        browser_capture_default_seconds = browser_capture_max_seconds
    if browser_autonomous_max_steps < 0:
        browser_autonomous_max_steps = 60
    if browser_autonomous_step_wait_ms < 0:
        browser_autonomous_step_wait_ms = 700
    if browser_autonomous_stable_rounds < 0:
        browser_autonomous_stable_rounds = 5
    if browser_overlay_max_attempts < 0:
        browser_overlay_max_attempts = 3
    if browser_carousel_max_steps < 0:
        browser_carousel_max_steps = 80
    if browser_sequence_stable_rounds < 0:
        browser_sequence_stable_rounds = 6
    if browser_smart_stop_min_steps < 0:
        browser_smart_stop_min_steps = 20
    if browser_smart_stop_stable_rounds < 0:
        browser_smart_stop_stable_rounds = 8
    if browser_smart_stop_min_sequence_length < 1:
        browser_smart_stop_min_sequence_length = 3
    if browser_smart_stop_reader_boundary_min_sequence_length < 1:
        browser_smart_stop_reader_boundary_min_sequence_length = 20
    if browser_smart_stop_reader_boundary_recent_growth_window < 0:
        browser_smart_stop_reader_boundary_recent_growth_window = 20
    if browser_smart_stop_reader_boundary_stable_rounds < 1:
        browser_smart_stop_reader_boundary_stable_rounds = 10
    if browser_large_sequence_min_length < 1:
        browser_large_sequence_min_length = 20
    if browser_large_sequence_max_steps < 1:
        browser_large_sequence_max_steps = 1000
    if browser_large_sequence_step_wait_ms < 0:
        browser_large_sequence_step_wait_ms = 250
    if browser_large_sequence_stable_rounds < 1:
        browser_large_sequence_stable_rounds = 25
    if browser_sustained_arrow_down_rounds < 1:
        browser_sustained_arrow_down_rounds = 120
    if browser_sustained_arrow_down_presses_per_round < 1:
        browser_sustained_arrow_down_presses_per_round = 10
    if browser_sustained_arrow_down_press_delay_ms < 0:
        browser_sustained_arrow_down_press_delay_ms = 40
    if browser_sustained_arrow_down_round_wait_ms < 0:
        browser_sustained_arrow_down_round_wait_ms = 250
    if browser_sustained_arrow_down_stable_rounds < 1:
        browser_sustained_arrow_down_stable_rounds = 20
    if browser_adaptive_arrow_probe_rounds < 1:
        browser_adaptive_arrow_probe_rounds = 3
    if browser_adaptive_arrow_presses_per_round < 1:
        browser_adaptive_arrow_presses_per_round = 3
    if browser_adaptive_arrow_wait_ms < 0:
        browser_adaptive_arrow_wait_ms = 300
    if browser_adaptive_arrow_min_sequence_gain < 1:
        browser_adaptive_arrow_min_sequence_gain = 1
    if browser_adaptive_arrow_max_steps < 1:
        browser_adaptive_arrow_max_steps = 1000
    if browser_adaptive_arrow_stable_rounds < 1:
        browser_adaptive_arrow_stable_rounds = 20
    if browser_adaptive_arrow_presses_per_step < 1:
        browser_adaptive_arrow_presses_per_step = 1
    if browser_adaptive_arrow_step_wait_ms < 0:
        browser_adaptive_arrow_step_wait_ms = 200
    if browser_right_arrow_max_steps < 1:
        browser_right_arrow_max_steps = 1000
    if browser_right_arrow_wait_ms < 0:
        browser_right_arrow_wait_ms = 250
    if browser_right_arrow_stable_rounds < 1:
        browser_right_arrow_stable_rounds = 25
    if browser_right_arrow_presses_per_round < 1:
        browser_right_arrow_presses_per_round = 1
    if batch_max_urls <= 0:
        batch_max_urls = 20

    return Settings(
        url_access_mode=url_access_mode,
        allowed_hosts=allowed_hosts,
        http_timeout_seconds=http_timeout_seconds,
        default_image_extension=default_image_extension.lower(),
        download_base_dir=download_base_dir,
        http_user_agent=http_user_agent,
        ssl_verify_mode=ssl_verify_mode,
        browser_executable_path=browser_executable_path,
        playwright_browser_channel=playwright_browser_channel,
        browser_headless=browser_headless,
        browser_user_data_dir=browser_user_data_dir,
        browser_persistent_context_enabled=browser_persistent_context_enabled,
        browser_scroll_enabled=browser_scroll_enabled,
        browser_max_scroll_steps=browser_max_scroll_steps,
        browser_scroll_wait_ms=browser_scroll_wait_ms,
        browser_initial_wait_ms=browser_initial_wait_ms,
        browser_scroll_stable_rounds=browser_scroll_stable_rounds,
        browser_max_scroll_containers=browser_max_scroll_containers,
        browser_scroll_delta_px=browser_scroll_delta_px,
        browser_capture_default_seconds=browser_capture_default_seconds,
        browser_capture_max_seconds=browser_capture_max_seconds,
        browser_capture_stop_policy=browser_capture_stop_policy,
        browser_autonomous_capture_enabled=browser_autonomous_capture_enabled,
        browser_autonomous_max_steps=browser_autonomous_max_steps,
        browser_autonomous_step_wait_ms=browser_autonomous_step_wait_ms,
        browser_autonomous_stable_rounds=browser_autonomous_stable_rounds,
        browser_autonomous_enable_keyboard=browser_autonomous_enable_keyboard,
        browser_autonomous_enable_mouse_wheel=browser_autonomous_enable_mouse_wheel,
        browser_reader_readiness_enabled=browser_reader_readiness_enabled,
        browser_overlay_dismiss_enabled=browser_overlay_dismiss_enabled,
        browser_overlay_max_attempts=browser_overlay_max_attempts,
        browser_carousel_exploration_enabled=browser_carousel_exploration_enabled,
        browser_carousel_max_steps=browser_carousel_max_steps,
        browser_sequence_stable_rounds=browser_sequence_stable_rounds,
        browser_smart_stop_min_steps=browser_smart_stop_min_steps,
        browser_smart_stop_stable_rounds=browser_smart_stop_stable_rounds,
        browser_smart_stop_min_sequence_length=browser_smart_stop_min_sequence_length,
        browser_smart_stop_use_reader_boundary=browser_smart_stop_use_reader_boundary,
        browser_smart_stop_reader_boundary_min_sequence_length=browser_smart_stop_reader_boundary_min_sequence_length,
        browser_smart_stop_reader_boundary_recent_growth_window=browser_smart_stop_reader_boundary_recent_growth_window,
        browser_smart_stop_reader_boundary_stable_rounds=browser_smart_stop_reader_boundary_stable_rounds,
        browser_large_sequence_mode_enabled=browser_large_sequence_mode_enabled,
        browser_large_sequence_min_length=browser_large_sequence_min_length,
        browser_large_sequence_max_steps=browser_large_sequence_max_steps,
        browser_large_sequence_step_wait_ms=browser_large_sequence_step_wait_ms,
        browser_large_sequence_extend_while_growing=browser_large_sequence_extend_while_growing,
        browser_large_sequence_stable_rounds=browser_large_sequence_stable_rounds,
        browser_sustained_arrow_down_enabled=browser_sustained_arrow_down_enabled,
        browser_sustained_arrow_down_rounds=browser_sustained_arrow_down_rounds,
        browser_sustained_arrow_down_presses_per_round=browser_sustained_arrow_down_presses_per_round,
        browser_sustained_arrow_down_press_delay_ms=browser_sustained_arrow_down_press_delay_ms,
        browser_sustained_arrow_down_round_wait_ms=browser_sustained_arrow_down_round_wait_ms,
        browser_sustained_arrow_down_stable_rounds=browser_sustained_arrow_down_stable_rounds,
        browser_reader_navigation_strategy=browser_reader_navigation_strategy,
        browser_adaptive_arrow_enabled=browser_adaptive_arrow_enabled,
        browser_adaptive_arrow_candidates=browser_adaptive_arrow_candidates,
        browser_adaptive_arrow_probe_rounds=browser_adaptive_arrow_probe_rounds,
        browser_adaptive_arrow_presses_per_round=browser_adaptive_arrow_presses_per_round,
        browser_adaptive_arrow_wait_ms=browser_adaptive_arrow_wait_ms,
        browser_adaptive_arrow_min_sequence_gain=browser_adaptive_arrow_min_sequence_gain,
        browser_adaptive_arrow_stop_on_url_change=browser_adaptive_arrow_stop_on_url_change,
        browser_adaptive_arrow_max_steps=browser_adaptive_arrow_max_steps,
        browser_adaptive_arrow_stable_rounds=browser_adaptive_arrow_stable_rounds,
        browser_adaptive_arrow_presses_per_step=browser_adaptive_arrow_presses_per_step,
        browser_adaptive_arrow_step_wait_ms=browser_adaptive_arrow_step_wait_ms,
        browser_right_arrow_nav_enabled=browser_right_arrow_nav_enabled,
        browser_right_arrow_max_steps=browser_right_arrow_max_steps,
        browser_right_arrow_wait_ms=browser_right_arrow_wait_ms,
        browser_right_arrow_stable_rounds=browser_right_arrow_stable_rounds,
        browser_right_arrow_presses_per_round=browser_right_arrow_presses_per_round,
        browser_right_arrow_stop_on_url_change=browser_right_arrow_stop_on_url_change,
        batch_max_urls=batch_max_urls,
        batch_report_base_dir=batch_report_base_dir,
        batch_download_base_dir=batch_download_base_dir,
    )
