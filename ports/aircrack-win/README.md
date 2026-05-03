# aircrack-win

Windows-native slice of aircrack-ng plus a WSL2 + usbipd-win bridge for the
parts that need real driver-level access to a Wi-Fi radio.

## Why two halves

The Windows internal-Wi-Fi story is essentially the same as macOS: the stock
WLAN drivers don't expose monitor mode or frame injection. Active attacks
need either:

1. A capture/injection-capable USB adapter (Alfa AWUS036ACH etc.) running
   under WSL2 with the upstream Linux drivers, USB attached via
   [usbipd-win](https://github.com/dorssel/usbipd-win); or
2. Vendor-specific drivers (e.g. Acrylic Wi-Fi Professional + a supported
   chipset). This port doesn't ship those — they're paid and chipset-specific.

What does work natively:

| Subcommand              | Status | Mechanism                                                |
|-------------------------|--------|----------------------------------------------------------|
| `aircrack-win scan`     | works  | `netsh wlan show networks mode=Bssid`                    |
| `aircrack-win sniff`    | works  | Npcap + dumpcap (Wireshark CLI), monitor mode if driver supports |
| `aircrack-win crack`    | works  | bundles aircrack-ng for Windows (precompiled)            |
| `aircrack-win wordlist` | works  | rockyou download + crunch (Scoop)                        |
| `aircrack-win inject`   | works  | WSL2 helper: `wsl --install`, `usbipd attach`, drop into VM |

## Install

```powershell
.\install.ps1   # winget aircrack-ng + Npcap + WSL2 if missing
```

Run elevated (Administrator) for Npcap install and usbipd binding.

## Layout

- `bin\aircrack-win.ps1`  — dispatcher
- `lib\scan.ps1`          — `netsh wlan` JSON-ish parser
- `lib\sniff.ps1`         — dumpcap wrapper (Npcap)
- `lib\crack.ps1`         — passthrough to bundled `aircrack-ng.exe`
- `lib\wordlist.ps1`      — rockyou + crunch helpers
- `lib\wsl_inject.ps1`    — usbipd-win passthrough into WSL Ubuntu
