# firejail-win

Firejail-shaped wrapper for Windows process isolation. The underlying
mechanisms are different — Windows doesn't have Linux namespaces — but the
goals (FS denial, network denial, capability reduction, resource caps) all
have native equivalents.

## Backend layers

| Concern        | firejail (Linux)          | firejail-win                                              |
|----------------|---------------------------|-----------------------------------------------------------|
| FS isolation   | mount/bind ns             | AppContainer profile + per-process Job Object access ACLs |
| Net isolation  | iptables                  | Windows Filtering Platform (WFP) per-app rule + WFP block |
| Process limits | rlimits                   | Job Object `JOB_OBJECT_LIMIT_*`                           |
| Caps / sec     | seccomp / capabilities    | AppContainer capabilities (deny-all is the default)       |
| Hard isolation | none in firejail          | Optional `--sandbox` mode runs the target in Windows Sandbox (lightweight VM) |

The default uses `Start-Process -UseNewEnvironment` plus a Job Object for
quick wins. The `--appcontainer` mode generates a SID + AppContainer profile
and launches via `CreateProcess` with `lpAttributeList` carrying the
container SID — that's the strong sandbox.

## Profile

Same syntax as `firejail-mac` (firejail directives → translator). On Windows
the translator emits a JSON config consumed by the Python launcher, which
then calls into `firejail_win.appcontainer.spawn()`.

## Usage

```powershell
firejail-win --profile=browser --net=none firefox.exe
firejail-win --profile=default --tmpfs=C:\Users\me\AppData\Local\Temp\test cmd.exe
firejail-win --sandbox notepad.exe   # uses Windows Sandbox (heaviest, most isolated)
```

## Install

```powershell
.\install.ps1
```

Requires Windows 10 1903+ (AppContainer) or Windows 11 (recommended).
`--sandbox` requires Windows 10/11 Pro/Enterprise with the "Windows Sandbox"
feature enabled.
