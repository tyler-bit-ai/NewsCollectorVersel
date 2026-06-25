import unittest
from unittest.mock import patch

from src.config.settings import APISettings, EmailSettings, RuntimeSettings, Settings
from src.pipeline.daily_job import run_daily_job


def build_settings() -> Settings:
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
            enable_0404_alerts=True,
            time_window_hours=24,
            global_trend_window_hours=720,
            max_articles_per_category=10,
            email_top_n=3,
            email_summary_max_chars=140,
            cron_secret="secret-token",
        ),
    )


class DailyJobTests(unittest.TestCase):
    @patch("src.pipeline.daily_job.collect_external_alerts")
    @patch("src.pipeline.daily_job.analyze_articles")
    @patch("src.pipeline.daily_job.collect_articles")
    def test_run_daily_job_returns_summary_for_dry_run(
        self,
        mock_collect_articles,
        mock_analyze_articles,
        mock_collect_external_alerts,
    ):
        mock_collect_articles.return_value = {
            "market_culture": [{"title": "A", "link": "https://example.com", "snippet": "S"}]
        }
        mock_analyze_articles.return_value = {
            "strategic_insight": "Insight",
            "key_findings": ["Finding"],
            "recommendations": ["Recommendation"],
            "section_market_culture": [
                {
                    "title": "A",
                    "summary": "Summary",
                    "link": "https://example.com",
                    "source": "naver",
                }
            ],
        }
        mock_collect_external_alerts.return_value = [
            {
                "title": "Alert",
                "content_one_line": "Alert summary",
                "link": "https://example.com/alert",
                "board_name": "0404",
            }
        ]

        summary = run_daily_job(settings=build_settings(), trigger="test")

        self.assertTrue(summary["dry_run"])
        self.assertEqual(summary["collected_article_count"], 1)
        self.assertEqual(summary["external_alert_count"], 1)
        self.assertTrue(summary["report_email"]["sent"])
        self.assertTrue(summary["safety_alert_email"]["sent"])
