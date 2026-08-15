# Userverse documentation

Userverse is a FastAPI service for users, companies, authentication, roles, permissions, and memberships. PostgreSQL and MySQL are supported production databases.

Start here:

- [Developer setup](development.md): one-command onboarding, Compose database profiles, and daily commands.
- [Configuration](configuration.md): environment variables, validation, database URLs, JWT, email, and CORS.
- [Testing](testing.md): local checks, 100% coverage, pre-commit, and container verification.
- [Database migrations](migrations.md): create, test, deploy, and roll back Alembic revisions safely.
- [Production deployment](production.md): immutable images, deliberate migrations, health checks, Trivy, and GHCR.
- [Troubleshooting](troubleshooting.md): common Docker, database, lockfile, migration, health, and registry failures.

Domain and operator guides:

- [Global and company RBAC](role-permission-guide.md)
- [Superuser administration](superuser-administration.md)
- [GitHub workflows](github-workflows.md)
- [FAQ](faq.md)
