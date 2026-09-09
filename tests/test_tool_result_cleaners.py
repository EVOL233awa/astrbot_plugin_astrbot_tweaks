import json

from astrbot_tweaks.tool_result_cleaners import (
    clean_fetch_content,
    clean_tool_result,
    clean_web_search_content,
    truncate_tool_result,
)

HTML_SAMPLE = """
<!doctype html>
<html>
  <head>
    <title>Page Title</title>
    <style>body { color: red; }</style>
  </head>
  <body>
    <h1>Heading &amp; Text</h1>
    <script>window.track('hidden');</script>
    <p>First paragraph.</p>
    <svg><circle/></svg>
    <!-- hidden comment -->
    <p>Second paragraph.</p>
  </body>
</html>
"""


def test_truncate_tool_result_adds_notice() -> None:
    result = truncate_tool_result("a" * 12, 10)
    assert result.startswith("aaaaaaaaaa")
    assert "[Astrbot Tweaks: content truncated]" in result


def test_truncate_tool_result_keeps_short_content() -> None:
    assert truncate_tool_result("short", 10) == "short"


def test_clean_fetch_content_strips_html_noise() -> None:
    result = clean_fetch_content(HTML_SAMPLE)

    assert "Heading & Text" in result
    assert "First paragraph." in result
    assert "Second paragraph." in result
    assert "Page Title" in result
    assert "<script" not in result
    assert "window.track" not in result
    assert "<style" not in result
    assert "color: red" not in result
    assert "<svg" not in result
    assert "hidden comment" not in result


def test_clean_fetch_content_passes_markdown_through() -> None:
    markdown = "# Title\n\nSome **useful** text with `<code>`.\n"
    assert clean_fetch_content(markdown) == markdown


def test_clean_fetch_content_passes_json_through() -> None:
    value = '{"ok": true, "items": [1, 2]}'
    assert clean_fetch_content(value) == value


def test_clean_web_search_content_formats_top_k() -> None:
    payload = {
        "answer": "ignored answer",
        "results": [
            {"title": "First", "url": "https://example.com/1", "snippet": "A"},
            {"title": "Second", "url": "https://example.com/2", "snippet": "B"},
            {"title": "Third", "url": "https://example.com/3", "snippet": "C"},
        ],
    }
    result = clean_web_search_content(json.dumps(payload), top_k=2)

    assert "### Web Search Results" in result
    assert "First" in result
    assert "https://example.com/1" in result
    assert "Second" in result
    assert "Third" not in result
    assert "ignored answer" not in result


def test_clean_web_search_content_passes_malformed_payload() -> None:
    raw = "not-json"
    assert clean_web_search_content(raw, top_k=2) == raw


def test_clean_tool_result_dispatches_by_tool_name() -> None:
    result = clean_tool_result(
        "web_search_tavily",
        json.dumps(
            {"results": [{"title": "Only", "url": "https://example.com", "snippet": "ok"}]}
        ),
        {"subagent_search_top_k": 1},
    )
    assert "Only" in result


def test_clean_tool_result_respects_fetch_html_switch() -> None:
    result = clean_tool_result(
        "fetch",
        HTML_SAMPLE,
        {
            "subagent_clean_fetch_html": False,
            "subagent_direct_max_chars": 0,
        },
    )
    assert "<script" in result


def test_clean_tool_result_respects_web_search_switch() -> None:
    raw = '{"results":[{"title":"Only","url":"https://example.com","snippet":"ok"}]}'
    result = clean_tool_result(
        "web_search_tavily",
        raw,
        {
            "subagent_clean_web_search": False,
            "subagent_direct_max_chars": 0,
        },
    )
    assert result == raw


def test_clean_tool_result_truncates_non_web_tools() -> None:
    result = clean_tool_result(
        "read_text_file",
        "x" * 12,
        {"subagent_direct_max_chars": 10},
    )
    assert result.startswith("xxxxxxxxxx")
    assert "[Astrbot Tweaks: content truncated]" in result
