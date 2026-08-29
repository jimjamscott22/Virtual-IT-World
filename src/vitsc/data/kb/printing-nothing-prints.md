---
id: printing-nothing-prints
title: Nothing prints
domain: printing
keywords: [printer, print, spooler, queue, nothing prints]
---

Print jobs that vanish without an error are almost always stopped between
the workstation and the print server, not lost on the printer itself.

## Check

1. Ask how many people are affected. One person points at their
   workstation; several people pointing at the same printer point at the
   print server.
2. `remote services -host <workstation>` — confirm the local spooler.
3. `print get-printer -printer <printer>` — confirm the queue and its host.
4. `remote services -host <print server>` — confirm the server's spooler.

## Notes

Meridian hosts every printer on MER-PRT-01. Printer names carry their
department: PRT-ACC-01, PRT-OPS-01, PRT-WH-01.
