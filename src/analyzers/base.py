"""
AI 분석 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, List
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """AI 분석 기본 클래스"""

    def __init__(self, api_key: str, base_url: str, model: str):
        """
        Args:
            api_key: OpenAI API Key
            base_url: OpenAI Base URL
            model: 모델명
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_retries = 3

    @abstractmethod
    def analyze(self, data: Dict) -> Dict:
        """분석 수행 (추상 메서드)"""
        pass

    def _call_ai(self, messages: List[Dict]) -> Dict:
        """
        AI 호출 with 재시도

        Args:
            messages: 메시지 리스트

        Returns:
            AI 응답 (JSON 딕셔너리)

        Raises:
            Exception: 재시도 실패 시
        """
        import time
        import json

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content

                # JSON 파싱 시도
                parsed = json.loads(content)

                # 파싱된 결과가 딕셔너리인지 확인
                if not isinstance(parsed, dict):
                    logger.error(f"AI response is not a dict: {type(parsed)}")
                    logger.error(f"Response content: {content[:500]}")  # 처음 500자만 로깅
                    raise ValueError(f"Expected dict, got {type(parsed)}")

                return parsed

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}")
                logger.error(f"Response content: {response.choices[0].message.content if response else 'No response'}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise ValueError(f"Failed to parse AI response as JSON after {self.max_retries} attempts")

            except Exception as e:
                logger.warning(f"AI call attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
