import unittest

from src.collectors.naver_collector import NaverCollector


class NaverCollectorTests(unittest.TestCase):
    def test_parse_items_preserves_query(self):
        collector = NaverCollector("id", "secret")
        items = [
            {
                "title": "KT 로밍 후기",
                "link": "https://blog.naver.com/example/1",
                "description": "사용 후기를 정리했다.",
                "postdate": "20260411",
            }
        ]

        parsed = collector._parse_items(items, endpoint="blog", query="KT 로밍 후기")

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["query"], "KT 로밍 후기")

    def test_parse_items_keeps_cafe_items_without_postdate(self):
        collector = NaverCollector("id", "secret")
        items = [
            {
                "title": "로밍도깨비 후기",
                "link": "https://cafe.naver.com/example/1",
                "description": "사용 후기와 연결 품질 정리",
            }
        ]

        parsed = collector._parse_items(items, endpoint="cafearticle", query="로밍도깨비 후기")

        self.assertEqual(len(parsed), 1)
        self.assertIsNone(parsed[0]["published"])
        self.assertEqual(parsed[0]["published_confidence"], "missing")
