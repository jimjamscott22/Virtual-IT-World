---
id: network-address-settings
title: Reading a workstation's address settings
domain: network
keywords: [ipconfig, address, mask, gateway, proxy, subnet, network settings]
---

Four numbers decide whether a machine can talk to anything: its own address,
the mask that tells it which addresses are local, the router it sends
everything else to, and the resolver that turns names into addresses. Any one
of them being wrong looks like "the network is down" to the person reporting
it, and each one fails differently.

## Check

1. `net ipconfig -from <host>` and read all four lines, not just the address.
   Compare them against a working machine on the same floor rather than
   against memory.
2. `net ping -host 10.20.10.6 -from <host>` — an address, so no name lookup is
   involved. This separates "cannot find the name" from "cannot get there".
3. `net ping -host 8.8.8.8 -from <host>` — somewhere outside the building. If
   step 2 works and this does not, the problem is what happens to traffic that
   has to leave the site.
4. `net get-proxy -from <host>` — a browser can be sent somewhere no other
   program goes. Mail arriving while web pages fail is the shape of this.

## Notes

What the failures look like, in the order they are easiest to confuse:

- Name lookups fail, addresses work: the resolver.
- Addresses fail too, including things on your own floor: the machine's own
  idea of which addresses are local.
- The building works, the outside world does not: whatever traffic leaving the
  site depends on.
- Only the browser fails: whatever the browser is configured to go through.

Meridian's workstations all take their settings automatically, so any machine
holding them by hand had somebody's hands on it. `net renew -from <host>` puts
every one of the four back at once, which is usually faster than setting them
one at a time — and worth knowing before you start typing values in.
