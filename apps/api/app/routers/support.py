from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies import CsrfGuard, CurrentTenant, CurrentUser, DbSession
from app.models import OutboxEvent, SupportTicket, SupportTicketCategory, SupportTicketPriority
from app.schemas import SupportTicketCreate, SupportTicketRead

router = APIRouter(prefix="/support", tags=["support"])


@router.get("/tickets", response_model=list[SupportTicketRead])
async def list_support_tickets(tenant: CurrentTenant, db: DbSession) -> list[SupportTicketRead]:
    tickets = await db.scalars(
        select(SupportTicket)
        .where(SupportTicket.tenant_id == tenant.id)
        .order_by(SupportTicket.created_at.desc())
        .limit(50)
    )
    return [SupportTicketRead.model_validate(ticket) for ticket in tickets]


@router.post("/tickets", response_model=SupportTicketRead, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    payload: SupportTicketCreate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
    _csrf: CsrfGuard,
) -> SupportTicketRead:
    if payload.preferred_channel != "platform" and not payload.contact_value:
        raise HTTPException(status_code=422, detail="Informe o contato para o canal selecionado")
    priority = SupportTicketPriority.HIGH if payload.category == SupportTicketCategory.CUSTOM_PLAN else SupportTicketPriority.NORMAL
    ticket = SupportTicket(
        tenant_id=tenant.id,
        created_by=user.id,
        priority=priority,
        **payload.model_dump(),
    )
    db.add(ticket)
    await db.flush()
    db.add(
        OutboxEvent(
            tenant_id=tenant.id,
            event_type="support.ticket.created",
            payload={
                "ticket_id": str(ticket.id),
                "category": ticket.category.value,
                "priority": ticket.priority.value,
                "subject": ticket.subject,
            },
        )
    )
    await db.commit()
    await db.refresh(ticket)
    return SupportTicketRead.model_validate(ticket)
