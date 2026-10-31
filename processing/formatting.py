import html
from html.parser import HTMLParser
from typing import List

# Telegram Bot API limits (counted in UTF-16 code units of the visible text, not the markup)
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096

# Tags Telegram accepts in parse_mode=HTML, with the attributes we keep for each
ALLOWED_TAGS = {
    "b": (), "strong": (), "i": (), "em": (), "u": (), "ins": (),
    "s": (), "strike": (), "del": (), "code": (), "pre": (),
    "tg-spoiler": (), "a": ("href",), "blockquote": ("expandable",),
    "span": ("class",),
}


class _Sanitizer(HTMLParser):
    """Rebuilds HTML keeping only Telegram-supported tags, escaping text and closing every open tag."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: List[str] = []
        self.stack: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.out.append("\n")
            return
        if tag not in ALLOWED_TAGS:
            return
        if tag == "span" and dict(attrs).get("class") != "tg-spoiler":
            return
        if tag == "a" and not dict(attrs).get("href"):
            return

        rendered = tag
        for name, value in attrs:
            if name not in ALLOWED_TAGS[tag]:
                continue
            if value is None:
                rendered += f" {name}"
            else:
                rendered += f' {name}="{html.escape(value, quote=True)}"'
        self.out.append(f"<{rendered}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return  # stray closing tag
        # Close everything opened after this tag so nesting stays valid
        while self.stack:
            open_tag = self.stack.pop()
            self.out.append(f"</{open_tag}>")
            if open_tag == tag:
                break

    def handle_data(self, data):
        self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def sanitize_html(text: str) -> str:
    """Returns Telegram-safe HTML: unknown tags removed, text escaped, tags balanced."""
    parser = _Sanitizer()
    parser.feed(text or "")
    parser.close()
    return parser.result().strip()


def strip_tags(text: str) -> str:
    """Plain text without any markup (for parse_mode=None fallbacks and embeddings)."""
    parser = _TextExtractor()
    parser.feed(text or "")
    parser.close()
    return "".join(parser.parts).strip()


def visible_length(text: str) -> int:
    """Length of the text as Telegram counts it: UTF-16 code units of the rendered text."""
    return len(strip_tags(text).encode("utf-16-le")) // 2


def _hard_split(paragraph: str, limit: int) -> List[str]:
    """Splits a paragraph that is too long on its own: by lines, then by words, markup dropped."""
    plain = strip_tags(paragraph)
    chunks, current = [], ""
    for word in plain.replace("\n", " \n ").split(" "):
        candidate = f"{current} {word}" if current else word
        if visible_length(html.escape(candidate)) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        # A single "word" longer than the limit (e.g. a URL) is cut as is
        while visible_length(html.escape(word)) > limit:
            chunks.append(word[:limit])
            word = word[limit:]
        current = word
    if current:
        chunks.append(current)
    return [html.escape(c.replace(" \n ", "\n").strip(), quote=False) for c in chunks if c.strip()]


def split_html(text: str, limit: int = MESSAGE_LIMIT) -> List[str]:
    """Splits sanitized HTML into chunks that each fit into `limit`, preferring paragraph boundaries."""
    text = sanitize_html(text)
    if visible_length(text) <= limit:
        return [text] if text else []

    chunks, current = [], ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if visible_length(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if visible_length(paragraph) <= limit:
            current = paragraph
        else:
            pieces = _hard_split(paragraph, limit)
            chunks.extend(pieces[:-1])
            current = pieces[-1] if pieces else ""
    if current:
        chunks.append(current)
    # Every chunk is re-sanitized so tags cut by the split are balanced again
    return [c for c in (sanitize_html(c) for c in chunks) if c]
