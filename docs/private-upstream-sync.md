# Private Upstream Sync

This repository can stay private while still pulling changes from another
repository through an upstream remote.

## Current remote setup

- `origin`: the repository you push your private changes to
- `upstream`: the repository you pull shared changes from

Configure the upstream remote when it is not already present:

```bash
git remote add upstream <upstream-repository-url>
```

Check the configured remotes with:

```bash
git remote -v
```

## Fetch changes from the old remote

Fetching downloads remote changes into your local git metadata. It does not make
your repository public and does not push anything anywhere.

```bash
git fetch upstream
git branch -r
```

## Bring upstream changes into this repo

If you want to merge everything from the old remote's `main` branch into your
current branch:

```bash
git merge upstream/main
```

If you want to replay your local work on top of the upstream branch instead:

```bash
git rebase upstream/main
```

If you only want selected commits:

```bash
git log upstream/main --oneline
git cherry-pick <commit-sha>
```

## Push only to the private repository

After merging, rebasing, or cherry-picking, push only to `origin`:

```bash
git push origin main
```

This updates your private repository only.

## Important notes

- `git fetch upstream` does not publish your code.
- `git push origin ...` pushes only to your private repository.
- Nothing is sent to `upstream` unless you explicitly push there.

## Recommended workflow

Use this flow when you want to keep this repository private while still syncing
selected or full changes from the old upstream:

```bash
git fetch upstream
git log upstream/main --oneline
git merge upstream/main
git push origin main
```

If you need more control, replace `merge` with `rebase` or `cherry-pick`.
