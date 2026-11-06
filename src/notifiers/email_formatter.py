"""
HTML 이메일 생성
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import html as html_lib
from pathlib import Path
from typing import Dict, List

from src.utils.helpers import ensure_global_trend_korean_text

# 신규 공지 강조 기준: 게시 후 7일
NEW_NOTICE_PERIOD = timedelta(days=7)


class EmailFormatter:
    """이메일 포매터"""

    CATEGORY_NAMES = {
        "market_culture": "Market & Culture",
        "global_trend": "Global Roaming Trend",
        "competitors": "SKT & Competitors",
        "esim_industry": "eSIM Industry",
        "voc_roaming": "로밍 VoC",
        "voc_esim": "eSIM VoC",
    }

    ROAMING_CARRIER_NAMES = {
        "SKT": "SKT",
        "KT": "KT",
        "LGU": "유플러스",
    }

    def __init__(self, template_dir: str | None = None, top_n: int = 3, summary_max_chars: int = 140):
        self.template_dir = Path(template_dir) if template_dir else Path(__file__).resolve().parent / "templates"
        self.top_n = max(1, top_n)
        self.summary_max_chars = max(60, summary_max_chars)

    def format(self, data: Dict) -> str:
        """
        분석된 데이터를 HTML 이메일로 변환

        Args:
            data: 분석 데이터

        Returns:
            HTML 이메일 본문
        """
        template_path = self.template_dir / "email_template.html"
        if template_path.exists():
            with template_path.open("r", encoding="utf-8") as f:
                template = f.read()
        else:
            template = self._get_default_template()

        rendered = template.replace("{{DATE}}", datetime.now().strftime("%Y년 %m월 %d일"))
        rendered = rendered.replace("{{EMAIL_TOP_N}}", str(self.top_n))
        rendered = rendered.replace("{{TODAY_BRIEF}}", self._format_today_brief(data))
        rendered = rendered.replace("{{STRATEGIC_INSIGHT}}", self._format_paragraph(data.get("strategic_insight", "")))
        rendered = rendered.replace("{{KEY_FINDINGS}}", self._format_findings(data.get("key_findings", [])))
        rendered = rendered.replace("{{RECOMMENDATIONS}}", self._format_recommendations(data.get("recommendations", [])))
        rendered = rendered.replace("{{CATEGORY_SECTIONS}}", self._generate_category_sections(data))
        rendered = rendered.replace("{{ROAMING_NOTICE_CARDS}}", self._generate_roaming_notice_cards(data))
        return rendered

    def _format_today_brief(self, data: Dict) -> str:
        lines: List[str] = []
        for finding in data.get("key_findings", [])[:2]:
            lines.append(self._truncate(str(finding), 110))
        for rec in data.get("recommendations", [])[:1]:
            lines.append(f"[권고] {self._truncate(str(rec), 110)}")
        if not lines:
            lines.append("요약 데이터가 없습니다.")
        return "\n".join(f'<li style="font-size:13px; line-height:1.7; color:#526478; margin-bottom:6px;">{html_lib.escape(line)}</li>' for line in lines[:3])

    def _format_paragraph(self, text: str) -> str:
        escaped = html_lib.escape(str(text or ""))
        if not escaped:
            return "데이터가 없습니다."
        return escaped.replace("\n", "<br>")

    def _format_findings(self, findings: List[str]) -> str:
        if not findings:
            return self._format_compact_bullets(["없음"])
        limited = [str(item) for item in findings[:3]]
        return self._format_compact_bullets(limited)

    def _format_recommendations(self, recommendations: List[str]) -> str:
        if not recommendations:
            return self._format_compact_bullets(["없음"])
        limited = [str(item) for item in recommendations[:3]]
        return self._format_compact_bullets(limited)

    def _format_compact_bullets(self, items: List[str]) -> str:
        rows = []
        for item in items:
            rows.append(
                f"""
                <tr>
                    <td width="8" valign="top" style="font-size:12px; line-height:1.55; color:#526478; padding:0 4px 3px 0;">•</td>
                    <td valign="top" style="font-size:12px; line-height:1.55; color:#526478; padding:0 0 3px 0;">{html_lib.escape(str(item))}</td>
                </tr>
                """
            )
        return f'<table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation">{"".join(rows)}</table>'

    def _generate_category_sections(self, data: Dict) -> str:
        rows = []
        for index, (key, name) in enumerate(self.CATEGORY_NAMES.items(), start=1):
            raw_articles = data.get(f"section_{key}", [])
            articles = [item for item in raw_articles if isinstance(item, dict)]
            if not articles:
                continue
            rows.append(
                f"""
                <tr>
                    {self._render_category_cell(index=index, name=name, category_key=key, articles=articles)}
                </tr>
                """
            )
        return "\n".join(rows)

    def _render_category_cell(self, index: int, name: str, category_key: str, articles: List[Dict]) -> str:
        top_articles = articles[: self.top_n]
        remaining = articles[self.top_n :]
        top_html = [self._render_article_card(article, category_key) for article in top_articles]
        more_html = self._render_more_links(remaining, category_key=category_key)

        return f"""
        <td width="100%" style="padding: 10px 0 0 0;" valign="top">
            <table class="category-card" width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation">
                <tr>
                    <td class="category-head" bgcolor="#fbf4f8" style="padding: 12px 16px; border-bottom: 1px solid #ece2e8; background-color:#fbf4f8;">
                        <p class="category-title" style="margin:0; font-size:16px; font-weight:bold; color:#191c1d;">{html_lib.escape(name)} <span style="font-size:11px; color:#707a84; font-weight:normal;">({len(articles)}건)</span></p>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px 16px 14px;">
                        {''.join(top_html)}
                        {more_html}
                    </td>
                </tr>
            </table>
        </td>
        """

    def _generate_roaming_notice_cards(self, data: Dict) -> str:
        notices_by_carrier = data.get("roaming_notices", {}) or {}
        cells = []
        for code, name in self.ROAMING_CARRIER_NAMES.items():
            raw_notices = notices_by_carrier.get(code, [])
            notices = [item for item in raw_notices if isinstance(item, dict)][: self.top_n]
            cells.append(self._render_roaming_notice_card(name=name, notices=notices))
        return '<td width="10"></td>'.join(cells)

    @staticmethod
    def _is_new_notice(notice: Dict) -> bool:
        """게시일이 최근 7일 이내면 True (파싱 실패/미상은 False)."""
        posted = notice.get("posted_at")
        if posted is None:
            return False
        try:
            if isinstance(posted, str):
                posted = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            if isinstance(posted, datetime):
                if posted.tzinfo is not None:
                    posted = posted.astimezone(timezone.utc).replace(tzinfo=None)
                return datetime.utcnow() - posted <= NEW_NOTICE_PERIOD
            if isinstance(posted, date):
                return date.today() - posted <= NEW_NOTICE_PERIOD
        except (ValueError, TypeError):
            return False
        return False

    def _render_roaming_notice_card(self, name: str, notices: List[Dict]) -> str:
        title_html = f'<p style="margin:0 0 8px 0; font-size:14px; font-weight:bold; color:#191c1d;">{html_lib.escape(name)}</p>'

        if not notices:
            body = '<p style="margin:0; font-size:12px; color:#758291;">공지사항이 없습니다.</p>'
        else:
            items = []
            for notice in notices:
                title = html_lib.escape(str(notice.get("title", "")))
                link = html_lib.escape(str(notice.get("url", "")))
                if self._is_new_notice(notice):
                    items.append(
                        f'<li style="margin-bottom: 6px;">'
                        f'<span style="color:#ff4d3d; font-size:12px; '
                        f'font-weight:bold; margin-right:4px;">[NEW]</span>'
                        f'<a href="{link}" '
                        f'style="font-size:14px; font-weight:bold; color:#1a1a1a; '
                        f'text-decoration:underline;">{title}</a></li>'
                    )
                else:
                    items.append(f'<li style="margin-bottom:6px;"><a href="{link}" style="font-size:14px; font-weight:bold; color:#1a1a1a; text-decoration:underline;">{title}</a></li>')
            body = f'<ul class="more-list">{" ".join(items)}</ul>'

        return f"""
        <td class="signal-card" width="33.33%" valign="top" bgcolor="#ffffff" style="padding: 14px; background-color:#ffffff; border:1px solid #e6ebee;">
            {title_html}
            {body}
        </td>
        """

    def _render_article_card(self, article: Dict, category_key: str) -> str:
        source = html_lib.escape(str(article.get("source", "")))
        title_raw = str(article.get("title", ""))
        summary_raw = str(article.get("summary", "")).strip()
        if category_key == "global_trend":
            title_raw, summary_raw = ensure_global_trend_korean_text(title_raw, summary_raw)
        title = html_lib.escape(title_raw)
        summary = html_lib.escape(self._truncate(summary_raw, self.summary_max_chars))
        link = html_lib.escape(str(article.get("link", "")))
        section_hint = "VoC 하이라이트" if category_key.startswith("voc_") else "뉴스 하이라이트"

        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" style="border-bottom: 1px solid #edf0f2;">
            <tr>
                <td style="padding: 10px 0;">
                    <p style="margin:0 0 6px 0; font-size:11px; color:#707a84; line-height:1.5;">{section_hint}{' | ' + source if source else ''}</p>
                    <p style="margin:0 0 6px 0; font-size:14px; font-weight:bold; color:#191c1d; line-height:1.45;">{title}</p>
                    <p style="margin:0 0 8px 0; font-size:13px; color:#526478; line-height:1.7;">{summary}</p>
                    <a href="{link}" style="color:#b90064; font-size:12px; font-weight:bold; text-decoration:underline;"><u>원문 보기</u></a>
                </td>
            </tr>
        </table>
        """

    def _render_more_links(self, remaining: List[Dict], category_key: str = "") -> str:
        if not remaining:
            return ""

        items = []
        for article in remaining:
            title_raw = str(article.get("title", ""))
            if category_key == "global_trend":
                title_raw, _ = ensure_global_trend_korean_text(title_raw, "")
            title = html_lib.escape(title_raw)
            link = html_lib.escape(str(article.get("link", "")))
            items.append(f'<li style="margin-bottom:5px;"><a href="{link}" style="color:#b90064; font-size:12px; font-weight:bold; text-decoration:underline;">{title}</a></li>')

        if not items:
            return ""

        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" style="border-top: 1px solid #edf0f2;">
            <tr>
                <td style="padding-top: 10px;">
                    <p style="margin:0 0 6px 0; font-size:12px; font-weight:bold; color:#36485b;">기타 {len(items)}건</p>
                    <ol class="more-list">{''.join(items)}</ol>
                </td>
            </tr>
        </table>
        """

    def format_safety_alert_digest(self, alerts: List[Dict]) -> str:
        """
        해외 안전 공지 전용 알림 메일 생성

        Args:
            alerts: 해외 안전 공지 리스트

        Returns:
            HTML 이메일 본문
        """
        date_text = datetime.now().strftime("%Y년 %m월 %d일")
        alert_cards = self._render_safety_alert_cards(alerts)
        return f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: "Malgun Gothic", "Apple SD Gothic Neo", Arial, sans-serif; line-height: 1.6; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 900px; margin: 0 auto; background: #fff; border-radius: 8px; padding: 24px; }}
                h1 {{ color: #d97706; border-bottom: 3px solid #d97706; padding-bottom: 10px; }}
                .date {{ color: #666; margin-bottom: 16px; }}
                .article {{ margin-bottom: 14px; padding: 14px; border-left: 4px solid #d97706; background: #fffbeb; }}
                .source {{ color: #666; font-size: 0.9em; }}
                .title {{ font-weight: bold; color: #222; margin: 6px 0; }}
                .summary {{ color: #444; }}
                .link {{ color: #b45309; text-decoration: none; }}
                .link:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>해외 안전 공지 알림</h1>
                <p class="date"><strong>{date_text}</strong></p>
                <p>당일 해외 안전 공지가 수집되어 별도 공유드립니다.</p>
                {alert_cards}
            </div>
        </body>
        </html>
        """

    def _render_safety_alert_cards(self, alerts: List[Dict]) -> str:
        if not alerts:
            return "<p>당일 매칭 공지 없음</p>"

        rendered = []
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            title = html_lib.escape(str(alert.get("title", "")))
            content = html_lib.escape(str(alert.get("content_one_line", "")))
            link = html_lib.escape(str(alert.get("link", "")))
            board_name = html_lib.escape(str(alert.get("board_name", "")))
            rendered.append(
                f"""
                <div class="article">
                    <div class="source">{board_name}</div>
                    <div class="title">{title}</div>
                    <div class="summary">{content}</div>
                    <a href="{link}" class="link">원문 보기</a>
                </div>
                """
            )
        return "\n".join(rendered) if rendered else "<p>당일 매칭 공지 없음</p>"

    def _truncate(self, text: str, max_chars: int) -> str:
        plain = str(text or "").strip()
        if len(plain) <= max_chars:
            return plain
        return f"{plain[:max_chars].rstrip()}..."

    def _get_default_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: "Malgun Gothic", "Apple SD Gothic Neo", Arial, sans-serif; line-height: 1.6; margin: 20px; }
                .section { margin-bottom: 30px; }
                .article { margin-bottom: 15px; padding: 10px; border-left: 3px solid #007bff; }
                .source { color: #666; font-size: 0.9em; }
                .title { font-weight: bold; color: #333; margin: 5px 0; }
                .summary { color: #666; }
                .link { color: #007bff; text-decoration: none; }
                .link:hover { text-decoration: underline; }
                ul { margin: 10px 0; }
            </style>
        </head>
        <body>
            <h1>SKT 로밍팀 일일 뉴스 리포트</h1>
            <p><strong>{{DATE}}</strong></p>
            <div class="section"><h2>오늘의 3줄 요약</h2><ul>{{TODAY_BRIEF}}</ul></div>
            <div class="section"><h2>전략 인사이트</h2><p>{{STRATEGIC_INSIGHT}}</p></div>
            <div class="section"><h2>주요 발견</h2><ul>{{KEY_FINDINGS}}</ul></div>
            <div class="section"><h2>행동 권고</h2><ul>{{RECOMMENDATIONS}}</ul></div>
            <table>{{CATEGORY_SECTIONS}}</table>
        </body>
        </html>
        """
