import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select, update

from app.config import get_settings
from app.dependencies import CsrfGuard, CurrentTenant, CurrentUser, DbSession
from app.email import EmailDeliveryError, TransactionalEmailService
from app.models import AuthToken, AuthTokenPurpose, Membership, OutboxEvent, Subscription, SubscriptionStatus, Tenant, TenantSettings, TenantStatus, User
from app.schemas import AuthResponse, EmailRequest, LoginRequest, MessageRead, RegisterRequest, ResetPasswordRequest, TokenRequest
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie("access_token", token, max_age=settings.access_token_expire_minutes * 60, httponly=True, secure=settings.cookie_secure, samesite="lax", domain=settings.cookie_domain, path="/")
    response.set_cookie("csrf_token", secrets.token_urlsafe(32), max_age=settings.access_token_expire_minutes * 60, httponly=False, secure=settings.cookie_secure, samesite="lax", domain=settings.cookie_domain, path="/")


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_token(db: DbSession, user: User, purpose: AuthTokenPurpose, lifetime: timedelta) -> tuple[str, AuthToken]:
    await db.execute(update(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose, AuthToken.used_at.is_(None)).values(used_at=datetime.now(UTC)))
    raw_token = secrets.token_urlsafe(48)
    record = AuthToken(user_id=user.id, purpose=purpose, token_hash=token_digest(raw_token), expires_at=datetime.now(UTC) + lifetime)
    db.add(record)
    await db.flush()
    return raw_token, record


async def find_valid_token(db: DbSession, token: str, purpose: AuthTokenPurpose) -> AuthToken | None:
    return await db.scalar(select(AuthToken).where(AuthToken.token_hash == token_digest(token), AuthToken.purpose == purpose, AuthToken.used_at.is_(None), AuthToken.expires_at > datetime.now(UTC)))


async def begin_trial(db: DbSession, user: User) -> Membership:
    membership = await db.scalar(select(Membership).where(Membership.user_id == user.id).limit(1))
    if not membership:
        raise HTTPException(status_code=403, detail="Usuário sem organização")
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == membership.tenant_id))
    now = datetime.now(UTC)
    if not subscription:
        subscription = Subscription(tenant_id=membership.tenant_id, provider=settings.billing_provider)
        db.add(subscription)
    if not subscription.trial_started_at:
        trial_end = now + timedelta(days=settings.trial_days)
        subscription.status = SubscriptionStatus.TRIALING
        subscription.trial_started_at = now
        subscription.trial_ends_at = trial_end
        subscription.current_period_end = trial_end
        tenant = await db.get(Tenant, membership.tenant_id)
        if tenant:
            tenant.status = TenantStatus.PROVISIONING
            db.add(OutboxEvent(tenant_id=tenant.id, event_type="tenant.provisioning.requested", payload={"tenant_id": str(tenant.id), "source": "free_trial"}))
    return membership


