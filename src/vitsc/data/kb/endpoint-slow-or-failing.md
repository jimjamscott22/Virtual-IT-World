---
id: endpoint-slow-or-failing
title: A workstation that's slow or acting strange
domain: endpoint
keywords: [slow, disk, hardware, profile, temporary profile, performance, endpoint]
---

"My computer is slow" or "it's acting weird" covers several unrelated
findings that happen to feel the same to the person sitting in front of the
machine. `remote inspect -host <machine>` returns three fields worth
checking separately, not as one combined "health" score.

## Check

1. **Free disk space.** A machine running low on space slows down in ways
   that have nothing to do with hardware failing — background processes and
   the profile system both need working room. Compare free space against
   total capacity, not just the raw number; a nearly-full small disk and a
   nearly-full large disk both count.
2. **Profile state.** A profile can load in a temporary, throwaway state
   instead of the user's normal one — often as a direct side effect of the
   disk being too full to load it properly. If you see this, check disk
   space *before* assuming the profile itself is corrupt; the two are
   frequently the same underlying event described two different ways.
3. **Disk health status.** This is reported independently of how much space
   is free — a disk can report a failing health status while still having
   plenty of room left, and a full disk in good health is a completely
   different situation from a nearly-empty disk that's failing.

## Notes

Only one of these three findings is a hardware call that ends in a
replacement ticket rather than something you can clear yourself today —
know which one before you tell the user what to expect.
