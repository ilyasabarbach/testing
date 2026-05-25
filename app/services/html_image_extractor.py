from html.parser import HTMLParser
from urllib.parse import urljoin


FRAMEWORK_MARKERS = (
    'id="app"',
    "id='app'",
    'id="root"',
    "id='root'",
    'id="app-root"',
    "id='app-root'",
    "__next",
    "data-reactroot",
    "ng-version",
    "data-server-rendered",
)

SRCSET_DELIMITER = ","


class HTMLImageExtractor(HTMLParser):
    def __init__(self, source_url: str, html: str) -> None:
        super().__init__()
        self.source_url = source_url
        self.html = html
        self.img_tag_count = 0
        self.script_tag_count = 0
        self.candidates: list[tuple[str, str]] = []
        self.meta_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        attributes = {key.lower(): value for key, value in attrs if value}

        if normalized_tag == "script":
            self.script_tag_count += 1
            return

        if normalized_tag == "img":
            self.img_tag_count += 1
            self._collect_img_candidates(attributes)
            return

        if normalized_tag == "source":
            srcset = attributes.get("srcset")
            candidate = pick_srcset_candidate(srcset)
            if candidate:
                self.candidates.append(("imagesFromSourceSrcset", candidate))
            return

        if normalized_tag == "meta":
            property_name = attributes.get("property", "").lower()
            meta_name = attributes.get("name", "").lower()
            content = attributes.get("content")
            if content and (
                property_name == "og:image" or meta_name == "twitter:image"
            ):
                self.meta_count += 1
                self.candidates.append(("imagesFromMeta", content))

    def _collect_img_candidates(self, attributes: dict[str, str]) -> None:
        ordered_attributes = [
            ("imagesFromSrc", attributes.get("src")),
            ("imagesFromDataSrc", attributes.get("data-src")),
            ("imagesFromDataLazySrc", attributes.get("data-lazy-src")),
            ("imagesFromDataOriginal", attributes.get("data-original")),
            ("imagesFromDataUrl", attributes.get("data-url")),
        ]

        for label, value in ordered_attributes:
            if value:
                self.candidates.append((label, value))

        srcset_candidate = pick_srcset_candidate(attributes.get("srcset"))
        if srcset_candidate:
            self.candidates.append(("imagesFromSrcset", srcset_candidate))


def pick_srcset_candidate(srcset: str | None) -> str | None:
    if not srcset:
        return None

    candidates = [part.strip() for part in srcset.split(SRCSET_DELIMITER) if part.strip()]
    if not candidates:
        return None

    # Deterministic strategy: choose last candidate, which is usually highest quality.
    last_candidate = candidates[-1]
    return last_candidate.split()[0] if last_candidate.split() else None


def extract_images_with_diagnostics(source_url: str, html: str) -> tuple[list[str], dict]:
    parser = HTMLImageExtractor(source_url=source_url, html=html)
    parser.feed(html)

    raw_count = len(parser.candidates)
    counts = {
        "imagesFromSrc": 0,
        "imagesFromDataSrc": 0,
        "imagesFromDataLazySrc": 0,
        "imagesFromDataOriginal": 0,
        "imagesFromDataUrl": 0,
        "imagesFromSrcset": 0,
        "imagesFromSourceSrcset": 0,
        "imagesFromMeta": 0,
    }

    unique_urls: list[str] = []
    seen_urls: set[str] = set()

    for label, raw_url in parser.candidates:
        counts[label] += 1
        resolved_url = urljoin(source_url, raw_url)
        if resolved_url in seen_urls:
            continue
        seen_urls.add(resolved_url)
        unique_urls.append(resolved_url)

    looks_dynamic = _looks_dynamic(html, parser.img_tag_count, parser.script_tag_count)
    notes = _build_notes(parser=parser, unique_count=len(unique_urls), looks_dynamic=looks_dynamic)

    diagnostics = {
        "htmlLength": len(html),
        "imgTagCount": parser.img_tag_count,
        **counts,
        "jsonScriptCount": 0,
        "embeddedImageUrlCount": 0,
        "imagesFromEmbeddedJson": 0,
        "deduplicatedCount": raw_count - len(unique_urls),
        "looksDynamic": looks_dynamic,
        "hasAppRootShell": has_framework_marker(html),
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
        "notes": notes,
    }

    return unique_urls, diagnostics


def _looks_dynamic(html: str, img_tag_count: int, script_tag_count: int) -> bool:
    has_framework = has_framework_marker(html)
    large_html = len(html) >= 5000
    few_direct_images = img_tag_count <= 1
    many_scripts = script_tag_count >= 5
    return has_framework or (large_html and few_direct_images and script_tag_count >= 3) or (many_scripts and few_direct_images)


def _build_notes(
    parser: HTMLImageExtractor, unique_count: int, looks_dynamic: bool
) -> list[str]:
    notes: list[str] = []

    if parser.script_tag_count >= 5 and parser.img_tag_count <= 1:
        notes.append("Page contains many script tags and very few direct image tags.")

    if looks_dynamic:
        notes.append("Page looks dynamic, so some images may not be directly present in raw HTML.")

    if parser.candidates and parser.img_tag_count > 0:
        lazy_sources = (
            sum(
                1
                for label, _ in parser.candidates
                if label in {
                    "imagesFromDataSrc",
                    "imagesFromDataLazySrc",
                    "imagesFromDataOriginal",
                    "imagesFromDataUrl",
                }
            )
            > 0
        )
        if lazy_sources:
            notes.append("Some images were recovered from lazy-load attributes.")

    if parser.candidates and any(label in {"imagesFromSrcset", "imagesFromSourceSrcset"} for label, _ in parser.candidates):
        notes.append("Srcset strategy uses the last candidate as the deterministic best image.")

    if unique_count == 0:
        notes.append("No directly usable image URLs were found in supported static HTML patterns.")

    return notes


def has_framework_marker(html: str) -> bool:
    html_lower = html.lower()
    return any(marker in html_lower for marker in FRAMEWORK_MARKERS)
