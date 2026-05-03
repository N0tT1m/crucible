# aircrack-mac

A native-macOS slice of the aircrack-ng workflow, plus a Lima passthrough for
the parts Apple disallows on the internal Wi-Fi card.

## What works on the internal Wi-Fi (no extra hardware)

| Subcommand        | Status | Mechanism                                                           |
|-------------------|--------|---------------------------------------------------------------------|
| `aircrack-mac sniff`   | works  | `airport en0 sniff <ch>` → pcap (private `Apple80211.framework`) |
| `aircrack-mac scan`    | works  | `airport -s` (BSSID/SSID/channel/RSSI/sec)                       |
| `aircrack-mac crack`   | works  | wraps `brew install aircrack-ng` (offline WPA/WEP from pcap)     |
| `aircrack-mac wordlist`| works  | thin wrapper around `crunch` / common rockyou paths              |

## What requires external hardware + Lima

Apple removed monitor-mode/injection from public APIs around macOS 11. The
internal card cannot deauth, replay, or fake-auth. There is no software fix —
KEXT signing + DriverKit policy mean a replacement Wi-Fi driver cannot ship.

For the active attacks (`aireplay-ng`, `airodump-ng --write` while injecting,
WPS/PMKID brute, etc.) the supported path is:

1. Plug in a supported USB adapter (Alfa AWUS036ACH, AWUS036NHA, etc.).
2. `aircrack-mac inject up` boots a Lima VM with a pinned Linux kernel +
   aircrack-ng + the right drivers (rt2800usb, 8812au, etc.).
3. `aircrack-mac inject pass <usbid>` claims the adapter for the VM via
   the Virtualization framework's USB device-attach API.
4. From there you `aircrack-mac inject shell` and run upstream aircrack-ng
   normally — it just runs in the VM with the USB radio attached.

This split keeps the slow/CPU-bound pipeline (capture, analysis, cracking)
on bare metal where it's fastest, and isolates the kernel-touching work
in a VM that can be torn down between sessions.

## Install

```sh
./install.sh    # runs: brew install aircrack-ng tcpdump crunch lima
                # symlinks ./bin/aircrack-mac to /usr/local/bin
```

## Layout

- `bin/aircrack-mac` — dispatcher (bash)
- `lib/sniff.sh`     — wraps `airport sniff`
- `lib/scan.sh`      — wraps `airport -s`
- `lib/crack.sh`     — wraps `aircrack-ng`
- `lib/lima_inject.sh` — Lima VM lifecycle + USB passthrough
