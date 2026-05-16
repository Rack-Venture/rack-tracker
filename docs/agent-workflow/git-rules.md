# Agent Git Rules

## Document Relations

- Parent index: `docs/agent-workflow/README.md`
- Related templates: `docs/agent-workflow/templates.md`
- Related documentation rules: `docs/agent-workflow/documentation-rules.md`

## Repository Remote Setup

- `upstream`: `https://github.com/Rack-Venture/rack-tracker.git` — the organization source of truth
- `origin`: personal fork of upstream — where you push feature branches before opening a PR
- Never push directly to `upstream`.
- Confirm remotes with `git remote -v` before push or PR work.

## Git Startup Checklist

- Check whether an existing open GitHub issue already matches the requested work.
- After the GitHub issue check, search for the matching management document under `docs/issues/`.
- Before any file edit, file creation, file move, or file deletion, re-run the management-document check from `AGENTS.md`.
- Do not skip that check because the change looks small or simple.
- Confirm the current branch matches the intended work.
- Confirm the changed files match the requested scope.

## Branch Rules

- Always branch from `develop`. Sync with `upstream/develop` before branching:
  ```bash
  git fetch upstream
  git checkout feature/이슈번호-description
  ```
- Branch name format: `type/이슈번호-short-description`
  - Example: `feature/12-rack-registration-api`
  - Example: `fix/34-login-token-expiry`
- Use one of these type values: `feature`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `perf`
- Use `hotfix/이슈번호-description` branching from `main` only for production emergencies.
- Use `release/버전` branching from `develop` for release preparation.
- Use a placeholder branch name until the real issue number is confirmed.

## Commit Rules

- Before any commit, update the management document that matches the work.
- Treat a missing management-document update as a workflow error, even for one-line fixes.
- Commit message format:
  ```
  type: 변경 내용 요약 (#이슈번호)

  - 세부 변경 사항 1
  - 세부 변경 사항 2
  ```
- Use one of these type values: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Do not finalize issue numbers in commit messages before GitHub has assigned them. Use `#<issue-number>` as a placeholder.
- On Windows, prefer writing the commit message to a temp file and using `git commit -F <message-file>`.
- Use repository-relative paths in commit messages when referencing files.

## Push Rules

- Always push to `origin` (personal fork), never to `upstream`.
- Before push, sync with `upstream/develop` to resolve conflicts locally:
  ```bash
  git fetch upstream
  git merge upstream/develop
  ```
- Resolve any conflicts, commit the resolution, then push:
  ```bash
  git push origin type/이슈번호-description
  ```

## PR Rules

- PR source: `내계정/rack-tracker` → `type/이슈번호-description`
- PR target: `Rack-Venture/rack-tracker` → `develop`
- PR title format: `[TYPE] 작업 내용 요약 (#이슈번호)`
- Merge strategy: **Squash and Merge** only
- Minimum approval: 1 team member Approve before merge
- Delete the branch immediately after merge
- Keep the PR body aligned with the management document using the template from `docs/agent-workflow/templates.md`.

## Prohibited Actions

- Direct push to `main` or `develop`
- Force push (`--force`)
- Merge without a PR
- Merge without at least 1 Approve
