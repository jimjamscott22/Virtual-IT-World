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
