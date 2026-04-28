"""
유틸리티 헬퍼 함수
"""
import re
from typing import Dict, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


ASCII_ALPHA_PATTERN = re.compile(r"[A-Za-z]")
KOREAN_CHAR_PATTERN = re.compile(r"[가-힣]")
TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "mkt_")
GLOBAL_TREND_TITLE_FALLBACK = "해외 로밍 동향 기사(한글 번역 준비중)"
GLOBAL_TREND_SUMMARY_FALLBACK = "한글 요약 준비중입니다. 원문 링크에서 확인해 주세요."


def clean_html(text: str) -> str:
    """
    HTML 태그 정리

    Args:
        text: 원본 텍스트

    Returns:
        정리된 텍스트
    """
    return (str(text or "")
            .replace('<b>', '')
            .replace('</b>', '')
            .replace('&quot;', '"'))


def normalize_title(title: str) -> str:
    """
    제목 정규화 (중복 제거용)

    Args:
        title: 원본 제목

    Returns:
        정규화된 제목
    """
    return (str(title or "")
            .replace(' ', '')
            .replace('<b>', '')
            .replace('</b>', '')
            .replace('&quot;', '')
            .lower())


def canonicalize_link(link: str) -> str:
    """중복 제거용 URL 정규화."""
    raw_link = str(link or "").strip()
    if not raw_link:
        return ""

    parsed = urlparse(raw_link)
    hostname = (parsed.netloc or "").lower()
    if hostname in {"n.news.naver.com", "news.naver.com"}:
        hostname = "news.naver.com"
    if hostname in {"m.blog.naver.com", "blog.naver.com"}:
        hostname = "blog.naver.com"
    if hostname in {"m.cafe.naver.com", "cafe.naver.com"}:
        hostname = "cafe.naver.com"

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    normalized_path = (parsed.path or "").rstrip("/")
    return urlunparse(
        (
            (parsed.scheme or "https").lower(),
            hostname,
            normalized_path,
            "",
            urlencode(filtered_query, doseq=True),
            "",
        )
    )


def normalize_link(link: str) -> str:
    """이전 호출부 호환용 alias."""
    return canonicalize_link(link)


def contains_ascii_alpha(text: str) -> bool:
    """영문 알파벳 포함 여부를 반환한다."""
    return bool(ASCII_ALPHA_PATTERN.search(str(text or "")))


def contains_korean_text(text: str) -> bool:
    """한글 포함 여부를 반환한다."""
    return bool(KOREAN_CHAR_PATTERN.search(str(text or "")))


def is_english_only_text(text: str) -> bool:
    """한글 없이 영문 알파벳만 포함된 문장인지 판단한다."""
    safe_text = str(text or "").strip()
    return bool(safe_text) and contains_ascii_alpha(safe_text) and not contains_korean_text(safe_text)


def inspect_global_trend_translation(title: str, summary: str) -> Dict[str, object]:
    """
    Global Roaming Trend 번역 상태를 판별하고 안전한 표시 텍스트를 반환한다.
    출력용 title/summary는 항상 문자열을 보장하고, 실패 상태는 metadata로 남긴다.
    """
    original_title = str(title or "").strip()
    original_summary = str(summary or "").strip()

    issues = []
    safe_title = original_title
    safe_summary = original_summary

    if not safe_title:
        issues.append("missing_title")
        safe_title = GLOBAL_TREND_TITLE_FALLBACK
    elif is_english_only_text(safe_title):
        issues.append("non_korean_title")
        safe_title = GLOBAL_TREND_TITLE_FALLBACK

    if not safe_summary:
        issues.append("missing_summary")
        safe_summary = GLOBAL_TREND_SUMMARY_FALLBACK
    elif is_english_only_text(safe_summary):
        issues.append("non_korean_summary")
        safe_summary = GLOBAL_TREND_SUMMARY_FALLBACK

    if not issues:
        translation_status = "translated"
    elif len(issues) == 4 or (
        "non_korean_title" in issues and "non_korean_summary" in issues
    ) or (
        "missing_title" in issues and "missing_summary" in issues
    ):
        translation_status = "full_fallback"
    else:
        translation_status = "partial_fallback"

    return {
        "title": safe_title,
        "summary": safe_summary,
        "translation_status": translation_status,
        "translation_notes": issues,
        "raw_title": original_title,
        "raw_summary": original_summary,
    }


def ensure_global_trend_korean_text(title: str, summary: str) -> Tuple[str, str]:
    """
    Global Roaming Trend 항목의 제목/요약에서 영문-only 노출을 차단한다.
    한글이 포함된 mixed text는 유지하고, 번역 상태 metadata는 inspection에서 추적한다.
    """
    inspection = inspect_global_trend_translation(title=title, summary=summary)
    return str(inspection["title"]), str(inspection["summary"])
