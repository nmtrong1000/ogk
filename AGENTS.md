# OGK: rules for Codex

`WORKFLOW.md` is the source of truth for phase steps, branches and commits, DB schema contracts, comments and language, imports, and lint/format. `PLAN.md` describes the architecture and project constraints; phase-specific plans live in `plan/`. Topic-specific rules are in `.claude/rules/`; read the relevant files when working on migrations or the Windows VM.

## Starting a session

- Check the current branch, git status, and recent history before changing files. Identify the active phase from the plan and current user request; do not rely on stale chat context.
- Read the applicable phase plan and the relevant parts of `WORKFLOW.md`, `PLAN.md`, `docs/protocol.md`, and the app's `migrations/DB_SCHEMA.md` before implementation.
- For `ogk-dashboard` work, also read `ogk-dashboard/DESIGN.md`, `ogk-dashboard/docs/CODE_CONVENTIONS.md`, and `ogk-dashboard/docs/PROJECT_STRUCTURE.md`; apply `ogk-dashboard/docs/REVIEW_CHECKLIST.md` during REVIEW.
- Preserve existing user changes. Do not include secrets, databases, certificates, or generated build artifacts in commits.

## Working through a phase

- State the current phase step and round when moving to another step, e.g. `TESTING, round 2 of 2`.
- Follow the TESTING, REVIEW, and HUMAN REVIEW loops and limits in `WORKFLOW.md`.
- Every HUMAN REVIEW message must include the checklist from `WORKFLOW.md` section 3, with exact dashboard/VM steps and expected results. Do not wait for the user to ask how to test.
- Do the available work yourself: tests, builds, log review, DB inspection, and Windows VM work over SSH/UTM. Batch actions that require a person at the child's screen into one numbered checklist.
- Report environmental limits and distinguish them from product failures. Do not claim tests or manual acceptance passed without evidence.

## Commit and merge

- Never commit, merge, or push until the user approves at HUMAN REVIEW. One approval authorizes one commit/merge/push sequence only.
- Work on the phase branch named `phase/p<number>`; do not commit directly to `main`.
- Use a Conventional Commit message. Merge the approved phase branch into `main` and push only the approved result, following `WORKFLOW.md`.

## Data and audit safety

- Prefer supported application workflows over direct edits to a live database.
- A direct live-data mutation requires an explicit user request. Before it, inspect affected rows and cascades; verify the exact target, preserve unrelated data, and report what remains in append-only audit logs.
- Keep audit logs append-only and update `DB_SCHEMA.md` with every schema change in the same commit as the model and migration.
