"""Environment-based settings for NewsCollector Vercel."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class APISettings:
    naver_client_id: str
    naver_client_secret: str
    google_api_key: str
    search_engine_id: str
    openai_api_key: str
    openai_base_url: str
    model_basic: str
    model_advanced: str


@dataclass(frozen=True)
class EmailSettings:
    gmail_user: str
    gmail_app_password: str
    report_recipients: List[str]
    safety_alert_recipients: List[str]


@dataclass(frozen=True)
class RuntimeSettings:
    debug_mode: bool
    dry_run: bool
    enable_0404_alerts: bool
    time_window_hours: int
    global_trend_window_hours: int
    max_articles_per_category: int
    email_top_n: int
    email_summary_max_chars: int
    cron_secret: str | None


@dataclass(frozen=True)
class Settings:
    api: APISettings
    email: EmailSettings
    runtime: RuntimeSettings

    @property
    def debug_mode(self) -> bool:
        return self.runtime.debug_mode

    @property
    def dry_run(self) -> bool:
        return self.runtime.dry_run

    @property
    def enable_0404_alerts(self) -> bool:
        return self.runtime.enable_0404_alerts

    @property
    def time_window_hours(self) -> int:
        return self.runtime.time_window_hours

    @property
    def global_trend_window_hours(self) -> int:
        return self.runtime.global_trend_window_hours

    @property
    def max_articles_per_category(self) -> int:
        return self.runtime.max_articles_per_category

    @property
    def email_top_n(self) -> int:
        return self.runtime.email_top_n

    @property
    def email_summary_max_chars(self) -> int:
        return self.runtime.email_summary_max_chars

    @property
    def cron_secret(self) -> str | None:
        return self.runtime.cron_secret


def load_settings() -> Settings:
    required_vars = {
        "NAVER_CLIENT_ID": os.getenv("NAVER_CLIENT_ID"),
        "NAVER_CLIENT_SECRET": os.getenv("NAVER_CLIENT_SECRET"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "SEARCH_ENGINE_ID": os.getenv("SEARCH_ENGINE_ID"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL"),
        "GMAIL_USER": os.getenv("GMAIL_USER"),
        "GMAIL_APP_PASSWORD": os.getenv("GMAIL_APP_PASSWORD"),
        "REPORT_RECIPIENTS": os.getenv("REPORT_RECIPIENTS"),
    }

    missing = [name for name, value in required_vars.items() if not value]
    if missing:
        raise ValueError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return Settings(
        api=APISettings(
            naver_client_id=required_vars["NAVER_CLIENT_ID"] or "",
            naver_client_secret=required_vars["NAVER_CLIENT_SECRET"] or "",
            google_api_key=required_vars["GOOGLE_API_KEY"] or "",
            search_engine_id=required_vars["SEARCH_ENGINE_ID"] or "",
            openai_api_key=required_vars["OPENAI_API_KEY"] or "",
            openai_base_url=required_vars["OPENAI_BASE_URL"] or "",
            model_basic=os.getenv("OPENAI_MODEL_BASIC", "gpt-4o-mini-2024-07-18"),
            model_advanced=os.getenv(
                "OPENAI_MODEL_ADVANCED", "gpt-4o-mini-2024-07-18"
            ),
        ),
        email=EmailSettings(
            gmail_user=required_vars["GMAIL_USER"] or "",
            gmail_app_password=required_vars["GMAIL_APP_PASSWORD"] or "",
            report_recipients=_parse_csv(required_vars["REPORT_RECIPIENTS"]),
            safety_alert_recipients=_parse_csv(os.getenv("SAFETY_ALERT_RECIPIENTS")),
        ),
        runtime=RuntimeSettings(
            debug_mode=_parse_bool(os.getenv("DEBUG_MODE"), False),
            dry_run=_parse_bool(os.getenv("DRY_RUN"), False),
            enable_0404_alerts=_parse_bool(os.getenv("ENABLE_0404_ALERTS"), True),
            time_window_hours=int(os.getenv("TIME_WINDOW_HOURS", "24")),
            global_trend_window_hours=int(
                os.getenv("GLOBAL_TREND_WINDOW_HOURS", "720")
            ),
            max_articles_per_category=int(
                os.getenv("MAX_ARTICLES_PER_CATEGORY", "10")
            ),
            email_top_n=int(os.getenv("EMAIL_TOP_N", "3")),
            email_summary_max_chars=int(
                os.getenv("EMAIL_SUMMARY_MAX_CHARS", "140")
            ),
            cron_secret=os.getenv("CRON_SECRET") or os.getenv("VERCEL_CRON_SECRET"),
        ),
    )
