import unittest

from src.notifiers.email_formatter import EmailFormatter
from src.notifiers.smtp_sender import SMTPSender


class EmailFormatterTests(unittest.TestCase):
    def test_format_includes_core_sections(self):
        formatter = EmailFormatter(top_n=2, summary_max_chars=80)
        html = formatter.format(
            {
                "strategic_insight": "Insight",
                "key_findings": ["Finding A"],
                "recommendations": ["Recommendation A"],
                "section_market_culture": [
                    {
                        "title": "Article A",
                        "summary": "Summary A",
                        "link": "https://example.com/a",
                        "source": "naver",
                    }
                ],
                "section_esim_industry": [
                    {
                        "title": "Airalo eSIM 기사",
                        "summary": "Summary B",
                        "link": "https://example.com/b",
                        "source": "naver",
                    }
                ],
                "external_alerts": [],
            }
        )

        self.assertIn("SKT 로밍팀 일일 뉴스 리포트", html)
        self.assertIn("Insight", html)
        self.assertIn("Article A", html)
        self.assertIn("eSIM Industry", html)

    def test_smtp_sender_dry_run_returns_metadata(self):
        result = SMTPSender("sender@example.com", "password").send(
            html_content="<b>test</b>",
            recipients=["a@example.com"],
            dry_run=True,
        )

        self.assertTrue(result.dry_run)
        self.assertEqual(result.recipients, ["a@example.com"])
        self.assertIn("[SKT 로밍팀] 일일 뉴스 리포트", result.subject)
