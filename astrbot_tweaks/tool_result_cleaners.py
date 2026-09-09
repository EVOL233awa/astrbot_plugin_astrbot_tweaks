"""SubAgent 直通结果的 CPU 侧内容清洗与截断。"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

TRUNCATION_NOTICE = "[Astrbot Tweaks: content truncated]"

_HTML_TAG_RE = re.compile(
    r"<(?:!doctype\s+html|html|body|div|p|h[1-6]|script|style|svg)\b",
    re.IGNORECASE,
)
_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
)
_IGNORED_TAGS = frozenset({"script", "style", "svg", "noscript", "template"})


class _HTMLTextExtractor(HTMLParser):
    """提取 HTML 正文并移除低价值标签。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in _IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if normalized in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in _IGNORED_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if normalized in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0 and data:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def truncate_tool_result(content: str, max_chars: int) -> str:
    """硬截断超长工具结果，避免撑爆主模型上下文。"""
    if max_chars <= 0 or len(content) <= max_chars:
        return content
    return f"{content[:max_chars]}\n\n{TRUNCATION_NOTICE}"


def _looks_like_html(content: str) -> bool:
    stripped = content.lstrip()
    lowered = stripped.lower()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html") or bool(
        _HTML_TAG_RE.search(lowered)
    )


def clean_fetch_content(content: str) -> str:
    """fetch 默认返回 Markdown/JSON 时穿透，仅清洗 HTML。"""
    if not _looks_like_html(content):
        return content

    parser = _HTMLTextExtractor()
    parser.feed(content)
    parser.close()
    lines = [
        _WHITESPACE_RE.sub(" ", line).strip()
        for line in parser.get_text().splitlines()
    ]
    return "\n".join(line for line in lines if line)


def clean_web_search_content(content: str, top_k: int = 4) -> str:
    """清洗 AstrBot 当前规范化的 Tavily JSON 结果。"""
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return content

    if not isinstance(payload, dict):
        return content
    results = payload.get("results")
    if not isinstance(results, list):
        return content

    limit = max(0, top_k)
    selected = results if limit == 0 else results[:limit]
    lines = ["### Web Search Results"]
    for index, item in enumerate(selected, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Untitled")
        url = str(item.get("url") or "")
        snippet = str(item.get("snippet") or "").replace("\n", " ").strip()
        lines.append("")
        lines.append(f"{index}. {title}")
        if url:
            lines.append(url)
        if snippet:
            lines.append(snippet)
    if len(lines) == 1:
        lines.append("No web search results.")
    return "\n".join(lines)


def clean_tool_result(
    tool_name: str,
    content: str,
    config: dict[str, Any],
) -> str:
    """按工具选择清洗策略，并对所有结果执行安全截断。"""
    if tool_name == "fetch":
        cleaned = (
            clean_fetch_content(content)
            if bool(config.get("subagent_clean_fetch_html", True))
            else content
        )
    elif tool_name == "web_search_tavily":
        if bool(config.get("subagent_clean_web_search", True)):
            top_k = int(config.get("subagent_search_top_k", 4))
            cleaned = clean_web_search_content(content, top_k=top_k)
        else:
            cleaned = content
    else:
        cleaned = content

    max_chars = int(config.get("subagent_direct_max_chars", 30000))
    return truncate_tool_result(cleaned, max_chars=max_chars)
