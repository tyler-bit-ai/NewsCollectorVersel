import os
import unittest
from unittest.mock import patch

from src.config.settings import load_settings


class SettingsTests(unittest.TestCase):
    def test_load_settings_raises_for_missing_required_variables(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                load_settings()

        self.assertIn("Missing required environment variables", str(context.exception))

    def test_load_settings_parses_runtime_flags_and_recipient_lists(self):
        env = {
            "NAVER_CLIENT_ID": "naver-id",
            "NAVER_CLIENT_SECRET": "naver-secret",
            "GOOGLE_API_KEY": "google-key",
            "SEARCH_ENGINE_ID": "search-id",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "GMAIL_USER": "sender@example.com",
            "GMAIL_APP_PASSWORD": "app-password",
            "REPORT_RECIPIENTS": "a@example.com, b@example.com",
            "SAFETY_ALERT_RECIPIENTS": "alert@example.com",
            "ENABLE_0404_ALERTS": "true",
            "DRY_RUN": "true",
            "CRON_SECRET": "secret-token",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = load_settings()

        self.assertTrue(settings.dry_run)
        self.assertTrue(settings.enable_0404_alerts)
        self.assertEqual(settings.email.report_recipients, ["a@example.com", "b@example.com"])
        self.assertEqual(settings.email.safety_alert_recipients, ["alert@example.com"])
        self.assertEqual(settings.cron_secret, "secret-token")
