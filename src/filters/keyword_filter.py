"""
키워드 필터링 (스팸, 광고, 게임)
"""
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class KeywordFilter:
    """키워드 기반 필터링"""

    KOREAN_PARTICLES: Tuple[str, ...] = (
        "으로부터",
        "에서부터",
        "까지",
        "부터",
        "에게",
        "께서",
        "에서",
        "으로",
        "처럼",
        "보다",
        "하고",
        "이랑",
        "라도",
        "마저",
        "조차",
        "밖에",
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "의",
        "와",
        "과",
        "도",
        "만",
        "로",
        "랑",
    )
    VOC_KEYWORDS: Set[str] = {
        "후기",
        "리뷰",
        "재구매",
        "사용기",
        "불편",
        "안됨",
        "오류",
        "속도",
        "개통",
        "환불",
        "문의",
        "연결",
        "설정",
    }
    ROAMING_KEYWORDS: Set[str] = {
        "로밍",
        "데이터 로밍",
        "로밍 요금제",
        "해외 로밍",
        "통화 로밍",
        "baro 로밍",
        "skt 로밍",
        "kt 로밍",
        "lgu+ 로밍",
        "lg유플러스 로밍",
    }
    CARRIER_ROAMING_KEYWORDS: Set[str] = {
        "baro 로밍",
        "skt 로밍",
        "kt 로밍",
        "lgu+ 로밍",
        "lg유플러스 로밍",
    }
    ESIM_KEYWORDS: Set[str] = {
        "esim",
        "이심",
        "e심",
        "로밍도깨비",
        "로밍 도깨비",
        "유심사",
        "도시락 esim",
        "도시락esim",
        "말톡",
        "에어알로",
        "airalo",
        "핀다이렉트",
        "핀다이렉트 esim",
        "로밍도깨비 esim",
        "로밍 도깨비 esim",
    }
    ESIM_BRAND_KEYWORDS: Set[str] = {
        "로밍도깨비",
        "로밍 도깨비",
        "유심사",
        "도시락 esim",
        "도시락esim",
        "말톡",
        "에어알로",
        "airalo",
        "핀다이렉트",
        "핀다이렉트 esim",
        "로밍도깨비 esim",
        "로밍 도깨비 esim",
    }

    def __init__(
        self,
        blacklist_domains: List[str],
        excluded_keywords: List[str],
        global_trend_rules: Optional[Dict] = None,
        category_rules: Optional[Dict[str, Dict]] = None,
    ):
        """
        Args:
            blacklist_domains: 블랙리스트 도메인 패턴
            excluded_keywords: 제외 키워드
        """
        self.blacklist_domains: Set[str] = set(blacklist_domains)
        self.excluded_keywords: Set[str] = set(kw.lower() for kw in excluded_keywords)
        rules = global_trend_rules or {}
        self.global_trend_excluded_domains: Set[str] = set(
            value.lower() for value in rules.get("excluded_domains", [])
        )
        self.global_trend_excluded_url_patterns: Set[str] = set(
            value.lower() for value in rules.get("excluded_url_patterns", [])
        )
        self.global_trend_excluded_keywords: Set[str] = set(
            value.lower() for value in rules.get("excluded_keywords", [])
        )
        self.global_trend_required_keywords: Set[str] = set(
            value.lower() for value in rules.get("required_keywords", [])
        )
        self.global_trend_required_topic_keywords: Set[str] = set(
            value.lower() for value in rules.get("required_topic_keywords", [])
        )
        self.global_trend_required_signal_keywords: Set[str] = set(
            value.lower() for value in rules.get("required_signal_keywords", [])
        )
        self.global_trend_excluded_marketing_keywords: Set[str] = set(
            value.lower() for value in rules.get("excluded_marketing_keywords", [])
        )
        self.global_trend_require_published_date = bool(
            rules.get("require_published_date", False)
        )
        self.category_rules: Dict[str, Dict] = category_rules or {}

    def _is_allowed_global_excluded_keyword(self, category: str, keyword: str) -> bool:
        rule = self.category_rules.get(category) or {}
        allowed_keywords = {
            str(value).lower()
            for value in rule.get("allow_global_excluded_keywords", [])
            if str(value).strip()
        }
        return str(keyword or "").lower() in allowed_keywords

    def _is_allowed_blacklist_domain(self, category: str, blocked_value: str) -> bool:
        rule = self.category_rules.get(category) or {}
        allowed_values = {
            str(value).lower()
            for value in rule.get("allow_blacklist_domains", [])
            if str(value).strip()
        }
        return str(blocked_value or "").lower() in allowed_values

    def _build_text_map(self, article: Dict) -> Dict[str, str]:
        title = str(article.get("title", "")).lower()
        snippet = str(article.get("snippet", "")).lower()
        query = str(article.get("query", "")).lower()
        return {
            "title": title,
            "snippet": snippet,
            "content": f"{title} {snippet}".strip(),
            "query": query,
            "combined": f"{title} {snippet} {query}".strip(),
        }

    def _keyword_matches(self, text: str, keyword: str) -> bool:
        normalized_text = str(text or "").lower()
        normalized_keyword = str(keyword or "").strip().lower()
        if not normalized_text or not normalized_keyword:
            return False

        escaped = re.escape(normalized_keyword)
        particle_suffix = "|".join(re.escape(value) for value in self.KOREAN_PARTICLES)
        right_boundary = (
            rf"(?:(?![0-9a-zA-Z가-힣])|(?:{particle_suffix})(?![0-9a-zA-Z가-힣]))"
        )
        pattern = rf"(?<![0-9a-zA-Z가-힣]){escaped}{right_boundary}"
        return re.search(pattern, normalized_text) is not None

    def _extract_matches(self, combined_text: str, keywords: Set[str]) -> List[str]:
        return sorted(
            keyword for keyword in keywords if self._keyword_matches(combined_text, keyword)
        )

    def _contains_any(self, text: str, keywords: Set[str]) -> bool:
        return any(str(keyword or "").lower() in text for keyword in keywords)

    def _apply_category_rule(self, article: Dict, category: str, text_map: Dict[str, str]) -> bool:
        rule = self.category_rules.get(category) or {}
        if category == "market_culture":
            return self._apply_market_culture_rule(article, text_map, rule)
        if category == "esim_industry":
            return self._apply_esim_industry_rule(article, text_map, rule)

        include_keywords = {
            value.lower() for value in rule.get("include_keywords", []) if str(value).strip()
        }
        exclude_keywords = {
            value.lower() for value in rule.get("exclude_keywords", []) if str(value).strip()
        }
        required_keywords = {
            value.lower() for value in rule.get("required_keywords", []) if str(value).strip()
        }
        match_field = str(rule.get("match_field", "combined")).lower()
        field_text = text_map.get(match_field, text_map["combined"])

        matched_excludes = self._extract_matches(field_text, exclude_keywords)
        if matched_excludes:
            article["matched_exclude_keywords"] = matched_excludes
            article["relevance_reason"] = f"category_exclude:{','.join(matched_excludes)}"
            return False

        matched_includes = self._extract_matches(field_text, include_keywords)
        if include_keywords and not matched_includes:
            article["matched_include_keywords"] = []
            article["relevance_reason"] = "missing_category_include_keywords"
            return False

        matched_required = self._extract_matches(field_text, required_keywords)
        if required_keywords and not matched_required:
            article["matched_required_keywords"] = []
            article["relevance_reason"] = "missing_category_required_keywords"
            return False

        article["matched_include_keywords"] = matched_includes
        article["matched_required_keywords"] = matched_required
        article["matched_exclude_keywords"] = []
        return True

    def _apply_esim_industry_rule(self, article: Dict, text_map: Dict[str, str], rule: Dict) -> bool:
        match_field = str(rule.get("match_field", "content")).lower()
        field_text = text_map.get(match_field, text_map["content"])
        brand_keywords = {
            str(value).lower()
            for value in rule.get("brand_keywords", [])
            if str(value).strip()
        }
        guarded_brand_keywords = {
            str(key).lower(): [
                str(value).lower() for value in values if str(value).strip()
            ]
            for key, values in (rule.get("guarded_brand_keywords", {}) or {}).items()
        }

        matched_brands = self._extract_matches(field_text, brand_keywords)
        if matched_brands:
            article["matched_include_keywords"] = matched_brands
            article["matched_exclude_keywords"] = []
            article["relevance_reason"] = "esim_industry_brand_match"
            return True

        for guarded_brand, companion_keywords in guarded_brand_keywords.items():
            if not self._keyword_matches(field_text, guarded_brand):
                continue
            matched_companions = [
                keyword
                for keyword in companion_keywords
                if self._keyword_matches(field_text, keyword)
            ]
            if matched_companions:
                article["matched_include_keywords"] = [guarded_brand, *matched_companions]
                article["matched_exclude_keywords"] = []
                article["relevance_reason"] = "esim_industry_guarded_brand_match"
                return True

        article["matched_include_keywords"] = []
        article["relevance_reason"] = "missing_esim_industry_brand_keywords"
        return False

    def _apply_market_culture_rule(self, article: Dict, text_map: Dict[str, str], rule: Dict) -> bool:
        match_field = str(rule.get("match_field", "content")).lower()
        field_text = text_map.get(match_field, text_map["content"])

        include_keywords = {
            str(value).lower()
            for value in rule.get("include_keywords", [])
            if str(value).strip()
        }
        exclude_keywords = {
            str(value).lower()
            for value in rule.get("exclude_keywords", [])
            if str(value).strip()
        }
        topic_keywords = {
            str(value).lower()
            for value in rule.get("topic_keywords", [])
            if str(value).strip()
        }
        market_signal_keywords = {
            str(value).lower()
            for value in rule.get("market_signal_keywords", [])
            if str(value).strip()
        }
        strong_market_signal_keywords = {
            str(value).lower()
            for value in rule.get("strong_market_signal_keywords", [])
            if str(value).strip()
        }
        soft_exclude_keywords = {
            str(value).lower()
            for value in rule.get("soft_exclude_keywords", [])
            if str(value).strip()
        }

        matched_excludes = self._extract_matches(field_text, exclude_keywords)
        if matched_excludes:
            article["matched_exclude_keywords"] = matched_excludes
            article["relevance_reason"] = f"category_exclude:{','.join(matched_excludes)}"
            return False

        matched_includes = self._extract_matches(field_text, include_keywords)
        if include_keywords and not matched_includes:
            article["matched_include_keywords"] = []
            article["relevance_reason"] = "missing_category_include_keywords"
            return False

        matched_topics = self._extract_matches(field_text, topic_keywords)
        if topic_keywords and not matched_topics:
            article["matched_topic_keywords"] = []
            article["relevance_reason"] = "missing_market_culture_topic"
            return False

        matched_market_signals = self._extract_matches(field_text, market_signal_keywords)
        if market_signal_keywords and not matched_market_signals:
            article["matched_market_signal_keywords"] = []
            article["relevance_reason"] = "missing_market_culture_signal"
            return False

        matched_soft_excludes = self._extract_matches(field_text, soft_exclude_keywords)
        matched_strong_market_signals = self._extract_matches(
            field_text,
            strong_market_signal_keywords,
        )
        if matched_soft_excludes and not matched_strong_market_signals:
            article["matched_soft_exclude_keywords"] = matched_soft_excludes
            article["matched_market_signal_keywords"] = matched_market_signals
            article["relevance_reason"] = (
                f"market_culture_soft_exclude:{','.join(matched_soft_excludes)}"
            )
            return False

        article["matched_include_keywords"] = matched_includes
        article["matched_required_keywords"] = matched_market_signals
        article["matched_topic_keywords"] = matched_topics
        article["matched_market_signal_keywords"] = matched_market_signals
        article["matched_strong_market_signal_keywords"] = matched_strong_market_signals
        article["matched_soft_exclude_keywords"] = matched_soft_excludes
        article["matched_exclude_keywords"] = []
        return True

    def _classify_voc(self, article: Dict, text_map: Dict[str, str]) -> Tuple[Optional[str], List[str]]:
        title_text = text_map["title"]
        content_text = text_map["content"]

        matched_voc = self._extract_matches(title_text, self.VOC_KEYWORDS)
        if not matched_voc:
            matched_voc = self._extract_matches(content_text, self.VOC_KEYWORDS)
        if not matched_voc:
            return None, []

        matched_roaming = self._extract_matches(title_text, self.ROAMING_KEYWORDS)
        matched_esim = self._extract_matches(title_text, self.ESIM_KEYWORDS)
        matched_carrier_roaming = self._extract_matches(
            title_text, self.CARRIER_ROAMING_KEYWORDS
        )
        matched_esim_brands = self._extract_matches(title_text, self.ESIM_BRAND_KEYWORDS)

        if not matched_roaming and not matched_esim:
            matched_roaming = self._extract_matches(content_text, self.ROAMING_KEYWORDS)
            matched_esim = self._extract_matches(content_text, self.ESIM_KEYWORDS)
        if not matched_carrier_roaming:
            matched_carrier_roaming = self._extract_matches(
                content_text, self.CARRIER_ROAMING_KEYWORDS
            )
        if not matched_esim_brands:
            matched_esim_brands = self._extract_matches(
                content_text, self.ESIM_BRAND_KEYWORDS
            )

        signals = [
            *(f"voc:{value}" for value in matched_voc),
            *(f"roaming:{value}" for value in matched_roaming),
            *(f"carrier_roaming:{value}" for value in matched_carrier_roaming),
            *(f"esim:{value}" for value in matched_esim),
            *(f"esim_brand:{value}" for value in matched_esim_brands),
        ]

        if matched_carrier_roaming:
            return "voc_roaming", signals
        if matched_esim_brands:
            return "voc_esim", signals
        if matched_roaming and not matched_esim:
            return "voc_roaming", signals
        if matched_esim:
            return "voc_esim", signals
        if matched_roaming:
            return "voc_roaming", signals
        return None, signals

    def _validate_global_trend(self, article: Dict, text_map: Dict[str, str]) -> bool:
        link = str(article.get('link', '')).lower()
        # "combined" = title + snippet + query. RSS 기사는 query에 topic_hint가 주입돼
        # 있어 roaming/esim 등 키워드가 포함된다.
        combined_text = text_map["combined"]
        source_domain = str(article.get('source_domain', '')).lower()
        title = str(article.get('title', '')).lower()

        # 시그널 워드(launch/announce/forecast/...)는 하드 탈락 조건이 아니라 소프트 랭킹
        # 신호다. 유무를 기록해 validate() 점수에서 뉴스성 높은 기사를 우선한다.
        article["global_trend_signal"] = bool(
            self.global_trend_required_signal_keywords
        ) and self._contains_any(
            combined_text, self.global_trend_required_signal_keywords
        )

        if self.global_trend_require_published_date and not article.get("published"):
            logger.debug(f"Filtered global_trend by missing published date: {title[:50]}")
            return False

        if any(domain in source_domain for domain in self.global_trend_excluded_domains):
            logger.debug(f"Filtered global_trend by domain: {source_domain}")
            return False

        if any(pattern in link for pattern in self.global_trend_excluded_url_patterns):
            logger.debug(f"Filtered global_trend by URL pattern: {link}")
            return False

        if self._contains_any(combined_text, self.global_trend_excluded_keywords):
            logger.debug(f"Filtered global_trend by excluded keyword: {title[:50]}")
            return False

        if self._contains_any(combined_text, self.global_trend_excluded_marketing_keywords):
            logger.debug(f"Filtered global_trend by marketing keyword: {title[:50]}")
            return False

        if self.global_trend_required_keywords and not self._contains_any(
            combined_text, self.global_trend_required_keywords
        ):
            logger.debug(f"Filtered global_trend by missing required keyword: {title[:50]}")
            return False

        # required_topic_keywords 는 required_keywords 와 거의 동일한 목록이고
        # RSS 소스 기사의 경우 스니펫이 짧아 중복 게이트가 과도하게 탈락시킨다.
        # topic_hint → query 필드로 컨텍스트를 주입하므로 별도 게이트 불필요.

        # required_signal_keywords 는 위에서 소프트 랭킹 신호로 전환했으므로
        # 여기서 하드 탈락시키지 않는다. 시그널이 없어도 관련성 게이트만 통과하면 유지.
        return True

    def validate(self, article: Dict, category: str = "") -> bool:
        """
        기사 검증

        Args:
            article: 기사 딕셔너리
            category: 카테고리 키

        Returns:
            유효하면 True
        """
        link = article.get('link', '')
        title = article.get('title', '').lower()
        text_map = self._build_text_map(article)
        combined_text = text_map["combined"]

        # 1. Cafe/Blog URL 필터링 (News API에서 반환되는 경우)
        if 'cafe.naver.com' in link or 'blog.naver.com' in link:
            if article.get('source') == 'Naver News':
                logger.debug(f"Filtered: Cafe/Blog URL in News API")
                return False

        # 2. 블랙리스트 도메인
        if any(
            blocked in link
            for blocked in self.blacklist_domains
            if not self._is_allowed_blacklist_domain(category, blocked)
        ):
            logger.debug(f"Filtered: URL blacklist - {title[:50]}")
            return False

        # 3. 제외 키워드 (제목 + 요약 + 수집 질의)
        for bad_word in self.excluded_keywords:
            if self._is_allowed_global_excluded_keyword(category, bad_word):
                continue
            if self._keyword_matches(combined_text, bad_word):
                logger.debug(f"Filtered: Keyword '{bad_word}' - {title[:50]}")
                return False

        # 4. URL에 포함된 키워드
        if any(
            bad_word in link.lower()
            for bad_word in self.excluded_keywords
            if not self._is_allowed_global_excluded_keyword(category, bad_word)
        ):
            logger.debug(f"Filtered: Link keyword - {title[:50]}")
            return False

        if not self._apply_category_rule(article, category, text_map):
            return False

        if category == "global_trend" and not self._validate_global_trend(article, text_map):
            return False

        if category in {"voc_roaming", "voc_esim"}:
            voc_category, signals = self._classify_voc(article, text_map)
            article["matched_signals"] = signals
            article["voc_type"] = voc_category
            if voc_category != category:
                article["relevance_reason"] = f"voc_mismatch:{voc_category or 'none'}"
                return False
            article["relevance_reason"] = "voc_match"
            article["relevance_score"] = 100 + len(signals)
        else:
            relevance_score = 50 + len(article.get("matched_include_keywords", []))
            # global_trend 시그널 워드 포함 기사에 부스트 → 정렬 상단 우선.
            if category == "global_trend" and article.get("global_trend_signal"):
                relevance_score += 25
            article["relevance_score"] = relevance_score
            article["relevance_reason"] = article.get("relevance_reason", "category_match")

        return True

    def filter_articles(self, articles: List[Dict], category: str = "") -> List[Dict]:
        """
        기사 리스트 키워드 필터링

        Args:
            articles: 기사 리스트
            category: 카테고리 키

        Returns:
            필터링된 기사 리스트
        """
        filtered = [a for a in articles if self.validate(a, category=category)]
        logger.info(f"Keyword filter: {len(filtered)}/{len(articles)} passed")
        return filtered
