"""JWT Authentication helpers."""
import bcrypt
from flask_jwt_extended import create_access_token


def hash_password(password: str) -> str:
    """Hash a plain password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_user_token(user) -> str:
    """Create a JWT access token for a user."""
    return create_access_token(identity=str(user.id))
