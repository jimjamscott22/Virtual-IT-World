# Phase 2b: catalog breadth

**Status:** outline only. Written at the end of Phase 2a, deliberately as a
skeleton — the per-task detail belongs in a plan written against finished 2a
code rather than guessed at now. Fill it in before starting Task 1.

**Prior plan:** `docs/superpowers/plans/2026-08-14-phase-2a-depth-mechanics.md`
(Tasks 1–17, complete).

**Spec:** `docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`
— **not in the working tree**; deleted in commit `dbcd2bb` along with the
Phase 1 plan. Recover with
`git show dbcd2bb^:docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`.

---

## Goal

Phase 2a built the *mechanics* — cascades, tier-2, distractors, a knowledge
base, a mail domain — and proved each one on two or three reference faults.
2b builds the *breadth* those mechanics need to stop being visible as
mechanics.

Thirteen faults is small enough that a returning player recognises a ticket
from its opening line. **Target: 30+ faults**, so roughly 18 more, spread so
that no domain is thin and no mechanic has only one instance.

The measure of success is not the count. It is that a player who has worked
twenty tickets still cannot predict the cause from the first sentence.

## Constraints

These are inherited, not up for renegotiation in 2b:

1. **Tools read world state; they never read the fault.** Enforced by
   `tests/test_architecture.py`. A 2b fault that needs a tool to know about
   it is a wrongly designed fault.
2. **`is_present()` is the only pass/fail gate.** `canonical_resolutions()`
   stays documentation and test fixture. Any path to a healthy world counts.
3. **Symptoms survive the `JARGON` check and the fault's own `leak_terms`.**
   If the check trips, rewrite the symptom, never the check.
4. **The suite passes with nothing running on localhost.** No 2b test may
   require LM Studio.
5. **Every new fault gets full conformance coverage for free** from
   `tests/test_catalog.py`. A new *test file* is only for what the harness
   cannot express.
6. **`tests/test_end_to_end.py:HTTP_FIX` is set-equality-guarded.** Every new
   resolvable fault needs an entry in the same commit that registers it, or
   the suite goes red in between.
7. **Two roster tests enumerate the catalog by hand**
   (`test_v1_catalog_is_complete`, `test_exactly_three_faults_are_escalate_correct`).
   They exist so that adding a fault is a visible decision. Extend them
   deliberately; do not delete them to avoid the friction.

## Shape of the work

One task per fault, in the order below. Each task is: write the failing
specifics test → write the fault → conformance harness green → `HTTP_FIX`
entry → full suite → commit. The 2a plan's Task 15 is the reference for what
a fault task looks like end to end.

A task adds *new query/action kinds* only when no existing kind can express
the fault. That is the expensive kind of task (`env/simulated.py` +
`tools/*.py` + tests), and it is called out below where it is unavoidable.

| Domain | Have | Add | Candidates |
|---|---|---|---|
| identity | 4 | +3 | expired cached credentials on a laptop; a group nested one level deeper than the obvious one; a UPN/sam mismatch after a name change (escalate-correct — needs HR to confirm the legal name) |
| network | 2 | +4 | wrong subnet mask; a duplicate static IP (**cascade** — two machines, two tickets); gateway unreachable; a proxy setting left behind |
| printing | 3 | +3 | printer offline at the device; a stuck job at the head of the queue (**new action kind**: clear a print queue); a driver mismatch after a model swap |
| endpoint | 2 | +4 | corrupt user profile; a service set to Disabled rather than merely stopped (the differential against `print.spooler_stopped`); time skew breaking authentication; RAM failure (escalate-correct) |
| mail | 2 | +4 | transport queue stalled (**cascade** — several people report late mail); a delegate left over from a departed employee; an autodiscover failure; a distribution list nobody owns |

Alongside the faults:

- **New KB articles** as the estate grows. The existing eight are
  domain-level; several 2b faults will want a second article per domain
  rather than a ninth link to the same one. Same rule: procedural, never an
  answer key.
- **More distractors.** Five is thin once there are thirty faults — the noise
  floor should scale with the catalog, or a seeded anomaly starts to read as
  a tell.
- **Mail invariants** (`world/invariants.py`): a deleted mailbox, a quota set
  below current usage. Deferred from Task 12 for the right reason — an
  invariant is a new way for a fault to accuse itself, and there was nothing
  to test it against. There is now.
- **The `Disposition.ESCALATED` dropdown.** 2a left two paths to the same
  disposition: the reviewed `/ticket/{id}/escalate` flow, and the unreviewed
  option still in the close-ticket dropdown, which skips `review_escalation`
  and so produces a report with no `tier2_note`. With four escalate-correct
  faults after 2b, that inconsistency stops being cosmetic. Decide it early
  in 2b, not late.

## Settled before Task 1

All three were decided and implemented before any 2b fault was written —
which was the point of asking them first.

**The estate grew: 20 users, 10 workstations.** Twelve and six was thin for a
thirty-fault catalog, and several candidates below (a duplicate static IP, a
stuck print job) need more machines to be interesting at all. Done
append-only, so every existing row is byte-identical and no fixed-seed test
moved. Twenty people share ten machines, which keeps a machine-placed fault
from being a user-placed fault under another name. Two gaps closed on the
way: HR had a share group with no share behind it, and Sales was borrowing
Operations' printer.

