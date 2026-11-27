# Project structure

The dashboard is a Vite, React, and TypeScript application organized by feature. A feature owns its UI and behavior; cross-feature code belongs in `shared/`.

```text
ogk-dashboard/
├── docs/                         Dashboard conventions and review guidance
├── public/                       Static public assets
├── src/
│   ├── app/                      App startup, router, app-level styles and pages
│   ├── features/                 Product capabilities, organized by feature
│   │   └── <feature>/            One product capability
│   │       ├── pages/            Route-level screens (when needed)
│   │       ├── components/       Feature-owned UI (when needed)
│   │       ├── hooks/            Feature-owned hooks (when needed)
│   │       ├── api.ts            Feature endpoints and query keys (when needed)
│   │       ├── schemas.ts        Feature validation schemas (when needed)
│   │       ├── utils/            Feature-owned helpers (when needed)
│   │       └── index.ts          Public exports (when needed)
│   └── shared/
│       ├── api/                  HTTP client and shared API operations
│       ├── components/           Reusable controls and display components
│       ├── layouts/              Dashboard, authentication, and child-view shells
│       ├── styles/               Shared design tokens and surface styles
│       ├── types/                Shared API and domain types
│       └── utils/                Shared pure utilities
├── tests/
│   ├── e2e/                      Playwright tests with mocked APIs
│   └── unit/                     Vitest unit tests
├── package.json                  Scripts and dependencies
├── playwright.config.ts          Playwright configuration
├── vite.config.ts                Vite and import alias configuration
└── vitest.config.ts              Vitest configuration
```

## Feature contents

Use this template only for folders a feature needs; do not create empty folders. A feature may also define local types. Feature code must not depend on another feature; extract a shared capability into `src/shared/` if multiple features need it.

## Ownership

- `app/` wires the application together and owns route-level composition.
- `features/<name>/` owns product behavior for that capability.
- `shared/api/` owns shared transport concerns such as credentials and CSRF.
- `shared/components/` and `shared/layouts/` own reusable UI and application shells.
- `tests/` mirrors important behavior without becoming a second implementation of product logic.
- `dist/` is generated output and must not be edited by hand.
