# Agent Workflow Docs

## Document Relations

- Parent entry point: `AGENTS.md`
- This document is the workflow index for agents and points to the smallest next document to read.
- Child documents:
  - `docs/agent-workflow/git-rules.md`
  - `docs/agent-workflow/documentation-rules.md`
  - `docs/agent-workflow/templates.md`

## Purpose

- Keep `AGENTS.md` short.
- Allow `AGENTS.md` to carry a minimal recent-work resume hint without replacing the normal issue and management-document lookup flow.
- Let agents open only the detailed document needed for the current task.
- Separate durable workflow rules from issue-specific management documents.

## Read Order

- At session startup: `AGENTS.md`
- At session startup: `docs/agent-workflow/documentation-rules.md`
- At session startup when git work is expected: `docs/agent-workflow/git-rules.md`
- Before any file edit, creation, move, or deletion: re-read `AGENTS.md` `## Pre-Execution Gate`
- Before any file edit, creation, move, or deletion: `docs/agent-workflow/documentation-rules.md`
- Before commit, push, or PR work: `docs/agent-workflow/git-rules.md`
- For placeholders, naming formats, and reusable examples: `docs/agent-workflow/templates.md`

## Scope

- These docs are the primary agent-oriented workflow references for this repository.
- Treat `docs/issues/` as the repository-local management document store.
- Do not depend on absolute local filesystem paths in workflow rules or management documents.