@router.post("/register", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> MessageRead:
    email = payload.email.lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    base_slug = re.sub(r"[^a-z0-9]+", "-", payload.company_name.lower()).strip("-")[:60] or "empresa"
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    tenant = Tenant(name=payload.company_name, slug=f"{base_slug}-{secrets.token_hex(3)}")
    db.add_all([user, tenant])
    await db.flush()
    db.add(Membership(user_id=user.id, tenant_id=tenant.id, role="owner"))
    db.add(Subscription(tenant_id=tenant.id, provider=settings.billing_provider, status=SubscriptionStatus.PENDING))
    db.add(TenantSettings(tenant_id=tenant.id, version=1, payload={"company_name": payload.company_name, "timezone": "America/Sao_Paulo", "assistant": {"tone": "acolhedor", "instructions": "", "human_handoff_message": "Vou chamar uma pessoa da equipe."}, "business_hours": {}}, created_by=user.id))
    raw_token, token_record = await issue_token(db, user, AuthTokenPurpose.VERIFY_EMAIL, timedelta(hours=settings.email_verification_expire_hours))
    await db.commit()
    try:
        await TransactionalEmailService().send_verification(to=user.email, name=user.full_name, token=raw_token, token_id=token_record.id)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=503, detail=f"Conta criada, mas {exc}. Use reenviar confirmação.") from exc
    return MessageRead(message="Conta criada. Confira seu e-mail para ativar os 3 dias grátis.")


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(payload: TokenRequest, response: Response, db: DbSession) -> AuthResponse:
    token_record = await find_valid_token(db, payload.token, AuthTokenPurpose.VERIFY_EMAIL)
    if not token_record:
        raise HTTPException(status_code=400, detail="Link inválido ou expirado")
    user = await db.get(User, token_record.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Conta não encontrada")
    now = datetime.now(UTC)
    user.email_verified_at = user.email_verified_at or now
    token_record.used_at = now
    membership = await begin_trial(db, user)
    await db.commit()
    set_auth_cookie(response, create_access_token(user.id, user.session_version))
    return AuthResponse(user=user, tenant_id=membership.tenant_id)


@router.post("/resend-verification", response_model=MessageRead)
async def resend_verification(payload: EmailRequest, db: DbSession) -> MessageRead:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or user.email_verified_at:
        return MessageRead(message="Se a conta precisar de confirmação, enviaremos um novo link.")
    raw_token, token_record = await issue_token(db, user, AuthTokenPurpose.VERIFY_EMAIL, timedelta(hours=settings.email_verification_expire_hours))
    await db.commit()
    try:
        await TransactionalEmailService().send_verification(to=user.email, name=user.full_name, token=raw_token, token_id=token_record.id)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return MessageRead(message="Se a conta precisar de confirmação, enviaremos um novo link.")


@router.post("/forgot-password", response_model=MessageRead)
async def forgot_password(payload: EmailRequest, db: DbSession) -> MessageRead:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.email_verified_at:
        return MessageRead(message="Se o e-mail estiver cadastrado, enviaremos as instruções.")
    raw_token, token_record = await issue_token(db, user, AuthTokenPurpose.RESET_PASSWORD, timedelta(minutes=settings.password_reset_expire_minutes))
    await db.commit()
    try:
        await TransactionalEmailService().send_password_reset(to=user.email, name=user.full_name, token=raw_token, token_id=token_record.id)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return MessageRead(message="Se o e-mail estiver cadastrado, enviaremos as instruções.")


@router.post("/reset-password", response_model=MessageRead)
async def reset_password(payload: ResetPasswordRequest, db: DbSession) -> MessageRead:
    token_record = await find_valid_token(db, payload.token, AuthTokenPurpose.RESET_PASSWORD)
    if not token_record:
        raise HTTPException(status_code=400, detail="Link inválido ou expirado")
    user = await db.get(User, token_record.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Conta não encontrada")
    now = datetime.now(UTC)
    user.password_hash = hash_password(payload.password)
    user.session_version += 1
    token_record.used_at = now
    await db.execute(update(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == AuthTokenPurpose.RESET_PASSWORD, AuthToken.used_at.is_(None)).values(used_at=now))
    await db.commit()
    return MessageRead(message="Senha alterada. Você já pode entrar.")


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response, db: DbSession) -> AuthResponse:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    if not user.email_verified_at:
        raise HTTPException(status_code=403, detail="Confirme seu e-mail antes de entrar")
    membership = await db.scalar(select(Membership).where(Membership.user_id == user.id).limit(1))
    if not membership:
        raise HTTPException(status_code=403, detail="Usuário sem organização")
    set_auth_cookie(response, create_access_token(user.id, user.session_version))
    return AuthResponse(user=user, tenant_id=membership.tenant_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, _csrf: CsrfGuard) -> None:
    response.delete_cookie("access_token", domain=settings.cookie_domain, path="/")
    response.delete_cookie("csrf_token", domain=settings.cookie_domain, path="/")


@router.get("/me", response_model=AuthResponse)
async def me(user: CurrentUser, tenant: CurrentTenant) -> AuthResponse:
    return AuthResponse(user=user, tenant_id=tenant.id)
