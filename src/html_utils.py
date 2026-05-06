from __future__ import annotations

import re
from html import escape, unescape
from pathlib import Path
from urllib.parse import unquote, urlparse


IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
IMG_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"', re.IGNORECASE)
HEAD_RE = re.compile(r"<head\b.*?>.*?</head>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style\b.*?>.*?</style>", re.IGNORECASE | re.DOTALL)
SCRIPT_RE = re.compile(r"<script\b.*?>.*?</script>", re.IGNORECASE | re.DOTALL)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
P_RE = re.compile(r"</p\s*>", re.IGNORECASE)
TAG_RE = re.compile(r"<.*?>", re.DOTALL)
PT_SIZE_RE = re.compile(r"font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)pt", re.IGNORECASE)


def _parse_img_attrs(img_tag: str) -> dict[str, str]:
    return {name.lower(): value for name, value in IMG_ATTR_RE.findall(img_tag)}


def _resolve_image_source(source: str, project_root: Path) -> Path | None:
    cleaned = source.strip()
    if not cleaned:
        return None

    parsed = urlparse(cleaned)
    if parsed.scheme == "file":
        candidate = Path(unquote(parsed.path.lstrip("/")))
        return candidate if candidate.exists() else None

    candidate = Path(cleaned)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    normalized = cleaned.replace("\\", "/")
    for relative_source in (normalized, normalized.lstrip("/")):
        full_path = (project_root / relative_source).resolve()
        if full_path.exists():
            return full_path
    return None


def html_to_plain_text(html: str) -> str:
    if not html.strip():
        return ""
    text = HEAD_RE.sub("", html)
    text = STYLE_RE.sub("", text)
    text = SCRIPT_RE.sub("", text)
    text = IMG_TAG_RE.sub("", text)
    text = BR_RE.sub("\n", text)
    text = P_RE.sub("\n", text)
    text = TAG_RE.sub("", text)
    return unescape(text).replace("\r", "").strip()


def html_contains_image(html: str) -> bool:
    return bool(IMG_TAG_RE.search(html))


def scale_html_font_sizes(html: str, scale: float) -> str:
    if scale == 1.0:
        return html

    def replace_font_size(match: re.Match[str]) -> str:
        scaled_size = float(match.group(1)) * scale
        return f"font-size:{scaled_size:.2f}pt"

    return PT_SIZE_RE.sub(replace_font_size, html)


def prepare_html_for_display(html: str, project_root: Path, text_scale: float = 1.0) -> str:
    if not html.strip():
        return "<p></p>"

    def replace_image(match: re.Match[str]) -> str:
        attrs = _parse_img_attrs(match.group(0))
        source = attrs.get("src", "")
        alt = unescape(attrs.get("alt", "image"))
        if not source:
            return match.group(0)
        full_path = _resolve_image_source(source, project_root)
        if full_path is not None:
            return (
                f'<img src="{full_path.as_uri()}" alt="{escape(alt)}" '
                'style="max-width:100%; max-height:480px; height:auto; width:auto;" />'
            )
        return f'<span style="color:#8a4b08; background:#fff4d6; padding:2px 6px;">[画像: {escape(alt)}]</span>'

    prepared = IMG_TAG_RE.sub(replace_image, html)
    prepared = scale_html_font_sizes(prepared, text_scale)
    transparent_css = (
        "<style>"
        "body { background: transparent; }"
        "p { background: transparent; }"
        "img { max-width: 100%; height: auto; }"
        "</style>"
    )
    if "<head" in prepared.lower():
        return re.sub(
            r"<head\b.*?>",
            lambda match: match.group(0) + transparent_css,
            prepared,
            count=1,
            flags=re.IGNORECASE,
        )
    return transparent_css + prepared
