# anonsurf-mac

Force all outbound TCP through Tor, redirect DNS to Tor's DNSPort, and block
non-Tor leaks at the firewall layer. macOS port of the Parrot/AnonSurf idea.

## How it works

| Layer | Linux AnonSurf            | anonsurf-mac                                     |
|-------|---------------------------|--------------------------------------------------|
| Tor   | `tor` daemon, TransPort   | `tor` (brew) with TransPort 9040 + DNSPort 5353  |
| NAT   | iptables nat OUTPUT       | `pf` `rdr-anchor` redirecting outbound → Tor     |
| Leaks | iptables filter DROP      | `pf` `block-anchor` for non-Tor egress           |
| DNS   | resolv.conf swap          | `networksetup -setdnsservers ... 127.0.0.1`      |
| MAC   | macchanger                | `ifconfig en0 ether <random>` (changeid)         |

## Caveats

- Requires `sudo` — pf, network DNS changes, and ifconfig all do.
- The pf approach catches everything routed through the kernel, but a few
  Apple system services use raw sockets or talk to Apple-only servers; for a
  hard guarantee against those leaks, prefer the Network Extension build
  (requires a paid Developer ID and `com.apple.developer.networking.networkextension`
  entitlement — out of scope for this port).
- macOS DHCP can rewrite DNS on network change. `enable.sh` re-pins after each
  `SystemConfiguration` change; restart `anonsurf-mac` after roaming.

## Commands

```sh
sudo anonsurf-mac enable    # start tor, install pf rules, swap DNS
sudo anonsurf-mac disable   # tear down rules, restore DNS, stop tor
     anonsurf-mac status    # show pf anchor + tor process + current IP
sudo anonsurf-mac changeid  # randomize MAC + signal tor for new circuit
```
