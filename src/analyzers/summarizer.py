"""
STEP 1: 기사 요약 (GPT-4o-mini)
"""
from typing import Dict, List
import logging

from .base import BaseAnalyzer
from src.utils.helpers import inspect_global_trend_translation

logger = logging.getLogger(__name__)


class Summarizer(BaseAnalyzer):
    """기사 요약기"""
    TRANSLATE_TO_KOREAN_CATEGORIES = {"global_trend"}

    def analyze(self, data: Dict) -> Dict:
        """
        기사 요약 분석

        Args:
            data: {'category_name': [articles...]}

        Returns:
            요약된 데이터
        """
        results = {}

        for category, articles in data.items():
            if not articles:
                results[category] = []
                continue

            # 카테고리별 텍스트 변환
            articles_text = self._format_articles(articles)

            # AI 요약 호출
            summaries = self._summarize_category(category, articles_text)
            if category == "global_trend":
                summaries = self._enforce_global_trend_korean_only(summaries)
            results[category] = summaries

        return results

    def _format_articles(self, articles: List[Dict]) -> str:
        """기사를 텍스트로 변환. RSS 기사는 rss_content 긴 excerpt 우선 사용."""
        formatted = []
        for i, article in enumerate(articles[:10], 1):  # 최대 10개
            body = article.get("rss_content") or article.get("snippet") or ""
            body_trimmed = body[:600].strip()
            formatted.append(
                f"[{i}] {article['title']}\n"
                f"링크: {article['link']}\n"
                f"본문: {body_trimmed}\n"
            )
        return "\n".join(formatted)

    def _summarize_category(self, category: str, articles_text: str) -> List[Dict]:
        """카테고리별 요약"""
        translate_to_korean = category in self.TRANSLATE_TO_KOREAN_CATEGORIES
        language_instruction = (
            "title과 summary는 반드시 자연스러운 한국어로 작성하세요. "
            "원문이 영어여도 한국어로 번역해서 작성해야 합니다."
            if translate_to_korean
            else "title과 summary는 기사 내용을 정확히 반영해 작성하세요."
        )

        prompt = f"""
다음은 '{category}' 카테고리의 뉴스 기사 목록입니다.

{articles_text}

각 기사를 2-3문장으로 요약하고, 다음 JSON 형식으로 반환:
{language_instruction}

{{
  "summaries": [
    {{
      "index": 1,
      "title": "기사 제목",
      "summary": "요약 내용",
      "link": "기사 링크"
    }}
  ]
}}
"""

        try:
            response = self._call_ai([
                {"role": "system", "content": "당신은 뉴스 요약 전문가입니다. 응답은 반드시 JSON 객체로만 반환하세요."},
                {"role": "user", "content": prompt}
            ])

            # 응답이 딕셔너리인지 확인
            if not isinstance(response, dict):
                logger.error(f"Invalid response type for {category}: {type(response)}")
                return []

            summaries = response.get('summaries', [])

            # summaries가 리스트인지 확인
            if not isinstance(summaries, list):
                logger.error(f"Summaries is not a list for {category}: {type(summaries)}")
                return []

            return summaries

        except Exception as e:
            logger.error(f"Summary failed for {category}: {e}")
            return []

    def _enforce_global_trend_korean_only(self, summaries: List[Dict]) -> List[Dict]:
        """Sanitize global_trend summaries to Korean-only text."""
        sanitized: List[Dict] = []
        for item in summaries:
            if not isinstance(item, dict):
                continue

            inspection = inspect_global_trend_translation(
                title=item.get("title", ""),
                summary=item.get("summary", ""),
            )
            safe_item = dict(item)
            safe_item["title"] = inspection["title"]
            safe_item["summary"] = inspection["summary"]
            safe_item["translation_status"] = inspection["translation_status"]
            safe_item["translation_notes"] = inspection["translation_notes"]
            sanitized.append(safe_item)

        return sanitized
