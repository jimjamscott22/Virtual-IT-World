# Helpdesk Workbench UI Implementation Plan

> **For agentic workers:** Implement sequentially in the current workspace. Do
> not use subagents for this repository. Steps use checkbox (`- [x]`) syntax for
> tracking.

**Goal:** Build the approved polished helpdesk-workbench interface across the
queue, active ticket, tools, feedback, knowledge base, history, and shift pages.

**Architecture:** Keep FastAPI, Jinja, HTMX, and the existing route contracts.
Add one shared shell-context helper, one shared header partial, and one small
vanilla-JavaScript file for SSE presentation, tool filtering, and mobile
master-detail behavior. Restructure templates semantically and replace the
minimal stylesheet with a responsive token-based system; do not change domain
or session behavior.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, HTMX, vanilla JavaScript, CSS.

**Spec:** `docs/superpowers/specs/2026-09-26-helpdesk-workbench-design.md`

## Global Constraints

- Preserve every current endpoint, form field name, HTMX target, ticket state
  transition, fault-leak safeguard, and SSE timing behavior.
- Use no new runtime dependency, frontend framework, external font, icon
  library, CDN, or image asset.
- Keep tools isolated from faults and world models; this work does not alter
  tool or environment architecture.
- Implement directly, then add or update tests; do not use a test-first loop.
- Work sequentially without subagents.
- Leave all changes uncommitted unless the user explicitly asks for a commit.
- Preserve the existing untracked `.playwright-cli/` and `output/` artifacts
  until the user approves their removal.

## Review Focus

- Repeated SSE queue refreshes must not remove the current mobile detail view or
  make simulated time advance faster.
- Tool filtering must still submit the exact `tool`, `command`, and `args`
  values expected by `POST /ticket/{id}/tool`.
- Fault ids and canonical titles must remain absent from every open-ticket
  template.
- Long reports, long tool output, and the full command catalog must wrap or
  scroll inside their region without widening the viewport.
- Keyboard and reduced-motion users must be able to open a ticket, return to the
  queue, use tools, chat, escalate, and close it.

---

### Task 1: Shared shell, navigation, and live shift rail

**Files:**
- Create: `src/vitsc/web/context.py`
- Create: `src/vitsc/web/templates/_app_header.html`
- Create: `src/vitsc/web/static/app.js`
- Modify: `src/vitsc/web/templates/base.html`
- Modify: `src/vitsc/web/templates/layout.html`
- Modify: `src/vitsc/web/routes/queue.py`
- Modify: `src/vitsc/web/routes/kb.py`
- Modify: `src/vitsc/web/routes/close.py`
- Modify: `src/vitsc/web/routes/shift.py`
- Modify: `src/vitsc/web/routes/events.py`
- Modify: `src/vitsc/web/static/app.css`
- Test: `tests/test_web_events.py`
- Test: `tests/test_web_queue.py`
- Test: `tests/test_web_kb.py`
- Test: `tests/test_web_close.py`
- Test: `tests/test_shift.py`

**Interfaces:**
- Produces: `shell_context(request: Request, **values: object) -> dict[str, object]`.
- Produces: SSE key `shift_progress`, a number from `0.0` to `100.0`.
- Produces: `window.VITSC` initialization behavior from `/static/app.js`.
- Consumes: `AppSession.shift.elapsed()`, `AppSession.shift.minutes`, and the
  existing `build_payload()` response.

- [x] **Step 1: Add the shared shell context**

  Create `vitsc.web.context.shell_context` so every full-page route receives
  consistent header state without copying calculations:

  ```python
  from fastapi import Request

  def shell_context(request: Request, **values: object) -> dict[str, object]:
      session = request.app.state.session
      now = session.env.world.clock
      progress = 100 * session.shift.elapsed(now) / session.shift.minutes
      return {
          "degraded": session.degraded,
          "shift_remaining": session.shift.remaining(now),
          "shift_over": session.shift.is_over(now),
          "shift_progress": round(progress, 2),
          **values,
      }
  ```

  Use this helper in `/`, `/kb`, `/kb/{article_id}`, `/history`, and `/shift`.
  Partial routes keep their focused contexts.

