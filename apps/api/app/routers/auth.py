import re
import secrets

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import CsrfGuard, CurrentTenant, CurrentUser, DbSession
from app.models import Membership, Tenant, TenantSettings, User
from app.schemas import AuthResponse, LoginRequest, RegisterRequest
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "access_token",
        token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        "csrf_token",
        secrets.token_urlsafe(32),
        max_age=settings.access_token_expire_minutes * 60,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, response: Response, db: DbSession) -> AuthResponse:
    email = payload.email.lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    base_slug = re.sub(r"[^a-z0-9]+", "-", payload.company_name.lower()).strip("-")[:60] or "empresa"
    slug = f"{base_slug}-{secrets.token_hex(3)}"
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    tenant = Tenant(name=payload.company_name, slug=slug)
    db.add_all([user, tenant])
    await db.flush()
    db.add(Membership(user_id=user.id, tenant_id=tenant.id, role="owner"))
    db.add(
        TenantSettings(
            tenant_id=tenant.id,
            version=1,
            payload={
                "company_name": payload.company_name,
                "timezone": "America/Sao_Paulo",
                "assistant": {
                    "tone": "acolhedor",
                    "instructions": "",
                    "human_handoff_message": "Vou chamar uma pessoa da equipe.",
                },
                "business_hours": {},
            },
            created_by=user.id,
        )
    )
    await db.commit()
    set_auth_cookie(response, create_access_token(user.id))
    return AuthResponse(user=user, tenant_id=tenant.id)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response, db: DbSession) -> AuthResponse:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    membership = await db.scalar(select(Membership).where(Membership.user_id == user.id).limit(1))
    if not membership:
        raise HTTPException(status_code=403, detail="Usuário sem organização")
    set_auth_cookie(response, create_access_token(user.id))
    return AuthResponse(user=user, tenant_id=membership.tenant_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, _csrf: CsrfGuard) -> None:
    response.delete_cookie("access_token", domain=settings.cookie_domain, path="/")
    response.delete_cookie("csrf_token", domain=settings.cookie_domain, path="/")


@router.get("/me", response_model=AuthResponse)
async def me(user: CurrentUser, tenant: CurrentTenant) -> AuthResponse:
    return AuthResponse(user=user, tenant_id=tenant.id)
