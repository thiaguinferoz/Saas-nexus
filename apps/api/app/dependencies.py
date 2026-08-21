import secrets
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.access import sync_billing_access
from app.database import get_db
from app.models import Membership, Tenant, User
from app.security import decode_access_token

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão ausente")
    try:
        user_id, session_version = decode_access_token(access_token)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida") from None
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo")
    if user.session_version != session_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão revogada")
    if not user.email_verified_at:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="E-mail ainda não confirmado")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def verify_csrf(
    csrf_cookie: Annotated[str | None, Cookie(alias="csrf_token")] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF inválido")


CsrfGuard = Annotated[None, Depends(verify_csrf)]


async def get_current_tenant(db: DbSession, user: CurrentUser) -> Tenant:
    statement = (
        select(Tenant)
        .join(Membership, Membership.tenant_id == Tenant.id)
        .where(Membership.user_id == user.id)
        .limit(1)
    )
    tenant = await db.scalar(statement)
    if not tenant:
        raise HTTPException(status_code=403, detail="Usuário sem organização")
    await sync_billing_access(db, tenant)
    await db.commit()
    return tenant


CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
