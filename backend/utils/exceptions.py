"""
Centralized Exception Hierarchy
Fixes QUAL-010: Inconsistent Error Handling
Provides unified error responses with localization support
"""
from fastapi import HTTPException
from typing import Optional, Dict, Any


class NTCommerceException(HTTPException):
    """Base exception for NT Commerce"""

    def __init__(
        self,
        status_code: int,
        message_en: str,
        message_ar: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message_en = message_en
        self.message_ar = message_ar or message_en
        self.error_code = error_code or f"ERR_{status_code}"
        self.details = details or {}

        super().__init__(
            status_code=status_code,
            detail={
                "message": message_en,
                "message_ar": self.message_ar,
                "code": self.error_code,
                **self.details,
            },
        )


class AuthenticationError(NTCommerceException):
    """Invalid credentials or token"""

    def __init__(self, message: str = "Invalid credentials", message_ar: str = "بيانات الدخول غير صحيحة"):
        super().__init__(status_code=401, message_en=message, message_ar=message_ar, error_code="AUTH_001")


class AuthorizationError(NTCommerceException):
    """Insufficient permissions"""

    def __init__(self, message: str = "Access denied", message_ar: str = "غير مصرح"):
        super().__init__(status_code=403, message_en=message, message_ar=message_ar, error_code="AUTH_002")


class ResourceNotFoundError(NTCommerceException):
    """Resource not found"""

    def __init__(self, resource: str = "Resource", resource_ar: str = "المورد"):
        super().__init__(
            status_code=404,
            message_en=f"{resource} not found",
            message_ar=f"{resource_ar} غير موجود",
            error_code="NOT_FOUND",
        )


class ValidationError(NTCommerceException):
    """Input validation failed"""

    def __init__(self, field: str, message: str, message_ar: str):
        super().__init__(
            status_code=400,
            message_en=f"Validation error: {field} - {message}",
            message_ar=f"خطأ في التحقق: {field} - {message_ar}",
            error_code="VALIDATION_001",
            details={"field": field},
        )


class RateLimitError(NTCommerceException):
    """Rate limit exceeded"""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            message_en=f"Rate limit exceeded. Retry after {retry_after} seconds",
            message_ar=f"تم تجاوز الحد المسموح. أعد المحاولة بعد {retry_after} ثانية",
            error_code="RATE_LIMIT",
            details={"retry_after": retry_after},
        )


class ConflictError(NTCommerceException):
    """Resource conflict (duplicate, etc.)"""

    def __init__(self, message: str = "Resource already exists", message_ar: str = "المورد موجود مسبقاً"):
        super().__init__(status_code=409, message_en=message, message_ar=message_ar, error_code="CONFLICT")


class BruteForceError(NTCommerceException):
    """Account locked due to brute force"""

    def __init__(self, lockout_minutes: int):
        super().__init__(
            status_code=429,
            message_en=f"Account locked. Try again in {lockout_minutes} minutes",
            message_ar=f"الحساب مقفل. حاول بعد {lockout_minutes} دقيقة",
            error_code="BRUTE_FORCE",
            details={"lockout_minutes": lockout_minutes},
        )
