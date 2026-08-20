from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import func, select, update

from app.dependencies import CsrfGuard, CurrentTenant, CurrentUser, DbSession
from app.models import TenantSettings
from app.schemas import SettingsRead, TenantRead, TenantSettingsPayload

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("", response_model=TenantRead)
async def read_tenant(tenant: CurrentTenant) -> TenantRead:
    return TenantRead.model_validate(tenant)


@router.get("/settings", response_model=SettingsRead)
async def read_settings(tenant: CurrentTenant, db: DbSession) -> SettingsRead:
    settings = await db.scalar(
        select(TenantSettings)
        .where(TenantSettings.tenant_id == tenant.id, TenantSettings.is_active.is_(True))
        .order_by(TenantSettings.version.desc())
        .limit(1)
    )
    if not settings:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    return SettingsRead(version=settings.version, payload=settings.payload, created_at=settings.created_at)


@router.put("/settings", response_model=SettingsRead)
async def replace_settings(
    payload: TenantSettingsPayload,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
    _csrf: CsrfGuard,
    if_match: int = Header(alias="If-Match"),
) -> SettingsRead:
    current_version = await db.scalar(
        select(func.max(TenantSettings.version)).where(TenantSettings.tenant_id == tenant.id)
    )
    if current_version != if_match:
        raise HTTPException(status_code=409, detail={"message": "Configuração alterada", "version": current_version})
    await db.execute(
        update(TenantSettings)
        .where(TenantSettings.tenant_id == tenant.id, TenantSettings.is_active.is_(True))
        .values(is_active=False)
    )
    settings = TenantSettings(
        tenant_id=tenant.id,
        version=current_version + 1,
        payload=payload.model_dump(mode="json"),
        created_by=user.id,
    )
    tenant.name = payload.company_name
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return SettingsRead(version=settings.version, payload=settings.payload, created_at=settings.created_at)
