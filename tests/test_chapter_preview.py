from fastapi.testclient import TestClient
import httpx
import json
from pathlib import Path
import ssl
import subprocess
import sys
from types import SimpleNamespace

from app.main import app
from app.config import get_settings
from app.services.http_client import TargetFetchError


client = TestClient(app)


def test_dotenv_example_exists() -> None:
    assert Path(".env.example").exists()


def test_config_reads_url_access_mode_from_env(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "allowlist")

    settings = get_settings()

    assert settings.url_access_mode == "allowlist"


def test_config_reads_allowed_hosts_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ALLOWED_HOSTS", "example.com,cdn.example.com")

    settings = get_settings()

    assert settings.allowed_hosts == ["example.com", "cdn.example.com"]


def test_config_reads_http_user_agent_from_env(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_USER_AGENT", "TestAgent/2.0")

    settings = get_settings()

    assert settings.http_user_agent == "TestAgent/2.0"


def test_config_reads_browser_executable_path_from_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "BROWSER_EXECUTABLE_PATH",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    )

    settings = get_settings()

    assert (
        settings.browser_executable_path
        == r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    )


def test_config_reads_ssl_verify_mode_from_env(monkeypatch) -> None:
    monkeypatch.setenv("SSL_VERIFY_MODE", "disabled")

    settings = get_settings()

    assert settings.ssl_verify_mode == "disabled"


def test_default_ssl_verify_mode_is_default(monkeypatch) -> None:
    monkeypatch.delenv("SSL_VERIFY_MODE", raising=False)

    settings = get_settings()

    assert settings.ssl_verify_mode == "default"


def test_config_reads_playwright_browser_channel_from_env(monkeypatch) -> None:
    monkeypatch.setenv("PLAYWRIGHT_BROWSER_CHANNEL", "msedge")

    settings = get_settings()

    assert settings.playwright_browser_channel == "msedge"


