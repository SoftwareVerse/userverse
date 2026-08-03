# GitHub Workflows

This project currently defines two GitHub Actions workflows in `.github/workflows/`:

- `build-and-test.yml`
- `release.yml`

Both workflows run on pushes to `main`. The test workflow also runs on pull requests targeting `main`.

## Current Workflow Layout

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `build-and-test.yml` | `push` to `main`, `pull_request` to `main` | Install Python with `uv`, sync dependencies, check formatting with Black, run the HTTP integration test suite, and upload coverage to Codecov. |
| `release.yml` | `push` to `main` | Calculate the next semantic version, update `pyproject.toml`, create a Git tag, and create or update a GitHub release. |

## How `build-and-test.yml` Works

The workflow is named `CI - HTTP Integration Tests with uv`.

### Trigger behavior

- Runs for every push to `main`.
- Runs for every pull request targeting `main`.

### What it does

1. Checks out the repository with full history using `actions/checkout@v4`.
2. Installs the latest `uv` release by downloading Astral's install script.
3. Installs Python `3.12` through `uv`.
4. Creates a virtual environment with `uv venv`.
5. Installs project dependencies with `uv sync`.
6. Runs `black --check .` across the repository.
7. Skips `[skip ci]` automation commits such as release version bumps.
8. Runs `./scripts/run_http_tests.sh`.
9. Uploads `coverage_reports/coverage.xml` to Codecov using `codecov/codecov-action@v5`.

### Test command details

The workflow delegates test execution to [`scripts/run_http_tests.sh`](/home/sandile/projects/pj-userverse/userverse/scripts/run_http_tests.sh:1).

That script currently:

- sets `ENVIRONMENT=testing`
- sets `TESTING=true`
- removes `test_environment.db` if present
- creates `coverage_reports/`
- runs:

```bash
uv run pytest -v --cov=app \
  --cov-report=term-missing \
  --cov-report=xml:coverage_reports/coverage.xml \
  --cov-fail-under=96
```

Coverage must stay at or above `96%` or the job fails.

### Formatting behavior

The workflow validates formatting only:

- `black --check .` fails the job when formatting is needed.
- The workflow does not rewrite files or push commits.

## How `release.yml` Works

The workflow is named `CI - Release Tag`.

### Trigger behavior

- Runs for every push to `main`.

### What it does

1. Checks out the full repository history and tags.
2. Fetches tags and determines the latest existing semantic version tag.
3. Collects non-merge commits since the latest tag and ignores automation commits such as `style: auto-format code with Black` and `chore: bump version to vX.Y.Z [skip ci]`.
4. Determines the highest requested version bump across those commits:
   - `[major]` -> major bump
   - `[minor]` -> minor bump
   - anything else -> patch bump
5. Calculates the next version.
6. Generates release notes from those filtered commits.
7. Configures Git credentials with `GITHUB_TOKEN`.
8. Updates `pyproject.toml` inside the `[project]` section.
9. Commits the version change with message `chore: bump version to vX.Y.Z [skip ci]`.
10. Creates an annotated Git tag `vX.Y.Z`.
11. Pushes `main` and the new tag.
12. Creates or updates the GitHub Release for that tag using the GitHub CLI.

### Version calculation rules

The workflow uses the latest tag as the base version. If no tag exists, it starts from `v0.1.0`.

Examples:

- latest tag `v0.6.29` + no marker in commits since that tag -> `v0.6.30`
- latest tag `v0.6.29` + any `[minor]` in commits since that tag -> `v0.7.0`
- latest tag `v0.6.29` + any `[major]` in commits since that tag -> `v1.0.0`

`[major]` takes precedence over `[minor]`, and automation commits are ignored.

### Release notes behavior

- If a previous tag exists, notes are generated from filtered non-merge commits in `git log <previous_tag>..HEAD`.
- If no previous tag exists, notes are generated from filtered non-merge commits on `main`.
- Each entry is formatted as commit subject, short SHA, and author.

## How To Use These Workflows

### For pull requests

- Open a pull request against `main`.
- GitHub runs `build-and-test.yml`.
- The PR workflow validates dependency installation, test execution, and coverage.
- Black still runs during the job, but formatting changes are not pushed back to your branch automatically.

To avoid CI failures or drift, run formatting and tests locally before opening the PR:

```bash
uv sync
uv run black .
./scripts/run_http_tests.sh
```

### For merges to `main`

Once code is merged or pushed to `main`:

- `build-and-test.yml` runs
- `release.yml` runs

That means a push to `main` currently does all of the following automatically:

- checks formatting
- runs the HTTP integration test suite
- uploads coverage to Codecov
- bumps the project version
- creates a tag
- creates or updates a GitHub release

### To control release version bumps

Use commit messages in the set of changes that land since the previous release tag:

- add `[major]` for a major release
- add `[minor]` for a minor release
- omit both for a patch release

Example commit messages:

- `feat: add audit export [minor]`
- `refactor!: simplify auth flow [major]`
- `fix: handle empty organisation name`

## Repository Dependencies And Secrets

These workflows currently depend on:

- `GITHUB_TOKEN` for pushing commits, tags, and managing releases
- `CODECOV_TOKEN` for Codecov upload
- internet access during CI to install `uv` and Python

They also assume:

- `pyproject.toml` contains the package version in `[project].version`
- `scripts/run_http_tests.sh` remains the CI entrypoint for tests
- the GitHub runner has `gh` available for release creation

## Potential Improvements

The current workflows are functional, but there are a few areas worth tightening.

### 1. Prevent workflow chaining and duplicate runs

Release automation still creates a version-bump commit, so `[skip ci]` remains part of the design to prevent unnecessary follow-up runs.

Possible improvement:

- add branch protections around direct pushes to `main`
- or gate release creation behind a dedicated manual or tagged workflow

### 2. Run release only after tests succeed

Both workflows trigger independently on pushes to `main`. The release workflow is not explicitly dependent on the test workflow passing first.

Possible improvement:

- trigger release from `workflow_run` after a successful test workflow
- or combine the release logic into a gated post-test job

### 3. Pin tool versions more explicitly

The test workflow installs the latest `uv` release at runtime. That can make CI behavior drift over time.

Possible improvement:

- pin a known `uv` version
- optionally cache Python and dependency artifacts for faster, more stable runs

### 4. Review commit-message-based versioning

The release workflow now inspects all releaseable commits since the latest tag. That is better than a single-commit check, but it still depends on commit-message discipline.

Possible improvement:

- derive release type from PR labels
- use Conventional Commits across all commits since the last tag
- or adopt a release tool such as Changesets or semantic-release

### 5. Clarify release notes quality

Current release notes are generated from raw commit subjects. That is simple, but not always user-friendly.

Possible improvement:

- group notes by feature, fix, and breaking change
- exclude internal-only commits
- generate notes from PR titles instead of raw commit history

### 6. Align docs with the live test script

The existing testing docs mention `REQUIRE_EMAIL_VERIFICATION=true`, but the current CI script only sets `ENVIRONMENT=testing` and `TESTING=true`.

Possible improvement:

- update the testing docs whenever the script changes
- or move test environment configuration into one documented source of truth

## Recommended Team Usage

Given the current implementation, the safest contributor workflow is:

1. Run Black locally before pushing.
2. Run `./scripts/run_http_tests.sh` locally before opening a PR.
3. Use `[minor]` or `[major]` in the commit message only when a real semantic version change is intended.
4. Treat every push to `main` as release-producing automation.
