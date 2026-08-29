---
id: mail-cannot-send-or-receive
title: Mail that won't send or won't arrive
domain: mail
keywords: [mail, email, mailbox, forwarding, rules, quota, transport, cannot send, cannot receive]
---

"My email isn't working" splits into two different complaints that need
separate answers — can't send, and can't receive — and each has its own
short list of independent causes. Don't assume they share a fix just
because they share a symptom.

## Check

1. **Mailbox size against its quota.** A mailbox at or over its limit stops
   accepting new mail even though the account itself is completely healthy.
   This is a capacity finding, not an account problem, and the fix is
   capacity, not a password reset or an account check.
2. **Inbox rules.** A rule the user doesn't remember creating — or doesn't
   remember what it does — can quietly move, delete, or redirect mail
   before the user ever sees it arrive. Ask what they expect to see and
   compare it against what the rules actually do, in order.
3. **Forwarding.** Check whether the mailbox is set to forward anywhere,
   and where. Forwarding to a colleague or a shared mailbox is a normal
   business need. Forwarding to an address outside the organization is not
   a "clean this up" ticket — treat it as a security concern and escalate
   it rather than quietly deleting the rule and moving on, even if deleting
   it also happens to fix the symptom the user reported.
4. **The transport queue.** If sending stalls for everyone rather than one
   person, the delay is more likely sitting in the mail system's own
   outbound queue than in any one mailbox. A queue backing up is a
   different scope of problem than a single mailbox misbehaving, and
   belongs on the server side of the conversation, not the individual
   account.

## Notes

Treat "can't send" and "can't receive" as two separate questions from the
first message onward — asking which one it is early saves retracing the
same four checks twice.
