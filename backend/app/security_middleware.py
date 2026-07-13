"""
Security Middleware - Hardened CORS + Security Headers
Fixes: SEC-002 (CORS misconfiguration), SEC-009 (Missing security headers)
"""
import os
from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    OWASP Recommended Security Headers
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS - Force HTTPS (only in production)
        if os.environ.get("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy - Strict
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Remove server identification
        response.headers.pop("Server", None)

        return response


def setup_cors(app):
    """
    Configure CORS with strict security settings.
    SEC-002 Fix: No wildcard origins, credentials only with specific origins
    """
    cors_env = os.environ.get("CORS_ORIGINS", "")
    origins = [o.strip() for o in cors_env.split(",") if o.strip()] if cors_env else []

    # Add preview URL if set
    preview_url = os.environ.get("PREVIEW_URL", "")
    if preview_url and preview_url not in origins:
        origins.append(preview_url)

    if not origins:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("CORS_ORIGINS is empty - CORS will block all cross-origin requests")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # No PATCH unless needed
        allow_headers=["Authorization", "Content-Type", "Accept"],  # Minimal headers
        expose_headers=["X-Response-Time"],
        max_age=600,  # Cache preflight for 10 minutes
    )

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
