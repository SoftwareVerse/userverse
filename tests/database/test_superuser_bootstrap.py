from uuid import uuid4

import pytest

from app.models.user.account_status import UserAccountStatus
from app.repository.database.tables import (
    PrivilegedAccessEvent,
    SuperuserBootstrapControl,
    User,
)
from app.services.superuser_bootstrap import (
    SuperuserBootstrapError,
    SuperuserBootstrapService,
)


def _add_control(test_session, **overrides) -> SuperuserBootstrapControl:
    control = SuperuserBootstrapControl(
        id=SuperuserBootstrapControl.SINGLETON_ID,
        primary_meta_data={},
        secondary_meta_data={},
        **overrides,
    )
    test_session.add(control)
    test_session.commit()
    return control


def _add_user(
    test_session,
    *,
    label: str,
    status: str = UserAccountStatus.ACTIVE.name_value,
    is_superuser: bool = False,
    refresh_token_version=0,
) -> User:
    user = User(
        email=f"{label}-{uuid4().hex}@example.com",
        password="unchanged-password-hash",
        first_name=label,
        is_superuser=is_superuser,
        primary_meta_data={
            "status": status,
            "refresh_token_version": refresh_token_version,
        },
        secondary_meta_data={},
    )
    test_session.add(user)
    test_session.commit()
    return user


def test_bootstrap_promotes_existing_active_user_and_is_idempotent(test_session):
    control = _add_control(test_session)
    user = _add_user(test_session, label="initial-admin", refresh_token_version=4)
    service = SuperuserBootstrapService(test_session)

    candidate = service.get_candidate(f"  {user.email.upper()}  ")
    result = service.bootstrap(
        email=user.email,
        reason="  Initial production bootstrap  ",
        expected_user_id=candidate.user_id,
    )

    test_session.refresh(user)
    test_session.refresh(control)
    assert result.user_id == user.id
    assert result.changed is True
    assert user.is_superuser is True
    assert user.password == "unchanged-password-hash"
    assert user.primary_meta_data["refresh_token_version"] == 5
    assert control.bootstrap_user_id == user.id
    assert control.bootstrap_completed_at is not None
    assert control.bootstrap_method == service.SOURCE

    event = test_session.query(PrivilegedAccessEvent).one()
    assert event.actor_user_id is None
    assert event.target_user_id == user.id
    assert event.action == service.ACTION
    assert event.source == service.SOURCE
    assert event.reason == "Initial production bootstrap"
    assert event.previous_superuser is False
    assert event.resulting_superuser is True
    assert event.request_id is None

    repeated = service.bootstrap(
        email=user.email,
        reason="Safe retry",
        expected_user_id=user.id,
    )
    test_session.refresh(user)
    assert repeated.changed is False
    assert user.primary_meta_data["refresh_token_version"] == 5
    assert test_session.query(PrivilegedAccessEvent).count() == 1


@pytest.mark.parametrize(
    ("email", "expected_message"),
    [
        ("   ", "email is required"),
        ("missing@example.com", "No active user exists"),
    ],
)
def test_candidate_rejects_blank_or_missing_users(
    test_session,
    email,
    expected_message,
):
    with pytest.raises(SuperuserBootstrapError, match=expected_message):
        SuperuserBootstrapService(test_session).get_candidate(email)


def test_candidate_rejects_deleted_and_inactive_users(test_session):
    deleted = _add_user(test_session, label="deleted")
    deleted._closed_at = deleted._created_at
    test_session.commit()
    inactive = _add_user(
        test_session,
        label="inactive",
        status=UserAccountStatus.AWAITING_VERIFICATION.name_value,
    )
    service = SuperuserBootstrapService(test_session)

    with pytest.raises(SuperuserBootstrapError, match="No active user exists"):
        service.get_candidate(deleted.email)
    with pytest.raises(SuperuserBootstrapError, match="active and verified"):
        service.get_candidate(inactive.email)


