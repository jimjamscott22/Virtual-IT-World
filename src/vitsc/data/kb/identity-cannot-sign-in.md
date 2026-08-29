---
id: identity-cannot-sign-in
title: Reading an account that can't sign in
domain: identity
keywords: [sign in, login, locked, password, account, cannot log in, lockout]
---

"I can't sign in" is a symptom, not a finding. A single account lookup
returns several independent fields, and they don't all mean the same thing —
mixing them up is the fastest way to apply the wrong fix.

## Check

1. `ad get-user -sam <sam>` and read every field back, not just the first
   one that looks relevant:
   - **Enabled** — whether the account exists and is turned on at all. A
     disabled account was turned off on purpose by someone; it did not
     "expire" or "lock" on its own.
   - **Locked** — a separate flag from enabled. An account can be perfectly
     enabled and still locked, and vice versa.
   - **Bad password count** — how many recent failed attempts have been
     recorded. A nonzero count with the account not yet locked is an early
     warning, not the problem itself.
   - **Password expiry** — a date, not a flag. A password past its expiry
     date stops working the same way a locked account does, from the user's
     side, but the underlying state and the fix are both different.
2. Ask when the last successful sign-in was, and whether the user changed
   anything recently (new device, changed their own password, been away).
   That answer usually points straight at which of the four fields above
   changed.
3. Treat "enabled", "locked", and "expired" as three separate yes/no
   questions you answer in order, not three names for the same problem.

## Notes

Two people can report what sounds like an identical complaint and have
completely different fields at fault underneath — that's the differential
this article exists to teach, not any one specific value.
