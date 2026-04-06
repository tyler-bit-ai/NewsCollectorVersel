"""
0404.go.kr 게시판(공관안전공지/안전공지) 수집기
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import requests

from .base import BaseCollector

logger = logging.getLogger(__name__)


class Mofa0404Collector(BaseCollector):
    """0404 게시판에서 KST 날짜 범위의 통신/로밍 관련 공지를 수집한다."""

    BOARD_URLS = {
        "embsyNtc": "https://0404.go.kr/bbs/embsyNtc/list",
        "safetyNtc": "https://0404.go.kr/bbs/safetyNtc/list",
    }

    BOARD_NAMES = {
        "embsyNtc": "공관안전공지",
        "safetyNtc": "안전공지",
    }

    STRONG_KEYWORDS = [
        "로밍",
        "esim",
        "e-sim",
        "유심",
        "sim",
        "데이터 로밍",
        "국제전화",
        "sms",
        "mms",
    ]
    CONTEXT_KEYWORDS = [
        "통신",
        "통신망",
        "인터넷",
        "데이터",
        "문자",
        "네트워크",
    ]
    WEAK_KEYWORDS = [
        "차단",
        "중단",
        "불가",
        "장애",
        "두절",
        "제한",
    ]
    DISRUPTION_KEYWORDS = [
        "장애",
        "불가",
        "제한",
        "중단",
        "두절",
        "먹통",
        "불안정",
        "지연",
        "원활하지",
        "끊김",
        "오류",
        "마비",
        "수신 불가",
        "발신 불가",
        "접속 불가",
        "사용 불가",
    ]
    EXCLUDE_PATTERNS = [
        r"통신\s*보안",
        r"보안\s*강화",
        r"반군",
        r"기뢰",
        r"해상\s*폭발물",
        r"화산",
        r"이산화황",
        r"유해\s*가스",
        r"공기\s*유입\s*차단",
        r"출입\s*차단",
        r"연락두절",
        r"연락주시기\s*바랍니다",
        r"긴급전화",
        r"대표전화",
        r"직통",
        r"영사안전콜센터",
        r"출입\s*제한",
        r"하차\s*제한",
        r"항공권\s*미소지자",
        r"터미널\s*진입",
        r"리플릿",
        r"체류\s*정보",
        r"대비\s*요령",
        r"유용한\s*여행정보",
    ]
    ADVISORY_MARKERS = [
        "가능성",
        "참고",
        "리플릿",
        "체류 정보",
        "대응 방법",
        "대비 요령",
        "유용한 여행정보",
        "안내드립니다",
    ]
    ACTIVE_ISSUE_MARKERS = [
        "현재",
        "최근",
        "일시",
        "일부",
        "장애",
        "불가",
        "중단",
        "지연",
        "오류",
        "먹통",
        "마비",
        "복구",
        "점검",
        "원활하지 않습니다",
        "원활하지 않아",
        "수신 불가",
        "발신 불가",
        "접속 불가",
        "사용 불가",
    ]
    TITLE_SERVICE_KEYWORDS = STRONG_KEYWORDS + CONTEXT_KEYWORDS
    KEYWORDS = STRONG_KEYWORDS + CONTEXT_KEYWORDS + WEAK_KEYWORDS

    LIST_ITEM_PATTERN = re.compile(
        r'<a href="(?P<link>/bbs/(?P<board>embsyNtc|safetyNtc)/[^"]*/detail[^"]*)" class="btn title">'
        r'(?P<title>[\s\S]*?)</a>[\s\S]*?<td>\s*(?P<date>\d{4}-\d{2}-\d{2})\s*</td>',
        re.IGNORECASE,
    )
    VIEW_BODY_PATTERN = re.compile(
        r'<div class="view-body"\s*[^>]*>(?P<body>[\s\S]*?)</div>',
        re.IGNORECASE,
    )
    TAG_PATTERN = re.compile(r"<[^>]+>")
    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\s+[ㅇ◦]\s+|\s*[-•]\s+|\n+")

    def __init__(self, debug_mode: bool = False, max_pages: int = 30, list_failure_threshold: int = 3):
        super().__init__(debug_mode)
        self.max_pages = max_pages
        self.list_failure_threshold = max(1, list_failure_threshold)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            }
        )
        self._compiled_exclude_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.EXCLUDE_PATTERNS]

    def collect(self, query: str = "", limit: int = 0) -> List[Dict]:
        """BaseCollector interface."""
        return self.collect_today_keyword_posts()

    def collect_today_keyword_posts(self) -> List[Dict]:
        """오늘 게시물 중 통신/로밍 관련 공지를 수집한다."""
        today_kst = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
        return self.collect_keyword_posts_by_date_range(today_kst, today_kst)

    def collect_keyword_posts_by_date_range(self, start_date_kst: str, end_date_kst: str) -> List[Dict]:
        """게시판 날짜 범위(KST, YYYY-MM-DD)의 통신/로밍 관련 공지를 수집한다."""
        collected: List[Dict] = []
        seen_links = set()

        for board_key, list_url in self.BOARD_URLS.items():
            board_name = self.BOARD_NAMES[board_key]
            logger.info(f"[0404] Collecting board: {board_name}")
            board_items = self._collect_board(board_key, list_url, start_date_kst, end_date_kst)

            for item in board_items:
                link = item["link"]
                if link in seen_links:
                    continue
                seen_links.add(link)
                collected.append(item)

        logger.info(f"[0404] Collected matched posts: {len(collected)}")
        return collected

    def _collect_board(self, board_key: str, list_url: str, start_date_kst: str, end_date_kst: str) -> List[Dict]:
        results: List[Dict] = []
        board_name = self.BOARD_NAMES[board_key]
        consecutive_failures = 0

        for page_index in range(1, self.max_pages + 1):
            page_url = f"{list_url}?pageIndex={page_index}"
            try:
                response = self.session.get(page_url, timeout=15)
                response.raise_for_status()
                page_html = response.text
                consecutive_failures = 0
            except Exception as e:
                logger.warning(f"[0404] Failed to load list page: {page_url} ({e})")
                consecutive_failures += 1
                if consecutive_failures >= self.list_failure_threshold:
                    logger.warning(
                        f"[0404] Stop board crawl after {consecutive_failures} consecutive failures: {board_name}"
                    )
                    break
                continue

            list_items = list(self.LIST_ITEM_PATTERN.finditer(page_html))
            if not list_items:
                break

            target_items = []
            older_exists = False
            for match in list_items:
                date_text = match.group("date").strip()
                if start_date_kst <= date_text <= end_date_kst:
                    target_items.append({"match": match, "date_text": date_text})
                elif date_text < start_date_kst:
                    older_exists = True

            logger.info(
                f"[0404] {board_name} page {page_index}: parsed={len(list_items)}, in_range={len(target_items)}"
            )

            for item in target_items:
                match = item["match"]
                date_text = item["date_text"]
                relative_link = html.unescape(match.group("link").strip())
                link = f"https://0404.go.kr{relative_link}"
                title = self._to_one_line(match.group("title"))

                body_text = self._fetch_detail_body(link)
                match_result = self._classify_post(title=title, body_text=body_text)
                if not match_result:
                    logger.info(f"[0404] Skipped non-telecom post: {title}")
                    continue

                content_preview = body_text
                if len(content_preview) > 200:
                    content_preview = f"{content_preview[:200].rstrip()}..."

                results.append(
                    {
                        "board_name": board_name,
                        "title": title,
                        "content_one_line": content_preview,
                        "link": link,
                        "published_date": date_text,
                        "matched_keywords": match_result["matched_keywords"],
                        "match_reason": match_result["match_reason"],
                        "matched_excerpt": match_result["matched_excerpt"],
                    }
                )
                self.collected_count += 1
                logger.info(
                    f"[0404] Matched post ({match_result['match_reason']}): "
                    f"{title} | keywords={match_result['matched_keywords']}"
                )

            if not target_items and older_exists:
                break

        logger.info(f"[0404] {board_name} matched posts: {len(results)}")
        return results

    def _fetch_detail_body(self, detail_url: str) -> str:
        try:
            response = self.session.get(detail_url, timeout=15)
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"[0404] Failed to load detail page: {detail_url} ({e})")
            return ""

        match = self.VIEW_BODY_PATTERN.search(response.text)
        if not match:
            return ""

        return self._to_one_line(match.group("body"))

    def _classify_post(self, title: str, body_text: str) -> Optional[Dict]:
        combined_text = f"{title} {body_text}".strip()
        if self._has_exclude_pattern(combined_text):
            return None

        title_service_hits = self._find_keywords(title, self.TITLE_SERVICE_KEYWORDS)
        title_disruption_hits = self._find_keywords(title, self.DISRUPTION_KEYWORDS)
        body_hits = self._matched_keywords(body_text)
        if title_service_hits and title_disruption_hits and not self._looks_like_advisory(title):
            return self._build_match_result(
                reason="title_service_disruption",
                matched_keywords=title_service_hits + title_disruption_hits + body_hits,
                excerpt=title,
            )

        body_match = self._find_context_disruption_match(title="", body_text=body_text)
        if title_service_hits and body_match:
            return self._build_match_result(
                reason="title_service_with_body_disruption",
                matched_keywords=title_service_hits + body_match["matched_keywords"],
                excerpt=body_match["matched_excerpt"] or title,
            )

        sentence_match = self._find_context_disruption_match(title=title, body_text=body_text)
        if sentence_match:
            return sentence_match

        return None

    def _find_context_disruption_match(self, title: str, body_text: str) -> Optional[Dict]:
        for sentence in self._split_sentences(f"{title}\n{body_text}"):
            if self._has_exclude_pattern(sentence):
                continue
            if self._looks_like_advisory(sentence):
                continue
            context_hits = self._find_keywords(sentence, self.TITLE_SERVICE_KEYWORDS)
            disruption_hits = self._find_keywords(sentence, self.DISRUPTION_KEYWORDS)

            if context_hits and disruption_hits and self._has_active_issue_marker(sentence):
                return self._build_match_result(
                    reason="context_disruption_sentence",
                    matched_keywords=context_hits + disruption_hits,
                    excerpt=sentence,
                )

        return None

    def _matched_keywords(self, text: str) -> List[str]:
        return self._normalize_keywords(self._find_keywords(text, self.KEYWORDS))

    def _find_keywords(self, text: str, keywords: List[str]) -> List[str]:
        text_lower = text.lower()
        matched = []
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)
        return self._normalize_keywords(matched)

    def _normalize_keywords(self, keywords: List[str]) -> List[str]:
        normalized: List[str] = []
        for keyword in keywords:
            normalized_value = keyword.upper() if keyword.lower() in {"sms", "mms", "esim", "sim", "e-sim"} else keyword
            if normalized_value not in normalized:
                normalized.append(normalized_value)
        return normalized

    def _has_disruption_keyword(self, text: str) -> bool:
        return bool(self._find_keywords(text, self.DISRUPTION_KEYWORDS))

    def _has_exclude_pattern(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self._compiled_exclude_patterns)

    def _has_active_issue_marker(self, text: str) -> bool:
        text_lower = text.lower()
        return any(marker.lower() in text_lower for marker in self.ACTIVE_ISSUE_MARKERS)

    def _looks_like_advisory(self, text: str) -> bool:
        text_lower = text.lower()
        return any(marker.lower() in text_lower for marker in self.ADVISORY_MARKERS)

    def _split_sentences(self, text: str) -> List[str]:
        parts = [part.strip() for part in self.SENTENCE_SPLIT_PATTERN.split(text) if part.strip()]
        return parts or [text.strip()]

    def _find_excerpt(self, text: str, keywords: List[str]) -> str:
        if not text:
            return ""

        text_lower = text.lower()
        indices = [text_lower.find(keyword.lower()) for keyword in keywords if text_lower.find(keyword.lower()) >= 0]
        if not indices:
            return text[:160]

        start = max(0, min(indices) - 40)
        end = min(len(text), min(indices) + 120)
        return text[start:end].strip()

    def _build_match_result(self, reason: str, matched_keywords: List[str], excerpt: str) -> Dict:
        return {
            "match_reason": reason,
            "matched_keywords": self._normalize_keywords(matched_keywords),
            "matched_excerpt": excerpt[:200].strip(),
        }

    def _to_one_line(self, value: str) -> str:
        text = self.TAG_PATTERN.sub(" ", value)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
