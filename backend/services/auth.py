import secrets
from datetime import datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.user import User, UserSession

# pbkdf2_sha256 avoids native bcrypt backend incompatibilities across environments.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_session(db: Session, user_id: str) -> UserSession:
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    session = UserSession(
        id=token,
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_from_token(db: Session, token: str) -> User | None:
    session = db.query(UserSession).filter(UserSession.id == token).first()
    if not session:
        return None
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        return None
    return db.query(User).filter(User.id == session.user_id).first()
