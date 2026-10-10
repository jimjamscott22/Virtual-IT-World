# Graph Report - Virtual-IT-World  (2026-10-09)

## Corpus Check
- 127 files · ~91,145 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1716 nodes · 4485 edges · 93 communities (76 shown, 17 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 118 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `12540647`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- htmx.min.js
- test_grading.py
- test_simulated_env.py
- load_world
- test_tools_rest.py
- Random
- Placement
- test_web_queue.py
- test_shift.py
- TemplatePersona
- app.py
- test_queue.py
- loader.py
- all_faults
- faults/base.py
- build_shift_report
- scrub
- test_faults_mail.py
- test_distractor_registry.py
- get_fault
- capture_baseline
- ticket.py
- Ticket
- test_persona_binding.py
- _mailbox
- Action
- Store
- UserSymptoms
- test_distractors.py
- GatewayMisconfigured
- DuplicateStaticIp
- ResolutionPath
- test_tier2.py
- .build
- ClockSkew
- test_end_to_end.py
- card_for
- test_store.py
- Phase 2a Depth Mechanics Implementation Plan
- LMStudioPersona
- Query
- mail.external_forwarding_rule fault
- Phase 2a Handoff Document
- EmptyReplyError
- Meridian Freight Co. company.yaml seed data
- session/queue.py
- world/models.py
- test_web_close.py
- ._reachable
- test_web_tools.py
- Helpdesk Workbench UI Design
- test_architecture.py
- Cascade faults (reporters/cascade_id)
- Phase 2b: Catalog Breadth Plan
- test_web_kb.py
- test_ticket.py
- World
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
- OwnerlessDistributionList
- Review Focus
- AGENTS.md
- NestedGroupMembership
- endpoint-profile-and-services.md
- general-escalation-and-ownership.md
- identity-group-and-access.md
- mail-delegates-and-lists.md
- network-address-settings.md
- printing-queue-and-device.md
- CachedCredentialsExpired
- .apply
- vercel.json
- phase-2a-notes.md
- plan-deviations.md
- CLAUDE.md

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

## Communities (93 total, 17 thin omitted)

### Community 0 - "htmx.min.js"
Cohesion: 0.08
Nodes (102): A(), ae(), ar(), at(), B(), be(), br(), bt() (+94 more)

### Community 1 - "test_grading.py"
Cohesion: 0.07
Nodes (70): build_after_action(), duplicate_mutations(), grade_ticket(), How many times an identical mutating call was repeated beyond its first use.…, ADConsole, BaseModel, ToolCall, ToolLog (+62 more)

### Community 2 - "test_simulated_env.py"
Cohesion: 0.06
Nodes (35): MailRule, env(), fixture, A fixed-width column silently collides with the next one once a value outgrows…, test_archive_reduces_usage_without_touching_quota(), test_clear_disk_caps_at_total_and_repairs_temp_profile(), test_ipconfig_reports_apipa_without_a_lease(), test_mail_mailbox_read_renders_exchange_shaped_output() (+27 more)

### Community 3 - "load_world"
Cohesion: 0.10
Nodes (31): load_world(), Path, Build a healthy `World` from `company.yaml`. The world returned is always at…, FaultBase supplies the default, so this is a retrofit check., Named explicitly rather than drawn from the scheduler. This used to call…, Falls out of grading asking the world, not the ticket., test_a_cascade_never_exceeds_the_queue(), test_every_fault_declares_reporters() (+23 more)

### Community 4 - "test_tools_rest.py"
Cohesion: 0.05
Nodes (43): Environment, Protocol, DispatchTool, Protocol, Player-facing tool framework. Tools are thin wrappers over `env.read()` /…, Shared dispatch for every tool: a read map, a write map, and a target.…, The argument `command` reads its target from. One answer serves both the lookup…, Return (kind, 'read'|'write'). Matching is case-insensitive. (+35 more)

### Community 5 - "Random"
Cohesion: 0.07
Nodes (10): EmptyLegacyGroup, IdleHelperProcess, MinorClockDrift, ModeratelyLowDisk, OldDiskWarning, PrinterQueueBacklog, Random, StaleMappedDrive (+2 more)

### Community 6 - "Placement"
Cohesion: 0.05
Nodes (18): HarmlessInboxRule, OfflineUnusedPrinter, Placement, A world entity a fault is attached to., AccountLocked, OffboardedReactivation, PasswordChangeNotCached, PasswordExpired (+10 more)

### Community 7 - "test_web_queue.py"
Cohesion: 0.20
Nodes (4): client(), fixture, test_cascade_siblings_are_visibly_related_in_the_queue(), test_no_template_leaks_the_canonical_title()

### Community 8 - "test_shift.py"
Cohesion: 0.11
Nodes (13): datetime, One fixed-length working day on the simulated clock., Simulated minutes worked, never negative and never past the end., Shift, parametrize, The fixed shift: when arrivals stop, and what the day added up to., Past the end it clamps rather than going negative — the header renders this…, The shift is optional on the queue itself — every test that builds a bare… (+5 more)

### Community 9 - "TemplatePersona"
Cohesion: 0.13
Nodes (16): _Degradation, make_client(), The one degraded flag an origin persona shares with all its bindings.…, Build a real LM Studio client. Imported lazily so the suite never needs openai., build_persona(), PersonaSettings, BaseModel, Where the persona backend is chosen. The drill must be fully playable with… (+8 more)

### Community 10 - "app.py"
Cohesion: 0.06
Nodes (54): SSE tick / degraded / shift-remaining polling pattern, Persona-mediated rendering guard (no fault_id/symptoms leak in ticket template), FastAPI, HTMLResponse, IntEnum, Priority, Lower is more urgent, so priorities sort naturally., post (+46 more)

### Community 11 - "test_queue.py"
Cohesion: 0.05
Nodes (42): choose_fault_and_placement(), datetime, Random, Open new tickets as the arrival interval elapses, until the shift ends., Pick the fault first, then one of its placements. Choosing uniformly from…, Apply `count` distinct distractors before the first baseline capture. Order…, seed_distractors(), _candidate_pairs() (+34 more)

### Community 12 - "loader.py"
Cohesion: 0.14
Nodes (22): get_article(), load_articles(), _parse(), Loads the original-content knowledge base from `vitsc/data/kb/*.md`. Each…, search_articles(), Article, BaseModel, A single knowledge-base page: procedure, not an answer key. (+14 more)

### Community 13 - "all_faults"
Cohesion: 0.11
Nodes (22): all_faults(), fault_cases(), parametrize, Conformance harness for the whole fault catalog. The failure mode of this…, The ten v1 faults, plus what Phase 2a has added to that set since. The name is…, One per reason a ticket is not yours, and no two alike: -…, A fault must change at least one observation, or it is invisible., test_discoverability_actually_differs() (+14 more)

### Community 14 - "faults/base.py"
Cohesion: 0.13
Nodes (18): Random, Honest distractors. A distractor is a real, truthfully-reported anomaly that is…, bind(), bind_query(), _first_host_with(), _machine_key(), _printer_key(), Fault declarations. `is_present()` is the single source of truth for both "is… (+10 more)

### Community 15 - "build_shift_report"
Cohesion: 0.15
Nodes (16): build_shift_report(), BaseModel, The fixed shift, and the report that closes it. A drill needs an end. Without…, Sum the shift from what the store already knows. Takes the store's own rows…, What the whole shift added up to. Deliberately the same shape of judgement the…, One line for the whole day, in the after-action's voice. Ordered worst-first on…, shift_verdict(), ShiftReport (+8 more)

### Community 16 - "scrub"
Cohesion: 0.15
Nodes (13): Pattern, _leak_pattern(), Compile leak terms into one word-start-anchored alternation. Anchoring matters…, Return the text if clean, or None if it leaks a forbidden term., scrub(), Plain substring matching would read "please" as the DHCP term "lease"., `"ad "` — trailing space — must not fire on "bad" or "address"., test_a_term_written_as_a_whole_word_stays_a_whole_word() (+5 more)

### Community 17 - "test_faults_mail.py"
Cohesion: 0.11
Nodes (21): broken(), parametrize, Specifics for the mail domain's two reference faults. The conformance harness…, Same encoding `endpoint.failing_disk` uses: escalate-correct plus an empty…, A world with the fault applied, plus its placement and an environment., Raise the quota or reduce the usage — both are real answers., Neither path is the 'real' one — the gate is world state, not a button., The gate reads the world, so a fix that does not actually help fails. (+13 more)

### Community 18 - "test_distractor_registry.py"
Cohesion: 0.13
Nodes (14): clean_registry(), fixture, Random, Unit coverage for the distractor protocol and registry. The conformance harness…, `Distractor` is runtime_checkable, so this is a real structural check., Two distractors sharing an id would make one of them unreachable., Task 3 shipped the mechanism with an empty catalog on purpose; Task 4 fills it.…, StubDistractor (+6 more)

### Community 19 - "get_fault"
Cohesion: 0.10
Nodes (20): get_fault(), The persona bound to this ticket's leak terms. Lives here, not in the chat…, The failure this guards is silent: a table entry listing one step for a two-…, test_every_http_fix_has_a_step_for_every_action_of_the_canonical_path(), Built from the store's own rows, so it cannot disagree with history., A ticket nobody closed was never written to the store — which is exactly why…, The shift gates arrivals, not the technician. A ticket already open at five…, test_an_open_ticket_is_still_workable_after_the_shift_ends() (+12 more)

### Community 20 - "capture_baseline"
Cohesion: 0.14
Nodes (26): capture_baseline(), check_invariants(), test_fault_conforms(), parametrize, Seeded before the baseline, a distractor is inherited world state., A seeded anomaly must not make a legitimate repair fail., test_distractor_does_not_break_a_canonical_fix(), test_distractor_is_invariant_clean() (+18 more)

### Community 21 - "ticket.py"
Cohesion: 0.23
Nodes (13): get_distractor(), AfterAction, _kb_suggestions(), BaseModel, The after-action report. The report, not the score, is why the drill transfers…, Grade, BaseModel, What the technician actually achieved on one ticket. Grading never asks a fault… (+5 more)

### Community 22 - "Ticket"
Cohesion: 0.18
Nodes (8): questions_before_first_mutation(), How many questions the technician asked before touching anything. Both…, BaseModel, datetime, Hand off to tier-2. Not a close — `review_escalation()` decides whether it…, A tier-2 bounce: back to the technician, disposition undecided again., A tier-2 acceptance. Records what tier-2 said before closing. The bounce path…, Ticket

### Community 23 - "test_persona_binding.py"
Cohesion: 0.13
Nodes (12): DeadClient, Degradation is session state, so it has to travel back to the origin. The queue…, Returns whatever it is told to, and records the prompts it saw., Layer 3 filters output. Telling the model the forbidden word hands it the…, Nothing listening on localhost., StubClient, test_a_bindings_fallback_marks_the_origin_degraded(), test_binding_does_not_mutate_the_original() (+4 more)

### Community 24 - "_mailbox"
Cohesion: 0.07
Nodes (13): ExternalForwardingRule, _is_external(), _mailbox(), _mailbox_is_gone(), _mailbox_owners(), MailboxFull, Random, Escalate-correct because *acting* is the mistake: deleting the rule destroys… (+5 more)

### Community 25 - "Action"
Cohesion: 0.13
Nodes (6): Action, ActionResult, A write against the environment., Update the driver on every workstation that has this printer. The per-…, Destructive on purpose. Nothing in the catalog is fixed by deleting a mailbox,…, SimulatedEnvironment

### Community 26 - "Store"
Cohesion: 0.21
Nodes (8): Connection, Path, The WHERE clause that keeps one run's rows apart from another's. Rows written…, Closed tickets on disk, scoped to the run that wrote them. The database…, Store, fixture, store(), test_init_is_idempotent()

### Community 27 - "UserSymptoms"
Cohesion: 0.18
Nodes (13): Only what a non-technical person can perceive. The sole persona input., UserSymptoms, Model-backed persona against an OpenAI-compatible local endpoint (LM Studio).…, ChatTurn, PersonaCard, BaseModel, Who is on the other end of the ticket. Derived from AD, never from the fault., build_system_prompt() (+5 more)

### Community 28 - "test_distractors.py"
Cohesion: 0.15
Nodes (15): Distractor, Protocol, all_distractors(), Distractor registration, mirroring `faults/registry.py`. Kept separate from the…, register_distractor(), cases(), Conformance harness for the whole distractor catalog. Mirrors…, A fixed five was fine against thirteen faults and is not against thirty-one:… (+7 more)

### Community 29 - "GatewayMisconfigured"
Cohesion: 0.06
Nodes (10): GatewayMisconfigured, NoDhcpLease, Random, A mask narrow enough that the machine believes the servers are on some other…, The differential against every DNS fault: names still resolve and everything…, Left behind by a project that ended: the proxy it points at was decommissioned.…, StaleProxy, StaticDnsMisconfig (+2 more)

### Community 30 - "DuplicateStaticIp"
Cohesion: 0.18
Nodes (5): DuplicateStaticIp, _lowest_hostname(), _partner_of(), Whose address this machine ends up holding. Deterministic rather than random:…, A cascade in the network domain: one wrong address, two people affected.…

### Community 31 - "ResolutionPath"
Cohesion: 0.10
Nodes (13): The swap point. Everything above this boundary — tools, faults, session, web —…, FaultBase, BaseModel, Who phones this in. `None` means "whoever the placement points at" — the…, Defaults for every optional `Fault` member. The protocol grew in Phase 2a. Ten…, ResolutionPath, CorruptProfile, FailingDisk (+5 more)

### Community 32 - "test_tier2.py"
Cohesion: 0.25
Nodes (15): BaseModel, review_escalation(), Tier2Response, Ownership is judged first: a good note doesn't change who owns it., The acceptance carries the fault's `escalation_reason`, and it is the only…, test_a_bounce_reopens_the_ticket_and_leaves_a_tier2_turn(), test_a_fixable_fault_is_bounced_back(), test_a_fixable_fault_is_bounced_even_with_a_well_evidenced_note() (+7 more)

### Community 33 - ".build"
Cohesion: 0.09
Nodes (27): main(), `uv run python -m vitsc` — the normal way to start the drill. Uses…, AppSession, BaseModel, datetime, Path, A single in-process session, not a per-request one — there is exactly one…, Whether the player is reading template text rather than model text. Read… (+19 more)

### Community 34 - "ClockSkew"
Cohesion: 0.06
Nodes (9): ClockSkew, DiskFull, DnsClientDisabled, Random, A service set to Disabled rather than merely stopped, which is the differential…, The machine's clock has drifted far enough that the domain stops trusting it.…, The cheap endpoint ticket, and the one that teaches the process table. Nothing…, RunawayProcess (+1 more)

### Community 35 - "test_end_to_end.py"
Cohesion: 0.13
Nodes (24): create_app(), _app(), escalate_via_http(), parametrize, Submit the fault's canonical fix through POST /ticket/{id}/tool, exercising the…, Three tickets, one fix, all three grade cleared — over HTTP only. The point of…, The teaching path: hand it off, get it back, fix it. A fixable fault is bounced…, The mail slice end to end: a mailbox read, a quota raise, a clean close. (+16 more)

### Community 36 - "card_for"
Cohesion: 0.27
Nodes (12): card_for(), Random, Build the persona card for an AD user. Seeded off `user.sam` by default, so the…, The template can only echo symptom fields, so every fault's replies must stay…, _symptoms(), test_card_is_derived_from_the_ad_user(), test_card_is_stable_for_the_same_person(), test_history_is_accepted_but_does_not_crash() (+4 more)

### Community 37 - "test_store.py"
Cohesion: 0.23
Nodes (14): closed_ticket(), A database created before Task 6 must survive `init()` being called again., The defect this column exists for, found by running the real app twice.…, A database from an earlier release has NULL `session_id`. Those rows are…, test_a_new_session_does_not_inherit_an_earlier_one_s_rows(), test_after_action_round_trips(), test_cascade_id_is_none_for_a_single_ticket(), test_cascade_id_round_trips() (+6 more)

### Community 38 - "Phase 2a Depth Mechanics Implementation Plan"
Cohesion: 0.18
Nodes (13): Mail domain (world model + tools + faults), Phase 2a Depth Mechanics Implementation Plan, Design decision: mail gets a real layer slice, not simulated symptoms, Task 11: The KB tool and after-action links, Task 12: The mail world model, Task 13: Mail query and action kinds, Task 14: The mail console tool, Task 16: End-to-end coverage for every new surface (+5 more)

### Community 39 - "LMStudioPersona"
Cohesion: 0.10
Nodes (24): setter, LMStudioPersona, A copy scrubbing this ticket's vocabulary, sharing everything else. A copy…, DeadClient, The technician is the model's 'user'; the persona is the 'assistant'., A thinking model that spends its whole token budget reasoning answers with…, 120 tokens was all reasoning and no answer for a thinking model., Mimics the surface of openai.OpenAI that LMStudioPersona uses. (+16 more)

### Community 40 - "Query"
Cohesion: 0.15
Nodes (4): Observation, BaseModel, Query, A read against the environment. Never mutates.

### Community 41 - "mail.external_forwarding_rule fault"
Cohesion: 0.20
Nodes (12): Knowledge base (vitsc.kb), is_present() must gate on both forwarding_smtp and rule halves, mail.external_forwarding_rule fault, mail.mailbox_full fault, _read_mail_rules content-sized column widths fix, Pull Request #10 (merged, Tasks 15-17), Pull Request #9 (parallel Task 15 implementation), KB articles are procedural, never an answer key (+4 more)

### Community 42 - "Phase 2a Handoff Document"
Cohesion: 0.20
Nodes (12): Phase 2a Handoff Document, remote clear-disk with no gb silently succeeds (open thread), Design spec deleted in commit dbcd2bb, Two paths to Disposition.ESCALATED (open design question), Fixed eight-hour shift (session/shift.py), Verifying the Model-Backed Persona (guide), Degraded banner on model outage, REQUEST_TIMEOUT_SECONDS (30s) transport setting (+4 more)

### Community 43 - "EmptyReplyError"
Cohesion: 0.50
Nodes (3): RuntimeError, EmptyReplyError, The model answered, but with no text to show.

### Community 44 - "Meridian Freight Co. company.yaml seed data"
Cohesion: 0.18
Nodes (11): Meridian Freight Co. company.yaml seed data, HR-Share-RW group with no share behind it (closed gap), MER-DC-01 (domain controller), MER-FS-01 (file server), MER-MB-01 (mail server), MER-PRT-01 (print server), meridian.local domain, KB: The Meridian estate, at a glance (+3 more)

### Community 45 - "session/queue.py"
Cohesion: 0.08
Nodes (25): Fault, Protocol, Random, difficulty_weight(), forgive(), The fault scheduler and the ticket queue. This is what makes a session…, Who phones this in, for a fault that does not declare its own reporters. User…, Who actually gets a ticket for this fault instance. `fault.reporters()` names… (+17 more)

### Community 46 - "world/models.py"
Cohesion: 0.14
Nodes (26): The distractor catalog. Eleven honest anomalies (spec §4): each is real,…, The v1 backend: an in-memory world model. Handlers read and write `self.world`…, ADGroup, ADUser, DistributionList, JobStatus, Machine, Mailbox (+18 more)

### Community 47 - "test_web_close.py"
Cohesion: 0.17
Nodes (14): client(), fixture, A disposition the drill does not review is not one it accepts. Removing the…, Apply the fault's canonical resolution directly through the environment., Phase 2a left two paths to `Disposition.ESCALATED` and they were not…, solve(), test_after_action_reveals_the_root_cause_only_after_closing(), test_closed_ticket_leaves_the_active_queue() (+6 more)

### Community 48 - "._reachable"
Cohesion: 0.19
Nodes (7): Can this machine get a packet to that address at all? On-subnet traffic needs…, What `ipconfig` would print — an APIPA address when the lease failed., Whether two addresses look local to each other under one mask., DNS resolution, honouring the querying machine's own resolvers. Three things…, What the adapter is actually using — APIPA brings its own mask., A machine with no lease has no default route, which is what `ipconfig` already…, _same_subnet()

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
Nodes (17): priority_for(), The *system's* triage call, which the player's own is graded against. Impact…, make_ticket(), parametrize, Every sign-in blocker is P1 for the most junior user in the org.…, A cascade is impact by definition, whatever the fault's own difficulty., test_a_harder_fault_outranks_an_easier_one_for_the_same_person(), test_a_manager_outranks_a_clerk_for_the_same_fault() (+9 more)

### Community 56 - "World"
Cohesion: 0.05
Nodes (19): DriverAfterModelSwap, _first_user_of(), _installed_printers(), _print_servers(), PrinterOffline, Random, The reference cascade fault: one outage, several tickets. The pair with…, The device itself, not the queue and not the workstation. The cheapest ticket… (+11 more)

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

### Community 78 - "OwnerlessDistributionList"
Cohesion: 0.12
Nodes (4): OwnerlessDistributionList, The mail domain's cascade, and the one fault in the catalog placed on a server…, The person who managed a distribution list left, so nobody can change who is on…, TransportStalled

### Community 80 - "Review Focus"
Cohesion: 0.18
Nodes (10): Global Constraints, Helpdesk Workbench UI Implementation Plan, Review Focus, Self-review record, Task 1: Shared shell, navigation, and live shift rail, Task 2: Scannable, keyboard-operable ticket queue, Task 3: Active case, conversation, and technician workbench, Task 4: Escalation, resolution, after-action, and secondary pages (+2 more)

### Community 81 - "AGENTS.md"
Cohesion: 0.22
Nodes (7): Architecture, Commands, Core design principle, Placement sentinels, The conformance harness, What this is, Where the code deliberately diverges from the plan

### Community 84 - "NestedGroupMembership"
Cohesion: 0.20
Nodes (4): `ACC-Share-RW` -> `ACC-Staff`. The convention lives here, beside the sentinel…, sub_group_name(), NestedGroupMembership, The account *is* in a group whose name looks right, and the share still refuses…

### Community 91 - "CachedCredentialsExpired"
Cohesion: 0.22
Nodes (3): CachedCredentialsExpired, A workstation's cached domain sign-in lets a user reach their desktop even when…, _workstations()

### Community 96 - ".apply"
Cohesion: 0.40
Nodes (3): CurrentEmployeeDelegate, _delegate_for(), A current employee to stand in as the assistant. The next person in the owner's…

### Community 97 - "vercel.json"
Cohesion: 0.40
Nodes (4): git, deploymentEnabled, ignoreCommand, $schema

## Knowledge Gaps
- **75 isolated node(s):** `vitsc`, `$schema`, `deploymentEnabled`, `ignoreCommand`, `What this is` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `World` connect `World` to `test_grading.py`, `load_world`, `Random`, `Placement`, `test_queue.py`, `faults/base.py`, `test_distractor_registry.py`, `capture_baseline`, `ticket.py`, `_mailbox`, `test_distractors.py`, `GatewayMisconfigured`, `DuplicateStaticIp`, `ResolutionPath`, `test_tier2.py`, `ClockSkew`, `session/queue.py`, `world/models.py`, `OwnerlessDistributionList`, `NestedGroupMembership`, `CachedCredentialsExpired`, `.apply`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Why does `Placement` connect `Placement` to `test_grading.py`, `Random`, `test_queue.py`, `faults/base.py`, `test_distractor_registry.py`, `ticket.py`, `_mailbox`, `test_distractors.py`, `GatewayMisconfigured`, `DuplicateStaticIp`, `ResolutionPath`, `ClockSkew`, `Query`, `session/queue.py`, `world/models.py`, `World`, `OwnerlessDistributionList`, `NestedGroupMembership`, `CachedCredentialsExpired`, `.apply`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `load_world()` connect `load_world` to `test_tier2.py`, `.build`, `test_grading.py`, `test_simulated_env.py`, `card_for`, `test_store.py`, `test_tools_rest.py`, `TemplatePersona`, `test_queue.py`, `all_faults`, `world/models.py`, `test_faults_mail.py`, `capture_baseline`, `test_ticket.py`, `test_persona_binding.py`, `World`, `get_tool`, `test_distractors.py`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `SimulatedEnvironment` (e.g. with `Grade` and `SessionQueue`) actually correct?**
  _`SimulatedEnvironment` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `vitsc`, `$schema`, `deploymentEnabled` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `htmx.min.js` be split into smaller, more focused modules?**
  _Cohesion score 0.0814772510946126 - nodes in this community are weakly interconnected._
- **Should `test_grading.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0689873417721519 - nodes in this community are weakly interconnected._