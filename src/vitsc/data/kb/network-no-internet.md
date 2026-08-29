---
id: network-no-internet
title: No internet, or nothing loads
domain: network
keywords: [internet, network, dns, no connection, cannot browse, ipconfig, cannot reach]
---

"The internet is down" almost never means the internet is down. It means
one of a handful of independent layers between the workstation and whatever
it's trying to reach isn't working, and each layer fails differently.

## Check

1. `net ipconfig -from <machine>` first, before anything else. Read the
   address it reports:
   - A normal-looking address on the subnet (`10.20.10.x` here) means the
     machine has basic connectivity and the problem is further up the
     chain.
   - An address starting `169.254.x.x` is a self-assigned address — the
     machine gave up waiting for one to be handed to it and picked its own.
     A machine in this state can't reach anything past its own segment,
     including the file server or the printer server, not just "the
     internet".
   - Compare the DNS servers listed against what every other machine on the
     estate uses. One machine pointed somewhere different from its peers is
     a configuration drift worth chasing on its own, separate from whether
     the address itself looks fine.
2. Once the address looks sane, separate *resolving* a name from *reaching*
   it — they fail independently:
   - `net nslookup -host <name>` — does the name turn into an address at
     all?
   - `net ping -host <name>` — once you have an address, can traffic
     actually get there?
   A name that resolves but doesn't ping, and a name that fails to resolve
   at all, point at different layers and different next steps.
3. Only after separating those two should you decide whether the fix is
   something the workstation asks for again, or something about what it's
   been told to ask.

## Notes

"No internet" is what the user experiences. What you're actually
diagnosing is which layer — addressing, name resolution, or reachability —
stopped agreeing with the rest of the estate.
