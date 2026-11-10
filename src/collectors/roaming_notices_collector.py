"""통신 3사 로밍 공지사항 직접 스크래핑 (각 사 공지 게시판에서 최신글 조회).

기존에는 roaming_dashboard Supabase DB(notices)를 읽었으나 published_at/url이
잘못 저장된 행이 있어 2022년 공지가 최신으로 노출되는 문제가 발생했다.
DB 의존을 제거하고 각 사 공지 페이지를 직접 파싱한다.
"""
from __future__ import annotations

import html
import logging
import re
import time
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)

CARRIER_ORDER = ["SKT", "KT", "LGU"]
CARRIER_DISPLAY_NAMES: Dict[str, str] = {
    "SKT": "SKT",
    "KT": "KT",
    "LGU": "유플러스",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
    ),
    "Accept-Language": "ko,en;q=0.8",
}

_SKT_LIST_URL = "https://m.tworld.co.kr/customer/svc-info/notice?category=roaming"
_KT_LIST_URL = "https://globalroaming.kt.com/news/list?gp=1&sp=1&type=&val="
_LGU_LIST_URL = "https://www.lguplus.com/plan/roaming/support/notice"
_LGU_LIST_URLS = [_LGU_LIST_URL, _LGU_LIST_URL + "?pageNo=1"]

_KT_ROW = re.compile(
    r'<td class="left">\s*<a href="(/news/view\?idx=\d+[^"]*)"[^>]*>(.*?)</a>\s*</td>\s*'
    r'<td[^>]*>(\d{4}-\d{2}-\d{2})</td>',
    re.S,
)
_SKT_ROW = re.compile(
    r'<span class="acco-notice-tit">\s*(.*?)\s*</span>.*?'
    r'<span class="acco-notice-date">\s*(\d{4})\.(\d{1,2})\.(\d{1,2})\.?\s*</span>',
    re.S,
)
_LGU_ROW = re.compile(
    r'<td[^>]*class="c-cell-subject"[^>]*>.*?<a href="(/plan/roaming/support/notice/\d+[^"]*)"[^>]*>(.*?)</a>'
    r'.*?class="c-cell-date">\s*(\d{4}-\d{2}-\d{2})',
    re.S,
)


def _strip_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


_UA_VARIANTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]


def _fetch(url: str, attempts: int = 3, timeout: int = 30) -> str:
    """UA를 바꿔가며 재시도한다 (Vercel 데이터센터 IP 차단/타임아웃 완화용)."""
    last_exc: Exception | None = None
    for i in range(attempts):
        headers = {
            "User-Agent": _UA_VARIANTS[i % len(_UA_VARIANTS)],
            "Accept-Language": "ko,en;q=0.8",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            if resp.text.strip():
                return resp.text
            last_exc = RuntimeError("empty body")
        except Exception as exc:  # noqa: BLE001 - 통신사별 격리 목적
            last_exc = exc
            logger.warning("fetch attempt %d/%d failed for %s: %s", i + 1, attempts, url, exc)
        time.sleep(2 * (i + 1))
    raise last_exc if last_exc else RuntimeError("fetch failed")


def _collect_kt(limit: int) -> List[Dict[str, str]]:
    body = _fetch(_KT_LIST_URL)
    rows = [
        {
            "title": _strip_tags(title),
            "url": "https://globalroaming.kt.com" + html.unescape(href),
            "posted_at": date,
        }
        for href, title, date in _KT_ROW.findall(body)
    ]
    rows.sort(key=lambda r: r["posted_at"], reverse=True)  # 상단 고정 공지 보정
    return rows[:limit]


def _collect_skt(limit: int) -> List[Dict[str, str]]:
    body = _fetch(_SKT_LIST_URL)
    rows = [
        {
            "title": _strip_tags(title),
            "url": _SKT_LIST_URL,  # 모바일 공지는 아코디언 구조로 개별 URL 없음
            "posted_at": f"{y}-{int(m):02d}-{int(d):02d}",
        }
        for title, y, m, d in _SKT_ROW.findall(body)
    ]
    rows.sort(key=lambda r: r["posted_at"], reverse=True)
    return rows[:limit]


def _collect_lgu(limit: int) -> List[Dict[str, str]]:
    body = ""
    errors: list[str] = []
    for url in _LGU_LIST_URLS:
        try:
            body = _fetch(url)
            break
        except Exception as exc:  # noqa: BLE001 - 대체 URL 폴백
            errors.append(f"{url} -> {exc}")
    if not body:
        raise RuntimeError("; ".join(errors))
    rows = [
        {
            "title": _strip_tags(title),
            "url": "https://www.lguplus.com" + html.unescape(href),
            "posted_at": date,
        }
        for href, title, date in _LGU_ROW.findall(body)
    ]
    rows.sort(key=lambda r: r["posted_at"], reverse=True)
    return rows[:limit]


_COLLECTORS = {
    "KT": _collect_kt,
    "SKT": _collect_skt,
    "LGU": _collect_lgu,
}


def fetch_roaming_notices(
    database_url: str | None = None,  # 더 이상 사용하지 않음(호환 유지)
    limit_per_carrier: int = 3,
) -> Dict[str, List[Dict[str, str]]]:
    """통신사 코드별 최근 공지 목록을 각 사 게시판에서 직접 수집해 반환한다.

    통신사 단위로 격리: 한 사 실패는 해당 사만 빈 목록이며 리포트 발송을 막지 않는다.
    """
    result: Dict[str, List[Dict[str, str]]] = {code: [] for code in CARRIER_ORDER}
    for code in CARRIER_ORDER:
        try:
            result[code] = _COLLECTORS[code](limit_per_carrier)
        except Exception as exc:
            logger.error("Failed to scrape roaming notices for %s: %s", code, exc)
    return result
