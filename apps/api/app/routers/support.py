from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import CsrfGuard, CurrentTenant, CurrentUser, DbSession
from app.models import OutboxEvent, SupportTicket, SupportTicketCategory, SupportTicketPriority
from app.schemas import SupportTicketCreate, SupportTicketRead

router = APIRouter(prefix="/support", tags=["support"])


@router.get("/tickets", response_model=list[SupportTicketRead])
async def list_support_tickets(tenant: CurrentTenant, db: DbSession) -> list[SupportTicketRead]:
    tickets = await db.scalars(
        select(SupportTicket)
        .options(selectinload(SupportTicket.replies))
        .where(SupportTicket.tenant_id == tenant.id)
        .order_by(SupportTicket.created_at.desc())
        .limit(50)
    )
    results: list[SupportTicketRead] = []
    for ticket in tickets:
        item = SupportTicketRead.model_validate(ticket)
        if ticket.replies:
            conversation = "\n\n".join(
                f"Equipe Nexus: {reply.message}" for reply in ticket.replies
            )
            item.message = f"{ticket.message}\n\n— Respostas do suporte —\n{conversation}"
        results.append(item)
    return results


@router.post("/tickets", response_model=SupportTicketRead, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    payload: SupportTicketCreate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
    _csrf: CsrfGuard,
) -> SupportTicketRead:
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
    return SupportTicketRead(
        id=ticket.id,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        subject=ticket.subject,
        message=ticket.message,
        preferred_channel=ticket.preferred_channel,
        contact_value=None,
        replies=[],
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )

