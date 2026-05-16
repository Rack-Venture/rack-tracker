# Agent Documentation Rules

## Document Relations

- Parent index: `docs/agent-workflow/README.md`
- Related git rules: `docs/agent-workflow/git-rules.md`
- Related templates: `docs/agent-workflow/templates.md`

## Management Document Rule

- Apply the pre-execution check immediately before any file edit, file creation, file move, or file deletion.
- Treat that pre-execution check as separate from session-start rule reading.
- Use behavior, not perceived task size, to decide whether the check applies.
- "Small task", "simple fix", "one-line change", "quick cleanup", and similar labels are not exceptions.
- Only pure question-answer turns with no file changes are exempt.
- If the match or logging duty is unclear, re-read this file before changing files.
- `AGENTS.md` may include a short `## Recent Active Context` block near the top.
- Keep that block lightweight: last active work name, a repository-relative tracking-document path, and a one-line summary.
- Treat that block as a resume hint only. It does not replace GitHub issue lookup or management-document discovery.
- Use the recent active context only when the user's new request clearly belongs to the same issue or sub-issue.
- For simple questions or unrelated requests, answer directly without forcing reuse of the recent active context.
- After checking for a matching GitHub issue, search the repository for the matching management document before creating a new one.
- When the task is to continue, resume, or update ongoing work, search `docs/issues/` first.
- Reuse an existing management document only when the issue, summary, scope, and current requested work clearly match.
- If no suitable management document exists after that search, create one under the matching type directory before committing.
- Before any commit, update the management document that matches the work.
- Do not log every task in one fixed document.

## Management Document Location

- Place the management document under the matching type directory:
  - `docs/issues/feature/`
  - `docs/issues/fix/`
  - `docs/issues/refactor/`
  - `docs/issues/docs/`
  - `docs/issues/chore/`
  - `docs/issues/ci/`
  - `docs/issues/perf/`
  - `docs/issues/test/`
- Use the issue branch name **without the type prefix** as the file name.
  - Branch `feature/12-rack-registration-api` → file `docs/issues/feature/12-rack-registration-api.md`
  - Branch `fix/34-login-token-expiry` → file `docs/issues/fix/34-login-token-expiry.md`
- Keep the issue title, issue number, branch name, directory type, and management document file name aligned.
- Use repository-relative paths in management documents so local workspace path changes do not invalidate the workflow.

## Work Log Rule

- Record implementation progress in the issue management document at commit-sized granularity.
- Use one `##` section per commit-sized work unit.
- Use the commit title as that section heading.
- Lower headings (`### Scope`, `### Changes`, `### Verification`, `### Notes`) inside a log section are optional.
- After completing a work unit, show the user a summary of changed files and request explicit approval before writing the log or committing.
- Write the log and commit only after the user approves. Do not log or commit without approval.
- Commit immediately after each approved work unit. Do not accumulate changes across multiple work units and commit later.
- If files changed without a matching management-document update, treat that as a workflow miss and correct it in the same work session.

## Cleanup Rule

- For repository cleanup work, record keep, remove, move, or archive decisions in the relevant management document.
- Prefer `archive/` over immediate deletion when a path may still be useful for reference.

## Sync Rule

- When a workflow change affects multiple docs, update the related docs in the same change.
- Do not let top-level guidance and detailed templates diverge.
