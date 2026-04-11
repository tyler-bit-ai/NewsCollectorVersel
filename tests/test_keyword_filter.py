import unittest

from src.filters.keyword_filter import KeywordFilter
from src.pipeline.core import load_categories


class KeywordFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = load_categories()
        cls.category_rules = config["categories"]
        cls.filters = config["filters"]

    def build_filter(self) -> KeywordFilter:
        return KeywordFilter(
            blacklist_domains=self.filters["blacklist_domains"],
            excluded_keywords=self.filters["excluded_keywords"],
            global_trend_rules=self.filters.get("global_trend", {}),
            category_rules=self.category_rules,
        )

    def test_competitors_rejects_non_roaming_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "SKT, Arm·리벨리온과 GPU 대체 AI 서버 솔루션 공동 개발",
            "snippet": "AI 인프라 경쟁력 강화를 위한 협업 발표",
            "link": "https://example.com/skt-ai",
            "source": "Naver News",
        }

        self.assertFalse(keyword_filter.validate(article, category="competitors"))

    def test_competitors_accepts_roaming_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "LGU+, 해외 로밍 혜택 강화…데이터·부가 서비스 확대",
            "snippet": "로밍 요금제와 데이터 로밍 혜택을 개편했다.",
            "link": "https://example.com/lgu-roaming",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="competitors"))
        self.assertGreaterEqual(article["relevance_score"], 50)

    def test_excluded_keyword_uses_boundary_matching(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "프롤로그 형식의 일본 여행 일지",
            "snippet": "해외 여행 준비 내용을 정리했다.",
            "link": "https://example.com/prologue",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="market_culture"))

    def test_global_trend_does_not_use_query_for_matching(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "Spring travel market outlook",
            "snippet": "General tourism demand is rising across Asia.",
            "query": "travel connectivity market",
            "link": "https://example.com/travel-market",
            "source": "Google",
            "source_domain": "example.com",
        }

        self.assertFalse(keyword_filter.validate(article, category="global_trend"))

    def test_esim_industry_accepts_brand_only_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "Airalo 봄 시즌 프로모션 공개",
            "snippet": "에어알로 할인 혜택과 상품 소개",
            "link": "https://example.com/airalo-promo",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="esim_industry"))
        self.assertIn("airalo", [value.lower() for value in article["matched_include_keywords"]])

    def test_esim_industry_accepts_guarded_dosirak_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "도시락 여름 이벤트",
            "snippet": "해외 데이터 프로모션과 이심 상품 안내",
            "link": "https://example.com/dosirak-event",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="esim_industry"))
        self.assertIn("도시락", article["matched_include_keywords"])

    def test_esim_industry_rejects_generic_dosirak_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "도시락 반찬 추천",
            "snippet": "일반 생활 기사",
            "link": "https://example.com/dosirak-food",
            "source": "Naver News",
        }

        self.assertFalse(keyword_filter.validate(article, category="esim_industry"))

    def test_voc_roaming_keeps_carrier_roaming_priority_articles(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "KT 로밍 eSIM 후기, 일본에서 데이터 로밍 연결 안정적",
            "snippet": "eSIM 설정과 로밍 속도, 연결 품질을 함께 정리한 리뷰",
            "link": "https://example.com/dual-signal",
            "source": "Naver Blog",
        }

        self.assertTrue(keyword_filter.validate(article, category="voc_roaming"))
        self.assertEqual(article["voc_type"], "voc_roaming")
        self.assertIn("carrier_roaming:kt 로밍", article["matched_signals"])

    def test_voc_esim_prioritizes_esim_brand_articles(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "로밍도깨비 사용 후기, 일본 여행에서 데이터 로밍 연결 안정적",
            "snippet": "설정과 로밍 속도, 연결 품질을 함께 정리한 리뷰",
            "link": "https://example.com/roamingdokkaebi-review",
            "source": "Naver Blog",
        }

        self.assertTrue(keyword_filter.validate(article, category="voc_esim"))
        self.assertEqual(article["voc_type"], "voc_esim")
        self.assertIn("esim_brand:로밍도깨비", article["matched_signals"])

    def test_voc_esim_accepts_esim_only_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "Airalo eSIM 후기, 유럽 여행에서 개통과 설정이 간단했다",
            "snippet": "eSIM 사용기와 개통 경험을 정리했다.",
            "link": "https://example.com/airalo-review",
            "source": "Naver Blog",
        }

        self.assertTrue(keyword_filter.validate(article, category="voc_esim"))
        self.assertEqual(article["voc_type"], "voc_esim")

    def test_voc_uses_snippet_when_title_lacks_review_wording(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "Airalo 사용법 정리",
            "snippet": "직접 사용 후기와 개통 팁을 정리했다.",
            "query": "Airalo 후기",
            "link": "https://example.com/airalo-guide",
            "source": "Naver Blog",
        }

        self.assertTrue(keyword_filter.validate(article, category="voc_esim"))
        self.assertEqual(article["voc_type"], "voc_esim")

    def test_voc_esim_rejects_roaming_priority_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "KT 로밍 eSIM 후기, 일본에서 로밍 속도와 통화 품질 점검",
            "snippet": "eSIM 개통 후 로밍 연결과 데이터 로밍 품질을 리뷰했다.",
            "link": "https://example.com/kt-roaming-esim",
            "source": "Naver Blog",
        }

        self.assertFalse(keyword_filter.validate(article, category="voc_esim"))
        self.assertEqual(article["voc_type"], "voc_roaming")
