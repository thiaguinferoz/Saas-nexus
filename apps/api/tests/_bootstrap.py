import os


def configure_test_environment() -> None:
    """Provide the minimum settings required before importing application modules."""
    defaults = {
        "APP_SECRET_KEY": "test-secret-key-that-is-longer-than-thirty-two-characters",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "REDIS_URL": "redis://localhost:6379/15",
        "FRONTEND_URL": "http://localhost:3000",
        "COOKIE_SECURE": "false",
        "STRIPE_SECRET_KEY": "sk_test_unit",
        "STRIPE_PRICE_ID": "price_unit",
        "RESEND_API_KEY": "re_test_unit",
        "REDIS_STREAM_PREFIX": "nexus-test",
    }
    for name, value in defaults.items():
        os.environ.setdefault(name, value)
