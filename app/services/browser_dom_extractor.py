import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin

from app.services.html_image_extractor import pick_srcset_candidate


LIKELY_CONTAINER_TERMS = ("page", "reader", "read", "viewer", "slide", "swiper")
IGNORE_TERMS = ("avatar", "icon", "logo", "gravatar", "comment", "comments", "rich-img")
PAGE_ALT_PATTERN = re.compile(r"\bpage\s*\d+\b", re.IGNORECASE)
SMALL_IMAGE_THRESHOLD = 64
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass
class BrowserImageCandidate:
    url: str
    score: int
    ignored: bool
    small: bool


class BrowserDOMImageExtractor(HTMLParser):
    def __init__(self, source_url: str) -> None:
        super().__init__()
        self.source_url = source_url
        self.dom_image_count = 0
        self.candidates: list[BrowserImageCandidate] = []
        self._context_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs if value}
        context_text = " ".join(
            filter(None, [attributes.get("id"), attributes.get("class")])
        ).lower()
        normalized_tag = tag.lower()
        if normalized_tag not in VOID_TAGS:
            self._context_stack.append(context_text)

        if normalized_tag != "img":
            return

        self.dom_image_count += 1
        raw_url = _pick_image_source(attributes)
        if not raw_url:
            return

        alt_text = attributes.get("alt", "").lower()
        own_text = " ".join(
            filter(
                None,
                [
                    attributes.get("id"),
                    attributes.get("class"),
                    attributes.get("alt"),
                ],
            )
        ).lower()
        context = " ".join(part for part in self._context_stack if part).lower()
        ignored = _contains_any(own_text, IGNORE_TERMS) or _contains_any(
            context, IGNORE_TERMS
        )
        small = _is_small_image(attributes)
        score = 0

        if PAGE_ALT_PATTERN.search(alt_text):
            score += 3
        if _contains_any(context, LIKELY_CONTAINER_TERMS):
            score += 2
        if _contains_any(own_text, LIKELY_CONTAINER_TERMS):
            score += 1

        self.candidates.append(
            BrowserImageCandidate(
                url=urljoin(self.source_url, raw_url),
                score=score,
                ignored=ignored,
                small=small,
            )
        )

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in VOID_TAGS:
            return
        if self._context_stack:
            self._context_stack.pop()


def extract_images_from_rendered_dom(source_url: str, html: str) -> tuple[list[str], dict]:
    parser = BrowserDOMImageExtractor(source_url)
    parser.feed(html)

    viable_candidates = [
        candidate
        for candidate in parser.candidates
        if not candidate.ignored and not candidate.small
    ]
    preferred_candidates = [candidate for candidate in viable_candidates if candidate.score >= 2]
    selected_candidates = preferred_candidates or viable_candidates

    image_urls: list[str] = []
    seen_urls: set[str] = set()
    for candidate in selected_candidates:
        if candidate.url in seen_urls:
            continue
        seen_urls.add(candidate.url)
        image_urls.append(candidate.url)

    notes: list[str] = [
        "Browser mode inspected the final rendered DOM after JavaScript execution.",
        "Browser filtering preserves DOM order and prefers likely reading-page images.",
    ]
    if preferred_candidates:
        notes.append(
            "Selection favored page-like alt text and reader-style container markers."
        )
    if any(candidate.ignored for candidate in parser.candidates):
        notes.append("Likely avatars, icons, logos, or comment images were ignored.")
    if any(candidate.small for candidate in parser.candidates):
        notes.append("Very small images were ignored during browser extraction.")
    if not image_urls:
        notes.append("No likely reading-page images survived browser-mode filtering.")

    diagnostics = {
        "domImageCount": parser.dom_image_count,
        "browserFilteredImageCount": len(image_urls),
        "browserExtractionNotes": notes,
        "selectedStrategy": "preferred" if preferred_candidates else "fallback",
    }
    return image_urls, diagnostics


def _pick_image_source(attributes: dict[str, str]) -> str | None:
    for key in ("src", "data-src", "data-lazy-src", "data-original", "data-url"):
        value = attributes.get(key)
        if value:
            return value

    return pick_srcset_candidate(attributes.get("srcset"))


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _is_small_image(attributes: dict[str, str]) -> bool:
    width = _parse_dimension(attributes.get("width"))
    height = _parse_dimension(attributes.get("height"))
    if width is None and height is None:
        return False
    if width is not None and width <= SMALL_IMAGE_THRESHOLD:
        return True
    if height is not None and height <= SMALL_IMAGE_THRESHOLD:
        return True
    return False


def _parse_dimension(value: str | None) -> int | None:
    if not value:
        return None

    digits = "".join(character for character in value if character.isdigit())
    if not digits:
        return None

    return int(digits)
