"""
키워드 필터링 (스팸, 광고, 게임)
"""
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class KeywordFilter:
    """키워드 기반 필터링"""

    def __init__(
        self,
        blacklist_domains: List[str],
        excluded_keywords: List[str],
        global_trend_rules: Optional[Dict] = None,
    ):
        """
        Args:
            blacklist_domains: 블랙리스트 도메인 패턴
            excluded_keywords: 제외 키워드
        """
        self.blacklist_domains: Set[str] = set(blacklist_domains)
        self.excluded_keywords: Set[str] = set(kw.lower() for kw in excluded_keywords)
        rules = global_trend_rules or {}
        self.global_trend_excluded_domains: Set[str] = set(
            value.lower() for value in rules.get("excluded_domains", [])
        )
        self.global_trend_excluded_url_patterns: Set[str] = set(
            value.lower() for value in rules.get("excluded_url_patterns", [])
        )
        self.global_trend_excluded_keywords: Set[str] = set(
            value.lower() for value in rules.get("excluded_keywords", [])
        )
        self.global_trend_required_keywords: Set[str] = set(
            value.lower() for value in rules.get("required_keywords", [])
        )

    def _validate_global_trend(self, article: Dict) -> bool:
        link = str(article.get('link', '')).lower()
        title = str(article.get('title', '')).lower()
        snippet = str(article.get('snippet', '')).lower()
        query = str(article.get('query', '')).lower()
        source_domain = str(article.get('source_domain', '')).lower()
        combined_text = f"{title} {snippet} {query}".strip()

        if any(domain in source_domain for domain in self.global_trend_excluded_domains):
            logger.debug(f"Filtered global_trend by domain: {source_domain}")
            return False

        if any(pattern in link for pattern in self.global_trend_excluded_url_patterns):
            logger.debug(f"Filtered global_trend by URL pattern: {link}")
            return False

        if any(keyword in combined_text for keyword in self.global_trend_excluded_keywords):
            logger.debug(f"Filtered global_trend by excluded keyword: {title[:50]}")
            return False

        if self.global_trend_required_keywords and not any(
            keyword in combined_text for keyword in self.global_trend_required_keywords
        ):
            logger.debug(f"Filtered global_trend by missing required keyword: {title[:50]}")
            return False

        return True

    def validate(self, article: Dict, category: str = "") -> bool:
        """
        기사 검증

        Args:
            article: 기사 딕셔너리
            category: 카테고리 키

        Returns:
            유효하면 True
        """
        link = article.get('link', '')
        title = article.get('title', '').lower()
        snippet = article.get('snippet', '').lower()

        # 1. Cafe/Blog URL 필터링 (News API에서 반환되는 경우)
        if 'cafe.naver.com' in link or 'blog.naver.com' in link:
            if article.get('source') == 'Naver News':
                logger.debug(f"Filtered: Cafe/Blog URL in News API")
                return False

        # 2. 블랙리스트 도메인
        if any(blocked in link for blocked in self.blacklist_domains):
            logger.debug(f"Filtered: URL blacklist - {title[:50]}")
            return False

        # 3. 제외 키워드 (제목 + 요약)
        combined_text = f"{title} {snippet}"
        for bad_word in self.excluded_keywords:
            if bad_word in combined_text:
                logger.debug(f"Filtered: Keyword '{bad_word}' - {title[:50]}")
                return False

        # 4. URL에 포함된 키워드
        if any(bad_word in link.lower() for bad_word in self.excluded_keywords):
            logger.debug(f"Filtered: Link keyword - {title[:50]}")
            return False

        if category == "global_trend" and not self._validate_global_trend(article):
            return False

        return True

    def filter_articles(self, articles: List[Dict], category: str = "") -> List[Dict]:
        """
        기사 리스트 키워드 필터링

        Args:
            articles: 기사 리스트
            category: 카테고리 키

        Returns:
            필터링된 기사 리스트
        """
        filtered = [a for a in articles if self.validate(a, category=category)]
        logger.info(f"Keyword filter: {len(filtered)}/{len(articles)} passed")
        return filtered
