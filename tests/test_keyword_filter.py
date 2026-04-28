import unittest
from datetime import datetime, timezone

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

    def test_competitors_rejects_query_only_roaming_match(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "SKT 무상교체 첫날 유심대란",
            "snippet": "SK텔레콤이 유심 무상 교체 서비스를 시작했다.",
            "query": "SKT 로밍",
            "link": "https://example.com/skt-usim",
            "source": "Naver News",
        }

        self.assertFalse(keyword_filter.validate(article, category="competitors"))

    def test_competitors_accepts_snippet_roaming_match(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "KT, 해외 서비스 혜택 강화",
            "snippet": "데이터 로밍 요금제를 개편하고 부가 혜택을 확대했다.",
            "query": "KT 로밍",
            "link": "https://example.com/kt-roaming",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="competitors"))

    def test_korean_particle_suffixes_match_keywords(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "KT, 해외 서비스 개편",
            "snippet": "KT가 데이터 로밍을 신청한 고객 혜택을 확대했다.",
            "query": "KT 로밍",
            "link": "https://example.com/kt-roaming-particle",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="competitors"))

    def test_excluded_keyword_uses_boundary_matching(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "프롤로그 형식의 일본 여행 일지",
            "snippet": "해외 여행객 준비 수요를 정리했다.",
            "link": "https://example.com/prologue",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="market_culture"))

    def test_market_culture_rejects_query_only_travel_match(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "박명수, 신인 시절 선배에 호통",
            "snippet": "방송 에피소드를 소개했다.",
            "query": "일본 여행",
            "link": "https://example.com/entertainment",
            "source": "Naver News",
        }

        self.assertFalse(keyword_filter.validate(article, category="market_culture"))
        self.assertNotEqual(article.get("relevance_reason"), "category_match")

    def test_market_culture_accepts_kpop_industry_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "음반 수출, 1분기 만에 1억 달러 넘겨",
            "snippet": "관세청은 케이팝 팬덤 확산과 콘텐츠 수출 증가를 배경으로 분석했다.",
            "query": "한류",
            "link": "https://example.com/kpop-export",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="market_culture"))
        self.assertIn("수출", article["matched_required_keywords"])

    def test_market_culture_rejects_card_travel_promotion(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "하나카드, 유니온페이와 해외 결제 할인 프로모션 진행",
            "snippet": "해외 여행객을 대상으로 결제 할인 혜택을 제공한다.",
            "query": "해외 여행객수",
            "link": "https://example.com/card-travel-offer",
            "source": "Naver News",
        }

        self.assertFalse(keyword_filter.validate(article, category="market_culture"))
        self.assertTrue(article["relevance_reason"].startswith("market_culture_soft_exclude"))

    def test_market_culture_rejects_finance_brief_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "[브리프] 한화생명 교보생명 삼성화재 하나카드",
            "snippet": "해외 여행객 대상 보험과 카드 혜택을 정리했다.",
            "query": "해외 여행객수",
            "link": "https://example.com/finance-brief",
            "source": "Naver News",
        }

        self.assertFalse(keyword_filter.validate(article, category="market_culture"))

    def test_market_culture_accepts_travel_payment_data_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "카드 해외 이용액으로 본 일본 여행 소비 증가",
            "snippet": "전년 대비 여행객 결제 이용액이 늘며 방한·출국 수요 회복을 보여줬다.",
            "query": "해외 여행객수",
            "link": "https://example.com/travel-payment-data",
            "source": "Naver News",
        }

        self.assertTrue(keyword_filter.validate(article, category="market_culture"))
        self.assertIn("이용액", article["matched_strong_market_signal_keywords"])

    def test_market_culture_rejects_generic_local_culture_event(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "용인특례시, 어린이날 대축제 개최",
            "snippet": "K-POP 공연과 체험 콘텐츠를 운영한다.",
            "query": "K-POP",
            "link": "https://example.com/local-event",
            "source": "Naver News",
        }

        self.assertFalse(keyword_filter.validate(article, category="market_culture"))

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

    def test_global_trend_rejects_vendor_product_page(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "MVNO Roaming Control Center – Mobileum - Active Intelligence",
            "snippet": "MVNO roaming services and network enterprise systems.",
            "query": "MVNO roaming services",
            "link": "https://www.mobileum.com/products/roaming-management/network-enterprise-systems/mvno-roaming-control-center",
            "source": "Google",
            "source_domain": "www.mobileum.com",
            "published": datetime(2026, 4, 28, tzinfo=timezone.utc),
        }

        self.assertFalse(keyword_filter.validate(article, category="global_trend"))

    def test_global_trend_accepts_missing_date_news_when_relevant(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "5G SA Roaming Enablement",
            "snippet": "5G SA roaming services for mobile operators.",
            "query": "5G SA roaming",
            "link": "https://example.com/news/5g-sa-roaming",
            "source": "Google",
            "source_domain": "example.com",
            "published": None,
        }

        self.assertTrue(keyword_filter.validate(article, category="global_trend"))

    def test_global_trend_accepts_recent_travel_esim_news(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "Travel eSIM market expands as roaming demand rises",
            "snippet": "Apr 28, 2026 ... Operators report stronger travel eSIM adoption and roaming usage.",
            "query": "travel eSIM trends 2026",
            "link": "https://example.com/news/travel-esim-market",
            "source": "Google",
            "source_domain": "example.com",
            "published": datetime(2026, 4, 28, tzinfo=timezone.utc),
        }

        self.assertTrue(keyword_filter.validate(article, category="global_trend"))

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

    def test_esim_industry_rejects_dosirak_food_event_article(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "[브리프] 농심 오뚜기 삼양식품 삼립 外",
            "snippet": "도시락 이벤트와 식품 프로모션 소식을 전했다.",
            "query": "도시락 이벤트",
            "link": "https://example.com/food-event",
            "source": "Naver News",
        }

        self.assertFalse(keyword_filter.validate(article, category="esim_industry"))

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

    def test_voc_does_not_use_query_as_review_signal(self):
        keyword_filter = self.build_filter()
        article = {
            "title": "Airalo eSIM 가격표 정리",
            "snippet": "국가별 데이터 용량과 가격을 비교했다.",
            "query": "Airalo 후기",
            "link": "https://example.com/airalo-price",
            "source": "Naver Blog",
        }

        self.assertFalse(keyword_filter.validate(article, category="voc_esim"))
        self.assertEqual(article["voc_type"], None)

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
