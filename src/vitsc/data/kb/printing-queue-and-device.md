---
id: printing-queue-and-device
title: Telling the queue from the device
domain: printing
keywords: [print queue, jobs, offline, printer, device, stuck, driver]
---

"Nothing prints" splits three ways, and the print queue tells you which one you
have before you touch anything.

## Check

1. `print get-jobs -printer <printer>` — the first read, every time. What the
   queue holds is the diagnosis:
   - **Empty**, and the person is certain they sent something: the job never
     reached the queue. Look at the workstation.
   - **Jobs waiting, and the device reports offline**: the queue is fine and
     the machine at the end of it is not.
   - **A job at the head that has errored, with everything behind it waiting**:
     the queue is blocked by one document, and everyone sharing that printer is
     stuck behind the same one.
   - **Jobs moving, output wrong**: it prints, so this is not a queue problem
     at all. Compare the model against the driver installed for it.
2. `print get-printer -printer <printer> -from <workstation>` — the device's
   model and the driver that workstation holds for it, side by side.
3. Ask how many people are affected, and whether anything about the device
   changed. "It was swapped over yesterday" is a different ticket from "it
   stopped this morning".

## Notes

Restarting a spooler is the reflex, and it is the wrong reflex for a blocked
queue: the job is stored, so it comes back when the service does. Clear the
queue instead.

A printer shared from MER-PRT-01 can have its driver published once from the
server rather than reinstalled at every desk. Worth knowing before you start
visiting desks — and worth checking afterwards that the desks actually picked
it up.
