# Code conventions

These conventions apply to TypeScript, React, styles, and tests in `ogk-dashboard`.

## Imports and module boundaries

- Import files from `src/` through the `@/` alias, including files in the same feature. Do not use `./` or `../` imports.
- Keep feature-owned pages, components, API functions, hooks, schemas, and utilities inside that feature.
- Features must not import from another feature. Move genuinely shared code to `src/shared/`.
- Keep application startup, route definitions, and app-level styles in `src/app/`.
- Keep dashboard-wide shells in `src/shared/layouts/` and reusable UI in `src/shared/components/`.
- Export a feature's public entry points through its `index.ts` when other modules need them.

## React and data flow

- Use function components and hooks. Keep state close to the component or feature that owns it.
- Use TanStack Query for server state, caching, polling, and invalidation; do not mirror query data into local state without a specific need.
- Keep API transport and endpoint functions in the feature's `api.ts` or the shared API layer. Use the shared API client for credentials, CSRF handling, and error conversion.
- Use shared form controls and feature-level Zod schemas for form validation. Do not duplicate a schema in component event handlers.
- Use semantic HTML and keep effects for synchronization with external systems, not for values that can be derived during render.

## Types and naming

- Use TypeScript types for API payloads, component props, and state boundaries. Avoid `any`; use `unknown` and narrow it when the shape is not known.
- Name React components and component files in PascalCase. Name hooks with the `use` prefix and utility functions in camelCase.
- Keep API types in `src/shared/types/` when they are shared; feature-specific types belong to the feature.
- Prefer explicit, domain-specific names over abbreviations whose meaning is not clear locally.

## Language, errors, and comments

- User-facing dashboard text is Vietnamese. System logs, exceptions, and CLI output are English.
- Convert API error codes to Vietnamese user messages in the relevant feature's message utility; do not show raw server details to users.
- Source comments, when needed, are English and explain a constraint or reason that the code cannot make clear by itself.
- Do not add inline comments, JSX comments, or docstrings. Put any necessary comment in a short header block at the top of the file.

## Validation commands

Run these from `ogk-dashboard/` when the task or phase calls for validation:

```sh
npm test
npm run test:e2e
npm run lint
npm run format:check
npm run build
```

`npm run build` also runs the TypeScript project build. Import alias configuration in `tsconfig.app.json` and `vite.config.ts` must stay aligned.
