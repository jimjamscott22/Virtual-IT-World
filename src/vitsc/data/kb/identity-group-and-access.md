---
id: identity-group-and-access
title: Access granted but still refused
domain: identity
keywords: [group, access, permission, denied, nested, folder]
---

"They told me I was given access and it still doesn't work" is its own
complaint, distinct from access that never existed. The grant may have landed
somewhere that does not reach the resource.

## Check

1. `share.access` first, from the person's own machine — confirm what the
   file server actually says. Access denied and path not found are different
   problems with different causes.
2. `ad get-user -sam <sam>` — read the groups listed against the account.
   Write them down; do not assume one of them is the right one.
3. `print` the share's own requirement: which single group does that folder
   ask for? Compare the two lists rather than glancing at them. A name that
   starts with the same department prefix is not the same name.
4. `ad get-group -group <the group the share requires>` — read both its direct
   members and anything nested inside it. A group can hold groups, and a
   person inside one of those is granted as surely as a direct member.

## Notes

Meridian's shares each require exactly one group, and the group is named for
the department with a `-Share-RW` suffix. Anything else with a department
prefix was created by somebody for some other purpose, and being in it grants
nothing on its own.

Two ways to finish once you know what is missing: put the inner group inside
the one the share requires, or grant the person directly. Ask which one the
site expects before choosing — the first scales to the next person, the second
does not.
