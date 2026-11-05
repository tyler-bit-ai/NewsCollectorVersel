"""
커뮤니티 VoC 다이제스트 수집 (Upstash Redis)

맥미니 업로더가 community_voc:YYYYMMDD 키에 올린 TSV 본문을 읽어 로밍/eSIM 버킷으로 나눈다.
Redis 미설정·오류·키 없음이면 빈 결과를 반환해 기존 파이프라인을 막지 않는다.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

_KEY_PREFIX = "community_voc:"
_FIELD_COUNT = 7
_ESIM_KEYWORDS = (
    "esim",
    "e심",
    "이심",
    "유심사",
    "도시락",
    "말톡",
    "에어알로",
    "airalo",
    "로밍도깨비",
    "로밍 도깨비",
    "핀다이렉트",
)
_ROAMING_KEYWORD = "로밍"


def _empty_result() -> Dict[str, List[Dict]]:
    return {"voc_roaming": [], "voc_esim": []}


def _parse_count(value: str) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return 0


def _parse_published(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value.strip(), "%y-%m-%d").replace(tzinfo=KST)
    except ValueError:
        return None


def _classify(title: str) -> Optional[str]:
    # "로밍도깨비"는 '로밍'을 포함하므로 eSIM을 반드시 먼저 평가한다.
    normalized = title.lower()
    if any(keyword in normalized for keyword in _ESIM_KEYWORDS):
        return "voc_esim"
    if _ROAMING_KEYWORD in normalized:
        return "voc_roaming"
    return None


def _build_article(fields: List[str]) -> Optional[Dict]:
    source, date, title, comments, views, author, url = fields
    title = title.strip()
    url = url.strip()
    if not title or not url:
        return None

    comment_count = _parse_count(comments)
    view_count = _parse_count(views)
    published = _parse_published(date)
    return {
        "title": title,
        "link": url,
        "source": source.strip(),
        "author": author.strip(),
        "comments": comment_count,
        "views": view_count,
        "snippet": f"댓글 {comment_count} · 조회 {view_count}",
        "published": published,
        "published_confidence": "date_only" if published else "missing",
    }


class CommunityVocCollector:
    """Upstash Redis 기반 커뮤니티 VoC 다이제스트 수집기"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_token: Optional[str] = None,
    ):
        self._redis = None
        if redis_url and redis_token:
            try:
                from upstash_redis import Redis  # type: ignore
                self._redis = Redis(url=redis_url, token=redis_token)
                logger.info("CommunityVocCollector: Upstash Redis 연결됨")
            except ImportError:
                logger.warning(
                    "CommunityVocCollector: upstash-redis 패키지 없음, no-op 모드"
                )
            except Exception as exc:
                logger.warning(
                    "CommunityVocCollector: Redis 초기화 실패 (%s), no-op 모드", exc
                )
        else:
            logger.info("CommunityVocCollector: 환경변수 미설정, no-op 모드")

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    def collect(self, now: Optional[datetime] = None) -> Dict[str, List[Dict]]:
        """오늘(KST) 다이제스트를 읽어 카테고리별 기사로 반환한다."""
        if not self._redis:
            return _empty_result()

        kst_now = now.astimezone(KST) if now else datetime.now(KST)
        key = f"{_KEY_PREFIX}{kst_now.strftime('%Y%m%d')}"
        try:
            raw = self._redis.get(key)
            if not raw:
                logger.info("CommunityVocCollector: %s 다이제스트 없음", key)
                return _empty_result()
            return self._parse_digest(raw)
        except Exception as exc:
            logger.warning("CommunityVocCollector.collect 오류: %s", exc)
            return _empty_result()

    def _parse_digest(self, raw: str) -> Dict[str, List[Dict]]:
        result = _empty_result()
        # 첫 줄은 업로더 계약상 항상 헤더다.
        for line in raw.split("\n")[1:]:
            fields = line.rstrip("\r").split("\t")
            # 필드에 탭이 섞이면 URL 위치가 밀리므로 7개가 아닌 행은 모두 버린다.
            if len(fields) != _FIELD_COUNT:
                continue
            article = _build_article(fields)
            if article is None:
                continue
            category = _classify(article["title"])
            if category:
                result[category].append(article)

        logger.info(
            "CommunityVocCollector: 로밍 %d건, eSIM %d건",
            len(result["voc_roaming"]),
            len(result["voc_esim"]),
        )
        return result
