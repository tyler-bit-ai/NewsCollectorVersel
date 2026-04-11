"""
중복 제거 (카테고리 내 + 카테고리 간)
"""
from typing import List, Dict
import logging
from src.utils.helpers import canonicalize_link, clean_html, normalize_title

logger = logging.getLogger(__name__)


class Deduplicator:
    """중복 제거"""

    def __init__(self):
        self.seen_titles: set = set()
        self.seen_links: set = set()

    def deduplicate_within_category(self, articles: List[Dict]) -> List[Dict]:
        """
        동일 카테고리 내 중복 제거 (제목 + URL)

        Args:
            articles: 기사 리스트

        Returns:
            중복 제거된 기사 리스트
        """
        unique_articles = []

        for article in articles:
            # 제목 정규화
            clean_title = normalize_title(article['title'])
            link = canonicalize_link(article['link'])

            if clean_title in self.seen_titles:
                continue
            if link in self.seen_links:
                continue

            # HTML 태그 정리
            article['title'] = clean_html(article['title'])
            article['snippet'] = clean_html(article['snippet'])

            unique_articles.append(article)
            self.seen_titles.add(clean_title)
            self.seen_links.add(link)

        logger.info(f"Deduplication: {len(unique_articles)}/{len(articles)} unique")
        return unique_articles

    def deduplicate_cross_categories(self, articles: List[Dict]) -> List[Dict]:
        """
        카테고리 간 중복 제거 (URL 기반)

        Args:
            articles: 기사 리스트

        Returns:
            중복 제거된 기사 리스트
        """
        seen_links = {}
        seen_titles = {}
        unique_articles = []

        for article in articles:
            link = canonicalize_link(article['link'])
            clean_title = normalize_title(article['title'])

            if link not in seen_links and clean_title not in seen_titles:
                seen_links[link] = True
                seen_titles[clean_title] = True
                unique_articles.append(article)

        logger.info(f"Cross-category deduplication: {len(unique_articles)} unique")
        return unique_articles
