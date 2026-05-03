# crucible launcher (`crux`)

Parrot-style categorized launcher over the local tool suite. Drop a TOML
manifest into `crucible_launcher/manifests/`, `~/.crucible/tools/`, or any
project's `.crucible/tools/` and it shows up in the menu.

## Why

`redbox`, `proxies`, `observatory`, plus every Parrot-equivalent tool you
install via brew/winget/scoop/docker/lima — all in one categorized TUI with
a single install/run flow.

## Install

```sh
cd crucible/launcher
pip install -e .

crux             # launches the TUI
crux list        # category-grouped list
crux doctor      # ✓/· per tool, with install hints
crux install nmap
crux run nmap -- -sV scanme.nmap.org
```

## Manifest format

```toml
name = "nmap"
category = "Information Gathering"
command = "nmap"
help = "Network mapper and port scanner."
args = []                       # always-on flags
requires_sudo = false
macos_only = false
windows_only = false
linux_only = false
install = { brew = "nmap" }     # or: cask, pipx, pip, cargo, go, docker,
                                # lima, winget, scoop, choco, powershell, script
```

`crux install` runs the first applicable installer. Cross-tree manifests
(redbox.toml, observatory.toml, etc.) point `script` or `powershell` at
that project's own `install.sh` / `install.ps1`.

## Categories

Defined in `manifests/_categories.toml` — order is the menu order. Mirrors
Parrot's pentest taxonomy, plus an **AI Red Team** section for crucible's
own tools and a **Reporting** section for Observatory.

## Adding a tool

1. Create `manifests/<tool>.toml` (or drop one into `~/.crucible/tools/`).
2. `crux doctor` to confirm install state.
3. `crux install <tool>` to install via the manifest.
4. `crux run <tool> -- <args>` or pick it from the TUI.

## Adding a project

Same as a tool — point `install.script` or `install.powershell` at the
project's own bootstrap, set `command` to the binary name, and the
launcher will hand off `crux run <project>`.
