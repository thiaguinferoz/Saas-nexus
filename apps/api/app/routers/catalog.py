import csv
import io
import re
import unicodedata
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CsrfGuard, CurrentTenant, DbSession
from app.models import CatalogItem
from app.schemas import CatalogImportRead, CatalogItemCreate, CatalogItemRead, CatalogItemUpdate

router = APIRouter(prefix="/catalog", tags=["catalog"])

MAX_CATALOG_FILE_BYTES = 20 * 1024 * 1024
MAX_CATALOG_ROWS = 1_000


def normalize_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def first_value(row: dict[str, object], *aliases: str) -> str | None:
    for alias in aliases:
        value = row.get(alias)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def parse_price(value: str | None) -> Decimal | None:
    if not value:
        return None
    number = re.sub(r"[^0-9,.-]", "", value)
    if not number:
        return None
    if "," in number and "." in number:
        number = number.replace(".", "").replace(",", ".")
    elif "," in number:
        number = number.replace(",", ".")
    try:
        return Decimal(number).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def spreadsheet_rows(filename: str, content: bytes) -> list[dict[str, object]]:
    suffix = filename.rsplit(".", 1)[-1].lower()
    if suffix == "csv":
        text = content.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))
    if suffix == "xlsx":
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        headers = next(rows, None)
        if not headers:
            return []
        normalized_headers = [normalize_header(header) for header in headers]
        return [
            {normalized_headers[index]: value for index, value in enumerate(values) if index < len(normalized_headers)}
            for values in rows
        ]
    raise HTTPException(status_code=415, detail="Envie uma planilha CSV ou XLSX")


@router.post("/import", response_model=CatalogImportRead)
async def import_catalog(
    tenant: CurrentTenant,
    db: DbSession,
    _csrf: CsrfGuard,
    file: UploadFile = File(...),
) -> CatalogImportRead:
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=415, detail="Envie uma planilha CSV ou XLSX")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="A planilha está vazia")
    if len(content) > MAX_CATALOG_FILE_BYTES:
        raise HTTPException(status_code=413, detail="A planilha deve ter no máximo 20 MB")
    try:
        raw_rows = spreadsheet_rows(filename, content)
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Não foi possível ler o CSV. Salve-o como UTF-8 e tente novamente") from None
    if len(raw_rows) > MAX_CATALOG_ROWS:
        raise HTTPException(status_code=422, detail=f"A planilha pode ter no máximo {MAX_CATALOG_ROWS} itens")

    imported = updated = skipped = 0
    errors: list[str] = []
    results: list[CatalogItem] = []
    for row_number, raw_row in enumerate(raw_rows, start=2):
        row = {normalize_header(key): value for key, value in raw_row.items()}
        name = first_value(row, "nome", "produto", "servico", "item", "descricao")
        if not name:
            skipped += 1
            errors.append(f"Linha {row_number}: informe o nome do produto ou serviço")
            continue
        price_text = first_value(row, "preco", "valor", "price", "valorunitario")
        price = parse_price(price_text)
        if price_text and price is None:
            skipped += 1
            errors.append(f"Linha {row_number}: preço inválido")
            continue
        sku = first_value(row, "sku", "codigo", "cod", "idproduto")
        item = None
        if sku:
            item = await db.scalar(select(CatalogItem).where(CatalogItem.tenant_id == tenant.id, CatalogItem.sku == sku))
        values = {
            "name": name[:200],
            "description": first_value(row, "descricao", "detalhes"),
            "category": first_value(row, "categoria", "tipo", "category"),
            "sku": sku,
            "price": price,
            "currency": (first_value(row, "moeda", "currency") or "BRL").upper()[:3],
        }
        if item:
            for key, value in values.items():
                setattr(item, key, value)
            updated += 1
        else:
            item = CatalogItem(tenant_id=tenant.id, source="import", **values)
            db.add(item)
            imported += 1
        results.append(item)
    if not results:
        raise HTTPException(status_code=422, detail={"message": "Nenhum item válido foi encontrado", "errors": errors[:20]})
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Há itens duplicados na planilha") from exc
    for item in results:
        await db.refresh(item)
    return CatalogImportRead(imported=imported, updated=updated, skipped=skipped, errors=errors[:20], items=[CatalogItemRead.model_validate(item) for item in results])


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
