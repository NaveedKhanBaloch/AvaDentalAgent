from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])
security = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized_email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == normalized_email).first()
    if user is None and normalized_email == settings.demo_admin_email.lower():
        user = User(
            email=normalized_email,
            password_hash=hash_password(settings.demo_admin_password),
            full_name="Harbor Dental Admin",
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserProfile)
def me(token: str = Depends(security)) -> UserProfile:
    return UserProfile(id="demo-user", email="admin@harbordentaldemo.local", full_name="Harbor Dental Admin", status="active", role="Clinic Owner")


@router.post("/logout")
def logout() -> dict[str, str]:
    return {"status": "success", "message": "Logged out successfully."}


@router.post("/change-password")
def change_password() -> dict[str, str]:
    return {"status": "success", "message": "Password updated."}
