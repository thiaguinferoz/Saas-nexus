import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import OutboundMessageStatus, SubscriptionStatus, TenantStatus, WhatsAppConnectionStatus, WorkflowExecutionStatus


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    company_name: str = Field(min_length=2, max_length=160)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str


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
