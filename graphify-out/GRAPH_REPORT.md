# Graph Report - .  (2026-09-12)

## Corpus Check
- 131 files · ~68,865 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1352 nodes · 3595 edges · 77 communities (66 shown, 11 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 113 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- HTMX Static Bundle
- Grading & Tool Consoles
- Environment Protocol I/O Types
- SimulatedEnvironment & Ticket Priority
- Environment Protocol & AD Console
- Distractor Protocol
- Cached Credentials Fault
- App Bootstrap & Persona Config
- Fixed Shift & Shift Report
- Fault Scheduler & Ticket Queue
- Ticket, Priority & FastAPI App
- Queue Scheduler Tests
- Knowledge Base Loader
- Fault Registry Conformance Tests
- Environment/Fault Base Protocols
- LMStudioPersona Client
- Tier-2 Escalation Review
- Mail Fault Conformance Tests
- Distractor Registry Tests
- Persona Degradation & Templates
- Baseline & Invariant Checking
- After-Action Store & Grade
- AppSession & Degraded State
- Persona Binding Tests
- External Forwarding Rule Fault
- Persona Prompts & Chat Turns
- End-to-End HTTP Tests
- LM Studio Client Build
- Distractor Catalog Tests
- No DHCP Lease Fault
- SSE Events & Web Templates
- Account Locked Fault
- Ticket Persona Binding & Escalation
- Shift Report Build
- Disk Full Fault
- Cascade & Escalate Web Tests
- Persona Card Templates
- Store Persistence Tests
- Phase 2a Mail Plan Notes
- Leak Term Scrubbing
- Difficulty-Weighted Fault Choice
- Mail Fault Handoff Notes
- Phase 2a Handoff Document
- Escalation Web Routes
- Meridian Company Seed Data
- After-Action Report & Grading
- Fault Protocol Base
- Ticket Close Web Tests
- Queue Web Tests
- Tools Web Tests
- PowerShell Tools & Web Routes
- Architecture Import Guards
- Cascade Faults Design Notes
- Phase 2b Catalog Plan Notes
- KB Web Tests
- Offboarded Reactivation Fault
- Spooler Stopped Fault
- Wrong Driver Fault
- Persona Protocol Design Notes
- Simulated Tier-2 Design Notes
- Cached Credentials Design Notes
- Test Suite Fixtures
- Distractor Protocol Design Notes
- Pylint CI Workflow
- Data Package Init
- vitsc Package Init
- Persona Package Init
- Session Package Init
- Environment Protocol Note
- Project Metadata

## God Nodes (most connected - your core abstractions)
1. `Placement` - 136 edges
2. `World` - 122 edges
3. `load_world()` - 85 edges
4. `SimulatedEnvironment` - 80 edges
5. `Action` - 78 edges
6. `Query` - 70 edges
7. `get_fault()` - 58 edges
8. `grade_ticket()` - 49 edges
9. `setup()` - 46 edges
10. `Ticket` - 43 edges

## Surprising Connections (you probably didn't know these)
- `KB: A workstation that's slow or acting strange` --semantically_similar_to--> `Phase 2b: Catalog Breadth Plan`  [INFERRED] [semantically similar]
  src/vitsc/data/kb/endpoint-slow-or-failing.md → docs/superpowers/plans/2026-08-14-phase-2b-catalog.md
- `test_no_template_leaks_the_canonical_title()` --calls--> `get_fault()`  [INFERRED]
  tests/test_web_queue.py → src/vitsc/faults/registry.py
- `test_chat_reply_never_contains_a_leak_term()` --calls--> `get_fault()`  [INFERRED]
  tests/test_web_tools.py → src/vitsc/faults/registry.py
- `ad.cached_credentials_expired fault` --semantically_similar_to--> `KB: Reading an account that can't sign in`  [INFERRED] [semantically similar]
  docs/superpowers/plans/2026-08-14-phase-2b-catalog.md → src/vitsc/data/kb/identity-cannot-sign-in.md
- `KB: Before you touch anything (triage first questions)` --semantically_similar_to--> `Cascade faults (reporters/cascade_id)`  [INFERRED] [semantically similar]
  src/vitsc/data/kb/general-triage-first-questions.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Mail domain implementation flow (world model -> env kinds -> tool -> faults)** — plan_2a_task12_mail_world_model, plan_2a_task13_mail_query_action_kinds, plan_2a_task14_mail_console_tool, plan_2a_task15_reference_mail_faults [EXTRACTED 0.90]
- **Task 15 implemented twice in parallel (PR #9 and PR #10) reconciled into mail.py** — docs_handoff_pr9, docs_handoff_pr10, docs_handoff_mail_mailbox_full, docs_handoff_mail_external_forwarding_rule [EXTRACTED 0.90]
- **Three Phase 2b groundwork questions settled before Task 1** — plan_2b_estate_settled_before_task1, plan_2b_fixed_shift_settled, plan_2b_difficulty_scheduling_settled [EXTRACTED 0.85]
- **Ticket workspace: detail + chat + tools + escalate compose the working ticket view** — src_vitsc_web_templates__ticket_template, src_vitsc_web_templates__chat_template, src_vitsc_web_templates__tools_template, src_vitsc_web_templates__toolout_template, src_vitsc_web_templates__escalate_template [EXTRACTED 0.90]
- **SSE tick loop drives SLA countdown, shift banner, and degraded banner across base/index/queue** — src_vitsc_web_templates_base_template, src_vitsc_web_templates_index_template, src_vitsc_web_templates__queue_template, src_vitsc_web_routes_events_events [EXTRACTED 0.90]
- **Escalation flow: escalate form -> tier-2 review -> bounce/accept -> after-action** — src_vitsc_web_templates__escalate_template, src_vitsc_web_routes_escalate_escalate_ticket, src_vitsc_web_templates__tier2_template, src_vitsc_web_templates__afteraction_template [INFERRED 0.85]

## Communities (77 total, 11 thin omitted)

### Community 0 - "HTMX Static Bundle"
Cohesion: 0.08
Nodes (102): A(), ae(), ar(), at(), B(), be(), br(), bt() (+94 more)

### Community 1 - "Grading & Tool Consoles"
Cohesion: 0.07
Nodes (73): HTMLResponse, build_after_action(), duplicate_mutations(), grade_ticket(), How many times an identical mutating call was repeated beyond its first use.…, ADConsole, BaseModel, ToolCall (+65 more)

### Community 2 - "Environment Protocol I/O Types"
Cohesion: 0.05
Nodes (45): Action, ActionResult, Observation, BaseModel, Query, A read against the environment. Never mutates., A write against the environment., DNS resolution, honouring the querying machine's own resolvers. (+37 more)

### Community 3 - "SimulatedEnvironment & Ticket Priority"
Cohesion: 0.05
Nodes (70): The v1 backend: an in-memory world model. Handlers read and write `self.world`…, priority_for(), The *system's* triage call, which the player's own is graded against. Impact…, get_tool(), ADGroup, ADUser, EventEntry, Machine (+62 more)

### Community 4 - "Environment Protocol & AD Console"
Cohesion: 0.06
Nodes (35): Environment, Protocol, DispatchTool, Protocol, Player-facing tool framework. Tools are thin wrappers over `env.read()` /…, Shared dispatch for every tool: a read map, a write map, and a target.…, Return (kind, 'read'|'write'). Matching is case-insensitive., Tool (+27 more)

### Community 5 - "Distractor Protocol"
Cohesion: 0.08
Nodes (20): Distractor, Protocol, Random, Honest distractors. A distractor is a real, truthfully-reported anomaly that is…, ModeratelyLowDisk, OfflineUnusedPrinter, OldDiskWarning, Random (+12 more)

### Community 6 - "Cached Credentials Fault"
Cohesion: 0.08
Nodes (11): CachedCredentialsExpired, Random, A workstation's cached domain sign-in lets a user reach their desktop even when…, ShareGroupRemoved, _workstations(), _mailbox_owners(), _print_servers(), Random (+3 more)

### Community 7 - "App Bootstrap & Persona Config"
Cohesion: 0.11
Nodes (26): main(), `uv run python -m vitsc` — the normal way to start the drill. Uses…, create_app(), datetime, Path, A typo in the environment must not take the drill down., The whole drill must survive nothing running on localhost., Template output, but reporting itself as degraded. (+18 more)

### Community 8 - "Fixed Shift & Shift Report"
Cohesion: 0.09
Nodes (19): datetime, The fixed shift, and the report that closes it. A drill needs an end. Without…, One fixed-length working day on the simulated clock., Simulated minutes worked, never negative and never past the end., Shift, parametrize, The fixed shift: when arrivals stop, and what the day added up to., Built from the store's own rows, so it cannot disagree with history. (+11 more)

### Community 9 - "Fault Scheduler & Ticket Queue"
Cohesion: 0.12
Nodes (17): forgive(), datetime, Random, The fault scheduler and the ticket queue. This is what makes a session…, Who phones this in, for a fault that does not declare its own reporters. User…, Who actually gets a ticket for this fault instance. `fault.reporters()` names…, Apply `fault` at `placement` and build one ticket per reporter. Shared by…, The first ticket of whatever `open_ticket()` deals, for callers that only ever… (+9 more)

### Community 10 - "Ticket, Priority & FastAPI App"
Cohesion: 0.18
Nodes (21): FastAPI, IntEnum, Priority, Lower is more urgent, so priorities sort naturally., post, Request, send_message(), close_ticket() (+13 more)

### Community 11 - "Queue Scheduler Tests"
Cohesion: 0.08
Nodes (21): _dealt(), make_queue(), fixture, parametrize, queue(), One arrival, one fault+placement — counted per *arrival*, not per ticket. A…, Closing a ticket without fixing it must not re-deal the same fault., The arrival *interval* is what this pins down. Not the ticket count: one… (+13 more)

### Community 12 - "Knowledge Base Loader"
Cohesion: 0.15
Nodes (20): get_article(), load_articles(), _parse(), Loads the original-content knowledge base from `vitsc/data/kb/*.md`. Each…, search_articles(), Article, BaseModel, A single knowledge-base page: procedure, not an answer key. (+12 more)

### Community 13 - "Fault Registry Conformance Tests"
Cohesion: 0.10
Nodes (24): all_faults(), FaultBase supplies the default, so this is a retrofit check., test_every_fault_declares_reporters(), fault_cases(), parametrize, Conformance harness for the whole fault catalog. The failure mode of this…, The ten v1 faults, plus what Phase 2a has added to that set since. The name is…, One per reason a ticket is not yours: it needs authorisation, it needs… (+16 more)

### Community 14 - "Environment/Fault Base Protocols"
Cohesion: 0.23
Nodes (15): The swap point. Everything above this boundary — tools, faults, session, web —…, bind(), FaultBase, _machine_key(), _printer_key(), BaseModel, Fault declarations. `is_present()` is the single source of truth for both "is…, Replace placement sentinels (`{placement}`, `{machine}`, `{group}`,… (+7 more)

### Community 15 - "LMStudioPersona Client"
Cohesion: 0.13
Nodes (13): setter, LMStudioPersona, A copy scrubbing this ticket's vocabulary, sharing everything else. A copy…, DeadClient, The technician is the model's 'user'; the persona is the 'assistant'., Mimics the surface of openai.OpenAI that LMStudioPersona uses., StubClient, test_a_clean_first_reply_costs_only_one_call() (+5 more)

### Community 16 - "Tier-2 Escalation Review"
Cohesion: 0.17
Nodes (21): bind_query(), Replace placement sentinels in a diagnostic query the same way `bind` does., _evidence_targets(), _has_evidence(), BaseModel, The simulated tier-2 queue. Deterministic and template-driven on purpose. The…, What a usable note could plausibly mention. `escalation_evidence` is the…, review_escalation() (+13 more)

### Community 17 - "Mail Fault Conformance Tests"
Cohesion: 0.11
Nodes (21): broken(), parametrize, Specifics for the mail domain's two reference faults. The conformance harness…, Same encoding `endpoint.failing_disk` uses: escalate-correct plus an empty…, A world with the fault applied, plus its placement and an environment., Raise the quota or reduce the usage — both are real answers., Neither path is the 'real' one — the gate is world state, not a button., The gate reads the world, so a fix that does not actually help fails. (+13 more)

### Community 18 - "Distractor Registry Tests"
Cohesion: 0.13
Nodes (14): clean_registry(), fixture, Random, Unit coverage for the distractor protocol and registry. The conformance harness…, `Distractor` is runtime_checkable, so this is a real structural check., Two distractors sharing an id would make one of them unreachable., Task 3 shipped the mechanism with an empty catalog on purpose; Task 4 fills it.…, StubDistractor (+6 more)

### Community 19 - "Persona Degradation & Templates"
Cohesion: 0.14
Nodes (14): _Degradation, The one degraded flag an origin persona shares with all its bindings.…, _quoted_error(), The model-free persona. Used whenever LM Studio is unavailable, and by every…, Report the on-screen text without stacking two 'It says' prefixes. Most faults…, Symptom-derived responses, matched on keywords in the question., Itself. Every sentence is a symptom field or fixed connective text, so there is…, TemplatePersona (+6 more)

### Community 20 - "Baseline & Invariant Checking"
Cohesion: 0.18
Nodes (18): Baseline, capture_baseline(), check_invariants(), BaseModel, Baseline capture and invariant checking. This is what gives wrong fixes teeth.…, fixture, The capture-after-apply guarantee has to hold for DNS like everything else.…, test_disabling_an_account_is_a_violation() (+10 more)

### Community 21 - "After-Action Store & Grade"
Cohesion: 0.20
Nodes (12): Connection, AfterAction, BaseModel, Grade, BaseModel, ClosedRecord, DomainStat, BaseModel (+4 more)

### Community 22 - "AppSession & Degraded State"
Cohesion: 0.14
Nodes (15): AppSession, BaseModel, A single in-process session, not a per-request one — there is exactly one…, Whether the player is reading template text rather than model text. Read…, advance_clock_if_due(), build_payload(), datetime, Advance the shared world clock at most once per `TICK_SECONDS` of real time, no… (+7 more)

### Community 23 - "Persona Binding Tests"
Cohesion: 0.13
Nodes (12): DeadClient, Degradation is session state, so it has to travel back to the origin. The queue…, Returns whatever it is told to, and records the prompts it saw., Layer 3 filters output. Telling the model the forbidden word hands it the…, Nothing listening on localhost., StubClient, test_a_bindings_fallback_marks_the_origin_degraded(), test_binding_does_not_mutate_the_original() (+4 more)

### Community 24 - "External Forwarding Rule Fault"
Cohesion: 0.13
Nodes (8): ExternalForwardingRule, _is_external(), _mailbox(), MailboxFull, Random, The placement's mailbox, or a loud failure. `placements()` only ever returns…, The clearest demonstration in the catalog that the gate is world state, not a…, Escalate-correct because *acting* is the mistake: deleting the rule destroys…

### Community 25 - "Persona Prompts & Chat Turns"
Cohesion: 0.15
Nodes (10): ChatTurn, PersonaCard, BaseModel, Who is on the other end of the ticket. Derived from AD, never from the fault., build_system_prompt(), The system prompt handed to a local model. Everything the model is told about…, Answer only from the symptom fields; deflect everything else. `history` is…, test_literacy_one_forbids_jargon_in_the_prompt() (+2 more)

### Community 26 - "End-to-End HTTP Tests"
Cohesion: 0.16
Nodes (17): _app(), parametrize, The other half: an entry can exist and still be unpostable., Three tickets, one fix, all three grade cleared — over HTTP only. The point of…, The teaching path: hand it off, get it back, fix it. A fixable fault is bounced…, The mail slice end to end: a mailbox read, a quota raise, a clean close., The other half of the mail slice: the one that is not yours to fix., A full pass with noise in the world. Distractors are applied before the… (+9 more)

### Community 27 - "LM Studio Client Build"
Cohesion: 0.19
Nodes (12): make_client(), Model-backed persona against an OpenAI-compatible local endpoint (LM Studio).…, Build a real LM Studio client. Imported lazily so the suite never needs openai., build_persona(), PersonaSettings, BaseModel, Where the persona backend is chosen. The drill must be fully playable with…, The persona for a whole session. Built with no leak terms: since Task 1 they… (+4 more)

### Community 28 - "Distractor Catalog Tests"
Cohesion: 0.17
Nodes (15): all_distractors(), cases(), parametrize, Conformance harness for the whole distractor catalog. Mirrors…, The honesty guarantee: a distractor is real, visible, and never a cause., Seeded before the baseline, a distractor is inherited world state., An invisible distractor distracts nobody., A seeded anomaly must not make a legitimate repair fail. (+7 more)

### Community 29 - "No DHCP Lease Fault"
Cohesion: 0.13
Nodes (4): NoDhcpLease, Random, StaticDnsMisconfig, _workstations()

### Community 30 - "SSE Events & Web Templates"
Cohesion: 0.17
Nodes (9): SSE tick / degraded / shift-remaining polling pattern, events(), get, Request, get, Request, The whole shift, summed. Reachable at any point, not only once the clock runs…, shift_summary() (+1 more)

### Community 31 - "Account Locked Fault"
Cohesion: 0.13
Nodes (4): AccountLocked, PasswordExpired, Users who make plausible victims: ordinary staff with a workstation., _staff_with_machines()

### Community 32 - "Ticket Persona Binding & Escalation"
Cohesion: 0.18
Nodes (7): The persona bound to this ticket's leak terms. Lives here, not in the chat…, BaseModel, datetime, Hand off to tier-2. Not a close — `review_escalation()` decides whether it…, A tier-2 bounce: back to the technician, disposition undecided again., A tier-2 acceptance. Records what tier-2 said before closing. The bounce path…, Ticket

### Community 33 - "Shift Report Build"
Cohesion: 0.14
Nodes (12): build_shift_report(), BaseModel, Sum the shift from what the store already knows. Takes the store's own rows…, What the whole shift added up to. Deliberately the same shape of judgement the…, One line for the whole day, in the after-action's voice. Ordered worst-first on…, shift_verdict(), ShiftReport, The whole shift, summed from what the store recorded. `unresolved` comes from… (+4 more)

### Community 34 - "Disk Full Fault"
Cohesion: 0.14
Nodes (4): DiskFull, FailingDisk, Random, Escalate-correct: a pre-fail SMART status means the drive needs replacing, not…

### Community 35 - "Cascade & Escalate Web Tests"
Cohesion: 0.20
Nodes (11): get_fault(), test_it_only_places_on_a_print_server(), test_server_spooler_reporters_are_users_of_that_server_s_printers(), A bounce nudges. It must not hand over the diagnosis. Checked with `scrub()`…, `escalation_reason` is why the ticket was not the technician's. The after-…, test_a_bounce_shows_the_tier2_turn_in_chat(), test_a_bounced_escalation_returns_the_ticket_to_the_queue(), test_an_accepted_escalation_persists_to_the_store() (+3 more)

### Community 36 - "Persona Card Templates"
Cohesion: 0.27
Nodes (12): card_for(), Random, Build the persona card for an AD user. Seeded off `user.sam` by default, so the…, The template can only echo symptom fields, so every fault's replies must stay…, _symptoms(), test_card_is_derived_from_the_ad_user(), test_card_is_stable_for_the_same_person(), test_history_is_accepted_but_does_not_crash() (+4 more)

### Community 37 - "Store Persistence Tests"
Cohesion: 0.23
Nodes (13): closed_ticket(), fixture, A database created before Task 6 must survive `init()` being called again., store(), test_after_action_round_trips(), test_cascade_id_is_none_for_a_single_ticket(), test_cascade_id_round_trips(), test_domain_stats_aggregate_by_fault_domain() (+5 more)

### Community 38 - "Phase 2a Mail Plan Notes"
Cohesion: 0.18
Nodes (13): Mail domain (world model + tools + faults), Phase 2a Depth Mechanics Implementation Plan, Design decision: mail gets a real layer slice, not simulated symptoms, Task 11: The KB tool and after-action links, Task 12: The mail world model, Task 13: Mail query and action kinds, Task 14: The mail console tool, Task 16: End-to-end coverage for every new surface (+5 more)

### Community 39 - "Leak Term Scrubbing"
Cohesion: 0.15
Nodes (13): Pattern, _leak_pattern(), Compile leak terms into one word-start-anchored alternation. Anchoring matters…, Return the text if clean, or None if it leaks a forbidden term., scrub(), Plain substring matching would read "please" as the DHCP term "lease"., `"ad "` — trailing space — must not fire on "bad" or "address"., test_a_term_written_as_a_whole_word_stays_a_whole_word() (+5 more)

### Community 40 - "Difficulty-Weighted Fault Choice"
Cohesion: 0.21
Nodes (13): choose_fault_and_placement(), difficulty_weight(), How often this fault should come up relative to the others., Pick the fault first, then one of its placements. Choosing uniformly from…, _candidate_pairs(), A real queue is mostly routine. The hard ticket has to stay rare enough to be…, The bug this scheduler exists to fix. Drawing uniformly from (fault, placement)…, Fixed-seed tests across the suite depend on this. (+5 more)

### Community 41 - "Mail Fault Handoff Notes"
Cohesion: 0.20
Nodes (12): Knowledge base (vitsc.kb), is_present() must gate on both forwarding_smtp and rule halves, mail.external_forwarding_rule fault, mail.mailbox_full fault, _read_mail_rules content-sized column widths fix, Pull Request #10 (merged, Tasks 15-17), Pull Request #9 (parallel Task 15 implementation), KB articles are procedural, never an answer key (+4 more)

### Community 42 - "Phase 2a Handoff Document"
Cohesion: 0.20
Nodes (12): Phase 2a Handoff Document, remote clear-disk with no gb silently succeeds (open thread), Design spec deleted in commit dbcd2bb, Two paths to Disposition.ESCALATED (open design question), Fixed eight-hour shift (session/shift.py), Verifying the Model-Backed Persona (guide), Degraded banner on model outage, REQUEST_TIMEOUT_SECONDS (30s) transport setting (+4 more)

### Community 43 - "Escalation Web Routes"
Cohesion: 0.24
Nodes (6): Persona-mediated rendering guard (no fault_id/symptoms leak in ticket template), escalate_form(), escalate_ticket(), get, post, Request

### Community 44 - "Meridian Company Seed Data"
Cohesion: 0.18
Nodes (11): Meridian Freight Co. company.yaml seed data, HR-Share-RW group with no share behind it (closed gap), MER-DC-01 (domain controller), MER-FS-01 (file server), MER-MB-01 (mail server), MER-PRT-01 (print server), meridian.local domain, KB: The Meridian estate, at a glance (+3 more)

### Community 45 - "After-Action Report & Grading"
Cohesion: 0.29
Nodes (8): The after-action report. The report, not the score, is why the drill transfers…, questions_before_first_mutation(), What the technician actually achieved on one ticket. Grading never asks a fault…, How many questions the technician asked before touching anything. Both…, Disposition, Enum, str, TicketState

### Community 46 - "Fault Protocol Base"
Cohesion: 0.20
Nodes (3): Fault, Protocol, Random

### Community 47 - "Ticket Close Web Tests"
Cohesion: 0.33
Nodes (8): Apply the fault's canonical resolution directly through the environment., solve(), test_after_action_reveals_the_root_cause_only_after_closing(), test_closed_ticket_leaves_the_active_queue(), test_closing_a_solved_ticket_reports_success(), test_closing_persists_to_the_store(), test_double_close_returns_409(), test_history_page_lists_closed_tickets()

### Community 48 - "Queue Web Tests"
Cohesion: 0.20
Nodes (4): client(), fixture, test_cascade_siblings_are_visibly_related_in_the_queue(), test_no_template_leaks_the_canonical_title()

### Community 49 - "Tools Web Tests"
Cohesion: 0.20
Nodes (3): client(), fixture, test_chat_reply_never_contains_a_leak_term()

### Community 50 - "PowerShell Tools & Web Routes"
Cohesion: 0.22
Nodes (7): parse_args(), get, post, Request, sam=m.alvarez host=MER-WS-001' -> dict. Malformed pairs are dropped., run_tool(), tool_pane()

### Community 51 - "Architecture Import Guards"
Cohesion: 0.31
Nodes (8): imported_modules(), Path, Guards for the spec's core principle: tools read world state, never faults. A…, Tools go through `Environment`, so they never need world types., The same rule as faults, for the same reason. A tool that could see the…, test_no_tool_imports_a_distractor(), test_no_tool_imports_a_fault(), test_no_tool_imports_the_world_model_directly()

### Community 52 - "Cascade Faults Design Notes"
Cohesion: 0.25
Nodes (8): Cascade faults (reporters/cascade_id), Fault protocol, One arrival is not one ticket (cascade convention), Design decision: cascade tickets are siblings, not parent and children, FaultBase (protocol defaults holder), Task 5: Cascade data model — reporters, sibling tickets, plural arrivals, Tools read world state, never read the fault, KB: Before you touch anything (triage first questions)

### Community 53 - "Phase 2b Catalog Plan Notes"
Cohesion: 0.29
Nodes (8): Difficulty-weighted fault scheduling (choose_fault_and_placement), Estate growth: 20 users, 10 workstations, Phase 2b: Catalog Breadth Plan, Phase 2b Definition of Done, Difficulty drives scheduling (settled before Task 1), Estate grown to 20 users/10 workstations (settled before Task 1), Fixed eight-hour shift (settled before Task 1), KB: A workstation that's slow or acting strange

### Community 58 - "Persona Protocol Design Notes"
Cohesion: 0.50
Nodes (4): Persona protocol, Three leak-prevention layers (structural, prompt, scrub), Design decision: leak terms bind per call not per construction, Task 1: Bind leak terms per ticket

### Community 59 - "Simulated Tier-2 Design Notes"
Cohesion: 0.50
Nodes (4): Simulated tier-2 (session/tier2.py), Ticket.accept_escalation(text, at) records tier-2's words, Design decision: tier-2 is deterministic and template-driven, never model-driven, Task 8: The simulated tier-2

### Community 60 - "Cached Credentials Design Notes"
Cohesion: 0.67
Nodes (4): ad.cached_credentials_expired fault, Task 1: Stale cached credentials after long network absence, KB: Reading an account that can't sign in, KB: Signed in locally but nothing else works

### Community 61 - "Test Suite Fixtures"
Cohesion: 0.50
Nodes (3): isolate_vitsc_env(), fixture, Suite-wide guards. `AppSession.build` reads the environment to pick a persona…

### Community 62 - "Distractor Protocol Design Notes"
Cohesion: 0.67
Nodes (3): Distractor protocol, Design decision: distractors are a separate protocol, not faults with a flag, Task 3: The Distractor protocol and its conformance harness

## Knowledge Gaps
- **26 isolated node(s):** `vitsc`, `Pylint GitHub Workflow`, `Meridian Freight Co. (fictional employer)`, `Fixed eight-hour shift (session/shift.py)`, `REQUEST_TIMEOUT_SECONDS (30s) transport setting` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `World` connect `Cached Credentials Fault` to `Grading & Tool Consoles`, `Disk Full Fault`, `SimulatedEnvironment & Ticket Priority`, `Distractor Protocol`, `Fault Scheduler & Ticket Queue`, `After-Action Report & Grading`, `Fault Protocol Base`, `Environment/Fault Base Protocols`, `Tier-2 Escalation Review`, `Distractor Registry Tests`, `Baseline & Invariant Checking`, `Offboarded Reactivation Fault`, `External Forwarding Rule Fault`, `Wrong Driver Fault`, `Spooler Stopped Fault`, `No DHCP Lease Fault`, `Account Locked Fault`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `load_world()` connect `SimulatedEnvironment & Ticket Priority` to `Grading & Tool Consoles`, `Environment Protocol I/O Types`, `Cascade & Escalate Web Tests`, `Persona Card Templates`, `Store Persistence Tests`, `Cached Credentials Fault`, `App Bootstrap & Persona Config`, `Difficulty-Weighted Fault Choice`, `Environment Protocol & AD Console`, `Queue Scheduler Tests`, `Fault Registry Conformance Tests`, `Tier-2 Escalation Review`, `Mail Fault Conformance Tests`, `Persona Degradation & Templates`, `Baseline & Invariant Checking`, `Persona Binding Tests`, `LM Studio Client Build`, `Distractor Catalog Tests`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `Placement` connect `Distractor Protocol` to `Grading & Tool Consoles`, `Disk Full Fault`, `Cached Credentials Fault`, `Difficulty-Weighted Fault Choice`, `Fault Scheduler & Ticket Queue`, `After-Action Report & Grading`, `Fault Protocol Base`, `Environment/Fault Base Protocols`, `Tier-2 Escalation Review`, `Distractor Registry Tests`, `Offboarded Reactivation Fault`, `External Forwarding Rule Fault`, `Wrong Driver Fault`, `Spooler Stopped Fault`, `No DHCP Lease Fault`, `Account Locked Fault`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `SimulatedEnvironment` (e.g. with `Grade` and `SessionQueue`) actually correct?**
  _`SimulatedEnvironment` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vitsc`, `Pylint GitHub Workflow`, `Meridian Freight Co. (fictional employer)` to the rest of the system?**
  _26 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `HTMX Static Bundle` be split into smaller, more focused modules?**
  _Cohesion score 0.0814772510946126 - nodes in this community are weakly interconnected._
- **Should `Grading & Tool Consoles` be split into smaller, more focused modules?**
  _Cohesion score 0.06523655598001764 - nodes in this community are weakly interconnected._