def test_browser_session_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_HEADLESS", raising=False)
    monkeypatch.delenv("BROWSER_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("BROWSER_PERSISTENT_CONTEXT_ENABLED", raising=False)

    settings = get_settings()

    assert settings.browser_headless is True
    assert settings.browser_user_data_dir is None
    assert settings.browser_persistent_context_enabled is False


def test_config_reads_browser_headless_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_HEADLESS", "false")

    settings = get_settings()

    assert settings.browser_headless is False


def test_config_reads_browser_user_data_dir_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_USER_DATA_DIR", r"C:\temp\profile")

    settings = get_settings()

    assert settings.browser_user_data_dir == r"C:\temp\profile"


def test_config_reads_browser_persistent_context_enabled_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_PERSISTENT_CONTEXT_ENABLED", "true")

    settings = get_settings()

    assert settings.browser_persistent_context_enabled is True


def test_browser_scroll_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_SCROLL_ENABLED", raising=False)
    monkeypatch.delenv("BROWSER_MAX_SCROLL_STEPS", raising=False)
    monkeypatch.delenv("BROWSER_SCROLL_WAIT_MS", raising=False)
    monkeypatch.delenv("BROWSER_INITIAL_WAIT_MS", raising=False)
    monkeypatch.delenv("BROWSER_SCROLL_STABLE_ROUNDS", raising=False)
    monkeypatch.delenv("BROWSER_MAX_SCROLL_CONTAINERS", raising=False)
    monkeypatch.delenv("BROWSER_SCROLL_DELTA_PX", raising=False)

    settings = get_settings()

    assert settings.browser_scroll_enabled is True
    assert settings.browser_max_scroll_steps == 30
    assert settings.browser_scroll_wait_ms == 500
    assert settings.browser_initial_wait_ms == 1200
    assert settings.browser_scroll_stable_rounds == 3
    assert settings.browser_max_scroll_containers == 5
    assert settings.browser_scroll_delta_px == 1000


def test_browser_capture_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_CAPTURE_DEFAULT_SECONDS", raising=False)
    monkeypatch.delenv("BROWSER_CAPTURE_MAX_SECONDS", raising=False)

    settings = get_settings()

    assert settings.browser_capture_default_seconds == 30
    assert settings.browser_capture_max_seconds == 120


def test_config_reads_browser_capture_duration_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_CAPTURE_DEFAULT_SECONDS", "45")
    monkeypatch.setenv("BROWSER_CAPTURE_MAX_SECONDS", "90")

    settings = get_settings()

    assert settings.browser_capture_default_seconds == 45
    assert settings.browser_capture_max_seconds == 90


def test_capture_stop_policy_defaults_to_sequence_stable(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_CAPTURE_STOP_POLICY", raising=False)

    settings = get_settings()

    assert settings.browser_capture_stop_policy == "sequence_stable"


def test_config_reads_capture_stop_policy_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_CAPTURE_STOP_POLICY", "duration")

    settings = get_settings()

    assert settings.browser_capture_stop_policy == "duration"


def test_autonomous_capture_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_AUTONOMOUS_CAPTURE_ENABLED", raising=False)
    monkeypatch.delenv("BROWSER_AUTONOMOUS_MAX_STEPS", raising=False)
    monkeypatch.delenv("BROWSER_AUTONOMOUS_STEP_WAIT_MS", raising=False)
    monkeypatch.delenv("BROWSER_AUTONOMOUS_STABLE_ROUNDS", raising=False)
    monkeypatch.delenv("BROWSER_AUTONOMOUS_ENABLE_KEYBOARD", raising=False)
    monkeypatch.delenv("BROWSER_AUTONOMOUS_ENABLE_MOUSE_WHEEL", raising=False)

    settings = get_settings()

    assert settings.browser_autonomous_capture_enabled is True
    assert settings.browser_autonomous_max_steps == 60
    assert settings.browser_autonomous_step_wait_ms == 700
    assert settings.browser_autonomous_stable_rounds == 5
    assert settings.browser_autonomous_enable_keyboard is True
    assert settings.browser_autonomous_enable_mouse_wheel is True


def test_config_reads_autonomous_capture_values_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_AUTONOMOUS_CAPTURE_ENABLED", "false")
    monkeypatch.setenv("BROWSER_AUTONOMOUS_MAX_STEPS", "12")
    monkeypatch.setenv("BROWSER_AUTONOMOUS_STEP_WAIT_MS", "333")
    monkeypatch.setenv("BROWSER_AUTONOMOUS_STABLE_ROUNDS", "4")
    monkeypatch.setenv("BROWSER_AUTONOMOUS_ENABLE_KEYBOARD", "false")
    monkeypatch.setenv("BROWSER_AUTONOMOUS_ENABLE_MOUSE_WHEEL", "false")

    settings = get_settings()

    assert settings.browser_autonomous_capture_enabled is False
    assert settings.browser_autonomous_max_steps == 12
    assert settings.browser_autonomous_step_wait_ms == 333
    assert settings.browser_autonomous_stable_rounds == 4
    assert settings.browser_autonomous_enable_keyboard is False
    assert settings.browser_autonomous_enable_mouse_wheel is False


def test_reader_readiness_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_READER_READINESS_ENABLED", raising=False)
    monkeypatch.delenv("BROWSER_OVERLAY_DISMISS_ENABLED", raising=False)
    monkeypatch.delenv("BROWSER_OVERLAY_MAX_ATTEMPTS", raising=False)
    monkeypatch.delenv("BROWSER_CAROUSEL_EXPLORATION_ENABLED", raising=False)
    monkeypatch.delenv("BROWSER_CAROUSEL_MAX_STEPS", raising=False)
    monkeypatch.delenv("BROWSER_SEQUENCE_STABLE_ROUNDS", raising=False)

    settings = get_settings()

    assert settings.browser_reader_readiness_enabled is True
    assert settings.browser_overlay_dismiss_enabled is True
    assert settings.browser_overlay_max_attempts == 3
    assert settings.browser_carousel_exploration_enabled is True
    assert settings.browser_carousel_max_steps == 80
    assert settings.browser_sequence_stable_rounds == 6


def test_config_reads_reader_readiness_values_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_READER_READINESS_ENABLED", "false")
    monkeypatch.setenv("BROWSER_OVERLAY_DISMISS_ENABLED", "false")
    monkeypatch.setenv("BROWSER_OVERLAY_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("BROWSER_CAROUSEL_EXPLORATION_ENABLED", "false")
    monkeypatch.setenv("BROWSER_CAROUSEL_MAX_STEPS", "22")
    monkeypatch.setenv("BROWSER_SEQUENCE_STABLE_ROUNDS", "4")

    settings = get_settings()

    assert settings.browser_reader_readiness_enabled is False
    assert settings.browser_overlay_dismiss_enabled is False
    assert settings.browser_overlay_max_attempts == 2
    assert settings.browser_carousel_exploration_enabled is False
    assert settings.browser_carousel_max_steps == 22
    assert settings.browser_sequence_stable_rounds == 4


def test_root_ui_returns_200() -> None:
    response = client.get("/")

    assert response.status_code == 200


def test_root_ui_contains_project_title() -> None:
    response = client.get("/")

    assert "Chapter Image Automation Tool" in response.text
    assert 'id="chapter-url"' in response.text
    assert 'id="inspect-button"' in response.text
    assert 'id="follow-redirects"' in response.text
    assert 'id="preview-diagnostics"' in response.text


def test_preview_ui_javascript_contains_embedded_json_diagnostic_labels() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "JSON Script Count" in response.text
    assert "Embedded JSON Image URL Count" in response.text
    assert "Images From Embedded JSON" in response.text
    assert "Has App Root Shell" in response.text
    assert "Possible API-Driven Page" in response.text


def test_preview_request_accepts_static_render_mode(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return '<html><body><img src="/page-001.jpg"></body></html>'

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html", "renderMode": "static"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/page-001.jpg"
    assert response.json()["diagnostics"]["renderModeUsed"] == "static"


def test_network_inspect_endpoint_exists(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        is_redirect = False
        headers = {"content-type": "text/html", "server": "demo"}
        text = "<html>ok</html>"
        url = "https://example.com/"

    async def fake_get_response(_: str, follow_redirects: bool, request_kind: str = "html"):
        assert follow_redirects is False
        assert request_kind == "html"
        return FakeResponse()

    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr("app.services.network_inspector.get_response", fake_get_response)

    response = client.post(
        "/api/network/inspect",
        json={"url": "https://example.com", "followRedirects": False},
    )

    assert response.status_code == 200


def test_inspect_without_follow_redirects_returns_301(monkeypatch) -> None:
    class FakeResponse:
        status_code = 301
        is_redirect = True
        headers = {
            "location": "https://example.com/",
            "content-type": "text/html; charset=UTF-8",
            "server": "cloudflare",
        }
        text = "Moved permanently"
        url = "http://example.com"

    async def fake_get_response(_: str, follow_redirects: bool, request_kind: str = "html"):
        assert follow_redirects is False
        assert request_kind == "html"
        return FakeResponse()

    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr("app.services.network_inspector.get_response", fake_get_response)

    response = client.post(
        "/api/network/inspect",
        json={"url": "http://example.com", "followRedirects": False},
    )

    assert response.status_code == 200
    assert response.json() == {
        "url": "http://example.com",
        "finalUrl": "http://example.com",
        "statusCode": 301,
        "isRedirect": True,
        "redirectLocation": "https://example.com/",
        "contentType": "text/html; charset=UTF-8",
        "server": "cloudflare",
        "bodyPreview": "Moved permanently",
    }


def test_inspect_with_follow_redirects_returns_final_url(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        is_redirect = False
        headers = {"content-type": "text/html", "server": "cloudflare"}
        text = "OK body"
        url = "https://example.com/"

    async def fake_get_response(_: str, follow_redirects: bool, request_kind: str = "html"):
        assert follow_redirects is True
        assert request_kind == "html"
        return FakeResponse()

    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr("app.services.network_inspector.get_response", fake_get_response)

    response = client.post(
        "/api/network/inspect",
        json={"url": "http://example.com", "followRedirects": True},
    )

    assert response.status_code == 200
    assert response.json()["finalUrl"] == "https://example.com/"
    assert response.json()["statusCode"] == 200


def test_ssl_errors_map_to_clean_502(monkeypatch) -> None:
    async def fake_get_response(_: str, __: bool, request_kind: str = "html"):
        assert request_kind == "html"
        raise TargetFetchError("SSL certificate verification failed for target.", 502)

    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr("app.services.network_inspector.get_response", fake_get_response)

    response = client.post(
        "/api/network/inspect",
        json={"url": "https://example.com", "followRedirects": True},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "SSL certificate verification failed for target."


def test_inspect_timeout_maps_to_504(monkeypatch) -> None:
    async def fake_get_response(_: str, __: bool, request_kind: str = "html"):
        assert request_kind == "html"
        raise TargetFetchError("Target request timed out.", 504)

    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr("app.services.network_inspector.get_response", fake_get_response)

    response = client.post(
        "/api/network/inspect",
        json={"url": "https://example.com", "followRedirects": True},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == "Target request timed out."


def test_url_policy_applies_to_network_inspect(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "local_only")

    response = client.post(
        "/api/network/inspect",
        json={"url": "https://example.com", "followRedirects": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "URL host is not allowed in local_only mode. "
        "Use localhost or 127.0.0.1."
    )


def test_local_only_allows_localhost_and_extracts_images_in_order(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "local_only")
    html = """
    <html>
        <body>
            <img src="http://localhost:3001/images/page-003.jpg">
            <div>text</div>
            <img src="http://localhost:3001/images/page-001.jpg">
            <img src="http://localhost:3001/images/page-002.jpg">
        </body>
    </html>
    """

    async def fake_fetch_text(_: str) -> str:
        return html

    monkeypatch.setattr(
        "app.services.chapter_preview.fetch_text",
        fake_fetch_text,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sourceUrl": "http://localhost:3001/chapter-1.html",
        "imageCount": 3,
        "images": [
            {
                "index": 1,
                "url": "http://localhost:3001/images/page-003.jpg",
                "filename": "001.jpg",
            },
            {
                "index": 2,
                "url": "http://localhost:3001/images/page-001.jpg",
                "filename": "002.jpg",
            },
            {
                "index": 3,
                "url": "http://localhost:3001/images/page-002.jpg",
                "filename": "003.jpg",
            },
        ],
        "diagnostics": {
            "htmlLength": len(html),
            "imgTagCount": 3,
            "imagesFromSrc": 3,
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
            "deduplicatedCount": 0,
            "looksDynamic": False,
            "hasAppRootShell": False,
            "possibleApiDrivenPage": False,
            "renderModeUsed": "static",
            "browserRendered": False,
            "domImageCount": 0,
            "browserFilteredImageCount": 0,
            "browserHeadless": True,
            "browserPersistentContextEnabled": False,
            "browserUserDataDirConfigured": False,
            "browserSessionMode": "ephemeral",
            "browserScrollEnabled": False,
            "browserScrollSteps": 0,
            "browserScrollHeightBefore": 0,
            "browserScrollHeightAfter": 0,
            "browserLazyLoadWaitMs": 0,
            "browserScrollableContainerCount": 0,
            "browserScrolledContainerCount": 0,
            "browserMouseWheelSteps": 0,
            "browserImageCountBeforeScroll": 0,
            "browserImageCountAfterScroll": 0,
            "browserImageCountStableRounds": 0,
            "browserScrollStrategy": "none",
            "browserExtractionNotes": [],
            "notes": [],
        },
    }


def test_local_only_allows_127001_and_resolves_relative_urls(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "local_only")
    html = """
    <html>
        <body>
            <img src="/images/page-001.jpg">
            <img src="pages/page-002.png">
            <img>
        </body>
    </html>
    """

    async def fake_fetch_text(_: str) -> str:
        return html

    monkeypatch.setattr(
        "app.services.chapter_preview.fetch_text",
        fake_fetch_text,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://127.0.0.1:3001/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sourceUrl": "http://127.0.0.1:3001/chapter-1.html",
        "imageCount": 2,
        "images": [
            {
                "index": 1,
                "url": "http://127.0.0.1:3001/images/page-001.jpg",
                "filename": "001.jpg",
            },
            {
                "index": 2,
                "url": "http://127.0.0.1:3001/pages/page-002.png",
                "filename": "002.png",
            },
        ],
        "diagnostics": {
            "htmlLength": len(html),
            "imgTagCount": 3,
            "imagesFromSrc": 2,
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
            "deduplicatedCount": 0,
            "looksDynamic": False,
            "hasAppRootShell": False,
            "possibleApiDrivenPage": False,
            "renderModeUsed": "static",
            "browserRendered": False,
            "domImageCount": 0,
            "browserFilteredImageCount": 0,
            "browserHeadless": True,
            "browserPersistentContextEnabled": False,
            "browserUserDataDirConfigured": False,
            "browserSessionMode": "ephemeral",
            "browserScrollEnabled": False,
            "browserScrollSteps": 0,
            "browserScrollHeightBefore": 0,
            "browserScrollHeightAfter": 0,
            "browserLazyLoadWaitMs": 0,
            "browserScrollableContainerCount": 0,
            "browserScrolledContainerCount": 0,
            "browserMouseWheelSteps": 0,
            "browserImageCountBeforeScroll": 0,
            "browserImageCountAfterScroll": 0,
            "browserImageCountStableRounds": 0,
            "browserScrollStrategy": "none",
            "browserExtractionNotes": [],
            "notes": [],
        },
    }


def test_data_src_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return '<html><body><img data-src="/images/page-001.jpg"></body></html>'

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/images/page-001.jpg"
    assert response.json()["diagnostics"]["imagesFromDataSrc"] == 1


def test_data_lazy_src_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return '<html><body><img data-lazy-src="/images/page-001.jpg"></body></html>'

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/images/page-001.jpg"
    assert response.json()["diagnostics"]["imagesFromDataLazySrc"] == 1


def test_data_original_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return '<html><body><img data-original="/images/page-001.jpg"></body></html>'

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/images/page-001.jpg"
    assert response.json()["diagnostics"]["imagesFromDataOriginal"] == 1


def test_data_url_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return '<html><body><img data-url="/images/page-001.jpg"></body></html>'

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/images/page-001.jpg"
    assert response.json()["diagnostics"]["imagesFromDataUrl"] == 1


def test_img_srcset_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <img srcset="/small.jpg 300w, /large.jpg 1200w">
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/large.jpg"
    assert response.json()["diagnostics"]["imagesFromSrcset"] == 1


def test_source_srcset_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <picture>
                <source srcset="/small.webp 300w, /large.webp 1200w">
            </picture>
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/large.webp"
    assert response.json()["diagnostics"]["imagesFromSourceSrcset"] == 1


def test_meta_image_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><head>
            <meta property="og:image" content="/cover.jpg">
            <meta name="twitter:image" content="/share.jpg">
        </head></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"] == [
        {
            "index": 1,
            "url": "https://example.com/cover.jpg",
            "filename": "001.jpg",
        },
        {
            "index": 2,
            "url": "https://example.com/share.jpg",
            "filename": "002.jpg",
        },
    ]
    assert response.json()["diagnostics"]["imagesFromMeta"] == 2


def test_duplicate_urls_are_deduplicated_and_order_preserved(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <img data-src="/page-001.jpg">
            <img src="/page-001.jpg">
            <img data-lazy-src="/page-002.jpg">
            <img srcset="/small.jpg 320w, /page-002.jpg 1200w">
            <meta property="og:image" content="/cover.jpg">
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert [item["url"] for item in response.json()["images"]] == [
        "https://example.com/page-001.jpg",
        "https://example.com/page-002.jpg",
        "https://example.com/cover.jpg",
    ]
    assert response.json()["diagnostics"]["deduplicatedCount"] == 2


def test_preview_diagnostics_can_mark_page_as_dynamic(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        scripts = "".join("<script>console.log('x')</script>" for _ in range(6))
        return f'<html><body><div id="root"></div>{scripts}</body></html>'

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["diagnostics"]["looksDynamic"] is True
    assert response.json()["diagnostics"]["notes"]


def test_application_json_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <script type="application/json">
              {"pages": ["/json/page-001.jpg", "/json/page-002.png"]}
            </script>
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert [item["url"] for item in response.json()["images"]] == [
        "https://example.com/json/page-001.jpg",
        "https://example.com/json/page-002.png",
    ]
    assert response.json()["diagnostics"]["jsonScriptCount"] == 1
    assert response.json()["diagnostics"]["imagesFromEmbeddedJson"] == 2


def test_application_ld_json_extraction_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <script type="application/ld+json">
              {"image": ["/json/cover.webp", "/json/share.avif"]}
            </script>
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert [item["url"] for item in response.json()["images"]] == [
        "https://example.com/json/cover.webp",
        "https://example.com/json/share.avif",
    ]
    assert response.json()["diagnostics"]["jsonScriptCount"] == 1


def test_json_urls_deduplicate_against_html_urls(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <img src="/page-001.jpg">
            <script type="application/json">
              {"pages": ["/page-001.jpg", "/page-002.jpg"]}
            </script>
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert [item["url"] for item in response.json()["images"]] == [
        "https://example.com/page-001.jpg",
        "https://example.com/page-002.jpg",
    ]
    assert response.json()["diagnostics"]["embeddedImageUrlCount"] == 2
    assert response.json()["diagnostics"]["imagesFromEmbeddedJson"] == 1


def test_json_relative_url_resolution_works(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <script type="application/json">
              {"page": "../images/page-003.gif"}
            </script>
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapters/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/images/page-003.gif"


def test_app_root_shell_and_possible_api_driven_page_heuristics_work(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        scripts = "".join(
            [
                '<script type="application/json">{"image":"/poster.jpg"}</script>',
                "<script>one</script>",
                "<script>two</script>",
            ]
        )
        return f'<html><body><div id="app-root"></div>{scripts}</body></html>'

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["diagnostics"]["hasAppRootShell"] is True
    assert response.json()["diagnostics"]["possibleApiDrivenPage"] is True
    assert response.json()["diagnostics"]["notes"]


def test_zero_direct_html_images_with_embedded_json_returns_json_images(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <div id="app-root"></div>
            <script type="application/json">
              {"pages": ["https://cdn.example.com/page-001.jpg"]}
            </script>
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["imageCount"] == 1
    assert response.json()["images"][0]["url"] == "https://cdn.example.com/page-001.jpg"


def test_embedded_json_notes_warn_about_metadata_assets(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <script type="application/json">
              {"poster": "/poster.jpg"}
            </script>
        </body></html>
        """

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert any(
        "metadata assets" in note.lower()
        for note in response.json()["diagnostics"]["notes"]
    )


def test_browser_mode_returns_clean_error_when_playwright_is_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    completed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(
            {
                "ok": False,
                "stage": "playwright_missing",
                "message": "Playwright package is not installed.",
            }
        ),
        stderr="",
    )
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: completed,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Browser render mode requires Playwright and installed browser binaries."
    )


def test_browser_preview_uses_simplified_launch_and_load_flow(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    browser_executable = tmp_path / "chrome.exe"
    browser_executable.write_text("fake", encoding="utf-8")
    monkeypatch.setenv("BROWSER_EXECUTABLE_PATH", str(browser_executable))
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["run_kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "html": '<html><body><div class="viewer"><img src="/page-001.jpg" alt="Page 1"></div></body></html>',
                    "finalUrl": "http://localhost:3001/chapter-1.html",
                }
            ).encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setattr("app.services.browser_preview.subprocess.run", fake_run)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 200
    assert observed["command"] == [
        sys.executable,
        "-m",
        "app.services.browser_render_worker",
        "--url",
        "http://localhost:3001/chapter-1.html",
        "--timeout-ms",
        "10000",
        "--settle-wait-ms",
        "1200",
        "--headless",
        "true",
        "--persistent-context-enabled",
        "false",
        "--scroll-enabled",
        "true",
        "--max-scroll-steps",
        "30",
        "--scroll-wait-ms",
        "500",
        "--scroll-stable-rounds",
        "3",
        "--max-scroll-containers",
        "5",
        "--scroll-delta-px",
        "1000",
        "--browser-executable-path",
        str(browser_executable),
    ]
    assert observed["run_kwargs"]["timeout"] == 15.0


def test_browser_preview_runs_sync_playwright_work_in_worker_thread(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    observed = {}

    async def fake_to_thread(fn, *args):
        observed["to_thread_called"] = True
        observed["to_thread_target"] = fn.__name__
        return (
            '<html><body><img src="/page-001.jpg"></body></html>',
            "http://localhost:3001/chapter-1.html",
            {
                "browserHeadless": True,
                "browserPersistentContextEnabled": False,
                "browserUserDataDirConfigured": False,
                "browserSessionMode": "ephemeral",
                "browserSessionNotes": [],
                "browserScrollEnabled": True,
                "browserScrollSteps": 1,
                "browserScrollHeightBefore": 1000,
                "browserScrollHeightAfter": 1200,
                "browserLazyLoadWaitMs": 500,
                "browserScrollableContainerCount": 2,
                "browserScrolledContainerCount": 1,
                "browserMouseWheelSteps": 1,
                "browserImageCountBeforeScroll": 1,
                "browserImageCountAfterScroll": 2,
                "browserImageCountStableRounds": 1,
                "browserScrollStrategy": "window_and_internal",
                "browserScrollNotes": [],
            },
        )

    monkeypatch.setattr("app.services.browser_preview.asyncio.to_thread", fake_to_thread)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 200
    assert observed["to_thread_called"] is True
    assert observed["to_thread_target"] == "run_browser_render_worker"


def test_browser_preview_no_custom_windows_event_loop_setup_required() -> None:
    import app.services.browser_preview as browser_preview

    assert not hasattr(browser_preview, "_fetch_rendered_html_sync")
    assert not hasattr(browser_preview, "_fetch_rendered_html_sync_with_loop")
    assert not hasattr(browser_preview, "_create_windows_playwright_loop")
    assert not hasattr(browser_preview, "_close_thread_event_loop")


def test_configured_browser_executable_path_is_preferred_when_present(monkeypatch, tmp_path) -> None:
    browser_executable = tmp_path / "chrome.exe"
    browser_executable.write_text("fake", encoding="utf-8")
    monkeypatch.setenv("BROWSER_EXECUTABLE_PATH", str(browser_executable))
    monkeypatch.delenv("PLAYWRIGHT_BROWSER_CHANNEL", raising=False)

    from app.services.browser_preview import build_browser_worker_command

    command = build_browser_worker_command(
        source_url="http://localhost:3001/chapter-1.html",
        timeout_seconds=10.0,
        browser_executable_path=get_settings().browser_executable_path,
        browser_channel=get_settings().playwright_browser_channel,
        headless=get_settings().browser_headless,
        user_data_dir=get_settings().browser_user_data_dir,
        persistent_context_enabled=get_settings().browser_persistent_context_enabled,
        scroll_enabled=get_settings().browser_scroll_enabled,
        max_scroll_steps=get_settings().browser_max_scroll_steps,
        scroll_wait_ms=get_settings().browser_scroll_wait_ms,
        initial_wait_ms=get_settings().browser_initial_wait_ms,
        stable_rounds=get_settings().browser_scroll_stable_rounds,
        max_scroll_containers=get_settings().browser_max_scroll_containers,
        scroll_delta_px=get_settings().browser_scroll_delta_px,
    )

    assert command[-2:] == ["--browser-executable-path", str(browser_executable)]


def test_blank_browser_channel_is_not_passed_to_worker(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_EXECUTABLE_PATH", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSER_CHANNEL", raising=False)

    from app.services.browser_preview import build_browser_worker_command

    command = build_browser_worker_command(
        source_url="http://localhost:3001/chapter-1.html",
        timeout_seconds=10.0,
        browser_executable_path=None,
        browser_channel=None,
        headless=get_settings().browser_headless,
        user_data_dir=get_settings().browser_user_data_dir,
        persistent_context_enabled=get_settings().browser_persistent_context_enabled,
        scroll_enabled=get_settings().browser_scroll_enabled,
        max_scroll_steps=get_settings().browser_max_scroll_steps,
        scroll_wait_ms=get_settings().browser_scroll_wait_ms,
        initial_wait_ms=get_settings().browser_initial_wait_ms,
        stable_rounds=get_settings().browser_scroll_stable_rounds,
        max_scroll_containers=get_settings().browser_max_scroll_containers,
        scroll_delta_px=get_settings().browser_scroll_delta_px,
    )

    assert "--browser-channel" not in command


def test_worker_receives_scroll_config(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_SCROLL_ENABLED", "false")
    monkeypatch.setenv("BROWSER_MAX_SCROLL_STEPS", "12")
    monkeypatch.setenv("BROWSER_SCROLL_WAIT_MS", "333")
    monkeypatch.setenv("BROWSER_INITIAL_WAIT_MS", "1444")
    monkeypatch.setenv("BROWSER_SCROLL_STABLE_ROUNDS", "4")
    monkeypatch.setenv("BROWSER_MAX_SCROLL_CONTAINERS", "6")
    monkeypatch.setenv("BROWSER_SCROLL_DELTA_PX", "777")

    from app.services.browser_preview import build_browser_worker_command

    settings = get_settings()
    command = build_browser_worker_command(
        source_url="http://localhost:3001/chapter-1.html",
        timeout_seconds=10.0,
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

    assert "--scroll-enabled" in command
    assert "false" in command
    assert "--max-scroll-steps" in command
    assert "12" in command
    assert "--scroll-wait-ms" in command
    assert "333" in command
    assert "--settle-wait-ms" in command
    assert "1444" in command
    assert "--scroll-stable-rounds" in command
    assert "4" in command
    assert "--max-scroll-containers" in command
    assert "6" in command
    assert "--scroll-delta-px" in command
    assert "777" in command


def test_worker_receives_browser_session_config(monkeypatch) -> None:
    monkeypatch.setenv("BROWSER_HEADLESS", "false")
    monkeypatch.setenv("BROWSER_USER_DATA_DIR", r"C:\profiles\reader")
    monkeypatch.setenv("BROWSER_PERSISTENT_CONTEXT_ENABLED", "true")

    from app.services.browser_preview import build_browser_worker_command

    settings = get_settings()
    command = build_browser_worker_command(
        source_url="http://localhost:3001/chapter-1.html",
        timeout_seconds=10.0,
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

    assert "--headless" in command
    assert "false" in command
    assert "--persistent-context-enabled" in command
    assert "--user-data-dir" in command
    assert r"C:\profiles\reader" in command


def test_blank_browser_user_data_dir_is_not_passed_to_worker(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER_USER_DATA_DIR", raising=False)

    from app.services.browser_preview import build_browser_worker_command

    settings = get_settings()
    command = build_browser_worker_command(
        source_url="http://localhost:3001/chapter-1.html",
        timeout_seconds=10.0,
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

    assert "--user-data-dir" not in command


def test_persistent_browser_context_requires_user_data_dir(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv("BROWSER_PERSISTENT_CONTEXT_ENABLED", "true")
    monkeypatch.delenv("BROWSER_USER_DATA_DIR", raising=False)
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": False,
                    "stage": "launch",
                    "message": "Persistent browser context requires BROWSER_USER_DATA_DIR.",
                }
            ).encode("utf-8"),
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Persistent browser context requires BROWSER_USER_DATA_DIR."
    )


def test_persistent_browser_launch_failure_maps_to_clean_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv("BROWSER_PERSISTENT_CONTEXT_ENABLED", "true")
    monkeypatch.setenv("BROWSER_USER_DATA_DIR", r"C:\profiles\reader")
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": False,
                    "stage": "launch",
                    "message": "launch_persistent_context failed",
                }
            ).encode("utf-8"),
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser persistent context could not be launched."


def test_worker_scroll_failure_does_not_crash(monkeypatch) -> None:
    from app.services.browser_render_worker import _perform_controlled_scroll

    class FakePage:
        def evaluate(self, script: str):
            raise RuntimeError("scroll fail")

    args = SimpleNamespace(
        scroll_enabled="true",
        max_scroll_steps=5,
        scroll_wait_ms=500,
    )

    diagnostics = _perform_controlled_scroll(FakePage(), args)

    assert diagnostics["browserScrollEnabled"] is True
    assert diagnostics["browserScrollSteps"] == 0
    assert diagnostics["browserScrollNotes"]


def test_internal_scrollable_container_detection_logic() -> None:
    from app.services.browser_render_worker import _scroll_internal_containers

    class FakePage:
        def __init__(self):
            self.calls = 0

        def evaluate(self, script: str, payload=None):
            self.calls += 1
            if self.calls == 1:
                return [{"index": 0}, {"index": 1}]
            return True

        def wait_for_timeout(self, milliseconds: int) -> None:
            return None

    args = SimpleNamespace(
        max_scroll_containers=5,
        scroll_delta_px=1000,
        scroll_wait_ms=500,
    )

    diagnostics = _scroll_internal_containers(FakePage(), args)

    assert diagnostics["container_count"] == 2
    assert diagnostics["scrolled_count"] == 2


def test_image_count_stabilization_logic() -> None:
    from app.services.browser_render_worker import _scroll_window_with_stabilization

    class FakeMouse:
        def wheel(self, dx: int, dy: int) -> None:
            return None

    class FakePage:
        def __init__(self):
            self.mouse = FakeMouse()
            self.image_counts = [2, 3, 3, 3]
            self.height_counts = [2000, 2500, 2500, 2500]

        def evaluate(self, script: str):
            if "window.innerHeight" in script:
                return 900
            if "document.querySelectorAll('img').length" in script:
                return self.image_counts.pop(0)
            if "document.body.scrollHeight" in script:
                return self.height_counts.pop(0)
            return None

        def wait_for_timeout(self, milliseconds: int) -> None:
            return None

    args = SimpleNamespace(
        max_scroll_steps=10,
        scroll_stable_rounds=2,
        scroll_delta_px=1000,
        scroll_wait_ms=500,
    )
    diagnostics = {
        "browserScrollHeightBefore": 2000,
        "browserImageCountBeforeScroll": 2,
    }

    state = _scroll_window_with_stabilization(FakePage(), args, diagnostics)

    assert state["steps"] >= 2
    assert state["stable_rounds"] == 2


def test_missing_configured_browser_executable_path_returns_clean_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv(
        "BROWSER_EXECUTABLE_PATH",
        r"C:\missing\browser.exe",
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Configured browser executable was not found."


def test_browser_launch_failure_maps_to_clean_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.delenv("BROWSER_EXECUTABLE_PATH", raising=False)
    completed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(
            {"ok": False, "stage": "launch", "message": "launch boom"}
        ).encode("utf-8"),
        stderr=b"worker log",
    )
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: completed,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render mode could not launch the browser."


def test_browser_launch_not_implemented_error_maps_to_clean_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.delenv("BROWSER_EXECUTABLE_PATH", raising=False)
    completed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(
            {
                "ok": False,
                "stage": "launch",
                "message": "subprocess transport unavailable",
            }
        ).encode("utf-8"),
        stderr=b"worker log",
    )
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: completed,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render mode could not launch the browser."


def test_browser_navigation_failure_maps_to_clean_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.delenv("BROWSER_EXECUTABLE_PATH", raising=False)
    completed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(
            {"ok": False, "stage": "navigation", "message": "goto boom"}
        ).encode("utf-8"),
        stderr=b"worker log",
    )
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: completed,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render mode failed during page navigation."


def test_browser_extraction_failure_maps_to_clean_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.delenv("BROWSER_EXECUTABLE_PATH", raising=False)
    completed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(
            {"ok": False, "stage": "content", "message": "content boom"}
        ).encode("utf-8"),
        stderr=b"worker log",
    )
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: completed,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Browser render mode failed while extracting rendered HTML."
    )


def test_browser_worker_invalid_json_maps_to_clean_worker_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout=b"not-json",
            stderr=b"traceback",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render worker failed."


def test_browser_worker_stdout_bytes_valid_json_parses_successfully(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "html": '<html><body><img src="/page-001.jpg" alt="Page 1"></body></html>',
                    "finalUrl": "http://localhost:3001/chapter-1.html",
                }
            ).encode("utf-8"),
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 200
    assert response.json()["imageCount"] == 1


def test_browser_worker_stdout_invalid_utf8_bytes_does_not_crash(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=b'{"ok":false,"stage":"unknown","message":"bad\xb7"}',
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render worker failed."


def test_browser_worker_stderr_invalid_utf8_bytes_does_not_crash(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {"ok": False, "stage": "launch", "message": "launch boom"}
            ).encode("utf-8"),
            stderr=b"bad\xb7stderr",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render mode could not launch the browser."


def test_browser_worker_stdout_none_maps_to_clean_worker_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout=None,
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render worker failed."


def test_browser_worker_stdout_empty_maps_to_clean_worker_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout=b"",
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render worker failed."


def test_browser_worker_non_zero_exit_with_valid_json_failure_still_maps_by_stage(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_preview.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout=json.dumps(
                {"ok": False, "stage": "navigation", "message": "goto boom"}
            ).encode("utf-8"),
            stderr=b"worker log",
        ),
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render mode failed during page navigation."


def test_browser_worker_timeout_maps_to_clean_worker_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="python", timeout=15)

    monkeypatch.setattr("app.services.browser_preview.subprocess.run", fake_run)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "http://localhost:3001/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser render worker failed."


def test_capture_endpoint_exists_and_maps_worker_success(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [
                        {
                            "url": "https://example.com/images/01.webp",
                            "source": "network",
                        }
                    ],
                    "networkImageCount": 1,
                    "domImageCount": 0,
                    "deduplicatedCount": 0,
                    "notes": ["manual capture"],
                }
            ).encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setattr("app.services.browser_capture.subprocess.run", fake_run)

    response = client.post(
        "/api/chapters/capture",
        json={"url": "https://example.com/chapter-1.html", "durationSeconds": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sourceUrl"] == "https://example.com/chapter-1.html"
    assert payload["captureDurationSeconds"] == 30
    assert payload["imageCount"] == 1
    assert payload["images"][0] == {
        "index": 1,
        "url": "https://example.com/images/01.webp",
        "filename": "001.webp",
        "source": "network",
    }
    assert payload["diagnostics"]["captureMode"] == "assisted"
    assert payload["diagnostics"]["manualInteractionExpected"] is True
    assert "--headless" in observed["command"]
    assert "false" in observed["command"]
    assert observed["kwargs"]["timeout"] == 50.0


def test_capture_mode_defaults_to_assisted(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [],
                    "networkImageCount": 0,
                    "domImageCount": 0,
                    "deduplicatedCount": 0,
                    "notes": [],
                }
            ).encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setattr("app.services.browser_capture.subprocess.run", fake_run)

    response = client.post(
        "/api/chapters/capture",
        json={"url": "https://example.com/chapter-1.html", "durationSeconds": 30},
    )

    assert response.status_code == 200
    assert response.json()["diagnostics"]["captureMode"] == "assisted"
    capture_mode_index = observed["command"].index("--capture-mode")
    assert observed["command"][capture_mode_index + 1] == "assisted"


def test_autonomous_capture_request_is_accepted(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [
                        {
                            "url": "https://example.com/pages/01.webp",
                            "source": "network",
                        }
                    ],
                    "networkImageCount": 1,
                    "domImageCount": 1,
                    "deduplicatedCount": 0,
                    "autonomousModeEnabled": True,
                    "autonomousStepsExecuted": 4,
                    "autonomousActionsUsed": ["window_scroll", "keyboard_arrowright"],
                    "imageCountBeforeAutonomousActions": 1,
                    "imageCountAfterAutonomousActions": 3,
                    "imageCountStableRounds": 2,
                    "notes": ["autonomous capture"],
                }
            ).encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setattr("app.services.browser_capture.subprocess.run", fake_run)

    response = client.post(
        "/api/chapters/capture",
        json={
            "url": "https://example.com/chapter-1.html",
            "durationSeconds": 60,
            "captureMode": "autonomous",
        },
    )

    assert response.status_code == 200
    diagnostics = response.json()["diagnostics"]
    assert diagnostics["captureMode"] == "autonomous"
    assert diagnostics["manualInteractionExpected"] is False
    assert diagnostics["autonomousModeEnabled"] is True
    assert diagnostics["autonomousStepsExecuted"] == 4
    assert diagnostics["autonomousActionsUsed"] == ["window_scroll", "keyboard_arrowright"]
    assert diagnostics["imageCountBeforeAutonomousActions"] == 1
    assert diagnostics["imageCountAfterAutonomousActions"] == 3
    assert diagnostics["imageCountStableRounds"] == 2
    assert diagnostics["observedImageCount"] == 1
    assert diagnostics["selectedImageCount"] == 1
    capture_mode_index = observed["command"].index("--capture-mode")
    assert observed["command"][capture_mode_index + 1] == "autonomous"
    assert "--autonomous-max-steps" in observed["command"]


def test_capture_stop_policy_duration_is_passed_to_worker(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [],
                    "networkImageCount": 0,
                    "domImageCount": 0,
                    "deduplicatedCount": 0,
                    "captureStopPolicy": "duration",
                    "captureRequestedDurationSeconds": 60,
                    "captureActualDurationSeconds": 60.0,
                    "autonomousStopReason": "duration_elapsed",
                    "stoppedBecauseSequenceStable": False,
                    "notes": ["Capture stayed open until requested duration elapsed."],
                }
            ).encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setattr("app.services.browser_capture.subprocess.run", fake_run)

    response = client.post(
        "/api/chapters/capture",
        json={
            "url": "https://example.com/chapter-1.html",
            "durationSeconds": 60,
            "captureMode": "autonomous",
            "stopPolicy": "duration",
        },
    )

    diagnostics = response.json()["diagnostics"]
    stop_policy_index = observed["command"].index("--stop-policy")

    assert response.status_code == 200
    assert observed["command"][stop_policy_index + 1] == "duration"
    assert diagnostics["captureStopPolicy"] == "duration"
    assert diagnostics["captureRequestedDurationSeconds"] == 60
    assert diagnostics["captureActualDurationSeconds"] == 60.0
    assert diagnostics["autonomousStopReason"] == "duration_elapsed"
    assert diagnostics["stoppedBecauseSequenceStable"] is False


def test_duration_policy_does_not_stop_early_on_sequence_stability(monkeypatch) -> None:
    from app.services.browser_capture_worker import _run_autonomous_capture

    class FakeKeyboard:
        def press(self, key: str) -> None:
            return None

    class FakeMouse:
        def wheel(self, dx: int, dy: int) -> None:
            return None

    class FakePage:
        def __init__(self):
            self.keyboard = FakeKeyboard()
            self.mouse = FakeMouse()

        def evaluate(self, script: str):
            if "querySelectorAll(\"img\")" in script:
                return ["https://example.com/pages/01.webp"]
            return None

        def wait_for_timeout(self, milliseconds: int) -> None:
            return None

    ticks = iter([0, 0, 1, 2, 3, 4])
    monkeypatch.setattr(
        "app.services.browser_capture_worker.time.monotonic",
        lambda: next(ticks),
    )

    args = SimpleNamespace(
        capture_mode="autonomous",
        stop_policy="duration",
        autonomous_enabled="true",
        autonomous_max_steps=1,
        autonomous_step_wait_ms=0,
        autonomous_stable_rounds=1,
        autonomous_enable_keyboard="true",
        autonomous_enable_mouse_wheel="true",
        carousel_exploration_enabled="true",
        carousel_max_steps=1,
        sequence_stable_rounds=1,
        duration_seconds=3,
    )
    discovered = []
    seen = set()

    def add_image(url: str, source: str) -> None:
        if url in seen:
            return
        seen.add(url)
        discovered.append({"url": url, "source": source})

    diagnostics = _run_autonomous_capture(FakePage(), args, add_image, discovered)

    assert diagnostics["autonomousStopReason"] == "duration_elapsed"
    assert diagnostics["stoppedBecauseSequenceStable"] is False
    assert diagnostics["sequenceStableRounds"] >= 1


def test_capture_diagnostics_include_session_fields(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv("BROWSER_HEADLESS", "false")
    monkeypatch.setenv("BROWSER_PERSISTENT_CONTEXT_ENABLED", "true")
    monkeypatch.setenv("BROWSER_USER_DATA_DIR", r"C:\profiles\reader")
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [],
                    "networkImageCount": 0,
                    "domImageCount": 0,
                    "deduplicatedCount": 0,
                    "browserHeadless": False,
                    "browserPersistentContextEnabled": True,
                    "browserUserDataDirConfigured": True,
                    "browserSessionMode": "persistent",
                    "captureStopPolicy": "sequence_stable",
                    "captureRequestedDurationSeconds": 30,
                    "captureActualDurationSeconds": 12.5,
                    "stoppedBecauseSequenceStable": True,
                    "notes": ["Capture used a persistent browser profile."],
                }
            ).encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setattr("app.services.browser_capture.subprocess.run", fake_run)

    response = client.post(
        "/api/chapters/capture",
        json={
            "url": "https://example.com/chapter-1.html",
            "durationSeconds": 30,
            "captureMode": "autonomous",
        },
    )

    diagnostics = response.json()["diagnostics"]

    assert response.status_code == 200
    assert diagnostics["browserHeadless"] is False
    assert diagnostics["browserPersistentContextEnabled"] is True
    assert diagnostics["browserUserDataDirConfigured"] is True
    assert diagnostics["browserSessionMode"] == "persistent"
    assert diagnostics["captureStopPolicy"] == "sequence_stable"
    assert diagnostics["captureActualDurationSeconds"] == 12.5
    assert diagnostics["stoppedBecauseSequenceStable"] is True
    assert "--user-data-dir" in observed["command"]
    assert r"C:\profiles\reader" in observed["command"]


def test_persistent_capture_mode_without_user_data_dir_returns_clean_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv("BROWSER_PERSISTENT_CONTEXT_ENABLED", "true")
    monkeypatch.delenv("BROWSER_USER_DATA_DIR", raising=False)
    monkeypatch.setattr(
        "app.services.browser_capture.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": False,
                    "stage": "launch",
                    "message": "Persistent browser context requires BROWSER_USER_DATA_DIR.",
                }
            ).encode("utf-8"),
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/capture",
        json={
            "url": "https://example.com/chapter-1.html",
            "durationSeconds": 30,
            "captureMode": "autonomous",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Persistent browser context requires BROWSER_USER_DATA_DIR."
    )


def test_worker_autonomous_actions_are_invoked_with_stabilization() -> None:
    from app.services.browser_capture_worker import _run_autonomous_capture

    class FakeMouse:
        def wheel(self, dx: int, dy: int) -> None:
            return None

    class FakeKeyboard:
        def press(self, key: str) -> None:
            return None

    class FakePage:
        def __init__(self):
            self.mouse = FakeMouse()
            self.keyboard = FakeKeyboard()
            self.scan_count = 0

        def evaluate(self, script: str):
            if "querySelectorAll(\"img\")" in script:
                self.scan_count += 1
                if self.scan_count == 1:
                    return ["https://example.com/pages/01.webp"]
                return ["https://example.com/pages/01.webp"]
            return None

        def wait_for_timeout(self, milliseconds: int) -> None:
            return None

    args = SimpleNamespace(
        capture_mode="autonomous",
        autonomous_enabled="true",
        autonomous_max_steps=5,
        autonomous_step_wait_ms=0,
        autonomous_stable_rounds=2,
        autonomous_enable_keyboard="true",
        autonomous_enable_mouse_wheel="true",
        duration_seconds=30,
    )
    discovered = []
    seen = set()

    def add_image(url: str, source: str) -> None:
        if url in seen:
            return
        seen.add(url)
        discovered.append({"url": url, "source": source})

    diagnostics = _run_autonomous_capture(FakePage(), args, add_image, discovered)

    assert diagnostics["autonomousModeEnabled"] is True
    assert diagnostics["autonomousStepsExecuted"] <= args.autonomous_max_steps
    assert diagnostics["imageCountStableRounds"] >= 2
    assert diagnostics["autonomousActionsUsed"]


def test_safe_overlay_text_matching() -> None:
    from app.services.browser_capture_worker import _is_safe_overlay_text

    assert _is_safe_overlay_text("Close") is True
    assert _is_safe_overlay_text("Got it") is True
    assert _is_safe_overlay_text("Start reading") is True
    assert _is_safe_overlay_text("Ne plus afficher") is True


def test_forbidden_overlay_text_is_not_clicked() -> None:
    from app.services.browser_capture_worker import (
        _is_forbidden_overlay_text,
        _is_safe_overlay_text,
    )

    assert _is_forbidden_overlay_text("Sign in to continue") is True
    assert _is_forbidden_overlay_text("Verify captcha") is True
    assert _is_forbidden_overlay_text("Subscribe now") is True
    assert _is_safe_overlay_text("Continue to sign in") is False


def test_reader_readiness_enforces_overlay_max_attempts() -> None:
    from app.services.browser_capture_worker import _run_reader_readiness

    class FakeKeyboard:
        def __init__(self):
            self.presses = []

        def press(self, key: str) -> None:
            self.presses.append(key)

    class FakePage:
        def __init__(self):
            self.keyboard = FakeKeyboard()

        def wait_for_timeout(self, milliseconds: int) -> None:
            return None

        def evaluate(self, script: str, payload=None):
            if "querySelectorAll('[role=\"dialog\"]" in script:
                return 1
            return False

    args = SimpleNamespace(
        reader_readiness_enabled="true",
        overlay_dismiss_enabled="true",
        overlay_max_attempts=2,
    )

    diagnostics = _run_reader_readiness(FakePage(), args)

    assert diagnostics["overlayDismissAttempts"] == 2
    assert diagnostics["overlayDismissedCount"] == 0
    assert diagnostics["blockedByOverlaySuspected"] is True


def test_reader_readiness_failure_does_not_crash() -> None:
    from app.services.browser_capture_worker import _run_reader_readiness

    class FakePage:
        def wait_for_timeout(self, milliseconds: int) -> None:
            raise RuntimeError("readiness fail")

    args = SimpleNamespace(
        reader_readiness_enabled="true",
        overlay_dismiss_enabled="true",
        overlay_max_attempts=3,
    )

    diagnostics = _run_reader_readiness(FakePage(), args)

    assert diagnostics["readerReadinessEnabled"] is True
    assert any("readiness failed" in note for note in diagnostics["notes"])


def test_carousel_exploration_actions_invoked_under_mocked_worker() -> None:
    from app.services.browser_capture_worker import _run_autonomous_capture

    class FakeMouse:
        def wheel(self, dx: int, dy: int) -> None:
            return None

    class FakeKeyboard:
        def __init__(self):
            self.keys = []

        def press(self, key: str) -> None:
            self.keys.append(key)

    class FakePage:
        def __init__(self):
            self.mouse = FakeMouse()
            self.keyboard = FakeKeyboard()

        def evaluate(self, script: str):
            if "querySelectorAll(\"img\")" in script:
                return ["https://example.com/pages/01.webp"]
            return None

        def wait_for_timeout(self, milliseconds: int) -> None:
            return None

    args = SimpleNamespace(
        capture_mode="autonomous",
        autonomous_enabled="true",
        autonomous_max_steps=8,
        autonomous_step_wait_ms=0,
        autonomous_stable_rounds=5,
        autonomous_enable_keyboard="true",
        autonomous_enable_mouse_wheel="true",
        carousel_exploration_enabled="true",
        carousel_max_steps=8,
        sequence_stable_rounds=4,
        duration_seconds=30,
    )
    page = FakePage()
    discovered = []
    seen = set()

    def add_image(url: str, source: str) -> None:
        if url in seen:
            return
        seen.add(url)
        discovered.append({"url": url, "source": source})

    diagnostics = _run_autonomous_capture(page, args, add_image, discovered)

    assert diagnostics["carouselExplorationEnabled"] is True
    assert diagnostics["carouselStepsExecuted"] > 0
    assert any(action.startswith("keyboard_") for action in diagnostics["autonomousActionsUsed"])


def test_dominant_sequence_length_stabilization_works() -> None:
    from app.services.browser_capture_worker import _dominant_sequence_length

    items = [
        {"url": "https://example.com/pages/01.webp", "source": "network"},
        {"url": "https://example.com/pages/02.webp", "source": "network"},
        {"url": "https://example.com/assets/logo-01.png", "source": "dom"},
    ]

    assert _dominant_sequence_length(items) == 2


def test_autonomous_capture_diagnostics_include_reader_fields(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_capture.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [
                        {"url": "https://example.com/pages/01.webp", "source": "network"},
                        {"url": "https://example.com/pages/02.webp", "source": "network"},
                        {"url": "https://example.com/pages/03.webp", "source": "network"},
                    ],
                    "networkImageCount": 3,
                    "domImageCount": 1,
                    "deduplicatedCount": 0,
                    "autonomousModeEnabled": True,
                    "autonomousStepsExecuted": 10,
                    "autonomousActionsUsed": ["keyboard_arrowright"],
                    "imageCountBeforeAutonomousActions": 1,
                    "imageCountAfterAutonomousActions": 3,
                    "imageCountStableRounds": 6,
                    "readerReadinessEnabled": True,
                    "overlayDismissEnabled": True,
                    "overlayDismissAttempts": 2,
                    "overlayDismissedCount": 1,
                    "carouselExplorationEnabled": True,
                    "carouselStepsExecuted": 7,
                    "sequenceLengthBeforeExploration": 1,
                    "sequenceLengthAfterExploration": 3,
                    "sequenceStableRounds": 6,
                    "autonomousStopReason": "sequence_stable",
                    "blockedByOverlaySuspected": False,
                    "notes": [
                        "Autonomous capture ran generic reader readiness checks.",
                        "No site-specific selectors or bypass logic were used.",
                    ],
                }
            ).encode("utf-8"),
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/capture",
        json={
            "url": "https://example.com/chapter-1.html",
            "durationSeconds": 60,
            "captureMode": "autonomous",
        },
    )

    diagnostics = response.json()["diagnostics"]

    assert response.status_code == 200
    assert diagnostics["readerReadinessEnabled"] is True
    assert diagnostics["overlayDismissEnabled"] is True
    assert diagnostics["overlayDismissAttempts"] == 2
    assert diagnostics["overlayDismissedCount"] == 1
    assert diagnostics["carouselExplorationEnabled"] is True
    assert diagnostics["carouselStepsExecuted"] == 7
    assert diagnostics["sequenceLengthBeforeExploration"] == 1
    assert diagnostics["sequenceLengthAfterExploration"] == 3
    assert diagnostics["sequenceStableRounds"] == 6
    assert diagnostics["autonomousStopReason"] == "sequence_stable"
    assert diagnostics["blockedByOverlaySuspected"] is False


def test_no_domain_specific_logic_in_capture_worker() -> None:
    worker_path = Path("app/services/browser_capture_worker.py")
    source = worker_path.read_text(encoding="utf-8").lower()

    assert "comix.to" not in source


def test_dominant_numeric_sequence_filtering_excludes_assets() -> None:
    from app.services.browser_capture import select_reader_sequence

    items = [
        {"url": "https://example.com/assets/logo.png", "source": "network"},
        {"url": "https://example.com/pages/01.webp", "source": "network"},
        {"url": "https://example.com/pages/02.webp", "source": "dom"},
        {"url": "https://example.com/pages/03.webp", "source": "network"},
        {"url": "https://example.com/avatar-99.png", "source": "dom"},
    ]

    selected, diagnostics = select_reader_sequence(items)

    assert [item["url"] for item in selected] == [
        "https://example.com/pages/01.webp",
        "https://example.com/pages/02.webp",
        "https://example.com/pages/03.webp",
    ]
    assert diagnostics["dominantSequenceDetected"] is True
    assert diagnostics["dominantSequenceLength"] == 3
    assert diagnostics["selectionStrategy"] == "dominant_numeric_sequence"


def test_capture_filenames_regenerated_after_filtering(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_capture.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [
                        {"url": "https://example.com/logo.png", "source": "network"},
                        {"url": "https://example.com/pages/01.webp", "source": "network"},
                        {"url": "https://example.com/pages/02.webp", "source": "network"},
                        {"url": "https://example.com/pages/03.webp", "source": "network"},
                    ],
                    "networkImageCount": 4,
                    "domImageCount": 0,
                    "deduplicatedCount": 0,
                    "notes": [],
                }
            ).encode("utf-8"),
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/capture",
        json={
            "url": "https://example.com/chapter-1.html",
            "durationSeconds": 30,
            "captureMode": "autonomous",
        },
    )

    assert response.status_code == 200
    assert [item["filename"] for item in response.json()["images"]] == [
        "001.webp",
        "002.webp",
        "003.webp",
    ]
    assert response.json()["diagnostics"]["excludedImageCount"] == 1


def test_capture_filter_falls_back_to_discovery_order_without_sequence() -> None:
    from app.services.browser_capture import select_reader_sequence

    items = [
        {"url": "https://example.com/cover.webp", "source": "network"},
        {"url": "https://example.com/reader-main.webp", "source": "dom"},
    ]

    selected, diagnostics = select_reader_sequence(items)

    assert selected == items
    assert diagnostics["dominantSequenceDetected"] is False
    assert diagnostics["selectionStrategy"] == "discovery_order"


def test_capture_duration_is_clamped(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_capture.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [],
                    "networkImageCount": 0,
                    "domImageCount": 0,
                    "deduplicatedCount": 0,
                    "notes": [],
                }
            ).encode("utf-8"),
            stderr=b"",
        ),
    )

    low_response = client.post(
        "/api/chapters/capture",
        json={"url": "https://example.com/chapter-1.html", "durationSeconds": 1},
    )
    high_response = client.post(
        "/api/chapters/capture",
        json={"url": "https://example.com/chapter-1.html", "durationSeconds": 999},
    )

    assert low_response.status_code == 200
    assert low_response.json()["captureDurationSeconds"] == 5
    assert high_response.status_code == 200
    assert high_response.json()["captureDurationSeconds"] == 120


def test_url_policy_applies_to_capture_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "local_only")

    response = client.post(
        "/api/chapters/capture",
        json={"url": "https://example.com/chapter-1.html", "durationSeconds": 30},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "URL host is not allowed in local_only mode. Use localhost or 127.0.0.1."
    )


def test_capture_merges_dom_and_network_images_in_discovery_order(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_capture.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "images": [
                        {
                            "url": "https://example.com/images/01.webp",
                            "source": "network",
                        },
                        {
                            "url": "https://example.com/images/01.webp",
                            "source": "dom",
                        },
                        {
                            "url": "https://example.com/images/02.webp",
                            "source": "dom",
                        },
                    ],
                    "networkImageCount": 1,
                    "domImageCount": 2,
                    "deduplicatedCount": 0,
                    "notes": [],
                }
            ).encode("utf-8"),
            stderr=b"",
        ),
    )

    response = client.post(
        "/api/chapters/capture",
        json={"url": "https://example.com/chapter-1.html", "durationSeconds": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["url"] for item in payload["images"]] == [
        "https://example.com/images/01.webp",
        "https://example.com/images/02.webp",
    ]
    assert [item["source"] for item in payload["images"]] == ["network", "dom"]
    assert payload["diagnostics"]["networkImageCount"] == 1
    assert payload["diagnostics"]["domImageCount"] == 2
    assert payload["diagnostics"]["deduplicatedCount"] == 1


def test_capture_worker_invalid_output_maps_to_clean_error(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setattr(
        "app.services.browser_capture.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout=b"not-json",
            stderr=b"traceback",
        ),
    )

    response = client.post(
        "/api/chapters/capture",
        json={"url": "https://example.com/chapter-1.html", "durationSeconds": 30},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Browser capture worker failed."


def test_capture_worker_stage_failures_map_to_clean_errors(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    cases = [
        ("launch", "Browser capture mode could not launch the browser."),
        ("navigation", "Browser capture mode failed during page navigation."),
        (
            "playwright_missing",
            "Browser render mode requires Playwright and installed browser binaries.",
        ),
    ]

    for stage, expected_detail in cases:
        monkeypatch.setattr(
            "app.services.browser_capture.subprocess.run",
            lambda *args, stage=stage, **kwargs: SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {"ok": False, "stage": stage, "message": "boom"}
                ).encode("utf-8"),
                stderr=b"",
            ),
        )
        response = client.post(
            "/api/chapters/capture",
            json={"url": "https://example.com/chapter-1.html", "durationSeconds": 30},
        )
        assert response.status_code in {500, 502}
        assert response.json()["detail"] == expected_detail


def test_browser_dom_extraction_prefers_likely_chapter_images_and_preserves_order() -> None:
    from app.services.browser_dom_extractor import extract_images_from_rendered_dom

    html = """
    <html><body>
      <div class="reader-shell">
        <img src="/avatar.png" class="avatar" width="40" height="40">
        <section class="viewer pages">
          <img src="/page-002.jpg" alt="Page 2">
          <img src="/page-001.jpg" alt="Page 1">
        </section>
        <img src="/site-logo.png" class="logo" width="120" height="40">
      </div>
    </body></html>
    """

    image_urls, diagnostics = extract_images_from_rendered_dom(
        "https://example.com/chapter-1.html",
        html,
    )

    assert image_urls == [
        "https://example.com/page-002.jpg",
        "https://example.com/page-001.jpg",
    ]
    assert diagnostics["domImageCount"] == 4
    assert diagnostics["browserFilteredImageCount"] == 2
    assert diagnostics["browserExtractionNotes"]


def test_browser_mode_diagnostics_fields_exist(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_rendered_html(_: str) -> tuple[str, str, dict]:
        return (
            """
            <html><body>
              <div class="reader swiper">
                <img src="/page-001.jpg" alt="Page 1">
                <img src="/icon.png" class="icon" width="16" height="16">
              </div>
            </body></html>
            """,
            "https://example.com/chapter-1.html",
            {
                "browserScrollEnabled": True,
                "browserScrollSteps": 3,
                "browserScrollHeightBefore": 1000,
                "browserScrollHeightAfter": 3000,
                "browserLazyLoadWaitMs": 500,
                "browserScrollableContainerCount": 2,
                "browserScrolledContainerCount": 1,
                "browserMouseWheelSteps": 2,
                "browserImageCountBeforeScroll": 1,
                "browserImageCountAfterScroll": 4,
                "browserImageCountStableRounds": 2,
                "browserScrollStrategy": "window_and_internal",
                "browserHeadless": False,
                "browserPersistentContextEnabled": True,
                "browserUserDataDirConfigured": True,
                "browserSessionMode": "persistent",
                "browserSessionNotes": [
                    "Browser mode used a persistent browser profile.",
                    "Browser mode launched a visible browser window for local debugging.",
                ],
                "browserScrollNotes": [
                    "Browser mode scrolled the page to trigger lazy-loaded content."
                ],
            },
        )

    monkeypatch.setattr(
        "app.services.browser_preview.fetch_rendered_html",
        fake_fetch_rendered_html,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html", "renderMode": "browser"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["images"] == [
        {
            "index": 1,
            "url": "https://example.com/page-001.jpg",
            "filename": "001.jpg",
        }
    ]
    assert payload["diagnostics"]["renderModeUsed"] == "browser"
    assert payload["diagnostics"]["browserRendered"] is True
    assert payload["diagnostics"]["domImageCount"] == 2
    assert payload["diagnostics"]["browserFilteredImageCount"] == 1
    assert payload["diagnostics"]["browserHeadless"] is False
    assert payload["diagnostics"]["browserPersistentContextEnabled"] is True
    assert payload["diagnostics"]["browserUserDataDirConfigured"] is True
    assert payload["diagnostics"]["browserSessionMode"] == "persistent"
    assert payload["diagnostics"]["browserScrollEnabled"] is True
    assert payload["diagnostics"]["browserScrollSteps"] == 3
    assert payload["diagnostics"]["browserScrollHeightBefore"] == 1000
    assert payload["diagnostics"]["browserScrollHeightAfter"] == 3000
    assert payload["diagnostics"]["browserLazyLoadWaitMs"] == 500
    assert payload["diagnostics"]["browserScrollableContainerCount"] == 2
    assert payload["diagnostics"]["browserScrolledContainerCount"] == 1
    assert payload["diagnostics"]["browserMouseWheelSteps"] == 2
    assert payload["diagnostics"]["browserImageCountBeforeScroll"] == 1
    assert payload["diagnostics"]["browserImageCountAfterScroll"] == 4
    assert payload["diagnostics"]["browserImageCountStableRounds"] == 2
    assert payload["diagnostics"]["browserScrollStrategy"] == "window_and_internal"
    assert payload["diagnostics"]["browserExtractionNotes"]


def test_local_only_rejects_example_dot_com(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "local_only")
    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "URL host is not allowed in local_only mode. "
        "Use localhost or 127.0.0.1."
    )


def test_allowlist_allows_configured_host(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "allowlist")
    monkeypatch.setenv("ALLOWED_HOSTS", "example.com,images.example.org")
    html = '<html><body><img src="/page-001.jpg"></body></html>'

    async def fake_fetch_text(_: str) -> str:
        return html

    monkeypatch.setattr(
        "app.services.chapter_preview.fetch_text",
        fake_fetch_text,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sourceUrl": "https://example.com/chapter-1.html",
        "imageCount": 1,
        "images": [
            {
                "index": 1,
                "url": "https://example.com/page-001.jpg",
                "filename": "001.jpg",
            }
        ],
        "diagnostics": {
            "htmlLength": len(html),
            "imgTagCount": 1,
            "imagesFromSrc": 1,
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
            "deduplicatedCount": 0,
            "looksDynamic": False,
            "hasAppRootShell": False,
            "possibleApiDrivenPage": False,
            "renderModeUsed": "static",
            "browserRendered": False,
            "domImageCount": 0,
            "browserFilteredImageCount": 0,
            "browserHeadless": True,
            "browserPersistentContextEnabled": False,
            "browserUserDataDirConfigured": False,
            "browserSessionMode": "ephemeral",
            "browserScrollEnabled": False,
            "browserScrollSteps": 0,
            "browserScrollHeightBefore": 0,
            "browserScrollHeightAfter": 0,
            "browserLazyLoadWaitMs": 0,
            "browserScrollableContainerCount": 0,
            "browserScrolledContainerCount": 0,
            "browserMouseWheelSteps": 0,
            "browserImageCountBeforeScroll": 0,
            "browserImageCountAfterScroll": 0,
            "browserImageCountStableRounds": 0,
            "browserScrollStrategy": "none",
            "browserExtractionNotes": [],
            "notes": [],
        },
    }


def test_allowlist_rejects_non_configured_host(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "allowlist")
    monkeypatch.setenv("ALLOWED_HOSTS", "example.com")

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://other.example.org/chapter-1.html"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "URL host is not allowed in allowlist mode."


def test_open_allows_example_dot_com(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return '<html><body><img src="/page-001.jpg"></body></html>'

    monkeypatch.setattr(
        "app.services.chapter_preview.fetch_text",
        fake_fetch_text,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    assert response.json()["images"][0]["url"] == "https://example.com/page-001.jpg"


def test_open_rejects_file_scheme(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    response = client.post(
        "/api/chapters/preview",
        json={"url": "file:///chapter-1.html"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only http and https URLs are allowed."


def test_missing_scheme_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    response = client.post(
        "/api/chapters/preview",
        json={"url": "example.com/chapter-1.html"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "URL must include http:// or https:// scheme."


def test_missing_hostname_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https:///chapter-1.html"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "URL must include a hostname."


def test_fetch_failure_returns_clean_502(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        raise TargetFetchError("Target page could not be reached.", 502)

    monkeypatch.setattr(
        "app.services.chapter_preview.fetch_text",
        fake_fetch_text,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Target page could not be reached."


def test_timeout_returns_clean_504(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        raise TargetFetchError("Target request timed out.", 504)

    monkeypatch.setattr(
        "app.services.chapter_preview.fetch_text",
        fake_fetch_text,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == "Target request timed out."


def test_http_client_maps_status_errors_to_502(monkeypatch) -> None:
    monkeypatch.setenv("SSL_VERIFY_MODE", "default")
    request = httpx.Request("GET", "https://example.com/chapter-1.html")
    response = httpx.Response(404, request=request)

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, _: str) -> httpx.Response:
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setattr("app.services.http_client.httpx.AsyncClient", lambda **_: FakeClient())

    from app.services.http_client import fetch_text

    try:
        import asyncio

        asyncio.run(fetch_text("https://example.com/chapter-1.html"))
    except TargetFetchError as exc:
        assert exc.status_code == 502
        assert exc.message == "Target server returned an error response."
    else:
        raise AssertionError("Expected TargetFetchError")


def test_http_client_maps_timeout_to_504(monkeypatch) -> None:
    monkeypatch.setenv("SSL_VERIFY_MODE", "default")
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, _: str) -> str:
            raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr("app.services.http_client.httpx.AsyncClient", lambda **_: FakeClient())

    from app.services.http_client import fetch_text

    try:
        import asyncio

        asyncio.run(fetch_text("https://example.com/chapter-1.html"))
    except TargetFetchError as exc:
        assert exc.status_code == 504
        assert exc.message == "Target request timed out."
    else:
        raise AssertionError("Expected TargetFetchError")


def test_disabled_ssl_mode_passes_verify_false(monkeypatch) -> None:
    captured_kwargs = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, _: str):
            return SimpleNamespace(
                status_code=200,
                is_redirect=False,
                headers={},
                text="ok",
                content=b"ok",
                url="https://example.com",
                raise_for_status=lambda: None,
            )

    monkeypatch.setenv("SSL_VERIFY_MODE", "disabled")
    monkeypatch.setattr("app.services.http_client.httpx.AsyncClient", FakeClient)

    from app.services.http_client import get_response

    import asyncio

    asyncio.run(get_response("https://example.com", follow_redirects=True))

    assert captured_kwargs["verify"] is False


def test_truststore_mode_handles_missing_package_gracefully(monkeypatch) -> None:
    monkeypatch.setenv("SSL_VERIFY_MODE", "truststore")

    def fake_import_module(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("app.services.http_client.importlib.import_module", fake_import_module)

    from app.services.http_client import get_response

    try:
        import asyncio

        asyncio.run(get_response("https://example.com", follow_redirects=True))
    except TargetFetchError as exc:
        assert exc.status_code == 500
        assert exc.message == "SSL truststore mode requires the truststore package."
    else:
        raise AssertionError("Expected TargetFetchError")


def test_configured_user_agent_is_used_in_outgoing_requests(monkeypatch) -> None:
    captured_kwargs = {}
    monkeypatch.setenv("SSL_VERIFY_MODE", "default")

    class FakeClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, _: str):
            return SimpleNamespace(
                status_code=200,
                is_redirect=False,
                headers={},
                text="ok",
                content=b"ok",
                url="https://example.com",
                raise_for_status=lambda: None,
            )

    monkeypatch.setenv("HTTP_USER_AGENT", "TestAgent/9.9")
    monkeypatch.setattr("app.services.http_client.httpx.AsyncClient", FakeClient)

    from app.services.http_client import get_response

    import asyncio

    asyncio.run(get_response("https://example.com", follow_redirects=True))

    assert captured_kwargs["headers"]["User-Agent"] == "TestAgent/9.9"


def test_html_fetch_uses_html_accept_header(monkeypatch) -> None:
    captured_kwargs = {}
    monkeypatch.setenv("SSL_VERIFY_MODE", "default")

    class FakeClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, _: str):
            return SimpleNamespace(
                status_code=200,
                is_redirect=False,
                headers={},
                text="ok",
                content=b"ok",
                url="https://example.com",
                raise_for_status=lambda: None,
            )

    monkeypatch.setattr("app.services.http_client.httpx.AsyncClient", FakeClient)

    from app.services.http_client import fetch_text

    import asyncio

    asyncio.run(fetch_text("https://example.com"))

    assert (
        captured_kwargs["headers"]["Accept"]
        == "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    )


def test_image_download_uses_image_accept_header(monkeypatch) -> None:
    captured_kwargs = {}
    monkeypatch.setenv("SSL_VERIFY_MODE", "default")

    class FakeClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, _: str):
            return SimpleNamespace(
                status_code=200,
                is_redirect=False,
                headers={},
                text="ok",
                content=b"ok",
                url="https://example.com/image.jpg",
                raise_for_status=lambda: None,
            )

    monkeypatch.setattr("app.services.http_client.httpx.AsyncClient", FakeClient)

    from app.services.http_client import fetch_bytes

    import asyncio

    asyncio.run(fetch_bytes("https://example.com/image.jpg"))

    assert captured_kwargs["headers"]["Accept"] == "image/*,*/*;q=0.8"


def test_http_client_maps_ssl_errors_to_clean_502(monkeypatch) -> None:
    monkeypatch.setenv("SSL_VERIFY_MODE", "default")
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, _: str):
            ssl_error = ssl.SSLCertVerificationError("certificate verify failed")
            raise httpx.ConnectError("ssl fail") from ssl_error

    monkeypatch.setattr("app.services.http_client.httpx.AsyncClient", lambda **_: FakeClient())

    from app.services.http_client import get_response

    try:
        import asyncio

        asyncio.run(get_response("https://example.com", follow_redirects=True))
    except TargetFetchError as exc:
        assert exc.status_code == 502
        assert exc.message == "SSL certificate verification failed for target."
    else:
        raise AssertionError("Expected TargetFetchError")


def test_no_images_returns_zero_count(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")

    async def fake_fetch_text(_: str) -> str:
        return "<html><body><p>No images here.</p></body></html>"

    monkeypatch.setattr(
        "app.services.chapter_preview.fetch_text",
        fake_fetch_text,
    )

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-2.html"},
    )

    assert response.status_code == 200
    assert response.json()["sourceUrl"] == "https://example.com/chapter-2.html"
    assert response.json()["imageCount"] == 0
    assert response.json()["images"] == []
    assert response.json()["diagnostics"]["htmlLength"] > 0
    assert response.json()["diagnostics"]["notes"]


def test_successful_ordered_image_download(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv("DOWNLOAD_BASE_DIR", str(tmp_path))

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <img src="/images/page-003.jpg">
            <img src="/images/page-001.jpg">
            <img src="/images/page-002.jpg">
        </body></html>
        """

    image_payloads = {
        "https://example.com/images/page-003.jpg": b"image-1",
        "https://example.com/images/page-001.jpg": b"image-2",
        "https://example.com/images/page-002.jpg": b"image-3",
    }

    async def fake_fetch_bytes(url: str) -> bytes:
        return image_payloads[url]

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)
    monkeypatch.setattr("app.services.image_downloader.fetch_bytes", fake_fetch_bytes)

    response = client.post(
        "/api/chapters/download",
        json={"url": "https://example.com/chapter-1.html"},
    )

    assert response.status_code == 200
    payload = response.json()
    download_dir = Path(payload["downloadDirectory"])

    assert payload["sourceUrl"] == "https://example.com/chapter-1.html"
    assert payload["imageCount"] == 3
    assert [item["index"] for item in payload["images"]] == [1, 2, 3]
    assert [item["filename"] for item in payload["images"]] == [
        "001.jpg",
        "002.jpg",
        "003.jpg",
    ]
    assert [item["status"] for item in payload["images"]] == [
        "downloaded",
        "downloaded",
        "downloaded",
    ]
    assert payload["runId"]
    assert payload["startedAt"]
    assert payload["finishedAt"]
    assert isinstance(payload["durationMs"], int)
    assert payload["successCount"] == 3
    assert payload["failedCount"] == 0
    assert download_dir.exists()
    assert (download_dir / "001.jpg").read_bytes() == b"image-1"
    assert (download_dir / "002.jpg").read_bytes() == b"image-2"
    assert (download_dir / "003.jpg").read_bytes() == b"image-3"

    report_path = download_dir / "report.json"
    assert report_path.exists()
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_payload == payload
    assert "\n  " in report_path.read_text(encoding="utf-8")


def test_zero_image_chapter_returns_empty_download_report(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv("DOWNLOAD_BASE_DIR", str(tmp_path))

    async def fake_fetch_text(_: str) -> str:
        return "<html><body><p>No images here.</p></body></html>"

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/download",
        json={"url": "https://example.com/chapter-2.html"},
    )

    assert response.status_code == 200
    payload = response.json()
    download_dir = Path(payload["downloadDirectory"])

    assert payload["imageCount"] == 0
    assert payload["successCount"] == 0
    assert payload["failedCount"] == 0
    assert payload["images"] == []
    assert download_dir.exists()
    assert [item.name for item in download_dir.iterdir()] == ["report.json"]
    report_payload = json.loads((download_dir / "report.json").read_text(encoding="utf-8"))
    assert report_payload["imageCount"] == 0
    assert report_payload["images"] == []


def test_failed_image_does_not_stop_whole_download(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv("DOWNLOAD_BASE_DIR", str(tmp_path))

    async def fake_fetch_text(_: str) -> str:
        return """
        <html><body>
            <img src="/images/page-001.jpg">
            <img src="/images/page-002.jpg">
            <img src="/images/page-003.jpg">
        </body></html>
        """

    async def fake_fetch_bytes(url: str) -> bytes:
        if url.endswith("page-002.jpg"):
            raise TargetFetchError("Target page could not be reached.", 502)
        return f"payload:{url}".encode()

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)
    monkeypatch.setattr("app.services.image_downloader.fetch_bytes", fake_fetch_bytes)

    response = client.post(
        "/api/chapters/download",
        json={"url": "https://example.com/chapter-3.html"},
    )

    assert response.status_code == 200
    payload = response.json()
    download_dir = Path(payload["downloadDirectory"])

    assert [item["status"] for item in payload["images"]] == [
        "downloaded",
        "failed",
        "downloaded",
    ]
    assert payload["successCount"] == 2
    assert payload["failedCount"] == 1
    assert payload["images"][1]["error"] == "Target page could not be reached."
    assert payload["images"][1]["path"] is None
    assert (download_dir / "001.jpg").exists()
    assert not (download_dir / "002.jpg").exists()
    assert (download_dir / "003.jpg").exists()
    report_payload = json.loads((download_dir / "report.json").read_text(encoding="utf-8"))
    assert report_payload["failedCount"] == 1
    assert report_payload["successCount"] == 2


def test_preview_endpoint_still_works_after_download_feature(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    html = '<html><body><img src="/page-001.jpg"></body></html>'

    async def fake_fetch_text(_: str) -> str:
        return html

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)

    response = client.post(
        "/api/chapters/preview",
        json={"url": "https://example.com/chapter-4.html"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sourceUrl": "https://example.com/chapter-4.html",
        "imageCount": 1,
        "images": [
            {
                "index": 1,
                "url": "https://example.com/page-001.jpg",
                "filename": "001.jpg",
            }
        ],
        "diagnostics": {
            "htmlLength": len(html),
            "imgTagCount": 1,
            "imagesFromSrc": 1,
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
            "deduplicatedCount": 0,
            "looksDynamic": False,
            "hasAppRootShell": False,
            "possibleApiDrivenPage": False,
            "renderModeUsed": "static",
            "browserRendered": False,
            "domImageCount": 0,
            "browserFilteredImageCount": 0,
            "browserHeadless": True,
            "browserPersistentContextEnabled": False,
            "browserUserDataDirConfigured": False,
            "browserSessionMode": "ephemeral",
            "browserScrollEnabled": False,
            "browserScrollSteps": 0,
            "browserScrollHeightBefore": 0,
            "browserScrollHeightAfter": 0,
            "browserLazyLoadWaitMs": 0,
            "browserScrollableContainerCount": 0,
            "browserScrolledContainerCount": 0,
            "browserMouseWheelSteps": 0,
            "browserImageCountBeforeScroll": 0,
            "browserImageCountAfterScroll": 0,
            "browserImageCountStableRounds": 0,
            "browserScrollStrategy": "none",
            "browserExtractionNotes": [],
            "notes": [],
        },
    }


def test_url_policy_applies_to_download_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "local_only")

    response = client.post(
        "/api/chapters/download",
        json={"url": "https://example.com/chapter-5.html"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "URL host is not allowed in local_only mode. "
        "Use localhost or 127.0.0.1."
    )


def test_report_write_failure_returns_clean_500(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("URL_ACCESS_MODE", "open")
    monkeypatch.setenv("DOWNLOAD_BASE_DIR", str(tmp_path))

    async def fake_fetch_text(_: str) -> str:
        return '<html><body><img src="/page-001.jpg"></body></html>'

    async def fake_fetch_bytes(_: str) -> bytes:
        return b"ok"

    def fake_write_report_json(_: str, __) -> None:
        from app.services.report_writer import ReportWriteError

        raise ReportWriteError("Failed to write download report.")

    monkeypatch.setattr("app.services.chapter_preview.fetch_text", fake_fetch_text)
    monkeypatch.setattr("app.services.image_downloader.fetch_bytes", fake_fetch_bytes)
    monkeypatch.setattr("app.services.image_downloader.write_report_json", fake_write_report_json)

    response = client.post(
        "/api/chapters/download",
        json={"url": "https://example.com/chapter-6.html"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to write download report."
