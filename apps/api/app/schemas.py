import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import OutboundMessageStatus, SubscriptionStatus, SupportTicketCategory, SupportTicketPriority, SupportTicketStatus, TenantStatus, WhatsAppConnectionStatus, WorkflowExecutionStatus


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    company_name: str = Field(min_length=2, max_length=160)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)


class ResetPasswordRequest(TokenRequest):
    password: str = Field(min_length=10, max_length=128)


class MessageRead(BaseModel):
    message: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str
    email_verified: bool = False
    is_platform_admin: bool = False


class AuthResponse(BaseModel):
    user: UserRead
    tenant_id: uuid.UUID


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    status: TenantStatus


class AssistantSettings(BaseModel):
    tone: str = Field(default="acolhedor", max_length=80)
    instructions: str = Field(default="", max_length=12000)
    human_handoff_message: str = Field(default="Vou chamar uma pessoa da equipe.", max_length=500)


class BusinessHoursDay(BaseModel):
    enabled: bool = True
    opens_at: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    closes_at: str = Field(default="18:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class TenantSettingsPayload(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    timezone: str = "America/Sao_Paulo"
    assistant: AssistantSettings = Field(default_factory=AssistantSettings)
    business_hours: dict[str, BusinessHoursDay] = Field(default_factory=dict)


class SettingsRead(BaseModel):
    version: int
    payload: TenantSettingsPayload
    created_at: datetime


class BillingSessionRead(BaseModel):
    url: str


class SubscriptionRead(BaseModel):
    status: SubscriptionStatus
    provider: str
    current_period_end: datetime | None = None
    trial_ends_at: datetime | None = None
    grace_ends_at: datetime | None = None
    trial_days_remaining: int = 0
    access_allowed: bool = False
    management_available: bool = False
    cancel_at_period_end: bool = False


class WhatsAppOnboardingSessionRead(BaseModel):
    app_id: str
    configuration_id: str
    state: str


class WhatsAppOnboardingComplete(BaseModel):
    state: str
    waba_id: str = Field(min_length=5, max_length=255)
    phone_number: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    phone_number_id: str | None = Field(default=None, max_length=255)

    @field_validator("phone_number", mode="before")
    @classmethod
    def normalize_brazilian_phone_number(cls, value: object) -> str:
        if not isinstance(value, str):
            return value  # type: ignore[return-value]
        digits = "".join(character for character in value if character.isdigit())
        if digits.startswith("55") and len(digits) in {12, 13}:
            digits = digits[2:]
        if len(digits) in {10, 11}:
            return f"+55{digits}"
        return value


class WhatsAppConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    waba_id: str
    phone_number: str
    phone_number_id: str | None = None
    display_name: str | None = None
    quality_rating: str | None = None
    status: WhatsAppConnectionStatus


class WorkflowResultRequest(BaseModel):
    status: WorkflowExecutionStatus
    n8n_execution_id: str | None = Field(default=None, max_length=255)
    error: str | None = Field(default=None, max_length=4000)


class SendTextMessageRequest(BaseModel):
    execution_id: uuid.UUID
    to: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    recipient_id: str | None = Field(default=None, max_length=255)
    text: str = Field(min_length=1, max_length=4096)
    reply_to_message_id: str | None = Field(default=None, max_length=255)
    idempotency_key: str = Field(min_length=8, max_length=255)


class OutboundMessageRead(BaseModel):
    id: uuid.UUID
    status: OutboundMessageStatus
    idempotency_key: str


class TypingIndicatorRequest(BaseModel):
    execution_id: uuid.UUID
    inbound_message_id: str = Field(min_length=5, max_length=255)


class CatalogItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=120)
    sku: str | None = Field(default=None, max_length=120)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    duration_minutes: int | None = Field(default=None, ge=1, le=525600)
    is_active: bool = True
    attributes: dict = Field(default_factory=dict)


class CatalogItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=120)
    sku: str | None = Field(default=None, max_length=120)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    duration_minutes: int | None = Field(default=None, ge=1, le=525600)
    is_active: bool | None = None
    attributes: dict | None = None


class CatalogItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    sku: str | None
    price: Decimal | None
    currency: str
    duration_minutes: int | None
    is_active: bool
    source: str
    attributes: dict
    created_at: datetime
    updated_at: datetime


class SupportTicketCreate(BaseModel):
    category: SupportTicketCategory = SupportTicketCategory.SUPPORT
    subject: str = Field(min_length=4, max_length=200)
    message: str = Field(min_length=10, max_length=8000)
    preferred_channel: str = Field(default="platform", pattern=r"^(platform|email|whatsapp|phone)$")
    contact_value: str | None = Field(default=None, max_length=320)


class SupportTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    category: SupportTicketCategory
    priority: SupportTicketPriority
    status: SupportTicketStatus
    subject: str
    message: str
    preferred_channel: str
    contact_value: str | None
    created_at: datetime
    updated_at: datetime


class AdminSummaryRead(BaseModel):
    total_tenants: int
    operational_tenants: int
    active_subscriptions: int
    trialing_subscriptions: int
    connected_whatsapp: int
    open_support_tickets: int


class AdminTenantRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: TenantStatus
    owner_email: EmailStr | None = None
    subscription_status: SubscriptionStatus | None = None
    trial_ends_at: datetime | None = None
    whatsapp_status: WhatsAppConnectionStatus | None = None
    created_at: datetime


class AdminSupportTicketRead(BaseModel):
    id: uuid.UUID
    tenant_name: str
    category: SupportTicketCategory
    priority: SupportTicketPriority
    status: SupportTicketStatus
    subject: str
    preferred_channel: str
    contact_value: str | None = None
    created_at: datetime


class AdminOverviewRead(BaseModel):
    summary: AdminSummaryRead
    tenants: list[AdminTenantRead]
    support_tickets: list[AdminSupportTicketRead]


class AdminSupportTicketUpdate(BaseModel):
    status: SupportTicketStatus
