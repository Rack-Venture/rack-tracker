# MVP v2 Issue Tracking

Use this structure to draft and maintain GitHub issues for `mvp v2`.

- `umbrella/`: top-level issue docs for scope, goals, risks, and linked work
- `sub-issues/`: management documents for concrete tasks or chores
- `sub-issues/README.md`: local index for sub-issue document relationships and nested design-note folders

## Recommended Flow

1. Start from `umbrella/mvp-v2-umbrella.md`.
2. Add focused work items as management documents under `sub-issues/`.
3. Include `Parent: #<issue-number>` in each sub-issue draft.
4. Put supporting design notes under a child folder named after the parent management document.
5. Keep shared scope changes and cross-cutting decisions in the umbrella doc.
