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

    def _base_required_env(self) -> dict:
        return {
            "NAVER_CLIENT_ID": "naver-id",
            "NAVER_CLIENT_SECRET": "naver-secret",
            "GOOGLE_API_KEY": "google-key",
            "SEARCH_ENGINE_ID": "search-id",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "GMAIL_USER": "sender@example.com",
            "GMAIL_APP_PASSWORD": "app-password",
            "REPORT_RECIPIENTS": "a@example.com",
        }

    def test_cache_settings_prefers_vercel_kv_env_vars(self):
        env = {
            **self._base_required_env(),
            "KV_REST_API_URL": "https://kv.example.com",
            "KV_REST_API_TOKEN": "kv-token",
            "UPSTASH_REDIS_REST_URL": "https://upstash.example.com",
            "UPSTASH_REDIS_REST_TOKEN": "upstash-token",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = load_settings()

        self.assertEqual(settings.cache.upstash_redis_url, "https://kv.example.com")
        self.assertEqual(settings.cache.upstash_redis_token, "kv-token")

    def test_cache_settings_falls_back_to_upstash_env_vars(self):
        env = {
            **self._base_required_env(),
            "UPSTASH_REDIS_REST_URL": "https://upstash.example.com",
            "UPSTASH_REDIS_REST_TOKEN": "upstash-token",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = load_settings()

        self.assertEqual(settings.cache.upstash_redis_url, "https://upstash.example.com")
        self.assertEqual(settings.cache.upstash_redis_token, "upstash-token")

    def test_cache_settings_none_when_no_redis_env_vars(self):
        with patch.dict(os.environ, self._base_required_env(), clear=True):
            settings = load_settings()

        self.assertIsNone(settings.cache.upstash_redis_url)
        self.assertIsNone(settings.cache.upstash_redis_token)
