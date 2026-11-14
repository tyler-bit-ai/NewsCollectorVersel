"""
앱스토어 고객리뷰 VoC 수집 (iTunes Customer Reviews RSS)

로밍/eSIM 전문 앱의 신규 리뷰를 공개 RSS에서 읽어 voc_esim 버킷에 넣는다.
- 7일 롤링 윈도우 + 파이프라인의 PersistentDeduplicator가 같은 리뷰 재노출을 막는다.
- HTTP 실패는 빈 결과로 무시한다(기존 파이프라인을 막지 않는다).
- 2026-11-14 도입(사용자 승인): 커뮤니티 일반글 대비 잡음이 없는 순수 VoC 소스.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import json
import urllib.request

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# (표시명, 한국 앱스토어 trackId) — 2026-11-14 iTunes Search API로 확인
_APPS: List[tuple] = [
    ("로밍도깨비", 1525664178),
    ("유심사", 1635360522),
    ("도시락eSIM", 1620488208),
    ("이심이지", 1628484156),
    ("Saily", 6475045151),
]

_WINDOW_DAYS = 7
_MAX_PER_APP = 10
_TIMEOUT_SECONDS = 10
_RSS_URL = "https://itunes.apple.com/kr/rss/customerreviews/id={app_id}/sortby=mostrecent/json"


class AppStoreReviewCollector:
    """iTunes RSS 기반 앱스토어 리뷰 수집기"""

    def __init__(self, apps: Optional[List[tuple]] = None, window_days: int = _WINDOW_DAYS):
        self._apps = apps or _APPS
        self._window_days = window_days

    def collect(self, now: Optional[datetime] = None) -> Dict[str, List[Dict]]:
        kst_now = now.astimezone(KST) if now else datetime.now(KST)
        cutoff = kst_now - timedelta(days=self._window_days)
        result: Dict[str, List[Dict]] = {"voc_esim": []}

        for app_name, app_id in self._apps:
            try:
                entries = self._fetch_entries(app_id)
            except Exception as exc:
                logger.warning("AppStoreReviewCollector: %s(%s) 실패 - %s", app_name, app_id, exc)
                continue
            added = 0
            for entry in entries:
                article = self._to_article(app_name, entry, cutoff)
                if article is None:
                    continue
                result["voc_esim"].append(article)
                added += 1
                if added >= _MAX_PER_APP:
                    break

        logger.info(
            "AppStoreReviewCollector: %d개 앱에서 eSIM 리뷰 %d건",
            len(self._apps),
            len(result["voc_esim"]),
        )
        return result

    def _fetch_entries(self, app_id: int) -> List[Dict]:
        request = urllib.request.Request(
            _RSS_URL.format(app_id=app_id),
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        )
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())
        entries = payload.get("feed", {}).get("entry", [])
        if isinstance(entries, dict):  # 리뷰 1건뿐이면 dict로 내려온다
            entries = [entries]
        return entries

    def _to_article(
        self, app_name: str, entry: Dict, cutoff: datetime
    ) -> Optional[Dict]:
        try:
            updated_raw = entry.get("updated", {}).get("label", "")
            published = datetime.fromisoformat(updated_raw)
            if published.tzinfo is None:
                published = published.replace(tzinfo=KST)
            if published < cutoff:
                return None
            rating = str(entry.get("im:rating", {}).get("label", "") or "?")
            title = str(entry.get("title", {}).get("label", "")).strip()
            content = str(entry.get("content", {}).get("label", "")).strip()
            author = str(entry.get("author", {}).get("name", {}).get("label", "")).strip()
            link = ""
            for link_item in entry.get("link", []):
                if isinstance(link_item, dict) and link_item.get("attributes", {}).get("rel") == "alternate":
                    link = link_item["attributes"].get("href", "")
                    break
            if not title or not link:
                return None
        except Exception:
            return None

        summary = content[:80] + ("..." if len(content) > 80 else "")
        return {
            "title": f"[{rating}★] {title}",
            "link": link,
            "source": f"앱스토어·{app_name}",
            "author": author,
            "comments": 0,
            "views": 0,
            "snippet": f"앱 리뷰 · {summary}" if summary else "앱 리뷰",
            "published": published,
            "published_confidence": "date_only",
        }
