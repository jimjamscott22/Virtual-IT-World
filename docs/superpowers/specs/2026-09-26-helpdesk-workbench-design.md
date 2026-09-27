# Helpdesk Workbench UI Design

## Goal

Turn the existing functional web interface into a polished training simulator
that feels like credible internal helpdesk software, gives urgent work a clear
visual order, uses ultrawide space deliberately, and remains usable on a phone.

The redesign changes presentation and lightweight browser interaction only. It
does not change fault generation, grading, persistence, ticket state, SLA
calculation, persona behavior, or tool execution.

## Design direction

The interface is an IT operations workbench rather than a generic dashboard.
Its three working areas are the ticket queue, the active case, and the
technician workbench. The shift rail in the header is the single expressive
visual element; everything else stays quiet, dense enough for real work, and
legible enough for a learner.

## Visual system

### Color

- Operations navy: `#0D151C`
- Work surface: `#16222B`
- Raised surface: `#1E2E39`
- Primary text: `#E7EEF2`
- Signal blue: `#62AFC2`
- Status colors: amber `#E2A84F`, red `#E06B65`, green `#61B38B`

Status colors communicate priority, SLA state, warnings, and outcomes. Every
colored state also has a text label, so color is never the only signal.

### Type

- `"Segoe UI Variable", "Segoe UI", sans-serif` for interface text.
- `"Cascadia Mono", "Consolas", monospace` only for commands and tool output.
- Body copy stays below 80 characters per line in the active case.
- Labels use sentence case. Small metadata is not tracked-out or all caps.

### Shape and depth

- Borders separate working regions and encode hierarchy.
- Modest corner radii distinguish editable or raised surfaces from the fixed
  application frame.
- Shadows are reserved for transient overlays, not repeated across every
  section.
- Motion occurs only in response to actions, such as opening a ticket or
  revealing escalation feedback, and respects reduced-motion preferences.

## Information architecture

### Wide desktop

```text
+--------------------------------------------------------------------------+
| Virtual IT Support Center     09:00 ------o------ 17:00     KB  History   |
| Meridian Freight Co.                  388 min left          Shift summary  |
+------------------+--------------------------------+-----------------------+
| Ticket queue     | Active case                    | Technician workbench  |
|                  |                                |                       |
| P1  22 overdue   | Requester and triage           | Diagnostic tools      |
| Sandra W.        | Reported problem               | Command output         |
| Printer issue    | Conversation timeline          | Escalate / resolve     |
|                  |                                |                       |
| P2  due in 41    |                                |                       |
| Emil Novak       |                                |                       |
+------------------+--------------------------------+-----------------------+
```

- Queue: `clamp(22rem, 25vw, 29rem)`.
- Active case: flexible, with readable content constrained to a useful line
  length.
- Workbench: `clamp(20rem, 25vw, 28rem)`.
- The overall shell fills the viewport without stretching prose across it.

### Laptop

The queue and case remain side-by-side. The technician workbench moves below
the case content so controls do not become narrow or clipped.

### Mobile

The page uses a master-detail interaction. The queue is the initial view.
Selecting a ticket opens the ticket workspace and exposes a clear `Back to
queue` control. Forms stack to the viewport width, tables scroll inside their
own containers, and no page depends on horizontal viewport scrolling.

## Shared application shell

- The header contains the product name, organization, shift rail, remaining
  time, and links to Queue, Knowledge base, History, and Shift summary.
- The current location is conveyed with `aria-current="page"` and visible
  styling.
- The existing degraded-persona and shift-over banners remain live SSE-driven
  states, restyled to fit the shell.
- The shift rail begins at 09:00 and ends at 17:00. Its progress is calculated
  by the server and updated by the existing SSE connection.

## Ticket queue

Each ticket is a keyboard-operable button with:

- ticket number;
- explicit priority label;
- requester name;
- a two- or three-line report preview;
- `Due in N min` or `N min overdue`;
- `Related incident C1` when the ticket belongs to a cascade.

Priority and SLA state determine the left-edge marker and status text. The
selected ticket uses the raised surface and signal-blue focus treatment.

When the queue is empty, the interface explains that new work arrives during
the shift rather than showing an unexplained blank region.

## Active case

The case is divided into semantic regions without forcing a linear workflow:

1. Requester identity and reported problem.
2. Triage-priority control.
3. Conversation timeline.
4. Technician workbench.
5. Escalation and resolution actions.

The user report is presented as the opening item in the case rather than as a
generic card. Technician and requester chat turns are visually distinct and
retain speaker labels in text.

## Technician workbench

- The tool and command controls receive visible labels.
- Selecting a tool filters the command selector to commands belonging to that
  tool; the submitted `tool`, `command`, and `args` fields remain unchanged.
- Tool output uses the mono font in a terminal-like, scrollable region.
- Escalation is secondary to continued investigation but remains clearly
  available.
- `Close ticket` is the primary terminal action and keeps the existing sole
  `resolved` disposition.

## Feedback and reports

- Tier-2 bounce and acceptance states receive explicit status treatments.
- After-action reports lead with the verdict, then the outcome summary,
  diagnostic path, wasted calls, collateral damage, KB suggestions, and tier-2
  notes.
- Success, warning, and failure treatments always include words and do not rely
  on hue alone.
- Shift summary and history use the same typography, navigation, status chips,
  and responsive table conventions as the main workbench.

## Empty, degraded, and failure states

- Empty queue: explain that tickets will arrive while the shift is running.
- No selected ticket: direct the player to choose the most urgent ticket and
  begin with the user report.
- No KB results: suggest changing the search terms.
- Model degraded: state that scripted replies are active and the drill remains
  playable.
- Shift over: state that arrivals stopped and existing tickets remain workable.

## Accessibility and responsiveness

- Visible `:focus-visible` treatment on every interactive element.
- Native buttons, labels, headings, navigation landmarks, and tables remain
  semantically correct.
- Minimum interactive height of 40px where the layout permits it.
- Status meanings are available as text.
- `prefers-reduced-motion: reduce` disables nonessential scrolling and
  transitions.
- The interface is validated at 390x844, 1024x768, 1440x900, and 2560x1440.

## Deliberate exclusions

- No frontend framework, CSS framework, icon library, external font, or CDN.
- No simulation or backend-domain behavior changes.
- No dashboard of generic statistic cards.
- No decorative gradients, animated ambient effects, or repeated shadows.
- No commit or push unless explicitly requested.