- [x] **Step 2: Add the shared header partial and semantic page shell**

  `_app_header.html` must contain a brand link, organization name, shift rail,
  remaining-time text, and Queue/Knowledge base/History/Shift summary links.
  Determine the active link from `request.url.path` and add
  `aria-current="page"`. In `layout.html`, retain the existing banner ids and
  the `#queue`/`#detail` HTMX targets.

  ```html
  <header class="app-header">
    <a class="app-brand" href="/">
      <strong>Virtual IT Support Center</strong>
      <span>Meridian Freight Co.</span>
    </a>
    <div class="shift-rail" style="--shift-progress: {{ shift_progress }}%">
      <span>09:00</span><span class="shift-track" aria-hidden="true"></span><span>17:00</span>
      <a href="/shift"><strong id="shift-remaining">{{ shift_remaining }}</strong> min left</a>
    </div>
    <nav aria-label="Primary">...</nav>
  </header>
  ```

- [x] **Step 3: Move browser behavior out of the template**

  Move the existing EventSource code from `base.html` into `app.js` without
  changing its endpoint or update cadence. Add these focused functions:

  ```javascript
  function updateShift(payload) { /* text, rail percentage, end banner */ }
  function updateSlas(activeTickets) { /* existing countdown behavior */ }
  function initializeToolPicker(root = document) { /* Task 3 fills this */ }
  function initializeMasterDetail() { /* Task 5 fills this */ }
  ```

  `base.html` loads HTMX first and `/static/app.js` with `defer`. Missing
  `EventSource` remains a safe no-op.

- [x] **Step 4: Expose progress through the existing SSE payload**

  Add `shift_progress` to `build_payload()` using the same bounded
  `Shift.elapsed()` calculation as initial rendering. Keep `shift_remaining`,
  `shift_over`, `degraded`, `arrivals`, and `active` unchanged.

- [x] **Step 5: Establish the CSS tokens and application frame**

  Replace the current root palette with the approved tokens, add the Segoe UI
  Variable stack, normalize controls, add visible focus styles, and implement
  the header/shift rail/application-frame layout. Preserve the warning banners'
  `[hidden]` behavior.

- [x] **Step 6: Update route-level tests after implementation**

  Extend existing tests to assert that full pages render `.app-header`, the
  four navigation destinations, and the initial shift progress. Extend
  `test_web_events.py` with:

  ```python
  def test_payload_reports_bounded_shift_progress(session):
      payload = build_payload(session, session.env.world.clock, [])
      assert payload["shift_progress"] == 0.0
      later = session.env.world.clock + timedelta(minutes=session.shift.minutes)
      assert build_payload(session, later, [])["shift_progress"] == 100.0
  ```

