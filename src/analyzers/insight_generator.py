"""
STEP 2: 전략 인사이트 (GPT-5)
"""
from typing import Dict
import logging

from .base import BaseAnalyzer

logger = logging.getLogger(__name__)


class InsightGenerator(BaseAnalyzer):
    """전략 인사이트 생성기"""

    def analyze(self, summary_data: Dict) -> Dict:
        """
        요약된 데이터에서 전략 인사이트 생성

        Args:
            summary_data: 카테고리별 요약 데이터

        Returns:
            인사이트 데이터
        """
        # 전체 텍스트 변환
        full_text = self._format_summaries(summary_data)

        # AI 인사이트 호출
        insights = self._generate_insights(full_text)

        # 타입 검증 추가
        if not isinstance(insights, dict):
            logger.error(f"Insights is not a dict: {type(insights)} - Value: {insights}")
            return {
                'strategic_insight': '인사이트 생성 실패 (잘못된 응답 형식)',
                'key_findings': [],
                'recommendations': []
            }

        return {
            'strategic_insight': insights.get('strategic_insight', ''),
            'key_findings': insights.get('key_findings', []),
            'recommendations': insights.get('recommendations', [])
        }

    def _format_summaries(self, summary_data: Dict) -> str:
        """요약 데이터를 텍스트로 변환"""
        sections = []
        for category, summaries in summary_data.items():
            sections.append(f"## {category}")
            # summaries가 리스트인지 확인
            if not isinstance(summaries, list):
                logger.warning(f"Summaries for {category} is not a list: {type(summaries)}")
                continue
            for item in summaries:
                # item이 딕셔너리인지 확인
                if isinstance(item, dict):
                    title = item.get('title', '')
                    summary = item.get('summary', '')
                    sections.append(f"- {title}: {summary}")
                else:
                    logger.warning(f"Invalid item type in {category}: {type(item)}")
        return "\n".join(sections)

    def _generate_insights(self, full_text: str) -> Dict:
        """전략 인사이트 생성"""
        prompt = f"""
당신은 SKT 로밍팀의 전략 분석가입니다.

다음은 오늘 수집된 로밍 관련 뉴스 요약입니다:

{full_text}

이를 바탕으로 다음을 분석해 주세요.

중요 규칙:
1. strategic_insight는 반드시 한국어 1문단, 최대 200자 이내로 작성합니다.
2. key_findings는 중요도 기준으로 가장 중요한 3개만 작성합니다.
3. recommendations는 실행 우선순위 기준으로 가장 중요한 3개만 작성합니다.
4. key_findings와 recommendations의 각 항목은 짧고 압축적으로, 한 항목당 60자 내외로 작성합니다.
5. 군더더기 표현, 중복 표현, 서론 문장은 제외하고 바로 핵심만 작성합니다.
6. JSON 외 다른 텍스트는 절대 출력하지 않습니다.

JSON 형식으로 반환:
{{
  "strategic_insight": "...",
  "key_findings": ["...", "...", "..."],
  "recommendations": ["...", "...", "..."]
}}
"""

        try:
            return self._call_ai([
                {"role": "system", "content": "당신은 통신사 로밍 사업 전략 전문가입니다. 응답은 반드시 JSON 객체만 반환하고, strategic_insight는 200자 이하, key_findings와 recommendations는 각각 가장 중요한 3개만 압축해 작성하세요."},
                {"role": "user", "content": prompt}
            ])
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return {
                'strategic_insight': '인사이트 생성 실패',
                'key_findings': [],
                'recommendations': []
            }
