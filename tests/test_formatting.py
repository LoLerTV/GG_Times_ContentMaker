from processing.formatting import CAPTION_LIMIT, MESSAGE_LIMIT, sanitize_html, split_html, strip_tags, visible_length


def test_unclosed_tags_are_closed():
    assert sanitize_html("<b>Crimson Desert завезёт") == "<b>Crimson Desert завезёт</b>"


def test_unknown_tags_dropped_text_kept():
    assert sanitize_html("<h1>Заголовок</h1> <div>текст</div>") == "Заголовок текст"


def test_stray_closing_tag_dropped():
    assert sanitize_html("текст</b> дальше") == "текст дальше"


def test_misnested_tags_fixed():
    assert sanitize_html("<b><i>x</b>y</i>") == "<b><i>x</i></b>y"


def test_text_is_escaped():
    assert sanitize_html("5 < 7 & <b>PS5</b>") == "5 &lt; 7 &amp; <b>PS5</b>"


def test_telegram_specific_tags_kept():
    src = '<blockquote expandable>список</blockquote><tg-spoiler>слив</tg-spoiler><span class="tg-spoiler">s</span>'
    assert sanitize_html(src) == src


def test_disallowed_attributes_and_spans_removed():
    assert sanitize_html('<b style="x">a</b><span class="red">b</span><a onclick="x" href="https://t.me">c</a>') == \
        '<b>a</b>b<a href="https://t.me">c</a>'


def test_br_becomes_newline():
    assert sanitize_html("a<br>b") == "a\nb"


def test_visible_length_ignores_markup_and_counts_utf16():
    assert visible_length("<b>abc</b>") == 3
    assert visible_length("&amp;") == 1
    assert visible_length("🎮") == 2


def test_short_text_not_split():
    assert split_html("<b>коротко</b>") == ["<b>коротко</b>"]


def test_split_on_paragraphs_within_limit():
    paragraphs = [f"<b>Абзац {i}</b> " + "слово " * 150 for i in range(10)]
    chunks = split_html("\n\n".join(paragraphs), CAPTION_LIMIT)
    assert len(chunks) > 1
    for chunk in chunks:
        assert visible_length(chunk) <= CAPTION_LIMIT
        assert chunk == sanitize_html(chunk)
    assert strip_tags("\n\n".join(chunks)).split() == strip_tags("\n\n".join(paragraphs)).split()


def test_huge_single_paragraph_is_hard_split():
    text = "игра " * 3000 + "x" * 5000
    chunks = split_html(text, MESSAGE_LIMIT)
    assert all(visible_length(c) <= MESSAGE_LIMIT for c in chunks)
    assert "".join(strip_tags(c) for c in chunks).replace(" ", "") == text.replace(" ", "")


def test_split_inside_blockquote_stays_balanced():
    text = "<blockquote expandable>" + "\n\n".join("пункт " * 100 for _ in range(5)) + "</blockquote>"
    for chunk in split_html(text, CAPTION_LIMIT):
        assert chunk.count("<blockquote") == chunk.count("</blockquote>")
