from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, StrictInt

ChannelType = Literal["email", "sms", "internal_alert"]
DecisionStatus = Literal["sent", "suppressed"]
NotificationStatus = Literal["applied", "suppressed"]


class UserTraits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    country: str = Field(min_length=2, max_length=2)
    marketing_opt_in: StrictBool
    risk_segment: str


class SignupCompletedProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LinkBankSuccessProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentInitiatedProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float | None = None
    attempt_number: StrictInt | None = None


class PaymentFailedProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float
    attempt_number: StrictInt
    failure_reason: str

# Event models
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

# Union of all event models
EventPayload = Annotated[
    SignupCompletedEvent | LinkBankSuccessEvent | PaymentInitiatedEvent | PaymentFailedEvent,
    Field(discriminator="event_type"),
]

# Response models
class EventIngestResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "accepted",
                "message": "Event accepted. notifications=1 applied=1 suppressed=0",
                "notifications": [
                    {
                        "template_name": "INSUFFICIENT_FUNDS_EMAIL",
                        "channel": "email",
                        "status": "applied",
                        "reason": "payment_failed due to insufficient funds",
                        "suppression_reason": None,
                    }
                ],
            }
        }
    )

    status: str
    message: str
    notifications: list["NotificationOutcome"]


class NotificationOutcome(BaseModel):
    template_name: str
    channel: ChannelType
    status: NotificationStatus
    reason: str
    suppression_reason: str | None = None


class MessageDecision(BaseModel):
    template_name: str
    channel: ChannelType
    timestamp: datetime
    reason: str
    status: DecisionStatus
    suppression_reason: str | None = None


class UserAuditResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "u_12346",
                "recent_events": [
                    {
                        "user_id": "u_12346",
                        "event_type": "payment_failed",
                        "event_timestamp": "2025-10-31T19:22:11Z",
                        "properties": "{\"amount\": 1425.0, \"attempt_number\": 2, \"failure_reason\": \"INSUFFICIENT_FUNDS\"}",
                        "user_traits": "{\"email\": \"maria@example.com\", \"country\": \"PT\", \"risk_segment\": \"MEDIUM\", \"marketing_opt_in\": true}",
                        "created_at": "2026-03-07T16:07:00.279071Z",
                    }
                ],
                "decisions": [
                    {
                        "user_id": "u_12346",
                        "template_name": "INSUFFICIENT_FUNDS_EMAIL",
                        "channel": "email",
                        "decision_status": "sent",
                        "reason": "payment_failed due to insufficient funds",
                        "suppression_reason": None,
                        "decided_at": "2025-10-31T19:22:11Z",
                        "created_at": "2026-03-07T16:07:00.287929Z",
                    }
                ],
            }
        }
    )

    user_id: str
    recent_events: list[dict[str, Any]]
    decisions: list[dict[str, Any]]


class HealthResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})

    status: Literal["ok"]
