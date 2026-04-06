import json
import unittest
from unittest.mock import patch

import api.cron as cron
from src.config.settings import APISettings, EmailSettings, RuntimeSettings, Settings


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
            max_articles_per_category=10,
            email_top_n=3,
            email_summary_max_chars=140,
            cron_secret="secret-token",
        ),
    )


class VercelHandlerTests(unittest.TestCase):
    @patch("api.cron.run_daily_job")
    @patch("api.cron.load_settings")
    def test_cron_handler_returns_summary_when_authorized(
        self,
        mock_load_settings,
        mock_run_daily_job,
    ):
        mock_load_settings.return_value = build_settings()
        mock_run_daily_job.return_value = {"trigger": "vercel-cron", "ok": True}
        captured = {}

        response_iterable = cron.app(
            {"REQUEST_METHOD": "GET", "HTTP_AUTHORIZATION": "Bearer secret-token"},
            lambda status, headers: captured.update({"status": status, "headers": headers}),
        )
        payload = json.loads(b"".join(response_iterable).decode("utf-8"))

        self.assertEqual(captured["status"], "200 OK")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["summary"]["trigger"], "vercel-cron")

    @patch("api.cron.load_settings")
    def test_cron_handler_rejects_invalid_secret(self, mock_load_settings):
        mock_load_settings.return_value = build_settings()
        captured = {}

        response_iterable = cron.app(
            {"REQUEST_METHOD": "GET", "HTTP_AUTHORIZATION": "Bearer wrong-token"},
            lambda status, headers: captured.update({"status": status, "headers": headers}),
        )
        payload = json.loads(b"".join(response_iterable).decode("utf-8"))

        self.assertEqual(captured["status"], "401 ERROR")
        self.assertFalse(payload["success"])
