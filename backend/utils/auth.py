"""
Authentication utilities for NT Commerce
SECURITY HARDENED - Fixes SEC-001, SEC-005, SEC-004
"""
import os
import uuid
import jwt
import bcrypt
import redis
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.database import db, main_db, get_tenant_db, set_tenant_context, _tenant_db_ctx
from config.constants import (
    ACCESS_TOKEN_EXPIRE_HOURS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    MAX_LOGIN_ATTEMPTS,
    LOCKOUT_MINUTES,
)

# JWT Configuration - CRITICAL FIX: No hardcoded fallback (SEC-001)
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY environment variable is REQUIRED. "
        "Set a strong random secret: openssl rand -hex 32"
    )

ALGORITHM = "HS256"

# Redis for brute force protection (SEC-004)
try:
    _redis_client = redis.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
    )
    _redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

security = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    """Create short-lived access token (SEC-005: reduced from 24h to 2h)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create long-lived refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())  # Unique token ID for revocation
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate JWT token"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ============ BRUTE FORCE PROTECTION (SEC-004) ============

def _get_redis_key(email: str) -> str:
    return f"login_attempts:{email}"


def check_brute_force(email: str) -> None:
    """Check if account is locked due to too many failed attempts"""
    if not REDIS_AVAILABLE:
        return  # Graceful degradation
    key = _get_redis_key(email)
    lock_key = f"{key}:locked"
    if _redis_client.exists(lock_key):
        ttl = _redis_client.ttl(lock_key)
        raise HTTPException(
            status_code=429,
            detail=f"الحساب مقفل. حاول بعد {ttl // 60 + 1} دقيقة (Account locked. Try again in {ttl // 60 + 1} minutes)",
        )


def record_failed_login(email: str) -> None:
    """Record a failed login attempt"""
    if not REDIS_AVAILABLE:
        return
    key = _get_redis_key(email)
    attempts = _redis_client.incr(key)
    _redis_client.expire(key, LOCKOUT_MINUTES * 60)
    if attempts >= MAX_LOGIN_ATTEMPTS:
        lock_key = f"{key}:locked"
        _redis_client.setex(lock_key, LOCKOUT_MINUTES * 60, "1")


def clear_failed_login(email: str) -> None:
    """Clear failed login attempts on successful login"""
    if not REDIS_AVAILABLE:
        return
    key = _get_redis_key(email)
    _redis_client.delete(key)
    _redis_client.delete(f"{key}:locked")


# ============ AUTH DEPENDENCIES ============

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get the current authenticated user from JWT token.

    SECURITY: This is the SINGLE canonical implementation.
    The legacy version in main.py is deprecated and will be removed.
    """
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id = payload.get("sub")
        user_type = payload.get("type", "tenant")
        role = payload.get("role")

        if user_type == "super_admin" or role == "super_admin":
            user = await main_db.users.find_one({"id": user_id})
            if not user:
                user = await main_db.super_admins.find_one({"id": user_id})
            if user:
                user["user_type"] = "super_admin"
                user["role"] = "super_admin"
                return user

        tenant_id = payload.get("tenant_id")
        if tenant_id:
            tenant_db = get_tenant_db(tenant_id)
            set_tenant_context(tenant_db)
            user = await tenant_db.users.find_one({"id": user_id})
            if user:
                user["tenant_id"] = tenant_id
                user["user_type"] = "tenant"
                return user

        raise HTTPException(status_code=401, detail="User not found")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_tenant_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get tenant user - sets up tenant DB context"""
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id = payload.get("sub")
        user_type = payload.get("type", "tenant")
        role = payload.get("role")
        tenant_id = payload.get("tenant_id")

        if user_type == "super_admin" or role == "super_admin":
            user = await main_db.users.find_one({"id": user_id})
            if not user:
                user = await main_db.super_admins.find_one({"id": user_id})
            if user:
                user["user_type"] = "super_admin"
                user["role"] = "super_admin"
                if tenant_id:
                    tenant_db = get_tenant_db(tenant_id)
                    set_tenant_context(tenant_db)
                    user["tenant_id"] = tenant_id
                return user

        if tenant_id:
            tenant_db = get_tenant_db(tenant_id)
            set_tenant_context(tenant_db)
            user = await tenant_db.users.find_one({"id": user_id})
            if user:
                user["tenant_id"] = tenant_id
                user["user_type"] = "tenant"
                return user

        raise HTTPException(status_code=401, detail="User not found")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin role"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_tenant_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Require tenant admin role"""
    role = current_user.get("role", "")
    if role not in ["admin", "manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin or Manager access required")
    return current_user


async def require_tenant(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Require valid tenant context"""
    if (
        not current_user.get("tenant_id")
        and current_user.get("user_type") != "super_admin"
    ):
        raise HTTPException(status_code=403, detail="Tenant access required")
    return current_user


async def get_super_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Require super admin access"""
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id = payload.get("sub")
        user_type = payload.get("type", "tenant")
        role = payload.get("role")

        if user_type != "super_admin" and role != "super_admin":
            raise HTTPException(status_code=403, detail="Super admin access required")

        user = await main_db.users.find_one({"id": user_id})
        if not user:
            user = await main_db.super_admins.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="Super admin not found")

        user["user_type"] = "super_admin"
        user["role"] = "super_admin"
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
