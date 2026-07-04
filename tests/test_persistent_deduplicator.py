import unittest

from src.filters.persistent_deduplicator import PersistentDeduplicator


class _FakePipeline:
    """upstash_redis.Pipeline 최소 재현체: set()으로 쌓고 exec()으로 반영."""

    def __init__(self, store: dict):
        self._store = store
        self._pending: list[str] = []

    def set(self, key: str, value: str, ex: int = None):
        self._pending.append(key)
        return self

    def exec(self):
        for key in self._pending:
            self._store[key] = "1"
        self._pending = []
        return []


class _FakeRedis:
    """upstash_redis.Redis 최소 재현체 (mget + pipeline)."""

    def __init__(self):
        self.store: dict = {}

    def mget(self, *keys: str):
        return [self.store.get(key) for key in keys]

    def pipeline(self):
        return _FakePipeline(self.store)


def _make_dedup_with_fake_redis() -> PersistentDeduplicator:
    dedup = PersistentDeduplicator(redis_url=None, redis_token=None)
    dedup._redis = _FakeRedis()
    return dedup


class PersistentDeduplicatorTests(unittest.TestCase):
    def test_mark_sent_then_filter_new_only_excludes_marked_articles(self):
        dedup = _make_dedup_with_fake_redis()
        articles = [
            {"link": "https://example.com/a"},
            {"link": "https://example.com/b"},
        ]

        dedup.mark_sent(articles)
        remaining = dedup.filter_new_only(articles)

        self.assertEqual(remaining, [])

    def test_filter_new_only_keeps_unmarked_articles(self):
        dedup = _make_dedup_with_fake_redis()
        dedup.mark_sent([{"link": "https://example.com/a"}])

        remaining = dedup.filter_new_only(
            [
                {"link": "https://example.com/a"},
                {"link": "https://example.com/b"},
            ]
        )

        self.assertEqual([a["link"] for a in remaining], ["https://example.com/b"])

    def test_disabled_deduplicator_is_fail_open(self):
        dedup = PersistentDeduplicator(redis_url=None, redis_token=None)
        articles = [{"link": "https://example.com/a"}]

        self.assertFalse(dedup.enabled)
        dedup.mark_sent(articles)
        self.assertEqual(dedup.filter_new_only(articles), articles)


if __name__ == "__main__":
    unittest.main()
