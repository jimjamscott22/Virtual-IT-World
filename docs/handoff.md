# Helpdesk workbench handoff

Updated 2026-10-14 after resuming the workbench redesign from commit `e25d316`.
This file records transient branch and verification state. The durable design is
in `docs/superpowers/specs/2026-09-26-helpdesk-workbench-design.md`; the
step-by-step checklist is in
`docs/superpowers/plans/2026-09-26-helpdesk-workbench-ui.md`.

## Current state

| | |
| --- | --- |
| Branch | `work` |
| Implementation commit | `e25d316` (`Refactor templates for improved structure and styling`) |
| Automated tests | 1731 passed; one third-party Starlette deprecation warning |
| Lint | `src` and `tests` both exit 0 at 10.00/10 |
| Working tree at pickup | clean |

Tasks 1–5 of the workbench plan are implemented. Task 6's automated regression,
lint, and whitespace checks have been repeated successfully. The remaining work
is the real-browser workflow and responsive screenshot pass in Task 6 steps 4–6.

## What the workbench commit contains

- Shared full-page context and application header with live shift progress.
- A semantic, keyboard-operable ticket queue with priority, SLA, and cascade
  information.
- A restructured active-case view, command filtering, durable tool output, and
  conversation timeline.
- Restyled escalation, tier-2, after-action, knowledge-base, history, and shift
  views.
- Responsive master/detail behavior and reduced-motion handling in vanilla
  JavaScript.
- Server-side regression coverage for the new markup contracts and SSE payload.

The redesign deliberately does not change simulation, persistence, fault,
grading, persona, or tool behavior. Preserve the endpoint names, form field
names, HTMX targets, fault-leak boundaries, and SSE cadence called out in the
plan.

## Verification repeated at pickup

```text
UV_CACHE_DIR=.venv/uv-cache uv run pytest
1731 passed, 1 warning in 229.05s

uv run pylint src
Your code has been rated at 10.00/10 (exit 0)

uv run pylint tests \
  --disable=redefined-outer-name,unused-variable,protected-access,use-implicit-booleaness-not-comparison
Your code has been rated at 10.00/10 (exit 0)

git diff --check
clean
```

The warning is emitted by FastAPI's vendored `TestClient` import because the
installed Starlette version marks its `httpx` integration as deprecated; it does
not represent a failing project test.

## Browser-validation blocker in this environment

The application starts successfully at `http://127.0.0.1:8000`, but this
container has no browser installed. `npx playwright install chromium` was tried
and every browser download was rejected by the environment's proxy with HTTP
403. Debian's configured repositories also expose no Chromium candidate.
Consequently, no honest screenshots or claims about the live responsive pass
were made here.

On a browser-capable machine, resume at Task 6 step 4. Use a temporary database,
exercise the complete ticket workflow, and capture the five specified states at
390x844, 1024x768, 1440x900, and 2560x1440. Store disposable screenshots under
`output/playwright/helpdesk-workbench/`; do not commit them unless explicitly
requested.

## Review focus for the browser pass

1. Repeated `/events` arrivals refresh `#queue` without removing
   `.layout.ticket-open` or accelerating simulated time.
2. Changing the selected tool filters commands while submitting the unchanged
   `tool`, `command`, and `args` values.
3. Open-ticket HTML never displays a fault id, canonical title, or raw symptom
   structure.
4. Long reports, tool output, KB articles, and tables stay within their regions
   without horizontal viewport overflow.
5. Keyboard focus moves to `#ticket-heading` when a ticket opens and returns to
   the selected `.ticket-row` through `Back to queue`.
6. Reduced-motion emulation removes nonessential transitions and smooth
   scrolling.

## Older open threads

The Phase 2b catalog remains complete at 32 faults. These earlier follow-ups are
still intentionally open:

- The LM Studio persona path still needs verification on a machine running LM
  Studio; use `docs/verifying-lmstudio.md`.
- The deleted original design spec has not been restored. Its last version is
  recoverable with
  `git show dbcd2bb^:docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`.
- Cross-session history is available through `Store.history()` and
  `domain_stats()` with `all_sessions=True`, but no career-to-date view consumes
  it yet.
- The overlapping `is_present()` predicates documented in repository history
  remain deliberate; do not introduce a fault-id branch to disambiguate them.