- [x] **Step 7: Run focused verification**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.venv/uv-cache'
  uv run pytest tests/test_web_events.py tests/test_web_queue.py tests/test_web_kb.py tests/test_web_close.py tests/test_shift.py -q
  ```

  Expected: all selected tests pass and no full-page route raises a template
  error.

### Task 2: Scannable, keyboard-operable ticket queue

**Files:**
- Modify: `src/vitsc/web/templates/_queue.html`
- Modify: `src/vitsc/web/templates/layout.html`
- Modify: `src/vitsc/web/static/app.css`
- Test: `tests/test_web_queue.py`

**Interfaces:**
- Consumes: `Ticket.system_priority`, `Ticket.cascade_id`,
  `Ticket.is_overdue(now)`, `Ticket.deadline`, and `Ticket.report_text`.
- Produces: `.ticket-row`, `[data-ticket-id]`, `[data-priority]`, and
  `[data-overdue]` hooks used by CSS and Task 5's mobile interaction.

- [x] **Step 1: Replace clickable divs with native buttons**

  Preserve `hx-get`, `hx-target="#detail"`, and `hx-swap="innerHTML"`, but
  render each ticket as `button type="button"`. Use semantic groups for ticket
  identity, requester, preview, cascade relationship, and SLA.

  ```html
  <button type="button" class="ticket-row"
          data-ticket-id="{{ t.id }}"
          data-priority="{{ t.system_priority.value }}"
          data-overdue="{{ 'true' if t.is_overdue(now) else 'false' }}"
          hx-get="/ticket/{{ t.id }}" hx-target="#detail" hx-swap="innerHTML">
    <span class="ticket-row__meta">#{{ t.id }} · P{{ t.system_priority.value }}</span>
    <strong class="ticket-row__person">{{ t.persona.name }}</strong>
    <span class="ticket-row__preview">{{ t.report_text }}</span>
    {% if t.cascade_id %}<span class="incident-chip">Related incident {{ t.cascade_id }}</span>{% endif %}
    <span class="ticket-row__sla" id="sla-{{ t.id }}">...</span>
  </button>
  ```

- [x] **Step 2: Add useful queue and workspace empty states**

  Queue copy: `No open tickets. New work will appear here during the shift.`
  Detail copy: `Choose the most urgent ticket to begin. Start with the user's
  report, then investigate before making changes.`

- [x] **Step 3: Style priority, overdue, cascade, hover, focus, and selection**

  Use a left-edge marker for priority, explicit red overdue text, an outlined
  incident chip, line clamping for report previews, and a raised selected state.
  Do not use color as the only indication.

- [x] **Step 4: Update queue tests after implementation**

  Extend `tests/test_web_queue.py` to assert:

  ```python
  assert body.count('class="ticket-row"') == len(session.queue.active())
  assert 'type="button"' in body
  assert 'data-overdue=' in body
  assert "Related incident C1" in cascade_body
  ```

  Keep the existing fault-title leak test unchanged.

- [x] **Step 5: Run focused verification**

  Run `uv run pytest tests/test_web_queue.py -q` with the workspace-local uv
  cache. Expected: all queue and leak-prevention checks pass.

### Task 3: Active case, conversation, and technician workbench

**Files:**
- Modify: `src/vitsc/web/templates/_ticket.html`
- Modify: `src/vitsc/web/templates/_tools.html`
- Modify: `src/vitsc/web/templates/_toolout.html`
- Modify: `src/vitsc/web/templates/_chat.html`
- Modify: `src/vitsc/web/static/app.js`
- Modify: `src/vitsc/web/static/app.css`
- Test: `tests/test_web_queue.py`
- Test: `tests/test_web_tools.py`
- Test: `tests/test_persona_binding.py`

**Interfaces:**
- Consumes: existing form fields `priority`, `tool`, `command`, `args`, and
  `message` without renaming them.
- Produces: `.case-workspace`, `.case-main`, `.technician-workbench`,
  `select[data-tool-picker]`, and `select[data-command-picker]`.
- Preserves: `#tools`, `#toolout`, and `#chat` HTMX targets.

- [x] **Step 1: Restructure the ticket into semantic working regions**

  Add a desktop-hidden `.back-to-queue` button, a case header, requester block,
  report blockquote, labeled triage form, conversation section, and workbench
  aside. Keep the comment forbidding direct rendering of `fault_id`, canonical
  title, or raw symptoms.

- [x] **Step 2: Improve the tool form without changing its POST contract**

  Give every control a label. Add `data-tool-picker` to the tool selector and
  `data-command-picker` to the command selector. Give each command option a
  `data-tool="{{ t.name }}"` attribute while keeping its submitted value equal
  to the command name only.

  ```html
  <option value="{{ cmd }}" data-tool="{{ t.name }}">{{ cmd }}</option>
  ```

- [x] **Step 3: Filter command options in vanilla JavaScript**

  `initializeToolPicker(root)` must disable and hide options that do not match
  the selected tool, select the first matching command, and rerun after HTMX
  swaps:

  ```javascript
  document.addEventListener("htmx:afterSwap", (event) => {
    initializeToolPicker(event.target);
  });
  ```

  Reinitialization must be idempotent and must not submit or run a tool.

- [x] **Step 4: Present tool output as a durable console history**

  Render each call with its tool, command, arguments, success state, and output
  inside the existing `#toolout`. Long output scrolls inside the console and
  preserves whitespace. Empty output invites the technician to choose a tool
  and run a diagnostic.

- [x] **Step 5: Present chat as a conversation timeline**

  Retain visible speaker names and the existing POST target. Style technician,
  user, and tier-2 turns distinctly without speech-bubble decoration on every
  line. Make the input and `Send message` action full-width at narrow sizes.

