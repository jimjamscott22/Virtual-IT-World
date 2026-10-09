# Graph Report - Virtual-IT-World  (2026-10-08)

## Corpus Check
- 123 files · ~89,901 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1686 nodes · 4442 edges · 91 communities (77 shown, 14 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0cecbc2e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- htmx.min.js
- test_grading.py
- test_simulated_env.py
- load_world
- tools/base.py
- Query
- Placement
- deps.py
- test_shift.py
- session/queue.py
- app.py
- test_queue.py
- loader.py
- faults/registry.py
- faults/base.py
- LMStudioPersona
- test_tier2.py
- test_faults_mail.py
- test_distractor_registry.py
- test_cascade.py
- capture_baseline
- Store
- advance_clock_if_due
- test_persona_binding.py
- catalog/mail.py
- SimulatedEnvironment
- ToolLog
- client.py
- afteraction.py
- World
- events
- Action
- Ticket
- build_shift_report
- UserSymptoms
- get_fault
- TemplatePersona
- test_store.py
- Phase 2a Depth Mechanics Implementation Plan
- test_persona_client.py
- Observation
- mail.external_forwarding_rule fault
- Phase 2a Handoff Document
- ticket.py
- Meridian Freight Co. company.yaml seed data
- grading.py
- world/models.py
- test_web_close.py
- test_web_queue.py
- test_web_tools.py
- Helpdesk Workbench UI Design
- test_architecture.py
- Cascade faults (reporters/cascade_id)
- Phase 2b: Catalog Breadth Plan
- test_web_kb.py
- test_ticket.py
- FaultBase
- get_tool
- Persona protocol
- Simulated tier-2 (session/tier2.py)
- ad.cached_credentials_expired fault
- conftest.py
- Design decision: distractors are a separate protocol, not faults with a flag
- Pylint GitHub Workflow
- data/__init__.py
- vitsc/__init__.py
- persona/__init__.py
- session/__init__.py
- Environment protocol
- vitsc
- ADConsole
- OwnerlessDistributionList
- Shift
- Review Focus
- AGENTS.md
- duplicate_mutations
- simulated.py
- JobStatus
- endpoint-profile-and-services.md
- general-escalation-and-ownership.md
- identity-group-and-access.md
- mail-delegates-and-lists.md
- network-address-settings.md
- printing-queue-and-device.md

## God Nodes (most connected - your core abstractions)
1. `Placement` - 252 edges
2. `World` - 227 edges
3. `Action` - 114 edges
4. `SimulatedEnvironment` - 108 edges
5. `Query` - 100 edges
6. `load_world()` - 93 edges
7. `get_fault()` - 64 edges
8. `UserSymptoms` - 53 edges
9. `grade_ticket()` - 49 edges
10. `setup()` - 46 edges

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

## Communities (91 total, 14 thin omitted)

### Community 0 - "htmx.min.js"
Cohesion: 0.08
Nodes (102): A(), ae(), ar(), at(), B(), be(), br(), bt() (+94 more)

### Community 1 - "test_grading.py"
Cohesion: 0.13
Nodes (43): build_after_action(), grade_ticket(), Escalating after only looking must not read as 'touched before asking'., `siblings` only feeds the report — `is_present()` already covers every sibling,…, A bounced-then-fixed ticket is still correct — the after-action is where the…, `{placement}`-style sentinels must all be resolved by the time a technician…, Nothing checks *how* the fault cleared — resetting the password counts., setup() (+35 more)

### Community 2 - "test_simulated_env.py"
Cohesion: 0.06
Nodes (35): MailRule, env(), fixture, A fixed-width column silently collides with the next one once a value outgrows…, test_archive_reduces_usage_without_touching_quota(), test_clear_disk_caps_at_total_and_repairs_temp_profile(), test_ipconfig_reports_apipa_without_a_lease(), test_mail_mailbox_read_renders_exchange_shaped_output() (+27 more)

### Community 3 - "load_world"
Cohesion: 0.15
Nodes (20): load_world(), Path, Build a healthy `World` from `company.yaml`. The world returned is always at…, Enumerated on purpose, like the catalog roster. Placement counts fall out of…, Twenty people, ten machines. A user-placed fault and a machine-placed fault…, HR had a group and no share until the estate grew — an HR workstation would…, The new machines have to be as complete as the original six., test_every_department_group_has_a_share_behind_it() (+12 more)

### Community 4 - "tools/base.py"
Cohesion: 0.09
Nodes (28): DispatchTool, Player-facing tool framework. Tools are thin wrappers over `env.read()` /…, Shared dispatch for every tool: a read map, a write map, and a target.…, EventViewer, MailConsole, NetworkTools, PowerShellConsole, A *defined* command set, not a parser. A free-form shell cannot be honestly… (+20 more)

### Community 5 - "Query"
Cohesion: 0.06
Nodes (19): CurrentEmployeeDelegate, _delegate_for(), EmptyLegacyGroup, HarmlessInboxRule, IdleHelperProcess, MinorClockDrift, ModeratelyLowDisk, OfflineUnusedPrinter (+11 more)

### Community 6 - "Placement"
Cohesion: 0.06
Nodes (19): Placement, A world entity a fault is attached to., AccountLocked, CachedCredentialsExpired, NestedGroupMembership, OffboardedReactivation, PasswordChangeNotCached, PasswordExpired (+11 more)

### Community 7 - "deps.py"
Cohesion: 0.08
Nodes (33): main(), `uv run python -m vitsc` — the normal way to start the drill. Uses…, create_app(), AppSession, BaseModel, datetime, Path, A single in-process session, not a per-request one — there is exactly one… (+25 more)

### Community 8 - "test_shift.py"
Cohesion: 0.10
Nodes (15): parametrize, The fixed shift: when arrivals stop, and what the day added up to., Built from the store's own rows, so it cannot disagree with history., A ticket nobody closed was never written to the store — which is exactly why…, Past the end it clamps rather than going negative — the header renders this…, The shift gates arrivals, not the technician. A ticket already open at five…, The shift is optional on the queue itself — every test that builds a bare…, test_a_clock_that_ran_backwards_does_not_go_negative() (+7 more)

### Community 9 - "session/queue.py"
Cohesion: 0.23
Nodes (8): difficulty_weight(), datetime, Random, The fault scheduler and the ticket queue. This is what makes a session…, Open new tickets as the arrival interval elapses, until the shift ends., How often this fault should come up relative to the others., Apply `count` distinct distractors before the first baseline capture. Order…, seed_distractors()

### Community 10 - "app.py"
Cohesion: 0.16
Nodes (20): FastAPI, post, Request, send_message(), index(), get, post, Request (+12 more)

### Community 11 - "test_queue.py"
Cohesion: 0.07
Nodes (35): choose_fault_and_placement(), Pick the fault first, then one of its placements. Choosing uniformly from…, _candidate_pairs(), _dealt(), make_queue(), fixture, parametrize, queue() (+27 more)

### Community 12 - "loader.py"
Cohesion: 0.14
Nodes (22): get_article(), load_articles(), _parse(), Loads the original-content knowledge base from `vitsc/data/kb/*.md`. Each…, search_articles(), Article, BaseModel, A single knowledge-base page: procedure, not an answer key. (+14 more)

### Community 13 - "faults/registry.py"
Cohesion: 0.11
Nodes (21): all_faults(), fault_cases(), parametrize, Conformance harness for the whole fault catalog. The failure mode of this…, The ten v1 faults, plus what Phase 2a has added to that set since. The name is…, One per reason a ticket is not yours, and no two alike: -…, A fault must change at least one observation, or it is invisible., test_discoverability_actually_differs() (+13 more)

### Community 14 - "faults/base.py"
Cohesion: 0.31
Nodes (9): _first_host_with(), _machine_key(), _printer_key(), Random, Fault declarations. `is_present()` is the single source of truth for both "is…, `ACC-Share-RW` -> `ACC-Staff`. The convention lives here, beside the sentinel…, _sentinels(), _share_group() (+1 more)

### Community 15 - "LMStudioPersona"
Cohesion: 0.17
Nodes (6): setter, LMStudioPersona, A copy scrubbing this ticket's vocabulary, sharing everything else. A copy…, DeadClient, test_model_dying_on_the_retry_also_falls_back(), test_unreachable_model_falls_back_to_template()

### Community 16 - "test_tier2.py"
Cohesion: 0.31
Nodes (13): review_escalation(), Ownership is judged first: a good note doesn't change who owns it., The acceptance carries the fault's `escalation_reason`, and it is the only…, test_a_bounce_reopens_the_ticket_and_leaves_a_tier2_turn(), test_a_fixable_fault_is_bounced_back(), test_a_fixable_fault_is_bounced_even_with_a_well_evidenced_note(), test_a_good_escalation_of_an_escalate_only_fault_is_accepted(), test_accepting_closes_the_ticket_as_escalated() (+5 more)

### Community 17 - "test_faults_mail.py"
Cohesion: 0.11
Nodes (21): broken(), parametrize, Specifics for the mail domain's two reference faults. The conformance harness…, Same encoding `endpoint.failing_disk` uses: escalate-correct plus an empty…, A world with the fault applied, plus its placement and an environment., Raise the quota or reduce the usage — both are real answers., Neither path is the 'real' one — the gate is world state, not a button., The gate reads the world, so a fix that does not actually help fails. (+13 more)

### Community 18 - "test_distractor_registry.py"
Cohesion: 0.15
Nodes (14): clean_registry(), fixture, Random, Unit coverage for the distractor protocol and registry. The conformance harness…, `Distractor` is runtime_checkable, so this is a real structural check., Two distractors sharing an id would make one of them unreachable., Task 3 shipped the mechanism with an empty catalog on purpose; Task 4 fills it.…, StubDistractor (+6 more)

### Community 19 - "test_cascade.py"
Cohesion: 0.17
Nodes (11): FaultBase supplies the default, so this is a retrofit check., Named explicitly rather than drawn from the scheduler. This used to call…, Falls out of grading asking the world, not the ticket., test_a_cascade_never_exceeds_the_queue(), test_every_fault_declares_reporters(), test_fixing_the_root_clears_every_sibling(), test_it_only_places_on_a_print_server(), test_open_one_is_still_available_for_single_ticket_tests() (+3 more)

### Community 20 - "capture_baseline"
Cohesion: 0.15
Nodes (26): bind(), Replace placement sentinels (`{placement}`, `{machine}`, `{group}`,…, capture_baseline(), check_invariants(), test_fault_conforms(), parametrize, Seeded before the baseline, a distractor is inherited world state., A seeded anomaly must not make a legitimate repair fail. (+18 more)

### Community 21 - "Store"
Cohesion: 0.18
Nodes (11): Connection, AfterAction, BaseModel, Grade, BaseModel, Path, SQLite persistence for closed tickets. Only *closed* tickets persist. Live…, The WHERE clause that keeps one run's rows apart from another's. Rows written… (+3 more)

### Community 22 - "advance_clock_if_due"
Cohesion: 0.32
Nodes (7): advance_clock_if_due(), Advance the shared world clock at most once per `TICK_SECONDS` of real time, no…, fixture, session(), test_the_clock_advances_again_once_a_full_tick_has_elapsed(), test_three_overlapping_connections_still_advance_only_once_per_tick(), test_two_connections_checking_in_within_the_same_tick_only_advance_once()

### Community 23 - "test_persona_binding.py"
Cohesion: 0.13
Nodes (12): DeadClient, Degradation is session state, so it has to travel back to the origin. The queue…, Returns whatever it is told to, and records the prompts it saw., Layer 3 filters output. Telling the model the forbidden word hands it the…, Nothing listening on localhost., StubClient, test_a_bindings_fallback_marks_the_origin_degraded(), test_binding_does_not_mutate_the_original() (+4 more)

### Community 24 - "catalog/mail.py"
Cohesion: 0.07
Nodes (15): AutodiscoverBroken, ExternalForwardingRule, _is_external(), _mailbox(), _mailbox_is_gone(), _mailbox_owners(), MailboxFull, Random (+7 more)

### Community 25 - "SimulatedEnvironment"
Cohesion: 0.09
Nodes (4): ActionResult, Update the driver on every workstation that has this printer. The per-…, Destructive on purpose. Nothing in the catalog is fixed by deleting a mailbox,…, SimulatedEnvironment

### Community 26 - "ToolLog"
Cohesion: 0.10
Nodes (15): Environment, Protocol, BaseModel, Protocol, Return (kind, 'read'|'write'). Matching is case-insensitive., Tool, ToolCall, ToolLog (+7 more)

### Community 27 - "client.py"
Cohesion: 0.10
Nodes (22): make_client(), Model-backed persona against an OpenAI-compatible local endpoint (LM Studio).…, Build a real LM Studio client. Imported lazily so the suite never needs openai., build_persona(), PersonaSettings, BaseModel, Where the persona backend is chosen. The drill must be fully playable with…, The persona for a whole session. Built with no leak terms: since Task 1 they… (+14 more)

### Community 28 - "afteraction.py"
Cohesion: 0.13
Nodes (20): Distractor, Protocol, Random, Honest distractors. A distractor is a real, truthfully-reported anomaly that is…, all_distractors(), get_distractor(), Distractor registration, mirroring `faults/registry.py`. Kept separate from the…, register_distractor() (+12 more)

### Community 29 - "World"
Cohesion: 0.06
Nodes (19): DuplicateStaticIp, GatewayMisconfigured, _lowest_hostname(), NoDhcpLease, _partner_of(), Random, A mask narrow enough that the machine believes the servers are on some other…, The differential against every DNS fault: names still resolve and everything… (+11 more)

### Community 30 - "events"
Cohesion: 0.17
Nodes (9): SSE tick / degraded / shift-remaining polling pattern, events(), get, Request, get, Request, The whole shift, summed. Reachable at any point, not only once the clock runs…, shift_summary() (+1 more)

### Community 31 - "Action"
Cohesion: 0.10
Nodes (3): Action, A write against the environment., ResolutionPath

### Community 32 - "Ticket"
Cohesion: 0.09
Nodes (27): bind_query(), Fault, Protocol, Replace placement sentinels in a diagnostic query the same way `bind` does., Who phones this in, for a fault that does not declare its own reporters. User…, Who actually gets a ticket for this fault instance. `fault.reporters()` names…, The persona bound to this ticket's leak terms. Lives here, not in the chat…, Apply `fault` at `placement` and build one ticket per reporter. Shared by… (+19 more)

### Community 33 - "build_shift_report"
Cohesion: 0.16
Nodes (14): build_shift_report(), BaseModel, Sum the shift from what the store already knows. Takes the store's own rows…, What the whole shift added up to. Deliberately the same shape of judgement the…, ShiftReport, ClosedRecord, DomainStat, BaseModel (+6 more)

### Community 34 - "UserSymptoms"
Cohesion: 0.06
Nodes (18): BaseModel, Only what a non-technical person can perceive. The sole persona input., UserSymptoms, ClockSkew, CorruptProfile, DiskFull, DnsClientDisabled, FailingDisk (+10 more)

### Community 35 - "get_fault"
Cohesion: 0.09
Nodes (32): get_fault(), _app(), escalate_via_http(), parametrize, Submit the fault's canonical fix through POST /ticket/{id}/tool, exercising the…, The failure this guards is silent: a table entry listing one step for a two-…, Three tickets, one fix, all three grade cleared — over HTTP only. The point of…, The teaching path: hand it off, get it back, fix it. A fixable fault is bounced… (+24 more)

### Community 36 - "TemplatePersona"
Cohesion: 0.16
Nodes (17): _Degradation, The one degraded flag an origin persona shares with all its bindings.…, card_for(), Random, Build the persona card for an AD user. Seeded off `user.sam` by default, so the…, Symptom-derived responses, matched on keywords in the question., Itself. Every sentence is a symptom field or fixed connective text, so there is…, TemplatePersona (+9 more)

### Community 37 - "test_store.py"
Cohesion: 0.19
Nodes (16): closed_ticket(), fixture, A database created before Task 6 must survive `init()` being called again., The defect this column exists for, found by running the real app twice.…, A database from an earlier release has NULL `session_id`. Those rows are…, store(), test_a_new_session_does_not_inherit_an_earlier_one_s_rows(), test_after_action_round_trips() (+8 more)

### Community 38 - "Phase 2a Depth Mechanics Implementation Plan"
Cohesion: 0.18
Nodes (13): Mail domain (world model + tools + faults), Phase 2a Depth Mechanics Implementation Plan, Design decision: mail gets a real layer slice, not simulated symptoms, Task 11: The KB tool and after-action links, Task 12: The mail world model, Task 13: Mail query and action kinds, Task 14: The mail console tool, Task 16: End-to-end coverage for every new surface (+5 more)

### Community 39 - "test_persona_client.py"
Cohesion: 0.10
Nodes (24): Pattern, _leak_pattern(), Compile leak terms into one word-start-anchored alternation. Anchoring matters…, Return the text if clean, or None if it leaks a forbidden term., scrub(), build_system_prompt(), The technician is the model's 'user'; the persona is the 'assistant'., Mimics the surface of openai.OpenAI that LMStudioPersona uses. (+16 more)

### Community 40 - "Observation"
Cohesion: 0.08
Nodes (7): Observation, BaseModel, Can this machine get a packet to that address at all? On-subnet traffic needs…, What `ipconfig` would print — an APIPA address when the lease failed., DNS resolution, honouring the querying machine's own resolvers. Three things…, What the adapter is actually using — APIPA brings its own mask., A machine with no lease has no default route, which is what `ipconfig` already…

### Community 41 - "mail.external_forwarding_rule fault"
Cohesion: 0.20
Nodes (12): Knowledge base (vitsc.kb), is_present() must gate on both forwarding_smtp and rule halves, mail.external_forwarding_rule fault, mail.mailbox_full fault, _read_mail_rules content-sized column widths fix, Pull Request #10 (merged, Tasks 15-17), Pull Request #9 (parallel Task 15 implementation), KB articles are procedural, never an answer key (+4 more)

### Community 42 - "Phase 2a Handoff Document"
Cohesion: 0.20
Nodes (12): Phase 2a Handoff Document, remote clear-disk with no gb silently succeeds (open thread), Design spec deleted in commit dbcd2bb, Two paths to Disposition.ESCALATED (open design question), Fixed eight-hour shift (session/shift.py), Verifying the Model-Backed Persona (guide), Degraded banner on model outage, REQUEST_TIMEOUT_SECONDS (30s) transport setting (+4 more)

### Community 43 - "ticket.py"
Cohesion: 0.11
Nodes (22): Persona-mediated rendering guard (no fault_id/symptoms leak in ticket template), HTMLResponse, IntEnum, Disposition, Priority, Enum, str, Lower is more urgent, so priorities sort naturally. (+14 more)

### Community 44 - "Meridian Freight Co. company.yaml seed data"
Cohesion: 0.18
Nodes (11): Meridian Freight Co. company.yaml seed data, HR-Share-RW group with no share behind it (closed gap), MER-DC-01 (domain controller), MER-FS-01 (file server), MER-MB-01 (mail server), MER-PRT-01 (print server), meridian.local domain, KB: The Meridian estate, at a glance (+3 more)

### Community 45 - "grading.py"
Cohesion: 0.16
Nodes (15): questions_before_first_mutation(), What the technician actually achieved on one ticket. Grading never asks a fault…, How many questions the technician asked before touching anything. Both…, forgive(), Fold a newly applied fault into the standing baseline. Overwriting the baseline…, _account_violations(), Baseline, _dns_violations() (+7 more)

### Community 46 - "world/models.py"
Cohesion: 0.18
Nodes (17): ADGroup, ADUser, DistributionList, Machine, Mailbox, MailSystem, Network, Organization (+9 more)

### Community 47 - "test_web_close.py"
Cohesion: 0.17
Nodes (14): client(), fixture, A disposition the drill does not review is not one it accepts. Removing the…, Apply the fault's canonical resolution directly through the environment., Phase 2a left two paths to `Disposition.ESCALATED` and they were not…, solve(), test_after_action_reveals_the_root_cause_only_after_closing(), test_closed_ticket_leaves_the_active_queue() (+6 more)

### Community 48 - "test_web_queue.py"
Cohesion: 0.20
Nodes (4): client(), fixture, test_cascade_siblings_are_visibly_related_in_the_queue(), test_no_template_leaks_the_canonical_title()

### Community 49 - "test_web_tools.py"
Cohesion: 0.20
Nodes (3): client(), fixture, test_chat_reply_never_contains_a_leak_term()

### Community 50 - "Helpdesk Workbench UI Design"
Cohesion: 0.10
Nodes (19): Accessibility and responsiveness, Active case, Color, Deliberate exclusions, Design direction, Empty, degraded, and failure states, Feedback and reports, Goal (+11 more)

### Community 51 - "test_architecture.py"
Cohesion: 0.31
Nodes (8): imported_modules(), Path, Guards for the spec's core principle: tools read world state, never faults. A…, Tools go through `Environment`, so they never need world types., The same rule as faults, for the same reason. A tool that could see the…, test_no_tool_imports_a_distractor(), test_no_tool_imports_a_fault(), test_no_tool_imports_the_world_model_directly()

### Community 52 - "Cascade faults (reporters/cascade_id)"
Cohesion: 0.25
Nodes (8): Cascade faults (reporters/cascade_id), Fault protocol, One arrival is not one ticket (cascade convention), Design decision: cascade tickets are siblings, not parent and children, FaultBase (protocol defaults holder), Task 5: Cascade data model — reporters, sibling tickets, plural arrivals, Tools read world state, never read the fault, KB: Before you touch anything (triage first questions)

### Community 53 - "Phase 2b: Catalog Breadth Plan"
Cohesion: 0.29
Nodes (8): Difficulty-weighted fault scheduling (choose_fault_and_placement), Estate growth: 20 users, 10 workstations, Phase 2b: Catalog Breadth Plan, Phase 2b Definition of Done, Difficulty drives scheduling (settled before Task 1), Estate grown to 20 users/10 workstations (settled before Task 1), Fixed eight-hour shift (settled before Task 1), KB: A workstation that's slow or acting strange

### Community 55 - "test_ticket.py"
Cohesion: 0.16
Nodes (18): priority_for(), The *system's* triage call, which the player's own is graded against. Impact…, make_ticket(), parametrize, Every sign-in blocker is P1 for the most junior user in the org.…, A cascade is impact by definition, whatever the fault's own difficulty., test_a_harder_fault_outranks_an_easier_one_for_the_same_person(), test_a_manager_outranks_a_clerk_for_the_same_fault() (+10 more)

### Community 56 - "FaultBase"
Cohesion: 0.05
Nodes (20): FaultBase, Who phones this in. `None` means "whoever the placement points at" — the…, Defaults for every optional `Fault` member. The protocol grew in Phase 2a. Ten…, DriverAfterModelSwap, _first_user_of(), _installed_printers(), _print_servers(), PrinterOffline (+12 more)

### Community 57 - "get_tool"
Cohesion: 0.19
Nodes (15): get_tool(), The architecture rule binds this tool like every other., test_a_missing_article_fails_without_raising(), test_kb_calls_are_never_mutating(), test_kb_read_renders_the_body(), test_kb_search_renders_hits(), test_the_kb_tool_does_not_import_faults_or_world(), test_a_missing_parameter_is_reported_not_raised() (+7 more)

### Community 58 - "Persona protocol"
Cohesion: 0.50
Nodes (4): Persona protocol, Three leak-prevention layers (structural, prompt, scrub), Design decision: leak terms bind per call not per construction, Task 1: Bind leak terms per ticket

### Community 59 - "Simulated tier-2 (session/tier2.py)"
Cohesion: 0.50
Nodes (4): Simulated tier-2 (session/tier2.py), Ticket.accept_escalation(text, at) records tier-2's words, Design decision: tier-2 is deterministic and template-driven, never model-driven, Task 8: The simulated tier-2

### Community 60 - "ad.cached_credentials_expired fault"
Cohesion: 0.67
Nodes (4): ad.cached_credentials_expired fault, Task 1: Stale cached credentials after long network absence, KB: Reading an account that can't sign in, KB: Signed in locally but nothing else works

### Community 61 - "conftest.py"
Cohesion: 0.50
Nodes (3): isolate_vitsc_env(), fixture, Suite-wide guards. `AppSession.build` reads the environment to pick a persona…

### Community 62 - "Design decision: distractors are a separate protocol, not faults with a flag"
Cohesion: 0.67
Nodes (3): Distractor protocol, Design decision: distractors are a separate protocol, not faults with a flag, Task 3: The Distractor protocol and its conformance harness

### Community 77 - "ADConsole"
Cohesion: 0.22
Nodes (13): ADConsole, env(), log(), fixture, test_add_member_restores_a_stripped_membership(), test_every_call_is_logged(), test_get_user_renders_attributes(), test_group_commands_target_the_group() (+5 more)

### Community 78 - "OwnerlessDistributionList"
Cohesion: 0.13
Nodes (4): OwnerlessDistributionList, The mail domain's cascade, and the one fault in the catalog placed on a server…, The person who managed a distribution list left, so nobody can change who is on…, TransportStalled

### Community 79 - "Shift"
Cohesion: 0.24
Nodes (7): datetime, The fixed shift, and the report that closes it. A drill needs an end. Without…, One fixed-length working day on the simulated clock., Simulated minutes worked, never negative and never past the end., One line for the whole day, in the after-action's voice. Ordered worst-first on…, Shift, shift_verdict()

### Community 80 - "Review Focus"
Cohesion: 0.18
Nodes (10): Global Constraints, Helpdesk Workbench UI Implementation Plan, Review Focus, Self-review record, Task 1: Shared shell, navigation, and live shift rail, Task 2: Scannable, keyboard-operable ticket queue, Task 3: Active case, conversation, and technician workbench, Task 4: Escalation, resolution, after-action, and secondary pages (+2 more)

### Community 81 - "AGENTS.md"
Cohesion: 0.22
Nodes (7): Architecture, Commands, Core design principle, Placement sentinels, The conformance harness, What this is, Where the code deliberately diverges from the plan

### Community 82 - "duplicate_mutations"
Cohesion: 0.32
Nodes (8): duplicate_mutations(), How many times an identical mutating call was repeated beyond its first use.…, _mutating_call(), Fixing one root cause three times is not three fixes., A technician re-running one fix once per cascade ticket is one fix, not several., test_distinct_mutations_are_not_counted_as_duplicates(), test_duplicate_mutations_counts_the_same_fix_across_siblings(), test_repeating_the_same_mutation_is_counted()

### Community 83 - "simulated.py"
Cohesion: 0.33
Nodes (4): The swap point. Everything above this boundary — tools, faults, session, web —…, The v1 backend: an in-memory world model. Handlers read and write `self.world`…, Whether two addresses look local to each other under one mask., _same_subnet()

### Community 84 - "JobStatus"
Cohesion: 0.60
Nodes (5): JobStatus, ProfileState, Enum, str, SmartStatus

## Knowledge Gaps
- **69 isolated node(s):** `vitsc`, `What this is`, `Commands`, `Core design principle`, `Architecture` (+64 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `World` connect `World` to `test_grading.py`, `load_world`, `Query`, `Placement`, `session/queue.py`, `faults/base.py`, `test_tier2.py`, `test_distractor_registry.py`, `capture_baseline`, `catalog/mail.py`, `SimulatedEnvironment`, `afteraction.py`, `Ticket`, `UserSymptoms`, `grading.py`, `world/models.py`, `FaultBase`, `OwnerlessDistributionList`, `simulated.py`?**
  _High betweenness centrality (0.177) - this node is a cross-community bridge._
- **Why does `Placement` connect `Placement` to `Ticket`, `test_grading.py`, `UserSymptoms`, `Query`, `session/queue.py`, `test_queue.py`, `ticket.py`, `faults/base.py`, `OwnerlessDistributionList`, `test_distractor_registry.py`, `capture_baseline`, `FaultBase`, `catalog/mail.py`, `afteraction.py`, `World`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `load_world()` connect `load_world` to `test_grading.py`, `test_simulated_env.py`, `deps.py`, `test_queue.py`, `faults/registry.py`, `test_tier2.py`, `test_faults_mail.py`, `test_cascade.py`, `capture_baseline`, `test_persona_binding.py`, `ToolLog`, `afteraction.py`, `World`, `Ticket`, `TemplatePersona`, `test_store.py`, `grading.py`, `world/models.py`, `test_ticket.py`, `get_tool`, `ADConsole`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `SimulatedEnvironment` (e.g. with `Grade` and `SessionQueue`) actually correct?**
  _`SimulatedEnvironment` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vitsc`, `What this is`, `Commands` to the rest of the system?**
  _69 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `htmx.min.js` be split into smaller, more focused modules?**
  _Cohesion score 0.0814772510946126 - nodes in this community are weakly interconnected._
- **Should `test_grading.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1321353065539112 - nodes in this community are weakly interconnected._