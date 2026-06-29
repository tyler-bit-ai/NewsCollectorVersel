"""
실행 간 중복 제거 (Upstash Redis)

UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN 환경변수가 없으면
graceful no-op으로 동작해 기존 메모리 내 dedup만 사용한다.
"""
import logging
from typing import Dict, List, Optional

from src.utils.helpers import canonicalize_link

logger = logging.getLogger(__name__)

_KEY_PREFIX = "seen_article:"
_DEFAULT_TTL_DAYS = 30


class PersistentDeduplicator:
    """Upstash Redis 기반 실행 간 중복 제거"""

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
                logger.info("PersistentDeduplicator: Upstash Redis 연결됨")
            except ImportError:
                logger.warning(
                    "PersistentDeduplicator: upstash-redis 패키지 없음, no-op 모드"
                )
            except Exception as exc:
                logger.warning(
                    "PersistentDeduplicator: Redis 초기화 실패 (%s), no-op 모드", exc
                )
        else:
            logger.info(
                "PersistentDeduplicator: 환경변수 미설정, no-op 모드 (메모리 dedup만 사용)"
            )

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    def _key(self, url: str) -> str:
        return f"{_KEY_PREFIX}{canonicalize_link(url)}"

    def filter_new_only(self, articles: List[Dict]) -> List[Dict]:
        """Redis에 없는(이전 실행에서 발송되지 않은) 기사만 반환한다.
        Redis 미설정이거나 오류 시 전량 반환 (fail-open).
        """
        if not self._redis or not articles:
            return articles

        keys = [self._key(a["link"]) for a in articles]
        try:
            results = self._redis.mget(*keys)
        except Exception as exc:
            logger.warning("PersistentDeduplicator.filter_new_only 오류: %s", exc)
            return articles

        new_articles = [a for a, seen in zip(articles, results) if not seen]
        skipped = len(articles) - len(new_articles)
        if skipped:
            logger.info(
                "PersistentDeduplicator: %d건 이전 발송 기사 제외", skipped
            )
        return new_articles

    def mark_sent(
        self, articles: List[Dict], ttl_days: int = _DEFAULT_TTL_DAYS
    ) -> None:
        """발송된 기사 URL을 Redis에 기록한다 (TTL: ttl_days일).
        오류 시 경고만 출력하고 진행 (silent-fail).
        """
        if not self._redis or not articles:
            return

        ttl_seconds = ttl_days * 86400
        try:
            pipe = self._redis.pipeline()
            for article in articles:
                pipe.set(self._key(article["link"]), "1", ex=ttl_seconds)
            pipe.execute()
            logger.info(
                "PersistentDeduplicator: %d건 발송 기록 완료 (TTL %dd)",
                len(articles),
                ttl_days,
            )
        except Exception as exc:
            logger.warning("PersistentDeduplicator.mark_sent 오류: %s", exc)
