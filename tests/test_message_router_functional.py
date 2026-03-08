from datetime import UTC, datetime, timedelta

import pytest

from src.schemas import LinkBankSuccessEvent, PaymentFailedEvent, SignupCompletedEvent


@pytest.mark.anyio
async def test_payment_failed_once_per_day_suppression(message_router_service, app_logger):
    first = PaymentFailedEvent(
        user_id="u_1",
        event_type="payment_failed",
        event_timestamp=datetime(2026, 3, 8, 10, 0, tzinfo=UTC),
        properties={
            "amount": 42.0,
            "attempt_number": 1,
            "failure_reason": "INSUFFICIENT_FUNDS",
        },
        user_traits={
            "email": "u1@example.com",
            "country": "PT",
            "marketing_opt_in": True,
            "risk_segment": "LOW",
        },
    )
    second = first.model_copy(
        update={"event_timestamp": datetime(2026, 3, 8, 16, 0, tzinfo=UTC)}
    )

    first_result = await message_router_service.process_event(first, app_logger)
    second_result = await message_router_service.process_event(second, app_logger)

    assert first_result["decision_count"] == 1
    assert first_result["decisions"][0]["status"] == "sent"
    assert first_result["decisions"][0]["template_name"] == "INSUFFICIENT_FUNDS_EMAIL"

    assert second_result["decision_count"] == 1
    assert second_result["decisions"][0]["status"] == "suppressed"
    assert "already sent today" in second_result["decisions"][0]["suppression_reason"]


@pytest.mark.anyio
async def test_link_bank_within_24h_matches_rule_and_once_ever_suppresses_repeat(
    message_router_service, app_logger
):
    signup = SignupCompletedEvent(
        user_id="u_2",
        event_type="signup_completed",
        event_timestamp=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
        properties={},
        user_traits={
            "email": "u2@example.com",
            "country": "PT",
            "marketing_opt_in": True,
            "risk_segment": "MEDIUM",
        },
    )
    link_bank_first = LinkBankSuccessEvent(
        user_id="u_2",
        event_type="link_bank_success",
        event_timestamp=signup.event_timestamp + timedelta(hours=1),
        properties={},
        user_traits=signup.user_traits,
    )
    link_bank_second = link_bank_first.model_copy(
        update={"event_timestamp": link_bank_first.event_timestamp + timedelta(hours=2)}
    )

    signup_result = await message_router_service.process_event(signup, app_logger)
    first_link_result = await message_router_service.process_event(link_bank_first, app_logger)
    second_link_result = await message_router_service.process_event(link_bank_second, app_logger)

    assert signup_result["decision_count"] == 1
    assert signup_result["decisions"][0]["template_name"] == "WELCOME_EMAIL"
    assert signup_result["decisions"][0]["channel"] == "email"
    assert signup_result["decisions"][0]["status"] == "sent"

    assert first_link_result["decision_count"] == 1
    assert first_link_result["decisions"][0]["template_name"] == "BANK_LINK_NUDGE_SMS"
    assert first_link_result["decisions"][0]["channel"] == "sms"
    assert first_link_result["decisions"][0]["status"] == "sent"

    assert second_link_result["decision_count"] == 1
    assert second_link_result["decisions"][0]["status"] == "suppressed"
    assert "already sent before" in (second_link_result["decisions"][0]["suppression_reason"] or "")


@pytest.mark.anyio
async def test_signup_completed_marketing_opt_out_does_not_notify_and_is_audited(
    message_router_service, app_logger
):
    signup = SignupCompletedEvent(
        user_id="u_6",
        event_type="signup_completed",
        event_timestamp=datetime(2026, 3, 8, 9, 0, tzinfo=UTC),
        properties={},
        user_traits={
            "email": "u6@example.com",
            "country": "PT",
            "marketing_opt_in": False,
            "risk_segment": "LOW",
        },
    )

    result = await message_router_service.process_event(signup, app_logger)
    audit = await message_router_service.get_user_audit(signup.user_id, app_logger)

    assert result["decision_count"] == 1
    assert result["decisions"][0]["template_name"] == "WELCOME_EMAIL"
    assert result["decisions"][0]["status"] == "suppressed"
    assert result["decisions"][0]["suppression_reason"] == "suppressed by rule configuration"

    assert len(audit["recent_events"]) == 1
    assert len(audit["decisions"]) == 1
    assert audit["decisions"][0]["template_name"] == "WELCOME_EMAIL"
    assert audit["decisions"][0]["decision_status"] == "suppressed"
    assert audit["decisions"][0]["reason"] == "signup_completed + marketing_opt_in=false"