@pytest.mark.parametrize("reason", ["", "   ", "x" * 1025])
def test_bootstrap_rejects_invalid_reasons(test_session, reason):
    with pytest.raises(SuperuserBootstrapError):
        SuperuserBootstrapService(test_session).bootstrap(
            email="unused@example.com",
            reason=reason,
            expected_user_id=uuid4(),
        )


def test_bootstrap_requires_migrated_singleton_control(test_session):
    user = _add_user(test_session, label="no-control")

    with pytest.raises(SuperuserBootstrapError, match="Apply Alembic migrations"):
        SuperuserBootstrapService(test_session).bootstrap(
            email=user.email,
            reason="Initial bootstrap",
            expected_user_id=user.id,
        )
    test_session.refresh(user)
    assert user.is_superuser is False


def test_bootstrap_rechecks_confirmed_identity_under_lock(test_session):
    _add_control(test_session)
    user = _add_user(test_session, label="mismatch")

    with pytest.raises(SuperuserBootstrapError, match="confirmed user ID"):
        SuperuserBootstrapService(test_session).bootstrap(
            email=user.email,
            reason="Initial bootstrap",
            expected_user_id=uuid4(),
        )


def test_bootstrap_rejects_existing_superuser(test_session):
    _add_control(test_session)
    target = _add_user(test_session, label="target")
    _add_user(test_session, label="existing-root", is_superuser=True)

    with pytest.raises(SuperuserBootstrapError, match="already exists"):
        SuperuserBootstrapService(test_session).bootstrap(
            email=target.email,
            reason="Initial bootstrap",
            expected_user_id=target.id,
        )
    test_session.refresh(target)
    assert target.is_superuser is False


def test_completed_bootstrap_rejects_different_or_demoted_target(test_session):
    original = _add_user(test_session, label="original", is_superuser=True)
    other = _add_user(test_session, label="other")
    control = _add_control(
        test_session,
        bootstrap_user_id=original.id,
        bootstrap_completed_at=original._created_at,
        bootstrap_method=SuperuserBootstrapService.SOURCE,
    )
    service = SuperuserBootstrapService(test_session)

    with pytest.raises(SuperuserBootstrapError, match="already been completed"):
        service.bootstrap(
            email=other.email,
            reason="Different target",
            expected_user_id=other.id,
        )

    original.is_superuser = False
    test_session.commit()
    with pytest.raises(SuperuserBootstrapError, match="already been completed"):
        service.bootstrap(
            email=original.email,
            reason="Do not restore silently",
            expected_user_id=original.id,
        )
    test_session.refresh(control)
    assert control.bootstrap_user_id == original.id


def test_bootstrap_normalizes_invalid_refresh_token_version(test_session):
    _add_control(test_session)
    user = _add_user(
        test_session,
        label="invalid-version",
        refresh_token_version="invalid",
    )

    SuperuserBootstrapService(test_session).bootstrap(
        email=user.email,
        reason="Initial bootstrap",
        expected_user_id=user.id,
    )

    test_session.refresh(user)
    assert user.primary_meta_data["refresh_token_version"] == 1


def test_bootstrap_rolls_back_privilege_change_when_commit_fails(
    test_session,
    monkeypatch,
):
    _add_control(test_session)
    user = _add_user(test_session, label="rollback")
    monkeypatch.setattr(
        test_session,
        "commit",
        lambda: (_ for _ in ()).throw(RuntimeError("audit transaction failed")),
    )

    with pytest.raises(RuntimeError, match="audit transaction failed"):
        SuperuserBootstrapService(test_session).bootstrap(
            email=user.email,
            reason="Initial bootstrap",
            expected_user_id=user.id,
        )

    test_session.expire_all()
    persisted = test_session.query(User).filter_by(id=user.id).one()
    control = test_session.query(SuperuserBootstrapControl).one()
    assert persisted.is_superuser is False
    assert persisted.primary_meta_data["refresh_token_version"] == 0
    assert control.bootstrap_completed_at is None
    assert test_session.query(PrivilegedAccessEvent).count() == 0
