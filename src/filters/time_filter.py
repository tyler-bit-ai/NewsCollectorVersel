"""
시간 필터링 (24시간 윈도우)
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TimeFilter:
    """시간 기반 필터링"""

    def __init__(self, window_hours: int = 24, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        """
        Args:
            window_hours: 시간 윈도우 (기본 24시간)
            start_time: 시작 시간 (UTC)
            end_time: 종료 시간 (UTC)
        """
        self.window_hours = window_hours
        self.cutoff_time = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        self.start_time = self._normalize_datetime(start_time) if start_time else self.cutoff_time
        self.end_time = self._normalize_datetime(end_time) if end_time else None

    def _normalize_datetime(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def is_valid(self, pub_date: datetime) -> bool:
        """
        24시간 윈도우 내에 있는지 확인

        Args:
            pub_date: 기사 발행일

        Returns:
            윈도우 내에 있으면 True
        """
        if not pub_date:
            return True  # 날짜 파싱 실패 시 포함

        pub_date = self._normalize_datetime(pub_date)
        if self.end_time is None:
            is_valid = pub_date >= self.start_time
        else:
            is_valid = self.start_time <= pub_date < self.end_time

        if not is_valid and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Filtered by time: {pub_date} not in [{self.start_time}, {self.end_time or 'now'})"
            )

        return is_valid

    def filter_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        기사 리스트 시간 필터링

        Args:
            articles: 기사 리스트

        Returns:
            필터링된 기사 리스트
        """
        filtered = []
        for article in articles:
            if self.is_valid(article.get('published')):
                filtered.append(article)

        logger.info(f"Time filter: {len(filtered)}/{len(articles)} passed")
        return filtered
