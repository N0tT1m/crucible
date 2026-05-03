# firejail-mac

A firejail-shaped front-end for macOS sandboxing. Linux namespaces don't exist
on Darwin, so under the hood this calls `sandbox-exec` (Apple's Seatbelt /
TinyScheme sandbox), `pf` for network restriction, and `launchctl limit` for
resource caps.

## What it gives you (vs upstream firejail)

| Concern        | firejail (Linux)              | firejail-mac (Darwin)                                |
|----------------|-------------------------------|------------------------------------------------------|
| FS isolation   | mount + bind namespaces       | Seatbelt `file-read*` / `file-write*` deny rules     |
| Net isolation  | net namespace + iptables      | Seatbelt `network*` deny + per-uid `pf` rules        |
| PID isolation  | PID namespace                 | (not available — process is still in the host PID ns)|
| Caps / sec     | seccomp-bpf                   | Seatbelt syscall deny via `(deny mach-lookup ...)`   |
| Limits         | rlimits                       | `launchctl limit` + Job Object equivalents           |

PID isolation isn't available without a per-process VM (`Virtualization.framework`
guest), which this tool deliberately doesn't reach for. If you need a hard
boundary, run inside Lima or Docker — covered by a `firejail-mac --lima` flag.

## Usage

```sh
firejail-mac --profile=browser /Applications/Firefox.app/Contents/MacOS/firefox
firejail-mac --profile=no-net curl https://example.com   # blocked
firejail-mac --profile=default --tmpfs=/tmp/test bash
firejail-mac --profile=default --net=none --read-only=$HOME bash
```

## Profile syntax

The on-disk profile uses firejail-style directives where they map cleanly:

```
include default.profile
private-tmp
read-only ${HOME}/.ssh
blacklist ${HOME}/.aws
net none
caps.drop all
```

`firejail_mac/translate.py` converts that to a Seatbelt `.sb`:

```scheme
(version 1)
(deny default)
(allow process-fork)
(allow process-exec)
(deny network*)
(deny file-read* (subpath "/Users/.../.aws"))
(deny file-write* (subpath "/Users/.../.ssh"))
...
```

## Install

```sh
./install.sh
```
