# Dashboard review checklist

Use this checklist during the REVIEW step for changes to `ogk-dashboard`. Check applicable best-practice items after verifying them. Record applicable anti-patterns as review findings; an anti-pattern section is not a list of goals to check off.

## Project

### Best practices

- [ ] Changes follow the feature ownership boundaries in [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md); shared behavior lives in `src/shared/`.
- [ ] Feature code does not import from another feature; imports from `src/` use the `@/` alias.
- [ ] API access uses the shared client and keeps endpoint functions in the owning feature or shared API layer.
- [ ] User-facing strings are Vietnamese; API error codes are translated at the feature boundary.
- [ ] Tests cover the changed behavior at an appropriate level and mock API responses in E2E tests.
- [ ] No secrets, local databases, generated output, or unrelated changes are included.

### Anti patterns

- Importing one feature's internal components or API directly into another feature.
- Duplicating API transport, CSRF handling, date formatting, or shared UI controls inside a feature.
- Placing route definitions, product behavior, and reusable UI together in an unowned catch-all module.
- Updating generated `dist/` files by hand or committing local credentials and data.

## Accessibility

### Best practices

- [ ] Controls use semantic HTML and have accessible names, labels, and descriptions where needed.
- [ ] All interactive behavior works with a keyboard and has a visible focus state.
- [ ] Heading levels describe the page structure, with one page-level `h1`.
- [ ] Dialogs, validation errors, loading states, and status updates are perceivable to assistive technology.
- [ ] Color is not the only way to convey meaning, and text remains readable on glass surfaces.
- [ ] Motion respects reduced-motion preferences.

### Anti patterns

- Clickable non-interactive elements without keyboard behavior or an accessible role/name.
- Icon-only controls without an accessible name.
- Removing focus outlines without a visible replacement.
- Using color alone to communicate success, warning, error, or selection.
- Using placeholder text as the only form-field label.

## Performance

### Best practices

- [ ] Server state uses TanStack Query caching and invalidation instead of redundant local copies.
- [ ] Polling and subscriptions are enabled only while needed and stop when the screen or state no longer requires them.
- [ ] Expensive or route-specific code is split when it materially reduces initial loading cost.
- [ ] Lists use stable keys and avoid unnecessary work for each item.
- [ ] Large assets, tables, and charts remain usable on mobile and do not cause avoidable layout shifts.

### Anti patterns

- Fetching the same resource independently from multiple components without shared query state.
- Polling continuously when the relevant screen is inactive or the result is terminal.
- Adding memoization everywhere without evidence of repeated expensive work.
- Importing large optional feature code into the initial route bundle without need.

## React

### Best practices

- [ ] Components render from props and state; effects synchronize with external systems only.
- [ ] Derived values are computed during render instead of copied into state by an effect.
- [ ] State is kept at the narrowest component or feature that owns it.
- [ ] Hooks are called unconditionally at the top level and effect dependencies are complete.
- [ ] Async work handles loading, success, empty, and error states where those states can occur.
- [ ] Shared context values and callbacks are stable when their identity affects consumers.

### Anti patterns

- Calling state setters synchronously in effects to derive state from props or other state.
- Mutating props, state, query data, or arrays/objects held by React.
- Using array indexes as keys for lists that can change order or membership.
- Storing server data in local state and allowing the two copies to drift.
- Suppressing hook dependencies to force an effect to run fewer times.

## TypeScript

### Best practices

- [ ] Public component props, API boundaries, and domain state have useful explicit types.
- [ ] Untrusted values use `unknown` and are narrowed or validated before use.
- [ ] API forms validate with the feature's Zod schema and preserve inferred types where appropriate.
- [ ] Nullable and optional values are handled explicitly.
- [ ] Types model supported domain variants without weakening the project compiler settings.
- [ ] `npm run build` passes its TypeScript project check when validation is required.

### Anti patterns

- Introducing `any`, broad type assertions, or non-null assertions to bypass an unclear type.
- Duplicating a type that already has a shared or feature-owned source of truth.
- Treating API payloads as trusted without validation or narrowing at the boundary.
- Using boolean/string unions that permit impossible combinations when a discriminated union fits.
- Hiding TypeScript failures with `@ts-ignore` or weakening compiler settings.
