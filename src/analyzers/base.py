"""
AI 분석 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json
import logging
import re
import time
from openai import OpenAI

logger = logging.getLogger(__name__)

JSON_ONLY_SYSTEM_PROMPT = "반드시 유효한 JSON 객체 하나만 출력한다. 마크다운 코드블록, 주석, 추가 설명은 금지."
_CODE_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def _extract_first_json_object(text: str) -> Optional[str]:
    """문자열 리터럴을 고려해 첫 번째 균형 잡힌 {...} 블록을 반환한다."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def _parse_json_content(content: Optional[str]) -> Any:
    """코드펜스·앞뒤 설명이 섞인 응답에서도 JSON을 파싱한다."""
    text = (content or "").strip()
    fence_match = _CODE_FENCE_PATTERN.match(text)
    if fence_match:
        text = fence_match.group(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        block = _extract_first_json_object(text)
        if block is None:
            raise
        return json.loads(block)


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

    def _create_completion(self, messages: List[Dict]):
        """json_object 모드로 호출하고, 파라미터가 거부되면 없이 1회 재호출한다."""
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"}
            )
        except Exception as e:
            if "response_format" not in str(e):
                raise
            logger.warning(f"response_format rejected, retrying without it: {e}")
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )

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
        if not any(message.get("role") == "system" for message in messages):
            messages = [{"role": "system", "content": JSON_ONLY_SYSTEM_PROMPT}, *messages]

        for attempt in range(self.max_retries):
            try:
                response = self._create_completion(messages)

                content = response.choices[0].message.content

                # JSON 파싱 시도
                parsed = _parse_json_content(content)

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
