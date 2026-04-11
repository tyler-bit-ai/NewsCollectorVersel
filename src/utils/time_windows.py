"""
수집 시간 윈도우 계산 유틸
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


@dataclass
class CollectionWindow:
    start_utc: datetime
    end_utc: datetime
    start_kst: datetime
    end_kst: datetime
    is_monday_special: bool
    label: str


def get_collection_window_kst(window_hours: int = 24, now_utc: Optional[datetime] = None) -> CollectionWindow:
    """
    KST 기준 수집 윈도우를 계산한다.

    월요일(KST) 실행 시: 금요일 09:00 ~ 월요일 09:00 고정 구간
    그 외: 현재시각 기준 window_hours 시간
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    now_kst = now_utc.astimezone(KST)

    # Monday = 0
    if now_kst.weekday() == 0:
        monday_9_kst = now_kst.replace(hour=9, minute=0, second=0, microsecond=0)
        friday_9_kst = monday_9_kst - timedelta(days=3)
        return CollectionWindow(
            start_utc=friday_9_kst.astimezone(timezone.utc),
            end_utc=monday_9_kst.astimezone(timezone.utc),
            start_kst=friday_9_kst,
            end_kst=monday_9_kst,
            is_monday_special=True,
            label="KST 금요일 09:00 ~ 월요일 09:00",
        )

    start_utc = now_utc - timedelta(hours=window_hours)
    end_utc = now_utc
    return CollectionWindow(
        start_utc=start_utc,
        end_utc=end_utc,
        start_kst=start_utc.astimezone(KST),
        end_kst=end_utc.astimezone(KST),
        is_monday_special=False,
        label=f"최근 {window_hours}시간",
    )
