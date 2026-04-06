"""Daily news job orchestration for local and Vercel execution."""

from __future__ import annotations

from typing import Any, Dict, List

from src.config.settings import Settings
from src.notifiers.email_formatter import EmailFormatter
from src.notifiers.smtp_sender import SMTPSender
from src.pipeline.core import analyze_articles, collect_articles, collect_external_alerts
from src.utils.logger import setup_logger


def _section_counts(analyzed_data: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for key, value in analyzed_data.items():
        if key.startswith("section_") and isinstance(value, list):
            counts[key.replace("section_", "")] = len(value)
    return counts


def _safe_send(
    sender: SMTPSender,
    html_content: str,
    recipients: List[str],
    subject_prefix: str,
    dry_run: bool,
) -> Dict[str, Any]:
    if not recipients:
        return {
            "sent": False,
            "skipped": True,
            "reason": "no_recipients",
            "recipient_count": 0,
            "subject": subject_prefix,
        }

    result = sender.send(
        html_content=html_content,
        recipients=recipients,
        subject_prefix=subject_prefix,
        dry_run=dry_run,
    )
    return {
        "sent": True,
        "skipped": False,
        "dry_run": result.dry_run,
        "recipient_count": len(result.recipients),
        "subject": result.subject,
    }


def run_daily_job(settings: Settings, trigger: str = "unknown") -> Dict[str, Any]:
    logger = setup_logger(debug_mode=settings.debug_mode)
    logger.info("=== Daily job started (%s) ===", trigger)

    collected_data = collect_articles(settings)
    analyzed_data = analyze_articles(collected_data, settings)

    alerts: List[Dict[str, Any]] = []
    if settings.enable_0404_alerts:
        try:
            alerts = collect_external_alerts(settings)
        except Exception as exc:
            logger.error("0404 alert collection failed: %s", exc)
            alerts = []
    analyzed_data["external_alerts"] = alerts

    formatter = EmailFormatter(
        top_n=settings.email_top_n,
        summary_max_chars=settings.email_summary_max_chars,
    )
    sender = SMTPSender(
        user=settings.email.gmail_user,
        password=settings.email.gmail_app_password,
    )

    report_html = formatter.format(analyzed_data)
    report_result = _safe_send(
        sender=sender,
        html_content=report_html,
        recipients=settings.email.report_recipients,
        subject_prefix="[SKT 로밍팀] 일일 뉴스 리포트",
        dry_run=settings.dry_run,
    )

    safety_alert_result: Dict[str, Any]
    if settings.enable_0404_alerts and alerts:
        alert_html = formatter.format_safety_alert_digest(alerts)
        safety_alert_result = _safe_send(
            sender=sender,
            html_content=alert_html,
            recipients=settings.email.safety_alert_recipients,
            subject_prefix="[SKT 로밍팀] 해외 안전 공지 알림",
            dry_run=settings.dry_run,
        )
    else:
        safety_alert_result = {
            "sent": False,
            "skipped": True,
            "reason": "alerts_disabled_or_empty",
            "recipient_count": 0,
            "subject": "[SKT 로밍팀] 해외 안전 공지 알림",
        }

    summary = {
        "trigger": trigger,
        "dry_run": settings.dry_run,
        "collected_category_count": len(collected_data),
        "collected_article_count": sum(len(items) for items in collected_data.values()),
        "section_counts": _section_counts(analyzed_data),
        "external_alert_count": len(alerts),
        "report_email": report_result,
        "safety_alert_email": safety_alert_result,
    }
    logger.info("=== Daily job completed ===")
    return summary
