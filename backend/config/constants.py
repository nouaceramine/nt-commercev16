"""
NT Commerce - Centralized Constants
Single source of truth for all magic numbers and configuration values
"""

# ============ PAGINATION ============
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
DEFAULT_PAGE = 1

# ============ AUTH ============
MIN_PASSWORD_LENGTH = 8  # Security: Was 4 (SEC-003)
ACCESS_TOKEN_EXPIRE_HOURS = 2  # Security: Was 24 (SEC-005)
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_LOGIN_ATTEMPTS = 3  # Security: Was 5 (SEC-004)
LOCKOUT_MINUTES = 30

# ============ STOCK ============
DEFAULT_LOW_STOCK_THRESHOLD = 10
MAX_PRODUCT_QUANTITY = 100000
MAX_SALE_ITEMS = 100

# ============ VALIDATION ============
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 2000
MAX_PHONE_LENGTH = 20
MAX_BARCODE_LENGTH = 50

# ============ CURRENCY ============
DEFAULT_CURRENCY = "دج"  # Algerian Dinar
DEFAULT_CURRENCY_CODE = "DZD"

# ============ CACHE ============
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_MAX_SIZE = 10000

# ============ FEATURE FLAGS ============
FEATURE_FLAGS = {
    "pos": True,
    "inventory": True,
    "customers": True,
    "credit_sales": True,
    "reports": True,
    "recharge": True,
    "barcode": True,
    "woocommerce": False,
    "ai_bots": False,
    "loyalty_points": False,
    "iptv": False,
    "backup": True,
    "wallet": True,
    "maintenance": True,
}

# ============ CASH BOXES ============
DEFAULT_CASH_BOXES = [
    {"id": "cash", "name": "الصندوق النقدي", "name_fr": "Caisse", "type": "cash", "balance": 0},
    {"id": "bank", "name": "الحساب البنكي", "name_fr": "Compte bancaire", "type": "bank", "balance": 0},
    {"id": "wallet", "name": "المحفظة الإلكترونية", "name_fr": "Portefeuille électronique", "type": "wallet", "balance": 0},
    {"id": "safe", "name": "الخزنة", "name_fr": "Coffre-fort", "type": "safe", "balance": 0},
]

# ============ ROLES HIERARCHY ============
ROLES_HIERARCHY = {
    "super_admin": {"level": 100, "can_manage": ["admin", "manager", "seller", "user"]},
    "admin": {"level": 80, "can_manage": ["manager", "seller", "user"]},
    "manager": {"level": 60, "can_manage": ["seller", "user"]},
    "sales_supervisor": {"level": 50, "can_manage": ["seller"]},
    "seller": {"level": 30, "can_manage": []},
    "inventory_manager": {"level": 40, "can_manage": []},
    "accountant": {"level": 45, "can_manage": []},
    "user": {"level": 10, "can_manage": []},
}

# ============ API RATE LIMITS ============
RATE_LIMITS = {
    "auth_login": "10/minute",
    "auth_register": "5/minute",
    "api_general": "100/minute",
    "api_heavy": "20/minute",
}
