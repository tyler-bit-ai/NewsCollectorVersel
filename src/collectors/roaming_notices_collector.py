"""통신 3사 로밍 공지사항 조회 (roaming_dashboard Supabase DB, read-only)."""
from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

CARRIER_ORDER = ["SKT", "KT", "LGU"]
CARRIER_DISPLAY_NAMES: Dict[str, str] = {
    "SKT": "SKT",
    "KT": "KT",
    "LGU": "유플러스",
}

_NOTICES_QUERY = """
    SELECT c.code AS carrier_code, n.title, n.url,
           COALESCE(n.published_at, n.first_seen_at) AS posted_at
    FROM notices n
    JOIN carriers c ON c.id = n.carrier_id
    WHERE n.is_active = true
    ORDER BY n.carrier_id, COALESCE(n.published_at, n.first_seen_at) DESC
"""


def fetch_roaming_notices(database_url: str | None, limit_per_carrier: int = 3) -> Dict[str, List[Dict[str, str]]]:
    """통신사 코드별 최근 공지 목록을 반환한다.

    실패하거나 DATABASE_URL이 없으면 빈 결과를 반환한다(리포트 발송을 막지 않기 위함).
    """
    empty: Dict[str, List[Dict[str, str]]] = {code: [] for code in CARRIER_ORDER}
    if not database_url:
        logger.warning("DATABASE_URL not configured; skipping roaming notices fetch")
        return empty

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            database_url,
            connect_timeout=10,
            application_name="news-collector-notices",
            prepare_threshold=None,
        ) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(_NOTICES_QUERY)
                rows = cur.fetchall()
    except Exception as exc:
        logger.error("Failed to fetch roaming notices: %s", exc)
        return empty

    result: Dict[str, List[Dict[str, str]]] = {code: [] for code in CARRIER_ORDER}
    for row in rows:
        code = row["carrier_code"]
        if code not in result or len(result[code]) >= limit_per_carrier:
            continue
        result[code].append({"title": row["title"], "url": row["url"], "posted_at": row["posted_at"]})

    return result
