"""SMTP sender for NewsCollector Vercel."""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from src.utils.exceptions import NotificationError
from src.utils.retry import retry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailSendResult:
    subject: str
    recipients: List[str]
    dry_run: bool


class SMTPSender:
    """SMTP-based email sender."""

    def __init__(self, user: str, password: str):
        self.user = user
        self.password = password

    @retry(max_attempts=3)
    def send(
        self,
        html_content: str,
        recipients: List[str],
        subject_prefix: str = "[SKT 로밍팀] 일일 뉴스 리포트",
        dry_run: bool = False,
    ) -> EmailSendResult:
        subject = f"{subject_prefix} - {datetime.now().strftime('%Y-%m-%d')}"

        if dry_run:
            logger.info("Dry-run email prepared for %s recipients", len(recipients))
            return EmailSendResult(
                subject=subject,
                recipients=list(recipients),
                dry_run=True,
            )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.user
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_content, "html", _charset="utf-8"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.user, self.password)
                server.send_message(msg)
        except Exception as exc:
            logger.error("Email send failed: %s", exc)
            raise NotificationError(f"이메일 발송 실패: {exc}") from exc

        logger.info("Email sent to %s recipients", len(recipients))
        return EmailSendResult(
            subject=subject,
            recipients=list(recipients),
            dry_run=False,
        )
