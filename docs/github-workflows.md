# GitHub workflows

Userverse has three workflows:

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `build-and-test.yml` | pushes and pull requests to `main` | Install pinned uv and Python, install the locked development group, run `make lint`, and enforce 100% coverage with `make coverage`. |
| `docker-smoke.yml` | pushes/tags, pull requests, weekly schedule, manual | Build the real production Dockerfile, generate/upload Trivy SARIF, enforce the vulnerability policy, migrate MySQL and PostgreSQL, verify `/` and Docker health, then publish eligible pushes to GHCR. |
| `release.yml` | pushes to `main` | Calculate the semantic version, update project metadata, create an annotated tag, and create a GitHub release. |

## Contributor checks

Run the Python workflow locally with:

```bash
uv sync --locked --group dev
make check
```

Changes affecting the container, dependencies, entrypoint, or migrations should additionally run:

```bash
make docker-test
```

The Docker workflow uploads SARIF only when Trivy successfully created a report, so an earlier build failure is not hidden by a missing-file upload error.

## Release behavior

Release automation collects non-merge commits since the latest semantic tag. `[major]` requests a major bump, `[minor]` requests a minor bump, and other releaseable changes receive a patch bump. Version-only `[skip ci]` commits are excluded.

The release and test workflows currently start independently on a push to `main`. Repository branch protection should require Python and Docker checks before merge. A future improvement is to trigger release publication only after required checks succeed.

## Container publication

After all Docker checks pass:

- a push to `main` publishes `latest` and `sha-<full-commit-sha>`;
- a semantic tag publishes full and major/minor version tags;
- pull requests, schedules, and manual runs do not publish.

The package is `ghcr.io/softwareverse/userverse`. GitHub organization administrators must make its first package version public if public anonymous pulls are required.

## Security and maintenance

Actions that handle security reports are pinned to commit SHAs. The Python workflow uses the immutable `setup-uv` v9 action and pins uv itself. Dependabot opens grouped weekly updates for Python packages, GitHub Actions, and Docker images. Review and test these updates; do not merge version bumps only because they are newer.

Required permissions and credentials:

- `GITHUB_TOKEN` writes release tags/releases and GHCR packages in their respective workflows.
- `security-events: write` uploads Trivy SARIF.
- A local maintainer needs `GHCR_USERNAME` and a token with `write:packages` for `scripts/publish_image.sh`.
