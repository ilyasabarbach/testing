import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin


JSON_SCRIPT_TYPES = {"application/json", "application/ld+json"}
IMAGE_URL_PATTERN = re.compile(
    r"(?i)\.(jpg|jpeg|png|webp|gif|avif)(?:[?#].*)?$"
)
APP_ROOT_MARKERS = (
    'id="app"',
    "id='app'",
    'id="root"',
    "id='root'",
    'id="app-root"',
    "id='app-root'",
    "__next",
)


class EmbeddedJSONScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.script_tag_count = 0
        self.json_script_count = 0
        self._capture_json = False
        self._buffer: list[str] = []
        self.json_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return

        self.script_tag_count += 1
        attributes = {key.lower(): value for key, value in attrs if value}
        script_type = attributes.get("type", "").lower()
        if script_type in JSON_SCRIPT_TYPES:
            self.json_script_count += 1
            self._capture_json = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_json:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capture_json:
            block = "".join(self._buffer).strip()
            if block:
                self.json_blocks.append(block)
            self._capture_json = False
            self._buffer = []


def extract_images_from_embedded_json(
    source_url: str,
    html: str,
    existing_urls: list[str] | None = None,
) -> tuple[list[str], dict]:
    parser = EmbeddedJSONScriptParser()
    parser.feed(html)

    discovered_urls: list[str] = []
    seen_urls = set(existing_urls or [])
    embedded_image_url_count = 0

    for json_block in parser.json_blocks:
        for raw_url in _extract_image_strings_from_json_block(json_block):
            embedded_image_url_count += 1
            resolved_url = urljoin(source_url, raw_url)
            if resolved_url in seen_urls:
                continue
            seen_urls.add(resolved_url)
            discovered_urls.append(resolved_url)

    has_app_root_shell = _has_app_root_shell(html)
    possible_api_driven_page = _possible_api_driven_page(
        html=html,
        has_app_root_shell=has_app_root_shell,
        json_script_count=parser.json_script_count,
        script_tag_count=parser.script_tag_count,
        direct_image_count=len(existing_urls or []),
    )

    notes: list[str] = []
    if parser.json_script_count > 0:
        notes.append("Page contains embedded JSON scripts.")
    if has_app_root_shell:
        notes.append("Page appears to be an application shell.")
    if discovered_urls:
        notes.append(
            "Embedded JSON image URLs may be metadata assets rather than chapter pages."
        )

    diagnostics = {
        "jsonScriptCount": parser.json_script_count,
        "embeddedImageUrlCount": embedded_image_url_count,
        "imagesFromEmbeddedJson": len(discovered_urls),
        "hasAppRootShell": has_app_root_shell,
        "possibleApiDrivenPage": possible_api_driven_page,
        "jsonNotes": notes,
    }

    return discovered_urls, diagnostics


def _extract_image_strings_from_json_block(json_block: str) -> list[str]:
    try:
        payload = json.loads(json_block)
    except json.JSONDecodeError:
        return []

    collected: list[str] = []
    _walk_json(payload, collected)
    return collected


def _walk_json(node, collected: list[str]) -> None:
    if isinstance(node, dict):
        for value in node.values():
            _walk_json(value, collected)
        return

    if isinstance(node, list):
        for value in node:
            _walk_json(value, collected)
        return

    if isinstance(node, str) and _looks_like_image_url(node):
        collected.append(node)


def _looks_like_image_url(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    if candidate.startswith("data:"):
        return False
    return bool(IMAGE_URL_PATTERN.search(candidate))


def _has_app_root_shell(html: str) -> bool:
    html_lower = html.lower()
    return any(marker in html_lower for marker in APP_ROOT_MARKERS)


def _possible_api_driven_page(
    html: str,
    has_app_root_shell: bool,
    json_script_count: int,
    script_tag_count: int,
    direct_image_count: int,
) -> bool:
    return (
        has_app_root_shell
        and json_script_count > 0
        and direct_image_count <= 1
        and script_tag_count >= 2
    )
