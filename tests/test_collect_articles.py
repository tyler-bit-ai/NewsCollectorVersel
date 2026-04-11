from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from src.config.settings import APISettings, EmailSettings, RuntimeSettings, Settings
from src.pipeline.core import collect_articles


def build_settings(max_articles_per_category: int = 10) -> Settings:
    return Settings(
        api=APISettings(
            naver_client_id="naver-id",
            naver_client_secret="naver-secret",
            google_api_key="google-key",
            search_engine_id="search-id",
            openai_api_key="openai-key",
            openai_base_url="https://api.openai.com/v1",
            model_basic="model-basic",
            model_advanced="model-advanced",
        ),
        email=EmailSettings(
            gmail_user="sender@example.com",
            gmail_app_password="password",
            report_recipients=["report@example.com"],
            safety_alert_recipients=[],
        ),
        runtime=RuntimeSettings(
            debug_mode=False,
            dry_run=True,
            enable_0404_alerts=False,
            time_window_hours=24,
            max_articles_per_category=max_articles_per_category,
            email_top_n=3,
            email_summary_max_chars=140,
            cron_secret="secret-token",
        ),
    )


class CollectArticlesTests(unittest.TestCase):
    @patch("src.pipeline.core.load_categories")
    @patch("src.pipeline.core.GoogleCollector.collect")
    @patch("src.pipeline.core.NaverCollector.collect_from_news")
    def test_collect_articles_applies_max_and_cross_category_dedup(
        self,
        mock_collect_news,
        mock_collect_google,
        mock_load_categories,
    ):
        mock_load_categories.return_value = {
            "categories": {
                "competitors": {
                    "id": 2,
                    "name": "SKT & Competitors",
                    "content_type": "news",
                    "sources": ["naver_news"],
                    "keywords": ["KT 로밍"],
                    "include_keywords": ["로밍"],
                    "exclude_keywords": [],
                },
                "esim_industry": {
                    "id": 3,
                    "name": "eSIM Industry",
                    "content_type": "news",
                    "sources": ["naver_news"],
                    "keywords": ["Airalo"],
                    "include_keywords": ["esim"],
                    "exclude_keywords": [],
                },
            },
            "filters": {
                "blacklist_domains": [],
                "excluded_keywords": [],
                "global_trend": {
                    "excluded_domains": [],
                    "excluded_url_patterns": [],
                    "excluded_keywords": [],
                    "required_keywords": [],
                },
            },
        }
        mock_collect_google.return_value = []
        mock_collect_news.side_effect = [
            [
                {
                    "title": "KT 로밍 요금제 개편",
                    "snippet": "로밍 혜택을 강화했다.",
                    "link": "https://example.com/shared",
                    "source": "Naver News",
                    "published": datetime(2026, 4, 11, 0, 0, tzinfo=timezone.utc),
                },
                {
                    "title": "KT 로밍 데이터 혜택 확대",
                    "snippet": "데이터 로밍 제공량이 늘었다.",
                    "link": "https://example.com/competitors-2",
                    "source": "Naver News",
                    "published": datetime(2026, 4, 10, 0, 0, tzinfo=timezone.utc),
                },
            ],
            [
                {
                    "title": "Airalo eSIM 상품 확대",
                    "snippet": "eSIM 여행 통신 서비스를 확장했다.",
                    "link": "https://example.com/shared",
                    "source": "Naver News",
                    "published": datetime(2026, 4, 11, 1, 0, tzinfo=timezone.utc),
                },
                {
                    "title": "핀다이렉트 eSIM 제휴 확대",
                    "snippet": "eSIM 시장 확장 기사",
                    "link": "https://example.com/esim-2",
                    "source": "Naver News",
                    "published": datetime(2026, 4, 10, 1, 0, tzinfo=timezone.utc),
                },
            ],
        ]

        collected = collect_articles(build_settings(max_articles_per_category=1))

        self.assertEqual(len(collected["competitors"]), 1)
        self.assertEqual(collected["competitors"][0]["link"], "https://example.com/shared")
        self.assertEqual(len(collected["esim_industry"]), 0)

    @patch("src.pipeline.core.load_categories")
    @patch("src.pipeline.core.GoogleCollector.collect")
    @patch("src.pipeline.core.NaverCollector.collect_from_blog")
    @patch("src.pipeline.core.NaverCollector.collect_from_news")
    def test_collect_articles_preserves_higher_priority_category_after_cross_category_dedup(
        self,
        mock_collect_news,
        mock_collect_blog,
        mock_collect_google,
        mock_load_categories,
    ):
        mock_load_categories.return_value = {
            "categories": {
                "market_culture": {
                    "id": 0,
                    "priority": 5,
                    "name": "Market & Culture",
                    "content_type": "news",
                    "sources": ["naver_news"],
                    "keywords": ["일본 여행"],
                    "include_keywords": ["여행"],
                    "match_field": "combined",
                    "exclude_keywords": [],
                },
                "voc_roaming": {
                    "id": 4,
                    "priority": 0,
                    "name": "로밍 VoC",
                    "content_type": "voc",
                    "sources": ["naver_blog"],
                    "keywords": ["KT 로밍 후기"],
                    "include_keywords": ["로밍", "KT 로밍"],
                    "match_field": "title",
                    "exclude_keywords": [],
                },
            },
            "filters": {
                "blacklist_domains": [],
                "excluded_keywords": [],
                "global_trend": {
                    "excluded_domains": [],
                    "excluded_url_patterns": [],
                    "excluded_keywords": [],
                    "required_keywords": [],
                },
            },
        }
        mock_collect_google.return_value = []
        mock_collect_news.return_value = [
            {
                "title": "일본 여행 준비 체크리스트",
                "snippet": "해외 여행 준비 내용을 정리했다.",
                "link": "https://example.com/shared",
                "source": "Naver News",
                "published": datetime(2026, 4, 11, 0, 0, tzinfo=timezone.utc),
            }
        ]
        mock_collect_blog.return_value = [
            {
                "title": "KT 로밍 후기, 일본 여행에서 데이터 품질 점검",
                "snippet": "직접 사용 후기와 연결 품질을 정리했다.",
                "link": "https://example.com/shared",
                "source": "Naver Blog",
                "query": "KT 로밍 후기",
                "published": datetime(2026, 4, 11, 1, 0, tzinfo=timezone.utc),
            }
        ]

        collected = collect_articles(build_settings(max_articles_per_category=5))

        self.assertEqual(len(collected["market_culture"]), 0)
        self.assertEqual(len(collected["voc_roaming"]), 1)
        self.assertEqual(collected["voc_roaming"][0]["link"], "https://example.com/shared")

    @patch("src.pipeline.core.load_categories")
    @patch("src.pipeline.core.GoogleCollector.collect")
    @patch("src.pipeline.core.NaverCollector.collect_from_blog")
    def test_collect_articles_sorts_missing_published_confidence_last(
        self,
        mock_collect_blog,
        mock_collect_google,
        mock_load_categories,
    ):
        mock_load_categories.return_value = {
            "categories": {
                "voc_esim": {
                    "id": 5,
                    "priority": 1,
                    "name": "eSIM VoC",
                    "content_type": "voc",
                    "sources": ["naver_blog"],
                    "keywords": ["Airalo 후기"],
                    "include_keywords": ["Airalo"],
                    "match_field": "title",
                    "exclude_keywords": [],
                }
            },
            "filters": {
                "blacklist_domains": [],
                "excluded_keywords": [],
                "global_trend": {
                    "excluded_domains": [],
                    "excluded_url_patterns": [],
                    "excluded_keywords": [],
                    "required_keywords": [],
                },
            },
        }
        mock_collect_google.return_value = []
        mock_collect_blog.return_value = [
            {
                "title": "Airalo 후기",
                "snippet": "사용 후기와 개통 팁 정리",
                "link": "https://example.com/missing-date",
                "source": "Naver Blog",
                "query": "Airalo 후기",
                "published": None,
                "published_confidence": "missing",
            },
            {
                "title": "Airalo 리뷰",
                "snippet": "직접 사용 후기",
                "link": "https://example.com/date-only",
                "source": "Naver Blog",
                "query": "Airalo 후기",
                "published": datetime(2026, 4, 11, 0, 0, tzinfo=timezone.utc),
                "published_confidence": "date_only",
            },
        ]

        collected = collect_articles(build_settings(max_articles_per_category=2))

        self.assertEqual(len(collected["voc_esim"]), 2)
        self.assertEqual(collected["voc_esim"][0]["link"], "https://example.com/date-only")
        self.assertEqual(collected["voc_esim"][1]["link"], "https://example.com/missing-date")
