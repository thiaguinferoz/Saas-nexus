import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CsrfGuard, CurrentTenant, DbSession
from app.models import CatalogItem
from app.schemas import CatalogItemCreate, CatalogItemRead, CatalogItemUpdate

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/items", response_model=list[CatalogItemRead])
async def list_catalog_items(tenant: CurrentTenant, db: DbSession) -> list[CatalogItemRead]:
    items = await db.scalars(
        select(CatalogItem)
        .where(CatalogItem.tenant_id == tenant.id)
        .order_by(CatalogItem.is_active.desc(), CatalogItem.name.asc())
    )
    return [CatalogItemRead.model_validate(item) for item in items]


@router.post("/items", response_model=CatalogItemRead, status_code=status.HTTP_201_CREATED)
async def create_catalog_item(
    payload: CatalogItemCreate,
    tenant: CurrentTenant,
    db: DbSession,
    _csrf: CsrfGuard,
) -> CatalogItemRead:
    values = payload.model_dump()
    values["currency"] = payload.currency.upper()
    item = CatalogItem(
        tenant_id=tenant.id,
        source="manual",
        **values,
    )
    db.add(item)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um item com este SKU") from exc
    await db.refresh(item)
    return CatalogItemRead.model_validate(item)


@router.patch("/items/{item_id}", response_model=CatalogItemRead)
async def update_catalog_item(
    item_id: uuid.UUID,
    payload: CatalogItemUpdate,
    tenant: CurrentTenant,
    db: DbSession,
    _csrf: CsrfGuard,
) -> CatalogItemRead:
    item = await db.scalar(
        select(CatalogItem).where(CatalogItem.id == item_id, CatalogItem.tenant_id == tenant.id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    values = payload.model_dump(exclude_unset=True)
    if values.get("currency"):
        values["currency"] = values["currency"].upper()
    for field, value in values.items():
        setattr(item, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um item com este SKU") from exc
    await db.refresh(item)
    return CatalogItemRead.model_validate(item)