**A session ends: a fixed eight-hour shift** (`session/shift.py`). Simulated
09:00–17:00, which is eight real minutes at one sim-minute per second. What
ends is the *arrivals*; tickets already open stay workable. `/shift` sums the
day from the store's own rows — closed, correct, within SLA, collateral,
still open — so it cannot disagree with the history page.

**Difficulty drives scheduling, because something already did.** The old
scheduler drew uniformly from `(fault, placement)` pairs, which weighted
every fault by how many targets it happened to have: the catalog's only
cascade has one placement and a mailbox fault has twenty, so the cascade was
dealt twenty times less often. `choose_fault_and_placement()` now picks the
fault first, weighted 5/4/3/2/1 by difficulty, then a placement uniformly.
Difficulty is the only thing that decides frequency, and the resulting mix is
roughly 21/51/19/9 across difficulties 1–4 — mostly routine, with the hard
ticket rare enough to stay surprising.

**What this means for 2b's faults.** Two consequences worth holding onto
while writing them:

- A fault's `difficulty` is now load-bearing, not decoration. Declaring 4
  because a fault *feels* involved will make it genuinely rare; declaring 1
  on something fiddly will make it the ticket the technician sees most.
  Pick it as a frequency decision as much as a hardness one.
- `placements()` no longer controls frequency, so a fault may legitimately
  attach to one specific server without becoming unreachable. That is what
  makes server-side and estate-wide 2b faults viable.

## Tasks

### Task 1: Stale cached credentials after a long absence from the network

The identity domain's first candidate ("expired cached credentials on a
laptop"), and the cheapest possible 2b task: it needs no new query/action
kind, no new `World` field, and no new tool surface. Everything it touches —
`machine.services` (read) and `machine.restart_service` (write) — already
exists and is already reachable through `remote services`, `ps Get-Service`,
and `ps Restart-Service`. That makes it a deliberate choice for Task 1: prove
the 2b groundwork (difficulty-weighted scheduling, the bigger estate) works
end to end before taking on a task that needs new plumbing (the printing
domain's stuck-queue candidate is the one flagged in the domain table as
needing that).

**The mechanism.** A workstation's cached domain sign-in lets a user reach
their desktop even when the machine's own channel to the domain controller is
broken — which is exactly what happens after an extended absence (working
from home, a long trip) if that channel needs to be re-established on return.
The user gets to their desktop fine, but everything that depends on live
domain authentication — mapped drives, printers, Outlook — fails at once.
Modelled as a `"Netlogon"` entry in the machine's existing `services` dict
(the same field `print.spooler_stopped` already uses for `"Spooler"`), gated
and cleared exactly the way that fault is: `ServiceState.STOPPED` /
`machine.restart_service`.

This is the differential against all four existing identity faults: `ad
get-user` on the affected sam comes back completely clean — not locked, not
expired, not disabled — because the account itself was never touched. The
technician has to notice that the account checks out and look at the machine
instead. It is also the first identity-domain fault placed on a `machine`
rather than a `user`, the same shape `print.spooler_stopped` and
`endpoint.disk_full` already use for a workstation-attached fault.

**Files:**
- Modify: `src/vitsc/faults/catalog/identity.py`
- Create: `src/vitsc/data/kb/identity-signed-in-but-cut-off.md`
- Modify: `tests/test_catalog.py` (`test_v1_catalog_is_complete`)
- Modify: `tests/test_end_to_end.py` (`HTTP_FIX`, `TARGET_FIELD`)

