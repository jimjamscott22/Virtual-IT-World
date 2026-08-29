---
id: identity-missing-drive
title: A mapped drive that stopped working
domain: identity
keywords: [drive, mapped drive, share, missing drive, s drive, permission]
---

A department drive letter is a mapping to a network path, and access to
that path is gated by group membership — not by the mapping itself. The
mapping can be completely unchanged and the drive can still stop opening,
because the thing that actually decides access lives elsewhere.

## Check

1. `ps Get-PSDrive -Name S:` (or whichever letter the user reports) on their
   machine, to confirm what path the mapping actually points at right now.
   A mapping pointing at a path that no longer exists reads differently
   from one pointing at a path the user simply can't reach.
2. Find which security group gates that path, then check whether the user
   is currently a member of it: `ad get-group -group <name>`. Compare that
   against who *should* be in it, based on their department.
3. Separate two different findings that look the same from the user's
   chair: the mapping itself being wrong or gone, versus the mapping being
   fine but the underlying permission having been pulled. Only one of those
   two is a group-membership problem.
4. If membership looks right but access still fails, don't assume the group
   check was pointless — a stale mapping and a real permissions change can
   both be true at once, and ruling one out is still progress.

## Notes

A drive letter is not the resource. It's a shortcut to one, and shortcuts
can go stale independently of whatever they point at.
