from __future__ import annotations

from uuid import UUID

import click
from pydantic import ValidationError
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.repository.database.session_manager import DatabaseSessionManager
from app.configs import Settings
from app.services.superuser_bootstrap import (
    SuperuserBootstrapCandidate,
    SuperuserBootstrapError,
    SuperuserBootstrapResult,
    SuperuserBootstrapService,
)


def _candidate(
    manager: DatabaseSessionManager, email: str
) -> SuperuserBootstrapCandidate:
    session = manager.session_object()
    try:
        return SuperuserBootstrapService(session).get_candidate(email)
    finally:
        session.close()


def _bootstrap(
    manager: DatabaseSessionManager,
    *,
    email: str,
    reason: str,
    user_id: UUID,
) -> SuperuserBootstrapResult:
    session = manager.session_object()
    try:
        return SuperuserBootstrapService(session).bootstrap(
            email=email,
            reason=reason,
            expected_user_id=user_id,
        )
    finally:
        session.close()


@click.group()
def cli() -> None:
    """Run trusted Userverse administration commands."""


@cli.command("config-check")
def config_check() -> None:
    """Validate runtime configuration without connecting to external services."""
    try:
        runtime_settings = Settings()
    except (ValidationError, ValueError) as exc:
        raise click.ClickException(f"Invalid configuration: {exc}") from exc

    try:
        database_url = make_url(runtime_settings.DATABASE_URL)
    except (ArgumentError, TypeError) as exc:
        raise click.ClickException(
            "DATABASE_URL is not a valid SQLAlchemy URL."
        ) from exc

    backend = database_url.get_backend_name()
    if backend not in {"postgresql", "mysql", "sqlite"}:
        raise click.ClickException(
            "DATABASE_URL must use PostgreSQL, MySQL, or development-only SQLite."
        )
    if (
        runtime_settings.ENVIRONMENT not in {"development", "testing", "test"}
        and backend == "sqlite"
    ):
        raise click.ClickException(
            "SQLite is supported only for development and tests."
        )
    if runtime_settings.EMAIL_SSL and runtime_settings.EMAIL_TLS:
        raise click.ClickException("EMAIL_SSL and EMAIL_TLS cannot both be enabled.")

    click.echo(f"Configuration is valid for {runtime_settings.ENVIRONMENT}.")
    click.echo(f"Database: {database_url.render_as_string(hide_password=True)}")


@cli.command("bootstrap-superuser")
@click.option(
    "--email",
    required=True,
    help="Email of an existing active and verified user.",
)
@click.option(
    "--reason",
    required=True,
    help="Operational reason recorded in the privileged audit event.",
)
@click.option(
    "--confirm-user-id",
    type=click.UUID,
    help="Exact target UUID required for non-interactive execution.",
)
def bootstrap_superuser(
    email: str,
    reason: str,
    confirm_user_id: UUID | None,
) -> None:
    """Promote the one and only initial superuser."""
    manager = DatabaseSessionManager()
    try:
        try:
            candidate = _candidate(manager, email)
        except SuperuserBootstrapError as exc:
            raise click.ClickException(str(exc)) from exc

        if confirm_user_id is not None:
            if confirm_user_id != candidate.user_id:
                raise click.ClickException(
                    "--confirm-user-id does not match the resolved user."
                )
        else:
            click.confirm(
                (
                    "Promote the existing active user "
                    f"{candidate.email} ({candidate.user_id}) to initial superuser?"
                ),
                abort=True,
            )

        try:
            result = _bootstrap(
                manager,
                email=email,
                reason=reason,
                user_id=candidate.user_id,
            )
        except SuperuserBootstrapError as exc:
            raise click.ClickException(str(exc)) from exc

        if result.changed:
            click.echo(
                f"Initial superuser bootstrap completed for user ID {result.user_id}."
            )
        else:
            click.echo(
                f"Initial superuser bootstrap was already complete for user ID "
                f"{result.user_id}."
            )
    finally:
        manager.engine.dispose()


def main() -> None:
    cli()
