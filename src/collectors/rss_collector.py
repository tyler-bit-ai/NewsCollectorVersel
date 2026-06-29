"""
RSS/Atom 피드 수집기
"""
import calendar
import html
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

import feedparser
import requests

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

logger = logging.getLogger(__name__)

SOURCE_QUALITY_WEIGHTS: Dict[str, float] = {
    "rcrwireless.com": 1.3,
    "telegeography.com": 1.5,
    "gsma.com": 1.5,
    "fiercewireless.com": 1.2,
    "totaltele.com": 1.2,
    "mobileworldlive.com": 1.2,
    "telecomstechnews.com": 1.1,
    "ppomppu.co.kr": 1.0,
}

_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}


class RSSCollector:
    """RSS/Atom 피드 수집기"""

    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.collected_count = 0

    def collect(
        self,
        feed_url: str,
        limit: int = 20,
        source_name: str = "",
        quality_weight: float = 1.0,
        topic_hint: str = "",
        article_type: str = "global",
    ) -> List[Dict]:
        """
        RSS 피드 수집

        Args:
            feed_url: RSS/Atom URL
            limit: 최대 수집 건수
            source_name: 소스 표시 이름
            quality_weight: 소스 품질 가중치 (relevance_score 산정에 활용)
            topic_hint: 기사의 query 필드에 주입할 토픽 힌트 (키워드 필터 통과에 활용)
            article_type: 'global' 또는 'domestic'
        """
        try:
            response = requests.get(feed_url, headers=_FETCH_HEADERS, timeout=15, allow_redirects=True)
            response.raise_for_status()
            d = feedparser.parse(response.content)
        except requests.exceptions.RequestException as exc:
            logger.warning("RSS fetch failed %s: %s", feed_url, exc)
            return []
        except Exception as exc:
            logger.error("RSS parse exception %s: %s", feed_url, exc)
            return []

        if not d.entries:
            logger.warning("RSS feed empty or malformed: %s", feed_url)
            return []

        source_domain = self._extract_domain(feed_url)
        effective_weight = SOURCE_QUALITY_WEIGHTS.get(source_domain, quality_weight)
        display_name = source_name or source_domain

        articles = []
        for entry in d.entries[:limit]:
            article = self._parse_entry(
                entry,
                source_domain=source_domain,
                source_name=display_name,
                quality_weight=effective_weight,
                topic_hint=topic_hint,
                article_type=article_type,
            )
            if article:
                articles.append(article)
                self.collected_count += 1

        logger.info("RSS %s (%s): %d articles", display_name, feed_url, len(articles))
        return articles

    def _parse_entry(
        self,
        entry,
        source_domain: str,
        source_name: str,
        quality_weight: float,
        topic_hint: str,
        article_type: str,
    ) -> Optional[Dict]:
        title = getattr(entry, "title", None)
        link = getattr(entry, "link", None)
        if not title or not link:
            return None

        published = self._parse_published(entry)

        snippet = self._extract_snippet(entry)
        rss_content = self._extract_content(entry) or snippet

        return {
            "title": title,
            "link": link,
            "snippet": snippet,
            "rss_content": rss_content,
            "source": f"RSS:{source_name}",
            "source_domain": source_domain,
            "published": published,
            "published_confidence": "exact" if published else "missing",
            "published_raw": str(published) if published else "",
            "freshness_source": "rss_published",
            "query": topic_hint,
            "type": article_type,
            "quality_flags": [] if published else ["missing_published_date"],
            "rss_quality_weight": quality_weight,
        }

    def _parse_published(self, entry) -> Optional[datetime]:
        for attr in ("published_parsed", "updated_parsed"):
            timetuple = getattr(entry, attr, None)
            if timetuple:
                try:
                    ts = calendar.timegm(timetuple)
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                except (TypeError, ValueError, OverflowError):
                    continue
        return None

    def _strip_html(self, text: str) -> str:
        stripped = _HTML_TAG_RE.sub(" ", str(text or ""))
        decoded = html.unescape(stripped)
        return _WHITESPACE_RE.sub(" ", decoded).strip()

    def _extract_snippet(self, entry) -> str:
        if hasattr(entry, "summary") and entry.summary:
            return self._strip_html(entry.summary)
        if hasattr(entry, "content") and entry.content:
            return self._strip_html(entry.content[0].get("value", ""))
        return ""

    def _extract_content(self, entry) -> str:
        if hasattr(entry, "content") and entry.content:
            return self._strip_html(entry.content[0].get("value", ""))
        return ""

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(str(url or ""))
        return parsed.netloc.lower()
