---
id: general-triage-first-questions
title: Before you touch anything
domain: general
keywords: [triage, first questions, scope, how many people, when did it start]
---

Every ticket starts the same way, before any tool is opened. Four questions
separate a five-minute fix from a rabbit hole, and they cost nothing to ask.

## Check

1. **What exactly is happening?** Get the words on the screen, not a summary
   of them. "It won't let me in" could be a locked account, an expired
   password, or a disabled one — three different findings that look
   identical from the user's side of the desk.
2. **When did it start?** "Since this morning" and "since I got back from
   leave" point in very different directions. A change that lines up with
   something the user did (a password reset, a new machine, coming back
   from time off) is worth asking about directly.
3. **Who else is affected?** One person reporting a problem and three people
   reporting the same problem in the same few minutes are different classes
   of ticket. The first is almost always local to that person's account or
   machine. The second usually means a shared resource — a server, a
   service, a group — is the actual target, and fixing one person's ticket
   without noticing the pattern means you'll be back here again shortly.
4. **What changed?** Not "what's broken" — what changed. A working thing
   that stops working did so because something moved: a password aged out,
   a cable came loose, a service stopped, a permission was pulled. Chasing
   the symptom without asking what changed underneath it is how a five-
   minute ticket becomes an hour.

## Notes

None of these questions require a tool. Asking them first, before running a
single command, is itself a signal worth paying attention to in your own
work — reaching for a tool before you know what you're looking for usually
means more tool calls, not fewer.
