"""
HTML 이메일 생성
"""
from datetime import datetime
import html as html_lib
from pathlib import Path
from typing import Dict, List
from src.utils.helpers import ensure_global_trend_korean_text


class EmailFormatter:
    """이메일 포매터"""

    CATEGORY_NAMES = {
        "market_culture": "0. Market & Culture (Macro)",
        "global_trend": "1. Global Roaming Trend",
        "competitors": "2. SKT & Competitors",
        "esim_products": "3. eSIM Products",
        "voc_roaming": "4. 로밍 VoC",
        "voc_esim": "5. eSIM VoC",
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
        rendered = rendered.replace("{{EXTERNAL_ALERTS_SECTION}}", self._format_external_alerts_section(data.get("external_alerts", [])))
        rendered = rendered.replace("{{STRATEGIC_INSIGHT}}", self._format_paragraph(data.get("strategic_insight", "")))
        rendered = rendered.replace("{{KEY_FINDINGS}}", self._format_findings(data.get("key_findings", [])))
        rendered = rendered.replace("{{RECOMMENDATIONS}}", self._format_recommendations(data.get("recommendations", [])))
        rendered = rendered.replace("{{CATEGORY_SECTIONS}}", self._generate_category_sections(data))
        return rendered

    def _format_today_brief(self, data: Dict) -> str:
        lines: List[str] = []
        for finding in data.get("key_findings", [])[:3]:
            lines.append(self._truncate(str(finding), 120))
        for rec in data.get("recommendations", [])[:2]:
            lines.append(f"[권고] {self._truncate(str(rec), 120)}")
        if not lines:
            lines.append("요약 데이터가 없습니다.")
        return "\n".join(f"<li>{html_lib.escape(line)}</li>" for line in lines[:5])

    def _format_paragraph(self, text: str) -> str:
        escaped = html_lib.escape(str(text or ""))
        if not escaped:
            return "데이터가 없습니다."
        return escaped.replace("\n", "<br>")

    def _format_findings(self, findings: List[str]) -> str:
        if not findings:
            return "<li>없음</li>"
        return "\n".join(f"<li>{html_lib.escape(str(item))}</li>" for item in findings)

    def _format_recommendations(self, recommendations: List[str]) -> str:
        if not recommendations:
            return "<li>없음</li>"
        return "\n".join(f"<li>{html_lib.escape(str(item))}</li>" for item in recommendations)

    def _format_external_alerts_section(self, alerts: List[Dict]) -> str:
        if not alerts:
            return """
            <div class="section">
                <h2>해외 안전 공지 <span class="count">(0건)</span></h2>
                <p>당일 매칭 공지 없음</p>
            </div>
            """

        rendered = []
        for alert in alerts[: self.top_n]:
            if not isinstance(alert, dict):
                continue
            title = html_lib.escape(alert.get("title", ""))
            content = html_lib.escape(self._truncate(alert.get("content_one_line", ""), self.summary_max_chars))
            link = html_lib.escape(alert.get("link", ""))
            board_name = html_lib.escape(alert.get("board_name", ""))

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

        more_html = ""
        remaining = alerts[self.top_n :]
        if remaining:
            items = []
            for alert in remaining:
                if not isinstance(alert, dict):
                    continue
                title = html_lib.escape(alert.get("title", ""))
                link = html_lib.escape(alert.get("link", ""))
                items.append(f'<li><a href="{link}" class="link">{title}</a></li>')
            if items:
                more_html = f"""
                <div class="more-list">
                    <strong>기타 {len(items)}건</strong>
                    <ol>{''.join(items)}</ol>
                </div>
                """

        return f"""
        <div class="section">
            <h2>해외 안전 공지 <span class="count">({len(alerts)}건)</span></h2>
            {''.join(rendered)}
            {more_html}
        </div>
        """

    def _generate_category_sections(self, data: Dict) -> str:
        sections = []
        for key, name in self.CATEGORY_NAMES.items():
            raw_articles = data.get(f"section_{key}", [])
            articles = [item for item in raw_articles if isinstance(item, dict)]
            sections.append(self._render_category_section(name=name, category_key=key, articles=articles))
        return "\n".join(sections)

    def _render_category_section(self, name: str, category_key: str, articles: List[Dict]) -> str:
        if not articles:
            return f"""
            <div class="section">
                <h2>{html_lib.escape(name)} <span class="count">(0건)</span></h2>
                <p>데이터가 없습니다.</p>
            </div>
            """

        top_articles = articles[: self.top_n]
        remaining = articles[self.top_n :]

        top_html = [self._render_article_card(article, category_key) for article in top_articles]
        more_html = self._render_more_links(remaining, category_key=category_key)

        return f"""
        <div class="section">
            <h2>{html_lib.escape(name)} <span class="count">({len(articles)}건)</span></h2>
            {''.join(top_html)}
            {more_html}
        </div>
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
        <div class="article">
            <div class="source">{section_hint}{' | ' + source if source else ''}</div>
            <div class="title">{title}</div>
            <div class="summary">{summary}</div>
            <a href="{link}" class="link">원문 보기</a>
        </div>
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
            items.append(f'<li><a href="{link}" class="link">{title}</a></li>')

        if not items:
            return ""

        return f"""
        <div class="more-list">
            <strong>기타 {len(items)}건</strong>
            <ol>{''.join(items)}</ol>
        </div>
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
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; background: #f5f5f5; }}
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
                body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }
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
            <div class="section"><h2>오늘의 5줄 요약</h2><ul>{{TODAY_BRIEF}}</ul></div>
            {{EXTERNAL_ALERTS_SECTION}}
            <div class="section"><h2>📊 전략 인사이트</h2><p>{{STRATEGIC_INSIGHT}}</p></div>
            <div class="section"><h2>🔍 주요 발견</h2><ul>{{KEY_FINDINGS}}</ul></div>
            <div class="section"><h2>💡 행동 권고</h2><ul>{{RECOMMENDATIONS}}</ul></div>
            {{CATEGORY_SECTIONS}}
        </body>
        </html>
        """
