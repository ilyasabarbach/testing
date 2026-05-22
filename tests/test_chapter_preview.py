from fastapi.testclient import TestClient
import httpx
import json
from pathlib import Path

from app.main import app
from app.services.http_client import TargetFetchError


client = TestClient(app)


def test_root_ui_returns_200() -> None:
    response = client.get("/")

    assert response.status_code == 200


def test_root_ui_contains_project_title() -> None:
    response = client.get("/")

    assert "Chapter Image Automation Tool" in response.text
    assert 'id="chapter-url"' in response.text


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
    }


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
    assert response.json() == {
        "sourceUrl": "https://example.com/chapter-2.html",
        "imageCount": 0,
        "images": [],
    }


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

    async def fake_fetch_text(_: str) -> str:
        return '<html><body><img src="/page-001.jpg"></body></html>'

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
