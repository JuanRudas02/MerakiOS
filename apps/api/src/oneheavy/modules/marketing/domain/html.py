"""Sanitizador HTML por lista blanca para emails generados por IA.

El HTML de un LLM es entrada no confiable: se reconstruye permitiendo sólo
etiquetas y atributos seguros, se descartan `<script>/<style>/<iframe>`,
manejadores `on*` y URLs `javascript:`/`data:`.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

ALLOWED_TAGS = frozenset(
    {
        "a", "b", "blockquote", "br", "div", "em", "h1", "h2", "h3", "h4", "hr", "i", "img", "li", "ol",
        "p", "span", "strong", "table", "tbody", "td", "th", "thead", "tr", "u", "ul", "center", "small",
    }
)  # fmt: skip
VOID_TAGS = frozenset({"br", "hr", "img"})
DROP_CONTENT_TAGS = frozenset({"script", "style", "iframe", "object", "embed", "noscript", "template"})
ALLOWED_ATTRS = frozenset(
    {"href", "src", "alt", "title", "style", "width", "height", "align", "target", "colspan", "rowspan"}
)
_URL_ATTRS = frozenset({"href", "src"})
_SAFE_URL = re.compile(
    r"^(https?:|mailto:|tel:|#|/|\{)", re.IGNORECASE
)  # "{" permite tokens Mautic {unsubscribe_url}
_STYLE_BAD = re.compile(r"expression\s*\(|url\s*\(\s*['\"]?\s*javascript:", re.IGNORECASE)


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._drop_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in DROP_CONTENT_TAGS:
            self._drop_depth += 1
            return
        if self._drop_depth or tag not in ALLOWED_TAGS:
            return
        safe: list[str] = []
        for name, value in attrs:
            name = name.lower()
            if name.startswith("on") or name not in ALLOWED_ATTRS or value is None:
                continue
            value = value.strip()
            if name in _URL_ATTRS and not _SAFE_URL.match(value):
                continue
            if name == "style" and _STYLE_BAD.search(value):
                continue
            if name == "target":
                safe.append('rel="noopener noreferrer"')
            safe.append(f'{name}="{html.escape(value, quote=True)}"')
        attr_str = (" " + " ".join(safe)) if safe else ""
        self.out.append(f"<{tag}{attr_str}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag in DROP_CONTENT_TAGS:
            self._drop_depth -= 1

    def handle_endtag(self, tag: str) -> None:
        if tag in DROP_CONTENT_TAGS:
            self._drop_depth = max(0, self._drop_depth - 1)
            return
        if self._drop_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._drop_depth:
            self.out.append(html.escape(data, quote=False))


def sanitize_html(raw: str) -> str:
    parser = _Sanitizer()
    parser.feed(raw or "")
    parser.close()
    return "".join(parser.out).strip()


def html_to_text(raw: str) -> str:
    text = re.sub(r"<(br|/p|/div|/h[1-4]|/li|/tr)\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.strip() for line in text.splitlines())).strip()


# Marcadores de personalización que suelen escribir los LLM → tokens de Mautic.
_MAUTIC_TOKENS = {
    "firstname": "{contactfield=firstname}",
    "company": "{contactfield=company}",
}
_PLACEHOLDER_RE = re.compile(
    r"\{\{?\s*(first[_ ]?name|nombre|name|company|empresa)\s*\}?\}|\[(nombre|empresa)\]", re.IGNORECASE
)


def normalize_mautic_tokens(text: str) -> str:
    """Convierte `{first_name}`, `{{nombre}}`, `[Empresa]`… a los tokens de Mautic.

    No toca tokens propios de Mautic como `{contactfield=...}` o `{unsubscribe_url}`.
    """

    def _swap(match: re.Match[str]) -> str:
        word = (match.group(1) or match.group(2) or "").lower()
        return _MAUTIC_TOKENS["company" if word in ("company", "empresa") else "firstname"]

    return _PLACEHOLDER_RE.sub(_swap, text)
