# OGK: rules for Claude

@WORKFLOW.md

WORKFLOW.md above is the source of truth for phases, branches and commits, the DB schema contract, comments and language, imports and lint. The rules below only cover how Claude works inside that process. Topic rules that apply to part of the repo live in `.claude/rules/`.

## Working through a phase

- Say which step and round you are in whenever you move to another step, e.g. "TESTING, round 2 of 2".
- Never commit, merge or push before the user approves at HUMAN REVIEW. One approval covers one commit, merge and push, not the next ones.
- Every HUMAN REVIEW message carries the test checklist from WORKFLOW.md section 3. Do not wait to be asked how to test.
- Do everything you can yourself: tests, builds, logs, DB queries, the VM over SSH. Ask the user only for actions that need a human on the child's screen, batched into one numbered list, each step with its expected result.
