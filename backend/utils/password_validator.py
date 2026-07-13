"""
Password Validator - NIST SP 800-63B Compliant
SECURITY FIX: Increased min length from 4 to 8 characters (SEC-003)
"""
import re
from config.constants import MIN_PASSWORD_LENGTH


def validate_password(password: str) -> dict:
    """
    Validate password against NIST SP 800-63B guidelines:
    - Minimum 8 characters
    - No complexity requirements (NIST recommends against them)
    - Check against common passwords
    """
    errors = []

    if not password:
        errors.append("Password is required")
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    elif len(password) > 128:
        errors.append("Password must not exceed 128 characters")

    # Check for common weak patterns (optional but recommended)
    common_patterns = ["password", "123456", "qwerty", "admin", "letmein"]
    password_lower = password.lower()
    for pattern in common_patterns:
        if pattern in password_lower:
            errors.append(f"Password contains common weak pattern: '{pattern}'")
            break

    # Check for consecutive identical characters (e.g., "aaa")
    if re.search(r'(.)\1{3,}', password):
        errors.append("Password has too many repeated characters")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "strength": _calculate_strength(password) if not errors else "weak",
    }


def _calculate_strength(password: str) -> str:
    """Calculate password strength"""
    score = 0
    if len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1

    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'\d', password):
        score += 1
    if re.search(r'[^A-Za-z0-9]', password):
        score += 1

    if score >= 5:
        return "strong"
    elif score >= 3:
        return "medium"
    return "weak"
