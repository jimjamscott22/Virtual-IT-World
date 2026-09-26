---
id: endpoint-profile-and-services
title: When one machine misbehaves and the account is fine
domain: endpoint
keywords: [profile, service, disabled, clock, time, process, slow, workstation]
---

The useful question for a single misbehaving machine is whether the same person
is fine somewhere else. If they are, the account is not the problem and the
machine is — and there are only a few places to look.

## Check

1. **Does it follow the person or stay with the desk?** Ask them to sign on to
   another machine. This one question separates half the endpoint tickets from
   half the identity tickets, and it costs nothing.
2. `remote inspect -host <host>` — read the whole dump, not the line you came
   for. Two fields get skimmed past and both cause tickets that look like
   something else: what the machine thinks the time is, and when it last spoke
   to the domain.
3. `remote services -host <host> -service <name>` — and read the *state*, not
   just whether the name appears. A service can be stopped, or it can be
   disabled, and those need different repairs.
4. `remote processes -host <host>` — for anything described as slow rather than
   broken. One entry far above the others is the whole ticket.

## Notes

Three traps worth naming:

- **Stopped is not disabled.** Restarting a disabled service fails, and the
  service manager tells you why. Change the startup type first, then start it —
  and check it is actually running afterwards, because setting a service to
  start automatically does not start it today.
- **An empty desktop with plenty of free space is a different ticket from an
  empty desktop with none.** In one the stored settings failed to load because
  there was no room; in the other they are damaged. Freeing space fixes the
  first and does nothing at all for the second.
- **A machine whose clock is far out gets refused by the domain**, and the
  refusal mentions your account rather than the time. If sign-in and shares
  both fail on one machine and work everywhere else, read the clock before you
  touch the account.
