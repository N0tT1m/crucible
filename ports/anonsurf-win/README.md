# anonsurf-win

Force outbound traffic through Tor on Windows. Two backends; pick the one
that matches your threat model and host configuration.

## Backends

| Backend         | What it does                                           | Pros                                | Cons                                                  |
|-----------------|--------------------------------------------------------|-------------------------------------|-------------------------------------------------------|
| `--mode proxy`  | Configures system proxy + DNS to Tor (127.0.0.1:9050) | No driver, works on any Windows     | Apps that ignore system proxy will leak              |
| `--mode tun`    | Wintun virtual adapter + userspace router → Tor SOCKS  | All TCP forced through Tor          | Needs Wintun driver (signed, MIT license, easy install) |
| `--mode wfp`    | Block all outbound traffic except Tor's process via WFP| Hard kill-switch on top of either   | Needs admin; doesn't itself route, only blocks leaks  |

The `enable` command applies a backend; `--mode tun` is recommended for new
setups and `--mode proxy` is the no-driver fallback.

## Commands

```powershell
.\bin\anonsurf-win.ps1 enable  --mode tun       # admin shell
.\bin\anonsurf-win.ps1 disable --mode tun
.\bin\anonsurf-win.ps1 status
.\bin\anonsurf-win.ps1 changeid                  # NEWNYM via control port
```

## Caveats

- DNS leaks: many Windows apps cache DNS; flush with `ipconfig /flushdns`.
- Teredo / IPv6: backend disables both — rolling back on `disable`.
- WSL2: WSL bypasses the Windows network stack; if you run WSL the host-side
  routing here doesn't cover the guest. Run `tor` inside WSL too, or use the
  `--mode wfp` kill-switch which catches the WSL vEthernet adapter.