- [x] **Step 6: Update focused tests after implementation**

  Assert tool and command labels, `data-tool` mappings, and unchanged POST
  behavior in `tests/test_web_tools.py`. Keep the existing tests proving tool
  logging and leak-term scrubbing. In `tests/test_web_queue.py`, assert that an
  open ticket still contains no fault id or canonical title after the markup
  restructure.

- [x] **Step 7: Run focused verification**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.venv/uv-cache'
  uv run pytest tests/test_web_queue.py tests/test_web_tools.py tests/test_persona_binding.py -q
  ```

  Expected: tool execution, chat, logging, and leak protection remain green.

### Task 4: Escalation, resolution, after-action, and secondary pages

**Files:**
- Modify: `src/vitsc/web/templates/_escalate.html`
- Modify: `src/vitsc/web/templates/_tier2.html`
- Modify: `src/vitsc/web/templates/_afteraction.html`
- Modify: `src/vitsc/web/templates/_kb.html`
- Modify: `src/vitsc/web/templates/history.html`
- Modify: `src/vitsc/web/templates/shift.html`
- Modify: `src/vitsc/web/static/app.css`
- Test: `tests/test_web_escalate.py`
- Test: `tests/test_web_close.py`
- Test: `tests/test_web_kb.py`
- Test: `tests/test_shift.py`

**Interfaces:**
- Consumes: existing escalation and close endpoints and their exact form fields.
- Consumes: `AfterAction`, `Grade`, `ShiftReport`, closed records, KB articles,
  and the shared shell context from Task 1.
- Produces: shared `.status-panel`, `.data-table-wrap`, `.verdict`, and
  `.page-content` presentation classes.

- [x] **Step 1: Separate escalation from resolution visually**

  Keep the reviewed escalation path as the only escalation path. Give the note
  textarea supporting copy, keep `note` unchanged, and label the tier-2 bounce
  as `Returned by tier-2`. Keep `Close ticket` primary and `Escalate` secondary.

- [x] **Step 2: Reorder after-action content into a readable review**

  Lead with verdict and root cause, then summary metrics, shortest diagnostic
  path, wasted calls, collateral damage, KB suggestions, cascade note, and
  tier-2 outcome. Do not change the conditions that decide whether a section is
  rendered.

- [x] **Step 3: Apply the shared shell to KB, history, and shift pages**

  Include `_app_header.html` on all three. Keep current endpoints and data.
  Wrap data tables in `.data-table-wrap`, convert the KB body from an unbounded
  `<pre>` into a styled preformatted article region, and add useful empty-result
  copy: `No matching articles. Try a broader term or search for the symptom.`

- [x] **Step 4: Update page and flow tests after implementation**

  Extend existing tests to assert the reviewed escalation URL is still present,
  the unreviewed disposition is still absent, the new tier-2 label appears on a
  bounce, the KB/history/shift pages contain the shared navigation, and all
  existing report strings still render.

- [x] **Step 5: Run focused verification**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.venv/uv-cache'
  uv run pytest tests/test_web_escalate.py tests/test_web_close.py tests/test_web_kb.py tests/test_shift.py -q
  ```

  Expected: escalation ownership, after-action grading, KB access, history, and
  shift reporting behave exactly as before.

### Task 5: Responsive master-detail behavior and accessibility finish

**Files:**
- Modify: `src/vitsc/web/static/app.js`
- Modify: `src/vitsc/web/static/app.css`
- Modify: `src/vitsc/web/templates/layout.html`
- Modify: `src/vitsc/web/templates/_ticket.html`
- Test: `tests/test_web_queue.py`

**Interfaces:**
- Consumes: `.ticket-row[data-ticket-id]`, `#queue`, `#detail`, and
  `.back-to-queue` from Tasks 2 and 3.
- Produces: `.ticket-open` state on `.layout` at narrow viewport widths.
- Preserves: desktop simultaneous queue/detail visibility.

- [x] **Step 1: Implement responsive layout breakpoints**

  At widths above 1200px, render queue, case, and workbench as three meaningful
  regions. Between 761px and 1200px, keep queue beside the case and move the
  workbench below it. At 760px and below, show the queue or the detail view,
  never both squeezed side-by-side.

