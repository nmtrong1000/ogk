---
paths:
  - "ogk-server/migrations/**"
---

# Server migrations

- Alembic autogenerate inserts `# ### commands auto generated ###` comments; delete them from new migrations (comment rule, WORKFLOW.md section 6).
- A migration that changes the schema updates `ogk-server/migrations/DB_SCHEMA.md` in the same commit: ER diagram, column tables and integrity constraints (WORKFLOW.md section 5). New constraint IDs continue from the highest `IC-nnn`; never reuse one.
