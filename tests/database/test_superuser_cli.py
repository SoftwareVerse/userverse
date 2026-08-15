from types import SimpleNamespace
from uuid import uuid4

from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.cli import admin
from app.models.user.account_status import UserAccountStatus
from app.repository.database import Base
from app.repository.database.tables import (
    PrivilegedAccessEvent,
    SuperuserBootstrapControl,
    User,
)
from app.services.superuser_bootstrap import SuperuserBootstrapError


def _configure_cli_database(monkeypatch, tmp_path):
    database_url = f"sqlite:///{tmp_path / 'superuser-cli.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    user = User(
        email=f"cli-admin-{uuid4().hex}@example.com",
        password="never-printed-password",
        first_name="CLI",
        is_superuser=False,
        primary_meta_data={
            "status": UserAccountStatus.ACTIVE.name_value,
            "refresh_token_version": 0,
        },
        secondary_meta_data={},
    )
    session.add_all(
        [
            SuperuserBootstrapControl(
                id=SuperuserBootstrapControl.SINGLETON_ID,
                primary_meta_data={},
                secondary_meta_data={},
            ),
            user,
        ]
    )
    session.commit()
    user_id = user.id
    email = user.email
    session.close()
    engine.dispose()

    class TestDatabaseManager:
        def __init__(self):
            self.engine = create_engine(database_url)
            self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

        def session_object(self):
            return self.Session()

    monkeypatch.setattr(admin, "DatabaseSessionManager", TestDatabaseManager)
    return database_url, user_id, email


def _read_state(database_url, user_id):
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        user = session.query(User).filter_by(id=user_id).one()
        return (
            user.is_superuser,
            user.primary_meta_data["refresh_token_version"],
            session.query(PrivilegedAccessEvent).count(),
        )
    finally:
        session.close()
        engine.dispose()


def test_cli_bootstraps_interactively_and_retries_with_exact_id(
    monkeypatch,
    tmp_path,
):
    database_url, user_id, email = _configure_cli_database(monkeypatch, tmp_path)
    runner = CliRunner()

    first = runner.invoke(
        admin.cli,
        [
            "bootstrap-superuser",
            "--email",
            email,
            "--reason",
            "Initial production bootstrap",
        ],
        input="y\n",
    )
    assert first.exit_code == 0, first.output
    assert str(user_id) in first.output
    assert "completed" in first.output
    assert "never-printed-password" not in first.output
    assert _read_state(database_url, user_id) == (True, 1, 1)

    repeated = runner.invoke(
        admin.cli,
        [
            "bootstrap-superuser",
            "--email",
            email,
            "--reason",
            "Safe retry",
            "--confirm-user-id",
            str(user_id),
        ],
    )
    assert repeated.exit_code == 0, repeated.output
    assert "already complete" in repeated.output
    assert _read_state(database_url, user_id) == (True, 1, 1)


def test_cli_rejects_declined_or_mismatched_confirmation(monkeypatch, tmp_path):
    database_url, user_id, email = _configure_cli_database(monkeypatch, tmp_path)
    runner = CliRunner()

    declined = runner.invoke(
        admin.cli,
        [
            "bootstrap-superuser",
            "--email",
            email,
            "--reason",
            "Initial production bootstrap",
        ],
        input="n\n",
    )
    assert declined.exit_code == 1
    assert "Aborted" in declined.output

    mismatch = runner.invoke(
        admin.cli,
        [
            "bootstrap-superuser",
            "--email",
            email,
            "--reason",
            "Initial production bootstrap",
            "--confirm-user-id",
            str(uuid4()),
        ],
    )
    assert mismatch.exit_code == 1
    assert "does not match" in mismatch.output
    assert _read_state(database_url, user_id) == (False, 0, 0)


def test_cli_reports_candidate_and_transaction_errors(monkeypatch):
    disposed = []
    manager = SimpleNamespace(
        engine=SimpleNamespace(dispose=lambda: disposed.append(True)),
    )
    monkeypatch.setattr(admin, "DatabaseSessionManager", lambda: manager)
    runner = CliRunner()
    args = [
        "bootstrap-superuser",
        "--email",
        "admin@example.com",
        "--reason",
        "Initial bootstrap",
        "--confirm-user-id",
        str(uuid4()),
    ]

    monkeypatch.setattr(
        admin,
        "_candidate",
        lambda manager, email: (_ for _ in ()).throw(
            SuperuserBootstrapError("candidate rejected")
        ),
    )
    candidate_error = runner.invoke(admin.cli, args)
    assert candidate_error.exit_code == 1
    assert "candidate rejected" in candidate_error.output

    user_id = uuid4()
    monkeypatch.setattr(
        admin,
        "_candidate",
        lambda manager, email: SimpleNamespace(
            user_id=user_id,
            email="admin@example.com",
        ),
    )
    monkeypatch.setattr(
        admin,
        "_bootstrap",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            SuperuserBootstrapError("transaction rejected")
        ),
    )
    transaction_error = runner.invoke(
        admin.cli,
        [*args[:-1], str(user_id)],
    )
    assert transaction_error.exit_code == 1
    assert "transaction rejected" in transaction_error.output
    assert disposed == [True, True]


def test_admin_main_invokes_cli(monkeypatch):
    invoked = []
    monkeypatch.setattr(admin, "cli", lambda: invoked.append(True))

    admin.main()

    assert invoked == [True]
