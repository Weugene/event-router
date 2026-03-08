from datetime import UTC, datetime

from fastapi.testclient import TestClient


def test_post_events_valid_payload_returns_accepted(client: TestClient):

    response = client.post(
        "/events",
        json={
            "user_id": "u_3",
            "event_type": "payment_failed",
            "event_timestamp": "2026-03-08T12:00:00Z",
            "properties": {
                "amount": 99.5,
                "attempt_number": 2,
                "failure_reason": "INSUFFICIENT_FUNDS",
            },
            "user_traits": {
                "email": "u3@example.com",
                "country": "PT",
                "marketing_opt_in": True,
                "risk_segment": "LOW",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert len(data["notifications"]) == 1
    assert data["notifications"][0]["template_name"] == "INSUFFICIENT_FUNDS_EMAIL"
    assert data["notifications"][0]["status"] in {"applied", "suppressed"}


def test_post_events_invalid_payload_is_rejected(client: TestClient):

    response = client.post(
        "/events",
        json={
            "user_id": "u_4",
            "event_type": "payment_failed",
            "event_timestamp": "2026-03-08T12:00:00Z",
            "properties": {
                "amount": 10,
                "attempt_number": 1,
                "failure_reason": "INSUFFICIENT_FUNDS",
            },
            "user_traits": {
                "country": "PT",
                "marketing_opt_in": True,
                "risk_segment": "LOW",
            },
        },
    )

    assert response.status_code == 422


def test_get_audit_returns_events_and_decisions(client: TestClient):
    user_id = "u_5"

    payload = {
        "user_id": user_id,
        "event_type": "payment_failed",
        "event_timestamp": datetime(2026, 3, 8, 12, 0, tzinfo=UTC).isoformat(),
        "properties": {
            "amount": 15,
            "attempt_number": 2,
            "failure_reason": "INSUFFICIENT_FUNDS",
        },
        "user_traits": {
            "email": "u5@example.com",
            "country": "PT",
            "marketing_opt_in": True,
            "risk_segment": "LOW",
        },
    }
    ingest_response = client.post("/events", json=payload)
    assert ingest_response.status_code == 200

    audit_response = client.get(f"/audit/{user_id}")
    assert audit_response.status_code == 200
    data = audit_response.json()
    assert data["user_id"] == user_id
    assert len(data["recent_events"]) >= 1
    assert len(data["decisions"]) >= 1
