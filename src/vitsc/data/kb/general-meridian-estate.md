---
id: general-meridian-estate
title: The Meridian estate, at a glance
domain: general
keywords: [meridian, naming, subnet, ou, server, hostname, topology, estate]
---

Meridian Freight Co. runs a small, flat estate. It doesn't change shape
often, so it's worth knowing cold rather than looking up every time.

## Notes

**Domain and network.** Everything lives under `meridian.local`, on a single
subnet. There is one domain controller, one file server, and one print
server — no branch offices, no second site, no VPN concentrator to rule out.

**Hostnames tell you the role.** `MER-DC-01` is the domain controller.
`MER-FS-01` is the file server — every department share lives there.
`MER-PRT-01` is the print server — every printer in the building is queued
through it, even though each workstation only has one installed locally.
Workstations are `MER-WS-0xx`; the number is just an inventory tag, not a
department code.

**Organizational units mirror departments.** Accounting, Operations, Sales,
Warehouse, and HR each have their own OU, and each department has its own
security group (named `<DEPT>-Share-RW`) gating access to its own share on
the file server. A person's OU and their share-group membership should
agree — when they don't, that's worth noticing on its own.

**Printer names carry their department.** `PRT-ACC-01`, `PRT-OPS-01`,
`PRT-WH-01` — the prefix tells you who normally uses it, even though the
physical device and its queue both live on `MER-PRT-01`.

## Check

1. `ad get-group -group <name>` to see who's actually in a department's
   share group right now, rather than assuming it matches the org chart.
2. Every workstation and server hostname, printer name, and share path in
   this drill follows the conventions above — if something doesn't fit the
   pattern, that mismatch is itself worth a second look.