- [x] **Step 2: Add mobile master-detail interaction**

  On a successful ticket-detail HTMX swap, add `.ticket-open` to `.layout`,
  record the selected ticket id, and focus the ticket heading. The Back to queue
  button removes the class and focuses the previously selected queue button.
  Queue refreshes must not clear the layout state.

- [x] **Step 3: Add accessibility and reduced-motion safeguards**

  Ensure focus is visible, headings remain hierarchical, form labels remain
  associated, status is not color-only, tables scroll within their wrapper, and
  long content uses `overflow-wrap`. Under `prefers-reduced-motion: reduce`,
  remove smooth scrolling and nonessential transitions.

- [x] **Step 4: Add structural regression checks after implementation**

  Extend `tests/test_web_queue.py` to assert the Back to queue control and ticket
  heading focus target exist. These server tests cover the contract used by the
  browser behavior; the behavior itself is covered by the live browser pass in
  Task 6.

- [x] **Step 5: Run focused verification**

  Run `uv run pytest tests/test_web_queue.py -q` with the workspace-local uv
  cache. Expected: all template contracts and leak checks pass.

### Task 6: Full regression and visual validation

**Files:**
- Verify only: all files changed in Tasks 1-5
- Artifacts: `output/playwright/helpdesk-workbench/`

**Interfaces:**
- Consumes: the complete UI and all existing application behavior.
- Produces: screenshots and a concise verification record in the final handoff;
  no application interface is added.

- [x] **Step 1: Run the full automated suite**

  Run:

  ```powershell
  $env:UV_CACHE_DIR='.venv/uv-cache'
  uv run pytest
  ```

  Expected baseline from the current handoff: 1662 tests pass and none are
  xfailed, plus any new assertions added by this plan.

- [x] **Step 2: Run both lint commands and inspect exit codes**

  Run without pipes:

  ```powershell
  uv run pylint src
  uv run pylint tests --disable=redefined-outer-name,unused-variable,protected-access,use-implicit-booleaness-not-comparison
  ```

  Expected: both exit with code 0. Do not infer success from the rounded score.

- [x] **Step 3: Run whitespace and working-tree checks**

  Run `git diff --check` and `git status --short`. Classify the pre-existing
  `.playwright-cli/` and `output/` paths separately from implementation files.

- [ ] **Step 4: Validate the primary workflow in a real browser**

  Start the app with a workspace-local temporary SQLite database. At minimum:

  1. Open a ticket by mouse and keyboard.
  2. Change triage priority.
  3. Switch tools and confirm commands filter correctly.
  4. Run one diagnostic and inspect long output.
  5. Ask the user a question.
  6. Open and cancel or submit escalation.
  7. Resolve a ticket and inspect the after-action.
  8. Visit KB, History, and Shift summary.
  9. Confirm queue refresh and SSE countdowns continue during the workflow.

- [ ] **Step 5: Capture and inspect responsive screenshots**

  Capture queue, open-ticket, tool-output, after-action, and secondary-page
  states at 390x844, 1024x768, 1440x900, and 2560x1440. Confirm no horizontal
  viewport overflow, clipped controls, unreadable line lengths, or loss of
  keyboard focus. Check reduced-motion emulation once.

- [ ] **Step 6: Self-review against the approved spec**

  Compare the implementation to every section of
  `docs/superpowers/specs/2026-09-26-helpdesk-workbench-design.md`. Remove one
  nonfunctional decoration if the result feels visually busy. Report any
  unimplemented requirement rather than implying complete coverage.

## Self-review record

- Spec coverage: every design section maps to Tasks 1-6.
- Completeness scan: every implementation step names its concrete behavior,
  files, interfaces, and verification command.
- Type consistency: `shift_progress`, `data-tool-picker`,
  `data-command-picker`, `.ticket-open`, and `shell_context` use one name
  throughout.
- Review focus: each listed risk has an automated contract check, browser
  validation step, or both.
- Repository constraints: the plan is sequential, implementation-first,
  uncommitted by default, and does not use subagents.
