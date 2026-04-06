"""
커스텀 예외 클래스
"""


class NewsCollectorError(Exception):
    """기본 예외"""
    pass


class APIError(NewsCollectorError):
    """API 호출 실패"""
    pass


class RateLimitError(APIError):
    """API Rate Limit 초과"""
    pass


class ValidationError(NewsCollectorError):
    """데이터 검증 실패"""
    pass


class AnalysisError(NewsCollectorError):
    """AI 분석 실패"""
    pass


class NotificationError(NewsCollectorError):
    """알림 발송 실패"""
    pass
