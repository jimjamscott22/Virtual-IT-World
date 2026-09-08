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
