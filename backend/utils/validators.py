"""
Shared Validators - DRY Principle
Consolidates validation logic used across multiple schemas and routes
Fixes QUAL-007: Duplicate Validation Logic
"""
import re
from typing import Optional
from config.constants import MIN_NAME_LENGTH, MAX_NAME_LENGTH, MAX_PHONE_LENGTH


def sanitize_string(value: str, max_length: int = MAX_NAME_LENGTH) -> str:
    """Remove HTML tags, strip whitespace, validate length"""
    if not value:
        return ""
    # Remove HTML tags
    value = re.sub(r"<[^>]+>", "", value)
    # Strip whitespace
    value = value.strip()
    # Limit length
    if len(value) > max_length:
        raise ValueError(f"Value exceeds maximum length of {max_length}")
    return value


def validate_name(name: str, field_name: str = "Name") -> str:
    """Validate name fields (products, customers, suppliers)"""
    sanitized = sanitize_string(name)
    if not sanitized or len(sanitized) < MIN_NAME_LENGTH:
        raise ValueError(f"{field_name} must be at least {MIN_NAME_LENGTH} characters")
    return sanitized


def validate_email(email: str) -> str:
    """Validate email format"""
    if not email or not email.strip():
        return ""
    email = email.strip()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    return email


def validate_phone(phone: str) -> str:
    """Validate phone number"""
    if not phone:
        return ""
    phone = phone.strip()
    if len(phone) > MAX_PHONE_LENGTH:
        raise ValueError(f"Phone number exceeds {MAX_PHONE_LENGTH} characters")
    # Allow only digits, spaces, +, -, (, )
    if not re.match(r"^[\d\s\+\-\(\)]+$", phone):
        raise ValueError("Phone number contains invalid characters")
    return phone


def validate_price(value: float, field_name: str = "Price") -> float:
    """Validate price fields"""
    if value is None:
        return 0.0
    if value < 0:
        raise ValueError(f"{field_name} must be zero or positive")
    return float(value)


def validate_quantity(value: int, field_name: str = "Quantity") -> int:
    """Validate quantity fields"""
    if value is None:
        return 0
    if value < 0:
        raise ValueError(f"{field_name} must be zero or positive")
    return int(value)


def validate_barcode(barcode: str) -> str:
    """Validate barcode format"""
    if not barcode:
        return ""
    barcode = barcode.strip()
    if len(barcode) > 50:
        raise ValueError("Barcode exceeds 50 characters")
    return barcode
