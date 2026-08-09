"""Tests for the tenancy layer — org creation, memberships, isolation, invites."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import select

from app.models import (
    User, Organization, OrganizationMember, OrganizationRole,
    Invitation, InvitationStatus,
)
from app.services.data_service import TenantDataService
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio


async def _make_org(db_session, name: str, slug: str, owner_id: str) -> Organization:
    org = Organization(name=name, slug=slug, owner_id=owner_id)
    db_session.add(org)
    await db_session.flush()
    return org


async def test_create_org_sets_owner(db_session):
    """The creator of an org becomes its owner with the OWNER role."""
    owner = User(email="owner@test.com", username="owner",
                 hashed_password=hash_password("password123"))
    db_session.add(owner)
    await db_session.flush()

    org = await _make_org(db_session, "Test Org", "test-org", owner.id)
    db_session.add(OrganizationMember(
        organization_id=org.id, user_id=owner.id, role=OrganizationRole.OWNER,
    ))
    await db_session.commit()

    members = (await db_session.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == org.id)
    )).scalars().all()
    assert len(members) == 1
    assert members[0].role == OrganizationRole.OWNER
    assert members[0].user_id == org.owner_id


async def test_invite_and_membership(db_session):
    """Invite a new user; accepting creates a member with the invited role."""
    owner = User(email="a@test.com", username="a", hashed_password=hash_password("pw"))
    db_session.add(owner)
    await db_session.flush()

    org = await _make_org(db_session, "O", "o", owner.id)
    db_session.add(OrganizationMember(organization_id=org.id, user_id=owner.id, role=OrganizationRole.OWNER))

    inv = Invitation(
        organization_id=org.id,
        email="newuser@test.com",
        role="analyst",
        token="tok123",
        invited_by=owner.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(inv)
    await db_session.commit()

    # Simulate acceptance: register the invitee and add the membership
    invitee = User(email="newuser@test.com", username="newuser",
                   hashed_password=hash_password("pw"))
    db_session.add(invitee)
    await db_session.flush()

    db_session.add(OrganizationMember(
        organization_id=org.id, user_id=invitee.id, role=OrganizationRole.ANALYST,
    ))
    inv.status = InvitationStatus.ACCEPTED
    await db_session.commit()

    members = (await db_session.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == org.id)
    )).scalars().all()
    assert len(members) == 2
    roles = {m.role for m in members}
    assert OrganizationRole.OWNER in roles
    assert OrganizationRole.ANALYST in roles


async def test_data_ingest_isolation(db_session):
    """Ingesting into org A must not leak into org B."""
    org_a = await _make_org(db_session, "A", "a", "u1")
    org_b = await _make_org(db_session, "B", "b", "u2")
    await db_session.commit()

    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "item_id": ["SKU1", "SKU1", "SKU2"],
        "store_id": ["S1", "S1", "S1"],
        "sales": [10, 20, 30],
        "sell_price": [5.0, 5.0, 8.0],
    })
    await TenantDataService.ingest_dataframe(db_session, org_a.id, df)

    # Org A has the data
    summary_a = await TenantDataService.org_data_summary(db_session, org_a.id)
    assert summary_a["sales_rows"] == 3
    assert summary_a["products"] == 2
    assert summary_a["stores"] == 1

    # Org B is untouched — full isolation
    summary_b = await TenantDataService.org_data_summary(db_session, org_b.id)
    assert summary_b["sales_rows"] == 0
    assert summary_b["products"] == 0
    assert summary_b["stores"] == 0


async def test_ingest_is_idempotent(db_session):
    """Re-ingesting the same data does not create duplicate rows."""
    org = await _make_org(db_session, "A", "a", "u1")
    await db_session.commit()

    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "item_id": ["SKU1", "SKU1"],
        "store_id": ["S1", "S1"],
        "sales": [10, 20],
    })
    await TenantDataService.ingest_dataframe(db_session, org.id, df)
    await TenantDataService.ingest_dataframe(db_session, org.id, df)

    summary = await TenantDataService.org_data_summary(db_session, org.id)
    assert summary["sales_rows"] == 2
    assert summary["products"] == 1


async def test_multi_user_multi_org(db_session):
    """A user can be a member of multiple orgs with different roles."""
    user = User(email="multi@test.com", username="multi", hashed_password=hash_password("pw"))
    db_session.add(user)
    await db_session.flush()

    org_a = await _make_org(db_session, "A", "a", "owner1")
    org_b = await _make_org(db_session, "B", "b", "owner1")
    await db_session.commit()

    db_session.add_all([
        OrganizationMember(organization_id=org_a.id, user_id=user.id, role=OrganizationRole.ADMIN),
        OrganizationMember(organization_id=org_b.id, user_id=user.id, role=OrganizationRole.VIEWER),
    ])
    await db_session.commit()

    memberships = (await db_session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    )).scalars().all()
    assert len(memberships) == 2
    roles_by_org = {m.organization_id: m.role for m in memberships}
    assert roles_by_org[org_a.id] == OrganizationRole.ADMIN
    assert roles_by_org[org_b.id] == OrganizationRole.VIEWER
