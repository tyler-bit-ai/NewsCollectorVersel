"""
Google Custom Search API 수집기
"""
import requests
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from typing import Any, Dict, List, Optional, Tuple
import logging
from urllib.parse import urlparse

from .base import BaseCollector
from src.utils.exceptions import APIError

logger = logging.getLogger(__name__)


SNIPPET_DATE_PATTERN = re.compile(
    r"^(?P<date>[A-Z][a-z]{2} \d{1,2}, \d{4})(?:\s+\.\.\.|\s+-|\s+\u00b7|\s+)"
)
DATE_META_KEYS = (
    "article:published_time",
    "article:modified_time",
    "og:published_time",
    "og:updated_time",
    "parsely-pub-date",
    "publishdate",
    "pubdate",
    "date",
    "dc.date",
    "dc.date.issued",
    "datepublished",
    "lastmod",
)


class GoogleCollector(BaseCollector):
    """Google Custom Search API 수집기"""

    def __init__(self, api_key: str, search_engine_id: str, debug_mode: bool = False):
        super().__init__(debug_mode)
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def _parse_datetime_value(self, raw_value: Any) -> Optional[datetime]:
        """Google 응답 메타데이터의 날짜 문자열을 UTC datetime으로 변환한다."""
        if raw_value is None:
            return None

        value = str(raw_value).strip()
        if not value:
            return None

        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass

        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            pass

        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return None

    def _extract_published_datetime(self, item: Dict[str, Any]) -> Tuple[Optional[datetime], str, str]:
        """Search item에서 게시일 후보를 추출한다."""
        pagemap = item.get("pagemap") or {}
        metatags = pagemap.get("metatags") or []

        for metatag in metatags:
            if not isinstance(metatag, dict):
                continue
            for key in DATE_META_KEYS:
                raw_value = metatag.get(key)
                published = self._parse_datetime_value(raw_value)
                if published:
                    return published, str(raw_value), f"meta:{key}"

        snippet = str(item.get("snippet") or "").strip()
        snippet_match = SNIPPET_DATE_PATTERN.match(snippet)
        if snippet_match:
            raw_value = snippet_match.group("date")
            published = self._parse_datetime_value(raw_value)
            if published:
                return published, raw_value, "snippet_prefix"

        return None, "", ""

    def _extract_source_domain(self, link: str) -> str:
        parsed = urlparse(str(link or ""))
        return parsed.netloc.lower()

    def collect(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Google Custom Search API 수집

        Args:
            query: 검색어
            limit: 수집 개수

        Returns:
            기사 리스트
        """
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": limit
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                raise APIError(f"Google API failed: {response.status_code}")

            data = response.json()
            items = data.get('items', [])

            articles = []
            for item in items:
                published, published_raw, freshness_source = self._extract_published_datetime(item)
                source_domain = self._extract_source_domain(item.get('link'))
                quality_flags = []
                if not published:
                    quality_flags.append('missing_published_date')

                article = {
                    'title': item.get('title'),
                    'link': item.get('link'),
                    'snippet': item.get('snippet'),
                    'source': 'Google',
                    'published': published,
                    'published_raw': published_raw,
                    'freshness_source': freshness_source,
                    'source_domain': source_domain,
                    'query': query,
                    'quality_flags': quality_flags,
                    'type': 'global'
                }

                articles.append(article)
                self.collected_count += 1

            return articles

        except requests.exceptions.Timeout:
            logger.error(f"Google API timeout: {query}")
            return []
        except Exception as e:
            logger.error(f"Google API exception: {e}")
            raise
