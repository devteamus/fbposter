"""Application configuration."""
import os
import tempfile


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def _get_str(name: str, default: str) -> str:
    return os.environ.get(name) or default


def _resolve_db_url() -> str:
    """
    Resolve DB URL.
    - If DATABASE_URL is set (postgres), normalize and use it.
    - Else fall back to SQLite in /app/data, then /tmp.
    """
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if raw:
        # SQLAlchemy 1.4+ requires postgresql:// scheme
        if raw.startswith("postgres://"):
            return raw.replace("postgres://", "postgresql://", 1)
        return raw

    # Local dev fallback — try /app/data, then /tmp
    primary_dir = "/app/data"
    fallback_dir = os.path.join(tempfile.gettempdir(), "fb_autoposter")
    try:
        os.makedirs(primary_dir, exist_ok=True)
        import sqlite3
        test_db = os.path.join(primary_dir, ".write_test.db")
        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
        os.remove(test_db)
        return f"sqlite:///{primary_dir}/fb_autoposter.db"
    except Exception:
        os.makedirs(fallback_dir, exist_ok=True)
        return f"sqlite:///{fallback_dir}/fb_autoposter.db"


class Config:
    SECRET_KEY = _get_str("SECRET_KEY", "super-secret-change-me-2026")
    JWT_SECRET_KEY = _get_str("JWT_SECRET_KEY", "jwt-secret-change-me-2026")
    JWT_ACCESS_TOKEN_EXPIRES = _get_int("JWT_ACCESS_TOKEN_EXPIRES", 86400)

    # Refuse to run with the placeholder secrets outside local dev — anyone
    # who has read this source (it's public in the repo) could forge a
    # valid JWT for ANY user account if these defaults are still active.
    _INSECURE_DEFAULTS = {"super-secret-change-me-2026", "jwt-secret-change-me-2026"}
    _is_dev = _get_str("FLASK_ENV", "production").lower() in ("development", "dev")
    if not _is_dev and (SECRET_KEY in _INSECURE_DEFAULTS or JWT_SECRET_KEY in _INSECURE_DEFAULTS):
        raise RuntimeError(
            "SECURITY: SECRET_KEY / JWT_SECRET_KEY are still set to the placeholder "
            "defaults. Set real random values via environment variables (e.g. "
            "`openssl rand -hex 32`) before running outside local dev, or set "
            "FLASK_ENV=development if you're intentionally testing locally."
        )

    SQLALCHEMY_DATABASE_URI = _resolve_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": {"connect_timeout": 10} if "postgresql" in _resolve_db_url() else {},
    }

    # Uploads
    _upload_primary = os.environ.get("UPLOAD_FOLDER", "/app/uploads")
    try:
        os.makedirs(_upload_primary, exist_ok=True)
        _test = os.path.join(_upload_primary, ".write_test")
        with open(_test, "w") as f:
            f.write("ok")
        os.remove(_test)
        UPLOAD_FOLDER = _upload_primary
    except (OSError, PermissionError):
        UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "fb_uploads")
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    MAX_CSV_ROWS = _get_int("MAX_CSV_ROWS", 5000)

    # Static frontend files (built by Dockerfile, copied to /app/static)
    STATIC_FOLDER = os.environ.get("STATIC_FOLDER", "/app/static")

    WORKER_TICK_SECONDS = _get_int("WORKER_TICK_SECONDS", 30)
    MAX_RETRIES = _get_int("MAX_RETRIES", 3)
    CSV_RETENTION_HOURS = _get_int("CSV_RETENTION_HOURS", 24)
    # Full job history (job + its post rows) is purged from the DB this many
    # days after the job finished, so storage doesn't grow forever.
    JOB_RETENTION_DAYS = _get_int("JOB_RETENTION_DAYS", 15)

    CORS_ORIGINS = _get_str("CORS_ORIGINS", "*").split(",")
