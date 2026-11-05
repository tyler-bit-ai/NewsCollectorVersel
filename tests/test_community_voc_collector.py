import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.collectors.community_voc_collector import KST, CommunityVocCollector

HEADER = "source\tdate\ttitle\tcomments\tviews\tauthor\turl"
EMPTY = {"voc_roaming": [], "voc_esim": []}


def row(title="해외 로밍 후기", url="https://example.com/1", date="26-11-05", comments="3", views="120"):
    return f"뽐뿌\t{date}\t{title}\t{comments}\t{views}\t작성자\t{url}"


def build_collector(value=None, error=None):
    client = MagicMock()
    client.get.return_value = value
    client.get.side_effect = error
    with patch("upstash_redis.Redis", return_value=client):
        collector = CommunityVocCollector(redis_url="https://redis.example.com", redis_token="token")
    return collector, client


class CommunityVocCollectorTests(unittest.TestCase):
    def test_missing_settings_returns_empty_result(self):
        for url, token in ((None, None), ("https://redis.example.com", None), (None, "token")):
            collector = CommunityVocCollector(redis_url=url, redis_token=token)

            self.assertFalse(collector.enabled)
            self.assertEqual(collector.collect(), EMPTY)

    def test_redis_init_failure_is_no_op(self):
        with patch("upstash_redis.Redis", side_effect=RuntimeError("boom")):
            collector = CommunityVocCollector(redis_url="https://redis.example.com", redis_token="token")

        self.assertFalse(collector.enabled)
        self.assertEqual(collector.collect(), EMPTY)

    def test_missing_or_empty_key_returns_empty_result(self):
        for value in (None, ""):
            collector, _ = build_collector(value)

            self.assertEqual(collector.collect(), EMPTY)

    def test_redis_error_returns_empty_result(self):
        collector, _ = build_collector(error=RuntimeError("redis down"))

        self.assertEqual(collector.collect(), EMPTY)

    def test_non_string_value_returns_empty_result(self):
        collector, _ = build_collector(12345)

        self.assertEqual(collector.collect(), EMPTY)

    def test_uses_kst_date_in_key(self):
        collector, client = build_collector(None)

        # 2026-11-05 15:30 UTC == 2026-11-06 00:30 KST
        collector.collect(now=datetime(2026, 11, 5, 15, 30, tzinfo=timezone.utc))

        client.get.assert_called_once_with("community_voc:20261106")

    def test_parses_valid_tsv_row(self):
        collector, _ = build_collector(f"{HEADER}\n{row()}\n")

        result = collector.collect()

        self.assertEqual(len(result["voc_roaming"]), 1)
        self.assertEqual(
            result["voc_roaming"][0],
            {
                "title": "해외 로밍 후기",
                "link": "https://example.com/1",
                "source": "뽐뿌",
                "author": "작성자",
                "comments": 3,
                "views": 120,
                "snippet": "댓글 3 · 조회 120",
                "published": datetime(2026, 11, 5, tzinfo=KST),
                "published_confidence": "date_only",
            },
        )
        self.assertEqual(result["voc_roaming"][0]["published"].utcoffset(), timedelta(hours=9))

    def test_invalid_counts_and_date_fall_back(self):
        collector, _ = build_collector(
            f"{HEADER}\n{row(date='어제', comments='많음', views='')}"
        )

        article = collector.collect()["voc_roaming"][0]

        self.assertEqual((article["comments"], article["views"]), (0, 0))
        self.assertEqual(article["snippet"], "댓글 0 · 조회 0")
        self.assertIsNone(article["published"])
        self.assertEqual(article["published_confidence"], "missing")

    def test_handles_crlf_line_endings(self):
        collector, _ = build_collector(f"{HEADER}\r\n{row()}\r\n")

        self.assertEqual(
            collector.collect()["voc_roaming"][0]["link"], "https://example.com/1"
        )

    def test_header_only_returns_empty_result(self):
        collector, _ = build_collector(HEADER)

        self.assertEqual(collector.collect(), EMPTY)

    def test_distributes_by_title_with_esim_first(self):
        titles = {
            "로밍도깨비 후기": "voc_esim",
            "로밍 도깨비 사용기": "voc_esim",
            "KT 로밍 eSIM 비교": "voc_esim",
            "AIRALO 설치법": "voc_esim",
            "해외 로밍 후기": "voc_roaming",
            "해외로밍 질문": "voc_roaming",
            "데이터로밍 차단": "voc_roaming",
            "baro 로밍 문의": "voc_roaming",
        }
        for title, expected in titles.items():
            collector, _ = build_collector(f"{HEADER}\n{row(title=title)}")

            result = collector.collect()

            self.assertEqual(len(result[expected]), 1, title)
            self.assertEqual(sum(len(bucket) for bucket in result.values()), 1, title)

    def test_title_without_keyword_is_dropped(self):
        collector, _ = build_collector(f"{HEADER}\n{row(title='아이폰 케이스 추천')}")

        self.assertEqual(collector.collect(), EMPTY)

    def test_skips_malformed_rows(self):
        malformed = [
            "뽐뿌\t26-11-05\t로밍 필드 부족",
            row() + "\t여덟번째 필드",
            row(title="  "),
            row(url=""),
            "",
        ]
        valid = row(title="로밍 정상", url="https://example.com/ok")
        collector, _ = build_collector("\n".join([HEADER, *malformed, valid]))

        result = collector.collect()

        self.assertEqual([a["link"] for a in result["voc_roaming"]], ["https://example.com/ok"])
        self.assertEqual(result["voc_esim"], [])
