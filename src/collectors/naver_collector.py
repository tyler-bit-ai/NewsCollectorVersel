"""
Naver API 수집기
"""
import requests
import urllib.parse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import List, Dict
import logging
import time

from .base import BaseCollector
from src.utils.exceptions import APIError, RateLimitError

logger = logging.getLogger(__name__)


class NaverCollector(BaseCollector):
    """Naver Search API 수집기"""

    def __init__(self, client_id: str, client_secret: str, debug_mode: bool = False):
        super().__init__(debug_mode)
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://openapi.naver.com/v1/search"
        self.request_delay = 0.3  # API 요청 간 딜레이 (초)
        self.last_request_time = 0

    def collect(self, query: str, limit: int = 5) -> List[Dict]:
        """
        기본 수집 메서드 (News API 사용)

        Args:
            query: 검색어
            limit: 수집 개수

        Returns:
            기사 리스트
        """
        return self.collect_from_news(query, limit)

    def collect_from_news(self, query: str, limit: int = 5) -> List[Dict]:
        """Naver News API 수집"""
        return self._call_api("news", query, limit)

    def collect_from_blog(self, query: str, limit: int = 5) -> List[Dict]:
        """Naver Blog API 수집"""
        return self._call_api("blog", query, limit)

    def collect_from_cafe(self, query: str, limit: int = 5) -> List[Dict]:
        """Naver Cafe API 수집"""
        return self._call_api("cafearticle", query, limit)

    def _call_api(self, endpoint: str, query: str, limit: int) -> List[Dict]:
        """
        Naver API 공통 호출

        Args:
            endpoint: 'news', 'blog', 'cafearticle'
            query: 검색어
            limit: 수집 개수

        Returns:
            기사 리스트

        Raises:
            APIError: API 호출 실패
        """
        # API 요청 간 딜레이 적용 (rate limit 방지)
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.request_delay:
            time.sleep(self.request_delay - time_since_last_request)

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }

        params = {
            "query": query,
            "display": limit,
            "sort": "date"
        }

        try:
            self.last_request_time = time.time()
            response = requests.get(
                f"{self.base_url}/{endpoint}.json",
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code == 429:
                logger.warning(f"Naver API rate limit exceeded for query: {query}")
                return []

            if response.status_code != 200:
                logger.error(f"Naver API failed: {response.status_code}")
                return []

            data = response.json()
            return self._parse_items(data.get('items', []), endpoint, query)

        except requests.exceptions.Timeout:
            logger.error(f"Naver API timeout: {query}")
            return []
        except RateLimitError:
            logger.warning(f"Naver API rate limit exceeded for query: {query}")
            return []
        except Exception as e:
            logger.error(f"Naver API exception: {e}")
            return []

    def _parse_items(self, items: List[Dict], endpoint: str, query: str) -> List[Dict]:
        """API 응답 파싱"""
        parsed_articles = []

        for item in items:
            # 시간 파싱
            if endpoint == "news":
                pub_date = parsedate_to_datetime(item.get('pubDate'))
                published_confidence = "exact" if pub_date else "missing"
            else:  # blog, cafe
                raw_date = item.get('postdate')
                if not raw_date:
                    logger.warning(f"Missing postdate for item: {item.get('link', 'unknown')}")
                    pub_date = None
                    published_confidence = "missing"
                else:
                    pub_date = datetime.strptime(raw_date, "%Y%m%d")
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                    published_confidence = "date_only"

            # 링크 정제
            clean_link = self._clean_naver_link(item.get('link', ''), endpoint)

            article = {
                'title': item.get('title'),
                'link': clean_link,
                'snippet': item.get('description'),
                'source': f"Naver {endpoint.capitalize()}",
                'published': pub_date,
                'published_confidence': published_confidence,
                'query': query,
                'type': 'domestic'
            }

            parsed_articles.append(article)
            self.collected_count += 1

        return parsed_articles

    def _clean_naver_link(self, link: str, category: str) -> str:
        """
        Naver 링크 정제 (리디렉트/랜딩 페이지 제거)

        Args:
            link: 원본 링크
            category: 'news', 'blog', 'cafe'

        Returns:
            정제된 링크
        """
        # Blog 프로모션 페이지
        if '/blog.naver.com/' in link and ('/Promotion' in link or 'blogId=' in link):
            parsed = urllib.parse.urlparse(link)
            params = urllib.parse.parse_qs(parsed.query)

            blog_id = params.get('blogId', [''])[0]
            log_no = params.get('logNo', [''])[0]

            if blog_id and log_no:
                return f"https://blog.naver.com/{blog_id}/{log_no}"

        # Cafe 랜딩 페이지
        if '/cafe.naver.com/' in link:
            parsed = urllib.parse.urlparse(link)
            path_parts = parsed.path.split('/')

            cafe_id = None
            article_id = None

            for part in path_parts:
                if part and part not in ['', 'cafe.naver.com', 'nview', 'ca-fe', 'cafes', 'articles']:
                    if not cafe_id:
                        cafe_id = part
                    elif not article_id:
                        article_id = part
                        break

            if cafe_id and article_id:
                return f"https://cafe.naver.com/{cafe_id}/{article_id}"

        return link
