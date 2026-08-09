"""API flow tests using FastAPI's sync TestClient.

Using the sync TestClient avoids the cross-event-loop headaches of running
the async engine from pytest-asyncio: the app, its lifespan, and all DB
connections run on TestClient's own internal loop. Schema reset happens via
a single asyncio.run() before/after each test, and the engine is disposed
within the same call so no connection outlives its loop.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine


async def _reset_schema():
    """Drop and recreate all tables; dispose the pool on the same loop."""
    import app.models  # noqa: F401 — register models with Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def _get_invitation_token(email: str) -> str:
    """Read a pending invitation's token from the DB (simulates email delivery)."""
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models import Invitation, InvitationStatus

    async with async_session_factory() as session:
        result = await session.execute(
            select(Invitation).where(
                Invitation.email == email,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        inv = result.scalar_one_or_none()
        if inv is None:
            raise AssertionError(f"No pending invitation for {email}")
        return inv.token
    await engine.dispose()


def _invite_token(email: str) -> str:
    """Sync wrapper for _get_invitation_token."""
    return asyncio.run(_get_invitation_token(email))


@pytest.fixture
def client():
    """A clean-schema app served via FastAPI's sync TestClient."""
    asyncio.run(_reset_schema())

    from app.main import app
    with TestClient(app) as c:
        yield c

    asyncio.run(_reset_schema())


def test_full_auth_org_flow(client):
    """Register → create org → login → token carries org_id → profile reflects it."""
    r = client.post("/api/v1/auth/register", json={
        "email": "boss@retailiq.com",
        "username": "boss",
        "password": "securepass123",
    })
    assert r.status_code == 201, r.text

    # Login (no org yet — token carries no org_id)
    r = client.post("/api/v1/auth/login", json={"username": "boss", "password": "securepass123"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["user"]["email"] == "boss@retailiq.com"

    # Create an organization
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    r = client.post("/api/v1/organizations", json={"name": "My Store Co"}, headers=headers)
    assert r.status_code == 201, r.text
    org = r.json()
    assert org["name"] == "My Store Co"
    assert org["slug"] == "my-store-co"

    # Login again — token now carries the org, response includes it
    r = client.post("/api/v1/auth/login", json={"username": "boss", "password": "securepass123"})
    body = r.json()
    assert body["organization"] is not None
    assert body["organization"]["id"] == org["id"]

    # Org profile via /organizations/me
    r = client.get("/api/v1/organizations/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r.status_code == 200, r.text
    assert r.json()["id"] == org["id"]


def test_invite_accept_flow(client):
    """Owner invites → invitee accepts → both are members."""
    # Owner registers + org
    r = client.post("/api/v1/auth/register", json={
        "email": "owner@retailiq.com", "username": "owner", "password": "securepass123",
    })
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login", json={"username": "owner", "password": "securepass123"})
    owner_tok = r.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_tok}"}
    r = client.post("/api/v1/organizations", json={"name": "Owner Co"}, headers=owner_headers)
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]

    # Owner invites a new user
    r = client.post("/api/v1/organizations/invitations", json={
        "email": "newbie@retailiq.com", "role": "analyst",
    }, headers=owner_headers)
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["status"] == "pending"
    token = _invite_token("newbie@retailiq.com")

    # Invitee (doesn't exist yet) accepts with a password
    r = client.post("/api/v1/organizations/invitations/accept", json={
        "email": "newbie@retailiq.com",
        "token": token,
        "password": "theirpassword123",
    })
    assert r.status_code == 200, r.text
    assert r.json()["organization_id"] == org_id
    assert r.json()["role"] == "analyst"

    # Invitee can log in and sees the org
    r = client.post("/api/v1/auth/login", json={"username": "newbie", "password": "theirpassword123"})
    assert r.status_code == 200, r.text
    assert r.json()["organization"]["id"] == org_id

    # Members list shows both
    r = client.get("/api/v1/organizations/members", headers=owner_headers)
    assert r.status_code == 200, r.text
    members = r.json()
    assert len(members) == 2
    assert {m["role"] for m in members} == {"owner", "analyst"}


def test_role_gate_enforced(client):
    """A viewer cannot invite; only owner/admin can."""
    # Owner + org
    r = client.post("/api/v1/auth/register", json={
        "email": "o@retailiq.com", "username": "own", "password": "securepass123",
    })
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login", json={"username": "own", "password": "securepass123"})
    owner_tok = r.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_tok}"}
    r = client.post("/api/v1/organizations", json={"name": "Gate Co"}, headers=owner_headers)
    assert r.status_code == 201, r.text

    # Invite a viewer
    r = client.post("/api/v1/organizations/invitations", json={
        "email": "viewer@retailiq.com", "role": "viewer",
    }, headers=owner_headers)
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/organizations/invitations/accept", json={
        "email": "viewer@retailiq.com",
        "token": _invite_token("viewer@retailiq.com"),
        "password": "viewerpass123",
    })
    assert r.status_code == 200, r.text

    # Viewer logs in and tries to invite — must be 403
    r = client.post("/api/v1/auth/login", json={"username": "viewer", "password": "viewerpass123"})
    assert r.status_code == 200, r.text
    viewer_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.post("/api/v1/organizations/invitations", json={
        "email": "someone@retailiq.com", "role": "viewer",
    }, headers=viewer_headers)
    assert r.status_code == 403, r.text
