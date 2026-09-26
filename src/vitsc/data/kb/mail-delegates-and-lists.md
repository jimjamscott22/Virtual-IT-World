---
id: mail-delegates-and-lists
title: Who else can act on a mailbox
domain: mail
keywords: [delegate, permission, distribution group, list, owner, shared mailbox]
---

Some mail tickets are not about mail failing. They are about mail working for
somebody who should no longer be involved, or about nobody being able to change
something. Neither shows up in a queue or a quota.

## Check

1. `mail get-delegates -sam <sam>` — who else can open this mailbox, and whether
   each of those accounts still exists. An entry whose account is gone is a
   permission nobody is watching: the person left, the access did not.
2. `mail get-rules -sam <sam>` — read these alongside the delegates, not
   instead of them. Mail being answered before the owner sees it has more than
   one possible explanation and you want to rule out both.
3. `mail get-lists -host <mail server>` — every group address, who manages it,
   and whether that manager still exists. A list with no manager cannot be
   changed by anyone, which is how a leavers' list keeps delivering for months.

## Notes

"Somebody is reading my mail" deserves care rather than speed. Find out *how*
before you remove anything: an access grant that has been there since somebody
left is untidy, and a redirection that appeared last week is not the same kind
of problem at all. If what is interesting about the ticket is when and how the
change was made, removing the change removes the answer — see the article on
when a ticket is not yours to close.

Meridian's group addresses are managed by a named person, and the convention is
that the list falls to the relevant department head rather than to whoever asks.
Check who that should be before assigning it.
