import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import and_, func, select

from app.dependencies import CsrfGuard, CurrentPlatformAdmin, DbSession
from app.models import (
    Membership,
    Subscription,
    SubscriptionStatus,
    SupportTicket,
    SupportTicketStatus,
    Tenant,
    TenantStatus,
    User,
    WhatsAppConnection,
    WhatsAppConnectionStatus,
)
from app.schemas import (
    AdminOverviewRead,
    AdminSummaryRead,
    AdminSupportTicketRead,
    AdminSupportTicketUpdate,
    AdminTenantRead,
)

router = APIRouter(prefix="/admin", tags=["admin"])


async def count_rows(db: DbSession, model, *conditions) -> int:
    statement = select(func.count()).select_from(model)
    if conditions:
        statement = statement.where(*conditions)
    return int(await db.scalar(statement) or 0)


@router.get("/overview", response_model=AdminOverviewRead)
async def read_admin_overview(
    db: DbSession,
    _admin: CurrentPlatformAdmin,
) -> AdminOverviewRead:
    summary = AdminSummaryRead(
        total_tenants=await count_rows(db, Tenant),
        operational_tenants=await count_rows(
            db,
            Tenant,
            Tenant.status.in_(
                [
                    TenantStatus.PROVISIONING,
                    TenantStatus.AWAITING_WHATSAPP,
                    TenantStatus.ACTIVE,
                    TenantStatus.GRACE_PERIOD,
                ]
            ),
        ),
        active_subscriptions=await count_rows(
            db, Subscription, Subscription.status == SubscriptionStatus.ACTIVE
        ),
        trialing_subscriptions=await count_rows(
            db, Subscription, Subscription.status == SubscriptionStatus.TRIALING
        ),
        connected_whatsapp=await count_rows(
            db,
            WhatsAppConnection,
            WhatsAppConnection.status == WhatsAppConnectionStatus.CONNECTED,
        ),
        open_support_tickets=await count_rows(
            db,
            SupportTicket,
            SupportTicket.status.in_(
                [SupportTicketStatus.OPEN, SupportTicketStatus.IN_PROGRESS]
            ),
        ),
    )

    tenant_statement = (
        select(
            Tenant,
            User.email.label("owner_email"),
            Subscription.status.label("subscription_status"),
            Subscription.trial_ends_at,
            WhatsAppConnection.status.label("whatsapp_status"),
        )
        .outerjoin(
            Membership,
            and_(Membership.tenant_id == Tenant.id, Membership.role == "owner"),
        )
        .outerjoin(User, User.id == Membership.user_id)
        .outerjoin(Subscription, Subscription.tenant_id == Tenant.id)
        .outerjoin(WhatsAppConnection, WhatsAppConnection.tenant_id == Tenant.id)
        .order_by(Tenant.created_at.desc())
        .limit(100)
    )
    tenant_rows = (await db.execute(tenant_statement)).all()
    tenants = [
        AdminTenantRead(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=tenant.status,
            owner_email=owner_email,
            subscription_status=subscription_status,
            trial_ends_at=trial_ends_at,
            whatsapp_status=whatsapp_status,
            created_at=tenant.created_at,
        )
        for tenant, owner_email, subscription_status, trial_ends_at, whatsapp_status in tenant_rows
    ]

    ticket_statement = (
        select(SupportTicket, Tenant.name)
        .join(Tenant, Tenant.id == SupportTicket.tenant_id)
        .order_by(SupportTicket.created_at.desc())
        .limit(50)
    )
    ticket_rows = (await db.execute(ticket_statement)).all()
    tickets = [
        AdminSupportTicketRead(
            id=ticket.id,
            tenant_name=tenant_name,
            category=ticket.category,
            priority=ticket.priority,
            status=ticket.status,
            subject=ticket.subject,
            preferred_channel=ticket.preferred_channel,
            contact_value=ticket.contact_value,
            created_at=ticket.created_at,
        )
        for ticket, tenant_name in ticket_rows
    ]
    return AdminOverviewRead(summary=summary, tenants=tenants, support_tickets=tickets)


@router.patch("/support/tickets/{ticket_id}", response_model=AdminSupportTicketRead)
async def update_support_ticket(
    ticket_id: uuid.UUID,
    payload: AdminSupportTicketUpdate,
    db: DbSession,
    _admin: CurrentPlatformAdmin,
    _csrf: CsrfGuard,
) -> AdminSupportTicketRead:
    row = (
        await db.execute(
            select(SupportTicket, Tenant.name)
            .join(Tenant, Tenant.id == SupportTicket.tenant_id)
            .where(SupportTicket.id == ticket_id)
        )
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    ticket, tenant_name = row
    ticket.status = payload.status
    await db.commit()
    await db.refresh(ticket)
    return AdminSupportTicketRead(
        id=ticket.id,
        tenant_name=tenant_name,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        subject=ticket.subject,
        preferred_channel=ticket.preferred_channel,
        contact_value=ticket.contact_value,
        created_at=ticket.created_at,
    )
