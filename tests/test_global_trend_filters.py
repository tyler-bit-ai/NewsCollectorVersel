from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from src.config.settings import APISettings, EmailSettings, RuntimeSettings, Settings
from src.filters.keyword_filter import KeywordFilter
from src.filters.time_filter import TimeFilter
from src.pipeline.core import collect_articles
from src.utils.time_windows import CollectionWindow


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
            safety_alert_recipients=["alert@example.com"],
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


class TimeFilterTests(unittest.TestCase):
    def test_filter_articles_can_exclude_missing_published(self):
        time_filter = TimeFilter(window_hours=24)

        filtered = time_filter.filter_articles(
            [{"title": "A", "published": None}],
            allow_missing_published=False,
        )

        self.assertEqual(filtered, [])


class GlobalTrendKeywordFilterTests(unittest.TestCase):
    def setUp(self):
        self.filter = KeywordFilter(
            blacklist_domains=[],
            excluded_keywords=[],
            global_trend_rules={
                "required_keywords": ["roaming", "mvno"],
                "required_topic_keywords": ["roaming", "mvno"],
                "required_signal_keywords": ["launch", "announced", "partnership"],
                "excluded_marketing_keywords": ["book a meeting", "download datasheet"],
                "excluded_url_patterns": ["/products/"],
            },
        )

    def test_global_trend_rejects_product_page(self):
        article = {
            "title": "MVNO Roaming Control Center",
            "link": "https://example.com/products/mvno-roaming-control-center",
            "snippet": "Book a meeting. Download datasheet for MVNO roaming services.",
            "query": "MVNO roaming services",
            "source_domain": "example.com",
        }

        self.assertFalse(self.filter.validate(article, category="global_trend"))

    def test_global_trend_accepts_newsworthy_article(self):
        article = {
            "title": "Carrier announced new MVNO roaming partnership",
            "link": "https://example.com/news/mvno-roaming-partnership",
            "snippet": "The operator announced a new roaming launch for travel eSIM users.",
            "query": "MVNO roaming services",
            "source_domain": "example.com",
        }

        self.assertTrue(self.filter.validate(article, category="global_trend"))


class CollectArticlesTests(unittest.TestCase):
    @patch("src.pipeline.core.load_categories")
    @patch("src.pipeline.core.get_collection_window_kst")
    @patch("src.pipeline.core.GoogleCollector")
    @patch("src.pipeline.core.NaverCollector")
    def test_collect_articles_limits_global_trend_and_requires_published_date(
        self,
        mock_naver_collector,
        mock_google_collector,
        mock_get_collection_window_kst,
        mock_load_categories,
    ):
        now = datetime.now(timezone.utc)
        mock_get_collection_window_kst.return_value = CollectionWindow(
            start_utc=now - timedelta(hours=24),
            end_utc=now + timedelta(minutes=1),
            start_kst=(now - timedelta(hours=24)).astimezone(timezone(timedelta(hours=9))),
            end_kst=(now + timedelta(minutes=1)).astimezone(timezone(timedelta(hours=9))),
            is_monday_special=False,
            label="test window",
        )
        mock_load_categories.return_value = {
            "categories": {
                "global_trend": {
                    "id": 1,
                    "name": "Global Roaming Trend",
                    "sources": ["google_search"],
                    "keywords": ["MVNO roaming services"],
                }
            },
            "filters": {
                "blacklist_domains": [],
                "excluded_keywords": [],
                "global_trend": {
                    "required_keywords": ["roaming", "mvno"],
                    "required_topic_keywords": ["roaming", "mvno"],
                    "required_signal_keywords": ["announced", "launch", "partnership"],
                    "excluded_marketing_keywords": [],
                    "excluded_url_patterns": [],
                },
            },
        }

        mock_naver_collector.return_value = object()
        mock_google_collector.return_value.collect.return_value = [
            {
                "title": "Carrier announced MVNO roaming launch",
                "link": "https://example.com/news/latest?utm_source=test",
                "snippet": "The operator announced a roaming partnership for MVNO users.",
                "source": "Google",
                "published": now,
                "published_raw": now.isoformat(),
                "freshness_source": "meta:date",
                "source_domain": "example.com",
                "query": "MVNO roaming services",
                "quality_flags": [],
                "type": "global",
            },
            {
                "title": "Carrier announced MVNO roaming launch duplicate",
                "link": "https://example.com/news/latest",
                "snippet": "The operator announced a roaming partnership for MVNO users.",
                "source": "Google",
                "published": now - timedelta(hours=1),
                "published_raw": (now - timedelta(hours=1)).isoformat(),
                "freshness_source": "meta:date",
                "source_domain": "example.com",
                "query": "MVNO roaming services",
                "quality_flags": [],
                "type": "global",
            },
            {
                "title": "Carrier announced MVNO roaming launch no date",
                "link": "https://example.com/news/no-date",
                "snippet": "The operator announced a roaming partnership for MVNO users.",
                "source": "Google",
                "published": None,
                "published_raw": "",
                "freshness_source": "",
                "source_domain": "example.com",
                "query": "MVNO roaming services",
                "quality_flags": ["missing_published_date"],
                "type": "global",
            },
        ]

        collected = collect_articles(build_settings(max_articles_per_category=1))

        self.assertEqual(len(collected["global_trend"]), 1)
        self.assertEqual(
            collected["global_trend"][0]["link"],
            "https://example.com/news/latest",
        )
