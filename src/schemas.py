from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

ChannelType = Literal["email", "sms", "internal_alert"]
DecisionStatus = Literal["sent", "suppressed"]


class UserTraits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    country: str = Field(min_length=2, max_length=2)
    marketing_opt_in: bool
    risk_segment: str


class SignupCompletedProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LinkBankSuccessProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentInitiatedProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float | None = None
    attempt_number: int | None = None


class PaymentFailedProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float
    attempt_number: int
    failure_reason: str


class SignupCompletedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    event_type: Literal["signup_completed"]
    event_timestamp: datetime
    properties: SignupCompletedProperties = Field(default_factory=SignupCompletedProperties)
    user_traits: UserTraits


class LinkBankSuccessEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    event_type: Literal["link_bank_success"]
    event_timestamp: datetime
    properties: LinkBankSuccessProperties = Field(default_factory=LinkBankSuccessProperties)
    user_traits: UserTraits


class PaymentInitiatedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    event_type: Literal["payment_initiated"]
    event_timestamp: datetime
    properties: PaymentInitiatedProperties = Field(default_factory=PaymentInitiatedProperties)
    user_traits: UserTraits


class PaymentFailedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    event_type: Literal["payment_failed"]
    event_timestamp: datetime
    properties: PaymentFailedProperties
    user_traits: UserTraits


EventPayload = Annotated[
    SignupCompletedEvent | LinkBankSuccessEvent | PaymentInitiatedEvent | PaymentFailedEvent,
    Field(discriminator="event_type"),
]


class EventIngestResponse(BaseModel):
    status: str
    message: str


class MessageDecision(BaseModel):
    template_name: str
    channel: ChannelType
    timestamp: datetime
    reason: str
    status: DecisionStatus
    suppression_reason: str | None = None


class UserAuditResponse(BaseModel):
    user_id: str
    recent_events: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
