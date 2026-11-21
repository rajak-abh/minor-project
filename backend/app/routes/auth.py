from datetime import timedelta
from datetime import datetime, timezone
import hashlib
import secrets
import smtplib
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.database.session import get_db
from app.models.entities import CompanyProfile, PasswordResetToken, RevokedToken, StudentProfile, User
from app.schemas import LoginInput, RegisterInput, TokenPair
from app.core.dependencies import current_user, oauth2_scheme

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(str(user.id), "access", timedelta(minutes=settings.jwt_access_minutes)),
        refresh_token=create_token(str(user.id), "refresh", timedelta(days=settings.jwt_refresh_days)),
    )


@router.post("/register", response_model=TokenPair, status_code=201)
def register(payload: RegisterInput, db: Session = Depends(get_db)):
    role = payload.role.lower()
    if role not in {"student", "company"}:
        raise HTTPException(400, "Registration is available for student and company accounts")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "An account with this email already exists")
    if role == "company" and not payload.company_name:
        raise HTTPException(422, "company_name is required for company registration")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role=role)
    db.add(user)
    db.flush()
    if role == "student":
        db.add(StudentProfile(user_id=user.id, full_name=payload.full_name or ""))
    else:
        db.add(CompanyProfile(user_id=user.id, name=payload.company_name or ""))
    db.commit()
    db.refresh(user)
    return token_pair(user)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(401, "Incorrect email or password")
    return token_pair(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: dict, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.get("refresh_token", ""))
        if claims.get("type") != "refresh":
            raise ValueError("Wrong token type")
        if db.query(RevokedToken).filter_by(jti=claims.get("jti")).first():
            raise ValueError("Revoked token")
        user = db.get(User, int(claims["sub"]))
    except (ValueError, TypeError, KeyError):
        raise HTTPException(401, "Invalid or expired refresh token")
    if not user or not user.is_active:
        raise HTTPException(401, "User is inactive or no longer exists")
    expiration = datetime.fromtimestamp(claims["exp"], timezone.utc)
    db.add(RevokedToken(jti=claims["jti"], expires_at=expiration))
    db.commit()
    return token_pair(user)


@router.post("/logout")
def logout(payload: dict | None = None, db: Session = Depends(get_db), user: User = Depends(current_user), access_token: str = Depends(oauth2_scheme)):
    tokens = [access_token]
    if payload and payload.get("refresh_token"):
        tokens.append(payload["refresh_token"])
    for token in tokens:
        try:
            claims = decode_token(token)
            if claims.get("sub") == str(user.id) and claims.get("jti"):
                expires = datetime.fromtimestamp(claims["exp"], timezone.utc)
                if not db.query(RevokedToken).filter_by(jti=claims["jti"]).first():
                    db.add(RevokedToken(jti=claims["jti"], expires_at=expires))
        except (ValueError, KeyError, TypeError):
            continue
    db.commit()
    return {"message": "Logged out"}


@router.get("/me")
def who_am_i(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/forgot-password")
def forgot_password(payload: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(payload.get("email", "")).lower()).first()
    response = {"message": "If an account exists, password reset instructions will be sent."}
    if not user:
        return response
    raw_token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(user_id=user.id, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)))
    db.commit()
    if settings.smtp_host and settings.smtp_from_email:
        message = EmailMessage()
        message["Subject"] = "Reset your SkillTrack password"
        message["From"] = settings.smtp_from_email
        message["To"] = user.email
        message.set_content(f"Use this one-time token in the password reset form: {raw_token}\nIt expires in 30 minutes.")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)
    elif settings.app_env.lower() == "development":
        response["development_reset_token"] = raw_token
    return response


@router.post("/reset-password")
def reset_password(payload: dict, db: Session = Depends(get_db)):
    raw_token = str(payload.get("token", ""))
    password = str(payload.get("password", ""))
    if len(password) < 10 or len(password) > 128:
        raise HTTPException(422, "Password must be 10 to 128 characters")
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.query(PasswordResetToken).filter_by(token_hash=digest, used_at=None).first()
    expires_at = token.expires_at.replace(tzinfo=timezone.utc) if token and token.expires_at.tzinfo is None else (token.expires_at if token else None)
    if not token or expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Reset token is invalid or expired")
    user = db.get(User, token.user_id)
    if not user:
        raise HTTPException(400, "Reset token is invalid or expired")
    user.password_hash = hash_password(password)
    token.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Password reset successfully"}