**Interfaces:**
- Consumes: `machine.services` / `machine.restart_service` (existing, from
  Phase 1's printing work), reachable today via `remote services` /
  `remote inspect`, `ps Get-Service` / `ps Restart-Service`.
- Produces: `ad.cached_credentials_expired`.

No new specifics test file: nothing here is a cascade, an escalate-correct
fault, or a fault with more than one fix path — the three reasons the
existing identity faults (all four of which also have no specifics file)
would need one. Conformance coverage from `tests/test_catalog.py`'s
parametrized harness is the whole test surface, per Constraint 5.

- [ ] **Step 1: Write the fault**

Add to `src/vitsc/faults/catalog/identity.py`, alongside a local
`_workstations()` placement helper (the same shape `network.py` and
`endpoint.py` each already define privately for their own machine-placed
faults — no shared util to extract, that duplication is this codebase's
existing convention):

```python
def _workstations(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class CachedCredentialsExpired(FaultBase):
    id = "ad.cached_credentials_expired"
    domain = "identity"
    difficulty = 2
    canonical_title = (
        "Workstation's cached domain credentials are stale after an "
        "extended absence from the corporate network"
    )
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["cached", "cache", "trust relationship", "secure channel", "netlogon"]
    escalation_is_correct = False
    kb_articles = ["identity-signed-in-but-cut-off"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].services["Netlogon"] = ServiceState.STOPPED

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].services.get("Netlogon") is not ServiceState.RUNNING

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="I can log in fine, but none of my shared drives will "
            "connect, my printer's missing, and Outlook won't stay signed in.",
            onset="I've been working from home for the last few weeks and "
            "only came back into the office this morning.",
            scope="Just me — the person next to me hasn't had any problems.",
            error_text="Outlook keeps asking for my password, I type it in "
            "correctly, and it just asks again. My drives say the network "
            "path can't be found.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.services", target=at.key, args={"service": "Netlogon"})]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Restart the Netlogon service",
                actions=[
                    Action(
                        kind="machine.restart_service",
                        target=PLACEHOLDER,
                        args={"service": "Netlogon"},
                    ),
                ],
            ),
        ]


register(CachedCredentialsExpired())
```

Needs `ServiceState` added to the module's `vitsc.world.models` import
(`identity.py` doesn't import it today — only `network.py`/`endpoint.py` do).

- [ ] **Step 2: Run the conformance harness**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: the new fault conforms across every workstation placement —
absent-then-present, `machine.services` actually differs between clean and
broken, the restart resolution clears it with no invariant violations, and
`symptoms()` contains none of its own `leak_terms` and none of `JARGON`. If
the symptom check trips, rewrite the symptom text, not the check.

- [ ] **Step 3: The KB article**

`src/vitsc/data/kb/identity-signed-in-but-cut-off.md` — a genuinely new
article, not a ninth link to `identity-cannot-sign-in`: that article's whole
premise is "the user can't get in at all," which is false here. Per the
plan's own note under "Alongside the faults," this domain earns a second
article precisely because this failure shape doesn't fit the first one.

```markdown
---
id: identity-signed-in-but-cut-off
title: Signed in locally but nothing else works
domain: identity
keywords: [signed in, drives, shares, printer, outlook, network path, cached credentials]
---

A user who reaches their desktop at all is not having the same failure as a
user who can't sign in. When the desktop loads but every drive, printer, or
mailbox connection fails at once, the account itself is rarely the problem —
start elsewhere.

## Check

1. `ad get-user -sam <sam>` first, even though it looks unrelated —
   confirming the account is enabled, not locked, and not expired rules out
   the whole "can't sign in" family in one call. If all three come back
   clean, the account was never the problem.
2. `remote services -host <workstation>` — a machine can be showing a
   perfectly normal desktop and still have the service that keeps it talking
   to the domain stopped. Compare against a machine that isn't having the
   problem.
3. Ask how long the machine has been off the corporate network. An extended
   absence — working from home, a long trip — is the most common trigger for
   this class of problem.

## Notes

A user who signed in successfully before the problem started can keep
working from the locally cached copy of their profile even while the
machine's own connection to the domain is broken — which is exactly why the
account checks out clean in step 1.
```

- [ ] **Step 4: HTTP fix table**

`tests/test_end_to_end.py`:

```python
HTTP_FIX = {
    ...
    "ad.cached_credentials_expired": ("ps", "Restart-Service"),
}

TARGET_FIELD = {
    ...
    "Restart-Service": "host",
}
```

`ps Restart-Service` already dispatches to `machine.restart_service` and is
machine-scoped (`target_key` returns `args["host"]`); the bound action's own
`args={"service": "Netlogon"}` passes straight through `query_args` unchanged
(it only renames a `name` arg to `service`, and there is no `name` arg here
to rename), so no tool code changes at all — confirmed by re-reading
`PowerShellConsole.query_args` rather than assumed.

- [ ] **Step 5: The roster test**

`tests/test_catalog.py:test_v1_catalog_is_complete` — add
`"ad.cached_credentials_expired"` to the hardcoded id set. (Not
`test_exactly_three_faults_are_escalate_correct` — this fault isn't one.)

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: all green, fourteen faults registered. Also `uv run pylint src
tests` (two-command form per `CLAUDE.md`) at 10.00/10.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(faults): add the identity domain's cached-credentials fault"
```

---

## Definition of Done

- [ ] 30+ faults registered, conforming across every placement, in all five
      domains, with no domain below five.
- [ ] At least two cascade faults in different domains, and at least four
      escalate-correct faults — still no two escalate-correct for the same
      reason.
- [ ] Every fault links at least one KB article, and every article is linked
      by at least one fault (no orphans in either direction).
- [ ] Distractor count scaled to the catalog, all passing the non-interference
      harness.
- [ ] Mail invariants land, with a fault that trips them when fixed wrongly.
- [ ] The escalation-disposition inconsistency is resolved, one way or the
      other, deliberately.
- [ ] Every fault's `difficulty` chosen as a frequency decision, not just a
      hardness one — see "Settled before Task 1" above.
- [ ] A full eight-hour shift is workable end to end, and the `/shift`
      summary reads correctly for a good shift and a bad one.
- [ ] `uv run pytest` green with nothing on localhost; `uv run pylint src`
      and `tests` at 10.00/10.
- [ ] A full ticket can be worked in the browser in all five domains, and a
      player working twenty consecutive tickets cannot predict the cause from
      the opening line.
