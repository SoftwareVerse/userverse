# Private Upstream Sync

This repository can stay private while still pulling changes from the old
`softwareverse` remote.

## Current remote setup

- `origin`: your private repository, for example `Vesta-Books/main-backend`
- `softwareverse`: the old upstream repository, for example `SoftwareVerse/userverse`

Check the configured remotes with:

```bash
git remote -v
```

## Fetch changes from the old remote

Fetching downloads remote changes into your local git metadata. It does not make
your repository public and does not push anything anywhere.

```bash
git fetch softwareverse
git branch -r
```

## Bring upstream changes into this repo

If you want to merge everything from the old remote's `main` branch into your
current branch:

```bash
git merge softwareverse/main
```

If you want to replay your local work on top of the upstream branch instead:

```bash
git rebase softwareverse/main
```

If you only want selected commits:

```bash
git log softwareverse/main --oneline
git cherry-pick <commit-sha>
```

## Push only to the private repository

After merging, rebasing, or cherry-picking, push only to `origin`:

```bash
git push origin main
```

This updates your private repository only.

## Important notes

- `git fetch softwareverse` does not publish your code.
- `git push origin ...` pushes only to your private repository.
- Nothing is sent back to `softwareverse` unless you explicitly push there.

## Recommended workflow

Use this flow when you want to keep this repository private while still syncing
selected or full changes from the old upstream:

```bash
git fetch softwareverse
git log softwareverse/main --oneline
git merge softwareverse/main
git push origin main
```

If you need more control, replace `merge` with `rebase` or `cherry-pick`.
