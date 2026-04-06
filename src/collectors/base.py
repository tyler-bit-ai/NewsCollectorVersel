"""
수집 계층 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """수집기 기본 클래스"""

    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.collected_count = 0
        self.filtered_count = 0

    @abstractmethod
    def collect(self, query: str, limit: int = 5) -> List[Dict]:
        """
        데이터 수집 (추상 메서드)

        Args:
            query: 검색어
            limit: 수집 개수

        Returns:
            기사 리스트
        """
        pass

    def log_stats(self):
        """수집 통계 로그"""
        logger.info(
            f"Collection Stats - Total: {self.collected_count}, "
            f"Filtered: {self.filtered_count}, "
            f"Passed: {self.collected_count - self.filtered_count}"
        )
